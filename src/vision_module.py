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

    def _load_vision_prompt(self) -> str:
        path = self.config.agent_config_dir / "VISION_PROMPT.md"
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return (
                "Read the live-stream chat text from this image. "
                "Return only the readable chat content, one message per line. "
                "If there is no readable chat text, return an empty string."
            )

    def _recognize_sync(self, image_path: Path) -> tuple[str, float]:
        image_bytes = image_path.read_bytes()
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        vision_prompt = self._load_vision_prompt()
        response = self.client.responses.create(
            model=self.config.vision_model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": vision_prompt,
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
        if self._looks_like_no_text_response(text):
            return "", 0.0
        confidence = 0.65 if text else 0.0
        return text, confidence

    def _looks_like_no_text_response(self, text: str) -> bool:
        normalized = text.strip().lower()
        if not normalized:
            return True
        phrases = (
            "no readable",
            "no visible text",
            "contains no visible text",
            "contains no readable text",
            "appears to be blank",
            "completely blank",
            "completely white",
            "blank/white",
            "empty string",
            "no chat content",
        )
        return any(phrase in normalized for phrase in phrases)
