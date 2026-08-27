"""Tests for data isolation and cross-source consistency.

Verifies that:
1. No stale/demo values leak into API responses.
2. Each analysis returns only values from the CURRENT document.
3. OCR vs MRZ conflicts are properly detected.
4. Missing fields return None (not placeholder data).
"""

import os
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.field_extraction_service import extract_fields, _compare_field_values, _normalize_for_comparison
from app.services.ocr_service import extract_text_sync
from app.services.mrz_service import detect_mrz, parse_mrz_passport


# ---------- Helper: create synthetic document images ----------

def _create_doc_image(output_path: str, name: str, dob: str, doc_number: str,
                      gender: str, address: str, font_size: int = 20) -> str:
    """Create a simple synthetic document image with specific identity values."""
    width, height = 700, 400
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
        font_small = ImageFont.truetype("arial.ttf", max(font_size - 6, 10))
    except OSError:
        font = ImageFont.load_default()
        font_small = font

    # Header
    draw.rectangle([(0, 0), (width, 50)], fill=(0, 51, 102))
    draw.text((20, 12), "IDENTITY DOCUMENT", fill=(255, 255, 255), font=font)

    y = 70
    gap = font_size + 12

    fields = [
        ("Name:", name),
        ("Date of Birth:", dob),
        ("Gender:", gender),
        ("ID Number:", doc_number),
        ("Address:", address),
    ]

    for label, value in fields:
        draw.text((30, y), label, fill=(100, 100, 100), font=font_small)
        draw.text((200, y), value, fill=(0, 0, 0), font=font)
        y += gap

    # Bottom label
    draw.text((30, height - 40), "SYNTHETIC TEST DOCUMENT - NOT A REAL IDENTITY", fill=(180, 50, 50), font=font_small)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def _create_passport_image(output_path: str, surname: str, given_names: str,
                           passport_no: str, nationality: str, dob_yymmdd: str,
                           sex: str, expiry_yymmdd: str) -> str:
    """Create a synthetic passport page with visible text AND MRZ."""
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color=(245, 245, 250))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 18)
        font_small = ImageFont.truetype("arial.ttf", 14)
        font_mrz = ImageFont.truetype("cour.ttf", 16)
    except OSError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            font_mrz = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 16)
        except OSError:
            font = ImageFont.load_default()
            font_small = font
            font_mrz = font

    # Header
    draw.rectangle([(0, 0), (width, 50)], fill=(0, 51, 102))
    draw.text((20, 12), "REPUBLIC OF INDIA", fill=(255, 255, 255), font=font)
    draw.text((width - 150, 15), "PASSPORT", fill=(200, 200, 200), font=font_small)

    # Identity fields
    y = 70
    gap = 30
    fields = [
        ("Surname:", surname),
        ("Given Names:", given_names),
        ("Passport No.:", passport_no),
        ("Nationality:", nationality),
        ("Date of Birth:", f"DOB: {dob_yymmdd}"),
        ("Sex:", sex),
    ]

    for label, value in fields:
        draw.text((30, y), label, fill=(100, 100, 100), font=font_small)
        draw.text((180, y), value, fill=(0, 0, 0), font=font)
        y += gap

    # MRZ at bottom (TD3 format: 44 chars per line)
    name_mrz = f"P<IND{surname.upper()}<<{given_names.upper()}"
    name_mrz = name_mrz.ljust(44, "<")

    line2 = f"{passport_no:<9}{nationality.upper()}{dob_yymmdd}{sex}{expiry_yymmdd}"
    # Pad to ~44 chars (not strictly 44 to test tolerance)
    line2 = line2.ljust(40, "<")

    draw.rectangle([(0, height - 80), (width, height)], fill=(230, 230, 240))
    draw.text((20, height - 70), name_mrz, fill=(0, 0, 0), font=font_mrz)
    draw.text((20, height - 45), line2, fill=(0, 0, 0), font=font_mrz)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


# ---------- Test: No stale data in extraction ----------

