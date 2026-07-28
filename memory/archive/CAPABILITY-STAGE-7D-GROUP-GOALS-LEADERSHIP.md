# Capability Stage 7D — Group Goals and Emergent Leadership

Status: **Implemented and verified; organic reachability PROVEN via the Stage 6
Liveness Pass (completed 2026-07-17).** Mechanism is full-kernel verified after
correcting review-found defects. Over a 1,000-tick `collective_groups` run the
`maintain_shared_shelter` goal is organically adopted **11 times** from naturally
formed `shared_shelter` facts (no seeding), with 0 deaths and repeat + replay
determinism. The instantaneous `final_active_group_goal_count` at tick 1000 is 0
by an emergent, structural dynamic (members self-solve via private shelters, and
tick 1000 is dawn) — organic reachability is therefore proven by the cumulative
`accepted` count, not the end-tick snapshot. See `STAGE-6-LIVENESS-PASS.md`
Close-out for the full evidence and root-cause. (updated 2026-07-17).

> **Correction (2026-07-16).** An earlier revision of this document claimed the
> mechanism was "verified" with organic emergence "deferred as Stage-6-blocked".
> That mechanism claim was **overstated**: a subsequent Codex adversarial review
> found that in the *enabled* kernel every adoption/cleanup proposal was rejected
> (`group_goal.stale_membership`) because group_goal committed after Stage 7A/7B
> revision churn — so adoption had never actually been exercised end-to-end, and
> the 14 focused tests all bypassed the full commit pipeline. The review also
> found a group could hold multiple simultaneous goals (one per shared_shelter
> fact, 16/tick vs the documented 1-per-group/4-per-tick), that validation
> accepted a forged `goal_id`/`ttl_tick`, and that the influence hook boosted
> stale supporters and could override an urgent survival decision. These are now
> fixed (commits on the branch then named `capability/stage-6-living-agents`,
> renamed to `capability/stage-8-culture` 2026-07-18), each with
> full-kernel or focused regression tests. The mechanism is therefore verified
> **through the real commit pipeline**, not in isolation.
>
> The earlier "organic emergence is Stage-6-blocked" analysis was **correct but
> incomplete**: even with the two Stage 6 causes (no shelter decay; comfort
> urgency peaks at 79 < the 150 want-activation threshold), the ordering defect
> would independently have rejected any adoption. With the ordering defect fixed,
> the remaining blocker is genuinely the Stage 6 world dynamics, which the **Stage
> 6 Liveness Pass** (`STAGE-6-LIVENESS-PASS.md`) now addresses. Organic
> reachability is therefore **in progress, not deferred**; the final organic
> proof and the re-baselined `living_settlement` hash are recorded by that pass.

The proposal-only `group_goal` domain, its `group-goal-registry-v1`, the Core
validator/provenance wiring, the guarded read-only Stage 6 upkeep-influence hook,
and harness reporting are implemented. Drafted 2026-07-14 as the ratified "depth"
next-capability after Stage 7C; the contract below is implemented (constants
finalised in the "Implemented constants" note).

## Goal

Prove that a recognised group can hold **one bounded collective goal** with an
**emergent, deterministically-derived coordinator**, where the goal is
member-grounded, Core-authored, inspectable, and *influences* member decisions
without commanding them. This is the smallest honest step from "groups act
together once" (7C) toward "groups pursue shared intent over time."

## Why this behaviour, and why it is organically reachable

Stage 7C's organic emergence is blocked on a surplus economy (Stage 9), because
it consumes `shared_storage` facts that require storage actions that require
surplus. Stage 7D deliberately grounds its proof on **`shared_shelter`** facts
instead, which the 1,000-tick `collective_groups` run showed **do** form
organically (9 shared facts, 11 recognised groups, no seeding required). Stage 7D
therefore closes the group loop on a link that already fires in natural runs.

## Agency model (no hidden group mind)

