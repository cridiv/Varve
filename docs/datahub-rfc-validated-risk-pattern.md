# RFC: `ValidatedRiskPattern` — a native DataHub aspect for evidence-backed risk history

**Status:** Proposal + reference implementation (built as part of Varve, submitted to
the DataHub Agent Hackathon, Production ML Agents track)
**Author:** [your name]
**Related:** `docs/validation.md`, `service/services/correlation_service.py`

---

## Summary

DataHub's metadata model can describe *what* an entity is and *what changed on it,
when*. It has no first-class way to describe a third, distinct kind of fact:
**this shape of change has, empirically, preceded a real incident before — N times,
with an average detection lag of D days.**

Today, every agent that wants to reason about historical risk has to invent its own
private convention for storing that judgment, usually buried in free-text notes or
kept entirely outside DataHub. This RFC proposes `ValidatedRiskPattern`: a small,
structured aspect that lets any agent attach evidence-backed risk history directly
to a DataHub node, in a form every other agent can read and build on.

Varve is the first consumer, and this document doubles as the reference
specification for how it writes and reads the aspect.

---

## Motivation

A platform team's real risk knowledge is almost always tacit — held in the memory
of whoever was on call, in a Slack thread, in a post-mortem doc nobody revisits.
DataHub already unifies *lineage* and *ownership* as first-class, queryable
context. Risk precedent — arguably the single most actionable piece of context
for a team deciding where to look first — has no equivalent home.

Without a standard shape for this, every agent working in this space (Varve
included) is forced to either:

1. Keep the evidence in a private database, invisible to any other tool reading
   the same DataHub node, or
2. Write it as unstructured free text on a node's description or a generic note,
   which is readable by a human but not reliably queryable or composable by
   another agent.

Neither is good enough for a context platform whose stated goal is that "every
agent, one source of truth." This RFC closes that specific gap.

---

## Proposed aspect

```json
{
  "aspectName": "validatedRiskPattern",
  "type": "record",
  "fields": [
    { "name": "patternType", "type": "string",
      "doc": "e.g. 'departingEngineerChange', 'staleThreshold', 'orphanedExperiment', 'reactiveFix'. Extensible — not a closed enum, so new agents can register new pattern shapes without a schema migration." },

    { "name": "scopeKey", "type": "string",
      "doc": "What this evidence is scoped to: a specific model/dataset urn, a specific actor, or the literal string 'org_wide'. Lets a consuming agent distinguish 'this exact model has a history' from 'this exact person's changes have a history' from 'this pattern shape has a history somewhere in the org'." },

    { "name": "timesObserved", "type": "int",
      "doc": "How many times this pattern shape has been observed at this scope." },

    { "name": "timesPrecededIncident", "type": "int",
      "doc": "Of those observations, how many were later linked to a confirmed incident via a causal record (see 'Provenance', below)." },

    { "name": "avgDetectionLagDays", "type": "float", "optional": true,
      "doc": "Average time between the originating change and incident detection, across matched cases." },

    { "name": "evidenceTier", "type": "string",
      "doc": "One of 'org_validated', 'actor_validated', 'industry_general'. Required. This is the single most important field in the aspect — see 'Why evidenceTier is mandatory' below." },

    { "name": "evidenceSourceNote", "type": "string", "optional": true,
      "doc": "Free-text pointer to where industry_general evidence tier numbers came from (e.g. a cited post-mortem or published source). Required in practice whenever evidenceTier = 'industry_general', to keep that tier auditable rather than asserted." },

    { "name": "lastValidatedAt", "type": "timestamp",
      "doc": "When this evidence was last recomputed. Lets a consumer judge staleness." },

    { "name": "sourceAgent", "type": "string",
      "doc": "Which agent computed this (e.g. 'varve'). Multiple agents can co-populate this aspect on the same node without clobbering each other, provided they key their writes by sourceAgent and merge rather than overwrite." }
  ]
}
```

---

## Why `evidenceTier` is mandatory, not optional

This is the field that makes the aspect trustworthy rather than merely convenient.
A raw `timesPrecededIncident: 3` looks identical whether it came from this specific
organization's confirmed incident history or from a hand-sourced industry base
rate — and those are very different strengths of evidence. Making `evidenceTier`
a required field, not an optional annotation, means no consumer of this aspect can
accidentally treat a generic industry number with the same confidence as a
validated, organization-specific one.

This mirrors a design principle already proven out in Varve's own implementation:
every claim the system makes is labeled with how much it should be trusted, and
that label travels with the claim rather than living in a separate document a
reader might miss. `evidenceTier` is that same discipline, promoted from an
internal Varve convention to a property of the shared aspect itself.

---

## Provenance: what "preceded an incident" is allowed to mean

The aspect intentionally does not encode the causal link itself — that belongs in
whatever incident-tracking system the writing agent already uses (in Varve's case,
a `root_cause_event_id` foreign key in its own Postgres store). `ValidatedRiskPattern`
is a *rollup* of that evidence, not a replacement for keeping the underlying
records. Any agent proposing a value for `timesPrecededIncident` should be able to,
on request, produce the specific incidents it counted — this aspect is a summary
a human or agent can act on quickly, not the system of record for the incidents
themselves.

---

## How multiple agents share one node without conflict

Because `sourceAgent` is part of the aspect, a node can carry more than one
`ValidatedRiskPattern` entry — one written by Varve, another potentially written by
a different agent using a different methodology. A consuming agent or human is free
to compare them, or to weight one source over another. This is deliberately not a
single, DataHub-arbitrated "true" risk score — it's a shared, structured place for
multiple agents' evidence-backed opinions to coexist and be inspected side by side,
consistent with DataHub's own stated model of curated context that experts (and,
here, agents) review and refine collaboratively.

---

## Reference implementation

Varve is the first working consumer of this proposal. Its correlation engine
(`service/services/correlation_service.py`) already computes every field in this
spec internally — `patternType`, `scopeKey`, `timesObserved`,
`timesPrecededIncident`, `avgDetectionLagDays`, and (as `evidence_scope` /
`tag_source` internally) exactly the tiered-trust concept proposed here as
`evidenceTier`. What this RFC proposes is promoting that internal shape into a
DataHub-native aspect, written back via `MetadataChangeProposalWrapper` alongside
Varve's existing finding annotations, so the evidence itself — not just Varve's
narrative conclusion — becomes a durable, queryable part of the node's metadata.

A non-functional schema stub matching this spec is included at
`docs/validated-risk-pattern.avsc` for reference against DataHub's existing aspect
definition conventions.

---

## Open questions for DataHub maintainers

- Should `evidenceTier` be a closed enum at the platform level, or left as a
  convention-only string (as proposed here) so new tiers can be introduced by
  agents without a core schema change?
- Should conflicting `ValidatedRiskPattern` entries from different `sourceAgent`
  values be surfaced to a human for reconciliation, similar to how DataHub already
  handles proposed business glossary terms pending review?
- Is `scopeKey` better modeled as a proper reference type (urn) where possible,
  rather than a loosely-typed string that sometimes holds an urn and sometimes
  holds a free-text actor identifier?

---

## Status at submission time

This is a proposal and a reference implementation running against a local DataHub
instance, not a merged contribution. It is submitted in that spirit — a concrete,
working starting point for a conversation with DataHub's maintainers, not a claim
that this exact shape is final.
