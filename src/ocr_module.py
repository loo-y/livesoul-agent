from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


class OCRModule:
    def __init__(self) -> None:
        self._easyocr_reader = None
        self._easyocr_unavailable = False
        self._tesseract_available: bool | None = None

    async def recognize(self, image_path: Path) -> tuple[str, float, str]:
        return await asyncio.to_thread(self._recognize_sync, image_path)

    def _recognize_sync(self, image_path: Path) -> tuple[str, float, str]:
        prepared = self._prepare_image(image_path)

        easyocr_result = self._run_easyocr(prepared)
        if easyocr_result is not None:
            return (*easyocr_result, "easyocr")

        tesseract_result = self._run_tesseract(prepared)
        if tesseract_result is not None:
            return (*tesseract_result, "tesseract")

        return "", 0.0, "none"

    def _prepare_image(self, image_path: Path) -> Image.Image:
        image = Image.open(image_path).convert("L")
        image = ImageOps.autocontrast(image)
        image = image.filter(ImageFilter.SHARPEN)
        return image

    def _run_easyocr(self, image: Image.Image) -> tuple[str, float] | None:
        if self._easyocr_unavailable:
            return None

        try:
            import easyocr
        except Exception:
            self._easyocr_unavailable = True
            return None

        try:
            if self._easyocr_reader is None:
                self._easyocr_reader = easyocr.Reader(
                    ["ch_sim", "en"],
                    gpu=False,
                    download_enabled=False,
                )
            result = self._easyocr_reader.readtext(np.array(image))
        except Exception as exc:
            logger.warning("EasyOCR failed: %s", exc)
            self._easyocr_unavailable = True
            return None

        if not result:
            return "", 0.0

        texts = [item[1].strip() for item in result if item[1].strip()]
        confidences = [float(item[2]) for item in result if item[1].strip()]
        if not texts:
            return "", 0.0
        return "\n".join(texts), sum(confidences) / len(confidences)

    def _run_tesseract(self, image: Image.Image) -> tuple[str, float] | None:
        try:
            import pytesseract
        except Exception:
            return None

        if self._tesseract_available is None:
            self._tesseract_available = shutil.which("tesseract") is not None
            if not self._tesseract_available:
                logger.warning("Tesseract binary is unavailable; skipping pytesseract fallback.")

        if not self._tesseract_available:
            return None

        try:
            data = pytesseract.image_to_data(
                image,
                lang="chi_sim+eng",
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:
            logger.warning("Tesseract failed: %s", exc)
            return None

        tokens: list[str] = []
        confidences: list[float] = []
        for text, conf in zip(data.get("text", []), data.get("conf", []), strict=False):
            text = text.strip()
            try:
                conf_value = float(conf)
            except Exception:
                conf_value = -1.0
            if text and conf_value >= 0:
                tokens.append(text)
                confidences.append(conf_value / 100.0)

        if not tokens:
            return "", 0.0
        return " ".join(tokens), sum(confidences) / len(confidences)
