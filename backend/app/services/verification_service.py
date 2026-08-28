"""Verification Engine — Document-type-aware identity verification.

Supports Aadhaar and Passport verification.
Returns a deterministic 0-100 score with explainable checks.
"""

import re
import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Document type normalization
# =============================================================================

# Canonical document types recognized by the verification engine
DOC_TYPE_AADHAAR = "aadhaar"
DOC_TYPE_PASSPORT = "passport"
DOC_TYPE_PAN = "pan"

# Maps every known variant/spelling/alias to the canonical lowercase value
_DOC_TYPE_ALIASES: dict[str, str] = {
    # Aadhaar variants
    "aadhaar": DOC_TYPE_AADHAAR,
    "aadhar": DOC_TYPE_AADHAAR,
    "aadhaar card": DOC_TYPE_AADHAAR,
    "aadhar card": DOC_TYPE_AADHAAR,
    "aadhaAR": DOC_TYPE_AADHAAR,
    "uidai": DOC_TYPE_AADHAAR,
    "unique identification": DOC_TYPE_AADHAAR,
    # Passport variants
    "passport": DOC_TYPE_PASSPORT,
    "passport card": DOC_TYPE_PASSPORT,
    # PAN variants
    "pan": DOC_TYPE_PAN,
    "pan card": DOC_TYPE_PAN,
    "permanent account number": DOC_TYPE_PAN,
}


def normalize_document_type(value: Optional[str]) -> Optional[str]:
    """Normalize any document-type string to a canonical internal value.

    Returns one of DOC_TYPE_AADHAAR, DOC_TYPE_PASSPORT, DOC_TYPE_PAN,
    or None when the value cannot be recognized.
    """
    if not value:
        return None
    key = value.strip().lower()
    if not key:
        return None
    # Direct alias lookup
    canonical = _DOC_TYPE_ALIASES.get(key)
    if canonical:
        return canonical
    # Substring fallback — e.g. "aadhaar card front" → "aadhaar"
    for alias, canon in _DOC_TYPE_ALIASES.items():
        if alias in key:
            return canon
    return None


def detect_document_type_from_ocr(ocr_lines: list[dict]) -> Optional[str]:
    """Heuristically detect the document type from OCR text lines.

    Looks for well-known keywords that appear on Aadhaar, Passport, and PAN
    cards.  Returns a canonical type or None.
    """
    if not ocr_lines:
        return None
    # Combine all OCR text into one lowercase string for fast searching
    combined = " ".join(line.get("text", "") for line in ocr_lines).lower()
    # Aadhaar / UIDAI indicators
    aadhaar_keywords = ["uidai", "unique identification", "aadhaar", "aadhar",
                        "government of india", "vid", "virtual id"]
    if any(kw in combined for kw in aadhaar_keywords):
        # Avoid false-positive: make sure at least one Aadhaar-specific
        # field label (like gender, dob, or a 12-digit number) is present
        has_field = any(kw in combined for kw in ["gender", "sex", "dob",
                                                  "date of birth"])
        has_uid = any(kw in combined for kw in ["uidai", "unique identification"])
        if has_uid or has_field:
            return DOC_TYPE_AADHAAR
    # Passport indicators
    passport_keywords = ["passport", "republic of india",
                         "ministry of external affairs"]
    if any(kw in combined for kw in passport_keywords):
        return DOC_TYPE_PASSPORT
    # PAN indicators
    pan_keywords = ["permanent account number", "income tax",
                    "computing Board of India"]
    if any(kw in combined for kw in pan_keywords):
        return DOC_TYPE_PAN
    return None


# =============================================================================
# Verification status constants
# =============================================================================

STATUS_VERIFIED = "VERIFIED"
STATUS_MANUAL_REVIEW = "MANUAL_REVIEW"
STATUS_REJECTED = "REJECTED"


# =============================================================================
# Check result helpers
# =============================================================================

def _check(name: str, status: str, message: str) -> dict:
    """Create a check result dict."""
    return {"name": name, "status": status, "message": message}


def _passed(name: str, message: str) -> dict:
    return _check(name, "passed", message)


def _warning(name: str, message: str) -> dict:
    return _check(name, "warning", message)


def _failed(name: str, message: str) -> dict:
    return _check(name, "failed", message)


