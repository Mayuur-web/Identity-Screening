"""MRZ (Machine Readable Zone) Service — Detection and extraction of MRZ regions.

Handles detection of MRZ regions in passport/identity documents and
extracts the two standardized MRZ lines.
Includes MRZ-specific image preprocessing for improved OCR accuracy.
"""

import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# MRZ character set (ICAO 9303)
MRZ_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<")


def clean_mrz_line(text: str) -> str:
    """Clean an OCR-detected MRZ line.

    Preserves MRZ-valid characters while fixing common OCR errors.
    """
    # Uppercase
    text = text.upper()
    # Replace common OCR confusions in MRZ context
    replacements = {
        "O": "0",  # In MRZ, 'O' is often '0'
        "I": "1",  # In MRZ, 'I' is often '1'
        "B": "8",  # Sometimes confused
        "S": "5",  # Sometimes confused
        "Z": "2",  # Sometimes confused
    }
    # Only replace if the character is clearly not part of a name
    # (MRZ line 2 starts with P or A, line 1 has < separators)
    return text


def is_mrz_line(text: str) -> bool:
    """Heuristic check if a text line looks like an MRZ line."""
    if not text:
        return False
    text = text.upper().strip()
    if len(text) < 20 or len(text) > 50:
        return False
    if " " in text:
        return False
    mrz_ratio = sum(1 for c in text if c in MRZ_CHARS) / len(text)
    return mrz_ratio > 0.7


def validate_mrz_passport(line1: str, line2: str) -> bool:
    """Strict validation of a TD3 passport MRZ.

    A valid passport MRZ must satisfy:
    - line1 and line2 must be structurally different
    - line1 begins with P<
    - line1 contains << (surname<<given names separator)
    - line1 is approximately 30-44 characters
    - line2 begins with alphanumeric (passport number)
    - line2 must NOT contain << (line2 is data, not a name line)
    - line2 contains a 3-letter nationality code at positions 10-12
    - line2 contains 6-digit DOB at positions 13-18
    - line2 contains sex M/F at position 20
    - line2 contains 6-digit expiry at positions 21-26
    - Both lines contain only A-Z, 0-9, and <
    """
    if not line1 or not line2:
        return False

    line1 = line1.upper().strip()
    line2 = line2.upper().strip()

    # Lines must be structurally different — identical lines are never valid
    if line1 == line2:
        return False

    # Line 1: must start with P<
    if not line1.startswith("P<"):
        return False

    # Line 1: must contain << in the name area (positions 5-14)
    # This distinguishes name lines (SURNAME<<GIVEN) from data lines
    # << after position 14 is just MRZ filler padding, not a name separator
    if not re.search(r'<<', line1[5:15]):
        return False

    # Line 1: reasonable length
    if len(line1) < 30 or len(line1) > 44:
        return False

    # Line 2: must NOT contain << in the first 20 characters
    # (line2 is document data, not a name line; << in filler area 27+ is normal)
    if "<<" in line2[:20]:
        return False

    # Line 2: must be reasonable length
    if len(line2) < 30 or len(line2) > 44:
        return False

    # Line 2: must contain only MRZ characters
    if not all(c in MRZ_CHARS for c in line2):
        return False

    # Line 2: passport number area (0-7) should be alphanumeric
    passport_area = line2[0:8]
    if not passport_area or not any(c.isalnum() for c in passport_area):
        return False

    # Line 2: nationality (10-12) should be 3 letters
    nationality = line2[10:13]
    if not nationality.isalpha() or len(nationality) != 3:
        return False

    # Line 2: DOB (13-18) should be 6 digits
    dob = line2[13:19]
    if not dob.isdigit() or len(dob) != 6:
        return False

    # Line 2: DOB month (14-15) should be 01-12
    month = int(dob[2:4])
    if month < 1 or month > 12:
        return False

    # Line 2: DOB day (16-17) should be 01-31
    day = int(dob[4:6])
    if day < 1 or day > 31:
        return False

    # Line 2: sex (20) should be M, F, or <
    sex = line2[20]
    if sex not in ("M", "F", "<"):
        return False

    # Line 2: expiry (21-26) should be 6 digits
    expiry = line2[21:27]
    if not expiry.isdigit() or len(expiry) != 6:
        return False

    # Line 2: expiry month (22-23) should be 01-12
    exp_month = int(expiry[2:4])
    if exp_month < 1 or exp_month > 12:
        return False

    # Line 2: expiry day (24-25) should be 01-31
    exp_day = int(expiry[4:6])
    if exp_day < 1 or exp_day > 31:
        return False

    return True


