"""Tests for the verification engine."""

import pytest
from app.services.verification_service import verify_document, _is_expired, _parse_date


# =============================================================================
# Aadhaar Verification Tests
# =============================================================================

class TestAadhaarVerification:
    """Test Aadhaar document verification."""

    def _make_aadhaar_fields(self, **overrides):
        """Create a valid Aadhaar fields dict with optional overrides."""
        fields = {
            "full_name": "PRIYA SHARMA",
            "date_of_birth": "1995-03-15",
            "gender": "FEMALE",
            "document_number": "1234 5678 9012",
            "address": "42 MG Road, Sector 15, Gurugram, Haryana, 122001",
            "document_type": "aadhaar",
            "father_name": None,
            "surname": None,
            "given_names": None,
            "nationality": None,
            "place_of_birth": None,
            "place_of_issue": None,
            "date_of_issue": None,
            "date_of_expiry": None,
            "field_confidence": {
                "full_name": 0.95, "date_of_birth": 0.90, "gender": 0.88,
                "document_number": 0.85, "address": 0.80,
            },
            "field_status": {},
        }
        fields.update(overrides)
        return fields

    def _make_ocr_data(self, confidence=0.90):
        return {"average_confidence": confidence, "lines_count": 15}

    def test_valid_aadhaar_verified(self):
        fields = self._make_aadhaar_fields()
        result = verify_document(fields, self._make_ocr_data(), document_type="aadhaar")
        assert result["status"] == "VERIFIED"
        assert result["score"] >= 80

    def test_missing_name_manual_review(self):
        fields = self._make_aadhaar_fields(full_name=None)
        result = verify_document(fields, self._make_ocr_data(), document_type="aadhaar")
        assert result["status"] == "MANUAL_REVIEW"

    def test_missing_aadhaar_number_manual_review(self):
        fields = self._make_aadhaar_fields(document_number=None)
        result = verify_document(fields, self._make_ocr_data(), document_type="aadhaar")
        assert result["status"] == "MANUAL_REVIEW"

    def test_invalid_aadhaar_number_rejected(self):
        fields = self._make_aadhaar_fields(document_number="12345")
        result = verify_document(fields, self._make_ocr_data(), document_type="aadhaar")
        assert result["status"] == "REJECTED"

    def test_low_ocr_confidence_manual_review(self):
        fields = self._make_aadhaar_fields()
        result = verify_document(fields, self._make_ocr_data(confidence=0.50), document_type="aadhaar")
        assert result["status"] == "MANUAL_REVIEW"
        # Score may still be above 80, but warning triggers MANUAL_REVIEW
        assert any(c["status"] == "warning" for c in result["checks"])

    def test_complete_valid_extraction_high_score(self):
        fields = self._make_aadhaar_fields()
        result = verify_document(fields, self._make_ocr_data(confidence=0.95), document_type="aadhaar")
        assert result["status"] == "VERIFIED"
        assert result["score"] >= 90

    def test_has_checks_and_reasons(self):
        fields = self._make_aadhaar_fields()
        result = verify_document(fields, self._make_ocr_data(), document_type="aadhaar")
        assert isinstance(result["checks"], list)
        assert isinstance(result["reasons"], list)
        assert len(result["checks"]) > 0

    def test_fields_checked_populated(self):
        fields = self._make_aadhaar_fields()
        result = verify_document(fields, self._make_ocr_data(), document_type="aadhaar")
        assert "fields_checked" in result
        assert len(result["fields_checked"]) > 0


# =============================================================================
# Passport Verification Tests
# =============================================================================

