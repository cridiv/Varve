# Varve

**Tells you which of your production ML models will break next — and proves it, before you have to trust it.**

Built for [Build with DataHub: The Agent Hackathon](https://datahub.devpost.com/) — Track: Production ML Agents.

---

## The one-minute version

- **Varve doesn't watch metrics. It reads history.** Every ML model carries undocumented decisions — a threshold changed under pressure, a feature added by an engineer who's since left, a preprocessing step nobody remembers the reason for. Varve reads DataHub's lineage graph the way a geologist reads sediment, layer by layer, to find that debt before it becomes an incident.
- **It ranks, it doesn't just report.** The output isn't a wall of history — it's a ranked list of which models are most likely to break next, backed by whether that exact debt pattern has caused a real incident in your organization before.
- **It correlates across models, not just within one.** The finding a single-model tool can never produce: a threshold change on Model A, made by an engineer who also touched Model B before leaving — and Model B failed 60 days later. No per-model diff can see that. Only a cross-model, actor-level join can.
- **It doesn't cry wolf, and it can prove it.** A pattern that looks dangerous but has zero incident precedent gets explicitly downgraded to "unvalidated" — live, in front of you, not asserted quietly. Every one of these decisions is written to an append-only, hash-chained ledger, so "trust us" is replaced with `varve verify`.
- **The reasoning is deterministic. Only the sentence is a model.** SQL decides whether a pattern is validated. Claude only ever turns that decision into readable English. The model never decides severity, never decides validity — which means a wrong finding is always a debuggable data problem, never an unexplainable model hallucination.
- **It writes back to DataHub, not just to its own database.** Every finding lands as metadata on the actual lineage node — so the next engineer who opens that model in DataHub sees it inline, and the next agent that reads that lineage inherits it automatically.

---

## Why "Varve"

A varve is a single annual layer of lakebed sediment — thin, distinct, and readable, because it was laid down under specific conditions that no longer exist. Geologists reconstruct a thousand years of climate history one layer at a time.

ML models accumulate the same kind of layering. A feature added two days after a churn spike. A threshold lowered during a traffic incident and never revisited. Varve reads those layers — not to tell you a story about the past for its own sake, but because the shape of a layer tells you whether it's load-bearing or a liability, and whether it's likely to fail again.

---

## The problem

A platform team running forty production models has three people to watch them. Conventional monitoring is reactive by construction — a metric crosses a threshold, and only then do you learn something was wrong. Nobody currently has a way to ask, in advance: *of everything we're running, which model is most likely to fail next, and why?*

DataHub already has the answer buried inside it. It knows every model's full history of feature additions, pipeline changes, and threshold adjustments. What it doesn't have — until now — is a way to check whether a given shape of change has, empirically, preceded a real failure before. Varve is that missing layer.

---

## What it actually does

1. **Reads DataHub's lineage graph, historically.** Not just what a model's dependencies are today, but when each dependency changed, who changed it, and whether the change was documented.
2. **Checks every change against the organization's own incident history.** Not a generic industry heuristic — this org's actual outages, actual root causes, actual detection lags.
3. **Correlates across models, not just within one.** The same actor, or the same pattern shape, appearing on an unrelated model is exactly the kind of connection a human reviewing one model at a time will never notice.
4. **Ranks risk with evidence attached, not a black-box score.** Every entry in the triage list points to a specific event, a specific past incident (if one exists), and an honest label — `validated` or `unvalidated` — never asserted as more certain than the data supports.
5. **Writes the finding back to DataHub**, as metadata on the lineage node itself, so the knowledge compounds forward instead of living in a Slack thread.

---

## Example output

> **1. `fraud_model_v4` — high risk, validated.**
> Undocumented threshold change 4 months ago, made during a traffic spike, by an engineer who left the team three weeks later. This exact pattern — a threshold change during a load spike, never revisited, by a since-departed engineer — has preceded 2 of the last 3 incidents on this team's models, with an average detection lag of 11 days. No incident yet on this model. Recommended action: review the threshold before it repeats.
>
> **2. `churn_model_v3` — low risk, unvalidated.**
> Orphaned experiment artifact with no measurable impact for 8 months. Superficially resembles a dangerous pattern — undocumented, unreviewed — but has zero incident precedent anywhere in this organization's history. Flagged for cleanup, not urgent.

The distinction between those two entries is the entire point of the system. One is a prediction backed by precedent. The other is archaeology without precedent — useful, but explicitly not oversold as risk.

---

## Design principles

**The model never decides validity.** Whether a pattern is `validated` is the output of a deterministic SQL join against the organization's real incident history — `incidents.root_cause_event_id → lineage_events.event_id`, checked at both the per-model and cross-model scope. Claude's only job is to turn that decision into a clear, specific, honestly-hedged sentence. If a finding is wrong, it's a data problem you can inspect, not a hallucination you have to take on faith.

**Correlation is not causation, and Varve says so.** Every finding is framed as a candidate for a human to verify — never as certainty. A pattern with confirmed precedent is ranked higher; a pattern with none is explicitly labeled unvalidated, not hidden or softened into something scarier than it is.

**Every decision is ledgered, not just logged.** Findings, validations, and downgrades are written to an append-only table where each row's hash includes the previous row's hash — a lightweight audit chain. `scripts/verify_ledger.py` walks the chain and confirms nothing was altered after the fact. This exists so "trust the agent's history" isn't a request for faith — it's something you can check yourself, in under a second, from the command line.

**Severity composes three DataHub primitives, not just lineage.** A pattern that touches a node tagged `PII` or `business-critical` in DataHub's own governance metadata is weighted higher than the identical pattern on an untagged node. Ownership metadata auto-routes every finding to the actual owning team at creation time — no manual "who even owns this" lookup.

**Varve gets more useful the longer a team uses it, without asking for extra work.** A brand-new team has no incident history to validate patterns against — every finding would honestly come back `unvalidated` on day one. Two things address this directly, rather than leaving it as a silent weakness:

- *Industry-general fallback.* `patterns` supports a `scope_key = 'industry_general'` tier — a small number of hand-sourced, clearly-labeled base rates drawn from published post-mortems (e.g. "departing-engineer changes precede incidents at roughly this rate across the industry"). Severity resolution always checks the most specific, most trustworthy evidence first — this team's own history, then this specific actor's history, and only falls back to the industry rate if neither exists yet. It is never presented as equivalent to real organizational evidence.
- *Self-bootstrapping from normal use.* When Varve notices a genuine anomaly in `business_metrics`, it proposes it as a candidate incident — "accuracy dropped 9%, nearest undocumented change was 4 days earlier, confirm this as a real incident?" A confirmation writes a real row into `incidents`, with a real `root_cause_event_id`, exactly like the hand-seeded scenarios in `seed-narrative.md` — except now it's this team's actual history. A dismissal costs nothing and logs useful negative evidence instead. No separate data-entry step is required: the same human review Varve already needs is the mechanism that grows its own precedent over time. As soon as one real, org-specific data point exists for a pattern type, it automatically outranks the industry fallback — there is no manual switch to flip.

---

## Architecture

```
DataHub (lineage, ownership, governance tags)
        │  read via MCP Server / Agent Context Kit
        ▼
PostgreSQL — lineage_events, business_metrics, incidents, findings, patterns, ledger
        │  deterministic SQL correlation (per-model + cross-model)
        ▼
Claude API — narrative + recommended action generation only
        │
        ▼
FastAPI backend  →  React frontend (triage dashboard, finding detail, actor view)
        │
        ▼
Write-back to DataHub (node annotation + proposed ValidatedRiskPattern aspect)
```

| Layer | Technology |
|---|---|
| Lineage source | DataHub MCP Server / Agent Context Kit |
| Structured store | PostgreSQL |
| Reasoning (narrative only) | Claude API (`claude-sonnet-5`) |
| Backend | FastAPI (Python) |
| Frontend | React + TailwindCSS |
| Hosting | AWS (ECS/Fargate + RDS) |

---

## Validation

Rather than claim Varve "correlates patterns" on the strength of a demo alone, its logic is checked against a small, hand-written, fully consistent seed history (`seed-narrative.md`) — every number in the database is required to match the story, not the other way around.

- Seeded scenarios covering both a real, validated pattern (a departing-engineer threshold change with a confirmed downstream incident) and a deliberately similar-looking pattern with zero precedent.
- Correlation logic run against all seeded scenarios; results reported as an explicit pass/fail count in `docs/validation.md`, not asserted without evidence.
- The live downgrade — a provisional high-severity classification re-checked and correctly downgraded once the cross-model check completes — is a dedicated, deliberate UI state, not a hidden backend detail.

This is a small, honest number, not a large, unverifiable one. Two clean, hand-checkable scenarios that you can narrate from memory beat twenty generated ones you'd have to double-check under Q&A pressure.

---

## Open-source contribution

Varve proposes a new DataHub aspect type, `ValidatedRiskPattern`, as a genuine extension to DataHub's own metadata model — not a Varve-internal convention buried in free text. Today, DataHub can describe *what* changed and *when*, but has no first-class way to record *this shape of change has, empirically, preceded failure before, N times, with an average detection lag of D days*. The RFC and reference implementation are in `docs/datahub-rfc-validated-risk-pattern.md`, submitted as a proposal so any future agent — not just Varve — can read and write it consistently.

---

## What's explicitly out of scope

Stated plainly rather than concealed:

- No model training or ML pipeline work — Varve reasons about other models' lineage, it doesn't build models.
- No real-time streaming ingestion — periodic sync from DataHub is sufficient for the workflow this solves. Anomaly detection on `business_metrics` runs on the same sync cadence, not a separate streaming pipeline.
- Pattern severity weighting is hand-tuned (counts and ratios), not a learned model, at every scope — including the industry-general fallback rates, which are seeded from a small number of published sources, not mined at scale. Making the weighting itself learned from an org's accumulated confirmations over time is a natural next step, not a claim made now.
- The `ValidatedRiskPattern` aspect is proposed as an RFC and reference implementation; it is not claimed to be merged upstream by submission time.

---

## Running it locally

```bash
# 1. Start DataHub (see DataHub Quickstart docs)
datahub docker quickstart
datahub datapack load showcase-ecommerce

# 2. Start Postgres
docker run --name varve-postgres \
  -e POSTGRES_USER=varve -e POSTGRES_PASSWORD=varve -e POSTGRES_DB=varve \
  -p 5433:5432 -d postgres:16

# 3. Apply schema and seed data
docker exec -i varve-postgres psql -U varve -d varve < schema.sql
python3 scripts/seed_from_narrative.py

# 4. Configure
export ANTHROPIC_API_KEY="your-key"
export DATAHUB_GMS_URL="http://localhost:8080"

# 5. Run the backend
uvicorn main:app --reload --port 8000

# 6. Verify the ledger at any time
python3 scripts/verify_ledger.py
```

---

## What we learned building this

Constraining where the model is allowed to act made the system easier to trust, not harder to build — every finding's validity is a SQL answer you can check by hand, and the model is only ever asked to do the one thing language models are actually good at: write a clear sentence from a clear fact.

The valuable signal was never in either table alone. `lineage_events` isn't new information, and `incidents` isn't new information — DataHub already has the first, and most teams already track the second somewhere. The join between them, at the right scope — per-model and per-actor — is what turns "this looks undocumented" into "this exact pattern has cost this team money before."

---

## What's next

- Learn pattern-severity weighting from an organization's own incident outcomes over time, rather than hand-tuned ratios.
- Extend cross-model correlation beyond shared actors to shared upstream data sources.
- A Slack/PagerDuty integration so a validated high-risk finding can page the routed owner directly, not just appear on a dashboard.

---

## Track fit

This directly answers the Production ML Agents track: Varve reads DataHub's end-to-end ML lineage via the MCP Server / Agent Context Kit, and its entire output is built to catch silent, undocumented risk before it costs money — ranked by real precedent, not generic heuristics, and written back to DataHub so the next engineer or agent inherits exactly what was found.

---

*Open source under the Apache 2.0 License.*