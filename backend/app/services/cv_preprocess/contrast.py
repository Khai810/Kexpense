"""Contrast enhancement service using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""

import cv2
import numpy as np


def enhance_contrast_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
    std_thresh: float = 50.0,
) -> tuple[np.ndarray, bool]:
    """Apply CLAHE to L-channel if image contrast standard deviation is below `std_thresh`.

    Returns (processed_image, applied_flag).
    """
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    contrast_std = float(np.std(gray))

    # Gate: only apply when image contrast is low/washed out
    if contrast_std >= std_thresh:
        return image, False

    if len(image.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        enhanced = clahe.apply(image)
        return enhanced, True

    # Convert BGR to LAB, apply CLAHE on L-channel
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l_clahe = clahe.apply(l_channel)

    enhanced_lab = cv2.merge((l_clahe, a_channel, b_channel))
    cv2.cvtColor(enhanced_lab, cv2.COLOR_BGR2LAB)
    enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    return enhanced, True
