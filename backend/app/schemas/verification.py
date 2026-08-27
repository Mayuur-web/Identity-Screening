"""Pydantic schemas for the verification workflow."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Overall verification status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    HIGH_RISK = "high_risk"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    ERROR = "error"


class RiskLevel(str, Enum):
    """Risk classification levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class BiometricResult(BaseModel):
    """Face matching / biometric comparison result."""
    face_detected: Optional[bool] = None
    face_quality: Optional[str] = None
    face_similarity: Optional[float] = None
    liveness_passed: Optional[bool] = None
    orientation: Optional[str] = None
    status: str = "not_implemented"


class TamperResult(BaseModel):
    """Document tampering analysis result."""
    structure_check: Optional[bool] = None
    text_consistency: Optional[bool] = None
    image_manipulation: Optional[bool] = None
    metadata_check: Optional[bool] = None
    required_fields: Optional[bool] = None
    status: str = "not_implemented"


class ConsistencyCheck(BaseModel):
    """Cross-field consistency check between document and submitted data."""
    field_name: str
    document_value: Optional[str] = None
    submitted_value: Optional[str] = None
    match: Optional[bool] = None
    status: str = "not_implemented"


class RiskAssessment(BaseModel):
    """Risk scoring and assessment."""
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    ai_confidence: Optional[float] = None
    signals: dict[str, Optional[str]] = {}
    explainable_findings: list[str] = []
    recommendation: Optional[str] = None
    status: str = "not_implemented"


class VerificationUploadRequest(BaseModel):
    """Request for identity verification upload."""
    document_type: Optional[str] = None


class VerificationUploadResponse(BaseModel):
    """Response after verification upload."""
    verification_id: str
    document_id: Optional[str] = None
    selfie_filename: Optional[str] = None
    status: VerificationStatus = VerificationStatus.PENDING
    message: str = "Verification initiated"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VerificationAnalysisRequest(BaseModel):
    """Request to trigger full verification analysis."""
    verification_id: str


class VerificationSummary(BaseModel):
    """Complete verification record."""
    verification_id: str
    document_id: Optional[str] = None
    status: VerificationStatus = VerificationStatus.PENDING
    document_type: Optional[str] = None
    applicant_name: Optional[str] = None

    # Sub-results (populated by AI services in later phases)
    ocr_result: Optional[dict] = None
    document_analysis: Optional[dict] = None
    biometric_result: Optional[BiometricResult] = None
    tamper_result: Optional[TamperResult] = None
    consistency_checks: list[ConsistencyCheck] = []
    risk_assessment: Optional[RiskAssessment] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VerificationDetailResponse(BaseModel):
    """Full detail response for GET /verification/{id}."""
    verification_id: str
    status: VerificationStatus
    document_type: Optional[str] = None
    risk_score: Optional[int] = None
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    face_similarity: Optional[float] = None
    ai_confidence: Optional[float] = None
    biometric: Optional[BiometricResult] = None
    tamper: Optional[TamperResult] = None
    consistency: list[ConsistencyCheck] = []
    risk: Optional[RiskAssessment] = None
    created_at: datetime
    updated_at: datetime
    message: str = "Verification data retrieved"
