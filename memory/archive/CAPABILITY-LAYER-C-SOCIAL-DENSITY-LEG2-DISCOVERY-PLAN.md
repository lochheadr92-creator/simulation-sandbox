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

### SELECTED CANDIDATE (2026-07-27) — widen `cooperate` ACTOR participation

**Approved in principle by Ryan, option (a): targeting is the lever. Acceptance
stays strictly on actor participation; pair effects are observation only. No
implementation authorised. Frozen-hash authorisation WITHHELD.**

**Root cause (VERIFIED).** `cooperate` eligibility is *conferred by being asked*:
`build_social_action_proposal:338-347` creates the `request_help` commitment with
`creator_id = requester`, `beneficiary_id = target`, and `RESPOND_HELP`
(`living_settlement_domain.py:334-344`) gates on `beneficiary_id == entity_id`.
`REQUEST_HELP` (`:324`) selects `visible_person_ids[0]` — the alphabetically
lowest visible id. Measured `cooperate` commits follow the sort prefix exactly:
`person-000` 256 / `person-001` 50 / `person-002` 12 (seed 1) and 241 / 104 / 12
(seed 2). The caste hypothesis is FALSIFIED — the blocker is a placeholder
tiebreak inside Layer C, not `stage6_role` and not `living_action_counts`.

**Change surface — exactly one, VERIFIED by grep.** `target_id =
visible_person_ids[0]` is a DUPLICATED expression, not a shared helper: separate
assignments at `:324` (REQUEST_HELP), `:402` (warn, PARKED), `:413` (lie), `:436`
(share_information), `:451` (trade), `:460` (threaten). Editing `:324` touches
REQUEST_HELP only. **SCOPE GUARD:** the shared variable `visible_person_ids =
sorted(people)` (`:259`) must NOT be modified — re-sorting it would silently
touch all six sites including PARKED `warn`.

#### Pre-registration (written BEFORE any run)

**2a — candidate rules considered.** Perception already exposes, per observed
person: `observed_subject_id`, `distance` (Manhattan, computed at
`living_agent_cognition.py:240`), `confidence`, `properties`. Observer state adds
`relationships` (familiarity / trust / affection / kinship /
perceived_reliability), `commitments`, `memories`.

| rule | reads | parameter-free | Behaviour-Bible | assessment |
|---|---|---|---|---|
| **R1 nearest visible** (min `distance`, tie lowest id) | observation `distance` | **YES** | PASS — spatial state | **selected** |
| R2 highest trust | `relationships[].trust` | YES | PASS | rich-get-richer risk: asking whom you trust raises trust → may NARROW |
| R3 kinship-first | `relationships[].kinship` | YES | PASS | kinship is genesis-fixed → narrows to siblings; reproduces the caste pattern just falsified |
| R4 most familiar | `relationships[].familiarity` | YES | PASS | same feedback risk as R2 |
| R5 least-recently-asked | prior request targets | YES | PASS | needs NEW retained state (`decision_history` is compact, bounded 12, records no target) → not extend-only |
| R6 perceived reliability | `relationships[].perceived_reliability` | YES | PASS | same feedback risk as R2 |
| R7 nearest, tie-broken by trust | distance + trust | YES | PASS | strictly larger surface than R1 for no established gain |
| — random among visible | RNG | n/a | **FAIL** | disqualified on sight — diversity must trace to state, not noise |

**2b — pre-registered rule: R1, nearest visible person, tie-break lowest id.**
Chosen because: (i) parameter-free, so Invariant 12(b) is satisfied trivially;
(ii) it reads a field perception already computes — no new state, no registry, no
schema bump, maximally extend-only; (iii) it is the most defensible *behavioural*
reading of the placeholder — a hungry person calls to whoever is actually near
them, i.e. agents acting on their own perception, squarely Layer C's charter;
(iv) it widens through spatial dynamics that already vary, whereas R2/R4/R6 risk
narrowing via feedback and R3 is genesis-fixed. **BINDING: if R1 fails its
pre-registered check, that is a RESULT — no second candidate in the same
session.**

**2c — N derivation METHOD (number NOT chosen here).**