# =============================================================================
# Date helpers
# =============================================================================

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string in common formats."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _is_expired(expiry_str: Optional[str]) -> bool:
    """Check if a date string represents an expired date."""
    d = _parse_date(expiry_str)
    if d is None:
        return False  # Cannot determine — do not assume expired
    return d < date.today()


# =============================================================================
# Aadhaar verification
# =============================================================================

def _verify_aadhaar(fields: dict, ocr_data: dict) -> dict:
    """Verify Aadhaar document extraction results.

    Args:
        fields: Extracted fields dict from field_extraction_service.
        ocr_data: OCR metadata (average_confidence, lines_count, etc.)

    Returns:
        dict with status, score, checks, reasons, fields_checked.
    """
    checks = []
    reasons = []
    score = 100

    # --- Required field presence checks ---

    full_name = fields.get("full_name")
    dob = fields.get("date_of_birth")
    gender = fields.get("gender")
    aadhaar_num = fields.get("document_number")
    address = fields.get("address")
    field_status = fields.get("field_status", {})
    field_confidence = fields.get("field_confidence", {})

    # Full name
    if full_name:
        checks.append(_passed("Full Name", f"Extracted: {full_name}"))
    else:
        checks.append(_warning("Full Name", "Not detected"))
        reasons.append("Full name could not be extracted from the document")
        score -= 15

    # Date of birth
    if dob:
        dob_date = _parse_date(dob)
        if dob_date:
            checks.append(_passed("Date of Birth", f"Extracted: {dob}"))
        else:
            checks.append(_warning("Date of Birth", f"Value present but unparseable: {dob}"))
            reasons.append("Date of birth format could not be validated")
            score -= 5
    else:
        checks.append(_warning("Date of Birth", "Not detected"))
        reasons.append("Date of birth could not be extracted")
        score -= 10

    # Gender
    if gender:
        checks.append(_passed("Gender", f"Extracted: {gender}"))
    else:
        checks.append(_warning("Gender", "Not detected"))
        reasons.append("Gender could not be extracted")
        score -= 5

    # Aadhaar number
    if aadhaar_num:
        digits = re.sub(r"[\s\-]", "", str(aadhaar_num))
        if digits.isdigit() and len(digits) == 12:
            checks.append(_passed("Aadhaar Number", f"Valid 12-digit number: {digits[:4]} **** {digits[8:]}"))
        else:
            checks.append(_failed("Aadhaar Number", f"Invalid format: expected 12 digits, got {len(digits)}"))
            reasons.append(f"Aadhaar number has invalid format ({len(digits)} digits instead of 12)")
            score -= 30
    else:
        checks.append(_warning("Aadhaar Number", "Not detected"))
        reasons.append("Aadhaar number could not be extracted")
        score -= 20

    # Address
    if address:
        checks.append(_passed("Address", "Present"))
    else:
        checks.append(_warning("Address", "Not detected"))
        reasons.append("Address could not be extracted")
        score -= 5

    # --- Field status checks (conflicts) ---

    has_conflict = False
    for key, status in field_status.items():
        if status == "conflict":
            checks.append(_warning(f"Field Conflict: {key}", "OCR and MRZ values disagree"))
            reasons.append(f"Conflict detected in {key}")
            has_conflict = True
            score -= 10

    if not has_conflict:
        checks.append(_passed("No Field Conflicts", "All extracted fields are consistent"))

    # --- OCR confidence ---

    avg_conf = ocr_data.get("average_confidence")
    if avg_conf is not None:
        conf_pct = round(avg_conf * 100)
        if conf_pct >= 85:
            checks.append(_passed("OCR Confidence", f"Good ({conf_pct}%)"))
        elif conf_pct >= 65:
            checks.append(_warning("OCR Confidence", f"Moderate ({conf_pct}%)"))
            reasons.append(f"OCR confidence is moderate at {conf_pct}%")
            score -= 5
        else:
            checks.append(_warning("OCR Confidence", f"Low ({conf_pct}%)"))
            reasons.append(f"OCR confidence is low at {conf_pct}% — manual review recommended")
            score -= 15

    # --- All required fields present ---

    required_fields = ["full_name", "date_of_birth", "gender", "document_number", "address"]
    missing = [f for f in required_fields if not fields.get(f)]
    if not missing:
        checks.append(_passed("Required Fields", "All required fields detected"))
    else:
        checks.append(_warning("Required Fields", f"Missing: {', '.join(missing)}"))
        reasons.append(f"Required fields missing: {', '.join(missing)}")
        score -= 10

    # --- Clamp score ---
    score = max(0, min(100, score))

    # --- Determine status ---
    has_failed = any(c["status"] == "failed" for c in checks)
    has_warning = any(c["status"] == "warning" for c in checks)

    if has_failed:
        status = STATUS_REJECTED
    elif has_warning or score < 80:
        status = STATUS_MANUAL_REVIEW
    else:
        status = STATUS_VERIFIED

    return {
        "status": status,
        "score": score,
        "checks": checks,
        "reasons": reasons,
    }


