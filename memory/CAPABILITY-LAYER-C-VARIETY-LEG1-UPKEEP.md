# Layer C, Variety Leg 1 — Upkeep Drive

**Status: VERIFIED — CLOSED (2026-07-25).** Contract confirmed by Ryan with 5
explicit conditions (recorded below); implemented, gated, adversarially
reviewed (Grok/xAI, cross-vendor), findings resolved per Ryan's rulings, and
committed. See §10 for the close-out record.
Owner of docs: cloud session · Implements: terminal session (this branch).

Frontier: `FRONTIER.md` — Layer C (Individual Agency), Behaviour Enrichment,
Closed leg: Variety Leg 1 — Upkeep drive. Next queued: CORE-PERF-01.

---

## 1. Goal

Agents currently rest the overwhelming majority of ticks and almost never
maintain their surroundings on their own initiative. Add one recurring
non-survival `upkeep` drive so idle ticks become small useful maintenance
actions (tending a mildly worn shelter) instead of resting, without touching
survival dominance, the frozen Stage 6–8A schemas, or the Stage 9 economy
boundary. Player outcome: agents visibly rest less and tend their
surroundings. This is an extension of already-organic behaviour (rest and
repair both already fire) per Invariant 12(v2), not a genuinely new decision
category — hence probe-before-contract, magnitude-after-build.

## 2. Organic-reachability evidence (measured, VERIFIED)

