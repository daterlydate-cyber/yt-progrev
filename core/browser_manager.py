"""
Модуль управления браузерами и профилями (антидетект).
Создаёт изолированные экземпляры undetected-chromedriver для каждого профиля.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

from utils.fingerprint import Fingerprint

logger = logging.getLogger(__name__)


class BrowserManager:
    """Управляет браузерными сессиями с изолированными профилями."""

    def __init__(self) -> None:
        # Словарь активных сессий: {profile_name: driver}
        self._sessions: Dict[str, uc.Chrome] = {}

    def create_browser(
        self,
        profile_name: str,
        proxy: Optional[str] = None,
        headless: bool = False,
        window_size: str = "1280,720",
        language: str = "ru-RU",
        user_agent: Optional[str] = None,
        fingerprint: Optional[Fingerprint] = None,
    ) -> uc.Chrome:
        """
        Создать экземпляр браузера с изолированным профилем.

        :param profile_name: Имя профиля (используется как имя папки)
        :param proxy: Строка прокси вида protocol://[user:pass@]host:port
        :param headless: Запустить браузер в фоновом режиме
        :param window_size: Размер окна браузера (ширина,высота)
        :param language: Язык интерфейса браузера
        :param user_agent: User-Agent строка (если None — дефолтный)
        :param fingerprint: Экземпляр Fingerprint для подмены цифрового отпечатка
        :return: Экземпляр undetected-chromedriver
        """
        if profile_name in self._sessions:
            logger.warning(
                "Браузер для профиля '%s' уже запущен, возвращаем существующий.",
                profile_name,
            )
            return self._sessions[profile_name]

        # Папка с данными Chrome для профиля
        profile_dir = Path("data/profiles") / profile_name / "chrome_data"
        profile_dir.mkdir(parents=True, exist_ok=True)

        options = uc.ChromeOptions()

        # Изолированный user-data-dir
        options.add_argument(f"--user-data-dir={profile_dir.resolve()}")

        # Подмена fingerprint и снижение детектируемости
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        if fingerprint:
            options.add_argument(f"--window-size={fingerprint.screen_resolution}")
            lang_short = fingerprint.languages.split(",")[0].split(";")[0]
            options.add_argument(f"--lang={lang_short}")
        else:
            options.add_argument(f"--window-size={window_size}")
            options.add_argument(f"--lang={language}")

        if headless:
            options.add_argument("--headless=new")

        if user_agent:
            options.add_argument(f"--user-agent={user_agent}")

        if proxy:
            formatted_proxy = self._format_proxy(proxy)
            if formatted_proxy:
                options.add_argument(f"--proxy-server={formatted_proxy}")
                logger.debug("Используем прокси: %s", formatted_proxy)

        try:
            driver = uc.Chrome(options=options, use_subprocess=True)

            if fingerprint:
                self._apply_fingerprint_via_cdp(driver, fingerprint)

            self._sessions[profile_name] = driver
            logger.info("Браузер для профиля '%s' успешно запущен.", profile_name)
            return driver
        except Exception as exc:
            logger.error(
                "Ошибка при создании браузера для профиля '%s': %s",
                profile_name,
                exc,
            )
            raise

    def _apply_fingerprint_via_cdp(self, driver: uc.Chrome, fingerprint: Fingerprint) -> None:
        """
        Применить fingerprint через Chrome DevTools Protocol (CDP).

        Инжектирует скрипты для подмены navigator свойств, WebGL, Canvas и AudioContext.

        :param driver: Экземпляр undetected-chromedriver
        :param fingerprint: Экземпляр Fingerprint
        """
        # Применяем переопределение часового пояса
        try:
            driver.execute_cdp_cmd(
                "Emulation.setTimezoneOverride",
                {"timezoneId": fingerprint.timezone},
            )
        except Exception as exc:
            logger.debug("Не удалось установить часовой пояс через CDP: %s", exc)

        # Формируем JS-скрипт для подмены navigator и других свойств
        fonts_json = json.dumps(fingerprint.fonts)
        dnt_value = "1" if fingerprint.do_not_track else "0"

        js_script = f"""
