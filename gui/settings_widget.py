"""Settings widget for YT-Progrev."""
import json
import logging
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QSpinBox, QGroupBox, QFormLayout,
    QMessageBox, QFileDialog, QComboBox, QTabWidget
)

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path("data/settings.json")


class SettingsWidget(QWidget):
    """App settings widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = {}
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        title = QLabel("⚙️ Настройки")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "Общие")
        tabs.addTab(self._create_browser_tab(), "Браузер")
        tabs.addTab(self._create_notifications_tab(), "Уведомления")
        layout.addWidget(tabs)

        # Save button
        save_btn = QPushButton("💾 Сохранить настройки")
        save_btn.setObjectName("accentButton")
        save_btn.setMinimumHeight(44)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

    def _create_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Общие настройки")
        form = QFormLayout(group)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Русский (RU)")
        form.addRow("Язык интерфейса:", self.lang_combo)

        self.data_dir_edit = QLineEdit("data")
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._browse_data_dir)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.data_dir_edit)
        dir_row.addWidget(browse_btn)
        dir_widget = QWidget()
        dir_widget.setLayout(dir_row)
        form.addRow("Папка данных:", dir_widget)

        self.autostart_check = QCheckBox("Автозапуск с Windows")
        form.addRow("", self.autostart_check)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _create_browser_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Настройки браузера")
        form = QFormLayout(group)

        self.chromedriver_edit = QLineEdit()
        self.chromedriver_edit.setPlaceholderText("Путь к ChromeDriver (авто если пусто)")
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._browse_chromedriver)
        cd_row = QHBoxLayout()
        cd_row.addWidget(self.chromedriver_edit)
        cd_row.addWidget(browse_btn)
        cd_widget = QWidget()
        cd_widget.setLayout(cd_row)
        form.addRow("ChromeDriver:", cd_widget)

        self.headless_check = QCheckBox("Headless режим (без окна браузера)")
        form.addRow("", self.headless_check)

        self.page_timeout_spin = QSpinBox()
        self.page_timeout_spin.setRange(10, 120)
        self.page_timeout_spin.setValue(30)
        self.page_timeout_spin.setSuffix(" сек")
        form.addRow("Таймаут страницы:", self.page_timeout_spin)

        self.upload_timeout_spin = QSpinBox()
        self.upload_timeout_spin.setRange(60, 7200)
        self.upload_timeout_spin.setValue(3600)
        self.upload_timeout_spin.setSuffix(" сек")
        form.addRow("Таймаут загрузки видео:", self.upload_timeout_spin)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _create_notifications_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Уведомления")
        form = QFormLayout(group)

        self.notify_errors_check = QCheckBox("Уведомлять об ошибках")
        self.notify_errors_check.setChecked(True)
        form.addRow("", self.notify_errors_check)

        self.notify_success_check = QCheckBox("Уведомлять об успешной публикации")
        self.notify_success_check.setChecked(True)
        form.addRow("", self.notify_success_check)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _browse_data_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Выбрать папку данных")
        if folder:
            self.data_dir_edit.setText(folder)

    def _browse_chromedriver(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать ChromeDriver", "", "Исполняемые файлы (*.exe);;Все файлы (*)"
        )
        if path:
            self.chromedriver_edit.setText(path)

    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
                self._apply_settings()
        except Exception as e:
            logger.error("Error loading settings: %s", e)

    def _apply_settings(self):
        s = self._settings
        self.data_dir_edit.setText(s.get("data_dir", "data"))
        self.autostart_check.setChecked(s.get("autostart", False))
        self.chromedriver_edit.setText(s.get("chromedriver_path", ""))
        self.headless_check.setChecked(s.get("headless", False))
        self.page_timeout_spin.setValue(s.get("page_timeout", 30))
        self.upload_timeout_spin.setValue(s.get("upload_timeout", 3600))
        self.notify_errors_check.setChecked(s.get("notify_errors", True))
        self.notify_success_check.setChecked(s.get("notify_success", True))

    def _save_settings(self):
        self._settings = {
            "data_dir": self.data_dir_edit.text(),
            "autostart": self.autostart_check.isChecked(),
            "chromedriver_path": self.chromedriver_edit.text(),
            "headless": self.headless_check.isChecked(),
            "page_timeout": self.page_timeout_spin.value(),
            "upload_timeout": self.upload_timeout_spin.value(),
            "notify_errors": self.notify_errors_check.isChecked(),
            "notify_success": self.notify_success_check.isChecked(),
        }
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Настройки", "Настройки сохранены.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
