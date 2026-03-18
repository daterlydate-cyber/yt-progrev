"""
Движок автопостинга видео на YouTube.
Загружает видео через YouTube Studio в браузере без использования API.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtCore import QThread, pyqtSignal
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.actions import HumanActions
from core.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

# Максимальное время ожидания обработки видео (секунды)
MAX_UPLOAD_WAIT = 3600  # 1 час


class PosterEngine(QThread):
    """Движок загрузки видео через YouTube Studio."""

    # Сигналы для обновления GUI
    upload_progress = pyqtSignal(str, int)   # (описание, процент)
    upload_completed = pyqtSignal(str)        # URL или ID видео
    error_occurred = pyqtSignal(str)          # сообщение об ошибке

    def __init__(
        self,
        profile_name: str,
        browser_manager: BrowserManager,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[list] = None,
        thumbnail_path: Optional[str] = None,
        privacy: str = "public",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile_name = profile_name
        self.browser_manager = browser_manager
        self.video_path = video_path
        self.title = title
        self.description = description
        self.tags = tags or []
        self.thumbnail_path = thumbnail_path
        self.privacy = privacy  # "public", "unlisted", "private"

    def run(self) -> None:
        """Основной процесс загрузки видео — выполняется в отдельном потоке."""
        driver = self.browser_manager.get_driver(self.profile_name)
        if driver is None:
            self.error_occurred.emit(
                f"Браузер для профиля '{self.profile_name}' не запущен. "
                "Сначала откройте браузер в разделе 'Браузер'."
            )
            return

        video_file = Path(self.video_path)
        if not video_file.exists():
            self.error_occurred.emit(f"Файл видео не найден: {self.video_path}")
            return

        try:
            self._upload_video(driver, video_file)
        except Exception as exc:
            logger.error("Ошибка при загрузке видео: %s", exc)
            self.error_occurred.emit(str(exc))

    def _upload_video(self, driver, video_file: Path) -> None:
        """Процесс загрузки видео через YouTube Studio."""
        wait = WebDriverWait(driver, 30)

        # Шаг 1: Переходим в YouTube Studio
        self.upload_progress.emit("Открываем YouTube Studio...", 5)
        driver.get("https://studio.youtube.com")
        HumanActions.random_delay(3, 5)

        # Шаг 2: Нажимаем «Создать» → «Загрузить видео»
        self.upload_progress.emit("Нажимаем 'Создать'...", 10)
        try:
            create_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#create-icon, button[aria-label='Создать']")
                )
            )
            create_button.click()
            HumanActions.random_delay(1, 2)

            upload_option = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//tp-yt-paper-item[contains(., 'Загрузить') or contains(., 'Upload')]")
                )
            )
            upload_option.click()
        except TimeoutException:
            # Пробуем прямой переход через URL
            logger.warning("Кнопка создания не найдена, пробуем прямой URL.")
            driver.get("https://www.youtube.com/upload")

        HumanActions.random_delay(2, 4)

        # Шаг 3: Выбираем файл через input[type="file"]
        self.upload_progress.emit("Выбираем файл...", 15)
        try:
            file_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='file']")
                )
            )
            # Делаем input видимым если он скрыт
            driver.execute_script("arguments[0].style.display = 'block';", file_input)
            file_input.send_keys(str(video_file.resolve()))
        except TimeoutException as exc:
            raise RuntimeError("Не найден input для загрузки файла") from exc

        # Шаг 4: Ждём появления формы заполнения данных
        self.upload_progress.emit("Ожидаем загрузки формы...", 20)
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#title-textarea, ytcp-video-title")
                )
            )
        except TimeoutException:
            logger.warning("Форма не появилась, продолжаем...")

        HumanActions.random_delay(2, 3)

        # Шаг 5: Заполняем заголовок
        self.upload_progress.emit("Заполняем заголовок...", 30)
        try:
            title_field = driver.find_element(
                By.CSS_SELECTOR,
                "#title-textarea #child-input, "
                "ytcp-video-title #textbox",
            )
            # Очищаем поле через Ctrl+A и Delete
            title_field.click()
            HumanActions.random_delay(0.3, 0.7)
            title_field.send_keys(Keys.CONTROL + "a")
            title_field.send_keys(Keys.BACKSPACE)
            HumanActions.type_like_human(title_field, self.title)
        except NoSuchElementException as exc:
            logger.warning("Поле заголовка не найдено: %s", exc)

        HumanActions.random_delay(0.5, 1.5)

        # Шаг 6: Заполняем описание
        if self.description:
            self.upload_progress.emit("Заполняем описание...", 40)
            try:
                desc_field = driver.find_element(
                    By.CSS_SELECTOR,
                    "#description-textarea #child-input, "
                    "ytcp-video-description #textbox",
                )
                desc_field.click()
                HumanActions.random_delay(0.3, 0.7)
                HumanActions.type_like_human(desc_field, self.description)
            except NoSuchElementException as exc:
                logger.warning("Поле описания не найдено: %s", exc)

        # Шаг 7: Загружаем превью (если указано)
        if self.thumbnail_path:
            thumbnail_file = Path(self.thumbnail_path)
            if thumbnail_file.exists():
                self.upload_progress.emit("Загружаем превью...", 50)
                try:
                    thumbnail_input = driver.find_element(
                        By.CSS_SELECTOR, "input[accept*='image']"
                    )
                    driver.execute_script(
                        "arguments[0].style.display = 'block';", thumbnail_input
                    )
                    thumbnail_input.send_keys(str(thumbnail_file.resolve()))
                    HumanActions.random_delay(1, 2)
                except NoSuchElementException as exc:
                    logger.warning("Input для превью не найден: %s", exc)

        # Шаг 8: Переходим к следующему шагу через кнопки "Далее"
        self.upload_progress.emit("Переходим к настройкам...", 60)
        for step in range(3):
            try:
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "ytcp-button#next-button, #next-button")
                    )
                )
                next_btn.click()
                HumanActions.random_delay(1.5, 3)
            except TimeoutException:
                logger.debug("Кнопка 'Далее' не найдена на шаге %d.", step)
                break

        # Шаг 9: Устанавливаем доступ к видео
        self.upload_progress.emit("Устанавливаем доступ к видео...", 70)
        self._set_privacy(driver)

        # Шаг 10: Ожидаем завершения загрузки и публикуем
        self.upload_progress.emit("Ожидаем завершения загрузки...", 80)
        self._wait_for_upload(driver)

        # Нажимаем «Опубликовать»
        self.upload_progress.emit("Публикуем видео...", 90)
        try:
            publish_btn = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "ytcp-button#done-button, "
                        "ytcp-button#publish-button, "
                        "#done-button",
                    )
                )
            )
            publish_btn.click()
            HumanActions.random_delay(3, 5)
            logger.info("Видео опубликовано.")
            self.upload_progress.emit("Видео успешно опубликовано!", 100)
            self.upload_completed.emit(self.title)
        except TimeoutException as exc:
            raise RuntimeError("Не найдена кнопка публикации") from exc

    def _set_privacy(self, driver) -> None:
        """Установить настройки доступа к видео."""
        privacy_map = {
            "public": "Открытый доступ",
            "unlisted": "Доступ по ссылке",
            "private": "Ограниченный доступ",
        }
        label = privacy_map.get(self.privacy, "Открытый доступ")

        try:
            radio = driver.find_element(
                By.XPATH,
                f"//tp-yt-paper-radio-button[contains(., '{label}')] | "
                f"//ytcp-privacy-radio-group //*[contains(text(), '{label}')]",
            )
            radio.click()
            HumanActions.random_delay(0.5, 1.0)
        except NoSuchElementException:
            logger.warning("Кнопка доступа '%s' не найдена.", label)

    def _wait_for_upload(self, driver) -> None:
        """Ожидать завершения технической обработки видео."""
        start_time = time.time()
        while time.time() - start_time < MAX_UPLOAD_WAIT:
            try:
                # Проверяем прогресс загрузки
                progress_el = driver.find_element(
                    By.CSS_SELECTOR,
                    "ytcp-video-upload-progress span, "
                    "ytcp-uploads-dialog .progress-label",
                )
                progress_text = progress_el.text
                if "завершена" in progress_text.lower() or "uploaded" in progress_text.lower():
                    break
                logger.debug("Прогресс загрузки: %s", progress_text)
            except NoSuchElementException:
                # Элемент прогресса не найден — возможно загрузка завершилась
                break
            time.sleep(5)
