"""
Главное окно приложения YT-Progrev.
"""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.browser_manager import BrowserManager
from core.profile_manager import ProfileManager
from core.scheduler import TaskScheduler
from gui.browser_widget import BrowserWidget
from gui.poster_widget import PosterWidget
from gui.profile_widget import ProfileWidget
from gui.proxy_widget import ProxyWidget
from gui.scheduler_widget import SchedulerWidget
from gui.warmup_widget import WarmupWidget
from utils.logger import QtLogHandler, get_logger
from utils.proxy_manager import ProxyManager

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Главное окно приложения с вкладками."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Общие объекты, которые передаются в виджеты
        self.browser_manager = BrowserManager()
        self.profile_manager = ProfileManager()
        self.scheduler = TaskScheduler()
        self.proxy_manager = ProxyManager()
        self.proxy_manager.load_saved_proxies()

        self.setWindowTitle("YT-Progrev — YouTube Автопостер с Прогревом")
        self.setMinimumSize(1100, 700)
        self.resize(1200, 800)

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._setup_log_handler()

        logger.info("Приложение YT-Progrev запущено.")

    def _setup_ui(self) -> None:
        """Инициализировать главный интерфейс с вкладками."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)

        # Виджеты вкладок
        self.profile_widget = ProfileWidget(
            self.profile_manager, self.browser_manager, parent=self
        )
        self.warmup_widget = WarmupWidget(
            self.profile_manager, self.browser_manager, parent=self
        )
        self.poster_widget = PosterWidget(
            self.profile_manager, self.browser_manager, parent=self
        )
        self.browser_widget = BrowserWidget(
            self.browser_manager, self.profile_manager, parent=self
        )
        self.proxy_widget = ProxyWidget(self.proxy_manager, parent=self)
        self.scheduler_widget = SchedulerWidget(
            self.scheduler, self.profile_manager, parent=self
        )

        # Вкладка «Логи»
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setFont(QFont("Courier New", 9))
        self.log_widget.setObjectName("logTextEdit")

        self.tabs.addTab(self.profile_widget, "👤 Профили")
        self.tabs.addTab(self.warmup_widget, "🔥 Прогрев")
        self.tabs.addTab(self.poster_widget, "📤 Автопостинг")
        self.tabs.addTab(self.browser_widget, "🌐 Браузер")
        self.tabs.addTab(self.proxy_widget, "🔗 Прокси")
        self.tabs.addTab(self.scheduler_widget, "📅 Планировщик")
        self.tabs.addTab(self.log_widget, "📋 Логи")

        layout.addWidget(self.tabs)

    def _setup_menu(self) -> None:
        """Создать главное меню."""
        menubar = self.menuBar()

        # Меню «Файл»
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

        # Меню «О программе»
        about_menu = menubar.addMenu("Справка")
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        about_menu.addAction(about_action)

    def _setup_statusbar(self) -> None:
        """Создать строку состояния."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Готово")
        self.status_bar.addWidget(self.status_label)

        self.sessions_label = QLabel("Активных сессий: 0")
        self.status_bar.addPermanentWidget(self.sessions_label)

    def _setup_log_handler(self) -> None:
        """Подключить Qt-хендлер логирования к текстовому виджету."""
        self.qt_log_handler = QtLogHandler()
        self.qt_log_handler.signals.log_message.connect(self._append_log)
        logging.getLogger().addHandler(self.qt_log_handler)

    def _append_log(self, message: str, levelno: int) -> None:
        """Добавить сообщение в лог-виджет с цветовой разметкой."""
        color_map = {
            logging.DEBUG: "#6c7086",
            logging.INFO: "#cdd6f4",
            logging.WARNING: "#f9e2af",
            logging.ERROR: "#f38ba8",
            logging.CRITICAL: "#eb4034",
        }
        color = color_map.get(levelno, "#cdd6f4")
        html = f'<span style="color:{color}">{message}</span>'
        self.log_widget.append(html)
        # Прокручиваем вниз
        scrollbar = self.log_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_sessions_count(self) -> None:
        """Обновить счётчик активных браузерных сессий в статусбаре."""
        count = len(self.browser_manager.list_active_sessions())
        self.sessions_label.setText(f"Активных сессий: {count}")

    def set_status(self, message: str) -> None:
        """Обновить текст строки состояния."""
        self.status_label.setText(message)

    def _import_config(self) -> None:
        """Диалог импорта конфигурации."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт конфигурации", "", "JSON файлы (*.json)"
        )
        if file_path:
            import json
            import shutil
            try:
                shutil.copy2(file_path, "config.json")
                QMessageBox.information(
                    self, "Успех", "Конфигурация импортирована."
                )
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _export_config(self) -> None:
        """Диалог экспорта конфигурации."""
        import shutil
        from pathlib import Path

        if not Path("config.json").exists():
            QMessageBox.warning(
                self, "Нет конфигурации", "Файл config.json не найден."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт конфигурации", "config.json", "JSON файлы (*.json)"
        )
        if file_path:
            try:
                shutil.copy2("config.json", file_path)
                QMessageBox.information(
                    self, "Успех", "Конфигурация экспортирована."
                )
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _show_about(self) -> None:
        """Показать диалог «О программе»."""
        QMessageBox.about(
            self,
            "О программе",
            "<h2>YT-Progrev v1.0.0</h2>"
            "<p>YouTube Автопостер с Прогревом Аккаунтов</p>"
            "<p>Работает без YouTube API через браузерную автоматизацию "
            "(undetected-chromedriver + Selenium)</p>"
            "<p><b>Стек:</b> Python 3.10+, PyQt5, Selenium, undetected-chromedriver</p>"
            "<hr>"
            "<p><i>Используйте ответственно. Соблюдайте ToS YouTube.</i></p>",
        )

    def closeEvent(self, event) -> None:
        """Закрыть все браузеры при выходе из приложения."""
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
