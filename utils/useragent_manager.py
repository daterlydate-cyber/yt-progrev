"""
Управление User-Agent строками: случайная генерация и сохранение для профилей.
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Запасные UA на случай если fake-useragent недоступен
FALLBACK_USER_AGENTS = {
    "windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ],
    "mac": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    ],
    "linux": [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
    ],
}

# Файл кэша сгенерированных UA для профилей
UA_CACHE_FILE = Path("data/profiles/ua_cache.json")


class UserAgentManager:
    """Генерация и хранение User-Agent строк для профилей."""

    def __init__(self) -> None:
        self._ua_cache: Dict[str, str] = self._load_cache()
        self._fake_ua = None
        try:
            from fake_useragent import UserAgent
            self._fake_ua = UserAgent()
        except Exception as exc:
            logger.warning(
                "fake-useragent недоступен, используем запасные UA: %s", exc
            )

    def get_random(self, os_type: str = "windows") -> str:
        """
        Получить случайный User-Agent для указанной ОС.

        :param os_type: Тип ОС: "windows", "mac", "linux"
        :return: Строка User-Agent
        """
        if self._fake_ua:
            try:
                if os_type == "windows":
                    return self._fake_ua.chrome
                elif os_type == "mac":
                    return self._fake_ua.safari
                else:
                    return self._fake_ua.firefox
            except Exception as exc:
                logger.debug("Ошибка fake-useragent: %s", exc)

        # Запасные UA
        agents = FALLBACK_USER_AGENTS.get(os_type, FALLBACK_USER_AGENTS["windows"])
        return random.choice(agents)

    def get_consistent(self, profile_name: str, os_type: str = "windows") -> str:
        """
        Получить сохранённый UA для профиля или сгенерировать новый.

        :param profile_name: Имя профиля
        :param os_type: Тип ОС для генерации нового UA
        :return: Строка User-Agent
        """
        if profile_name in self._ua_cache:
            return self._ua_cache[profile_name]

        new_ua = self.get_random(os_type)
        self._ua_cache[profile_name] = new_ua
        self._save_cache()
        return new_ua

    def set_for_profile(self, profile_name: str, user_agent: str) -> None:
        """
        Сохранить конкретный UA для профиля.

        :param profile_name: Имя профиля
        :param user_agent: Строка User-Agent
        """
        self._ua_cache[profile_name] = user_agent
        self._save_cache()

    def _load_cache(self) -> Dict[str, str]:
        """Загрузить кэш UA из файла."""
        if UA_CACHE_FILE.exists():
            try:
                with open(UA_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self) -> None:
        """Сохранить кэш UA в файл."""
        UA_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(UA_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._ua_cache, f, ensure_ascii=False, indent=2)
