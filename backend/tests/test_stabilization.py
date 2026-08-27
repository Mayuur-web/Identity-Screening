"""Stabilization tests — comprehensive coverage of the complete OCR + field extraction pipeline.

Tests corrupted labels, multiple identities, edge cases, document isolation,
and the full flow from OCR through field extraction.
"""

import pytest
from app.services.field_extraction_service import (
    extract_fields,
    _is_valid_name_candidate,
    _is_label_like,
    _parse_date,
    _normalize_for_comparison,
)


# =============================================================================
# Corrupted OCR label tests
# =============================================================================

class TestCorruptedLabels:
    """Test extraction when OCR labels are corrupted by noise."""

    def test_dob_embedded_in_noisy_line(self):
        """'fafal DOB: 18/04/2006' should extract DOB."""
        lines = [
            {"text": "fafal DOB: 18/04/2006", "confidence": 0.88},
        ]
        result = extract_fields(lines)
        assert result["date_of_birth"] == "2006-04-18"

    def test_dob_with_prefix_noise(self):
        """'T4fafa/ DOB: 18/01/2006' should extract DOB."""
        lines = [
            {"text": "T4fafa/ DOB: 18/01/2006", "confidence": 0.85},
        ]
        result = extract_fields(lines)
        assert result["date_of_birth"] == "2006-01-18"

    def test_gender_embedded_in_noisy_line(self):
        """'AfrT / FEMALE' should extract FEMALE."""
        lines = [
            {"text": "AfrT / FEMALE", "confidence": 0.82},
        ]
        result = extract_fields(lines)
        assert result["gender"] == "FEMALE"

    def test_gender_with_number_prefix(self):
        """'1 FEMALE' should extract FEMALE."""
        lines = [
            {"text": "1 FEMALE", "confidence": 0.80},
        ]
        result = extract_fields(lines)
        assert result["gender"] == "FEMALE"

    def test_aadhaar_with_spaces(self):
        """'9264 1656 4196' should extract as 12-digit Aadhaar."""
        lines = [
            {"text": "9264 1656 4196", "confidence": 0.90},
        ]
        result = extract_fields(lines)
        assert result["document_number"] == "926416564196"

    def test_aadhaar_with_dashes(self):
        """'1234-5678-9012' should extract as Aadhaar."""
        lines = [
            {"text": "1234-5678-9012", "confidence": 0.92},
        ]
        result = extract_fields(lines)
        assert result["document_number"] == "123456789012"

    def test_name_without_label_when_other_fields_present(self):
        """Name without label should be detected when DOB exists."""
        lines = [
            {"text": "Isha Raj", "confidence": 0.93},
            {"text": "DOB: 18/04/2006", "confidence": 0.88},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "Isha Raj"

    def test_name_without_label_no_other_fields(self):
        """Name without label should NOT be detected when no other fields exist."""
        lines = [
            {"text": "Random unrelated text", "confidence": 0.80},
        ]
        result = extract_fields(lines)
        assert result["full_name"] is None


# =============================================================================
# Full corrupted document test
# =============================================================================

class TestFullCorruptedDocument:
    """Test the complete corrupted OCR scenario from the requirements."""

    def test_full_corrupted_aadhaar(self):
        """Extract all fields from fully corrupted Aadhaar OCR."""
        lines = [
            {"text": "Isha Raj", "confidence": 0.93},
            {"text": "T4fafa/ DOB: 18/01/2006", "confidence": 0.85},
            {"text": "fafal DOB: 18/04/2006", "confidence": 0.88},
            {"text": "AfrT / FEMALE", "confidence": 0.82},
            {"text": "1 FEMALE", "confidence": 0.80},
            {"text": "9264 1656 4196", "confidence": 0.90},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "Isha Raj"
        assert result["date_of_birth"] is not None
        assert result["gender"] == "FEMALE"
        assert result["document_number"] == "926416564196"
        # All should have confidence values
        assert result["field_confidence"]["full_name"] is not None
        assert result["field_confidence"]["date_of_birth"] is not None
        assert result["field_confidence"]["gender"] is not None
        assert result["field_confidence"]["document_number"] is not None


# =============================================================================
# Multiple date context scoring
# =============================================================================

class TestDateContextScoring:
    """Test that DOB context gets higher priority than issue/expiry dates."""

    def test_dob_label_wins_over_issue_date(self):
        """Date near DOB label should be preferred over date near issue label."""
        lines = [
            {"text": "DOB:", "confidence": 0.90},
            {"text": "18/04/2006", "confidence": 0.88},
            {"text": "Issue Date:", "confidence": 0.91},
            {"text": "01/01/2020", "confidence": 0.89},
        ]
        result = extract_fields(lines)
        assert result["date_of_birth"] == "2006-04-18"

    def test_date_without_label_prefers_dob_context(self):
        """When multiple dates exist, the one near DOB context wins."""
        lines = [
            {"text": "Name:", "confidence": 0.93},
            {"text": "TEST USER", "confidence": 0.97},
            {"text": "01/01/2020", "confidence": 0.89},
            {"text": "DOB:", "confidence": 0.90},
            {"text": "18/04/2006", "confidence": 0.88},
        ]
        result = extract_fields(lines)
        assert result["date_of_birth"] == "2006-04-18"


# =============================================================================
# Document isolation
# =============================================================================

class TestDocumentIsolation:
    """Verify complete isolation between analyses."""

    def test_analyze_a_then_b(self):
        """No data from A should appear in B."""
        lines_a = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.98},
            {"text": "DOB:", "confidence": 0.93},
            {"text": "14/03/1995", "confidence": 0.97},
            {"text": "Gender:", "confidence": 0.94},
            {"text": "FEMALE", "confidence": 0.99},
            {"text": "ID Number:", "confidence": 0.91},
            {"text": "1111-2222-3333", "confidence": 0.96},
        ]
        ra = extract_fields(lines_a, document_type="aadhaar")

        lines_b = [
            {"text": "Name:", "confidence": 0.96},
            {"text": "AMIT SINGH", "confidence": 0.99},
            {"text": "DOB:", "confidence": 0.92},
            {"text": "22/11/1990", "confidence": 0.96},
            {"text": "Gender:", "confidence": 0.95},
            {"text": "MALE", "confidence": 0.98},
            {"text": "ID Number:", "confidence": 0.90},
            {"text": "9999-8888-7777", "confidence": 0.97},
        ]
        rb = extract_fields(lines_b, document_type="aadhaar")

        assert ra["full_name"] == "PRIYA SHARMA"
        assert rb["full_name"] == "AMIT SINGH"
        assert ra["date_of_birth"] == "1995-03-14"
        assert rb["date_of_birth"] == "1990-11-22"
        assert ra["gender"] == "FEMALE"
        assert rb["gender"] == "MALE"
        assert ra["document_number"] == "1111-2222-3333"
        assert rb["document_number"] == "9999-8888-7777"

    def test_three_sequential_analyses(self):
        """Three analyses should all be independent."""
        names = ["ALICE WONDER", "BOB BUILDER", "CHARLIE BROWN"]
        for name in names:
            lines = [
                {"text": "Name:", "confidence": 0.95},
                {"text": name, "confidence": 0.98},
            ]
            result = extract_fields(lines)
            assert result["full_name"] == name