1. Shadow over the **unmodified baseline** run, both seeds, 1,200 ticks: at every
   decision where `REQUEST_HELP` was actually generated, additionally compute
   `argmin distance` over the observed person set (tie lowest id). Log it; never
   use it.
2. Per 1,000-tick window, count **distinct shadow-selected persons**.
3. **N := the MINIMUM of that distinct-count across all windows and both seeds**
   — the worst window, matching "fires in EVERY 1,000-tick window".
4. **Concentration ceiling := the MAXIMUM shadow top-person share** across
   windows and seeds; a modified run must come in at or below it.
5. **If the shadow distinct-count is ≤ 3 in any window, R1 does not widen → the
   pre-registered check FAILS, report and stop.**

*Comparator caveat:* `repay` and `request_help` reach 8/8, but neither is
targeting-gated on the actor side — everyone gets hungry, everyone incurs
obligations. `cooperate`'s actor role is CONFERRED BY SELECTION, so 8 bounds what
the world can do, not what the responder role can. N therefore comes from the
responder-side distribution above, not from that comparator.

*Non-circularity, for the record:* N is derived from **baseline (unmodified)**
state via a read-only shadow that never influences selection; validation would
run against a **modified** trajectory. Different runs, different datasets — the
derivation cannot be tuned to its own validation.

#### Acceptance classification (replaces the earlier two-surface split)

| outcome | verdict |
|---|---|
| Surface 1 fails to widen decision-stage actors | **REJECT** |
| Surface 1 passes, but committed actors remain ≤ 3 on EITHER seed | **INCONCLUSIVE** — Layer A throughput blocks player-visible proof |
| Both surfaces pass | eligible for contract ratification |

Rationale: as first written the leg could pass its own gate while a player sees
nothing change, because ~56–70% of widened decisions are refused at the
whole-blob `living_agent` CAS. That collides with project rule 1 (GAMEPLAY
FIRST). **INCONCLUSIVE is NOT a licence to attempt any Layer A remedy inside this
leg** — it records the blocker and stops.

#### Player story (requester-side)

> Today every hungry villager calls the same name. One villager answers between
> two-thirds and four-fifths of all calls, and five of the eight never help
> anyone. After this change a hungry villager calls to whoever is actually near
> them, so help comes from across the camp instead of from one perpetual carer —
> and the player can see why, because the person who answers is the person who
> was closest.

### RATIFIED CONTRACT — R1 (2026-07-27)

**Ratified rule.** For `REQUEST_HELP` **only**: from the existing eligible
visible-person set, select the person at minimum existing spatial distance from
the requester; on an equal-distance tie, select the lowest deterministic entity
ID within that nearest cohort. Existing ID ordering survives **only** as a
deterministic equal-distance tiebreak. Eligibility is unchanged; `RESPOND_HELP`
is unchanged; `warn` is unchanged; no shared helper is extracted.

| ratified parameter | value | derived from |
|---|---|---|
| **N** (distinct actors) | **8** | MIN distinct shadow-selected persons per window, across windows and both seeds |
| **decision-stage concentration ceiling** | **0.528** | MAX shadow top-person share |

**Three-way verdict (binding).** Surface 1 fails → **REJECT**. Surface 1 passes
but committed `cooperate` actors ≤ 3 on either acceptance seed → **INCONCLUSIVE**
(Layer A throughput blocks player-visible proof; **no Layer A remedy inside this
leg**). Both pass → **ACCEPTED**.

**Player story (requester-side).** Today every hungry villager calls the same
name; one villager answers between two-thirds and four-fifths of all calls and
five of the eight never help anyone. After this change a hungry villager calls to
whoever is actually near them, so help comes from across the camp — and the
player can see why, because the person who answers is the person who was closest.

**N comparator caveat.** `repay` and `request_help` reach 8/8 but are not
targeting-gated on the actor side. `cooperate`'s actor role is CONFERRED BY
SELECTION, so 8 bounds what the world can do, not what the responder role can.

