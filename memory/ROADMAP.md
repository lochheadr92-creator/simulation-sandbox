# Phase 5 Roadmap - Minimal Foundations

Phase 5 keeps the existing doctrine: accepted events are simulation truth; Core owns time, ordering, validation, mutation, replay, hashing, lineage, RNG policy, and storage authority; domains only propose. Each phase is the smallest deterministic, proposal-only foundation that makes the mechanic real and inspectable.

The detailed fork decision and implementation boundary are recorded in [ADR-001: Fork Semantics Contract](ADR-001-fork-semantics.md).

## Priority and gates

1. 5A1 - Fork Semantics Contract
2. 5A2 - Fork Implementation (`Implemented — Verification Pending` for live transaction-capable Mongo)
3. 5A3 - Deterministic Navigation (behaviour; implemented)
4. 5A4a - Transactional Tick Persistence (implemented)
5. **5A5 - Cognitive Grounding** (Perception / Knowledge / Planning) — implemented
6. **5A6 - Cognitive Visualisation and Live World Readability** — implemented
7. **5B - Social Behaviour Foundations** (`5B1`–`5B2` implemented; **5B3 next active**)
8. 5C - Resource Organisation and Economic Foundations
9. 5D - Canonical World State and Environment (controlled parallel workstream if 5B3 is blocked)
10. 5E - Social Conflict
11. 5F - Pairing, Kinship and Reproduction
12. 6 - Groups, Settlements and Civilisation (deferred)

No phase may be marked complete from workflow labels such as `testing_agent_v4`. Completion requires reproducible repository commands and recorded results.

Status labels used in this roadmap:

- **implementation complete** — code and focused tests land; does not by itself close the phase
- **Implemented — Verification Pending** — implementation complete, but one or more acceptance criteria remain unexercised solely due to missing infrastructure (see policy below)
- **fully verified** — all deterministic acceptance gates for the phase have passed with recorded results
- **Reopened — Blocking** — a previously implemented or completed phase later failed an acceptance gate

### Infrastructure-gated verification policy

When an acceptance criterion cannot be exercised because the available local environment lacks required infrastructure, the phase may be marked `Implemented — Verification Pending` only when:

- the blocked check depends solely on a documented infrastructure capability;
- the implementation fails closed when that capability is unavailable;
- all available deterministic unit, contract, replay, and failure-path tests pass;
- the exact unverified criteria, required infrastructure, and reproduction commands are recorded.

Unrelated phases may continue.

Dependent phases may be developed cautiously, but they must not be marked fully verified or closed while a required prerequisite remains `Verification Pending`.

When the required infrastructure becomes available, the deferred acceptance checks must be run.

Failure reopens the prerequisite phase and blocks closure of dependent phases until the defect is repaired or affected dependent work is reverted.

Known Phase 5 infrastructure gate: 5A2 live fork creation (and any other criterion that requires multi-document transactional commit) depends on a transaction-capable Mongo replica set. Standalone Mongo is not sufficient for those live checks; fail-closed behaviour on unsupported deployments remains required.

### Acceptance regression and rollback policy

If an implemented or completed phase later fails one of its deterministic acceptance gates, its status changes to `Reopened — Blocking`.

Closure of dependent phases is paused immediately.

Patch-forward is preferred when canonical state, replay compatibility, determinism, and persistence contracts can be preserved safely.

Revert the affected phase and dependent work when those contracts cannot be preserved safely.

Clearly distinguish:

- implementation complete
- verification pending
- fully verified
- reopened and blocking

Development on dependency-independent work may continue under the parallel-work rule below; formal closure of any dependent phase remains blocked while a prerequisite is `Reopened — Blocking` or `Verification Pending` when that pending check is required.

### Controlled parallel work when 5B3 is blocked

**Phase 5B3 is the next active phase** on the social interaction chain.

If Phase 5B3 is blocked, dependency-independent Phase 5D work may proceed as the controlled parallel workstream.

