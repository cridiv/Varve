# Varve — Walkthrough & Build Summary

**Project:** AI Risk & Decision Intelligence Platform for production data pipelines  
**Backend:** Python 3.11, FastAPI, PostgreSQL 15 (Docker), `acryl-datahub`  
**LLM:** `stepfun-ai/step-3.7-flash` via NVIDIA API  
**DataHub:** Local GMS at `http://localhost:8080` (showcase-ecommerce sample)

---

## Modular Backend Architecture Refactoring (Completed)

The backend code under `service/` has been structured into domain-driven Python packages:

```
service/
├── config/
│   ├── __init__.py
│   └── config.py               # Settings & ENV handling
├── db/
│   ├── __init__.py
│   ├── connection.py           # Shared PostgreSQL connection manager
│   ├── schema.sql              # DDL schema definitions
│   └── seed.sql                # Ground truth seed narratives 1-4
├── services/                   # Core business logic domain
│   ├── __init__.py
│   ├── correlation_service.py  # Correlation engine, cross-model checks & pattern rollups
│   ├── generator_service.py    # LLM narrative synthesis (StepFun AI) & findings table population
│   └── datahub_service.py      # DataHub GMS REST write-back & aspect verification
├── api/                        # FastAPI modular routers
│   ├── __init__.py
│   ├── health.py               # GET /health
│   ├── findings.py             # GET /models/risk-ranking, GET /findings/{id}, POST /findings/{id}/writeback
│   └── patterns.py             # GET /patterns/by-actor/{actor}
├── main.py                     # Entry point mounting health_router, findings_router, patterns_router
├── correlation.py              # Backward-compatibility adapter
├── generator.py                # Backward-compatibility adapter
├── datahub_writeback.py        # Backward-compatibility adapter
└── test/                       # Test suite
    ├── test_api.py
    └── test_datahub.py
```

---

## Tier 1 — Core Loop (Complete & Verified)

### 1. PostgreSQL Schema & DB Connection
- Pinned to `service/db/connection.py` with `RealDictCursor`.
- Schema defines `lineage_events`, `business_metrics`, `incidents`, `findings`, and `patterns`.

### 2. Ground Truth Seed Narratives
- Defined in `service/seed-narrative.md` and seeded in `service/db/seed.sql`:
  - **Story 1 (J. Alvarez / customers)**: Validated HIGH severity incident (11-day detection lag, -14.4% accuracy drop).
  - **Story 2 (R. Chen / products)**: Unvalidated LOW severity control group.
  - **Story 3 (J. Alvarez / addresses $\rightarrow$ order_items)**: Cross-model incident precedent.
  - **Story 4 (M. Santos / countries)**: Provisional HIGH severity downgraded to LOW (zero precedent anywhere).

### 3. DataHub Write-Back & API Integration
- `POST /findings/{finding_id}/writeback` emits `InstitutionalMemoryClass` aspects onto DataHub GMS.
- Direct read-back verification confirmed live on DataHub.

---

## Verification Results

### 1. Ground Truth & Correlation Verification
```text
=======================================================
   VARVE CORRELATION SERVICE — GROUND TRUTH VERIFICATION
=======================================================
Total seeded events evaluated: 5

addresses   J. Alvarez  departed=True  Provisional=HIGH   Final=HIGH    validated=True   cross_model=True
order_items J. Alvarez  departed=True  Provisional=MEDIUM Final=MEDIUM  validated=True   cross_model=True
customers   J. Alvarez  departed=True  Provisional=HIGH   Final=HIGH    validated=True   cross_model=True
products    R. Chen     departed=False Provisional=MEDIUM Final=LOW     validated=False  cross_model=False
countries   M. Santos   departed=False Provisional=HIGH   Final=LOW     validated=False  cross_model=False

✅ ALL GROUND TRUTH ASSERTIONS PASSED — Cross-model + downgrade logic verified!
✅ Patterns table upserted with 9 scope rows.
```

### 2. REST API & DataHub Write-Back Verification
```text
=======================================================
   TESTING FASTAPI REST ENDPOINTS (Step 7.3)
=======================================================

► GET /health -> Status 200
► GET /models/risk-ranking -> Status 200
► GET /findings/f462a38b-4156-4467-a7f7-3ffecd4ae5fd -> Status 200
► Emitting MetadataChangeProposal to DataHub for URN: urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)...
✅ Write-back successful! Updated written_back_at timestamp in database.
✅ CONFIRMED ON DATAHUB SIDE: Found 1 documentation annotation(s)
► POST /findings/f462a38b-4156-4467-a7f7-3ffecd4ae5fd/writeback -> Status 200

✅ STEP 7 & STEP 9 COMPLETE: All REST & Write-Back endpoints verified!
```
