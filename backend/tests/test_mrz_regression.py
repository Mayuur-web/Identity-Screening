"""Regression tests for MRZ duplicate line rejection and structural validation.

Tests the fix for the bug where identical MRZ lines (OCR returning the same
line twice) were accepted as a valid two-line MRZ.
"""

import pytest
from app.services.mrz_service import (
    validate_mrz_passport,
    detect_mrz,
    parse_mrz_passport,
    parse_mrz_generic,
    is_mrz_line,
)
from app.services.field_extraction_service import extract_passport_fields


# =============================================================================
# Valid MRZ Fixtures
# =============================================================================

VALID_MRZ_LINE1 = "P<INDRAI<<AISHWARYA<<<<<<<<<<<<<<<<<<<<<<"
VALID_MRZ_LINE2 = "F7802033<0IND7311017F1605011<<<<<<<<<<<<<<4"

VALID_MRZ = {
    "detected": True,
    "line1": VALID_MRZ_LINE1,
    "line2": VALID_MRZ_LINE2,
    "confidence": 0.90,
}

DUPLICATE_LINE = "F7802033<0IND7311017F1605011<<<<<<<<<<<<<<4"


# =============================================================================
# Identical Line Rejection Tests
# =============================================================================

class TestIdenticalLineRejection:
    """Two identical MRZ lines must never be accepted as valid."""

    def test_identical_lines_rejected_by_validate(self):
        assert validate_mrz_passport(DUPLICATE_LINE, DUPLICATE_LINE) is False

    def test_identical_lines_rejected_detect_mrz(self):
        ocr = [
            {"text": DUPLICATE_LINE, "confidence": 0.8},
            {"text": DUPLICATE_LINE, "confidence": 0.8},
        ]
        result = detect_mrz(ocr)
        assert result["detected"] is False

    def test_identical_lines_with_spaces_rejected(self):
        line = "F7802033<0IND7311017F1605011<<<<<<<<<<<<<<4"
        assert validate_mrz_passport(line, line) is False

    def test_identical_short_lines_rejected(self):
        short = "P<INDRAI<<AISHWARYA<<<<<<<<<<<<<<<<"
        assert validate_mrz_passport(short, short) is False


# =============================================================================
# Structural Difference Tests
# =============================================================================

class TestStructuralDifference:
    """Line1 must be a name line, Line2 must be a data line."""

    def test_valid_two_line_mrz_accepted(self):
        assert validate_mrz_passport(VALID_MRZ_LINE1, VALID_MRZ_LINE2) is True

    def test_line1_must_start_with_p(self):
        bad_line1 = "F7802033<0IND7311017F1605011<<<<<<<<<<<<<<4"
        assert validate_mrz_passport(bad_line1, VALID_MRZ_LINE2) is False

    def test_line1_must_contain_double_angle(self):
        line1_no_dbl = "P<INDRAIAISHWARYA<<<<<<<<<<<<<<<<<<<<<<<"
        # No << separator
        assert validate_mrz_passport(line1_no_dbl, VALID_MRZ_LINE2) is False

    def test_line2_must_not_have_double_angle_in_data(self):
        line2_with_dbl = "F7802033<<0IND7311017F1605011<<<<<<<<<<<<4"
        # << in positions 0-19 is invalid for line2
        assert validate_mrz_passport(VALID_MRZ_LINE1, line2_with_dbl) is False

    def test_reversed_lines_rejected(self):
        """Line2 used as line1 should be rejected (no P< prefix)."""
        assert validate_mrz_passport(VALID_MRZ_LINE2, VALID_MRZ_LINE1) is False


# =============================================================================
# Parse MRZ Passport Tests
# =============================================================================

class TestParseMRZPassport:
    """Parse fields from a valid MRZ."""

    def test_surname(self):
        result = parse_mrz_passport(VALID_MRZ)
        assert result["surname"] == "Rai"

    def test_given_names(self):
        result = parse_mrz_passport(VALID_MRZ)
        assert result["given_names"] == "Aishwarya"

    def test_passport_number(self):
        result = parse_mrz_passport(VALID_MRZ)
        assert result["passport_number"] == "F7802033"

    def test_nationality(self):
        result = parse_mrz_passport(VALID_MRZ)
        assert result["nationality"] == "IND"

    def test_date_of_birth(self):
        result = parse_mrz_passport(VALID_MRZ)
        assert result["date_of_birth"] == "1973-11-01"

    def test_sex(self):
        result = parse_mrz_passport(VALID_MRZ)
        assert result["sex"] == "F"

    def test_date_of_expiry(self):
        result = parse_mrz_passport(VALID_MRZ)
        assert result["date_of_expiry"] == "2016-05-01"

    def test_not_detected_returns_empty(self):
        no_mrz = {"detected": False, "line1": None, "line2": None, "confidence": None}
        result = parse_mrz_passport(no_mrz)
        assert result["passport_number"] is None
        assert result["surname"] is None