Do not bypass the 5B interaction chain by starting barter (`5C5`), conflict motives (`5E3`), reproduction (`5F3`), lifecycle-dependent social systems, or other phases whose declared prerequisites are incomplete. From this roadmap, that includes at least `5B4`–`5B6`, Phase `5C` (depends on `5B1`–`5B6`), Phase `5E` (depends on 5B social foundations and 5C ownership/resource contracts), and Phase `5F` (depends on 5B social facts/memory and lifecycle state). Phase 5D depends only on completed 5A Core/replay contracts and is the permitted parallel track.

## 5A5 - Cognitive Grounding Vertical Slice

**Status:** in progress / implemented as a vertical slice.

**Goal:** close remaining omniscient decision paths so survival targets come only from bounded perception and sparse personal knowledge.

- Perception: integer Manhattan vision; detections for people, animals, food, water, shelter, danger; material-change only knowledge writes.
- Knowledge: observer-owned facts (`knowledge-v2`) with last-known locations; no full world copy; caps per category.
- Planning: Needs drive urgency; eligible targets only from knowledge / this-tick detections; exploration is 4-neighbour unknown tiles only.
- Animals are not globally scanned for hunting; last-known animal positions may go stale without becoming live truth.
- Social behaviour, resource organisation, weather, conflict, and reproduction remain later stages (unchanged goals below).

## 5A6 — Cognitive Visualisation and Live World Readability

**Status:** implemented as a frontend projection stage.

**Goal:** make existing canonical action state and selected-person cognition observable without introducing any new simulation authority.

- The selected-person canvas overlay uses a bounded, versioned, observer-specific projection for current perception, retained knowledge, stale last-known entity markers, latest discoveries, and stored route state.
- Route, target, arrival-mode, planning, action, injury, death, urgent-need, and accepted-change indicators are presentation only. They never create state, recalculate routes, or alter decision results.
- The normal observer view remains complete when no person is selected; personal fog is never applied automatically.
- 5B1 Food Ownership and Atomic Transfer and 5B2 Social Observation Facts are implemented. **Phase 5B3 (Request, Offer and Response Protocol) is the next active phase.**

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

**Status:** `Implemented — Verification Pending` for live transaction-capable Mongo. Covered by the focused backend contract suite and exposed through the existing timeline/load surfaces. Successful live creation requires a transaction-capable Mongo replica set; the current local standalone deployment was verified to fail closed before child writes. Deferred live criteria: full atomic child-create success path and multi-document transaction commit under a replica set (see Infrastructure-gated verification policy).

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

## Phase 5B — Social Behaviour Foundations

**Goal:** build minimal deterministic social interaction from bounded personal observation; this is not a complete economy.

**Dependencies:** completed 5A1–5A6 contracts, especially version-pinned perception, knowledge, planning, and Core commit ordering.

**Bounded implementation scope:** proposal-only social actions and bounded observer-owned facts; Core remains the sole canonical mutation authority.

**Explicit deferrals:** currency, markets, debt, wages, trade routes, large property systems, LLM authority, hidden mutable domain state, and Dice Reactions architecture.

**Deterministic acceptance gate:** stable selection, canonical ordering, replay-equivalent state/event traces, bounded projections, and Core-validated rejection behaviour.

### 5B1 — Food Ownership and Atomic Transfer

**Status:** implemented and focused-verified (`29 passed` across 5B1, 5A5, and kernel determinism suites).

**Goal:** establish a giver-owned food transfer primitive, not a complete economy.

**Dependencies:** 5A5 bounded perception/knowledge and the Core commit pipeline.

**Bounded implementation scope:** `GIVE_FOOD` selects one stably ordered adjacent living recipient with critical hunger and no carried food. Core validates both parties and atomically transfers one unit of `food_inventory` while preserving exact pairwise conservation.

**Explicit deferrals:** negotiation, requests, offers, refusals, reciprocity, generic `inventory` transfer, barter, markets, currency, debt, and property expansion.

**Deterministic acceptance gate:** accepted events contain both people in scope and transfer provenance; rejected proposals have stable reasons; success, insufficient supply, invalid ownership, duplicate/replay, rollback, cognitive regression, and kernel determinism tests pass.

