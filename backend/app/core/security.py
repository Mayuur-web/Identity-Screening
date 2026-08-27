"""Security utilities for Parakh Seva backend."""

import uuid
import re
from pathlib import Path


def generate_id(prefix: str = "VS") -> str:
    """Generate a unique verification/document ID.

    Format: PREFIX-XXXXXXXX (8-char hex segment).
    Example: VS-A3F2B1C9
    """
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{short_uuid}"


def safe_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and injection.

    - Strips directory components.
    - Allows only alphanumeric, hyphens, underscores, and dots.
    - Preserves the original extension.
    """
    # Strip any directory path
    name = Path(filename).name

    # Split name and extension
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()

    # Sanitize stem: keep only safe characters
    safe_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem)

    # Ensure we have something
    if not safe_stem:
        safe_stem = "file"

    return f"{safe_stem}{suffix}"


def validate_file_extension(filename: str, allowed: set[str]) -> bool:
    """Check if the file extension is in the allowed set."""
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in allowed


def validate_file_size(size_bytes: int, max_mb: int) -> bool:
    """Check if the file size is within the allowed limit."""
    max_bytes = max_mb * 1024 * 1024
    return size_bytes <= max_bytes
