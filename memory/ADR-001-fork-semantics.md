# ADR-001: Fork Semantics Contract

- **Status:** Accepted for 5A2 implementation
- **Decision version:** `fork-semantics-v1`
- **Scope:** Phase 5A only
- **Runtime implementation:** implemented in Phase 5A2; focused contract verification passes. Live successful fork creation remains environment-gated because the current local Mongo deployment is standalone rather than a transaction-capable replica set.

## Context and runtime evidence

The current runtime supports tick-zero world genesis, mutable entity projections, accepted-event replay, and same-seed shadow re-simulation. It does not support a fork genesis or an atomic child-creation transaction.

Relevant current assumptions:

- `core/mutations.py::snapshot_for_hash` hashes `{lineage, tick, entities}`. Parent and child hashes cannot match if their lineage differs.
- `core/run_service.py::lineage_key_for` derives lineage only from seed/schema/engine. A fork needs a stored lineage key because retaining the seed while creating a fresh lineage cannot be represented by that function.
- `core/rng.py::DeterministicRNG` seeds named streams from `run_seed`; live people and animal stream names include entity ID and absolute tick. World-generation streams do not include tick and must not run during fork creation.
- `core/kernel.py::build_genesis`, `core/run_service.py::create_run`, and both replay modes hardcode genesis at tick 0.
- `core/replay_service.py::verify_determinism` regenerates the world from scenario and seed. A fork must instead bootstrap from its accepted fork-genesis payload.
- `core/run_service.py` writes a run, events, entity projections, and frame in separate operations and uses UUID/wall-clock values for ordinary run storage identity. That is insufficient for atomic, idempotent fork creation.
- `accepted_events` and `commit_frames` are retained indefinitely today; `entities`, terrain on the run document, diagnostics, and history views are projections or operational caches.
- Terrain is immutable and currently excluded from `snapshot_for_hash`. The fork contract therefore binds it with a separate immutable `world_context_hash`; it does not claim the existing parent state hash covers terrain.
- If a tick accepts no event, the current service carries forward the prior hash instead of hashing the new tick. 5A2 must define and test an exact boundary hash for empty frames rather than assuming every tick has an accepted event.

`incoming/# SOURCE-OF-TRUTH-v2.md.txt` appeared during Phase 5A2 implementation and was reviewed read-only. Its taxonomy requires lineage creation to be a separate non-mutating Core administrative record. The implementation therefore atomically pairs a deterministic `LineageRecord` with the accepted `fork_genesis` simulation event; the former establishes ancestry/effective context, while only the latter establishes child world state.

## Decision

### 1. Classification

A v1 fork is a **state-equivalent exact-continuation branch from a canonical accepted-event boundary**.

It is:

- state-equivalent at the selected boundary under a lineage-neutral comparison;
- a fresh lineage and fresh child event stream;
- checkpoint-derived from a verified parent boundary;
- independently replayable from its own accepted fork-genesis record.

It is not:

- a copy of parent accepted-event history;
- a byte-exact historical continuation;
- evidence that parent and child lineage-bound hashes should match;
- a guarantee that source provenance can be re-proved after parent source evidence is removed.

### 2. Boundary and clock

The default and only v1 clock model is **preserved absolute simulation time**.

- `fork_tick` selects the inclusive end of that tick as visible in the transaction's parent read snapshot.
- The resolved boundary stores `boundary_frame_id`, terminal `boundary_event_id`, terminal `boundary_order_index`, parent `next_order_index`, and recorded boundary hash. When a frame has no event, the frame boundary is still explicit and must carry a hash computed for that tick.
- Optional expected boundary event/hash inputs act as compare-and-fail-closed guards.
- Same-tick events appended after the captured terminal order index are excluded.
- `genesis_tick = fork_tick`.
- `child.current_tick = genesis_tick` immediately after creation.
- The first child simulation step is `genesis_tick + 1`.
- Scheduled actions, cooldowns, age, cadence, and due ticks retain their absolute values; no time rebasing occurs.
- The child inherits the parent's absolute `next_order_index` for subsequent simulation events so proposal/event identity and deterministic conflict ordering are not perturbed merely by forking.

