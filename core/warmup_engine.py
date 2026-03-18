"""
Движок прогрева аккаунтов YouTube.
Запускается в QThread, выполняет тематический прогрев: поиск, просмотр, лайки, подписки, комментарии.
"""

import logging
import random
from datetime import datetime
from typing import List, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from core.actions import HumanActions
from core.browser_manager import BrowserManager
from core.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class WarmupEngine(QThread):
    """Движок тематического прогрева аккаунтов в отдельном потоке."""

    # Сигналы для обновления GUI
    progress_updated = pyqtSignal(str, int)   # (profile_name, progress_percent)
    action_completed = pyqtSignal(str)         # описание выполненного действия
    error_occurred = pyqtSignal(str)           # сообщение об ошибке
    warmup_finished = pyqtSignal(str)          # имя профиля по завершению

    def __init__(
        self,
        profile_name: str,
        browser_manager: BrowserManager,
        profile_manager: ProfileManager,
        keywords: Optional[List[str]] = None,
        actions_per_session: int = 10,
        watch_duration_range: tuple = (30, 180),
        like_probability: float = 0.3,
        subscribe_probability: float = 0.1,
        comment_probability: float = 0.05,
        comment_templates: Optional[List[str]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile_name = profile_name
        self.browser_manager = browser_manager
        self.profile_manager = profile_manager
        self.keywords = keywords or ["youtube", "видео", "блог"]
        self.actions_per_session = actions_per_session
        self.watch_duration_range = watch_duration_range
        self.like_probability = like_probability
        self.subscribe_probability = subscribe_probability
        self.comment_probability = comment_probability
        self.comment_templates = comment_templates or [
            "Отличное видео! 👍",
            "Очень интересно, спасибо!",
            "Продолжай в том же духе!",
        ]
        self._stop_requested = False

    def stop(self) -> None:
        """Запросить остановку прогрева."""
        self._stop_requested = True

    def run(self) -> None:
        """Основной цикл прогрева — выполняется в отдельном потоке."""
        logger.info("Прогрев профиля '%s' начат.", self.profile_name)

        driver = self.browser_manager.get_driver(self.profile_name)
        if driver is None:
            # Пробуем создать браузер для профиля
            profile = self.profile_manager.get_profile(self.profile_name)
            if profile is None:
                self.error_occurred.emit(
                    f"Профиль '{self.profile_name}' не найден."
                )
                return
            try:
                driver = self.browser_manager.create_browser(
                    profile_name=self.profile_name,
                    proxy=profile.get("proxy") or None,
                    user_agent=profile.get("user_agent"),
                    language=profile.get("language", "ru-RU"),
                )
            except Exception as exc:
                self.error_occurred.emit(
                    f"Не удалось создать браузер: {exc}"
                )
                return

        completed_actions = 0
        try:
            for i in range(self.actions_per_session):
                if self._stop_requested:
                    logger.info("Прогрев остановлен по запросу.")
                    break

                keyword = random.choice(self.keywords)
                self.action_completed.emit(f"🔍 Поиск: '{keyword}'")

                # Шаг 1: Поиск по ключевому слову
                if not HumanActions.search_youtube(driver, keyword):
                    logger.warning("Поиск не выполнен, пропускаем итерацию.")
                    continue

                # Шаг 2: Клик по видео из результатов
                self.action_completed.emit("🎬 Выбираем видео из результатов...")
                if not HumanActions.click_video_from_results(driver):
                    logger.warning("Не удалось кликнуть по видео.")
                    continue

                # Шаг 3: Просмотр видео
                duration = random.randint(*self.watch_duration_range)
                self.action_completed.emit(
                    f"▶️ Смотрим видео ({duration} сек)..."
                )
                HumanActions.watch_video(driver, duration)

                # Шаг 4: Случайный лайк
                if random.random() < self.like_probability:
                    if HumanActions.like_video(driver):
                        self.action_completed.emit("👍 Лайк поставлен")

                # Шаг 5: Случайная подписка
                if random.random() < self.subscribe_probability:
                    if HumanActions.subscribe_channel(driver):
                        self.action_completed.emit("🔔 Подписка оформлена")

                # Шаг 6: Случайный комментарий
                if random.random() < self.comment_probability and self.comment_templates:
                    comment = random.choice(self.comment_templates)
                    if HumanActions.leave_comment(driver, comment):
                        self.action_completed.emit(f"💬 Комментарий: {comment[:40]}...")

                # Шаг 7: Прокрутка ленты рекомендаций
                HumanActions.random_scroll(driver)
                HumanActions.random_delay(1, 3)

                completed_actions += 1
                progress = int((completed_actions / self.actions_per_session) * 100)
                self.progress_updated.emit(self.profile_name, progress)

        except Exception as exc:
            logger.error("Ошибка при прогреве: %s", exc)
            self.error_occurred.emit(str(exc))
        finally:
            # Обновляем статистику профиля
            try:
                profile = self.profile_manager.get_profile(self.profile_name)
                if profile:
                    warmup_progress = profile.get("warmup_progress", {})
                    warmup_progress["total_sessions"] = (
                        warmup_progress.get("total_sessions", 0) + 1
                    )
                    warmup_progress["total_actions"] = (
                        warmup_progress.get("total_actions", 0) + completed_actions
                    )
                    warmup_progress["last_warmup"] = datetime.now().isoformat()
                    self.profile_manager.update_profile(
                        self.profile_name,
                        {"warmup_progress": warmup_progress, "status": "ready"},
                    )
            except Exception as exc:
                logger.error("Ошибка при обновлении статистики профиля: %s", exc)

            logger.info(
                "Прогрев профиля '%s' завершён. Выполнено действий: %d.",
                self.profile_name,
                completed_actions,
            )
            self.warmup_finished.emit(self.profile_name)