class TestDataIsolation:
    """Verify that each analysis contains only values from the current document."""

    def test_different_documents_produce_different_names(self):
        """Document A and Document B with different names should produce different full_name."""
        # Document A
        lines_a = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "RAJESH KUMAR", "confidence": 0.98},
            {"text": "Date of Birth:", "confidence": 0.93},
            {"text": "15/06/1985", "confidence": 0.97},
            {"text": "Gender:", "confidence": 0.94},
            {"text": "MALE", "confidence": 0.99},
        ]
        result_a = extract_fields(lines_a, document_type="aadhaar")

        # Document B
        lines_b = [
            {"text": "Name:", "confidence": 0.96},
            {"text": "SUNITA DEVI", "confidence": 0.99},
            {"text": "Date of Birth:", "confidence": 0.92},
            {"text": "22/11/1990", "confidence": 0.96},
            {"text": "Gender:", "confidence": 0.95},
            {"text": "FEMALE", "confidence": 0.98},
        ]
        result_b = extract_fields(lines_b, document_type="aadhaar")

        # Verify different results
        assert result_a["full_name"] == "RAJESH KUMAR"
        assert result_b["full_name"] == "SUNITA DEVI"
        assert result_a["date_of_birth"] == "1985-06-15"
        assert result_b["date_of_birth"] == "1990-11-22"
        assert result_a["gender"] == "MALE"
        assert result_b["gender"] == "FEMALE"

    def test_analyze_a_then_b_no_bleed(self):
        """Analyzing Document A then Document B should not carry over A's data into B."""
        lines_a = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.98},
            {"text": "ID Number:", "confidence": 0.93},
            {"text": "1234-5678-9012", "confidence": 0.97},
        ]
        result_a = extract_fields(lines_a)

        lines_b = [
            {"text": "Name:", "confidence": 0.96},
            {"text": "AMIT SINGH", "confidence": 0.99},
            {"text": "ID Number:", "confidence": 0.94},
            {"text": "ABCD-EFGH-IJKL", "confidence": 0.98},
        ]
        result_b = extract_fields(lines_b)

        # B should contain ONLY B's values
        assert result_b["full_name"] == "AMIT SINGH"
        assert result_b["document_number"] == "ABCD-EFGH-IJKL"
        assert result_b["full_name"] != "PRIYA SHARMA"
        assert result_b["document_number"] != "1234-5678-9012"

    def test_analyze_b_then_a_no_bleed(self):
        """Analyzing Document B then Document A should not carry over B's data into A."""
        lines_b = [
            {"text": "Name:", "confidence": 0.96},
            {"text": "AMIT SINGH", "confidence": 0.99},
            {"text": "ID Number:", "confidence": 0.94},
            {"text": "ABCD-EFGH-IJKL", "confidence": 0.98},
        ]
        result_b = extract_fields(lines_b)

        lines_a = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.98},
            {"text": "ID Number:", "confidence": 0.93},
            {"text": "1234-5678-9012", "confidence": 0.97},
        ]
        result_a = extract_fields(lines_a)

        # A should contain ONLY A's values
        assert result_a["full_name"] == "PRIYA SHARMA"
        assert result_a["document_number"] == "1234-5678-9012"
        assert result_a["full_name"] != "AMIT SINGH"
        assert result_a["document_number"] != "ABCD-EFGH-IJKL"

    def test_missing_fields_return_none_not_placeholder(self):
        """Fields that cannot be extracted must return None, not placeholder data."""
        lines = [
            {"text": "Random unrelated text", "confidence": 0.80},
            {"text": "Another random line", "confidence": 0.75},
        ]
        result = extract_fields(lines)

        # All identity fields should be None
        assert result["full_name"] is None
        assert result["date_of_birth"] is None
        assert result["document_number"] is None
        assert result["address"] is None
        assert result["gender"] is None
        assert result["father_name"] is None
        assert result["surname"] is None
        assert result["given_names"] is None

        # No field should contain "PRIYA SHARMA" or any other known demo name
        for key in result:
            if key == "field_confidence" or key == "field_status":
                continue
            val = result.get(key)
            if val is not None:
                assert val.upper() not in ("PRIYA SHARMA", "RAJESH SHARMA", "DEMO USER")

    def test_empty_ocr_returns_all_none(self):
        """Empty OCR lines should produce all-None fields."""
        result = extract_fields([])

        assert result["full_name"] is None
        assert result["date_of_birth"] is None
        assert result["document_number"] is None
        assert result["gender"] is None

    def test_no_global_state_leak(self):
        """Multiple sequential calls should not share any state."""
        # Call 1
        lines_1 = [{"text": "Name:", "confidence": 0.9}, {"text": "ALPHA PERSON", "confidence": 0.95}]
        r1 = extract_fields(lines_1)

        # Call 2
        lines_2 = [{"text": "Name:", "confidence": 0.9}, {"text": "BETA PERSON", "confidence": 0.95}]
        r2 = extract_fields(lines_2)

        # Call 3 - no name at all
        lines_3 = [{"text": "Some other text", "confidence": 0.7}]
        r3 = extract_fields(lines_3)

        assert r1["full_name"] == "ALPHA PERSON"
        assert r2["full_name"] == "BETA PERSON"
        assert r3["full_name"] is None

    def test_passport_document_isolation(self):
        """Different passport MRZ data should produce isolated results."""
        mrz_a = {
            "detected": True,
            "line1": "P<INDKUMAR<<RAVI<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "Y123456784IND8506155M3012315<<<<<<<<<<<<<04",
            "confidence": 0.92,
        }
        result_a = extract_fields([], document_type="passport", mrz_data=mrz_a)

        mrz_b = {
            "detected": True,
            "line1": "P<INDPATEL<<NITIN<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "Z987654324IND9001152F2812310<<<<<<<<<<<<<06",
            "confidence": 0.88,
        }
        result_b = extract_fields([], document_type="passport", mrz_data=mrz_b)

        assert result_a["surname"] == "Kumar"
        assert result_a["given_names"] == "Ravi"
        assert result_b["surname"] == "Patel"
        assert result_b["given_names"] == "Nitin"
        assert result_a["document_number"] == "Y12345678"
        assert result_b["document_number"] == "Z98765432"