### 5B2 — Social Observation Facts

**Status:** implemented as `social-observation-v1` nested within compatible `knowledge-v2` `known_people` records.

**Goal:** extend bounded perception and `known_people` with visible action, visible injury/distress, apparent urgent need, and apparent carried food.

**Dependencies:** 5B1 and 5A5 perception/knowledge caps.

**Bounded implementation scope:** versioned observer-owned facts derived only from current visible frames, with explicit visibility semantics and bounded retention.

**Visibility contract (`social-observation-v1`):** only a living non-observer person inside the current integer-Manhattan perception radius is observed. The retained record contains the subject ID, last-known position/tick, a whitelisted coarse action kind/status, `appears_injured`, `apparent_urgent_need` (`none`, `distressed`, or `critical` from existing seek/critical hunger-thirst thresholds plus visible injury), and boolean `appears_to_carry_food` from existing carried-food fields. It never contains health, hunger, thirst, energy, quantities, plan/goal, target, route, utility, or motive. Identical re-observation does not write solely for tick advancement; unseen records remain last-known until material refresh or deterministic eviction.

**Explicit deferrals:** exact private inventory without an explicit visibility rule, telepathy, global social knowledge, relationships, and interaction protocol state.

**Deterministic acceptance gate:** same frame yields identical facts regardless of entity insertion/proposal arrival order; facts are capped, replayable, and never canonical truth by themselves.

### 5B3 — Request, Offer and Response Protocol

**Status:** next active phase (not started).

**Goal:** add one bounded food-interaction state machine: pending, accepted, fulfilled, refused, expired, and invalidated.

**Dependencies:** 5B1 transfer primitive and 5B2 visible social facts (both implemented).

**Bounded implementation scope:** proposal-owned interaction records with deterministic expiry, response authority, causal parents, and duplicate prevention; fulfilment invokes 5B1 rather than mutating inventory directly.

**Explicit deferrals:** open-ended conversation, bargaining, multi-party exchange, persistent trust fields, and generic resource protocols.

**Deterministic acceptance gate:** identical inputs produce one ordered lifecycle, duplicate commands cannot duplicate fulfilment, and expiry/invalidations replay exactly.

### 5B4 — Event-Backed Interaction Memory

**Goal:** retain bounded observer-owned facts referencing accepted interaction events.

**Dependencies:** 5B3 accepted interaction lifecycle and existing knowledge retention rules.

**Bounded implementation scope:** initial fact kinds are helped, refused, requested, offered, and witnessed assistance, each with accepted-event provenance.

**Explicit deferrals:** free-form memories, inferred private motives, unbounded social history, and memory as a replacement for accepted-event truth.

**Deterministic acceptance gate:** facts are bounded and reconstruction-safe; every fact references a valid accepted event or is rejected without state mutation.

### 5B5 — Derived Reciprocity and Trust

**Goal:** derive bounded reciprocity/trust signals from retained interaction facts, confidence, and recency.

**Dependencies:** 5B4 event-backed facts and deterministic time/replay.

**Bounded implementation scope:** a reproducible derived projection may influence sharing, requests, and refusals without becoming a freely mutable universal trust field.

**Explicit deferrals:** global reputation, relationship calculus, factions, romance, and unbounded score accumulation.

**Deterministic acceptance gate:** equal fact histories and ticks produce equal signals; projections are bounded, rebuildable, and cannot mutate canonical state directly.

### 5B6 — Persistent Motive and Replanning Contract

**Goal:** establish the first persistent social motive: maintain a personal food reserve.

**Dependencies:** 5B1 transfer, 5B5 derived signals, and existing multi-tick planning/action state.

**Bounded implementation scope:** deterministic progress, interruption, resumption, abandonment, and completion for one reserve-maintenance motive.

**Explicit deferrals:** broad motive libraries, personality systems, strategic planning, and hidden mutable planner state.

**Deterministic acceptance gate:** identical state/seed/tick yields the same lifecycle and replay trace; interruption and resumption cannot duplicate transfer or create unbounded state.

