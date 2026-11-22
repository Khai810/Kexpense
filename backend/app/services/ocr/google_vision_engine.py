"""Google Cloud Vision OCR Engine adapter with retry, circuit breaker, and timeout (TC-03-12, TC-03-15)."""

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

from backend.app.models.schemas.ocr_schema import BBox
from backend.app.services.ocr.base import (
    BaseOCREngine,
    OCRDocument,
    OCRInvalidImage,
    OCRLine,
    OCRNoText,
    OCRPage,
    OCRProviderUnavailable,
    OCRRateLimited,
    OCRTimeout,
    OCRWord,
)


class CircuitBreaker:
    """Simple in-memory circuit breaker to prevent cascading failures to 3rd party APIs."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def is_available(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure_time is not None:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout_seconds:
                    self.state = "HALF_OPEN"
                    return True
            return False
        return True  # HALF_OPEN allows a trial request


def _vertices_to_bbox(vertices: list[dict[str, Any]], page_w: int, page_h: int) -> BBox | None:
    """Normalize polygon vertices to BBox (0-1)."""
    if not vertices or page_w <= 0 or page_h <= 0:
        return None

    xs = [v.get("x", 0) for v in vertices]
    ys = [v.get("y", 0) for v in vertices]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    norm_x = max(0.0, min(1.0, float(min_x) / page_w))
    norm_y = max(0.0, min(1.0, float(min_y) / page_h))
    norm_w = max(0.0, min(1.0, float(max_x - min_x) / page_w))
    norm_h = max(0.0, min(1.0, float(max_y - min_y) / page_h))

    return BBox(x=round(norm_x, 4), y=round(norm_y, 4), w=round(norm_w, 4), h=round(norm_h, 4))


class GoogleVisionEngine(BaseOCREngine):
    """Adapter for Google Cloud Vision DOCUMENT_TEXT_DETECTION."""

    def __init__(
        self,
        client: Any = None,
        language_hints: list[str] | None = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        self._client = client
        self.language_hints = language_hints or ["vi", "en"]
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google.cloud import vision

            self._client = vision.ImageAnnotatorClient()
            return self._client
        except Exception as err:
            raise OCRProviderUnavailable(f"Failed to initialize Google Vision client: {err}") from err

    async def extract(self, image_bytes: bytes, **kwargs: Any) -> OCRDocument:
        """Call Google Vision API with timeout, retry, and circuit breaker."""
        if not image_bytes:
            raise OCRInvalidImage("Image content is empty")

        if not self.circuit_breaker.is_available():
            raise OCRProviderUnavailable("Google Vision circuit breaker is OPEN due to repeated errors")

        attempt = 0
        last_error: Exception | None = None

        while attempt <= self.max_retries:
            try:
                loop = asyncio.get_running_loop()
                raw_response = await asyncio.wait_for(
                    loop.run_in_executor(None, self._call_vision_api, image_bytes),
                    timeout=self.timeout,
                )
                self.circuit_breaker.record_success()
                return self.parse_raw_response(raw_response)

            except asyncio.TimeoutError as err:
                self.circuit_breaker.record_failure()
                raise OCRTimeout(f"Google Vision request timed out after {self.timeout}s") from err

            except (OCRNoText, OCRInvalidImage) as non_retryable:
                raise non_retryable

            except Exception as exc:
                err_str = str(exc).lower()
                # Check for 400 Bad Request or client error -> DO NOT RETRY
                if "400" in err_str or "invalid_argument" in err_str or "bad request" in err_str:
                    self.circuit_breaker.record_failure()
                    raise OCRInvalidImage(f"Google Vision rejected request: {exc}") from exc

                # Check for 429 / Rate Limit
                is_transient = (
                    "429" in err_str
                    or "resource_exhausted" in err_str
                    or "503" in err_str
                    or "unavailable" in err_str
                    or "deadline_exceeded" in err_str
                )

                if is_transient and attempt < self.max_retries:
                    attempt += 1
                    backoff = (2**attempt) * 0.5 + random.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff)
                    continue

                self.circuit_breaker.record_failure()
                if "429" in err_str or "resource_exhausted" in err_str:
                    raise OCRRateLimited(f"Google Vision quota/rate limited: {exc}") from exc

                raise OCRProviderUnavailable(f"Google Vision service error: {exc}") from exc

        raise OCRProviderUnavailable(f"Exceeded {self.max_retries} retries calling Google Vision: {last_error}")

    def _call_vision_api(self, image_bytes: bytes) -> dict[str, Any]:
        """Synchronous Google Cloud Vision SDK call."""
        client = self._get_client()

        # If mock client has extract_sync or direct call:
        if hasattr(client, "annotate_image_bytes"):
            return client.annotate_image_bytes(image_bytes)

        from google.cloud import vision

        image = vision.Image(content=image_bytes)
        image_context = vision.ImageContext(language_hints=self.language_hints)

        response = client.document_text_detection(image=image, image_context=image_context)

        if response.error.message:
            raise RuntimeError(f"Vision API Error: {response.error.message}")

        # Convert protobuf to dict for serialization
        from google.protobuf.json_format import MessageToDict

        return MessageToDict(response._pb)

    def parse_raw_response(self, raw_data: dict[str, Any]) -> OCRDocument:
        """Parse raw Google Vision API JSON response into standard OCRDocument (TC-03-15)."""
        full_text_annotation = raw_data.get("fullTextAnnotation")
        text_annotations = raw_data.get("textAnnotations") or []

        if not full_text_annotation and not text_annotations:
            raise OCRNoText("No text annotations found in Google Vision response")

        full_text = full_text_annotation.get("text", "") if full_text_annotation else ""
        if not full_text and text_annotations:
            full_text = text_annotations[0].get("description", "")

        if not full_text.strip():
            raise OCRNoText("Empty text returned from Google Vision")

        pages: list[OCRPage] = []
        gv_pages = full_text_annotation.get("pages", []) if full_text_annotation else []

        for _p_idx, gv_page in enumerate(gv_pages):
            page_w = int(gv_page.get("width", 1000))
            page_h = int(gv_page.get("height", 1000))
            lines: list[OCRLine] = []

            for block in gv_page.get("blocks", []):
                for paragraph in block.get("paragraphs", []):
                    current_line_words: list[OCRWord] = []

                    for word_obj in paragraph.get("words", []):
                        word_chars = []
                        has_line_break = False

                        for symbol in word_obj.get("symbols", []):
                            char_text = symbol.get("text", "")
                            word_chars.append(char_text)

                            break_type = symbol.get("property", {}).get("detectedBreak", {}).get("type")
                            # LINE_BREAK (3 or 'LINE_BREAK'), EOL_SURE_SPACE (5)
                            if break_type in [
                                "LINE_BREAK",
                                "EOL_SURE_SPACE",
                                3,
                                5,
                            ]:
                                has_line_break = True

                        w_text = "".join(word_chars)
                        w_conf = float(word_obj.get("confidence", 1.0))
                        w_verts = word_obj.get("boundingBox", {}).get("vertices", [])
                        w_bbox = _vertices_to_bbox(w_verts, page_w, page_h)

                        word_model = OCRWord(text=w_text, bbox=w_bbox, confidence=w_conf)
                        current_line_words.append(word_model)

                        if has_line_break:
                            line_text = " ".join(w.text for w in current_line_words)
                            line_conf = (
                                sum(w.confidence for w in current_line_words) / len(current_line_words)
                                if current_line_words
                                else 1.0
                            )
                            # Bounding box of line from first and last words
                            line_bbox = None
                            if current_line_words and current_line_words[0].bbox and current_line_words[-1].bbox:
                                b_first = current_line_words[0].bbox
                                b_last = current_line_words[-1].bbox
                                min_x = min(b_first.x, b_last.x)
                                min_y = min(b_first.y, b_last.y)
                                max_x = max(b_first.x + b_first.w, b_last.x + b_last.w)
                                max_y = max(b_first.y + b_first.h, b_last.y + b_last.h)
                                line_bbox = BBox(
                                    x=round(min_x, 4),
                                    y=round(min_y, 4),
                                    w=round(max_x - min_x, 4),
                                    h=round(max_y - min_y, 4),
                                )

                            lines.append(
                                OCRLine(
                                    text=line_text,
                                    words=current_line_words,
                                    bbox=line_bbox,
                                    confidence=round(line_conf, 2),
                                )
                            )
                            current_line_words = []

                    # Remaining words in paragraph
                    if current_line_words:
                        line_text = " ".join(w.text for w in current_line_words)
                        line_conf = sum(w.confidence for w in current_line_words) / len(current_line_words)
                        lines.append(
                            OCRLine(
                                text=line_text,
                                words=current_line_words,
                                bbox=None,
                                confidence=round(line_conf, 2),
                            )
                        )

            pages.append(OCRPage(width=page_w, height=page_h, lines=lines))

        # Fallback if fullTextAnnotation pages had no lines but full_text exists
        if not pages or not any(p.lines for p in pages):
            fallback_lines = [
                OCRLine(text=txt.strip(), words=[], confidence=1.0) for txt in full_text.splitlines() if txt.strip()
            ]
            pages = [OCRPage(width=1000, height=1000, lines=fallback_lines)]

        return OCRDocument(pages=pages, full_text=full_text, raw_payload=raw_data)