# ---------- Test: Cross-source consistency ----------

class TestCrossSourceConsistency:
    """Test OCR vs MRZ consistency checking."""

    def test_consistent_date_of_birth(self):
        """When OCR and MRZ agree on DOB, status should be 'consistent'."""
        ocr_lines = [
            {"text": "Date of Birth:", "confidence": 0.95},
            {"text": "20/05/1983", "confidence": 0.97},  # Same as MRZ
        ]
        # TD3 MRZ line 2: passport(9)+check(1)+nationality(3)+dob(6)+check(1)+sex(1)+expiry(6)+check(1)+optional(15)+check(1) = 44
        mrz_data = {
            "detected": True,
            "line1": "P<INDTEST<<NAME<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "X123456784IND8305202M3012310<<<<<<<<<<<<<06",
            "confidence": 0.90,
        }
        result = extract_fields(ocr_lines, document_type="passport", mrz_data=mrz_data)

        # Both sources give 1983-05-20
        assert result["date_of_birth"] is not None
        status = result.get("field_status", {})
        assert status.get("date_of_birth") == "consistent"

    def test_conflicting_date_of_birth(self):
        """When OCR and MRZ disagree on DOB, status should be 'conflict'."""
        ocr_lines = [
            {"text": "Date of Birth:", "confidence": 0.95},
            {"text": "15/03/1990", "confidence": 0.97},  # Different from MRZ
        ]
        mrz_data = {
            "detected": True,
            "line1": "P<INDTEST<<NAME<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "X123456784IND8305202M3012310<<<<<<<<<<<<<06",  # DOB = 1983-05-20
            "confidence": 0.90,
        }
        result = extract_fields(ocr_lines, document_type="passport", mrz_data=mrz_data)

        status = result.get("field_status", {})
        assert status.get("date_of_birth") == "conflict"

    def test_conflicting_gender(self):
        """When OCR says MALE and MRZ says F, status should be 'conflict'."""
        ocr_lines = [
            {"text": "Gender:", "confidence": 0.95},
            {"text": "MALE", "confidence": 0.97},
        ]
        mrz_data = {
            "detected": True,
            "line1": "P<INDTEST<<NAME<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "X123456784IND8305202F3012310<<<<<<<<<<<<<06",  # Sex = F
            "confidence": 0.90,
        }
        result = extract_fields(ocr_lines, document_type="passport", mrz_data=mrz_data)

        status = result.get("field_status", {})
        assert status.get("gender") == "conflict"

    def test_mrz_only_field_is_extracted(self):
        """Fields found only in MRZ (not OCR) should have status 'extracted'."""
        ocr_lines = [
            {"text": "Some random text", "confidence": 0.80},
        ]
        mrz_data = {
            "detected": True,
            "line1": "P<INDTEST<<NAME<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "X123456784IND8305202M3012310<<<<<<<<<<<<<06",
            "confidence": 0.90,
        }
        result = extract_fields(ocr_lines, document_type="passport", mrz_data=mrz_data)

        status = result.get("field_status", {})
        assert status.get("document_number") == "extracted"
        assert status.get("date_of_birth") == "extracted"
        assert result["document_number"] == "X12345678"

    def test_no_mrz_fields_use_extracted_status(self):
        """Without MRZ, extracted fields should have status 'extracted'."""
        ocr_lines = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "TEST PERSON", "confidence": 0.98},
        ]
        result = extract_fields(ocr_lines, document_type="aadhaar")

        status = result.get("field_status", {})
        assert status.get("full_name") == "extracted"
        assert status.get("date_of_birth") == "not_detected"


