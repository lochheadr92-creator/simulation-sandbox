# Capability Stage 7B - Bounded Shared Group State

Status: Stage 7B baseline and Stage 7B.1 capacity hardening acceptance-verified
on 2026-07-13.

Stage 7B proves that a recognised Stage 7A group can have bounded canonical
shared state and can participate in a narrow collective-proposal contract
without becoming an autonomous group agent.

## Authority and integration

1. Stage 7B reuses the existing Core authority path:
   proposal, deterministic ordering, Core validation, precondition
   revalidation, accepted mutation, canonical hashing, atomic frame
   persistence, replay.
2. The group-state domain is proposal-only. It reads a pinned frame and never
   mutates storage or canonical entities directly.
3. The accepted Stage 7A association registry event is the Core causal parent
   for Stage 7B proposals. Detailed participant event ids remain bounded
   provenance inside the support metadata and shared fact.
4. Core validates the proposed complete next shared-state registry revision and
   stamps the accepting event into facts and collective-proposal records before
   applying the generic mutation envelope.
5. Replay applies the accepted mutation through `apply_mutation`; there is no
   Stage 7B-specific replay or persistence path.

## Canonical schemas

One `group-shared-state-registry-v1` entity contains:

- bounded `shared-group-state-v1` rows keyed by recognised group id;
- bounded `shared-group-fact-v1` facts per group;
- bounded `group-support-evidence-v1` support history per fact;
- bounded retained `collective-group-proposal-v1` summaries; and
- a bounded processed-proposal-key window for duplicate suppression.

The only implemented shared fact categories are:

- `shared_shelter`;
- `shared_storage`.

The facts record shared use/participation evidence only. They do not create
group inventory, goals, leadership, obedience, authority, governance, politics,
culture, warfare, diplomacy, or player control.

## Collective proposal rule

A Stage 7B collective proposal is valid only when all of these are true:

- the referenced Stage 7A group currently exists and is recognised;
- the support names exactly two current living group members;
- the support category is one of the two Stage 7B categories;
- the support target is an existing shared/public shelter or storage entity;
- the support is present in the current association registry as accepted
  Stage 7A evidence;
- the support carries at least two non-genesis accepted event ids;
- the support is fresh under the Stage 7B freshness window;
- the association registry revision and group-state registry revision still
  match the proposal preconditions at commit time; and
- the deterministic proposal key has not already been processed.

Recognition alone is insufficient. Membership alone is insufficient. A target
or neighbour is not silently treated as a supporter.

## Individual agency boundary

Stage 7B proposals may mutate only `group-shared-state-000`.

They cannot mutate person state, move resources, spend inventory, command
members, create group goals, or override individual validators. If a future
proposal affects individual canonical state, it must use the existing
individual-authority semantics or be rejected as outside Stage 7B.

## Explicit bounds

- shared groups: 16;
- facts per group: 8;
- support history per fact: 8;
- participants per support: 8;
- provenance references per fact/support: 16;
- retained collective proposal summaries per group: 12;
- processed proposal keys: 96;
- support items per proposal: 16;
- causal parents per proposal: 32;
- group-state proposal canonical JSON: 64 KiB.

Stage 7B.1 does not raise either hard cap. It adds operational compaction
targets of 96 KiB for association state and 48 KiB for group state, leaving a
25% target reserve. Under pressure, redundant per-group collective-proposal
summaries compact before fact-local support history. At least one latest
proposal summary per retained group and one support-history row per retained
fact survive. The processed proposal-key window remains 96 except for the
pre-existing last-resort hard-cap fallback.

Stage 7A recent evidence now uses a shorter canonical representation containing
only fields that cannot be reconstructed from its enclosing pair record.
Category summaries retain two category-specific event references while each
record still retains sixteen aggregate causal references and each recent item
retains its source events. This preserves current scores, group recognition,
Stage 7B support validation, and causal traceability while removing repeated
pair/schema/weight fields and duplicated per-category history.

These caps are independent of Stage 7A's 128 KiB association proposal ceiling.
The Stage 7A association registry remains a separate canonical entity with its
own validator and payload cap.

## Scenario and diagnostics

Stage 6 `living_settlement` and Stage 7A `emergent_groups` activation are
unchanged. Stage 7B uses the explicit `collective_groups` scenario, which adds
only the `group_state` domain after Stage 7A.

The read-only `/runs/{run_id}/group-state` projection exposes group ids,
current shared facts, revisions, participants, compact provenance, latest
collective proposal summaries, diagnostics, and caps. It never mutates state.

## Verified local evidence

- Focused Stage 7B suite: 24 passed.
- Focused Stage 7A + Stage 7B: 46 passed.
- Affected Stage 6/7 regression set: 69 passed.
- Live Mongo concurrency module: 4 passed, including concurrent Stage 7B
  stepping with one head advance, one frame, and no duplicate shared facts.
