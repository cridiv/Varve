# Varve — Seed Narrative (DRAFT — for review)

This is the ground truth. Every row inserted into the database in later
steps must match the specific names, dates, and numbers written here —
if a seeded row doesn't match this file, the row is wrong, not the file.

Built on top of the real `showcase-ecommerce` DataHub sample dataset,
using actual dataset names from the lineage graph already loaded
(customers, addresses, countries, order_items, products, order_details).

---

## Story 1 — The validated pattern (has a real incident behind it)

**What happened:**

On **2026-05-20**, an engineer named **J. Alvarez** modified a threshold
value in the transformation logic feeding the `customers` table
(`urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)`).
No commit message, ticket, or documentation was attached to the change.
J. Alvarez left the team three weeks later, on **2026-06-10**.

The change went unnoticed. Sixty days after the original change, on
**2026-07-19**, a data quality incident was detected on the downstream
`order_details` analytics table
(`urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)`) —
customer records were being miscategorized due to the unreviewed
threshold change six weeks earlier.

Because nobody knew to look at `customers` first, detection took
**11 days longer** than it should have — the incident was first flagged
by a downstream analyst on 2026-07-08, but root cause wasn't confirmed
until 2026-07-19.

**Root cause traced to:** the undocumented threshold change on `customers`,
made by an engineer who had since left the team.

**This is the pattern type:** `departing_engineer_change`

**Numbers this story commits to (must match seeded rows exactly):**
- Original change: 2026-05-20
- Engineer departure: 2026-06-10
- Incident first flagged: 2026-07-08
- Root cause confirmed: 2026-07-19
- Detection lag: 11 days (2026-07-08 to 2026-07-19)
- Days between original change and incident: 60 days

---

## Story 2 — The unvalidated pattern (looks risky, isn't)

**What happened:**

On **2026-06-01**, a different engineer, **R. Chen**, added a new
undocumented column to the `products` table
(`urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)`).
No documentation was attached — superficially the same red flag as
Story 1: an undocumented change, no review, no ticket.

Unlike Story 1, **no incident has ever been traced back to this change.**
R. Chen is still on the team and available to explain the change if asked.
The column has been in place for over six weeks with zero downstream
impact recorded in `business_metrics`.

**This is the pattern type:** `stale_threshold` (chosen deliberately to
resemble Story 1's severity class on the surface, so the downgrade in
Tier 2 reads as a real check rather than an obviously different case)

**Numbers this story commits to:**
- Change made: 2026-06-01
- No incident, ever, linked to this event
- Engineer still active on the team (no departure flag)

---

## Why these two specific stories

Story 1 gives the correlation engine something real to find — a genuine
`root_cause_event_id → incidents` link, with a specific, defensible
detection lag number (11 days) that will be quoted in the demo.

Story 2 exists purely to prove Varve isn't alarmist. It's built to
*look* like Story 1 on the surface — undocumented, unreviewed — but
correctly resolves to "no precedent, not urgent" when checked. This is
the credibility beat referenced in the design doc (§2.3).

Two stories, not twenty. Both hand-verified, both traceable to real
DataHub entities already loaded, both simple enough to narrate from
memory without notes during a live demo or Q&A.

---

## Summary Table & Decisions

| Narrative | Dataset URN | Pattern Type | Incident Precedent? | Business Metric Drop | Final Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Story 1** | `b2fd91.order_entry_db.order_entry.customers` → `analytics.order_details` | `departing_engineer_change` | Yes (11-day detection lag) | `categorization_accuracy`: 96.5% → 82.1% (-14.4%) | **High Severity (Validated)** |
| **Story 2** | `b2fd91.order_entry_db.order_entry.products` | `stale_threshold` | No | None (Stable) | **Low Severity (Unvalidated)** |

---

## Review & Confirmation Checklist

- [x] **Engineer Names**: `J. Alvarez` and `R. Chen` are confirmed and memorable.
- [x] **Timelines & Lag**: 60-day change gap and 11-day detection lag confirmed.
- [x] **Business Metric Drop**: Added explicit metric drop (`categorization_accuracy` dropped by 14.4% from 96.5% to 82.1%) to populate `business_metrics`.
- [x] **DataHub Dataset URNs**: Verified against live DataHub GMS instance via `test_datahub.py`:
  - `customers`: `urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)`
  - `products`: `urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)`
  - `order_details`: `urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)`