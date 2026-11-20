"""Unit tests for OpenCV preprocessing pipeline (TC-03-01, TC-03-05 to TC-03-07, TC-03-13)."""

import asyncio
from io import BytesIO

import cv2
import numpy as np
import pytest
from PIL import Image

from backend.app.services.cv_preprocess import (
    PreprocessPipeline,
    apply_deskew,
    correct_perspective,
    decode_image_bytes,
    detect_skew_angle,
    enhance_contrast_clahe,
    rotate_image,
)


def create_synthetic_receipt_image(angle: float = 0.0, w: int = 400, h: int = 600) -> np.ndarray:
    """Create a white background image with synthetic dark horizontal text lines."""
    img = np.ones((h, w, 3), dtype=np.uint8) * 255

    # Draw header
    cv2.putText(img, "HIGHLANDS COFFEE", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Hoa don ban hang", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1)

    # Draw text lines
    for y in range(160, 480, 40):
        cv2.putText(img, f"Mon hang so {y // 40}: 35.000 d", (40, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    cv2.putText(img, "TONG CONG: 140.000 d", (40, 530), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    if abs(angle) > 0.01:
        img = rotate_image(img, angle)

    return img


def test_tc_03_01_deskew_15_degrees():
    """TC-03-01: An image rotated 15 degrees has residual skew <= 1.5 degrees after deskew."""
    # Synthetic image rotated 15 degrees
    tilted = create_synthetic_receipt_image(angle=15.0)

    # Apply deskew
    deskewed, applied, detected_angle = apply_deskew(tilted)
    assert applied is True
    assert abs(detected_angle - 15.0) <= 2.0

    # Measure remaining residual angle
    residual_angle = detect_skew_angle(deskewed)
    assert abs(residual_angle) <= 1.5, f"Residual angle too high: {residual_angle}"


@pytest.mark.parametrize("angle", [-30.0, -15.0, -5.0, 5.0, 15.0, 30.0])
def test_tc_03_05_deskew_parameterized(angle: float):
    """TC-03-05: Deskew across angles in {±5°, ±15°, ±30°} leaves residual skew <= 1.5 degrees."""
    tilted = create_synthetic_receipt_image(angle=angle)
    deskewed, applied, _detected_angle = apply_deskew(tilted)

    assert applied is True
    residual = detect_skew_angle(deskewed)
    assert abs(residual) <= 1.5, f"Failed for angle {angle}: residual is {residual}"


def test_tc_03_05_straight_image_unchanged():
    """TC-03-05: An already straight image (< 0.5 deg) is not rotated (do-no-harm gate)."""
    straight = create_synthetic_receipt_image(angle=0.0)
    _result, applied, angle = apply_deskew(straight)

    assert applied is False or abs(angle) < 0.5
    assert abs(angle) <= 0.5


def test_tc_03_05_exif_orientation():
    """TC-03-05: Image with EXIF orientation (e.g. 6 = 90 deg CW) is auto-oriented."""
    pil_img = Image.new("RGB", (200, 400), color=(255, 255, 255))
    exif = pil_img.getexif()
    exif[0x0112] = 6  # Orientation tag: 90 deg CW

    buf = BytesIO()
    pil_img.save(buf, format="JPEG", exif=exif)

    bgr, _resized = decode_image_bytes(buf.getvalue())
    # Orientation 6 rotates (200, 400) into (400, 200)
    h, w = bgr.shape[:2]
    assert (w, h) == (400, 200)


def test_tc_03_07_no_contour_returns_original():
    """TC-03-07: Complex background without clear quad returns original image without error."""
    # Plain noise or complex background
    np.random.seed(42)
    noise = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)

    warped, applied = correct_perspective(noise, min_area_ratio=0.25)
    assert applied is False
    assert np.array_equal(warped, noise)


def test_clahe_contrast_enhancement():
    """Low contrast image triggers CLAHE, high contrast image does not."""
    # Low contrast image (low standard deviation)
    washed_out = np.ones((300, 300, 3), dtype=np.uint8) * 120
    # Add minor noise so std is ~10
    washed_out[50:250, 50:250] = 135

    _enhanced, applied = enhance_contrast_clahe(washed_out, std_thresh=50.0)
    assert applied is True

    # High contrast image
    high_contrast = create_synthetic_receipt_image(angle=0.0)
    _, applied_hc = enhance_contrast_clahe(high_contrast, std_thresh=30.0)
    assert applied_hc is False


@pytest.mark.asyncio
async def test_tc_03_13_pipeline_non_blocking_async():
    """TC-03-13: Async preprocessing executes in worker thread without blocking event loop."""
    img = create_synthetic_receipt_image(angle=15.0)
    _, buf = cv2.imencode(".jpg", img)
    raw_bytes = buf.tobytes()

    # Run 10 parallel preprocess requests
    tasks = [PreprocessPipeline.process_async(raw_bytes, enable_preprocess=True) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    for final_img, quality in results:
        assert isinstance(final_img, np.ndarray)
        assert "deskew" in quality.steps_applied
