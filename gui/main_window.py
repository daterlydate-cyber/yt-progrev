"""
Main window of YT-Progrev with sidebar navigation.
"""
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QSizePolicy,
    QStackedWidget, QStatusBar, QTextEdit, QVBoxLayout, QWidget,
)

from core.browser_manager import BrowserManager
from core.content_plan import ContentPlan
from core.profile_manager import ProfileManager
from core.scheduler import TaskScheduler
from gui.accounts_widget import AccountsWidget
from gui.content_plan_widget import ContentPlanWidget
from gui.dashboard_widget import DashboardWidget
from gui.poster_widget import PosterWidget
from gui.proxy_widget import ProxyWidget
from gui.scheduler_widget import SchedulerWidget
from gui.settings_widget import SettingsWidget
from gui.warmup_widget import WarmupWidget
from utils.logger import QtLogHandler, get_logger
from utils.proxy_manager import ProxyManager

logger = get_logger(__name__)

APP_VERSION = "2.0.0"


class NavButton(QPushButton):
    """Sidebar navigation button."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = QFont("Segoe UI", 12)
        self.setFont(font)
        self.setCursor(Qt.PointingHandCursor)


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.browser_manager = BrowserManager()
        self.profile_manager = ProfileManager()
        self.scheduler = TaskScheduler()
        self.proxy_manager = ProxyManager()
        self.proxy_manager.load_saved_proxies()

        self.setWindowTitle("YT-Progrev — YouTube SMM Панель")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._setup_log_handler()

        # Start with dashboard
        self._nav_buttons[0].setChecked(True)
        self.content_stack.setCurrentIndex(0)

        logger.info("YT-Progrev запущен.")

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # === Sidebar ===
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(4)

        # App logo/title
        logo_label = QLabel("▶ YT-Progrev")
        logo_label.setObjectName("sidebarTitle")
        logo_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        sidebar_layout.addWidget(logo_label)

        version_label = QLabel(f"YouTube SMM Панель v{APP_VERSION}")
        version_label.setObjectName("sidebarVersion")
        sidebar_layout.addWidget(version_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #2a2a4a; margin: 8px 0;")
        sidebar_layout.addWidget(sep)

        # Navigation items
        nav_items = [
            ("📊  Дашборд", 0),
            ("👤  Аккаунты", 1),
            ("📝  Публикация", 2),
            ("📅  Планировщик", 3),
            ("🔥  Прогрев", 4),
            ("🌐  Прокси", 5),
            ("📋  Контент-план", 6),
            ("⚙️  Настройки", 7),
        ]

        self._nav_buttons = []
        for label, idx in nav_items:
            btn = NavButton(label)
            btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Logs toggle at bottom
        logs_btn = NavButton("📋  Логи")
        logs_btn.clicked.connect(lambda checked: self._navigate(8))
        sidebar_layout.addWidget(logs_btn)
        self._nav_buttons.append(logs_btn)

        root_layout.addWidget(sidebar)

        # === Content area ===
        content_area = QFrame()
        content_area.setObjectName("contentArea")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.content_stack = QStackedWidget()

        # 0 - Dashboard
        self.dashboard_widget = DashboardWidget(
            self.profile_manager, self.browser_manager, self.scheduler, parent=self
        )
        # Connect quick action buttons
        self.dashboard_widget.add_post_btn.clicked.connect(
            lambda: self._navigate(2)
        )
        self.dashboard_widget.new_account_btn.clicked.connect(
            lambda: self._navigate(1)
        )
        self.content_stack.addWidget(self.dashboard_widget)

        # 1 - Accounts
        self.accounts_widget = AccountsWidget(
            self.profile_manager, self.browser_manager, parent=self
        )
        self.content_stack.addWidget(self.accounts_widget)

        # 2 - Poster
        self.poster_widget = PosterWidget(
            self.profile_manager, self.browser_manager, parent=self
        )
        self.content_stack.addWidget(self.poster_widget)

        # 3 - Scheduler
        self.scheduler_widget = SchedulerWidget(
            self.scheduler, self.profile_manager, parent=self
        )
        self.content_stack.addWidget(self.scheduler_widget)

        # 4 - Warmup
        self.warmup_widget = WarmupWidget(
            self.profile_manager, self.browser_manager, parent=self
        )
        self.content_stack.addWidget(self.warmup_widget)

        # 5 - Proxy
        self.proxy_widget = ProxyWidget(self.proxy_manager, parent=self)
        self.content_stack.addWidget(self.proxy_widget)

        # 6 - Content Plan
        self.content_plan_widget = ContentPlanWidget(
            self.profile_manager, self.browser_manager, self.scheduler, parent=self
        )
        self.content_stack.addWidget(self.content_plan_widget)

        # 7 - Settings
        self.settings_widget = SettingsWidget(parent=self)
        self.content_stack.addWidget(self.settings_widget)

        # 8 - Logs
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setFont(QFont("Courier New", 9))
        self.log_widget.setObjectName("logTextEdit")
        self.content_stack.addWidget(self.log_widget)

        content_layout.addWidget(self.content_stack)
        root_layout.addWidget(content_area, stretch=1)

    def _navigate(self, index: int) -> None:
        """Switch to the given page index."""
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

        # Refresh relevant widgets when navigating to them
        if index == 0:
            self.dashboard_widget.refresh_stats()
        elif index == 1:
            self.accounts_widget.refresh()
        elif index == 2:
            self.poster_widget.refresh_profiles()
        elif index == 4:
            self.warmup_widget.refresh_profiles()

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")

        import_action = QAction("Импорт конфигурации...", self)
        import_action.triggered.connect(self._import_config)
        file_menu.addAction(import_action)

        export_action = QAction("Экспорт конфигурации...", self)
        export_action.triggered.connect(self._export_config)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        about_menu = menubar.addMenu("Справка")
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        about_menu.addAction(about_action)

    def _setup_statusbar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Готово")
        self.status_bar.addWidget(self.status_label)

        self.sessions_label = QLabel("Активных сессий: 0")
        self.status_bar.addPermanentWidget(self.sessions_label)

    def _setup_log_handler(self) -> None:
        self.qt_log_handler = QtLogHandler()
        self.qt_log_handler.signals.log_message.connect(self._append_log)
        logging.getLogger().addHandler(self.qt_log_handler)

    def _append_log(self, message: str, levelno: int) -> None:
        color_map = {
            logging.DEBUG: "#6c7086",
            logging.INFO: "#a0a0b0",
            logging.WARNING: "#ff9800",
            logging.ERROR: "#f44336",
            logging.CRITICAL: "#e94560",
        }
        color = color_map.get(levelno, "#a0a0b0")
        html = f'<span style="color:{color}">{message}</span>'
        self.log_widget.append(html)
        scrollbar = self.log_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_sessions_count(self) -> None:
        count = len(self.browser_manager.list_active_sessions())
        self.sessions_label.setText(f"Активных сессий: {count}")

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _import_config(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт конфигурации", "", "JSON файлы (*.json)"
        )
        if file_path:
            import shutil
            try:
                shutil.copy2(file_path, "config.json")
                QMessageBox.information(self, "Успех", "Конфигурация импортирована.")
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _export_config(self) -> None:
        import shutil
        from pathlib import Path

        if not Path("config.json").exists():
            QMessageBox.warning(self, "Нет конфигурации", "Файл config.json не найден.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт конфигурации", "config.json", "JSON файлы (*.json)"
        )
        if file_path:
            try:
                shutil.copy2("config.json", file_path)
                QMessageBox.information(self, "Успех", "Конфигурация экспортирована.")
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "О программе",
            f"<h2>YT-Progrev v{APP_VERSION}</h2>"
            "<p>YouTube SMM Панель — Автопостер с Прогревом Аккаунтов</p>"
            "<p>Работает без YouTube API через браузерную автоматизацию</p>"
            "<p><b>Стек:</b> Python 3.10+, PyQt5, Selenium, undetected-chromedriver</p>"
            "<hr>"
            "<p><i>Используйте ответственно. Соблюдайте ToS YouTube.</i></p>",
        )

    def closeEvent(self, event) -> None:
        active = self.browser_manager.list_active_sessions()
        if active:
            reply = QMessageBox.question(
                self,
                "Подтверждение выхода",
                f"Запущено {len(active)} браузерных сессий. Закрыть все и выйти?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.browser_manager.close_all()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
