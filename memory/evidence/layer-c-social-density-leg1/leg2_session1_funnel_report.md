# Layer C Social Density Leg 2 — Session 1 discovery report (receipts-only C–H funnel)

**Plan:** `memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md` §Phase 1,
"Session 1 — receipts-only funnel". Read-only investigation. No behaviour change,
no tuning, no contract, no fixes.

**Code state measured:** commit `77b8287d`, run in a detached worktree at HEAD.
`git diff --stat 180c43f4 HEAD` = the three baseline JSONs only, so the code is
byte-identical to the state that produced `baseline_collective_groups_5000.json`.
The working tree's uncommitted Leg 1 change (`STORE_SURPLUS_MIN_FOOD = 2`) is
**NOT** in the measured state — the worktree still reads
`resources.get("food", 0) >= 3` and defines no `STORE_SURPLUS_MIN_FOOD`. Chosen
because the plan anchors its evidence base to "post-age-leg HEAD 180c43f4" and
lists Leg 1's storage mechanism as out of scope for this leg.

**Primary run:** `collective_groups`, seed `living-agents-stage6`, 3,000 ticks, no
DB. `status: complete`, `replay_matches_entities: true`.

| tick | final_state_hash | replay |
|---|---|---|
| 1,000 | `03312018977e518227652d4929afb643bdc6db3fc99f7a7a5ee4e055754488a6` | true |
| 2,000 | `4ce5f2b67a42e7c1c96769d92f62cd19a0ea4fa4c75ac4d1be0aa0d28e079f63` | true |
| 3,000 | `fb032eaf6fa5041cea73e6172943ce31203809c1c3dab90b893aba8025597d7a` | true |

Scale: 24,000 decisions = 24,000 person-ticks = 24,000 alive-person-ticks (8
people, **zero deaths through 3,000 ticks** — consistent with the baseline's
0/0/2 at 1k/3k/5k). 63,609 accepted events, 5,581 rejected proposals.

---

## 1. Instrumentation neutrality — VERIFIED PASS

Evidence: `leg2_session1_neutrality_300.json`. `collective_groups`, seed
`living-agents-stage6`, 300 ticks, identical `run_id` across arms.

- **Claim 1 — the `capture_events` flag is canonically inert: PASS.** The ordered
  accepted-event hash stream is identical element-by-element
  (`first_divergent_event_index: null`), as are `final_state_hash`,
  `frame_sequence_hash`, `replay_state_hash`, `actions_by_type`,
  `accepted_by_type`, `rejected_by_reason`, `decisions_by_kind`, and the
  aggregate `summary_hash`. This is the check the baseline needed, since it ran
  with `capture_events: false`.
- **Claim 2 — the funnel probe is canonically inert: PASS.** Harness and probe
  both produced
  `f365ebcd83dab45c2fad2d418c119f25992cbfc052be58ed19cc6f5ca2789843`. Because
  both callers used the same `run_id` through different code paths, this also
  shows `run_id` does not leak into canonical state.

The probe monkeypatches **nothing** (`monkeypatched_functions: []`). It reads only
values `run_tick` already returns; `diagnostics` in particular is discarded by
`tools/living_agent_harness.py` today. Leg 1's probe patched
`build_settlement_candidates` — that is the stage A/B surface, and per the
session amendment it is deliberately not built here.

### Instrument defect found and corrected before classification

The first probe revision filtered decision rows with
`actor_id.startswith("person-")`. `run_tick` merges every enabled domain's
diagnostics into one dict (`core/kernel.py:130-132`), and
`lifecycle_domain.lifecycle_diag_key` emits `"person-000::lifecycle"`, which
passes that test. Result: 8 phantom zero-candidate rows per tick, doubling
`decisions_observed` (4,800 against a true 2,400 at 300 ticks) and pulling
`candidate_count_distribution` to min 0 / mean 1.26.

Funnel stage counts were never affected — phantom rows carry no candidates, so
they enter no stage, and every conservation identity stayed balanced. What was
corrupted was the **denominator**, including `candidate_cap_saturated_decisions`,
which is precisely the bound on stage-C observability. Fixed by selecting on the
positive marker `"decision_receipt" in row`. Post-fix the probe reproduces
`95ce1ac893bcf8ff66fcdf0567ed4f0d6c6f9a5595df199c2fb72de37c0b3fab` at 40 ticks,
byte-identical to the pre-fix run — the fix is canonically inert, as a read-side
filter must be.

