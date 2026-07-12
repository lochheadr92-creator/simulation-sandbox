# Source of Truth v2

---

## 1. Purpose and Authority

### 1.1 What This Document Defines

Source of Truth v2 defines what is canonical in the Simulation Sandbox kernel, what is not canonical, and how canonical truth is represented through records, state, lineage, time, events, administrative records, receipts, checkpoints, and projections.

### 1.2 What This Document Does Not Define

This document does not define product behavior, interface design, presentation, implementation code, database schemas, network protocols, or user-facing features.

### 1.3 Authority Hierarchy

| Document | Authority |
|---|---|
| Constitution | Binding doctrine. Wins all conflicts. |
| Source of Truth v2 | Defines canonical data meaning and record authority. |
| Architecture v2 | Defines system structure and execution mechanisms. |
| Engine Contracts | Defines domain engine interfaces and proposal payload rules. |
| Storage and History | Defines retention, horizon, checkpoint, archive, and purge policy. |
| Verification Strategy | Defines proof obligations and test implementation. |

If these documents conflict, the Constitution wins first, then Source of Truth v2, then specialized specifications.

---

## 2. Core Identity

### 2.1 Simulation Sandbox

Simulation Sandbox is an independent deterministic living-world simulation engine.

### 2.2 Central Model

- Core owns canonical truth.
- Domain engines observe state and submit proposals.
- Core validates, orders, accepts, rejects, and commits proposals.
- Only accepted canonical events mutate state.
- Rejected proposals are diagnostics, not state mutations.
- Canonical state must be reconstructable through deterministic replay.
- Domain engines cannot directly mutate canonical state.
- Observation frames are read-only and version-pinned.
- RNG is deterministic and Core-governed.
- Ongoing actions are represented as canonical multi-stage state.
- Interruptions are proposals resolved deterministically by Core.
- Population emerges through lifecycle processes, not spawn-rate mechanics.
- Rendering cadence is separate from simulation cadence.
- LLMs may assist with presentation or explanation but cannot create simulation truth.

---

## 3. Canonical Truth Model

### 3.1 Core Definitions

**Canonical world truth** is the authoritative simulated-world state and simulation time produced by accepted simulation events, interpreted under the canonical schema, version, lineage, and Core administrative records effective at each event boundary.

**Canonical state** is the current materialized expression of canonical world truth. It is operationally useful but not independent of canonical history.

**Canonical history** is the durable Core-owned record sequence needed to interpret, replay, reconstruct, validate, or explain a kernel lineage. It includes accepted simulation events and replay-relevant administrative records.

**Canonical causal records** are Core-owned records that preserve causal, compression, checkpoint, receipt, migration, lineage, or reconstruction evidence.

**Canonical administrative and audit truth** is an authoritative Core-owned record that an input, proposal, rejection, administrative decision, checkpoint, receipt, lineage action, or similar non-world action occurred. It is not canonical simulated-world truth and cannot independently mutate world state or simulation time.

**Simulation time** is Core-owned simulated time. It is not wall-clock time.

**Lineage** is a causally honest run ancestry: genesis, fork, import, migration, branch, checkpoint, or continuation boundaries.

**Event boundary** is the deterministic position of an accepted simulation event in the canonical event order.

**Administrative effective boundary** is the deterministic boundary where an administrative record begins affecting replay, interpretation, validation, schema compatibility, storage horizon, receipt validity, checkpoint validity, migration, lineage, or projection validity.

Current state is derived by applying accepted simulation events under the administrative records effective at their boundaries, optionally beginning from a valid Core-authorized checkpoint inside declared storage horizons.

### 3.2 Conflict Resolution Rules

