from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import platform

from PIL import Image

from .config import AppConfig
from .models import FramePayload

logger = logging.getLogger(__name__)


class ScreenshotCapture:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.runtime_dir = Path("runtime/frames")
        self.region_state_path = Path("runtime/current_region.json")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

    async def capture_frame(self) -> FramePayload:
        return await asyncio.to_thread(self._capture_frame_sync)

    def _capture_frame_sync(self) -> FramePayload:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        frame_path = self.runtime_dir / f"{timestamp}.png"
        image = self._capture_image()
        cropped = self._crop_barrage_region(image)
        cropped.save(frame_path)
        return FramePayload(frame_id=timestamp, image_path=frame_path)

    def _capture_image(self) -> Image.Image:
        if self.config.screenshot_image_path:
            logger.debug("Loading screenshot from %s", self.config.screenshot_image_path)
            return Image.open(self.config.screenshot_image_path).convert("RGB")

        backend = self.config.screenshot_backend
        if backend in ("auto", "mss"):
            try:
                import mss

                with mss.mss() as sct:
                    shot = sct.grab(sct.monitors[self.config.screenshot_monitor])
                    return Image.frombytes("RGB", shot.size, shot.rgb)
            except Exception as exc:
                if backend == "mss":
                    raise RuntimeError(self._build_capture_error("mss screenshot failed", exc)) from exc
                logger.warning("mss capture unavailable, fallback to PIL.ImageGrab: %s", exc)

        try:
            from PIL import ImageGrab

            grabbed = ImageGrab.grab(all_screens=True)
            return grabbed.convert("RGB")
        except Exception as exc:
            raise RuntimeError(
                self._build_capture_error(
                    "No screenshot backend available. Configure SCREENSHOT_IMAGE_PATH for testing.",
                    exc,
                )
            ) from exc

    def _crop_barrage_region(self, image: Image.Image) -> Image.Image:
        self._refresh_region_from_runtime_state()
        region = self.config.barrage_region
        if region is None:
            raise RuntimeError("Barrage region is not configured.")
        x, y, w, h = region
        return image.crop((x, y, x + w, y + h))

    def _refresh_region_from_runtime_state(self) -> None:
        if not self.region_state_path.exists():
            return
        try:
            payload = json.loads(self.region_state_path.read_text(encoding="utf-8"))
            region = (
                int(payload["x"]),
                int(payload["y"]),
                int(payload["w"]),
                int(payload["h"]),
            )
        except Exception:
            return
        self.config.barrage_region_x = region[0]
        self.config.barrage_region_y = region[1]
        self.config.barrage_region_w = region[2]
        self.config.barrage_region_h = region[3]

    def _build_capture_error(self, message: str, exc: Exception) -> str:
        system = platform.system().lower()
        details = [message, f"Original error: {exc}"]
        if system == "darwin":
            details.append(
                "macOS hint: enable System Settings > Privacy & Security > Screen Recording for your terminal/Python app."
            )
        elif system == "windows":
            details.append(
                "Windows hint: ensure the mirrored iPhone/OBS window is visible and not minimized."
            )
        return " ".join(details)
