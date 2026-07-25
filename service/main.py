"""
Varve FastAPI Application — Main Entry Point

Mounts API routers:
- health_router: GET /health
- findings_router: GET /models/risk-ranking, GET /findings/{finding_id}, POST /findings/{finding_id}/writeback
- patterns_router: GET /patterns/by-actor/{actor}
"""

import sys
import os

service_dir = os.path.dirname(os.path.abspath(__file__))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.config import validate_config
from api import health_router, findings_router, patterns_router, ledger_router, validation_router
from services.validation_service import generate_validation_report

app = FastAPI(title="Varve AI API", version="0.2.0")

# Enable CORS for React frontend (Vite default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include modular API routers
app.include_router(health_router)
app.include_router(findings_router)
app.include_router(patterns_router)
app.include_router(ledger_router)
app.include_router(validation_router)


@app.on_event("startup")
def on_startup():
    try:
        validate_config()
    except Exception as e:
        print(f"[warning] Config validation warning: {e}")

    try:
        print("[startup] Auto-generating validation report and verifying benchmark...")
        generate_validation_report()
    except Exception as e:
        print(f"[warning] Validation report auto-generation skipped: {e}")