- The Constitution overrides older audit wording that treated receipt creation, checkpoint creation, or projection invalidation as possible event families. In Source of Truth v2, these are **Core administrative records**, not simulation events.
- "Canonical causal records" is broad enough to become dangerous. This document narrows it: causal records can support replay, reconstruction, compression, or explanation, but only accepted simulation events mutate world state or simulation time.
- Rejected proposals are **Core-owned audit records**, not canonical world history. They explain non-events. If a failed attempt has world consequences, those consequences require accepted simulation events.
- Receipts are canonical causal records, not world truth and not mutable state. They may support deep reconstruction but cannot replace accepted events inside the recent replay horizon.
- Checkpoints are both records and artifacts: the **CheckpointRecord** is canonical; the serialized checkpoint artifact is valid only while its hash, lineage, schema context, and source range match the record.
- External influence uses a **paired model**: an ExternalInfluenceRecord captures normalized input, and accepted simulation events reference it when it causes world mutation. This avoids making every input a world event.
- Administrative records do not share a false event shape with simulation events. Separate ordered domains plus mandatory deterministic effective boundaries are safer.
- Deep causal reconstruction is not byte-exact replay. Event replay may start from checkpoints inside declared horizons, but older compressed history is reconstruction unless raw events remain available.
- State hashes across schema migrations must include the effective schema and administrative context. Migrations cannot reinterpret old records silently.
- Bounded growth is a doctrine risk: compression, aggregation, and purge policies can hide truth loss unless causal anchors and lineage boundaries are explicit.

---

## 4. Canonical Record Taxonomy

| Record category | Canonical? | Can mutate world state/time? | Creator | Replay consumes? | Rebuildable? | Compressible? | Required provenance |
|---|---|---:|---|---:|---:|---:|---|
| `KernelRun` | Yes, administrative root | No | Core | Yes | No | No | run identity, seed policy, schema registry, engine context, lineage origin |
| Proposal | Canonical audit if normalized/retained | No | Domain/external via Core normalization | No for event replay; yes for resimulation audit | No | Yes, by audit policy | proposer, activation/input source, preconditions, touched scope, content hash |
| Rejected proposal | Canonical audit | No | Core | No for event replay; yes for explanation | No | Yes | proposal ref, reason code, state hash, conflict/staleness context |
| Accepted simulation event | Yes, world-truth history | Yes | Core | Yes | No | Raw event may compress only outside recent horizon | order, time, parents, mutation, scope, versions, post-state hash |
| Core administrative record | Yes, canonical administrative history | No | Core | Yes when effective | No | Superseded only by explicit admin record | type, effective boundary, authority, version, source policy |
| External influence record | Yes, canonical input/audit record | No by itself | Core normalization | Yes when referenced | No | Raw input may be hashed/redacted by policy; normalized accepted form must survive required horizon | source class, normalized payload, hash, acceptance/rejection refs |
| Receipt | Yes, canonical causal record | No | Core | Yes for reconstruction/explanation | No after it becomes retained evidence | May be superseded, not silently rewritten | coverage, anchors, source hashes, policy, effective boundary |
| Checkpoint | Yes as record; artifact valid by hash | No | Core | Yes | Artifact can be regenerated only while source horizon exists | Superseded by policy | event/admin range, state hash, schema hash, lineage, included receipts |
| Projection record | Derived record, not truth | No | Projection service under Core policy | No for truth; yes for projection rebuild validation | Yes | Disposable unless checkpointed | source declaration, source hashes, version, observer/scope, dirty rules |
| Entity record | Yes as canonical state container | No independently | Core via accepted events | Yes as state/checkpoint input | Rebuildable within horizon | Via checkpoint/receipt policy | origin event, type, identity, acquired-state causes, state hash |
| Migration/import boundary record | Yes, administrative | No | Core | Yes | No | Superseded only explicitly | source material, classification, limits, effective boundary, lineage impact |
| Lineage/branch record | Yes, administrative | No | Core | Yes | No | No | parent lineage, fork/import/checkpoint boundary, reason, effective point |

Not every record uses one envelope. All canonical records need deterministic identity, version context, provenance, and hash semantics, but record shapes may differ to avoid false equivalence.

---

## 5. Accepted Simulation Events

An accepted simulation event is the only record that may mutate canonical world state or simulation time.

