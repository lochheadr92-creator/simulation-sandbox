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

## Known limitation — organic reachability (measured 2026-07-14)

The focused gate proves 7C in the seeded `collective_groups` scenario, which
hand-places two members adjacent to `storage-camp` with pre-loaded carried
surplus. An **unseeded** organic run (emergent_groups world, natural positions,
no injected surplus; 40-tick harness probe, seed `stage7b1-capacity`) measured:

| Link | Result | Starved? |
|---|---|---|
| 7A group recognition | 4 recognised groups | no — forms naturally |
| 7B shared facts (any category) | 7 facts | no — forms naturally |
| 7C coordinated deposit | 0 accepted, 0 `group_collective.*` rejections | **yes — never proposes** |
| storage actions, all agents | store 1, retrieve 2, access 0 | very rare |

**Diagnosis (VERIFIED signal; LIKELY at full horizon).** Recognition and
generic fact-formation are healthy. The starving link is the *input* to 7C:
`shared_storage`-category **7A evidence**, which requires two recognised-group
members to act (`store`/`retrieve`/`access`) on the *same* shared/public storage
within the evidence window. Organically this rarely happens because:

- The `STORE_SURPLUS`→`store`-to-shared-storage candidate
  (`living_settlement_domain.build_settlement_candidates`) is gated on carrying
  `food >= 3` and scores 1350, so survival goals (~2600) routinely outrank it;
- retrieve/take candidates target `storage-private`, not shared storage, so they
  do not generate `shared_storage` evidence;
- `SUPPORT_FRESHNESS_TICKS = 4` (Stage 7B) is a tight window for two members'
  independent stores to coincide.

**Tested and rejected fix.** Relaxing the `STORE_SURPLUS` precondition
(`food >= 3` → `>= 2`) and raising its score (1350 → 1650) was applied and
measured. Focused suite stayed 65/65, but a 40-tick unseeded probe showed **no
change** in store frequency (still 1). The change was reverted — it moves the
frozen Stage 6 `living_settlement` hash for zero organic gain.

**1,000-tick seeded evidence (2026-07-14, default seed `living-agents-stage6`).**
A full `collective_groups --ticks 1000 --repeat 2` run:

- `stage7c.accepted_count = 0` **and** `rejected_count = 0` — 7C never even
  proposes over 1,000 ticks. The domain has no candidate to evaluate.
- `store = 0`, `retrieve = 1` across all agents — storage actions are effectively
  absent, so no `shared_storage`-category 7A evidence can form.
- `final_shared_group_fact_count = 9` — shared facts do form, but (store ≈ 0)
  these are `shared_shelter`, not the `shared_storage` category 7C consumes.
- `repeat_matches = true`, `replay_matches_final_entities = true` with
  `group_collective_domain_enabled = true`; association peak headroom 25.1%,
  group-state 24.7% (both above the 20% target).

**Reasoned conclusion — deferral, not defect.** The 7C *mechanism* is proven
(15 focused tests) and the 1,000-tick run independently satisfies 7C's
persistence/replay, integrated 6→7A→7B→7C determinism, and projection-safety
gates. The only unmet gate — organic reachability — is blocked at its first
link: agents in a survival-pressured camp have no surplus to store, so shared
*storage* use (as opposed to shared *shelter*) essentially never happens.
Reliable surplus is a **Stage 9 (Economy)** capability, downstream of Stage 7C
in the capability chain. Forcing organic 7C reachability now — by tuning the
Stage 6 planner — would build a higher capability on an absent lower one, the
exact anti-pattern the roadmap forbids.

**Decision:** organic reachability is **deferred, dependency-blocked on Stage 9
surplus economy**. The seeded `collective_groups` scenario remains 7C's
legitimate mechanism-acceptance proof. 7C is therefore *mechanism-verified;
organic emergence deferred*, and is removed from the critical path for the
Stage 8-vs-depth decision.

(Note: this run used the harness default seed `living-agents-stage6`, not the
`stage7b1-capacity` seed behind the recorded 7B.1 hashes, so its
`final_state_hash 0a5a0189…` is not comparable to `31f27b2c…`; re-record with
the documented seed if a canonical 7C organic-gate hash is wanted.)
