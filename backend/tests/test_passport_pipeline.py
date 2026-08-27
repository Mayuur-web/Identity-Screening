"""Comprehensive passport MRZ and extraction tests.

Tests the complete passport pipeline:
- MRZ image extraction (crop, upscale, OCR)
- MRZ line detection
- MRZ parsing (TD3 format)
- Passport field extraction (MRZ priority)
- Visual + MRZ consistency/conflict
- Garbage OCR must not override valid MRZ
"""

import pytest
from app.services.mrz_service import (
    detect_mrz, parse_mrz_passport, is_mrz_line,
    extract_mrz_from_image,
)
from app.services.field_extraction_service import extract_passport_fields


# =============================================================================
# MRZ Line Detection
# =============================================================================

class TestMRZLineDetection:
    """Test MRZ line detection from OCR output."""

    def test_valid_mrz_lines(self):
        lines = [
            {"text": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<", "confidence": 0.90},
            {"text": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8", "confidence": 0.88},
        ]
        result = detect_mrz(lines)
        assert result["detected"] is True
        assert result["line1"] is not None
        assert result["line2"] is not None

    def test_mrz_with_missing_trailing_padding(self):
        """MRZ lines shorter than 44 chars (OCR trimmed trailing <)."""
        lines = [
            {"text": "P<INDSHARMA<<RAHUL<KUMAR", "confidence": 0.90},
            {"text": "Z1234567<4IND9508157M3107199", "confidence": 0.88},
        ]
        result = detect_mrz(lines)
        assert result["detected"] is True

    def test_no_mrz_when_absent(self):
        lines = [
            {"text": "Name: JOHN DOE", "confidence": 0.95},
            {"text": "DOB: 01/01/1990", "confidence": 0.93},
        ]
        result = detect_mrz(lines)
        assert result["detected"] is False

    def test_mrz_empty_lines(self):
        result = detect_mrz([])
        assert result["detected"] is False

    def test_mrz_single_line(self):
        lines = [{"text": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<", "confidence": 0.90}]
        result = detect_mrz(lines)
        assert result["detected"] is False


# =============================================================================
# MRZ Parsing
# =============================================================================

class TestMRZParsing:
    """Test TD3 passport MRZ parsing."""

    def test_parse_full_passport(self):
        """Parse the expected passport MRZ."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        fields = parse_mrz_passport(mrz_data)
        assert fields["surname"] == "Sharma"
        assert fields["given_names"] == "Rahul Kumar"
        assert fields["passport_number"] == "Z1234567"
        assert fields["nationality"] == "IND"
        assert fields["date_of_birth"] == "1995-08-15"
        assert fields["sex"] == "M"
        assert fields["date_of_expiry"] == "2031-07-19"

    def test_parse_passport_number(self):
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        fields = parse_mrz_passport(mrz_data)
        assert fields["passport_number"] is not None
        assert len(fields["passport_number"]) >= 6

    def test_parse_not_detected(self):
        mrz_data = {"detected": False, "line1": None, "line2": None, "confidence": None}
        fields = parse_mrz_passport(mrz_data)
        assert fields["passport_number"] is None
        assert fields["surname"] is None

    def test_parse_female_passport(self):
        """Female passport MRZ."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDPATEL<<ANANYA<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654324IND9207142F3207130<<<<<<<<<<<<<06",
            "confidence": 0.90,
        }
        fields = parse_mrz_passport(mrz_data)
        assert fields["surname"] == "Patel"
        assert fields["given_names"] == "Ananya"
        assert fields["sex"] == "F"
        assert fields["nationality"] == "IND"


# =============================================================================
# Passport Field Extraction
# =============================================================================

class TestPassportFieldExtraction:
    """Test passport-specific field extraction with MRZ priority."""

    def test_mrz_only_extraction(self):
        """Extract all fields from MRZ alone (no visual OCR)."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        result = extract_passport_fields(ocr_lines=[], mrz_data=mrz_data)
        assert result["surname"] == "Sharma"
        assert result["given_names"] == "Rahul Kumar"
        # Passport: full_name is null — surname + given_names are separate fields
        assert result["full_name"] is None
        assert result["document_number"] == "Z1234567"
        assert result["nationality"] == "IND"
        assert result["date_of_birth"] == "1995-08-15"
        assert result["gender"] == "M"
        assert result["date_of_expiry"] == "2031-07-19"

    def test_full_name_is_null_for_passport(self):
        """Passport should NOT have a full_name field — surname + given_names are separate."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        result = extract_passport_fields(ocr_lines=[], mrz_data=mrz_data)
        assert result["full_name"] is None
        assert result["surname"] == "Sharma"
        assert result["given_names"] == "Rahul Kumar"

    def test_gender_normalized(self):
        """Gender should be normalized to M/F."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        result = extract_passport_fields(ocr_lines=[], mrz_data=mrz_data)
        assert result["gender"] == "M"

    def test_nationality_normalized(self):
        """Nationality should be normalized to 3-letter code."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        result = extract_passport_fields(ocr_lines=[], mrz_data=mrz_data)
        assert result["nationality"] == "IND"

    def test_passport_number_normalized(self):
        """Passport number should have no spaces."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        result = extract_passport_fields(ocr_lines=[], mrz_data=mrz_data)
        assert " " not in result["document_number"]
        assert result["document_number"] == "Z1234567"


# =============================================================================
# Visual + MRZ Consistency
# =============================================================================

class TestVisualMRZConsistency:
    """Test consistency checking between visual OCR and MRZ."""

    def test_consistent_dob(self):
        """Visual DOB matches MRZ DOB → consistent."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        ocr_lines = [
            {"text": "Date of Birth: 15/08/1995", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr_lines=ocr_lines, mrz_data=mrz_data)
        assert result["field_status"]["date_of_birth"] == "consistent"

    def test_conflicting_gender(self):
        """Visual says F but MRZ says M → conflict."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        ocr_lines = [
            {"text": "Sex:", "confidence": 0.85},
            {"text": "FEMALE", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr_lines=ocr_lines, mrz_data=mrz_data)
        # MRZ value wins, but status is conflict
        assert result["gender"] == "M"
        assert result["field_status"]["gender"] == "conflict"

    def test_no_mrz_uses_visual(self):
        """Without MRZ, visual extraction is used."""
        ocr_lines = [
            {"text": "Surname:", "confidence": 0.90},
            {"text": "KUMAR", "confidence": 0.95},
            {"text": "Given Names:", "confidence": 0.88},
            {"text": "RAJESH", "confidence": 0.93},
            {"text": "Sex:", "confidence": 0.85},
            {"text": "MALE", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr_lines=ocr_lines, mrz_data=None)
        assert result["surname"] == "Kumar"
        assert result["given_names"] == "Rajesh"
        assert result["gender"] == "M"


# =============================================================================
# Garbage OCR Must Not Override Valid MRZ
# =============================================================================

class TestGarbageOCRPriority:
    """Verify garbage OCR values do not override valid MRZ."""

    def test_garbage_passport_number_does_not_override_mrz(self):
        """OCR '2134 / Type' must not override MRZ passport number."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        ocr_lines = [
            {"text": "Passport No.:", "confidence": 0.80},
            {"text": "2134 / Type", "confidence": 0.75},
        ]
        result = extract_passport_fields(ocr_lines=ocr_lines, mrz_data=mrz_data)
        # MRZ value must win
        assert result["document_number"] == "Z1234567"

    def test_garbage_nationality_does_not_override_mrz(self):
        """OCR 'FTet' must not override MRZ nationality."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        ocr_lines = [
            {"text": "Nationality:", "confidence": 0.80},
            {"text": "FTet", "confidence": 0.70},
        ]
        result = extract_passport_fields(ocr_lines=ocr_lines, mrz_data=mrz_data)
        # MRZ value must win
        assert result["nationality"] == "IND"

    def test_visual_gender_conflict_uses_mrz(self):
        """OCR FEMALE but MRZ M → M with conflict status."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        ocr_lines = [
            {"text": "Sex:", "confidence": 0.85},
            {"text": "FEMALE", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr_lines=ocr_lines, mrz_data=mrz_data)
        assert result["gender"] == "M"
        assert result["field_status"]["gender"] == "conflict"

    def test_visual_nationality_matches_mrz(self):
        """OCR IND matches MRZ IND → consistent."""
        mrz_data = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        ocr_lines = [
            {"text": "Nationality:", "confidence": 0.85},
            {"text": "IND", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr_lines=ocr_lines, mrz_data=mrz_data)
        assert result["nationality"] == "IND"
        assert result["field_status"]["nationality"] == "consistent"


# =============================================================================
# MRZ Image Extraction
# =============================================================================

class TestMRZImageExtraction:
    """Test MRZ extraction from passport image."""

    def test_extract_mrz_from_passport_image(self):
        """Extract MRZ from a synthetic passport image.

        Note: Synthetic images have small MRZ text. Detection may not
        always succeed. The critical tests are the parsing tests above.
        This test verifies the extraction pipeline runs without errors.
        """
        from tests.test_aadhaar_passport import create_synthetic_passport
        import os

        path = os.path.join(os.path.dirname(__file__), "..", "uploads", "test_passport_mrz.png")
        create_synthetic_passport(
            path,
            surname="SHARMA",
            given_names="RAHUL KUMAR",
            passport_no="Z1234567",
            nationality="IND",
            dob_yymmdd="950815",
            sex="M",
            expiry_yymmdd="310719",
        )

        result = extract_mrz_from_image(path)
        # Pipeline should run without errors
        assert isinstance(result["detected"], bool)
        assert isinstance(result["raw_lines"], list)
        assert len(result["raw_lines"]) > 0
        # If detected, fields should be parseable
        if result["detected"]:
            from app.services.mrz_service import parse_mrz_passport
            fields = parse_mrz_passport(result)
            assert fields.get("passport_number") is not None

    def test_extract_mrz_nonexistent_image(self):
        """Non-existent image should return not detected."""
        result = extract_mrz_from_image("nonexistent.png")
        assert result["detected"] is False


# =============================================================================
# Document Type Isolation
# =============================================================================

class TestPassportDocumentIsolation:
    """Verify passport data doesn't leak into Aadhaar and vice versa."""

    def test_passport_mrz_does_not_affect_aadhaar(self):
        """Passport MRZ should not be used for Aadhaar extraction."""
        from app.services.field_extraction_service import extract_fields

        # Aadhaar extraction (no MRZ)
        ocr_lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "PRIYA SHARMA", "confidence": 0.97},
            {"text": "Gender:", "confidence": 0.91},
            {"text": "FEMALE", "confidence": 0.98},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar", mrz_data=None)
        assert result["full_name"] == "PRIYA SHARMA"
        assert result["gender"] == "FEMALE"
        assert result.get("field_status", {}).get("gender") == "extracted"

    def test_different_passports_different_data(self):
        """Two different passport MRZs produce different results."""
        mrz_a = {
            "detected": True,
            "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<",
            "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<8",
            "confidence": 0.95,
        }
        result_a = extract_passport_fields(ocr_lines=[], mrz_data=mrz_a)

        mrz_b = {
            "detected": True,
            "line1": "P<INDPATEL<<ANANYA<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "R987654324IND9207142F3207130<<<<<<<<<<<<<06",
            "confidence": 0.90,
        }
        result_b = extract_passport_fields(ocr_lines=[], mrz_data=mrz_b)

        # full_name is null for passport — check surname and given_names instead
        assert result_a["surname"] != result_b["surname"]
        assert result_a["given_names"] != result_b["given_names"]
        assert result_a["document_number"] != result_b["document_number"]
        assert result_a["gender"] != result_b["gender"]
