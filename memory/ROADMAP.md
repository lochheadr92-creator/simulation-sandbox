# Phase 5 Roadmap - Minimal Foundations

Phase 5 keeps the existing doctrine: accepted events are simulation truth; Core owns time, ordering, validation, mutation, replay, hashing, lineage, RNG policy, and storage authority; domains only propose. Each phase is the smallest deterministic, proposal-only foundation that makes the mechanic real and inspectable.

The detailed fork decision and implementation boundary are recorded in [ADR-001: Fork Semantics Contract](ADR-001-fork-semantics.md).

## Priority and gates

1. 5A1 - Fork Semantics Contract
2. 5A2 - Fork Implementation
3. 5A3 - Deterministic Navigation (behaviour; implemented)
4. 5A4a - Transactional Tick Persistence (implemented)
5. **5A5 - Cognitive Grounding** (Perception / Knowledge / Planning) — implemented
6. **5A6 - Cognitive Visualisation and Live World Readability** — implemented
7. 5B - Economy
8. 5C1 - Canonical World-State Entity
9. 5C2 - Weather Transitions and Effects
10. 5D - Combat
11. 5E - Reproduction and Genetics

No phase may be marked complete from workflow labels such as `testing_agent_v4`. Completion requires reproducible repository commands and recorded results.

## 5A5 - Cognitive Grounding Vertical Slice

**Status:** in progress / implemented as a vertical slice.

**Goal:** close remaining omniscient decision paths so survival targets come only from bounded perception and sparse personal knowledge.

- Perception: integer Manhattan vision; detections for people, animals, food, water, shelter, danger; material-change only knowledge writes.
- Knowledge: observer-owned facts (`knowledge-v2`) with last-known locations; no full world copy; caps per category.
- Planning: Needs drive urgency; eligible targets only from knowledge / this-tick detections; exploration is 4-neighbour unknown tiles only.
- Animals are not globally scanned for hunting; last-known animal positions may go stale without becoming live truth.
- Economy, weather, combat, and reproduction remain later stages (unchanged goals below).

## 5A6 — Cognitive Visualisation and Live World Readability

**Status:** implemented as a frontend projection stage.

**Goal:** make existing canonical action state and selected-person cognition observable without introducing any new simulation authority.

- The selected-person canvas overlay uses a bounded, versioned, observer-specific projection for current perception, retained knowledge, stale last-known entity markers, latest discoveries, and stored route state.
- Route, target, arrival-mode, planning, action, injury, death, urgent-need, and accepted-change indicators are presentation only. They never create state, recalculate routes, or alter decision results.
- The normal observer view remains complete when no person is selected; personal fog is never applied automatically.
- 5B Economy remains the next simulation-mechanic stage.

## 5A1 - Fork Semantics Contract

**Status:** contract complete and implemented by 5A2.

**Goal:** define an honest, deterministic branch boundary before adding a fork endpoint.

### Decisions

- A fork is a **state-equivalent exact-continuation branch from a canonical accepted-event boundary**. It is not a byte-identical copy of the parent's history or hashes.
- The child preserves absolute simulation time. Its `genesis_tick` is the parent's selected fork tick, its `current_tick` immediately after creation is the same value, and its first step is `genesis_tick + 1`.
- A tick request means the inclusive end-of-tick boundary captured by an exact boundary event/order index and recorded state hash. Same-tick events after that captured boundary are not part of the fork.
- Scheduled actions, cooldowns, ageing, ecology cadence, and other due ticks retain absolute values.
- The default RNG model is **exact continuation**: preserve the parent seed, RNG policy, RNG namespace, absolute tick, and absolute next simulation order index. Fork creation consumes no randomness. Parent and child receive the same future named-stream draws until their accepted inputs or canonical state differ.
- Counterfactual RNG branches are deferred. If added, they require an explicit versioned model and must never silently replace exact continuation.
- The child has a fresh, deterministically derived lineage and event stream. Parent accepted events are not copied into the child stream.
- The child's fork-genesis accepted record contains the full reconstructed entity state, immutable world context, fork provenance, and compact external causal anchors needed to interpret retained parent `last_event_id` references. Cached entity and terrain documents are projections of that record.
- Parent and child canonical hashes are expected to differ because canonical hashes bind lineage. Source content equality is verified with a separate lineage-neutral content hash.
- The child can replay independently from its own fork-genesis record if parent raw history later becomes unavailable. In that case the child's replay remains verifiable, but its historical source provenance can only be classified from the stored source-hash and causal-anchor evidence.
- Fork identity is deterministic and idempotent. Wall-clock time, UUIDs, database insertion order, and process-global randomness do not participate in child run identity, lineage, canonical hashes, or fork ordering.
- Fork creation is transactional and fails closed when the configured Mongo deployment cannot provide the required transaction semantics.

