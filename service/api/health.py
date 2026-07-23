"""
FastAPI router for system health check endpoint.
"""

from fastapi import APIRouter
from config.config import MODEL_NAME, DATAHUB_GMS_URL

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "model_name": MODEL_NAME,
        "datahub_gms_url": DATAHUB_GMS_URL,
    }
