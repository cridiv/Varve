# Varve — Walkthrough & Build Summary

**Project:** AI Risk & Decision Intelligence Platform for production data pipelines  
**Backend:** Python 3.11, FastAPI, PostgreSQL 16 (Docker), `acryl-datahub`  
**LLM:** `stepfun-ai/step-3.7-flash` via NVIDIA API  
**DataHub:** Local GMS at `http://localhost:8080` (showcase-ecommerce sample)

---

## Modular Backend Architecture

The backend code under `service/` is structured into domain-driven Python packages:

```text
service/
├── config/
│   ├── __init__.py
│   └── config.py                 # Settings & ENV handling
├── db/
│   ├── __init__.py
│   ├── connection.py             # Shared PostgreSQL connection manager (RealDictCursor)
│   ├── schema.sql                # DDL schema definitions (lineage_events, business_metrics, incidents, findings, patterns, ledger)
│   └── seed.sql                  # Ground truth seed narratives 1-4
├── services/                     # Core business logic domain
│   ├── __init__.py
│   ├── correlation_service.py    # Correlation engine, cross-model checks & structured benchmark
│   ├── generator_service.py      # LLM narrative synthesis (StepFun AI) & findings population
│   ├── datahub_service.py        # DataHub GMS REST write-back & aspect verification
│   ├── ledger_service.py         # Cryptographic SHA-256 hash-chained audit ledger engine
│   └── validation_service.py    # Automatic validation report generator for docs/validation.md
├── api/                          # FastAPI modular routers
│   ├── __init__.py
│   ├── health.py                 # GET /health
│   ├── findings.py               # GET /models/risk-ranking, GET /findings/{id}, POST /findings/{id}/writeback
│   ├── patterns.py               # GET /patterns/by-actor/{actor}
│   ├── ledger.py                 # GET /ledger/verify (audit chain integrity check)
│   └── validation.py             # GET /validation/report (on-demand benchmark & doc update)
├── scripts/                      # Executable CLI tools
│   ├── verify_ledger.py         # Terminal verifier for ledger hash chain integrity
│   └── generate_validation_report.py # Terminal benchmark generator
├── main.py                       # Entry point mounting routers & auto-benchmark startup hook
├── correlation.py                # Backward-compatibility adapter
├── generator.py                  # Backward-compatibility adapter
└── datahub_writeback.py          # Backward-compatibility adapter
```

---

## Completed Phases & Capabilities

### Tier 1 — Core Correlation & DataHub Write-Back
- **Schema & Connection**: PostgreSQL connection manager with `RealDictCursor`.
- **Ground Truth Seed**: 4 distinct narratives covering single-model incidents, cross-model actor correlations, and unvalidated control group downgrades.
- **DataHub Write-Back**: `POST /findings/{id}/writeback` emitting `InstitutionalMemoryClass` aspects to DataHub GMS.

### Phase B — Audit Ledger Capability (New)
- **Database Schema**: `ledger` table in PostgreSQL (`ledger_id`, `event_type`, `finding_id`, `payload`, `prev_hash`, `this_hash`, `created_at`).
- **Cryptographic Hash Chain**: SHA-256 linking of decision events (`finding_created`, `severity_set`, `downgrade`, `writeback`).
- **Independent Verification**: `service/scripts/verify_ledger.py` and `GET /ledger/verify` endpoint sequentially recomputing hashes and validating zero tamper state.
- **Tamper Resistance Proof**: Deliberate PostgreSQL payload modification tested; verifier instantly pinpoints exact corrupted row index and returns exit code 1.

### Phase C — Structured Benchmark & Automatic Validation (New)
- **Structured Benchmark**: `run_ground_truth_check()` refactored to return structured JSON containing summary (`total`, `passed`, `failed`, `all_passed`) and per-event expected vs. actual comparisons.
- **Automated Validation Report**: `generate_validation_report()` auto-writes [`docs/validation.md`](file:///Users/Cridiv/Documents/Varve/docs/validation.md) on backend startup (`main.py`) and via `GET /validation/report`.
- **Validation Scope**: 5/5 seeded scenarios classified correctly, including 1 correct downgrade from provisional-high to validated-low with zero false positives.

---

## Verification Results

### 1. Ground Truth Benchmark (`python service/correlation.py`)
```text
=======================================================
   VARVE CORRELATION SERVICE — GROUND TRUTH BENCHMARK
=======================================================
Total seeded events evaluated: 5

► [✔ PASS] Model: addresses    | Actor: J. Alvarez  
  Severity:  expected=HIGH   | actual=HIGH  
  Validated: expected=True   | actual=True  

► [✔ PASS] Model: order_items  | Actor: J. Alvarez  
  Severity:  expected=MEDIUM | actual=MEDIUM
  Validated: expected=True   | actual=True  

► [✔ PASS] Model: customers    | Actor: J. Alvarez  
  Severity:  expected=HIGH   | actual=HIGH  
  Validated: expected=True   | actual=True  

► [✔ PASS] Model: products     | Actor: R. Chen     
  Severity:  expected=LOW    | actual=LOW   
  Validated: expected=False  | actual=False 

► [✔ PASS] Model: countries    | Actor: M. Santos   
  Severity:  expected=LOW    | actual=LOW   
  Validated: expected=False  | actual=False 

✅ GROUND TRUTH BENCHMARK PASSED: 5/5 events matched expectations.
```

### 2. Audit Ledger Chain Verification (`python service/scripts/verify_ledger.py`)
```text
=======================================================
      VARVE AUDIT LEDGER — HASH CHAIN VERIFIER         
=======================================================

Verifying 21 ledger entries sequentially...

✔ [PASS] Row 01 | Event: finding_created    | Finding: bfd5bb19... | this_hash: adb51d93a3ec... | prev_hash: None
✔ [PASS] Row 02 | Event: severity_set       | Finding: bfd5bb19... | this_hash: b6e663654d43... | prev_hash: adb51d93a3ec...
...
✔ [PASS] Row 20 | Event: severity_set       | Finding: 965c9c9f... | this_hash: 25aab1653db5... | prev_hash: 271236dfbd8f...
✔ [PASS] Row 21 | Event: downgrade          | Finding: 965c9c9f... | this_hash: 85705b0d64c8... | prev_hash: 25aab1653db5...

-------------------------------------------------------
✔ 21/21 ledger entries verified, chain intact.
  Zero tampering detected. All decision records are mathematically authentic.
```

### 3. REST API Endpoint Verification
- **`GET /health`** -> 200 OK
- **`GET /models/risk-ranking`** -> 200 OK
- **`GET /findings/{id}`** -> 200 OK
- **`POST /findings/{id}/writeback`** -> 200 OK (Aspect verified on DataHub)
- **`GET /ledger/verify`** -> 200 OK (`{"verified": true, "entries_checked": N}`)
- **`GET /validation/report`** -> 200 OK (`{"summary": {"total": 5, "passed": 5, "failed": 0, "all_passed": true}}`)