`BEHAVIOUR-BASELINE-001` (the frontier doc's citation) does not exist as a
committed artifact anywhere in the repo — checked directly, no file/doc/probe
output references it. It's a forward-reference the cloud session flagged as
pending. This contract substitutes directly-measured numbers recomputed from
two already-committed, repeat-verified harness runs instead:

| Scenario | Ticks | Total actions | `rest` | `rest`% | `repair` |
|---|---|---|---|---|---|
| `living_settlement` (`memory/evidence/stage-8b-leg1/harness_living_settlement_320_v3.json`) | 320 | 1149 | 789 | **68.7%** | 9 |
| `collective_groups` (`memory/evidence/stage-8b-leg1/harness_collective_groups_1000_v3.json`) | 1000 | 7937 | 7199 | **90.7%** | 9 |

The ~89–90% figure in THE-SPINE.md/FRONTIER.md is real but specific to
`collective_groups`; `living_settlement` alone currently rests 68.7%. Both
runs report `repeat_matches: true`. `repair` (the existing shelter-maintenance
action) already fires organically 9 times in both — low but nonzero; this is
the mechanism Upkeep must not collide with or double-count against.

Frozen hash, verified exact: `final_state_hash` in the `living_settlement_320_v3`
run is `84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`
(`repeat_matches: true`) — matches CLAUDE.md's `84d3ad52…c32d2`.

## 3. Code discovery — the exact collision surface

- **`backend/domains/ecology_domain.py`** (`EcologyDomain`, `engine_priority=0`,
  `phase="environment"`) — sole proposer of `structure_wear`: every
  `STRUCTURE_WEAR_INTERVAL` (5) ticks, decrements `shelter.condition` by
  `STRUCTURE_WEAR_BASE` (4) + weather term, floored at `STRUCTURE_WEAR_MIN_
  CONDITION` (0). Exogenous. Its own docstring documents the existing
  ownership discipline: *"Repair (agent phase) commits AFTER wear... a wear
  tick and a repair on the same structure resolve deterministically as a wear
  then a rejected repair that retries next tick."* — via a
  `field=condition, op=eq, value=<condition captured at proposal time>`
  precondition on the repair proposal. No new arbitration code needed for
  `tend` — same pattern, reused.

- **`backend/domains/living_settlement_domain.py`**
  (`engine_priority=10`, `phase="agent"`, runs after ecology within a tick):
  - Line 484: `REST` **unconditional fallback**, `_candidate("REST","rest",60)`
    — the true idle floor, not "nothing available."
  - Line 324-325: `REST`-as-survival, `if fatigue>=650:
    _candidate("REST","rest",1200+fatigue)` — stays untouched, dominant.
  - Line 369-382: `REPAIR_SHELTER` — gated to `role=="builder"` AND
    `condition<750` AND `wood>0` AND an accessible hammer. In
    `scenarios/living_settlement.py`, exactly one of 8 genesis people is
    `builder` (`person-002`, who also owns the only hammer) — explains the
    measured 9-count.
  - Lines 132-177 / 183-236 (`_apply_group_goal_influence` Stage 7D,
    `_apply_group_norm_influence` Stage 8B Leg 1) — pure, read-only,
    survival-dominance-guarded score boosts keyed **strictly** on
    `cand.get("goal")=="REPAIR_SHELTER"` (string match). Never create a
    candidate, never lift above the highest present survival `score_total`.

- **`backend/domains/living_agent_actions.py`** line 457-471 — `repair`
  executor: adjacency required, `wood>=quantity` consumed, `delta=+120` to
  `condition` (capped at `max_condition`), carries the condition-equality
  precondition, wears the hammer tool.

- **`backend/domains/living_agent_cognition.py`**
  `derive_internal_pressures()` (line 399) — one generic loop derives
  `severity`/`urgency`/`tolerance`/**`individual_weight`** (bounded 1-200,
  default 100) for every kind in a `raw: dict[kind] = (severity, source)`
  mapping. The per-agent-weight hook the brief asks to "bank for
  individuality" **already exists generically** — a new `raw` key inherits it
  for free, at the uniform default, zero bespoke code.

- **`backend/domains/living_agent_contracts.py`** — `PRESSURE_KINDS` (line
  27-42), a 14-entry tuple; `empty_pressure()` raises `ValueError` for any
  kind outside it. **The one schema surface this leg touches**: a 15th,
  additive entry.

- **`backend/scenarios/living_settlement.py`** — genesis: 2 shelters
  (`shelter-family` cond=850, `shelter-damaged` cond=380 — already worn at
  genesis), 8 people.

- **Perception gap (pre-existing, not this leg's problem)**:
  `backend/domains/perception.py`'s sighting loop has no branch for the
  generic `structure` entity type (only `tree`/`shelter`/`carcass`/`animal`/
  `person`/danger). Generic structures are unperceived today — out of scope.

## 4. Mechanism (as authorized, with Ryan's 5 conditions incorporated)

### Decision 1 — new goal/action names — AUTHORIZED
`TEND_STRUCTURE` (goal) / `tend` (action_type), not a broadened
`REPAIR_SHELTER`/`repair`. Reasons ratified: (a) additive discipline — keeps
REPAIR_SHELTER's existing 7D-linked behaviour inside the frozen baseline
untouched; (b) the gate needs action-spread visibility — a distinct name lets
the metric see upkeep firing separately from existing repair; a broadened
REPAIR_SHELTER couldn't be told apart from the old behaviour in the counts.

**Condition — no double-apply, satisfied by a disjoint wear-band split (not
precondition-race luck):**
- `repair` keeps its existing trigger **unchanged**: `condition < 750`
  (builder-gated, unmodified).
- `tend` triggers only in the **disjoint** band `750 <= condition <
  max_condition` (any role). A new named constant
  `STRUCTURE_TEND_CONDITION_FLOOR = 750` is added (duplicating repair's
  existing inline `750`, not refactoring it, to avoid touching sealed Stage 6
  code) with a comment cross-referencing this doc so the two bands are
  provably documented as matching.
- Consequence: `repair` and `tend` **never target the same structure in the
  same state** — the bands are mutually exclusive by construction, independent
  of tick-ordering or precondition-race timing. Once a shelter crosses below
  750, only `repair` is proposed for it; `tend` backs off automatically. This
  is a stronger guarantee than "the precondition happens to reject the
  loser," though that mechanism remains present as defense-in-depth (e.g. two
  different `tend`-eligible actors targeting the same shelter same tick still
  resolve via the existing precondition-equality serialize-or-reject path —
  no new arbitration code).
- Because `TEND_STRUCTURE` is a new goal name, it is invisible to both the
  Stage 7D and Stage 8B nudges (they match `"REPAIR_SHELTER"` literally) —
  zero collision with that surface by construction.

### Decision 2 — idle signal from `decision_history` tail — AUTHORIZED
**Condition — confirm pinned-frame read, fixed tail length:** `derive_internal_
pressures` runs inside `LivingSettlementDomain.activate()` against
`frame.entities` — the Pinned Read-Only Observation Frame for tick T-1 per
Rail A (the same frame every other pressure, e.g. fatigue/hunger/exposure,
already reads from). The new idle term reads `state["decision_history"]`
(already-canonical, already capacity-bounded at `LIMITS.decision_receipts_
retained`=12) from that same pinned entity snapshot — no new canonical field,
no mutable/hidden state. Tail length is a new fixed named constant (e.g.
`UPKEEP_IDLE_TAIL_TICKS`, value <=12, exact value an implementation-time
choice within that bound) — fixed across all agents, not computed
per-instance.

Severity signal (structure, not magnitude — coefficients calibrated at
implementation):
- a term for a visible worn shelter in the tend band (reusing the existing
  `shelters = _observation_map(delta, "shelter")` / `condition` read that
  `REPAIR_SHELTER`'s candidate already uses — no new observation plumbing);
- a term for consecutive trailing `decision_history` entries with
  `selected_goal=="REST"`, capped at the fixed tail constant.

### Decision 3 — `PRESSURE_KINDS` additive touch — AUTHORIZED
Ratified as the right model, not just tolerated: a drive that builds over
idle time and discharges is the needs-based pattern the spine calls for, and
it's what lets per-agent individuality weighting slot in later (Decision 2's
sibling finding — `individual_weight` already generic).

**Condition — additive only, schema-version bump if versioned, re-baseline
carried with explained diff:**
- Additive only: the 14 existing `PRESSURE_KINDS` entries are byte-unchanged;
  `"upkeep"` is a 15th entry.
- Schema-version judgment call (flagged explicitly per the condition, not
  decided silently): `PRESSURE_SCHEMA_VERSION` (`"internal-pressure-v1"`)
  versions the **per-pressure-record field shape** (severity/urgency/
  tolerance/individual_weight/etc.), validated in `_compat_pressure`. That
  shape is unchanged by adding an allowed kind. `PRESSURE_KINDS` itself is a
  bare tuple with no version field of its own today — there is nothing to
  bump for it. Recommendation: **do not bump `PRESSURE_SCHEMA_VERSION`**.
  Flagged here for override if this reasoning is wrong.
- Re-baseline: handled in §6 below (expected hash move, explained diff, its
  own STOP).

### Decision 4 — shelter-only scope — AUTHORIZED, structure deferred
Generic `structure` entities aren't perceived today (§3) — covering them
would mean building structure perception first, a second feature. Shelter is
already perceived, already repaired — the minimal additive leg, and it keeps
the collision surface to the three known shelter writers (wear, repair,
tend). Generic structure upkeep is a clean future leg.

### Candidate generation & score placement
`TEND_STRUCTURE` is proposed for **any role** (unlike `REPAIR_SHELTER`'s
`role=="builder"` gate) whenever a visible shelter's `condition` is in the
tend band. Base score placed so the effective score band (base + upkeep
urgency) sits strictly between REST-fallback's floor (60) and the lowest
survival-triggered candidate's base (1200) — an ordering constraint, not a
picked magnitude; the exact base integer is an implementation-time choice
bounded by this constraint and confirmed by the §6 gate's survival-dominance
integration test. `TEND_STRUCTURE` is **not** added to `SURVIVAL_GOALS` —
dominance is structural (score band), matching how `REPAIR_SHELTER` already
works.

## 5. Ownership check

| Component / Field | Entity Type | Canonical Owner | Current Writers | New Writer (this leg) | Legal Cross-Owner Writes | Collision Risk | Tests |
|---|---|---|---|---|---|---|---|
| `condition` | shelter | shared multi-proposer (Core-arbitrated, single-writer commit) | `ecology_domain` (decrement, `structure_wear`, unconditional) · `living_settlement_domain` (`repair`, builder-gated, `condition<750`, +120) | `living_settlement_domain` (`tend`, any-role, `750<=condition<max_condition`, new) | N/A — peer proposers, disjoint bands, not cross-owner mutation | LOW — disjoint bands by construction + existing precondition-equality serialize-or-reject as defense-in-depth | existing wear-vs-repair same-tick coverage + **new**: wear+tend same-tick test, and a same-tick test proving repair/tend bands never both fire on one structure |
| `pressures["upkeep"]` | person (`living_agent`) | `living_settlement_domain` (`derive_internal_pressures`) | none (new kind) | `living_settlement_domain` | N/A | NONE — new key | `PRESSURE_KINDS` extension forged-field-rejection test; replay equality |
| `decision_history` (read-only new consumer) | person | `living_agent_reasoning.record_decision` (unchanged) | unchanged | read-only | N/A | NONE | covered by existing decision_history + new replay/resume check |

**Domain Ordering Registry** (extends the existing relationship, no new rule):

| Domain | Phase | Priority | Reads | Writes | Must Run Before | Must Run After | Reason |
|---|---|---|---|---|---|---|---|
| ecology | environment | 0 | `shelter.condition`, weather | `structure_wear` proposal | living_settlement | — | wear lands first so a same-tick repair/tend precondition correctly goes stale-and-rejects (existing, now also protects `tend`) |
| living_settlement | agent | 10 | `shelter.condition` (shelter observation), pressures/tools/resources | `repair` (builder-gated) + **new** `tend` (any-role) | — | ecology | must run after ecology to capture this tick's post-wear condition (existing pattern extended) |

**Event Family Registry** (new row):

| Event Family | Producer | Validator | Canonical Mutations | Causal Parents | Lifecycle | Projection | Replay Handler |
|---|---|---|---|---|---|---|---|
| `tend` (physical action) | `living_settlement_domain` | existing generic physical-action validator (same path as `repair`) | `shelter.condition += delta` (capped at `max_condition`) | prior accepted event for the actor | terminal, single-tick | event log / entity inspector (shelter condition) | standard living_action replay handler (same as `repair`) |

## 6. Acceptance gate (REVISED shape — `scratchpad/UPKEEP-GATE-REVISED.md`, 2026-07-24; results below)

**Why revised:** the original 1000-tick x 2-scenario x 3-run shape (repeat +
resume with full event capture) went multi-hour and was stopped. Upkeep
saturates by ~tick 80 (every idle tick is spent tending once a shelter is in
band), so a long horizon proves nothing extra. Right-sized per the
proportionality doctrine: horizon **H = 250 ticks** for all organic runs,
**no event capture** (counts come from a live per-tick tally —
`tools/_probe_layer_c_upkeep_gate.py` — never an accumulated event list, so
cost stays flat regardless of tick count), **two seeds**
(`living-agents-stage6` + `living-agents-stage6-alt`). Gate **direction is
unchanged** — this is a horizon/shape revise, not a weakening. The single
320-tick `living_settlement` run is kept, but only for the frozen-hash
re-baseline, not for repeat/resume.

### Gate items and results (all VERIFIED — evidence in `memory/evidence/layer-c-leg1/`)

1. **Mechanism — Tier A fixtures** (`backend/tests/test_layer_c_upkeep.py`,
   16 tests, all pass): candidate generation gated correctly (any role, band
   `750<=condition<1000`), outscores REST / loses to survival, an accepted
   `tend` discharges the drive (severity measurably lower afterward), no
   double-apply with `repair`/`REPAIR_SHELTER` (disjoint-band proof +
   same-tick wear-vs-tend churn test), **the Stage 7D nudge is inert for
   `TEND_STRUCTURE` even under a fully active, matching, valid registry**
   (`test_stage7d_nudge_is_inert_for_tend_structure_even_with_an_active_
   matching_goal` — the companion `REPAIR_SHELTER` candidate in the same call
   *does* get boosted, proving the registry setup was genuinely live, not
   inert-by-omission), forged-field rejection for both the `PRESSURE_KINDS`
   and `PHYSICAL_ACTION_TYPES` additive touches.

2. **Organic rest-decrease — the headline.** `collective_groups`, H=250, seed
   `living-agents-stage6`:
   - `BEHAVIOUR-BASELINE-001@250` re-measured (no-upkeep, stashed
     implementation): rest **89.5%** (1769/1976).
   - With upkeep: rest **40.9%** (638/1560) — strictly below baseline.
   - `tend` fired by **N=8** distinct actors (all of them) across **M=2**
     distinct shelters (both of them).
   - **0 deaths, 8 alive.** `repair` count 5 (nonzero — not cannibalised;
     plausibly *lower* than baseline's 9 because proactive tending keeps
     shelters from crossing into `repair`'s `<750` band as often — a
     positive emergent interaction between the two mechanisms, not a
     suppression bug).
   - Action-type diversity: 17 -> 19 distinct types. Mix genuinely **broadened**,
     not just reshuffled: Shannon entropy of `actions_by_type` rises **0.75 ->
     2.31 bits** (adversarial review Focus A / finding F-01). Rest's ~49pp drop
     splits across `tend` (+19.8pp) *and* a larger `move`/social expansion
     (move 3.8%->24.9%, cooperate 0.1%->4.0%, repay 0.1%->2.3%,
     request_help 0.4%->2.3%); residual rest+tend is still 60.7% combined —
     cite the full distribution/entropy here, not rest% alone.

3. **`living_settlement` — direction check + re-baseline.**
   - Direction, H=250, seed `living-agents-stage6`: baseline rest **73.3%**
     (789/1077) -> with-upkeep **32.1%** (351/1093). N=8, M=2, 0 deaths.
     Shannon entropy of `actions_by_type` rises **1.52 -> 2.46 bits**
     (finding F-01) — same broadening pattern as `collective_groups` above.
   - Re-baseline, single 320-tick run, seed `living-agents-stage6`: **new
     hash `897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab`**
     (old, frozen: `84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788
     c32d2`). **Full causal diff** (adversarial review finding F-06 — the
     original write-up listed rest/tend/repair only and omitted the largest
     non-tend shift; corrected here with the complete action-count delta,
     old 320 -> new 320, sourced directly from
     `memory/evidence/stage-8b-leg1/harness_living_settlement_320_v3.json` and
     `memory/evidence/layer-c-leg1/upkeep_living_settlement_320_frozen_rebaseline.json`):

     | action | old 320 | new 320 |
     |---|---:|---:|
     | rest | 789 (68.7%) | 351 (29.9%) |
     | tend | 0 | 244 (20.8%) |
     | repair | 9 | 4 |
     | move | 62 | **304** |
     | request_help | 182 | 141 |
     | cooperate | 28 | 37 |
     | repay | 28 | 36 |

     The largest single shift is **not** `tend` — it is `move` (62 -> 304, a
     4.9x increase), followed by the social actions (`cooperate` +9, `repay`
     +8) and the `request_help` drop (-41). All other action types (`consume`,
     `drink`, `gather`, `apologise`, `lie`, `promise`, `reconcile`, `retrieve`,
     `share_information`, `store`, `threaten`, `trade`) are unchanged or within
     +/-2 (verified directly from both evidence files, not estimated).
     `repeat_matches: true`, `replay_matches_final_entities: true` (both read
     directly from the rebaseline evidence file). Same domains, same schema
     versions, same genesis — the causal chain's *structure* is unchanged; its
     *distribution* broadened well beyond rest/tend/repair, as the table above
     shows. **Re-baseline AUTHORISED** (Ryan, 2026-07-25, conditional on this
     write-up being complete — see "Rulings" in
     `scratchpad/upkeep_adversarial_review_ledger.md`) on that basis.
   - Note: `rest` and `tend` counts are byte-identical between the H=250 and
     the 320-tick run on this seed (351/244 both times) — the marginal 70
     ticks are dominated entirely by an accumulating social-debt cascade
     (`request_help` 80->141, `repay` 31->36) that outscores both REST and
     `TEND_STRUCTURE` for that whole window; not a bug, just where this
     particular seed's late game goes.

4. **Determinism.** repeat + replay + resume (`--repeat 2 --resume-at
   <H/2>`), H=250, both scenarios, primary seed: **all `True`**
   (`repeat_matches`, `replay_matches_final_entities`, `resume_matches` on
   both `living_settlement` and `collective_groups`).

5. **Robustness (multi-seed).** `collective_groups`, H=250, alternate seed
   `living-agents-stage6-alt`: baseline rest **88.9%** (1764/1984) ->
   with-upkeep **47.2%** (795/1685). N=8, M=2, 0 deaths. Rest-decrease result
   holds under the alternate seed.

6. **Regression.** Re-measured at close-out (adversarial review finding F-05 —
   the original 338 figure was builder-asserted, not backed by a saved log;
   evidence now saved at
   `memory/evidence/layer-c-leg1/full_suite_closeout.txt`): **339 executed
   passed** (336 pre-existing + the 2 original Tier-A additions + the 1 new
   dedicated false-belief test added for F-04), **4 known pre-existing skips**
   (Docker live-server env only) excluded from execution, **0 executed test
   failed**; 5 known `MONGO_URL`-env collection failures excluded from
   execution (pre-existing environment gap, confirmed unrelated: none of those
   5 files import anything this leg touches; `test_concurrency.py`'s flake is
   separately classified under `CORE-INTEGRITY-001`, not a fail).
7. **Survival never suppressed** — structural guarantee (score band strictly
   below all survival-triggered candidates) plus
   `test_tend_never_outranks_an_active_survival_candidate`.

### Out of scope / logged, not fixed here

- **O(n²)-shaped per-tick engine cost** (rising with accumulated registry
  state; ~1s/tick at the high end during the original 1000-tick attempt) is a
  **pre-existing performance item**, not introduced by this leg. Logged here
  as a telemetry note for a future core-perf leg; **not touched in Leg 1**.
- 1000-tick horizons are not a gate for this leg. A long-horizon confirmation
  run is optional and never a blocker.

## 7. Non-goals for this leg

- No new advertisement framework.
- No broadening to generic `structure` entities (Decision 4).
- No individuality/trait weighting of `upkeep` yet — uniform default weight
  only (`_pressure_weight()` left at its generic `100` fallback), hook
  banked for later with zero rework.
- No change to `REPAIR_SHELTER`'s existing builder-gated branch or to the
  Stage 7D/8A nudge functions — both untouched, still only see
  `REPAIR_SHELTER`.
- No Aid Exchange reopening, no Stage 9 boundary, no institutions/governance.
- No re-baseline performed in this contract phase — separate STOP, explained
  diff.

## 8. Risks

- **Score placement**: mitigated by the score-band constraint (§4) plus gate
  item 7's integration test.
- **Determinism of the idle signal**: `decision_history` is already
  canonical/replay-safe, but explicitly covered by gate item 4 as a new
  consumer of that field.
- **Hash-churn laundering**: pre-authorised to move, but only with a genuine
  causal diff; if not cleanly attributable to `tend`, stop and investigate
  before re-baselining.
- **Triple-writer contention on `condition`**: mitigated structurally by the
  disjoint wear-band split (§4 Decision 1), with the existing
  precondition-equality mechanism as defense-in-depth; falsified by the new
  same-tick tests (§5).
- **Schema touch**: `PRESSURE_KINDS` is Stage-6 sealed-adjacent. Change is
  additive-only; called out explicitly (§4 Decision 3) rather than silently
  done.

## 9. Implementation notes (as-built deviations, found during verification)

- **A second additive schema touch, not just `PRESSURE_KINDS`**: `tend` also
  had to be added to `PHYSICAL_ACTION_TYPES`
  (`living_agent_contracts.py`) — the generic physical-action validator
  (`build_physical_action_proposal` and `validate_living_action_proposal`)
  rejects any `action_type` outside that frozenset. Additive-only, same
  treatment as `PRESSURE_KINDS`; not called out in the original contract
  because it wasn't discovered until wiring the action executor. Covered by
  `test_unsupported_physical_action_still_rejected_with_tend_present`.
- **Candidate generation order matters, not just presence**:
  `build_settlement_candidates` truncates to
  `LIMITS.candidate_goals_per_decision` (16) in **append order**, before
  scoring. Inserting `TEND_STRUCTURE` right after `REPAIR_SHELTER` (as
  originally drafted) silently starved rarer, later-declared candidates
  (`WARN_DANGER`, `SHARE_RUMOUR`, `VERIFY_INFORMATION`, `TRADE_RESOURCES`,
  `THREATEN`, `TAKE_FOOD`) for busy actors — caught by
  `test_stage6e_living_settlement.py`'s required-action-vocabulary assertion
  (a scout's `warn` never fired). Fixed by generating `TEND_STRUCTURE` last,
  immediately before the `EXPLORE`/`REST` fallback block, so it only ever
  contends with the two fallbacks it's designed to compete with.
- **`TEND_STRUCTURE_BASE_SCORE` revised from an initial 400 down to 120**
  (between `REST`'s 60 and `EXPLORE`'s 180, not above both). A shelter sits in
  the tend band almost continuously in these scenarios, so scoring above
  `EXPLORE` made tending a permanently-preferred absorbing loop that starved
  map exploration — traced directly: with the scout's `WARN_DANGER` selected
  from tick 1, it got interrupted by a higher-priority `REPAY_DEBT` at tick 3
  (pre-existing, unrelated to this leg), and on the ORIGINAL 400-score build
  never returned to wandering afterward (permanently ping-ponging between the
  two genesis shelters instead), so it never re-perceived the animal+person
  needed to re-trigger `WARN_DANGER`. At 120, `EXPLORE` wins whenever there is
  still unknown adjacent ground, `TEND_STRUCTURE` only wins once exploration
  is locally exhausted. Both orderings are within the contract's "below
  survival, above rest" latitude — this is a placement choice within that
  band, not a rail change. Covered by
  `test_tend_beats_rest_fallback_when_no_survival_pressure_present` and
  `test_explore_still_wins_over_tend_when_unknown_ground_is_adjacent`.
- **A second, non-hash re-baseline-shaped consequence**:
  `test_stage6e_living_settlement.py::test_integrated_camp_closes_the_living_
  agent_loop_and_replays` pins a deterministic 30-tick trace (seed
  `stage6-integrated`) and asserts `false_belief_count >= 1`. This project has
  hit this exact class of issue before on this same test (see its own
  existing comment on the `commitment_statuses` assertion, from the Stage 6
  Liveness Pass). Verified directly (not guessed): `false_belief_count` is 0
  at 30, 40, 50, and 60 ticks post-leg (was >=1 pre-leg at 30) — not a timing
  margin, a genuine shift in which agent reaches the genesis false-rumour
  signal (expires tick 4) before this run's idle-time behaviour changed. No
  other test in the suite covers false-belief detection, so the assertion was
  loosened (`>= 0`) with an explanatory comment rather than deleted or
  papered over with an extended tick count. `reported_claim_count >= 1`
  (the provenance mechanism itself) still holds and is unchanged.
- **Net effect**: these are exactly the kind of causal, verified behavioural
  shifts the contract's "frozen hash WILL move" clause anticipated, just
  surfacing in two additional artifacts (a candidate-order bug that was a
  real defect and needed fixing outright, and one narrative-timing test
  assertion that needed loosening) beyond the single hash explicitly named up
  front. Flagged here and in the close-out rather than silently absorbed.

## Session handoff

Contract authorized this session (2026-07-25) with all 5 conditions
incorporated above. Worktree branch `worktree-typed-painting-marshmallow`
(fast-forwarded to `capability/stage-8c-phase1-aid-exchange` tip `d5d80a43`).
Nothing committed yet past the contract-confirmation commit `b58e60d2` — the
implementation is uncommitted on purpose pending your STOP sign-off below.

**Done, this session — gate is GREEN:**
- Implementation complete (§4 mechanism, §9 as-built notes): `upkeep`
  pressure kind, `TEND_STRUCTURE` goal, `tend` action, disjoint wear bands,
  `TEND_STRUCTURE_BASE_SCORE` calibrated to 120 after a real
  candidate-starvation bug and an absorbing-loop finding, both fixed and
  documented in §9.
- Focused tests: `backend/tests/test_layer_c_upkeep.py`, **16 tests, all
  pass** (14 original + 2 added for the revised gate's Tier-A requirements:
  discharge-after-tend, Stage 7D nudge inertness under a live registry).
- The full revised acceptance gate (§6) is measured and **green** on every
  item: rest-decrease and N=8/M=2 organic-reachability (adversarial review
  finding F-03 — actual coverage shape, corrected here: `collective_groups`
  ran **both** seeds `living-agents-stage6` + `living-agents-stage6-alt`;
  `living_settlement` ran **seed1 only**, `living-agents-stage6` — the alt
  seed was never independently run on `living_settlement` for either metric,
  so "both scenarios, both seeds" as originally stated overstated the
  coverage), 0 deaths, full determinism (repeat+replay+resume, both
  scenarios, primary seed), the frozen-hash re-baseline with an explained
  causal diff (§6 item 3, full action delta), full regression suite (see
  §6 item 6 for the exact counts sourced from the F-05 evidence log).
  Evidence: `memory/evidence/layer-c-leg1/*.json`.
- `backend/tools/_probe_layer_c_upkeep_gate.py` consolidated to one script
  (the two spent timing-diagnostic scripts that found the O(n²) cost were
  deleted, not committed — their finding is logged in §6's "out of scope"
  note).
- `test_stage6e_living_settlement.py` needed one targeted, documented
  loosening (§9) — verified causally, not guessed.

**At the time this session ended:** adversarial review had not yet run, and
nothing was committed past `b58e60d2` per AGENT_WORKFLOW ("never self-review" +
"nothing committed past... an open review finding"). Both are now resolved —
see §10.

## 10. Close-out (adversarial review resolved, 2026-07-25)

**Review:** Grok 4.5 (xAI) — cross-vendor independent of the Anthropic
implementer session (Codex path unavailable, quota exhausted to Jul 29; brief
authorised Grok as substitute). Full findings ledger, pass-1-blind +
pass-2-builder-seeded procedure, and Ryan's rulings:
`scratchpad/upkeep_adversarial_review_ledger.md`.

**Findings and disposition (all resolved):**
- **F-04** (vacuous `false_belief_count >= 0` net) — **FIXED.** The assertion
  in `test_integrated_camp_closes_the_living_agent_loop_and_replays` is kept
  (documents the trace-timing shift, `>= 0` cannot regress-catch) but a new
  dedicated test, `test_false_belief_detection_flags_a_known_deceptive_report`
  in the same file, replaces it as the real net: it self-verifies a genesis
  false-rumour fixture (`stage6-information` seed, tick 1) produces a genuine
  canonical/claimed mismatch, then asserts `false_belief_count` catches it.
  Demonstrated to fail under a temporary induced regression (short-circuiting
  the harness's false-belief loop) and pass once reverted; the harness file
  itself carries zero net diff from that verification.
- **F-05** (suite counts builder-asserted, not evidenced) — **FIXED.**
  Full suite re-run at close-out, log saved:
  `memory/evidence/layer-c-leg1/full_suite_closeout.txt`. Result: 339
  executed passed (the 338 previously claimed plus the 1 new F-04 test), 4
  known pre-existing skips excluded, 5 known `MONGO_URL`-env collection
  failures excluded, 0 executed test failed. See §6 item 6.
- **F-03** (organic-reachability claim overstated seed coverage) — **FIXED.**
  The individual per-scenario gate items in §6 (2, 3, 5) were already
  correctly single-seed-scoped and never themselves claimed "both scenarios,
  both seeds" — the overstatement lived only in the session-handoff summary
  above and in `FRONTIER.md`'s gate-shape bullet, both now corrected:
  `collective_groups` ran both seeds; `living_settlement` ran seed1 only
  (`living-agents-stage6`) for every metric — direction, organic-reachability,
  and the frozen-hash re-baseline. No run on `living_settlement`'s alt seed
  exists in the evidence package.
- **F-06** (re-baseline causal diff omitted move/social shifts) — **FIXED.**
  §6 item 3 now carries the full 7-action delta table (rest, tend, repair,
  move, request_help, cooperate, repay) instead of rest/tend/repair only, and
  no longer claims "nothing else in the causal chain changed."
- **F-01** (variety claim needs entropy/full distribution, not rest% alone) —
  **ACCEPT**, wording addressed: §6 items 2/3 and `FRONTIER.md` now cite
  Shannon entropy (0.75->2.31 bits `collective_groups`; 1.52->2.46 bits
  `living_settlement`) alongside the distribution table, not rest% in
  isolation.
- **F-02** (repair 9->4 attribution plausible, not trajectory-proven) —
  **ACCEPT** as ruled; no code or wording change required, mechanism argument
  and nonzero residual repair count stand as originally written.

**Re-baseline:** authorised by Ryan (2026-07-25) conditional on the F-06
write-up above being complete. Applied: frozen `living_settlement` 320-tick
hash moves from `84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`
to `897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab`, updated
in `CLAUDE.md`, `memory/CAPABILITY-DOCTRINE.md`, and
`.claude/agents/hard-rail-reviewer.md`'s tripwire.

**Commit series:** F-04 test fix, F-05 evidence log, this contract's wording
fixes + close-out, `FRONTIER.md` move, and the `CORE-PERF-01` queued-next
pointer ship together per AGENT_WORKFLOW's "same commit series" rule. Exact
commit list is in the STOP report delivered alongside this close-out.

**Next:** no active Layer C behaviour leg. `CORE-PERF-01` (Layer A kernel
infra, hash-neutral) is queued next per `memory/CORE-PERF-01-TICK-VALIDATION-COST.md`
and `FRONTIER.md` — not authorised, not started; needs its own
contract-confirmation STOP before implementation.
