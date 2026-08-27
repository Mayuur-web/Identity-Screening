"""Risk Assessment Service — placeholder for the AI risk scoring engine.

This module will aggregate results from OCR, document analysis,
face matching, and tamper detection to produce a final risk score
and decision. Currently returns not_implemented status.
"""

from typing import Optional


async def assess_risk(verification_data: dict) -> dict:
    """Compute an overall risk score for a verification attempt.

    Returns a dict with status "not_implemented" until the real
    risk engine is built.
    """
    return {
        "status": "not_implemented",
        "message": "Risk assessment has not been implemented yet",
        "risk_score": None,
        "risk_level": "unknown",
        "ai_confidence": None,
        "signals": {},
        "explainable_findings": [],
        "recommendation": None,
        "final_decision": None,
    }


async def get_signal_breakdown(verification_data: dict) -> dict:
    """Return individual signal scores for explainability.

    Returns not_implemented until the real risk engine is ready.
    """
    return {
        "status": "not_implemented",
        "message": "Signal breakdown has not been implemented yet",
        "signals": {
            "document_authenticity": None,
            "ocr_confidence": None,
            "face_match": None,
            "data_consistency": None,
            "tampering_risk": None,
            "liveness": None,
        },
    }