## Phase 5C — Resource Organisation and Economic Foundations

**Goal:** organise canonical resources after social interaction foundations are complete.

**Dependencies:** 5B1–5B6 and existing Core entity/event/replay contracts.

**Bounded implementation scope:** resource ownership, storage, cooperative work, allocation, and narrowly bounded barter/value stages.

**Explicit deferrals:** currency, markets, debt, wages, trade routes, large property systems, and macroeconomic simulation.

**Deterministic acceptance gate:** each stage proves Core-owned resource mutation, exact accounting/conservation where applicable, bounded state, stable conflict resolution, and replay determinism.

### 5C1 — Canonical Resource Ownership Contract

**Goal:** define canonical ownership and authority for existing resource-bearing entities.

**Dependencies:** 5B1 transfer provenance and Core entity mutation envelopes.

**Bounded implementation scope:** versioned owner references, ownership validation, and migration/default rules for existing resources only.

**Explicit deferrals:** land/property law, inheritance, taxation, and generic economy mechanics.

**Deterministic acceptance gate:** ownership changes require accepted Core events, invalid owners reject deterministically, and replay reconstructs identical owner state.

### 5C2 — Storage and Stockpiles

**Goal:** add bounded canonical storage locations and stockpiles.

**Dependencies:** 5C1 ownership contract.

**Bounded implementation scope:** versioned storage entities with explicit capacity and atomic deposit/withdraw proposals.

**Explicit deferrals:** hauling networks, spoilage systems, warehouses, theft, and settlement logistics.

**Deterministic acceptance gate:** deposits/withdrawals conserve resources, capacity conflicts resolve stably, and storage state replays exactly.

### 5C3 — Production and Cooperative Work Tasks

**Goal:** support one bounded multi-person productive task using existing resources.

**Dependencies:** 5C2 storage and existing multi-tick action contracts.

**Bounded implementation scope:** deterministic task eligibility, participant scope, contribution accounting, and one accepted output path.

**Explicit deferrals:** job markets, specialised professions, production trees, and arbitrary work graphs.

**Deterministic acceptance gate:** participant/order conflicts have stable outcomes, inputs/outputs account exactly, and task replay is identical.

### 5C4 — Resource Allocation Behaviour

**Goal:** let existing deterministic planning choose among bounded resource allocations.

**Dependencies:** 5B6 motives and 5C1–5C3 resource contracts.

**Bounded implementation scope:** proposal-only choices among existing owned resources, storage, and cooperative tasks.

**Explicit deferrals:** central planning, markets, dynamic price discovery, and hidden allocator state.

**Deterministic acceptance gate:** candidate ordering is stable, Core revalidation resolves contention, and no planner mutates resources directly.

### 5C5 — Barter and Subjective Value

**Goal:** explore one bounded bilateral barter/value contract.

**Dependencies:** 5B3 interaction protocol and 5C1–5C4 resource organisation.

**Bounded implementation scope:** explicit offer/accept/atomic exchange of a tightly specified resource set with deterministic subjective evaluation.

**Explicit deferrals:** money, market clearing, credit, debt, wages, trade routes, and general pricing.

**Deterministic acceptance gate:** bilateral exchange is all-or-nothing, duplicate-safe, value inputs are inspectable, and replay produces the same accepted/rejected trace.

## Phase 5D — Canonical World State and Environment

**Goal:** establish a canonical global state seam before environmental behaviour.

**Dependencies:** completed 5A Core/replay contracts; no dependency on unimplemented economic behaviour.

**Bounded implementation scope:** one world-state entity followed by deterministic weather state and staged effects.

**Explicit deferrals:** seasons, forecasting, temperature, regional weather, climate systems, and environmental LLM authority.

**Deterministic acceptance gate:** global state is event-sourced, versioned, replayable, and no effect uses wall-clock or unpinned randomness.

### 5D1 — Canonical World-State Entity

**Goal:** create one canonical singleton `world-000` through accepted genesis events.

**Dependencies:** Core genesis, hashing, reconstruction, and inspection seams.

