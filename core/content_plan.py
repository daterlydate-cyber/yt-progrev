"""
Модель данных и хранилище контент-плана.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PLAN_FILE = Path("data/content_plan.json")


@dataclass
class ScheduledPost:
    """Запись контент-плана — одно запланированное видео."""

    post_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    profile_name: str = ""
    video_path: str = ""
    title: str = ""
    description: str = ""
    tags: list = field(default_factory=list)
    thumbnail_path: str = ""
    privacy: str = "public"          # public / unlisted / private
    scheduled_date: str = ""         # YYYY-MM-DD
    scheduled_time: str = "12:00"    # HH:MM
    status: str = "pending"          # pending / uploading / done / error / cancelled
    error_msg: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()[:16]
    )


class ContentPlan:
    """Хранилище контент-плана: загрузка/сохранение из JSON-файла."""

    def __init__(self) -> None:
        self._posts: Dict[str, ScheduledPost] = {}
        self.load()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_post(self, post: ScheduledPost) -> str:
        """Добавить запись и сохранить план."""
        self._posts[post.post_id] = post
        self.save()
        return post.post_id

    def update_post(self, post: ScheduledPost) -> None:
        """Обновить существующую запись и сохранить план."""
        self._posts[post.post_id] = post
        self.save()

    def remove_post(self, post_id: str) -> None:
        """Удалить запись и сохранить план."""
        self._posts.pop(post_id, None)
        self.save()

    def get_post(self, post_id: str) -> Optional[ScheduledPost]:
        """Получить запись по ID."""
        return self._posts.get(post_id)

    # ------------------------------------------------------------------
    # Запросы
    # ------------------------------------------------------------------

    def get_all_posts(self) -> List[ScheduledPost]:
        """Вернуть все записи."""
        return list(self._posts.values())

    def get_posts_for_date(self, date_str: str) -> List[ScheduledPost]:
        """Вернуть записи для конкретной даты (YYYY-MM-DD)."""
        return [p for p in self._posts.values() if p.scheduled_date == date_str]

    def get_posts_sorted_by_date(self) -> List[ScheduledPost]:
        """Вернуть все записи, отсортированные по дате и времени."""
        return sorted(
            self._posts.values(),
            key=lambda p: (p.scheduled_date, p.scheduled_time),
        )

    # ------------------------------------------------------------------
    # Сериализация
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Сохранить план в JSON-файл."""
        PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PLAN_FILE, "w", encoding="utf-8") as fh:
            json.dump(
                [asdict(p) for p in self._posts.values()],
                fh,
                ensure_ascii=False,
                indent=2,
            )

    def load(self) -> None:
        """Загрузить план из JSON-файла (если существует)."""
        if PLAN_FILE.exists():
            try:
                with open(PLAN_FILE, "r", encoding="utf-8") as fh:
                    for item in json.load(fh):
                        post = ScheduledPost(**item)
                        self._posts[post.post_id] = post
            except Exception:
                pass
