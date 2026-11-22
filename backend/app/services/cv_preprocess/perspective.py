"""Perspective transformation service for phone-captured receipts (TC-03-07)."""

import cv2
import numpy as np


def order_quad_points(pts: np.ndarray) -> np.ndarray:
    """Order coordinates in clockwise order: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")

    # Sum of coordinates: top-left has smallest sum, bottom-right has largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Difference of coordinates: top-right has smallest diff, bottom-left has largest diff
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def correct_perspective(
    image: np.ndarray,
    min_area_ratio: float = 0.25,
    max_area_ratio: float = 0.90,
) -> tuple[np.ndarray, bool]:
    """Detect quadrilateral receipt contour and unwarp perspective.

    Do-no-harm gate: only warps if a 4-point convex contour is found covering
    between 25% and 90% of image area (avoiding full-frame border capture).
    Returns (processed_image, applied_flag).
    """
    h, w = image.shape[:2]
    total_area = float(h * w)

    # Convert to grayscale and blur
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200)

    # Dilate edges slightly to close gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edged, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    target_contour = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            area = cv2.contourArea(approx)
            if min_area_ratio * total_area <= area <= max_area_ratio * total_area:
                target_contour = approx
                break

    if target_contour is None:
        return image, False

    # Extract 4 points
    pts = target_contour.reshape(4, 2)
    rect = order_quad_points(pts)
    (tl, tr, br, bl) = rect

    # Compute width and height of destination image
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = max(int(height_a), int(height_b))

    # Reject degenerated bounding boxes
    if max_w < 100 or max_h < 100:
        return image, False

    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype="float32",
    )

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_w, max_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return warped, True