1. Stage 7A supplies recognised membership (canonical association registry).
2. Stage 7B supplies a `shared_shelter` fact for a shelter the group co-uses.
3. The Stage 7D domain is **proposal-only**. It evaluates a pinned frame and
   derives at most one collective-goal proposal per group per evaluation.
4. **Adoption precondition:** the shared shelter's `condition` is below a fixed
   threshold **and** at least two current members individually hold the
   `improve_shelter` want (member-grounded — the group cannot want what no member
   wants).
5. **Coordinator** = lexicographically first eligible living member id (same
   deterministic rule as the 7C initiator). Recorded with provenance. The
   coordinator has **no command authority** and issues no orders.
6. **Core alone** validates preconditions and writes the group-goal record.

The group never scores privately, never owns a planner, never mutates member or
world state, and never auto-includes members. A member who does not hold the
`improve_shelter` want is not bound by the group goal.

## How the goal "affects decisions" without commanding

A live group-shelter-upkeep goal is consumed by Stage 6 **only as read-only
context**, applying a small bounded priority increment to the `REPAIR_SHELTER`
candidate **of members who already hold the `improve_shelter` want**. It cannot
create a goal a member lacks, override survival goals, or force action. The
influence path runs only in scenarios where the `group_goal` domain is enabled,
so the frozen `living_settlement` Stage 6 determinism hash is unaffected.

## Chosen behaviour

**`adopt_shelter_upkeep_goal`** (`group-goal-v1`)

When a recognised group has a Stage 7B `shared_shelter` fact for a shelter whose
`condition < UPKEEP_THRESHOLD`, and ≥2 current members hold `improve_shelter`,
the group adopts a single canonical `maintain_shared_shelter` goal naming the
shelter, the coordinator, and the supporting members. The goal expires
deterministically when the shelter recovers above the threshold, when support
falls below two members, or after a fixed TTL.

## Proposed contracts

| Item | Value |
|---|---|
| Proposal type | `group_adopt_collective_goal` |
| Proposal family | `group_goal` |
| Goal schema | `group-goal-v1` |
| Domain | `group_goal` (proposal-only; engine_priority TBD, after `group_collective`) |
| Registry | new `group-goal-registry-v1` (separate, versioned) |
| Scenario | reuse `collective_groups` (+ `group_goal` domain), no new seeding |

## Proposed bounds

- max collective goals per group: 1
- max goals adopted per tick (all groups): 4
- coordinator: single first-eligible member id; no obedience
- priority increment to member `REPAIR_SHELTER`: small fixed cap, member must
  already hold `improve_shelter`
- goal TTL and `UPKEEP_THRESHOLD`: fixed constants
- group-goal registry hard cap: TBD (target < 32 KiB), no 7A/7B/7C caps raised

## Explicit non-goals

Voting, elections, deposable authority, obedience, taxation, punishment, laws,
succession, multiple simultaneous goals, warfare, diplomacy, culture, religion,
politics, economy, LLM decisions, arbitrary group spawn, population targets,
Stage 8 institutions, player control, frontend redesign. Leadership here is a
recorded coordinator role only, not command.

## Proposed acceptance gate

1. Focused `group_goal` unit tests: adoption precondition, two-member support
   requirement, coordinator derivation/order, member-grounded influence (a member
   without `improve_shelter` is unaffected), expiry (recovery / support loss /
   TTL), no mutation of member or world state, replay, resume reconstruction,
   duplicate-key idempotence, capacity bound.
2. Integrated regression: Stage 6 / 7A / 7B / 7C focused suites stay green.
3. Determinism: two `collective_groups` traces (documented seed) match; replay
   and resume equality hold with `group_goal` enabled.
4. Frozen-hash safety: `living_settlement` 320-tick hash **unchanged**
   (`group_goal` domain absent there; the Stage 6 influence path is inert).
5. Organic proof: over a 1,000-tick `collective_groups` run, ≥1 shelter-upkeep
   goal is adopted from naturally-formed `shared_shelter` facts (no seeding).
6. Capacity: group-goal registry stays under its hard cap with ≥20% peak
   headroom; no cap raised on 7A/7B/7C.

## Open questions for review

