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
from api import health_router, findings_router, patterns_router, ledger_router, validation_router, candidates_router, alerts_router
from services.validation_service import generate_validation_report

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        validate_config()
    except Exception as e:
        print(f"[warning] Config validation warning: {e}")

    try:
        print("[startup] Auto-generating validation report and verifying benchmark...")
        generate_validation_report()
    except Exception as e:
        print(f"[warning] Validation report auto-generation skipped: {e}")
    yield


app = FastAPI(title="Varve AI API", version="0.2.0", lifespan=lifespan)

# Enable CORS for Next.js frontend (default port 3000)
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
app.include_router(candidates_router)
app.include_router(alerts_router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)