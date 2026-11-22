"""Deskew service for document images using OpenCV minAreaRect / Hough lines (TC-03-01, TC-03-05)."""

import cv2
import numpy as np


def detect_skew_angle(image: np.ndarray) -> float:
    """Detect rotation skew angle of text in image in degrees (-45.0 to 45.0).

    A positive angle indicates clockwise tilt; a negative angle indicates counter-clockwise.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    # Invert and threshold to isolate dark text on bright receipt paper
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Dilate horizontally to connect text characters into lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    # Find text line contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    angles: list[float] = []

    for c in contours:
        if cv2.contourArea(c) < 100:
            continue
        rect = cv2.minAreaRect(c)
        (w, h) = rect[1]
        raw_angle = rect[2]

        line_angle = raw_angle + 90.0 if w < h else raw_angle

        if line_angle < -45:
            line_angle += 90.0
        elif line_angle > 45:
            line_angle -= 90.0

        angles.append(line_angle)

    if not angles:
        return 0.0

    # Invert sign to match image rotation convention
    return float(round(-float(np.median(angles)), 2))


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image around its center by `angle` degrees, expanding border to avoid clipping."""
    h, w = image.shape[:2]
    cx, cy = w / 2, h / 2

    # Get rotation matrix (negative angle rotates clockwise)
    M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)

    # Compute new bounding dimensions
    cos_val = abs(M[0, 0])
    sin_val = abs(M[0, 1])
    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))

    # Adjust transformation matrix translation
    M[0, 2] += (new_w / 2) - cx
    M[1, 2] += (new_h / 2) - cy

    rotated = cv2.warpAffine(
        image,
        M,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


def apply_deskew(image: np.ndarray, min_angle: float = 0.5, max_angle: float = 45.0) -> tuple[np.ndarray, bool, float]:
    """Do-no-harm deskew gate: only rotate if min_angle <= |angle| <= max_angle."""
    angle = detect_skew_angle(image)
    if min_angle <= abs(angle) <= max_angle:
        rotated = rotate_image(image, -angle)
        return rotated, True, angle
    return image, False, angle
