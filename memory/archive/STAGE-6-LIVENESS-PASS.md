# Stage 6 Liveness Pass — IMPLEMENTED (2026-07-17)

Status: **IMPLEMENTED and verified (2026-07-17).** Three bounded changes landed
(passive shelter wear; comfort→want calibration; a scenario-scoped food fix).
The frozen Stage 6 `living_settlement` determinism gate was **deliberately
re-baselined**: old hash `8ff861b8…069a` → new canonical hash
`84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`
(`living_settlement --ticks 320 --repeat 2`, repeat + replay match). Organic
Stage 7D reachability is **proven** over a 1,000-tick `collective_groups` run:
`accepted_by_type["group_adopt_collective_goal"] = 11`, 0 deaths, repeat +
replay match. See the **Close-out** section below for the full result set,
including why the instantaneous `final_active@1000` metric was superseded by the
cumulative `accepted` count.

## Close-out (VERIFIED, 2026-07-17)

**What shipped (three bounded changes):**
1. **Passive shelter wear** — `ecology_domain._wear` + `STRUCTURE_WEAR_*`
   constants. Weather-driven, floored at 0, proposal-only via the environment
   phase. Applies globally (re-baselines the frozen gate on purpose).
2. **Comfort→want calibration** — `living_agent_cognition.py` comfort pressure
   uses the natural full-exposure coupling (was an arbitrary `exposure//2`), so
   the shared-shelter-dependent, shelterless-at-night members cross the 150
   want-activation gate together. Peak urgency ≈350 in the sustained camp (well
   under the starving all-shelterless artifact of 430), survival still dominant.
3. **Food fix (scenario-scoped, added 2026-07-17 with owner approval)** —
   `collective_groups.py` raises the non-regrowing `food-patch` from 12 to 999
   (mirrors the `water_source`), deep-copied so the frozen `living_settlement` /
   `emergent_groups` genesis is untouched. Without it the camp starved out by
   ~tick 790; with it the population is fully sustained (0 deaths) over 1,000
   ticks. Contained to `collective_groups` only.

**Verified results:**
- Focused suites green: 136 passed (46 Stage 6 + 90 for 7A/7B/7C/7D); full
  backend suite 306 passed (4 pre-existing Docker-path collection errors
  excluded, unrelated).
- Determinism: `living_settlement 320×2` and `collective_groups 1000×2` both
  `repeat_matches` + `replay_matches_final_entities` = True.
- Organic 7D: `collective_groups 1000×2` →
  `accepted_by_type["group_adopt_collective_goal"] = 11`, 0 deaths.
- New frozen hash `84d3ad52…c32d2`; `collective_groups` canonical final hash
  `cb238522…7321`, `group_goal_summary_hash 71b78479…de41`.

**Why `final_active@1000` was superseded by `accepted` (root-cause, VERIFIED):**
The 7D goal is grounded in a *personal* `improve_shelter` want (exposure-driven,
active only at night for a member without a functional shelter). Two structural
facts make the instantaneous end-tick count 0 regardless of any comfort/wear/food
tuning: (a) agents autonomously **build private shelters** over the run
(`has_shelter=True`, permanent), self-solving their comfort need, so by ~tick 950
zero members hold the support want and the collective goal recedes; and (b) tick
1000 is **dawn** (`1000 % 100 = 0`), when even a shelterless member has no
night-exposure term. Confirmed by an end-game probe: `best_supporters = 0` across
ticks 950–1000 including every night tick. This is a plausible living-world
trajectory (the goal *emerges* mid-run when members are shared-shelter-dependent
and *recedes* as they self-solve), not a failure. Making the end-tick count ≥1
would require changing 7D's member-grounding semantics (a personal want → a
shared-asset want), which is out of this pass's scope and violates the
"member-grounded" invariant. Owner decision (2026-07-17): **accept organic
reachability as proven by `accepted ≥ 1` (11 adoptions) + sustained population +
determinism**, and record the end-tick artifact honestly.

## Historical plan (as authorised 2026-07-16)

## Why this, and why now

Two consecutive group-behaviour stages are mechanism-verified but **organically
dormant**: 7C (blocked on a Stage 9 surplus economy) and 7D (no goal adopts over
1,000 ticks). Both are starved by the same root cause — the Stage 6 world does
not produce the conditions the higher stages consume. Building Stage 8 on top
would stack a third dormant stage. This pass makes the foundation *live* enough
to exercise 7D organically before adding new capability breadth.

## Root cause (VERIFIED in code, 2026-07-16)

7D adoption needs BOTH: a shared shelter with `condition < UPKEEP_THRESHOLD (750)`
AND ≥2 members holding an **active** `improve_shelter` want. Neither occurs:

1. **Shelters never degrade.** No passive shelter-condition decay exists anywhere
   (`grep`: only carcass decay in `ecology_domain.py` and tool wear in
   `living_agent_actions.py`). `collective_groups` shelters sit at 850–980 for the
   whole run, so condition never crosses 750.
2. **`improve_shelter` never activates.** `refresh_wants`
   (`living_agent_cognition.py:505`) sets the want strength to the *comfort*
   pressure urgency; a want is `active` only at `strength >= 150`
   (`cognition.py:539`). Comfort urgency = f(exposure, fatigue) via
   `cognition.py:427–465`, and over 1,000 ticks it never reaches 150 → the want
   stays dormant for every agent.

## Goal

Make sustained exposure and shelter wear deterministically produce (a) shelter
conditions that fall below the upkeep threshold, and (b) active `improve_shelter`
wants — so ≥1 Stage 7D goal is adopted organically over 1,000 ticks, without
seeding, while preserving determinism and Core authority.

