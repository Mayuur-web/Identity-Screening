"""Face Verification Service — placeholder for biometric face matching.

This module will compare a document photo against a live selfie
for identity verification. Currently returns not_implemented status.
"""

from typing import Optional


async def compare_faces(
    document_image_path: str,
    selfie_image_path: str,
) -> dict:
    """Compare a document photo with a live selfie.

    Returns a dict with status "not_implemented" until the real
    face recognition pipeline is built.
    """
    return {
        "status": "not_implemented",
        "message": "Face comparison has not been implemented yet",
        "face_detected": None,
        "face_quality": None,
        "similarity_score": None,
        "liveness_passed": None,
        "orientation": None,
    }


async def detect_liveness(selfie_image_path: str) -> dict:
    """Perform liveness detection on a selfie image.

    Returns not_implemented until the real liveness detection is ready.
    """
    return {
        "status": "not_implemented",
        "message": "Liveness detection has not been implemented yet",
        "liveness_passed": None,
        "spoofing_detected": None,
    }
