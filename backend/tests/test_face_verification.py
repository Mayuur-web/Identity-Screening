"""Tests for face_verification_service.

Uses synthetic test images created with OpenCV. The YuNet DNN detector
is tested against images that contain simple face-like structures;
results are verified for structural correctness rather than perfect
detection accuracy.
"""

import os
import tempfile

import cv2
import numpy as np
import pytest

from app.services.face_verification_service import (
    verify_faces,
    _detect_faces,
    _select_largest_face,
    _get_detector,
    _standardize_face,
    _histogram_similarity,
    _structural_similarity,
    _pixel_difference_score,
)


# ---------------------------------------------------------------------------
# Helpers — synthetic image creation
# ---------------------------------------------------------------------------

def _create_face_image(
    size=(400, 400),
    bg_color=(200, 200, 200),
    face_color=(180, 150, 130),
    eye_color=(50, 50, 50),
    offset=(0, 0),
) -> np.ndarray:
    """Create a synthetic face-like image with oval, eyes, nose, mouth."""
    img = np.full((*size, 3), bg_color, dtype=np.uint8)

    cx = size[0] // 2 + offset[0]
    cy = size[1] // 2 + offset[1]

    # Face oval
    cv2.ellipse(img, (cx, cy), (60, 80), 0, 0, 360, face_color, -1)

    # Eyes (white + pupil)
    eye_y = cy - 20
    cv2.circle(img, (cx - 25, eye_y), 12, (255, 255, 255), -1)
    cv2.circle(img, (cx + 25, eye_y), 12, (255, 255, 255), -1)
    cv2.circle(img, (cx - 25, eye_y), 6, eye_color, -1)
    cv2.circle(img, (cx + 25, eye_y), 6, eye_color, -1)

    # Nose
    cv2.line(img, (cx, cy - 5), (cx - 3, cy + 15), (150, 120, 100), 2)

    # Mouth
    cv2.ellipse(img, (cx, cy + 30), (20, 10), 0, 0, 180, (100, 60, 60), 2)

    # Hair
    cv2.ellipse(img, (cx, cy - 50), (65, 30), 0, 180, 360, (60, 40, 30), -1)

    return img


def _create_blank_image(size=(400, 400), color=(200, 200, 200)) -> np.ndarray:
    """Create a plain image with no face."""
    return np.full((*size, 3), color, dtype=np.uint8)


