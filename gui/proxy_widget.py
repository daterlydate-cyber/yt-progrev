"""
Виджет управления прокси-серверами.
Предоставляет таблицу сохранённых прокси, импорт, проверку и удаление.
"""

import logging
from typing import List, Optional

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

# Индексы колонок таблицы
COL_PROTOCOL = 0
COL_HOST_PORT = 1
COL_USERNAME = 2
COL_STATUS = 3
COL_PING = 4
COL_COUNTRY = 5
COL_ADDED = 6


class _ProxyCheckWorker(QObject):
    """Рабочий объект для проверки прокси в фоновом потоке."""

    progress = pyqtSignal(int)          # прогресс (0..100)
    proxy_checked = pyqtSignal(str, dict)  # (proxy_str, result_dict)
    finished = pyqtSignal()

    def __init__(
        self,
        proxy_manager: ProxyManager,
        proxies: List[str],
    ) -> None:
        super().__init__()
        self._proxy_manager = proxy_manager
        self._proxies = proxies
        self._cancelled = False

    def cancel(self) -> None:
        """Отменить проверку."""
        self._cancelled = True

    def run(self) -> None:
        """Запустить проверку прокси."""
        total = len(self._proxies)
        for idx, proxy in enumerate(self._proxies):
            if self._cancelled:
                break
            result = self._proxy_manager.check_proxy_detailed(proxy, timeout=5)
            self.proxy_checked.emit(proxy, result)
            if total > 0:
                self.progress.emit(int((idx + 1) / total * 100))
        self.finished.emit()


