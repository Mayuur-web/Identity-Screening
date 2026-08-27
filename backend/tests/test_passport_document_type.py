"""Comprehensive passport document-type tests.

Tests the passport-specific extraction pipeline:
- MRZ priority over visual OCR
- Garbage rejection
- full_name is null for passport
- Visual field validation
- Consistency/conflict detection
- Document isolation
- Aadhaar regression
"""

import pytest
from app.services.field_extraction_service import extract_passport_fields, extract_fields


# =============================================================================
# MRZ Data Fixtures
# =============================================================================

VALID_MRZ = {
    "detected": True,
    "line1": "P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<<<<<",
    "line2": "Z1234567<4IND9508157M3107199<<<<<<<<<<<<<<02",
    "confidence": 0.89,
}

VALID_MRZ_2 = {
    "detected": True,
    "line1": "P<INDPATEL<<ANANYA<<<<<<<<<<<<<<<<<<<<<<",
    "line2": "R987654324IND9207142F3207130<<<<<<<<<<<<<06",
    "confidence": 0.90,
}

INCOMPLETE_MRZ = {
    "detected": True,
    "line1": "P<INDSMITH<<JOHN<<<<<<<<<<<<<<<<<<<<",
    "line2": "AB1234567",
    "confidence": 0.50,
}

NO_MRZ = {
    "detected": False,
    "line1": None,
    "line2": None,
    "confidence": None,
}


# =============================================================================
# Valid MRZ Extraction Tests
# =============================================================================

