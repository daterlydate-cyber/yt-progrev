"""
Управление cookies: сохранение, загрузка, импорт/экспорт.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

COOKIES_DIR = Path("data/cookies")


class CookieManager:
    """Управление cookies браузерных профилей."""

    def __init__(self, cookies_dir: Path = COOKIES_DIR) -> None:
        self.cookies_dir = cookies_dir
        self.cookies_dir.mkdir(parents=True, exist_ok=True)

    def save_cookies(self, driver, profile_name: str) -> str:
        """
        Сохранить cookies из браузера в JSON-файл.

        :param driver: Экземпляр WebDriver
        :param profile_name: Имя профиля
        :return: Путь к сохранённому файлу
        """
        cookies: List[Dict[str, Any]] = driver.get_cookies()
        file_path = self.cookies_dir / f"{profile_name}_cookies.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        logger.info(
            "Сохранено %d cookies для профиля '%s'.", len(cookies), profile_name
        )
        return str(file_path)

    def load_cookies(self, driver, profile_name: str) -> bool:
        """
        Загрузить cookies из файла в браузер.

        :param driver: Экземпляр WebDriver
        :param profile_name: Имя профиля
        :return: True если cookies загружены успешно
        """
        file_path = self.cookies_dir / f"{profile_name}_cookies.json"
        if not file_path.exists():
            logger.debug("Файл cookies для '%s' не найден.", profile_name)
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cookies: List[Dict[str, Any]] = json.load(f)

            for cookie in cookies:
                # Удаляем поля которые могут вызвать ошибку
                cookie.pop("sameSite", None)
                try:
                    driver.add_cookie(cookie)
                except Exception as exc:
                    logger.debug("Не удалось добавить cookie: %s", exc)

            logger.info(
                "Загружено %d cookies для профиля '%s'.", len(cookies), profile_name
            )
            return True
        except Exception as exc:
            logger.error(
                "Ошибка загрузки cookies для '%s': %s", profile_name, exc
            )
            return False

    def export_cookies(self, profile_name: str, export_path: str) -> str:
        """
        Экспортировать файл cookies профиля.

        :param profile_name: Имя профиля
        :param export_path: Путь для сохранения
        :return: Путь к скопированному файлу
        """
        src = self.cookies_dir / f"{profile_name}_cookies.json"
        if not src.exists():
            raise FileNotFoundError(f"Файл cookies профиля '{profile_name}' не найден.")

        dest = Path(export_path)
        shutil.copy2(src, dest)
        logger.info("Cookies профиля '%s' экспортированы в '%s'.", profile_name, dest)
        return str(dest)

    def import_cookies(self, profile_name: str, import_path: str) -> bool:
        """
        Импортировать cookies из файла.

        :param profile_name: Имя профиля для сохранения
        :param import_path: Путь к файлу cookies
        :return: True если импорт успешен
        """
        src = Path(import_path)
        if not src.exists():
            raise FileNotFoundError(f"Файл '{import_path}' не найден.")

        dest = self.cookies_dir / f"{profile_name}_cookies.json"
        shutil.copy2(src, dest)
        logger.info("Cookies импортированы для профиля '%s'.", profile_name)
        return True

    def delete_cookies(self, profile_name: str) -> None:
        """
        Удалить файл cookies профиля.

        :param profile_name: Имя профиля
        """
        file_path = self.cookies_dir / f"{profile_name}_cookies.json"
        if file_path.exists():
            file_path.unlink()
            logger.info("Cookies профиля '%s' удалены.", profile_name)