**Bounded implementation scope:** minimal versioned singleton recognition in scenario genesis, replay, hashing, and projections; no behaviour.

**Explicit deferrals:** weather transitions, global mutable domain state outside the singleton, and terrain ownership changes.

**Deterministic acceptance gate:** genesis/replay/hash/reconstruction recognise exactly one world entity and corrupt/missing projections rebuild or fail closed correctly.

### 5D2 — Deterministic Weather State

**Goal:** add one authoritative global weather transition per defined cadence.

**Dependencies:** 5D1 singleton entity and a versioned Core-issued RNG stream.

**Bounded implementation scope:** explicit integer transition table, cadence, state value, and proposal-only weather domain.

**Explicit deferrals:** weather effects, forecasting, regional cells, seasons, and temperature.

**Deterministic acceptance gate:** same seed, stream, tick, state, and version yield the same transition/event trace under replay.

### 5D3 — Weather Effects and Behavioural Response

**Goal:** apply staged exact weather effects to existing mechanics.

**Dependencies:** 5D2 weather state and affected existing mechanics.

**Bounded implementation scope:** separately gated rain-regrowth, storm-exposure, and exact storm-travel delay/stall rules.

**Explicit deferrals:** vague efficiency modifiers, new weather categories, climate, and weather-driven spawning.

**Deterministic acceptance gate:** each effect has integer semantics, visible causal parents, no duplicate application, and identical replay results.

## Phase 5E — Social Conflict

**Goal:** introduce conflict only after ownership and social consequence seams are explicit.

**Dependencies:** 5B social foundations and 5C ownership/resource contracts.

**Bounded implementation scope:** unauthorised taking, detection/consequences, autonomous conflict motives, and bounded combat execution in separate stages.

**Explicit deferrals:** factions, warfare, tactics, weapons, groups, retaliation trees, and unbounded hostility state.

**Deterministic acceptance gate:** each conflict consequence has an accepted causal chain, stable contention resolution, and replayable canonical mutations.

### 5E1 — Unauthorized Resource Taking

**Goal:** represent one explicit unauthorised resource-taking proposal.

**Dependencies:** 5C1 ownership and 5C2 storage/stockpile semantics where used.

**Bounded implementation scope:** one actor, one owned resource, exact ownership preconditions, and atomic transfer/rejection.

**Explicit deferrals:** stealth, theft skill, property law, violence, and retaliation.

**Deterministic acceptance gate:** ownership violations and stale attempts reject stably; accepted taking preserves exact accounting and replay.

### 5E2 — Detection and Social Consequences

**Goal:** record bounded observation-backed consequences of unauthorised taking.

**Dependencies:** 5B2 social observation facts, 5B4 interaction memory, and 5E1.

**Bounded implementation scope:** visible detection fact plus one deterministic consequence proposal.

**Explicit deferrals:** justice systems, reputation networks, gossip, and global crime state.

**Deterministic acceptance gate:** only eligible observers receive bounded facts; consequence provenance and replay are deterministic.

### 5E3 — Autonomous Conflict Motives

**Goal:** permit one deterministic motive to initiate conflict under explicit conditions.

**Dependencies:** 5B6 persistent motives and 5E1–5E2 causal facts.

**Bounded implementation scope:** one versioned candidate with inspectable threshold and stable target selection.

**Explicit deferrals:** personality, vendettas, group conflict, tactics, and LLM decisions.

**Deterministic acceptance gate:** identical observed facts/state produce identical candidate selection and no motive directly mutates canonical state.

### 5E4 — Combat Execution

**Goal:** execute one deterministic person-to-person conflict action through Core.

**Dependencies:** 5E3 and existing lifecycle/death contracts.

**Bounded implementation scope:** living person pairs, dual scope, liveness/range preconditions, deterministic damage, and explicitly adapted death mutation.

**Explicit deferrals:** animals, weapons, groups, tactics, retaliation, and combat economies.

**Deterministic acceptance gate:** attacks are causally parented, conflict order is stable, and replay matches.

## Phase 5F — Pairing, Kinship and Reproduction

