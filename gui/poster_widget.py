"""
Виджет автопостинга видео на YouTube.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
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
    """Виджет загрузки и управления автопостингом видео."""

    # Колонки таблицы истории
    HISTORY_COLUMNS = ["Дата", "Профиль", "Файл", "Заголовок", "Статус"]

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
        main_layout = QVBoxLayout(self)

        # --- Настройки загрузки ---
        upload_group = QGroupBox("Загрузка видео")
        upload_layout = QVBoxLayout(upload_group)

        # Выбор профиля
        prof_row = QHBoxLayout()
        prof_row.addWidget(QLabel("Профиль (аккаунт):"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        prof_row.addWidget(self.profile_combo)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setMaximumWidth(36)
        self.refresh_btn.clicked.connect(self.refresh_profiles)
        prof_row.addWidget(self.refresh_btn)
        prof_row.addStretch()
        upload_layout.addLayout(prof_row)

        # Выбор видеофайла
        video_row = QHBoxLayout()
        video_row.addWidget(QLabel("Видеофайл:"))
        self.video_path_label = QLabel("Файл не выбран")
        self.video_path_label.setObjectName("fileLabel")
        video_row.addWidget(self.video_path_label, stretch=1)
        self.select_video_btn = QPushButton("📁 Выбрать видео")
        self.select_video_btn.clicked.connect(self._select_video)
        video_row.addWidget(self.select_video_btn)
        upload_layout.addLayout(video_row)

        # Заголовок
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Заголовок:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название вашего видео")
        title_row.addWidget(self.title_edit)
        upload_layout.addLayout(title_row)

        # Описание
        upload_layout.addWidget(QLabel("Описание:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("Описание видео...")
        upload_layout.addWidget(self.desc_edit)

        # Теги + превью
        extra_row = QHBoxLayout()
        extra_row.addWidget(QLabel("Теги:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("тег1, тег2, тег3")
        extra_row.addWidget(self.tags_edit)

        self.thumbnail_btn = QPushButton("🖼️ Превью")
        self.thumbnail_btn.clicked.connect(self._select_thumbnail)
        self.thumbnail_label = QLabel("—")
        extra_row.addWidget(self.thumbnail_btn)
        extra_row.addWidget(self.thumbnail_label)
        upload_layout.addLayout(extra_row)

        # Доступ к видео
        privacy_row = QHBoxLayout()
        privacy_row.addWidget(QLabel("Доступ:"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["Публичное", "По ссылке", "Приватное"])
        privacy_row.addWidget(self.privacy_combo)
        privacy_row.addStretch()
        upload_layout.addLayout(privacy_row)

        main_layout.addWidget(upload_group)

        # --- Кнопка загрузки и прогресс ---
        ctrl_group = QGroupBox("Статус загрузки")
        ctrl_layout = QVBoxLayout(ctrl_group)

        self.upload_btn = QPushButton("📤 Загрузить видео")
        self.upload_btn.setMinimumHeight(40)
        self.upload_btn.clicked.connect(self._start_upload)
        ctrl_layout.addWidget(self.upload_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        ctrl_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ожидание...")
        ctrl_layout.addWidget(self.status_label)

        main_layout.addWidget(ctrl_group)

        # --- История загрузок ---
        history_group = QGroupBox("История загрузок")
        history_layout = QVBoxLayout(history_group)

        self.history_table = QTableWidget(0, len(self.HISTORY_COLUMNS))
        self.history_table.setHorizontalHeaderLabels(self.HISTORY_COLUMNS)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        history_layout.addWidget(self.history_table)

        main_layout.addWidget(history_group)

    def refresh_profiles(self) -> None:
        """Обновить список профилей."""
        current = self.profile_combo.currentText()
        self.profile_combo.clear()
        for p in self.profile_manager.list_profiles():
            self.profile_combo.addItem(p["name"])
        idx = self.profile_combo.findText(current)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

    def _select_video(self) -> None:
        """Открыть диалог выбора видеофайла."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать видео",
            "data/videos",
            "Видеофайлы (*.mp4 *.mov *.avi *.mkv *.webm);;Все файлы (*.*)",
        )
        if file_path:
            self._selected_video = file_path
            name = Path(file_path).name
            self.video_path_label.setText(name)
            # Авто-заполняем заголовок если пуст
            if not self.title_edit.text():
                self.title_edit.setText(Path(file_path).stem)

    def _select_thumbnail(self) -> None:
        """Открыть диалог выбора превью."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать превью",
            "",
            "Изображения (*.jpg *.jpeg *.png *.webp);;Все файлы (*.*)",
        )
        if file_path:
            self._selected_thumbnail = file_path
            self.thumbnail_label.setText(Path(file_path).name)

    def _start_upload(self) -> None:
        """Начать загрузку видео."""
        profile_name = self.profile_combo.currentText()
        if not profile_name:
            QMessageBox.warning(self, "Ошибка", "Выберите профиль.")
            return

        if not self._selected_video:
            QMessageBox.warning(self, "Ошибка", "Выберите видеофайл.")
            return

        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите заголовок видео.")
            return

        # Проверяем что браузер открыт
        if profile_name not in self.browser_manager.list_active_sessions():
            reply = QMessageBox.question(
                self,
                "Браузер не запущен",
                f"Браузер для профиля '{profile_name}' не открыт. Открыть сейчас?",
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

        # Конвертируем доступ
        privacy_map = {
            "Публичное": "public",
            "По ссылке": "unlisted",
            "Приватное": "private",
        }
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
        logger.info("Загрузка видео запущена: '%s', профиль '%s'.",
                    self._selected_video, profile_name)

    def _on_progress(self, description: str, percent: int) -> None:
        """Обновить прогресс загрузки."""
        self.progress_bar.setValue(percent)
        self.status_label.setText(description)

    def _on_completed(self, title: str) -> None:
        """Обработать завершение загрузки."""
        self.progress_bar.setValue(100)
        self.status_label.setText(f"✅ Загружено: '{title}'")
        self.upload_btn.setEnabled(True)
        self._add_to_history(title, "✅ Успешно")
        QMessageBox.information(self, "Готово", f"Видео '{title}' успешно загружено!")

    def _on_error(self, error_msg: str) -> None:
        """Обработать ошибку загрузки."""
        self.status_label.setText(f"❌ Ошибка: {error_msg}")
        self.upload_btn.setEnabled(True)
        title = self.title_edit.text().strip() or "—"
        self._add_to_history(title, f"❌ Ошибка: {error_msg[:50]}")

    def _add_to_history(self, title: str, status: str) -> None:
        """Добавить запись в таблицу истории."""
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