| Field / concern | Constitutional necessity? | Notes |
|---|---:|---|
| Event identity | Yes | Deterministic, content-addressed or equivalent stable identity. |
| Event family | Yes | Required for validation, storage, projection invalidation, and bounded growth. Exact taxonomy may evolve. |
| Event type | Yes | Specific mutation type. |
| Simulation time | Yes | Core-owned simulated time at event boundary. |
| Deterministic order | Yes | One total order for simulation events within a lineage. |
| Causal parents | Yes for non-genesis/non-exogenous effects | Must explain durable consequence. |
| External influence reference | Required when caused by external influence | References normalized durable input record. |
| Touched scope | Yes | State paths/entities/resources/regions affected. |
| Preconditions | Yes | Revalidated at commit; exact structure is schema-specific. |
| Mutation payload | Yes | Canonical mutation, not presentation text or projection cache. |
| Post-state hash | Yes for state/time mutation | Verifies result after commit. |
| Schema and engine versions | Yes | Must identify interpretation context. |

Replaceable schema decisions include exact field names, serialization format, hash algorithm, event-family naming, phase vocabulary, and payload structure.

---

## 6. Core Administrative Records

Core administrative records are canonical but do not mutate simulated world state or simulation time.

### 6.1 Administrative Record Taxonomy

| Administrative record | Purpose | Effective boundary required? |
|---|---:|---|
| Schema activation | Defines schema availability/meaning from boundary forward | Yes |
| Engine-version activation | Defines compatible engine behavior from boundary forward | Yes |
| Storage horizon change | Changes retention/compression policy | Yes |
| Checkpoint creation | Authorizes checkpoint record/artifact | Yes |
| Receipt creation | Authorizes receipt as canonical causal record | Yes |
| Receipt supersession | Replaces receipt validity without rewriting it | Yes |
| Compression policy application | Defines compression coverage and anchors | Yes |
| Projection invalidation | Marks derived views dirty/unusable | Yes |
| Migration/import boundary | Records provenance, limits, lineage implications | Yes |
| Compatibility representation | Defines derived view over older records without changing them | Yes |
| Lineage creation/fork | Defines branch ancestry | Yes |
| Archival authorization | Moves records across storage classes | Yes |
| Purge authorization | Permits deletion only under declared policy | Yes |

### 6.2 Administrative Record Rules

No administrative record may retroactively alter the canonical meaning of an already accepted record. Changed interpretation requires a migration boundary plus a new lineage, new accepted records, or a clearly derived compatibility representation.

---

## 7. Proposal And Rejection Truth

### 7.1 Core Principles

A proposal is intent, not world truth.

Before acceptance, a proposal has no canonical world effect. After Core normalization, it may become a Core-owned audit record if retained by policy.

Rejected proposals are audit truth: they prove that a request was considered and rejected. They do not prove that anything happened in the world.

### 7.2 Required Rejection Properties

- deterministic rejection identity
- proposal reference
- rejection stage
- stable reason code
- state hash or boundary used for validation
- conflict or staleness references where relevant
- bounded reason detail

### 7.3 Conflict and Staleness

Conflict and staleness records explain why a proposal lost. If losing has simulated consequences, those consequences require accepted simulation events.

### 7.4 Retention Policy

Proposal retention is policy-bound. Within the recent audit horizon, normalized proposals and rejections should be retained. Beyond that, they may compress into receipts or administrative audit summaries if not needed for world replay.

---

## 8. External Influence

### 8.1 Core Principle

External influence becomes replay-safe only through Core normalization and durable recording.

### 8.2 Required Flow

1. Receive external input.
2. Normalize to canonical form.
3. Assign deterministic identity.
4. Record durable ExternalInfluenceRecord.
5. Validate authority, scope, schema, bounds, and causality.
6. Produce proposal or rejection.
7. If accepted and state-changing, commit accepted simulation event referencing the influence record.
8. During replay, read the recorded accepted influence. Do not request it again.

### 8.3 Paired Model

**Recommendation:** use the paired model. ExternalInfluenceRecord is canonical input/audit truth. Accepted simulation events reference it when it causes world-state or time mutation. Administrative records may reference it for import assessment or migration decisions.

---

## 9. Receipts