Restarting at tick 0 is rejected for v1 because it changes time-of-day, ageing, ecology cadence, cooldowns, scheduled work, event identity, and tick-named RNG streams.

### 3. RNG model

The default v1 model is **exact continuation**, identified as `rng-fork-exact-v1`.

- Preserve the parent `seed` exactly.
- Preserve the parent RNG policy/version and effective namespace exactly.
- Do not add the child lineage or branch key to live domain stream names.
- Use the preserved absolute tick in existing named streams.
- Fork creation must not instantiate or draw from simulation RNG and must not call world generation.
- Historical replay before the boundary never uses the child RNG namespace because parent events are not replayed into the child stream.
- Child replay starts from fork genesis and uses the inherited namespace only for ticks after `genesis_tick`.
- RNG policy and namespace are inputs to the child lineage derivation, so they affect canonical hashes indirectly through the lineage key. They are not mutable entity fields.

Consequence: an unmodified parent continuation and its child receive identical future random draws until accepted inputs or canonical state differ. Canonical hashes still differ because lineage differs.

A counterfactual model may later derive a namespace from parent lineage, boundary, child lineage identity, and RNG policy version. It must use a different explicit fork-semantics version/API option and is out of scope for 5A2.

### 4. Source reconstruction and hash verification

Core reconstructs the parent from accepted-event mutations only, beginning at the parent's own genesis and stopping at the captured inclusive boundary. Current `entities` documents must not be the source of fork truth.

The following values are distinct:

1. `forked_from_state_hash`: the parent's recorded canonical hash at the boundary, bound to parent lineage and absolute tick.
2. Recomputed parent canonical hash: `canonical_hash(snapshot_for_hash(reconstructed_entities, fork_tick, parent_lineage_key))`; it must equal `forked_from_state_hash`.
3. `source_content_hash`: a lineage-neutral hash over absolute tick, canonical entities, and `world_context_hash`; it compares parent source content with the child genesis payload before child lineage binding.
4. `child_genesis_state_hash`: the canonical hash over the child genesis payload, `genesis_tick`, and child lineage key.

Values 1 and 4 are expected to differ. Equality is required only between the recorded and recomputed parent hashes, and between the parent and child lineage-neutral source content hashes.

The immutable `world_context_hash` covers scenario ID and versioned scenario configuration, width, height, and terrain. It closes the current terrain-hash gap for fork verification without falsely claiming existing parent state hashes already cover terrain.

### 5. Child lineage and deterministic identity

Canonical fork identity excludes wall-clock time, UUIDs, database object IDs, and insertion order.

Define a canonical lineage input containing:

```text
kind = fork-lineage-v1
parent_lineage_key
fork_tick
boundary_event_id or explicit empty-frame boundary identity
boundary_order_index
forked_from_state_hash
source_content_hash
world_context_hash
branch_key
engine_version
schema_context_hash
rng_policy_version
rng_namespace
fork_semantics_version
```

`child_lineage_key` is the SHA-256 canonical hash of that object. `branch_key` defaults to `default`; a caller must supply a different stable branch key to create another child from the same boundary.

The storage command additionally contains `parent_run_id` and expected compare values. Its canonical hash is `creation_command_hash`. The deterministic child run ID is derived from that command hash. `parent_run_id` can distinguish storage operations but is not an input to `child_lineage_key`, so a storage-only parent ID cannot change canonical state hashes.

An optional creation timestamp may be stored for display after identity is resolved. It is never canonical.

### 6. Child history and fork genesis

- Do not copy parent accepted events into the child stream.
- Create one deterministic, hash-verified Core `LineageRecord` administrative record with the child genesis effective boundary. It cannot mutate world state or simulation time.
- Create one Core-owned accepted `fork_genesis` boundary record at `genesis_tick`.
- Its authoritative payload contains the complete canonical entity set, immutable world context, exact source/boundary metadata, inherited next simulation order index, schema/RNG/fork versions, and external causal-anchor manifest.
- It does not run through a domain proposal and does not overwrite source entity `last_event_id` values.
- Parent event IDs referenced by copied entity causal fields remain stable external ancestors. The compact manifest records each referenced ID with its parent lineage and verifiable event/header hash, allowing the child to validate the anchor without copying full parent history.
- Subsequent child events refer to child events normally once each entity advances.
- The child event stream has its own stream sequence. Simulation `order_index` remains absolute and begins from the captured parent next order index; the fork boundary record does not consume a simulation order index.
- `kernel_runs`, `entities`, terrain/run state, and any checkpoint materialization are rebuildable projections of accepted child events and immutable genesis context, not independent truth.

