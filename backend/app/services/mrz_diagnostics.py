"""MRZ Character-Split Pipeline Diagnostics.

Temporary diagnostic logging for debugging MRZ reconstruction failures.
Logs detailed information at each stage of the pipeline.
"""

import logging
import re
import os

logger = logging.getLogger("mrz_diagnostics")


def log_detections(detections: list, label: str = ""):
    """Log all OCR detections with bounding box details."""
    logger.warning(f"=== DIAGNOSTIC {label}: {len(detections)} detections ===")
    for i, det in enumerate(detections):
        bbox, text, conf = det
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        logger.warning(
            f"  [{i:3d}] text={text!r:12s} conf={conf:.3f} "
            f"center=({center_x:.0f},{center_y:.0f}) "
            f"size=({w:.0f}x{h:.0f}) "
            f"bbox_x={min(xs):.0f}"
        )


def log_clustering_result(rows: list, items: list):
    """Log row clustering results."""
    logger.warning(f"=== ROW CLUSTERING: {len(rows)} rows from {len(items)} items ===")
    heights = [it["bbox_h"] for it in items if it["bbox_h"] > 0]
    if heights:
        median_h = sorted(heights)[len(heights) // 2]
        logger.warning(f"  Median char height: {median_h:.1f}, tolerance: {median_h * 1.0:.1f}")

    for row_idx, row in enumerate(rows):
        avg_y = sum(it["center_y"] for it in row) / len(row)
        texts = [it["text"] for it in row]
        x_positions = [it["center_x"] for it in row]
        logger.warning(
            f"  Row {row_idx}: {len(row)} items, "
            f"avg_y={avg_y:.0f}, "
            f"x_range=({min(x_positions):.0f}-{max(x_positions):.0f}), "
            f"texts={texts[:10]}{'...' if len(texts) > 10 else ''}"
        )


def log_merged_row(row_items: list, label: str = ""):
    """Log merged row result."""
    if not row_items:
        logger.warning(f"  {label}: EMPTY ROW")
        return
    sorted_items = sorted(row_items, key=lambda x: x["center_x"])
    line_text = "".join(it["text"] for it in sorted_items)
    logger.warning(
        f"  {label}: {len(row_items)} fragments -> "
        f"line={line_text!r} (len={len(line_text)})"
    )


def log_reconstructed_lines(line1: str, line2: str):
    """Log the reconstructed MRZ lines before normalization."""
    logger.warning(f"=== RECONSTRUCTED LINES ===")
    logger.warning(f"  Line1 raw: {line1!r} (len={len(line1)})")
    logger.warning(f"  Line2 raw: {line2!r} (len={len(line2)})")
    line1_clean = re.sub(r"[^A-Z0-9<]", "", line1.upper())
    line2_clean = re.sub(r"[^A-Z0-9<]", "", line2.upper())
    logger.warning(f"  Line1 clean: {line1_clean!r} (len={len(line1_clean)})")
    logger.warning(f"  Line2 clean: {line2_clean!r} (len={len(line2_clean)})")


def log_validation_failure(line1: str, line2: str):
    """Log exactly why validate_mrz_passport rejects a candidate."""
    if not line1 or not line2:
        logger.warning(f"  VALIDATION FAIL: line1={line1!r} line2={line2!r} - empty line")
        return

    l1 = line1.upper().strip()
    l2 = line2.upper().strip()

    if l1 == l2:
        logger.warning(f"  VALIDATION FAIL: identical lines")
        return
    if not l1.startswith("P<"):
        logger.warning(f"  VALIDATION FAIL: line1 does not start with P<: {l1[:10]!r}")
        return
    if not re.search(r'<<', l1[5:15]) if len(l1) >= 15 else True:
        logger.warning(f"  VALIDATION FAIL: line1 missing << in name area [5:15]: {l1[5:15]!r}")
        return
    if len(l1) < 30 or len(l1) > 44:
        logger.warning(f"  VALIDATION FAIL: line1 length {len(l1)} not in [30,44]")
        return
    if "<<" in l2[:20]:
        logger.warning(f"  VALIDATION FAIL: line2 has << in first 20 chars: {l2[:20]!r}")
        return
    if len(l2) < 30 or len(l2) > 44:
        logger.warning(f"  VALIDATION FAIL: line2 length {len(l2)} not in [30,44]")
        return
    non_mrz = [c for c in l2 if c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"]
    if non_mrz:
        logger.warning(f"  VALIDATION FAIL: line2 has non-MRZ chars: {non_mrz}")
        return
    passport_area = l2[0:8]
    if not passport_area or not any(c.isalnum() for c in passport_area):
        logger.warning(f"  VALIDATION FAIL: passport area [0:8] invalid: {passport_area!r}")
        return
    nationality = l2[10:13]
    if not nationality.isalpha() or len(nationality) != 3:
        logger.warning(f"  VALIDATION FAIL: nationality [10:13] invalid: {nationality!r}")
        return
    dob = l2[13:19]
    if not dob.isdigit() or len(dob) != 6:
        logger.warning(f"  VALIDATION FAIL: DOB [13:19] invalid: {dob!r}")
        return
    month = int(dob[2:4])
    if month < 1 or month > 12:
        logger.warning(f"  VALIDATION FAIL: DOB month {month} out of range")
        return
    day = int(dob[4:6])
    if day < 1 or day > 31:
        logger.warning(f"  VALIDATION FAIL: DOB day {day} out of range")
        return
    sex = l2[20]
    if sex not in ("M", "F", "<"):
        logger.warning(f"  VALIDATION FAIL: sex char [20] invalid: {sex!r}")
        return
    expiry = l2[21:27]
    if not expiry.isdigit() or len(expiry) != 6:
        logger.warning(f"  VALIDATION FAIL: expiry [21:27] invalid: {expiry!r}")
        return
    exp_month = int(expiry[2:4])
    if exp_month < 1 or exp_month > 12:
        logger.warning(f"  VALIDATION FAIL: expiry month {exp_month} out of range")
        return
    exp_day = int(expiry[4:6])
    if exp_day < 1 or exp_day > 31:
        logger.warning(f"  VALIDATION FAIL: expiry day {exp_day} out of range")
        return

    logger.warning(f"  VALIDATION FAIL: unknown reason (should not reach here)")


def log_candidate_score(line1: str, line2: str, score: float):
    """Log candidate scoring details."""
    l1_len = len(line1)
    l2_len = len(line2)
    mrz_ratio_1 = sum(1 for c in line1 if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<") / l1_len if l1_len else 0
    mrz_ratio_2 = sum(1 for c in line2 if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<") / l2_len if l2_len else 0
    has_p_prefix = line1.startswith("P<")
    has_dbl_angle = bool(re.search(r'<<', line1[5:15])) if len(line1) >= 15 else False
    logger.warning(
        f"  CANDIDATE SCORE: {score:.2f} | "
        f"L1_len={l1_len} L2_len={l2_len} | "
        f"mrz_ratio=({mrz_ratio_1:.2f},{mrz_ratio_2:.2f}) | "
        f"P<={has_p_prefix} <<={has_dbl_angle} | "
        f"L1={line1[:20]!r} L2={line2[:20]!r}"
    )
