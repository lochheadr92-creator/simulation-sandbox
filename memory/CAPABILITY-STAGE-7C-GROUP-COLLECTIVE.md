# Capability Stage 7C - Group Behaviour and Collective Action

Status: Stage 7C baseline implemented and focused-verified on 2026-07-13
(kernel/test-harness). Not marked fully verified while broader product-facing
explanation UI and any remaining infrastructure gates remain open.

## Goal

Prove one narrow end-to-end collective behaviour grounded in Stage 7A
membership and Stage 7B shared facts, without creating a hidden group mind.

## Agency model

Collective agency originates as follows:

1. Stage 7A supplies recognised membership (canonical association registry).
2. Stage 7B supplies shared context (`shared_storage` facts only for this slice).
3. The Stage 7C domain is **proposal-only**. It evaluates a pinned frame and
   derives eligible multi-member deposits.
4. **Initiator** = lexicographically first eligible living member id.
5. **Participants** = sorted eligible members (cap 4), each causally justified
   by membership, liveness, availability, adjacency to storage, and carried
   resources.
6. Proposal `entity_id` is the initiator. The proposal lists all participants,
   deposits, revisions, and causal parents.
7. **Core alone** validates, revalidates preconditions, and mutates person
   inventories and storage contents.

The group never scores privately, never owns a planner, never mutates state
outside Core, and never auto-includes every member.

## Chosen behaviour

**`coordinated_storage_deposit`** (`group-collective-action-v1`)

When a recognised group has a Stage 7B `shared_storage` fact for a shared/public
storage entity, two or more eligible members may deposit one unit each
(prefer `food_inventory`, else wood `inventory`) into that storage in one
atomic accepted event.

Why this is the smallest useful proof:

- reuses existing storage entities and inventory fields;
- consumes Stage 7B shared facts as read-only context (aligned with the Stage
  7B.1 boundary note);
- produces multi-party canonical consequences through Core;
- exercises eligibility, initiator selection, conflict, replay, and bounds.

## Contracts

| Item | Value |
|---|---|
| Proposal type | `group_coordinated_storage_deposit` |
| Proposal family | `group_collective_action` |
| Action schema | `group-collective-action-v1` |
| Domain | `group_collective` (engine_priority 90) |
| Scenario | `collective_groups` (+ `group_collective` domain) |

## Bounds

- max participants per action: 4
- max collective actions derived per tick: 4
- processed action keys retained on storage: 64
- causal parents per proposal: 16
- collective_action metadata payload soft ceiling: 16 KiB

No Stage 7A/7B hard caps were raised for Stage 7C.

## Explicit non-goals

Leadership, voting, governance, obedience, warfare, diplomacy, culture,
religion, politics, group personality, LLM decisions, arbitrary group spawn,
population targets, Stage 8 institutions, frontend redesign.

## Focused verification

```
cd backend
python -m pytest tests/test_stage7c_group_collective.py -q
# 15 passed

python -m pytest tests/test_stage7c_group_collective.py tests/test_stage7b_group_state.py tests/test_stage7a_associations.py -q
# 65 passed (after scenario domain-list assertion update for group_collective)
```

Covered: eligibility, initiator/order, end-to-end deposit, exclusions, stale
membership, death, conflict, shuffled arrival, replay, no partial mutation on
reject, busy exclusion, domain activation, duplicate key, participant cap,
resume reconstruction.
