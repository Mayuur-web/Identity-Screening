"""Health check endpoint."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Return API health status."""
    return {
        "status": "healthy",
        "service": "Parakh Seva API",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