*Recorded, not acted on:* Leg 1's `_probe_layer_c_social_density.py:279` carries
the identical `startswith("person-")` filter. It was harmless there (that probe
sourced opportunity counts from its monkeypatched builder, not from diagnostics),
but the pattern is live in committed tooling.

---

## 2. Lifecycle map per family

Full map: `leg2_session1_lifecycle_map.md` (deliverable 2). Summary of what
governs the funnel:

- All eleven tracked actions share one pathway; all eight targets are members of
  `SOCIAL_DIRECT_ACTIONS` and route through `build_social_action_proposal`.
  **No target action bypasses any stage** — confirmed statically *and*
  dynamically (§3, bypass detector).
- Stage F has three separable modes: travel preemption (winner rewritten to
  `move`, intent re-offered next tick as a continuation), pathfinding failure,
  and builder `ValueError` → fallback `rest`.
- **All eight targets carry a monotone `_action_count(X) < N` guard; none of the
  three reference actions carry any.** `living_action_counts` has one read site
  and one write site, increment-only, with no decrement, reset, decay or TTL.
- Each role occurs exactly once in the scenario, so each target action has
  exactly one eligible actor in the entire world.
- `reconcile` and `promise` are `elif` branches requiring a sibling's cap to be
  spent first (`apologise > 0`; `cooperate >= 1`).

---

## 3. Stage-conservation table

**All 33 identities balanced (11 actions × 3 identities). Zero unmatched counts,
zero bypass.**

| identity | result |
|---|---|
| `scored = lost + won` | balanced, 11/11 actions |
| `won = preempted + invalidated + rejected + committed + other + no_record` | balanced, 11/11 |
| `committed(resolved from decisions) = raw committed events` (bypass detector) | balanced, 11/11 |

The second identity is reported with the extra `commit_rejected` / `other` /
`no_commit_record` terms the plan's three-term form omits. That is not cosmetic:
`commit_rejected` is large for the reference family (§7), and folding it into
"invalidated" would have hidden it.

**Stage C is bounded, not closed.** `build_settlement_candidates` truncates to
`candidates[:16]` in append order before any receipt exists, so
`generated = rejected_before_scoring + scored` cannot be closed from receipts.
Measured bound: **1 cap-saturated decision out of 24,000** (max observed
candidate count 16, mean 2.66, p90 5). For 23,999 of 24,000 decisions C = D is
*proven*, not assumed, and at most one decision could have hidden any given
target candidate. Truncation is not a material confound in this run.

---

## 4. Per-action funnel table

Counts are decisions (per actor-tick), not candidates. Percentages are relative
to the immediately preceding stage.

### Target family

| action | C/D scored | actors | at-risk | won | lost | preempt | inv-plan | inv-build | rejected | G committed | H in stream |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `warn` | 1 | 1 | 1 | 1 (100%) | 0 | 0 | 0 | 0 | 0 | 1 (100%) | 1 |
| `share_information` | 4 | 1 | 1 | 4 (100%) | 0 | 2 | 0 | 1 | 0 | 1 (25%) | 1 |
| `lie` | 2 | 1 | 1 | 2 (100%) | 0 | 1 | 0 | 0 | 0 | 1 (50%) | 1 |
| `promise` | 2 | 1 | 1 | 2 (100%) | 0 | 0 | 0 | 0 | 1 | 1 (50%) | 1 |
| `apologise` | 1 | 1 | 1 | 1 (100%) | 0 | 0 | 0 | 0 | 0 | 1 (100%) | 1 |
| `reconcile` | 2 | 1 | 1 | 2 (100%) | 0 | 1 | 0 | 0 | 0 | 1 (50%) | 1 |
| `threaten` | 1 | 1 | 1 | 1 (100%) | 0 | 0 | 0 | 0 | 0 | 1 (100%) | 1 |
| `trade` | 5 | 1 | 1 | 1 (20%) | 4 | 0 | 0 | 0 | 0 | 1 (100%) | 1 |

