"""
Генерация и применение отпечатков браузера (fingerprint).
"""

import random
from dataclasses import dataclass
from typing import List, Optional


# Популярные разрешения экрана
RESOLUTIONS = [
    "1920,1080",
    "1366,768",
    "1440,900",
    "1536,864",
    "1280,720",
    "1280,800",
    "1600,900",
    "2560,1440",
]

# Платформы
PLATFORMS = ["Win32", "Win64", "MacIntel", "Linux x86_64"]

# WebGL vendor/renderer комбинации
WEBGL_CONFIGS = [
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0)"),
    ("Apple Inc.", "Apple M1"),
    ("Google Inc.", "ANGLE (AMD Radeon Pro 5300M OpenGL Engine)"),
]

# Часовые пояса
TIMEZONES = [
    "Europe/Moscow",
    "Europe/Kiev",
    "Europe/Minsk",
    "Asia/Almaty",
    "Asia/Tashkent",
    "Europe/London",
    "America/New_York",
    "America/Los_Angeles",
]

# Языки
LANGUAGES = [
    "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-US,en;q=0.9,ru;q=0.8",
    "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
    "de-DE,de;q=0.9,en;q=0.8",
]


@dataclass
class Fingerprint:
    """Отпечаток браузера."""

    screen_resolution: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    languages: str
    timezone: str


class FingerprintGenerator:
    """Генератор случайных отпечатков браузера."""

    def generate(self) -> Fingerprint:
        """
        Сгенерировать случайный fingerprint.

        :return: Экземпляр Fingerprint
        """
        webgl = random.choice(WEBGL_CONFIGS)
        return Fingerprint(
            screen_resolution=random.choice(RESOLUTIONS),
            platform=random.choice(PLATFORMS),
            webgl_vendor=webgl[0],
            webgl_renderer=webgl[1],
            languages=random.choice(LANGUAGES),
            timezone=random.choice(TIMEZONES),
        )

    def apply_to_options(self, chrome_options, fingerprint: Fingerprint) -> None:
        """
        Применить fingerprint к Chrome options.

        :param chrome_options: Экземпляр ChromeOptions
        :param fingerprint: Экземпляр Fingerprint
        """
        # Устанавливаем размер окна
        chrome_options.add_argument(f"--window-size={fingerprint.screen_resolution}")

        # Язык
        lang_short = fingerprint.languages.split(",")[0].split(";")[0]
        chrome_options.add_argument(f"--lang={lang_short}")

        # Дополнительные аргументы для снижения детектируемости
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation"]
        )
        chrome_options.add_experimental_option("useAutomationExtension", False)

    def get_preset_for_device(self, device: str = "windows") -> Fingerprint:
        """
        Получить предустановленный fingerprint для типичного устройства.

        :param device: Тип устройства: "windows", "mac", "linux"
        :return: Fingerprint
        """
        presets = {
            "windows": Fingerprint(
                screen_resolution="1920,1080",
                platform="Win64",
                webgl_vendor="Google Inc. (NVIDIA)",
                webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
                languages="ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                timezone="Europe/Moscow",
            ),
            "mac": Fingerprint(
                screen_resolution="2560,1440",
                platform="MacIntel",
                webgl_vendor="Apple Inc.",
                webgl_renderer="Apple M2",
                languages="en-US,en;q=0.9,ru;q=0.8",
                timezone="America/New_York",
            ),
            "linux": Fingerprint(
                screen_resolution="1920,1080",
                platform="Linux x86_64",
                webgl_vendor="Google Inc. (Intel)",
                webgl_renderer="ANGLE (Intel, Mesa Intel(R) Iris(R) Xe Graphics, OpenGL 4.6)",
                languages="en-US,en;q=0.9",
                timezone="Europe/London",
            ),
        }
        return presets.get(device, self.generate())
