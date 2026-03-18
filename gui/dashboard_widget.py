"""Dashboard widget for YT-Progrev."""
import logging
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QListWidget, QListWidgetItem, QGroupBox
)
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class StatCard(QFrame):
    """A stat card widget showing a metric."""
    def __init__(self, title: str, value: str = "0", icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumSize(160, 100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        top_row = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 20))
        top_row.addWidget(icon_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.value_label.setObjectName("statValue")
        layout.addWidget(self.value_label)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        layout.addWidget(title_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class DashboardWidget(QWidget):
    """Main dashboard widget."""

    def __init__(self, profile_manager, browser_manager, scheduler, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.browser_manager = browser_manager
        self.scheduler = scheduler
        self._setup_ui()

        # Refresh stats every 30 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_stats)
        self._timer.start(30000)
        self.refresh_stats()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("📊 Дашборд")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setObjectName("pageTitle")
        layout.addWidget(header)

        # Stats cards row
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        self.card_accounts = StatCard("Аккаунтов", "0", "👤")
        self.card_scheduled = StatCard("Запланировано", "0", "📅")
        self.card_published = StatCard("Опубликовано сегодня", "0", "✅")
        self.card_errors = StatCard("Ошибок", "0", "❌")

        cards_layout.addWidget(self.card_accounts, 0, 0)
        cards_layout.addWidget(self.card_scheduled, 0, 1)
        cards_layout.addWidget(self.card_published, 0, 2)
        cards_layout.addWidget(self.card_errors, 0, 3)
        layout.addLayout(cards_layout)

        # Bottom row: recent actions + quick actions
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        # Recent actions
        recent_group = QGroupBox("📋 Последние действия")
        recent_layout = QVBoxLayout(recent_group)
        self.recent_list = QListWidget()
        self.recent_list.setObjectName("recentList")
        recent_layout.addWidget(self.recent_list)
        bottom_row.addWidget(recent_group, stretch=2)

        # Quick actions
        actions_group = QGroupBox("⚡ Быстрые действия")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(10)

        self.add_post_btn = QPushButton("📤 Добавить пост")
        self.add_post_btn.setMinimumHeight(44)
        self.add_post_btn.setObjectName("accentButton")
        actions_layout.addWidget(self.add_post_btn)

        self.new_account_btn = QPushButton("👤 Новый аккаунт")
        self.new_account_btn.setMinimumHeight(44)
        actions_layout.addWidget(self.new_account_btn)

        self.open_browser_btn = QPushButton("🌐 Открыть браузер")
        self.open_browser_btn.setMinimumHeight(44)
        actions_layout.addWidget(self.open_browser_btn)

        actions_layout.addStretch()
        bottom_row.addWidget(actions_group, stretch=1)

        layout.addLayout(bottom_row)

    def refresh_stats(self):
        """Refresh dashboard statistics."""
        try:
            profiles = self.profile_manager.list_profiles()
            self.card_accounts.set_value(str(len(profiles)))
        except Exception:
            self.card_accounts.set_value("—")

        try:
            active = self.browser_manager.list_active_sessions()
            # Show active sessions info
        except Exception:
            pass

    def add_recent_action(self, action: str):
        """Add an action to the recent actions list."""
        item = QListWidgetItem(action)
        self.recent_list.insertItem(0, item)
        # Keep only last 50 items
        while self.recent_list.count() > 50:
            self.recent_list.takeItem(self.recent_list.count() - 1)