### Reference family

| action | C/D scored | actors | won | lost | preempt | inv-build | rejected | G committed | H in stream |
|---|---|---|---|---|---|---|---|---|---|
| `cooperate` | 1,957 | 4 | 1,957 (100%) | 0 | 94 | 0 | 1,082 | 781 (39.9% of won) | 781 |
| `repay` | 1,347 | 8 | 1,114 (82.7%) | 233 | 11 | 0 | 683 | 420 (37.7% of won) | 420 |
| `request_help` | 5,153 | 8 | 1,688 (32.8%) | 3,465 | 41 | 6 | 1,110 | 531 (31.5% of won) | 531 |

### Firing times — every target fires once, in ticks 1–14, then never again

| action | tick | actor | role | target | decision kind |
|---|---|---|---|---|---|
| `warn` | 1 | person-007 | scout | person-001 | new_goal |
| `share_information` | 4 | person-003 | steward | person-000 | plan_continuation |
| `trade` | 5 | person-003 | steward | person-002 | new_goal |
| `lie` | 6 | person-005 | rumourmonger | person-004 | plan_continuation |
| `promise` | 6 | person-001 | caretaker | person-007 | new_goal |
| `threaten` | 8 | person-004 | hoarder | person-000 | new_goal |
| `apologise` | 12 | person-005 | rumourmonger | person-004 | new_goal |
| `reconcile` | 14 | person-005 | rumourmonger | person-004 | plan_continuation |

Committed target actions by window: **window 0 (ticks 1–1,000) — all eight;
window 1 — none; window 2 — none.** Every target has exactly one actor and one
actor→target pair for the whole run.

### Self-cap gate state (canonical `living_action_counts`, of 24,000 alive-person-ticks)

| action | cap | closed | open | % closed |
|---|---|---|---|---|
| `warn` | 2 | 0 | 24,000 | **0.0%** |
| `share_information` | 1 | 2,997 | 21,003 | 12.5% |
| `lie` | 1 | 2,995 | 21,005 | 12.5% |
| `promise` | 1 | 2,995 | 21,005 | 12.5% |
| `apologise` | 1 | 2,989 | 21,011 | 12.5% |
| `reconcile` | 1 | 2,987 | 21,013 | 12.4% |
| `threaten` | 1 | 2,993 | 21,007 | 12.5% |
| `trade` | 1 | 2,996 | 21,004 | 12.5% |

12.5% is exactly one actor of eight with the counter spent, from shortly after
the firing tick to the end of the run.

---

## 5. Dominant and secondary failure modes per action

Applied to the RECURRENCE question — why no second firing. Not forced to one
class where several contribute.

| action | dominant mode (recurrence) | secondary | verdict |
|---|---|---|---|
| `share_information` | **prerequisite-never-recurs** — cap 1 spent at tick 4, closed 2,997/3,000 ticks | first-firing only: 2 wins preempted by travel, 1 builder `ValueError` "social target must be adjacent" before the tick-4 commit | CLASSIFIED |
| `lie` | **prerequisite-never-recurs** — cap 1 spent at tick 6 | 1 travel preemption before commit | CLASSIFIED |
| `promise` | **prerequisite-never-recurs** — cap 1 spent at tick 6; also `elif`-gated behind `cooperate >= 1` | 1 commit-pipeline `precondition.failed` before commit | CLASSIFIED |
| `apologise` | **prerequisite-never-recurs** — cap 1 spent at tick 12; upstream `lie` cap also spent, so the ladder cannot restart | none | CLASSIFIED |
| `reconcile` | **prerequisite-never-recurs** — cap 1 spent at tick 14; `elif`-gated behind `apologise > 0` | 1 travel preemption | CLASSIFIED |
| `threaten` | **prerequisite-never-recurs** — cap 1 spent at tick 8 | none | CLASSIFIED |
| `trade` | **generated-but-loses, then prerequisite-never-recurs.** Genuinely two modes: lost 4 of 5 scorings to `VERIFY_INFORMATION` (`lost_by` median 8,623, min 5,593) — both are `steward`-only candidates from the same actor, and `share_information` outscores `trade`. Once `share_information`'s cap closed, `trade` won and spent its own cap at tick 5 | — | CLASSIFIED (plan-excluded, see §10) |
| `warn` | **UNDETERMINED — the self-cap is NOT the blocker.** Cap is 2, the scout consumed 1, so the gate was open for 100% of 24,000 alive-person-ticks. The `animal-threat` entity was alive all 3,000 ticks. `warn` was still generated exactly once (tick 1), won, and committed with zero preemption | — | **INSUFFICIENT EVIDENCE** |

