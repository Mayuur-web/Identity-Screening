"""Tests for MRZ detection, image preprocessing, and OCR pipeline."""

import os
import pytest
from app.services.mrz_service import detect_mrz, is_mrz_line, parse_mrz_passport
from app.services.image_preprocessing import (
    auto_rotate, upscale_if_small, to_grayscale,
    enhance_contrast, create_preprocessing_variants,
)


# --- MRZ Tests ---

class TestMRZDetection:
    def test_mrz_detected_in_passport_lines(self):
        """MRZ should be detected from passport-style lines."""
        lines = [
            {"text": "REPUBLIC OF INDIA", "confidence": 0.95},
            {"text": "PASSPORT", "confidence": 0.98},
            {"text": "SAIVARAJ", "confidence": 0.92},
            {"text": "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<", "confidence": 0.90},
            {"text": "W119276408IND8305202M2501010<<<<<<<<<<<<<<02", "confidence": 0.88},
        ]
        result = detect_mrz(lines)
        assert result["detected"] is True
        assert result["line1"] is not None
        assert result["line2"] is not None
        assert "P<IND" in result["line1"] or "P<" in result["line1"]

    def test_mrz_not_detected_when_no_mrz(self):
        """MRZ should not be detected for non-passport documents."""
        lines = [
            {"text": "Republic of India", "confidence": 0.95},
            {"text": "Name: PRIYA SHARMA", "confidence": 0.98},
            {"text": "Date of Birth: 15-MAR-1995", "confidence": 0.92},
        ]
        result = detect_mrz(lines)
        assert result["detected"] is False
        assert result["line1"] is None
        assert result["line2"] is None

    def test_mrz_empty_lines(self):
        result = detect_mrz([])
        assert result["detected"] is False

    def test_mrz_single_line_only(self):
        lines = [{"text": "P<INDSOMENAME<<<<<<<<<<<<<<<<<<<<<<<<<<<", "confidence": 0.85}]
        result = detect_mrz(lines)
        assert result["detected"] is False


class TestMRZParsing:
    def test_parse_passport_mrz(self):
        """Parse a valid TD3 passport MRZ."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "line2": "W119276408IND8305202M2501010<<<<<<<<<<<<<<02",
            "confidence": 0.89,
        }
        fields = parse_mrz_passport(mrz_data)
        assert fields["passport_number"] is not None
        assert len(fields["passport_number"]) >= 6
        assert fields["nationality"] == "IND"
        assert fields["date_of_birth"] == "1983-05-20"
        assert fields["sex"] == "M"
        assert fields["surname"] is not None or fields["given_names"] is not None

    def test_parse_mrz_not_detected(self):
        mrz_data = {"detected": False, "line1": None, "line2": None, "confidence": None}
        fields = parse_mrz_passport(mrz_data)
        assert fields["passport_number"] is None


class TestMRZLineDetection:
    def test_valid_mrz_line(self):
        assert is_mrz_line("P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<") is True

    def test_invalid_mrz_line_too_short(self):
        assert is_mrz_line("Hello") is False

    def test_invalid_mrz_line_empty(self):
        assert is_mrz_line("") is False

    def test_invalid_mrz_line_lowercase(self):
        assert is_mrz_line("this is not an mrz line") is False


# --- Image Preprocessing Tests ---

class TestPreprocessing:
    def test_auto_rotate_portrait(self):
        """Portrait images should be rotated."""
        import numpy as np
        img = np.zeros((200, 100, 3), dtype=np.uint8)
        rotated = auto_rotate(img)
        assert rotated.shape[1] >= rotated.shape[0]

    def test_auto_rotate_landscape(self):
        """Landscape images should NOT be rotated."""
        import numpy as np
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        rotated = auto_rotate(img)
        assert rotated.shape == img.shape

    def test_upscale_small_image(self):
        import numpy as np
        img = np.zeros((100, 500, 3), dtype=np.uint8)
        upscaled = upscale_if_small(img, min_width=1200)
        assert upscaled.shape[1] >= 1200

    def test_upscale_large_image_unchanged(self):
        import numpy as np
        img = np.zeros((100, 1500, 3), dtype=np.uint8)
        upscaled = upscale_if_small(img, min_width=1200)
        assert upscaled.shape[1] == 1500

    def test_grayscale_conversion(self):
        import numpy as np
        color = np.zeros((100, 100, 3), dtype=np.uint8)
        gray = to_grayscale(color)
        assert len(gray.shape) == 2

    def test_grayscale_already_gray(self):
        import numpy as np
        gray = np.zeros((100, 100), dtype=np.uint8)
        result = to_grayscale(gray)
        assert result.shape == gray.shape

    def test_enhance_contrast(self):
        import numpy as np
        gray = np.ones((100, 100), dtype=np.uint8) * 128
        enhanced = enhance_contrast(gray)
        assert enhanced.shape == gray.shape


class TestPreprocessingVariants:
    def test_creates_two_variants(self):
        """Should create exactly 2 preprocessing variants."""
        demo_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "demo_document.png")
        if not os.path.exists(demo_path):
            pytest.skip("Demo document not found")

        result = create_preprocessing_variants(demo_path)
        assert len(result["variants"]) == 2
        names = [v["name"] for v in result["variants"]]
        assert "preprocessed" in names
        assert "gray_contrast" in names
        assert len(result["preprocessing_applied"]) >= 1

        # Cleanup
        from app.services.image_preprocessing import cleanup_temp_files
        cleanup_temp_files(demo_path)


# --- OCR Pipeline Integration Test ---

class TestOCRPipeline:
    def test_multi_pass_ocr_on_demo_document(self):
        """Full OCR pipeline should produce results on the demo document."""
        from app.services.ocr_service import extract_text_sync
        demo_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "demo_document.png")
        if not os.path.exists(demo_path):
            pytest.skip("Demo document not found")

        result = extract_text_sync(demo_path)
        assert result["success"] is True
        assert len(result["lines"]) > 0
        assert result["average_confidence"] is not None
        assert result["passes_run"] >= 1
        assert len(result["preprocessing_applied"]) >= 1
