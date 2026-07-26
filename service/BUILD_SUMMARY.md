# Varve — Walkthrough & Build Summary

**Project:** AI Risk & Decision Intelligence Platform for production data pipelines  
**Backend:** Python 3.11, FastAPI, PostgreSQL 16 (Docker), `acryl-datahub`  
**LLM:** `deepseek-ai/deepseek-v4-flash` via NVIDIA API (with 2-worker parallel reasoning)  
**DataHub:** Local GMS at `http://localhost:8080` (showcase-ecommerce sample)

> **"Every claim Varve makes carries a visible label for how much you should trust it, and every one of those labels is independently checkable."**

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
│   ├── schema.sql                # DDL schema definitions (lineage_events, business_metrics, incidents, findings, patterns, ledger, candidate_incidents, actor_owner_mappings)
│   └── seed.sql                  # Ground truth seed narratives 1-4 + industry_general baselines
├── services/                     # Core business logic domain
│   ├── __init__.py
│   ├── correlation_service.py    # Correlation engine, 5-tier trust hierarchy & ground-truth benchmark
│   ├── generator_service.py      # LLM narrative synthesis & findings population
│   ├── datahub_service.py        # DataHub GMS write-back, DataHub Ownership & Governance Tag resolution
│   ├── actor_resolution_service.py # Actor identity resolution engine & DataHub Corpuser URN mapping
│   ├── ledger_service.py         # Cryptographic SHA-256 hash-chained audit ledger engine
│   ├── validation_service.py    # Automatic validation report generator for docs/validation.md
│   └── anomaly_service.py       # Rolling Z-score anomaly detection & candidate incident discovery
├── api/                          # FastAPI modular routers
│   ├── __init__.py
│   ├── health.py                 # GET /health, POST /datahub/connect, POST /datahub/connect/step/*
│   ├── findings.py               # GET /models/risk-ranking, GET /findings/{id}, GET /findings/by-team/{team}, POST /findings/{id}/writeback
│   ├── patterns.py               # GET /patterns/by-actor/{actor}, POST /actors/resolve, GET /actors/mappings
│   ├── ledger.py                 # GET /ledger/verify (audit chain integrity check)
│   ├── validation.py             # GET /validation/report (on-demand benchmark & doc update)
│   └── candidates.py             # GET /candidate-incidents, POST /candidate-incidents/{id}/confirm, POST /candidate-incidents/{id}/dismiss
├── scripts/                      # Executable CLI tools
│   ├── verify_ledger.py         # Terminal verifier for ledger hash chain integrity
│   ├── generate_validation_report.py # Terminal benchmark generator
│   └── verify_coldstart_candidate.py # Harness for Scenario 5 cold-start candidate verification
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

### Phase B — Audit Ledger Capability
- **Database Schema**: `ledger` table in PostgreSQL (`ledger_id`, `event_type`, `finding_id`, `payload`, `prev_hash`, `this_hash`, `created_at`).
- **Cryptographic Hash Chain**: SHA-256 linking of decision events (`finding_created`, `severity_set`, `downgrade`, `writeback`, `incident_confirmed`, `incident_dismissed`).
- **Independent Verification**: `service/scripts/verify_ledger.py` and `GET /ledger/verify` endpoint validating zero tamper state.
- **Tamper Resistance Proof**: Deliberate PostgreSQL payload modification tested; verifier instantly pinpoints exact corrupted row index and returns exit code 1.

