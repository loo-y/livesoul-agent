from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def _env_optional_int(name: str) -> int | None:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else None


@dataclass(slots=True)
class AppConfig:
    ocr_confidence_threshold: float
    screenshot_interval: float
    barrage_region_x: int | None
    barrage_region_y: int | None
    barrage_region_w: int | None
    barrage_region_h: int | None
    auto_select_region: bool
    screenshot_backend: str
    screenshot_monitor: int
    screenshot_image_path: str | None
    vision_api_key: str | None
    vision_model_name: str
    vision_api_base: str
    llm_api_key: str | None
    llm_model_name: str
    llm_api_base: str
    tts_provider: str
    tts_api_key: str | None
    tts_model_name: str
    tts_api_base: str
    tts_voice: str
    tts_output_dir: Path
    agent_config_dir: Path
    log_level: str
    dedup_window_seconds: int
    queue_maxsize: int

    @property
    def barrage_region(self) -> tuple[int, int, int, int] | None:
        if None in (
            self.barrage_region_x,
            self.barrage_region_y,
            self.barrage_region_w,
            self.barrage_region_h,
        ):
            return None
        return (
            self.barrage_region_x,
            self.barrage_region_y,
            self.barrage_region_w,
            self.barrage_region_h,
        )


def load_config(env_path: str | Path | None = None) -> AppConfig:
    if env_path is not None:
        load_dotenv(env_path)
    else:
        load_dotenv()

    base_dir = Path.cwd()
    config = AppConfig(
        ocr_confidence_threshold=_env_float("OCR_CONFIDENCE_THRESHOLD", 0.8),
        screenshot_interval=_env_float("SCREENSHOT_INTERVAL", 0.5),
        barrage_region_x=_env_optional_int("BARRAGE_REGION_X"),
        barrage_region_y=_env_optional_int("BARRAGE_REGION_Y"),
        barrage_region_w=_env_optional_int("BARRAGE_REGION_W"),
        barrage_region_h=_env_optional_int("BARRAGE_REGION_H"),
        auto_select_region=os.getenv("AUTO_SELECT_REGION", "true").lower() in {"1", "true", "yes"},
        screenshot_backend=os.getenv("SCREENSHOT_BACKEND", "auto").lower(),
        screenshot_monitor=_env_int("SCREENSHOT_MONITOR", 1),
        screenshot_image_path=os.getenv("SCREENSHOT_IMAGE_PATH") or None,
        vision_api_key=os.getenv("VISION_API_KEY") or None,
        vision_model_name=os.getenv("VISION_MODEL_NAME", "gpt-4.1-mini"),
        vision_api_base=os.getenv("VISION_API_BASE", "https://api.openai.com/v1"),
        llm_api_key=os.getenv("LLM_API_KEY") or None,
        llm_model_name=os.getenv("LLM_MODEL_NAME", "gpt-4.1-mini"),
        llm_api_base=os.getenv("LLM_API_BASE", "https://api.openai.com/v1"),
        tts_provider=os.getenv("TTS_PROVIDER", "console").lower(),
        tts_api_key=os.getenv("TTS_API_KEY") or None,
        tts_model_name=os.getenv("TTS_MODEL_NAME", "gpt-4o-mini-tts"),
        tts_api_base=os.getenv("TTS_API_BASE", "https://api.openai.com/v1"),
        tts_voice=os.getenv("TTS_VOICE", "alloy"),
        tts_output_dir=base_dir / os.getenv("TTS_OUTPUT_DIR", "runtime/audio"),
        agent_config_dir=base_dir / os.getenv("AGENT_CONFIG_DIR", "agent_config"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        dedup_window_seconds=_env_int("DEDUP_WINDOW_SECONDS", 8),
        queue_maxsize=_env_int("QUEUE_MAXSIZE", 50),
    )
    config.tts_output_dir.mkdir(parents=True, exist_ok=True)
    return config


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
