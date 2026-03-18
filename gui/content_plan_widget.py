"""
Виджет контент-плана (SMM-планировщик).
Содержит два режима: «Простое» (SimpleView) и «Расширенное» (AdvancedView).
"""

import json
import logging
from dataclasses import fields as dc_fields
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QDate, QTime, pyqtSignal
from PyQt5.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from core.content_plan import ContentPlan, ScheduledPost
from core.poster_engine import PosterEngine

logger = logging.getLogger(__name__)

_PRIVACY_LABELS = {
    "public": "Публичное",
    "unlisted": "По ссылке",
    "private": "Приватное",
}
_PRIVACY_VALUES = {v: k for k, v in _PRIVACY_LABELS.items()}

_STATUS_LABELS = {
    "pending": "⏳ Ожидание",
    "uploading": "⚙️ Загрузка",
    "done": "✅ Готово",
    "error": "❌ Ошибка",
    "cancelled": "🚫 Отменено",
}

VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm")


# ─────────────────────────────────────────────────────────────────────────────
#  Диалог редактирования поста
# ─────────────────────────────────────────────────────────────────────────────

class EditPostDialog(QDialog):
    """Диалог создания / редактирования запланированного поста."""

    def __init__(self, post: Optional[ScheduledPost], profile_names: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать пост" if post else "Новый пост")
        self.setMinimumWidth(520)
        self._post = post
        self._setup_ui(profile_names)
        if post:
            self._populate(post)

    # ------------------------------------------------------------------

    def _setup_ui(self, profile_names: list) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Профиль
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(profile_names)
        form.addRow("Профиль:", self.profile_combo)

        # Видеофайл
        video_row = QHBoxLayout()
        self.video_edit = QLineEdit()
        self.video_edit.setPlaceholderText("Путь к видеофайлу…")
        video_btn = QPushButton("📂")
        video_btn.setFixedWidth(32)
        video_btn.clicked.connect(self._browse_video)
        video_row.addWidget(self.video_edit)
        video_row.addWidget(video_btn)
        form.addRow("Видеофайл:", video_row)

        # Заголовок
        self.title_edit = QLineEdit()
        form.addRow("Заголовок:", self.title_edit)

        # Описание
        self.desc_edit = QTextEdit()
        self.desc_edit.setFixedHeight(80)
        form.addRow("Описание:", self.desc_edit)

        # Теги
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("тег1, тег2, тег3")
        form.addRow("Теги:", self.tags_edit)

        # Превью
        thumb_row = QHBoxLayout()
        self.thumb_edit = QLineEdit()
        self.thumb_edit.setPlaceholderText("Путь к превью (необязательно)…")
        thumb_btn = QPushButton("📂")
        thumb_btn.setFixedWidth(32)
        thumb_btn.clicked.connect(self._browse_thumb)
        thumb_row.addWidget(self.thumb_edit)
        thumb_row.addWidget(thumb_btn)
        form.addRow("Превью:", thumb_row)

        # Дата публикации
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setCalendarPopup(True)
        form.addRow("Дата публикации:", self.date_edit)

        # Время публикации
        self.time_edit = QTimeEdit(QTime(12, 0))
        self.time_edit.setDisplayFormat("HH:mm")
        form.addRow("Время публикации:", self.time_edit)

        # Доступ
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(list(_PRIVACY_LABELS.values()))
        form.addRow("Доступ:", self.privacy_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------

    def _populate(self, post: ScheduledPost) -> None:
        idx = self.profile_combo.findText(post.profile_name)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        self.video_edit.setText(post.video_path)
        self.title_edit.setText(post.title)
        self.desc_edit.setPlainText(post.description)
        self.tags_edit.setText(", ".join(post.tags))
        self.thumb_edit.setText(post.thumbnail_path)
        if post.scheduled_date:
            self.date_edit.setDate(QDate.fromString(post.scheduled_date, "yyyy-MM-dd"))
        if post.scheduled_time:
            self.time_edit.setTime(QTime.fromString(post.scheduled_time, "HH:mm"))
        label = _PRIVACY_LABELS.get(post.privacy, "Публичное")
        pidx = self.privacy_combo.findText(label)
        if pidx >= 0:
            self.privacy_combo.setCurrentIndex(pidx)

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать видеофайл",
            "",
            "Видеофайлы (*.mp4 *.mov *.avi *.mkv *.webm)",
        )
        if path:
            self.video_edit.setText(path)
            if not self.title_edit.text():
                self.title_edit.setText(Path(path).stem)

    def _browse_thumb(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать превью",
            "",
            "Изображения (*.jpg *.jpeg *.png *.webp)",
        )
        if path:
            self.thumb_edit.setText(path)

    # ------------------------------------------------------------------

    def get_post(self) -> ScheduledPost:
        """Вернуть пост с данными из формы (создаёт новый или обновляет)."""
        tags_raw = self.tags_edit.text()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        privacy_label = self.privacy_combo.currentText()
        privacy = _PRIVACY_VALUES.get(privacy_label, "public")

        if self._post:
            post = self._post
        else:
            post = ScheduledPost()

        post.profile_name = self.profile_combo.currentText()
        post.video_path = self.video_edit.text().strip()
        post.title = self.title_edit.text().strip()
        post.description = self.desc_edit.toPlainText().strip()
        post.tags = tags
        post.thumbnail_path = self.thumb_edit.text().strip()
        post.scheduled_date = self.date_edit.date().toString("yyyy-MM-dd")
        post.scheduled_time = self.time_edit.time().toString("HH:mm")
        post.privacy = privacy
        return post


# ─────────────────────────────────────────────────────────────────────────────
#  SimpleView — календарь + список постов на день
# ─────────────────────────────────────────────────────────────────────────────

class SimpleView(QWidget):
    """Простой вид: календарь слева, список постов на выбранный день справа."""

    # Запросы к родительскому виджету
    add_requested = pyqtSignal()
    edit_requested = pyqtSignal(str)    # post_id
    delete_requested = pyqtSignal(str)  # post_id
    run_requested = pyqtSignal(str)     # post_id

    def __init__(self, content_plan: ContentPlan, parent=None):
        super().__init__(parent)
        self._plan = content_plan
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        # --- Левая панель: Календарь ---
        cal_group = QGroupBox("Календарь")
        cal_layout = QVBoxLayout(cal_group)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.selectionChanged.connect(self._on_date_selected)
        cal_layout.addWidget(self.calendar)
        splitter.addWidget(cal_group)

        # --- Правая панель: Список постов ---
        right_group = QGroupBox("Посты на выбранный день")
        right_layout = QVBoxLayout(right_group)

        self.day_label = QLabel()
        right_layout.addWidget(self.day_label)

        self.post_list = QListWidget()
        self.post_list.setAlternatingRowColors(True)
        self.post_list.itemDoubleClicked.connect(self._on_double_click)
        right_layout.addWidget(self.post_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ Добавить пост")
        add_btn.clicked.connect(self.add_requested.emit)
        edit_btn = QPushButton("✏️ Редактировать")
        edit_btn.clicked.connect(self._emit_edit)
        del_btn = QPushButton("🗑️ Удалить")
        del_btn.clicked.connect(self._emit_delete)
        run_btn = QPushButton("▶️ Запустить сейчас")
        run_btn.clicked.connect(self._emit_run)
        for b in (add_btn, edit_btn, del_btn, run_btn):
            btn_row.addWidget(b)
        right_layout.addLayout(btn_row)

        splitter.addWidget(right_group)
        splitter.setSizes([300, 600])
        layout.addWidget(splitter)

        # Инициализировать отображение
        self._on_date_selected()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Обновить список и подсветку календаря."""
        self._highlight_calendar()
        self._on_date_selected()

    def _selected_date_str(self) -> str:
        return self.calendar.selectedDate().toString("yyyy-MM-dd")

    def _on_date_selected(self) -> None:
        date_str = self._selected_date_str()
        display = self.calendar.selectedDate().toString("d MMMM yyyy")
        self.day_label.setText(f"<b>Посты на {display}:</b>")
        self._refresh_list(date_str)

    def _refresh_list(self, date_str: str) -> None:
        self.post_list.clear()
        posts = self._plan.get_posts_for_date(date_str)
        posts.sort(key=lambda p: p.scheduled_time)
        for post in posts:
            status = _STATUS_LABELS.get(post.status, post.status)
            text = f"{post.scheduled_time}  |  {post.profile_name}  |  {post.title}  |  {status}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, post.post_id)
            self.post_list.addItem(item)

    def _highlight_calendar(self) -> None:
        """Сбросить форматирование и подсветить дни с постами."""
        from PyQt5.QtGui import QTextCharFormat, QColor
        default_fmt = QTextCharFormat()
        # Сбрасываем только текущий месяц (±2 месяца) для производительности
        current = self.calendar.selectedDate()
        for delta in range(-60, 61):
            d = current.addDays(delta)
            self.calendar.setDateTextFormat(d, default_fmt)

        highlight_fmt = QTextCharFormat()
        highlight_fmt.setBackground(QColor("#4CAF50"))
        highlight_fmt.setForeground(QColor("#ffffff"))

        for post in self._plan.get_all_posts():
            if post.scheduled_date:
                qdate = QDate.fromString(post.scheduled_date, "yyyy-MM-dd")
                if qdate.isValid():
                    self.calendar.setDateTextFormat(qdate, highlight_fmt)

    def _current_post_id(self) -> Optional[str]:
        item = self.post_list.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None

    def _on_double_click(self, item: QListWidgetItem) -> None:
        post_id = item.data(Qt.UserRole)
        if post_id:
            self.edit_requested.emit(post_id)

    def _emit_edit(self) -> None:
        post_id = self._current_post_id()
        if post_id:
            self.edit_requested.emit(post_id)

    def _emit_delete(self) -> None:
        post_id = self._current_post_id()
        if post_id:
            self.delete_requested.emit(post_id)

    def _emit_run(self) -> None:
        post_id = self._current_post_id()
        if post_id:
            self.run_requested.emit(post_id)


# ─────────────────────────────────────────────────────────────────────────────
#  AdvancedView — полная таблица + пакетные операции
# ─────────────────────────────────────────────────────────────────────────────

_ADV_COLS = ["Дата", "Время", "Профиль", "Видеофайл", "Заголовок", "Доступ", "Статус"]
_COL_DATE, _COL_TIME, _COL_PROFILE, _COL_VIDEO, _COL_TITLE, _COL_PRIVACY, _COL_STATUS = range(7)


class AdvancedView(QWidget):
    """Расширенный вид: таблица всех постов + пакетные операции."""

    edit_requested = pyqtSignal(str)   # post_id
    run_requested = pyqtSignal(list)   # [post_id, ...]

    def __init__(self, content_plan: ContentPlan, profile_manager, parent=None):
        super().__init__(parent)
        self._plan = content_plan
        self._pm = profile_manager
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Кнопки инструментов
        toolbar = QHBoxLayout()
        import_btn = QPushButton("📁 Импорт папки")
        import_btn.clicked.connect(self._import_folder)
        select_all_btn = QPushButton("✅ Выбрать все")
        select_all_btn.clicked.connect(self._select_all)
        del_sel_btn = QPushButton("🗑️ Удалить выбранные")
        del_sel_btn.clicked.connect(self._delete_selected)
        run_sel_btn = QPushButton("📤 Запустить выбранные")
        run_sel_btn.clicked.connect(self._run_selected)
        for w in (import_btn, select_all_btn, del_sel_btn, run_sel_btn):
            toolbar.addWidget(w)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Таблица
        self.table = QTableWidget(0, len(_ADV_COLS))
        self.table.setHorizontalHeaderLabels(_ADV_COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        # Прогресс пакетного запуска
        prog_group = QGroupBox("Пакетный запуск")
        prog_layout = QVBoxLayout(prog_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.upload_status = QLabel("Готово")
        prog_layout.addWidget(self.progress_bar)
        prog_layout.addWidget(self.upload_status)
        layout.addWidget(prog_group)

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Перестроить таблицу из плана."""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for post in self._plan.get_posts_sorted_by_date():
            self._append_row(post)
        self.table.setSortingEnabled(True)

    def _append_row(self, post: ScheduledPost) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        values = [
            post.scheduled_date,
            post.scheduled_time,
            post.profile_name,
            Path(post.video_path).name if post.video_path else "",
            post.title,
            _PRIVACY_LABELS.get(post.privacy, post.privacy),
            _STATUS_LABELS.get(post.status, post.status),
        ]
        for col, val in enumerate(values):
            item = QTableWidgetItem(str(val))
            item.setData(Qt.UserRole, post.post_id)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, col, item)

    # ------------------------------------------------------------------

    def _import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выбрать папку с видео")
        if not folder:
            return
        profile_names = [p["name"] for p in self._pm.list_profiles()]
        default_profile = profile_names[0] if profile_names else ""

        added = 0
        for path in sorted(Path(folder).iterdir()):
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                post = ScheduledPost(
                    profile_name=default_profile,
                    video_path=str(path),
                    title=path.stem,
                )
                self._plan.add_post(post)
                self._append_row(post)
                added += 1

        if added:
            logger.info("Импортировано %d видеофайлов из папки '%s'.", added, folder)
        else:
            QMessageBox.information(self, "Импорт", "В папке не найдено видеофайлов.")

    def _select_all(self) -> None:
        self.table.selectAll()

    def _delete_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.table.selectedIndexes()},
            reverse=True,
        )
        if not rows:
            return
        reply = QMessageBox.question(
            self,
            "Удалить",
            f"Удалить {len(rows)} запись(ей)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                post_id = item.data(Qt.UserRole)
                self._plan.remove_post(post_id)
            self.table.removeRow(row)

    def _run_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        post_ids = []
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                post_ids.append(item.data(Qt.UserRole))
        if post_ids:
            self.run_requested.emit(post_ids)

    def _on_double_click(self, item: QTableWidgetItem) -> None:
        post_id = item.data(Qt.UserRole)
        if post_id:
            self.edit_requested.emit(post_id)

    # ------------------------------------------------------------------

    def set_upload_progress(self, description: str, percent: int) -> None:
        self.upload_status.setText(description)
        self.progress_bar.setValue(percent)

    def update_post_row(self, post_id: str) -> None:
        """Обновить строку в таблице для указанного поста."""
        post = self._plan.get_post(post_id)
        if post is None:
            return
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == post_id:
                self.table.item(row, _COL_STATUS).setText(
                    _STATUS_LABELS.get(post.status, post.status)
                )
                break


# ─────────────────────────────────────────────────────────────────────────────
#  ContentPlanWidget — основной виджет с двумя режимами
# ─────────────────────────────────────────────────────────────────────────────

class ContentPlanWidget(QWidget):
    """Виджет SMM-планировщика с вкладками «Простое» и «Расширенное»."""

    post_status_changed = pyqtSignal(str, str)  # post_id, status

    def __init__(self, profile_manager, browser_manager, scheduler, parent=None):
        super().__init__(parent)
        self._pm = profile_manager
        self._bm = browser_manager
        self._scheduler = scheduler
        self._plan = ContentPlan()
        self._active_engine = None  # PosterEngine при пакетном запуске
        self._batch_queue: list = []
        self._setup_ui()

    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Счётчик ---
        self.counter_label = QLabel()
        self._update_counter()
        layout.addWidget(self.counter_label)

        # --- Вкладки режимов ---
        self.mode_tabs = QTabWidget()

        self.simple_view = SimpleView(self._plan, self)
        self.simple_view.add_requested.connect(self._add_post)
        self.simple_view.edit_requested.connect(self._edit_post)
        self.simple_view.delete_requested.connect(self._delete_post)
        self.simple_view.run_requested.connect(lambda pid: self._run_posts([pid]))

        self.advanced_view = AdvancedView(self._plan, self._pm, self)
        self.advanced_view.edit_requested.connect(self._edit_post)
        self.advanced_view.run_requested.connect(self._run_posts)

        self.mode_tabs.addTab(self.simple_view, "🗓️ Простое")
        self.mode_tabs.addTab(self.advanced_view, "📊 Расширенное")
        self.mode_tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.mode_tabs)

        # --- Нижняя панель кнопок ---
        bottom = QHBoxLayout()
        save_btn = QPushButton("💾 Сохранить план")
        save_btn.clicked.connect(self._save_plan)
        load_btn = QPushButton("📥 Загрузить план")
        load_btn.clicked.connect(self._load_plan)
        bottom.addWidget(save_btn)
        bottom.addWidget(load_btn)
        bottom.addStretch()
        layout.addLayout(bottom)

        # Первичное обновление обеих вкладок
        self._refresh_all()

    # ------------------------------------------------------------------
    # Вспомогательные
    # ------------------------------------------------------------------

    def _profile_names(self) -> list:
        return [p["name"] for p in self._pm.list_profiles()]

    def _update_counter(self) -> None:
        posts = self._plan.get_all_posts()
        total = len(posts)
        pending = sum(1 for p in posts if p.status == "pending")
        done = sum(1 for p in posts if p.status == "done")
        errors = sum(1 for p in posts if p.status == "error")
        self.counter_label.setText(
            f"Всего постов: <b>{total}</b> | "
            f"Запланировано: <b>{pending}</b> | "
            f"Выполнено: <b>{done}</b> | "
            f"Ошибок: <b>{errors}</b>"
        )
        self.counter_label.setTextFormat(Qt.RichText)

    def _refresh_all(self) -> None:
        self._update_counter()
        self.simple_view.refresh()
        self.advanced_view.refresh()

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self.simple_view.refresh()
        else:
            self.advanced_view.refresh()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def _add_post(self) -> None:
        profile_names = self._profile_names()
        dialog = EditPostDialog(None, profile_names, self)
        if dialog.exec_() == QDialog.Accepted:
            post = dialog.get_post()
            if not post.video_path:
                QMessageBox.warning(self, "Ошибка", "Укажите путь к видеофайлу.")
                return
            self._plan.add_post(post)
            self._refresh_all()
            logger.info("Добавлен пост '%s' (%s).", post.title, post.post_id)

    def _edit_post(self, post_id: str) -> None:
        post = self._plan.get_post(post_id)
        if post is None:
            return
        dialog = EditPostDialog(post, self._profile_names(), self)
        if dialog.exec_() == QDialog.Accepted:
            updated = dialog.get_post()
            self._plan.update_post(updated)
            self._refresh_all()
            logger.info("Пост '%s' обновлён.", post_id)

    def _delete_post(self, post_id: str) -> None:
        post = self._plan.get_post(post_id)
        if post is None:
            return
        reply = QMessageBox.question(
            self,
            "Удалить пост",
            f"Удалить пост «{post.title}»?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._plan.remove_post(post_id)
            self._refresh_all()
            logger.info("Пост '%s' удалён.", post_id)

    # ------------------------------------------------------------------
    # Запуск постов
    # ------------------------------------------------------------------

    def _run_posts(self, post_ids: list) -> None:
        """Запустить посты последовательно через PosterEngine (QThread)."""
        if not post_ids:
            return
        if self._active_engine and self._active_engine.isRunning():
            QMessageBox.warning(self, "Занято", "Загрузка уже выполняется.")
            return
        self._batch_queue = list(post_ids)
        self._run_next_in_queue()

    def _run_next_in_queue(self) -> None:
        if not self._batch_queue:
            self.advanced_view.set_upload_progress("Все загрузки завершены.", 100)
            return

        post_id = self._batch_queue.pop(0)
        post = self._plan.get_post(post_id)
        if post is None:
            self._run_next_in_queue()
            return

        if not post.video_path or not Path(post.video_path).exists():
            post.status = "error"
            post.error_msg = "Видеофайл не найден."
            self._plan.update_post(post)
            self._on_post_status(post_id, "error")
            self._run_next_in_queue()
            return

        post.status = "uploading"
        self._plan.update_post(post)
        self._on_post_status(post_id, "uploading")

        engine = PosterEngine(
            profile_name=post.profile_name,
            browser_manager=self._bm,
            video_path=post.video_path,
            title=post.title,
            description=post.description,
            tags=post.tags,
            thumbnail_path=post.thumbnail_path if post.thumbnail_path else None,
            privacy=post.privacy,
        )
        self._active_engine = engine

        def on_progress(desc: str, pct: int) -> None:
            self.advanced_view.set_upload_progress(
                f"[{post.title}] {desc}", pct
            )

        def on_completed() -> None:
            post.status = "done"
            self._plan.update_post(post)
            self._on_post_status(post_id, "done")
            logger.info("Пост '%s' успешно загружен.", post_id)
            self._run_next_in_queue()

        def on_error(msg: str) -> None:
            post.status = "error"
            post.error_msg = msg
            self._plan.update_post(post)
            self._on_post_status(post_id, "error")
            logger.error("Ошибка загрузки поста '%s': %s", post_id, msg)
            self._run_next_in_queue()

        engine.upload_progress.connect(on_progress)
        engine.upload_completed.connect(on_completed)
        engine.error_occurred.connect(on_error)
        engine.start()

    def _on_post_status(self, post_id: str, status: str) -> None:
        self._update_counter()
        self.advanced_view.update_post_row(post_id)
        self.simple_view.refresh()
        self.post_status_changed.emit(post_id, status)

    # ------------------------------------------------------------------
    # Сохранение / загрузка
    # ------------------------------------------------------------------

    def _save_plan(self) -> None:
        self._plan.save()
        QMessageBox.information(self, "Сохранено", "Контент-план сохранён.")

    def _load_plan(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить контент-план", "", "JSON файлы (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Создаём новый план и загружаем из выбранного файла
            allowed_keys = {f.name for f in dc_fields(ScheduledPost)}
            for item in data:
                filtered = {k: v for k, v in item.items() if k in allowed_keys}
                post = ScheduledPost(**filtered)
                self._plan.add_post(post)
            self._refresh_all()
            logger.info("Загружен контент-план из '%s'.", path)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить план:\n{exc}")