### Required metadata

The child run and fork-genesis record must retain:

- child run ID and stored child lineage key;
- parent run ID as storage provenance and parent lineage key as canonical provenance;
- parent boundary tick, frame ID, terminal event ID, event order index, and parent next order index;
- `genesis_tick`, `forked_from_state_hash`, lineage-neutral source content hash, immutable world-context hash, and child genesis state hash;
- Core engine version, schema version and schema-context hash, RNG policy/version and namespace, fork semantics/version;
- canonical fork identity hash, creation command/input hash, and deterministic `branch_key`;
- replay/storage-horizon classification and compact external causal-anchor manifest.

Storage-only IDs and timestamps may be retained for operations and display, but must not affect canonical state hashes. See the ADR for identity derivation and compatibility rules.

### 5A1 completion evidence

- The impossible parent-hash-equals-child-hash criterion is removed.
- Clock, boundary, RNG, lineage, replay, causal-anchor, identity, atomicity, and compatibility semantics are explicit.
- 5A2 has bounded acceptance criteria and a verification matrix in the ADR.

## 5A2 - Fork Implementation

**Status:** implemented, covered by the focused backend contract suite, and exposed through the existing timeline/load surfaces. Successful live creation requires a transaction-capable Mongo replica set; the current local standalone deployment was verified to fail closed before child writes.

**Goal:** implement the contract in ADR-001 without adding branch comparison, fork trees, UI redesign, or gameplay behavior.

### Intended API

`POST /api/runs/{parent_run_id}/fork`

The command supplies:

- `fork_tick`;
- optional expected terminal `boundary_event_id` and `forked_from_state_hash` for compare-and-fail-closed behavior;
- deterministic `branch_key`, defaulting to `default`.

The response returns the ready child or the existing ready child for the same canonical command. A different command resolving to an existing deterministic identity is a conflict, never an overwrite.

### Bounded implementation scope

- Reconstruct the parent exclusively from accepted events through the captured boundary.
- Verify the reconstruction against the parent's recorded boundary hash and immutable world-context hash.
- Create a deterministic child lineage and fork-genesis accepted record without invoking world generation or RNG.
- Create a deterministic non-mutating Core lineage administrative record at the child genesis effective boundary.
- Start the child stream at the inherited absolute simulation tick and next simulation order index.
- Generalize replay and determinism verification to bootstrap either world-generated tick-zero genesis or snapshot-derived non-zero fork genesis.
- Materialize child entity/world projections from the accepted fork-genesis record.
- Commit child run, fork-genesis record, frame/head, and projections atomically; never mutate the parent.
- Expose parent-to-child lineage text in existing run-loading/timeline surfaces only after the backend contract passes.

### Acceptance criteria

- Parent reconstruction through the selected inclusive boundary recomputes `forked_from_state_hash` under the parent lineage.
- The lineage-neutral source content hash matches between the reconstructed parent source and the pre-materialization child genesis payload.
- The child has a fresh deterministic lineage and its own verified genesis hash; it is never asserted equal to the parent's lineage-bound hash.
- Forking at tick 0 and at a later tick works, including replay from non-zero `genesis_tick`.
- `current_tick == genesis_tick` immediately after creation; the next step is `genesis_tick + 1`; absolute due ticks are unchanged.
- Exact-continuation RNG draws and simulation ordering match an unmodified parent continuation until accepted inputs or canonical state differ.
- The fork operation does not write any parent collection document. A concurrent parent advance cannot change the already captured boundary.
- The child replays and deterministically re-simulates from its own fork genesis without parent raw history.
- Corrupt or missing child projections rebuild from the child accepted-event stream; corrupt authoritative fork-genesis data fails verification.
- Unsupported engine/schema/RNG/fork-semantics context and source-hash mismatches fail before child writes.
- The entire child creation is atomic. An injected failure leaves no child run, event, frame/head, or projection.
- Repeating an identical fork command returns the same ready child. Same identity with mismatched stored content fails as corruption/conflict.
- Existing tick-zero runs continue to replay without migration.