**`warn` contradicts the plan's recorded precedent.** The plan states "warn's
single firing was wins-but-preempted". In this run `warn` was generated once, won
once, and committed once with **no** preemption at all. Its recurrence blocker
lies upstream of stage C, in the perception-dependent conjunction
`animals AND visible_person_ids` — the stage A/B surface Session 1 does not
instrument by design. This is exactly the Session 2 trigger condition.

---

## 6. Seed-sensitivity note

**NOT RUN — no result.** The pre-registered ~1,200-tick comparison seed
(`living-agents-stage6-alt`) was launched three times during this session and
terminated externally each time; the final attempt was stopped ~7 minutes in,
before the tick-1,000 checkpoint, so no partial output exists. No
`leg2_session1_funnel_seedalt_1200.json` was produced. Recorded as a gap, not as
a null result — nothing about seed sensitivity was measured either way.

**Consequence: every measured claim in this report is single-seed**, and per
CORE-INTEGRITY-004 single-run action-count deltas are untrustworthy at
tens-of-percent scale. The plan's purpose for this run — separating seed-specific
pathology from structure — is therefore **unmet**, and remains open.

Scope of the exposure, stated precisely so it is not overstated or understated:

- **Not seed-exposed:** the self-cap mechanism. `living_action_counts` having one
  read site, one write site, increment-only with no decrement/reset/decay, and
  each role occurring exactly once in the scenario, are properties of committed
  code and of the scenario definition. No seed changes them.
- **Seed-exposed:** every number. Firing ticks (1–14), the `trade` vs
  `share_information` scoring margins, all reference-family rates, all
  concentration and unique-actor figures, the 55–66% commit-pipeline attrition,
  and the `group_state` headroom curve.
- **Seed-exposed and load-bearing:** `warn`'s INSUFFICIENT EVIDENCE verdict rests
  on a single observation (C/D = 1) in a single seed. A second seed is the
  cheapest way to learn whether one generation in 3,000 ticks is characteristic
  or seed-specific, and it should be obtained before Session 2 designs a
  semantic-opportunity definition around it.

What single-seed status does *not* threaten: the self-cap mechanism is a
structural property of committed code (one read site, one write site,
increment-only), not a seed-dependent measurement. What it does threaten: the
exact firing ticks, the `trade` vs `share_information` scoring margins, and every
reference-family rate and concentration figure.

---

## 7. Reference-family concentration table

The word "healthy" is **withheld**. Two distinct problems appear.

### Participation breadth per 1,000-tick window

| window | action | committed | rate /alive-person-tick | unique actors | unique pairs | top pair | top-pair share |
|---|---|---|---|---|---|---|---|
| 0 (1–1,000) | `cooperate` | 266 | 0.033250 | **2** | 9 | person-000→person-002 ×81 | 30.5% |
| 0 | `repay` | 147 | 0.018375 | 8 | 8 | person-002→person-000 ×49 | 33.3% |
| 0 | `request_help` | 211 | 0.026375 | 8 | 8 | person-002→person-000 ×43 | 20.4% |
| 1 (1,001–2,000) | `cooperate` | 305 | 0.038125 | **3** | 9 | person-001→person-000 ×81 | 26.6% |
| 1 | `repay` | 183 | 0.022875 | 8 | 9 | person-000→person-001 ×47 | 25.7% |
| 1 | `request_help` | 160 | 0.020000 | 8 | 9 | person-001→person-000 ×31 | 19.4% |
| 2 (2,001–3,000) | `cooperate` | 210 | 0.026250 | **4** | 10 | person-000→person-001 ×46 | 21.9% |
| 2 | `repay` | 90 | 0.011250 | 8 | 10 | person-005→person-000 ×26 | 28.9% |
| 2 | `request_help` | 160 | 0.020000 | 8 | 10 | person-005→person-000 ×39 | 24.4% |