- Broad backend regression: 256 passed with only the four known Docker-path API
  modules excluded.
- Two independent 320-tick `collective_groups` traces matched accepted-event
  hashes, frame hashes, final canonical state, entities, and full summaries.
- Final canonical state hash:
  `86a7dc7fa994d95d6c8c7016ddc127bf7f9d6f7d7b34eb610769a8dcb05482df`.
- Final association summary hash:
  `e286f69d8e3baa60289c014681c9c60f2279b6a1f3c72ff413aaf623e6d7a550`.
- Final group-state summary hash:
  `aab2c7565d74d0747f28c544e75701afc54661b706cf1c6a8f9072b27d603fae`.
- Per 320-tick trace: 4,844 accepted events, 1,407 rejected proposals, 137
  accepted `update_group_shared_state` events, 28 final association records, 7
  final recognised groups, 7 final shared group states, and 10 final shared
  facts.
- Observed maxima: 28 association records, 7 association candidates, 0 retained
  dissolved groups, 128,994 association registry bytes, 7 shared group states,
  10 shared group facts, 96 processed group-state proposal keys, and 63,466
  group-state registry bytes.

Long-horizon Stage 7B acceptance uses the `collective_groups` scenario and
reports separate Stage 7A association growth and Stage 7B group-state growth.

Stage 7B.1 diagnostics partition canonical bytes exactly into current truth,
historical/support evidence, processed identities, retained proposal summaries,
provenance references, and structural overhead. The partition is read-only and
is never consumed as canonical truth. The harness also records peak tick and
headroom, capacity rejection reasons, retained-history counts, replay equality,
restart-boundary repeat equality, and current-truth changes after tick 320.

## Stage 7B.1 acceptance evidence

- The pre-change 320-tick `stage7b-acceptance` trace reproduced the supplied
  final hash exactly before editing. Association records consumed 105,049
  bytes, including 51,498 bytes of recent full evidence and 35,293 bytes of
  category summaries. Group rows consumed 59,017 bytes, including 35,218 bytes
  of duplicated proposal summaries.
- A post-change trace with the same seed preserved all semantic counters:
  4,844 accepted events, 1,407 rejected proposals, identical action/event-type
  counts, 28 association records, 7 recognised groups, 7 shared-group states,
  and 10 shared facts. Peak registry bytes fell from 128,994 to 97,141 for
  association state and from 63,466 to 49,335 for group state.
- Two independent 1,000-tick `collective_groups` traces with seed
  `stage7b1-capacity` matched accepted-event hashes, frame hashes, final
  canonical state, final entities, summaries, and retained-history
  composition. The second trace reconstructed state and RNG at tick 320.
- Final state hash:
  `31f27b2c15be45d76946b898c0d0dcd791edfe49ce52b49758a0b2517b686d89`.
  Accepted-event sequence hash:
  `7e316ea6b2beffa3fc1370dda72aafb74f69007fb0c53279058c53b151a37d52`.
  Frame sequence hash:
  `055bbe6e6956d80895bb39eccaba72cd5f7799f5f9b0c69089ae9acc926a6656`.
- Association peak was 95,628 / 131,072 bytes at tick 540, leaving 27.042%
  headroom. Group-state peak was 49,374 / 65,536 bytes at tick 37, leaving
  24.661% headroom. No proposal was rejected for either payload cap.
- The trace accepted 9,351 events and rejected 3,859 proposals. Current
  association truth changed on 401 ticks after tick 320, from tick 321 through
  tick 728. Shared-fact truth remained stable after tick 320 because the seed
  produced no new valid shared-fact support, not because capacity rejected it.
- Final retained history comprised 168 recent association evidence rows, 96
  processed evidence ids, 72 fact-local support rows, 12 group-level proposal
  summaries, and 96 processed group proposal keys.
- Focused Stage 7A/7B tests passed 50; Stage 6C through 7B regressions passed
  73; live Mongo concurrency passed 4; and the broad backend gate passed 260
  tests with one existing warning and only the four documented Docker-path API
  modules excluded.

## Stage 7C boundary

The Stage 7B.1 capacity prerequisite is cleared. Stage 7C is contracted
separately as a **read-only consumer of Stage 7B shared facts** that enables
one narrow multi-member deposit behaviour; see
[`CAPABILITY-STAGE-7C-GROUP-COLLECTIVE.md`](CAPABILITY-STAGE-7C-GROUP-COLLECTIVE.md).
Leadership, voting, governance, obedience, group-owned inventory, collective
goals, warfare, diplomacy, culture, religion, politics, and player control
remain out of scope until separately contracted.
