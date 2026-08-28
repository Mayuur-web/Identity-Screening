"""OCR Service — EasyOCR-based text extraction for identity documents.

Runs EasyOCR on preprocessed image variants and combines results
for improved accuracy on identity documents.

Architecture:
  Uploaded image → preprocessing (2 variants) → EasyOCR → merge → results
"""

import os
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded EasyOCR reader (initialized on first use)
_reader_instance = None


def _get_reader():
    """Get or initialize the EasyOCR reader (lazy loading)."""
    global _reader_instance
    if _reader_instance is None:
        logger.info("Initializing EasyOCR engine...")
        import easyocr
        _reader_instance = easyocr.Reader(["en"], gpu=False, verbose=False)
        logger.info("EasyOCR engine initialized successfully")
    return _reader_instance


def get_easyocr_reader():
    """Public accessor: return the shared, lazily-initialized EasyOCR reader.

    Other services (MRZ, face verification) should call this instead of
    creating their own ``easyocr.Reader`` to avoid the ~1.3 s model-load
    penalty on every invocation.
    """
    return _get_reader()


def _run_ocr_on_image(image_path: str) -> list[dict]:
    """Run EasyOCR on a single image and return raw detections."""
    try:
        reader = _get_reader()
        results = reader.readtext(image_path)
        lines = []
        for bbox, text, confidence in results:
            if text and text.strip():
                lines.append({
                    "text": text.strip(),
                    "confidence": round(float(confidence), 4),
                    "bbox": bbox,
                })
        return lines
    except Exception as e:
        logger.warning(f"OCR failed on {image_path}: {e}")
        return []


def _normalize_text(text: str) -> str:
    """Normalize text for deduplication comparison."""
    text = text.upper().strip()
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text


def _merge_ocr_results(all_results: list[list[dict]]) -> list[dict]:
    """Merge OCR results from multiple passes, deduplicating similar lines.

    For each group of duplicate lines, keeps the highest-confidence version.
    Returns lines sorted by vertical position (top to bottom).
    """
    if not all_results:
        return []

    all_lines = []
    for pass_idx, lines in enumerate(all_results):
        for line in lines:
            all_lines.append({**line, "pass": pass_idx})

    if not all_lines:
        return []

    # Group by normalized text
    from collections import defaultdict
    groups = defaultdict(list)
    for line in all_lines:
        norm = _normalize_text(line["text"])
        if len(norm) >= 3:
            groups[norm].append(line)
        else:
            groups[f"short_{line['text']}_{id(line)}"].append(line)

    # Keep highest-confidence line per group
    merged = []
    for group in groups.values():
        best = max(group, key=lambda x: x.get("confidence", 0))
        merged.append(best)

    # Sort by vertical position (y-coordinate of bbox center)
    def get_y_center(line):
        bbox = line.get("bbox", [[0, 0], [0, 0], [0, 0], [0, 0]])
        if bbox and len(bbox) >= 4:
            y_coords = [p[1] for p in bbox]
            return sum(y_coords) / len(y_coords)
        return 0

    merged.sort(key=get_y_center)

    # Clean up internal fields
    for line in merged:
        line.pop("bbox", None)
        line.pop("pass", None)

    return merged


def extract_text_sync(image_path: str, document_type: Optional[str] = None) -> dict:
    """Extract text from an image using EasyOCR with preprocessing.

    Runs OCR on 2 preprocessing variants (original + contrast-enhanced)
    and merges the best results.

    Args:
        image_path: Path to the image file.
        document_type: Optional document type hint.

    Returns:
        dict with keys:
            - success: bool
            - full_text: str
            - average_confidence: float or None
            - lines: list of dicts with 'text' and 'confidence'
            - preprocessing_applied: list of preprocessing steps used
            - passes_run: int
            - error: str or None
    """
    try:
        from app.services.image_preprocessing import create_preprocessing_variants, cleanup_temp_files

        # Step 1: Create preprocessing variants (2 variants: original + grayscale/contrast)
        preprocessing = create_preprocessing_variants(image_path, document_type)
        variants = preprocessing.get("variants", [])
        preprocessing_steps = preprocessing.get("preprocessing_applied", [])

        if not variants:
            # Fallback: run OCR on original image
            raw_lines = _run_ocr_on_image(image_path)
            lines = [{"text": l["text"], "confidence": l["confidence"]} for l in raw_lines]
        else:
            # Step 2: Run OCR on each variant
            all_results = []
            for variant in variants:
                variant_path = variant["path"]
                if os.path.exists(variant_path):
                    raw = _run_ocr_on_image(variant_path)
                    all_results.append(raw)
                    logger.debug(f"OCR pass '{variant['name']}': {len(raw)} detections")

            # Step 3: Merge and deduplicate
            merged = _merge_ocr_results(all_results)
            lines = [{"text": l["text"], "confidence": l["confidence"]} for l in merged]

            # Step 4: Cleanup temp files
            cleanup_temp_files(image_path)

        if not lines:
            return {
                "success": True,
                "full_text": "",
                "average_confidence": None,
                "lines": [],
                "preprocessing_applied": preprocessing_steps,
                "passes_run": len(variants) if variants else 1,
                "error": None,
            }

        # Build full text
        full_text = "\n".join(line["text"] for line in lines)

        # Calculate average confidence
        confidences = [line["confidence"] for line in lines if line["confidence"] is not None]
        avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else None

        return {
            "success": True,
            "full_text": full_text,
            "average_confidence": avg_confidence,
            "lines": lines,
            "preprocessing_applied": preprocessing_steps,
            "passes_run": len(variants) if variants else 1,
            "error": None,
        }

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return {
            "success": False,
            "full_text": "",
            "average_confidence": None,
            "lines": [],
            "preprocessing_applied": [],
            "passes_run": 0,
            "error": str(e),
        }


async def extract_text(image_path: str, document_type: Optional[str] = None) -> dict:
    """Async wrapper for OCR extraction."""
    return extract_text_sync(image_path, document_type)


async def get_extraction_confidence(image_path: str) -> dict:
    """Return confidence metrics for OCR extraction."""
    result = extract_text_sync(image_path)
    return {
        "success": result["success"],
        "overall_confidence": result["average_confidence"],
        "lines_detected": len(result["lines"]),
        "error": result["error"],
    }
