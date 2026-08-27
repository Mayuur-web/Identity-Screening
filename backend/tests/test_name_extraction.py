"""Comprehensive name extraction tests.

Tests the robust name candidate scoring algorithm that:
- Scans multiple lines ahead from the Name label
- Skips labels, noise, short strings
- Scores candidates by word count, confidence, distance
- Never returns a label as a name
"""

import pytest
from app.services.field_extraction_service import (
    extract_fields,
    _is_valid_name_candidate,
    _is_label_like,
    _find_name_candidate,
    _score_name_candidate,
)


class TestNameExtractionBasic:
    """Basic name extraction: label followed by name."""

    def test_label_then_name(self):
        """Name: followed by a name on the next line."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "JOHN KUMAR", "confidence": 0.97},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN KUMAR"
        assert result["field_confidence"]["full_name"] == 0.97

    def test_label_inline_value(self):
        """Name: VALUE on the same line."""
        lines = [
            {"text": "Name: JOHN KUMAR", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN KUMAR"

    def test_full_name_label(self):
        """Full Name: followed by value."""
        lines = [
            {"text": "Full Name:", "confidence": 0.92},
            {"text": "PRIYA DEVI", "confidence": 0.96},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "PRIYA DEVI"


class TestNameExtractionMultiLine:
    """Name extraction with noise/labels between label and actual name."""

    def test_label_then_another_label_then_name(self):
        """Name: followed by another label, then the actual name."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "TMA / Name:", "confidence": 0.88},
            {"text": "JOHN KUMAR", "confidence": 0.97},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN KUMAR"

    def test_label_then_noise_then_name(self):
        """Name: followed by short OCR noise, then name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "TA", "confidence": 0.75},
            {"text": "JOHN KUMAR", "confidence": 0.96},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN KUMAR"

    def test_label_multiple_labels_then_name(self):
        """Name: followed by multiple label-like lines, then name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "TMA / Name:", "confidence": 0.88},
            {"text": "TA", "confidence": 0.75},
            {"text": "SANJANA KA DIWANA ROHIT", "confidence": 0.91},
            {"text": "TFATR", "confidence": 0.70},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "SANJANA KA DIWANA ROHIT"
        assert result["field_confidence"]["full_name"] == 0.91

    def test_label_then_date_noise_then_name(self):
        """Name: followed by date-like noise, then name."""
        lines = [
            {"text": "Name:", "confidence": 0.90},
            {"text": "12345", "confidence": 0.80},
            {"text": "RAJESH SINGH", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "RAJESH SINGH"


class TestNameExtractionWordCount:
    """Name extraction based on word count scoring."""

    def test_single_word_name(self):
        """Single word name (shorter but still valid)."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "KUMAR", "confidence": 0.97},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "KUMAR"

    def test_two_word_name(self):
        """Two-word name (strong candidate)."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "AMIT SINGH", "confidence": 0.97},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "AMIT SINGH"

    def test_three_plus_word_name(self):
        """Three or more word name (strongest candidate)."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "SANJANA KA DIWANA ROHIT", "confidence": 0.91},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "SANJANA KA DIWANA ROHIT"


class TestNameExtractionEdgeCases:
    """Edge cases for name extraction."""

    def test_missing_name_returns_none(self):
        """No name at all → full_name = None."""
        lines = [
            {"text": "DOB:", "confidence": 0.93},
            {"text": "21/08/2002", "confidence": 0.96},
        ]
        result = extract_fields(lines)
        assert result["full_name"] is None
        assert result["field_confidence"]["full_name"] is None

    def test_only_name_label_no_value(self):
        """Name: with nothing after it → full_name = None."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
        ]
        result = extract_fields(lines)
        assert result["full_name"] is None

    def test_name_label_then_only_noise(self):
        """Name: followed only by noise → full_name = None."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "TA", "confidence": 0.60},
            {"text": "12", "confidence": 0.50},
        ]
        result = extract_fields(lines)
        assert result["full_name"] is None

    def test_name_label_then_only_date(self):
        """Name: followed by DOB (another field) → full_name = None."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "DOB:", "confidence": 0.90},
            {"text": "21/08/2002", "confidence": 0.96},
        ]
        result = extract_fields(lines)
        assert result["full_name"] is None
        # DOB should still be extracted
        assert result["date_of_birth"] == "2002-08-21"

    def test_empty_ocr_lines(self):
        """Empty OCR → all None."""
        result = extract_fields([])
        assert result["full_name"] is None

    def test_name_not_first_field(self):
        """Name label appears after other fields."""
        lines = [
            {"text": "DOB:", "confidence": 0.90},
            {"text": "21/08/2002", "confidence": 0.96},
            {"text": "Gender:", "confidence": 0.91},
            {"text": "MALE", "confidence": 0.98},
            {"text": "Name:", "confidence": 0.93},
            {"text": "AMIT SINGH", "confidence": 0.97},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "AMIT SINGH"
        assert result["date_of_birth"] == "2002-08-21"
        assert result["gender"] == "MALE"

    def test_hindi_name_label(self):
        """Hindi name label नाम: followed by name."""
        lines = [
            {"text": "नाम:", "confidence": 0.90},
            {"text": "राजेश कुमार", "confidence": 0.88},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "राजेश कुमार"


class TestNameExtractionIsolation:
    """Verify different names produce different results (no stale data)."""

    def test_different_names_different_documents(self):
        """Two different OCR runs should produce different names."""
        lines_a = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "PRIYA SHARMA", "confidence": 0.97},
        ]
        result_a = extract_fields(lines_a)

        lines_b = [
            {"text": "Name:", "confidence": 0.94},
            {"text": "AMIT SINGH", "confidence": 0.98},
        ]
        result_b = extract_fields(lines_b)

        assert result_a["full_name"] == "PRIYA SHARMA"
        assert result_b["full_name"] == "AMIT SINGH"
        assert result_a["full_name"] != result_b["full_name"]

    def test_sequential_analyses_no_bleed(self):
        """Analyzing doc A then doc B should not carry A's name into B."""
        lines_a = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.98},
        ]
        extract_fields(lines_a)

        lines_b = [
            {"text": "Name:", "confidence": 0.94},
            {"text": "AMIT SINGH", "confidence": 0.99},
        ]
        result_b = extract_fields(lines_b)

        assert result_b["full_name"] == "AMIT SINGH"
        assert result_b["full_name"] != "PRIYA SHARMA"


