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

> **EXECUTION EVIDENCE ADDED 2026-07-26 — read this before acting on any
> finding below.** The F2 and F3 probes have now been run and **F2 is
> REFUTED**. See "Probe results" before the Findings section. Two structural
> lessons from the run, both of which cost this pass accuracy:
>
> 1. **A preconditions-only read under-counts defences.** This inventory
>    reasoned entirely over `preconditions` lists, because `core/mutations.py:24`
>    is a blind whole-value replace and preconditions are Core's only *generic*
>    guard. But a proposal family may also ship a **domain validator** that
>    re-derives expected state at commit-revalidation — functionally a CAS,
>    structurally invisible to a precondition grep. That is exactly what
>    defends F2. Any future ownership audit must read the family's
>    `validate_*_proposal` alongside its `preconditions`.
> 2. **Writer lists here are not exhaustive.** `test_component_ownership_
>    invariants.py` found a writer of `energy` that all three passes missed
>    (`living_agent_social.py:436-437`, and it is *cross-entity*). Treat every
>    "Current Writers" cell as a lower bound until a test pins it.

**Scope (per §11):** canonical person-state; cognition/social state;
group/culture registries; structures; shared storage; all domains carrying an
`engine_priority`. **Out of scope this pass:** the Event Family Registry (third
registry, not built), animal/weather internals, migration policies.

---

## Table 1 — Component Ownership

