# FINDING — genesis parameter ranges are coupled through one shared RNG stream

**Status: FIXED 2026-07-27** (re-baseline leg stage 1). CONFIRMED by code-read
2026-07-26; fix authorised and landed with a pre-registered gate, see
"Resolution" at the foot of this file. Found while attempting an age
re-baseline; **not an age finding**. Ages were the messenger.

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

---

## RESOLUTION — stage 1 of the re-baseline leg, 2026-07-27

Authorised as a re-baseline. Landed as ONE commit with the genesis spawn index,
because the two changes close the two halves of the same leak and neither is
verifiable without the other.

### What shipped

1. **Keyed per-parameter sub-streams** (`world/generator.py`). One stream per
   genesis parameter — `world_gen.spawn.placement`, `.tree_resource`,
   `.person_hunger`, `.person_thirst`, `.person_energy`, `.person_age`,
   `.animal_hunger`, `.animal_energy`. Streams are seeded from
   `sha256(run_seed::name)`, so they are independent of each other and of call
   order. Closes the VALUE channel this finding is about.
2. **Genesis spawn index** (`core/kernel.py`). Each spec's position becomes its
   `engine_priority`, so genesis commit order is positional rather than
   content-derived. Closes the ORDER channel — which this finding did **not**
   identify, and which sub-streams alone do not touch. See
   `memory/CORE-INTEGRITY-004-COMMIT-ORDER-CONTENT-SENSITIVITY.md`.

### Why one commit, stated plainly

Sub-streams alone leave the two-tier test's tier 1 RED: with values isolated, an
age-band edit still relocated an *unedited* entity's provenance ids, because
commit order still fell through to `content_hash`. The index alone would have
left the value channel open. Splitting them would have meant committing a state
in which the regression test for this finding fails.

### Regression test

`backend/tests/test_genesis_rng_isolation.py`, two tiers, both pre-registered
with their expected colour **before** implementation:

- **Tier 1** — an entity the edit never touched must come out of genesis
  byte-identical INCLUDING provenance. Pre-registered EXPECTED RED (it was the
  stage-1 gate); now green.
- **Tier 2** — an edited entity may differ only in the edited value and in
  fields whose **VALUE** is an event/proposal id, at any depth, inside lists.
  Pre-registered EXPECTED GREEN; was green, which is what proved the
  sub-streams work independently of the ordering fix.

Predicate is the value, never a field name — a name list had already missed
`source_event_id` once. The scrub asserts it actually fired, and fails loudly on
an unrecognised id shape or an id-shaped dict key rather than comparing raw.

### Pre-registered gate result, all four bands PASS

Bands fixed before the run. Noise source is **SAMPLING** — re-streaming draws a
genuinely different starting world, so values were expected to move. Baseline
figures derived from committed evidence
`memory/evidence/layer-c-leg1/upkeep_living_settlement_320_frozen_rebaseline.json`,
not from a fresh control run.

| quantity | baseline | band | measured | verdict |
|---|---|---|---|---|
| accepted events | 5,004 | 4,754 – 5,254 (±5%) | **4,849** (−155, −3.10%) | PASS |
| deaths | 0 | ≤ 1 | **0** | PASS |
| rest fraction | 0.2995 | 0.25 – 0.45 | **0.3740** | PASS |
| entropy (`actions_by_type`) | 2.5285 bits | ≥ 1.8 | **2.5242** | PASS |

Deaths measured via the exact 0-death signature `lifecycle_tick == persons ×
ticks` (2,560 = 8 × 320). Valid because `lifecycle_domain.select_due_ids`
filters on `alive`, so a dead person stops emitting the event.

**New frozen `living_settlement` 320 hash, pasted from run output:**

```
48dfec2267b4ded7752a2f3fbdbee45a3ee6f69c8b1f62e19b6fe095741b1e3b
(was 897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab)

repeat_matches True | replay_matches_final_entities True
resume_matches True (resumed at 160) | replay_state_hash == final_state_hash
```

### FIRST MEASURED ENTROPY-NOISE DATUM

No prior measurement of entropy's own noise existed, so per the leg contract
this is recorded as a datum rather than gated tightly. Under a pure resampling
perturbation, **entropy moved −0.0043 bits (2.5285 → 2.5242)** while individual
counts moved by up to ±72 (`rest` +72, `move` −67, `tend` −63) and distinct
types held at 19.

Reading: the *shape* of the action distribution is far more stable than any
single action count. This is an independent, mechanism-free reason to prefer
entropy over `rest%` for A/B comparisons, and it arrived after the Upkeep leg's
F-01 already argued the same thing on other grounds.

### BASELINE REGISTER — Stage 6 integrated-camp trace census (2026-07-27)

Moved here out of `backend/tests/test_stage6e_living_settlement.py`, which had
been asserting it. These are **recorded data, not gates**: they describe one
seed's trajectory, so every re-baseline is expected to move them. Nothing here
should ever be cited as a pass/fail condition.

