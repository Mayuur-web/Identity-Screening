"""Field Extraction Service — Rule-based extraction of identity fields from OCR output.

Converts raw OCR lines into structured identity/document fields using
deterministic parsing, regex patterns, and label-matching logic.

Supports two extraction strategies:
  A. Label/context-based extraction (clean OCR labels)
  B. Candidate-based extraction when OCR labels are corrupted

Supports MRZ data for passport-style documents.
Includes cross-source consistency checking (OCR vs MRZ).
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# --- Label patterns (start-of-string, case-insensitive) ---

NAME_LABELS = [
    r"^name\s*:?$",
    r"^full\s*name\s*:?$",
    r"^applicant\s*name\s*:?$",
    r"^holder\s*name\s*:?$",
    r"^given\s*name\s*:?$",
    r"^given\s*names?\s*:?$",
]

SURNAME_LABELS = [
    r"^surname\s*:?$",
    r"^family\s*name\s*:?$",
    r"^last\s*name\s*:?$",
]

DOB_LABELS = [
    r"^date\s*of\s*birth\s*:?$",
    r"^dob\s*:?$",
    r"^birth\s*date\s*:?$",
    r"^d\.?o\.?b\.?\s*:?$",
]

GENDER_LABELS = [
    r"^gender\s*:?$",
    r"^sex\s*:?$",
    r"^m/?f\s*:?$",
]

ADDRESS_LABELS = [
    r"^address\s*-?:?$",
    r"^addr\s*-?:?$",
    r"^residential\s*address\s*:?$",
    r"^permanent\s*address\s*:?$",
    r"^place\s*of\s*birth\s*-?:?$",
]

DOC_NUMBER_LABELS = [
    r"^id\s*number\s*:?$",
    r"^id\s*no\.?\s*:?$",
    r"^document\s*number\s*:?$",
    r"^document\s*no\.?\s*:?$",
    r"^doc\s*no\.?\s*:?$",
    r"^aadhaar\s*:?$",
    r"^aadhar\s*:?$",
    r"^pan\s*:?$",
    r"^passport\s*no\.?\s*:?$",
    r"^passport\s*number\s*:?$",
    r"^licence\s*no\.?\s*:?$",
    r"^license\s*no\.?\s*:?$",
]

FATHER_NAME_LABELS = [
    r"^father'?s?\s*name\s*:?$",
    r"^father\s*:?$",
    r"^s/?o\s*:?$",
    r"^d/?o\s*:?$",
]

NATIONALITY_LABELS = [
    r"^nationality\s*:?$",
    r"^national\s*:?$",
]

PLACE_OF_ISSUE_LABELS = [
    r"^place\s*of\s*issue\s*:?$",
    r"^issued\s*at\s*:?$",
    r"^issuing\s*authority\s*:?$",
]

DATE_OF_ISSUE_LABELS = [
    r"^date\s*of\s*issue\s*:?$",
    r"^issue\s*date\s*:?$",
    r"^issued\s*on\s*:?$",
]

DATE_OF_EXPIRY_LABELS = [
    r"^date\s*of\s*expiry\s*:?$",
    r"^expiry\s*date\s*:?$",
    r"^valid\s*until\s*:?$",
    r"^expires?\s*:?$",
]

HINDI_NAME_LABELS = [
    r"^नाम\s*:?$",
    r"^पूरा\s*नाम\s*:?$",
]

ALL_FIELD_LABELS = (
    NAME_LABELS + SURNAME_LABELS + DOB_LABELS + GENDER_LABELS +
    ADDRESS_LABELS + DOC_NUMBER_LABELS + FATHER_NAME_LABELS +
    NATIONALITY_LABELS + PLACE_OF_ISSUE_LABELS + DATE_OF_ISSUE_LABELS +
    DATE_OF_EXPIRY_LABELS + HINDI_NAME_LABELS
)

# Keywords that indicate a label line (for corrupted-OCR label detection)
LABEL_KEYWORDS = [
    "name", "full name", "applicant name", "holder name", "given name",
    "surname", "family name", "last name",
    "date of birth", "dob", "birth date", "birth",
    "gender", "sex",
    "address", "addr",
    "id number", "id no", "document number", "document no",
    "aadhaar", "aadhar", "pan", "passport no", "passport number",
    "father", "s/o", "d/o",
    "nationality", "national",
    "place of issue", "issued at", "issuing authority",
    "date of issue", "issue date", "issued on",
    "date of expiry", "expiry date", "valid until", "expires",
    "नाम",
]

NOT_NAME_KEYWORDS = [
    "date of birth", "dob", "birth", "gender", "sex", "male", "female",
    "address", "aadhaar", "aadhar", "pan", "passport",
    "government", "republic", "authority", "india",
    "tma", "tfat",
    "photo", "sample", "specimen",
    "valid until", "expires", "issue",
]

# Date patterns
DATE_PATTERNS = [
    (r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", "DMY"),
    (r"(\d{1,2})[-\s](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s](\d{4})", "DMonthY"),
    (r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", "YMD"),
    (r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]+\s+(\d{4})", "DDMonthYYYY"),
]

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

COMPARABLE_FIELDS = ["date_of_birth", "gender", "nationality", "document_number", "date_of_expiry"]


# =============================================================================
# Helper functions
# =============================================================================

def _clean_text(text: str) -> str:
    """Clean OCR noise from text."""
    text = re.sub(r"[-:.\s]+$", "", text)
    text = re.sub(r"^[-:.\s]+", "", text)
    return text.strip()


def _normalize_date(date_str: str) -> Optional[str]:
    """Normalize any date string to YYYY-MM-DD format."""
    if not date_str:
        return None
    parsed = _parse_date(date_str)
    return parsed if parsed else None


def _normalize_for_comparison(value: str, field: str) -> str:
    """Normalize a field value for comparison across sources."""
    if not value:
        return ""
    v = value.strip()
    if field in ("date_of_birth", "date_of_expiry", "date_of_issue"):
        normalized = _normalize_date(v)
        return normalized if normalized else v.upper()
    if field == "gender":
        v_up = v.upper()
        gender_map = {"MALE": "M", "FEMALE": "F", "OTHER": "O"}
        return gender_map.get(v_up, v_up)
    if field == "full_name":
        # Normalize names: lowercase, collapse whitespace, strip
        return re.sub(r"\s+", " ", v.lower().strip())
    return v.upper()


def _compare_field_values(ocr_val: Optional[str], mrz_val: Optional[str], field: str) -> str:
    """Compare two values for the same field from different sources."""
    if not ocr_val or not mrz_val:
        return "consistent"
    norm_ocr = _normalize_for_comparison(ocr_val, field)
    norm_mrz = _normalize_for_comparison(mrz_val, field)
    if not norm_ocr or not norm_mrz:
        return "consistent"
    if norm_ocr == norm_mrz:
        return "consistent"
    return "conflict"


def _match_label(text: str, patterns: list[str]) -> bool:
    """Check if text matches any label pattern (start-of-string)."""
    cleaned = _clean_text(text).lower()
    for pattern in patterns:
        if re.match(pattern, cleaned, re.IGNORECASE):
            return True
    return False


def _is_label_like(text: str) -> bool:
    """Check if text looks like a field label."""
    cleaned = _clean_text(text).lower()
    if not cleaned:
        return False

    if _match_label(cleaned, ALL_FIELD_LABELS):
        return True

    has_colon = ":" in text
    words = cleaned.split()
    for keyword in LABEL_KEYWORDS:
        if cleaned.startswith(keyword):
            return True
        if " " in keyword and keyword in cleaned:
            return True
        if " " not in keyword and keyword in cleaned:
            if has_colon and len(words) <= 4:
                return True

    if len(cleaned) < 4 and ":" in text:
        return True

    return False


def _is_valid_name_candidate(text: str) -> bool:
    """Check if text is a valid name candidate (not a label, not noise)."""
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    if len(cleaned) < 2:
        return False
    if len(cleaned) <= 2 and not any(c.isalpha() for c in cleaned):
        return False

    alpha_chars = sum(1 for c in cleaned if c.isalpha())
    if alpha_chars == 0:
        return False

    if _is_label_like(cleaned):
        return False

    cleaned_lower = cleaned.lower()
    for keyword in NOT_NAME_KEYWORDS:
        if cleaned_lower == keyword or cleaned_lower.startswith(keyword + " ") or cleaned_lower.endswith(" " + keyword):
            return False

    words = cleaned.split()
    if re.search(r'\bname\b', cleaned_lower) and len(words) <= 1:
        return False

    if _is_date_like(cleaned):
        return False

    if cleaned.isupper() and len(cleaned) <= 3 and " " not in cleaned:
        return False

    return True


def _score_name_candidate(text: str, confidence: float, distance: int) -> float:
    """Score a name candidate. Higher is better."""
    cleaned = _clean_text(text)
    words = cleaned.split()
    alpha_words = [w for w in words if any(c.isalpha() for c in w)]

    score = 0.0
    if len(alpha_words) >= 3:
        score += 3.0
    elif len(alpha_words) == 2:
        score += 2.5
    elif len(alpha_words) == 1:
        score += 1.0

    if len(cleaned) >= 6:
        score += 1.0
    elif len(cleaned) >= 4:
        score += 0.5

    score += confidence * 2.0
    score -= distance * 0.3

    alpha_chars_count = sum(1 for c in cleaned if c.isalpha())
    alpha_ratio = alpha_chars_count / len(cleaned) if cleaned else 0
    if alpha_ratio > 0.8:
        score += 1.0
    elif alpha_ratio > 0.5:
        score += 0.5

    return score


def _extract_label_and_value(line_text: str, label_patterns: list[str]) -> tuple[bool, Optional[str]]:
    """Extract label and optional value from a line."""
    cleaned = _clean_text(line_text)
    for pattern in label_patterns:
        match = re.match(
            pattern.rstrip("$") + r"\s*[:\-]?\s*(.+)$",
            cleaned, re.IGNORECASE,
        )
        if match:
            value = match.group(1).strip()
            return True, value if value else None
        if re.match(pattern, cleaned, re.IGNORECASE):
            return True, None
    return False, None


def _find_name_candidate(lines: list[tuple[str, float]], label_index: int) -> tuple[Optional[str], Optional[float], int]:
    """Find the best name candidate scanning ahead from a Name label."""
    best_value = None
    best_conf = None
    best_score = -1.0
    best_index = -1

    for offset in range(1, 6):
        candidate_index = label_index + offset
        if candidate_index >= len(lines):
            break
        text, conf = lines[candidate_index]
        if not _is_valid_name_candidate(text):
            continue
        score = _score_name_candidate(text, conf, offset)
        if score > best_score:
            best_score = score
            best_value = _clean_text(text)
            best_conf = conf
            best_index = candidate_index

    if best_score < 1.0:
        return None, None, -1
    return best_value, best_conf, best_index


def _parse_date(date_str: str) -> Optional[str]:
    """Parse a date string and return YYYY-MM-DD or None."""
    date_str = _clean_text(date_str)
    if not date_str:
        return None
    for pattern, fmt in DATE_PATTERNS:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                if fmt == "DMY":
                    day, month, year = groups[0], groups[1], groups[2]
                    return f"{year}-{int(month):02d}-{int(day):02d}"
                elif fmt == "DMonthY":
                    day, month_str, year = groups[0], groups[1], groups[2]
                    month_num = MONTH_MAP.get(month_str[:3].lower())
                    if month_num:
                        return f"{year}-{month_num}-{int(day):02d}"
                elif fmt == "YMD":
                    year, month, day = groups[0], groups[1], groups[2]
                    return f"{year}-{int(month):02d}-{int(day):02d}"
                elif fmt == "DDMonthYYYY":
                    day, month_str, year = groups[0], groups[1], groups[2]
                    month_num = MONTH_MAP.get(month_str[:3].lower())
                    if month_num:
                        return f"{year}-{month_num}-{int(day):02d}"
            except (ValueError, TypeError):
                continue
    return None


def _is_date_like(text: str) -> bool:
    return _parse_date(date_str=text) is not None


def _is_address_line(text: str, label_patterns: list[str]) -> bool:
    cleaned = _clean_text(text).lower()
    all_labels = (label_patterns + NAME_LABELS + DOB_LABELS + GENDER_LABELS +
                  DOC_NUMBER_LABELS + FATHER_NAME_LABELS + SURNAME_LABELS)
    for pattern in all_labels:
        if re.match(pattern, cleaned, re.IGNORECASE):
            return False
    if _is_date_like(text):
        return False
    if re.match(r"^[\d\s\-]+$", cleaned):
        digits_only = re.sub(r"[\s\-]", "", cleaned)
        if len(digits_only) < 5:
            return False
    return True


def _find_embedded_value(text: str, label_keywords: list[str]) -> Optional[str]:
    """Find a value after a label keyword embedded in noisy text.

    Example: 'fafal DOB: 18/04/2006' → finds '18/04/2006' after 'DOB'
    Example: 'AfrT / FEMALE' → finds 'FEMALE' after gender keywords
    """
    cleaned = _clean_text(text)
    if not cleaned:
        return None

    for keyword in label_keywords:
        # Look for keyword followed by colon, dash, slash, or space+value
        pattern = re.compile(
            re.escape(keyword) + r"\s*[:/\-]\s*(.+)$",
            re.IGNORECASE,
        )
        match = pattern.search(cleaned)
        if match:
            value = match.group(1).strip()
            if value:
                return value

        # Also try: keyword followed by whitespace then value
        pattern2 = re.compile(
            r"(?:^|\s)" + re.escape(keyword) + r"\s+(.+)$",
            re.IGNORECASE,
        )
        match2 = pattern2.search(cleaned)
        if match2:
            value = match2.group(1).strip()
            if value and not _is_label_like(value):
                return value

    return None


def _score_date_context(line_text: str, line_index: int, all_lines: list[tuple[str, float]]) -> float:
    """Score a date candidate based on context (proximity to DOB labels, etc.)."""
    score = 0.0
    cleaned = line_text.lower()

    # Direct DOB label on same line → highest score
    dob_keywords = ["dob", "date of birth", "birth date", "जन्म"]
    for kw in dob_keywords:
        if kw in cleaned:
            score += 5.0
            break

    # Check nearby lines (±2) for DOB labels
    for offset in range(-2, 3):
        check_idx = line_index + offset
        if check_idx < 0 or check_idx >= len(all_lines) or check_idx == line_index:
            continue
        nearby_text = all_lines[check_idx][0].lower()
        for kw in dob_keywords:
            if kw in nearby_text:
                score += 3.0 - abs(offset) * 0.5
                break

    # Penalize if near issue/expiry keywords
    issue_keywords = ["issue", "expiry", "valid until", "expires"]
    for offset in range(-1, 2):
        check_idx = line_index + offset
        if check_idx < 0 or check_idx >= len(all_lines) or check_idx == line_index:
            continue
        nearby_text = all_lines[check_idx][0].lower()
        for kw in issue_keywords:
            if kw in nearby_text:
                score -= 2.0
                break

    return score


# =============================================================================
# Main field extraction
# =============================================================================

def _extract_generic_fields(ocr_lines: list[dict], document_type: Optional[str] = None) -> dict:
    """Extract fields from raw OCR lines with label-based and fallback strategies."""
    result = {
        "full_name": None,
        "date_of_birth": None,
        "document_number": None,
        "address": None,
        "gender": None,
        "document_type": document_type,
        "father_name": None,
        "surname": None,
        "given_names": None,
        "nationality": None,
        "place_of_birth": None,
        "place_of_issue": None,
        "date_of_issue": None,
        "date_of_expiry": None,
        "field_confidence": {
            "full_name": None, "date_of_birth": None, "document_number": None,
            "address": None, "gender": None, "father_name": None,
            "surname": None, "given_names": None, "nationality": None,
            "place_of_birth": None, "place_of_issue": None,
            "date_of_issue": None, "date_of_expiry": None,
        },
    }

    if not ocr_lines:
        return result

    lines = [(line["text"], line.get("confidence", 0.0)) for line in ocr_lines]
    consumed = [False] * len(lines)

    # =========================================================================
    # Pass 1: Clean label-based extraction (works for clean OCR)
    # =========================================================================

    simple_label_configs = [
        (SURNAME_LABELS, "surname", None),
        (DOB_LABELS, "date_of_birth", "date"),
        (GENDER_LABELS, "gender", "upper"),
        (DOC_NUMBER_LABELS, "document_number", None),
        (FATHER_NAME_LABELS, "father_name", None),
        (NATIONALITY_LABELS, "nationality", None),
        (DATE_OF_ISSUE_LABELS, "date_of_issue", "date"),
        (DATE_OF_EXPIRY_LABELS, "date_of_expiry", "date"),
    ]

    # Name extraction with multi-line scanning
    for i, (text, conf) in enumerate(lines):
        if consumed[i]:
            continue
        is_label, inline_val = _extract_label_and_value(text, NAME_LABELS + HINDI_NAME_LABELS)
        if is_label:
            consumed[i] = True
            if inline_val:
                val = _clean_text(inline_val)
                if val and _is_valid_name_candidate(val):
                    result["full_name"] = val
                    result["field_confidence"]["full_name"] = conf
            else:
                name_val, name_conf, name_idx = _find_name_candidate(lines, i)
                if name_val and name_idx >= 0:
                    result["full_name"] = name_val
                    result["field_confidence"]["full_name"] = name_conf
                    consumed[name_idx] = True
            break

    # Other label configs
    for i, (text, conf) in enumerate(lines):
        if consumed[i]:
            continue
        for label_pats, field_key, transform in simple_label_configs:
            is_label, inline_val = _extract_label_and_value(text, label_pats)
            if is_label:
                consumed[i] = True
                if inline_val:
                    val = _clean_text(inline_val)
                    if transform == "date":
                        parsed = _parse_date(val)
                        if parsed:
                            val = parsed
                        else:
                            break
                    elif transform == "upper":
                        val = val.upper()
                    result[field_key] = val
                    result["field_confidence"][field_key] = conf
                elif i + 1 < len(lines) and not consumed[i + 1]:
                    next_text, next_conf = lines[i + 1]
                    all_label_pats = list(label_pats) + NAME_LABELS + HINDI_NAME_LABELS
                    if not _match_label(next_text, all_label_pats) and not _is_label_like(next_text):
                        val = _clean_text(next_text)
                        if transform == "date":
                            parsed = _parse_date(val)
                            if parsed:
                                val = parsed
                            else:
                                break
                        elif transform == "upper":
                            val = val.upper()
                        result[field_key] = val
                        result["field_confidence"][field_key] = next_conf
                        consumed[i + 1] = True
                break

    # =========================================================================
    # Pass 2: Embedded label extraction (for corrupted OCR labels)
    # Example: 'fafal DOB: 18/04/2006', 'AfrT / FEMALE'
    # =========================================================================

    # DOB from embedded labels
    if result["date_of_birth"] is None:
        for i, (text, conf) in enumerate(lines):
            if consumed[i]:
                continue
            embedded_val = _find_embedded_value(text, ["dob", "date of birth", "birth date", "d.o.b", "जन्म"])
            if embedded_val:
                parsed = _parse_date(embedded_val)
                if parsed:
                    result["date_of_birth"] = parsed
                    result["field_confidence"]["date_of_birth"] = conf
                    consumed[i] = True
                    break

    # Gender from embedded labels
    if result["gender"] is None:
        for i, (text, conf) in enumerate(lines):
            if consumed[i]:
                continue
            embedded_val = _find_embedded_value(text, ["gender", "sex", "m/f"])
            if embedded_val:
                cleaned_val = _clean_text(embedded_val).upper()
                if cleaned_val in ("MALE", "FEMALE", "OTHER", "M", "F"):
                    result["gender"] = cleaned_val if len(cleaned_val) > 1 else cleaned_val
                    result["field_confidence"]["gender"] = conf
                    consumed[i] = True
                    break

    # =========================================================================
    # Pass 3: Context-based date extraction (find best DOB from all dates)
    # =========================================================================

    if result["date_of_birth"] is None:
        date_candidates = []
        for i, (text, conf) in enumerate(lines):
            if consumed[i]:
                continue
            parsed = _parse_date(text)
            if parsed:
                ctx_score = _score_date_context(text, i, lines)
                total_score = ctx_score + conf * 2.0
                date_candidates.append((parsed, conf, i, total_score))

        if date_candidates:
            # Sort by total score (highest first)
            date_candidates.sort(key=lambda x: x[3], reverse=True)
            best = date_candidates[0]
            result["date_of_birth"] = best[0]
            result["field_confidence"]["date_of_birth"] = best[1]
            consumed[best[2]] = True

    # =========================================================================
    # Pass 4: Gender detection (find MALE/FEMALE/M/F anywhere)
    # =========================================================================

    if result["gender"] is None:
        for i, (text, conf) in enumerate(lines):
            if consumed[i]:
                continue
            cleaned = _clean_text(text).upper().strip()
            # Exact match on clean line
            if cleaned in ("MALE", "FEMALE", "OTHER"):
                result["gender"] = cleaned
                result["field_confidence"]["gender"] = conf
                consumed[i] = True
                break
            # Extract gender value from noisy line like "AfrT / FEMALE"
            gender_match = re.search(r"\b(MALE|FEMALE|OTHER)\b", cleaned)
            if gender_match:
                result["gender"] = gender_match.group(1)
                result["field_confidence"]["gender"] = conf
                consumed[i] = True
                break
            # Single letter M/F as standalone word
            gender_single = re.search(r"(?:^|\s)([MF])(?:\s|$)", cleaned)
            if gender_single and not re.search(r"[A-Z]{2,}", cleaned.replace(gender_single.group(1), "")):
                result["gender"] = gender_single.group(1)
                result["field_confidence"]["gender"] = conf
                consumed[i] = True
                break

    # =========================================================================
    # Pass 5: Aadhaar number detection (12 digits, with optional spaces/dashes)
    # =========================================================================

    if result["document_number"] is None:
        aadhaar_pattern = re.compile(r"\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b")
        for i, (text, conf) in enumerate(lines):
            if consumed[i]:
                continue
            match = aadhaar_pattern.search(text)
            if match:
                raw = match.group(1)
                digits = re.sub(r"[\s\-]", "", raw)
                if len(digits) == 12 and digits.isdigit():
                    result["document_number"] = digits
                    result["field_confidence"]["document_number"] = conf
                    consumed[i] = True
                    break

    # =========================================================================
    # Pass 6: Address extraction (multi-line)
    # =========================================================================

    address_fields = {
        "address": ADDRESS_LABELS,
        "place_of_birth": [r"^place\s*of\s*birth\s*-?:?$"],
        "place_of_issue": PLACE_OF_ISSUE_LABELS,
    }

    for field_key, field_labels in address_fields.items():
        if result[field_key] is not None:
            continue
        addr_lines = []
        addr_confs = []
        in_addr = False
        for i, (text, conf) in enumerate(lines):
            if consumed[i]:
                in_addr = False
                continue
            is_label, inline_val = _extract_label_and_value(text, field_labels)
            if is_label:
                consumed[i] = True
                in_addr = True
                if inline_val:
                    addr_lines.append(inline_val)
                    addr_confs.append(conf)
                continue
            if in_addr:
                if _is_address_line(text, field_labels):
                    addr_lines.append(_clean_text(text))
                    addr_confs.append(conf)
                    consumed[i] = True
                else:
                    in_addr = False
        if addr_lines:
            result[field_key] = ", ".join(addr_lines)
            if addr_confs:
                result["field_confidence"][field_key] = round(
                    sum(addr_confs) / len(addr_confs), 4
                )

    # =========================================================================
    # Pass 7: Generic document number fallback (alphanumeric patterns)
    # =========================================================================

    if result["document_number"] is None:
        for i, (text, conf) in enumerate(lines):
            if consumed[i]:
                continue
            cleaned = _clean_text(text)
            if " " in cleaned:
                continue
            if re.match(r"^[A-Z0-9]{2,}[-]?[A-Z0-9]+[-]?[A-Z0-9]+$", cleaned, re.IGNORECASE):
                if re.search(r"\d", cleaned):
                    result["document_number"] = cleaned
                    result["field_confidence"]["document_number"] = conf
                    consumed[i] = True
                    break

    # =========================================================================
    # Pass 8: Fallback name detection (when no Name label was found)
    # Only activate when other identity fields exist (proves it's an ID document).
    # =========================================================================

    has_other_fields = any(result.get(f) is not None for f in [
        "date_of_birth", "gender", "document_number", "father_name",
    ])
    if result["full_name"] is None and has_other_fields:
        best_name = None
        best_name_conf = None
        best_name_score = -1.0
        for i, (text, conf) in enumerate(lines):
            if consumed[i]:
                continue
            if _is_valid_name_candidate(text):
                score = _score_name_candidate(text, conf, 1)
                if score > best_name_score:
                    best_name_score = score
                    best_name = _clean_text(text)
                    best_name_conf = conf
        if best_name and best_name_score >= 3.0:
            result["full_name"] = best_name
            result["field_confidence"]["full_name"] = best_name_conf

    # =========================================================================
    # Compose full_name from surname + given_names if available
    # =========================================================================

    if result["full_name"] is None:
        parts = []
        if result.get("surname"):
            parts.append(result["surname"])
        if result.get("given_names"):
            parts.append(result["given_names"])
        if parts:
            result["full_name"] = " ".join(parts)
            confs = [
                result["field_confidence"].get("surname"),
                result["field_confidence"].get("given_names"),
            ]
            confs = [c for c in confs if c is not None]
            result["field_confidence"]["full_name"] = min(confs) if confs else None

    return result


def extract_fields(
    ocr_lines: list[dict],
    document_type: Optional[str] = None,
    mrz_data: Optional[dict] = None,
) -> dict:
    """Extract structured identity fields from OCR output, optionally using MRZ data.

    Implements cross-source consistency checking between OCR and MRZ.
    Every field value originates solely from the current document's OCR/MRZ evidence.
    """
    result = _extract_generic_fields(ocr_lines, document_type)

    all_field_keys = list(result["field_confidence"].keys())
    field_status = {}
    for key in all_field_keys:
        field_status[key] = "extracted" if result.get(key) is not None else "not_detected"

    # MRZ integration (passport only)
    if mrz_data and mrz_data.get("detected"):
        from app.services.mrz_service import parse_mrz_generic
        mrz_fields = parse_mrz_generic(mrz_data)

        ocr_sources = {}
        for key in all_field_keys:
            if result.get(key) is not None:
                ocr_sources[key] = result[key]

        mrz_sources = {}
        mrz_field_map = {
            "passport_number": "document_number",
            "surname": "surname",
            "given_names": "given_names",
            "nationality": "nationality",
            "sex": "gender",
            "date_of_birth": "date_of_birth",
            "date_of_expiry": "date_of_expiry",
        }

        for mrz_key, field_key in mrz_field_map.items():
            mrz_val = mrz_fields.get(mrz_key)
            if mrz_val:
                mrz_sources[field_key] = mrz_val

        for mrz_key, field_key in mrz_field_map.items():
            mrz_val = mrz_fields.get(mrz_key)
            if mrz_val and (result.get(field_key) is None or field_key == "gender"):
                result[field_key] = mrz_val
                result["field_confidence"][field_key] = mrz_data.get("confidence", 0.0)

        if result.get("full_name") is None:
            parts = []
            if result.get("surname"):
                parts.append(result["surname"])
            if result.get("given_names"):
                parts.append(result["given_names"])
            if parts:
                result["full_name"] = " ".join(parts)
                confs = [
                    result["field_confidence"].get("surname"),
                    result["field_confidence"].get("given_names"),
                ]
                confs = [c for c in confs if c is not None]
                result["field_confidence"]["full_name"] = min(confs) if confs else None

        if document_type is None and mrz_data.get("line1", "").startswith("P"):
            result["document_type"] = "passport"

        for key in all_field_keys:
            ocr_val = ocr_sources.get(key)
            mrz_val = mrz_sources.get(key)
            final_val = result.get(key)

            if final_val is None:
                field_status[key] = "not_detected"
            elif ocr_val and mrz_val:
                consistency = _compare_field_values(ocr_val, mrz_val, key)
                if consistency == "conflict":
                    field_status[key] = "conflict"
                    logger.warning(f"Field '{key}' conflict: OCR='{ocr_val}' vs MRZ='{mrz_val}'")
                else:
                    field_status[key] = "consistent"
            elif ocr_val and not mrz_val:
                field_status[key] = "extracted"
            elif mrz_val and not ocr_val:
                field_status[key] = "extracted"
            else:
                field_status[key] = "extracted"
    else:
        for key in all_field_keys:
            field_status[key] = "extracted" if result.get(key) is not None else "not_detected"

    result["field_status"] = field_status
    return result


# =============================================================================
# Passport-specific extraction
# =============================================================================

# Passport visual field labels (fuzzy/keyword matching)
PASSPORT_LABEL_KEYWORDS = {
    "passport_number": ["passport no", "passport number", "passport no.", "passport#"],
    "surname": ["surname", "family name", "last name"],
    "given_names": ["given name", "given names", "first name"],
    "nationality": ["nationality", "national"],
    "sex": ["sex", "gender"],
    "date_of_birth": ["date of birth", "dob", "birth date", "d.o.b"],
    "date_of_expiry": ["date of expiry", "expiry date", "valid until", "expires"],
    "date_of_issue": ["date of issue", "issue date", "issued on"],
    "place_of_birth": ["place of birth"],
    "place_of_issue": ["place of issue", "issued at", "issuing authority"],
}

# Gender normalization
GENDER_MAP = {"MALE": "M", "FEMALE": "F", "M": "M", "F": "F"}

# Nationality normalization
NATIONALITY_MAP = {"INDIAN": "IND", "INDIA": "IND"}

# Strings that are clearly OCR garbage — never accept as field values
PASSPORT_GARBAGE_PATTERNS = [
    r"^[^a-zA-Z]*$",  # No alphabetic chars at all (e.g. "56T", "39717")
    r"^\s*\d+\s*$",   # Pure digits
    r"/",              # Lines with / are typically labels ("FAI / SEX", "2134 / Type")
    r"\btype\b",       # "Type" is a passport layout label
]


def _is_valid_passport_visual_value(value: str, field_key: str) -> bool:
    """Validate that a visual OCR value is plausible for the given field.

    Rejects OCR garbage, labels, and random strings.
    Returns True only if the value passes validation for the field type.
    """
    if not value or not value.strip():
        return False
    cleaned = value.strip()

    # Reject values that are clearly labels or garbage
    cleaned_lower = cleaned.lower()

    # Reject label-like values
    if _is_label_like(cleaned):
        return False

    # Reject values containing / (typically label fragments like "FAI / SEX", "2134 / Type")
    # Exception: dates legitimately use / (e.g. 15/08/1995)
    if "/" in cleaned and field_key not in ("date_of_birth", "date_of_expiry", "date_of_issue"):
        return False

    # Field-specific validation
    if field_key in ("date_of_birth", "date_of_expiry", "date_of_issue"):
        parsed = _parse_date(cleaned)
        if not parsed:
            return False
        # Additional: reject if it looks like random OCR noise with digits
        digit_count = sum(1 for c in cleaned if c.isdigit())
        alpha_count = sum(1 for c in cleaned if c.isalpha())
        # A valid date has more digits than letters
        if digit_count < 4:
            return False

    elif field_key == "sex":
        norm = GENDER_MAP.get(cleaned.upper(), "")
        if norm not in ("M", "F"):
            return False

    elif field_key == "nationality":
        norm = re.sub(r"[^A-Z]", "", cleaned.upper())
        # Must be a valid 3-letter country code or known normalization
        if len(norm) != 3 or not norm.isalpha():
            if norm not in NATIONALITY_MAP:
                return False

    elif field_key == "passport_number":
        # Must be alphanumeric and contain at least one digit
        norm = re.sub(r"[^A-Z0-9]", "", cleaned.upper())
        if len(norm) < 4 or not any(c.isdigit() for c in norm):
            return False
        # Reject if it looks like a label
        if any(kw in cleaned_lower for kw in ["passport", "type", "no", "number"]):
            return False

    elif field_key in ("surname", "given_names"):
        # Must contain at least 2 alphabetic characters
        alpha_count = sum(1 for c in cleaned if c.isalpha())
        if alpha_count < 2:
            return False
        # Reject common non-name patterns
        if cleaned_lower in ("(s)", "(s)", "s)", "(s", "s", "f t4", "f4"):
            return False
        # Reject if it contains only parens/short fragments
        stripped = re.sub(r"[^a-zA-Z]", "", cleaned)
        if len(stripped) < 2:
            return False

    elif field_key in ("place_of_birth", "place_of_issue"):
        # Must contain at least some alphabetic content and not be garbage
        alpha_count = sum(1 for c in cleaned if c.isalpha())
        if alpha_count < 3:
            return False
        # Reject pure digit/garbage strings
        non_space = re.sub(r"\s", "", cleaned)
        if re.match(r"^[^a-zA-Z]+$", non_space):
            return False
        # Reject strings with too many special characters (OCR garbage)
        special_count = sum(1 for c in cleaned if not c.isalnum() and not c.isspace() and c != ',')
        if special_count > len(cleaned) * 0.2:
            return False
        # Reject strings where alphabetic ratio is too low
        alpha_ratio = alpha_count / len(cleaned) if cleaned else 0
        if alpha_ratio < 0.5:
            return False
        # Reject strings with digits mixed into alphabetic content (garbage)
        digit_count = sum(1 for c in cleaned if c.isdigit())
        if digit_count > 0 and alpha_count < 6:
            return False
        # Reject very short strings that don't look like place names
        if len(cleaned) < 4:
            return False

    return True


def _find_passport_visual_field(ocr_lines: list[dict], field_key: str) -> tuple[Optional[str], Optional[float]]:
    """Find a passport field value from visual OCR using keyword matching.

    Handles corrupted labels by searching for keywords anywhere in each line.
    For place fields, collects multi-line values until the next field label.
    Only returns values that pass validation.
    """
    keywords = PASSPORT_LABEL_KEYWORDS.get(field_key, [])
    if not keywords:
        return None, None

    # Known field labels that stop multi-line collection
    stop_labels = set()
    for fk, kws in PASSPORT_LABEL_KEYWORDS.items():
        if fk != field_key:
            for kw in kws:
                stop_labels.add(kw.lower())

    for i, line in enumerate(ocr_lines):
        text = line.get("text", "")
        conf = line.get("confidence", 0.0)
        cleaned = text.lower().strip()

        for keyword in keywords:
            if keyword in cleaned:
                # Check if this line itself is the value (keyword embedded in value)
                pattern = re.compile(
                    re.escape(keyword) + r"s?\s*[:/\-]?\s*(.+)$",
                    re.IGNORECASE,
                )
                match = pattern.search(cleaned)
                if match:
                    value = match.group(1).strip()
                    if value and len(value) >= 1:
                        val = _clean_text(value)
                        if _is_valid_passport_visual_value(val, field_key):
                            return val, conf

                # Multi-line collection for place fields and other multi-line values
                if field_key in ("place_of_birth", "place_of_issue"):
                    candidate_lines = []
                    # Check next lines until we hit a stop label or end of lines
                    for j in range(i + 1, min(i + 8, len(ocr_lines))):
                        next_text = ocr_lines[j].get("text", "")
                        next_conf = ocr_lines[j].get("confidence", 0.0)
                        next_cleaned = _clean_text(next_text).lower()

                        # Stop at next field label
                        if next_cleaned and any(sl in next_cleaned for sl in stop_labels):
                            break
                        # Stop at label-like text
                        if next_cleaned and _is_label_like(next_cleaned):
                            break
                        # Stop at known field patterns
                        if next_cleaned and re.match(r'^(date|sex|gender|nationality|passport|surname|given|place|signature)', next_cleaned):
                            break

                        val = _clean_text(next_text)
                        if val and len(val) >= 1:
                            candidate_lines.append((val, next_conf))

                    if candidate_lines:
                        # Try single lines AND combined consecutive lines
                        best_val = None
                        best_conf = 0.0
                        best_score = -1.0

                        def _place_score(val: str) -> float:
                            """Score a place field value."""
                            alpha_count = sum(1 for ch in val if ch.isalpha())
                            total = len(val)
                            if total == 0:
                                return -1.0
                            alpha_ratio = alpha_count / total
                            # Prefer higher alpha ratio and reasonable length
                            # Use log scaling for length to avoid capping too early
                            import math
                            length_bonus = math.log2(max(total, 1)) * 1.5
                            return alpha_ratio * 10 + length_bonus

                        # Score individual lines
                        for val, c in candidate_lines:
                            score = _place_score(val)
                            if score > best_score and _is_valid_passport_visual_value(val, field_key):
                                best_score = score
                                best_val = val
                                best_conf = c

                        # Try combining consecutive lines (e.g., "NEW" + "DELHI" = "NEW DELHI")
                        for start_idx in range(len(candidate_lines)):
                            combined = candidate_lines[start_idx][0]
                            combined_conf = candidate_lines[start_idx][1]
                            for end_idx in range(start_idx + 1, len(candidate_lines)):
                                combined = combined + " " + candidate_lines[end_idx][0]
                                combined_conf = min(combined_conf, candidate_lines[end_idx][1])
                                score = _place_score(combined)
                                if score > best_score and _is_valid_passport_visual_value(combined, field_key):
                                    best_score = score
                                    best_val = combined
                                    best_conf = combined_conf

                        if best_val:
                            return best_val, best_conf

                # Single-line field: check next line for value (label on one line, value on next)
                if i + 1 < len(ocr_lines):
                    next_text = _clean_text(ocr_lines[i + 1].get("text", ""))
                    next_conf = ocr_lines[i + 1].get("confidence", 0.0)
                    if next_text and not _is_label_like(next_text) and len(next_text) >= 1:
                        if _is_valid_passport_visual_value(next_text, field_key):
                            return next_text, next_conf

    return None, None


def _normalize_passport_nationality(value: str) -> str:
    """Normalize nationality to 3-letter code."""
    if not value:
        return value
    v = value.upper().strip()
    v = re.sub(r"[^A-Z]", "", v)
    return NATIONALITY_MAP.get(v, v)


def _normalize_passport_gender(value: str) -> str:
    """Normalize gender to M/F."""
    if not value:
        return value
    v = value.upper().strip()
    return GENDER_MAP.get(v, v)


def _normalize_passport_number(value: str) -> str:
    """Normalize passport number — remove spaces, keep alphanumeric."""
    if not value:
        return value
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def extract_passport_fields(
    ocr_lines: list[dict],
    mrz_data: Optional[dict] = None,
) -> dict:
    """Extract passport-specific fields with MRZ priority.

    Priority: MRZ > validated visual passport field
    full_name is always null for passport (passport uses surname + given_names).
    """
    result = {
        "full_name": None,  # Passport does NOT have a single Full Name field
        "date_of_birth": None,
        "document_number": None,
        "address": None,
        "gender": None,
        "document_type": "passport",
        "father_name": None,
        "surname": None,
        "given_names": None,
        "nationality": None,
        "place_of_birth": None,
        "place_of_issue": None,
        "date_of_issue": None,
        "date_of_expiry": None,
        "field_confidence": {
            "full_name": None, "date_of_birth": None, "document_number": None,
            "address": None, "gender": None, "father_name": None,
            "surname": None, "given_names": None, "nationality": None,
            "place_of_birth": None, "place_of_issue": None,
            "date_of_issue": None, "date_of_expiry": None,
        },
        "field_status": {},
    }

    field_status = {}
    mrz_available = False

    # Step 1: Parse MRZ (primary source for core fields)
    if mrz_data and mrz_data.get("detected"):
        from app.services.mrz_service import parse_mrz_passport
        mrz_fields = parse_mrz_passport(mrz_data)
        mrz_available = bool(mrz_fields.get("passport_number"))

        # Apply MRZ values with high confidence
        mrz_confidence = mrz_data.get("confidence", 0.9)
        if mrz_available:
            mrz_confidence = max(mrz_confidence, 0.95)

        if mrz_fields.get("surname"):
            result["surname"] = mrz_fields["surname"]
            result["field_confidence"]["surname"] = mrz_confidence
            field_status["surname"] = "extracted"

        if mrz_fields.get("given_names"):
            result["given_names"] = mrz_fields["given_names"]
            result["field_confidence"]["given_names"] = mrz_confidence
            field_status["given_names"] = "extracted"

        if mrz_fields.get("passport_number"):
            result["document_number"] = _normalize_passport_number(mrz_fields["passport_number"])
            result["field_confidence"]["document_number"] = mrz_confidence
            field_status["document_number"] = "extracted"

        if mrz_fields.get("nationality"):
            result["nationality"] = _normalize_passport_nationality(mrz_fields["nationality"])
            result["field_confidence"]["nationality"] = mrz_confidence
            field_status["nationality"] = "extracted"

        if mrz_fields.get("sex"):
            result["gender"] = _normalize_passport_gender(mrz_fields["sex"])
            result["field_confidence"]["gender"] = mrz_confidence
            field_status["gender"] = "extracted"

        if mrz_fields.get("date_of_birth"):
            result["date_of_birth"] = mrz_fields["date_of_birth"]
            result["field_confidence"]["date_of_birth"] = mrz_confidence
            field_status["date_of_birth"] = "extracted"

        if mrz_fields.get("date_of_expiry"):
            result["date_of_expiry"] = mrz_fields["date_of_expiry"]
            result["field_confidence"]["date_of_expiry"] = mrz_confidence
            field_status["date_of_expiry"] = "extracted"

    # Step 2: Visual passport field extraction (supplements MRZ)
    # Only validates visual fields that pass strict validation.
    # Invalid visual values are silently discarded — never marked as conflict.
    visual_fields = [
        ("passport_number", "document_number"),
        ("surname", "surname"),
        ("given_names", "given_names"),
        ("nationality", "nationality"),
        ("sex", "gender"),
        ("date_of_birth", "date_of_birth"),
        ("date_of_expiry", "date_of_expiry"),
        ("date_of_issue", "date_of_issue"),
        ("place_of_birth", "place_of_birth"),
        ("place_of_issue", "place_of_issue"),
    ]

    for visual_field_key, result_key in visual_fields:
        vis_val, vis_conf = _find_passport_visual_field(ocr_lines, visual_field_key)

        # Validate the visual value before using it
        if vis_val and not _is_valid_passport_visual_value(vis_val, visual_field_key):
            # Garbage visual value — discard silently
            logger.debug(f"Passport visual {visual_field_key} discarded (invalid): '{vis_val}'")
            vis_val = None

        if vis_val:
            # Normalize the visual value
            if visual_field_key == "nationality":
                vis_val_norm = _normalize_passport_nationality(vis_val)
            elif visual_field_key == "sex":
                vis_val_norm = _normalize_passport_gender(vis_val)
            elif visual_field_key == "passport_number":
                vis_val_norm = _normalize_passport_number(vis_val)
            elif visual_field_key in ("surname", "given_names"):
                vis_val_norm = vis_val.title()
            elif visual_field_key in ("date_of_birth", "date_of_expiry", "date_of_issue"):
                vis_val_norm = _normalize_date(vis_val) or vis_val
            else:
                vis_val_norm = vis_val

            if result.get(result_key) is not None and mrz_available:
                # MRZ already provided — compare for consistency
                mrz_val = result[result_key]
                if visual_field_key in ("date_of_birth", "date_of_expiry", "date_of_issue"):
                    mrz_comp = mrz_val
                    vis_comp = vis_val_norm if _normalize_date(vis_val) else None
                elif visual_field_key in ("nationality", "sex", "passport_number"):
                    mrz_comp = mrz_val.upper()
                    vis_comp = vis_val_norm.upper()
                else:
                    mrz_comp = mrz_val.strip().upper()
                    vis_comp = vis_val_norm.strip().upper()

                if vis_comp and mrz_comp == vis_comp:
                    field_status[result_key] = "consistent"
                elif vis_comp:
                    field_status[result_key] = "conflict"
                    logger.warning(
                        f"Passport {result_key} conflict: MRZ='{mrz_val}' vs visual='{vis_val}'"
                    )
                # If vis_comp is None (garbage that passed basic but not date validation),
                # keep MRZ value with "extracted" status
            elif result.get(result_key) is None:
                # No MRZ value — use visual extraction
                result[result_key] = vis_val_norm
                result["field_confidence"][result_key] = vis_conf
                field_status[result_key] = "extracted"

    # Step 3: full_name is always null for passport documents
    # Passport uses surname + given_names separately
    result["full_name"] = None
    result["field_confidence"]["full_name"] = None
    field_status["full_name"] = "not_detected"

    # Step 4: Set remaining field statuses
    for key in result["field_confidence"]:
        if key not in field_status:
            field_status[key] = "extracted" if result.get(key) is not None else "not_detected"

    result["field_status"] = field_status
    return result
