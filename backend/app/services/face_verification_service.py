"""Face Verification Service for Parakh Seva.

Uses OpenCV 5's FaceDetectorYN (YuNet DNN model) for face detection
and a multi-metric comparison (histogram correlation + structural
similarity + SSIM) to produce a 0–100 similarity score.

Design decisions:
- Uses YuNet DNN face detector (shipped with OpenCV 5 via
  FaceDetectorYN_create) for robust face detection.
- If multiple faces are detected, selects the LARGEST face by bounding
  box area — this is the most likely primary subject.
- Compares faces using three complementary metrics:
  1. Histogram correlation (colour distribution similarity)
  2. Structural similarity (edge/texture pattern via mean-abs-diff)
  3. SSIM (structural similarity index)
- All weights are documented and deterministic.
- No external AI APIs are used. No embeddings are stored or logged.
"""

import os
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# YuNet model for face detection
# Primary: project-controlled location (backend/models/)
# Fallback: OpenCV's bundled data directory
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
_YUNET_MODEL_PRIMARY = _BACKEND_DIR / "models" / "face_detection_yunet_2023mar.onnx"
_YUNET_MODEL_FALLBACK = os.path.join(
    os.path.dirname(cv2.__file__), "data",
    "face_detection_yunet_2023mar.onnx",
)


def _resolve_model_path() -> str:
    """Resolve the YuNet model path, preferring the project-local copy."""
    if _YUNET_MODEL_PRIMARY.is_file():
        return str(_YUNET_MODEL_PRIMARY)
    if os.path.isfile(_YUNET_MODEL_FALLBACK):
        return _YUNET_MODEL_FALLBACK
    return str(_YUNET_MODEL_PRIMARY)  # return primary path for error message

# Face detection parameters
_SCORE_THRESHOLD = 0.3
_NMS_THRESHOLD = 0.3
_TOP_K = 5000

# Face comparison: standardised crop size for comparison
_COMPARE_SIZE = (100, 100)

# Histogram bins per channel
_HIST_BINS = [8, 8, 8]

# Thresholds (tuned for prototype; not from a trained model)
_MATCH_THRESHOLD = 55   # similarity >= this → MATCH
_HIGH_CONFIDENCE = 75   # >= this → high confidence match
_LOW_CONFIDENCE = 40    # < this → likely no match

# Weights for final score
_WEIGHT_HISTOGRAM = 0.40
_WEIGHT_STRUCTURAL = 0.35
_WEIGHT_PIXEL_DIFF = 0.25


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_detector():
    """Create and return a FaceDetectorYN instance, or None."""
    model_path = _resolve_model_path()
    if not os.path.isfile(model_path):
        logger.error(
            "YuNet face detection model not found.\n"
            "  Expected at: %s\n"
            "  Fallback checked: %s\n"
            "  Please download the model from:\n"
            "    https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet\n"
            "  and place it at: %s",
            _YUNET_MODEL_PRIMARY,
            _YUNET_MODEL_FALLBACK,
            _YUNET_MODEL_PRIMARY,
        )
        return None
    try:
        return cv2.FaceDetectorYN_create(
            model=model_path,
            config="",
            input_size=(320, 320),
            score_threshold=_SCORE_THRESHOLD,
            nms_threshold=_NMS_THRESHOLD,
            top_k=_TOP_K,
        )
    except Exception:
        logger.exception("Failed to create FaceDetectorYN")
        return None


def _detect_faces(image: np.ndarray, detector) -> list:
    """Detect faces using YuNet. Returns list of (x, y, w, h, score)."""
    h, w = image.shape[:2]
    detector.setInputSize((w, h))
    retval, faces = detector.detect(image)

    if faces is None or len(faces) == 0:
        return []

    # faces shape: (N, 15) — cols 0-3: bbox, 4-13: landmarks, 14: score
    results = []
    for face in faces:
        x, y, fw, fh = face[0], face[1], face[2], face[3]
        score = face[14]
        results.append((int(x), int(y), int(fw), int(fh), float(score)))

    return results


