# CORE-INTEGRITY-004 — commit order is content-derived, and content includes provenance

**Status: OPEN. CONFIRMED by pre-registered experiment 2026-07-26/27.**
This is the finding that explains this week's unattributable deltas.

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
