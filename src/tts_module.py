from __future__ import annotations

import asyncio
import binascii
import logging
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import requests

from .config import AppConfig

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


class TTSModule:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = (
            OpenAI(api_key=config.tts_api_key, base_url=config.tts_api_endpoint)
            if config.tts_provider == "openai" and config.tts_api_key and OpenAI is not None
            else None
        )

    async def speak(self, text: str) -> Path | None:
        if self.config.tts_provider == "console":
            logger.info("TTS(console): %s", text)
            return None
        if self.config.tts_provider == "pyttsx3":
            return await asyncio.to_thread(self._speak_with_pyttsx3, text)
        if self.config.tts_provider == "edge":
            return await self._speak_with_edge(text)
        if self.config.tts_provider == "minimaxi":
            if not self.config.tts_api_key:
                logger.warning("MiniMax TTS is selected but API key is missing.")
                return None
            return await asyncio.to_thread(self._speak_with_minimaxi, text)
        if self.config.tts_provider == "openai":
            if self.client is None:
                logger.warning("OpenAI TTS is selected but API key is missing.")
                return None
            return await asyncio.to_thread(self._speak_with_openai, text)
        logger.warning("Unknown TTS provider: %s", self.config.tts_provider)
        return None

    def _speak_with_openai(self, text: str) -> Path:
        output = self._output_path("mp3")
        with self.client.audio.speech.with_streaming_response.create(
            model=self.config.tts_model_name,
            voice=self.config.tts_voice,
            input=text,
        ) as response:
            response.stream_to_file(output)
        self._play_file(output)
        return output

    def _speak_with_minimaxi(self, text: str) -> Path:
        output = self._output_path("mp3")
        endpoint = self.config.tts_api_endpoint or "https://api.minimaxi.com/v1/t2a_v2"
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {self.config.tts_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.tts_model_name,
                "text": text,
                "stream": False,
                "voice_setting": {
                    "voice_id": self.config.tts_voice,
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0,
                },
                "audio_setting": {
                    "sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 1,
                },
                "pronunciation_dict": {"tone": []},
                "subtitle_enable": False,
                "output_format": "hex",
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        audio_hex = payload.get("data", {}).get("audio", "")
        if not audio_hex:
            raise RuntimeError(f"MiniMax TTS response did not contain audio data: {payload}")
        output.write_bytes(binascii.unhexlify(audio_hex))
        self._play_file(output)
        return output

    async def _speak_with_edge(self, text: str) -> Path | None:
        try:
            import edge_tts
        except Exception:
            logger.warning("edge-tts is not installed.")
            return None

        output = self._output_path("mp3")
        communicator = edge_tts.Communicate(text=text, voice="zh-CN-XiaoxiaoNeural")
        await communicator.save(str(output))
        await asyncio.to_thread(self._play_file, output)
        return output

    def _speak_with_pyttsx3(self, text: str) -> Path | None:
        try:
            import pyttsx3
        except Exception:
            logger.warning("pyttsx3 is not installed.")
            return None

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return None

    def _output_path(self, ext: str) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        return self.config.tts_output_dir / f"tts-{timestamp}.{ext}"

    def _play_file(self, path: Path) -> None:
        system = platform.system().lower()
        try:
            if system == "darwin":
                subprocess.run(["afplay", str(path)], check=False)
            elif system == "windows":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            logger.warning("Audio playback failed for %s: %s", path, exc)
