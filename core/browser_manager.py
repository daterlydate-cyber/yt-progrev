"""
Модуль управления браузерами и профилями (антидетект).
Создаёт изолированные экземпляры undetected-chromedriver для каждого профиля.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)


class BrowserManager:
    """Управляет браузерными сессиями с изолированными профилями."""

    def __init__(self) -> None:
        # Словарь активных сессий: {profile_name: driver}
        self._sessions: Dict[str, uc.Chrome] = {}

    def create_browser(
        self,
        profile_name: str,
        proxy: Optional[str] = None,
        headless: bool = False,
        window_size: str = "1280,720",
        language: str = "ru-RU",
        user_agent: Optional[str] = None,
    ) -> uc.Chrome:
        """
        Создать экземпляр браузера с изолированным профилем.

        :param profile_name: Имя профиля (используется как имя папки)
        :param proxy: Строка прокси вида protocol://[user:pass@]host:port
        :param headless: Запустить браузер в фоновом режиме
        :param window_size: Размер окна браузера (ширина,высота)
        :param language: Язык интерфейса браузера
        :param user_agent: User-Agent строка (если None — дефолтный)
        :return: Экземпляр undetected-chromedriver
        """
        if profile_name in self._sessions:
            logger.warning(
                "Браузер для профиля '%s' уже запущен, возвращаем существующий.",
                profile_name,
            )
            return self._sessions[profile_name]

        # Папка с данными Chrome для профиля
        profile_dir = Path("data/profiles") / profile_name / "chrome_data"
        profile_dir.mkdir(parents=True, exist_ok=True)

        options = uc.ChromeOptions()

        # Изолированный user-data-dir
        options.add_argument(f"--user-data-dir={profile_dir.resolve()}")

        # Подмена fingerprint и снижение детектируемости
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument(f"--window-size={window_size}")
        options.add_argument(f"--lang={language}")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        if headless:
            options.add_argument("--headless=new")

        if user_agent:
            options.add_argument(f"--user-agent={user_agent}")

        if proxy:
            formatted_proxy = self._format_proxy(proxy)
            if formatted_proxy:
                options.add_argument(f"--proxy-server={formatted_proxy}")
                logger.debug("Используем прокси: %s", formatted_proxy)

        try:
            driver = uc.Chrome(options=options, use_subprocess=True)
            self._sessions[profile_name] = driver
            logger.info("Браузер для профиля '%s' успешно запущен.", profile_name)
            return driver
        except Exception as exc:
            logger.error(
                "Ошибка при создании браузера для профиля '%s': %s",
                profile_name,
                exc,
            )
            raise

    def close_browser(self, profile_name: str) -> None:
        """
        Закрыть браузер для указанного профиля.

        :param profile_name: Имя профиля
        """
        driver = self._sessions.get(profile_name)
        if driver is None:
            logger.warning(
                "Браузер для профиля '%s' не найден.", profile_name
            )
            return
        try:
            driver.quit()
            logger.info("Браузер профиля '%s' закрыт.", profile_name)
        except Exception as exc:
            logger.error(
                "Ошибка при закрытии браузера '%s': %s", profile_name, exc
            )
        finally:
            del self._sessions[profile_name]

    def close_all(self) -> None:
        """Закрыть все активные браузерные сессии."""
        for name in list(self._sessions.keys()):
            self.close_browser(name)

    def get_driver(self, profile_name: str) -> Optional[uc.Chrome]:
        """
        Получить активный драйвер по имени профиля.

        :param profile_name: Имя профиля
        :return: Экземпляр драйвера или None
        """
        return self._sessions.get(profile_name)

    def list_active_sessions(self) -> list[str]:
        """
        Получить список имён активных сессий.

        :return: Список имён профилей с активными браузерами
        """
        return list(self._sessions.keys())

    @staticmethod
    def _format_proxy(proxy_str: str) -> Optional[str]:
        """
        Форматировать строку прокси для аргумента --proxy-server Chrome.

        :param proxy_str: Строка прокси
        :return: Отформатированная строка или None при ошибке
        """
        try:
            # Chrome принимает proxy-server без указания протокола для auth
            if "://" in proxy_str:
                protocol, rest = proxy_str.split("://", 1)
                if "@" in rest:
                    # Для Chrome прокси с авторизацией формируем только host:port
                    # авторизация задаётся через расширение или отдельный обработчик
                    credentials, host_port = rest.rsplit("@", 1)
                    return f"{protocol}://{host_port}"
                return proxy_str
            return proxy_str
        except Exception as exc:
            logger.error("Ошибка форматирования прокси '%s': %s", proxy_str, exc)
            return None
