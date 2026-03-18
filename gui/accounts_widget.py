"""Accounts widget for YT-Progrev."""
import json
import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QComboBox, QGroupBox,
    QFileDialog, QFrame
)

from core.browser_manager import BrowserManager
from core.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class AddAccountDialog(QDialog):
    """Dialog for adding a new account."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить аккаунт")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Уникальное имя аккаунта")
        form.addRow("Имя аккаунта:", self.name_edit)

        self.proxy_edit = QLineEdit()
        self.proxy_edit.setPlaceholderText("host:port или user:pass@host:port")
        form.addRow("Прокси:", self.proxy_edit)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Заметки...")
        form.addRow("Заметки:", self.notes_edit)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("✅ Добавить")
        ok_btn.setObjectName("accentButton")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "proxy": self.proxy_edit.text().strip(),
            "notes": self.notes_edit.text().strip(),
        }


class AccountsWidget(QWidget):
    """Widget for managing YouTube accounts/profiles."""

    account_selected = pyqtSignal(str)  # profile_name

    COLUMNS = ["Аккаунт", "Прокси", "Статус", "Заметки"]

    def __init__(self, profile_manager: ProfileManager, browser_manager: BrowserManager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.browser_manager = browser_manager
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("👤 Аккаунты")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setObjectName("pageTitle")
        header_row.addWidget(title)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Toolbar
        toolbar = QHBoxLayout()

        self.add_btn = QPushButton("➕ Добавить")
        self.add_btn.setObjectName("accentButton")
        self.add_btn.clicked.connect(self._add_account)
        toolbar.addWidget(self.add_btn)

        self.import_btn = QPushButton("📂 Импорт из файла")
        self.import_btn.clicked.connect(self._import_accounts)
        toolbar.addWidget(self.import_btn)

        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self._delete_account)
        toolbar.addWidget(self.delete_btn)

        self.open_browser_btn = QPushButton("🌐 Открыть браузер")
        self.open_browser_btn.clicked.connect(self._open_browser)
        toolbar.addWidget(self.open_browser_btn)

        self.check_auth_btn = QPushButton("🔍 Проверить авторизацию")
        self.check_auth_btn.clicked.connect(self._check_auth)
        toolbar.addWidget(self.check_auth_btn)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setMaximumWidth(40)
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Accounts table
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setObjectName("accountsTable")
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

    def refresh(self):
        """Refresh accounts list."""
        self.table.setRowCount(0)
        profiles = self.profile_manager.list_profiles()
        active_sessions = self.browser_manager.list_active_sessions()

        for p in profiles:
            row = self.table.rowCount()
            self.table.insertRow(row)

            name = p.get("name", "—")
            proxy = p.get("proxy") or "—"
            status = "🟢 Онлайн" if name in active_sessions else "⚫ Офлайн"
            notes = p.get("notes", "")

            for col, val in enumerate([name, proxy, status, notes]):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row, col, item)

    def _add_account(self):
        """Open dialog to add new account."""
        dlg = AddAccountDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Ошибка", "Введите имя аккаунта.")
                return
            try:
                self.profile_manager.create_profile(
                    name=data["name"],
                    proxy=data["proxy"] or None,
                    notes=data["notes"],
                )
                self.refresh()
                logger.info("Account created: %s", data["name"])
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def _delete_account(self):
        """Delete selected account."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Нет выбора", "Выберите аккаунт для удаления.")
            return
        name = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить аккаунт '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.profile_manager.delete_profile(name)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def _open_browser(self):
        """Open browser for selected account."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Нет выбора", "Выберите аккаунт.")
            return
        name = self.table.item(row, 0).text()
        profile = self.profile_manager.get_profile(name)
        if not profile:
            return
        try:
            self.browser_manager.create_browser(
                profile_name=name,
                proxy=profile.get("proxy") or None,
                user_agent=profile.get("user_agent"),
                language=profile.get("language", "ru-RU"),
            )
            self.refresh()
            QMessageBox.information(self, "Успех", f"Браузер для '{name}' открыт.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _check_auth(self):
        """Check authorization status for selected account."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Нет выбора", "Выберите аккаунт.")
            return
        name = self.table.item(row, 0).text()
        active = self.browser_manager.list_active_sessions()
        if name in active:
            QMessageBox.information(self, "Статус", f"Аккаунт '{name}': браузер активен.")
        else:
            QMessageBox.information(self, "Статус", f"Аккаунт '{name}': браузер не запущен.")

    def _import_accounts(self):
        """Import accounts from JSON/TXT file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт аккаунтов", "", "JSON файлы (*.json);;Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if not file_path:
            return
        try:
            path = Path(file_path)
            if path.suffix.lower() == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("name"):
                            try:
                                self.profile_manager.create_profile(
                                    name=item["name"],
                                    proxy=item.get("proxy"),
                                    notes=item.get("notes", ""),
                                )
                            except Exception:
                                pass
            else:
                # TXT: one account name per line
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        name = line.strip()
                        if name:
                            try:
                                self.profile_manager.create_profile(name=name)
                            except Exception:
                                pass
            self.refresh()
            QMessageBox.information(self, "Успех", "Аккаунты импортированы.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def _on_double_click(self, index):
        """Emit signal when account is double-clicked."""
        row = index.row()
        name = self.table.item(row, 0).text()
        self.account_selected.emit(name)