**Goal:** add bounded durable social bonds before any birth path.

**Dependencies:** 5B social facts/memory and lifecycle canonical state.

**Bounded implementation scope:** pairing, shared-resource bond, reproduction, and kinship are isolated stages with explicit state and growth limits.

**Explicit deferrals:** romance simulation, genetics beyond approved scope, population curves, animal reproduction, and household economies beyond the listed bond.

**Deterministic acceptance gate:** every relationship/birth mutation is Core-accepted, pair selection/conflict resolution is stable, and replay proves bounded growth.

### 5F1 — Durable Pairing Foundations

**Goal:** establish one bounded durable pair record between eligible people.

**Dependencies:** 5B4 interaction memory and 5B5 derived signals.

**Bounded implementation scope:** eligibility, mutual acceptance protocol, pair scope, and lifecycle-safe invalidation.

**Explicit deferrals:** romance narratives, multi-partner systems, households, and reproduction.

**Deterministic acceptance gate:** pairing is duplicate-safe, mutual, replayable, and invalidates deterministically on lifecycle changes.

### 5F2 — Household or Shared-Resource Bond

**Goal:** allow one bounded shared-resource relation for an existing pair.

**Dependencies:** 5F1 and 5C ownership/storage contracts.

**Bounded implementation scope:** an explicit shared-resource reference and Core-validated access rules.

**Explicit deferrals:** settlements, inheritance, broad property pooling, and multi-household logistics.

**Deterministic acceptance gate:** access/withdrawals have exact authority, accounting, rejection, and replay behaviour.

### 5F3 — Reproduction

**Goal:** add one deterministic, inspectable birth path with bounded growth.

**Dependencies:** 5F1, 5F2 where resource cost applies, and lifecycle ageing.

**Bounded implementation scope:** one eligible adjacent healthy pair, fixed costs/cooldowns, atomic parent/child event, and bounded integer trait derivation using a versioned stream.

**Explicit deferrals:** pregnancy simulation, trait tables, mutation systems, population curves, and animal reproduction.

**Deterministic acceptance gate:** same seed/timing/traits replay identically; parent links are valid; cost/cooldown imply an explicit growth bound.

### 5F4 — Kinship and Parent-Child Knowledge

**Goal:** add bounded canonical parent links and observer-owned knowledge of visible kinship.

**Dependencies:** 5F3 birth events and 5B2/5B4 fact rules.

**Bounded implementation scope:** parent-child relation provenance and capped visible/learned kin facts.

**Explicit deferrals:** genealogy graphs, inheritance, clans, and unbounded family memory.

**Deterministic acceptance gate:** parent links reconstruct solely from accepted events; knowledge remains bounded and never replaces canonical lineage.

## Phase 6 — Groups, Settlements and Civilisation

**Status:** deferred.

**Goal:** eventually compose verified social, resource, environment, conflict, and kinship foundations into group-scale simulation.

**Dependencies:** completion and explicit acceptance of the relevant Phase 5B–5F contracts.

**Bounded implementation scope:** none in the current roadmap; no stubs are authorised.

**Explicit deferrals:** groups, settlements, civilisation mechanics, institutions, governance, trade networks, and population-scale systems.

**Deterministic acceptance gate:** before implementation, define a versioned canonical group contract, bounded growth/retention model, proposal-only domain boundary, and replay verification matrix.

## Sequencing rule

5A2 must satisfy its contract before later Phase 5 mechanics that depend on fork/lineage semantics. Live 5A2 success-path verification remains infrastructure-gated (transaction-capable Mongo) under the Infrastructure-gated verification policy; fail-closed behaviour on unsupported deployments does not by itself block unrelated work.

Within the revised sequence, 5B1 is a transfer primitive rather than complete economy work; **5B2 is implemented**; **5B3 is the next active stage** on the social interaction chain. If 5B3 is blocked, Phase 5D is the only controlled parallel workstream authorised by this roadmap. Every stage receives focused unit tests, API/integration tests where relevant, replay verification, determinism verification, and a final diff review limited to that stage.
