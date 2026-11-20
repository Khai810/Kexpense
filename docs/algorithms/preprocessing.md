# Image Preprocessing Architecture & Algorithms

This document details the image preprocessing pipeline implemented in `backend/app/services/cv_preprocess/` according to the do-no-harm principles specified in `ROADMAP.md` (Feature 03).

## 1. Pipeline Overview

The `PreprocessPipeline` cleans, normalizes, and prepares mobile camera receipts and uploaded scans before OCR submission:

```mermaid
flowchart TD
    Raw[Raw Bytes: JPEG / PNG / HEIC] --> EXIF[EXIF Transpose & Decode]
    EXIF --> Downscale[Cap Max Dimension <= 2500px]
    Downscale --> Quality[Measure Blur & Brightness]
    Quality --> DeskewGate{0.5 deg <= |Angle| <= 45 deg?}
    DeskewGate -- Yes --> Rotate[Rotate -Angle with border replicate]
    DeskewGate -- No --> PerspGate
    Rotate --> PerspGate{Convex 4-point Quad in [25%, 90%]? }
    PerspGate -- Yes --> Warp[Four-point Perspective Transform]
    PerspGate -- No --> CLAHEGate
    Warp --> CLAHEGate{L-channel Std < 50.0?}
    CLAHEGate -- Yes --> CLAHE[CLAHE on L Channel in LAB]
    CLAHEGate -- No --> Out[Final Preprocessed Image + Quality Report]
    CLAHE --> Out
```

## 2. Detailed Algorithms & Do-No-Harm Gates

### 2.1 EXIF Orientation & HEIC Normalization
- Automatically transposes image according to EXIF metadata tag `0x0112` (handling orientation codes 3, 6, 8) before any pixel operations.
- Decodes HEIC/HEIF images via `pillow-heif` into standard RGB/BGR arrays.
- Downscales images with max dimension $> 2500$ px to protect against pixel-bomb denial of service while preserving high-contrast text features.

### 2.2 Text-Oriented Deskewing (`deskew.py`)
- **Isolation of text lines:** Binarizes grayscale image via Otsu inverse thresholding (`cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU`).
- **Morphological connection:** Applies a horizontal structuring element `(25, 3)` to fuse characters into continuous line segments.
- **Orientation estimation:** Finds bounding rectangles (`cv2.minAreaRect`) for text line contours. Extracts line tilt angles relative to horizontal and takes the median across all valid lines.
- **Do-no-harm gate:** Only rotates if $0.5^\circ \le |\text{angle}| \le 45.0^\circ$. If the image is already straight ($|\text{angle}| < 0.5^\circ$), it is left untouched.

### 2.3 Perspective Unwarping (`perspective.py`)
- Detects the outer quadrilateral boundary of a receipt lying on a contrasting background using Canny edge detection and polygon approximation (`cv2.approxPolyDP`).
- **Do-no-harm gate:**
  - Contour must have exactly 4 vertices.
  - Contour must be convex (`cv2.isContourConvex`).
  - Area must occupy between $25\%$ and $90\%$ of the image ($0.25 \le \text{area\_ratio} \le 0.90$). If area exceeds $90\%$, the document already fills the frame, and warping would distort edges.
- Unwarps perspective using `cv2.getPerspectiveTransform` and `cv2.warpPerspective`.

### 2.4 Contrast Enhancement CLAHE (`contrast.py`)
- Converts BGR image into CIE LAB color space.
- Analyzes luminance standard deviation on the L-channel.
- **Do-no-harm gate:** CLAHE is applied only when $\sigma_L < 50.0$ (low contrast / washed out). High-contrast clean receipts bypass CLAHE to prevent introducing background noise.