- Exact `UPKEEP_THRESHOLD`, TTL, and priority-increment cap (determinism-visible
  constants — set before implementation, not during).
- Whether the coordinator role should carry *any* future contract hook, or remain
  a pure record until a later stage.
- Registry hard-cap value and compaction policy (mirror the 7B.1 approach).

## Implemented constants (determinism-visible)

| Constant | Value | Location |
|---|---|---|
| `UPKEEP_THRESHOLD` | 750 | `domains/group_goal_contracts.py` |
| `GOAL_TTL_TICKS` | 48 | `domains/group_goal_contracts.py` |
| `MIN_SUPPORTERS` | 2 | `domains/group_goal_contracts.py` |
| `SUPPORT_WANT_TYPE` | `improve_shelter` | `domains/group_goal_contracts.py` |
| `GROUP_GOAL_REPAIR_INCREMENT` | 250 | `domains/living_settlement_domain.py` |

## Verification results (2026-07-16)

> **Superseded in part — see the Correction note at the top.** The mechanism
> gates below were run against the *isolated* domain functions and the 79-test
> focused set, which did not exercise adoption through the full commit pipeline;
> a later review found the enabled kernel rejected all adoptions (now fixed). The
> frozen-hash and determinism results below stand. The "organic emergence
> DEFERRED" conclusion is superseded: it is being established by the Stage 6
> Liveness Pass, whose final organic-adoption count and re-baselined
> `living_settlement` hash replace the numbers here.

**STATUS (as recorded 2026-07-16, mechanism claim later corrected): mechanism
focused-verified; organic emergence then believed Stage-6-blocked.**

### Post-Liveness organic proof (VERIFIED 2026-07-17 — supersedes the numbers below)

The Stage 6 Liveness Pass (`STAGE-6-LIVENESS-PASS.md`) made organic 7D adoption
reachable. Current verified results (seed `living-agents-stage6`):

- **Focused tests — 90 passed** (7A/7B/7C/7D); full Stage 6 + 7 set 136 passed;
  full backend suite 306 passed.
- **Frozen Stage 6 gate — deliberately re-baselined.** `living_settlement
  --ticks 320 --repeat 2`: `repeat_matches: true`, `replay_matches: true`, new
  canonical `final_state_hash =
  84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2` (was
  `8ff861b8…069a`). The re-baseline is intentional — passive shelter wear +
  full-exposure comfort change the Stage 6 trace on purpose.
- **Organic adoption — PROVEN.** `collective_groups --ticks 1000 --repeat 2`:
  `accepted_by_type["group_adopt_collective_goal"] = 11`, 0 deaths,
  `repeat_matches: true`, `replay_matches: true`.

| Field (`collective_groups` 1000×2, 2026-07-17) | Value |
|---|---|
| `accepted[group_adopt_collective_goal]` | **11** |
| `final_state_hash` | `cb238522c776947e46640efd9fd7ca2fa96f0c2cb922cff83f3813d9ecb67321` |
| `group_goal_summary_hash` | `71b7847963563c2ab4d53e07672bdd765ae5cd904c5be37f7a71d9f98a14de41` |
| `final_active_group_goal_count` @1000 | **0** (emergent artifact — see below) |
| `final_group_goal_count` | 7 |

**Why `final_active@1000` is 0 despite 11 organic adoptions:** the goal is
grounded in a personal, exposure-driven `improve_shelter` want. Members
autonomously build private shelters over the run (`has_shelter=True`, permanent)
and self-solve, so by ~tick 950 zero members hold the support want (verified:
`best_supporters=0` across ticks 950–1000, night ticks included); and tick 1000
is dawn (no night-exposure term). The goal emerges mid-run and recedes as members
self-solve — a plausible trajectory, not a failure. Reachability is proven by the
cumulative `accepted` count. Full root-cause in `STAGE-6-LIVENESS-PASS.md`.

---

### Gates met (VERIFIED) — HISTORICAL, pre-Liveness (2026-07-16), superseded above

