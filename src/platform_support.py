from __future__ import annotations

import importlib.util
import logging
import platform
import shutil

from .config import AppConfig

logger = logging.getLogger(__name__)


class PlatformSupportChecker:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.system = platform.system().lower()

    def log_runtime_summary(self) -> None:
        logger.info("Platform: %s", platform.platform())
        logger.info("Screenshot backend preference: %s", self.config.screenshot_backend)
        logger.info("TTS provider: %s", self.config.tts_provider)

    def run_startup_checks(self) -> None:
        self.log_runtime_summary()
        self._check_screen_capture_setup()
        self._check_region_selector_setup()
        self._check_ocr_setup()
        self._check_tts_setup()

    def _check_screen_capture_setup(self) -> None:
        if self.config.screenshot_image_path:
            logger.info("Static image mode enabled: %s", self.config.screenshot_image_path)
            return

        if self.system == "darwin":
            logger.info(
                "macOS requires Screen Recording permission. If capture fails, enable it in "
                "System Settings > Privacy & Security > Screen Recording."
            )
        elif self.system == "windows":
            logger.info("Windows capture mode is active. Use your mirrored iPhone/OBS window on screen.")
        else:
            logger.info("Non-macOS/Windows environment detected. Screen capture compatibility may vary.")

        if self.config.screenshot_backend in {"auto", "mss"}:
            if importlib.util.find_spec("mss") is None:
                logger.warning("`mss` is not installed. Screen capture will fall back to PIL.ImageGrab.")

    def _check_region_selector_setup(self) -> None:
        if not self.config.auto_select_region:
            return
        if self.config.screenshot_image_path:
            logger.warning(
                "AUTO_SELECT_REGION is enabled but SCREENSHOT_IMAGE_PATH is set. "
                "Interactive selection will be skipped."
            )
            return
        if importlib.util.find_spec("tkinter") is None:
            logger.warning(
                "`tkinter` is unavailable. Interactive region selection will fail. "
                "Install a Python build with Tk support or disable AUTO_SELECT_REGION."
            )

    def _check_ocr_setup(self) -> None:
        has_easyocr = importlib.util.find_spec("easyocr") is not None
        has_pytesseract = importlib.util.find_spec("pytesseract") is not None

        if not has_easyocr and not has_pytesseract:
            logger.warning(
                "No OCR library detected. Install EasyOCR or pytesseract, otherwise only vision fallback can work."
            )

        if has_pytesseract and shutil.which("tesseract") is None:
            logger.warning(
                "`pytesseract` is installed but the `tesseract` binary was not found in PATH."
            )
            if self.system == "darwin":
                logger.info("On macOS, install it with `brew install tesseract tesseract-lang`.")

    def _check_tts_setup(self) -> None:
        provider = self.config.tts_provider
        if provider == "console":
            logger.info("Console TTS mode enabled; replies will only be logged.")
            return
        if provider == "edge" and importlib.util.find_spec("edge_tts") is None:
            logger.warning("TTS provider `edge` selected but `edge-tts` is not installed.")
        if provider == "pyttsx3" and importlib.util.find_spec("pyttsx3") is None:
            logger.warning("TTS provider `pyttsx3` selected but `pyttsx3` is not installed.")
        if provider == "openai" and not self.config.tts_api_key:
            logger.warning("TTS provider `openai` selected but TTS_API_KEY is missing.")