(function() {{
    // Подмена navigator.platform
    Object.defineProperty(navigator, 'platform', {{
        get: () => '{fingerprint.platform}',
        configurable: true,
    }});

    // Подмена navigator.hardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: () => {fingerprint.hardware_concurrency},
        configurable: true,
    }});

    // Подмена navigator.deviceMemory
    Object.defineProperty(navigator, 'deviceMemory', {{
        get: () => {fingerprint.device_memory},
        configurable: true,
    }});

    // Подмена navigator.language / navigator.languages
    Object.defineProperty(navigator, 'language', {{
        get: () => '{fingerprint.languages.split(",")[0].split(";")[0]}',
        configurable: true,
    }});
    Object.defineProperty(navigator, 'languages', {{
        get: () => {json.dumps([l.split(";")[0] for l in fingerprint.languages.split(",")])},
        configurable: true,
    }});

    // Подмена navigator.doNotTrack
    Object.defineProperty(navigator, 'doNotTrack', {{
        get: () => '{dnt_value}',
        configurable: true,
    }});

    // Подмена navigator.maxTouchPoints
    Object.defineProperty(navigator, 'maxTouchPoints', {{
        get: () => {fingerprint.touch_points},
        configurable: true,
    }});

    // Подмена screen
    Object.defineProperty(screen, 'colorDepth', {{
        get: () => {fingerprint.color_depth},
        configurable: true,
    }});
    Object.defineProperty(screen, 'pixelDepth', {{
        get: () => {fingerprint.color_depth},
        configurable: true,
    }});

    // Подмена devicePixelRatio
    Object.defineProperty(window, 'devicePixelRatio', {{
        get: () => {fingerprint.pixel_ratio},
        configurable: true,
    }});

    // Подмена WebGL vendor/renderer
    const getParameterOrig = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return '{fingerprint.webgl_vendor}';
        if (parameter === 37446) return '{fingerprint.webgl_renderer}';
        return getParameterOrig.call(this, parameter);
    }};
    const getParameter2Orig = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return '{fingerprint.webgl_vendor}';
        if (parameter === 37446) return '{fingerprint.webgl_renderer}';
        return getParameter2Orig.call(this, parameter);
    }};

    // Canvas noise (добавляем шум только к части пикселей для снижения нагрузки)
    const canvasNoise = {fingerprint.canvas_noise_level};
    if (canvasNoise > 0) {{
        const toDataURLOrig = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                const imgData = ctx.getImageData(0, 0, this.width, this.height);
                const step = Math.max(1, Math.floor(imgData.data.length / (4 * 64)));
                for (let i = 0; i < imgData.data.length; i += 4 * step) {{
                    imgData.data[i]     = Math.max(0, Math.min(255, imgData.data[i]     + Math.round((Math.random() - 0.5) * canvasNoise * 4)));
                    imgData.data[i + 1] = Math.max(0, Math.min(255, imgData.data[i + 1] + Math.round((Math.random() - 0.5) * canvasNoise * 4)));
                    imgData.data[i + 2] = Math.max(0, Math.min(255, imgData.data[i + 2] + Math.round((Math.random() - 0.5) * canvasNoise * 4)));
                }}
                ctx.putImageData(imgData, 0, 0);
            }}
            return toDataURLOrig.apply(this, arguments);
        }};
    }}

    // AudioContext noise
    const audioNoise = {fingerprint.audio_context_noise};
    if (audioNoise > 0) {{
        const origGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function() {{
            const arr = origGetChannelData.apply(this, arguments);
            for (let i = 0; i < arr.length; i++) {{
                arr[i] = arr[i] + (Math.random() - 0.5) * audioNoise * 0.0001;
            }}
            return arr;
        }};
    }}

    // Удаляем признаки автоматизации
    Object.defineProperty(navigator, 'webdriver', {{
        get: () => undefined,
        configurable: true,
    }});

    // Подмена navigator.plugins (имитируем обычный браузер)
    if (navigator.plugins.length === 0) {{
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{ name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
                {{ name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }},
                {{ name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }},
            ],
        }});
    }}
}})();
"""

        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": js_script},
            )
            logger.debug(
                "CDP fingerprint применён для платформы %s, GPU: %s",
                fingerprint.platform,
                fingerprint.webgl_renderer[:50],
            )
        except Exception as exc:
            logger.warning("Не удалось применить CDP fingerprint: %s", exc)

    def close_browser(self, profile_name: str) -> None:
        """
        Закрыть браузер для указанного профиля.

        :param profile_name: Имя профиля
        """
        driver = self._sessions.get(profile_name)
        if driver is None:
            logger.warning(
                "Браузер для профиля '%s' не найден.", profile_name
            )
            return
        try:
            driver.quit()
            logger.info("Браузер профиля '%s' закрыт.", profile_name)
        except Exception as exc:
            logger.error(
                "Ошибка при закрытии браузера '%s': %s", profile_name, exc
            )
        finally:
            del self._sessions[profile_name]

    def close_all(self) -> None:
        """Закрыть все активные браузерные сессии."""
        for name in list(self._sessions.keys()):
            self.close_browser(name)

    def get_driver(self, profile_name: str) -> Optional[uc.Chrome]:
        """
        Получить активный драйвер по имени профиля.

        :param profile_name: Имя профиля
        :return: Экземпляр драйвера или None
        """
        return self._sessions.get(profile_name)

    def list_active_sessions(self) -> list[str]:
        """
        Получить список имён активных сессий.

        :return: Список имён профилей с активными браузерами
        """
        return list(self._sessions.keys())

    @staticmethod
    def _format_proxy(proxy_str: str) -> Optional[str]:
        """
        Форматировать строку прокси для аргумента --proxy-server Chrome.

        :param proxy_str: Строка прокси
        :return: Отформатированная строка или None при ошибке
        """
        try:
            # Chrome принимает proxy-server без указания протокола для auth
            if "://" in proxy_str:
                protocol, rest = proxy_str.split("://", 1)
                if "@" in rest:
                    # Для Chrome прокси с авторизацией формируем только host:port
                    # авторизация задаётся через расширение или отдельный обработчик
                    credentials, host_port = rest.rsplit("@", 1)
                    return f"{protocol}://{host_port}"
                return proxy_str
            return proxy_str
        except Exception as exc:
            logger.error("Ошибка форматирования прокси '%s': %s", proxy_str, exc)
            return None
