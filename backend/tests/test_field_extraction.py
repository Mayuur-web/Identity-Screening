"""Tests for the field extraction service."""

import pytest
from app.services.field_extraction_service import extract_fields, _parse_date, _clean_text


# --- Helper to build OCR line dicts ---

def make_lines(texts_and_confs: list[tuple[str, float]]) -> list[dict]:
    """Build OCR line list from (text, confidence) tuples."""
    return [{"text": t, "confidence": c} for t, c in texts_and_confs]


# --- Name extraction tests ---

class TestNameExtraction:
    def test_name_on_label_line(self):
        """Name label on one line, value on the next."""
        lines = make_lines([
            ("Name:", 0.95),
            ("RAHUL KUMAR", 0.98),
        ])
        result = extract_fields(lines)
        assert result["full_name"] == "RAHUL KUMAR"
        assert result["field_confidence"]["full_name"] == 0.98

    def test_full_name_label(self):
        lines = make_lines([
            ("Full Name", 0.90),
            ("ANITA DESAI", 0.97),
        ])
        result = extract_fields(lines)
        assert result["full_name"] == "ANITA DESAI"

    def test_name_inline(self):
        """Name value on the same line as the label."""
        lines = make_lines([
            ("Name: PRIYA SHARMA", 0.99),
        ])
        result = extract_fields(lines)
        assert result["full_name"] == "PRIYA SHARMA"
        assert result["field_confidence"]["full_name"] == 0.99

    def test_applicant_name(self):
        lines = make_lines([
            ("Applicant Name:", 0.88),
            ("MOHAN SINGH", 0.92),
        ])
        result = extract_fields(lines)
        assert result["full_name"] == "MOHAN SINGH"

    def test_name_with_ocr_noise(self):
        """OCR may add trailing dashes or colons."""
        lines = make_lines([
            ("Name-", 0.85),
            ("SURESH PATEL", 0.94),
        ])
        result = extract_fields(lines)
        assert result["full_name"] == "SURESH PATEL"


# --- DOB extraction tests ---

class TestDOBExtraction:
    def test_dob_label_with_date_next_line(self):
        lines = make_lines([
            ("Date of Birth:", 0.90),
            ("15-MAR-1995", 0.98),
        ])
        result = extract_fields(lines)
        assert result["date_of_birth"] == "1995-03-15"

    def test_dob_inline_dd_mm_yyyy(self):
        lines = make_lines([
            ("DOB: 24/10/1985", 0.95),
        ])
        result = extract_fields(lines)
        assert result["date_of_birth"] == "1985-10-24"

    def test_dob_dd_mm_yyyy_format(self):
        lines = make_lines([
            ("Date of Birth", 0.90),
            ("01/06/1990", 0.97),
        ])
        result = extract_fields(lines)
        assert result["date_of_birth"] == "1990-06-01"

    def test_dob_iso_format(self):
        lines = make_lines([
            ("DOB:", 0.88),
            ("1992-07-15", 0.96),
        ])
        result = extract_fields(lines)
        assert result["date_of_birth"] == "1992-07-15"

    def test_dob_dd_month_yyyy(self):
        lines = make_lines([
            ("Date of Birth:", 0.90),
            ("14 Aug 1999", 0.95),
        ])
        result = extract_fields(lines)
        assert result["date_of_birth"] == "1999-08-14"

    def test_dob_with_label_variation(self):
        lines = make_lines([
            ("Birth Date", 0.85),
            ("22/03/1988", 0.93),
        ])
        result = extract_fields(lines)
        assert result["date_of_birth"] == "1988-03-22"

    def test_dob_no_date_following(self):
        """Label present but no valid date follows."""
        lines = make_lines([
            ("DOB:", 0.80),
            ("Unknown", 0.70),
        ])
        result = extract_fields(lines)
        assert result["date_of_birth"] is None


# --- Gender extraction tests ---

class TestGenderExtraction:
    def test_gender_label_next_line(self):
        lines = make_lines([
            ("Gender", 0.92),
            ("MALE", 0.99),
        ])
        result = extract_fields(lines)
        assert result["gender"] == "MALE"

    def test_gender_female(self):
        lines = make_lines([
            ("Gender:", 0.90),
            ("FEMALE", 0.98),
        ])
        result = extract_fields(lines)
        assert result["gender"] == "FEMALE"

    def test_gender_inline(self):
        lines = make_lines([
            ("Sex: M", 0.85),
        ])
        result = extract_fields(lines)
        assert result["gender"] == "M"

    def test_gender_fallback_detection(self):
        """Gender detected from standalone word even without label."""
        lines = make_lines([
            ("Name:", 0.95),
            ("RAVI KUMAR", 0.98),
            ("FEMALE", 0.97),
        ])
        result = extract_fields(lines)
        # Should not match because RAVI KUMAR is consumed by name
        # but FEMALE is standalone and should be picked up
        assert result["gender"] == "FEMALE"


# --- Document number extraction tests ---

class TestDocumentNumberExtraction:
    def test_id_number_label(self):
        lines = make_lines([
            ("ID Number", 0.90),
            ("A89330129B", 0.95),
        ])
        result = extract_fields(lines)
        assert result["document_number"] == "A89330129B"

    def test_doc_number_with_dashes(self):
        lines = make_lines([
            ("Document Number:", 0.88),
            ("1234-5678-9012", 0.92),
        ])
        result = extract_fields(lines)
        assert result["document_number"] == "1234-5678-9012"

    def test_pan_label(self):
        lines = make_lines([
            ("PAN:", 0.90),
            ("ABCDE1234F", 0.96),
        ])
        result = extract_fields(lines)
        assert result["document_number"] == "ABCDE1234F"

    def test_passport_number(self):
        lines = make_lines([
            ("Passport No:", 0.85),
            ("Z1234567", 0.94),
        ])
        result = extract_fields(lines)
        assert result["document_number"] == "Z1234567"

    def test_fallback_pattern_detection(self):
        """If no label found, detect alphanumeric patterns with dashes."""
        lines = make_lines([
            ("Something else", 0.90),
            ("AB-123-CD45", 0.88),
        ])
        result = extract_fields(lines)
        assert result["document_number"] == "AB-123-CD45"


