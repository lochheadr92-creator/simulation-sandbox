# Capability Stage 7A — Emergent Association and Group Recognition

Status: implemented and acceptance-verified on 2026-07-13.

Stage 7A recognises bounded canonical social structures from accepted history.
It does not give those structures agency. Core remains the only mutation and
acceptance authority; the association domain observes a pinned frame and emits
proposals only.

## Authority and integration

1. Accepted person actions and committed spatial/resource conditions are the
   only association evidence inputs.
2. Every evidence item names exactly two people, a fixed category, an integer
   contribution, a simulation tick, and accepted-event provenance.
3. The association domain proposes a complete next registry revision. Core
   validates schema, identity, membership, bounds, payload size, and revision.
4. Core stamps the accepting event onto formation, recognition, membership,
   weakening, expiry, and dissolution transitions before applying the generic
   mutation envelope.
5. Replay applies the accepted mutation through `apply_mutation`; there is no
   association-specific storage or replay path.

## Canonical schemas

One `association-registry-v1` entity contains:

- bounded pairwise `association-evidence-v1` summaries;
- bounded `group-candidate-v1` candidates and recognised groups;
- bounded compact dissolved/expired history;
- a bounded processed-evidence identity window; and
- an integer revision used for deterministic conflict rejection.

Pair and candidate identities are SHA-256 content derivatives. Inputs are
sorted person ids, schema version, founding evidence, and first-supported tick.
They never include UUIDs, wall-clock time, database order, proposal arrival
order, or mutable sequence numbers.

## Evidence categories and weights

Positive categories, from strongest to weakest, are caregiving, shared shelter,
resource sharing, mutual protection, cooperation, shared storage, coordinated
travel, dependency, coordinated action, and proximity. Conflict and sustained
separation weaken an association.

Proximity contributes only enough to maintain a supported association; normal
per-tick decay cancels proximity-only accumulation. It cannot independently
form a household or recognised group.

Detailed evidence is capped. Older detail collapses into integer category
scores, support counts, first/last support ticks, and bounded decisive accepted
event references. Accepted events remain the durable causal spine.

## Candidate and recognition lifecycle

- One interaction is below candidate creation threshold.
- A pair becomes a candidate only after multiple supported ticks and sufficient
  non-proximity strength.
- Recognition requires greater strength, at least three distinct support ticks,
  and persistence across time.
- `household_like` requires caregiving, shared-shelter, or dependency evidence.
- `travelling_working` requires coordinated travel, cooperation, coordinated
  work, or shared-storage evidence.
- Other qualifying structures remain `persistent_association`.
- A member may join only when qualifying pair evidence connects that person to
  every current member. Member order never affects the result.
- Unsupported added members are removed after a grace period. Founding pairs
  weaken and dissolve as a structure rather than being silently rewritten.
- Candidates expire after their shorter grace period. Recognised structures
  weaken first and dissolve only after a longer grace period.

## Explicit bounds

- association records: 48 globally, 8 per person;
- evidence categories: 10 fixed positive categories plus 2 weakening kinds;
- detailed evidence: 8 items per pair;
- accepted-event references: 16 per pair/candidate;
- candidates/recognised groups: 24;
- members per candidate: 8;
- dissolved/expired summaries: 8;
- processed evidence identities: 96; and
- evidence items / causal parents per proposal: 64 / 32; and
- association proposal canonical JSON: 128 KiB.

Deterministic ranking prunes weakest/oldest pair records first while enforcing
the per-person cap. Detailed dissolved history is intentionally compact because
accepted events preserve the full durable record.

## Diagnostics

The read-only association projection explains current state, inferred type,
members, strength, decisive categories/events, membership support, weakening,
removal, expiry, and dissolution. Diagnostics are not consumed by any domain.

## Stage 7B boundary

Stage 7A groups cannot choose actions, create goals, own inventory, elect
leaders, enforce obedience, merge wants, replace pair relationships, create
culture, govern settlements, wage war, or accept player commands. Those remain
future Stage 7 work and require separate contracts.

## Verified acceptance evidence

- Focused Stage 7A suite: 22 passed.
- Live Mongo concurrency module: 3 passed, including one-head/one-frame
  concurrent Stage 7A stepping with unique candidate identities.
- Broad backend regression: 231 passed, 0 failed, 0 skipped; the four existing
  Docker-path API modules requiring `/app/frontend/.env` were excluded at
  collection as a separate test-configuration limitation.
- Two independent 320-tick `emergent_groups` traces matched accepted-event
  hashes, frame hashes, final canonical state, entities, and full summaries.
  A final third 320-tick trace after validation tightening reproduced the same
  final hashes and counts.
- Final canonical state hash:
  `4016f097c3bab6ff1fd9590c5e46731144dff1f6e5c868910c5a0da3bb4ec4e2`.
- Final association summary hash:
  `01af6144c2fdaac92fe4b451cb12ffffaae7976fdf29d6f78f16581132185701`.
- Per 320-tick trace: 4,708 accepted events, 1,394 rejected proposals, 28 final
  association records, 9 final candidates, and 9 recognised groups.
- Observed maxima: 28 association records, 9 candidates, 0 retained dissolved
  summaries, and 128,981 registry bytes. Focused lifecycle tests separately
  prove weakening, member removal, candidate expiry, and recognised dissolution.
- Long-run time was 794.8 seconds for the two-run comparison and 389.8 seconds
  for the final single-run confirmation. Full canonical snapshot hashing remains
  the dominant known runtime cost; it did not cause unbounded state growth.