If parent history later becomes unavailable, child replay and hash verification remain available. Source provenance is then reported as `anchored-source-unavailable`, not freshly re-proved.

### 7. Replay semantics

Replay must dispatch by genesis kind:

- **World genesis:** existing seed/scenario generation at tick 0, retained for backward compatibility.
- **Fork genesis:** load the accepted fork-genesis payload at stored non-zero `genesis_tick`, verify its child genesis hash, then apply child events after the boundary.

Recorded-event replay rebuilds from the accepted fork-genesis payload and verifies every child frame. Determinism verification starts a shadow child from the same fork-genesis payload, inherited absolute next order index, RNG policy/namespace, and world context, then re-runs ticks `genesis_tick + 1` through `current_tick`.

Parent history is needed during fork creation and optional later source-provenance re-verification, but not for ordinary child replay.

### 8. Atomicity, concurrency, and idempotency

5A2 requires a Mongo transaction with snapshot/majority semantics. If the deployment cannot provide it, fork creation fails before any child write; v1 does not fall back to a partially visible staged child.

Within one transaction Core must:

1. Read the parent run, lineage/schema context, stream head, boundary frame/event, and required accepted events from one consistent snapshot.
2. Resolve the exact terminal boundary and verify optional expected values.
3. Reconstruct source state and verify parent canonical and world-context hashes.
4. Derive the canonical fork identity, creation command hash, child lineage, and deterministic child run ID.
5. If the identical ready child exists, verify its command/hash fields and return it.
6. If the deterministic identity exists with different content, fail as conflict/corruption.
7. Insert the child lineage administrative record, child run, accepted fork-genesis record, genesis frame/head, immutable context, and projections.
8. Re-read/verify the selected parent boundary from the transaction snapshot and commit.

The transaction never updates a parent document. Concurrent parent progression may legitimately append after the selected boundary, but cannot alter which boundary the fork captured. Tests asserting byte-for-byte parent immutability must pause unrelated parent activity or compare only fork-induced writes.

Any exception aborts the transaction and leaves no child run, accepted event, frame/head, or projection. Repeating the same command returns the same child; it never creates a sibling or overwrites state.

### 9. Version and compatibility policy

Required stored context:

| Field | Purpose |
| --- | --- |
| `engine_version` | Exact Core/domain behavior expected after genesis |
| `schema_version` | Human-readable schema compatibility version |
| `schema_context_hash` | Canonical hash of the executable entity/event/genesis schema context |
| `rng_policy_version` | Named-stream derivation policy |
| `rng_namespace` | Effective namespace inherited by exact continuation |
| `fork_semantics_version` | Boundary, identity, lineage, and replay rules |
| `replay_horizon` | `child-full`; child events available from fork genesis |
| `source_horizon` | `parent-full-at-creation`, later allowed to degrade to `anchored-source-unavailable` |

5A2 initially supports only parent engine/schema/RNG contexts executable by the current process. Missing hashes, unknown versions, mismatched scenario context, or unsupported historical engine behavior fail closed before child creation. No silent schema upgrade or reinterpretation is allowed.

## 5A2 verification matrix

