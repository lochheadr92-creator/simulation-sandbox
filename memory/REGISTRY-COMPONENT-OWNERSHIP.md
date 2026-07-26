# COMPONENT OWNERSHIP + DOMAIN ORDERING REGISTRY

**Status: PROPOSED — first pass.** Built per `ARCHITECTURE-SPINE.md` §11
(risk-based, not exhaustive). Indexes, not essays.

**Stamped as of `d1c18f52`; re-confirmed valid at `23fa8160`.**
The worktree line was merged into `capability/stage-8c-phase1-aid-exchange`
(`cf06a323`), and `backend/` at HEAD is **byte-identical** to `d1c18f52`
(`git diff --stat d1c18f52 HEAD -- backend/` is empty, VERIFIED). Every
`file:line` citation below therefore applies unchanged to the current canonical
checkout. One renumber to carry: the frame-knowledge-aliasing finding registered
as **002** in `d1c18f52` is **003** from `23fa8160` — the merge exposed a
collision with the pre-existing 002 concurrency-CAS stub. Three distinct
findings, three numbers: 001 lost-update, 002 concurrency-CAS, 003
frame-knowledge aliasing.

> **Re-verification note.** The inventory was read at `5267217b`; two commits
> landed during it (`c2d7b4c6 fix(core): integrity repairs`, `d1c18f52`) and
> have since been re-checked against the rows below:
>
> - **Interventions rows — resolved, rating unchanged.** `c2d7b4c6`'s
>   "intervention CAS" is a CAS on `next_order_index` at the **API request**
>   layer (`api/routes.py`, guarding concurrent intervention requests against
>   an order-index collision), *not* a field-level CAS on the need values.
>   `core/interventions.py` `boost_need` still carries `"preconditions": []`
>   while writing `hunger` / `thirst` / `energy`. The LOW rating stands, but it
>   rests **entirely on frame isolation** (the intervention commits in its own
>   frame), not on any precondition. If interventions are ever folded into the
>   domain frame, these rows become HIGH with no guard at all.
> - **Line-anchor drift in `core/commit_pipeline.py`:** `order_key` is now
>   line **108** (cited as 109 below); `collective_action` stamping 492 and
>   event metadata 550 are unmoved. Other anchors in that file may be off by
>   ±1.
> - `c2d7b4c6` and `d1c18f52` touch none of F1, F2 or F3.
>
> **Provenance of the repairs:** `c2d7b4c6`'s in-code comments attribute them to
> a "KIMI review, 2026-07-25". `CORE-INTEGRITY-002` records that "the review
> document itself was not locatable in this repo" and that findings were
> independently re-derived from the code. The document exists — it is
> `claude/KIMI-ADVERSARIAL-REVIEW-2026-07-25.md` in the Claude project, which is
> not synced into the repo tree. Cost: one round of re-derivation that was not
> needed.

**Method:** read-only code inventory (grep/read, no execution) by three
independent passes over `backend/domains`, `backend/core` and `backend/tests`.
Every writer claim carries `file:line`. **Reasoning-level evidence, not
execution-level** — no run was performed, so collision *reachability* in a
shipped scenario is LIKELY where marked, not VERIFIED.

**Scope (per §11):** canonical person-state; cognition/social state;
group/culture registries; structures; shared storage; all domains carrying an
`engine_priority`. **Out of scope this pass:** the Event Family Registry (third
registry, not built), animal/weather internals, migration policies.

---

## Table 1 — Component Ownership

