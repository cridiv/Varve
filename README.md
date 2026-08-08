<div align="center">

<img src="docs/images/varve_logo.png" alt="Varve Logo" width="280" />

### **Tells you which of your production ML models will break next — and proves it, before you have to trust it.**

[![Hackathon](https://img.shields.io/badge/Build%20with%20DataHub-Production%20ML%20Agents-7c3aed?style=for-the-badge&logo=datahub)](https://datahub.devpost.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Backend-FastAPI_3.11-009688?style=for-the-badge&logo=fastapi)](service/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js_16-000000?style=for-the-badge&logo=nextdotjs)](app/)
[![Contributing](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge)](CONTRIBUTING.md)


### 📺 **Watch the 3-Minute Demo Video**

[![Varve Demo Video](https://img.youtube.com/vi/KfsU7xwhtp0/maxresdefault.jpg)](https://youtu.be/KfsU7xwhtp0)

</div>


> [!NOTE]
> *Every claim Varve makes carries a visible label for how much you should trust it, and every one of those labels is independently checkable.*


## Community & Open Source

We welcome community contributions! Please check out our guidelines:
- 📖 [Contributing Guide](CONTRIBUTING.md)
- 🤝 [Code of Conduct](CODE_OF_CONDUCT.md)
- 🛡️ [Security Policy](SECURITY.md)
- 📜 [Apache 2.0 License](LICENSE)


## Table of Contents

- [The One-Minute Version](#the-one-minute-version)
- [Why "Varve"](#why-varve)
- [The Problem](#the-problem)
- [What It Actually Does](#what-it-actually-does)
- [Example Output](#example-output)
- [Design Principles](#design-principles)
- [Architecture](#architecture)
- [Validation](#validation)
- [Open-Source Contribution (RFC)](#open-source-contribution)
- [What's Explicitly Out of Scope](#whats-explicitly-out-of-scope)
- [Running It Locally](#running-it-locally)
- [What We Learned Building This](#what-we-learned-building-this)
- [What's Next](#whats-next)
- [Track Fit](#track-fit)


## The One-Minute Version

- **Varve doesn't watch metrics. It reads history.** Every ML model carries undocumented decisions — a threshold changed under pressure, a feature added by an engineer who's since left, a preprocessing step nobody remembers the reason for. Varve reads DataHub's lineage graph the way a geologist reads sediment, layer by layer, to find that debt before it becomes an incident.
- **It ranks, it doesn't just report.** The output is a ranked triage list of which models are most likely to break next, backed by whether that exact debt pattern has caused a real incident in your organization before.
- **It correlates across models, not just within one.** A threshold change on Model A, made by an engineer who also touched Model B before leaving — and Model B failed 60 days later. No per-model diff can see that. Only a cross-model, actor-level join can.
- **It doesn't cry wolf, and it can prove it.** A pattern that looks dangerous but has zero incident precedent gets explicitly downgraded — live, not asserted quietly. Every decision is written to an append-only, hash-chained ledger, so "trust us" is replaced with a verification script anyone can run.
- **The reasoning is deterministic. Only the sentence is a model.** SQL and structured rules decide severity and validity. The LLM's only job is to turn that decision into a clear, specific sentence. A wrong finding is always a debuggable data problem, never an unexplainable hallucination.
- **It gets useful on day one, and smarter every day after.** A brand-new team with no incident history still gets an honestly-labeled, industry-sourced baseline instead of silence — and every confirmed finding automatically upgrades that pattern to real, organization-specific evidence going forward.
- **It composes three DataHub primitives, not just lineage.** Ownership metadata auto-routes findings to the right team. Governance tags — read natively where present, inferred where absent, and always labeled which — adjust severity. Lineage alone was never the whole picture.
- **It writes back to DataHub, not just to its own database.** Every finding lands as metadata on the actual lineage node, idempotently, so re-running Varve never litters a node with duplicate annotations.


## Why "Varve"

A **varve** is a single annual layer of lakebed sediment — thin, distinct, and readable, because it was laid down under specific conditions that no longer exist. Geologists reconstruct a thousand years of climate history one layer at a time.

ML models accumulate the same kind of layering. A feature added two days after a churn spike. A threshold lowered during a traffic incident and never revisited. Varve reads those layers — not to tell a story about the past for its own sake, but because the shape of a layer tells you whether it's load-bearing or a liability, and whether it's likely to fail again.


## The Problem

A platform team running forty production models has three people to watch them. Conventional monitoring is reactive by construction — a metric crosses a threshold, and only then do you learn something was wrong. Nobody currently has a way to ask, in advance: *of everything we're running, which model is most likely to fail next, and why?*

DataHub already has the answer buried inside it. It knows every model's full history of feature additions, pipeline changes, and threshold adjustments. What it doesn't have — until now — is a way to check whether a given shape of change has, empirically, preceded a real failure before. Varve is that missing layer.


## What It Actually Does

1. **Reads DataHub's lineage graph, historically.** Not just what a model's dependencies are today, but when each dependency changed, who changed it, and whether the change was documented.
2. **Checks every change against the organization's own incident history**, falling back honestly to a labeled industry baseline when no organizational evidence exists yet.
3. **Correlates across models, not just within one** — the same actor, or the same pattern shape, appearing on an unrelated model is exactly the kind of connection a human reviewing one model at a time will never notice.
4. **Ranks risk with evidence attached, not a black-box score.** Every entry in the triage list points to a specific event, a specific past incident (if one exists), and an honest evidence tier — never asserted as more certain than the data supports.
5. **Grows its own evidence automatically.** Genuine anomalies in tracked business metrics are proposed as candidate incidents; a human confirms or dismisses in the normal course of reviewing findings, and confirmations become real, permanent organizational precedent.
6. **Routes and weighs findings using DataHub's own ownership and governance data**, not a parallel system Varve invents on the side.
7. **Writes the finding back to DataHub**, idempotently, as metadata on the lineage node itself, so the knowledge compounds forward instead of living in a Slack thread.
8. **Ledgers every decision.** Every finding, severity resolution, downgrade, ownership routing, and write-back is recorded in an append-only, hash-chained table that can be independently re-verified at any time.


## Example Output

> **1. `fraud_model_v4` — high risk, org-validated.**  
> Undocumented threshold change 4 months ago, made during a traffic spike, by an engineer who left the team three weeks later. This exact pattern has preceded 2 of the last 3 incidents on this team's models, average detection lag 11 days. Routed to: Payments Platform (owner). Recommended action: review the threshold before it repeats.
>
> **2. `churn_model_v3` — low risk, unvalidated.**  
> Orphaned experiment artifact with no measurable impact for 8 months. Superficially resembles a dangerous pattern — undocumented, unreviewed — but has zero incident precedent anywhere in this organization's history. Flagged for cleanup, not urgent.
>
> **3. `new_signup_model` — medium risk, industry-general (cold start).**  
> This team has no incident history yet. Evidence tier: industry-general baseline (source: published post-mortem data). Pattern type `unreviewed_change` carries a moderate industry base rate — capped at MEDIUM rather than inheriting the provisional HIGH guess. This will automatically upgrade to organization-specific evidence the first time a related finding is confirmed.

The distinction between these three entries is the entire point of the system: a prediction backed by this team's own precedent, archaeology with no precedent at all, and an honest, capped estimate for a team that hasn't built up history yet — never presented with more confidence than the evidence supports.


## Design Principles

> [!IMPORTANT]
> **The model never decides validity.** Whether a pattern is validated is the output of a deterministic SQL join against the organization's real incident history — `incidents.root_cause_event_id → lineage_events.event_id`, checked at per-model, per-actor, and org-wide scope. The LLM's only job is to turn that decision into a clear, honestly-hedged sentence. If a finding is wrong, it's a data problem you can inspect, not a hallucination you have to take on faith.

**Correlation is not causation, and Varve says so.** Every finding is framed as a candidate for a human to verify — never as certainty. A pattern with confirmed precedent is ranked higher; a pattern with none is explicitly labeled unvalidated, not hidden or softened into something scarier than it is.

**Every decision is ledgered, not just logged.** Findings, severity resolutions, downgrades, ownership routing, and write-backs are written to an append-only table where each row's hash includes the previous row's hash. `service/scripts/verify_ledger.py` walks the full chain and confirms nothing was altered after the fact — "trust the agent's history" is something you can check yourself in under a second, not a request for faith.

> [!TIP]
> **Cold start is answered honestly, not silently.** A brand-new team has no incident history to validate patterns against. Rather than leave every finding `unvalidated` with no further context, or worse, quietly assert confidence it hasn't earned, Varve does two things:
> - *Industry-general fallback, with real thresholds — not a rubber stamp.* A small number of hand-sourced, clearly-cited base rates are used only when no organization-specific evidence exists. These rates actively drive the outcome: a high industry base rate retains a provisional high severity, a moderate rate caps it at medium, and a low rate downgrades it to low — the fallback tier obeys the same evidentiary discipline as validated organizational data, it doesn't just repeat the initial guess.
> - *Self-bootstrapping from normal use.* When Varve notices a genuine statistical anomaly in a tracked business metric, it proposes a candidate incident — with the nearest undocumented lineage change and the gap in days — for a human to confirm or dismiss. Confirmation writes a real, permanent row into the organization's own incident history; dismissal costs nothing and is logged as negative evidence. No separate data-entry workflow is required — the same review a team already does closes the loop and grows the organization's own precedent, automatically outranking the industry fallback the moment real evidence exists.

**Severity composes three DataHub primitives, not just lineage.** Ownership metadata resolves the correct team or individual to route a finding to, using a documented priority order (specific individual owner, then a designated fallback owner, then the owning group). Governance and classification tags — read directly from DataHub where present, and conservatively inferred from naming conventions where absent — apply a severity multiplier. Every finding's output honestly labels which of these two sources produced its tag, so an inferred heuristic is never mistaken for verified governance data.


## Architecture

```
DataHub (lineage, ownership, governance tags)
        │  read via MCP Server / Agent Context Kit
        ▼
PostgreSQL
  lineage_events · business_metrics · incidents · findings · patterns · ledger
        │  deterministic correlation: per-model, per-actor, org-wide, industry-general
        ▼
LLM synthesis layer  (narrative + recommended action generation only —
                       never severity, never validity)
        │
        ▼
FastAPI backend  →  React frontend
  (triage dashboard · finding detail · cross-model actor history)
        │
        ▼
Write-back to DataHub  (idempotent node annotation +
                         proposed ValidatedRiskPattern aspect)
        │
        ▼
Append-only hash-chained ledger, independently re-verifiable at any time
```

| Layer | Technology |
|---|---|
| Lineage, ownership, governance source | DataHub MCP Server / Agent Context Kit |
| Structured store | PostgreSQL 16 |
| Narrative synthesis (reasoning excluded) | NVIDIA API / DeepSeek-V4 |
| Backend API | FastAPI (Python 3.11) |
| Frontend UI | Next.js 16 + React 19 + TailwindCSS |
| Audit trail | Append-only SHA-256 hash-chained ledger table |


## Validation

Rather than claim Varve "correlates patterns" on the strength of a demo alone, its logic is checked end-to-end against a small, hand-written, fully consistent seed history — every number in the database is required to match the written story, not the other way around.

- **6 seeded ground-truth scenarios**, covering single-model validated patterns, an unvalidated control, a cross-model actor-linked incident, a live provisional-to-downgraded severity transition, and one real incident produced by the self-bootstrapping loop itself during a live end-to-end run.
- **6/6 scenarios classified correctly** — full detail and reproducible harness commands in `docs/validation.md`, regenerated automatically from a live run rather than hand-copied.
- **Industry-general fallback thresholds independently verified** across all three bands: a high base rate retains severity, a moderate rate caps it, a low rate downgrades it — the fallback is proven to actively constrain the outcome, not just relabel a provisional guess.
- **The full self-bootstrapping loop verified live**: a genuine metric anomaly detected, proposed as a candidate, confirmed, and shown to update the organization's own pattern evidence immediately — closing the exact gap a brand-new team would otherwise face.
- **The audit ledger independently verified**: every finding, severity resolution, downgrade, ownership routing decision, and write-back across a full run confirmed as an intact, untampered hash chain.
- **DataHub write-back independently confirmed**, not merely assumed successful — read back directly from DataHub after writing, and proven idempotent under repeated runs against the same node.


## Open-Source Contribution

Varve proposes a new DataHub aspect type, `ValidatedRiskPattern`, as a genuine extension to DataHub's own metadata model — not a Varve-internal convention buried in free text. Today, DataHub can describe *what* changed and *when*, but has no first-class way to record *this shape of change has, empirically, preceded failure before, N times, with an average detection lag of D days, at this evidence tier*. The full RFC, its rationale, and a reference schema stub are in `docs/datahub-rfc-validated-risk-pattern.md` and `docs/validated-risk-pattern.avsc` — submitted as a concrete proposal so any future agent, not just Varve, can read and write this shape of evidence consistently.


## What's Explicitly Out of Scope

Stated plainly rather than concealed:

- **No autonomous remediation.** Varve recommends; it never modifies a model, pipeline, or configuration itself. Every action beyond producing a finding and a recommendation is left to the human who owns that decision.
- **No model training or ML pipeline work.** Varve reasons about other models' lineage and history; it does not build or retrain models.
- **No real-time streaming ingestion.** Periodic sync from DataHub is sufficient for the workflow this solves; anomaly detection runs on the same cadence, not a separate streaming pipeline.
- **Severity and fallback weighting are hand-tuned, not learned**, at every scope — including the industry-general baseline rates, which are seeded from a small number of cited published sources, not mined at scale. Learning these weights from an organization's own accumulated confirmations over time is a natural next step, not a claim made now.
- **The `ValidatedRiskPattern` aspect is a proposal and reference implementation**, not a claim of upstream merge by submission time.


## Running It Locally

### Option A: 1-Command Startup with Docker Compose (Recommended)

```bash
# 1. Set your API keys
cp service/.env.example service/.env   # fill in MODEL_API_KEY and SLACK_WEBHOOK_URL

# 2. Spin up Postgres, FastAPI Backend (port 8001), and Next.js Frontend (port 3000)
docker compose up -d

# 3. Run the live human-in-the-loop verification harness
cd scripts
../service/.venv/bin/python e2e_live_test.py
```

---

### Option B: Manual Local Development

```bash
# 1. Clone repo
git clone https://github.com/cridiv/varve.git
cd varve

# 2. Start DataHub sample graph (optional)
datahub docker quickstart
datahub datapack load showcase-ecommerce

# 3. Start Postgres
docker run --name varve-postgres \
  -e POSTGRES_USER=varve -e POSTGRES_PASSWORD=varve -e POSTGRES_DB=varve \
  -p 5433:5432 -d postgres:16

# 4. Start Backend & Frontend
cd service && .venv/bin/python main.py   # runs FastAPI on http://localhost:8001
cd app && npm run dev                    # runs Next.js on http://localhost:3000

# 5. Run the full end-to-end verification harness
cd scripts && ../service/.venv/bin/python e2e_live_test.py
```


## What We Learned Building This

Constraining where the model is allowed to act made the system easier to trust, not harder to build — every finding's validity and severity are answers you can check by hand, and the LLM is only ever asked to do the one thing language models are actually good at: write a clear sentence from a clear fact.

The valuable signal was never in any single table alone. Lineage events aren't new information — DataHub already has them. Incidents aren't new information — most teams already track them somewhere. The join between the two, at the right scope, is what turns "this looks undocumented" into "this exact pattern has cost this team money before." Extending that same join across evidence tiers — organizational, actor-specific, and industry-general — is what let the same discipline hold even for a team with no history yet.

We also learned, catching it ourselves before it reached a demo, that a fallback is only honest if it's actually evaluated, not just inherited. An early version of the industry-general tier silently passed through a provisional severity guess unchanged. Fixing that — making the fallback tier subject to the same evidentiary thresholds as validated data — turned out to be one of the more important corrections in the whole build, and is now one of the system's independently verified behaviors.


## What's Next

- Learn pattern-severity weighting from an organization's own accumulated incident outcomes over time, rather than hand-tuned thresholds.
- Extend cross-model correlation beyond shared actors to shared upstream data sources.
- A Slack/PagerDuty integration so a validated high-risk finding can page its routed owner directly, not just appear on a dashboard.
- Push the `ValidatedRiskPattern` RFC into an actual conversation with DataHub's maintainers.


## Track Fit

This directly answers the **Production ML Agents** track: Varve reads DataHub's end-to-end ML lineage, ownership, and governance metadata via the MCP Server / Agent Context Kit, and its entire output is built to catch silent, undocumented risk before it costs money — ranked by real precedent, honestly labeled by evidence tier, self-improving from normal use, and written back to DataHub so the next engineer or agent inherits exactly what was found.


*Open source under the [Apache 2.0 License](LICENSE).*
