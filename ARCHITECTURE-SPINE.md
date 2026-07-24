# ARCHITECTURE SPINE — Simulation Sandbox

**Status: PROPOSED (2026-07-24).** The operational rules under `THE-SPINE.md`.
The Spine says *what the world needs and where it's weak*; this says *how the
machine must be built so it stops repeating ownership and ordering defects*.
Templates here are populated by the code inventory (§11); this document defines
the structure, not the current contents.

---

## Authority (higher wins on conflict)

1. **Constitution / doctrine** — irreversible rules and prohibited behaviour.
2. **Source of Truth** — canonical truth, events, state, lineage, replay,
   checkpoints, projections, and what may *never* be a truth source.
3. **THE-SPINE.md** — the operational map + current state + frontier.
4. **This document (ARCHITECTURE-SPINE)** — runtime structure, ownership,
   ordering, event lifecycles, scenario/projection mechanics.
5. **Core contracts** — accepted-event and proposal envelopes, validation,
   causal references, deterministic identity and ordering.
6. **Domain contracts** — one domain's observations, candidates, proposals,
   owned state, dependencies, projections.
7. **Scenario manifests** — enabled capabilities + genesis configuration.
8. **Capability contracts** — one bounded, player-visible addition + its gates.
9. **Evidence & close-outs** — prove / defer / reject / supersede claims.
10. **Roadmap & frontier** — sequence only; never redefine truth or architecture.

Superseded records preserve history but stop being active authority.

## The canonical runtime path (Rail A, in full)

Every world transition follows exactly this route. No capability may skip a step;
no domain may mutate canonical state directly; no projection, UI, diagnostic, or
model output may become canonical truth.

```
Scenario Manifest
→ Validated Genesis
→ Core Tick Scheduler
→ Pinned Read-Only Observation Frame   (end of tick T-1)
→ Domain Activation
→ Candidate Generation
→ Proposal Construction
→ Deterministic Proposal Ordering       (requested_time, phase, priority, content_hash)
→ Core Validation
→ Atomic Acceptance or Rejection
→ Accepted Event
→ Canonical State Mutation               (single-writer: core/mutations.py)
→ History, Causality, Replay Records
→ Read-Only Projections
→ World View / Inspector / Event Log / Causal Chain / Replay
→ Verification & Acceptance Evidence
```

## Core vs domains

**Core owns:** simulation time; deterministic identity + ordering; the pinned
observation frame; validation; atomic commit; accepted/rejected records; canonical
serialization + hashing; replay/resume; lineage/checkpoints. Core does **not**
decide domain behaviour.

**A domain MAY:** read its declared inputs; generate candidates; score/select
deterministically; construct proposals; validate its own semantics; project
accepted state.
**A domain MAY NOT:** write storage directly; read mutable hidden state; depend on
wall-clock; invent unrecorded randomness; mutate another owner's component without
an accepted cross-owner contract; treat a projection as truth.

## Canonical state = owned components

Every canonical component must declare: schema name + version; allowed entity
types; **one** owning domain (or Core); the event families that may change it; a
validation function; capacity + compaction policy; projection policy; a replay
test; a migration policy. **Ad-hoc fields with no owner are prohibited** — that is
the CORE-INTEGRITY-001 class.

## The three protective registries (templates)

Indexes, not essays. Each stamped "as of `<commit>`".

**1. Component Ownership Registry** — the direct control against lost updates.
```
| Component / Field | Entity Type | Canonical Owner | Current Writers | Legal Cross-Owner Writes | Collision Risk | Tests |
```
Must cover at least: `action`, `living_agent`, `hunger`, `thirst`, `fatigue`,
`carried_resources`, relationships, memories, knowledge, group membership, group
state, norm records, carriage records, structures, shared storage.

**2. Domain Ordering Registry** — ordering *relationships* are the contract;
priority numbers are just their implementation.
```
| Domain | Phase | Priority | Reads | Writes | Must Run Before | Must Run After | Reason (evidence protected) |
```
Tests assert relationships — "aid observes before any writer overwrites the
observed action", "registry Z commits before its upstream producer changes state"
— **never** merely `priority == 5`. Changing a priority is an architectural change.

