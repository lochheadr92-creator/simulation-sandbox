# CORE-INTEGRITY-004 — commit order is content-derived, and content includes provenance

**Status: OPEN. CONFIRMED by pre-registered experiment 2026-07-26/27.**
This is the finding that explains this week's unattributable deltas.

## VERBATIM EVIDENCE — transcribed across a context boundary

The scalpel probe is **gitignored**; these numbers existed nowhere durable and
are transcribed here verbatim so the finding survives without them.

```
SCALPEL: in-process monkey-patch replacing the content_hash tie-break with
         (entity_id, proposal_type). Core untouched, probe gitignored.

CONTROL PASS: 6,198 invocations run A; 12,396 total (strictly increasing)

BAND_A (657000, 2007500): accepted=4620  rejected=1578
BAND_B (700000, 1500000): accepted=4620  rejected=1578
Delta: 0.  Action mix: identical, every type.

SAME BANDS UNDER THE REAL TIE-BREAK (Gate 1):
  accepted             -61 (~1.2%)
  living_rest          451 -> 325  (-28%)
  social_request_help  +51
  social_cooperate     -19
  social_repay         -22
  precondition.failed  +95
  causality.invalid_parent = 0 on BOTH sides
```

**Collision instrument INVALID.** Its `SEEN` map was module-level and never
reset between arms, so it reported 6,198 — exactly run A's invocation count.
**Do not cite it.** Moot for an identical result; it would have been
load-bearing on a "still moves" outcome, where collision-slot fallback ordering
is a competing explanation. **Requirement for any re-run: reset the map between
arms and log the resolved order within each collision slot in both arms.**

An earlier scalpel attempt ran **without** a positive control; its output was
never read, so it cannot have anchored this conclusion.

## The mechanism

`order_key` (`commit_pipeline.py:108`) is
`(requested_time, PHASE_RANK[phase], engine_priority, content_hash)`.
Within a tick, proposals routinely tie on the first three, so **`content_hash`
decides commit order**. And `content_hash` is computed over `core_fields`
(`:75-100`), which **includes `causal_parent_event_ids`** — event ids. Memories
also embed event-id lists inside pinned `living_agent` blobs
(`living_agent_social.py:127-128`).

Event ids embed a content-hash prefix. So:

> **Any perturbation to any committed event id propagates into commit ordering
> for the remainder of the run.**

Deterministic — same seed, same result, always — but **chaotic**: an
arbitrarily small content change relocates events in the order, and the
relocation compounds.

## The experiment (pre-registered, controls first)

Two `living_settlement` 320 runs differing only in `person_age_range`, both
bands entirely above `CHILD_MAX_AGE_TICKS` so no life_stage reclassification
confounds the comparison.

**Unpatched** (`world_gen` sub-streams already isolating genesis *values*):

```
accepted 4925 -> 4864   (-61, ~1.2%)
living_rest  451 -> 325 (-28%)
social_request_help 116 -> 167   social_repay 56 -> 34
```

**Patched** — `content_hash` replaced by `(entity_id, proposal_type)` in the
tie-break, as an in-process monkey-patch in a gitignored scratch probe. Core
source never edited:

```
POSITIVE CONTROL: 6,198 invocations run A, 12,396 total  -- PASS
BAND_A accepted=4620 rejected=1578
BAND_B accepted=4620 rejected=1578
accepted delta: 0        action-mix differences: NONE
```

**Identical.** With ordering made content-independent, a change that previously
moved `living_rest` by 28% moves nothing at all.

### What this confirmed and what it killed

- **CONFIRMED:** content-hash ordering is the *only* live channel by which the
  age band reaches behaviour.
- **KILLED in the same run:** the competing hypothesis of a live RNG path
  (`empty_living_agent_state(person_id, 0, rng)` taking the top-level stream).
  No RNG audit was needed.
- **Subsumes** the abandoned forced-ordering test — the patch pins genesis and
  runtime ordering through one pipeline. That test would not have
  discriminated anyway: spawn-event `hash8` differs by age regardless of order.

### Instrument defect, recorded rather than quoted

The collision counter in that probe was **broken**: its `SEEN` map was
module-level and never reset between runs, so every slot revisited in run B
registered as a collision — hence exactly 6,198, run A's invocation count. It
measures nothing and is not cited as evidence. It is moot here only because the
pre-registered rule made collisions relevant solely to a *"still moves"*
outcome, and the outcome was identical.