| Component / Field | Entity Type | Canonical Owner | Current Writers (file:line) | Legal Cross-Owner Writes | Collision Risk | Tests |
|---|---|---|---|---|---|---|
| `action` | person (also animal) | `people_domain` *(desert_oasis, wilderness_survival)* / `living_settlement_domain` *(living_settlement, emergent_groups, collective_groups)* — mutually exclusive per scenario | `people_domain.py:385`; `living_settlement_domain.py:777`; `living_agent_actions.py:521`; `living_agent_social.py:315`; `group_collective_contracts.py:283`; `lifecycle_domain.py:168`; `animal_domain.py:105,147`; Core stamps sub-keys `commit_pipeline.py:292-297` | `lifecycle_domain.py:168` (death) — **contractual**: environment phase, prio 1, commits first; actor proposals then fail their `alive eq True` precondition (`people_domain.py:402`, `living_agent_actions.py:295`) | **HIGH — CONFIRMED 2026-07-26.** Rating conflict resolved in favour of HIGH: the discriminating test was written and the clobber reproduces | `test_component_ownership_invariants.py::test_same_tick_person_action_collision_overwrites_the_committed_action` (the discriminating `rest` case); ownership pinned by `::test_no_unregistered_writer_of_a_canonical_component` |
| `living_agent` (whole blob) | person | `living_settlement_domain` / `people_domain` per scenario | `people_domain.py:389`; `living_settlement_domain.py:776`; `living_agent_social.py:318,327,348-349,362-363,382-383,474`; sub-keys stamped `commit_pipeline.py:226-264` | `living_agent_social.py:327,474` writes the **target's** blob — contractual, gated by `validate_social_action_proposal` (`living_agent_social.py:570-574`) and CAS at `:324,:331`, re-pinned by `living_settlement_domain.py:515-518` | **MEDIUM** — see F4 (asymmetric CAS) | Behaviour only: `test_stage6d_social_relationships.py:70,136,165`; `test_stage6a_living_cognition.py:246,277-279` |
| `living_agent.pressures` | person | `living_agent_cognition` (derived into the blob) | produced only at `living_agent_cognition.py:530`; `living_agent_contracts.py:179,283` | — | inherits `living_agent` | `test_stage6a_living_cognition.py:278` (key set) |
| `living_agent.relationships` | person | `living_agent_social` (`apply_relationship_consequence:73`, write `:137`) | self: `people_domain.py:389`, `living_settlement_domain.py:776`; cross-entity: `living_agent_social.py:318,327,348-349,362-363,382-383,474`, emitted `:537`, invoked `living_settlement_domain.py:660-670` | cross-entity write of B's blob by A — contractual, CAS-protected | **HIGH** (rejection, not loss — CAS revalidated `commit_pipeline.py:476`). `people_domain.py:401-405` adds **no** `living_agent` precondition | `test_stage6d_social_relationships.py:57,76,79-111`; caps `test_stage6_contracts.py:51` |
| `living_agent.memories` | person | `living_agent_cognition` (`merge_meaningful_memories:702`, write `:800`) | `people_domain.py:132→389`; `living_settlement_domain.py:565,756→776` | — (observer-scoped: built from own observations/action_result) | **MEDIUM** — rides in the `living_agent` blob; a whole-blob overwrite takes memories with it | caps `test_stage6a_living_cognition.py:189,279`; `test_stage6_contracts.py:50` |
| `knowledge` (`knowledge-v2`) | person | `perception` (`merge_knowledge:289`, returns `:433`) | `people_domain.py:395`; `living_settlement_domain.py:655,715`; **cross-entity** `living_agent_social.py:457` | none declared | **HIGH — see F1. No precondition on `knowledge` exists anywhere in the repo** | observer-scoping `test_phase5a5_cognitive.py:91`; caps `test_phase5b2_social_observations.py:169`; replay `:215-216` |
| `knowledge.interaction_memory` (`interaction-memory-v1`) | person | `interaction_memory` (`merge_interaction_memory:441`, write `:481`) | sole producer `people_domain.py:100→395` | — (strictly observer-scoped, `compute_eligible_witness_ids:234`) | **MEDIUM** — nested inside `knowledge`, so inherits F1 | `test_phase5b4_interaction_memory.py:282,293,424,430-467,470-499` |
| `reciprocity_trust` view | *(no entity field)* | `reciprocity_trust` | **none — zero writers.** Read-only consumers `people_domain.py:357`, `people_utility.py:253,263`, `food_interaction_proposals.py:442-443` | — | **LOW** | `test_phase5b5_reciprocity_trust.py:162-163,375-376,389-393,401-410,502-514` |
| `hunger` | person (also animal) | per-scenario action owner | `people_domain.py:373`; `living_settlement_domain.py:708,714`; `living_agent_actions.py:422`; `core/interventions.py:25`; `animal_domain.py:104` | `interventions.py:25` player boost — contractual, commits in its own frame (`api/routes.py:467-470`) | **LOW** *(re-verify: `c2d7b4c6` added intervention CAS)* | `test_simulation_sandbox.py:158-169` (behaviour only) |
| `thirst` | person | per-scenario action owner | `people_domain.py:374`; `living_settlement_domain.py:709-711,714`; `living_agent_actions.py:431`; `interventions.py:25` | as above | **LOW** *(same re-verify)* | `test_phase5a3_navigation.py:369` |
| `energy` *(canonical; `fatigue` is derived)* | person | per-scenario action owner | `people_domain.py:375`; `living_settlement_domain.py:712,715`; `living_agent_actions.py:435,503,505`; **`living_agent_social.py:436-437` (cross-entity — actor AND target; missed by all three passes, found 2026-07-26 by test)**; `interventions.py:25` | `living_agent_social.py:436` writes the **target's** energy — same domain family, so not an ownership violation, but undeclared | **MEDIUM** *(was LOW; that rating assumed one-per-scenario **self**-writes, which the cross-entity social writer breaks. Held at MEDIUM pending **OQ-1** — 64 unattributed same-tick `energy` collisions in `collective_groups`, 0 in `living_settlement`. Drop to LOW if OQ-1 resolves to something benign)* | `test_component_ownership_invariants.py::test_social_actions_write_energy_cross_entity` |
| `fatigue` | — | **no canonical field exists** | none — derived at `living_agent_cognition.py:470` as `1000 - energy` | — | inherits `living_agent` | `test_stage6a_living_cognition.py:278` |
| `carried_resources` / `inventory` / `food_inventory` | person | per-scenario action owner | `people_domain.py:378,425`; `living_agent_actions.py:138` via `:342,395,399,421,447,468`; `living_agent_social.py:240` via `:395-396,422-423`; `group_collective_contracts.py:293`; genesis `world/generator.py:97` | `people_domain.py:425` (food receiver), `living_agent_social.py:396,423` (target), `group_collective_contracts.py:293` — all contractual and CAS-guarded | **LOW/MEDIUM** — every producer CASes (`living_agent_actions.py:345,406-408,423`; `living_agent_social.py:404-405,432-433`; `group_collective_contracts.py:351-356`) | `test_stage6c_physical_actions.py:69,71,87,137,163,203`; `test_stage7c_group_collective.py:225,247,345` |
| Structure `condition` (wear) | shelter / structure | **shared — no single owner** | ecology wear `ecology_domain.py:100`; repair/damage `living_agent_actions.py:470-471`; tend `living_agent_actions.py:485-489`; created at 1000 `:452` | Yes by design — environment-phase wear vs agent-phase repair/tend | **MEDIUM** — resolved by phase order + strict CAS; see F7 | `test_layer_c_upkeep.py:113,136,152,159,197`; `test_stage6c_physical_actions.py:144-161` |
| Structure `max_condition` | shelter / structure | creation only | `living_agent_actions.py:452` | none | none | — |
| Shared storage `contents` | storage | **contested** | `living_agent_actions.py:399-401` (prio 10, CASes `contents` at `:406-407`); `group_collective_contracts.py:296` (prio 90, no storage *precondition* — but see the validator) | intended: both write camp storage | **LOW** *(was HIGH; **F2 REFUTED** — `validate_group_collective_proposal:515-521` re-derives expected contents from live state and rejects on mismatch)* | `test_stage7c_group_collective.py:186,257,272`; **now mixed in one tick**: `test_component_ownership_invariants.py::test_same_tick_storage_contents_collision_rejects_the_collective_deposit` |
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

