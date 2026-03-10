from __future__ import annotations

import asyncio
import logging
import signal
import time
from contextlib import suppress

from .ai_agent import AIAgent
from .config import load_config, setup_logging
from .models import FramePayload, RecognitionResult, ReplyPayload
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
        self.frame_queue: asyncio.Queue[FramePayload] = asyncio.Queue(
            maxsize=self.config.queue_maxsize
        )
        self.text_queue: asyncio.Queue[RecognitionResult] = asyncio.Queue(
            maxsize=self.config.queue_maxsize
        )
        self.reply_queue: asyncio.Queue[ReplyPayload] = asyncio.Queue(
            maxsize=self.config.queue_maxsize
        )
        self.recent_messages: dict[str, float] = {}

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

        tasks = [
            asyncio.create_task(self.capture_loop(), name="capture_loop"),
            asyncio.create_task(self.recognition_loop(), name="recognition_loop"),
            asyncio.create_task(self.agent_loop(), name="agent_loop"),
            asyncio.create_task(self.tts_loop(), name="tts_loop"),
        ]

        logger.info("LiveSoul agent started.")
        await self.stop_event.wait()
        logger.info("Stopping runtime.")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def capture_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                frame = await self.capture.capture_frame()
                await self.frame_queue.put(frame)
                logger.debug("Captured frame %s", frame.frame_id)
            except Exception as exc:
                logger.exception("Capture loop failed: %s", exc)
            await asyncio.sleep(self.config.screenshot_interval)

    async def recognition_loop(self) -> None:
        while not self.stop_event.is_set():
            frame = await self.frame_queue.get()
            try:
                text, confidence, source = await self.ocr.recognize(frame.image_path)
                if confidence < self.config.ocr_confidence_threshold or not text.strip():
                    vision_text, vision_confidence = await self.vision.recognize(frame.image_path)
                    if vision_text.strip():
                        text = vision_text
                        confidence = vision_confidence
                        source = "vision"

                normalized = self._normalize_text(text)
                if not normalized:
                    continue
                if self._is_duplicate(normalized):
                    logger.debug("Skipping duplicate barrage: %s", normalized)
                    continue

                result = RecognitionResult(
                    frame=frame,
                    text=normalized,
                    confidence=confidence,
                    source=source,
                )
                await self.text_queue.put(result)
                logger.info("Recognized barrage via %s: %s", source, normalized)
            except Exception as exc:
                logger.exception("Recognition loop failed: %s", exc)
            finally:
                self.frame_queue.task_done()

    async def agent_loop(self) -> None:
        while not self.stop_event.is_set():
            recognition = await self.text_queue.get()
            try:
                reply_text = await self.agent.generate_reply(recognition.text)
                if reply_text.strip():
                    await self.reply_queue.put(
                        ReplyPayload(recognition=recognition, reply_text=reply_text.strip())
                    )
                    logger.info("Generated reply: %s", reply_text.strip())
            except Exception as exc:
                logger.exception("Agent loop failed: %s", exc)
            finally:
                self.text_queue.task_done()

    async def tts_loop(self) -> None:
        while not self.stop_event.is_set():
            reply = await self.reply_queue.get()
            try:
                await self.tts.speak(reply.reply_text)
            except Exception as exc:
                logger.exception("TTS loop failed: %s", exc)
            finally:
                self.reply_queue.task_done()

    def _normalize_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _is_duplicate(self, text: str) -> bool:
        now = time.time()
        expired = [
            key
            for key, seen_at in self.recent_messages.items()
            if now - seen_at > self.config.dedup_window_seconds
        ]
        for key in expired:
            self.recent_messages.pop(key, None)

        if text in self.recent_messages:
            return True
        self.recent_messages[text] = now
        return False


async def async_main() -> None:
    runtime = LiveSoulRuntime()
    await runtime.run()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