An earlier scalpel attempt ran **without** a positive control. Its output was
never read, so it cannot have anchored this conclusion.

## Consequence — statistical gates become the default

**Gate 1 is the first measured ordering-noise magnitude: `living_rest` ±28%,
accepted count ±1.2%.**

| | Affected? |
|---|---|
| Byte-identical hash gates | **No.** Same input, same output, always |
| repeat / replay / resume equality | **No.** Determinism is intact |
| Single-run A/B action-count deltas | **YES — untrustworthy at this scale** |
| Upkeep (Variety Leg 1) | **Stands** — it replicated across scenarios *and* seeds, which ordering noise does not survive |

Any single-run behavioural comparison carries ordering noise of roughly the
above magnitude. **Re-baselines need statistical gates by default, not as an
escalation.** A delta under ~30% on a single action type, from a single run,
is not evidence of a behaviour change.

## Hypothesis record — including the ones that failed

Kept in full deliberately: a record preserving only surviving predictions is
one nobody should trust.

| Hypothesis | Raised | Outcome |
|---|---|---|
| Genesis ordering is content-derived and reshuffles on any content change | STOP report, **before** this run | **CONFIRMED** |
| The delta was a `causality.invalid_parent` cascade | same STOP report | **REFUTED** — zero occurrences either side |
| Keyed sub-streams fix the coupling | mine, this session | **REFUTED** — values isolated, behaviour still moved |
| Gate 1 verdict: ordering carrying meaning makes the spawn index *unsafe* | mine | **WRONG INFERENCE** — measurement sound, conclusion inverted. A live ordering channel makes freezing the genesis door load-bearing, not unsafe |
| Gate 1 stop-rule, and endorsing the forced-ordering test as discriminating | cloud session | **WRONG**, corrected **before** the result. Forced ordering could not discriminate: spawn-event `hash8` differs by age regardless of order, so both candidates predicted movement under it |
| "Stage 2 will be small and explicable" | cloud session | **WRONG**, corrected **before** the result. Event ids embed content `hash8`, so an edited entity's spawn id changes, enters proposals as a causal parent, and perturbs ordering — stage 2 lands at noise-floor order, not near zero |
| Genesis priorities are uniform `None`, and the index also removes a `None`-vs-`int` trap in `order_key` | this doc, pre-implementation | **WRONG on both counts**, caught by code-read **before** implementing. Priorities were uniform `-1`, and no proposal anywhere carries a present-but-`None` priority, so no `TypeError` was ever latent. The uniformity argument — and therefore the index's justification — survives; only the second billed benefit is struck. See the CORRECTION block above |
| Entropy would move materially under a pure resampling perturbation | implied by treating it as a gated statistic | **REFUTED as a worry.** Entropy moved −0.0043 bits while single counts moved up to ±72. Distribution *shape* is far more stable than any single count — recorded as the first entropy-noise datum |
| The `warn` regression is either (i) candidate generated-and-lost ⇒ displacement, or (ii) never generated ⇒ geometry | pre-registered fork, cloud session **and** mine, before the receipts | **BOTH WRONG — the fork was incomplete.** Decision receipts show a third outcome nobody listed: the candidate is generated, **wins** at ticks 1–2, and still never commits, because its plan is `['MOVE_TO_TARGET', 'WARN']` and the move is rejected `precondition.failed` (the scout is boxed in by campmates) until `REPAY_DEBT` replans it away. Neither selection-displacement nor geometry: **plan preemption.** Consequence caught before writing the test: a "sated scout ⇒ WARN_DANGER wins" fixture would have been **vacuous**, since winning is exactly what already happens organically. The fixture had to assert the action COMMITS, which required an adjacent target |
| My own first reading: the re-stream moved the entities, so the geometry broke | mine, mid-investigation | **WRONG**, corrected from the genesis dump within the same investigation. `living_settlement` pins all person positions and roles, the animal, storages, tools and shelters via `person_positions` / `person_profiles` / `extra_genesis_specs`. Only the 5 trees and the RNG-drawn needs actually moved |

Both corrections landed **pre-result**, which is what distinguishes them from
rationalisation. Recorded on both sides: predictions from the cloud session and
from the implementing session failed at similar rates.

## Remediation candidates — DEFERRED to a dedicated high-risk stage

**None of these enter the current leg.** All are Core surgery and all move
every hash once:

