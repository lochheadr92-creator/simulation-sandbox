# Layer C, Variety Leg 1 — Upkeep Drive

**Status: AUTHORIZED (2026-07-25).** Contract confirmed by Ryan with 5 explicit
conditions (recorded below); implementation proceeds against this doc.
Owner of docs: cloud session · Implements: terminal session (this branch).

Frontier: `FRONTIER.md` — Layer C (Individual Agency), Behaviour Enrichment,
Active leg: Variety Leg 1 — Upkeep drive.

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

## 6. Acceptance gate

**Condition (Decision 5, REVISED) — split direction vs. magnitude:**
- **Direction, gated on BOTH scenarios**: rest fraction strictly decreases vs
  the measured baselines (68.7% `living_settlement`, 90.7%
  `collective_groups`). Cheap, binary; catches a broken drive in the smaller,
  confound-free scenario too.
- **Magnitude, the formal pre-registered organic-reachability gate,
  `collective_groups` only**: `TEND_STRUCTURE`/`tend` fires organically by
  **>=N distinct actors across >=M distinct shelters** — N, M measured from a
  post-build probe on `collective_groups` (not pre-picked). `repair`'s
  existing ~9-count must not collapse to 0 (would indicate cannibalisation,
  not addition).
- `living_settlement`'s own magnitude (how far rest fell, how many `tend`
  firings, etc.) is **not** a second independently-thresholded gate — it
  becomes the causal-diff evidence for the re-baseline STOP below.

Full gate:
1. Rest fraction direction check, both scenarios (above).
2. `TEND_STRUCTURE` organic-reachability magnitude gate, `collective_groups`
   only (above); `repair` count non-collapse on both.
3. 0 deaths regression, both scenarios.
4. Determinism: repeat + replay + resume byte-equality, both scenarios.
5. Frozen `living_settlement` 320-tick hash change is **expected** —
   re-baseline only at a follow-up STOP with an explained causal diff (old
   hash `84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`
   cited verbatim; `living_settlement`'s direction-check result and magnitude
   are the supporting evidence for that diff), never a bare re-hash.
6. Full regression suite green (honest phrasing, no unqualified "green" while
   exclusions exist).
7. Survival never suppressed — structural guarantee (score band strictly
   below all survival-triggered candidates) plus one integration test with an
   actor simultaneously eligible for both `TEND_STRUCTURE` and an active
   survival candidate, asserting survival wins.

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

## Session handoff

Contract authorized this session (2026-07-25) with all 5 conditions
incorporated above. Implementation, tests, and the full gate are in progress
in the same session on worktree branch `worktree-typed-painting-marshmallow`
(fast-forwarded to `capability/stage-8c-phase1-aid-exchange` tip `d5d80a43`).
If context runs low before the gate + adversarial review complete, the next
session should resume from the task list on this branch rather than
re-deriving the design.
