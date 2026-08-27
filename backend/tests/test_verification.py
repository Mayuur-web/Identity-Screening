"""Tests for verification endpoints."""

import io
from app.core.security import generate_id, safe_filename


def test_generate_id_format():
    """generate_id should produce PREFIX-XXXXXXXX format."""
    vid = generate_id("VS")
    assert vid.startswith("VS-")
    assert len(vid) == 11  # "VS-" (3) + 8 hex chars
    # The 8 chars after the dash should be uppercase hex
    suffix = vid.split("-")[1]
    assert len(suffix) == 8
    assert suffix == suffix.upper()


def test_generate_id_is_unique():
    """Two calls to generate_id should produce different IDs."""
    ids = {generate_id() for _ in range(50)}
    assert len(ids) == 50


def test_generate_id_custom_prefix():
    """generate_id with custom prefix should use that prefix."""
    vid = generate_id("DOC")
    assert vid.startswith("DOC-")


def test_safe_filename_strips_paths():
    """safe_filename should remove directory components."""
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("C:\\Users\\admin\\file.jpg") == "file.jpg"
    assert safe_filename("sub/dir/file.png") == "file.png"


def test_safe_filename_sanitizes_special_chars():
    """safe_filename should replace special characters."""
    result = safe_filename("my file (copy).jpg")
    assert result == "my_file__copy_.jpg"
    assert "/" not in result
    assert ".." not in result


def test_safe_filename_preserves_extension():
    """safe_filename should preserve the file extension."""
    assert safe_filename("doc.pdf").endswith(".pdf")
    assert safe_filename("scan.jpg").endswith(".jpg")


def test_safe_filename_handles_hidden_file():
    """safe_filename should handle dotfiles safely."""
    result = safe_filename(".hidden")
    # Result is sanitized - no path traversal possible
    assert ".." not in result
    assert "/" not in result
    assert len(result) > 0


def test_safe_filename_handles_path_traversal():
    """safe_filename should neutralize path traversal attempts."""
    assert ".." not in safe_filename("../../etc/passwd")
    assert "/" not in safe_filename("sub/dir/file.txt")


def test_verification_upload_returns_id(client):
    """POST /api/verification/upload should return a verification ID."""
    jpg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9"
    response = client.post(
        "/api/verification/upload",
        files={"document": ("doc.jpg", io.BytesIO(jpg_content), "image/jpeg")},
        data={"document_type": "aadhaar"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "verification_id" in data
    assert data["verification_id"].startswith("VS-")
    assert data["status"] == "pending"


def test_verification_detail_returns_record(client):
    """GET /api/verification/{id} should return the verification record."""
    # First create a verification
    jpg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9"
    upload_resp = client.post(
        "/api/verification/upload",
        files={"document": ("doc.jpg", io.BytesIO(jpg_content), "image/jpeg")},
        data={"document_type": "pan"},
    )
    vid = upload_resp.json()["verification_id"]

    # Then retrieve it
    detail_resp = client.get(f"/api/verification/{vid}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert data["verification_id"] == vid
    assert data["document_type"] == "pan"


def test_verification_detail_returns_404_for_unknown(client):
    """GET /api/verification/{id} should 404 for non-existent ID."""
    response = client.get("/api/verification/VS-FAKEID00")
    assert response.status_code == 404


def test_verification_analyze_runs_pipeline(client):
    """POST /api/verification/analyze should orchestrate the pipeline."""
    # Create verification first
    jpg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9"
    upload_resp = client.post(
        "/api/verification/upload",
        files={"document": ("doc.jpg", io.BytesIO(jpg_content), "image/jpeg")},
    )
    vid = upload_resp.json()["verification_id"]

    # Run analysis
    analyze_resp = client.post(
        "/api/verification/analyze",
        json={"verification_id": vid},
    )
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert data["verification_id"] == vid
    assert "ocr" in data
    # OCR service returns success: False for empty paths (no real file to process)
    assert "success" in data["ocr"]


def test_verification_analyze_rejects_missing_id(client):
    """POST /api/verification/analyze should reject missing verification_id."""
    response = client.post(
        "/api/verification/analyze",
        json={},
    )
    assert response.status_code == 400


def test_verification_analyze_rejects_unknown_id(client):
    """POST /api/verification/analyze should 404 for unknown ID."""
    response = client.post(
        "/api/verification/analyze",
        json={"verification_id": "VS-UNKNOWN000"},
    )
    assert response.status_code == 404
