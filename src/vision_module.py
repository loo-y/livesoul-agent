from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path

from .config import AppConfig

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


class VisionModule:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = (
            OpenAI(api_key=config.vision_api_key, base_url=config.vision_api_base)
            if config.vision_api_key and OpenAI is not None
            else None
        )

    async def recognize(self, image_path: Path) -> tuple[str, float]:
        if self.client is None:
            logger.info("Vision client unavailable; skipping visual fallback.")
            return "", 0.0
        return await asyncio.to_thread(self._recognize_sync, image_path)

    def _recognize_sync(self, image_path: Path) -> tuple[str, float]:
        image_bytes = image_path.read_bytes()
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = self.client.responses.create(
            model=self.config.vision_model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Read the live-stream chat text from this image. "
                                "Return only the readable chat content, one message per line."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{b64}",
                        },
                    ],
                }
            ],
        )
        text = response.output_text.strip()
        confidence = 0.65 if text else 0.0
        return text, confidence
