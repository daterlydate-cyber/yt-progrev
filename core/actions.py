"""
Имитация человеческих действий в браузере.
Набор вспомогательных методов для взаимодействия с YouTube-интерфейсом.
"""

import logging
import random
import time
from typing import Optional

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


class HumanActions:
    """Статические методы для имитации действий реального пользователя."""

    @staticmethod
    def random_delay(min_sec: float = 0.5, max_sec: float = 2.0) -> None:
        """
        Случайная пауза между действиями.

        :param min_sec: Минимальное время паузы в секундах
        :param max_sec: Максимальное время паузы в секундах
        """
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    @staticmethod
    def random_scroll(driver) -> None:
        """
        Случайная прокрутка страницы вниз и/или вверх.

        :param driver: Экземпляр WebDriver
        """
        scroll_amount = random.randint(300, 1000)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        HumanActions.random_delay(0.5, 1.5)
        # Иногда прокручиваем немного обратно
        if random.random() < 0.3:
            back_scroll = random.randint(50, 200)
            driver.execute_script(f"window.scrollBy(0, -{back_scroll});")
            HumanActions.random_delay(0.3, 0.8)

    @staticmethod
    def random_mouse_movement(driver) -> None:
        """
        Имитация случайных движений мыши через ActionChains.

        :param driver: Экземпляр WebDriver
        """
        try:
            action = ActionChains(driver)
            # Серия случайных перемещений
            for _ in range(random.randint(3, 7)):
                x_offset = random.randint(-200, 200)
                y_offset = random.randint(-200, 200)
                action.move_by_offset(x_offset, y_offset)
                action.pause(random.uniform(0.05, 0.2))
            action.perform()
        except Exception as exc:
            logger.debug("Ошибка при движении мышью: %s", exc)

    @staticmethod
    def type_like_human(element, text: str) -> None:
        """
        Ввод текста с задержками между символами (имитация печати).

        :param element: Элемент ввода (WebElement)
        :param text: Текст для ввода
        """
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))

    @staticmethod
    def search_youtube(driver, query: str) -> bool:
        """
        Выполнить поиск на YouTube.

        :param driver: Экземпляр WebDriver
        :param query: Поисковый запрос
        :return: True если поиск выполнен успешно
        """
        try:
            driver.get("https://www.youtube.com")
            HumanActions.random_delay(2, 4)

            # Находим строку поиска
            wait = WebDriverWait(driver, 15)
            search_box = wait.until(
                EC.element_to_be_clickable((By.NAME, "search_query"))
            )
            search_box.click()
            HumanActions.random_delay(0.3, 0.8)

            # Вводим запрос как человек
            HumanActions.type_like_human(search_box, query)
            HumanActions.random_delay(0.5, 1.5)
            search_box.send_keys(Keys.RETURN)

            HumanActions.random_delay(2, 4)
            logger.debug("Поиск по запросу '%s' выполнен.", query)
            return True
        except (TimeoutException, NoSuchElementException) as exc:
            logger.warning("Ошибка при поиске '%s': %s", query, exc)
            return False

    @staticmethod
    def click_video_from_results(driver) -> bool:
        """
        Кликнуть по случайному видео из результатов поиска.

        :param driver: Экземпляр WebDriver
        :return: True если клик выполнен успешно
        """
        try:
            wait = WebDriverWait(driver, 10)
            # Ждём загрузки результатов
            videos = wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "ytd-video-renderer #video-title")
                )
            )
            if not videos:
                return False

            # Выбираем случайное видео (не первое — слишком предсказуемо)
            idx = random.randint(0, min(len(videos) - 1, 8))
            selected = videos[idx]

            # Прокручиваем к видео
            driver.execute_script("arguments[0].scrollIntoView(true);", selected)
            HumanActions.random_delay(0.5, 1.5)
            selected.click()

            HumanActions.random_delay(2, 4)
            logger.debug("Кликнули по видео с индексом %d.", idx)
            return True
        except (TimeoutException, NoSuchElementException) as exc:
            logger.warning("Ошибка при клике по видео: %s", exc)
            return False

    @staticmethod
    def watch_video(driver, duration: int) -> None:
        """
        Просмотр видео в течение заданного времени с имитацией поведения.

        :param driver: Экземпляр WebDriver
        :param duration: Время просмотра в секундах
        """
        logger.debug("Начинаем просмотр видео на %d секунд.", duration)
        elapsed = 0
        check_interval = random.randint(15, 30)

        while elapsed < duration:
            sleep_time = min(check_interval, duration - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time

            # Иногда прокручиваем страницу вниз
            if random.random() < 0.3:
                HumanActions.random_scroll(driver)

            # Иногда двигаем мышью
            if random.random() < 0.2:
                HumanActions.random_mouse_movement(driver)

    @staticmethod
    def like_video(driver) -> bool:
        """
        Поставить лайк текущему видео.

        :param driver: Экземпляр WebDriver
        :return: True если лайк поставлен успешно
        """
        try:
            wait = WebDriverWait(driver, 10)

            # Прокручиваем к кнопке лайка
            like_button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "ytd-toggle-button-renderer:first-child #button[aria-label*='like' i], "
                        "like-button-view-model button",
                    )
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", like_button)
            HumanActions.random_delay(0.5, 1.5)
            like_button.click()
            logger.debug("Лайк поставлен.")
            return True
        except (TimeoutException, NoSuchElementException) as exc:
            logger.warning("Не удалось поставить лайк: %s", exc)
            return False

    @staticmethod
    def subscribe_channel(driver) -> bool:
        """
        Подписаться на канал текущего видео.

        :param driver: Экземпляр WebDriver
        :return: True если подписка выполнена успешно
        """
        try:
            wait = WebDriverWait(driver, 10)
            subscribe_button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "ytd-subscribe-button-renderer tp-yt-paper-button, "
                        "#subscribe-button ytd-subscribe-button-renderer button",
                    )
                )
            )
            # Проверяем что ещё не подписаны
            aria_label = subscribe_button.get_attribute("aria-label") or ""
            if "unsubscribe" in aria_label.lower() or "отписаться" in aria_label.lower():
                logger.debug("Уже подписаны на этот канал.")
                return False

            driver.execute_script("arguments[0].scrollIntoView(true);", subscribe_button)
            HumanActions.random_delay(0.5, 1.5)
            subscribe_button.click()
            logger.debug("Подписка выполнена.")
            return True
        except (TimeoutException, NoSuchElementException) as exc:
            logger.warning("Не удалось подписаться: %s", exc)
            return False

    @staticmethod
    def leave_comment(driver, text: str) -> bool:
        """
        Оставить комментарий к текущему видео.

        :param driver: Экземпляр WebDriver
        :param text: Текст комментария
        :return: True если комментарий оставлен успешно
        """
        try:
            wait = WebDriverWait(driver, 15)

            # Прокручиваем вниз чтобы появилась секция комментариев
            driver.execute_script("window.scrollTo(0, 600);")
            HumanActions.random_delay(2, 4)

            # Кликаем по полю ввода
            comment_box = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "ytd-comment-simplebox-renderer #placeholder-area")
                )
            )
            comment_box.click()
            HumanActions.random_delay(0.5, 1.5)

            # Вводим текст
            input_field = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "ytd-comment-simplebox-renderer #contenteditable-root")
                )
            )
            HumanActions.type_like_human(input_field, text)
            HumanActions.random_delay(0.5, 1.5)

            # Отправляем комментарий
            submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "ytd-comment-simplebox-renderer #submit-button")
                )
            )
            submit_button.click()
            logger.debug("Комментарий оставлен.")
            return True
        except (TimeoutException, NoSuchElementException) as exc:
            logger.warning("Не удалось оставить комментарий: %s", exc)
            return False
