"""Document upload, analysis, OCR, and field extraction endpoints."""

import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.core.config import settings
from app.core.security import (
    generate_id,
    safe_filename,
    validate_file_extension,
    validate_file_size,
)
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentStatus,
)
from app.services import ocr_service
from app.services.database_service import save_verification_record
from app.services.field_extraction_service import (
    extract_fields,
    extract_passport_fields,
)
from app.services.mrz_service import (
    detect_mrz,
    extract_mrz_from_image,
)
from app.services.verification_service import verify_document, normalize_document_type, detect_document_type_from_ocr
from app.services.face_verification_service import verify_faces

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
):
    """Upload an identity document for verification."""

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided",
        )

    if not validate_file_extension(
        file.filename,
        settings.ALLOWED_EXTENSIONS,
    ):
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {allowed}",
        )

    content = await file.read()

    if not validate_file_size(
        len(content),
        settings.MAX_FILE_SIZE_MB,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large. "
                f"Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            ),
        )

    doc_id = generate_id(prefix="DOC")
    original_name = safe_filename(file.filename)
    stored_filename = f"{doc_id}_{original_name}"

    upload_path = os.path.join(
        settings.UPLOAD_DIR,
        stored_filename,
    )

    with open(upload_path, "wb") as f:
        f.write(content)

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=original_name,
        file_size=len(content),
        document_type=(
            document_type
            if document_type != "other"
            else None
        ),
        status=DocumentStatus.UPLOADED,
        message="Document uploaded successfully",
    )