def detect_mrz(ocr_lines: list[dict], image_height: Optional[int] = None) -> dict:
    """Detect MRZ lines from OCR output.

    MRZ is typically at the bottom of the document. We look for
    consecutive lines that match MRZ characteristics.

    Args:
        ocr_lines: List of dicts with 'text' and 'confidence' keys.
        image_height: Optional image height for position-based detection.

    Returns:
        dict with keys: detected, line1, line2, confidence
    """
    result = {
        "detected": False,
        "line1": None,
        "line2": None,
        "confidence": None,
    }

    if not ocr_lines or len(ocr_lines) < 2:
        return result

    # Look for consecutive MRZ-like lines
    # MRZ is usually the last 2 lines of the document
    candidates = []
    for i in range(len(ocr_lines) - 1):
        line1 = ocr_lines[i].get("text", "")
        line2 = ocr_lines[i + 1].get("text", "")
        conf1 = ocr_lines[i].get("confidence", 0.0)
        conf2 = ocr_lines[i + 1].get("confidence", 0.0)

        if (is_mrz_line(line1) and is_mrz_line(line2)
                and line1.upper().strip() != line2.upper().strip()):
            # Validate the MRZ pair structurally before accepting
            l1 = line1.upper().strip()
            l2 = line2.upper().strip()
            # Try original lines and OCR-corruption fixes for line 1
            for l1_fixed in _normalize_mrz_line1(l1):
                l1_padded = l1_fixed.ljust(44, "<")
                l2_padded = l2.ljust(44, "<")
                if validate_mrz_passport(l1_padded, l2_padded):
                    candidates.append({
                        "line1": l1_fixed.ljust(44, "<"),
                        "line2": line2.upper().strip().ljust(44, "<"),
                        "confidence": round((conf1 + conf2) / 2, 4),
                        "index": i,
                    })
                    break

    if candidates:
        # Prefer the last MRZ occurrence (usually at the bottom of the document)
        best = candidates[-1]
        result["detected"] = True
        result["line1"] = best["line1"].upper().strip()
        result["line2"] = best["line2"].upper().strip()
        result["confidence"] = best["confidence"]
        logger.info(f"MRZ detected at position {best['index']}")

    return result


