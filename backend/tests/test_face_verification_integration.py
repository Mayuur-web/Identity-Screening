"""Integration tests for face verification in POST /api/documents/verify.

Tests the optional selfie parameter and face verification check
without modifying existing Aadhaar/passport verification logic.
"""

import io
import os
import tempfile

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_image_bytes(
    size=(400, 400),
    bg=(200, 200, 200),
    face_color=(180, 150, 130),
) -> bytes:
    """Create a synthetic image and return as PNG bytes."""
    img = np.full((*size, 3), bg, dtype=np.uint8)
    cx, cy = size[0] // 2, size[1] // 2

    # Face oval
    cv2.ellipse(img, (cx, cy), (60, 80), 0, 0, 360, face_color, -1)
    # Eyes
    cv2.circle(img, (cx - 25, cy - 20), 12, (255, 255, 255), -1)
    cv2.circle(img, (cx + 25, cy - 20), 12, (255, 255, 255), -1)
    cv2.circle(img, (cx - 25, cy - 20), 6, (50, 50, 50), -1)
    cv2.circle(img, (cx + 25, cy - 20), 6, (50, 50, 50), -1)
    # Mouth
    cv2.ellipse(img, (cx, cy + 30), (20, 10), 0, 0, 180, (100, 60, 60), 2)
    # Hair
    cv2.ellipse(img, (cx, cy - 50), (65, 30), 0, 180, 360, (60, 40, 30), -1)

    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _create_blank_image_bytes(size=(400, 400), color=(200, 200, 200)) -> bytes:
    """Create a plain image with no face."""
    img = np.full((*size, 3), color, dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _verify_with_optional_selfie(
    doc_bytes: bytes,
    doc_name: str = "test_doc.png",
    doc_type: str = "aadhaar",
    selfie_bytes: bytes | None = None,
    selfie_name: str = "selfie.png",
):
    """Call POST /api/documents/verify with optional selfie."""
    files = {"file": (doc_name, io.BytesIO(doc_bytes), "image/png")}
    if selfie_bytes is not None:
        files["selfie"] = (selfie_name, io.BytesIO(selfie_bytes), "image/png")

    data = {"document_type": doc_type}
    return client.post("/api/documents/verify", files=files, data=data)


# ---------------------------------------------------------------------------
# Tests — backward compatibility (no selfie)
# ---------------------------------------------------------------------------

class TestVerifyWithoutSelfie:
    """Existing verification behavior must remain unchanged."""

    def test_no_selfie_returns_200(self):
        """Verification without selfie should still work."""
        doc = _create_image_bytes()
        resp = _verify_with_optional_selfie(doc, doc_type="aadhaar")
        assert resp.status_code == 200

    def test_no_selfie_face_status_not_provided(self):
        """Face verification should show NOT_PROVIDED when no selfie."""
        doc = _create_image_bytes()
        resp = _verify_with_optional_selfie(doc, doc_type="aadhaar")
        body = resp.json()
        assert body["face_verification"]["status"] == "NOT_PROVIDED"
        assert body["face_verification"]["similarity_score"] is None
        assert "not provided" in body["face_verification"]["message"].lower()

    def test_no_selfie_face_check_not_checked(self):
        """Face Match check should be not_checked without selfie."""
        doc = _create_image_bytes()
        resp = _verify_with_optional_selfie(doc, doc_type="aadhaar")
        body = resp.json()
        face_checks = [
            c for c in body["checks"] if c["name"] == "Face Match"
        ]
        assert len(face_checks) == 1
        assert face_checks[0]["status"] == "not_checked"

    def test_no_selfie_response_has_face_verification_key(self):
        """Response must always contain face_verification key."""
        doc = _create_image_bytes()
        resp = _verify_with_optional_selfie(doc, doc_type="aadhaar")
        body = resp.json()
        assert "face_verification" in body
        fv = body["face_verification"]
        assert "status" in fv
        assert "similarity_score" in fv
        assert "face_detected_in_document" in fv
        assert "face_detected_in_selfie" in fv
        assert "message" in fv

    def test_response_still_has_all_original_keys(self):
        """All original response keys must still be present."""
        doc = _create_image_bytes()
        resp = _verify_with_optional_selfie(doc, doc_type="aadhaar")
        body = resp.json()
        for key in (
            "success", "document_id", "document_type", "status",
            "score", "checks", "reasons", "fields", "ocr",
        ):
            assert key in body, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Tests — with selfie
# ---------------------------------------------------------------------------

class TestVerifyWithSelfie:
    """Face verification when selfie is provided."""

    def test_with_selfie_returns_200(self):
        """Verification with selfie should succeed."""
        doc = _create_image_bytes()
        selfie = _create_image_bytes(face_color=(170, 130, 110))
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        assert resp.status_code == 200

    def test_with_selfie_face_verification_structure(self):
        """Face verification should have proper structure."""
        doc = _create_image_bytes()
        selfie = _create_image_bytes(face_color=(170, 130, 110))
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        body = resp.json()
        fv = body["face_verification"]
        assert fv["status"] in ("MATCH", "NO_MATCH", "NO_FACE", "ERROR")
        assert isinstance(fv["similarity_score"], int)
        assert isinstance(fv["face_detected_in_document"], bool)
        assert isinstance(fv["face_detected_in_selfie"], bool)
        assert isinstance(fv["message"], str)

    def test_with_selfie_similarity_in_range(self):
        """Similarity score must be 0-100."""
        doc = _create_image_bytes()
        selfie = _create_image_bytes(face_color=(170, 130, 110))
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        body = resp.json()
        score = body["face_verification"]["similarity_score"]
        assert 0 <= score <= 100

    def test_with_selfie_face_check_present(self):
        """Face Match check should be in the checks list."""
        doc = _create_image_bytes()
        selfie = _create_image_bytes(face_color=(170, 130, 110))
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        body = resp.json()
        face_checks = [
            c for c in body["checks"] if c["name"] == "Face Match"
        ]
        assert len(face_checks) == 1
        assert face_checks[0]["status"] in ("passed", "failed", "not_checked")

    def test_match_check_message_contains_percentage(self):
        """MATCH check message should contain similarity percentage."""
        doc = _create_image_bytes()
        selfie = _create_image_bytes(face_color=(180, 150, 130))
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        body = resp.json()
        face_check = next(
            c for c in body["checks"] if c["name"] == "Face Match"
        )
        if face_check["status"] == "passed":
            assert "%" in face_check["message"]

    def test_no_match_check_message(self):
        """NO_MATCH check should show 'do not match' or percentage."""
        doc = _create_image_bytes(size=(400, 400))
        # Very different selfie (different size, different colour)
        selfie = _create_blank_image_bytes(size=(200, 200), color=(50, 50, 50))
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        body = resp.json()
        face_check = next(
            c for c in body["checks"] if c["name"] == "Face Match"
        )
        # Should be failed (no match or no face)
        assert face_check["status"] == "failed"


# ---------------------------------------------------------------------------
# Tests — edge cases
# ---------------------------------------------------------------------------

class TestVerifyEdgeCases:
    """Edge cases for face verification integration."""

    def test_invalid_selfie_file(self):
        """Corrupt selfie should not break verification."""
        doc = _create_image_bytes()
        resp = client.post(
            "/api/documents/verify",
            files={
                "file": ("doc.png", io.BytesIO(doc), "image/png"),
                "selfie": ("bad.png", io.BytesIO(b"not an image"), "image/png"),
            },
            data={"document_type": "aadhaar"},
        )
        assert resp.status_code == 200
        body = resp.json()
        fv = body["face_verification"]
        # Should handle gracefully — either ERROR or NO_FACE
        assert fv["status"] in ("ERROR", "NO_FACE", "MATCH", "NO_MATCH")

    def test_selfie_with_no_face(self):
        """Selfie with no face should show NO_FACE in face verification."""
        doc = _create_image_bytes()
        selfie = _create_blank_image_bytes()
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        assert resp.status_code == 200
        body = resp.json()
        fv = body["face_verification"]
        assert fv["face_detected_in_selfie"] is False

    def test_empty_selfie_filename(self):
        """Empty selfie filename should be treated as no selfie."""
        doc = _create_image_bytes()
        selfie = _create_image_bytes()
        resp = client.post(
            "/api/documents/verify",
            files={
                "file": ("doc.png", io.BytesIO(doc), "image/png"),
                "selfie": ("", io.BytesIO(selfie), "image/png"),
            },
            data={"document_type": "aadhaar"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["face_verification"]["status"] == "NOT_PROVIDED"

    def test_temp_selfie_cleanup(self):
        """Selfie file should be deleted after processing."""
        doc = _create_image_bytes()
        selfie = _create_image_bytes()
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        assert resp.status_code == 200
        # Check no selfie files remain in uploads
        upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "uploads"
        )
        if os.path.isdir(upload_dir):
            selfie_files = [
                f for f in os.listdir(upload_dir) if "selfie" in f
            ]
            assert len(selfie_files) == 0, (
                f"Selfie files not cleaned up: {selfie_files}"
            )

    def test_face_check_added_to_verification_checks(self):
        """Face Match check should appear in verification checks."""
        doc = _create_image_bytes()
        selfie = _create_image_bytes()
        resp = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        body = resp.json()
        check_names = [c["name"] for c in body["checks"]]
        assert "Face Match" in check_names

    def test_face_verification_independent_of_doc_verification(self):
        """Face verification should not change the document verification score."""
        doc = _create_image_bytes()

        # Without selfie
        resp1 = _verify_with_optional_selfie(doc)
        body1 = resp1.json()
        score1 = body1["score"]
        status1 = body1["status"]

        # With selfie
        selfie = _create_image_bytes()
        resp2 = _verify_with_optional_selfie(doc, selfie_bytes=selfie)
        body2 = resp2.json()
        score2 = body2["score"]
        status2 = body2["status"]

        # Document verification score/status should be the same
        # (face check is appended but doesn't affect the main score)
        assert score1 == score2
        assert status1 == status2