**Two DIFFERENT surfaces — do not conflate.**
- *Selection-side calibration* (where N=8 and 0.528 come from): a read-only
  shadow over **baseline, unmodified** runs, measuring **who gets ASKED**.
- *Decision-stage acceptance* (what the gate tests): **modified** runs, measuring
  **who DECIDES `cooperate`**. Being asked confers eligibility; it does not
  guarantee a decision. Measured baseline conversion is lossy — seed 1 had 6
  distinct persons asked but only **3** ever decided `cooperate`.

**Population-ceiling / death-fragility risk.** N=8 equals the full population, so
the gate has no headroom for a death. Seed 2 loses one person during window 1
(`alive_person_ticks` 1,434 of a possible 1,600).

**R2 deferred.** A state-derived tiebreak is **out of scope for this leg** and is
recorded as a *character-quality* limitation, not a participation one: measured
tiebreak reach headroom is **zero** (R1 reaches 8; the cohort union is 8), and
100% of R1's widening is attributable to the distance filter. R2 would rebalance
frequency only.

#### AMENDED ACCEPTANCE GATES (ruling 2026-07-27) — supersedes the two-surface split

**Horizon.** Acceptance runs at **3,000 ticks** per required seed and scenario,
using exactly three complete windows: 1–1,000, 1,001–2,000, 2,001–3,000. The
1,200-tick runs were calibration/diagnostic only; their 200-tick partial window
is NOT an acceptance window. 3,000 ticks is the contract's ratified horizon, not
an extension.

**Surface crossing corrected (VERIFIED).** N=8 and 0.528 were derived from
counterfactual `REQUEST_HELP` *target selections*, not from actual winning
`cooperate` decisions. They therefore belong to a **selection/mechanism**
surface and must NOT be applied to decision-stage `cooperate` actors.

**SURFACE 0 — `REQUEST_HELP` targeting mechanism.** Per complete window, the
*required survivor set* = identities of all people alive at the END of that
window. Every survivor must appear **at least once** as an actual selected
`REQUEST_HELP` target in that window — an **identity-based** gate, so a count may
not pass by including someone who died while omitting a living person. Actual
top-target concentration must be **≤ 0.528** in every complete window.
Operationally `N_window` = people alive at window end, capped at the scenario
population ceiling of 8. This must NOT be weakened via minimum concurrent
population, average population, alive-person-ticks, or whole-run union coverage.
The dynamic survivor denominator is **not** permission to cause deaths — C-6
remains a separate binding gate.

**SURFACE 1 — actual `cooperate` decision participation.** Verified baseline is
**3** distinct `cooperate` actors across both prior seeds. No decision-stage N or
ceiling was ever calibrated, so none is invented and no selection-side value is
imported. Operational threshold: **≥ 4 distinct winning `cooperate` actors per
complete window** — the smallest strict improvement over the verified baseline of
3. Reported but NOT gated: per-actor winning counts, decision-stage top-actor
concentration, absolute winning-decision count, and the selected-target →
winning-actor conversion.

**SURFACE 2 — committed player-visible result.** Distinct committed `cooperate`
actors must **exceed 3** on every required seed. Also reported: per-actor
committed counts, committed top-actor concentration, absolute committed count,
refusal rate, refusal-reason histogram, and unique ordered pairs (observation
only).

**Binding classification, applied in order:**

| # | condition | verdict |
|---|---|---|
| A | Surface 0 fails | **REJECT** — R1 failed to reproduce its calibrated targeting effect |
| B | Surface 0 passes, Surface 1 fails | **INCONCLUSIVE — ASK→DECIDE conversion blocks decision-stage proof** |
| C | Surfaces 0 and 1 pass, Surface 2 fails | **INCONCLUSIVE — Layer A throughput blocks player-visible proof** |
| D | Surfaces 0, 1 and 2 pass | **ACCEPTED** |

A survival-dominance, character-envelope, determinism, or unattributable-hash
failure independently blocks acceptance regardless of the three surfaces. Neither
INCONCLUSIVE verdict licenses a repair to Layer A, or to scoring, motivation,
eligibility, goals, priorities, or any Stage 6 path, inside this leg.

