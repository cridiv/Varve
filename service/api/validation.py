"""
FastAPI Router for Ground Truth Validation & Benchmark (C2)
"""

import sys
import os
from fastapi import APIRouter, HTTPException

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from services.validation_service import generate_validation_report

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/report")
def get_validation_report():
    """
    Auto-generates/refreshes docs/validation.md and returns the structured benchmark result JSON.
    """
    try:
        benchmark_res = generate_validation_report()
        return benchmark_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate validation report: {str(e)}")
