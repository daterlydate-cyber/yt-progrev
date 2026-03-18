"""
Виджет планировщика задач.
"""

import logging
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.profile_manager import ProfileManager
from core.scheduler import TaskScheduler

logger = logging.getLogger(__name__)


class AddTaskDialog(QDialog):
    """Диалог добавления новой задачи в планировщик."""

    def __init__(self, profile_names: list, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добавить задачу")
        self.setMinimumWidth(400)
        self.profile_names = profile_names
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Прогрев", "Постинг"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("Тип задачи:", self.type_combo)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.profile_names)
        layout.addRow("Профиль:", self.profile_combo)

        # Для прогрева — интервал в часах
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 168)
        self.interval_spin.setValue(6)
        self.interval_label = QLabel("Интервал (часов):")
        layout.addRow(self.interval_label, self.interval_spin)

        # Для постинга — время (HH:MM)
        self.time_edit = QLineEdit("12:00")
        self.time_edit.setPlaceholderText("HH:MM")
        self.time_label = QLabel("Время публикации:")
        self.time_edit.setVisible(False)
        self.time_label.setVisible(False)
        layout.addRow(self.time_label, self.time_edit)

        # Для постинга — путь к видео
        self.video_edit = QLineEdit()
        self.video_edit.setPlaceholderText("Путь к видеофайлу")
        self.video_label = QLabel("Видеофайл:")
        self.video_edit.setVisible(False)
        self.video_label.setVisible(False)
        layout.addRow(self.video_label, self.video_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_type_changed(self, index: int) -> None:
        """Переключить видимость полей в зависимости от типа задачи."""
        is_posting = index == 1
        self.interval_label.setVisible(not is_posting)
        self.interval_spin.setVisible(not is_posting)
        self.time_label.setVisible(is_posting)
        self.time_edit.setVisible(is_posting)
        self.video_label.setVisible(is_posting)
        self.video_edit.setVisible(is_posting)

    def _validate_and_accept(self) -> None:
        """Проверить данные и принять диалог."""
        if not self.profile_combo.currentText():
            QMessageBox.warning(self, "Ошибка", "Выберите профиль.")
            return
        if self.type_combo.currentIndex() == 1:
            if not self.video_edit.text().strip():
                QMessageBox.warning(self, "Ошибка", "Укажите путь к видеофайлу.")
                return
        self.accept()

    def get_data(self) -> dict:
        """Получить данные из формы."""
        return {
            "task_type": "warmup" if self.type_combo.currentIndex() == 0 else "posting",
            "profile_name": self.profile_combo.currentText(),
            "interval_hours": self.interval_spin.value(),
            "time_str": self.time_edit.text().strip(),
            "video_path": self.video_edit.text().strip(),
        }


class SchedulerWidget(QWidget):
    """Виджет управления планировщиком задач."""

    COLUMNS = ["ID", "Тип", "Профиль", "Расписание", "Статус", "Последний запуск"]

    def __init__(
        self,
        scheduler: TaskScheduler,
        profile_manager: ProfileManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.scheduler = scheduler
        self.profile_manager = profile_manager
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Панель кнопок
        btn_row = QHBoxLayout()

        self.add_btn = QPushButton("➕ Добавить задачу")
        self.add_btn.clicked.connect(self._add_task)

        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self._delete_task)

        self.toggle_btn = QPushButton("▶️ Вкл планировщик")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.toggled.connect(self._toggle_scheduler)

        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self._refresh_tasks)

        for btn in [self.add_btn, self.delete_btn, self.toggle_btn, self.refresh_btn]:
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Статус планировщика
        self.status_label = QLabel("Статус: Остановлен")
        layout.addWidget(self.status_label)

        # Таблица задач
        tasks_group = QGroupBox("Запланированные задачи")
        tasks_layout = QVBoxLayout(tasks_group)

        self.tasks_table = QTableWidget(0, len(self.COLUMNS))
        self.tasks_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tasks_table.setAlternatingRowColors(True)
        tasks_layout.addWidget(self.tasks_table)

        layout.addWidget(tasks_group)

    def _connect_signals(self) -> None:
        """Подключить сигналы планировщика к GUI."""
        self.scheduler.task_started.connect(self._on_task_started)
        self.scheduler.task_completed.connect(self._on_task_completed)
        self.scheduler.task_error.connect(self._on_task_error)

    def _refresh_tasks(self) -> None:
        """Обновить таблицу задач."""
        tasks = self.scheduler.get_tasks()
        self.tasks_table.setRowCount(0)

        for task in tasks:
            row = self.tasks_table.rowCount()
            self.tasks_table.insertRow(row)

            type_label = "🔥 Прогрев" if task.task_type == "warmup" else "📤 Постинг"
            items = [
                task.task_id,
                type_label,
                task.profile_name,
                task.schedule_str,
                task.status,
                task.last_run[:16] if task.last_run else "—",
            ]
            for col, value in enumerate(items):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                item.setData(Qt.UserRole, task.task_id)
                self.tasks_table.setItem(row, col, item)

    def _add_task(self) -> None:
        """Открыть диалог добавления задачи."""
        profiles = self.profile_manager.list_profiles()
        names = [p["name"] for p in profiles]
        if not names:
            QMessageBox.warning(self, "Нет профилей", "Сначала создайте профиль.")
            return

        dialog = AddTaskDialog(names, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                if data["task_type"] == "warmup":
                    task_id = self.scheduler.add_warmup_task(
                        profile_name=data["profile_name"],
                        interval_hours=data["interval_hours"],
                    )
                else:
                    task_id = self.scheduler.add_posting_task(
                        profile_name=data["profile_name"],
                        video_path=data["video_path"],
                        metadata={},
                        time_str=data["time_str"],
                    )
                self._refresh_tasks()
                QMessageBox.information(
                    self, "Задача добавлена", f"Задача {task_id} добавлена."
                )
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _delete_task(self) -> None:
        """Удалить выбранную задачу."""
        current = self.tasks_table.currentItem()
        if not current:
            QMessageBox.warning(self, "Нет выбора", "Выберите задачу.")
            return

        task_id = self.tasks_table.item(self.tasks_table.currentRow(), 0)
        if task_id:
            self.scheduler.remove_task(task_id.text())
            self._refresh_tasks()

    def _toggle_scheduler(self, checked: bool) -> None:
        """Включить или выключить планировщик."""
        if checked:
            if not self.scheduler.isRunning():
                self.scheduler.start()
            self.toggle_btn.setText("⏹️ Выкл планировщик")
            self.status_label.setText("Статус: Работает")
        else:
            if self.scheduler.isRunning():
                self.scheduler.stop()
            self.toggle_btn.setText("▶️ Вкл планировщик")
            self.status_label.setText("Статус: Остановлен")

    def _on_task_started(self, task_id: str) -> None:
        """Обновить статус задачи на 'выполняется'."""
        self._update_task_status(task_id, "⚙️ выполняется")

    def _on_task_completed(self, task_id: str) -> None:
        """Обновить статус задачи на 'завершено'."""
        self._update_task_status(task_id, "✅ завершено")

    def _on_task_error(self, error_msg: str) -> None:
        """Показать ошибку выполнения задачи."""
        logger.error("Ошибка задачи планировщика: %s", error_msg)

    def _update_task_status(self, task_id: str, status: str) -> None:
        """Найти задачу в таблице и обновить её статус."""
        for row in range(self.tasks_table.rowCount()):
            id_item = self.tasks_table.item(row, 0)
            if id_item and id_item.text() == task_id:
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.tasks_table.setItem(row, 4, status_item)
                break