| Component / Field | Entity Type | Canonical Owner | Current Writers (file:line) | Legal Cross-Owner Writes | Collision Risk | Tests |
|---|---|---|---|---|---|---|
| `action` | person (also animal) | `people_domain` *(desert_oasis, wilderness_survival)* / `living_settlement_domain` *(living_settlement, emergent_groups, collective_groups)* — mutually exclusive per scenario | `people_domain.py:385`; `living_settlement_domain.py:777`; `living_agent_actions.py:521`; `living_agent_social.py:315`; `group_collective_contracts.py:283`; `lifecycle_domain.py:168`; `animal_domain.py:105,147`; Core stamps sub-keys `commit_pipeline.py:292-297` | `lifecycle_domain.py:168` (death) — **contractual**: environment phase, prio 1, commits first; actor proposals then fail their `alive eq True` precondition (`people_domain.py:402`, `living_agent_actions.py:295`) | **HIGH** — see F3. Owner-rated HIGH by one pass, Low-Medium by another; recorded HIGH pending the discriminating test | **None pin ownership.** Nearest: `test_stage7c_group_collective.py:257`, `test_layer_c_upkeep.py:159` (both other fields) |
| `living_agent` (whole blob) | person | `living_settlement_domain` / `people_domain` per scenario | `people_domain.py:389`; `living_settlement_domain.py:776`; `living_agent_social.py:318,327,348-349,362-363,382-383,474`; sub-keys stamped `commit_pipeline.py:226-264` | `living_agent_social.py:327,474` writes the **target's** blob — contractual, gated by `validate_social_action_proposal` (`living_agent_social.py:570-574`) and CAS at `:324,:331`, re-pinned by `living_settlement_domain.py:515-518` | **MEDIUM** — see F4 (asymmetric CAS) | Behaviour only: `test_stage6d_social_relationships.py:70,136,165`; `test_stage6a_living_cognition.py:246,277-279` |
| `living_agent.pressures` | person | `living_agent_cognition` (derived into the blob) | produced only at `living_agent_cognition.py:530`; `living_agent_contracts.py:179,283` | — | inherits `living_agent` | `test_stage6a_living_cognition.py:278` (key set) |
| `living_agent.relationships` | person | `living_agent_social` (`apply_relationship_consequence:73`, write `:137`) | self: `people_domain.py:389`, `living_settlement_domain.py:776`; cross-entity: `living_agent_social.py:318,327,348-349,362-363,382-383,474`, emitted `:537`, invoked `living_settlement_domain.py:660-670` | cross-entity write of B's blob by A — contractual, CAS-protected | **HIGH** (rejection, not loss — CAS revalidated `commit_pipeline.py:476`). `people_domain.py:401-405` adds **no** `living_agent` precondition | `test_stage6d_social_relationships.py:57,76,79-111`; caps `test_stage6_contracts.py:51` |
| `living_agent.memories` | person | `living_agent_cognition` (`merge_meaningful_memories:702`, write `:800`) | `people_domain.py:132→389`; `living_settlement_domain.py:565,756→776` | — (observer-scoped: built from own observations/action_result) | **MEDIUM** — rides in the `living_agent` blob; a whole-blob overwrite takes memories with it | caps `test_stage6a_living_cognition.py:189,279`; `test_stage6_contracts.py:50` |
| `knowledge` (`knowledge-v2`) | person | `perception` (`merge_knowledge:289`, returns `:433`) | `people_domain.py:395`; `living_settlement_domain.py:655,715`; **cross-entity** `living_agent_social.py:457` | none declared | **HIGH — see F1. No precondition on `knowledge` exists anywhere in the repo** | observer-scoping `test_phase5a5_cognitive.py:91`; caps `test_phase5b2_social_observations.py:169`; replay `:215-216` |
| `knowledge.interaction_memory` (`interaction-memory-v1`) | person | `interaction_memory` (`merge_interaction_memory:441`, write `:481`) | sole producer `people_domain.py:100→395` | — (strictly observer-scoped, `compute_eligible_witness_ids:234`) | **MEDIUM** — nested inside `knowledge`, so inherits F1 | `test_phase5b4_interaction_memory.py:282,293,424,430-467,470-499` |
| `reciprocity_trust` view | *(no entity field)* | `reciprocity_trust` | **none — zero writers.** Read-only consumers `people_domain.py:357`, `people_utility.py:253,263`, `food_interaction_proposals.py:442-443` | — | **LOW** | `test_phase5b5_reciprocity_trust.py:162-163,375-376,389-393,401-410,502-514` |
| `hunger` | person (also animal) | per-scenario action owner | `people_domain.py:373`; `living_settlement_domain.py:708,714`; `living_agent_actions.py:422`; `core/interventions.py:25`; `animal_domain.py:104` | `interventions.py:25` player boost — contractual, commits in its own frame (`api/routes.py:467-470`) | **LOW** *(re-verify: `c2d7b4c6` added intervention CAS)* | `test_simulation_sandbox.py:158-169` (behaviour only) |
| `thirst` | person | per-scenario action owner | `people_domain.py:374`; `living_settlement_domain.py:709-711,714`; `living_agent_actions.py:431`; `interventions.py:25` | as above | **LOW** *(same re-verify)* | `test_phase5a3_navigation.py:369` |
| `energy` *(canonical; `fatigue` is derived)* | person | per-scenario action owner | `people_domain.py:375`; `living_settlement_domain.py:712,715`; `living_agent_actions.py:435,503,505`; `interventions.py:25` | as above | **LOW** | — |
| `fatigue` | — | **no canonical field exists** | none — derived at `living_agent_cognition.py:470` as `1000 - energy` | — | inherits `living_agent` | `test_stage6a_living_cognition.py:278` |
| `carried_resources` / `inventory` / `food_inventory` | person | per-scenario action owner | `people_domain.py:378,425`; `living_agent_actions.py:138` via `:342,395,399,421,447,468`; `living_agent_social.py:240` via `:395-396,422-423`; `group_collective_contracts.py:293`; genesis `world/generator.py:97` | `people_domain.py:425` (food receiver), `living_agent_social.py:396,423` (target), `group_collective_contracts.py:293` — all contractual and CAS-guarded | **LOW/MEDIUM** — every producer CASes (`living_agent_actions.py:345,406-408,423`; `living_agent_social.py:404-405,432-433`; `group_collective_contracts.py:351-356`) | `test_stage6c_physical_actions.py:69,71,87,137,163,203`; `test_stage7c_group_collective.py:225,247,345` |
| Structure `condition` (wear) | shelter / structure | **shared — no single owner** | ecology wear `ecology_domain.py:100`; repair/damage `living_agent_actions.py:470-471`; tend `living_agent_actions.py:485-489`; created at 1000 `:452` | Yes by design — environment-phase wear vs agent-phase repair/tend | **MEDIUM** — resolved by phase order + strict CAS; see F7 | `test_layer_c_upkeep.py:113,136,152,159,197`; `test_stage6c_physical_actions.py:144-161` |
| Structure `max_condition` | shelter / structure | creation only | `living_agent_actions.py:452` | none | none | — |
| Shared storage `contents` | storage | **contested** | `living_agent_actions.py:399-401` (prio 10, CASes `contents` at `:406-407`); `group_collective_contracts.py:296` (prio 90, **no storage precondition**) | intended: both write camp storage | **HIGH — see F2** | `test_stage7c_group_collective.py:186,257,272`; **no test mixes a living `store` with a collective deposit in one tick** |
| Storage `collective_processed_keys`, `last_collective_action_key/tick` | storage | `group_collective` | `group_collective_contracts.py:296-307` | none | LOW | `test_stage7c_group_collective.py:369` |
| `association-registry-000` (membership) | registry | `association` (90) | `association_contracts.py:838,846` — sole writer | none; downstream domains only pin `revision` as `eq` | **LOW** — commits last, so earlier readers' pins still match | `test_stage7a_associations.py` |
| `group-shared-state-000` (incl. `shared_storage`) | registry | `group_state` (89) | `group_state_contracts.py:488,497` | none; validator restricts `entity_updates` to this ID (`:693`) | **LOW** — diagnostic duplicate at prio 91 (`:581`) is deliberately rejected | `test_stage7b_group_state.py` |
| `group-goal-000` | registry | `group_goal` (88) | `group_goal_contracts.py:430,437` | none; validator restricts (`:515`) | LOW | `test_stage7d_group_goal.py` |
| `group-norm-000` | registry | `group_norm` (87) | `group_norm_contracts.py:512,519` | none; dual-slot guard (`:604-610`) | LOW | `test_stage8a_group_norm.py` |
| `group-carriage-000` | registry | `group_carriage` (86) | `group_carriage_contracts.py:524,531` | none; dual-slot guard (`:623-625`) | LOW | `test_stage8b_leg1_norm_transmission.py` |

