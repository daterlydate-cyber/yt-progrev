"""
Генерация и применение отпечатков браузера (fingerprint).
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


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
    "1680,1050",
    "2560,1600",
    "3440,1440",
    "3840,2160",
    "1024,768",
    "1152,864",
    "1360,768",
    "1600,1200",
    "2048,1152",
    "2560,1080",
    "1920,1200",
    "1280,1024",
    "1400,1050",
    "1920,1440",
    "2560,1600",
    "3200,1800",
    "1800,1200",
    "1440,960",
    "2304,1440",
    "2880,1800",
]

# Платформы
PLATFORMS = [
    "Win32",
    "Win64",
    "MacIntel",
    "Linux x86_64",
    "Linux armv7l",
    "Linux aarch64",
]

# WebGL vendor/renderer комбинации
WEBGL_CONFIGS: List[Tuple[str, str]] = [
    # NVIDIA GTX серия
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1070 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)"),
    # NVIDIA RTX серия
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2080 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3050 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0)"),
    # Intel GPU
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 730 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Plus Graphics Direct3D11 vs_5_0 ps_5_0)"),
    # AMD GPU
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 570 Series Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 590 Series Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 5500 XT Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 5600 XT Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 5700 XT Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 6800 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0)"),
    # Apple Silicon
    ("Apple Inc.", "Apple M1"),
    ("Apple Inc.", "Apple M1 Pro"),
    ("Apple Inc.", "Apple M1 Max"),
    ("Apple Inc.", "Apple M2"),
    ("Apple Inc.", "Apple M2 Pro"),
    ("Apple Inc.", "Apple M3"),
    ("Apple Inc.", "Apple M3 Pro"),
    # Linux Mesa
    ("Google Inc. (Intel)", "ANGLE (Intel, Mesa Intel(R) Iris(R) Xe Graphics, OpenGL 4.6)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630, OpenGL 4.6)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Mesa AMD Radeon RX 5700 XT (NAVI10 DRM 3.46.0), OpenGL 4.6)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, Mesa AMD Radeon RX 580 (POLARIS10 DRM 3.40.0), OpenGL 4.6)"),
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
    "America/Chicago",
    "America/Denver",
    "America/Toronto",
    "America/Sao_Paulo",
    "Europe/Berlin",
    "Europe/Paris",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Warsaw",
    "Europe/Prague",
    "Europe/Stockholm",
    "Europe/Amsterdam",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Asia/Shanghai",
    "Asia/Singapore",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Australia/Sydney",
    "Pacific/Auckland",
    "Africa/Cairo",
]

# Языки
LANGUAGES = [
    "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-US,en;q=0.9,ru;q=0.8",
    "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
    "de-DE,de;q=0.9,en;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "pt-BR,pt;q=0.9,en;q=0.8",
    "it-IT,it;q=0.9,en;q=0.8",
    "ja-JP,ja;q=0.9,en;q=0.8",
    "ko-KR,ko;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9,en;q=0.8",
    "pl-PL,pl;q=0.9,en;q=0.8",
    "tr-TR,tr;q=0.9,en;q=0.8",
    "nl-NL,nl;q=0.9,en;q=0.8",
    "sv-SE,sv;q=0.9,en;q=0.8",
    "cs-CZ,cs;q=0.9,en;q=0.8",
    "ar-SA,ar;q=0.9,en;q=0.8",
    "hi-IN,hi;q=0.9,en;q=0.8",
    "en-GB,en;q=0.9",
    "en-AU,en;q=0.9",
]

# Шрифты по платформам
FONTS_WINDOWS = [
    "Arial", "Arial Black", "Calibri", "Cambria", "Comic Sans MS",
    "Consolas", "Courier New", "Georgia", "Impact", "Lucida Console",
    "Lucida Sans Unicode", "Microsoft Sans Serif", "Palatino Linotype",
    "Segoe UI", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
    "Wingdings", "Wingdings 2", "Wingdings 3", "Symbol",
    "Franklin Gothic Medium", "Garamond", "Gill Sans MT", "Haettenschweiler",
]

FONTS_MAC = [
    "Arial", "Arial Black", "Courier New", "Georgia", "Helvetica",
    "Helvetica Neue", "Impact", "Lucida Grande", "Times New Roman",
    "Trebuchet MS", "Verdana", "American Typewriter", "Andale Mono",
    "Apple Chancery", "Apple Color Emoji", "AppleGothic", "AppleMyungjo",
    "Baskerville", "BigCaslon", "BrushScriptMT", "Chalkboard", "Cochin",
    "Copperplate", "Didot", "Futura", "Geneva", "Gill Sans",
    "Hoefler Text", "Marker Felt", "Menlo", "Monaco", "Optima",
    "Palatino", "Papyrus", "Skia", "Zapf Chancery",
]

FONTS_LINUX = [
    "Arial", "Courier New", "DejaVu Sans", "DejaVu Sans Mono",
    "DejaVu Serif", "FreeMonospace", "FreeSans", "FreeSerif",
    "Georgia", "Liberation Mono", "Liberation Sans", "Liberation Serif",
    "Nimbus Mono L", "Nimbus Roman No9 L", "Nimbus Sans L",
    "Times New Roman", "Trebuchet MS", "Ubuntu", "Ubuntu Mono",
    "Verdana",
]

# Значения hardware concurrency
HARDWARE_CONCURRENCY_VALUES = [2, 4, 6, 8, 10, 12, 16, 24, 32]

# Значения device memory (GB)
DEVICE_MEMORY_VALUES = [2, 4, 8, 16, 32]


@dataclass
class Fingerprint:
    """Расширенный отпечаток браузера."""

    screen_resolution: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    languages: str
    timezone: str
    fonts: List[str] = field(default_factory=list)
    canvas_noise_level: float = 0.1
    audio_context_noise: float = 0.05
    hardware_concurrency: int = 4
    device_memory: int = 8
    do_not_track: bool = False
    touch_points: int = 0
    color_depth: int = 24
    pixel_ratio: float = 1.0


# Предустановленные конфиги (пресеты)
PRESET_CONFIGS: Dict[str, dict] = {
    "windows_gamer": {
        "description": "Windows геймерский ПК",
        "screen_resolutions": ["1920,1080", "2560,1440"],
        "platform": "Win64",
        "webgl_configs": [
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)"),
        ],
        "languages": ["ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7", "en-US,en;q=0.9"],
        "timezones": ["Europe/Moscow", "Europe/Kiev", "Europe/Minsk"],
        "hardware_concurrency": [8, 12],
        "device_memory": [16],
        "fonts": FONTS_WINDOWS,
        "pixel_ratio": [1.0],
        "color_depth": 24,
    },
    "windows_office": {
        "description": "Windows офисный компьютер",
        "screen_resolutions": ["1920,1080", "1366,768", "1600,900"],
        "platform": "Win64",
        "webgl_configs": [
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)"),
        ],
        "languages": ["ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"],
        "timezones": ["Europe/Moscow", "Europe/Kiev"],
        "hardware_concurrency": [4],
        "device_memory": [8],
        "fonts": FONTS_WINDOWS,
        "pixel_ratio": [1.0],
        "color_depth": 24,
    },
    "macbook_pro": {
        "description": "MacBook Pro (M2/M3)",
        "screen_resolutions": ["2560,1600"],
        "platform": "MacIntel",
        "webgl_configs": [
            ("Apple Inc.", "Apple M2 Pro"),
            ("Apple Inc.", "Apple M3 Pro"),
            ("Apple Inc.", "Apple M3"),
        ],
        "languages": ["en-US,en;q=0.9", "ru-RU,ru;q=0.9,en-US;q=0.8"],
        "timezones": ["America/New_York", "America/Los_Angeles", "America/Chicago", "Europe/London"],
        "hardware_concurrency": [10, 12],
        "device_memory": [16, 32],
        "fonts": FONTS_MAC,
        "pixel_ratio": [2.0],
        "color_depth": 24,
    },
    "macbook_air": {
        "description": "MacBook Air (M1/M2)",
        "screen_resolutions": ["2560,1600"],
        "platform": "MacIntel",
        "webgl_configs": [
            ("Apple Inc.", "Apple M1"),
            ("Apple Inc.", "Apple M2"),
        ],
        "languages": ["en-US,en;q=0.9", "ru-RU,ru;q=0.9,en-US;q=0.8"],
        "timezones": ["America/New_York", "America/Los_Angeles", "Europe/London"],
        "hardware_concurrency": [8],
        "device_memory": [8, 16],
        "fonts": FONTS_MAC,
        "pixel_ratio": [2.0],
        "color_depth": 24,
    },
    "linux_developer": {
        "description": "Linux рабочая станция разработчика",
        "screen_resolutions": ["1920,1080", "2560,1440"],
        "platform": "Linux x86_64",
        "webgl_configs": [
            ("Google Inc. (Intel)", "ANGLE (Intel, Mesa Intel(R) Iris(R) Xe Graphics, OpenGL 4.6)"),
            ("Google Inc. (Intel)", "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630, OpenGL 4.6)"),
            ("Google Inc. (AMD)", "ANGLE (AMD, Mesa AMD Radeon RX 5700 XT (NAVI10 DRM 3.46.0), OpenGL 4.6)"),
        ],
        "languages": ["en-US,en;q=0.9", "de-DE,de;q=0.9,en;q=0.8"],
        "timezones": ["Europe/Berlin", "Europe/London", "America/New_York"],
        "hardware_concurrency": [8, 16],
        "device_memory": [16, 32],
        "fonts": FONTS_LINUX,
        "pixel_ratio": [1.0, 1.25],
        "color_depth": 24,
    },
    "old_laptop": {
        "description": "Старый ноутбук",
        "screen_resolutions": ["1366,768", "1280,720"],
        "platform": "Win64",
        "webgl_configs": [
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Plus Graphics Direct3D11 vs_5_0 ps_5_0)"),
        ],
        "languages": ["ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"],
        "timezones": ["Europe/Moscow", "Europe/Kiev", "Asia/Almaty"],
        "hardware_concurrency": [2, 4],
        "device_memory": [4, 8],
        "fonts": FONTS_WINDOWS,
        "pixel_ratio": [1.0],
        "color_depth": 24,
    },
    "high_end_desktop": {
        "description": "Топовый десктоп",
        "screen_resolutions": ["3840,2160", "2560,1440"],
        "platform": "Win64",
        "webgl_configs": [
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 Direct3D11 vs_5_0 ps_5_0)"),
        ],
        "languages": ["en-US,en;q=0.9", "ru-RU,ru;q=0.9,en-US;q=0.8"],
        "timezones": ["America/New_York", "America/Los_Angeles", "Europe/London"],
        "hardware_concurrency": [16, 24],
        "device_memory": [32],
        "fonts": FONTS_WINDOWS,
        "pixel_ratio": [1.0, 1.5],
        "color_depth": 24,
    },
    "mid_range_desktop": {
        "description": "Середнячок десктоп",
        "screen_resolutions": ["1920,1080", "1440,900"],
        "platform": "Win64",
        "webgl_configs": [
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 5700 XT Direct3D11 vs_5_0 ps_5_0)"),
        ],
        "languages": ["ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7", "en-US,en;q=0.9"],
        "timezones": ["Europe/Moscow", "Europe/Kiev", "Europe/Berlin"],
        "hardware_concurrency": [8, 12],
        "device_memory": [16],
        "fonts": FONTS_WINDOWS,
        "pixel_ratio": [1.0],
        "color_depth": 24,
    },
    "eastern_europe_user": {
        "description": "Пользователь из Восточной Европы",
        "screen_resolutions": ["1920,1080", "1366,768", "1600,900"],
        "platform": "Win64",
        "webgl_configs": [
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0)"),
        ],
        "languages": ["uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7", "pl-PL,pl;q=0.9,en;q=0.8", "cs-CZ,cs;q=0.9,en;q=0.8"],
        "timezones": ["Europe/Kiev", "Europe/Warsaw", "Europe/Prague"],
        "hardware_concurrency": [4, 8],
        "device_memory": [8, 16],
        "fonts": FONTS_WINDOWS,
        "pixel_ratio": [1.0],
        "color_depth": 24,
    },
}


class FingerprintGenerator:
    """Генератор случайных отпечатков браузера с поддержкой пресетов."""

    def generate(self) -> Fingerprint:
        """
        Сгенерировать случайный fingerprint.

        :return: Экземпляр Fingerprint
        """
        webgl = random.choice(WEBGL_CONFIGS)
        platform = random.choice(PLATFORMS)
        fonts = self._get_fonts_for_platform(platform)
        return Fingerprint(
            screen_resolution=random.choice(RESOLUTIONS),
            platform=platform,
            webgl_vendor=webgl[0],
            webgl_renderer=webgl[1],
            languages=random.choice(LANGUAGES),
            timezone=random.choice(TIMEZONES),
            fonts=random.sample(fonts, min(len(fonts), random.randint(15, 25))),
            canvas_noise_level=round(random.uniform(0.05, 0.3), 3),
            audio_context_noise=round(random.uniform(0.01, 0.1), 3),
            hardware_concurrency=random.choice(HARDWARE_CONCURRENCY_VALUES),
            device_memory=random.choice(DEVICE_MEMORY_VALUES),
            do_not_track=random.choice([True, False]),
            touch_points=0,
            color_depth=random.choice([24, 32]),
            pixel_ratio=random.choice([1.0, 1.25, 1.5, 2.0]),
        )

    def generate_realistic(self) -> Fingerprint:
        """
        Сгенерировать реалистичный консистентный fingerprint.

        Параметры подбираются совместимыми: платформа + GPU + разрешение + RAM + ядра.

        :return: Экземпляр Fingerprint с согласованными параметрами
        """
        preset_name = random.choice(list(PRESET_CONFIGS.keys()))
        return self.get_preset(preset_name)

    def get_preset_names(self) -> List[str]:
        """
        Получить список имён доступных пресетов.

        :return: Список строк с именами пресетов
        """
        return list(PRESET_CONFIGS.keys())

    def get_preset(self, name: str) -> Fingerprint:
        """
        Получить пресетный fingerprint по имени.

        :param name: Имя пресета из PRESET_CONFIGS
        :return: Экземпляр Fingerprint
        :raises KeyError: Если пресет не найден
        """
        if name not in PRESET_CONFIGS:
            raise KeyError(f"Пресет '{name}' не найден. Доступные: {list(PRESET_CONFIGS.keys())}")

        cfg = PRESET_CONFIGS[name]
        webgl = random.choice(cfg["webgl_configs"])
        fonts = cfg["fonts"]
        return Fingerprint(
            screen_resolution=random.choice(cfg["screen_resolutions"]),
            platform=cfg["platform"],
            webgl_vendor=webgl[0],
            webgl_renderer=webgl[1],
            languages=random.choice(cfg["languages"]),
            timezone=random.choice(cfg["timezones"]),
            fonts=random.sample(fonts, min(len(fonts), random.randint(15, 25))),
            canvas_noise_level=round(random.uniform(0.05, 0.2), 3),
            audio_context_noise=round(random.uniform(0.01, 0.08), 3),
            hardware_concurrency=random.choice(cfg["hardware_concurrency"]),
            device_memory=random.choice(cfg["device_memory"]),
            do_not_track=random.choice([True, False]),
            touch_points=0,
            color_depth=cfg["color_depth"],
            pixel_ratio=random.choice(cfg["pixel_ratio"]),
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

    @staticmethod
    def _get_fonts_for_platform(platform: str) -> List[str]:
        """
        Получить список шрифтов для указанной платформы.

        :param platform: Строка платформы
        :return: Список шрифтов
        """
        if platform.startswith("Mac"):
            return FONTS_MAC
        if platform.startswith("Linux"):
            return FONTS_LINUX
        return FONTS_WINDOWS

    def get_preset_for_device(self, device: str = "windows") -> Fingerprint:
        """
        Получить предустановленный fingerprint для типичного устройства.

        :param device: Тип устройства: "windows", "mac", "linux"
        :return: Fingerprint
        """
        device_map = {
            "windows": "windows_office",
            "mac": "macbook_pro",
            "linux": "linux_developer",
        }
        preset_name = device_map.get(device, "windows_office")
        return self.get_preset(preset_name)