## Probe results (2026-07-26)

Run at `09c92c93`. Probe: `backend/tools/_probe_ownership_f2_f3.py`. Mechanism
proved Tier A (real builders, real commit frames) in
`backend/tests/test_component_ownership_invariants.py`; organic reachability
measured on the recorded harness invocation, seed `living-agents-stage6`,
scenario `collective_groups`, 1,000 ticks.

**1. Mechanism — the two findings split.**

- **F2 REFUTED (VERIFIED).** No lost update occurs. `validate_group_collective_
  proposal` (`group_collective_contracts.py:515-521`) re-derives expected
  storage contents from **live** entities at commit-revalidation and returns
  `REASON_MUTATION` on any mismatch. The agent's `store` commits; the
  *collective* proposal is rejected (`group_collective.invalid_mutation`) and
  retries. Functionally a CAS on `contents`, implemented as a domain
  re-derivation — which is why a preconditions-only read missed it.
  A **second, independent** defence sits in front: if the storer is itself a
  participant, eligibility re-derivation (`:494-503`) rejects first
  (`participant_ineligible`). F2's scenario needs a *non-participant* storer to
  reach the contents question at all.
- **F3 CONFIRMED (VERIFIED), HIGH.** The discriminating case named below — a
  deposit-eligible member whose action that tick is `rest` — reproduces
  exactly: the committed `action` is overwritten while the `carried_resources`
  CAS passes throughout. The competing Low-Medium rating is wrong.

**2. Organic reachability — neither is reachable, so both fixes are
hash-neutral.** In 1,000 ticks the collective deposit is **never proposed**:

```
accepted_count: 0    rejected_count: 0
first_accepted_tick: null    first_rejected_tick: null    rejected_by_reason: {}
final_storage_contents: {"storage-camp": {"food": 0, "wood": 12}, ...}
```

Not proposed-and-rejected — zero proposals. Agents demonstrably *do* store into
`storage-camp` (12 wood accumulated); only the collective path never triggers.
**Why is UNKNOWN** and was not probed. Consequence: **gate tier is hash-neutral,
not re-baseline-class.** Frozen `living_settlement` 320 hash
`897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab`
(matches baseline) and `collective_groups` 1,000
`43893bdde4ce4b93c6076650326861b66ff8bd6343a7568653d122917db1638a`
(byte-identical pre- and post-F7).

**3. Multi-writer census, same tick / same entity / same top-level key.**
`last_event_id` 6012 (Core stamps this on every accepted event —
`commit_pipeline.py:485`; benign), `condition` 221, `living_agent` 132,
`energy` 64, `quantity` 12. Every non-`last_event_id` collision is
**intra-family** (`living_settlement`). No cross-owner collision fired in
1,000 ticks. **Correction (2026-07-26):** an earlier revision of this section
attributed the 64 `energy` collisions to the F11 cross-entity writer. That was
an inference, never measured, and the follow-up census actively weakens it —
`living_settlement` 320 accepts **37 `cooperate` actions and produces 0 energy
collisions**. A `cooperate` writes actor and target energy inside **one**
proposal, so it yields one event touching two entities, not two events touching
one — which is not the collision shape at all. The 64 collisions are real and
`collective_groups`-only; **their cause is UNKNOWN and unattributed.**

*Note on engine identity: in the organic run the settlement domain re-stamps
`proposer_engine_id` to `living_settlement`, while the builders set
`living_actions` / `living_social`. Ownership is therefore per **domain**, not
per builder — which is how the invariant tests model it.*

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