### 9.1 Core Principle

Receipts are Core-authorized canonical causal records.

### 9.2 Permitted Purposes

- compression
- explanation
- audit
- deep reconstruction
- acquired-state causality
- projection rebuild support
- idempotence evidence
- conflict explanation
- observer/scope access causality where relevant

### 9.3 Required Receipt Properties

- receipt identity
- receipt type
- Core authorization
- covered event IDs or ranges
- causal anchors
- covered scope
- source state hash
- source admin/schema context hash
- compression policy and version
- receipt payload hash
- supersession policy

### 9.4 Receipt Restrictions

Receipts must not become:
- mutable state
- event substitutes inside the recent replay horizon
- hidden domain storage
- unexplained summaries
- projection-only facts
- authority for new mutation

### 9.5 Supersession

Receipt supersession requires a Core administrative record. Receipts are never silently rewritten.

---

## 10. Checkpoints

### 10.1 Two-Part Structure

A checkpoint has two parts:

| Part | Status |
|---|---|
| CheckpointRecord | Canonical administrative/causal record |
| CheckpointArtifact | Core-authorized artifact valid only if hashes and context match |

### 10.2 Required Checkpoint Properties

- checkpoint identity
- lineage
- source event range
- source administrative boundary range
- canonical state hash
- schema registry hash
- engine/version context
- included receipt IDs
- storage horizon policy
- replay/reconstruction mode
- creation boundary
- validity status
- supersession reference if replaced

### 10.3 Checkpoint Usage

Checkpoints accelerate replay or reconstruction. They do not independently mutate world state. A checkpoint can be a replay starting point only when valid for the requested lineage, schema context, and storage horizon.

---

## 11. Projections

### 11.1 Definition

A projection is a derived computational view over declared canonical sources.

### 11.2 Required Projection Properties

- projection name
- projection version
- source declaration
- source state hash
- source event dependencies
- source receipt dependencies
- checkpoint dependency if any
- observer or scope identity where relevant
- projection payload hash
- dirty conditions
- rebuild policy
- invalidation boundary
- disposal policy

### 11.3 Projection Restrictions

A projection must not:
- introduce facts absent from canonical records
- become the sole causal origin of a proposal
- substitute for required canonical provenance
- remain usable when source hash, version, or validity cannot be established
- repair itself by mutating truth

Domain engines may receive projections only as reproducible views over declared canonical sources.

---

## 12. Entity Truth

### 12.1 Core Principle

Entity truth is general-purpose. It must support people, ecology, weather systems, disease, economy, settlements, factions, objects, regions, processes, stocks, and flows.

An EntityRecord is a canonical state container, not an independent mutation source. It is updated only by accepted simulation events and may be rebuilt or reconstructed within declared horizons.

### 12.2 Required Entity Properties

- entity identity
- origin event
- entity type
- lineage/scope
- stable identity payload
- base state
- acquired state
- causal references for acquired state
- lifecycle/status
- aggregation state
- promotion/demotion history
- merge/split references
- retirement/deletion event
- entity state hash

### 12.3 Entity Rules

Base state may originate at genesis/import/creation events. Acquired state must be event-backed. Aggregation may reduce resolution but cannot erase required causal anchors.

---

## 13. Time, Ordering And Lineage

### 13.1 Core Concepts

Simulation time is Core-owned. Event order is Core-owned. Lineage is Core-owned.

| Concept | Meaning |
|---|---|
| Simulation time | In-world time value. |
| Event order | Deterministic total order of accepted simulation events within a lineage. |
| Administrative effective boundary | Where admin records affect interpretation or replay. |
| Commit frame | One Core execution frame that may accept/reject proposals and create admin records. |
| Run identity | Kernel run root. |
| Branch/fork identity | New lineage derived from parent boundary. |
| Migration lineage | New or continued lineage with explicit import/migration boundary. |
| Replay boundary | Start point for event replay or reconstruction. |

### 13.2 Ordering Model