class TestPassportVerification:
    """Test Passport document verification."""

    def _make_passport_fields(self, **overrides):
        fields = {
            "full_name": None,  # Passport: no full_name
            "surname": "Sharma",
            "given_names": "Rahul Kumar",
            "date_of_birth": "1995-08-15",
            "gender": "M",
            "nationality": "IND",
            "document_number": "Z1234567",
            "date_of_expiry": "2031-07-19",
            "date_of_issue": "2021-07-20",
            "place_of_birth": "NEW DELHI",
            "place_of_issue": "MUMBAI",
            "document_type": "passport",
            "address": None,
            "father_name": None,
            "field_confidence": {
                "surname": 0.95, "given_names": 0.93,
                "date_of_birth": 0.90, "gender": 0.88,
                "nationality": 0.92, "document_number": 0.91,
                "date_of_expiry": 0.89,
            },
            "field_status": {},
        }
        fields.update(overrides)
        return fields

    def _make_mrz_data(self, detected=True):
        return {"detected": detected, "line1": "P<INDSHARMA<<RAHUL<KUMAR", "line2": "Z1234567<4IND9508157M310719", "confidence": 0.89}

    def _make_ocr_data(self, confidence=0.90):
        return {"average_confidence": confidence, "lines_count": 20}

    def test_valid_passport_verified(self):
        fields = self._make_passport_fields()
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(), "passport")
        assert result["status"] == "VERIFIED"
        assert result["score"] >= 80

    def test_missing_surname_manual_review(self):
        fields = self._make_passport_fields(surname=None)
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(), "passport")
        assert result["status"] == "MANUAL_REVIEW"

    def test_missing_given_names_manual_review(self):
        fields = self._make_passport_fields(given_names=None)
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(), "passport")
        assert result["status"] == "MANUAL_REVIEW"

    def test_invalid_mrz_manual_review(self):
        fields = self._make_passport_fields()
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(detected=False), "passport")
        assert result["status"] == "MANUAL_REVIEW"

    def test_mrz_visual_conflict_manual_review(self):
        fields = self._make_passport_fields(field_status={"gender": "conflict"})
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(), "passport")
        assert result["status"] == "MANUAL_REVIEW"

    def test_expired_passport_rejected(self):
        fields = self._make_passport_fields(date_of_expiry="2020-01-01")
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(), "passport")
        assert result["status"] == "REJECTED"

    def test_valid_passport_full_name_none_verified(self):
        """Passport with full_name=None should still be VERIFIED."""
        fields = self._make_passport_fields(full_name=None)
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(), "passport")
        assert result["status"] == "VERIFIED"
        assert result["score"] >= 80

    def test_mrz_detected_check(self):
        fields = self._make_passport_fields()
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(detected=True), "passport")
        mrz_checks = [c for c in result["checks"] if "MRZ" in c["name"]]
        assert any(c["status"] == "passed" for c in mrz_checks)

    def test_mrz_not_detected_warning(self):
        fields = self._make_passport_fields()
        result = verify_document(fields, self._make_ocr_data(), self._make_mrz_data(detected=False), "passport")
        mrz_checks = [c for c in result["checks"] if "MRZ" in c["name"]]
        assert any(c["status"] == "warning" for c in mrz_checks)


# =============================================================================
# Date/Expiry Helper Tests
# =============================================================================

class TestDateHelpers:
    """Test date parsing and expiry checking."""

    def test_parse_date_yyyy_mm_dd(self):
        assert _parse_date("2025-01-15") is not None

    def test_parse_date_dd_mm_yyyy(self):
        assert _parse_date("15/01/2025") is not None

    def test_parse_date_none(self):
        assert _parse_date(None) is None

    def test_parse_date_empty(self):
        assert _parse_date("") is None

    def test_parse_date_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_is_expired_past_date(self):
        assert _is_expired("2020-01-01") is True

    def test_is_expired_future_date(self):
        assert _is_expired("2099-12-31") is False

    def test_is_expired_none(self):
        assert _is_expired(None) is False


# =============================================================================
# Edge Cases
# =============================================================================

class TestVerificationEdgeCases:
    """Edge cases for verification."""

    def test_unknown_document_type(self):
        fields = {"document_type": "other"}
        result = verify_document(fields, {}, document_type="other")
        assert result["status"] == "MANUAL_REVIEW"

    def test_empty_fields_aadhaar(self):
        result = verify_document({}, {}, document_type="aadhaar")
        assert result["status"] in ("MANUAL_REVIEW", "REJECTED")
        assert result["score"] < 80

    def test_empty_fields_passport(self):
        result = verify_document({}, {}, document_type="passport")
        assert result["status"] in ("MANUAL_REVIEW", "REJECTED")

    def test_score_clamped_to_100(self):
        fields = {
            "full_name": "Test", "date_of_birth": "2000-01-01",
            "gender": "M", "document_number": "123456789012",
            "address": "Test Address",
            "field_confidence": {}, "field_status": {},
        }
        result = verify_document(fields, {"average_confidence": 1.0}, document_type="aadhaar")
        assert result["score"] <= 100

    def test_score_clamped_to_0(self):
        result = verify_document({}, {"average_confidence": 0.1}, document_type="aadhaar")
        assert result["score"] >= 0