class ProxyWidget(QWidget):
    """Виджет вкладки управления прокси."""

    def __init__(self, proxy_manager: ProxyManager, parent=None) -> None:
        super().__init__(parent)
        self._proxy_manager = proxy_manager
        self._check_thread: Optional[QThread] = None
        self._check_worker: Optional[_ProxyCheckWorker] = None
        self._setup_ui()
        self._refresh_table()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Создать интерфейс вкладки."""
        layout = QVBoxLayout(self)

        # --- Заголовок ---
        title = QLabel("🔗 Управление прокси")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # --- Таблица прокси ---
        table_group = QGroupBox("Сохранённые прокси")
        table_layout = QVBoxLayout(table_group)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            "Протокол", "Хост:Порт", "Логин",
            "Статус", "Пинг (мс)", "Страна", "Добавлен",
        ])
        self._table.horizontalHeader().setSectionResizeMode(COL_HOST_PORT, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(COL_ADDED, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        table_layout.addWidget(self._table)

        layout.addWidget(table_group)

        # --- Кнопки управления ---
        btn_group = QGroupBox("Действия")
        btn_layout = QHBoxLayout(btn_group)

        self._add_btn = QPushButton("➕ Добавить")
        self._add_btn.setToolTip("Добавить прокси вручную")
        self._add_btn.clicked.connect(self._add_proxy)
        btn_layout.addWidget(self._add_btn)

        self._import_btn = QPushButton("📂 Импорт из файла")
        self._import_btn.setToolTip("Загрузить прокси из .txt файла")
        self._import_btn.clicked.connect(self._import_from_file)
        btn_layout.addWidget(self._import_btn)

        self._check_all_btn = QPushButton("🔍 Проверить все")
        self._check_all_btn.setToolTip("Проверить все прокси в фоне")
        self._check_all_btn.clicked.connect(self._check_all)
        btn_layout.addWidget(self._check_all_btn)

        self._check_one_btn = QPushButton("✅ Проверить выбранный")
        self._check_one_btn.setToolTip("Проверить выбранный прокси")
        self._check_one_btn.clicked.connect(self._check_selected)
        btn_layout.addWidget(self._check_one_btn)

        self._copy_btn = QPushButton("📋 Копировать")
        self._copy_btn.setToolTip("Скопировать прокси в буфер обмена")
        self._copy_btn.clicked.connect(self._copy_selected)
        btn_layout.addWidget(self._copy_btn)

        self._remove_btn = QPushButton("🗑️ Удалить")
        self._remove_btn.setToolTip("Удалить выбранный прокси")
        self._remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self._remove_btn)

        self._remove_dead_btn = QPushButton("❌ Удалить нерабочие")
        self._remove_dead_btn.setToolTip("Удалить все прокси со статусом ❌")
        self._remove_dead_btn.clicked.connect(self._remove_dead)
        btn_layout.addWidget(self._remove_dead_btn)

        layout.addWidget(btn_group)

        # --- Прогресс-бар ---
        progress_group = QGroupBox("Прогресс проверки")
        progress_layout = QVBoxLayout(progress_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        progress_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("Готово")
        progress_layout.addWidget(self._status_label)

        self._cancel_btn = QPushButton("⏹️ Остановить проверку")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_check)
        progress_layout.addWidget(self._cancel_btn)

        layout.addWidget(progress_group)

    # ------------------------------------------------------------------
    # Обновление таблицы
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        """Перерисовать таблицу прокси из ProxyManager."""
        proxies = self._proxy_manager.get_all_proxies()
        self._table.setRowCount(len(proxies))

        for row, proxy in enumerate(proxies):
            info = self._proxy_manager.get_proxy_info(proxy)

            status_text, status_color = self._status_display(info.get("status", "unknown"))
            ping_val = info.get("ping", -1)
            ping_text = f"{ping_val} мс" if ping_val >= 0 else "—"

            cells = [
                (info.get("protocol", "http"), None),
                (f"{info.get('host', '')}:{info.get('port', '')}", None),
                (info.get("username", "") or "—", None),
                (status_text, status_color),
                (ping_text, None),
                (info.get("country", "") or "—", None),
                (info.get("added_at", "") or "—", None),
            ]

            for col, (text, color) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setData(Qt.UserRole, proxy)
                if color:
                    item.setForeground(Qt.green if color == "green" else Qt.red)
                self._table.setItem(row, col, item)

        self._status_label.setText(f"Всего прокси: {len(proxies)}")

    @staticmethod
    def _status_display(status: str):
        """Вернуть (текст, цвет) для статуса прокси."""
        if status == "alive":
            return "✅ Работает", "green"
        if status == "dead":
            return "❌ Недоступен", "red"
        if status == "checking":
            return "⏳ Проверка...", None
        return "❓ Не проверен", None

    def _selected_proxy(self) -> Optional[str]:
        """Получить строку выбранного прокси или None."""
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    # ------------------------------------------------------------------
    # Обработчики кнопок
    # ------------------------------------------------------------------

    def _add_proxy(self) -> None:
        """Диалог добавления нового прокси."""
        text, ok = QInputDialog.getText(
            self,
            "Добавить прокси",
            "Введите прокси (форматы: protocol://user:pass@host:port, host:port:user:pass, host:port):",
        )
        if ok and text.strip():
            proxy_str = text.strip()
            if proxy_str in self._proxy_manager.get_all_proxies():
                QMessageBox.information(self, "Дубликат", "Этот прокси уже есть в списке.")
                return
            self._proxy_manager.add_proxy(proxy_str)
            self._refresh_table()
            logger.info("Прокси добавлен: %s", proxy_str)

    def _import_from_file(self) -> None:
        """Импортировать прокси из .txt файла."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт прокси",
            "",
            "Текстовые файлы (*.txt);;Все файлы (*)",
        )
        if not file_path:
            return
        count = self._proxy_manager.load_from_file(file_path)
        self._refresh_table()
        QMessageBox.information(
            self,
            "Импорт завершён",
            f"Загружено {count} прокси из файла.",
        )

    def _remove_selected(self) -> None:
        """Удалить выбранный прокси."""
        proxy = self._selected_proxy()
        if not proxy:
            QMessageBox.warning(self, "Нет выбора", "Выберите прокси для удаления.")
            return
        reply = QMessageBox.question(
            self,
            "Удалить прокси",
            f"Удалить прокси:\n{proxy}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._proxy_manager.remove_proxy(proxy)
            self._refresh_table()

    def _remove_dead(self) -> None:
        """Удалить все нерабочие прокси."""
        count = self._proxy_manager.remove_dead_proxies()
        self._refresh_table()
        QMessageBox.information(
            self,
            "Удалено",
            f"Удалено {count} нерабочих прокси.",
        )

    def _copy_selected(self) -> None:
        """Скопировать выбранный прокси в буфер обмена."""
        proxy = self._selected_proxy()
        if not proxy:
            QMessageBox.warning(self, "Нет выбора", "Выберите прокси для копирования.")
            return
        clipboard: QClipboard = QApplication.clipboard()
        clipboard.setText(proxy)
        self._status_label.setText(f"Скопировано: {proxy}")

    def _check_selected(self) -> None:
        """Проверить выбранный прокси."""
        proxy = self._selected_proxy()
        if not proxy:
            QMessageBox.warning(self, "Нет выбора", "Выберите прокси для проверки.")
            return
        self._start_check([proxy])

    def _check_all(self) -> None:
        """Запустить проверку всех прокси в фоновом потоке."""
        proxies = self._proxy_manager.get_all_proxies()
        if not proxies:
            QMessageBox.information(self, "Список пуст", "Нет прокси для проверки.")
            return
        self._start_check(proxies)

    def _cancel_check(self) -> None:
        """Отменить текущую проверку."""
        if self._check_worker:
            self._check_worker.cancel()

    # ------------------------------------------------------------------
    # Фоновая проверка через QThread
    # ------------------------------------------------------------------

    def _start_check(self, proxies: List[str]) -> None:
        """Запустить фоновую проверку списка прокси."""
        if self._check_thread and self._check_thread.isRunning():
            QMessageBox.information(
                self, "Идёт проверка", "Дождитесь завершения текущей проверки."
            )
            return

        self._check_thread = QThread(self)
        self._check_worker = _ProxyCheckWorker(self._proxy_manager, proxies)
        self._check_worker.moveToThread(self._check_thread)

        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.progress.connect(self._on_progress)
        self._check_worker.proxy_checked.connect(self._on_proxy_checked)
        self._check_worker.finished.connect(self._on_check_finished)
        self._check_worker.finished.connect(self._check_thread.quit)

        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._cancel_btn.setVisible(True)
        self._check_all_btn.setEnabled(False)
        self._check_one_btn.setEnabled(False)
        self._status_label.setText(f"Проверяем {len(proxies)} прокси...")

        self._check_thread.start()

    def _on_progress(self, value: int) -> None:
        """Обновить прогресс-бар."""
        self._progress_bar.setValue(value)

    def _on_proxy_checked(self, proxy: str, result: dict) -> None:
        """Обновить строку прокси после проверки."""
        self._refresh_table()

    def _on_check_finished(self) -> None:
        """Завершение проверки прокси."""
        self._progress_bar.setValue(100)
        self._progress_bar.setVisible(False)
        self._cancel_btn.setVisible(False)
        self._check_all_btn.setEnabled(True)
        self._check_one_btn.setEnabled(True)

        proxies = self._proxy_manager.get_all_proxies()
        alive = sum(
            1 for p in proxies
            if self._proxy_manager.get_proxy_info(p).get("status") == "alive"
        )
        self._status_label.setText(
            f"Проверка завершена. Работает: {alive} / {len(proxies)}"
        )
        self._refresh_table()
        self._check_worker = None