`living_settlement`, seed `stage6-integrated`, 30 ticks, post-stage-1:

```
final_state_hash 01160b49c2eabedc7665ad3bad62cb59390ccad35c171a034acfcde0f8132e15
total actions 176   distinct types 18

apologise 1   consume 4   cooperate 1   drink 3    gather 2
lie 1         move 68     promise 1     reconcile 1  repair 4
repay 1       rest 40     retrieve 2    share_information 1
store 1       tend 43     threaten 1    trade 1

warn                 0        (was >=1 pre-stage-1; see the deferral row)
reported_claim_count 0        (assertion had required >=1)
```

**`warn` horizon datum.** Recorded as a datum only, per the ruling — not a gate.
`warn` is absent at every horizon probed on this seed: **30, 35, 40, 45, 50, 60,
80, 100, 150, 320 ticks**. So no horizon extension recovers it, and none was
adopted. A seed re-pin was likewise rejected.

**5-seed assertion robustness** (30 ticks; seeds `stage6-integrated`,
`living-agents-stage6`, `stage6-order`, `stage6-information`, `warn-probe-b`).
Measured rather than assumed, because asserting seed-robustness without
measuring it is the defect that produced three successive in-place weakenings of
this test:

| assertion | verdict |
|---|---|
| the 14 non-`warn` action types | SEED-ROBUST — all 5 — retained as an assertion |
| the full 15-type census | TRACE-DEPENDENT — fails 4 of 5 — moved here |
| `reported_claim_count >= 1` | TRACE-DEPENDENT — fails 2 of 5 — moved here |
| `critical_interrupt` / `resumption` / `failed_plan_replan` ≥ 1 | SEED-ROBUST — retained |
| `rejected` / `resource_depletion` / `contradicted` ≥ 1 | SEED-ROBUST — retained |
| `weather_conditions == ["rain"]` | SEED-ROBUST — retained |
| `deceptive_claim_count == 0` | SEED-ROBUST — retained |
| `final_relationship_count > 8`, commitments ≥ 1 | SEED-ROBUST — retained |
| all five capacity bounds, replay equality | SEED-ROBUST — retained |

`reported_claim_count >= 1` was a **latent** failure: it had never been evaluated
on a failing run, because the census assertion above it failed first and pytest
short-circuits. Repairing only the assertion that shouted would have produced a
second red run.

The retained assertions are now **parametrised over two seeds**, so
seed-robustness is enforced by the suite rather than claimed in a comment.

### DEFERRAL RECORD — `warn` organic firing, scenario-dynamics-blocked

Register row: `memory/CAPABILITY_ROADMAP.md`. Category is
**scenario-dynamics-blocked**; the three records that taxonomy requires:

**(a) The blocking measurement.** Decision receipts, `living_settlement`, seed
`stage6-integrated`, 320 ticks, scout `person-007`:

```
tick 1  WARN_DANGER WINS (23299 vs REST 743)
        plan = ['MOVE_TO_TARGET', 'WARN'], step_index 0
        executes move -> living_move ACCEPTED
tick 2  WARN_DANGER continues, still step_index 0
        move REJECTED precondition.failed          <- plan stalls
tick 3  REPLAN -> REPAY_DEBT 27477 beats WARN_DANGER 23435
        plan abandoned before the WARN step ever runs

3 offers in 320 ticks. animal in range 270/320 ticks, a person 320/320.
```

The scout at (5,6) is **boxed in by its own campmates**: reaching `person-000`
at (4,4) requires stepping onto (4,5) or (5,5), both occupied, so
`MOVE_TO_TARGET` can never succeed. Compare `TEND_STRUCTURE` at ticks 4–7, which
needed four uninterrupted ticks (move, move-rejected, move-rejected, `tend`) to
reach its terminal step. WARN_DANGER got two.

This is **plan preemption** — not selection displacement (it won) and not
geometry (the animal was in range for 270 ticks). Mechanism verified INTACT: it
fires on another seed under the same code.

**(b) The unblock condition.** A `living_settlement`-family scenario in which a
scout's warn target is reachable — not walled off by campmate-occupied tiles.
No dynamics change was made here; doing so would edit a Stage 6 canonical
fixture and move further hashes for reasons unrelated to the RNG fix.

**(c) No threshold was lowered to manufacture a firing.** Explicitly:

- the 14 seed-robust action types are **still asserted**, on two seeds;
- `warn` moved to a **stronger** deterministic fixture pair asserting the action
  **commits** through `run_commit_frame`, not merely that the goal is selected —
  which matters because the goal already wins organically and still never
  commits, so a selection-only assertion would have been vacuous;
- a horizon extension was **rejected** on measurement (absent through 320 ticks);
- a seed re-pin was **rejected** as seed-shopping.

**Recorded, deliberately NOT asserted as correct:** the preemptor was
`REPAY_DEBT` (27477) — a social obligation, *not* a survival goal. So repaying a
debt currently outranks warning a neighbour about a predator. VERIFIED by the
receipts above, **pre-existing** (not introduced by the re-stream), and parked in
`FRONTIER.md`'s queued rulings for a future scoring-contract leg. The negative
fixture pins invariant C-6 survival dominance **only**, and its docstring says so.

