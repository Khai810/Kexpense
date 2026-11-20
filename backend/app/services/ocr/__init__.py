"""OCR Services package."""

from backend.app.services.ocr.base import (
    BaseOCREngine,
    OCRDocument,
    OCRError,
    OCRInvalidImage,
    OCRLine,
    OCRNoText,
    OCRPage,
    OCRProviderUnavailable,
    OCRRateLimited,
    OCRTimeout,
    OCRWord,
)
from backend.app.services.ocr.google_vision_engine import CircuitBreaker, GoogleVisionEngine

__all__ = [
    "BaseOCREngine",
    "CircuitBreaker",
    "GoogleVisionEngine",
    "OCRDocument",
    "OCRError",
    "OCRInvalidImage",
    "OCRLine",
    "OCRNoText",
    "OCRPage",
    "OCRProviderUnavailable",
    "OCRRateLimited",
    "OCRTimeout",
    "OCRWord",
]