def _select_largest_face(faces: list) -> Optional[tuple]:
    """Select the largest face by bounding-box area.

    Rationale: in identity documents and selfies the primary subject
    is typically the largest detected face. Secondary/background faces
    are ignored for the prototype.
    """
    if not faces:
        return None
    return max(faces, key=lambda f: f[2] * f[3])


def _crop_face(image: np.ndarray, face_rect: tuple, padding: float = 0.2) -> np.ndarray:
    """Crop face region with padding, clamped to image bounds."""
    x, y, w, h = face_rect[:4]
    img_h, img_w = image.shape[:2]

    pad_x = int(w * padding)
    pad_y = int(h * padding)

    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(img_w, x + w + pad_x)
    y2 = min(img_h, y + h + pad_y)

    return image[y1:y2, x1:x2]


def _standardize_face(face_img: np.ndarray) -> np.ndarray:
    """Resize and convert face to standard grayscale for comparison."""
    resized = cv2.resize(face_img, _COMPARE_SIZE, interpolation=cv2.INTER_AREA)
    if len(resized.shape) == 3:
        return cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    return resized


def _histogram_similarity(face_a: np.ndarray, face_b: np.ndarray) -> float:
    """Compare faces using colour histogram correlation (0–100)."""
    if len(face_a.shape) == 2:
        hist_a = cv2.calcHist([face_a], [0], None, [64], [0, 256])
        hist_b = cv2.calcHist([face_b], [0], None, [64], [0, 256])
    else:
        hist_a = cv2.calcHist(face_a, [0, 1, 2], None, _HIST_BINS,
                              [0, 256, 0, 256, 0, 256])
        hist_b = cv2.calcHist(face_b, [0, 1, 2], None, _HIST_BINS,
                              [0, 256, 0, 256, 0, 256])

    cv2.normalize(hist_a, hist_a)
    cv2.normalize(hist_b, hist_b)

    similarity = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    return max(0.0, min(100.0, (similarity + 1) * 50))


def _structural_similarity(face_a: np.ndarray, face_b: np.ndarray) -> float:
    """Compare faces using mean absolute difference (0–100)."""
    diff = cv2.absdiff(face_a, face_b)
    mean_diff = float(np.mean(diff))
    return max(0.0, (1.0 - mean_diff / 255.0) * 100)