| Case | Required evidence |
| --- | --- |
| Fork from genesis boundary | Child `genesis_tick == 0`; source reconstruction/hash verification passes; child lineage differs; child replays |
| Fork from later tick | Inclusive terminal boundary, absolute tick, pending actions/cooldowns, and inherited next order index are exact |
| Non-zero genesis replay | Recorded replay and shadow determinism begin at `genesis_tick`, not 0, and first step is `genesis_tick + 1` |
| Source state comparison | Reconstructed parent canonical hash equals `forked_from_state_hash`; lineage-neutral parent/child content hashes match |
| Lineage-bound hashes | Child lineage and genesis hash are deterministic and differ from the parent where lineage differs |
| Parent immutability | Raw parent run, events, frames, entities, diagnostics/projections, stream head, and hashes show no fork-induced writes |
| Child deterministic replay | Repeated child replay and shadow re-simulation produce identical child event/state hash sequences |
| Exact-continuation RNG | Parent and child draw the same values for the same future named streams until accepted input/state divergence |
| Concurrent parent progression | A barrier-controlled append after boundary capture cannot enter or move the child's boundary |
| Atomic failure | Failure injection after each planned write aborts all child records; no partial child is listable or loadable |
| Projection rebuild | Deleted/corrupt child entity or terrain projections rebuild from accepted fork genesis plus child events |
| Authoritative corruption | Changed fork-genesis payload or accepted event fails hash/replay verification; it is never repaired from a cache |
| Version mismatch | Unknown/mismatched engine, schema context, RNG policy, or fork semantics fails before writes |
| Idempotent repeat | Identical command returns the same child ID and unchanged bytes; different content at that ID fails |
| Empty accepted-event frame | Boundary hash is tick-correct and forkable even when no event committed in the selected tick |
| Parent source unavailable later | Child replay passes; source verification reports anchored/unavailable without overclaiming |
| Existing run regression | Pre-5A tick-zero runs retain identical replay and determinism behavior |

## Exact 5A2 implementation surface

Implemented production surface, bounded to the fork contract:

- `backend/core/run_service.py`: stored lineage/genesis/version metadata, deterministic fork identity, parent reconstruction orchestration, transaction, idempotency, atomic child materialization.
- `backend/core/replay_service.py`: genesis-kind dispatch, non-zero genesis, fork-snapshot shadow bootstrap, independent child replay, source-provenance classification.
- `backend/core/kernel.py`: separate world-genesis and fork-genesis bootstrap contracts; no domain behavior change.
- `backend/core/rng.py`: expose/version the effective RNG policy and namespace without changing v1 draw results.
- `backend/core/hashing.py` and `backend/core/mutations.py`: lineage-neutral content/world-context hashing helpers and explicit schema-context inputs; preserve old-run hash compatibility.
- `backend/core/commit_pipeline.py`: accept stored child lineage and absolute order continuation; validate external causal anchors if validation is centralized here.
- `backend/core/db.py`: transaction/session support and required unique indexes for child ID/creation command hash.
- `backend/api/routes.py`: fork request/response schema and one endpoint.
- `backend/tests/test_phase5_fork.py`: the matrix above, including failure injection and concurrency barriers.
- `frontend/src/api.js`, `frontend/src/components/TimelineTab.jsx`, and `frontend/src/components/LoadRunModal.jsx`: only after backend acceptance; add the existing-surface fork action and lineage label.

No new domain, gameplay behavior, branch comparison, fork tree, or storage-compaction system belongs in 5A2.

## Implementation status and retained risks

- The current local Mongo deployment was verified as standalone (`setName` absent), so it cannot execute successful fork transactions. The implemented endpoint returns a fail-closed service error before child writes; a replica-set deployment is required for live success verification.
- Existing lineage-bound state hashes still exclude immutable terrain; Phase 5A2 adds and verifies a separate `world_context_hash` without rewriting historical hashes.
- New runs use tick-correct empty-frame hashes. Pre-5A runs retain the legacy carry-forward policy and are not forkable when required schema/hash context is absent.
- New runs store lineage explicitly; existing runs retain the derived-lineage fallback for replay but fail closed for fork creation when Phase 5A metadata is absent.
- Fork creation validates external causal anchors against actual parent accepted events and later validates the stored compact manifest; ordinary non-exogenous commits can now reject unvalidated parent IDs.
- Historical executable engine/schema registries do not exist. v1 must reject unsupported old contexts rather than claim cross-version deterministic continuation.
- Startup now declares unique run, fork-command, fork-lineage, event, frame, and entity indexes; deployment still must provide replica-set transaction semantics.
