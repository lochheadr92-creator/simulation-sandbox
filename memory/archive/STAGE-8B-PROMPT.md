> **⚠ SUPERSEDED — disposable execution aid, not authority (2026-07-24).**
> Replaced by `THE-SPINE.md` + `FRONTIER.md` + `AGENT_WORKFLOW.md`. Retained for
> reference only; do not follow its session ritual or frontier.

---

> **SUPERSEDED** — this prompt is superseded by `memory/STAGE-8-CONTINUATION-PROMPT.md`, which governs the 8B→9 arc. Kept for historical reference only; do not follow it directly.

# TASK: Stage 8B — Norm Transmission (individual carriage, one taught/imitated pathway): contract-first, gate-and-stop

Mode: greenfield-addition inside the live deterministic kernel. This is Leg 2 of the Stage 8 master protocol (`memory/STAGE-8-MASTER-PROMPT.md`) — same rules, same STOPs. This prompt **assumes Stage 8A is implemented, verified, and committed**; Phase 0 verifies that assumption before anything else.

## Context

Repo: `simulation-sandbox`, branch `capability/stage-8-culture` (renamed from `capability/stage-6-living-agents` at the Stage 8 Leg 0 boundary, 2026-07-18). Stage 8A delivered ONE group-scoped `shelter_upkeep_norm` whose transmission is **group-membership-implicit**: a member is covered because the association registry says they are currently a member. Nothing about *how* culture moves between individuals is modelled — a joiner is silently covered, a leaver silently loses it, and no transfer is ever a caused event.

Stage 8B's goal: **norm carriage becomes per-individual and observable.** Who carries the norm becomes canonical state; how they came to carry it becomes a caused, committed, inspectable event chain (learned from whom, via which interaction, at which tick). Culture must be shown to outlive its originators — a norm persisting through membership turnover via individual carriers, not via a membership lookup.

## Authority and reading order (binding)

1. `memory/SOURCE-OF-TRUTH-v2.md` — architecture authority.
2. `memory/STAGE-8-MASTER-PROMPT.md` — the leg protocol, Stage 9 boundary, and global invariants (all apply verbatim here).
3. `memory/CAPABILITY-STAGE-8A-EMERGENT-NORMS.md` — the delivered 8A contract, its verified results, recorded hashes, and constants. 8B builds on it and must not silently change it.
4. `memory/CAPABILITY-STAGE-7D-GROUP-GOALS-LEADERSHIP.md` + `memory/STAGE-6-LIVENESS-PASS.md` — the defect history (ordering, forged fields, focused-tests-bypassing-the-pipeline).
5. `memory/CAPABILITY_ROADMAP.md` — Stage 8 goals ("teaching", "imitation", "generational knowledge transfer") and global completion rules.

## Phase 0 — Preflight: verify the "8A is done" assumption (gap-stop if false)

1. `git log` shows the 8A leg committed (substance separated from any churn commits); working tree clean or attributable.
2. The 8A doc status is promoted past PROPOSED with verified results and **recorded `collective_groups` hashes** — capture those hashes as the 8B baseline.
3. Full backend suite green; note the count. Frozen `living_settlement` 320-tick hash present and matching (`84d3ad52…c32d2` unless a later authorised re-baseline superseded it — use whatever the docs record as current).
4. The adversarial-review findings from the 8A leg are closed (fixed or explicitly waived in the doc), none open.

If any check fails, STOP and report — this prompt was issued on the assumption they pass. Do not "finish 8A quickly" under this prompt; that is the 8A leg's prompt, not yours.

## Phase 1 — Probes: measure before you design (no constant without a distribution)

Run read-only probes (pattern: `backend/tools/_probe_*.py`) against the committed pipeline, seed `living-agents-stage6`, 1,000-tick `collective_groups`, and paste the measured outputs:

1. **Membership turnover** of norm-holding groups: joins and leaves after norm formation, per group, with tick timestamps. This is the phenomenon 8B must ride; if turnover is ~0, transmission has nothing organic to prove and you STOP with that evidence and options (longer horizon, different grounding) rather than seeding behaviour.
2. **Interaction opportunity**: counts of existing 6C/6D interaction events (which types actually fire — from the interaction-memory / social seams) between current norm carriers (today: members of norm-holding groups) and non-carriers, especially around the norm shelter context. The transmission trigger must ride an event type that demonstrably fires.
3. **Lifecycle activity**: births and deaths in the horizon (`lifecycle_domain`). Zero births in-horizon ⇒ generational transfer is recorded **Deferred — demography-blocked (Stage 11)** in the contract, with this probe as evidence. Evidence decides, not ambition.
4. **Norm timeline** from the 8A run: formation ticks, decay/expiry events, membership sizes at formation — the windows transmission constants must fit inside.

## Phase 2 — Contract: write `memory/CAPABILITY-STAGE-8B-NORM-TRANSMISSION.md`, then STOP for confirmation

Mirror the 8A doc structure exactly (goal, organic-reachability evidence, agency model, mechanism, commit ordering, validation, contracts table, constants table each justified by a Phase 1 measurement, registry schema, non-goals, acceptance gate, risks). Status: PROPOSED. Contract decisions this leg must resolve — with a recommendation and evidence, per the conflict rule:

