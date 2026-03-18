"""
Виджет планировщика задач — с видом по неделям и планировщиком по дням (как SMM Box).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from PyQt5.QtCore import Qt, QDate, QDateTime, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from core.profile_manager import ProfileManager
from core.scheduler import TaskScheduler

logger = logging.getLogger(__name__)

DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ---------------------------------------------------------------------------
# Dialog: Add/edit task
# ---------------------------------------------------------------------------

class AddTaskDialog(QDialog):
    """Диалог добавления новой задачи в планировщик (с поддержкой дней недели)."""

    def __init__(self, profile_names: List[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добавить задачу")
        self.setMinimumWidth(460)
        self.profile_names = profile_names
        self._selected_video: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        # Task type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["🔥 Прогрев", "📤 Постинг"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Тип задачи:", self.type_combo)

        # Profile
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.profile_names)
        form.addRow("Профиль:", self.profile_combo)

        layout.addLayout(form)

        # --- Warmup settings ---
        self.warmup_group = QGroupBox("⚙️ Параметры прогрева")
        warmup_form = QFormLayout(self.warmup_group)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 168)
        self.interval_spin.setValue(6)
        self.interval_spin.setSuffix(" ч")
        warmup_form.addRow("Интервал:", self.interval_spin)
        layout.addWidget(self.warmup_group)

        # --- Posting settings ---
        self.post_group = QGroupBox("📤 Параметры постинга")
        post_form = QFormLayout(self.post_group)

        # Video file
        video_row = QHBoxLayout()
        self.video_label = QLabel("Файл не выбран")
        self.video_label.setObjectName("fileLabel")
        self.video_btn = QPushButton("📁 Выбрать")
        self.video_btn.setMaximumWidth(90)
        self.video_btn.clicked.connect(self._select_video)
        video_row.addWidget(self.video_label, stretch=1)
        video_row.addWidget(self.video_btn)
        post_form.addRow("Видеофайл:", video_row)

        self.post_title_edit = QLineEdit()
        self.post_title_edit.setPlaceholderText("Заголовок видео")
        post_form.addRow("Заголовок:", self.post_title_edit)

        # Schedule mode toggle
        mode_row = QHBoxLayout()
        self.mode_specific = QPushButton("📅 Конкретная дата")
        self.mode_specific.setCheckable(True)
        self.mode_specific.setChecked(True)
        self.mode_recurring = QPushButton("🔁 По дням недели")
        self.mode_recurring.setCheckable(True)
        self.mode_specific.clicked.connect(lambda: self._set_mode(False))
        self.mode_recurring.clicked.connect(lambda: self._set_mode(True))
        mode_row.addWidget(self.mode_specific)
        mode_row.addWidget(self.mode_recurring)
        post_form.addRow("Тип расписания:", mode_row)

        # Specific date/time
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDateTime(
            QDateTime.currentDateTime().addSecs(3600)
        )
        self.datetime_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        post_form.addRow("Дата и время:", self.datetime_edit)

        # Day-of-week checkboxes + time
        self.days_widget = QWidget()
        days_layout = QVBoxLayout(self.days_widget)
        days_layout.setContentsMargins(0, 0, 0, 0)
        days_layout.setSpacing(6)

        day_check_row = QHBoxLayout()
        self.day_checks = []
        for day_ru in DAYS_RU:
            cb = QCheckBox(day_ru)
            day_check_row.addWidget(cb)
            self.day_checks.append(cb)
        days_layout.addLayout(day_check_row)

        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Время публикации:"))
        self.recurring_time = QTimeEdit()
        self.recurring_time.setDisplayFormat("HH:mm")
        self.recurring_time.setTime(self.recurring_time.time().fromString("12:00", "HH:mm"))
        time_row.addWidget(self.recurring_time)
        time_row.addStretch()
        days_layout.addLayout(time_row)

        self.days_widget.setVisible(False)
        post_form.addRow("Дни и время:", self.days_widget)

        layout.addWidget(self.post_group)
        self.post_group.setVisible(False)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_type_changed(self, index: int) -> None:
        is_posting = index == 1
        self.warmup_group.setVisible(not is_posting)
        self.post_group.setVisible(is_posting)
        self.adjustSize()

    def _set_mode(self, recurring: bool) -> None:
        self.mode_specific.setChecked(not recurring)
        self.mode_recurring.setChecked(recurring)
        self.datetime_edit.setVisible(not recurring)
        self.days_widget.setVisible(recurring)
        self.adjustSize()

    def _select_video(self) -> None:
        from pathlib import Path
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать видео", "data/videos",
            "Видеофайлы (*.mp4 *.mov *.avi *.mkv *.webm);;Все файлы (*)",
        )
        if path:
            self._selected_video = path
            self.video_label.setText(Path(path).name)
            if not self.post_title_edit.text():
                self.post_title_edit.setText(Path(path).stem)

    def _validate_and_accept(self) -> None:
        if not self.profile_combo.currentText():
            QMessageBox.warning(self, "Ошибка", "Выберите профиль.")
            return
        if self.type_combo.currentIndex() == 1:
            if not self._selected_video:
                QMessageBox.warning(self, "Ошибка", "Выберите видеофайл.")
                return
            if self.mode_recurring.isChecked():
                if not any(cb.isChecked() for cb in self.day_checks):
                    QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один день недели.")
                    return
        self.accept()

    def get_data(self) -> dict:
        is_posting = self.type_combo.currentIndex() == 1
        data = {
            "task_type": "posting" if is_posting else "warmup",
            "profile_name": self.profile_combo.currentText(),
            "interval_hours": self.interval_spin.value(),
        }
        if is_posting:
            data["video_path"] = self._selected_video or ""
            data["title"] = self.post_title_edit.text().strip()
            data["recurring"] = self.mode_recurring.isChecked()
            if data["recurring"]:
                data["days"] = [
                    DAYS_EN[i] for i, cb in enumerate(self.day_checks) if cb.isChecked()
                ]
                data["time_str"] = self.recurring_time.time().toString("HH:mm")
            else:
                dt = self.datetime_edit.dateTime().toPyDateTime()
                data["scheduled_dt"] = dt
                data["time_str"] = dt.strftime("%H:%M")
        return data


# ---------------------------------------------------------------------------
# Week calendar widget
# ---------------------------------------------------------------------------

class _DayColumn(QFrame):
    """Одна колонка дня в недельном представлении."""

    def __init__(self, day_label: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("scheduleCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QLabel(day_label)
        header.setAlignment(Qt.AlignCenter)
        header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        header.setStyleSheet("color: #4c84ff; padding: 4px;")
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #252840;")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(4)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_widget)
        layout.addWidget(scroll)

    def clear_cards(self) -> None:
        """Удалить все карточки задач."""
        while self._cards_layout.count() > 1:  # keep stretch
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_task_card(self, task_type: str, profile: str, time_str: str) -> None:
        """Добавить карточку задачи в колонку."""
        card = QFrame()
        card.setObjectName("postCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(6, 4, 6, 4)
        card_layout.setSpacing(2)

        icon = "🔥" if task_type == "warmup" else "📤"
        type_label = QLabel(f"{icon} {time_str}")
        type_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        type_label.setStyleSheet("color: #4c84ff;")
        card_layout.addWidget(type_label)

        prof_label = QLabel(profile)
        prof_label.setFont(QFont("Segoe UI", 9))
        prof_label.setStyleSheet("color: #8890a4;")
        card_layout.addWidget(prof_label)

        self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)


class WeekCalendarWidget(QWidget):
    """Виджет недельного календаря для отображения запланированных задач."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_week_offset = 0  # 0 = current week
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Navigation
        nav_row = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Предыдущая")
        self.prev_btn.clicked.connect(self._prev_week)
        nav_row.addWidget(self.prev_btn)

        self.week_label = QLabel()
        self.week_label.setAlignment(Qt.AlignCenter)
        self.week_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        nav_row.addWidget(self.week_label, stretch=1)

        self.next_btn = QPushButton("Следующая ▶")
        self.next_btn.clicked.connect(self._next_week)
        nav_row.addWidget(self.next_btn)

        self.today_btn = QPushButton("Сегодня")
        self.today_btn.clicked.connect(self._go_today)
        nav_row.addWidget(self.today_btn)

        layout.addLayout(nav_row)

        # Day columns
        cols_row = QHBoxLayout()
        cols_row.setSpacing(6)
        self._day_columns: List[_DayColumn] = []
        for day in DAYS_RU:
            col = _DayColumn(day)
            col.setMinimumWidth(100)
            col.setMinimumHeight(180)
            cols_row.addWidget(col)
            self._day_columns.append(col)
        layout.addLayout(cols_row)

        self._update_week_label()

    def _get_week_start(self) -> datetime:
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        return week_start + timedelta(weeks=self._current_week_offset)

    def _update_week_label(self) -> None:
        ws = self._get_week_start()
        we = ws + timedelta(days=6)
        self.week_label.setText(
            f"Неделя: {ws.strftime('%d.%m')} — {we.strftime('%d.%m.%Y')}"
        )
        # Highlight today
        today = datetime.now()
        for i, col in enumerate(self._day_columns):
            day_date = ws + timedelta(days=i)
            is_today = (
                day_date.date() == today.date()
                and self._current_week_offset == 0
            )
            day_label_text = DAYS_RU[i]
            if is_today:
                col.setStyleSheet(
                    "QFrame#scheduleCard { border: 2px solid #4c84ff; border-radius: 10px; }"
                )
            else:
                col.setStyleSheet("")

    def _prev_week(self) -> None:
        self._current_week_offset -= 1
        self._update_week_label()
        self.refresh_tasks([])

    def _next_week(self) -> None:
        self._current_week_offset += 1
        self._update_week_label()
        self.refresh_tasks([])

    def _go_today(self) -> None:
        self._current_week_offset = 0
        self._update_week_label()
        self.refresh_tasks([])

    def refresh_tasks(self, tasks) -> None:
        """Обновить карточки задач в колонках дней."""
        for col in self._day_columns:
            col.clear_cards()

        ws = self._get_week_start()

        for task in tasks:
            # Determine which days this task falls on
            if task.task_type == "warmup":
                continue  # Warmup tasks don't have a specific day display

            schedule_str = task.schedule_str  # e.g. "ежедневно в 12:00" or "monday, wednesday в 14:00"
            time_str = ""
            if " в " in schedule_str:
                time_str = schedule_str.split(" в ")[-1].strip()

            target_days: List[int] = []  # 0=Mon..6=Sun

            if "ежедневно" in schedule_str:
                target_days = list(range(7))
            else:
                for i, day_en in enumerate(DAYS_EN):
                    if day_en in schedule_str.lower():
                        target_days.append(i)

            for day_idx in target_days:
                day_date = ws + timedelta(days=day_idx)
                self._day_columns[day_idx].add_task_card(
                    task.task_type,
                    task.profile_name,
                    time_str or "—",
                )