### Attribution — which effect caused what

Honest split, per CORE-INTEGRITY-004:

- **Value changes are the re-stream.** Every genesis draw comes from a different
  stream, so positions, needs and tree resources all differ. This is a genuinely
  different starting world, by design and once only.
- **Order changes are the index.** Genesis commit order is now spec position.
- **Trajectory changes are statistical, not attributable.** The −155 accepted
  events and the action-mix reshuffle are the combined consequence of a different
  starting world plus ordering noise of the magnitude 004 measured
  (`living_rest` ±28%, accepted ±1.2%). No single action-count delta here is
  claimed as a behaviour change, and none should be cited as one.

### What is still NOT fixed

- An **edited** entity's own spawn event id still changes, because `hash8` is a
  prefix of its content hash. 004's channel, 004's stage.
- The index stabilises order against **content** changes only, not
  **composition** changes: appending a genesis spec is free, inserting one
  mid-list renumbers everything after it.
- **Per-entity RNG keying is still owed.** Only per-parameter landed. Adding a
  person still shifts every later person's draws on that parameter's stream.
  Debt is load-bearing before Stage 11 touches population counts.

---

## SESSION HANDOFF — 2026-07-27, stopped after stage 1

Stopped on user instruction ("stop and save") with stage 1 committed and green.
Start a fresh session; this doc is the memory, not the context window.

### DONE

- **Step 0 — push.** `85ba7c87..7270e61f`. The 004 evidence, this finding, and
  age Part A are on origin.
- **Step 1 — two-tier isolation tests.** Written and pre-registered before
  implementing; both observed colours matched the pre-registration.
- **Step 2 — stage 1.** Committed as **`ce49d762`**. Gate fully green: four
  pre-registered bands PASS, tier 1 green, suite 430 executed passed / 0
  executed failed / 4 skipped, repeat+replay+resume True, frozen hash
  `48dfec22…1b1e3b` reconfirmed byte-identical on the final tree.

### NOT STARTED

- **Stage 2** — genesis band `(657000, 2007500)` + `CHILD_MAX_AGE_TICKS =
  657_000`. Both were drafted in the working tree earlier this session and
  **deliberately reverted by edit** (never `git checkout`) so stage 2 lands on
  top of stage 1 rather than inside it. Re-apply to `core/constants.py`,
  `world/generator.py` (`_default_person_age_range()` + `GENESIS_ADULT_AGE_MAX_
  TICKS`) and `tests/test_age_projection.py`.
- **Step 4** — qualified full suite, repeat/replay/resume, push.
- **Step 5** — STOP; frontier returns to Layer C social density.

### Pre-registered stage-2 gate (agreed, not yet run)

Noise source is **ORDERING**, and that is now a code-read fact rather than an
assumption: `age_ticks`'s only consumers are the genesis draw, the read-only API
projection, and `lifecycle_domain`, whose sole behavioural branch is
`if life_stage == "elder"`. `life_stage` is `"adult"` on both sides (strict `<`,
so exactly 657,000 is an adult; max genesis 2,007,500 + 320 ticks stays 364,000
below elder). So new ages can reach behaviour ONLY through
content_hash → event-id `hash8` → commit order.

- genesis diff exact via tier 2, ages only — **already proven**: tiers 1 and 2
  compare exactly `(3_000, 30_000)` against `(657_000, 2_007_500)`, which is
  precisely the stage-2 default change, so they *are* stage 2's genesis diff;
- accepted within **±3%** of stage 1's 4,849 → **4,704 – 4,994**;
- character envelope unchanged: deaths ≤ 1, rest fraction 0.25–0.45, entropy
  ≥ 1.8 bits;
- expect a delta at **noise-floor order, not near zero** — the hash8 channel
  guarantees movement;
- second hash, second write-up, same honesty split: exact at genesis,
  statistical at trajectory.

### Outstanding, tracked

1. **`collective_groups` baseline is STALE** and unmeasured — see the register
   entry in `memory/CAPABILITY-DOCTRINE.md`. Its hash necessarily moved. Measure
   ONCE at the leg close (after stage 2) so the value is not immediately
   superseded, and only with explicit authorisation at that STOP.
2. **Adversarial review is AUTHORISED** for after stage 2 — independent
   non-Anthropic agent over the complete branch diff, blind pass first, findings
   ledger (FIX/ACCEPT/DISPUTE) in the close-out per
   `memory/ADVERSARIAL-REVIEW-PROTOCOL.md`. Never self-review: this session
   wrote the code, the tests, and the claims.
3. **Goal-scoring smell parked** in `FRONTIER.md` queued rulings beside the
   effort-transfer gradient. Pre-existing, untouched, not asserted as correct.
4. Old-trace `warn` completion is **LIKELY**, inferred from the pre-change test
   passing. Not observed; no revert was performed to check.
