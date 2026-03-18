"""
Планировщик задач прогрева и постинга.
Запускается в QThread, использует библиотеку schedule.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import schedule
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Описание запланированной задачи."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: str = ""           # "warmup" или "posting"
    profile_name: str = ""
    schedule_str: str = ""        # Описание расписания (например, "каждые 6 ч")
    enabled: bool = True
    status: str = "ожидание"      # ожидание / выполняется / завершено / ошибка
    last_run: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class TaskScheduler(QThread):
    """Планировщик задач в фоновом потоке."""

    # Сигналы для обновления GUI
    task_started = pyqtSignal(str)    # task_id
    task_completed = pyqtSignal(str)  # task_id
    task_error = pyqtSignal(str)      # сообщение об ошибке
    post_uploaded = pyqtSignal(str, str)  # post_id, status

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tasks: Dict[str, Task] = {}
        self._running = False

    def run(self) -> None:
        """Основной цикл планировщика."""
        self._running = True
        logger.info("Планировщик задач запущен.")
        while self._running:
            schedule.run_pending()
            time.sleep(1)
        logger.info("Планировщик задач остановлен.")

    def stop(self) -> None:
        """Остановить планировщик."""
        self._running = False

    def add_warmup_task(
        self,
        profile_name: str,
        interval_hours: int,
        warmup_kwargs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Добавить задачу автопрогрева.

        :param profile_name: Имя профиля
        :param interval_hours: Интервал запуска в часах
        :param warmup_kwargs: Дополнительные параметры для WarmupEngine
        :return: ID созданной задачи
        """
        task = Task(
            task_type="warmup",
            profile_name=profile_name,
            schedule_str=f"каждые {interval_hours} ч",
            extra=warmup_kwargs or {},
        )
        self._tasks[task.task_id] = task

        def job():
            self._run_task(task.task_id)

        schedule.every(interval_hours).hours.do(job).tag(task.task_id)
        logger.info(
            "Задача прогрева добавлена: %s, профиль '%s', каждые %d ч.",
            task.task_id,
            profile_name,
            interval_hours,
        )
        return task.task_id

    def add_posting_task(
        self,
        profile_name: str,
        video_path: str,
        metadata: Dict[str, Any],
        time_str: str,
    ) -> str:
        """
        Добавить задачу постинга видео.

        :param profile_name: Имя профиля
        :param video_path: Путь к видеофайлу
        :param metadata: Метаданные видео (title, description, tags, ...)
        :param time_str: Время запуска в формате HH:MM
        :return: ID созданной задачи
        """
        task = Task(
            task_type="posting",
            profile_name=profile_name,
            schedule_str=f"ежедневно в {time_str}",
            extra={"video_path": video_path, "metadata": metadata},
        )
        self._tasks[task.task_id] = task

        def job():
            self._run_task(task.task_id)

        schedule.every().day.at(time_str).do(job).tag(task.task_id)
        logger.info(
            "Задача постинга добавлена: %s, профиль '%s', в %s.",
            task.task_id,
            profile_name,
            time_str,
        )
        return task.task_id

    def add_content_plan_task(self, post_id: str, content_plan) -> str:
        """
        Добавить задачу из контент-плана.

        :param post_id: ID поста в ContentPlan
        :param content_plan: Экземпляр ContentPlan
        :return: ID созданной задачи
        """
        post = content_plan.get_post(post_id)
        if post is None:
            raise ValueError(f"Пост '{post_id}' не найден в контент-плане.")

        task = Task(
            task_type="content_plan",
            profile_name=post.profile_name,
            schedule_str=f"{post.scheduled_date} {post.scheduled_time}",
            extra={"post_id": post_id},
        )
        self._tasks[task.task_id] = task

        def job():
            # Получаем пост свежим из плана, чтобы избежать устаревших данных
            current_post = content_plan.get_post(post_id)
            if current_post is None:
                return  # Пост был удалён
            current_date = datetime.now().strftime("%Y-%m-%d")
            if current_date != current_post.scheduled_date:
                return  # Не тот день — пропускаем
            self._run_content_plan_task(task.task_id, content_plan)

        schedule.every().day.at(post.scheduled_time).do(job).tag(task.task_id)
        logger.info(
            "Задача контент-плана добавлена: %s, пост '%s', в %s %s.",
            task.task_id,
            post_id,
            post.scheduled_date,
            post.scheduled_time,
        )
        return task.task_id

    def _run_content_plan_task(self, task_id: str, content_plan) -> None:
        """Выполнить задачу из контент-плана."""
        task = self._tasks.get(task_id)
        if task is None or not task.enabled:
            return

        post_id = task.extra.get("post_id")
        post = content_plan.get_post(post_id)
        if post is None:
            return

        task.status = "выполняется"
        task.last_run = datetime.now().isoformat()
        self.task_started.emit(task_id)

        try:
            from core.browser_manager import BrowserManager
            from core.poster_engine import PosterEngine

            bm = BrowserManager()
            engine = PosterEngine(
                profile_name=post.profile_name,
                browser_manager=bm,
                video_path=post.video_path,
                title=post.title,
                description=post.description,
                tags=post.tags,
                thumbnail_path=post.thumbnail_path if post.thumbnail_path else None,
                privacy=post.privacy,
            )
            engine.run()

            post.status = "done"
            content_plan.update_post(post)
            task.status = "завершено"
            self.task_completed.emit(task_id)
            self.post_uploaded.emit(post_id, "done")
            logger.info("Пост '%s' успешно загружен планировщиком.", post_id)
        except Exception as exc:
            post.status = "error"
            post.error_msg = str(exc)
            content_plan.update_post(post)
            task.status = "ошибка"
            error_msg = f"Ошибка задачи контент-плана '{task_id}': {exc}"
            logger.error(error_msg)
            self.task_error.emit(error_msg)
            self.post_uploaded.emit(post_id, "error")

    def remove_task(self, task_id: str) -> None:
        """
        Удалить задачу из планировщика.

        :param task_id: ID задачи
        """
        schedule.clear(task_id)
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info("Задача '%s' удалена.", task_id)

    def get_tasks(self) -> List[Task]:
        """
        Получить список всех задач.

        :return: Список задач
        """
        return list(self._tasks.values())

    def _run_task(self, task_id: str) -> None:
        """Выполнить задачу по ID."""
        task = self._tasks.get(task_id)
        if task is None or not task.enabled:
            return

        task.status = "выполняется"
        task.last_run = datetime.now().isoformat()
        self.task_started.emit(task_id)
        logger.info("Запуск задачи '%s' (тип: %s).", task_id, task.task_type)

        try:
            if task.task_type == "warmup":
                self._execute_warmup(task)
            elif task.task_type == "posting":
                self._execute_posting(task)
            task.status = "завершено"
            self.task_completed.emit(task_id)
        except Exception as exc:
            task.status = "ошибка"
            error_msg = f"Ошибка задачи '{task_id}': {exc}"
            logger.error(error_msg)
            self.task_error.emit(error_msg)

    def _execute_warmup(self, task: Task) -> None:
        """Выполнить задачу прогрева синхронно (внутри планировщика)."""
        from core.browser_manager import BrowserManager
        from core.profile_manager import ProfileManager
        from core.warmup_engine import WarmupEngine

        bm = BrowserManager()
        pm = ProfileManager()
        engine = WarmupEngine(
            profile_name=task.profile_name,
            browser_manager=bm,
            profile_manager=pm,
            **task.extra,
        )
        # Запускаем синхронно (не как QThread)
        engine.run()

    def _execute_posting(self, task: Task) -> None:
        """Выполнить задачу постинга синхронно (внутри планировщика)."""
        from core.browser_manager import BrowserManager
        from core.poster_engine import PosterEngine

        bm = BrowserManager()
        meta = task.extra.get("metadata", {})
        engine = PosterEngine(
            profile_name=task.profile_name,
            browser_manager=bm,
            video_path=task.extra.get("video_path", ""),
            title=meta.get("title", ""),
            description=meta.get("description", ""),
            tags=meta.get("tags", []),
            thumbnail_path=meta.get("thumbnail_path"),
            privacy=meta.get("privacy", "public"),
        )
        engine.run()