# ---------- Test: Compare function ----------

class TestCompareFunction:
    """Test the _compare_field_values helper."""

    def test_identical_values_are_consistent(self):
        assert _compare_field_values("1983-05-20", "1983-05-20", "date_of_birth") == "consistent"

    def test_different_dates_are_conflict(self):
        assert _compare_field_values("1990-03-15", "1983-05-20", "date_of_birth") == "conflict"

    def test_different_date_formats_same_date(self):
        # 20/05/1983 and 1983-05-20 should be the same date
        result = _compare_field_values("20/05/1983", "1983-05-20", "date_of_birth")
        assert result == "consistent"

    def test_missing_ocr_value_is_consistent(self):
        assert _compare_field_values(None, "1983-05-20", "date_of_birth") == "consistent"

    def test_missing_mrz_value_is_consistent(self):
        assert _compare_field_values("1983-05-20", None, "date_of_birth") == "consistent"

    def test_both_missing_is_consistent(self):
        assert _compare_field_values(None, None, "date_of_birth") == "consistent"

    def test_different_genders_are_conflict(self):
        assert _compare_field_values("MALE", "F", "gender") == "conflict"

    def test_same_gender_normalized(self):
        # "Male" normalizes to "M", "M" stays "M"
        assert _compare_field_values("Male", "M", "gender") == "consistent"

    def test_female_vs_f_is_consistent(self):
        assert _compare_field_values("FEMALE", "F", "gender") == "consistent"

    def test_different_nationality_is_conflict(self):
        assert _compare_field_values("IND", "USA", "nationality") == "conflict"

    def test_same_nationality_case_insensitive(self):
        assert _compare_field_values("ind", "IND", "nationality") == "consistent"


# ---------- Test: Normalize function ----------

class TestNormalizeForComparison:
    """Test the _normalize_for_comparison helper."""

    def test_normalize_date_dmy(self):
        assert _normalize_for_comparison("20/05/1983", "date_of_birth") == "1983-05-20"

    def test_normalize_date_iso(self):
        assert _normalize_for_comparison("1983-05-20", "date_of_birth") == "1983-05-20"

    def test_normalize_gender(self):
        # "Male" normalizes to "M" for comparison with MRZ single-letter sex
        assert _normalize_for_comparison("Male", "gender") == "M"

    def test_normalize_nationality(self):
        assert _normalize_for_comparison("ind", "nationality") == "IND"

    def test_normalize_empty(self):
        assert _normalize_for_comparison("", "date_of_birth") == ""

    def test_normalize_none(self):
        assert _normalize_for_comparison(None, "date_of_birth") == ""


# ---------- Test: field_status populated correctly ----------

class TestFieldStatus:
    """Verify field_status dict is populated for every extraction."""

    def test_field_status_has_all_keys(self):
        """field_status should have an entry for every field."""
        ocr_lines = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "TEST PERSON", "confidence": 0.98},
        ]
        result = extract_fields(ocr_lines)
        field_status = result.get("field_status", {})

        # Should have status for all standard fields
        expected_keys = [
            "full_name", "date_of_birth", "document_number", "address",
            "gender", "father_name", "surname", "given_names", "nationality",
            "place_of_birth", "place_of_issue", "date_of_issue", "date_of_expiry",
        ]
        for key in expected_keys:
            assert key in field_status, f"field_status missing key: {key}"
            assert field_status[key] in ("extracted", "not_detected", "consistent", "conflict")

    def test_extracted_field_has_status_extracted(self):
        ocr_lines = [
            {"text": "Name:", "confidence": 0.95},
            {"text": "TEST PERSON", "confidence": 0.98},
        ]
        result = extract_fields(ocr_lines)
        assert result["field_status"]["full_name"] == "extracted"

    def test_missing_field_has_status_not_detected(self):
        ocr_lines = [
            {"text": "Some random text", "confidence": 0.80},
        ]
        result = extract_fields(ocr_lines)
        assert result["field_status"]["full_name"] == "not_detected"
        assert result["field_status"]["date_of_birth"] == "not_detected"
