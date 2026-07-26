# 7b precondition formation-tick distribution — 30 seeds, 500-tick horizon

Durable record of the measurement that must precede any timeout choice for
`test_concurrent_stage7b_steps_do_not_duplicate_shared_state_or_head`. The
disposable probe output is not sufficient evidence; this is.

## Provenance

| | |
|---|---|
| Branch | `capability/stage-8c-phase1-aid-exchange` |
| Commit measured | `df44e19a7e4ffd525f3257bbafece4647c923d03` |
| Date | 2026-07-26 |
| Scenario | `collective_groups` |
| Execution path | **API** — `create_run` / `step_run`, the path 7b drives |
| Seeds | 30, independent, randomly generated |
| Measurement horizon | **500 ticks** |
| Production code changed | **None.** `git diff HEAD -- backend/core backend/domains backend/scenarios` empty |

**Why a 500-tick horizon and not the candidate timeout.** A horizon equal to the
proposed timeout cannot distinguish a slow-forming seed from one that does not
form in the observed range. The horizon is deliberately far above any timeout
being considered.

## Exact precondition measured

The complete condition the concurrent operations require, not a proxy:

```
group-shared-state-000 EXISTS  AND  carries a non-empty `groups` map
```

Registry existence alone was **not** used — an earlier, cruder measurement in
this investigation did use existence, and it is why a 40-tick cap looked
adequate when it is not.

## Methodology

Gitignored scratch probe, `scratchpad/ci002_formation_measurement.py`, **not
committed**. Per seed: `create_run(seed, "collective_groups")`, then
`step_run(run, 1)` one tick at a time, checking the full precondition after
each tick, recording the first tick at which it holds.

**Database isolation.** `DB_NAME` was overridden to a dedicated scratch
database **before `core.db` was imported**, so every run created by this probe
landed in a throwaway database. The normal test database was structurally
untouched rather than cleaned up afterwards.

## Results — all 30 seeds formed

```
formed: 30/30        NOT-FORMED-BY-500: 0
min 11   median 27   p95 117   max 187
```

Raw sorted formation ticks — **the primary evidence**, because with n≈30 the
p95 is only a coarse order statistic:

```
11, 11, 12, 14, 17, 22, 22, 22, 22, 22, 23, 23, 23, 27, 27, 27,
28, 31, 32, 32, 32, 32, 33, 42, 80, 86, 86, 91, 117, 187
```

### Seed → formation tick, with revisions at formation

| Seed | Tick | assoc rev | group-state rev | head rev |
|---|---|---|---|---|
| `ci002-form-04ff129255` | 11 | 8 | 1 | 11 |
| `ci002-form-59a94b8d79` | 11 | 8 | 1 | 11 |
| `ci002-form-fab803ddd7` | 12 | 9 | 1 | 12 |
| `ci002-form-3bcd78a4f7` | 14 | 11 | 1 | 14 |
| `ci002-form-794a434127` | 17 | 12 | 1 | 17 |
| `ci002-form-0867a37426` | 22 | 15 | 1 | 22 |
| `ci002-form-4ff54b5487` | 22 | 19 | 1 | 22 |
| `ci002-form-aa0d80b363` | 22 | 18 | 1 | 22 |
| `ci002-form-d54af5b4cc` | 22 | 14 | 1 | 22 |
| `ci002-form-84a4458bd2` | 22 | 16 | 1 | 22 |
| `ci002-form-f642481177` | 23 | 14 | 1 | 23 |
| `ci002-form-ff8769a576` | 23 | 14 | 1 | 23 |
| `ci002-form-43acc0fd21` | 23 | 17 | 1 | 23 |
| `ci002-form-e0b74d0da2` | 27 | 17 | 1 | 27 |
| `ci002-form-c44d974319` | 27 | 17 | 1 | 27 |
| `ci002-form-c4cfb35d16` | 27 | 19 | 1 | 27 |
| `ci002-form-a6dc1db689` | 28 | 20 | 1 | 28 |
| `ci002-form-2c27b2ffb6` | 31 | 27 | 1 | 31 |
| `ci002-form-c0e08c64de` | 32 | 25 | 1 | 32 |
| `ci002-form-545efdc7f2` | 32 | 25 | 1 | 32 |
| `ci002-form-cbce16c737` | 32 | 27 | 1 | 32 |
| `ci002-form-0e8665a7d0` | 32 | 25 | 1 | 32 |
| `ci002-form-f9c7e14dba` | 33 | 24 | 1 | 33 |
| `ci002-form-0b0afcf98b` | 42 | 38 | 1 | 42 |
| `ci002-form-0523cc6ed8` | 80 | 63 | 1 | 80 |
| `ci002-form-3b542fdc30` | 86 | 66 | 1 | 86 |
| `ci002-form-91c6b7c28d` | 86 | 58 | 1 | 86 |
| `ci002-form-d05844fbb5` | 91 | 56 | 1 | 91 |
| `ci002-form-fea8d62fbf` | 117 | 65 | 1 | 117 |
| `ci002-form-1d2191a4c0` | 187 | 90 | 1 | 187 |

