"""Base interfaces and data structures for OCR Engines (ADR-007, TC-03-12)."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from backend.app.models.schemas.ocr_schema import BBox


class OCRError(Exception):
    """Base exception for all OCR operations."""

    def __init__(self, message: str, code: str = "OCR_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class OCRTimeout(OCRError):
    """Raised when an OCR engine exceeds timeout limits."""

    def __init__(self, message: str = "OCR operation timed out"):
        super().__init__(message, code="OCR_TIMEOUT")


class OCRNoText(OCRError):
    """Raised when an image contains no readable text."""

    def __init__(self, message: str = "No text detected in image"):
        super().__init__(message, code="OCR_NO_TEXT")


class OCRProviderUnavailable(OCRError):
    """Raised when OCR provider is temporarily down or circuit breaker is open."""

    def __init__(self, message: str = "OCR provider unavailable"):
        super().__init__(message, code="OCR_PROVIDER_UNAVAILABLE")


class OCRRateLimited(OCRError):
    """Raised when OCR quota or rate limit is reached."""

    def __init__(self, message: str = "OCR provider rate limit exceeded"):
        super().__init__(message, code="RATE_LIMITED")


class OCRInvalidImage(OCRError):
    """Raised when image format is unreadable or corrupted."""

    def __init__(self, message: str = "Invalid or corrupted image format"):
        super().__init__(message, code="IMAGE_UNREADABLE")


class OCRWord(BaseModel):
    """Atomic text unit with normalized coordinates and confidence score."""

    text: str
    bbox: BBox | None = None
    confidence: float = 1.0


class OCRLine(BaseModel):
    """Line of text composed of words."""

    text: str
    words: list[OCRWord] = Field(default_factory=list)
    bbox: BBox | None = None
    confidence: float = 1.0


class OCRPage(BaseModel):
    """Page containing lines of text."""

    width: int
    height: int
    lines: list[OCRLine] = Field(default_factory=list)


class OCRDocument(BaseModel):
    """SDK-independent internal representation of OCR extraction."""

    pages: list[OCRPage] = Field(default_factory=list)
    full_text: str = ""
    raw_payload: dict[str, Any] | None = None

    @property
    def lines(self) -> list[OCRLine]:
        """Flatten lines across all pages."""
        result: list[OCRLine] = []
        for p in self.pages:
            result.extend(p.lines)
        return result

    @property
    def mean_confidence(self) -> float:
        """Calculate average confidence across all lines/words."""
        all_lines = self.lines
        if not all_lines:
            return 0.0
        return float(sum(line.confidence for line in all_lines) / len(all_lines))


class BaseOCREngine(ABC):
    """Abstract Base Class for OCR engines."""

    @abstractmethod
    async def extract(self, image_bytes: bytes, **kwargs: Any) -> OCRDocument:
        """Extract text and layout from raw image bytes into an OCRDocument."""
        pass