# =============================================================================
# Passport verification
# =============================================================================

def _verify_passport(fields: dict, ocr_data: dict, mrz_data: dict) -> dict:
    """Verify Passport document extraction results.

    Args:
        fields: Extracted fields dict from extract_passport_fields.
        ocr_data: OCR metadata.
        mrz_data: MRZ detection data.

    Returns:
        dict with status, score, checks, reasons.
    """
    checks = []
    reasons = []
    score = 100

    surname = fields.get("surname")
    given_names = fields.get("given_names")
    dob = fields.get("date_of_birth")
    gender = fields.get("gender")
    nationality = fields.get("nationality")
    passport_number = fields.get("document_number")
    date_of_expiry = fields.get("date_of_expiry")
    date_of_issue = fields.get("date_of_issue")
    place_of_birth = fields.get("place_of_birth")
    place_of_issue = fields.get("place_of_issue")
    field_status = fields.get("field_status", {})

    # --- Required field presence ---

    # Surname
    if surname:
        checks.append(_passed("Surname", f"Extracted: {surname}"))
    else:
        checks.append(_warning("Surname", "Not detected"))
        reasons.append("Surname could not be extracted")
        score -= 15

    # Given names
    if given_names:
        checks.append(_passed("Given Names", f"Extracted: {given_names}"))
    else:
        checks.append(_warning("Given Names", "Not detected"))
        reasons.append("Given names could not be extracted")
        score -= 15

    # Passport number
    if passport_number:
        checks.append(_passed("Passport Number", f"Extracted: {passport_number}"))
    else:
        checks.append(_warning("Passport Number", "Not detected"))
        reasons.append("Passport number could not be extracted")
        score -= 20

    # Date of birth
    if dob:
        dob_date = _parse_date(dob)
        if dob_date:
            checks.append(_passed("Date of Birth", f"Extracted: {dob}"))
        else:
            checks.append(_warning("Date of Birth", f"Unparseable: {dob}"))
            reasons.append("Date of birth format could not be validated")
            score -= 5
    else:
        checks.append(_warning("Date of Birth", "Not detected"))
        reasons.append("Date of birth could not be extracted")
        score -= 10

    # Sex/Gender
    if gender:
        checks.append(_passed("Sex", f"Extracted: {gender}"))
    else:
        checks.append(_warning("Sex", "Not detected"))
        reasons.append("Gender/sex could not be extracted")
        score -= 5

    # Nationality
    if nationality:
        checks.append(_passed("Nationality", f"Extracted: {nationality}"))
    else:
        checks.append(_warning("Nationality", "Not detected"))
        reasons.append("Nationality could not be extracted")
        score -= 5

    # Date of expiry
    if date_of_expiry:
        if _is_expired(date_of_expiry):
            checks.append(_failed("Date of Expiry", f"EXPIRED on {date_of_expiry}"))
            reasons.append(f"Passport expired on {date_of_expiry}")
            score -= 50
        else:
            checks.append(_passed("Date of Expiry", f"Valid until {date_of_expiry}"))
    else:
        checks.append(_warning("Date of Expiry", "Not detected"))
        reasons.append("Expiry date could not be extracted")
        score -= 10

    # --- MRZ checks ---

    mrz_detected = mrz_data.get("detected", False) if mrz_data else False

    if mrz_detected:
        checks.append(_passed("MRZ Detected", "Machine-readable zone found"))
    else:
        checks.append(_warning("MRZ Detected", "MRZ not detected — visual extraction only"))
        reasons.append("MRZ was not detected; relying on visual OCR only")
        score -= 10

    # MRZ ↔ visual field consistency
    has_conflict = False
    for key, status in field_status.items():
        if status == "conflict":
            checks.append(_warning(f"Field Conflict: {key}", "MRZ and visual values disagree"))
            reasons.append(f"Conflict detected in {key} between MRZ and visual OCR")
            has_conflict = True
            score -= 10

    if not has_conflict:
        if mrz_detected:
            checks.append(_passed("MRZ-Visual Consistency", "All fields consistent between MRZ and visual"))
        else:
            checks.append(_passed("No Field Conflicts", "No conflicting values detected"))

    # --- Place fields (optional but nice to have) ---

    if place_of_birth:
        checks.append(_passed("Place of Birth", f"Extracted: {place_of_birth}"))
    else:
        checks.append(_warning("Place of Birth", "Not detected"))

    if place_of_issue:
        checks.append(_passed("Place of Issue", f"Extracted: {place_of_issue}"))
    else:
        checks.append(_warning("Place of Issue", "Not detected"))

    # --- OCR confidence ---

    avg_conf = ocr_data.get("average_confidence")
    if avg_conf is not None:
        conf_pct = round(avg_conf * 100)
        if conf_pct >= 85:
            checks.append(_passed("OCR Confidence", f"Good ({conf_pct}%)"))
        elif conf_pct >= 65:
            checks.append(_warning("OCR Confidence", f"Moderate ({conf_pct}%)"))
            reasons.append(f"OCR confidence is moderate at {conf_pct}%")
            score -= 5
        else:
            checks.append(_warning("OCR Confidence", f"Low ({conf_pct}%)"))
            reasons.append(f"OCR confidence is low at {conf_pct}%")
            score -= 15

    # --- All required fields present ---

    required_fields = ["surname", "given_names", "document_number", "date_of_birth", "gender", "nationality", "date_of_expiry"]
    missing = [f for f in required_fields if not fields.get(f)]
    if not missing:
        checks.append(_passed("Required Fields", "All required passport fields detected"))
    else:
        checks.append(_warning("Required Fields", f"Missing: {', '.join(missing)}"))
        reasons.append(f"Required fields missing: {', '.join(missing)}")
        score -= 10

    # --- Clamp score ---
    score = max(0, min(100, score))

    # --- Determine status ---
    has_failed = any(c["status"] == "failed" for c in checks)
    has_warning = any(c["status"] == "warning" for c in checks)

    if has_failed:
        status = STATUS_REJECTED
    elif has_warning or score < 80:
        status = STATUS_MANUAL_REVIEW
    else:
        status = STATUS_VERIFIED

    return {
        "status": status,
        "score": score,
        "checks": checks,
        "reasons": reasons,
    }


