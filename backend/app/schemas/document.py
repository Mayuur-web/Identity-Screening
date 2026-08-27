"""Pydantic schemas for document-related data."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported document types."""
    AADHAAR = "aadhaar"
    PAN = "pan"
    PASSPORT = "passport"
    DRIVING_LICENCE = "driving_licence"
    VOTER_ID = "voter_id"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    ERROR = "error"


class OCRField(BaseModel):
    """A single extracted OCR field with its value and confidence."""
    field_name: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: str = "not_implemented"  # "verified" | "warning" | "not_implemented"


class DocumentUploadResponse(BaseModel):
    """Response after successful document upload."""
    document_id: str
    filename: str
    file_size: int
    document_type: Optional[DocumentType] = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    message: str = "Document uploaded successfully"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentAnalysisRequest(BaseModel):
    """Request body for document analysis."""
    document_id: str
    document_type: Optional[DocumentType] = None


class DocumentIntegrityCheck(BaseModel):
    """Result of a single integrity check."""
    check_name: str
    passed: Optional[bool] = None
    status: str = "not_implemented"


class DocumentAnalysisResponse(BaseModel):
    """Response from document analysis."""
    document_id: str
    status: str = "not_implemented"
    ocr_fields: list[OCRField] = []
    integrity_checks: list[DocumentIntegrityCheck] = []
    authenticity_score: Optional[int] = None
    image_manipulation_detected: Optional[bool] = None
    message: str = "Document analysis not yet implemented"
