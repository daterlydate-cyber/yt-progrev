"""
Точка входа приложения YT-Progrev.
Инициализирует PyQt5 приложение, создаёт нужные директории и запускает GUI.
"""

import sys
import os
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Создаём нужные директории при первом запуске
def ensure_directories() -> None:
    """Создать необходимые директории, если они не существуют."""
    dirs = [
        "data/profiles",
        "data/cookies",
        "data/videos",
        "data/logs",
        "data/proxies",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Главная функция запуска приложения."""
    # Создаём папки
    ensure_directories()

    # Инициализируем логирование
    from utils.logger import setup_logging
    setup_logging()

    # Создаём Qt-приложение
    app = QApplication(sys.argv)
    app.setApplicationName("YT-Progrev")
    app.setApplicationVersion("1.0.0")
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    # Загружаем QSS стили
    qss_path = Path("gui/styles.qss")
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # Создаём и показываем главное окно
    from gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
