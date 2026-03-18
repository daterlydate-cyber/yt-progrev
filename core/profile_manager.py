"""
Модуль управления профилями (CRUD + импорт/экспорт).
Каждый профиль хранится как JSON в data/profiles/{name}/profile.json.
"""

import json
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Базовая папка для хранения профилей
PROFILES_DIR = Path("data/profiles")


class ProfileManager:
    """Управляет профилями браузеров (создание, удаление, импорт/экспорт)."""

    def __init__(self, profiles_dir: Path = PROFILES_DIR) -> None:
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def create_profile(
        self,
        name: str,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        language: str = "ru-RU",
        timezone: str = "Europe/Moscow",
        screen_resolution: str = "1280x720",
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Создать новый профиль.

        :param name: Уникальное имя профиля
        :param proxy: Строка прокси
        :param user_agent: User-Agent строка
        :param language: Язык браузера
        :param timezone: Часовой пояс
        :param screen_resolution: Разрешение экрана
        :param notes: Заметки
        :return: Словарь с данными профиля
        """
        profile_dir = self.profiles_dir / name
        if profile_dir.exists():
            raise ValueError(f"Профиль '{name}' уже существует.")

        profile_dir.mkdir(parents=True)
        (profile_dir / "chrome_data").mkdir(exist_ok=True)

        # Если user_agent не задан — попробуем сгенерировать через UserAgentManager
        if not user_agent:
            try:
                from utils.useragent_manager import UserAgentManager
                user_agent = UserAgentManager().get_consistent(name)
            except Exception:
                user_agent = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )

        profile_data: Dict[str, Any] = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "user_agent": user_agent,
            "proxy": proxy or "",
            "language": language,
            "timezone": timezone,
            "screen_resolution": screen_resolution,
            "status": "active",
            "warmup_progress": {
                "total_sessions": 0,
                "total_actions": 0,
                "last_warmup": None,
            },
            "notes": notes,
        }

        self._save_profile(name, profile_data)
        logger.info("Профиль '%s' создан.", name)
        return profile_data

    def delete_profile(self, name: str) -> None:
        """
        Удалить профиль и все его данные.

        :param name: Имя профиля
        """
        profile_dir = self.profiles_dir / name
        if not profile_dir.exists():
            raise ValueError(f"Профиль '{name}' не найден.")
        shutil.rmtree(profile_dir)

        # Удаляем cookies если есть
        cookies_file = Path("data/cookies") / f"{name}_cookies.json"
        if cookies_file.exists():
            cookies_file.unlink()

        logger.info("Профиль '%s' удалён.", name)

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Получить данные профиля по имени.

        :param name: Имя профиля
        :return: Словарь с данными или None
        """
        profile_file = self.profiles_dir / name / "profile.json"
        if not profile_file.exists():
            return None
        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Ошибка чтения профиля '%s': %s", name, exc)
            return None

    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        Получить список всех профилей.

        :return: Список словарей с данными профилей
        """
        profiles = []
        for profile_dir in sorted(self.profiles_dir.iterdir()):
            if profile_dir.is_dir():
                profile = self.get_profile(profile_dir.name)
                if profile:
                    profiles.append(profile)
        return profiles

    def update_profile(self, name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновить данные профиля.

        :param name: Имя профиля
        :param updates: Словарь с обновляемыми полями
        :return: Обновлённые данные профиля
        """
        profile = self.get_profile(name)
        if profile is None:
            raise ValueError(f"Профиль '{name}' не найден.")
        profile.update(updates)
        self._save_profile(name, profile)
        logger.debug("Профиль '%s' обновлён.", name)
        return profile

    def export_profile(self, name: str, export_path: str) -> str:
        """
        Экспортировать профиль в ZIP-архив.

        :param name: Имя профиля
        :param export_path: Путь для сохранения ZIP
        :return: Путь к созданному архиву
        """
        profile_dir = self.profiles_dir / name
        if not profile_dir.exists():
            raise ValueError(f"Профиль '{name}' не найден.")

        zip_path = Path(export_path)
        if not zip_path.suffix:
            zip_path = zip_path.with_suffix(".zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Добавляем все файлы профиля
            for file_path in profile_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.profiles_dir)
                    zf.write(file_path, arcname)

            # Добавляем cookies если есть
            cookies_file = Path("data/cookies") / f"{name}_cookies.json"
            if cookies_file.exists():
                zf.write(cookies_file, f"cookies/{name}_cookies.json")

        logger.info("Профиль '%s' экспортирован в '%s'.", name, zip_path)
        return str(zip_path)

    def import_profile(self, zip_path: str) -> str:
        """
        Импортировать профиль из ZIP-архива.

        :param zip_path: Путь к ZIP-архиву
        :return: Имя импортированного профиля
        """
        zip_file = Path(zip_path)
        if not zip_file.exists():
            raise FileNotFoundError(f"Файл '{zip_path}' не найден.")

        with zipfile.ZipFile(zip_file, "r") as zf:
            # Определяем имя профиля из структуры архива
            names = zf.namelist()
            profile_name = None
            for n in names:
                parts = Path(n).parts
                if len(parts) >= 2 and parts[1] == "profile.json":
                    profile_name = parts[0]
                    break

            if not profile_name:
                raise ValueError("Невалидный архив профиля: profile.json не найден.")

            # Извлекаем файлы профиля
            for item in zf.infolist():
                item_path = Path(item.filename)
                parts = item_path.parts
                if parts[0] == "cookies":
                    # Cookies сохраняем в data/cookies/
                    dest = Path("data/cookies") / item_path.name
                else:
                    dest = self.profiles_dir / item_path

                dest.parent.mkdir(parents=True, exist_ok=True)
                if not item.is_dir():
                    with zf.open(item) as src, open(dest, "wb") as dst:
                        dst.write(src.read())

        logger.info("Профиль '%s' импортирован.", profile_name)
        return profile_name

    def _save_profile(self, name: str, data: Dict[str, Any]) -> None:
        """Сохранить данные профиля в JSON-файл."""
        profile_file = self.profiles_dir / name / "profile.json"
        with open(profile_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