---

## Table 2 — Domain Ordering

Lower `engine_priority` commits first. Order key:
`(requested_time, PHASE_RANK[phase], engine_priority, content_hash)` —
`commit_pipeline.py:109`.

| Domain | Phase | Prio | Writes | Must run before | Must run after | Reason the ordering protects |
|---|---|---|---|---|---|---|
| `weather` | environment | −2 | `weather-000` | ecology | — | **UNDOCUMENTED** |
| `ecology` | environment | 0 | resources, structure `condition` | all agent actions | weather | Documented `ecology_domain.py:64-70` — wear commits before repair so a wear tick and a repair on one structure resolve as wear-then-rejected-repair, retried next tick |
| `lifecycle` | UNKNOWN | 1 | person lifecycle | — | ecology | **UNDOCUMENTED** |
| `people` | agent | 10 | person state | group domains | environment | **UNDOCUMENTED** |
| `living_settlement` | agent | 10 | person state, structure `condition`, storage `contents` | group domains | ecology | **UNDOCUMENTED at the class**; nudge rationale only at `living_settlement_domain.py:138-146,189-207` |
| `animal` | UNKNOWN | 20 | animals | group domains | environment | **UNDOCUMENTED** |
| `group_carriage` | agent | 86 | `group-carriage-000` | norm, goal, state, association | living_settlement | Documented `group_carriage_contracts.py:33-40`, `group_carriage_domain.py:19-28` — its pinned upstream revisions revalidate before 87/88 bump them; avoids same-tick stale-precondition rejection |
| `group_norm` | agent | 87 | `group-norm-000` | goal, state, association | carriage | Documented `group_norm_domain.py:17-24` — commits before 88/89/90 so pinned upstream revisions still match; cost is a documented one-tick lag |
| `group_goal` | agent | 88 | `group-goal-000` | state, association | norm | Documented `group_goal_domain.py:17-22` — commit before 7A association (90) and 7B group_state (89) churn revisions; fixes same-frame `stale_membership` rejection |
| `group_state` | agent | 89 | `group-shared-state-000` | association | goal | **UNDOCUMENTED at the class** — intent implied only by downstream comments |
| `association` | agent | 90 | `association-registry-000` | — | everything | **UNDOCUMENTED at the class** — terminal write in the chain |
| `group_collective` | agent | 90 | person resources, person `action`, storage `contents` | — | group_state | `group_collective_contracts.py:398-399` — "want collective AFTER group_state". **Priority tie with `association` at 90**, broken only by `content_hash`; see F6 |