**3. Event Family Registry.**
```
| Event Family | Producer | Validator | Canonical Mutations | Causal Parents | Lifecycle | Projection | Replay Handler |
```
Also records schema version, identity rule, preconditions, rejection reasons,
terminal states, compaction anchors. Stops new capabilities inventing inconsistent
event paths.

## Scenario manifests

A scenario is **configuration, not architecture**. Each manifest declares: genesis
entities; environment; enabled domains; enabled capability versions; deterministic
seed; scenario-specific limits; player-facing description; expected baselines;
required projections; known exclusions. A scenario may enable/disable capabilities;
it may **not** redefine Core semantics or silently change a domain contract.
(Summarized in the Scenario Capability Registry.)

## Projections

Read-only views of canonical records: world state, entity inspector, cognition/
decision trace, relationships, groups/culture, resources/economy, event log,
causal chain, replay timeline, developer diagnostics. **Every capability names the
projection through which the player sees it** (Rail D). No visible projection ⇒
incomplete, unless explicitly classified as infrastructure for an approved visible
slice.

## Capability delivery lifecycle

Every capability passes the same gates; an agent cannot authorize its own contract.

0. **Player story** — what becomes visibly different (else join to a visible slice
   or classify as approved infrastructure).
1. **Discovery** — does the trigger occur organically? actor/scenario spread,
   existing vs missing mechanics, dependencies, ordering/ownership risks. *No code.*
2. **Contract** — event sequence, ownership, validators, ordering, capacity,
   projection, acceptance gates, rollback rule, named GAPs. *No guessed constants.*
3. **Authorization** — owner authorizes / revises / defers / rejects.
4. **Implementation** — only the authorized contract; no opportunistic expansion.
5. **Verification** — risk-selected: focused → integrated pipeline → deterministic
   run → repeat/replay/resume → frozen baseline → same-frame churn → full suite →
   organic acceptance run. A failed gate is never renamed a pass.
6. **Disposition** — exactly one: VERIFIED / PARTIAL / DEFERRED / REJECTED.
7. **Close-out** — commits, evidence, hashes, tests, limitations, risks, rollback
   state, roadmap move, re-entry conditions. **The frontier moves only in the same
   commit series as the close-out.**

### Pre-registered gates & re-baseline (from the aid lesson)

- Pre-register gate *direction* up front; leave *magnitude* a measured value, not a
  pre-picked number (Invariant 12(b)). One evidence-based calibration; failure ⇒
  rollback.
- A frozen-baseline change requires an **explained diff at a STOP** — the new hash
  must be shown to be *caused by the leg* (causal chain), not merely re-recorded. A
  bare re-hash can launder a regression.

## §11 — Registry-build discipline (risk-based, not exhaustive)

Do **not** document every field across the whole engine before returning to
behaviour work. First pass maps only what the current front (Layer C / Upkeep)
touches plus known collision surfaces:

- all domains + their priorities;
- all canonical **person-state** writers (`action`, `living_agent`, `hunger`,
  `thirst`, `fatigue`, `carried_resources`);
- structure + resource writers (`structure_wear`, `living_repair`, the 7D
  `REPAIR_SHELTER` nudge) — Upkeep's direct collision surface;
- group/culture registries (single-owner check);
- event families involved in Layer C;
- known collision cases from 7D and Leg A.

Expand registries in later passes only when a capability touches new territory.

## What must NOT happen during this pass

No folder moves; no repo-wide rename; no Core rewrite; no centralizing every
constant; no replacing domains with a new abstraction; no generic advertisement
framework before Upkeep proves the need; no new constitution-sized documents; no
reopening Aid Exchange; no continuing Stage 8C culture. That is restructuring
theatre. The deliverable of this pass is: one truthful spine, three protective
registries, one frontier — then Layer C.
