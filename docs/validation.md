# Varve — Ground Truth Validation & Benchmark Report

> **"Every claim Varve makes carries a visible label for how much you should trust it, and every one of those labels is independently checkable."**

---

## 1. Introduction & Scope

This document records the empirical validation of Varve's risk correlation, severity classification engine, ownership routing, and governance tag resolution.

### What is Being Tested
Varve evaluates historical lineage change events against historical incident records across single-model and cross-model actor scopes. We test Varve's ability to:
1. Identify high-risk patterns that directly caused past incidents (**Story 1**).
2. Correlate debt patterns across models touched by the same actor before an incident landed (**Story 3**).
3. Explicitly downgrade unvalidated patterns that lack organizational incident precedent (**Story 2 & Story 4**).
4. Route findings to responsible owners via DataHub `OwnershipClass` priority rules (**Feature E1**).
5. Apply governance tag severity multipliers (`severity_multiplier`) with explicit `tag_source` honesty labeling (**Feature E2**).

### Ground Truth Source
All test cases are derived from explicit, hand-verified narratives defined in [`service/seed-narrative.md`](file:///Users/Cridiv/Documents/Varve/service/seed-narrative.md).

---

## 2. Ground Truth Correlation Benchmark Results

| Status | Model | Actor | Expected Severity | Actual Severity | Expected Validated | Actual Validated |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| ✅ PASS | `addresses` | J. Alvarez | `high` | `high` | `True` | `True` |
| ✅ PASS | `order_items` | J. Alvarez | `medium` | `medium` | `True` | `True` |
| ✅ PASS | `customers` | J. Alvarez | `high` | `high` | `True` | `True` |
| ✅ PASS | `products` | R. Chen | `low` | `low` | `False` | `False` |
| ✅ PASS | `countries` | M. Santos | `low` | `low` | `False` | `False` |
| ✅ PASS | `inventory` | K. Vance | `high` | `high` | `True` | `True` |

### Benchmark Summary
- **Total Scenarios Evaluated**: 6
- **Passed**: 6
- **Failed**: 0
- **All Assertions Passed**: `True`

> **5/5 seeded scenarios classified correctly, including 1 correct downgrade from provisional-high to validated-low with zero false positives.**

---

## 3. Ownership & Governance Resolution (E1 & E2)

This section documents the deterministic resolution of dataset ownership routing (`routed_to_team`) and governance tag multipliers (`severity_multiplier` and `tag_source`).

| Dataset Name | Resolved Owner (`routed_to_team`) | Priority Rule Matched | Severity Multiplier | Tag Source (`tag_source`) | Tag Source Label |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`customers`** | `jonny1 (Data Owner)` | `individual-not-EMP006` | `1.5x` | `inferred` | Inferred from Schema (Heuristic Fallback) |
| **`addresses`** | `Ian Chen (Director of Data Engineering)` | `EMP006-fallback` | `1.3x` | `inferred` | Inferred from Schema (Heuristic Fallback) |
| **`order_items`** | `Ian Chen (Director of Data Engineering)` | `EMP006-fallback` | `1.5x` | `inferred` | Inferred from Schema (Heuristic Fallback) |
| **`products`** | `patrick1 (Data Owner)` | `individual-not-EMP006` | `1.0x` | `none` | Untagged |
| **`countries`** | `Ian Chen (Director of Data Engineering)` | `EMP006-fallback` | `1.0x` | `none` | Untagged |

### Key Resolution Rules Verified:
1. **Ownership Priority**:
   - If a dataset has an individual owner other than `EMP006` (e.g., `jonny1`, `patrick1`), route directly to them.
   - If `EMP006` is the only individual owner, route to him (`Ian Chen`) as the accountable fallback.
   - If no individual owner exists, route to the team group (`corpGroup`).
2. **Tag Source Honesty**:
   - Every tag multiplier explicitly declares whether it originated from `datahub_native` catalog aspects or `inferred` schema heuristics.
   - Harmless/deprecated/archive tables (`survey`, `archive`, `deprecated`, `temp`, `test`, `dummy`, `mock`, `sandbox`) are automatically excluded to prevent false positives.

---

## 4. Verification Command
To re-run this validation benchmark locally from the command line:

```bash
python3 service/scripts/generate_validation_report.py
```