## Scope

**In scope (two bounded, determinism-visible changes):**
1. **Passive shelter degradation.** A small deterministic condition decrement for
   shelter/structure entities, driven by weather exposure and/or elapsed ticks,
   bounded and floored (never below 0). Proposal-only through the existing
   commit/authority path (candidate: extend `ecology_domain` or a narrow new
   `structure_wear` proposal). Repair actions already raise condition, so this
   creates a real wear/repair loop.
2. **Comfort→want calibration.** Adjust the exposure/comfort coupling
   (`cognition.py:427–465`) and/or the want-activation coupling so that an agent
   under sustained exposure with a degraded shelter reaches comfort urgency ≥ 150
   and holds an active `improve_shelter` want. Prefer the smallest change that
   crosses the threshold under real conditions — do not lower the 150 gate blindly.

**Out of scope:** new wants/goals beyond `improve_shelter`; any change to survival
goal dominance; new social/economic mechanics; Stage 7/8 behaviour; tuning
`UPKEEP_THRESHOLD` as a substitute for real degradation (raising it to 900 is a
fallback lever only if degradation proves too slow, and must be recorded as such).

## Invariants (MUST preserve)

- Deterministic + replayable: two traces match; replay equals final entities.
- Proposal-only; Core alone mutates; no new authority path.
- Survival goals still dominate — agents must not abandon food/water/sleep to
  repair. Verify `actions_by_type` and `goals_by_actor` show a sane balance, not
  a repair spiral.
- Bounded: shelter condition floored at 0; wear rate small; no unbounded state.
- The frozen `living_settlement` hash is **intentionally superseded** — record the
  new canonical 320-tick hash and update every doc that cites `8ff861b8…069a`.

## Acceptance gate (as met — see Close-out for evidence)

1. Focused suites green: Stage 6 living-agent tests + 7A/7B/7C/7D. **MET** —
   136 passed (46 Stage 6 + 90 for 7A/7B/7C/7D); full suite 306 passed.
2. Determinism: two `living_settlement` and two `collective_groups` 1,000-tick
   traces each match (`repeat_matches` + replay). **MET.**
3. **Organic 7D proof (reworded, owner-approved 2026-07-17):** over a 1,000-tick
   `collective_groups` run, `accepted_by_type["group_adopt_collective_goal"] >= 1`
   with no seeding — the goal is organically adopted from naturally formed
   `shared_shelter` facts. **MET — 11 adoptions.** The original clause also
   required `final_active_group_goal_count >= 1`; that instantaneous end-tick
   metric is 0 for structural reasons independent of the Liveness levers (members
   self-solve via private shelters; tick 1000 is dawn — see Close-out) and was
   superseded by the cumulative `accepted` count, which is the substantive proof.
4. Behavioural sanity: survival actions remain the majority; **no agent starves
   or dehydrates (0 deaths)**; survival dominance holds (deaths were 100%
   food/water in the un-fixed baseline, 0 from a repair pull). Note: the *shared*
   shelters **degrade to 0 and are not continually repaired** late-run — this is
   the same emergent dynamic as (3): members build private shelters and stop
   maintaining the shared one, so the idealised "oscillate rather than pin" is
   not literally observed for the shared shelters. Recorded honestly, not tuned
   away (tuning wear/comfort cannot change the self-solving trajectory).
5. New canonical Stage 6 `living_settlement` hash recorded:
   `84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2` (was
   `8ff861b8…069a`); docs citing the old frozen hash updated. Registry capacities
   unchanged/within caps. **MET.**
6. No 7A/7B/7C/7D hard caps raised; no new domain authority. **MET.**

One Stage 6 behavioural test shifted under the re-baseline and was updated
honestly: `test_stage6e_living_settlement.py::test_integrated_camp…` asserted a
*broken* commitment within a 30-tick window; passive shelter wear perturbs the
deterministic schedule so the first breach now lands just past tick 30 (after the
tick-40 storm), and cannot co-occur with that test's `weather==["rain"]` window.
The assertion was relaxed to "commitments form and are tracked"; the broken-
commitment path remains directly covered by `test_stage6d_social_relationships`.

## Constants likely in play (confirm before changing)

| Constant / seam | Current | Location |
|---|---|---|
| want-activation threshold | `strength >= 150` | `living_agent_cognition.py:539` |
| comfort pressure formula | `exposure//2 + (1000-energy)//3` | `living_agent_cognition.py:440` |
| comfort tolerance | `50 - comfort_preference` | `living_agent_cognition.py:455` |
| urgency scaling | `max(0, severity - tolerance) * weight // 100` | `living_agent_cognition.py:465` |
| shelter passive decay | **none (missing)** | to add |
| `UPKEEP_THRESHOLD` | 750 | `group_goal_contracts.py` |

## Risks

- Highest-blast-radius change in the sequence: comfort pressure and shelter wear
  touch every Stage 6 agent and every scenario's hash. Measure the current
  comfort-urgency distribution first; change the minimum that crosses thresholds.
- Cascade risk: more exposure pressure can shift energy/rest/gather balance.
  Watch for regressions in existing Stage 6 behavioural expectations.
- Re-baselining the frozen hash removes a safety anchor — do it once, deliberately,
  with the new hash recorded and reviewed.

## Sequencing note

The 5A2 live-transaction infrastructure gate is independent and can proceed in
parallel. Fold the pending Codex adversarial-review findings on the 7D diff into
this pass before implementation, since they may touch the same Stage 6 seams.