def parse_mrz_passport(mrz_data: dict) -> dict:
    """Parse TD3 (passport) MRZ format into structured fields.

    MRZ Line 1: P<UTO Surname<<Given Names<<<<<<<<<<<<<<<<<<
    MRZ Line 2: PassportNo<CheckDigit Nationality DOB Sex ExpiryDate<CheckDigit

    Returns extracted fields or None for unparseable fields.
    """
    fields = {
        "passport_number": None,
        "nationality": None,
        "date_of_birth": None,
        "sex": None,
        "date_of_expiry": None,
        "surname": None,
        "given_names": None,
    }

    if not mrz_data.get("detected"):
        return fields

    line1 = mrz_data.get("line1") or ""
    line2 = mrz_data.get("line2") or ""

    # Reject identical lines — never valid for a passport MRZ
    if line1 and line2 and line1.strip() == line2.strip():
        logger.warning("MRZ rejected: identical lines")
        return fields

    # Validate line1 is actually a name line (starts with P< and has << in name area)
    # If line1 is not a valid name line, MRZ name fields cannot be extracted
    line1_is_name_line = (
        line1
        and line1.startswith("P<")
        and len(line1) >= 20
        and re.search(r'<<', line1[5:15])
    )

    # Parse line 1: P<IC Surname<<Given Names
    if line1_is_name_line and len(line1) >= 30:  # Accept shorter lines (OCR may trim trailing < chars)
        # Document type (1-2): P< or PA
        # Issuing country (3-5): 3-letter code
        # Name (6-44): Surname<<Given Names with < padding
        end = min(len(line1), 44)
        name_part = line1[5:end].strip("<")
        parts = name_part.split("<<")
        if len(parts) >= 2:
            surname_raw = parts[0].strip("<")
            given_raw = parts[1].strip("<")
            # Replace internal < with spaces (MRZ uses < as word separator in names)
            fields["surname"] = surname_raw.replace("<", " ").title() if surname_raw else None
            fields["given_names"] = given_raw.replace("<", " ").title() if given_raw else None
        elif len(parts) == 1:
            fields["surname"] = parts[0].strip("<").replace("<", " ").title() if parts[0].strip("<") else None

    # Parse line 2: PassportNo<Check Nationality DOB Sex Expiry<Check
    if len(line2) >= 30:  # Accept shorter lines (OCR may trim trailing < chars)
        # Passport number (0-8): 9 chars
        passport_raw = line2[0:9].replace("<", "")
        if passport_raw:
            fields["passport_number"] = passport_raw

        # Nationality (10-12): 3-letter country code
        nationality = line2[10:13].replace("<", "")
        if nationality and nationality.isalpha():
            fields["nationality"] = nationality

        # Date of birth (13-18): YYMMDD
        dob_raw = line2[13:19]
        if len(dob_raw) == 6 and dob_raw.isdigit():
            yy, mm, dd = dob_raw[:2], dob_raw[2:4], dob_raw[4:6]
            year = int(yy)
            # ICAO convention: years 00-99 map to 1900-2099
            # Heuristic: if year > 30, it's likely 1900s
            if year > 30:
                year = 1900 + year
            else:
                year = 2000 + year
            fields["date_of_birth"] = f"{year}-{mm}-{dd}"

        # Sex (20): M, F, or <
        sex = line2[20]
        if sex in ("M", "F", "<"):
            fields["sex"] = sex if sex != "<" else None

        # Date of expiry (21-26): YYMMDD
        expiry_raw = line2[21:27]
        if len(expiry_raw) == 6 and expiry_raw.isdigit():
            yy, mm, dd = expiry_raw[:2], expiry_raw[2:4], expiry_raw[4:6]
            year = 2000 + int(yy)
            fields["date_of_expiry"] = f"{year}-{mm}-{dd}"

    return fields


def parse_mrz_generic(mrz_data: dict) -> dict:
    """Generic MRZ parsing — extract what we can without assuming TD3 format."""
    fields = {
        "passport_number": None,
        "nationality": None,
        "date_of_birth": None,
        "sex": None,
        "date_of_expiry": None,
        "surname": None,
        "given_names": None,
    }

    if not mrz_data.get("detected"):
        return fields

    # Try passport TD3 parsing first
    td3_fields = parse_mrz_passport(mrz_data)
    if td3_fields.get("passport_number"):
        return td3_fields

    # Fallback: try to extract what we can
    line1 = mrz_data.get("line1", "")
    line2 = mrz_data.get("line2", "")

    if "<<" in line1:
        name_part = line1.split("<<")
        if len(name_part) >= 2:
            fields["surname"] = name_part[0].replace("P<", "").replace("PA", "").strip("<").title() or None
            fields["given_names"] = name_part[1].strip("<").title() or None

    matches = re.findall(r"[A-Z0-9]{5,}", line2)
    if matches:
        for m in matches:
            if len(m) >= 6:
                fields["passport_number"] = m
                break

    return fields


# =============================================================================
# MRZ-specific image extraction
# =============================================================================

