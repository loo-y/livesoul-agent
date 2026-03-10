from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class FramePayload:
    frame_id: str
    image_path: Path
    captured_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class RecognitionResult:
    frame: FramePayload
    text: str
    confidence: float
    source: str


@dataclass(slots=True)
class ReplyPayload:
    recognition: RecognitionResult
    reply_text: str
