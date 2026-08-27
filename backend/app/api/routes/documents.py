"""Document upload, analysis, OCR, and field extraction endpoints."""

import logging
import os

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
from app.services.field_extraction_service import (
    extract_fields,
    extract_passport_fields,
)
from app.services.mrz_service import (
    detect_mrz,
    extract_mrz_from_image,
)
from app.services.verification_service import verify_document

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
        # Always remove temporary OCR upload
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

    The uploaded image is kept until ALL processing is complete.
    """

    # ---------------------------------------------------------
    # 1. Validate file
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 2. Save image
    # ---------------------------------------------------------

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
        # -----------------------------------------------------
        # 3. Run OCR
        # -----------------------------------------------------

        doc_type = (
            document_type
            if document_type != "other"
            else None
        )

        logger.info(
            "Starting document analysis: id=%s type=%s file=%s",
            doc_id,
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

        # -----------------------------------------------------
        # 4. Document-type-specific processing
        # -----------------------------------------------------

        mrz_data = None

        if doc_type == "passport":

            logger.info(
                "Running passport MRZ extraction for %s",
                doc_id,
            )

            # IMPORTANT:
            # The image still exists here.
            # extract_mrz_from_image() needs the actual image.
            mrz_data = extract_mrz_from_image(
                upload_path
            )

            # Fallback to MRZ detection from OCR lines
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

            # Passport-specific extraction
            fields = extract_passport_fields(
                ocr_lines=ocr_result["lines"],
                mrz_data=mrz_data,
            )

        else:

            # -------------------------------------------------
            # Aadhaar / other documents
            # -------------------------------------------------

            logger.info(
                "Running generic field extraction for %s",
                doc_id,
            )

            fields = extract_fields(
                ocr_lines=ocr_result["lines"],
                document_type=doc_type,
                mrz_data=None,
            )

        # -----------------------------------------------------
        # 5. Build response
        # -----------------------------------------------------

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
        # -----------------------------------------------------
        # 6. Cleanup AFTER all processing
        # -----------------------------------------------------
        #
        # This is intentionally at the end.
        # Passport MRZ extraction must have access to the
        # original image before it is deleted.
        #
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
):
    """
    Run OCR + field extraction + verification in one step.

    Returns verification status, score, and detailed checks.
    """

    # ---------------------------------------------------------
    # 1. Validate file
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 2. Save image
    # ---------------------------------------------------------

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
        # -----------------------------------------------------
        # 3. Run OCR
        # -----------------------------------------------------

        doc_type = (
            document_type
            if document_type != "other"
            else None
        )

        logger.info(
            "Starting verification: id=%s type=%s file=%s",
            doc_id,
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

        # -----------------------------------------------------
        # 4. Document-type-specific extraction
        # -----------------------------------------------------

        mrz_data = None

        if doc_type == "passport":
            mrz_data = extract_mrz_from_image(
                upload_path
            )
            if not mrz_data.get("detected"):
                mrz_data = detect_mrz(
                    ocr_result["lines"]
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

        # -----------------------------------------------------
        # 5. Run verification engine
        # -----------------------------------------------------

        ocr_meta = {
            "average_confidence": ocr_result.get(
                "average_confidence"
            ),
            "lines_count": len(ocr_result.get("lines", [])),
        }

        verification = verify_document(
            fields=fields,
            ocr_data=ocr_meta,
            mrz_data=mrz_data,
            document_type=doc_type,
        )

        # -----------------------------------------------------
        # 6. Build response
        # -----------------------------------------------------

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
        try:
            if os.path.exists(upload_path):
                os.remove(upload_path)
        except OSError:
            pass