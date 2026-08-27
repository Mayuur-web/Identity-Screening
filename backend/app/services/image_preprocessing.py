"""Image Preprocessing Service — Lightweight pipeline for OCR quality improvement.

Provides two preprocessing variants:
1. Auto-rotated + upscaled original (best general case)
2. Grayscale with CLAHE contrast enhancement (helps low-contrast documents)

Avoids aggressive thresholding or transformations that can destroy text.
"""

import os
import logging
from typing import Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Target minimum width for OCR — small images get upscaled
MIN_WIDTH = 1200
# Maximum dimension to prevent memory issues
MAX_DIMENSION = 4000


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_image(image_path: str) -> Optional[np.ndarray]:
    """Load an image from disk as a BGR numpy array."""
    if not os.path.exists(image_path):
        logger.error(f"Image not found: {image_path}")
        return None
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Failed to read image: {image_path}")
    return img


def save_image(img: np.ndarray, path: str) -> str:
    """Save a numpy array as an image file. Returns the path."""
    _ensure_dir(path)
    cv2.imwrite(path, img)
    return path


def auto_rotate(img: np.ndarray) -> np.ndarray:
    """Rotate portrait images 90° CW (common for phone-captured documents)."""
    h, w = img.shape[:2]
    if h > w * 1.4:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        logger.debug("Auto-rotated image 90° CW (portrait detected)")
    return img


def upscale_if_small(img: np.ndarray, min_width: int = MIN_WIDTH) -> np.ndarray:
    """Upscale image if it's too small for reliable OCR."""
    h, w = img.shape[:2]
    if w < min_width:
        scale = min(min_width / w, 3.0)
        new_w = int(w * scale)
        new_h = int(h * scale)
        if new_w > MAX_DIMENSION:
            ratio = MAX_DIMENSION / new_w
            new_w = MAX_DIMENSION
            new_h = int(new_h * ratio)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        logger.debug(f"Upscaled image from {w}x{h} to {new_w}x{new_h}")
    return img


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert to grayscale if the image is in color."""
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def enhance_contrast(img: np.ndarray, clip_limit: float = 2.0, grid_size: int = 8) -> np.ndarray:
    """Apply CLAHE contrast enhancement.

    Works on both grayscale and color images.
    """
    if len(img.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
        return clahe.apply(img)

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def create_preprocessing_variants(
    image_path: str,
    document_type: Optional[str] = None,
) -> dict:
    """Create preprocessing variants of the input image.

    Returns a dict with:
        - variants: list of dicts with 'name', 'path', 'description'
        - preprocessing_applied: list of preprocessing step names
    """
    img = load_image(image_path)
    if img is None:
        return {"variants": [], "preprocessing_applied": []}

    preprocessing_applied = []
    variants = []

    # Step 1: Auto-rotate if needed
    h, w = img.shape[:2]
    if h > w * 1.4:
        img = auto_rotate(img)
        preprocessing_applied.append("auto_rotate")

    # Step 2: Upscale if small
    img = upscale_if_small(img)
    preprocessing_applied.append("upscale")

    # Variant 1: Preprocessed original (best general case for Aadhaar/PAN/etc.)
    base_path = image_path.rsplit(".", 1)[0] + "_preprocessed.png"
    save_image(img, base_path)
    variants.append({
        "name": "preprocessed",
        "path": base_path,
        "description": "Auto-rotated and upscaled",
    })

    # Variant 2: Grayscale + CLAHE contrast enhancement
    gray = to_grayscale(img)
    gray_enhanced = enhance_contrast(gray)
    gray_path = image_path.rsplit(".", 1)[0] + "_gray_enhanced.png"
    save_image(gray_enhanced, gray_path)
    preprocessing_applied.append("grayscale_contrast")
    variants.append({
        "name": "gray_contrast",
        "path": gray_path,
        "description": "Grayscale with CLAHE contrast enhancement",
    })

    return {
        "variants": variants,
        "preprocessing_applied": preprocessing_applied,
    }


def cleanup_temp_files(image_path: str):
    """Remove preprocessed temporary files."""
    import glob
    base = image_path.rsplit(".", 1)[0]
    for pattern in [f"{base}_preprocessed.*", f"{base}_gray_*"]:
        for f in glob.glob(pattern):
            try:
                os.remove(f)
            except OSError:
                pass
