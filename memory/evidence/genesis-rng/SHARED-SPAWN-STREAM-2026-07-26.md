# FINDING — genesis parameter ranges are coupled through one shared RNG stream

**Status: OPEN. Needs authorisation to fix. CONFIRMED by code-read 2026-07-26.**
Found while attempting an age re-baseline; **not an age finding**. Ages were the
messenger.

## The defect

`world/generator.py:39` draws every genesis parameter from a single stream:

```python
spawn_rng = rng.stream("world_gen.spawn")
```

`DeterministicRNG.stream` (`core/rng.py:31-36`) returns a plain `random.Random`
seeded from `sha256(run_seed::name)`. `random.Random.randint(a, b)` routes to
`_randbelow(n)` with `n = b - a + 1`, which pulls
`getrandbits(n.bit_length())` inside a **rejection loop**.

So the entropy a single draw consumes depends on **the width of its range**:

| draw | n | bits per attempt |
|---|---|---|
| `randint(3000, 30000)` | 27,001 | 15 |
| `randint(657000, 2007500)` | 1,350,501 | 21 |

…plus a variable number of rejection iterations.

**Consequence: changing ANY genesis parameter's range silently redraws EVERY
subsequent value on that stream** — positions, hunger, thirst, energy, trees,
animals, tools. A one-line edit to one integer band produces a different
starting world.

**It is invisible in a diff.** Nothing in `person_age_range: (3000, 30000) ->
(657000, 2007500)` suggests that agent *positions* move.

## The module already warns about this

`core/rng.py:4-7`:

> a single global seed/stream is dangerous because adding one new random draw
> anywhere can shift every later draw ("adding flowers causes the king to die").
> Instead every call site asks for a NAMED stream.

The doctrine is correct and stated. `world_gen.spawn` then funnels every genesis
parameter through one named stream, reinstating the exact hazard *inside* it.
Named streams isolate call sites from each other; they do nothing for draws
sharing one name.

## Measured consequence

`living_settlement` 320, seed `living-agents-stage6`, changing only
`person_age_range`:

```
accepted events   5,004 -> 4,830   (-174, ~3.5%)
final_state_hash  897f3f7f...3c5ab -> b8d438ff1d45272decf2bd72864d8eef8bc4722070f63aee0e9c195a3a09bfc0
```

`causality.invalid_parent` appears **zero** times on either side — an earlier
hypothesis that this was a causal-parent cascade is **refuted**.

## Retroactive doubt — the reason this matters beyond ages

Any past claim that a scenario edit was hash-neutral, or that a hash movement
was attributable to the edited behaviour, is only sound if the edit did not
change a draw width on a shared stream. Adding an entity, moving a position, or
widening any range could have redrawn the world underneath the change being
measured. **Past attributions of this kind should be re-examined rather than
trusted.** No specific prior claim is alleged to be wrong here; the point is
that the method could not have detected it.

## Proposed fix — keyed per-parameter sub-streams

Give each genesis parameter its own named stream, so a range change is
contained:

```python
age_rng      = rng.stream("world_gen.spawn.person_age")
hunger_rng   = rng.stream("world_gen.spawn.person_hunger")
position_rng = rng.stream("world_gen.spawn.position")
```

Per-entity keying (`f"world_gen.spawn.person_age.{person_index}"`) would isolate
further still, so even the *count* of people stops shifting other draws.

**This is itself a re-baseline**: re-streaming changes every genesis value once.
The gain is that it is the *last* such cascade — afterwards a parameter change
moves only that parameter. **Not implemented. Needs authorisation.**

## A measurement caveat, recorded because it caught me

The comparison run that produced `5,022 / 67c44c53...` was **contaminated** and
its numbers must not be used: it applied the old age band against the **new**
`CHILD_MAX_AGE_TICKS = 657_000`, classifying every 3,000–30,000-tick agent as
`child` and changing canonical state. The trustworthy pair is the true
pre-change capture (5,004 / `897f3f7f…3c5ab`) against the post-change capture
(4,830 / `b8d438ff…`), giving the −174 above.

Scope of the doubt: only `scratchpad/partB_mechanism.py` used a scenario
config-override path. The formation-distribution, F8 and CORE-INTEGRITY-002
serial probes all drove real scenarios through the harness or API directly and
do not inherit it.

## Status of the age work this came from

- **Part A** (`e478229a`, derived `age_years` + elder threshold) — committed,
  verified hash-neutral, **deliberately unpushed**: with genesis still
  3,000–30,000, every founding adult renders as **`0 years`**, which is worse
  than the raw tick count it replaced. Helper and tests are keepers; the display
  waits for real ages.
- **Part B** (genesis band + child threshold) — **uncommitted, on hold** pending
  this fix. No F-06 was written: the 174-event delta measures *a different
  starting world*, not a consequence of ages, and that story must not enter the
  baseline record.
