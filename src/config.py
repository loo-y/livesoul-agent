from __future__ import annotations

import copy
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

DEFAULT_CONFIG_FILENAME = "default_config.json"
RUNTIME_CONFIG_RELATIVE = Path("runtime/config.json")
LEGACY_ENV_FILENAME = ".env"
PROFILES_DIRNAME = "profiles"


def resolve_base_dir(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return base_dir
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _as_float(value: Any, default: float) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _as_int(value: Any, default: int) -> int:
    if value in (None, ""):
        return default
    return int(value)


def _as_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _as_bool(value: Any, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppConfig:
    active_profile_id: str
    profiles_dir: Path
    ocr_confidence_threshold: float
    vision_timeout_seconds: float
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
    tts_api_endpoint: str | None
    tts_voice: str
    tts_response_format: str
    tts_sample_rate: int
    tts_stream: bool
    tts_speed: float
    tts_gain: float
    tts_output_dir: Path
    memory_dir: Path
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

    @property
    def agent_config_dir(self) -> Path:
        return self.profiles_dir / self.active_profile_id


def _default_config_path(base_dir: Path) -> Path:
    return base_dir / DEFAULT_CONFIG_FILENAME


def _runtime_config_path(base_dir: Path) -> Path:
    return base_dir / RUNTIME_CONFIG_RELATIVE


def _legacy_env_path(base_dir: Path) -> Path:
    return base_dir / LEGACY_ENV_FILENAME


def _load_default_config(base_dir: Path) -> dict[str, Any]:
    path = _default_config_path(base_dir)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _migrate_legacy_env(base_dir: Path) -> dict[str, Any] | None:
    env_path = _legacy_env_path(base_dir)
    if not env_path.exists():
        return None

    env = dotenv_values(env_path)
    default_payload = _load_default_config(base_dir)
    migrated = copy.deepcopy(default_payload)

    capture = migrated.setdefault("capture", {})
    vision = migrated.setdefault("vision", {})
    llm = migrated.setdefault("llm", {})
    tts = migrated.setdefault("tts", {})
    runtime = migrated.setdefault("runtime", {})

    migrated["active_profile_id"] = "default"
    capture["ocr_confidence_threshold"] = _as_float(env.get("OCR_CONFIDENCE_THRESHOLD"), capture["ocr_confidence_threshold"])
    capture["vision_timeout_seconds"] = _as_float(env.get("VISION_TIMEOUT_SECONDS"), capture["vision_timeout_seconds"])
    capture["screenshot_interval"] = _as_float(env.get("SCREENSHOT_INTERVAL"), capture["screenshot_interval"])
    capture["auto_select_region"] = _as_bool(env.get("AUTO_SELECT_REGION"), capture["auto_select_region"])
    capture["screenshot_backend"] = env.get("SCREENSHOT_BACKEND") or capture["screenshot_backend"]
    capture["screenshot_monitor"] = _as_int(env.get("SCREENSHOT_MONITOR"), capture["screenshot_monitor"])
    capture["screenshot_image_path"] = env.get("SCREENSHOT_IMAGE_PATH") or ""
    capture["barrage_region"] = {
        "x": _as_optional_int(env.get("BARRAGE_REGION_X")),
        "y": _as_optional_int(env.get("BARRAGE_REGION_Y")),
        "w": _as_optional_int(env.get("BARRAGE_REGION_W")),
        "h": _as_optional_int(env.get("BARRAGE_REGION_H")),
    }

    vision["api_key"] = env.get("VISION_API_KEY") or ""
    vision["model"] = env.get("VISION_MODEL_NAME") or vision["model"]
    vision["api_base"] = env.get("VISION_API_BASE") or vision["api_base"]

    llm["api_key"] = env.get("LLM_API_KEY") or ""
    llm["model"] = env.get("LLM_MODEL_NAME") or llm["model"]
    llm["api_base"] = env.get("LLM_API_BASE") or llm["api_base"]

    tts["provider"] = (env.get("TTS_PROVIDER") or tts["provider"]).lower()
    tts["api_key"] = env.get("TTS_API_KEY") or ""
    tts["model"] = env.get("TTS_MODEL_NAME") or tts["model"]
    tts["api_endpoint"] = env.get("TTS_API_ENDPOINT") or env.get("TTS_API_BASE") or tts["api_endpoint"]
    tts["voice"] = env.get("TTS_VOICE") or tts["voice"]
    tts["response_format"] = env.get("TTS_RESPONSE_FORMAT") or tts["response_format"]
    tts["sample_rate"] = _as_int(env.get("TTS_SAMPLE_RATE"), tts["sample_rate"])
    tts["stream"] = _as_bool(env.get("TTS_STREAM"), tts["stream"])
    tts["speed"] = _as_float(env.get("TTS_SPEED"), tts["speed"])
    tts["gain"] = _as_float(env.get("TTS_GAIN"), tts["gain"])
    tts["output_dir"] = env.get("TTS_OUTPUT_DIR") or tts["output_dir"]

    runtime["memory_dir"] = env.get("MEMORY_DIR") or runtime["memory_dir"]
    runtime["log_level"] = (env.get("LOG_LEVEL") or runtime["log_level"]).upper()
    runtime["dedup_window_seconds"] = _as_int(env.get("DEDUP_WINDOW_SECONDS"), runtime["dedup_window_seconds"])
    runtime["queue_maxsize"] = _as_int(env.get("QUEUE_MAXSIZE"), runtime["queue_maxsize"])
    return migrated


def ensure_runtime_config(base_dir: Path | None = None) -> Path:
    base = resolve_base_dir(base_dir)
    runtime_path = _runtime_config_path(base)
    if runtime_path.exists():
        return runtime_path

    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _migrate_legacy_env(base)
    if payload is None:
        payload = _load_default_config(base)
    runtime_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return runtime_path


def load_settings(base_dir: Path | None = None) -> dict[str, Any]:
    base = resolve_base_dir(base_dir)
    runtime_path = ensure_runtime_config(base)
    payload = json.loads(runtime_path.read_text(encoding="utf-8-sig"))
    defaults = _load_default_config(base)
    return _deep_merge(defaults, payload)


def save_settings(payload: dict[str, Any], base_dir: Path | None = None) -> Path:
    base = resolve_base_dir(base_dir)
    runtime_path = _runtime_config_path(base)
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return runtime_path


def list_profiles(base_dir: Path | None = None) -> list[dict[str, str]]:
    base = resolve_base_dir(base_dir)
    profiles_dir = base / PROFILES_DIRNAME
    profiles: list[dict[str, str]] = []
    if not profiles_dir.exists():
        return profiles
    for path in sorted(profiles_dir.iterdir()):
        if not path.is_dir():
            continue
        meta_path = path / "meta.json"
        name = path.name
        description = ""
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                name = str(meta.get("name") or name)
                description = str(meta.get("description") or "")
            except Exception:
                pass
        profiles.append({"id": path.name, "name": name, "description": description})
    return profiles


def load_config(base_dir: Path | None = None) -> AppConfig:
    base = resolve_base_dir(base_dir)
    payload = load_settings(base)

    capture = payload.get("capture", {})
    vision = payload.get("vision", {})
    llm = payload.get("llm", {})
    tts = payload.get("tts", {})
    runtime = payload.get("runtime", {})
    region = capture.get("barrage_region", {})

    config = AppConfig(
        active_profile_id=str(payload.get("active_profile_id") or "default"),
        profiles_dir=base / PROFILES_DIRNAME,
        ocr_confidence_threshold=_as_float(capture.get("ocr_confidence_threshold"), 0.8),
        vision_timeout_seconds=_as_float(capture.get("vision_timeout_seconds"), 300.0),
        screenshot_interval=_as_float(capture.get("screenshot_interval"), 0.5),
        barrage_region_x=_as_optional_int(region.get("x")),
        barrage_region_y=_as_optional_int(region.get("y")),
        barrage_region_w=_as_optional_int(region.get("w")),
        barrage_region_h=_as_optional_int(region.get("h")),
        auto_select_region=_as_bool(capture.get("auto_select_region"), True),
        screenshot_backend=str(capture.get("screenshot_backend") or "auto").lower(),
        screenshot_monitor=_as_int(capture.get("screenshot_monitor"), 1),
        screenshot_image_path=(capture.get("screenshot_image_path") or None),
        vision_api_key=(vision.get("api_key") or None),
        vision_model_name=str(vision.get("model") or "gpt-4.1-mini"),
        vision_api_base=str(vision.get("api_base") or "https://api.openai.com/v1"),
        llm_api_key=(llm.get("api_key") or None),
        llm_model_name=str(llm.get("model") or "gpt-4.1-mini"),
        llm_api_base=str(llm.get("api_base") or "https://api.openai.com/v1"),
        tts_provider=str(tts.get("provider") or "console").lower(),
        tts_api_key=(tts.get("api_key") or None),
        tts_model_name=str(tts.get("model") or "gpt-4o-mini-tts"),
        tts_api_endpoint=(tts.get("api_endpoint") or None),
        tts_voice=str(tts.get("voice") or "alloy"),
        tts_response_format=str(tts.get("response_format") or "mp3"),
        tts_sample_rate=_as_int(tts.get("sample_rate"), 32000),
        tts_stream=_as_bool(tts.get("stream"), False),
        tts_speed=_as_float(tts.get("speed"), 1.0),
        tts_gain=_as_float(tts.get("gain"), 0.0),
        tts_output_dir=base / str(tts.get("output_dir") or "runtime/audio"),
        memory_dir=base / str(runtime.get("memory_dir") or "runtime/memory"),
        log_level=str(runtime.get("log_level") or "INFO").upper(),
        dedup_window_seconds=_as_int(runtime.get("dedup_window_seconds"), 8),
        queue_maxsize=_as_int(runtime.get("queue_maxsize"), 50),
    )
    config.tts_output_dir.mkdir(parents=True, exist_ok=True)
    config.memory_dir.mkdir(parents=True, exist_ok=True)
    return config


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