def _save_temp_image(img: np.ndarray, suffix: str = ".png") -> str:
    """Save image to a temp file and return the path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    cv2.imwrite(path, img)
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def face_image_a():
    """A synthetic face image."""
    img = _create_face_image()
    path = _save_temp_image(img)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def face_image_b():
    """A slightly different synthetic face image."""
    img = _create_face_image(face_color=(170, 130, 110))
    path = _save_temp_image(img)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def no_face_image():
    """An image with no face."""
    img = _create_blank_image()
    path = _save_temp_image(img)
    yield path
    if os.path.exists(path):
        os.unlink(path)


# ---------------------------------------------------------------------------
# Internal helper tests
# ---------------------------------------------------------------------------

class TestDetector:
    def test_get_detector_returns_instance(self):
        """_get_detector should return a FaceDetectorYN or None."""
        detector = _get_detector()
        assert detector is None or hasattr(detector, "detect")

    def test_detect_faces_returns_list(self, face_image_a):
        """_detect_faces should return a list."""
        img = cv2.imread(face_image_a)
        detector = _get_detector()
        if detector is None:
            pytest.skip("YuNet model not available")
        result = _detect_faces(img, detector)
        assert isinstance(result, list)

    def test_detect_faces_on_blank_image(self, no_face_image):
        """Blank image should return no faces."""
        img = cv2.imread(no_face_image)
        detector = _get_detector()
        if detector is None:
            pytest.skip("YuNet model not available")
        result = _detect_faces(img, detector)
        assert isinstance(result, list)
        assert len(result) == 0


class TestSelectLargestFace:
    def test_select_largest_face_empty(self):
        """Empty list should return None."""
        assert _select_largest_face([]) is None

    def test_select_largest_face_single(self):
        """Single face should be returned."""
        faces = [(10, 10, 50, 50, 0.9)]
        result = _select_largest_face(faces)
        assert result == (10, 10, 50, 50, 0.9)

    def test_select_largest_face_picks_biggest(self):
        """Should pick the face with largest area."""
        faces = [
            (0, 0, 30, 30, 0.8),   # area = 900
            (10, 10, 80, 80, 0.9),  # area = 6400
            (5, 5, 40, 40, 0.85),   # area = 1600
        ]
        result = _select_largest_face(faces)
        assert result[0] == 10 and result[1] == 10


class TestStandardizeFace:
    def test_standardize_returns_grayscale(self):
        """Should return a 100x100 grayscale image."""
        img = np.full((200, 200, 3), 128, dtype=np.uint8)
        result = _standardize_face(img)
        assert result.shape == (100, 100)
        assert len(result.shape) == 2


class TestSimilarityMetrics:
    def test_identical_images_high_similarity(self):
        """Identical images should have very high similarity."""
        img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        hist = _histogram_similarity(img, img)
        struct = _structural_similarity(img, img)
        pixel = _pixel_difference_score(img, img)

        assert hist >= 95
        assert struct >= 95
        assert pixel >= 95

    def test_different_images_lower_similarity(self):
        """Very different images should have lower similarity."""
        img_a = np.zeros((100, 100), dtype=np.uint8)
        img_b = np.full((100, 100), 255, dtype=np.uint8)

        hist = _histogram_similarity(img_a, img_b)
        struct = _structural_similarity(img_a, img_b)
        pixel = _pixel_difference_score(img_a, img_b)

        assert hist < 80
        assert struct < 80
        assert pixel < 80


# ---------------------------------------------------------------------------
# Main API tests
# ---------------------------------------------------------------------------

class TestVerifyFaces:
    def test_valid_images_returns_dict(self, face_image_a, face_image_b):
        """Two valid images should return a result dict."""
        result = verify_faces(face_image_a, face_image_b)
        assert isinstance(result, dict)
        for key in ("success", "status", "similarity_score",
                     "face_detected_in_document", "face_detected_in_selfie",
                     "message"):
            assert key in result

    def test_similarity_score_range(self, face_image_a, face_image_b):
        """Similarity score must be 0–100."""
        result = verify_faces(face_image_a, face_image_b)
        assert 0 <= result["similarity_score"] <= 100

    def test_status_is_valid_value(self, face_image_a, face_image_b):
        """Status must be one of the defined values."""
        result = verify_faces(face_image_a, face_image_b)
        assert result["status"] in ("MATCH", "NO_MATCH", "NO_FACE", "ERROR")

    def test_missing_document_image(self, face_image_b):
        """Missing document image should return ERROR."""
        result = verify_faces("/nonexistent/path.png", face_image_b)
        assert result["success"] is False
        assert result["status"] == "ERROR"
        assert result["face_detected_in_document"] is False
        assert result["similarity_score"] == 0

    def test_missing_selfie(self, face_image_a):
        """Missing selfie should return ERROR."""
        result = verify_faces(face_image_a, "/nonexistent/selfie.png")
        assert result["success"] is False
        assert result["status"] == "ERROR"
        assert result["face_detected_in_selfie"] is False
        assert result["similarity_score"] == 0

    def test_both_missing(self):
        """Both paths missing should return ERROR."""
        result = verify_faces("/a.png", "/b.png")
        assert result["success"] is False
        assert result["status"] == "ERROR"

    def test_none_paths(self):
        """None paths should return ERROR."""
        result = verify_faces(None, None)
        assert result["success"] is False
        assert result["status"] == "ERROR"

    def test_empty_string_paths(self):
        """Empty string paths should return ERROR."""
        result = verify_faces("", "")
        assert result["success"] is False
        assert result["status"] == "ERROR"

    def test_no_face_in_document(self, no_face_image, face_image_a):
        """No face in document should return NO_FACE."""
        result = verify_faces(no_face_image, face_image_a)
        assert result["success"] is False
        assert result["status"] == "NO_FACE"
        assert result["face_detected_in_document"] is False

    def test_no_face_in_selfie(self, face_image_a, no_face_image):
        """No face in selfie should return NO_FACE."""
        result = verify_faces(face_image_a, no_face_image)
        assert result["success"] is False
        assert result["status"] == "NO_FACE"
        assert result["face_detected_in_selfie"] is False

    def test_no_face_in_both(self, no_face_image):
        """No face in either image should return NO_FACE."""
        img2 = _create_blank_image(color=(150, 150, 150))
        path2 = _save_temp_image(img2)
        try:
            result = verify_faces(no_face_image, path2)
            assert result["success"] is False
            assert result["status"] == "NO_FACE"
            assert result["face_detected_in_document"] is False
            assert result["face_detected_in_selfie"] is False
        finally:
            if os.path.exists(path2):
                os.unlink(path2)

    def test_response_structure_complete(self, face_image_a, face_image_b):
        """Response should contain all required keys."""
        result = verify_faces(face_image_a, face_image_b)
        required_keys = {
            "success", "status", "similarity_score",
            "face_detected_in_document", "face_detected_in_selfie",
            "message",
        }
        assert required_keys.issubset(result.keys())

    def test_similarity_is_integer(self, face_image_a, face_image_b):
        """Similarity score should be an integer."""
        result = verify_faces(face_image_a, face_image_b)
        assert isinstance(result["similarity_score"], int)

    def test_message_is_string(self, face_image_a, face_image_b):
        """Message should be a non-empty string."""
        result = verify_faces(face_image_a, face_image_b)
        assert isinstance(result["message"], str)
        assert len(result["message"]) > 0

    def test_same_image_high_similarity(self, face_image_a):
        """Same image compared to itself should yield high similarity."""
        result = verify_faces(face_image_a, face_image_a)
        if result["success"]:
            assert result["similarity_score"] >= 70

    def test_corrupt_image_file(self, face_image_a):
        """A corrupt/non-image file should return ERROR."""
        fd, corrupt_path = tempfile.mkstemp(suffix=".png")
        os.write(fd, b"this is not an image")
        os.close(fd)
        try:
            result = verify_faces(face_image_a, corrupt_path)
            assert result["success"] is False
            assert result["status"] == "ERROR"
        finally:
            if os.path.exists(corrupt_path):
                os.unlink(corrupt_path)

    def test_both_false_returns_error(self):
        """Both invalid paths should return ERROR with both flags false."""
        result = verify_faces("/no/such/file1.png", "/no/such/file2.png")
        assert result["success"] is False
        assert result["face_detected_in_document"] is False
        assert result["face_detected_in_selfie"] is False
