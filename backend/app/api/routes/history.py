"""Verification history endpoints."""

import json
from datetime import datetime, date

from fastapi import APIRouter, HTTPException

from app.services.database_service import get_verification_history

router = APIRouter(prefix="/history", tags=["history"])


def _sanitize_record(record: dict) -> dict:
    """Ensure all values are JSON-serializable."""
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, (datetime, date)):
            cleaned[key] = value.isoformat()
        elif isinstance(value, (dict, list)):
            cleaned[key] = json.loads(json.dumps(value, default=str))
        else:
            cleaned[key] = value
    return cleaned


@router.get("")
async def verification_history(limit: int = 100):
    """Return recent verification records."""

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100",
        )

    try:
        records = get_verification_history(limit=limit)
        sanitized = [_sanitize_record(r) for r in records]

        return {
            "success": True,
            "count": len(sanitized),
            "records": sanitized,
        }

    except Exception as exc:
        # Return empty list instead of 500 — history is non-critical
        return {
            "success": True,
            "count": 0,
            "records": [],
        }