Alive population is 8 in every window; there is no thinning to flatter the rates
at this horizon.

**The narrow-loop hypothesis is half-confirmed, and it names a different action
than expected.** The plan flagged "repay 776 vs apologise 1" as making a
two-agent debt treadmill live. Measured: **`repay` is broad** — all 8 actors
participate in every window, 8–10 distinct pairs, top-pair share 26–33%.
**`cooperate` is the narrow one** — only 2, 3 and 4 distinct actors across the
three windows, i.e. at most half the camp ever cooperates, with an 81-commit
single pair in each of the first two windows. `request_help` is broad (8 actors,
lowest concentration at 19–24%).

### A second, larger problem: most winning social intents never commit

| action | won | committed | share of wins committed | rejected | rejection reasons |
|---|---|---|---|---|---|
| `cooperate` | 1,957 | 781 | **39.9%** | 1,082 (55.3%) | `precondition.failed` 1,048, `social_action.not_adjacent` 34 |
| `repay` | 1,114 | 420 | **37.7%** | 683 (61.3%) | `precondition.failed` 677, `social_action.not_adjacent` 6 |
| `request_help` | 1,688 | 531 | **31.5%** | 1,110 (65.8%) | `precondition.failed` 1,105, `social_action.not_adjacent` 5 |

Run-wide rejections: `precondition.failed` 5,386 (96.5% of all 5,581),
`group_state.stale_membership` 150, `social_action.not_adjacent` 45. Between 55%
and 66% of *winning* reference-family decisions are refused by the commit
pipeline. UNKNOWN: what `precondition.failed` is actually failing on — the
reason code is not decomposed further in the rejection record. Not investigated;
out of Session 1 scope, and flagged as a candidate Session 2 or contract-phase
question.

`request_help` also loses heavily at scoring: 5,153 scored → 1,688 won (32.8%),
with `lost_by` median 6,305 (p90 12,204).

---

## 8. `group_state` cap attribution

**Code-read (bounded, as the plan budgets):** no target-action prerequisite reads
`group_state` or any group registry. `build_settlement_candidates` reads only
`stage6_role`, `carried_resources`, `living_action_counts`,
`living_failed_goal_counts`, `plan`, `paused_living_plan`, `position`, and from
living-agent state `pressures`, `commitments`, `relationships`, plus `knowledge`
and the perception `delta`. The only group-derived influence is post-scoring:
`_apply_group_goal_influence` (`:178`) and `_apply_group_norm_influence` (`:237`)
both filter on `cand.get("goal") == "REPAIR_SHELTER"` and boost nothing else.

**Therefore `group_state` trimming cannot gate, suppress or delay any of the
eight target actions or the three reference actions.** It can perturb the world
only indirectly, via REPAIR_SHELTER priority. The plan's question is answered NO.

**Counters:**

| window | peak payload | hard cap | peak headroom | ticks over operational target (49,152 B) | recognised groups | active goals | active norms |
|---|---|---|---|---|---|---|---|
| 0 | 53,886 B | 65,536 B | 17.78% | 846 / 1,000 | 11 | 0 | 0 |
| 1 | 58,760 B | 65,536 B | 10.34% | 1,000 / 1,000 | 12 | 0 | 0 |
| 2 | 63,385 B | 65,536 B | **3.28%** | 1,000 / 1,000 | 13 | 0 | 0 |

Two observations recorded, neither acted on:

1. **Headroom is 3.28% at tick 3,000 and falling monotonically.** Culture
   invariant C-4 requires ≥20% measured peak headroom. This run is below that
   from window 1 onward. Flagged as cap context, per the plan's instruction that
   it "must be captured before any slice that adds group facts".
2. **`group_state.payload_limit` fired zero times in this run.** The plan's
   evidence base records it binding "after ~3k (321 rejections)"; at exactly
   3,000 ticks it has not yet bound here. `group_state.stale_membership` fired
   150 times (50 per window, flat). Group goals and norms are zero throughout,
   matching the baseline.

---

## 9. Per-action evidence-sufficiency verdicts