@router.post("/ocr")
async def run_ocr(file: UploadFile = File(...)):
    """Run multi-pass EasyOCR on an uploaded image."""

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided",
        )

    if not validate_file_extension(
        file.filename,
        settings.ALLOWED_EXTENSIONS,
    ):
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {allowed}",
        )

    content = await file.read()

    if not validate_file_size(
        len(content),
        settings.MAX_FILE_SIZE_MB,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large. "
                f"Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            ),
        )

    doc_id = generate_id(prefix="OCR")
    original_name = safe_filename(file.filename)
    stored_filename = f"{doc_id}_{original_name}"

    upload_path = os.path.join(
        settings.UPLOAD_DIR,
        stored_filename,
    )

    with open(upload_path, "wb") as f:
        f.write(content)

    try:
        result = await ocr_service.extract_text(
            image_path=upload_path,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=(
                    "OCR processing failed: "
                    f"{result.get('error', 'Unknown error')}"
                ),
            )

        return {
            "success": True,
            "document_id": doc_id,
            "filename": original_name,
            "full_text": result["full_text"],
            "average_confidence": result["average_confidence"],
            "lines": result["lines"],
            "lines_count": len(result["lines"]),
        }

    finally:
        try:
            os.remove(upload_path)
        except OSError:
            pass


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
):
    """
    Run OCR + document-type-specific processing.

    Aadhaar:
        OCR → generic field extraction

    Passport:
        OCR → MRZ image extraction → passport field extraction
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided",
        )

    if not validate_file_extension(
        file.filename,
        settings.ALLOWED_EXTENSIONS,
    ):
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {allowed}",
        )

    content = await file.read()

    if not validate_file_size(
        len(content),
        settings.MAX_FILE_SIZE_MB,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large. "
                f"Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            ),
        )

    doc_id = generate_id(prefix="DOC")
    original_name = safe_filename(file.filename)
    stored_filename = f"{doc_id}_{original_name}"

    upload_path = os.path.join(
        settings.UPLOAD_DIR,
        stored_filename,
    )

    with open(upload_path, "wb") as f:
        f.write(content)

    try:
        raw_doc_type = (
            document_type
            if document_type not in ("other", "")
            else None
        )
        doc_type = normalize_document_type(raw_doc_type)

        logger.info(
            "Starting document analysis: id=%s raw_type=%s normalized=%s file=%s",
            doc_id,
            raw_doc_type,
            doc_type,
            original_name,
        )

        ocr_result = await ocr_service.extract_text(
            image_path=upload_path,
            document_type=doc_type,
        )

        if not ocr_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=(
                    "OCR processing failed: "
                    f"{ocr_result.get('error', 'Unknown error')}"
                ),
            )

        # Auto-detect document type from OCR text when not provided
        if doc_type is None:
            doc_type = detect_document_type_from_ocr(
                ocr_result["lines"]
            )
            if doc_type:
                logger.info(
                    "Auto-detected document type: %s for %s",
                    doc_type, doc_id,
                )

        mrz_data = None

        if doc_type == "passport":
            logger.info(
                "Running passport MRZ extraction for %s",
                doc_id,
            )

            mrz_data = extract_mrz_from_image(
                upload_path
            )

            if not mrz_data.get("detected"):
                logger.info(
                    "Image MRZ extraction failed; "
                    "trying OCR-line MRZ detection"
                )

                mrz_data = detect_mrz(
                    ocr_result["lines"]
                )

            logger.info(
                "Passport MRZ detected: %s",
                mrz_data.get("detected", False),
            )

            fields = extract_passport_fields(
                ocr_lines=ocr_result["lines"],
                mrz_data=mrz_data,
            )

        else:
            fields = extract_fields(
                ocr_lines=ocr_result["lines"],
                document_type=doc_type,
                mrz_data=None,
            )

        response = {
            "success": True,
            "document_id": doc_id,
            "filename": original_name,
            "document_type": doc_type,
            "ocr": {
                "full_text": ocr_result["full_text"],
                "average_confidence": (
                    ocr_result["average_confidence"]
                ),
                "lines": ocr_result["lines"],
                "lines_count": len(
                    ocr_result["lines"]
                ),
                "preprocessing_applied": (
                    ocr_result.get(
                        "preprocessing_applied",
                        [],
                    )
                ),
                "passes_run": ocr_result.get(
                    "passes_run",
                    1,
                ),
            },
            "mrz": mrz_data,
            "fields": fields,
        }

        logger.info(
            "Document analysis completed: id=%s type=%s",
            doc_id,
            doc_type,
        )

        return response

    finally:
        try:
            if os.path.exists(upload_path):
                os.remove(upload_path)

                logger.debug(
                    "Temporary upload removed: %s",
                    upload_path,
                )

        except OSError as exc:
            logger.warning(
                "Could not remove temporary upload %s: %s",
                upload_path,
                exc,
            )


@router.post("/verify")
async def verify_document_endpoint(
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    selfie: Optional[UploadFile] = File(default=None),
):
    """
    Run OCR + field extraction + verification.

    Optionally accepts a selfie for face verification.
    Also saves the verification result to Supabase.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided",
        )

    if not validate_file_extension(
        file.filename,
        settings.ALLOWED_EXTENSIONS,
    ):
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {allowed}",
        )

    content = await file.read()

    if not validate_file_size(
        len(content), settings.MAX_FILE_SIZE_MB,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large. "
                f"Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            ),
        )

    doc_id = generate_id(prefix="DOC")
    original_name = safe_filename(file.filename)
    stored_filename = f"{doc_id}_{original_name}"

    upload_path = os.path.join(
        settings.UPLOAD_DIR,
        stored_filename,
    )

    # Save selfie temporarily if provided
    selfie_path = None

    if selfie and selfie.filename:
        selfie_content = await selfie.read()
        if selfie_content and validate_file_size(
            len(selfie_content), settings.MAX_FILE_SIZE_MB,
        ):
            selfie_ext = os.path.splitext(selfie.filename)[1] or ".png"
            selfie_filename = f"{doc_id}_selfie{selfie_ext}"
            selfie_path = os.path.join(
                settings.UPLOAD_DIR, selfie_filename,
            )
            with open(selfie_path, "wb") as sf:
                sf.write(selfie_content)

    with open(upload_path, "wb") as f:
        f.write(content)

    try:
        # Normalize the document type from the frontend value.
        # "other" means the user did not pick a type — treat as None so
        # we can try auto-detection after OCR.
        raw_doc_type = (
            document_type
            if document_type not in ("other", "")
            else None
        )
        doc_type = normalize_document_type(raw_doc_type)

        logger.info(
            "Starting verification: id=%s raw_type=%s normalized=%s file=%s",
            doc_id,
            raw_doc_type,
            doc_type,
            original_name,
        )

        # OCR — pass the initial type hint for preprocessing
        t0 = time.time()
        ocr_result = await ocr_service.extract_text(
            image_path=upload_path,
            document_type=doc_type,
        )
        t1 = time.time()
        logger.info("[TIMING] OCR: %.2fs", t1 - t0)

        if not ocr_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=(
                    "OCR processing failed: "
                    f"{ocr_result.get('error', 'Unknown error')}"
                ),
            )

        # Auto-detect document type from OCR text when not provided
        if doc_type is None:
            doc_type = detect_document_type_from_ocr(
                ocr_result["lines"]
            )
            if doc_type:
                logger.info(
                    "Auto-detected document type: %s for %s",
                    doc_type, doc_id,
                )

        # Field extraction
        mrz_data = None

        if doc_type == "passport":
            t2 = time.time()
            mrz_data = extract_mrz_from_image(
                upload_path
            )
            t3 = time.time()
            logger.info("[TIMING] MRZ image extraction: %.2fs (detected=%s)", t3 - t2, mrz_data.get('detected'))

            if not mrz_data.get("detected"):
                t3b = time.time()
                mrz_data = detect_mrz(
                    ocr_result["lines"]
                )
                t4 = time.time()
                logger.info("[TIMING] MRZ text detection: %.2fs (detected=%s)", t4 - t3b, mrz_data.get('detected'))

            t5 = time.time()
            fields = extract_passport_fields(
                ocr_lines=ocr_result["lines"],
                mrz_data=mrz_data,
            )
            t6 = time.time()
            logger.info("[TIMING] Passport field extraction: %.2fs", t6 - t5)

        else:
            t2 = time.time()
            fields = extract_fields(
                ocr_lines=ocr_result["lines"],
                document_type=doc_type,
                mrz_data=None,
            )
            t3 = time.time()
            logger.info("[TIMING] Aadhaar field extraction: %.2fs", t3 - t2)

        # Verification
        ocr_meta = {
            "average_confidence": ocr_result.get(
                "average_confidence"
            ),
            "lines_count": len(
                ocr_result.get("lines", [])
            ),
        }

        t7 = time.time()
        verification = verify_document(
            fields=fields,
            ocr_data=ocr_meta,
            mrz_data=mrz_data,
            document_type=doc_type,
        )
        t8 = time.time()
        logger.info("[TIMING] Verification engine: %.2fs", t8 - t7)

        # --- Face verification (optional) ---
        face_verification = {
            "status": "NOT_PROVIDED",
            "similarity_score": None,
            "face_detected_in_document": False,
            "face_detected_in_selfie": False,
            "message": "Selfie not provided",
        }
        face_check_status = "not_checked"
        face_check_message = "Selfie not provided"

        if selfie_path and os.path.isfile(selfie_path):
            logger.info(
                "Running face verification for %s",
                doc_id,
            )
            fv = verify_faces(
                document_image_path=upload_path,
                selfie_image_path=selfie_path,
            )
            face_verification = {
                "status": fv["status"],
                "similarity_score": fv["similarity_score"],
                "face_detected_in_document": fv["face_detected_in_document"],
                "face_detected_in_selfie": fv["face_detected_in_selfie"],
                "message": fv["message"],
            }

            if fv["status"] == "MATCH":
                face_check_status = "passed"
                face_check_message = (
                    f"Faces match ({fv['similarity_score']}%)"
                )
            elif fv["status"] == "NO_MATCH":
                face_check_status = "failed"
                face_check_message = (
                    f"Faces do not match ({fv['similarity_score']}%)"
                )
            elif fv["status"] == "NO_FACE":
                face_check_status = "failed"
                face_check_message = fv["message"]
            else:
                # ERROR or other
                face_check_status = "failed"
                face_check_message = fv["message"]

            logger.info(
                "Face verification result: status=%s score=%s",
                fv["status"],
                fv["similarity_score"],
            )

        # Add face check to verification checks
        face_check = {
            "name": "Face Match",
            "status": face_check_status,
            "message": face_check_message,
        }
        verification["checks"].append(face_check)

        # Save verification result to Supabase
        logger.info(
            "Calling save_verification_record for %s",
            doc_id,
        )
        saved = save_verification_record(
            document_id=doc_id,
            document_type=doc_type,
            filename=original_name,
            verification_result=verification,
            extracted_fields=fields,
        )
        if saved:
            logger.info("Record saved successfully: %s", doc_id)
        else:
            logger.warning(
                "Record NOT saved (Supabase unavailable or insert failed): %s",
                doc_id,
            )

        # Response
        response = {
            "success": True,
            "document_id": doc_id,
            "document_type": doc_type,
            "status": verification["status"],
            "score": verification["score"],
            "checks": verification["checks"],
            "reasons": verification["reasons"],
            "fields": fields,
            "mrz": mrz_data,
            "face_verification": face_verification,
            "ocr": {
                "full_text": ocr_result["full_text"],
                "average_confidence": (
                    ocr_result["average_confidence"]
                ),
                "lines": ocr_result["lines"],
                "lines_count": len(
                    ocr_result["lines"]
                ),
            },
        }

        logger.info(
            "Verification completed: id=%s type=%s status=%s score=%s",
            doc_id,
            doc_type,
            verification["status"],
            verification["score"],
        )

        return response

    finally:
        # Clean up temporary files
        for path in (upload_path, selfie_path):
            if path:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError as exc:
                    logger.warning(
                        "Could not remove temporary file %s: %s",
                        path, exc,
                    )