def _pixel_difference_score(face_a: np.ndarray, face_b: np.ndarray) -> float:
    """Compare faces using SSIM-like metric (0–100)."""
    a = face_a.astype(np.float64)
    b = face_b.astype(np.float64)

    mu_a, mu_b = np.mean(a), np.mean(b)
    sigma_a, sigma_b = np.std(a), np.std(b)
    sigma_ab = np.mean((a - mu_a) * (b - mu_b))

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    ssim = ((2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)) / (
        (mu_a ** 2 + mu_b ** 2 + c1) * (sigma_a ** 2 + sigma_b ** 2 + c2)
    )
    return max(0.0, min(100.0, (ssim + 1) * 50))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_faces(
    document_image_path: str,
    selfie_image_path: str,
) -> dict:
    """Compare a face from an identity document against a selfie.

    Args:
        document_image_path: Path to the identity document image.
        selfie_image_path: Path to the selfie image.

    Returns:
        dict with keys:
            success (bool)
            status (str): MATCH | NO_MATCH | NO_FACE | ERROR
            similarity_score (int): 0–100
            face_detected_in_document (bool)
            face_detected_in_selfie (bool)
            message (str)
    """
    # --- Validate inputs ---
    if not document_image_path or not os.path.isfile(document_image_path):
        return {
            "success": False,
            "status": "ERROR",
            "similarity_score": 0,
            "face_detected_in_document": False,
            "face_detected_in_selfie": False,
            "message": "Identity document image not found or path is invalid",
        }

    if not selfie_image_path or not os.path.isfile(selfie_image_path):
        return {
            "success": False,
            "status": "ERROR",
            "similarity_score": 0,
            "face_detected_in_document": False,
            "face_detected_in_selfie": False,
            "message": "Selfie image not found or path is invalid",
        }

    # --- Load images ---
    doc_img = cv2.imread(document_image_path)
    selfie_img = cv2.imread(selfie_image_path)

    if doc_img is None:
        return {
            "success": False,
            "status": "ERROR",
            "similarity_score": 0,
            "face_detected_in_document": False,
            "face_detected_in_selfie": False,
            "message": "Failed to read identity document image (corrupt or unsupported format)",
        }

    if selfie_img is None:
        return {
            "success": False,
            "status": "ERROR",
            "similarity_score": 0,
            "face_detected_in_document": False,
            "face_detected_in_selfie": False,
            "message": "Failed to read selfie image (corrupt or unsupported format)",
        }

    # --- Load face detector ---
    detector = _get_detector()

    if detector is None:
        return {
            "success": False,
            "status": "ERROR",
            "similarity_score": 0,
            "face_detected_in_document": False,
            "face_detected_in_selfie": False,
            "message": "Face detection model not available",
        }

    # --- Detect faces ---
    doc_faces = _detect_faces(doc_img, detector)
    selfie_faces = _detect_faces(selfie_img, detector)

    face_in_doc = len(doc_faces) > 0
    face_in_selfie = len(selfie_faces) > 0

    logger.info(
        "Face detection: document=%d faces, selfie=%d faces",
        len(doc_faces), len(selfie_faces),
    )

    if not face_in_doc and not face_in_selfie:
        return {
            "success": False,
            "status": "NO_FACE",
            "similarity_score": 0,
            "face_detected_in_document": False,
            "face_detected_in_selfie": False,
            "message": "No face detected in either image",
        }

    if not face_in_doc:
        return {
            "success": False,
            "status": "NO_FACE",
            "similarity_score": 0,
            "face_detected_in_document": False,
            "face_detected_in_selfie": True,
            "message": "No face detected in identity document",
        }

    if not face_in_selfie:
        return {
            "success": False,
            "status": "NO_FACE",
            "similarity_score": 0,
            "face_detected_in_document": True,
            "face_detected_in_selfie": False,
            "message": "No face detected in selfie",
        }

    # --- Select largest face from each image ---
    doc_face = _select_largest_face(doc_faces)
    selfie_face = _select_largest_face(selfie_faces)

    if doc_face is None or selfie_face is None:
        return {
            "success": False,
            "status": "NO_FACE",
            "similarity_score": 0,
            "face_detected_in_document": face_in_doc,
            "face_detected_in_selfie": face_in_selfie,
            "message": "Could not isolate primary face in one or both images",
        }

    # --- Crop and standardise ---
    doc_face_crop = _crop_face(doc_img, doc_face)
    selfie_face_crop = _crop_face(selfie_img, selfie_face)

    doc_std = _standardize_face(doc_face_crop)
    selfie_std = _standardize_face(selfie_face_crop)

    # --- Multi-metric comparison ---
    hist_score = _histogram_similarity(doc_face_crop, selfie_face_crop)
    struct_score = _structural_similarity(doc_std, selfie_std)
    pixel_score = _pixel_difference_score(doc_std, selfie_std)

    raw_score = (
        hist_score * _WEIGHT_HISTOGRAM
        + struct_score * _WEIGHT_STRUCTURAL
        + pixel_score * _WEIGHT_PIXEL_DIFF
    )

    similarity = int(round(min(100.0, max(0.0, raw_score))))

    logger.info(
        "Face comparison: hist=%.1f struct=%.1f pixel=%.1f → final=%d",
        hist_score, struct_score, pixel_score, similarity,
    )

    # --- Determine status ---
    if similarity >= _MATCH_THRESHOLD:
        status = "MATCH"
        message = (
            "Faces match with high confidence"
            if similarity >= _HIGH_CONFIDENCE
            else "Faces match"
        )
    else:
        status = "NO_MATCH"
        message = (
            "Faces do not match"
            if similarity < _LOW_CONFIDENCE
            else "Faces may not match — manual review recommended"
        )

    return {
        "success": True,
        "status": status,
        "similarity_score": similarity,
        "face_detected_in_document": True,
        "face_detected_in_selfie": True,
        "message": message,
    }