The complete verification matrix is in ADR-001.

## 5B - Economy: giver-owned food transfer

**Goal:** one deterministic person-to-person transfer, not markets, barter, pricing, currency, or property expansion.

- Add a giver-owned `GIVE_FOOD` utility candidate.
- An adjacent living person with critical hunger and no carried food is eligible to receive one unit of `food_inventory` from a living giver with a defined surplus.
- Select the recipient by a stable ordering rule after eligibility filtering; proposal arrival order must not decide the recipient.
- Commit one accepted event with both people in `touched_scope`, preconditions on both parties, and an atomic decrement/increment.
- Assert exact conservation: giver plus receiver `food_inventory` is unchanged.
- Defer negotiation, reciprocity, debt, barter, markets, and transfers of generic wood `inventory`.

## 5C1 - Canonical world-state entity

**Goal:** establish a proposal-owned canonical seam for mutable global state before weather exists.

- Add exactly one canonical singleton entity, `world-000`, through genesis accepted events.
- Version its minimal contract and make replay, hashing, state reconstruction, scenario genesis, and inspection recognize it generically.
- Do not add weather behavior in 5C1.
- Immutable terrain/scenario context remains separately versioned and hashed until an explicit doctrine decision changes that boundary.

## 5C2 - Weather transitions and effects

**Goal:** one deterministic global weather state per tick affecting only existing mechanics.

- Add a proposal-only weather domain that mutates `world-000`.
- Specify a versioned transition table, transition cadence, and named RNG stream before implementation. The same seed, RNG namespace, absolute tick, and state must produce the same transition.
- Stage effects separately: first transition/replay, then rain-regrowth, then storm-exposure, then storm-travel efficiency.
- Every effect uses integer rules and one authoritative weather value. Define storm travel as an exact deterministic delay/stall rule; "reduced efficiency" alone is not an acceptance criterion.
- Defer forecasting, temperature, seasons, and regional weather.

## 5D - Combat: paired command, person-to-person only

**Goal:** deterministic intervention-triggered conflict without autonomous aggression.

- An external attack request first becomes an accepted exogenous command through the normal intervention path.
- A combat domain consumes that command and proposes the actual person-to-person attack with the command event and attacker state event as causal parents.
- The attack proposal owns deterministic damage, dual-entity scope, liveness/range preconditions, and any death mutation through the existing commit pipeline.
- Start with living person attacking living person. Animals, generalized "any living entity," autonomous aggression, retaliation, weapons, groups, and tactics are deferred.
- Do not claim one shared death implementation until the existing people lifecycle and hunted-animal paths are actually unified or explicitly adapted.

## 5E - Reproduction and genetics: bounded birth

**Goal:** one deterministic, inspectable birth path with bounded population growth.

- Deterministically select one eligible adjacent healthy adult pair; proposal arrival order cannot select the pair.
- Require both parents' valid causal events, sufficient resources, a fixed resource cost, and a fixed birth cooldown recorded in canonical state.
- Commit parent resource/cooldown changes and one child creation atomically in a single accepted event with both parents and child in scope.
- Derive one or two integer traits from both parents with a versioned named RNG stream and bounded integer variance.
- Children use existing lifecycle ageing; do not add a second ageing path.
- Prove same-seed timing/traits, deterministic conflict resolution, valid parent links, and an explicit upper growth bound implied by cost and cooldown.
- Defer pregnancy simulation, trait tables, mutation systems, population curves, relationships, and animal reproduction.

## Sequencing rule

5A2 must satisfy its contract before any later Phase 5 mechanic begins. 5C1 must precede 5C2. Every phase receives focused unit tests, API/integration tests where relevant, replay verification, determinism verification, and a final diff review limited to that phase.
