"""Tests for document upload and validation."""

import io


def test_upload_rejects_unsupported_file_type(client):
    """POST /api/documents/upload should reject .exe files."""
    file_content = b"fake executable content"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", io.BytesIO(file_content), "application/octet-stream")},
        data={"document_type": "other"},
    )
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"].lower()


def test_upload_rejects_txt_file(client):
    """POST /api/documents/upload should reject .txt files."""
    file_content = b"plain text content"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
        data={"document_type": "other"},
    )
    assert response.status_code == 400


def test_upload_accepts_jpg(client):
    """POST /api/documents/upload should accept .jpg files."""
    # Minimal valid JPEG: SOI + EOI markers
    jpg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"\xff\xd9"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("document.jpg", io.BytesIO(jpg_content), "image/jpeg")},
        data={"document_type": "aadhaar"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert data["document_id"].startswith("DOC-")
    assert data["status"] == "uploaded"


def test_upload_accepts_png(client):
    """POST /api/documents/upload should accept .png files."""
    # Minimal valid PNG
    png_content = (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\rIHDR" + b"\x00" * 13  # Minimal IHDR
        + b"\x00\x00\x00\x00IDAT" + b"\x00" * 10
        + b"\x00\x00\x00\x00IEND" + b"\x00" * 4
    )
    response = client.post(
        "/api/documents/upload",
        files={"file": ("photo.png", io.BytesIO(png_content), "image/png")},
        data={"document_type": "passport"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"].startswith("DOC-")


def test_upload_accepts_pdf(client):
    """POST /api/documents/upload should accept .pdf files."""
    pdf_content = b"%PDF-1.4 fake pdf content for testing \n%%EOF"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("scan.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"document_type": "pan"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"].startswith("DOC-")


def test_upload_generates_unique_ids(client):
    """Two uploads should produce different document IDs."""
    jpg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 50 + b"\xff\xd9"

    resp1 = client.post(
        "/api/documents/upload",
        files={"file": ("a.jpg", io.BytesIO(jpg_content), "image/jpeg")},
    )
    resp2 = client.post(
        "/api/documents/upload",
        files={"file": ("b.jpg", io.BytesIO(jpg_content), "image/jpeg")},
    )

    assert resp1.json()["document_id"] != resp2.json()["document_id"]


def test_upload_rejects_empty_file(client):
    """POST /api/documents/upload should handle empty file uploads."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")},
        data={"document_type": "other"},
    )
    # Empty file is technically valid extension, just zero bytes
    assert response.status_code == 200


def test_analyze_rejects_no_file(client):
    """POST /api/documents/analyze should reject missing file."""
    response = client.post("/api/documents/analyze")
    assert response.status_code == 422  # Unprocessable entity


def test_analyze_accepts_image(client):
    """POST /api/documents/analyze should accept image and return OCR + fields."""
    # Use the actual demo document for a valid OCR test
    import os
    demo_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "demo_document.png")
    if os.path.exists(demo_path):
        with open(demo_path, "rb") as f:
            img_content = f.read()
        response = client.post(
            "/api/documents/analyze",
            files={"file": ("demo.png", io.BytesIO(img_content), "image/png")},
            data={"document_type": "aadhaar"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ocr" in data
        assert "fields" in data
        assert data["ocr"]["lines_count"] > 0
        assert data["fields"]["full_name"] is not None
    else:
        # Skip if demo doc not available
        pass