- **Focused tests — 79 passed.** `tests/test_stage7d_group_goal.py`,
  `test_stage7c_group_collective.py`, `test_stage7b_group_state.py`,
  `test_stage7a_associations.py`.
- **Frozen Stage 6 safety — PRESERVED (pre-Liveness).** `living_settlement
  --ticks 320 --repeat 2` (seed `living-agents-stage6`): `repeat_matches: true`,
  `final_state_hash =
  8ff861b85614eb4139feaf71e10d34dd630d9b9869b35044b6a90577eaaf069a`
  (the then-frozen value; re-baselined by the Liveness Pass — see above). The
  Stage 6 group-goal influence hook is inert when no `group-goal-registry-v1`
  exists, as designed.
- **Integrated determinism + replay — VERIFIED.** `collective_groups --ticks
  1000 --repeat 2` (seed `living-agents-stage6`): `repeat_matches: true`,
  `replay_matches_final_entities: true`.

Recorded `collective_groups` 1,000-tick hashes (seed `living-agents-stage6`):

| Field | Value |
|---|---|
| `final_state_hash` | `0a5a018934fa0579075e9ec44e898bf8b9cfd1bae4497e8662c68c936e6a6a84` |
| `association_summary_hash` | `479e2a037bac4ed8631f91ad795ff86890b481f42d64c6d99f8b84950b8a3225` |
| `group_state_summary_hash` | `1e640fde4ccd73eb75ae3d894fbc2ab1ab44a0098ae3b3bdf120538a0f2a621c` |
| `group_goal_summary_hash` | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` (empty registry) |
| `final_recognised_group_count` | 11 |
| `final_shared_group_fact_count` | 9 |
| `final_active_group_goal_count` | **0** |
| `final_group_goal_count` | **0** |

### Gate deferred, not open — organic long-run adoption (Stage-6-blocked)

Over 1,000 ticks, **0** `maintain_shared_shelter` goals were adopted. No
`group_adopt_collective_goal` proposal was even generated (none accepted, none
rejected), so the block is in the derivation preconditions, not validation. A
per-tick diagnostic probe (seed `living-agents-stage6`, single 1,000-tick run)
isolated the binding constraint:

- **Member-grounding never satisfied (binding constraint).** The number of
  members holding an *active* `improve_shelter` want was **0 on every one of the
  1,000 ticks**; the maximum eligible supporters in any recognised group was
  **0**. A want is stored `active` only when its strength ≥ 150
  (`domains/living_agent_cognition.py`); the `improve_shelter` want's strength is
  the agent's comfort-pressure urgency, which **peaked at 79** (peak comfort
  severity 618) — always below 150, so the want stayed `dormant` throughout.
- **Shelter-condition precondition also starved.** A `shared_shelter` fact's
  target was below `UPKEEP_THRESHOLD` (750) on only **1 of 1,000 ticks**. Shared
  facts settled on `shelter-family` (steady condition 850) and `shelter-damaged`
  (repaired 380 → 980 by the builder role); observed shared-shelter condition
  range was 740–980. There is no shelter-weathering/decay mechanism, so repaired
  shelters remain above the threshold.

Because the member-grounding constraint is threshold-independent (supporters = 0
regardless of `UPKEEP_THRESHOLD`), **no Stage 7D constant can produce an organic
adoption.** Raising `UPKEEP_THRESHOLD` (e.g. 750→900) would satisfy the *shelter*
side (e.g. `shelter-family`@850) but leaves supporters at 0, so it was not
applied — changing it would be a blind change that does not close the gate.
Achieving organic adoption requires an upstream Stage 6 change (comfort/exposure
pressure reaching the want-activation threshold, or a shelter-decay mechanism),
which would alter the frozen `living_settlement` determinism hash and is out of
scope for Stage 7D. Organic emergence is therefore **deferred and
dependency-blocked on Stage 6 dynamics**, mirroring 7C's deferral, and the seeded
mechanism gates above stand as 7D's verification. **Decision (2026-07-16):**
recorded as deferred per user direction; no Stage 6 change made.
