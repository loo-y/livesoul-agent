from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .config import AppConfig

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


class SoulStore:
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir

    def load_prompt(self) -> str:
        parts = []
        for filename in ("SOUL.md", "IDENTITY.md", "USER.md"):
            path = self.config_dir / filename
            try:
                content = path.read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                content = f"{filename} is missing."
            parts.append(f"## {filename}\n{content}")
        return "\n\n".join(parts)


class AIAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.soul_store = SoulStore(config.agent_config_dir)
        self.client = (
            OpenAI(api_key=config.llm_api_key, base_url=config.llm_api_base)
            if config.llm_api_key and OpenAI is not None
            else None
        )

    async def generate_reply(self, barrage_text: str) -> str:
        soul_prompt = self.soul_store.load_prompt()
        if self.client is None:
            return self._fallback_reply(barrage_text)
        return await asyncio.to_thread(self._generate_reply_sync, soul_prompt, barrage_text)

    def _generate_reply_sync(self, soul_prompt: str, barrage_text: str) -> str:
        response = self.client.responses.create(
            model=self.config.llm_model_name,
            input=[
                {
                    "role": "system",
                    "content": (
                        f"{soul_prompt}\n\n"
                        "Generate one short spoken reply for the live stream. "
                        "Keep it concise, safe, and natural for voice output."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Latest barrage text:\n{barrage_text}",
                },
            ],
        )
        return response.output_text.strip()

    def _fallback_reply(self, barrage_text: str) -> str:
        preview = barrage_text.replace("\n", " ").strip()
        if not preview:
            return "这条弹幕我没看清，再发一次我就接上。"
        preview = preview[:60]
        return f"我看到弹幕在聊：{preview}。这个话题可以继续展开说说。"
