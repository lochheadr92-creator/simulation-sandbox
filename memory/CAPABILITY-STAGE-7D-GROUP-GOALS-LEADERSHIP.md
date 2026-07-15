# Capability Stage 7D — Group Goals and Emergent Leadership (PROPOSED CONTRACT)

Status: **PROPOSED — planned, not authorised.** This is a draft contract for
review. Implementation requires explicit acceptance and its own checkpoint plan,
per the Global completion rules in `CAPABILITY_ROADMAP.md`. Drafted 2026-07-14
as the ratified "depth" next-capability after Stage 7C.

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