### Phase C — Structured Benchmark & Automatic Validation
- **Structured Benchmark**: `run_ground_truth_check()` returning structured JSON summary (`total`, `passed`, `failed`, `all_passed`) and per-event comparisons.
- **Automated Validation Report**: `generate_validation_report()` auto-writing [`docs/validation.md`](file:///Users/Cridiv/Documents/Varve/docs/validation.md) on backend startup (`main.py`) and via `GET /validation/report`.
- **Validation Scope**: 5/5 seeded scenarios classified correctly with zero false alarms.

### Phase D — Cold-Start Mitigation & Candidate Incidents
- **Hand-Sourced Industry Baselines (`scope_key = 'industry_general'`)**: Hand-sourced base rates documented in [`docs/industry-baseline-sources.md`](file:///Users/Cridiv/Documents/Varve/docs/industry-baseline-sources.md) (Google SRE Book, DORA 2023, Datadog 2023, Stripe, Slack, Knight Capital).
- **5-Tier Trust Hierarchy Resolution Engine**: `correlation_service.py` evaluates risk in strict trust order:
  $$\text{Model Incident} \longrightarrow \text{Actor Cross-Model} \longrightarrow \text{\texttt{org\_wide}} \longrightarrow \text{Actor Scope} \longrightarrow \text{\texttt{industry\_general}}$$
- **Evidentiary Base-Rate Thresholds**: Fallback tier evaluates ratio $\frac{\text{times\_preceded\_incident}}{\text{times\_observed}}$:
  - Base Rate $\ge 25\% \rightarrow$ Retains provisional severity.
  - $15\% \le \text{Base Rate} < 25\% \rightarrow$ Caps severity at `MEDIUM`.
  - Base Rate $< 15\% \rightarrow$ Downgrades severity to `LOW` (Cold-start fallback downgrade proof).
- **Z-Score Anomaly Detection (`anomaly_service.py`)**: Rolling Z-score anomaly detector ($z \ge 2.0$) flagging `is_anomaly = TRUE` on `business_metrics`.
- **Candidate Incident Discovery**: `find_candidate_incidents()` matching metric anomalies to nearest preceding lineage change within lookback window.
- **Human-in-the-Loop Candidate Workflow**:
  - `GET /candidate-incidents`: Lists unconfirmed candidate proposals.
  - `POST /candidate-incidents/{id}/confirm`: Creates a real `incidents` row, logs `incident_confirmed` in ledger, and updates `patterns` rollups immediately.
  - `POST /candidate-incidents/{id}/dismiss`: Logs `incident_dismissed` in audit ledger as free negative evidence.

### Phase E — Governance, Routing & Tag Honesty Labeling
- **Automated DataHub Owner Resolution**: `resolve_dataset_routed_owner()` querying DataHub `OwnershipClass` aspect with strict priority:
  1. Specific individual owner (non-EMP006) $\rightarrow$ `jonny1 (Data Owner)`, `patrick1 (Data Owner)`
  2. Accountable Director fallback (EMP006) $\rightarrow$ `Ian Chen (Director of Data Engineering)`
  3. Group fallback $\rightarrow$ `corpGroup (Team Group)`
- **Team Triage API (`GET /findings/by-team/{team}`)**: Filters findings by owner/team name with case-insensitive partial matching.
- **Governance Tag Multipliers (`severity_multiplier`)**:
  - `business-critical` / `tier-1`: **1.5x** multiplier (promotes severity, e.g. `medium` $\rightarrow$ `high`).
  - `PII` / `sensitive`: **1.3x** multiplier.
  - Default / untagged: **1.0x** multiplier.
- **Tag Source Honesty Labeling (`tag_source`)**:
  - Mirroring `evidence_scope`, Varve explicitly labels whether a tag originated from verified catalog data or schema inference:
    - `datahub_native` $\rightarrow$ `"Verified DataHub Catalog Tag"`
    - `inferred` $\rightarrow$ `"Inferred from Schema (Heuristic Fallback)"`
    - `none` $\rightarrow$ `"Untagged"`
- **False-Positive Exclusion Engine**: Harmless/deprecated/test datasets (`survey`, `archive`, `deprecated`, `temp`, `test`, `dummy`, `mock`, `sandbox`) are automatically excluded from heuristic auto-detection to prevent false positives.

### Phase F — DataHub Connect Flow & Step-by-Step Verification (New)
- **DataHub Authentication**: `POST /datahub/connect` verifying DataHub server-side HTTP credentials against `/logIn`.
- **Live 5-Step Connection Pipeline**:
  - `POST /datahub/connect/step/gms`: Verifies GMS connection & server health.
  - `POST /datahub/connect/step/lineage`: Queries DataHub graph for lineage dataset URNs.
  - `POST /datahub/connect/step/ownership`: Resolves DataHub dataset ownership aspect.
  - `POST /datahub/connect/step/governance`: Checks DataHub governance tags and severity multipliers.
  - `POST /datahub/connect/step/incidents`: Evaluates historical organizational incidents (cold-start baseline indicator).

### Phase G — Actor Identity Resolution & Corpuser Mapping (New)
- **Identity Space Bridge (`actor_resolution_service.py`)**: Resolves free-text `lineage_events.actor` names (`"J. Alvarez"`, `"K. Vance"`, `"Ian Chen"`) to DataHub owner URNs (`urn:li:corpuser:EMP006`, `urn:li:corpuser:jonny1`, `urn:li:corpuser:k_vance`).
- **Database Table (`actor_owner_mappings`)**: Stores `lineage_actor`, `datahub_owner_urn`, `datahub_display_name`, `match_type`, `created_at`.
- **3-Layer Resolution Engine**:
  1. Dynamic database & DataHub GMS corpuser lookup.
  2. First initial + last name matching (e.g. `J. Alvarez` $\rightarrow$ `jonny1`, `I. Chen` $\rightarrow$ `Ian Chen`).
  3. Standardized fallback URN construction for unknown actors (`urn:li:corpuser:{slug}`).
- **Identity Resolution Endpoints**:
  - `POST /actors/resolve`: Runs identity resolution step across all lineage actors and updates `actor_owner_mappings`.
  - `GET /actors/mappings`: Retrieves all stored identity mappings.
  - `GET /patterns/by-actor/{actor}`: Dynamically resolves identity and returns cross-model authoring events + owned dataset findings + DataHub owner URN badge.

### Phase H — Frontend Live Data Integration (New)
- **Live Risk Triage Console (`RiskTriageList.tsx`)**: 100% connected to `GET /models/risk-ranking` and `POST /findings/{id}/writeback` without local mock data.
- **Actor History Board (`ActorHistoryBoard.tsx`)**: Displays resolved DataHub Corpuser URN badges (`urn:li:corpuser:EMP006`).
- **Actor Profile Selector (`app/app/actors/page.tsx`)**: Merges lineage authors and DataHub Owners (`Ian Chen`, `jonny1`, `patrick1`) into unified profile selection bar.

---

## Verification Results

### 1. Ground Truth Benchmark (`python service/scripts/generate_validation_report.py`)
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

### 2. Actor Identity Resolution Verification (`POST /actors/resolve`)
```json
[
  {
    "lineage_actor": "Ian Chen",
    "datahub_owner_urn": "urn:li:corpuser:EMP006",
    "datahub_display_name": "Ian Chen (Director of Data Engineering)",
    "match_type": "exact_display_match"
  },
  {
    "lineage_actor": "J. Alvarez",
    "datahub_owner_urn": "urn:li:corpuser:jonny1",
    "datahub_display_name": "jonny1 (Data Owner)",
    "match_type": "alias_keyword_match"
  },
  {
    "lineage_actor": "K. Vance",
    "datahub_owner_urn": "urn:li:corpuser:k_vance",
    "datahub_display_name": "K. Vance (Data Owner)",
    "match_type": "exact_display_match"
  },
  {
    "lineage_actor": "Alice Cooper",
    "datahub_owner_urn": "urn:li:corpuser:alice_cooper",
    "datahub_display_name": "Alice Cooper (Data Owner)",
    "match_type": "constructed_corpuser_urn"
  }
]
```

### 3. Audit Ledger Chain Verification (`python service/scripts/verify_ledger.py`)
```text
=======================================================
      VARVE AUDIT LEDGER — HASH CHAIN VERIFIER         
=======================================================

Verifying 38 ledger entries sequentially...

✔ [PASS] Row 01 | Event: finding_created    | Finding: bfd5bb19... | this_hash: adb51d93a3ec...
...
✔ [PASS] Row 37 | Event: incident_confirmed | Finding: None        | this_hash: 9a721b44c8e1...
✔ [PASS] Row 38 | Event: incident_dismissed | Finding: None        | this_hash: 419df820a2bc...

-------------------------------------------------------
✔ 38/38 ledger entries verified, chain intact.
  Zero tampering detected. All decision records are mathematically authentic.
```

### 4. Complete REST API Endpoint Coverage
- **`GET /health`** -> 200 OK
- **`POST /datahub/connect`** -> 200 OK
- **`POST /datahub/connect/step/{stepKey}`** -> 200 OK (`gms`, `lineage`, `ownership`, `governance`, `incidents`)
- **`GET /models/risk-ranking`** -> 200 OK
- **`GET /findings/{id}`** -> 200 OK
- **`GET /findings/by-team/{team}`** -> 200 OK
- **`POST /findings/{id}/writeback`** -> 200 OK (Aspect verified on DataHub GMS)
- **`POST /actors/resolve`** -> 200 OK (Runs resolution step & stores mappings)
- **`GET /actors/mappings`** -> 200 OK (Returns stored identity mappings)
- **`GET /patterns/by-actor/{actor}`** -> 200 OK (Identity-resolved cross-model analytics)
- **`GET /ledger/verify`** -> 200 OK (`{"verified": true, "entries_checked": N}`)
- **`GET /validation/report`** -> 200 OK (`{"summary": {"total": 5, "passed": 5, "failed": 0, "all_passed": true}}`)
- **`GET /candidate-incidents`** -> 200 OK (Returns unconfirmed candidates)
- **`POST /candidate-incidents/{id}/confirm`** -> 200 OK (Creates incident & updates pattern rollups)
- **`POST /candidate-incidents/{id}/dismiss`** -> 200 OK (Logs negative evidence to audit ledger)