# =============================================================================
# Main verification entry point
# =============================================================================

def verify_document(
    fields: dict,
    ocr_data: dict,
    mrz_data: Optional[dict] = None,
    document_type: Optional[str] = None,
) -> dict:
    """Run document-type-aware verification.

    Args:
        fields: Extracted fields from field_extraction_service.
        ocr_data: OCR metadata (average_confidence, lines_count, etc.)
        mrz_data: MRZ data (for passport only).
        document_type: "aadhaar" or "passport".

    Returns:
        dict with status, score, checks, reasons, fields_checked.
    """
    doc_type = normalize_document_type(
        document_type or fields.get("document_type")
    ) or ""

    # Collect fields_checked for transparency
    fields_checked = []
    for key, val in fields.items():
        if key in ("field_confidence", "field_status"):
            continue
        conf = fields.get("field_confidence", {}).get(key)
        status = fields.get("field_status", {}).get(key, "extracted" if val else "not_detected")
        fields_checked.append({
            "field": key,
            "value": val,
            "confidence": conf,
            "status": status,
        })

    if doc_type == DOC_TYPE_AADHAAR:
        result = _verify_aadhaar(fields, ocr_data)
    elif doc_type == DOC_TYPE_PASSPORT:
        result = _verify_passport(fields, ocr_data, mrz_data)
    else:
        # Generic fallback — basic field presence check
        result = {
            "status": STATUS_MANUAL_REVIEW,
            "score": 50,
            "checks": [_warning("Document Type", f"Unsupported document type: {doc_type}")],
            "reasons": [f"Verification not implemented for document type: {doc_type}"],
        }

    result["fields_checked"] = fields_checked
    return result