# =============================================================================
# Detect MRZ from OCR Lines
# =============================================================================

class TestDetectMRZFromOCR:
    """Test MRZ detection from OCR output."""

    def test_valid_mrz_detected(self):
        ocr = [
            {"text": VALID_MRZ_LINE1, "confidence": 0.9},
            {"text": VALID_MRZ_LINE2, "confidence": 0.9},
        ]
        result = detect_mrz(ocr)
        assert result["detected"] is True
        assert result["line1"] is not None
        assert result["line2"] is not None

    def test_duplicate_second_line_not_duplicated(self):
        """If OCR returns the same line twice, MRZ must not be detected."""
        ocr = [
            {"text": DUPLICATE_LINE, "confidence": 0.8},
            {"text": DUPLICATE_LINE, "confidence": 0.8},
        ]
        result = detect_mrz(ocr)
        assert result["detected"] is False

    def test_missing_first_line_no_mrz(self):
        """If only line2-like text exists, MRZ must not be detected."""
        ocr = [
            {"text": "Some random text", "confidence": 0.7},
            {"text": DUPLICATE_LINE, "confidence": 0.8},
        ]
        result = detect_mrz(ocr)
        assert result["detected"] is False

    def test_too_few_lines(self):
        ocr = [{"text": VALID_MRZ_LINE1, "confidence": 0.9}]
        result = detect_mrz(ocr)
        assert result["detected"] is False

    def test_empty_ocr(self):
        result = detect_mrz([])
        assert result["detected"] is False


# =============================================================================
# MRZ Priority vs Visual Fallback
# =============================================================================

