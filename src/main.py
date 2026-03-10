from __future__ import annotations

import asyncio
import json
import logging
import signal
from collections import deque
from contextlib import suppress
from datetime import datetime, timezone
from html import escape

from .ai_agent import AIAgent
from .config import load_config, setup_logging
from .hotkey_listener import GlobalHotkeyListener
from .models import FramePayload
from .ocr_module import OCRModule
from .platform_support import PlatformSupportChecker
from .region_selector import RegionSelector
from .screenshot import ScreenshotCapture
from .tts_module import TTSModule
from .vision_module import VisionModule

logger = logging.getLogger(__name__)


class LiveSoulRuntime:
    def __init__(self) -> None:
        self.config = load_config()
        setup_logging(self.config.log_level)
        self.support_checker = PlatformSupportChecker(self.config)
        self.support_checker.run_startup_checks()
        self._prepare_barrage_region()
        self.capture = ScreenshotCapture(self.config)
        self.ocr = OCRModule()
        self.vision = VisionModule(self.config)
        self.agent = AIAgent(self.config)
        self.tts = TTSModule(self.config)
        self.stop_event = asyncio.Event()
        self.hotkey_listener = GlobalHotkeyListener(self.stop_event.set)
        self.last_recognized_text = ""
        self.dialogue_history: deque[tuple[str, str]] = deque(maxlen=4)
        self.memory_json_path = self.config.memory_dir / "session_memory.json"
        self.memory_html_path = self.config.memory_dir / "session_memory.html"
        self._load_memory()

    def _prepare_barrage_region(self) -> None:
        if self.config.auto_select_region:
            selector = RegionSelector(self.config)
            selector.select_region()
            return
        if self.config.barrage_region is None:
            raise RuntimeError(
                "Barrage region is not configured. Set BARRAGE_REGION_* in .env or enable AUTO_SELECT_REGION."
            )

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with suppress(NotImplementedError):
                loop.add_signal_handler(sig, self.stop_event.set)

        self.hotkey_listener.start()
        tasks = [asyncio.create_task(self.pipeline_loop(), name="pipeline_loop")]

        logger.info("LiveSoul agent started.")
        await self.stop_event.wait()
        logger.info("Stopping runtime.")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.hotkey_listener.stop()

    async def pipeline_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                frame = await self.capture.capture_frame()
                logger.debug("Captured frame %s", frame.frame_id)
                text, confidence, source = await self._recognize_barrage(frame)
                normalized = self._normalize_text(text)
                if not normalized:
                    logger.debug("No readable barrage text in frame %s", frame.frame_id)
                elif normalized == self.last_recognized_text:
                    logger.debug("Skipping unchanged barrage snapshot.")
                else:
                    self.last_recognized_text = normalized
                    self._save_memory()
                    logger.info(
                        "Recognized barrage via %s (confidence=%.2f): %s",
                        source,
                        confidence,
                        normalized,
                    )
                    reply_text = await self.agent.generate_reply(
                        normalized,
                        recent_context=list(self.dialogue_history),
                    )
                    if reply_text.strip():
                        reply_text = reply_text.strip()
                        logger.info("Generated reply: %s", reply_text)
                        await self.tts.speak(reply_text)
                        self.dialogue_history.append((normalized, reply_text))
                        self._save_memory()
            except Exception as exc:
                logger.exception("Pipeline loop failed: %s", exc)
            await asyncio.sleep(self.config.screenshot_interval)

    async def _recognize_barrage(self, frame: FramePayload) -> tuple[str, float, str]:
        try:
            vision_text, vision_confidence = await asyncio.wait_for(
                self.vision.recognize(frame.image_path),
                timeout=self.config.vision_timeout_seconds,
            )
            if vision_text.strip():
                return vision_text, vision_confidence, "vision"
        except TimeoutError:
            logger.warning(
                "Vision recognition timed out after %.1f seconds; falling back to OCR.",
                self.config.vision_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("Vision recognition failed; falling back to OCR: %s", exc)

        text, confidence, source = await self.ocr.recognize(frame.image_path)
        return text, confidence, source

    def _normalize_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _load_memory(self) -> None:
        if not self.memory_json_path.exists():
            self._save_memory()
            return

        try:
            payload = json.loads(self.memory_json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load memory file %s: %s", self.memory_json_path, exc)
            return

        self.last_recognized_text = str(payload.get("last_recognized_text", "") or "")
        history = payload.get("dialogue_history", [])
        if isinstance(history, list):
            for item in history[-4:]:
                if not isinstance(item, dict):
                    continue
                recognized_text = str(item.get("recognized_text", "") or "").strip()
                reply_text = str(item.get("reply_text", "") or "").strip()
                if recognized_text and reply_text:
                    self.dialogue_history.append((recognized_text, reply_text))

    def _save_memory(self) -> None:
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_recognized_text": self.last_recognized_text,
            "dialogue_history": [
                {"recognized_text": recognized_text, "reply_text": reply_text}
                for recognized_text, reply_text in self.dialogue_history
            ],
        }
        self.memory_json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.memory_html_path.write_text(self._render_memory_html(payload), encoding="utf-8")

    def _render_memory_html(self, payload: dict[str, object]) -> str:
        updated_at = escape(str(payload.get("updated_at", "") or ""))
        last_recognized_text = escape(str(payload.get("last_recognized_text", "") or ""))
        history = payload.get("dialogue_history", [])

        if isinstance(history, list) and history:
            cards = []
            for index, item in enumerate(history, start=1):
                if not isinstance(item, dict):
                    continue
                recognized_text = escape(str(item.get("recognized_text", "") or ""))
                reply_text = escape(str(item.get("reply_text", "") or ""))
                cards.append(
                    "<section class='card'>"
                    f"<h2>Round {index}</h2>"
                    f"<h3>Barrage</h3><pre>{recognized_text}</pre>"
                    f"<h3>Reply</h3><pre>{reply_text}</pre>"
                    "</section>"
                )
            history_html = "".join(cards)
        else:
            history_html = "<p class='empty'>No dialogue history yet.</p>"

        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>LiveSoul Memory</title>"
            "<style>"
            "body{font-family:Segoe UI,Arial,sans-serif;max-width:960px;margin:0 auto;padding:24px;"
            "background:#f4f6f8;color:#18212b;line-height:1.5}"
            "h1,h2,h3{margin:0 0 12px}"
            ".meta,.card{background:#fff;border:1px solid #d8e0e8;border-radius:12px;padding:16px;margin-bottom:16px}"
            "pre{white-space:pre-wrap;word-break:break-word;background:#f8fafc;padding:12px;border-radius:8px;"
            "border:1px solid #e5ebf1}"
            ".empty{color:#5b6b7b}"
            "</style></head><body>"
            "<h1>LiveSoul Memory</h1>"
            f"<section class='meta'><p><strong>Updated:</strong> {updated_at}</p>"
            f"<h2>Last Recognized Text</h2><pre>{last_recognized_text}</pre></section>"
            f"{history_html}</body></html>"
        )


async def async_main() -> None:
    runtime = LiveSoulRuntime()
    await runtime.run()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
