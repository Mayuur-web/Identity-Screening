"""Verification history endpoints."""

import json
import logging
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Path

from app.services.database_service import get_verification_history, delete_verification_record

logger = logging.getLogger(__name__)

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
        logger.error("History endpoint error: %s: %s", type(exc).__name__, exc, exc_info=True)
        # Return empty list instead of 500 — history is non-critical
        return {
            "success": True,
            "count": 0,
            "records": [],
        }


@router.delete("/{document_id}")
async def delete_verification(document_id: str = Path(..., description="Document ID to delete")):
    """Delete an individual verification record by document_id."""

    result = delete_verification_record(document_id)

    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "deleted": result["deleted"],
        }

    if "No record found" in result["message"]:
        raise HTTPException(status_code=404, detail=result["message"])

    raise HTTPException(status_code=500, detail=result["message"])