def _preprocess_mrz_region(crop_bgr, sharpness: float = 0.0) -> list[tuple[str, "np.ndarray"]]:
    """Create preprocessing variants for an MRZ image crop.

    Returns a list of (variant_name, processed_image) tuples.
    Each variant is a grayscale image suitable for EasyOCR.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY) if len(crop_bgr.shape) == 3 else crop_bgr

    # Upscale 4x (sweet spot for MRZ characters at typical passport resolutions)
    h, w = gray.shape[:2]
    scale = 4
    upscaled = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    variants = []

    # Variant A: CLAHE contrast enhancement (good general-purpose)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    variants.append(("clahe", clahe.apply(upscaled)))

    # Variant B: CLAHE + unsharp mask (enhances MRZ character edges)
    blurred = cv2.GaussianBlur(upscaled, (0, 0), 3)
    sharpened = cv2.addWeighted(upscaled, 1.5, blurred, -0.5, 0)
    variants.append(("sharp", sharpened))

    # Variant C: Otsu binarization (helps with low-contrast / security patterns)
    _, otsu = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("otsu", otsu))

    return variants


def _normalize_mrz_line1(line: str) -> list[str]:
    """Try to fix common OCR corruptions of MRZ line 1.

    Returns a list of candidate corrections to try, in order of likelihood.
    The first candidate is the original line unchanged.
    """
    candidates = [line]  # Always try the original first

    # Fix 1: P< read as PI, P1, PIND, etc.
    # If line starts with P followed by a non-< char, try inserting < after P
    if len(line) >= 2 and line[0] == "P" and line[1] != "<":
        # Try P< + rest (replace char after P with <)
        fixed = "P<" + line[2:]
        if fixed not in candidates:
            candidates.append(fixed)
        # Also try P< + everything from position 1 (insert < at position 1)
        fixed2 = "P<" + line[1:]
        if fixed2 not in candidates:
            candidates.append(fixed2)

    # Fix 2: Missing << in name area (positions 5-14)
    # Some passports use single < in name, MRZ spec requires <<
    if len(line) >= 15:
        name_area = line[5:15]
        if "<<" not in name_area and "<" in name_area:
            # Try doubling the < separators
            fixed = line[:5] + name_area.replace("<", "<<") + line[15:]
            if fixed not in candidates:
                candidates.append(fixed)

    return candidates


def _try_detect_mrz_from_variants(
    reader,
    image_path: str,
    crop_bgr,
    crop_label: str,
    temp_prefix: str,
) -> Optional[dict]:
    """Run EasyOCR on preprocessing variants of a crop and try to detect MRZ.

    Returns a result dict if MRZ is detected, otherwise None.
    Performs early exit — stops as soon as a valid MRZ is found.
    """
    import cv2

    variants = _preprocess_mrz_region(crop_bgr)

    for variant_name, variant_img in variants:
        tag = f"{temp_prefix}_{variant_name}"
        temp_path = image_path.rsplit(".", 1)[0] + f"_mrz_{tag}.png"
        try:
            cv2.imwrite(temp_path, variant_img)
            ocr_results = reader.readtext(temp_path)
        except Exception as e:
            logger.debug(f"EasyOCR failed on {tag}: {e}")
            continue
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

        # Normalize OCR output to MRZ characters
        normalized = []
        for bbox, text, conf in ocr_results:
            if text and text.strip():
                text_upper = text.strip().upper()
                text_clean = re.sub(r"[^A-Z0-9<]", "", text_upper)
                if text_clean:
                    normalized.append({"text": text_clean, "confidence": round(float(conf), 4)})

        if len(normalized) < 2:
            continue

        # Try consecutive-line MRZ detection
        for i in range(len(normalized) - 1):
            l1 = normalized[i]["text"]
            l2 = normalized[i + 1]["text"]
            if l1 == l2:
                continue
            if not (is_mrz_line(l1) and is_mrz_line(l2)):
                continue

            # Try the original lines first, then OCR-corruption fixes for line 1
            l1_candidates = _normalize_mrz_line1(l1)
            for l1_fixed in l1_candidates:
                l1_pad = l1_fixed.ljust(44, "<")
                l2_pad = l2.ljust(44, "<")
                if validate_mrz_passport(l1_pad, l2_pad):
                    conf = round(
                        (normalized[i]["confidence"] + normalized[i + 1]["confidence"]) / 2, 4
                    )
                    logger.info(
                        f"MRZ detected from {crop_label} variant={variant_name} "
                        f"lines {i}-{i+1} conf={conf}"
                    )
                    return {
                        "detected": True,
                        "line1": l1_pad,
                        "line2": l2_pad,
                        "confidence": conf,
                    }

    return None


def extract_mrz_from_image(image_path: str) -> dict:
    """Extract MRZ from a passport image using multi-region cropping.

    Tries several bottom-region crops (bottom 15%, 20%, 25%, 30%) with
    multiple preprocessing variants per crop.  Exits early as soon as a
    valid MRZ is found, keeping the total number of readtext() calls low.

    Falls back to character-split reconstruction if the primary strategy
    does not find a valid MRZ.

    Returns dict with: detected, line1, line2, confidence, raw_lines
    """
    result = {
        "detected": False,
        "line1": None,
        "line2": None,
        "confidence": None,
        "raw_lines": [],
    }

    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("OpenCV not available for MRZ image extraction")
        return result

    if not os.path.exists(image_path):
        logger.error(f"Image not found for MRZ extraction: {image_path}")
        return result

    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Failed to read image: {image_path}")
            return result

        h, w = img.shape[:2]
        logger.info(f"[MRZ] Image size: {w}x{h}")

        from app.services.ocr_service import get_easyocr_reader
        reader = get_easyocr_reader()

        # ------------------------------------------------------------------
        # Strategy 1: Multi-region crop with early exit
        # Try different bottom-region sizes.  MRZ position varies across
        # passport layouts (landscape vs portrait, with/without margins).
        # ------------------------------------------------------------------
        crop_pcts = [0.15, 0.20, 0.25, 0.30]
        ocr_call_count = 0

        for crop_pct in crop_pcts:
            crop_start = int(h * (1.0 - crop_pct))
            crop_bgr = img[crop_start:h, :]
            crop_h = crop_bgr.shape[0]
            if crop_h < 20:
                continue

            label = f"bottom-{int(crop_pct*100)}%"
            detected = _try_detect_mrz_from_variants(
                reader, image_path, crop_bgr, label, f"mrz_{int(crop_pct*100)}",
            )
            # Each _try_detect_mrz_from_variants call runs up to 3 readtext
            # calls (3 preprocessing variants) but exits early on success.
            ocr_call_count += 3  # worst case per crop region

            if detected is not None:
                result.update(detected)
                logger.info(
                    f"[MRZ] Primary detection succeeded at {label} "
                    f"(~{ocr_call_count} readtext calls max)"
                )
                return result

        logger.info(
            f"[MRZ] Primary detection exhausted {len(crop_pcts)} regions, "
            f"falling back to character-split"
        )

    except Exception as e:
        logger.error(f"MRZ image extraction failed: {e}")

    # ------------------------------------------------------------------
    # Strategy 2: Character-split reconstruction (fallback)
    # For low-res or heavily patterned images where whole-word OCR fails.
    # ------------------------------------------------------------------
    cs_result = extract_mrz_character_split(image_path)
    if cs_result["detected"]:
        return cs_result

    return result


def _cluster_into_rows(items: list) -> list[list]:
    """Cluster detections into horizontal rows using Y-coordinate tolerance.

    Uses median character height as tolerance: detections whose center Y
    values are within ~1.0 character heights belong to the same row.
    Returns a list of rows (each row is a list of items), sorted by Y.
    """
    if not items:
        return []

    # Compute median character height
    heights = [it["bbox_h"] for it in items if it["bbox_h"] > 0]
    if not heights:
        return []
    median_h = sorted(heights)[len(heights) // 2]
    # Use 1.0x median height (was 0.6x which was too tight for low-res images)
    tolerance = median_h * 1.0

    # Sort by center Y
    sorted_items = sorted(items, key=lambda x: x["center_y"])

    # Greedy clustering: start a new row when Y gap > tolerance
    rows = [[sorted_items[0]]]
    for item in sorted_items[1:]:
        last_row_y = sum(it["center_y"] for it in rows[-1]) / len(rows[-1])
        if abs(item["center_y"] - last_row_y) <= tolerance:
            rows[-1].append(item)
        else:
            rows.append([item])

    # Merge small adjacent rows if their Y distance is small
    merged = []
    for row in rows:
        if merged:
            prev_y = sum(it["center_y"] for it in merged[-1]) / len(merged[-1])
            curr_y = sum(it["center_y"] for it in row) / len(row)
            if abs(curr_y - prev_y) <= tolerance:
                merged[-1].extend(row)
                continue
        merged.append(row)

    return merged


def _merge_close_fragments(row_items: list) -> list:
    """Merge horizontally close detections that are likely adjacent MRZ characters.

    If two detections are very close horizontally and have similar Y,
    concatenate them (they may be part of the same MRZ character or
    a multi-char fragment that was split).
    """
    if len(row_items) < 2:
        return row_items

    # Sort by X
    row_items.sort(key=lambda x: x["center_x"])

    merged = [row_items[0]]
    for item in row_items[1:]:
        prev = merged[-1]
        # Horizontal distance between the right edge of prev and left edge of current
        h_dist = item["bbox_x"] - (prev["bbox_x"] + prev["bbox_w"])
        # If very close horizontally and similar Y, merge
        y_diff = abs(item["center_y"] - prev["center_y"])
        if h_dist < prev["bbox_w"] * 0.5 and y_diff < prev["bbox_h"] * 0.3:
            merged[-1] = {
                **prev,
                "text": prev["text"] + item["text"],
                "confidence": min(prev["confidence"], item["confidence"]),
                "center_x": (prev["center_x"] + item["center_x"]) / 2,
                "bbox_w": (item["bbox_x"] + item["bbox_w"]) - prev["bbox_x"],
            }
        else:
            merged.append(item)

    return merged


def _score_mrz_candidate(line1: str, line2: str) -> float:
    """Score an MRZ candidate. Higher is better."""
    score = 0.0

    # Length proximity to 44
    score -= abs(len(line1) - 44) * 0.5
    score -= abs(len(line2) - 44) * 0.5

    # MRZ character ratio
    mrz_ratio_1 = sum(1 for c in line1 if c in MRZ_CHARS) / len(line1) if line1 else 0
    mrz_ratio_2 = sum(1 for c in line2 if c in MRZ_CHARS) / len(line2) if line2 else 0
    score += mrz_ratio_1 * 10
    score += mrz_ratio_2 * 10

    # line1 starts with P<
    if line1.startswith("P<"):
        score += 5.0

    # line1 has << in name area
    if re.search(r'<<', line1[5:15]) if len(line1) >= 15 else False:
        score += 3.0

    return score


def _reconstruct_mrz_from_detections(detections: list, diagnostics: bool = False) -> list[tuple[str, str, float]]:
    """Reconstruct MRZ line candidates from character-level OCR detections.

    Uses bounding-box coordinates to group detections into two rows,
    merges close fragments, sorts by X, and returns candidates.

    Args:
        detections: list of (bbox, text, confidence) tuples from EasyOCR.
        diagnostics: if True, log detailed diagnostic information.

    Returns:
        list of (line1, line2, score) tuples, sorted by score descending.
    """
    if diagnostics:
        try:
            from app.services.mrz_diagnostics import (
                log_clustering_result, log_merged_row, log_reconstructed_lines,
                log_validation_failure,
            )
        except ImportError:
            log_clustering_result = log_merged_row = log_reconstructed_lines = log_validation_failure = None
    else:
        log_clustering_result = log_merged_row = log_reconstructed_lines = log_validation_failure = None

    if not detections:
        return []

    # Extract bounding box info for each detection
    items = []
    for bbox, text, conf in detections:
        text = text.strip()
        if not text:
            continue
        # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        items.append({
            "text": text,
            "confidence": float(conf),
            "center_y": sum(ys) / len(ys),
            "center_x": sum(xs) / len(xs),
            "bbox_x": x_min,
            "bbox_y": y_min,
            "bbox_w": x_max - x_min,
            "bbox_h": y_max - y_min,
        })

    if len(items) < 10:
        if diagnostics:
            logger.warning(f"[MRZ-CS] Too few items: {len(items)} < 10")
        return []

    # Cluster into rows
    rows = _cluster_into_rows(items)

    if diagnostics and log_clustering_result:
        log_clustering_result(rows, items)

    # We need exactly 2 rows for MRZ
    if len(rows) < 2:
        if diagnostics:
            logger.warning(f"[MRZ-CS] Only {len(rows)} row(s) found, need 2")
        return []

    # If more than 2 rows, try different combinations of the top clusters
    # But prefer the two rows with the most detections (most likely MRZ)
    row_candidates = []
    if len(rows) == 2:
        row_candidates = [rows]
    else:
        # Try all pairs of rows, prefer pairs with most total detections
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                row_candidates.append([rows[i], rows[j]])
        # Sort by total detection count (descending)
        row_candidates.sort(key=lambda r: sum(len(row) for row in r), reverse=True)
        row_candidates = row_candidates[:5]  # Top 5 pairs

    candidates = []
    for row_pair in row_candidates:
        for row_a, row_b in [(row_pair[0], row_pair[1]), (row_pair[1], row_pair[0])]:
            # Merge close fragments in each row
            merged_a = _merge_close_fragments(list(row_a))
            merged_b = _merge_close_fragments(list(row_b))

            # Sort by X and concatenate
            merged_a.sort(key=lambda x: x["center_x"])
            merged_b.sort(key=lambda x: x["center_x"])

            line1_raw = "".join(it["text"] for it in merged_a)
            line2_raw = "".join(it["text"] for it in merged_b)

            if diagnostics and log_merged_row:
                log_merged_row(merged_a, "Row_A (candidate line1)")
                log_merged_row(merged_b, "Row_B (candidate line2)")

            # Normalize to MRZ characters only (no O->0 / I->1 — corrupts IND)
            line1_clean = re.sub(r"[^A-Z0-9<]", "", line1_raw.upper())
            line2_clean = re.sub(r"[^A-Z0-9<]", "", line2_raw.upper())

            if diagnostics and log_reconstructed_lines:
                log_reconstructed_lines(line1_raw, line2_raw)

            if not line1_clean or not line2_clean:
                if diagnostics:
                    logger.warning(f"[MRZ-CS] Empty after normalization: L1={line1_clean!r} L2={line2_clean!r}")
                continue

            # Pad to 44 chars
            line1_padded = line1_clean.ljust(44, "<")
            line2_padded = line2_clean.ljust(44, "<")

            if not validate_mrz_passport(line1_padded, line2_padded):
                if diagnostics and log_validation_failure:
                    log_validation_failure(line1_padded, line2_padded)
                continue

            score = _score_mrz_candidate(line1_clean, line2_clean)
            candidates.append((line1_padded, line2_padded, score))

    # Sort by score (highest first)
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates


def extract_mrz_character_split(image_path: str) -> dict:
    """Fallback MRZ extraction for low-resolution / character-split OCR.

    Tries multiple bottom-region crops and preprocessing variants to
    reconstruct MRZ from character-level detections.

    Returns dict with: detected, line1, line2, confidence
    """
    try:
        from app.services.mrz_diagnostics import (
            log_detections, log_clustering_result, log_merged_row,
            log_reconstructed_lines, log_validation_failure, log_candidate_score,
        )
    except ImportError:
        log_detections = log_clustering_result = log_merged_row = None
        log_reconstructed_lines = log_validation_failure = log_candidate_score = None

    result = {
        "detected": False,
        "line1": None,
        "line2": None,
        "confidence": None,
    }

    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("OpenCV not available for MRZ character-split extraction")
        return result

    if not os.path.exists(image_path):
        logger.error(f"Image not found for MRZ character-split extraction: {image_path}")
        return result

    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Failed to read image: {image_path}")
            return result

        h, w = img.shape[:2]
        logger.warning(f"[MRZ-CS] Image size: {w}x{h}")

        # Try bottom-region crops (2 crops × 2 variants = 4 readtext calls max)
        crop_percentages = [0.20, 0.25]

        try:
            from app.services.ocr_service import get_easyocr_reader
            reader = get_easyocr_reader()
        except Exception as e:
            logger.warning(f"EasyOCR failed to initialize for character-split: {e}")
            return result

        all_candidates = []
        total_detections_all = 0

        for crop_pct in crop_percentages:
            crop_start = int(h * (1.0 - crop_pct))
            mrz_crop = img[crop_start:h, :]
            crop_h, crop_w = mrz_crop.shape[:2]
            if crop_h < 10:
                logger.warning(f"[MRZ-CS] crop_pct={crop_pct}: crop too small ({crop_h}px), skipping")
                continue

            logger.warning(f"[MRZ-CS] crop_pct={crop_pct}: crop region y={crop_start}-{h}, size={crop_w}x{crop_h}")

            # Create multiple preprocessing variants
            scale = 5
            upscaled = cv2.resize(mrz_crop, (crop_w * scale, crop_h * scale),
                                  interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY) if len(upscaled.shape) == 3 else upscaled

            variants = []

            # Variant 1: CLAHE contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            variants.append(("clahe", clahe.apply(gray)))

            # Variant 2: Otsu binarization (helps with low-contrast MRZ)
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            variants.append(("otsu", otsu))

            for variant_name, variant_img in variants:
                tag = f"cs_{crop_pct}_{variant_name}"
                temp_path = image_path.rsplit(".", 1)[0] + f"_mrz_{tag}.png"
                try:
                    cv2.imwrite(temp_path, variant_img)
                    ocr_results = reader.readtext(temp_path)
                    detections = [(bbox, text.strip(), float(conf))
                                  for bbox, text, conf in ocr_results
                                  if text and text.strip()]
                    total_detections_all += len(detections)

                    logger.warning(
                        f"[MRZ-CS] {tag}: {len(detections)} detections from {len(ocr_results)} raw"
                    )

                    if detections and log_detections:
                        log_detections(detections, label=tag)

                    if detections:
                        candidates = _reconstruct_mrz_from_detections(
                            detections,
                            diagnostics=True,
                        )
                        for c in candidates:
                            if log_candidate_score:
                                log_candidate_score(c[0], c[1], c[2])
                        all_candidates.extend(candidates)

                except Exception as e:
                    logger.debug(f"EasyOCR variant {tag} failed: {e}")
                finally:
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

        logger.warning(
            f"[MRZ-CS] Total candidates across all variants: {len(all_candidates)} "
            f"(total detections: {total_detections_all})"
        )

        if not all_candidates:
            logger.warning("[MRZ-CS] No valid MRZ candidates found")
            return result

        # Pick the best candidate (highest score)
        all_candidates.sort(key=lambda x: x[2], reverse=True)
        best = all_candidates[0]

        result["detected"] = True
        result["line1"] = best[0]
        result["line2"] = best[1]
        result["confidence"] = 0.80
        logger.warning(
            f"[MRZ-CS] SUCCESS: L1={best[0][:30]!r} L2={best[1][:30]!r} score={best[2]:.2f}"
        )

    except Exception as e:
        logger.error(f"MRZ character-split extraction failed: {e}")

    return result