**Recommendation:** separate ordered domains with explicit effective boundaries, plus an optional unified storage journal/index. Simulation events have a deterministic total order. Administrative records have deterministic effective boundaries relative to that order and lineage. Replay must never face ambiguity about which administrative context applies to an event.

### 13.3 Fork Doctrine

Forks preserve absolute simulation time.

Child genesis occurs at the fork tick, not tick zero.

Forks preserve the parent’s deterministic RNG continuation context at the fork boundary, including seed, namespace, policy, absolute simulation tick, and next deterministic ordering index.

A fork creates a fresh deterministic child lineage and event stream.

Parent events are referenced, not copied into the child event stream.

The child begins from a snapshot-derived fork genesis record.

Replay must support non-zero genesis ticks.

UUIDs, database IDs, and timestamps must not affect canonical identity.

Fork creation must be atomic. A failed fork operation must leave neither a partial child lineage nor partial fork records.

Parent and child canonical hashes may differ because lineage metadata differs.

Snapshot content equivalence and fork provenance should be verified separately.

Branch/fork lineage preserves causal honesty by recording parent lineage, fork boundary, checkpoint/event source, and any changed policy. A branch is not a rewrite of its parent.

---

## 14. State Hashing

### 14.1 Core Principle

Canonical state hashes must be stable across storage placement and runtime representation.

### 14.2 Included in Canonical State Hash

- canonical world state values
- simulation time
- lineage identity
- last applied event boundary
- active schema/version context
- effective administrative context needed for interpretation
- deterministic numeric normalization
- canonical ordering of maps/sets/lists where semantically ordered

### 14.3 Excluded from Canonical State Hash

- database object IDs
- collection/table/file names
- insertion time
- wall-clock timestamps
- replication metadata
- cache location
- projection caches
- diagnostics
- operator notes
- physical compression encoding
- incidental runtime object identity

### 14.4 Hash Usage

Storage policy and projection validity may have their own hashes. A replay trace may combine world state hash plus administrative context hash, but these should remain distinguishable.

Across schema migrations, the original record hash remains tied to original canonical meaning. A migrated representation receives its own compatibility or lineage hash.

---

## 15. Storage Metadata Boundary

### 15.1 Core Principle

Storage metadata is not canonical meaning.

### 15.2 Noncanonical Storage Metadata Includes

- database object IDs
- physical collection
- file path
- compression encoding
- insertion time
- replication metadata
- cache location
- operator notes
- index placement
- backup location
- storage engine internals

### 15.3 Usage

Storage metadata may help operations, auditing, or recovery. It cannot alter canonical interpretation, event order, schema meaning, lineage, or replay result.

---

## 16. Import And Legacy Truth

### 16.1 Classification

Legacy material is not kernel-native history.

| Class | Meaning |
|---|---|
| Observation archive | Rendered/history material only. No replay claim. |
| State snapshot | Candidate state evidence. No past event claim. |
| Checkpoint import | Imported state becomes a replay/reconstruction boundary. |
| Synthetic genesis | Imported material seeds a new lineage start. |
| Hybrid shadow lineage | Kernel records begin alongside old runtime; replay starts at first valid kernel boundary. |
| Quarantine | Material is inconsistent, unsafe, or ambiguous. |
| Archive only | Preserved for reference, never canonical input. |

### 16.2 Rules

State-changing imports require accepted simulation events.

Import assessment, provenance, classification, compatibility, limitations, and migration-boundary metadata are Core administrative records.

Legacy material must not overclaim historical causality. An export or snapshot may justify an import assessment, but it is not proof of accepted simulation-event history.

---

## 17. Compression And Horizon Truth

### 17.1 Retention Modes

Three retention/reconstruction modes must remain distinct:

| Mode | Guarantee |
|---|---|
| Recent byte-exact replay | Raw accepted events and effective admin context reproduce exact canonical state hashes. |
| Deep causal reconstruction | Checkpoints, receipts, retained anchors, and later events reconstruct current causal truth, not every intermediate event. |
| Observation/archive retention | Human-readable or external artifacts only; not simulation replay. |

### 17.2 Truths That Survive Compression

