# Layer C, Social Density Leg 2 — Singleton-Family Discovery Plan

**Status: PROPOSED — discovery plan only. Nothing here is authorised until a
contract STOP. Leg numbering is provisional; `FRONTIER.md` owns the frontier.**

Relationship to Leg 1 (`CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG1.md`, CONFIRMED,
implementing): complementary, not competing. Leg 1 wakes the dead
`STORE_SURPLUS` intent (threshold-only, genesis-endowment-bounded per its §9
amendment). This plan targets what Leg 1's candidate table does not touch: the
**singleton action family** — warn, share_information, lie, promise, apologise,
reconcile, threaten — each committed exactly once in the 5,000-tick control and
never again. (trade is excluded here: food-coupled, Stage 9 F-A. store is
Leg 1's subject.) An earlier draft of this plan listed storage out of scope for
the whole social-density arc; the user's Leg 1 confirmation supersedes that
line for Leg 1's bounded reachability goal, and the substance agrees — Leg 1's
own amendment records that sustained storage traffic remains F-A-gapped.

Provenance of this plan: cloud-session chat, 2026-07-27; two external
adversarial review rounds (funnel design and two clarifications) recorded in
the project doc `claude/SOCIAL-DENSITY-LEG-PLAN.md` (mirror; THIS file is
canonical once committed).

## Evidence base (VERIFIED — memory/evidence/layer-c-social-density-leg1/)

From `baseline_collective_groups_5000.json` (post-age-leg HEAD 180c43f4,
replay-verified at 1k/3k/5k, 0.59 s/tick):

- Recurring social actions, rate flat with horizon: cooperate ~266–298/1k
  ticks, repay ~136–178/1k, request_help ~160–211/1k → sparsity of the rest is
  NOT a horizon artifact. "Healthy" is PROVISIONAL: concentration unmeasured;
  repay 776 vs apologise 1 makes a narrow-loop hypothesis live.
- Singleton family: exactly 1 firing each at tick 1,000, unchanged at 5,000.
- World thins at horizon: 2 of 8 dead by tick 5,000 → all recurrence metrics
  pair per-alive-person-tick rate WITH absolute counts and unique actor/pair
  coverage per window.
- group_state.payload_limit binds after ~3k (321 rejections) — cap context
  must be captured before any slice that adds group facts.
- CORE-INTEGRITY-004 noise floor: single-action counts ±28%, accepted ±1.2% →
  statistical gates by default; single-run A/B deltas untrustworthy.

## Phase 1 — Discovery probe (funnel, not matrix)

**Architecture — offline-first.** Run with event capture ON and decision
receipts persisted; derive funnel stages C–H offline from those records
(receipts already hold every candidate, score, rejected alternative). In-loop
probes exist ONLY for stages A–B (semantic opportunity present; prerequisite
gate evaluations) — the entire neutrality risk surface. Reuse Leg 1's probe
pattern (`_probe_layer_c_social_density.py`): live census, immediate replay,
matched on/off neutrality comparison (Leg 1's shadow achieved identical hashes
— the standard this probe must meet).

**Funnel, per action type, with conservation checks:**

    A semantic opportunities
    B gate evaluations (ALL gate-failure counts, never first-false only)
    C candidate generated
    D accepted for scoring
    E won / lost
    F preempted / invalidated / rejected
    G committed
    H persisted/visible = PRESENT IN THE COMMITTED, REPLAY-VISIBLE CANONICAL
      EVENT RECORD — not player-UI visibility (no UI renders these yet; the
      inspector slice is later; a UI definition would false-negative every
      committed social event)

    Conservation:  generated = rejected_before_scoring + scored
                   scored    = lost + won
                   won       = preempted + invalidated + committed
    Any unmatched count is itself a probe failure and a finding.

Lifecycle pathways are mapped PER FAMILY before counting — the eight actions
are not assumed to share one path; any bypass is a finding.

**Classification** (generated-but-loses / never-generated / wins-but-preempted
/ prerequisite-never-recurs) is a derived SUMMARY of the funnel, applied to
the RECURRENCE question (why no second firing), never forced to one class per
action where multiple failure modes contribute. Precedent: warn's single
firing was wins-but-preempted; its recurrence blocker may be different.

> **CORRECTED 2026-07-27 by Phase 1 measurement.** Two claims above/nearby did
> not survive:
> 1. **"warn's single firing was wins-but-preempted" is FALSE.** Measured on the
>    primary seed: warn was generated once (tick 1), won, and committed with
>    **zero** preemption (`leg2_session2_warn_report.md`).
> 2. **"warn converts every opportunity end to end with zero loss" is
>    seed-specific and FALSIFIED.** That held on the primary seed only; on
>    `living-agents-stage6-alt` the single opportunity won arbitration and was
>    then refused at commit (`precondition.failed`), giving zero warn commits
>    (`leg2_seed2_diagnostic_report.md`). Conversion efficiency is a
>    seed-sensitive quantity, not a mechanism invariant.
>
> warn's recurrence classification — never-generated via semantic-opportunity
> absence — was CORROBORATED across both seeds and is unchanged.

**Staged execution (cost control):**
- **Session 1 — receipts-only funnel:** stages C–H offline from captured
  events + receipts. No in-loop A–B probes built. Neutrality check covers only
  the capture_events flag (~300 ticks on/off, hash + ordered event stream).
  Delivers: C–H funnel, conservation table, reference-family concentration,
  population + cap context.
- **Session 2 — A/B probes ONLY for the never-generated subset:** semantic-
  opportunity definitions built only for actions Session 1 classifies C≈0.
  Each definition derived from the action's own prerequisite semantics,
  evaluated against world state, documented per action so it can be
  criticised. If most singletons are generated-and-losing or preempted, the
  expensive A-layer work is never built.

**Run criteria:** collective_groups, seed living-agents-stage6, scratch DB,
3,000 ticks minimum; extend to 5,000 only if any target action has <20
semantic opportunities (pre-registered heuristic, not a measured constant).
Still <20 at 5,000 ⇒ that action's verdict is **INSUFFICIENT EVIDENCE — a
result, not an abort**: publish its full funnel counts, withhold
classification and causal claims for that action only; adequately-sampled
actions still get classified. One short comparison seed (~1,200 ticks,
heuristic) separates seed pathology from structure — diagnostic, not
acceptance replication.

**Also captured:** causal neighbourhoods (±3 committed events, full competing
candidate set + scores, arbitration, commit result) for firings IN THE PROBE
RUN only — the 5,000-tick baseline persisted no events (capture_events:false),
so historical neighbourhoods are unavailable and are recorded as such, never
reconstructed. Reference-family health per 1,000-tick window for
cooperate/repay/request_help: raw count, per-alive-person-tick rate, unique
actors, unique pairs, top-pair concentration, repeat concentration — the word
"healthy" is withheld unless participation is broad. group_state cap: payload
vs cap, saturation duration, dominant fields, what is trimmed, and whether any
target-action prerequisite reads trimmed state (counters + one code-read,
bounded).

**Abort conditions (broken instruments only):** tracing changes canonical
behaviour; conservation fails to reconcile; a target action bypasses
unobserved stages; evidence files incomplete. Aborts produce a report, not a
table. Insufficient opportunity volume is NOT an abort (see run criteria).

**Cost, stated honestly:** compute ~45–90 min total; engineering one to two
CC sessions (Session 2 conditional on the data); failure budget one instrument
rework (this project's measured base rate for new instruments). The A-layer
semantic-opportunity definitions are the known scope trap — bounded by making
Session 2 conditional.

## Phase 2 — Contract (chosen FROM the funnel, not before)

Smallest coherent slice. Candidate clusters: info-sharing recurrence
(warn/share_information — potentially drivable from decaying, divergent
knowledge that already exists) vs relationship-repair recurrence
(apologise/reconcile/promise — needs recurring guilt/rift evidence). The
funnel decides — including against a possibly-unhealthy reference family: if
the recurring three are a narrow loop, the leg reframes from "raise eight rare
actions" to "widen one habit", a different contract. Contract requirements:
player story; disjoint field ownership registered in
REGISTRY-COMPONENT-OWNERSHIP.md BEFORE implementation; extend-only (no sealed
Stage 6 scorer/mutations edits; C-6 survival dominance); no guessed constants
— N and floors from the probe (Invariant 12(b)).

## Phase 3 — Implementation slices

One purpose per commit, capability gates between slices. Paired visibility
slice with slice 1: render the existing Stage 6 decision receipt in the
inspector (Simple / Detailed / Diagnostics) — read-only projection, zero hash
risk, and the density becomes visible instead of only counted. Fixture rule
(warn lesson): positive fixtures assert COMMIT through the pipeline, never
selection; incidents are recorded, never pinned as invariants.

## Acceptance (statistical, pre-registered at contract time)

- Targeted action types: sustained recurrence — fires in EVERY 1,000-tick
  window of a 3,000-tick run, ≥N distinct actors, per-alive-person-tick rate
  ≥ probe-derived floor, WITH absolute counts and unique actor/pair coverage
  (rate alone can flatter a thinning world).
- Concentration ceilings from the Phase 1 reference-family measurement, so
  density is not achieved by actor-pair spam.
- Behaviour-Bible bars: no personality puppets; diversity traceable to state
  and history, not noise; explanation completeness (receipt-only causes).
- Character envelope vs the 5,000-tick control (entropy, rest fraction,
  deaths); census two-strikes rule stands.
- Replication: 2 seeds × both scenarios before any re-baseline write-up.
- Hash: behaviour-changing ⇒ authorised re-baseline, statistical gate,
  exact-at-genesis / statistical-at-trajectory write-up per 004.

## Out of scope (recorded)

Leg 1's storage mechanism (its own contract governs); trade (Stage 9 F-A);
threaten/conflict escalation (5E) unless the funnel shows it trivially
unblocked; norms/enforcement (Layer E); CORE-INTEGRITY-004 remediation; F1/F4
fixes; RNG-among-top-N; per-entity RNG keying (owed before Stage 11); any
frozen-hash change without explicit authorisation.