# --- Address extraction tests ---

class TestAddressExtraction:
    def test_single_line_address(self):
        lines = make_lines([
            ("Address:", 0.90),
            ("42 MG Road, Sector 15", 0.85),
        ])
        result = extract_fields(lines)
        assert "42 MG Road" in result["address"]

    def test_multi_line_address(self):
        lines = make_lines([
            ("Address-", 0.88),
            ("42 MG Road, Sector 15", 0.85),
            ("Gurugram, Haryana", 0.82),
            ("122001", 0.95),
        ])
        result = extract_fields(lines)
        assert "42 MG Road" in result["address"]
        assert "Gurugram" in result["address"]
        assert "122001" in result["address"]

    def test_address_confidence_average(self):
        """Address confidence should be average of line confidences."""
        lines = make_lines([
            ("Address:", 0.90),
            ("Street A", 0.80),
            ("City B", 0.90),
        ])
        result = extract_fields(lines)
        assert result["field_confidence"]["address"] is not None
        # Average of 0.80 and 0.90 = 0.85
        assert abs(result["field_confidence"]["address"] - 0.85) < 0.01

    def test_address_inline(self):
        lines = make_lines([
            ("Address: 123 Main St, Delhi", 0.88),
        ])
        result = extract_fields(lines)
        assert "123 Main St" in result["address"]


# --- Missing fields tests ---

class TestMissingFields:
    def test_empty_ocr_lines(self):
        result = extract_fields([])
        assert result["full_name"] is None
        assert result["date_of_birth"] is None
        assert result["document_number"] is None
        assert result["address"] is None
        assert result["gender"] is None

    def test_only_unrelated_lines(self):
        lines = make_lines([
            ("Republic of India", 0.90),
            ("Sample Document", 0.88),
            ("Photo", 0.95),
        ])
        result = extract_fields(lines)
        assert result["full_name"] is None
        assert result["date_of_birth"] is None
        assert result["document_number"] is None


# --- Document type tests ---

class TestDocumentType:
    def test_document_type_passed_through(self):
        lines = make_lines([("Name:", 0.90), ("TEST", 0.95)])
        result = extract_fields(lines, document_type="passport")
        assert result["document_type"] == "passport"

    def test_document_type_none(self):
        lines = make_lines([("Name:", 0.90), ("TEST", 0.95)])
        result = extract_fields(lines)
        assert result["document_type"] is None


# --- OCR noise tests ---

class TestOCRNoise:
    def test_trailing_dashes(self):
        lines = make_lines([
            ("Name:", 0.90),
            ("RAVI-", 0.85),
        ])
        result = extract_fields(lines)
        assert result["full_name"] == "RAVI"

    def test_trailing_colons_in_value(self):
        lines = make_lines([
            ("DOB:", 0.88),
            ("1990-05-20:", 0.92),
        ])
        result = extract_fields(lines)
        assert result["date_of_birth"] == "1990-05-20"

    def test_case_insensitive_labels(self):
        lines = make_lines([
            ("name", 0.90),
            ("UPPER CASE", 0.95),
        ])
        result = extract_fields(lines)
        assert result["full_name"] == "UPPER CASE"


# --- Low confidence tests ---

class TestLowConfidence:
    def test_low_confidence_still_extracts(self):
        """Even low confidence OCR lines should be extracted if text matches."""
        lines = make_lines([
            ("Name:", 0.30),
            ("PARTIAL NAME", 0.35),
        ])
        result = extract_fields(lines)
        assert result["full_name"] == "PARTIAL NAME"
        assert result["field_confidence"]["full_name"] == 0.35

    def test_confidence_reflects_ocr(self):
        """Field confidence should match the OCR confidence of the source line."""
        lines = make_lines([
            ("Name:", 0.50),
            ("VALUE", 0.60),
        ])
        result = extract_fields(lines)
        assert result["field_confidence"]["full_name"] == 0.60


# --- Helper function tests ---

class TestParseDate:
    def test_parse_dd_mm_yyyy(self):
        assert _parse_date("15/03/1995") == "1995-03-15"

    def test_parse_dd_mm_yyyy_with_dashes(self):
        assert _parse_date("24-10-1985") == "1985-10-24"

    def test_parse_dd_mmm_yyyy(self):
        assert _parse_date("15-MAR-1995") == "1995-03-15"

    def test_parse_iso_format(self):
        assert _parse_date("1992-07-15") == "1992-07-15"

    def test_parse_dd_month_yyyy(self):
        assert _parse_date("14 Aug 1999") == "1999-08-14"

    def test_parse_invalid_date(self):
        assert _parse_date("not a date") is None

    def test_parse_empty_string(self):
        assert _parse_date("") is None


class TestCleanText:
    def test_clean_trailing_dash(self):
        assert _clean_text("Hello-") == "Hello"

    def test_clean_trailing_colon(self):
        assert _clean_text("Value:") == "Value"

    def test_clean_leading_dash(self):
        assert _clean_text("-Hello") == "Hello"

    def test_clean_whitespace(self):
        assert _clean_text("  Hello  ") == "Hello"

    def test_clean_empty(self):
        assert _clean_text("") == ""