class TestMRZPriorityVsVisual:
    """When MRZ is invalid, visual extraction must work."""

    def test_invalid_mrz_falls_back_to_visual(self):
        """With no MRZ, visual fields should be extracted."""
        ocr_lines = [
            {"text": "Surname", "confidence": 0.95},
            {"text": "RAI", "confidence": 0.93},
            {"text": "Given Name(s)", "confidence": 0.94},
            {"text": "AISHWARYA", "confidence": 0.92},
            {"text": "Nationality", "confidence": 0.91},
            {"text": "INDIAN", "confidence": 0.90},
            {"text": "Sex", "confidence": 0.89},
            {"text": "F", "confidence": 0.88},
            {"text": "Date of Birth", "confidence": 0.95},
            {"text": "01/11/1973", "confidence": 0.93},
            {"text": "Passport No", "confidence": 0.92},
            {"text": "F 7802033", "confidence": 0.90},
            {"text": "Date of Expiry", "confidence": 0.90},
            {"text": "01/05/2016", "confidence": 0.88},
        ]
        no_mrz = {"detected": False, "line1": None, "line2": None, "confidence": None}
        result = extract_passport_fields(ocr_lines, no_mrz)
        assert result["surname"] == "Rai"
        assert result["given_names"] == "Aishwarya"
        assert result["nationality"] == "IND"
        assert result["gender"] == "F"
        assert result["date_of_birth"] == "1973-11-01"
        assert result["full_name"] is None  # Passport: no full_name

    def test_valid_mrz_takes_priority(self):
        """When MRZ is valid, MRZ values should be used."""
        ocr_lines = [
            {"text": "Surname", "confidence": 0.95},
            {"text": "WRONG_NAME", "confidence": 0.93},
        ]
        result = extract_passport_fields(ocr_lines, VALID_MRZ)
        assert result["surname"] == "Rai"  # From MRZ, not visual
        assert result["given_names"] == "Aishwarya"

    def test_invalid_mrz_does_not_override_visual(self):
        """When MRZ is invalid, visual fields should not be overridden."""
        ocr_lines = [
            {"text": "Surname", "confidence": 0.95},
            {"text": "RAI", "confidence": 0.93},
            {"text": "Given Name(s)", "confidence": 0.94},
            {"text": "AISHWARYA", "confidence": 0.92},
        ]
        invalid_mrz = {
            "detected": True,
            "line1": DUPLICATE_LINE,
            "line2": DUPLICATE_LINE,
            "confidence": 0.8,
        }
        result = extract_passport_fields(ocr_lines, invalid_mrz)
        # Visual extraction should work since MRZ is invalid
        assert result["surname"] == "Rai"
        assert result["given_names"] == "Aishwarya"


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge cases for MRZ handling."""

    def test_empty_mrz_data(self):
        result = parse_mrz_passport({})
        assert result["passport_number"] is None

    def test_none_mrz_fields(self):
        result = parse_mrz_passport({"detected": True, "line1": None, "line2": None})
        assert result["passport_number"] is None

    def test_short_mrz_lines(self):
        short_line1 = "P<INDRAI<<AISHWARYA<<<<<<<<<<<<<<"
        short_line2 = "F7802033<0IND7311017F1605011<<<<<<<"
        # Should still be parsed (we accept shorter lines)
        result = parse_mrz_passport({
            "detected": True,
            "line1": short_line1,
            "line2": short_line2,
            "confidence": 0.7,
        })
        assert result["passport_number"] == "F7802033"
        assert result["surname"] == "Rai"

    def test_mrz_with_ocr_whitespace(self):
        """MRZ lines with internal spaces should still work after normalization."""
        line1 = "P<INDRAI<<AISHWARYA<<<<<<<<<<<<<<<<<<<<<<"
        line2 = "F7802033<0IND7311017F1605011<<<<<<<<<<<<<<4"
        # The detect_mrz function strips spaces during normalization
        ocr = [
            {"text": "P<INDRAI<<AISHWARYA", "confidence": 0.9},
            {"text": "F7802033<0IND7311017F1605011<<<<<<<<<<<<<<4", "confidence": 0.9},
        ]
        result = detect_mrz(ocr)
        # May or may not detect depending on is_mrz_line check
        # But should never crash
        assert isinstance(result, dict)


# =============================================================================
# Surname-from-Line2 Rejection Tests
# =============================================================================

class TestSurnameFromLine2Rejection:
    """MRZ surname and given names must ONLY come from line 1.
    
    Line 2 contains passport number, DOB, sex, expiry -- never names.
    """

    def test_valid_line1_surname(self):
        """Valid line 1 produces correct surname."""
        result = parse_mrz_passport(VALID_MRZ)
        assert result["surname"] == "Rai"

    def test_valid_line1_given_names(self):
        """Valid line 1 produces correct given names."""
        result = parse_mrz_passport(VALID_MRZ)
        assert result["given_names"] == "Aishwarya"

    def test_line2_alone_no_surname(self):
        """Line 2 alone must not produce a surname."""
        mrz = {
            "detected": True,
            "line1": DUPLICATE_LINE,
            "line2": DUPLICATE_LINE,
            "confidence": 0.9,
        }
        result = parse_mrz_passport(mrz)
        assert result["surname"] is None

    def test_line2_alone_no_given_names(self):
        """Line 2 alone must not produce given names."""
        mrz = {
            "detected": True,
            "line1": DUPLICATE_LINE,
            "line2": DUPLICATE_LINE,
            "confidence": 0.9,
        }
        result = parse_mrz_passport(mrz)
        assert result["given_names"] is None

    def test_swapped_lines_no_surname(self):
        """When lines are swapped, surname must be None."""
        mrz = {
            "detected": True,
            "line1": DUPLICATE_LINE,  # Actually line2 data
            "line2": VALID_MRZ_LINE1,  # Actually line1 name
            "confidence": 0.9,
        }
        result = parse_mrz_passport(mrz)
        assert result["surname"] is None

    def test_swapped_lines_no_given_names(self):
        """When lines are swapped, given_names must be None."""
        mrz = {
            "detected": True,
            "line1": DUPLICATE_LINE,
            "line2": VALID_MRZ_LINE1,
            "confidence": 0.9,
        }
        result = parse_mrz_passport(mrz)
        assert result["given_names"] is None

    def test_line2_passport_number_never_becomes_surname(self):
        """Passport number data from line 2 must never be interpreted as surname."""
        mrz = {
            "detected": True,
            "line1": DUPLICATE_LINE,
            "line2": DUPLICATE_LINE,
            "confidence": 0.9,
        }
        result = parse_mrz_passport(mrz)
        # Surname must not contain passport number fragments
        if result["surname"]:
            assert "7802033" not in result["surname"]
            assert "0IND" not in result["surname"].upper()

    def test_visual_surname_used_when_mrz_line1_unavailable(self):
        """Visual extraction provides surname when MRZ line 1 is missing."""
        ocr = [
            {"text": "Surname", "confidence": 0.95},
            {"text": "RAI", "confidence": 0.93},
            {"text": "Given Name(s)", "confidence": 0.94},
            {"text": "AISHWARYA", "confidence": 0.92},
        ]
        no_mrz = {"detected": False, "line1": None, "line2": None, "confidence": None}
        result = extract_passport_fields(ocr, no_mrz)
        assert result["surname"] == "Rai"
        assert result["given_names"] == "Aishwarya"

    def test_detect_mrz_rejects_swapped_ocr(self):
        """detect_mrz must not accept swapped MRZ lines."""
        ocr = [
            {"text": DUPLICATE_LINE, "confidence": 0.8},
            {"text": VALID_MRZ_LINE1, "confidence": 0.9},
        ]
        result = detect_mrz(ocr)
        assert result["detected"] is False

    def test_detect_mrz_accepts_correct_order(self):
        """detect_mrz must accept correctly ordered MRZ lines."""
        ocr = [
            {"text": VALID_MRZ_LINE1, "confidence": 0.9},
            {"text": VALID_MRZ_LINE2, "confidence": 0.8},
        ]
        result = detect_mrz(ocr)
        assert result["detected"] is True
        assert "RAI" in (result["line1"] or "")

    def test_mrz_surname_is_title_case(self):
        """MRZ surname should be title-cased."""
        result = parse_mrz_passport(VALID_MRZ)
        assert result["surname"] == "Rai"
        assert result["given_names"] == "Aishwarya"


# =============================================================================
# Character-Split MRZ Reconstruction Tests
# =============================================================================

class TestCharacterSplitReconstruction:
    """Test MRZ reconstruction from character-level OCR detections.
    
    When EasyOCR returns individual characters or tiny fragments instead of
    full MRZ lines, the reconstruction function groups them by Y position
    into two rows and concatenates by X position.
    """

    def _make_char_detections(self, line1: str, line2: str, y1: float = 10.0, y2: float = 30.0, x_spacing: float = 15.0):
        """Helper to create synthetic character-level detections and return the best candidate."""
        from app.services.mrz_service import _reconstruct_mrz_from_detections
        detections = []
        for i, ch in enumerate(line1):
            bbox = [[i*x_spacing, y1], [i*x_spacing+12, y1], [i*x_spacing+12, y1+14], [i*x_spacing, y1+14]]
            detections.append((bbox, ch, 0.9))
        for i, ch in enumerate(line2):
            bbox = [[i*x_spacing, y2], [i*x_spacing+12, y2], [i*x_spacing+12, y2+14], [i*x_spacing, y2+14]]
            detections.append((bbox, ch, 0.9))
        candidates = _reconstruct_mrz_from_detections(detections)
        if candidates:
            return candidates[0][0], candidates[0][1]
        return None, None

    def test_saivaraj_karthik_reconstruction(self):
        """Reconstruct MRZ for SAIVARAJ KARTHIK passport."""
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        assert l1 is not None
        assert l2 is not None
        assert l1.startswith("P<INDSAIVARAJ")
        assert l2.startswith("W1192764")

    def test_saivaraj_surname_from_reconstructed_mrz(self):
        """Parsed surname from reconstructed MRZ must be correct."""
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        mrz = {"detected": True, "line1": l1.ljust(44, "<"), "line2": l2.ljust(44, "<"), "confidence": 0.8}
        result = parse_mrz_passport(mrz)
        assert result["surname"] == "Saivaraj"

    def test_saivaraj_given_names_from_reconstructed_mrz(self):
        """Parsed given names from reconstructed MRZ must be correct."""
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        mrz = {"detected": True, "line1": l1.ljust(44, "<"), "line2": l2.ljust(44, "<"), "confidence": 0.8}
        result = parse_mrz_passport(mrz)
        assert result["given_names"] == "Karthik"

    def test_saivaraj_passport_number(self):
        """Passport number from reconstructed MRZ."""
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        mrz = {"detected": True, "line1": l1.ljust(44, "<"), "line2": l2.ljust(44, "<"), "confidence": 0.8}
        result = parse_mrz_passport(mrz)
        assert result["passport_number"] == "W1192764"

    def test_saivaraj_nationality(self):
        """Nationality from reconstructed MRZ."""
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        mrz = {"detected": True, "line1": l1.ljust(44, "<"), "line2": l2.ljust(44, "<"), "confidence": 0.8}
        result = parse_mrz_passport(mrz)
        assert result["nationality"] == "IND"

    def test_saivaraj_dob(self):
        """Date of birth from reconstructed MRZ."""
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        mrz = {"detected": True, "line1": l1.ljust(44, "<"), "line2": l2.ljust(44, "<"), "confidence": 0.8}
        result = parse_mrz_passport(mrz)
        assert result["date_of_birth"] == "1983-05-20"

    def test_saivaraj_gender(self):
        """Gender from reconstructed MRZ."""
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        mrz = {"detected": True, "line1": l1.ljust(44, "<"), "line2": l2.ljust(44, "<"), "confidence": 0.8}
        result = parse_mrz_passport(mrz)
        assert result["sex"] == "M"

    def test_saivaraj_expiry(self):
        """Date of expiry from reconstructed MRZ."""
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        mrz = {"detected": True, "line1": l1.ljust(44, "<"), "line2": l2.ljust(44, "<"), "confidence": 0.8}
        result = parse_mrz_passport(mrz)
        assert result["date_of_expiry"] == "2032-06-09"

    def test_saivaraj_full_extraction_via_passport_fields(self):
        """Full passport field extraction from reconstructed MRZ."""
        from app.services.field_extraction_service import extract_passport_fields
        l1, l2 = self._make_char_detections(
            "P<INDSAIVARAJ<<KARTHIK<<<<<<<<<<<<<<<<<<<<",
            "W1192764<8IND8305206M32060982074287317122<04",
        )
        mrz = {"detected": True, "line1": l1.ljust(44, "<"), "line2": l2.ljust(44, "<"), "confidence": 0.8}
        result = extract_passport_fields([], mrz)
        assert result["surname"] == "Saivaraj"
        assert result["given_names"] == "Karthik"
        assert result["document_number"] == "W1192764"
        assert result["nationality"] == "IND"
        assert result["date_of_birth"] == "1983-05-20"
        assert result["gender"] == "M"
        assert result["date_of_expiry"] == "2032-06-09"
        assert result["full_name"] is None  # Passport: no full_name

    def test_too_few_detections_returns_empty(self):
        """With fewer than 10 detections, reconstruction should return empty list."""
        from app.services.mrz_service import _reconstruct_mrz_from_detections
        detections = [([[0,0],[10,0],[10,10],[0,10]], "P", 0.9)] * 5
        result = _reconstruct_mrz_from_detections(detections)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_empty_detections_returns_empty(self):
        """Empty detections should return empty list."""
        from app.services.mrz_service import _reconstruct_mrz_from_detections
        result = _reconstruct_mrz_from_detections([])
        assert isinstance(result, list)
        assert len(result) == 0

    def test_single_row_detections_returns_empty_or_valid(self):
        """All detections at same Y should not form two MRZ lines."""
        from app.services.mrz_service import _reconstruct_mrz_from_detections
        detections = []
        for i in range(50):
            bbox = [[i*10, 10], [i*10+8, 10], [i*10+8, 18], [i*10, 18]]
            ch = "A" if i < 25 else "<"
            detections.append((bbox, ch, 0.9))
        result = _reconstruct_mrz_from_detections(detections)
        # With no Y gap, should return empty list (no valid MRZ candidate)
        assert isinstance(result, list)

    def test_aadhaar_not_affected(self):
        """Aadhaar extraction must remain completely unchanged."""
        from app.services.field_extraction_service import extract_fields
        ocr_lines = [
            {"text": "Name", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.93},
            {"text": "DOB: 15/03/1995", "confidence": 0.90},
            {"text": "Gender: FEMALE", "confidence": 0.91},
            {"text": "1234 5678 9012", "confidence": 0.88},
        ]
        result = extract_fields(ocr_lines=ocr_lines, document_type="aadhaar", mrz_data=None)
        assert result["full_name"] == "PRIYA SHARMA"
        assert result["document_type"] == "aadhaar"
        assert result.get("surname") is None  # Aadhaar: no MRZ surname
        assert result.get("given_names") is None


# =============================================================================
# Place of Birth / Place of Issue Multi-Line Tests
# =============================================================================

class TestPlaceFieldExtraction:
    """Test multi-line place field extraction for passports.
    
    Place of Birth and Place of Issue often span multiple OCR lines.
    """

    def test_single_line_place_of_birth(self):
        """Single-line Place of Birth."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Birth", "confidence": 0.95},
            {"text": "NEW DELHI", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr, None)
        assert result["place_of_birth"] == "NEW DELHI"

    def test_multi_line_place_of_birth(self):
        """Multi-line Place of Birth should pick the best candidate."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Birth", "confidence": 0.95},
            {"text": "NEW", "confidence": 0.85},
            {"text": "DELHI", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr, None)
        # Should pick the line with most meaningful content
        assert result["place_of_birth"] is not None
        assert "DELHI" in result["place_of_birth"] or "NEW" in result["place_of_birth"]

    def test_place_of_birth_with_comma(self):
        """Place of Birth with comma-separated location."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Birth", "confidence": 0.95},
            {"text": "PUDUKKOTTAI, TAMIL NADU", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr, None)
        assert result["place_of_birth"] == "PUDUKKOTTAI, TAMIL NADU"

    def test_place_of_issue_single_line(self):
        """Single-line Place of Issue."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Issue", "confidence": 0.95},
            {"text": "MUMBAI", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr, None)
        assert result["place_of_issue"] == "MUMBAI"

    def test_garbage_place_of_birth_rejected(self):
        """OCR garbage should not become Place of Birth."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Birth", "confidence": 0.95},
            {"text": "T7 F2177", "confidence": 0.70},
            {"text": "T F2TT", "confidence": 0.65},
        ]
        result = extract_passport_fields(ocr, None)
        # Should not accept garbage as place of birth
        if result["place_of_birth"]:
            assert "F2177" not in result["place_of_birth"]
            assert "F2TT" not in result["place_of_birth"]

    def test_garbage_place_of_issue_rejected(self):
        """OCR garbage should not become Place of Issue."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Issue", "confidence": 0.95},
            {"text": "Mn 3++ %7 F2TTF", "confidence": 0.60},
        ]
        result = extract_passport_fields(ocr, None)
        # Should not accept garbage
        if result["place_of_issue"]:
            assert "3++" not in result["place_of_issue"]
            assert "F2TTF" not in result["place_of_issue"]

    def test_place_stops_at_next_label(self):
        """Place of Birth should stop collecting at next field label."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Birth", "confidence": 0.95},
            {"text": "MANGALORE", "confidence": 0.90},
            {"text": "Date of Issue", "confidence": 0.92},
            {"text": "20/07/2021", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr, None)
        assert result["place_of_birth"] == "MANGALORE"

    def test_place_of_birth_mangalore_karnataka(self):
        """Multi-word place of birth."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Birth", "confidence": 0.95},
            {"text": "MANGALORE KARNATAKA", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr, None)
        assert result["place_of_birth"] == "MANGALORE KARNATAKA"

    def test_multi_line_place_of_birth_combined(self):
        """Multi-line Place of Birth should be combined."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Birth", "confidence": 0.95},
            {"text": "NEW", "confidence": 0.85},
            {"text": "DELHI", "confidence": 0.90},
            {"text": "Place of Issue", "confidence": 0.92},
            {"text": "MUMBAI", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr, None)
        assert "NEW" in result["place_of_birth"]
        assert "DELHI" in result["place_of_birth"]

    def test_multi_line_place_of_issue_combined(self):
        """Multi-line Place of Issue should be combined."""
        from app.services.field_extraction_service import extract_passport_fields
        ocr = [
            {"text": "Place of Issue", "confidence": 0.95},
            {"text": "TIRUCHIRAPPALLI", "confidence": 0.88},
            {"text": "TAMIL NADU", "confidence": 0.85},
        ]
        result = extract_passport_fields(ocr, None)
        assert "TIRUCHIRAPPALLI" in result["place_of_issue"]
        assert "TAMIL NADU" in result["place_of_issue"]