1. **The eligibility fork (the central decision).** After 8B there is exactly ONE source of truth for norm-influence eligibility — no dual path where both "current membership" and "carriage records" can grant the nudge. The default recommendation to argue for or against: **carriage-only**, with formation deterministically backfilling carriage records for members at formation tick (preserving 8A's proven behaviour at the moment of formation), and post-formation coverage acquired only through transmission events. This deliberately changes the semantics 8A shipped for late joiners (implicit coverage → must learn); say so explicitly in the doc, record the expected `collective_groups` hash change, and justify it as the honest model. If evidence favours keeping membership-implicit and layering carriage as observation-only records, argue that instead — but one owner, stated in the doc.
2. **One transmission mechanism, not two.** Pick teaching (carrier-initiated, deliberate) or imitation (observer-initiated, learning by watching) — whichever the Phase 1 interaction probe shows has an organically firing substrate. The other is a named non-goal for a later leg. Same "smallest honest step" discipline as 8A's one norm type.
3. **Trigger semantics — deterministic, counted, no probabilities.** Transmission commits on a counted condition (e.g. the Nth qualifying carrier↔non-carrier interaction, N from the probe distribution), keyed-RNG-free or keyed-RNG-only per the kernel's rules; never wall-clock, never random-uniform "chance to learn".
4. **Where carriage lives**: extend `group-norm-registry-v1` (schema-versioned bump) or a new bounded registry — justify by size math (cap, payload target, ≥20% measured headroom, deterministic compaction). Every carriage record carries provenance: `learned_from`, `via_event_id`, `learned_tick` (or `backfilled_at_formation`).
5. **Commit-order analysis**: which upstream registries the transmission evaluation pins (association, group_state, group_goal, group_norm, interaction-memory), the engine_priority chosen so pinned upstreams commit after it (the 87-before-88/89/90 discipline, extended), and every one-tick lag documented.
6. **Decay interaction**: what happens to individual carriage when the group norm weakens/expires or the group dissolves — carriage may outlive the group norm (that IS "culture outlives its originators") but its influence guard, decay, and eventual expiry must be explicit, bounded, and Core-committed.

STOP. The contract is confirmed by the user before implementation.

## Phase 3 — Implement (only after contract confirmation)

Contract-conformant, proposal-only, through existing seams. The influence hook change in `living_settlement_domain.py` keeps the exact survival-dominance guard semantics 8A verified; `living_settlement` stays inert (no registry ⇒ unchanged behaviour ⇒ frozen hash safe).

## Phase 4 — Verify (the gate; every item pasted, not claimed)

1. Focused 8B tests: transmission trigger at exactly N (not before), provenance correctness, backfill-at-formation, eligibility source exclusivity (a covered-but-non-carrier entity is NOT nudged, or vice versa per the decided fork), carriage decay/expiry, dissolve behaviour, forged-field rejection (carrier ids, learned_from, tick), duplicate idempotence, capacity bound, replay + resume reconstruction.
2. **Integrated full-kernel test through same-frame upstream churn** — association + group_state + group_goal + group_norm revision bumps plus the 8B proposal in one frame through the real commit pipeline. Mandatory; focused-only verification is a named historical defect.
3. End-to-end causal chain proof: one test (or measured run assertion) walking norm formation → carrier → qualifying interaction → transmission event → new carrier → influence firing on the new carrier, entirely from committed records.
4. Organic proof, unseeded 1,000-tick `collective_groups`: ≥1 transmission event fires organically; a post-formation joiner (or surviving carrier, per the fork) is verifiably influenced; 0 deaths; counts measured and pasted.
5. Regression: full backend suite green; 8A focused suite green untouched (or updated only where the confirmed contract changes behaviour — every such test listed in the report).
6. Determinism: repeat + replay + resume equality with 8B enabled; frozen `living_settlement` hash byte-identical; new `collective_groups` hashes recorded in the 8B doc.

## Phase 5 — Adversarial review, then close

Independent review (Codex or equivalent) of the branch diff against the contract. Findings fixed ⇒ **re-run the full Phase 4 gate** (fixes invalidate prior run evidence) ⇒ commit per discipline ⇒ update the 8B doc status, the master-protocol frontier, and `CAPABILITY_ROADMAP.md` in the same commit series ⇒ close-out report (STATUS with evidence labels / CHANGES / RISKS / NEXT STEP) ⇒ STOP for the user's go on 8C.

## Do NOT touch / do NOT build

- No second norm type, no values/taboos, no enforcement, no cross-group diffusion, no myths/rituals — 8C/8D material.
- No Stage 9 anything (surplus, ownership, trade), no 7C unblocking, no institutions, no player-facing, no LLM-generated canonical state.
- No changes to 7A–7D registry schemas, caps, or priorities; no 8A constant changes without a contract-recorded, evidence-backed decision at a STOP.
- No `living_settlement` dynamics changes (frozen hash stays); no destructive git, ever.

## On missing data or ambiguity

STOP and report. No invented constants, no probability shortcuts, no new store to route around a full registry, no silent semantic changes to 8A. If probes contradict this prompt's framing (e.g. zero turnover), that is a finding to report with options — not a licence to seed the behaviour.

## Commit discipline

One leg, one purpose; reviewable commits in the house style (`feat(stage-8b): …`); nothing committed past a failing gate, an open review finding, or an unresolved STOP; doc updates ship with the behaviour they describe.

## Assumptions made (veto any that are wrong)

1. The 8A leg closed clean (committed, verified, reviewed) — Phase 0 verifies rather than trusts, and stops if it didn't.
2. Work continues on the same branch as 8A unless the 8A close-out renamed it.
3. One transmission mechanism in 8B (teaching OR imitation, probe-decided); the other is deferred by name.
4. Carriage-only eligibility with deterministic formation backfill is the recommended resolution of the fork — the contract may overturn it with evidence, and the user ratifies either way at the Phase 2 STOP.
5. Generational transfer ships in 8B only if the lifecycle probe shows in-horizon births; otherwise Deferred — demography-blocked (Stage 11).
6. The adversarial reviewer remains Codex or an equivalent independent agent.
