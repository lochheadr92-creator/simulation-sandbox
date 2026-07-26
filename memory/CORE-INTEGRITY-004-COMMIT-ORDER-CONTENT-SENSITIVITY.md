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
spec; genesis priorities are currently uniform `None`, so nothing is clobbered).
Re-billed honestly: it stabilises provenance for **unedited** entities and
removes the `None`-vs-`int` comparison trap. **It does not make an edited
entity's stage attributable** — event ids embed content `hash8`, so a changed
person spawn id still enters proposals as a causal parent and still perturbs
ordering.

**Residual property, not a solved problem:** a positional index stabilises
ordering against *content* changes, not *composition* changes. Appending an
entity is free; **inserting mid-spec still renumbers everything after it**.

## Debt carried

**Per-parameter-per-entity RNG keying was authorised; only per-parameter is
implemented** (`world/generator.py`). With per-parameter streams, adding a
person still shifts every later person's draws. The per-entity half is owed
**before Stage 11 changes population counts**.
