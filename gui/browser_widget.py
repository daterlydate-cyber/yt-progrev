"""
Виджет управления активными браузерными сессиями.
"""

import logging
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.browser_manager import BrowserManager
from core.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class BrowserWidget(QWidget):
    """Виджет для просмотра и управления активными браузерными сессиями."""

    def __init__(
        self,
        browser_manager: BrowserManager,
        profile_manager: ProfileManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.browser_manager = browser_manager
        self.profile_manager = profile_manager
        self._setup_ui()

        # Таймер для обновления списка сессий каждые 3 секунды
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_sessions)
        self._refresh_timer.start(3000)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Список активных сессий ---
        sessions_group = QGroupBox("Активные браузерные сессии")
        sessions_layout = QVBoxLayout(sessions_group)

        self.session_list = QListWidget()
        self.session_list.currentItemChanged.connect(self._on_session_selected)
        sessions_layout.addWidget(self.session_list)

        btn_row = QHBoxLayout()
        self.open_btn = QPushButton("▶️ Открыть браузер для профиля")
        self.open_btn.clicked.connect(self._open_browser)
        btn_row.addWidget(self.open_btn)

        self.close_btn = QPushButton("⏹️ Закрыть выбранную сессию")
        self.close_btn.clicked.connect(self._close_session)
        btn_row.addWidget(self.close_btn)

        self.close_all_btn = QPushButton("🚫 Закрыть все")
        self.close_all_btn.clicked.connect(self._close_all)
        btn_row.addWidget(self.close_all_btn)

        sessions_layout.addLayout(btn_row)
        layout.addWidget(sessions_group)

        # --- Информация о выбранной сессии ---
        info_group = QGroupBox("Информация о сессии")
        info_layout = QVBoxLayout(info_group)

        self.session_info_label = QLabel("Выберите сессию для просмотра информации.")
        self.session_info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.session_info_label.setWordWrap(True)
        info_layout.addWidget(self.session_info_label)

        layout.addWidget(info_group)
        layout.addStretch()

    def _refresh_sessions(self) -> None:
        """Обновить список активных сессий."""
        active = self.browser_manager.list_active_sessions()
        current_items = [
            self.session_list.item(i).text()
            for i in range(self.session_list.count())
        ]

        # Удаляем закрытые сессии из списка
        for name in list(current_items):
            if name not in active:
                items = self.session_list.findItems(name, Qt.MatchExactly)
                for item in items:
                    self.session_list.takeItem(self.session_list.row(item))

        # Добавляем новые сессии
        for name in active:
            if name not in current_items:
                item = QListWidgetItem(f"🌐 {name}")
                item.setData(Qt.UserRole, name)
                self.session_list.addItem(item)

    def _on_session_selected(self, current: Optional[QListWidgetItem], _) -> None:
        """Показать информацию о выбранной сессии."""
        if current is None:
            self.session_info_label.setText("Выберите сессию для просмотра информации.")
            return

        profile_name = current.data(Qt.UserRole) or current.text().replace("🌐 ", "")
        driver = self.browser_manager.get_driver(profile_name)
        profile = self.profile_manager.get_profile(profile_name)

        info_lines = [f"<b>Профиль:</b> {profile_name}"]

        if driver:
            try:
                current_url = driver.current_url
                info_lines.append(f"<b>Текущий URL:</b> {current_url}")
            except Exception:
                info_lines.append("<b>Текущий URL:</b> недоступно")

        if profile:
            info_lines.append(f"<b>Прокси:</b> {profile.get('proxy') or '—'}")
            info_lines.append(f"<b>Язык:</b> {profile.get('language', '—')}")
            ua = profile.get("user_agent", "")
            info_lines.append(f"<b>User-Agent:</b> {ua[:80]}...")

        self.session_info_label.setText("<br>".join(info_lines))

    def _open_browser(self) -> None:
        """Открыть диалог выбора профиля и запустить браузер."""
        from PyQt5.QtWidgets import QInputDialog
        profiles = self.profile_manager.list_profiles()
        if not profiles:
            QMessageBox.warning(self, "Нет профилей", "Сначала создайте профиль.")
            return

        names = [p["name"] for p in profiles]
        name, ok = QInputDialog.getItem(
            self, "Выбор профиля", "Профиль:", names, 0, False
        )
        if ok and name:
            if name in self.browser_manager.list_active_sessions():
                QMessageBox.information(
                    self, "Уже открыт", f"Браузер '{name}' уже запущен."
                )
                return
            profile = self.profile_manager.get_profile(name)
            try:
                self.browser_manager.create_browser(
                    profile_name=name,
                    proxy=profile.get("proxy") or None,
                    user_agent=profile.get("user_agent"),
                    language=profile.get("language", "ru-RU"),
                )
                self._refresh_sessions()
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _close_session(self) -> None:
        """Закрыть выбранную сессию."""
        current = self.session_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Нет выбора", "Выберите сессию.")
            return

        profile_name = current.data(Qt.UserRole) or current.text().replace("🌐 ", "")
        self.browser_manager.close_browser(profile_name)
        self._refresh_sessions()
        self.session_info_label.setText("Сессия закрыта.")

    def _close_all(self) -> None:
        """Закрыть все активные сессии."""
        if not self.browser_manager.list_active_sessions():
            QMessageBox.information(self, "Нет сессий", "Нет активных сессий.")
            return

        reply = QMessageBox.question(
            self,
            "Закрыть все?",
            "Закрыть все активные браузерные сессии?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.browser_manager.close_all()
            self._refresh_sessions()