**Death claim, stated precisely.** A person dying partway through a window does
not by itself make eight distinct window-level actors impossible, if that person
acted before dying. But any *later* window beginning with seven people cannot
contain eight distinct living actors, so a fixed decision-stage N=8 is
structurally incompatible with a surviving population below eight. The
identity-based end-of-window survivor set removes that false impossibility
without hiding survival regressions; C-6 still decides whether the death itself
is acceptable.

#### R1 SHADOW RESULT (executed 2026-07-27; evidence `leg2_r1_target_shadow_seed{1,2}_1200.json`)

**Neutrality VERIFIED, both seeds.** The shadow reproduced the committed
unmodified Phase 3 hashes byte-for-byte —
`4efe6c5080704633fd5806e70ee9560b79a7294664caca0d5228cd3e108d2a21` (seed 1) and
`8d900c97dbf349ed0ff583003963d4c9367bb836f43a31d91bb1bc33014669ca` (seed 2),
`replay_matches_entities: true` on both.

**Pre-registered derivation executed as written:**

| quantity | value |
|---|---|
| **N** := MIN distinct shadow-selected persons per 1,000-tick window, across windows and both seeds | **8** |
| **concentration ceiling** := MAX shadow top-person share | **0.5278** |
| FAIL check — any window ≤ 3 distinct | **False → R1 PASSES** |

| | baseline (actual) distinct / top share | R1 shadow distinct / top share |
|---|---|---|
| seed 1 w0 | 6 / 0.8013 | **8** / 0.3646 |
| seed 1 w1 | **3** / 0.7856 | **8** / 0.3604 |
| seed 2 w0 | 7 / 0.7391 | **8** / 0.3663 |
| seed 2 w1 | 5 / 0.6701 | **8** / 0.5278 |

**Cohort-min vs global-min decomposition** (added after the rule was
pre-registered; measures how much of the change is distance vs the surviving
lowest-id tie-break):

| bucket | seed 1 | seed 2 |
|---|---|---|
| `tiebreak_reproduces_baseline` (global-min inside cohort) | 1,072 (43.6%) | 1,276 (50.0%) |
| `tied_global_min_excluded` — distance did the work | 874 (35.6%) | 657 (25.8%) |
| `unique_nearest_differs_from_global_min` | 401 (16.3%) | 449 (17.6%) |
| `unique_nearest_same_as_global_min` | 111 (4.5%) | 168 (6.6%) |

Cohort-size histograms show ties are the norm — a unique nearest person occurs in
only 512/2,458 (seed 1) and 617/2,550 (seed 2) decisions, so the tie-break is
*active* in roughly three-quarters of all decisions.

**Tie-break headroom: ZERO on both seeds.** Persons reached by R1's lowest-id
tie-break = 8; persons appearing in any nearest cohort = 8. A state-derived R2
tie-break could not reach anyone R1 does not already reach; it could only
rebalance frequency.

**Structural note (VERIFIED by construction, not merely observed):** R1 can
differ from baseline *only* when the distance filter excludes the global-minimum
id, because the lowest-id tie-break always re-selects that id whenever it remains
in the cohort. Therefore **100% of the widening is attributable to the distance
filter and 0% to the tie-break.** The tie-break's residual effect is to *dampen*
widening and leave an alphabetical gradient (seed 1 shadow: `person-000` 894 …
`person-006` 53).

**Caution on N.** The pre-registered method returned N = 8, which equals the full
population, so the gate has no headroom for a death. Seed 2 loses one person
during window 1. Recorded as a property of the derivation, not a reason to change
a pre-registered method.

#### Derivability status (checked BEFORE commissioning any probe)

The counterfactual "which person would rule R have selected instead" is **NOT
COMPUTABLE** from captured evidence for any state-derived rule: no run record
holds per-(tick, observer) visible-person sets, positions, or relationship maps.
`causal_neighbourhoods[*].target_ids` gives ACTUAL targets for ≤32 committed
firings only; the warn probe's `nearest_person_distance` is scout-only,
distribution-form, and carries no identities. A Step-3 shadow probe is therefore
REQUIRED to execute 2c.

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