### `NOT-FORMED-BY-500` seeds

**None.** All 30 formed inside the horizon.

> `NOT-FORMED-BY-500` is an observation about this measurement horizon. It does
> not prove that a seed can never form groups. No seed here required that
> label, but the definition is recorded because a future measurement may.

## Shape — two regimes, not one spread

- **24 of 30 (80%) form by tick 42.**
- **6 of 30 (20%) form between 80 and 187.**
- **Nothing lands between 43 and 79.** An empty 37-tick gap across 30 samples
  is not what a single smooth distribution looks like.
- `max / median` = **6.9×**; `max` exceeds `p95` by **60%**.

## The finding that most affects the design choice

**`group-state revision at formation is exactly 1 for all 30 seeds** — every
value in that column, from the 11-tick seed to the 187-tick seed.

Formation *is* that registry's first write, always. So waiting longer does not
accumulate group-state churn ahead of the concurrent step; a 187-tick wait
arrives at exactly the same group-state revision as an 11-tick wait. The
association registry does vary (8 → 90), so association churn accumulates — but
the registry 7b actually asserts on is group-state.

This materially weakens the usual argument for organic waiting ("it preserves
the natural churn preceding concurrency") **for this specific test**, and it
should be weighed in the design ruling rather than assumed away in either
direction.

## Cleanup and verification

| | |
|---|---|
| Method | dedicated scratch database, dropped at end |
| Scratch DB | `simulation_sandbox_ci002_scratch` |
| Present after drop | **false** (verified via `list_database_names`) |
| Normal DB | `simulation_sandbox` — **not touched by the probe** |

## Draw order — how the observed maximum developed

The sorted list above describes **shape**. It cannot show how the maximum
emerged, which is a different question and the one that matters when judging
whether 30 samples bound anything. Recorded in measurement order:

| # | seed | tick | running max | new max? | assoc rev | gs rev | head rev |
|---|---|---|---|---|---|---|---|
| 1 | `ci002-form-0867a37426` | 22 | 22 | **YES** | 15 | 1 | 22 |
| 2 | `ci002-form-d05844fbb5` | 91 | 91 | **YES** | 56 | 1 | 91 |
| 3 | `ci002-form-0523cc6ed8` | 80 | 91 | no | 63 | 1 | 80 |
| 4 | `ci002-form-3b542fdc30` | 86 | 91 | no | 66 | 1 | 86 |
| 5 | `ci002-form-c0e08c64de` | 32 | 91 | no | 25 | 1 | 32 |
| 6 | `ci002-form-4ff54b5487` | 22 | 91 | no | 19 | 1 | 22 |
| 7 | `ci002-form-1d2191a4c0` | 187 | 187 | **YES** | 90 | 1 | 187 |
| 8 | `ci002-form-aa0d80b363` | 22 | 187 | no | 18 | 1 | 22 |
| 9 | `ci002-form-f642481177` | 23 | 187 | no | 14 | 1 | 23 |
| 10 | `ci002-form-fab803ddd7` | 12 | 187 | no | 9 | 1 | 12 |
| 11 | `ci002-form-a6dc1db689` | 28 | 187 | no | 20 | 1 | 28 |
| 12 | `ci002-form-2c27b2ffb6` | 31 | 187 | no | 27 | 1 | 31 |
| 13 | `ci002-form-e0b74d0da2` | 27 | 187 | no | 17 | 1 | 27 |
| 14 | `ci002-form-f9c7e14dba` | 33 | 187 | no | 24 | 1 | 33 |
| 15 | `ci002-form-d54af5b4cc` | 22 | 187 | no | 14 | 1 | 22 |
| 16 | `ci002-form-ff8769a576` | 23 | 187 | no | 14 | 1 | 23 |
| 17 | `ci002-form-0b0afcf98b` | 42 | 187 | no | 38 | 1 | 42 |
| 18 | `ci002-form-545efdc7f2` | 32 | 187 | no | 25 | 1 | 32 |
| 19 | `ci002-form-04ff129255` | 11 | 187 | no | 8 | 1 | 11 |
| 20 | `ci002-form-c44d974319` | 27 | 187 | no | 17 | 1 | 27 |
| 21 | `ci002-form-43acc0fd21` | 23 | 187 | no | 17 | 1 | 23 |
| 22 | `ci002-form-84a4458bd2` | 22 | 187 | no | 16 | 1 | 22 |
| 23 | `ci002-form-794a434127` | 17 | 187 | no | 12 | 1 | 17 |
| 24 | `ci002-form-cbce16c737` | 32 | 187 | no | 27 | 1 | 32 |
| 25 | `ci002-form-3bcd78a4f7` | 14 | 187 | no | 11 | 1 | 14 |
| 26 | `ci002-form-fea8d62fbf` | 117 | 187 | no | 65 | 1 | 117 |
| 27 | `ci002-form-c4cfb35d16` | 27 | 187 | no | 19 | 1 | 27 |
| 28 | `ci002-form-0e8665a7d0` | 32 | 187 | no | 25 | 1 | 32 |
| 29 | `ci002-form-91c6b7c28d` | 86 | 187 | no | 58 | 1 | 86 |
| 30 | `ci002-form-59a94b8d79` | 11 | 187 | no | 8 | 1 | 11 |

**Running-maximum sequence**

```
22, 91, 91, 91, 91, 91, 187, 187, 187, 187, 187, 187, 187, 187, 187,
187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187
```

| | |
|---|---|
| New maxima at samples | **1, 2, 7** |
| Last new maximum | sample **7**, value **187** |
| Samples after the final new maximum | **23** |

### What this does and does not license

- **The sorted list describes shape.** Two regimes, empty gap 43–79.
- **The draw order describes how the observed maximum developed.** It tripled
  within the first 7 samples (22 → 91 → 187) and then did not move for 23.
- **Neither proves the true distribution is bounded.** 23 draws without a new
  maximum is *consistent with* stabilisation and equally consistent with a
  heavy tail whose next exceedance simply had not been drawn. With a long tail,
  extended runs without a new maximum are exactly what you expect to see; they
  are not evidence of an upper limit. **No convergence is inferred.**
- **This uncertainty no longer blocks 7b.** Deterministic precondition
  construction removes formation timing from the test entirely, so the
  unbounded tail stops being a property the test depends on.

## Limitations

1. **n = 30.** p95 is a coarse order statistic at this sample size; the raw
   sorted list is the primary evidence.
2. **The tail is not characterised.** `max` (187) exceeds `p95` (117) by 60%,
   so the sample does not bound the upper tail. A larger sample could produce
   values well above 187.
3. **Single scenario, single path.** `collective_groups` on the API path only.
   Says nothing about other scenarios or the harness path.
4. **Formation timing only.** The probe measures when the precondition becomes
   true. It does not measure contention, and does not establish whether
   formation timing correlates with the churn the canary observes — though the
   constant group-state revision above is evidence *against* a strong link for
   this registry.
5. **Wall-clock cost not recorded** per seed; only tick counts.
