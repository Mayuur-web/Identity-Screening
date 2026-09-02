"""Supabase database service for Parakh Seva."""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env from the backend/ directory (same logic as config.py)
_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")

logger = logging.getLogger(__name__)

_supabase: Client | None = None


def get_supabase() -> Client | None:
    """Return the Supabase client, or None if not configured."""
    global _supabase

    if _supabase is not None:
        return _supabase

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        logger.warning("Supabase environment variables are not configured")
        return None

    try:
        _supabase = create_client(url, key)
        return _supabase
    except Exception:
        logger.exception("Failed to initialize Supabase client")
        return None


def save_verification_record(
    document_id: str | None,
    document_type: str,
    filename: str | None,
    verification_result: dict,
    extracted_fields: dict | None = None,
) -> dict | None:
    """Save a verification result to Supabase."""

    logger.info("Saving verification record...")
    logger.info("  document_id=%s", document_id)
    logger.info("  document_type=%s", document_type)
    logger.info("  filename=%s", filename)
    logger.info("  status=%s", verification_result.get("status"))
    logger.info("  score=%s", verification_result.get("score"))

    supabase = get_supabase()

    if supabase is None:
        logger.warning(
            "Verification record NOT saved: Supabase client is None. "
            "Check SUPABASE_URL and SUPABASE_KEY environment variables."
        )
        return None

    record = {
        "document_id": document_id,
        "document_type": document_type,
        "filename": filename,
        "status": verification_result.get("status"),
        "score": verification_result.get("score"),
        "extracted_fields": extracted_fields or verification_result.get("fields", {}),
        "checks": verification_result.get("checks", []),
        "reasons": verification_result.get("reasons", []),
    }

    try:
        logger.info("Inserting record into verification_records table...")
        response = (
            supabase
            .table("verification_records")
            .insert(record)
            .execute()
        )

        logger.info(
            "Verification record SAVED to Supabase: %s",
            document_id,
        )

        if response.data:
            return response.data[0]

        logger.warning("Supabase insert returned no data for %s", document_id)
        return None

    except Exception as exc:
        logger.error(
            "Failed to save verification record %s: %s: %s",
            document_id,
            type(exc).__name__,
            exc,
        )
        return None
        
def get_verification_history(limit: int = 50):
    """Fetch recent verification records from Supabase."""

    supabase = get_supabase()

    if supabase is None:
        logger.warning("Cannot fetch history: Supabase unavailable")
        return []

    try:
        logger.info("Fetching verification history (limit=%d)...", limit)
        response = (
            supabase
            .table("verification_records")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        logger.info("History query returned %d records", len(response.data) if response.data else 0)
        return response.data or []

    except Exception:
        logger.exception("Failed to fetch verification history")
        return []


def delete_verification_record(document_id: str) -> dict:
    """Delete a verification record by document_id.

    Returns {"success": bool, "message": str, "deleted": int}.
    """
    supabase = get_supabase()

    if supabase is None:
        logger.warning("Cannot delete record: Supabase unavailable")
        return {"success": False, "message": "Supabase unavailable", "deleted": 0}

    try:
        response = (
            supabase
            .table("verification_records")
            .delete()
            .eq("document_id", document_id)
            .execute()
        )

        deleted_count = len(response.data) if response.data else 0

        if deleted_count > 0:
            logger.info(
                "Deleted verification record %s (%d row(s))",
                document_id, deleted_count,
            )
            return {
                "success": True,
                "message": f"Record {document_id} deleted",
                "deleted": deleted_count,
            }

        logger.warning(
            "No record found to delete for document_id=%s", document_id
        )
        return {
            "success": False,
            "message": f"No record found for {document_id}",
            "deleted": 0,
        }

    except Exception as exc:
        logger.error(
            "Failed to delete verification record %s: %s: %s",
            document_id,
            type(exc).__name__,
            exc,
        )
        return {
            "success": False,
            "message": str(exc),
            "deleted": 0,
        }