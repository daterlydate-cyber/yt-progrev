"""
Настройка логирования приложения.
Логи пишутся в файл и выводятся в GUI через Qt-сигнал.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

LOG_DIR = Path("data/logs")
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """
    Настроить корневой логгер приложения.

    :param level: Уровень логирования (default: INFO)
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Форматтер
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Файловый хендлер с ротацией по дням
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"app_{today}.log"
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Очищаем существующие хендлеры чтобы не дублировать
    if root_logger.handlers:
        root_logger.handlers.clear()

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Получить именованный логгер.

    :param name: Имя логгера (обычно __name__ модуля)
    :return: Логгер
    """
    return logging.getLogger(name)


class QtLogSignals(QObject):
    """Объект сигналов для Qt-хендлера (QObject не может быть миксином)."""

    log_message = pyqtSignal(str, int)  # (formatted_message, levelno)


class QtLogHandler(logging.Handler):
    """
    Хендлер логирования, который эмитит Qt-сигнал для вывода в QTextEdit.

    Использование:
        handler = QtLogHandler()
        handler.signals.log_message.connect(my_text_edit_slot)
        logging.getLogger().addHandler(handler)
    """

    def __init__(self) -> None:
        super().__init__()
        self.signals = QtLogSignals()
        self.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    def emit(self, record: logging.LogRecord) -> None:
        """Эмитировать сигнал с отформатированным сообщением."""
        try:
            msg = self.format(record)
            self.signals.log_message.emit(msg, record.levelno)
        except Exception:
            self.handleError(record)
