"""Unit tests for Google Vision OCR Engine adapter (TC-03-12, TC-03-15)."""

import pytest

from backend.app.services.ocr.base import (
    OCRInvalidImage,
    OCRNoText,
    OCRRateLimited,
)
from backend.app.services.ocr.google_vision_engine import CircuitBreaker, GoogleVisionEngine


class MockVisionClient:
    """Mock client simulating Google Cloud Vision API responses and errors."""

    def __init__(self, mode: str = "success", error_message: str = ""):
        self.mode = mode
        self.error_message = error_message
        self.call_count = 0

    def annotate_image_bytes(self, image_bytes: bytes):
        self.call_count += 1
        if self.mode == "rate_limit":
            raise RuntimeError("429 ResourceExhausted: Quota exceeded")
        elif self.mode == "bad_request":
            raise RuntimeError("400 Invalid_Argument: Bad image format")
        elif self.mode == "empty":
            return {"fullTextAnnotation": {"text": ""}, "textAnnotations": []}
        elif self.mode == "success":
            return {
                "fullTextAnnotation": {
                    "text": "HIGHLANDS COFFEE\nHoa don: 100.000 d",
                    "pages": [
                        {
                            "width": 800,
                            "height": 1000,
                            "blocks": [
                                {
                                    "paragraphs": [
                                        {
                                            "words": [
                                                {
                                                    "symbols": [
                                                        {"text": "H"},
                                                        {"text": "I"},
                                                        {"text": "G"},
                                                        {"text": "H"},
                                                        {"text": "L"},
                                                        {"text": "A"},
                                                        {"text": "N"},
                                                        {"text": "D"},
                                                        {"text": "S"},
                                                        {
                                                            "text": " ",
                                                            "property": {"detectedBreak": {"type": "SPACE"}},
                                                        },
                                                    ],
                                                    "confidence": 0.98,
                                                },
                                                {
                                                    "symbols": [
                                                        {"text": "C"},
                                                        {"text": "O"},
                                                        {"text": "F"},
                                                        {"text": "F"},
                                                        {"text": "E"},
                                                        {"text": "E"},
                                                        {
                                                            "text": "\n",
                                                            "property": {"detectedBreak": {"type": "LINE_BREAK"}},
                                                        },
                                                    ],
                                                    "confidence": 0.99,
                                                },
                                            ]
                                        }
                                    ]
                                }
                            ],
                        }
                    ],
                }
            }


@pytest.mark.asyncio
async def test_tc_03_12_mock_429_retry_and_rate_limit():
    """TC-03-12: Transient 429 retries max 2 times then raises OCRRateLimited."""
    client = MockVisionClient(mode="rate_limit")
    engine = GoogleVisionEngine(client=client, max_retries=2, timeout=5.0)

    with pytest.raises(OCRRateLimited):
        await engine.extract(b"fake_image_bytes")

    # 1 initial call + 2 retries = 3 calls total
    assert client.call_count == 3


@pytest.mark.asyncio
async def test_tc_03_12_mock_400_no_retry():
    """TC-03-12: Client error 400 Bad Request is NOT retried."""
    client = MockVisionClient(mode="bad_request")
    engine = GoogleVisionEngine(client=client, max_retries=2)

    with pytest.raises(OCRInvalidImage):
        await engine.extract(b"corrupted_bytes")

    # Fails immediately on first attempt without retrying
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_tc_03_12_empty_response_ocr_no_text():
    """TC-03-12: Empty response raises OCRNoText."""
    client = MockVisionClient(mode="empty")
    engine = GoogleVisionEngine(client=client)

    with pytest.raises(OCRNoText):
        await engine.extract(b"blank_image_bytes")


@pytest.mark.asyncio
async def test_tc_03_12_circuit_breaker():
    """TC-03-12: Repeated failures trip circuit breaker to OPEN."""
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=60.0)
    assert breaker.is_available() is True

    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_available() is True

    breaker.record_failure()
    assert breaker.is_available() is False
    assert breaker.state == "OPEN"

    breaker.record_success()
    assert breaker.is_available() is True
    assert breaker.state == "CLOSED"


def test_tc_03_15_deterministic_reparse_raw_ocr():
    """TC-03-15: Parsing saved raw Vision JSON produces identical result (reproducibility)."""
    raw_payload = {
        "fullTextAnnotation": {
            "text": "COFFEE HOUSE\nTong cong: 50.000",
            "pages": [{"width": 500, "height": 800, "blocks": []}],
        }
    }
    engine = GoogleVisionEngine()
    doc1 = engine.parse_raw_response(raw_payload)
    doc2 = engine.parse_raw_response(raw_payload)

    assert doc1.full_text == doc2.full_text
    assert len(doc1.pages) == len(doc2.pages)
    assert doc1.raw_payload == doc2.raw_payload