# ---------------------------------------------------------------------------
# Main scheduler widget
# ---------------------------------------------------------------------------

class SchedulerWidget(QWidget):
    """Виджет управления планировщиком задач с видом по неделям."""

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

        # Auto-refresh timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_tasks)
        self._timer.start(10_000)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        header = QLabel("📅 Планировщик")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setObjectName("pageTitle")
        layout.addWidget(header)

        # Control bar
        ctrl_row = QHBoxLayout()

        self.add_btn = QPushButton("➕ Добавить задачу")
        self.add_btn.setObjectName("accentButton")
        self.add_btn.clicked.connect(self._add_task)
        ctrl_row.addWidget(self.add_btn)

        self.delete_btn = QPushButton("🗑️ Удалить задачу")
        self.delete_btn.clicked.connect(self._delete_task)
        ctrl_row.addWidget(self.delete_btn)

        ctrl_row.addSpacing(16)

        self.toggle_btn = QPushButton("▶️ Запустить планировщик")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.toggled.connect(self._toggle_scheduler)
        ctrl_row.addWidget(self.toggle_btn)

        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self._refresh_tasks)
        ctrl_row.addWidget(self.refresh_btn)

        ctrl_row.addStretch()

        self.status_label = QLabel("⏸ Планировщик остановлен")
        self.status_label.setStyleSheet("color: #6b7394; font-weight: bold;")
        ctrl_row.addWidget(self.status_label)

        layout.addLayout(ctrl_row)

        # Tabs: Week view + Task list
        self.tabs = QTabWidget()

        # Tab 0 — Week calendar
        week_tab = QWidget()
        week_layout = QVBoxLayout(week_tab)
        week_layout.setContentsMargins(8, 8, 8, 8)
        self.week_calendar = WeekCalendarWidget()
        week_layout.addWidget(self.week_calendar)
        self.tabs.addTab(week_tab, "🗓️ Неделя")

        # Tab 1 — Task list table
        tasks_tab = QWidget()
        tasks_layout = QVBoxLayout(tasks_tab)
        tasks_layout.setContentsMargins(8, 8, 8, 8)

        self.tasks_table = QTableWidget(0, len(self.COLUMNS))
        self.tasks_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tasks_table.setAlternatingRowColors(True)
        self.tasks_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tasks_table.customContextMenuRequested.connect(self._show_task_context_menu)
        tasks_layout.addWidget(self.tasks_table)
        self.tabs.addTab(tasks_tab, "📋 Список задач")

        # Tab 2 — Day-based recurring schedule configurator
        day_tab = QWidget()
        day_layout = QVBoxLayout(day_tab)
        day_layout.setContentsMargins(8, 8, 8, 8)
        day_layout.addWidget(self._create_day_schedule_panel())
        self.tabs.addTab(day_tab, "🔁 Расписание по дням")

        layout.addWidget(self.tabs)

    def _create_day_schedule_panel(self) -> QWidget:
        """Создать панель настройки расписания по дням недели."""
        panel = QGroupBox("🔁 Настройка повторяющегося расписания")
        panel_layout = QVBoxLayout(panel)

        desc = QLabel(
            "Настройте автоматическую публикацию видео по выбранным дням недели.\n"
            "Задача будет запускаться каждую неделю в указанные дни и время."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8890a4;")
        panel_layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(10)

        # Profile selector
        self.ds_profile_combo = QComboBox()
        form.addRow("Аккаунт:", self.ds_profile_combo)

        # Video file
        video_row = QHBoxLayout()
        self.ds_video_label = QLabel("Файл не выбран")
        self.ds_video_label.setObjectName("fileLabel")
        ds_video_btn = QPushButton("📁 Выбрать")
        ds_video_btn.setMaximumWidth(90)
        ds_video_btn.clicked.connect(self._ds_select_video)
        video_row.addWidget(self.ds_video_label, stretch=1)
        video_row.addWidget(ds_video_btn)
        form.addRow("Видеофайл:", video_row)
        self._ds_video_path: Optional[str] = None

        self.ds_title_edit = QLineEdit()
        self.ds_title_edit.setPlaceholderText("Заголовок видео")
        form.addRow("Заголовок:", self.ds_title_edit)

        panel_layout.addLayout(form)

        # Days of week grid
        days_group = QGroupBox("Дни публикации")
        days_grid = QHBoxLayout(days_group)
        self.ds_day_checks: List[QCheckBox] = []
        self.ds_day_times: List[QTimeEdit] = []

        for i, day_ru in enumerate(DAYS_RU):
            day_widget = QWidget()
            col_layout = QVBoxLayout(day_widget)
            col_layout.setSpacing(4)
            col_layout.setContentsMargins(4, 4, 4, 4)

            cb = QCheckBox(day_ru)
            cb.setStyleSheet("font-weight: bold;")
            col_layout.addWidget(cb, alignment=Qt.AlignHCenter)

            te = QTimeEdit()
            te.setDisplayFormat("HH:mm")
            te.setTime(te.time().fromString("12:00", "HH:mm"))
            te.setEnabled(False)
            cb.toggled.connect(te.setEnabled)
            col_layout.addWidget(te)

            days_grid.addWidget(day_widget)
            self.ds_day_checks.append(cb)
            self.ds_day_times.append(te)

        panel_layout.addWidget(days_group)

        # Add button
        add_row = QHBoxLayout()
        self.ds_add_btn = QPushButton("➕ Добавить расписание")
        self.ds_add_btn.setObjectName("accentButton")
        self.ds_add_btn.setMinimumHeight(40)
        self.ds_add_btn.clicked.connect(self._add_day_schedule)
        add_row.addWidget(self.ds_add_btn)
        add_row.addStretch()
        panel_layout.addLayout(add_row)
        panel_layout.addStretch()

        return panel

    def _ds_select_video(self) -> None:
        from pathlib import Path
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать видео", "data/videos",
            "Видеофайлы (*.mp4 *.mov *.avi *.mkv *.webm);;Все файлы (*)",
        )
        if path:
            self._ds_video_path = path
            self.ds_video_label.setText(Path(path).name)
            if not self.ds_title_edit.text():
                self.ds_title_edit.setText(Path(path).stem)

    def _add_day_schedule(self) -> None:
        """Добавить задачу с расписанием по дням недели."""
        profile_name = self.ds_profile_combo.currentText()
        if not profile_name:
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт.")
            return
        if not self._ds_video_path:
            QMessageBox.warning(self, "Ошибка", "Выберите видеофайл.")
            return

        selected_days = [
            (DAYS_EN[i], self.ds_day_times[i].time().toString("HH:mm"))
            for i, cb in enumerate(self.ds_day_checks)
            if cb.isChecked()
        ]
        if not selected_days:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один день.")
            return

        metadata = {"title": self.ds_title_edit.text().strip()}
        days_list = [d[0] for d in selected_days]
        # Use the first selected day's time as common time (simplified)
        time_str = selected_days[0][1]

        try:
            if hasattr(self.scheduler, "add_posting_task_by_days"):
                task_id = self.scheduler.add_posting_task_by_days(
                    profile_name=profile_name,
                    video_path=self._ds_video_path,
                    metadata=metadata,
                    days=days_list,
                    time_str=time_str,
                )
            else:
                task_id = self.scheduler.add_posting_task(
                    profile_name=profile_name,
                    video_path=self._ds_video_path,
                    metadata=metadata,
                    time_str=time_str,
                )
            self._refresh_tasks()
            days_display = ", ".join(DAYS_RU[DAYS_EN.index(d)] for d in days_list)
            QMessageBox.information(
                self, "Готово",
                f"Расписание добавлено!\nДни: {days_display}\nВремя: {time_str}\nЗадача ID: {task_id}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))

    def _connect_signals(self) -> None:
        self.scheduler.task_started.connect(self._on_task_started)
        self.scheduler.task_completed.connect(self._on_task_completed)
        self.scheduler.task_error.connect(self._on_task_error)

    def _refresh_tasks(self) -> None:
        """Обновить таблицу задач и недельный вид."""
        tasks = self.scheduler.get_tasks()

        # Update profiles list in day schedule panel
        profiles = self.profile_manager.list_profiles()
        names = [p["name"] for p in profiles]
        current = self.ds_profile_combo.currentText()
        self.ds_profile_combo.clear()
        self.ds_profile_combo.addItems(names)
        idx = self.ds_profile_combo.findText(current)
        if idx >= 0:
            self.ds_profile_combo.setCurrentIndex(idx)

        # Update week calendar
        self.week_calendar.refresh_tasks(tasks)

        # Update task table
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
                elif data.get("recurring"):
                    if hasattr(self.scheduler, "add_posting_task_by_days"):
                        task_id = self.scheduler.add_posting_task_by_days(
                            profile_name=data["profile_name"],
                            video_path=data["video_path"],
                            metadata={"title": data.get("title", "")},
                            days=data["days"],
                            time_str=data["time_str"],
                        )
                    else:
                        task_id = self.scheduler.add_posting_task(
                            profile_name=data["profile_name"],
                            video_path=data["video_path"],
                            metadata={"title": data.get("title", "")},
                            time_str=data["time_str"],
                        )
                else:
                    task_id = self.scheduler.add_posting_task(
                        profile_name=data["profile_name"],
                        video_path=data["video_path"],
                        metadata={"title": data.get("title", "")},
                        time_str=data["time_str"],
                    )
                self._refresh_tasks()
                QMessageBox.information(self, "Задача добавлена", f"Задача {task_id} добавлена.")
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))

    def _delete_task(self) -> None:
        current = self.tasks_table.currentItem()
        if not current:
            QMessageBox.warning(self, "Нет выбора", "Выберите задачу.")
            return
        task_id_item = self.tasks_table.item(self.tasks_table.currentRow(), 0)
        if task_id_item:
            self.scheduler.remove_task(task_id_item.text())
            self._refresh_tasks()

    def _toggle_scheduler(self, checked: bool) -> None:
        if checked:
            if not self.scheduler.isRunning():
                self.scheduler.start()
            self.toggle_btn.setText("⏹️ Остановить планировщик")
            self.status_label.setText("▶ Планировщик работает")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            if self.scheduler.isRunning():
                self.scheduler.stop()
            self.toggle_btn.setText("▶️ Запустить планировщик")
            self.status_label.setText("⏸ Планировщик остановлен")
            self.status_label.setStyleSheet("color: #6b7394; font-weight: bold;")

    def _show_task_context_menu(self, pos) -> None:
        row = self.tasks_table.rowAt(pos.y())
        if row < 0:
            return
        self.tasks_table.selectRow(row)
        menu = QMenu(self)
        del_action = QAction("🗑️ Удалить задачу", self)
        del_action.triggered.connect(self._delete_task)
        menu.addAction(del_action)
        menu.exec_(self.tasks_table.viewport().mapToGlobal(pos))

    def _on_task_started(self, task_id: str) -> None:
        self._update_task_status(task_id, "⚙️ выполняется")

    def _on_task_completed(self, task_id: str) -> None:
        self._update_task_status(task_id, "✅ завершено")

    def _on_task_error(self, error_msg: str) -> None:
        logger.error("Ошибка задачи планировщика: %s", error_msg)

    def _update_task_status(self, task_id: str, status: str) -> None:
        for row in range(self.tasks_table.rowCount()):
            id_item = self.tasks_table.item(row, 0)
            if id_item and id_item.text() == task_id:
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.tasks_table.setItem(row, 4, status_item)
                break
