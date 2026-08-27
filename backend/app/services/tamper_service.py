"""Tamper Detection Service — placeholder for document tampering analysis.

This module will analyze uploaded documents for signs of forgery,
digital alteration, and structural anomalies. Currently returns
not_implemented status.
"""

from typing import Optional


async def analyze_tampering(document_path: str) -> dict:
    """Analyze a document for signs of tampering.

    Returns a dict with status "not_implemented" until the real
    tamper detection pipeline is built.
    """
    return {
        "status": "not_implemented",
        "message": "Tamper detection has not been implemented yet",
        "structure_check": None,
        "text_consistency": None,
        "image_manipulation": None,
        "metadata_check": None,
        "required_fields": None,
        "anomalies": [],
    }


async def check_hologram(document_path: str) -> dict:
    """Analyze holographic security features on the document.

    Returns not_implemented until the real hologram analysis is ready.
    """
    return {
        "status": "not_implemented",
        "message": "Hologram analysis has not been implemented yet",
        "hologram_present": None,
        "pattern_valid": None,
    }