When persistent, the following must survive compression:
- identity
- acquired state
- lifecycle state
- relationships
- ownership
- injuries
- standing
- persistent resources
- causal anchors
- lineage
- schema meaning
- import limitations
- storage horizon boundary
- receipt/checkpoint provenance

### 17.3 Compression Rule

Compression may reduce event detail outside the recent horizon. It cannot silently remove the evidence required to explain current persistent truth.

---

## 18. Invalid And Forbidden Truth Sources

Canonical truth must not depend on:
- generated prose
- external display state
- projection caches
- diagnostics
- unordered database reads
- wall-clock timing
- unrecorded environment configuration
- random UUID generation
- unseeded randomness
- mutable hidden domain state
- legacy exports
- filesystem paths
- current network state
- storage insertion order
- operator notes
- cache contents

Any data from these sources must enter only through explicit recorded influence, import assessment, projection, or administrative policy as appropriate.

---

## 19. Invariants

1. One mutation authority: only Core-accepted simulation events mutate canonical world state or simulation time.
2. No accepted simulation event lacks deterministic identity.
3. No accepted simulation event lacks deterministic order.
4. No state-changing import occurs without accepted simulation events.
5. No non-genesis durable consequence lacks causal provenance.
6. No external influence affects truth unless normalized, recorded, validated, accepted, and replayed from record.
7. No domain engine writes canonical storage.
8. No proposal is world truth before acceptance.
9. No rejected proposal mutates world state.
10. No receipt exists without Core authorization.
11. No receipt replaces accepted events inside the recent replay horizon.
12. No checkpoint is valid without source event/admin ranges and hashes.
13. No projection is valid without rebuild provenance.
14. No projection introduces noncanonical facts.
15. No projection is the sole causal origin of a proposal.
16. No administrative record lacks deterministic effective boundary when replay-relevant.
17. No administrative record retroactively changes accepted record meaning.
18. No canonical hash depends on storage metadata.
19. No replay depends on external services.
20. No schema migration silently strengthens legacy or old records.
21. No branch/fork rewrites parent lineage.
22. No compression erases required causal anchors.
23. No storage purge occurs outside explicit Core policy.
24. No current state is accepted if its post-state hash cannot be reproduced.
25. No bounded-growth policy may hide truth loss as optimization.

---

## 20. Appendices

### 20.1 Open Decisions

Decisions requiring approval:

| Decision | Recommendation |
|---|---|
| External influence model | Approve paired ExternalInfluenceRecord plus accepted event reference. |
| Rejected proposal status | Approve canonical audit record, not canonical world history. |
| Checkpoint status | Approve split CheckpointRecord plus hash-bound CheckpointArtifact. |
| Entity record status | Approve canonical state container updated only by events. |
| Ordering model | Approve separate ordered domains with deterministic admin effective boundaries. |
| Deep reconstruction wording | Use "deep causal reconstruction," not byte-exact replay. |
| Minimum recent horizon | Needs policy set. |
| Minimum deep reconstruction horizon | Needs policy set. |
| Receipt requirement scope | Decide which event families require receipts. |
| Administrative record taxonomy | Approve initial taxonomy above. |
| Import classes | Approve listed classifications or revise names. |
| Migration lineage rules | Decide when import creates new lineage versus compatibility representation. |
| Canonical hash profile | Approve world-state hash versus administrative-context hash split. |

### 20.2 Material Deferred To Architecture v2

- Core process/module/service layout.
- Commit pipeline mechanics and transaction boundaries.
- Exact event order-key algorithm.
- Exact schema registry implementation.
- Exact record envelope and field names.
- Storage backend, collections, indexes, and transaction strategy.
- Checkpoint artifact serialization.
- Projection scheduler and cache invalidation implementation.
- Domain activation scheduler.
- Branch/fork command mechanics.
- Migration tooling.
- Verification harness implementation.
- Performance budgets and concrete caps.

---

## 21. Strict Verdict

Ready for architecture review.

No known blocking contradiction remains in the canonical truth model. Open policy decisions remain explicitly listed and must not be treated as settled doctrine.