class TestNameExtractionFalsePositives:
    """Ensure labels and noise are NOT extracted as names."""

    def test_tma_name_not_extracted(self):
        """'TMA / Name:' should NOT be returned as a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "TMA / Name:", "confidence": 0.88},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] != "TMA / Name"
        assert result["full_name"] == "JOHN DOE"

    def test_tfatr_not_extracted(self):
        """'TFATR' (OCR noise) should NOT be returned as a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "TFATR", "confidence": 0.70},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] != "TFATR"
        assert result["full_name"] == "JOHN DOE"

    def test_aadhaar_label_not_extracted(self):
        """'Aadhaar' should NOT be returned as a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "Aadhaar", "confidence": 0.90},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] != "Aadhaar"
        assert result["full_name"] == "JOHN DOE"

    def test_government_not_extracted(self):
        """'Government of India' should NOT be returned as a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "Government of India", "confidence": 0.93},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] != "Government of India"
        assert result["full_name"] == "JOHN DOE"

    def test_single_char_not_name(self):
        """Single character 'T' should NOT be a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "T", "confidence": 0.60},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN DOE"

    def test_digits_not_name(self):
        """Pure digits should NOT be a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "12345", "confidence": 0.80},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN DOE"


class TestLabelDetection:
    """Test the _is_label_like helper function."""

    def test_name_is_label(self):
        assert _is_label_like("Name:") is True

    def test_full_name_is_label(self):
        assert _is_label_like("Full Name:") is True

    def test_tma_name_is_label(self):
        assert _is_label_like("TMA / Name:") is True

    def test_dob_is_label(self):
        assert _is_label_like("DOB:") is True

    def test_date_of_birth_is_label(self):
        assert _is_label_like("Date of Birth:") is True

    def test_gender_is_label(self):
        assert _is_label_like("Gender:") is True

    def test_address_is_label(self):
        assert _is_label_like("Address:") is True

    def test_hindi_name_is_label(self):
        assert _is_label_like("नाम:") is True

    def test_john_doe_is_not_label(self):
        assert _is_label_like("JOHN DOE") is False

    def test_long_name_is_not_label(self):
        assert _is_label_like("SANJANA KA DIWANA ROHIT") is False

    def test_empty_is_not_label(self):
        assert _is_label_like("") is False


class TestCandidateValidation:
    """Test the _is_valid_name_candidate helper function."""

    def test_valid_two_word_name(self):
        assert _is_valid_name_candidate("JOHN KUMAR") is True

    def test_valid_three_word_name(self):
        assert _is_valid_name_candidate("SANJANA KA DIWANA ROHIT") is True

    def test_invalid_too_short(self):
        assert _is_valid_name_candidate("T") is False

    def test_invalid_digits_only(self):
        assert _is_valid_name_candidate("12345") is False

    def test_invalid_label(self):
        assert _is_valid_name_candidate("Name:") is False

    def test_invalid_tma_label(self):
        assert _is_valid_name_candidate("TMA / Name:") is False

    def test_invalid_date(self):
        assert _is_valid_name_candidate("21/08/2002") is False

    def test_invalid_empty(self):
        assert _is_valid_name_candidate("") is False

    def test_invalid_male(self):
        assert _is_valid_name_candidate("MALE") is False

    def test_invalid_single_char_caps(self):
        assert _is_valid_name_candidate("TA") is False
