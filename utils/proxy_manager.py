"""
Управление прокси: загрузка из файла, проверка доступности, ротация.
"""

import logging
import random
import socket
import urllib.parse
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class ProxyManager:
    """Загрузка, проверка и ротация прокси-серверов."""

    def __init__(self, proxy_list: Optional[List[str]] = None) -> None:
        self._proxies: List[str] = proxy_list or []
        self._index: int = 0  # Для round-robin ротации

    def load_from_file(self, file_path: str) -> int:
        """
        Загрузить прокси из файла (один прокси на строку).

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

        self._proxies = loaded
        self._index = 0
        logger.info("Загружено %d прокси из '%s'.", len(loaded), file_path)
        return len(loaded)

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

    def check_proxy(self, proxy_str: str, timeout: int = 5) -> bool:
        """
        Проверить доступность прокси (простая TCP-проверка).

        :param proxy_str: Строка прокси
        :param timeout: Таймаут в секундах
        :return: True если прокси доступен
        """
        try:
            parsed = urllib.parse.urlparse(proxy_str)
            host = parsed.hostname
            port = parsed.port
            if not host or not port:
                return False

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as exc:
            logger.debug("Ошибка проверки прокси '%s': %s", proxy_str, exc)
            return False

    def format_for_chrome(self, proxy_str: str) -> Optional[str]:
        """
        Форматировать строку прокси для аргумента --proxy-server Chrome.

        Chrome принимает: protocol://host:port (без авторизации в аргументе)

        :param proxy_str: Исходная строка прокси
        :return: Строка для --proxy-server или None при ошибке
        """
        try:
            parsed = urllib.parse.urlparse(proxy_str)
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

    def get_all_proxies(self) -> List[str]:
        """Получить копию списка всех прокси."""
        return list(self._proxies)

    def add_proxy(self, proxy_str: str) -> None:
        """Добавить прокси в список."""
        if proxy_str not in self._proxies:
            self._proxies.append(proxy_str)