# =============================================================================
# Name extraction edge cases
# =============================================================================

class TestNameEdgeCases:
    """Name extraction edge cases."""

    def test_tma_label_not_returned_as_name(self):
        """'TMA / Name:' should not be returned as the name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "TMA / Name:", "confidence": 0.88},
            {"text": "SANJANA KA DIWANA ROHIT", "confidence": 0.91},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "SANJANA KA DIWANA ROHIT"
        assert result["full_name"] != "TMA / Name"

    def test_tfatr_not_returned_as_name(self):
        """'TFATR' should not be returned as the name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "TFATR", "confidence": 0.70},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN DOE"

    def test_single_char_not_name(self):
        """Single character should not be a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "T", "confidence": 0.60},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN DOE"

    def test_digits_not_name(self):
        """Pure digits should not be a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "12345", "confidence": 0.80},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN DOE"

    def test_government_not_name(self):
        """'Government of India' should not be a name."""
        lines = [
            {"text": "Name:", "confidence": 0.92},
            {"text": "Government of India", "confidence": 0.93},
            {"text": "JOHN DOE", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "JOHN DOE"

    def test_hindi_name_label(self):
        """Hindi label नाम: should work."""
        lines = [
            {"text": "नाम:", "confidence": 0.90},
            {"text": "राजेश कुमार", "confidence": 0.88},
        ]
        result = extract_fields(lines)
        assert result["full_name"] == "राजेश कुमार"


# =============================================================================
# Gender extraction
# =============================================================================

class TestGenderExtraction:
    """Gender extraction from various formats."""

    def test_gender_label(self):
        lines = [{"text": "Gender:", "confidence": 0.93}, {"text": "MALE", "confidence": 0.98}]
        assert extract_fields(lines)["gender"] == "MALE"

    def test_gender_female(self):
        lines = [{"text": "Gender:", "confidence": 0.93}, {"text": "FEMALE", "confidence": 0.98}]
        assert extract_fields(lines)["gender"] == "FEMALE"

    def test_gender_standalone(self):
        lines = [{"text": "FEMALE", "confidence": 0.95}]
        assert extract_fields(lines)["gender"] == "FEMALE"

    def test_gender_embedded(self):
        lines = [{"text": "AfrT / FEMALE", "confidence": 0.82}]
        assert extract_fields(lines)["gender"] == "FEMALE"

    def test_gender_with_number(self):
        lines = [{"text": "1 FEMALE", "confidence": 0.80}]
        assert extract_fields(lines)["gender"] == "FEMALE"


# =============================================================================
# Document number extraction
# =============================================================================

class TestDocumentNumberExtraction:
    """Document number extraction for various formats."""

    def test_aadhaar_with_spaces(self):
        lines = [{"text": "9264 1656 4196", "confidence": 0.90}]
        assert extract_fields(lines)["document_number"] == "926416564196"

    def test_aadhaar_with_dashes(self):
        lines = [{"text": "1234-5678-9012", "confidence": 0.92}]
        assert extract_fields(lines)["document_number"] == "123456789012"

    def test_aadhaar_plain(self):
        lines = [{"text": "123456789012", "confidence": 0.94}]
        assert extract_fields(lines)["document_number"] == "123456789012"

    def test_label_then_aadhaar(self):
        lines = [
            {"text": "ID Number:", "confidence": 0.90},
            {"text": "1234-5678-9012", "confidence": 0.95},
        ]
        result = extract_fields(lines)
        assert result["document_number"] == "1234-5678-9012"


# =============================================================================
# Date extraction
# =============================================================================

class TestDateExtraction:
    """Date extraction from various formats."""

    def test_dd_mm_yyyy(self):
        lines = [{"text": "DOB:", "confidence": 0.93}, {"text": "21/08/2002", "confidence": 0.96}]
        assert extract_fields(lines)["date_of_birth"] == "2002-08-21"

    def test_dd_mm_yyyy_dashes(self):
        lines = [{"text": "DOB:", "confidence": 0.93}, {"text": "21-08-2002", "confidence": 0.96}]
        assert extract_fields(lines)["date_of_birth"] == "2002-08-21"

    def test_yyyy_mm_dd(self):
        lines = [{"text": "DOB:", "confidence": 0.93}, {"text": "2002-08-21", "confidence": 0.96}]
        assert extract_fields(lines)["date_of_birth"] == "2002-08-21"

    def test_dd_mon_yyyy(self):
        lines = [{"text": "DOB:", "confidence": 0.93}, {"text": "21 Aug 2002", "confidence": 0.96}]
        assert extract_fields(lines)["date_of_birth"] == "2002-08-21"

    def test_embedded_dob(self):
        lines = [{"text": "fafal DOB: 18/04/2006", "confidence": 0.88}]
        assert extract_fields(lines)["date_of_birth"] == "2006-04-18"


# =============================================================================
# Cross-source consistency
# =============================================================================

class TestCrossSourceConsistency:
    """OCR vs MRZ consistency checking."""

    def test_consistent_dob(self):
        ocr_lines = [{"text": "Date of Birth:", "confidence": 0.95}, {"text": "20/05/1983", "confidence": 0.97}]
        mrz_data = {
            "detected": True,
            "line1": "P<INDTEST<<NAME<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "X123456784IND8305202M3012310<<<<<<<<<<<<<06",
            "confidence": 0.90,
        }
        result = extract_fields(ocr_lines, document_type="passport", mrz_data=mrz_data)
        assert result["field_status"]["date_of_birth"] == "consistent"

    def test_conflicting_gender(self):
        ocr_lines = [{"text": "Gender:", "confidence": 0.95}, {"text": "MALE", "confidence": 0.97}]
        mrz_data = {
            "detected": True,
            "line1": "P<INDTEST<<NAME<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "X123456784IND8305202F3012310<<<<<<<<<<<<<06",
            "confidence": 0.90,
        }
        result = extract_fields(ocr_lines, document_type="passport", mrz_data=mrz_data)
        assert result["field_status"]["gender"] == "conflict"


# =============================================================================
# Normalization
# =============================================================================

class TestNormalization:
    """Value normalization for comparison."""

    def test_date_normalization(self):
        assert _normalize_for_comparison("21/08/2002", "date_of_birth") == "2002-08-21"
        assert _normalize_for_comparison("2002-08-21", "date_of_birth") == "2002-08-21"

    def test_gender_normalization(self):
        assert _normalize_for_comparison("Male", "gender") == "M"
        assert _normalize_for_comparison("FEMALE", "gender") == "F"

    def test_name_normalization(self):
        assert _normalize_for_comparison("John Doe", "full_name") == "john doe"
        assert _normalize_for_comparison("  JOHN  DOE  ", "full_name") == "john doe"


# =============================================================================
# Empty / edge cases
# =============================================================================

class TestEdgeCases:
    """Empty and edge-case inputs."""

    def test_empty_ocr(self):
        result = extract_fields([])
        assert result["full_name"] is None
        assert result["date_of_birth"] is None
        assert result["gender"] is None
        assert result["document_number"] is None

    def test_single_unrelated_line(self):
        result = extract_fields([{"text": "Some random text", "confidence": 0.80}])
        assert result["full_name"] is None

    def test_all_none_fields_have_null_confidence(self):
        result = extract_fields([{"text": "Random", "confidence": 0.80}])
        for key in result["field_confidence"]:
            if result.get(key) is None:
                assert result["field_confidence"][key] is None

    def test_field_status_populated(self):
        result = extract_fields([
            {"text": "Name:", "confidence": 0.93},
            {"text": "TEST USER", "confidence": 0.97},
        ])
        assert "full_name" in result["field_status"]
        assert result["field_status"]["full_name"] == "extracted"
        assert result["field_status"]["date_of_birth"] == "not_detected"