**F2 — Shared storage `contents` lost update. ~~HIGH~~ → REFUTED 2026-07-26.**
*Original claim, preserved:* `group_collective_contracts.py:296` writes the
whole `contents` dict, built from the pinned pre-tick frame (`:266`), with **no
precondition on the storage entity at all** (`:326-361` covers only registry
revisions and each participant's `alive`/`carried_resources`). It commits at
prio 90, after `STORE_SURPLUS` (`living_settlement_domain.py:390-397`) at
prio 10, which *does* CAS `contents` (`living_agent_actions.py:406-407`). The
conclusion drawn — "the collective write silently reverts the agent's deposit"
— **is wrong.**

**Refutation (VERIFIED, Tier A).** The precondition gap is real; the lost
update is not. `validate_group_collective_proposal:515-521` re-derives
`expected` contents from the **live** storage entity at commit-revalidation and
returns `REASON_MUTATION` unless the proposal's precomputed dict matches — so
*any* concurrent change to that storage rejects the collective proposal
instead. The agent's deposit survives. A second defence precedes it: a
participant-storer trips eligibility re-derivation (`:494-503`) first.

**What went wrong in the analysis, not just the answer:** the pass reasoned
only over `preconditions`, on the correct premise that `core/mutations.py:24`
is a blind replace and preconditions are Core's only *generic* guard. It did
not read this family's domain validator, where the compensating re-derivation
lives. F1 and F4 were rated by the same method. **Both have since been
re-checked against their validators (2026-07-26) and both survive:**

- **F1 `knowledge` — survives.** `validate_social_action_proposal`
  (`living_agent_social.py:544-601`) touches knowledge exactly once, in the
  `lie` branch: `target_knowledge = (updates.get(target_id) or {}).get("knowledge")`
  followed by a `deceptive_source_claim` leak check. It reads from **`updates`**
  — the proposal's own declared mutation — never from the live `entities`
  argument. No re-derivation, no comparison against current state. With the
  VERIFIED absence of any `knowledge` precondition, F1's defence class is
  **none**.
- **F4 `living_agent` — survives.** The only guard is `if "living_agent" in
  update and entity_id not in allowed_people: return
  "social_action.uncausal_relationship_update"`. That constrains **which
  entity** may be written, never **which value**.
  `validate_living_action_proposal` (`living_agent_actions.py:586-660`) does not
  compare `living_agent` against live state either. Defence class:
  **scope-only guard**.

**The distinction that decided it** — and the reason F2 died while F1 and F4 did
not — is that the collective validator reads `storage.get("contents")` and
`_person_resources(person)` from the live `entities` argument, whereas the social
and living-action validators check `actor_before` / `source_before` /
`destination_before` values carried in the proposal's own `meta`. The second
shape looks identical in review and defends nothing against a concurrent writer:
a stale proposal is internally consistent and passes.

That is why "has a CAS / has no CAS" is too coarse to audit against. The
defence classes actually observed so far are four, and only the first is a
real guard against a concurrent writer:

| Class | Guards against a concurrent writer? | Seen at |
|---|---|---|
| Live re-derivation | **yes** — reads current `entities` | F2 (`group_collective_contracts.py:515-521`) |
| Self-consistency vs the proposal's own `_before` meta | **no** — a stale proposal passes | living-action transfers (`living_agent_actions.py:635-646`) |
| Scope-only guard | **no** — constrains *which entity*, not *which value* | F4 (`living_agent_social.py:573-574`) |
| None | **no** | F1 |

Recording the *class*, not merely the presence, is what would have caught F2
in the first pass — and it is what makes F1 and F4 survive this re-check
rather than dissolve the way F2 did.

*No remediation required. The rejected "reverse the priorities" fix and the
proposed `contents` CAS are both moot.*

**F3 — `group_collective` clobbers person `action`. HIGH — CONFIRMED 2026-07-26.**
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
*Rating conflict — RESOLVED in favour of HIGH.* One pass rated this HIGH with
the mechanism above; another rated it Low-Medium without addressing the
resource-free-action case. The **discriminating test** — a tick where a
deposit-eligible member's selected action is `rest` — is now written
(`test_component_ownership_invariants.py::test_same_tick_person_action_
collision_overwrites_the_committed_action`) and the clobber reproduces: `rest`
touches no carried resource, so the `carried_resources` CAS passes and the
freshly-committed action is overwritten anyway.

**Why F3 survives the validator that refuted F2.** The same
`validate_group_collective_proposal` checks the deposit exhaustively —
`source_field`, both legacy mirrors, live resources, capacity, contents
(`:489-521`) — and never mentions `action`. The re-derivation defence is
**field-scoped**, so it covers `contents` and misses `action` entirely. That is
the whole difference between the two findings.

*Remediation still required, still deferred to the core-integrity stage. Now
known to be **hash-neutral**: the collective deposit is never proposed in the
frozen scenario (see Probe results), so adding the CAS cannot move a hash.*

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

**F8 — `group_collective` is a behavioural dead end. SHARPENED 2026-07-26 —
it is worse than "dead end".** The original claim: it commits real mutations,
but no domain reads its output to make a decision — `collective_action` is
event metadata only (`commit_pipeline.py:550`), and `collective_processed_keys`
is read only by itself for dedupe and by the harness
(`tools/living_agent_harness.py:205-209,322`).

**Measured:** in 1,000 organic ticks of `collective_groups` at the recorded
seed the domain proposes **nothing at all** — `accepted_count: 0`,
`rejected_count: 0`, `first_accepted_tick: null`. So it is not merely that
nothing reads its output; there is no output. Agents *do* use that storage
(`storage-camp` ends `{"food": 0, "wood": 12}`), so the storage and the
proximity are live — only the collective path never triggers. **Why is UNKNOWN
and unprobed** (candidate causes: group recognition never completes, the
`shared_storage` fact never lands, or no member carries a resource at the
moment eligibility is evaluated). This upgrades F8 from a design question to a
"does 7C function organically at all" question.

### F8 RULING BRIEF

**The decision:** is 7C intentionally inert, or broken?

**What is not in question.** The mechanism works. `test_stage7c_group_collective.py`
passes, and the ownership-invariant fixture builds a real deposit proposal from
the real builder. The code is fine; the *organic preconditions* are never met.

**DIAGNOSED 2026-07-26 (ruling B). Blocked at GATE 3 — and it was neither
candidate cause.** Probe: `backend/tools/_probe_f8_collective_preconditions.py`,
which walks the eligibility chain in the domain's own order and reports the
first gate that fails. Identical result at **120 and 1,000 ticks**
(`collective_groups`, seed `living-agents-stage6`, hash
`43893bdde4ce4b93c6076650326861b66ff8bd6343a7568653d122917db1638a`):

| Gate | Result |
|---|---|
| 1 · domain activates (both registries exist) | **PASS** — `association-registry-000` tick 1, `group-shared-state-000` tick 23 |
| 2 · a group is recognised | **PASS** — 12 candidates, **all 12 recognised** |
| 3 · a recognised group holds a `shared_storage` fact | **FAIL** — `all_fact_categories: {"shared_shelter": 24}`, **zero `shared_storage`, ever** |
| 4 · ≥2 eligible participants | vacuous |
| 5 · `derive_coordinated_deposits` | 0 |

*Both original hypotheses were wrong.* The registries **do** materialise and the
domain **does** activate (refuting cause 1), and groups form and are recognised
readily (so cause 2's premise never even arises). The failure is a third thing:
**the specific fact category the deposit requires is never produced.**

### Gate-3 cause — SETTLED 2026-07-26, and simpler than the first attempt

Probe: `backend/tools/_probe_f8_storage_pairing.py`, which replays the
accepted-event stream and evaluates the real predicate from
`association_contracts.py:303-316` every tick. `collective_groups`, 1,000
ticks, hash `43893bdde4ce4b93c6076650326861b66ff8bd6343a7568653d122917db1638a`:

```
VERDICT                 : C_ONLY_ONE_DISTINCT_STORER
storage_action_count    : 1        <- in the ENTIRE 1,000-tick run
distinct_storer_count   : 1
closest_cross_agent_gap : null     <- no two agents ever touched one storage
```

The single action is a **`retrieve`** of 1 food by `person-006` at tick 7.
**Zero `store` actions occur, ever.**

| Candidate | Verdict |
|---|---|
| (a) rule counts food stores only, so wood never qualified | **REFUTED** — code-read: `association_contracts.py:303-316` tests `action["type"] in {"store","retrieve","access"}` and never inspects resource kind. Wood would qualify identically |
| (b) resource-agnostic, but no two stores ever fell inside the 4-tick window | **REFUTED** — you cannot pair two storage actions when the run contains one |
| (c) only one distinct agent ever performed a storage action | **CONFIRMED, VERIFIED** |

**The `{food: 0, wood: 12}` final state was genesis seeding, not deposits.**
Genesis `storage-camp` contents are `{"food": 1, "wood": 12}`. Wood went
**12 → 12, untouched**; food went 1 → 0 via that one `retrieve`. Nothing was
ever deposited. Reading the wood as evidence that "stores demonstrably
happened" is the trap here, and it caught both of us.

**Correcting the previous attribution, which was mine and was wrong.** The
earlier text blamed `STORE_SURPLUS`'s `food >= 3` gate
(`living_settlement_domain.py:393`) for stores failing to *pair up*. That
framing is void: stores do not fail to pair, they do not happen. The 4-tick
pairing window is **not** the binding constraint and never gets the chance to
be. The `food >= 3` gate survives only as one unverified candidate answer to
the *new* and different question below.

**`THE-SPINE.md`'s "surplus falsified for 7C" claim (`683ef0fe`) is
reinstated, not walked back.** The deposit is not food-scoped — true, and
irrelevant, because the chain dies four steps earlier. Surplus is not
demonstrated as the blocker either; what is demonstrated is that the
storage-interaction layer is organically inert in this scenario.

**New open question, deliberately not investigated:** *why* do agents never
perform storage actions? Candidates include the `food >= 3` gate, `STORE_SURPLUS`
never winning action scoring, or no nudge ever selecting it. Unverified.

| # | Option | Cost | Effect |
|---|---|---|---|
| **A** | Rule 7C observability-only; close F8 as intended behaviour | free | Records a claim we have not tested. Sits badly with **Rail C** — "a mechanism is not alive because a test can fire it" |
| **B** | **Run the one distinguishing diagnostic, then rule** | one read-only probe | Ruling becomes evidence-based; see leverage below |
| **C** | Retire 7C | destructive | Premature — mechanism is built, tested, and already DEFERRED behind F-A |

**Ruling B taken 2026-07-26; diagnostic run (above). It paid off on all three
predicted fronts:**

- **F8 itself** — cause located: gate 3, no `shared_storage` fact.
- **`THE-SPINE.md` §8's 7C row** — its UNKNOWN blocker is replaced with the
  measured one.
- **The last failing test in the suite** — and the mechanism is now concrete
  rather than a hypothesis. `CORE-INTEGRITY-002`'s `test_concurrent_stage7b_…`
  fails 4/4 at `assert registry_before.get("groups")`, a setup assertion taken
  **after 12 setup ticks**. The probe measures `group-shared-state-000` first
  appearing at **tick 23**. The registry does not exist yet when the test
  asserts on it. **LIKELY** the whole explanation — the test's setup horizon is
  simply too short — pending confirmation that the API path matches the
  harness path. That would make it a test-isolation defect, not an engine race,
  which is one of the two outcomes CORE-INTEGRITY-002 was opened to decide.

**What remains for Ryan: the ruling itself.** The question is no longer "why" —
it is what 7C should *be*, now that the cause is known and cheap to state:

| | Ruling | Consequence |
|---|---|---|
| **A** | 7C is observability-only; accept it never fires organically | Honest now that the cause is documented, but concedes a built, tested capability is dead |
| **B** | 7C should fire; the 4-tick paired-storage window is too tight and/or `STORE_SURPLUS`'s `food >= 3` gate is too strict | A behaviour change, **re-baseline-class**, and it belongs behind Layer F-A or the social-density leg, not a spot fix |
| **C** | Retire 7C | Still premature |

Recommendation deferred: this is a capability-scope question, not a technical
one, and it interacts with the F-A deferral already recorded in `THE-SPINE.md`.

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

**F10 — No ownership test exists, anywhere. CLOSED 2026-07-26.** Nothing in
`backend/tests/` asserted that a component has exactly one writing module, or
exercised a same-tick two-writer case. The three nearest tests
(`test_layer_c_upkeep.py:159`, `test_stage7c_group_collective.py:257`,
`test_phase5b3_food_interaction.py:541`) all prove the *rejection* path works
**where a CAS already exists** — which is precisely why the unguarded fields
(F1, F2, F3) were never caught.

**Closed by `backend/tests/test_component_ownership_invariants.py`** (9 tests,
Tier A, no harness run, hash-neutral). It asserts: no unregistered writer of a
canonical component; single-owner fields keep one writing domain; every
multi-writer field carries a CAS **except an explicitly pinned gap set**; the
existing guards are not silently removed; F4's asymmetry holds; and both
same-tick two-writer cases (F2, F3) behave as measured.

Two design points worth carrying to the next registry:
- **Characterization, not aspiration.** F1–F4 are deliberately unfixed, so a
  test demanding "every multi-writer field has a CAS" would fail on arrival.
  Instead the gap set is pinned *exactly*: a new gap fails, **and** silently
  closing a known gap fails — which forces the fix and the registry update into
  one commit.
- **The precondition rule is directional.** Only a writer that can commit
  *after* another writer of the same field needs the CAS; guarding the earlier
  writer protects nothing. "After" is `engine_priority` (`commit_pipeline.py:108`).

**F11 — `energy` has an undeclared cross-entity writer. LOW (ownership).
RESCOPED 2026-07-26.** Found by the F10 tests, not by any inventory pass:
`living_agent_social.py:436-437` writes `energy` on **both the actor and the
target**. Table 1's `energy` row listed `people_domain`,
`living_settlement_domain`, `living_agent_actions` and `interventions` — not
`living_agent_social`, and did not record that the write is cross-entity. Same
domain family, so it is not an ownership violation; it is an incomplete row.
Table 1 corrected. **That writer fact is all that remains of F11 here.**

**Everything else that was filed under F11 has moved to
`memory/FINDING-EFFORT-TRANSFER-ENERGY.md`,** because it was misclassified
twice and the second misclassification was mine:

- **Not a collision.** One `cooperate` proposal writing both energies is *one
  event touching two entities*, not two events touching one. Measured:
  `living_settlement` 320 → 37 cooperates, **0** same-tick energy collisions.
  No CAS applies; it does not belong in the CORE-INTEGRITY family.
- **Not a conservation defect.** Energy is non-conserved *by design* — `rest`
  mints 80 from nothing (`living_agent_actions.py:435`), and the engine's
  conservation validators (`living_action.nonconserving_transfer`,
  `social_action.nonconserving_exchange`) are deliberately scoped to
  **resource** transfers, not energy.
- **The "+740 units of invented energy" figure previously stated here was
  wrong in magnitude *and sign*.** `min(1000, e+40)` and `max(0, e-20)` clamp
  at both ends, so `37 × 20` was an unclamped ceiling, not a measurement.
  Summing the real per-event deltas gives **−420**: 29 of 37 target gains
  evaporate at the ceiling while every actor cost lands in full. In that
  baseline `cooperate` is net energy-**destroying**.

The rescoped finding needs a **ruling**, not a fix, and its one concrete gap is
that `+40 / −20 / +50 / +80` are inline literals with no evidence comment
(`CLAUDE.md`: constants carry the evidence that set them). See that doc.

*Unrelated to all of the above:* the 64 same-tick `energy` collisions measured
in `collective_groups` are a **different phenomenon** and remain **UNKNOWN** —
see "Open questions" below.

---

## Open questions

**OQ-1 — the 64 `collective_groups` same-tick `energy` collisions are
unexplained. UNKNOWN. Opened 2026-07-26. Do not close by assumption.**

The multi-writer census measured **64** same-tick / same-person / same-field
`energy` collisions in 1,000 ticks of `collective_groups` (engine pair
`living_settlement`, i.e. intra-family), reproduced identically across two
independent probe runs. `living_settlement` 320 measured **0**.

It was attributed to F11's cross-entity `cooperate` writer. **That attribution
is withdrawn.** The disproof is direct: `living_settlement` accepts 37
cooperates and produces zero collisions, and a `cooperate` writes both energies
inside *one* proposal — one event touching two entities, which is not the
collision shape at all. Cooperate is not sufficient to produce one.

Scenario counts, for whoever picks this up:

| Scenario | cooperates | energy-writing events | collisions |
|---|---|---|---|
| `living_settlement` 320 | 37 | 1,529 | **0** |
| `collective_groups` 1,000 | 232 | 7,244 | **64** |

If cooperate drove collisions at the `collective_groups` rate (0.276 each),
`living_settlement`'s 37 would predict ~10. It produces none — so something
scenario-specific to `collective_groups` is required, and it is not known what.

Not investigated: deliberately out of scope for the audit that found it. Cheap
next step is to dump the two colliding events per incident with their
`proposer_engine_id`, `order_index` and action types — the existing probe
(`backend/tools/_probe_ownership_f2_f3.py`) already collects the grouping and
needs only the per-incident detail printed.

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
| F1 `knowledge` | **LIKELY** — code-read; no CAS on `knowledge` anywhere VERIFIED by grep; the same-tick collision is not probed. **Validator re-check DONE 2026-07-26 — no compensating re-derivation exists** (defence class: none) | reachable only in `living_settlement` / `emergent_groups` / `collective_groups` | **UNKNOWN** — not probed | DEFERRED to core-integrity stage | probe reachability, then disposition with CORE-INTEGRITY-003 |
| F2 storage `contents` | **REFUTED — VERIFIED.** Defended by `validate_group_collective_proposal:515-521` (live re-derivation), plus eligibility re-derivation for the participant-storer case | moot | none — no fix required | **REJECTED** (finding withdrawn) | none; retain the pinning test |
| F3 person `action` | **CONFIRMED — VERIFIED.** Discriminating `rest` test written and reproduces; rating conflict resolved to HIGH | `collective_groups` only — and **never proposed** there in 1,000 organic ticks | **none — hash-neutral** (VERIFIED: zero collective proposals in the frozen scenario) | DEFERRED to core-integrity stage | add the `action` CAS in that stage; gate tier is trivial, not re-baseline |
| F4 asymmetric CAS | **LIKELY** — code-read. **Validator re-check DONE 2026-07-26 — guarded by scope only, never by value** (defence class: scope-only guard) | `living_settlement` family | UNKNOWN — the "likely moves the hash" note was an inference, not a measurement | DEFERRED | probe reachability, then bundle with F1 |
| F5 trust SSOT | **VERIFIED** — both representations and their divergent consumers read directly from code | `people` family (derived view) vs `living_settlement` family (canonical field) | n/a — design decision, not a CAS | **needs a ruling**, not a fix | Ryan: reconcile or deprecate one |
| F6 priority tie | **VERIFIED** | all group scenarios | changing a priority is an architectural change (`ARCHITECTURE-SPINE.md`) | record as intentional, or re-assign | Ryan |
| F7 dead literal | **VERIFIED** | n/a | **none — VERIFIED, not inferred**: `engine_priority` is absent from `core_fields` (`commit_pipeline.py:75-100`) and `canonical_json` sorts keys; frozen 320 hash and `collective_groups` 1,000 hash both byte-identical pre/post | **DONE 2026-07-26** | none |
| F8 dead end | **VERIFIED, and worse than recorded** — zero proposals in 1,000 organic ticks | `collective_groups` | none | **needs a ruling** — is 7C organically inert by design, or broken? | Ryan; probe *why* nothing is proposed if it matters |
| F9 structure sound | **VERIFIED** | all | none | no action — recorded as a counterexample | — |
| F10 no ownership tests | **VERIFIED** | all | tests only — hash-neutral | **DONE 2026-07-26** | none; extend coverage as new domains land |
| F11 `energy` cross-entity writer | **VERIFIED** — `living_agent_social.py:436-437` writes actor AND target; Table 1 row was incomplete | `living_settlement` family | n/a — registry correction, no code change | **LOW.** Row corrected; ownership half closed | none |
| *(rescoped out of F11)* effort-transfer `+40/−20` | **VERIFIED** — measured net **−420** on frozen `living_settlement` 320, not the +740 previously stated (29/37 target gains clamp at the ceiling) | `cooperate` + `help`, both frozen baselines | re-baseline-class **only if** the arithmetic changes | **MOVED** → `memory/FINDING-EFFORT-TRANSFER-ENERGY.md`; needs a ruling, not a fix | Ryan: rule on the gradient; name the constants either way |
| OQ-1 64 `energy` collisions | **UNKNOWN** — measured twice, cause unattributed; F11 attribution withdrawn | `collective_groups` only (0 in `living_settlement`) | unknown | **OPEN QUESTION**, not a finding | not investigated this session |

**The probes did double duty, and running them first was correct — it killed a
HIGH finding and downgraded a gate.** Adding a CAS changes which proposals Core
accepts, which changes committed state, which moves the frozen
`living_settlement` hash — *unless the collision never fires in the frozen
scenarios*, in which case the fix is hash-neutral. **Result (2026-07-26):** F2
is refuted outright, and F3, while real, is unreachable in the frozen scenario
because `group_collective` proposes nothing there. **The F3 gate tier is
hash-neutral/trivial, not re-baseline-class.** No re-baseline authorisation is
needed for it.

**"Just add a CAS" is not a feature-leg change.** F1, F3 and F4 write person or
storage entities and fall under the CORE-INTEGRITY-001 7-point interim
containment discipline: remediation may not happen inside a feature leg. They
belong in the core-integrity stage alongside 001, 002 and 003. *(F2 is
withdrawn — no remediation to schedule.)* What the probes changed is the **gate
tier**, not the containment rule: F3's fix is now known hash-neutral, so it
needs the stage but not a re-baseline authorisation.

~~**Rejected fix for F2**~~ — **moot, retained for the reasoning.** Reversing
the `living_settlement` / `group_collective` priorities was rejected because
`ARCHITECTURE-SPINE.md` makes a priority change an architectural change, and
the reversal would break the documented collective-after-`group_state`
ordering. That reasoning stands; the finding it addressed does not. The
proposed `contents` CAS is also unnecessary — the validator already
re-derives.

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
3. ~~**No execution evidence.**~~ **CLOSED for F2/F3 (2026-07-26)** — both
   probed, mechanism proved Tier A and reachability measured over 1,000 organic
   ticks; see "Probe results". **Still open for F1, F4, F5:** those remain
   code-reading only, and F1/F4 were rated by the same preconditions-only
   method that produced the refuted F2, so neither should be remediated before
   its family's `validate_*_proposal` is read.
4. **Scenario matrix not tabulated.** `people` and `living_settlement` never
   co-exist (`scenarios/desert_oasis.py:19`, `wilderness_survival.py:11`,
   `living_settlement.py:21`), which bounds blast radius — that mapping belongs
   in the Scenario Capability Registry, not here.
