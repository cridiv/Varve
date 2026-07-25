# Varve — Ground Truth Validation & Benchmark Report

## 1. Introduction & Scope

This document records the empirical validation of Varve's risk correlation and severity classification engine.

### What is Being Tested
Varve evaluates historical lineage change events against historical incident records across single-model and cross-model actor scopes. We test Varve's ability to:
1. Identify high-risk patterns that directly caused past incidents (**Story 1**).
2. Correlate debt patterns across models touched by the same actor before an incident landed (**Story 3**).
3. Explicitly downgrade unvalidated patterns that lack organizational incident precedent (**Story 2 & Story 4**).

### Ground Truth Source
All test cases are derived from explicit, hand-verified narratives defined in [`service/seed-narrative.md`](file:///Users/Cridiv/Documents/Varve/service/seed-narrative.md).

### Honest Scope & Benchmark Philosophy
Rather than generating thousands of synthetic, synthetic-random metric points to pad benchmark counts, Varve's validation suite focuses on **5 hand-verified, distinct architectural scenarios**.

This is the deliberate right size for Varve's risk profile:
- **Traceable**: Every lineage event maps directly to an engineered dataset change and incident post-mortem.
- **Defensible**: Each classification rule is a deterministic SQL query, not an unexplainable model hallucination.
- **Narratable**: Every scenario can be explained and verified by memory during live review without hiding behind statistical fluff.

---

## 2. Ground Truth Benchmark Results

| Status | Model | Actor | Expected Severity | Actual Severity | Expected Validated | Actual Validated |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| ✅ PASS | `addresses` | J. Alvarez | `high` | `high` | `True` | `True` |
| ✅ PASS | `order_items` | J. Alvarez | `medium` | `medium` | `True` | `True` |
| ✅ PASS | `customers` | J. Alvarez | `high` | `high` | `True` | `True` |
| ✅ PASS | `products` | R. Chen | `low` | `low` | `False` | `False` |
| ✅ PASS | `countries` | M. Santos | `low` | `low` | `False` | `False` |

### Benchmark Summary
- **Total Scenarios Evaluated**: 5
- **Passed**: 5
- **Failed**: 0
- **All Assertions Passed**: `True`

> **5/5 seeded scenarios classified correctly, including 1 correct downgrade from provisional-high to validated-low with zero false positives.**

---

## 3. Verification Command
To re-run this validation benchmark locally from the command line:

```bash
python3 service/scripts/generate_validation_report.py
```