---

## Findings

Ranked. Each is the CORE-INTEGRITY-001 shape unless stated: `core/mutations.py:24`
is a plain `entities[eid].update(updates)` — whole-value replace per top-level
key, no merge, no version check — so **a field with no CAS precondition is
unprotected by construction**, and preconditions are the only defence
(`commit_pipeline.py:376-497`).

**F1 — `knowledge` has no precondition anywhere in the repo. HIGH.**
`living_agent_social.py:457` (actor's proposal writes the *target's* knowledge)
and `living_settlement_domain.py:715` (that target's own knowledge write) both
land in one tick with no CAS on `knowledge`. Silent last-writer-wins.
*Distinct from CORE-INTEGRITY-**003*** (frame-knowledge aliasing — registered as
002 in `d1c18f52`, **renumbered to 003 in `23fa8160`** after the merge exposed a
collision with the pre-existing 002 concurrency-CAS stub). 003 is a **read-side**
defect — in-place aliasing of pinned-frame fact records in
`perception.py::_compat_knowledge`. Same field, different mechanism: 003 is a
frame-purity violation, F1 is a write-side lost update. Both should be
dispositioned together; neither subsumes the other.

**F2 — Shared storage `contents` lost update. HIGH.**
`group_collective_contracts.py:296` writes the whole `contents` dict, built
from the pinned pre-tick frame (`:266`), with **no precondition on the storage
entity at all** (`:326-361` covers only registry revisions and each
participant's `alive`/`carried_resources`). It commits at prio 90, after
`STORE_SURPLUS` (`living_settlement_domain.py:390-397`) at prio 10, which
*does* CAS `contents` (`living_agent_actions.py:406-407`). Same tick, same
storage → the collective write silently reverts the agent's deposit. Both
domains ship together in `collective_groups` (`scenarios/collective_groups.py:65-72`),
and that scenario deliberately seeds two storage-adjacent people with surplus
food (`:31-42`). Asymmetric: the reverse order is safe.

**F3 — `group_collective` clobbers person `action`. HIGH.**
`group_collective_contracts.py:283,286-292` overwrites `action.type` to
`group_collective_deposit` with **no `action` CAS** in its precondition set
(`:327-363`). It CASes `carried_resources` (`:350-356`), so when the victim's
`living_settlement` action that tick does not touch resources (`rest`, `drink`,
`move`, a social action) the CAS still passes and the freshly-committed action
is overwritten. `_is_available` (`:78-85`) reads the pre-frame action status and
cannot see it.
**Consequence for the explanation guarantee:** `living_agent.current_decision`
and `causal_links` (written at `living_settlement_domain.py:766-776`) survive
and still reference the discarded action's `action_id`/`plan_id` — so the
decision receipt points at an action that never happened. That is a direct hit
on the "every explanation drawn only from committed decision data" rule.
*Rating conflict, recorded not resolved:* one inventory pass rated this HIGH
with the mechanism above; another rated it Low-Medium without addressing the
resource-free-action case. **Discriminating test:** a `collective_groups` tick
where a deposit-eligible member's selected action is `rest`. Not written.

**F4 — Asymmetric CAS on `living_agent`. MEDIUM.**
`build_social_action_proposal` CASes both actor and target
(`living_agent_social.py:324,331`); `build_physical_action_proposal` CASes
neither (`living_agent_actions.py:294-296` is `alive` only). Since
`living_settlement_domain.py:776` attaches `living_agent` to *every* proposal
including physical ones, the guard is one-directional: A's social write onto B
committing before B's own write loses the relationship consequence; the reverse
order is caught. Reads as an omission, not a design.

**F5 — Single-source-of-truth violation on "trust". MEDIUM.**
Two unreconciled representations: canonical
`living_agent.relationships[*].trust` / `perceived_reliability`, range
−1000..1000, signal-driven (`living_agent_social.py:26-49,101-109`); and derived
`support_score`/`caution_score`/`reciprocity_net`, range 0..100, fact-driven
(`reciprocity_trust.py:119-131`). Different consumers use different ones:
`food_interaction_proposals.py:442-443` gates auto-accept on the **derived**
caution score, while `living_agent_cognition.py:489-492` and
`living_settlement_domain.py:447` drive pressures and decisions off the
**canonical** field. The test that appears to pin the boundary,
`test_phase5b5_reciprocity_trust.py:502-508`, only asserts `"trust" not in
entities[oid]` at the entity top level — it never looks inside
`living_agent.relationships`.

**F6 — Undeclared priority tie at 90** between `association` and
`group_collective`, broken only by `content_hash`. Currently benign (disjoint
entities) but unrecorded. LOW.

**F7 — Dead, actively misleading `engine_priority` literal.**
`group_collective_contracts.py:383` sets `88` with a self-questioning comment
arguing the opposite conclusion; `:400` unconditionally overwrites it with `90`
before returning. Two contradictory comments survive in one function. **90
ships.** LOW severity, high confusion cost.

**F8 — `group_collective` is a behavioural dead end.** It commits real
mutations, but no domain reads its output to make a decision: `collective_action`
is event metadata only (`commit_pipeline.py:550`), and `collective_processed_keys`
is read only by itself for dedupe and by the harness
(`tools/living_agent_harness.py:205-209,322`). Observable in the event log and
storage totals; nothing reacts to it. Confirms the 7C "dead end" note in the
technical handoff.

**F9 — Structure `condition` is sound.** Recorded because it was the expected
risk and is not one. Phase separation (wear = environment/0, repair+tend =
agent/10) plus loose-`gt 0` wear precondition (`ecology_domain.py:98`) vs strict
equality CAS on agent actions (`living_agent_actions.py:470,487`) makes wear
deterministically win and the agent action retry. Repair `<750` and tend
`[750,1000)` are genuinely disjoint against a shared frozen frame
(`living_settlement_domain.py:377,490-494`; `core/constants.py:70-71`). The 7D
and 8B nudges gate on `goal == "REPAIR_SHELTER"` only and cannot reach
TEND_STRUCTURE (`living_settlement_domain.py:177,236`; tested
`test_layer_c_upkeep.py:415`). Residual: with `STRUCTURE_WEAR_INTERVAL = 5`
(`core/constants.py:59`), ~1 in 5 tend/repair attempts on a wearing structure is
discarded — deterministic, but a visible wasted-action pattern.

**F10 — No ownership test exists, anywhere.** Nothing in `backend/tests/`
asserts that a component has exactly one writing module, or exercises a
same-tick two-writer case. The three nearest tests
(`test_layer_c_upkeep.py:159`, `test_stage7c_group_collective.py:257`,
`test_phase5b3_food_interaction.py:541`) all prove the *rejection* path works
**where a CAS already exists** — which is precisely why the unguarded fields
(F1, F2, F3) were never caught.

---

## Bounded-state caps (recorded, non-negotiable 4)

Memories 32/entity, 8/subject (`living_agent_contracts.py:77-78`), compaction
score-then-id (`living_agent_cognition.py:635-650`). Relationships 16
(`living_agent_contracts.py:87`), evicted by `last_changed_tick` then id
(`living_agent_social.py:130-136`). Knowledge: tiles 200, water 40, trees 30,
shelters 10, carcasses 15, animals 15, people 15, dangers 10, detections 48
(`perception.py:31-39`, trimmed `:414-428`). Interaction memory 24/observer,
8/subject (`interaction_memory.py:32-33`). Reciprocity contributions 16
(`reciprocity_trust.py:28-30`).

---

## Disposition table

Added 2026-07-25 after review. Evidence labels per `CLAUDE.md` reporting rules;
disposition vocabulary per `ARCHITECTURE-SPINE.md` §Capability delivery lifecycle
(no other wording permitted).

| # | Evidence | Scenario reachability | Hash consequence of the fix | Disposition | Next action |
|---|---|---|---|---|---|
| F1 `knowledge` | **LIKELY** — code-read; no CAS on `knowledge` anywhere is VERIFIED by grep, the same-tick collision is not | reachable only in `living_settlement` / `emergent_groups` / `collective_groups` | **UNKNOWN** — probe decides | DEFERRED to core-integrity stage | disposition together with CORE-INTEGRITY-003 |
| F2 storage `contents` | **LIKELY** — mechanism VERIFIED by code; firing not measured | `collective_groups` only, and that scenario seeds two storage-adjacent people with surplus (`scenarios/collective_groups.py:31-42`) — reachability is LIKELY-high, not theoretical | **UNKNOWN** — probe decides | DEFERRED to core-integrity stage | run probe |
| F3 person `action` | **LIKELY**, rating contested | `collective_groups` only; requires a deposit-eligible member whose action that tick is resource-free | **UNKNOWN** — probe decides | DEFERRED to core-integrity stage | run discriminating probe (`rest` tick) |
| F4 asymmetric CAS | **LIKELY** | `living_settlement` family | likely moves the hash (adds rejections) | DEFERRED | bundle with F1–F3 |
| F5 trust SSOT | **VERIFIED** — both representations and their divergent consumers read directly from code | `people` family (derived view) vs `living_settlement` family (canonical field) | n/a — design decision, not a CAS | **needs a ruling**, not a fix | Ryan: reconcile or deprecate one |
| F6 priority tie | **VERIFIED** | all group scenarios | changing a priority is an architectural change (`ARCHITECTURE-SPINE.md`) | record as intentional, or re-assign | Ryan |
| F7 dead literal | **VERIFIED** | n/a | none — dead code | remove | trivial tier |
| F8 dead end | **VERIFIED** | `collective_groups` | none | **needs a ruling** — intended observability-only, or incomplete? | Ryan |
| F9 structure sound | **VERIFIED** | all | none | no action — recorded as a counterexample | — |
| F10 no ownership tests | **VERIFIED** | all | tests only — hash-neutral | act now | write them |

**The probes do double duty, and this is the reason to run them first.** Adding a
CAS changes which proposals Core accepts, which changes committed state, which
moves the frozen `living_settlement` hash — *unless the collision never fires in
the frozen scenarios*, in which case the fix is hash-neutral. The probes for F2
and F3 therefore decide both whether the defect is real **and** whether its fix
is a hash-neutral repair or a re-baseline-class change needing authorisation.
That classification is what determines the gate tier, so it comes before any
remediation planning.

**"Just add a CAS" is not a feature-leg change.** F1–F4 all write person or
storage entities and fall under the CORE-INTEGRITY-001 7-point interim
containment discipline: remediation may not happen inside a feature leg. They
belong in the core-integrity stage alongside 001, 002 and 003.

**Rejected fix for F2:** reversing the `living_settlement` / `group_collective`
priorities would make the agent write land last and appear to solve it. It does
not — `ARCHITECTURE-SPINE.md` states that changing a priority *is* an
architectural change, and the reversal would break the documented
collective-after-`group_state` ordering. The CAS on `contents` is the fix.

## CAS failure and atomicity semantics

Recorded because the tables above assume it and it was nowhere written down.

- **Per proposal, all-or-nothing at the gate.** `commit_pipeline.py` commits
  proposals one at a time in `order_key` order and re-evaluates every
  precondition against progressively-mutated state. If any precondition fails,
  that whole proposal is rejected — there is no partial commit of its
  `entity_updates`.
- **Per top-level key on the write.** `core/mutations.py:24` is
  `entities[eid].update(updates)` — a shallow replace of each top-level key. A
  proposal writing `living_agent` replaces the entire blob including
  `relationships`, `memories` and `pressures`, whether or not it intended to.
  This is why F4's asymmetry matters and why nested state cannot be protected by
  guarding a sibling field.
- **Failure is rejection-then-retry, not error.** VERIFIED for one path: ecology
  wear commits first and the agent's repair/tend is rejected on its equality CAS
  and retried the following tick (`ecology_domain.py:64-70`, tested
  `test_layer_c_upkeep.py:159`). With `STRUCTURE_WEAR_INTERVAL = 5`, roughly 1 in
  5 attempts on a wearing structure is discarded.
- **UNKNOWN:** whether a rejected proposal produces a player-visible or
  inspectable receipt, and whether the rejection reason reaches the decision
  trace. Core owns "accepted/rejected records" per `ARCHITECTURE-SPINE.md`, but
  the projection path for rejections was not traced in this pass. Worth
  resolving — the Behaviour Bible's explanation surface depends on it.

## Read-only consumers (blast radius of an ordering change)

Not writers, but they break if a value goes stale or an ordering moves.

| Field | Read-only consumers |
|---|---|
| `reciprocity_trust` view | `people_domain.py:357` (diagnostics), `people_utility.py:253,263` (recipient ranking), `food_interaction_proposals.py:442-443` (auto-accept gate) |
| canonical `relationships[*].trust` | `living_agent_cognition.py:489-492` (pressures), `living_settlement_domain.py:447` (settlement decisions) |
| `collective_action` metadata | `tools/living_agent_harness.py:205-209` only (see F8) |
| `collective_processed_keys` | `group_collective` self-dedupe; `tools/living_agent_harness.py:322` |

The first two rows are F5 stated as a dependency graph: two consumer sets, two
substrates, no reconciliation.

## Gaps in this pass

1. **Event Family Registry not built** — the third registry named in
   `THE-SPINE.md` §7. Needs its own inventory pass.
2. **Interventions rows unverified against `d1c18f52`** — `c2d7b4c6` added an
   intervention CAS after this inventory ran.
3. **No execution evidence.** All collision claims are code-reading (LIKELY on
   reachability). F2 and F3 each have a cheap decisive probe described above;
   neither has been run.
4. **Scenario matrix not tabulated.** `people` and `living_settlement` never
   co-exist (`scenarios/desert_oasis.py:19`, `wilderness_survival.py:11`,
   `living_settlement.py:21`), which bounds blast radius — that mapping belongs
   in the Scenario Capability Registry, not here.
