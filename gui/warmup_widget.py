"""
Виджет настройки и запуска прогрева аккаунтов.
"""

import logging
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.browser_manager import BrowserManager
from core.profile_manager import ProfileManager
from core.warmup_engine import WarmupEngine

logger = logging.getLogger(__name__)


class WarmupWidget(QWidget):
    """Виджет для настройки и запуска тематического прогрева."""

    def __init__(
        self,
        profile_manager: ProfileManager,
        browser_manager: BrowserManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.browser_manager = browser_manager
        self._engine: Optional[WarmupEngine] = None
        self._setup_ui()
        self.refresh_profiles()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        # --- Блок настроек ---
        settings_group = QGroupBox("Настройки прогрева")
        settings_layout = QVBoxLayout(settings_group)

        # Выбор профиля
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Профиль:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        profile_row.addWidget(self.profile_combo)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setMaximumWidth(36)
        self.refresh_btn.setToolTip("Обновить список профилей")
        self.refresh_btn.clicked.connect(self.refresh_profiles)
        profile_row.addWidget(self.refresh_btn)
        profile_row.addStretch()
        settings_layout.addLayout(profile_row)

        # Ключевые слова
        kw_row = QHBoxLayout()
        kw_row.addWidget(QLabel("Ключевые слова:"))
        self.keywords_edit = QLineEdit()
        self.keywords_edit.setPlaceholderText("кулинария, рецепты, готовка (через запятую)")
        kw_row.addWidget(self.keywords_edit)
        settings_layout.addLayout(kw_row)

        # Количество действий + длительность просмотра
        actions_row = QHBoxLayout()
        actions_row.addWidget(QLabel("Действий за сессию:"))
        self.actions_spin = QSpinBox()
        self.actions_spin.setRange(1, 100)
        self.actions_spin.setValue(10)
        actions_row.addWidget(self.actions_spin)

        actions_row.addWidget(QLabel("Просмотр (сек):  от"))
        self.watch_min_spin = QSpinBox()
        self.watch_min_spin.setRange(5, 3600)
        self.watch_min_spin.setValue(30)
        actions_row.addWidget(self.watch_min_spin)

        actions_row.addWidget(QLabel("до"))
        self.watch_max_spin = QSpinBox()
        self.watch_max_spin.setRange(5, 3600)
        self.watch_max_spin.setValue(180)
        actions_row.addWidget(self.watch_max_spin)
        actions_row.addStretch()
        settings_layout.addLayout(actions_row)

        # Вероятности
        prob_row = QHBoxLayout()
        prob_row.addWidget(QLabel("Вероятность лайка:"))
        self.like_prob_spin = QDoubleSpinBox()
        self.like_prob_spin.setRange(0.0, 1.0)
        self.like_prob_spin.setSingleStep(0.05)
        self.like_prob_spin.setValue(0.30)
        prob_row.addWidget(self.like_prob_spin)

        prob_row.addWidget(QLabel("Подписки:"))
        self.sub_prob_spin = QDoubleSpinBox()
        self.sub_prob_spin.setRange(0.0, 1.0)
        self.sub_prob_spin.setSingleStep(0.05)
        self.sub_prob_spin.setValue(0.10)
        prob_row.addWidget(self.sub_prob_spin)

        prob_row.addWidget(QLabel("Комментария:"))
        self.comment_prob_spin = QDoubleSpinBox()
        self.comment_prob_spin.setRange(0.0, 1.0)
        self.comment_prob_spin.setSingleStep(0.01)
        self.comment_prob_spin.setValue(0.05)
        prob_row.addWidget(self.comment_prob_spin)
        prob_row.addStretch()
        settings_layout.addLayout(prob_row)

        # Шаблоны комментариев
        settings_layout.addWidget(QLabel("Шаблоны комментариев (по одному на строку):"))
        self.comments_edit = QTextEdit()
        self.comments_edit.setMaximumHeight(100)
        self.comments_edit.setPlaceholderText(
            "Отличное видео! 👍\nОчень интересно!\nСпасибо за контент!"
        )
        settings_layout.addWidget(self.comments_edit)

        main_layout.addWidget(settings_group)

        # --- Блок управления ---
        control_group = QGroupBox("Управление")
        control_layout = QVBoxLayout(control_group)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Старт прогрева")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._start_warmup)

        self.stop_btn = QPushButton("⏹️ Стоп")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_warmup)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        control_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% — %v/%m действий")
        control_layout.addWidget(self.progress_bar)

        main_layout.addWidget(control_group)

        # --- Лог текущих действий ---
        log_group = QGroupBox("Текущие действия")
        log_layout = QVBoxLayout(log_group)
        self.action_log = QTextEdit()
        self.action_log.setReadOnly(True)
        self.action_log.setMaximumHeight(200)
        log_layout.addWidget(self.action_log)
        main_layout.addWidget(log_group)

    def refresh_profiles(self) -> None:
        """Обновить список профилей в выпадающем списке."""
        current = self.profile_combo.currentText()
        self.profile_combo.clear()
        profiles = self.profile_manager.list_profiles()
        for p in profiles:
            self.profile_combo.addItem(p["name"])
        # Восстанавливаем выбранный
        idx = self.profile_combo.findText(current)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

    def _start_warmup(self) -> None:
        """Запустить прогрев."""
        profile_name = self.profile_combo.currentText()
        if not profile_name:
            QMessageBox.warning(self, "Нет профиля", "Выберите профиль для прогрева.")
            return

        # Парсим ключевые слова
        keywords_text = self.keywords_edit.text().strip()
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]
        if not keywords:
            QMessageBox.warning(self, "Нет ключевых слов", "Введите хотя бы одно ключевое слово.")
            return

        # Парсим шаблоны комментариев
        comments_text = self.comments_edit.toPlainText()
        templates = [t.strip() for t in comments_text.splitlines() if t.strip()]

        self._engine = WarmupEngine(
            profile_name=profile_name,
            browser_manager=self.browser_manager,
            profile_manager=self.profile_manager,
            keywords=keywords,
            actions_per_session=self.actions_spin.value(),
            watch_duration_range=(self.watch_min_spin.value(), self.watch_max_spin.value()),
            like_probability=self.like_prob_spin.value(),
            subscribe_probability=self.sub_prob_spin.value(),
            comment_probability=self.comment_prob_spin.value(),
            comment_templates=templates,
        )

        self._engine.progress_updated.connect(self._on_progress)
        self._engine.action_completed.connect(self._on_action)
        self._engine.error_occurred.connect(self._on_error)
        self._engine.warmup_finished.connect(self._on_finished)

        self.progress_bar.setValue(0)
        self.action_log.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self._engine.start()
        logger.info("Прогрев профиля '%s' запущен из GUI.", profile_name)

    def _stop_warmup(self) -> None:
        """Остановить прогрев."""
        if self._engine:
            self._engine.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_progress(self, profile_name: str, percent: int) -> None:
        """Обновить прогресс-бар."""
        self.progress_bar.setValue(percent)

    def _on_action(self, action_desc: str) -> None:
        """Добавить сообщение о действии в лог."""
        self.action_log.append(action_desc)
        scrollbar = self.action_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_error(self, error_msg: str) -> None:
        """Показать ошибку."""
        self.action_log.append(f"❌ Ошибка: {error_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_finished(self, profile_name: str) -> None:
        """Обработать завершение прогрева."""
        self.action_log.append(f"✅ Прогрев профиля '{profile_name}' завершён!")
        self.progress_bar.setValue(100)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
