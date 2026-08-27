"""Verification workflow endpoints."""

import os
from datetime import datetime
from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.core.config import settings
from app.core.security import generate_id, safe_filename, validate_file_extension, validate_file_size
from app.schemas.verification import (
    VerificationUploadResponse,
    VerificationDetailResponse,
    VerificationStatus,
    RiskLevel,
)
from app.services import ocr_service, document_service, face_service, tamper_service, risk_service

router = APIRouter(prefix="/verification", tags=["verification"])

# In-memory storage for verification records (foundation; DB will replace this)
verification_store: dict[str, dict] = {}


@router.post("/upload", response_model=VerificationUploadResponse)
async def upload_verification(
    document: UploadFile = File(...),
    selfie: UploadFile = File(default=None),
    document_type: str = Form(default="other"),
):
    """Upload a document (and optional selfie) to start a new verification.

    Returns a unique verification ID to track the full workflow.
    """
    # Validate document file
    if not document.filename:
        raise HTTPException(status_code=400, detail="No document file provided")

    if not validate_file_extension(document.filename, settings.ALLOWED_EXTENSIONS):
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Document file type not supported. Allowed: {allowed}",
        )

    doc_content = await document.read()
    if not validate_file_size(len(doc_content), settings.MAX_FILE_SIZE_MB):
        raise HTTPException(
            status_code=400,
            detail=f"Document too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Validate selfie if provided
    selfie_filename = None
    if selfie and selfie.filename:
        if not validate_file_extension(selfie.filename, settings.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail=f"Selfie file type not supported. Allowed: {allowed}",
            )
        selfie_content = await selfie.read()
        if not validate_file_size(len(selfie_content), settings.MAX_FILE_SIZE_MB):
            raise HTTPException(
                status_code=400,
                detail=f"Selfie too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB",
            )

        # Save selfie
        verification_id = generate_id(prefix="VS")
        selfie_safe = safe_filename(selfie.filename)
        selfie_stored = f"{verification_id}_selfie_{selfie_safe}"
        import os
        selfie_path = os.path.join(settings.UPLOAD_DIR, selfie_stored)
        with open(selfie_path, "wb") as f:
            f.write(selfie_content)
        selfie_filename = selfie_safe

    else:
        verification_id = generate_id(prefix="VS")

    # Save document
    doc_id = generate_id(prefix="DOC")
    doc_safe = safe_filename(document.filename)
    doc_stored = f"{verification_id}_{doc_safe}"
    import os
    doc_path = os.path.join(settings.UPLOAD_DIR, doc_stored)
    with open(doc_path, "wb") as f:
        f.write(doc_content)

    # Create verification record in memory
    now = datetime.utcnow()
    verification_store[verification_id] = {
        "verification_id": verification_id,
        "document_id": doc_id,
        "document_type": document_type,
        "document_filename": doc_safe,
        "selfie_filename": selfie_filename,
        "status": VerificationStatus.PENDING.value,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "ocr_result": None,
        "document_analysis": None,
        "biometric_result": None,
        "tamper_result": None,
        "consistency_checks": [],
        "risk_assessment": None,
    }

    return VerificationUploadResponse(
        verification_id=verification_id,
        document_id=doc_id,
        selfie_filename=selfie_filename,
        status=VerificationStatus.PENDING,
        message="Verification initiated. Upload complete.",
    )


@router.post("/analyze")
async def analyze_verification(request: dict):
    """Trigger full verification analysis pipeline.

    Orchestrates OCR, document analysis, face matching, tamper detection,
    consistency checks, and risk assessment. Currently returns
    not_implemented for all AI services.
    """
    verification_id = request.get("verification_id")
    if not verification_id:
        raise HTTPException(status_code=400, detail="verification_id is required")

    record = verification_store.get(verification_id)
    if not record:
        raise HTTPException(status_code=404, detail="Verification not found")

    # Update status
    record["status"] = VerificationStatus.IN_PROGRESS.value
    record["updated_at"] = datetime.utcnow().isoformat()

    # Get document path for OCR
    doc_path = os.path.join(settings.UPLOAD_DIR, record.get("document_filename", ""))

    # Run all services (only OCR is implemented; rest return not_implemented)
    if os.path.exists(doc_path):
        ocr_result = await ocr_service.extract_text(doc_path)
    else:
        ocr_result = await ocr_service.extract_text(doc_path)  # will return error
    doc_result = await document_service.analyze_document(doc_path)
    biometric_result = await face_service.compare_faces("", "")
    tamper_result = await tamper_service.analyze_tampering("")
    risk_result = await risk_service.assess_risk({})

    # Store results
    record["ocr_result"] = ocr_result
    record["document_analysis"] = doc_result
    record["biometric_result"] = biometric_result
    record["tamper_result"] = tamper_result
    record["risk_assessment"] = risk_result
    record["status"] = VerificationStatus.MANUAL_REVIEW.value
    record["updated_at"] = datetime.utcnow().isoformat()

    return {
        "verification_id": verification_id,
        "status": record["status"],
        "message": "Analysis pipeline executed. AI services are not yet implemented.",
        "ocr": ocr_result,
        "document": doc_result,
        "biometric": biometric_result,
        "tamper": tamper_result,
        "risk": risk_result,
    }


@router.get("/{verification_id}")
async def get_verification(verification_id: str):
    """Retrieve the full details of a verification record."""
    record = verification_store.get(verification_id)
    if not record:
        raise HTTPException(status_code=404, detail="Verification not found")

    return VerificationDetailResponse(
        verification_id=record["verification_id"],
        status=VerificationStatus(record["status"]),
        document_type=record.get("document_type"),
        risk_score=None,
        risk_level=RiskLevel.UNKNOWN,
        face_similarity=None,
        ai_confidence=None,
        biometric=None,
        tamper=None,
        consistency=[],
        risk=None,
        created_at=record["created_at"],
        updated_at=record["updated_at"],
        message="Verification record retrieved. AI results pending implementation.",
    )
