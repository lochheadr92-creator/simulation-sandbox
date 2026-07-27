# Layer C Social Density Leg 2 — Session 1, deliverable 2: lifecycle map per family

**Plan:** `memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md` §Phase 1
("Lifecycle pathways are mapped PER FAMILY before counting — the eight actions are
not assumed to share one path; any bypass is a finding.")

**Code state:** commit `77b8287d` (detached worktree at HEAD; `git diff --stat
180c43f4 HEAD` = the three baseline JSONs only, so the code is byte-identical to
the state that produced `baseline_collective_groups_5000.json`). The working
tree's uncommitted Leg 1 change (`STORE_SURPLUS_MIN_FOOD = 2`) is **not** present
in the measured state — verified: the worktree still reads
`resources.get("food", 0) >= 3` and defines no `STORE_SURPLUS_MIN_FOOD`.

**Method:** static read of the committed decision path. Every claim below is
VERIFIED by code read at the cited line and carries no measurement content; the
measured funnel is deliverable 4.

---

## 1. The common pathway (VERIFIED)

All eleven tracked actions — the eight targets and the three reference families —
share one pathway. `domains/living_settlement_domain.py:535` `activate()`, once
per due, alive person, per tick:

| Stage | Code | Observable in Session 1? |
|---|---|---|
| perceive | `perceive_living` → `delta["observations"]` (`:546`) | no — in-loop only |
| generate | `build_settlement_candidates` (`:571`), returns `candidates[:16]` (`:513`) | **no** — pre-receipt truncation |
| score | `score_goal_candidates` (`:572`) | yes — receipt `candidate_goals` |
| influence | `_apply_group_goal_influence`, `_apply_group_norm_influence` (`:580-581`) | yes — folded into `score_total` |
| select | `select_goal` (`:582`), argmax on `candidate_rank` | yes — receipt `selected_goal_id` |
| route | distance/pathfind rewrite (`:604-619`) | yes — committed `action_type` |
| build | `build_social_action_proposal` else physical (`:660-687`) | yes — `plan.failure_reason` |
| commit | `run_commit_frame` (`core/kernel.py:123`) | yes — accepted / rejected |

**No target action bypasses any stage.** The eight targets are all members of
`SOCIAL_DIRECT_ACTIONS` (`:63-68`), so all eight route through
`build_social_action_proposal`; none has a private commit path. The plan's abort
condition "a target action bypasses unobserved stages" is therefore **not met by
static reading**, and the measured funnel carries an independent dynamic check
(the `committed_equals_raw_event_count` bypass detector).

### Three distinct stage-F modes, all separable offline (VERIFIED)

1. **preempted_travel** (`:606-612`) — the winner has a `target_pos` at Manhattan
   distance > 1 and a route exists ⇒ `actual_action` is rewritten to `"move"`.
   The social intent is *not* lost: it is stored in `plan["intent"]` (`:636`) and
   re-offered next tick as a `continuation` candidate at base score 2300
   (`:270-277`). A social goal can therefore win many times and commit only
   `move` events.
2. **invalidated_plan_failed** (`:613-619`) — no route ⇒ `"rest"`, plan
   `abandoned`, `decision_kind = "failed_plan_replan"`.
3. **invalidated_builder_error** (`:688-700`) — the proposal builder raises
   `ValueError` ⇒ fallback `rest`, `plan["failure_reason"]` set, and
   `living_failed_goal_counts[goal]` incremented.

`proposal["living_action"]["causal_goal_id"]` is stamped **after** the try/except
(`:779-783`), so every outcome — commit, move, or fallback rest — carries the
selected goal id. Matching decisions to committed events on
`(actor_id, selected_goal_id)` is therefore total, which is what makes the
`won = Σ outcomes` conservation identity closable.

### What Session 1 structurally cannot see (VERIFIED)

`build_settlement_candidates` returns `candidates[:LIMITS.candidate_goals_per_decision]`
(= 16) in **append order**, before any scoring and before any receipt exists.
Candidates dropped there are invisible to receipts, so stage C ("generated") is
not independently observable and `generated = rejected_before_scoring + scored`
cannot be closed this session. It is **bounded, not unknown**: a decision whose
scored list holds < 16 entries provably lost nothing. `score_goal_candidates`
re-slices to 16 after sorting (`living_agent_reasoning.py:257`), but its input is
already capped, so that second slice is a proven no-op.

---

## 2. Per-family generation gates (VERIFIED — `build_settlement_candidates`)

Every gate below is a conjunct: **all** must hold for the candidate to be
appended. "count" = `_action_count(entity, X)` = `entity["living_action_counts"][X]`.

### 2a. Target family — all eight carry a monotone self-limiting counter

| Action | Goal | Line | Role gate | World / state gates | Self-cap | Base score |
|---|---|---|---|---|---|---|
| `warn` | WARN_DANGER | 401 | `scout` | ≥1 animal observed; ≥1 person visible | **< 2** | 2300 |
| `lie` | SHARE_RUMOUR | 414 | `rumourmonger` | ≥1 person visible; `tick >= 5` | **< 1** | 2050 |
| `apologise` | APOLOGISE | 424 | `rumourmonger` | ≥1 person visible; `lie count > 0`; `tick >= 12` | **< 1** | 2250 |
| `reconcile` | RECONCILE | 429 | `rumourmonger` | ≥1 person visible; `apologise count > 0`; **`elif`** of APOLOGISE | **< 1** | 1900 |
| `share_information` | VERIFY_INFORMATION | 435 | `steward` | ≥1 person visible; `storage-private` observed | **< 1** | 2000 |
| `trade` | TRADE_RESOURCES | 444 | `steward` | ≥1 person visible; carried `food > 0` | **< 1** | 1450 |
| `threaten` | THREATEN | 459 | `hoarder` | ≥1 person visible; `tick >= 8` | **< 1** | 1750 |
| `promise` | PROMISE_HELP | 368 | `caretaker` | ≥1 injured/critical person observed; **`elif`** of HELP_PERSON ⇒ requires `cooperate count >= 1` | **< 1** | 2100 |

Each role exists exactly once in `collective_groups` (inherited from
`living_settlement.py:33-48` via `emergent_groups`), so **every target action has
exactly one eligible actor in the entire world** — `person-007` (scout),
`person-005` (rumourmonger), `person-003` (steward), `person-004` (hoarder),
`person-001` (caretaker). VERIFIED from the scenario definition.

Two family-specific structures are findings in their own right:

- **`reconcile` and `promise` are `elif` branches**, not independent gates. Their
  prerequisite is the *exhaustion* of a sibling: `reconcile` requires
  `apologise count > 0`, and `promise` requires `cooperate count >= 1` so the
  HELP_PERSON branch stops claiming the `if`. Once the sibling's cap and its own
  cap are both consumed, the whole `if/elif` chain is permanently dead.
- **`apologise` depends on `lie`**, and `lie` is itself capped at 1. So the
  rumourmonger chain is a fixed three-step ladder (`lie` → `apologise` →
  `reconcile`), each rung consumable exactly once, with no cycle back.

### 2b. Reference family — no self-limiting counter on any of the three

| Action | Goal | Line | Gates | Self-cap | Base score |
|---|---|---|---|---|---|
| `cooperate` | RESPOND_HELP | 336-344 | pending `request_help` commitment where self is beneficiary; creator visible; role ≠ `skeptic` (else `refuse`) | **none** | 3100 |
| `cooperate` | HELP_PERSON | 363 | `caretaker`; injured person observed | < 1 | 2600 |
| `repay` | REPAY_DEBT | 345-354 | `debt` commitment created by self, status `active`/`broken`, beneficiary visible, age ≥ 1 tick | **none** | 2700 |
| `request_help` | REQUEST_HELP | 323-329 | `hunger >= 600`; ≥1 person visible | **none** | 1200 + hunger |

**This is the structural asymmetry.** Every target action is capped by a counter
that only ever increases; no reference action is capped at all. The recurring
three are also **not role-gated** — any person can generate them — whereas each
target has a single eligible actor.

`REPAY_DEBT` is generated inside a `for` loop over **all** commitments
(`:334`), so one actor with many debts emits many REPAY_DEBT candidates in one
decision. That is the most plausible mechanical route to candidate-cap
saturation, which is the one thing that could hide a target candidate from the
receipts (§1). Measured in deliverable 4 as `candidate_cap_saturated_decisions`
and per-action `stage_C_truncation_at_risk_decisions`.

---

## 3. The counter is monotone and world-scoped (VERIFIED)

`living_action_counts` has exactly **one** read site and **one** write site in
`backend/{core,domains,world}`:

- read: `_action_count` (`living_settlement_domain.py:88`)
- write: `living_settlement_domain.py:731-735`
  ```python
  action_counts[executed_action] = min(9999, action_counts.get(executed_action, 0) + 1)
  actor_update["living_action_counts"] = {key: action_counts[key] for key in sorted(action_counts)[:32]}
  ```

There is no decrement, reset, decay, or TTL anywhere. Two consequences:

1. **A target action's generation gate, once closed, is closed permanently for
   the remaining life of that actor.** Since each target has exactly one eligible
   actor, closing that actor's counter closes the action **for the whole world**.
   This is the leading structural hypothesis for "why no second firing", and the
   measured funnel tests it: if it holds, targets should show stage C/D ≈ 0 after
   their single firing, not losses at stage E.
2. The counter increments `executed_action`, not the *selected* action
   (`:707`, `:732`). A win that was rewritten to `move` increments `move`, **not**
   the social action — so travel preemption does **not** consume the cap. The cap
   is spent only on actual execution. VERIFIED.

Minor, recorded but not load-bearing: `sorted(action_counts)[:32]` retains only
the first 32 keys in ascending string order. `SOCIAL_DIRECT_ACTIONS` has 17
members and physical actions add roughly a dozen more, so the ceiling is close
enough to the observed key count to be worth a note, but no measured actor is
near it. Not investigated further — out of Session 1 scope.

---

## 4. group_state cannot gate any target action (VERIFIED — deliverable 8's code-read)

The plan budgets "counters + one code-read" for whether any target-action
prerequisite reads trimmed group state. The read-set of
`build_settlement_candidates` is:

`entity["stage6_role"]`, `entity["carried_resources"]`,
`entity["living_action_counts"]`, `entity["living_failed_goal_counts"]`,
`entity["plan"]`, `entity["paused_living_plan"]`, `entity["position"]`,
`state["pressures"]`, `state["commitments"]`, `state["relationships"]`,
`knowledge["facts"]`, `knowledge["known_tiles"]`, and the perception `delta`.

**No group registry is read at any point.** The only group-derived influence on
the decision is post-scoring: `_apply_group_goal_influence` (`:178`) and
`_apply_group_norm_influence` (`:237`) both filter on
`cand.get("goal") == "REPAIR_SHELTER"` and boost nothing else.

Therefore `group_state.payload_limit` saturation and whatever it trims **cannot**
gate, suppress, or delay any of the eight target actions or the three reference
actions. It can perturb the world only indirectly, by changing REPAIR_SHELTER's
priority and hence where agents are and what they do next. Cap counters are
still reported per window (deliverable 8) as context, but the causal question the
plan asked is answered NO by construction.

---

## 5. What this map predicts, and what would falsify it

Stated before the counts are read, so the funnel can contradict it:

- **Predicted:** each target action shows a single commit, then stage C/D → 0
  for the remainder of the run — the dominant mode is *prerequisite-never-recurs*
  (a consumed monotone counter), not *generated-but-loses*.
- **Falsified by:** any target action showing sustained stage C/D > 0 with
  stage E losses after its first commit. That would mean the counter is not the
  binding constraint and scoring competition is, redirecting the contract.
- **Also falsified by:** a non-zero `stage_C_truncation_at_risk_decisions` large
  enough to make "never generated" indistinguishable from "generated but
  truncated" — in which case the Session 2 A/B probe is required to separate them
  rather than optional.
- **Not predicted either way:** whether the reference family is broad behaviour
  or a narrow two-agent loop. Nothing in the static path constrains that;
  deliverable 7 measures it.

`warn` is the documented precedent for the map being incomplete: the plan records
its single firing as *wins-but-preempted*, and notes its recurrence blocker may be
a different mode from its first-firing mode. The funnel reports both — stage F
preemption counts and stage C/D recurrence — rather than collapsing them.