1. **Make the content-independent tie-break permanent** — the scalpel's
   `(entity_id, proposal_type)` in place of `content_hash`. Proven to remove
   the channel; needs a collision policy for the residual ties.
2. **Event ids without a content component** — drop `hash8` from
   `evt-{tick}-{order}-{hash8}`, so a changed payload no longer changes the id
   that other proposals cite as a causal parent.
3. **Provenance references out of `core_fields`** — exclude
   `causal_parent_event_ids` from the hashed set, so ordering stops depending
   on which events preceded.

## Remediation — not done, needs its own stage

The fix is to make commit order independent of content, e.g. an explicit
ordering key that does not derive from `content_hash`. That is Core surgery,
moves every hash once, and is **004's own stage** — not a rider on an age task.

**Interim, authorised separately:** a genesis spawn index (`engine_priority` per
spec). Genesis priorities were uniform, so nothing is clobbered — every genesis
proposal tied on the priority slot, which is precisely why `content_hash` was
deciding the order. Re-billed honestly: it stabilises provenance for
**unedited** entities, and that is its *only* benefit. **It does not make an
edited entity's stage attributable** — event ids embed content `hash8`, so a
changed person spawn id still enters proposals as a causal parent and still
perturbs ordering.

> **CORRECTION (2026-07-27, verified by code-read before implementing).** An
> earlier revision of this section said genesis priorities were uniform `None`
> and billed the index as also removing a `None`-vs-`int` comparison trap in
> `order_key`. **Both claims are false.** `core/kernel.py` set
> `"engine_priority": -1` on every genesis spawn proposal — uniform `-1`, not
> `None` — and a repo-wide search finds no proposal anywhere that carries a
> present-but-`None` priority, so `order_key`'s `.get(..., 100)` default is
> never defeated and no `TypeError` was ever latent. The uniformity argument
> survives unchanged (uniform `-1` ties just as uniform `None` would); only the
> second billed benefit is struck. Recorded rather than silently edited,
> because a finding doc that quietly drops a wrong claim is one nobody should
> trust.

**Residual property, not a solved problem:** a positional index stabilises
ordering against *content* changes, not *composition* changes. Appending an
entity is free; **inserting mid-spec still renumbers everything after it**.

### Spawn index — IMPLEMENTED 2026-07-27 (re-baseline leg, stage 1)

`core/kernel.py`, `GENESIS_SPAWN_PRIORITY_BASE + spawn_index` per genesis spec.
Landed with the genesis RNG sub-streams in one commit: sub-streams alone left the
ordering channel open, so the regression test for the RNG finding stayed red
without the index.

**Direct evidence of the channel, from the pre-registration run.** With only
`person_age_range` changed and the sub-streams already in place, the unedited
`animal-threat` entity moved:

```
creation_event_id   evt-0-12-3794366e  ->  evt-0-7-3794366e
```

`hash8` is **identical** (`3794366e`) — the animal's content never changed. Only
its slot moved, because eight people's edited ages changed their content hashes
and displaced it. That is this finding's mechanism isolated with zero value
confound, and it is why an unedited entity is the sharp probe rather than an
edited one.

Verified properties, each pinned by test in
`backend/tests/test_genesis_rng_isolation.py`:

- genesis commit order is identical across two different age bands (asserted
  content-independently, so it cannot pass by mirroring the id-assignment logic);
- `order_index == spec position` for every genesis event — holds only while every
  genesis proposal is accepted, so that is asserted too;
- genesis priorities are strictly increasing and remain below every domain
  priority.

`engine_priority` is **not** stored in the accepted event record
(`commit_pipeline.py`) — it only feeds the sort. So the index changes ordering
and nothing else.

**Post-implementation gate:** all four pre-registered bands passed; frozen
`living_settlement` 320 hash moved
`897f3f7f…3c5ab` → `48dfec2267b4ded7752a2f3fbdbee45a3ee6f69c8b1f62e19b6fe095741b1e3b`;
repeat / replay / resume all True. Full detail, including the first measured
entropy-noise datum, in
`memory/evidence/genesis-rng/SHARED-SPAWN-STREAM-2026-07-26.md` "Resolution".

## Debt carried

**Per-parameter-per-entity RNG keying was authorised; only per-parameter is
implemented** (`world/generator.py`). With per-parameter streams, adding a
person still shifts every later person's draws. The per-entity half is owed
**before Stage 11 changes population counts**.
