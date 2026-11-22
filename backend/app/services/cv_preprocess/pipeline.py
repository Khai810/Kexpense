"""Composite OpenCV preprocessing pipeline with do-no-harm gates and quality checks (TC-03-05 to TC-03-07, TC-03-13)."""

import asyncio
from io import BytesIO

import cv2
import numpy as np
import pillow_heif
from PIL import Image, ImageOps

from backend.app.models.schemas.ocr_schema import ImageQuality
from backend.app.services.cv_preprocess.contrast import enhance_contrast_clahe
from backend.app.services.cv_preprocess.deskew import apply_deskew
from backend.app.services.cv_preprocess.perspective import correct_perspective

# Register HEIF opener with PIL so iPhone .heic images load seamlessly
pillow_heif.register_heif_opener()


def decode_image_bytes(image_bytes: bytes, max_dimension: int = 2500) -> tuple[np.ndarray, bool]:
    """Decode raw image bytes, auto-correct EXIF orientation, and downscale if excessively large."""
    pil_image = Image.open(BytesIO(image_bytes))

    # Auto-orient based on EXIF (crucial for mobile camera shots)
    oriented_image = ImageOps.exif_transpose(pil_image)
    if oriented_image is None:
        oriented_image = pil_image

    # Convert to RGB (in case of RGBA, Palette, etc.)
    if oriented_image.mode != "RGB":
        oriented_image = oriented_image.convert("RGB")

    # Downscale if larger than max_dimension
    w, h = oriented_image.size
    resized = False
    if max(w, h) > max_dimension:
        ratio = max_dimension / float(max(w, h))
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        oriented_image = oriented_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        resized = True

    # Convert PIL Image to OpenCV BGR ndarray
    np_image = np.array(oriented_image)
    bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

    return bgr_image, resized


def check_image_quality(image: np.ndarray) -> tuple[bool, bool, float, float]:
    """Assess image quality metrics: blur (Laplacian variance) and brightness.

    Returns (is_blur, is_dark, laplacian_variance, mean_brightness).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_bright = float(np.mean(gray))

    is_blur = lap_var < 100.0
    is_dark = mean_bright < 60.0

    return is_blur, is_dark, lap_var, mean_bright


def preprocess_image(
    image: np.ndarray,
    enable_preprocess: bool = True,
) -> tuple[np.ndarray, ImageQuality]:
    """Execute do-no-harm preprocessing pipeline with gates."""
    is_blur, is_dark, _, _ = check_image_quality(image)
    steps_applied: list[str] = []

    if not enable_preprocess:
        quality = ImageQuality(
            is_blur=is_blur,
            is_dark=is_dark,
            steps_applied=[],
            ocr_mean_confidence=0.0,
        )
        return image, quality

    current = image.copy()

    # Step 1: Perspective unwarping (gate: quadrilateral >= 25% area)
    current, applied_perspective = correct_perspective(current)
    if applied_perspective:
        steps_applied.append("perspective")

    # Step 2: Deskew (gate: 0.5 deg <= |angle| <= 45 deg)
    current, applied_deskew, _ = apply_deskew(current)
    if applied_deskew:
        steps_applied.append("deskew")

    # Step 3: Contrast enhancement (gate: low contrast std < 50)
    current, applied_clahe = enhance_contrast_clahe(current)
    if applied_clahe:
        steps_applied.append("clahe")

    quality = ImageQuality(
        is_blur=is_blur,
        is_dark=is_dark,
        steps_applied=steps_applied,
        ocr_mean_confidence=0.0,
    )

    return current, quality


class PreprocessPipeline:
    """Async wrapper for OpenCV preprocessing executed in worker thread (TC-03-13)."""

    @classmethod
    def process_sync(
        cls,
        image_bytes: bytes,
        enable_preprocess: bool = True,
        max_dimension: int = 2500,
    ) -> tuple[np.ndarray, ImageQuality]:
        img, _ = decode_image_bytes(image_bytes, max_dimension=max_dimension)
        return preprocess_image(img, enable_preprocess=enable_preprocess)

    @classmethod
    async def process_async(
        cls,
        image_bytes: bytes,
        enable_preprocess: bool = True,
        max_dimension: int = 2500,
    ) -> tuple[np.ndarray, ImageQuality]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            cls.process_sync,
            image_bytes,
            enable_preprocess,
            max_dimension,
        )