The plan's rule triggers on **stage A semantic opportunities**, which Session 1
does not measure by design (the amendment moved all A/B instrumentation to
Session 2). The rule's trigger therefore cannot be evaluated on its own terms.
Recorded honestly rather than silently substituted.

Observable proxy — stage C/D scored decisions over 3,000 ticks: `warn` 1,
`threaten` 1, `apologise` 1, `lie` 2, `promise` 2, `reconcile` 2,
`share_information` 4, `trade` 5. All eight are below 20.

**Extension to 5,000 ticks was NOT run.** Justification, offered as a
recommendation the user may override:

- For the seven counter-gated actions, extension is *provably* uninformative:
  the gate is a monotone counter measured closed for ~2,990 of 3,000 ticks, and
  it has no decrement, reset or decay path in committed code. A longer horizon
  cannot reopen it.
- The 5,000-tick answer for commits is **already committed evidence**: the plan's
  own base records "Singleton family: exactly 1 firing each at tick 1,000,
  unchanged at 5,000" (`baseline_collective_groups_5000.json`). Re-running to
  5,000 would add stage C/D counts only, not change any classification.
- Per CLAUDE.md proportionality: the cheapest decisive observation already exists.

| action | verdict | basis |
|---|---|---|
| `share_information` | **SUFFICIENT — CLASSIFIED** | complete funnel; gate measured closed 2,997/3,000 |
| `lie` | **SUFFICIENT — CLASSIFIED** | complete funnel; gate closed 2,995/3,000 |
| `promise` | **SUFFICIENT — CLASSIFIED** | complete funnel; gate closed 2,995/3,000 |
| `apologise` | **SUFFICIENT — CLASSIFIED** | complete funnel; gate closed 2,989/3,000; upstream `lie` also closed |
| `reconcile` | **SUFFICIENT — CLASSIFIED** | complete funnel; gate closed 2,987/3,000 |
| `threaten` | **SUFFICIENT — CLASSIFIED** | complete funnel; gate closed 2,993/3,000 |
| `trade` | **SUFFICIENT — CLASSIFIED** (plan-excluded, §10) | complete funnel; two modes measured |
| `warn` | **INSUFFICIENT EVIDENCE** | 1 observation at C/D; gate open 100% of the run; blocker is upstream of stage C and unmeasured this session. Classification and causal claims withheld for this action only |

Low volume is **not** converted into "pathway broken" anywhere in this report.
For seven actions the finding is positive and mechanical: a measured, monotone,
consumed counter. For `warn` the finding is that Session 1 cannot answer it.

---

## 10. Scope notes

- **`trade` is measured but plan-excluded.** The canonical plan removes it from
  the singleton family ("food-coupled, Stage 9 F-A") and lists it under Out of
  scope; the session prompt named it among the targets. Measuring it cost
  nothing, so its funnel is published, flagged here and in the payload
  (`trade_note`) so it cannot silently drive a contract.
- **`claude/SOCIAL-DENSITY-LEG-PLAN.md` (REV 2.1) was never read.** It is not on
  disk and the Basic Memory Cloud connector returns "Your Basic Memory trial has
  ended". This report follows the committed canonical doc
  (`CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md`, which declares
  itself canonical over that mirror) plus the session prompt. If REV 2.1 §Phase 1
  differs, the ratified doc governs and this report must be re-checked against it.
- No mechanism, constant, contract change, behavioural slice, utility tuning, new
  canonical state or fix is proposed anywhere in this document.

## 11. Files

| file | contents |
|---|---|
| `leg2_session1_neutrality_300.json` | neutrality gate, both claims, all compared fields |
| `leg2_session1_lifecycle_map.md` | deliverable 2, per-family lifecycle map |
| `leg2_session1_funnel_collective_groups_3000.json` | primary run: full funnels, conservation, windows, causal neighbourhoods, examples |
| `leg2_session1_funnel_seedalt_1200.json` | **not produced** — comparison seed never completed (§6) |
| `leg2_session1_funnel_report.md` | this report |
| `backend/tools/_probe_layer_c_singleton_funnel.py` | the probe |
| `backend/tools/_probe_capture_events_neutrality.py` | the neutrality gate |
