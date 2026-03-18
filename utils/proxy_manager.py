"""
Управление прокси: загрузка из файла, проверка доступности, ротация, сохранение.
"""

import json
import logging
import random
import socket
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_SAVED_PROXIES_FILE = "data/proxies_saved.json"


class ProxyManager:
    """Загрузка, проверка и ротация прокси-серверов с поддержкой сохранения."""

    def __init__(
        self,
        proxy_list: Optional[List[str]] = None,
        saved_proxies_file: str = DEFAULT_SAVED_PROXIES_FILE,
        auto_save: bool = True,
    ) -> None:
        self._proxies: List[str] = proxy_list or []
        self._index: int = 0  # Для round-robin ротации
        self._saved_proxies_file = Path(saved_proxies_file)
        self._auto_save = auto_save
        # Метаданные прокси: {proxy_str: {last_check, status, ping, country, added_at}}
        self._proxy_meta: Dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Загрузка / сохранение
    # ------------------------------------------------------------------

    def load_from_file(self, file_path: str) -> int:
        """
        Загрузить прокси из текстового файла (один прокси на строку).

        Формат строки: protocol://[user:pass@]host:port

        :param file_path: Путь к файлу с прокси
        :return: Количество загруженных прокси
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning("Файл прокси '%s' не найден.", file_path)
            return 0

        loaded = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                proxy = line.strip()
                if proxy and not proxy.startswith("#"):
                    loaded.append(proxy)

        for proxy in loaded:
            if proxy not in self._proxies:
                self._proxies.append(proxy)
                if proxy not in self._proxy_meta:
                    self._proxy_meta[proxy] = self._default_meta()

        self._index = 0
        logger.info("Загружено %d прокси из '%s'.", len(loaded), file_path)
        if self._auto_save:
            self.save_proxies()
        return len(loaded)

    def save_proxies(self) -> None:
        """Сохранить текущий список прокси и метаданные в JSON файл."""
        try:
            self._saved_proxies_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "proxies": self._proxies,
                "meta": self._proxy_meta,
            }
            with open(self._saved_proxies_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("Прокси сохранены в '%s'.", self._saved_proxies_file)
        except Exception as exc:
            logger.error("Ошибка сохранения прокси: %s", exc)

    def load_saved_proxies(self) -> int:
        """
        Загрузить сохранённые прокси из JSON файла.

        :return: Количество загруженных прокси
        """
        if not self._saved_proxies_file.exists():
            logger.debug("Файл сохранённых прокси '%s' не найден.", self._saved_proxies_file)
            return 0

        try:
            with open(self._saved_proxies_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._proxies = data.get("proxies", [])
            self._proxy_meta = data.get("meta", {})
            self._index = 0
            logger.info(
                "Загружено %d прокси из '%s'.", len(self._proxies), self._saved_proxies_file
            )
            return len(self._proxies)
        except Exception as exc:
            logger.error("Ошибка загрузки сохранённых прокси: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # CRUD прокси
    # ------------------------------------------------------------------

    def add_proxy(self, proxy_str: str) -> None:
        """
        Добавить прокси в список.

        :param proxy_str: Строка прокси
        """
        proxy_str = proxy_str.strip()
        if proxy_str and proxy_str not in self._proxies:
            self._proxies.append(proxy_str)
            self._proxy_meta[proxy_str] = self._default_meta()
            if self._auto_save:
                self.save_proxies()

    def remove_proxy(self, proxy_str: str) -> bool:
        """
        Удалить прокси из списка.

        :param proxy_str: Строка прокси
        :return: True если прокси был удалён
        """
        if proxy_str in self._proxies:
            self._proxies.remove(proxy_str)
            self._proxy_meta.pop(proxy_str, None)
            if self._auto_save:
                self.save_proxies()
            return True
        return False

    def remove_dead_proxies(self) -> int:
        """
        Удалить все прокси со статусом 'dead'.

        :return: Количество удалённых прокси
        """
        dead = [
            p for p in self._proxies
            if self._proxy_meta.get(p, {}).get("status") == "dead"
        ]
        for p in dead:
            self._proxies.remove(p)
            self._proxy_meta.pop(p, None)
        if dead and self._auto_save:
            self.save_proxies()
        return len(dead)

    # ------------------------------------------------------------------
    # Ротация
    # ------------------------------------------------------------------

    def get_next_proxy(self, mode: str = "round-robin") -> Optional[str]:
        """
        Получить следующий прокси.

        :param mode: Режим ротации: "round-robin" или "random"
        :return: Строка прокси или None если список пуст
        """
        if not self._proxies:
            return None

        if mode == "random":
            return random.choice(self._proxies)

        # Round-robin
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy

    def get_all_proxies(self) -> List[str]:
        """Получить копию списка всех прокси."""
        return list(self._proxies)

    # ------------------------------------------------------------------
    # Информация и проверка
    # ------------------------------------------------------------------

    def get_proxy_info(self, proxy_str: str) -> dict:
        """
        Распарсить строку прокси и вернуть словарь с полями.

        Поддерживает форматы:
        - ``protocol://user:pass@host:port``
        - ``host:port:user:pass``
        - ``host:port``

        :param proxy_str: Строка прокси
        :return: Словарь с полями: protocol, host, port, username, password,
                 last_check, status, ping, country
        """
        meta = self._proxy_meta.get(proxy_str, self._default_meta())

        # Нормализуем строку к URL-формату
        normalized = self._normalize_proxy_str(proxy_str)

        try:
            parsed = urllib.parse.urlparse(normalized)
            return {
                "raw": proxy_str,
                "protocol": parsed.scheme or "http",
                "host": parsed.hostname or "",
                "port": parsed.port or 0,
                "username": parsed.username or "",
                "password": parsed.password or "",
                "last_check": meta.get("last_check", ""),
                "status": meta.get("status", "unknown"),
                "ping": meta.get("ping", -1),
                "country": meta.get("country", ""),
                "added_at": meta.get("added_at", ""),
            }
        except Exception:
            return {
                "raw": proxy_str,
                "protocol": "http",
                "host": "",
                "port": 0,
                "username": "",
                "password": "",
                "last_check": meta.get("last_check", ""),
                "status": meta.get("status", "unknown"),
                "ping": meta.get("ping", -1),
                "country": meta.get("country", ""),
                "added_at": meta.get("added_at", ""),
            }

    def check_proxy(self, proxy_str: str, timeout: int = 5) -> bool:
        """
        Проверить доступность прокси (простая TCP-проверка).

        :param proxy_str: Строка прокси
        :param timeout: Таймаут в секундах
        :return: True если прокси доступен
        """
        result = self.check_proxy_detailed(proxy_str, timeout=timeout)
        return result["alive"]

    def check_proxy_detailed(self, proxy_str: str, timeout: int = 5) -> dict:
        """
        Проверить прокси с замером пинга и определением страны.

        :param proxy_str: Строка прокси
        :param timeout: Таймаут в секундах
        :return: Словарь с полями: alive, ping_ms, country, status, error
        """
        info = self.get_proxy_info(proxy_str)
        host = info["host"]
        port = info["port"]
        result: dict = {
            "alive": False,
            "ping_ms": -1,
            "country": "",
            "status": "dead",
            "error": "",
        }

        if not host or not port:
            result["error"] = "Неверный формат прокси"
            self._update_meta(proxy_str, result)
            return result

        try:
            start = time.monotonic()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            conn_result = sock.connect_ex((host, port))
            elapsed = time.monotonic() - start
            sock.close()

            if conn_result == 0:
                result["alive"] = True
                result["ping_ms"] = round(elapsed * 1000)
                result["status"] = "alive"
                result["country"] = self._get_country_by_ip(host)
            else:
                result["error"] = f"TCP connect вернул код {conn_result}"
        except socket.timeout:
            result["error"] = "Таймаут подключения"
        except Exception as exc:
            result["error"] = str(exc)

        self._update_meta(proxy_str, result)
        if self._auto_save:
            self.save_proxies()
        return result

    def format_for_chrome(self, proxy_str: str) -> Optional[str]:
        """
        Форматировать строку прокси для аргумента --proxy-server Chrome.

        Chrome принимает: protocol://host:port (без авторизации в аргументе)

        :param proxy_str: Исходная строка прокси
        :return: Строка для --proxy-server или None при ошибке
        """
        try:
            normalized = self._normalize_proxy_str(proxy_str)
            parsed = urllib.parse.urlparse(normalized)
            scheme = parsed.scheme or "http"
            host = parsed.hostname
            port = parsed.port
            if not host:
                return None
            if port:
                return f"{scheme}://{host}:{port}"
            return f"{scheme}://{host}"
        except Exception as exc:
            logger.error("Ошибка форматирования прокси '%s': %s", proxy_str, exc)
            return None

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _default_meta() -> dict:
        """Вернуть словарь метаданных по умолчанию."""
        return {
            "last_check": "",
            "status": "unknown",
            "ping": -1,
            "country": "",
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    def _update_meta(self, proxy_str: str, check_result: dict) -> None:
        """Обновить метаданные прокси после проверки."""
        if proxy_str not in self._proxy_meta:
            self._proxy_meta[proxy_str] = self._default_meta()
        self._proxy_meta[proxy_str]["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._proxy_meta[proxy_str]["status"] = check_result.get("status", "dead")
        self._proxy_meta[proxy_str]["ping"] = check_result.get("ping_ms", -1)
        self._proxy_meta[proxy_str]["country"] = check_result.get("country", "")

    @staticmethod
    def _normalize_proxy_str(proxy_str: str) -> str:
        """
        Нормализовать строку прокси к формату URL.

        Поддерживает форматы:
        - ``protocol://user:pass@host:port`` (уже готов)
        - ``host:port:user:pass``
        - ``host:port``

        :param proxy_str: Исходная строка прокси
        :return: Строка в URL-формате
        """
        if "://" in proxy_str:
            return proxy_str
        parts = proxy_str.split(":")
        if len(parts) == 4:
            # host:port:user:pass
            host, port, user, password = parts
            return f"http://{user}:{password}@{host}:{port}"
        if len(parts) == 2:
            # host:port
            return f"http://{proxy_str}"
        return f"http://{proxy_str}"

    @staticmethod
    def _get_country_by_ip(host: str) -> str:
        """
        Определить страну по IP-адресу через ip-api.com.

        Используется бесплатный эндпоинт ip-api.com (лимит: 45 запросов/мин).
        При любой ошибке (недоступность, превышение лимита и т.д.) возвращает пустую строку.

        :param host: IP-адрес или хост
        :return: Двухбуквенный код страны или пустая строка
        """
        try:
            import urllib.request
            url = f"http://ip-api.com/json/{host}?fields=countryCode"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                return data.get("countryCode", "")
        except Exception:
            return ""