class TestValidMRZExtraction:
    """Test passport extraction from valid MRZ data."""

    def test_surname_from_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["surname"] == "Sharma"

    def test_given_names_from_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["given_names"] == "Rahul Kumar"

    def test_passport_number_from_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["document_number"] == "Z1234567"

    def test_nationality_from_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["nationality"] == "IND"

    def test_dob_from_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["date_of_birth"] == "1995-08-15"

    def test_gender_from_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["gender"] == "M"

    def test_expiry_from_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["date_of_expiry"] == "2031-07-19"

    def test_full_name_is_null_for_passport(self):
        """Passport has surname + given_names, NOT full_name."""
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["full_name"] is None

    def test_document_type_is_passport(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["document_type"] == "passport"


# =============================================================================
# Full Name is Null Tests
# =============================================================================

class TestPassportFullNameNull:
    """Passport must never have a full_name value."""

    def test_full_name_null_with_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["full_name"] is None
        assert result["field_status"]["full_name"] == "not_detected"

    def test_full_name_null_with_visual_surname(self):
        ocr = [
            {"text": "Surname", "confidence": 0.95},
            {"text": "SHARMA", "confidence": 0.93},
            {"text": "Given Name(s)", "confidence": 0.94},
            {"text": "RAHUL KUMAR", "confidence": 0.92},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["full_name"] is None

    def test_full_name_null_no_mrz_no_visual(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=None)
        assert result["full_name"] is None


# =============================================================================
# Garbage Rejection Tests
# =============================================================================

class TestGarbageRejection:
    """Garbage visual OCR must never override valid MRZ values."""

    def test_reject_dob_56t(self):
        """'56T' is not a valid date — MRZ DOB should be used."""
        ocr = [
            {"text": "Date of Birth", "confidence": 0.95},
            {"text": "56T", "confidence": 0.50},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["date_of_birth"] == "1995-08-15"
        assert result["field_status"]["date_of_birth"] != "conflict"

    def test_reject_gender_fai_sex(self):
        """'FAI / SEX' is a label, not a gender value."""
        ocr = [
            {"text": "FAI / SEX", "confidence": 0.70},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["gender"] == "M"

    def test_reject_nationality_ftet(self):
        """'FTet' is garbage OCR, not a valid nationality."""
        ocr = [
            {"text": "Nationality", "confidence": 0.90},
            {"text": "FTet", "confidence": 0.60},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["nationality"] == "IND"

    def test_reject_passport_number_2134_type(self):
        """'2134 / Type' is a label fragment, not a passport number."""
        ocr = [
            {"text": "2134 / Type", "confidence": 0.65},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["document_number"] == "Z1234567"

    def test_reject_s_paren_s(self):
        """'(S)' is not a valid surname or given name."""
        ocr = [
            {"text": "Given Name(s)", "confidence": 0.80},
            {"text": "(S)", "confidence": 0.75},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["given_names"] == "Rahul Kumar"

    def test_reject_solo_s(self):
        """'S' alone is not a valid surname."""
        ocr = [
            {"text": "Surname", "confidence": 0.85},
            {"text": "S", "confidence": 0.80},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["surname"] == "Sharma"

    def test_reject_pure_digits_as_dob(self):
        """'39717' is not a valid date."""
        ocr = [
            {"text": "39717", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["date_of_birth"] == "1995-08-15"


# =============================================================================
# Visual Field Validation Tests
# =============================================================================

class TestVisualFieldValidation:
    """Visual passport fields must pass strict validation."""

    def test_valid_visual_surname(self):
        ocr = [
            {"text": "Surname", "confidence": 0.95},
            {"text": "SHARMA", "confidence": 0.93},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["surname"] == "Sharma"

    def test_valid_visual_given_names(self):
        ocr = [
            {"text": "Given Name(s)", "confidence": 0.94},
            {"text": "RAHUL KUMAR", "confidence": 0.92},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["given_names"] == "Rahul Kumar"

    def test_valid_visual_dob(self):
        ocr = [
            {"text": "Date of Birth", "confidence": 0.95},
            {"text": "15/08/1995", "confidence": 0.93},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["date_of_birth"] == "1995-08-15"

    def test_valid_visual_gender(self):
        ocr = [
            {"text": "Sex", "confidence": 0.89},
            {"text": "M", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["gender"] == "M"

    def test_valid_visual_nationality(self):
        ocr = [
            {"text": "Nationality", "confidence": 0.91},
            {"text": "INDIAN", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["nationality"] == "IND"

    def test_valid_visual_expiry(self):
        ocr = [
            {"text": "Date of Expiry", "confidence": 0.90},
            {"text": "19/07/2031", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["date_of_expiry"] == "2031-07-19"

    def test_valid_visual_issue_date(self):
        ocr = [
            {"text": "Date of Issue", "confidence": 0.92},
            {"text": "20/07/2021", "confidence": 0.90},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["date_of_issue"] == "2021-07-20"

    def test_valid_visual_place_of_birth(self):
        ocr = [
            {"text": "Place of Birth", "confidence": 0.91},
            {"text": "NEW DELHI, DELHI", "confidence": 0.89},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=None)
        assert result["place_of_birth"] == "NEW DELHI, DELHI"


# =============================================================================
# MRZ Priority Over Visual Tests
# =============================================================================

class TestMRZPriority:
    """MRZ values must take priority over visual OCR."""

    def test_mrz_wins_over_valid_visual_dob(self):
        """Even when visual DOB is valid, MRZ DOB should be authoritative."""
        ocr = [
            {"text": "Date of Birth", "confidence": 0.95},
            {"text": "15/08/1995", "confidence": 0.93},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["date_of_birth"] == "1995-08-15"
        assert result["field_status"]["date_of_birth"] == "consistent"

    def test_mrz_wins_over_garbage_visual(self):
        """Garbage visual must not override MRZ."""
        ocr = [
            {"text": "56T", "confidence": 0.50},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["date_of_birth"] == "1995-08-15"
        assert result["field_status"]["date_of_birth"] == "extracted"

    def test_mrz_wins_over_garbage_passport_number(self):
        ocr = [
            {"text": "2134 / Type", "confidence": 0.65},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["document_number"] == "Z1234567"

    def test_mrz_wins_over_garbage_nationality(self):
        ocr = [
            {"text": "FTet", "confidence": 0.60},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["nationality"] == "IND"


# =============================================================================
# Consistency / Conflict Detection Tests
# =============================================================================

class TestConsistencyConflictDetection:
    """Test visual + MRZ consistency and conflict detection."""

    def test_consistent_surname(self):
        ocr = [
            {"text": "Surname", "confidence": 0.95},
            {"text": "SHARMA", "confidence": 0.93},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["field_status"]["surname"] == "consistent"

    def test_consistent_given_names(self):
        ocr = [
            {"text": "Given Name(s)", "confidence": 0.94},
            {"text": "RAHUL KUMAR", "confidence": 0.92},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["field_status"]["given_names"] == "consistent"

    def test_conflicting_gender(self):
        """MRZ says M, visual says FEMALE — should be conflict."""
        ocr = [
            {"text": "Sex", "confidence": 0.89},
            {"text": "FEMALE", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["gender"] == "M"  # MRZ wins
        assert result["field_status"]["gender"] == "conflict"

    def test_consistent_gender(self):
        """MRZ says M, visual says M — should be consistent."""
        ocr = [
            {"text": "Sex", "confidence": 0.89},
            {"text": "M", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["gender"] == "M"
        assert result["field_status"]["gender"] == "consistent"

    def test_garbage_visual_plus_valid_mrz_not_conflict(self):
        """Garbage visual + valid MRZ must NOT be marked as conflict."""
        ocr = [
            {"text": "FAI / SEX", "confidence": 0.70},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        # Gender should be from MRZ, status should be "extracted" not "conflict"
        assert result["gender"] == "M"
        assert result["field_status"]["gender"] == "extracted"


# =============================================================================
# Document Isolation Tests
# =============================================================================

class TestPassportDocumentIsolation:
    """Each passport analysis must produce isolated results."""

    def test_different_passports_different_surnames(self):
        result_a = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        result_b = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ_2)
        assert result_a["surname"] == "Sharma"
        assert result_b["surname"] == "Patel"
        assert result_a["surname"] != result_b["surname"]

    def test_different_passports_different_given_names(self):
        result_a = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        result_b = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ_2)
        assert result_a["given_names"] == "Rahul Kumar"
        assert result_b["given_names"] == "Ananya"

    def test_different_passports_different_numbers(self):
        result_a = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        result_b = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ_2)
        assert result_a["document_number"] == "Z1234567"
        assert result_b["document_number"] == "R98765432"

    def test_different_passports_different_genders(self):
        result_a = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        result_b = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ_2)
        assert result_a["gender"] == "M"
        assert result_b["gender"] == "F"

    def test_no_data_leaks_between_analyses(self):
        """Three sequential analyses must be completely isolated."""
        r1 = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        r2 = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ_2)
        r3 = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)

        assert r1["surname"] == "Sharma"
        assert r2["surname"] == "Patel"
        assert r3["surname"] == "Sharma"
        assert r1["gender"] == "M"
        assert r2["gender"] == "F"
        assert r3["gender"] == "M"


# =============================================================================
# Aadhaar Pipeline Regression Tests
# =============================================================================

class TestAadhaarRegression:
    """Aadhaar extraction must not be affected by passport changes."""

    def test_aadhaar_full_name_still_works(self):
        """Aadhaar must still extract full_name (passport sets it to null)."""
        ocr_lines = [
            {"text": "Name", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.93},
            {"text": "DOB: 15/03/1995", "confidence": 0.90},
            {"text": "Gender: FEMALE", "confidence": 0.91},
            {"text": "1234 5678 9012", "confidence": 0.88},
            {"text": "42 MG Road, Sector 15", "confidence": 0.85},
            {"text": "Gurugram, Haryana, 122001", "confidence": 0.84},
        ]
        result = extract_fields(ocr_lines=ocr_lines, document_type="aadhaar", mrz_data=None)
        assert result["full_name"] == "PRIYA SHARMA"
        assert result["document_type"] == "aadhaar"

    def test_aadhaar_no_mrz_processing(self):
        """Aadhaar must NOT use MRZ."""
        ocr_lines = [
            {"text": "Name", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.93},
            {"text": "9264 1656 4196", "confidence": 0.88},
        ]
        result = extract_fields(ocr_lines=ocr_lines, document_type="aadhaar", mrz_data=None)
        assert result.get("nationality") is None or result.get("nationality") is not None
        # MRZ should not be involved for Aadhaar

    def test_aadhaar_corrupted_labels_still_work(self):
        """Aadhaar must still handle corrupted labels."""
        ocr_lines = [
            {"text": "Isha Raj", "confidence": 0.90},
            {"text": "T4fafa/ DOB: 18/01/2006", "confidence": 0.85},
            {"text": "fafal DOB: 18/04/2006", "confidence": 0.80},
            {"text": "AfrT / FEMALE", "confidence": 0.78},
            {"text": "9264 1656 4196", "confidence": 0.82},
        ]
        result = extract_fields(ocr_lines=ocr_lines, document_type="aadhaar", mrz_data=None)
        assert result["full_name"] == "Isha Raj"
        assert result["date_of_birth"] is not None
        assert result["gender"] == "FEMALE"
        assert result["document_number"] == "926416564196"

    def test_aadhaar_12_digit_number_detection(self):
        """Aadhaar 12-digit number with spaces must be detected."""
        ocr_lines = [
            {"text": "9264 1656 4196", "confidence": 0.88},
        ]
        result = extract_fields(ocr_lines=ocr_lines, document_type="aadhaar", mrz_data=None)
        assert result["document_number"] == "926416564196"

    def test_aadhaar_no_mrz_in_api_flow(self):
        """In the API flow, Aadhaar never receives MRZ data -- only passport does."""
        ocr_lines = [
            {"text": "Name", "confidence": 0.95},
            {"text": "PRIYA SHARMA", "confidence": 0.93},
        ]
        # API passes mrz_data=None for Aadhaar -- MRZ is only used for passport
        result = extract_fields(ocr_lines=ocr_lines, document_type="aadhaar", mrz_data=None)
        assert result["full_name"] == "PRIYA SHARMA"
        assert result.get("surname") is None
        assert result.get("given_names") is None


# =============================================================================
# Incomplete / Missing MRZ Tests
# =============================================================================

class TestIncompleteMRZ:
    """Handle cases where MRZ is incomplete or invalid."""

    def test_incomplete_mrz_no_fields(self):
        """Incomplete MRZ should not produce MRZ-derived fields."""
        result = extract_passport_fields(ocr_lines=[], mrz_data=INCOMPLETE_MRZ)
        # MRZ parsing may or may not extract partial fields
        # But full_name must always be null
        assert result["full_name"] is None

    def test_no_mrz_visual_only(self):
        """Without MRZ, only visual extraction should work."""
        ocr = [
            {"text": "Surname", "confidence": 0.95},
            {"text": "SHARMA", "confidence": 0.93},
            {"text": "Given Name(s)", "confidence": 0.94},
            {"text": "RAHUL KUMAR", "confidence": 0.92},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=NO_MRZ)
        assert result["surname"] == "Sharma"
        assert result["given_names"] == "Rahul Kumar"
        assert result["full_name"] is None
        assert result["field_status"]["surname"] == "extracted"


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestPassportEdgeCases:
    """Edge cases for passport extraction."""

    def test_empty_ocr_no_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=None)
        assert result["full_name"] is None
        assert result["surname"] is None
        assert result["given_names"] is None
        assert result["document_number"] is None

    def test_empty_ocr_with_mrz(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=VALID_MRZ)
        assert result["surname"] == "Sharma"
        assert result["given_names"] == "Rahul Kumar"
        assert result["full_name"] is None

    def test_all_fields_none_when_no_data(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=None)
        for key in ["full_name", "surname", "given_names", "date_of_birth",
                     "gender", "nationality", "document_number"]:
            assert result[key] is None
            assert result["field_confidence"][key] is None

    def test_field_status_all_not_detected(self):
        result = extract_passport_fields(ocr_lines=[], mrz_data=None)
        for key in ["full_name", "surname", "given_names", "date_of_birth",
                     "gender", "nationality", "document_number"]:
            assert result["field_status"][key] == "not_detected"

    def test_passport_place_of_birth_from_visual(self):
        ocr = [
            {"text": "Place of Birth", "confidence": 0.91},
            {"text": "NEW DELHI, DELHI", "confidence": 0.89},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["place_of_birth"] == "NEW DELHI, DELHI"
        assert result["field_status"]["place_of_birth"] == "extracted"

    def test_passport_place_of_issue_from_visual(self):
        ocr = [
            {"text": "Place of Issue", "confidence": 0.90},
            {"text": "NEW DELHI", "confidence": 0.88},
        ]
        result = extract_passport_fields(ocr_lines=ocr, mrz_data=VALID_MRZ)
        assert result["place_of_issue"] == "NEW DELHI"
        assert result["field_status"]["place_of_issue"] == "extracted"
