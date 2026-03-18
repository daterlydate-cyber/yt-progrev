"""
Виджет публикации видео на YouTube — с вкладками New Post / Queue / History.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.browser_manager import BrowserManager
from core.poster_engine import PosterEngine
from core.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class PosterWidget(QWidget):
    """Widget for video publishing with tabs: New Post / Queue / History."""

    HISTORY_COLUMNS = ["Дата", "Профиль", "Файл", "Заголовок", "Статус"]
    QUEUE_COLUMNS = ["ID", "Дата/Время", "Аккаунт", "Заголовок", "Статус"]

    def __init__(
        self,
        profile_manager: ProfileManager,
        browser_manager: BrowserManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.browser_manager = browser_manager
        self._engine: Optional[PosterEngine] = None
        self._selected_video: Optional[str] = None
        self._selected_thumbnail: Optional[str] = None
        self._setup_ui()
        self.refresh_profiles()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("📝 Публикация")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setObjectName("pageTitle")
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_new_post_tab(), "📤 Новый пост")
        self.tabs.addTab(self._create_queue_tab(), "📅 Очередь")
        self.tabs.addTab(self._create_history_tab(), "📋 История")
        layout.addWidget(self.tabs)

    def _create_new_post_tab(self) -> QWidget:
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Account selection
        upload_group = QGroupBox("Настройки публикации")
        upload_layout = QVBoxLayout(upload_group)

        prof_row = QHBoxLayout()
        prof_row.addWidget(QLabel("Аккаунт:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        prof_row.addWidget(self.profile_combo)
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setMaximumWidth(36)
        self.refresh_btn.clicked.connect(self.refresh_profiles)
        prof_row.addWidget(self.refresh_btn)
        prof_row.addStretch()
        upload_layout.addLayout(prof_row)

        # Video file
        video_row = QHBoxLayout()
        video_row.addWidget(QLabel("Видеофайл:"))
        self.video_path_label = QLabel("Файл не выбран")
        self.video_path_label.setObjectName("fileLabel")
        video_row.addWidget(self.video_path_label, stretch=1)
        self.select_video_btn = QPushButton("📁 Выбрать видео")
        self.select_video_btn.clicked.connect(self._select_video)
        video_row.addWidget(self.select_video_btn)
        upload_layout.addLayout(video_row)

        # Title with char counter
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Заголовок:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название видео (макс. 100 символов)")
        self.title_edit.setMaxLength(100)
        self.title_edit.textChanged.connect(self._on_title_changed)
        title_row.addWidget(self.title_edit)
        self.title_counter = QLabel("0/100")
        self.title_counter.setStyleSheet("color: #a0a0b0;")
        title_row.addWidget(self.title_counter)
        upload_layout.addLayout(title_row)

        # Description with char counter
        desc_label_row = QHBoxLayout()
        desc_label_row.addWidget(QLabel("Описание:"))
        self.desc_counter = QLabel("0/5000")
        self.desc_counter.setStyleSheet("color: #a0a0b0;")
        desc_label_row.addStretch()
        desc_label_row.addWidget(self.desc_counter)
        upload_layout.addLayout(desc_label_row)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("Описание видео (макс. 5000 символов)...")
        self.desc_edit.textChanged.connect(self._on_desc_changed)
        upload_layout.addWidget(self.desc_edit)

        # Tags
        tags_row = QHBoxLayout()
        tags_row.addWidget(QLabel("Теги:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("тег1, тег2, тег3 (через запятую)")
        tags_row.addWidget(self.tags_edit)
        upload_layout.addLayout(tags_row)

        # Thumbnail
        thumb_row = QHBoxLayout()
        thumb_row.addWidget(QLabel("Превью (thumbnail):"))
        self.thumbnail_label = QLabel("Не выбрано")
        self.thumbnail_label.setObjectName("fileLabel")
        thumb_row.addWidget(self.thumbnail_label, stretch=1)
        self.thumbnail_btn = QPushButton("🖼️ Выбрать превью")
        self.thumbnail_btn.clicked.connect(self._select_thumbnail)
        thumb_row.addWidget(self.thumbnail_btn)
        upload_layout.addLayout(thumb_row)

        # Privacy + Category row
        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Доступ:"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["Публичное", "По ссылке", "Приватное"])
        opts_row.addWidget(self.privacy_combo)

        opts_row.addSpacing(16)
        opts_row.addWidget(QLabel("Категория:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Без категории", "Авто/транспорт", "Музыка", "Животные",
            "Спорт", "Путешествия", "Игры", "Видеоблог",
            "Люди и блоги", "Комедия", "Развлечения", "Новости",
            "Политика", "Как это устроено", "Образование",
            "Наука и техника", "Фильмы", "НКО и активизм"
        ])
        opts_row.addWidget(self.category_combo)
        opts_row.addStretch()
        upload_layout.addLayout(opts_row)

        main_layout.addWidget(upload_group)

        # Upload controls
        ctrl_group = QGroupBox("Загрузка")
        ctrl_layout = QVBoxLayout(ctrl_group)

        btn_row = QHBoxLayout()
        self.upload_btn = QPushButton("📤 Опубликовать сейчас")
        self.upload_btn.setMinimumHeight(44)
        self.upload_btn.setObjectName("accentButton")
        self.upload_btn.clicked.connect(self._start_upload)
        btn_row.addWidget(self.upload_btn)

        self.schedule_btn = QPushButton("📅 Запланировать")
        self.schedule_btn.setMinimumHeight(44)
        self.schedule_btn.clicked.connect(self._schedule_post)
        btn_row.addWidget(self.schedule_btn)
        ctrl_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        ctrl_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ожидание...")
        ctrl_layout.addWidget(self.status_label)

        main_layout.addWidget(ctrl_group)
        return widget

    def _create_queue_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self._refresh_queue)
        toolbar.addWidget(refresh_btn)

        clear_btn = QPushButton("🗑️ Очистить завершённые")
        clear_btn.clicked.connect(self._clear_completed)
        toolbar.addWidget(clear_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.queue_table = QTableWidget(0, len(self.QUEUE_COLUMNS))
        self.queue_table.setHorizontalHeaderLabels(self.QUEUE_COLUMNS)
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.queue_table.setAlternatingRowColors(True)
        layout.addWidget(self.queue_table)
        return widget

    def _create_history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        toolbar = QHBoxLayout()
        clear_btn = QPushButton("🗑️ Очистить историю")
        clear_btn.clicked.connect(self._clear_history)
        toolbar.addWidget(clear_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.history_table = QTableWidget(0, len(self.HISTORY_COLUMNS))
        self.history_table.setHorizontalHeaderLabels(self.HISTORY_COLUMNS)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)
        return widget

    def refresh_profiles(self) -> None:
        current = self.profile_combo.currentText()
        self.profile_combo.clear()
        for p in self.profile_manager.list_profiles():
            self.profile_combo.addItem(p["name"])
        idx = self.profile_combo.findText(current)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

    def _on_title_changed(self, text: str) -> None:
        self.title_counter.setText(f"{len(text)}/100")

    def _on_desc_changed(self) -> None:
        text = self.desc_edit.toPlainText()
        if len(text) > 5000:
            cursor = self.desc_edit.textCursor()
            self.desc_edit.setPlainText(text[:5000])
            self.desc_edit.setTextCursor(cursor)
        self.desc_counter.setText(f"{min(len(text), 5000)}/5000")

    def _select_video(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать видео", "data/videos",
            "Видеофайлы (*.mp4 *.mov *.avi *.mkv *.webm);;Все файлы (*.*)",
        )
        if file_path:
            self._selected_video = file_path
            self.video_path_label.setText(Path(file_path).name)
            if not self.title_edit.text():
                self.title_edit.setText(Path(file_path).stem)

    def _select_thumbnail(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать превью", "",
            "Изображения (*.jpg *.jpeg *.png *.webp);;Все файлы (*.*)",
        )
        if file_path:
            self._selected_thumbnail = file_path
            self.thumbnail_label.setText(Path(file_path).name)

    def _start_upload(self) -> None:
        profile_name = self.profile_combo.currentText()
        if not profile_name:
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт.")
            return
        if not self._selected_video:
            QMessageBox.warning(self, "Ошибка", "Выберите видеофайл.")
            return
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите заголовок.")
            return

        if profile_name not in self.browser_manager.list_active_sessions():
            reply = QMessageBox.question(
                self, "Браузер не запущен",
                f"Браузер для '{profile_name}' не открыт. Открыть сейчас?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                profile = self.profile_manager.get_profile(profile_name)
                try:
                    self.browser_manager.create_browser(
                        profile_name=profile_name,
                        proxy=profile.get("proxy") or None,
                        user_agent=profile.get("user_agent"),
                        language=profile.get("language", "ru-RU"),
                    )
                except Exception as exc:
                    QMessageBox.critical(self, "Ошибка", str(exc))
                    return
            else:
                return

        privacy_map = {"Публичное": "public", "По ссылке": "unlisted", "Приватное": "private"}
        privacy = privacy_map.get(self.privacy_combo.currentText(), "public")
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]

        self._engine = PosterEngine(
            profile_name=profile_name,
            browser_manager=self.browser_manager,
            video_path=self._selected_video,
            title=self.title_edit.text().strip(),
            description=self.desc_edit.toPlainText(),
            tags=tags,
            thumbnail_path=self._selected_thumbnail,
            privacy=privacy,
        )
        self._engine.upload_progress.connect(self._on_progress)
        self._engine.upload_completed.connect(self._on_completed)
        self._engine.error_occurred.connect(self._on_error)

        self.upload_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self._engine.start()

    def _schedule_post(self) -> None:
        QMessageBox.information(self, "Планировщик", "Используйте вкладку «Планировщик» для настройки расписания.")

    def _refresh_queue(self) -> None:
        pass  # Will be connected to content plan

    def _clear_completed(self) -> None:
        rows_to_remove = []
        for row in range(self.queue_table.rowCount()):
            status_item = self.queue_table.item(row, 4)
            if status_item and status_item.text() in ("✅ Готово", "❌ Ошибка"):
                rows_to_remove.append(row)
        for row in reversed(rows_to_remove):
            self.queue_table.removeRow(row)

    def _clear_history(self) -> None:
        self.history_table.setRowCount(0)

    def _on_progress(self, description: str, percent: int) -> None:
        self.progress_bar.setValue(percent)
        self.status_label.setText(description)

    def _on_completed(self, title: str) -> None:
        self.progress_bar.setValue(100)
        self.status_label.setText(f"✅ Загружено: '{title}'")
        self.upload_btn.setEnabled(True)
        self._add_to_history(title, "✅ Успешно")
        QMessageBox.information(self, "Готово", f"Видео '{title}' успешно загружено!")

    def _on_error(self, error_msg: str) -> None:
        self.status_label.setText(f"❌ Ошибка: {error_msg}")
        self.upload_btn.setEnabled(True)
        title = self.title_edit.text().strip() or "—"
        self._add_to_history(title, f"❌ Ошибка: {error_msg[:50]}")

    def _add_to_history(self, title: str, status: str) -> None:
        self.tabs.setCurrentIndex(2)  # Switch to History tab
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        items = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            self.profile_combo.currentText(),
            Path(self._selected_video).name if self._selected_video else "—",
            title,
            status,
        ]
        for col, value in enumerate(items):
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.history_table.setItem(row, col, item)
