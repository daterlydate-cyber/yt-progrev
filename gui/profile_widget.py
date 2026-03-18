"""
Виджет управления профилями.
"""

import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.browser_manager import BrowserManager
from core.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class CreateProfileDialog(QDialog):
    """Диалог создания нового профиля."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создать профиль")
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("account_01")
        layout.addRow("Имя профиля *:", self.name_edit)

        self.proxy_edit = QLineEdit()
        self.proxy_edit.setPlaceholderText("http://user:pass@host:port (опционально)")
        layout.addRow("Прокси:", self.proxy_edit)

        self.ua_combo = QComboBox()
        self.ua_combo.addItems(["Авто (случайный)", "Ввести вручную"])
        layout.addRow("User-Agent:", self.ua_combo)

        self.ua_edit = QLineEdit()
        self.ua_edit.setPlaceholderText("Mozilla/5.0 ...")
        self.ua_edit.setVisible(False)
        self.ua_combo.currentIndexChanged.connect(
            lambda i: self.ua_edit.setVisible(i == 1)
        )
        layout.addRow("", self.ua_edit)

        self.lang_edit = QLineEdit("ru-RU")
        layout.addRow("Язык:", self.lang_edit)

        self.tz_edit = QLineEdit("Europe/Moscow")
        layout.addRow("Часовой пояс:", self.tz_edit)

        self.resolution_combo = QComboBox()
        resolutions = ["1920x1080", "1366x768", "1440x900", "1280x720", "1536x864"]
        self.resolution_combo.addItems(resolutions)
        layout.addRow("Разрешение экрана:", self.resolution_combo)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Заметки (опционально)")
        layout.addRow("Заметки:", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _validate_and_accept(self) -> None:
        """Проверить данные и принять диалог."""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите имя профиля.")
            return
        self.accept()

    def get_data(self) -> dict:
        """Получить данные из формы."""
        user_agent = None
        if self.ua_combo.currentIndex() == 1:
            user_agent = self.ua_edit.text().strip() or None
        return {
            "name": self.name_edit.text().strip(),
            "proxy": self.proxy_edit.text().strip() or None,
            "user_agent": user_agent,
            "language": self.lang_edit.text().strip() or "ru-RU",
            "timezone": self.tz_edit.text().strip() or "Europe/Moscow",
            "screen_resolution": self.resolution_combo.currentText(),
            "notes": self.notes_edit.text().strip(),
        }


class ProfileWidget(QWidget):
    """Виджет управления профилями браузеров."""

    # Колонки таблицы
    COLUMNS = ["Имя", "Статус", "Прогресс прогрева", "Прокси", "User-Agent", "Дата создания"]

    def __init__(
        self,
        profile_manager: ProfileManager,
        browser_manager: BrowserManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.browser_manager = browser_manager
        self._setup_ui()
        self.refresh_profiles()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Панель кнопок
        btn_bar = QHBoxLayout()

        self.create_btn = QPushButton("➕ Создать профиль")
        self.create_btn.clicked.connect(self._create_profile)

        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self._delete_profile)

        self.open_browser_btn = QPushButton("🌐 Открыть браузер")
        self.open_browser_btn.clicked.connect(self._open_browser)

        self.export_btn = QPushButton("📦 Экспорт")
        self.export_btn.clicked.connect(self._export_profile)

        self.import_btn = QPushButton("📂 Импорт")
        self.import_btn.clicked.connect(self._import_profile)

        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self.refresh_profiles)

        for btn in [
            self.create_btn,
            self.delete_btn,
            self.open_browser_btn,
            self.export_btn,
            self.import_btn,
            self.refresh_btn,
        ]:
            btn_bar.addWidget(btn)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # Таблица профилей
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def refresh_profiles(self) -> None:
        """Обновить список профилей в таблице."""
        profiles = self.profile_manager.list_profiles()
        self.table.setRowCount(0)

        for profile in profiles:
            row = self.table.rowCount()
            self.table.insertRow(row)

            warmup = profile.get("warmup_progress", {})
            total_actions = warmup.get("total_actions", 0)
            total_sessions = warmup.get("total_sessions", 0)
            progress_str = f"{total_sessions} сессий / {total_actions} действий"

            ua = profile.get("user_agent", "")
            ua_short = ua[:50] + "..." if len(ua) > 50 else ua

            items = [
                profile.get("name", ""),
                profile.get("status", ""),
                progress_str,
                profile.get("proxy", "") or "—",
                ua_short,
                profile.get("created_at", "")[:10],
            ]

            for col, value in enumerate(items):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row, col, item)

    def _get_selected_profile_name(self) -> Optional[str]:
        """Получить имя выбранного профиля."""
        rows = self.table.selectedItems()
        if not rows:
            QMessageBox.warning(self, "Не выбран профиль", "Выберите профиль из таблицы.")
            return None
        return self.table.item(self.table.currentRow(), 0).text()

    def _create_profile(self) -> None:
        """Открыть диалог создания нового профиля."""
        dialog = CreateProfileDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                self.profile_manager.create_profile(**data)
                self.refresh_profiles()
                QMessageBox.information(
                    self, "Готово", f"Профиль '{data['name']}' создан."
                )
                logger.info("Профиль '%s' создан через GUI.", data["name"])
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _delete_profile(self) -> None:
        """Удалить выбранный профиль."""
        name = self._get_selected_profile_name()
        if not name:
            return

        reply = QMessageBox.question(
            self,
            "Удаление профиля",
            f"Удалить профиль '{name}' и все его данные?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                # Закрываем браузер если открыт
                if name in self.browser_manager.list_active_sessions():
                    self.browser_manager.close_browser(name)
                self.profile_manager.delete_profile(name)
                self.refresh_profiles()
                logger.info("Профиль '%s' удалён через GUI.", name)
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _open_browser(self) -> None:
        """Открыть браузер для выбранного профиля."""
        name = self._get_selected_profile_name()
        if not name:
            return

        profile = self.profile_manager.get_profile(name)
        if not profile:
            QMessageBox.warning(self, "Ошибка", "Профиль не найден.")
            return

        try:
            self.browser_manager.create_browser(
                profile_name=name,
                proxy=profile.get("proxy") or None,
                user_agent=profile.get("user_agent"),
                language=profile.get("language", "ru-RU"),
            )
            QMessageBox.information(self, "Готово", f"Браузер для '{name}' запущен.")
            # Обновляем счётчик в главном окне
            if hasattr(self.parent(), "update_sessions_count"):
                self.parent().update_sessions_count()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))

    def _export_profile(self) -> None:
        """Экспортировать выбранный профиль в ZIP."""
        name = self._get_selected_profile_name()
        if not name:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт профиля", f"{name}_export.zip", "ZIP архивы (*.zip)"
        )
        if file_path:
            try:
                self.profile_manager.export_profile(name, file_path)
                QMessageBox.information(
                    self, "Готово", f"Профиль '{name}' экспортирован."
                )
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _import_profile(self) -> None:
        """Импортировать профиль из ZIP-архива."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт профиля", "", "ZIP архивы (*.zip)"
        )
        if file_path:
            try:
                name = self.profile_manager.import_profile(file_path)
                self.refresh_profiles()
                QMessageBox.information(
                    self, "Готово", f"Профиль '{name}' импортирован."
                )
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))
