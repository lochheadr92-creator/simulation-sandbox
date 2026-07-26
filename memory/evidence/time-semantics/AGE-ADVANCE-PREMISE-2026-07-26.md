# Time semantics — does age advance per tick? Premise check.

**Read-only. No migration performed, none designed, none scoped.** Measured at
`9d024d27` on branch `capability/stage-8c-phase1-aid-exchange`, 2026-07-26.

## CLASSIFICATION: (a) — age advances 1/tick. Premise VERIFIED on the arithmetic.

**With one material correction: nothing in the codebase treats a tick as a
year.** See "The year framing is unsupported" below — it changes what a
migration would be *about*, so it is recorded up front rather than buried.

## 1. The read

| Question | Answer |
|---|---|
| Is there an `age` field? | **`age_ticks`** — canonical person state, not derived |
| What increments it? | `lifecycle_domain.py:81` — `age = e.get("age_ticks", 0) + 1` |
| By how much, how often? | **+1, every tick.** `select_due_ids` (`:68-69`) returns *every* alive person each tick; no cadence gate |
| Is there a `birth_tick`? | **No.** `grep -rn "birth_tick\|birth_time\|born_tick\|date_of_birth" backend/` returns **nothing** |
| Seeded where? | `world/generator.py:107`, `spawn_rng.randint(*p_age)`, range `(3000, 30000)` (`:64`) |

**What consumes age:**

- `_life_stage(age_ticks)` (`lifecycle_domain.py:54-59`) → `child` / `adult` /
  `elder`, on `CHILD_MAX_AGE_TICKS = 3000` and `ELDER_MIN_AGE_TICKS = 40000`
  (`core/constants.py:33-34`).
- `life_stage == "elder"` gates an age-decline health cost
  (`lifecycle_domain.py:91`). **This is the only place age changes behaviour.**
- `child` is unreachable: genesis spawns at 3000+ and there is no birth path.
  `core/constants.py:33` says so itself — *"purely observational, no spawn path
  exists"*.

So age is **not** an unread field, but its behavioural reach is one health
penalty at one threshold.

*Not a consumer:* `reciprocity_trust.py:27` mentions `age_ticks`, but that is
the age of a **contribution record**, not of a person. Different quantity, same
word.

**Display:** `frontend/src/components/EntityInspector.jsx:146-147` renders
`age_ticks` and `life_stage` under those literal labels. No unit conversion, no
"years" anywhere.

## 2. The measurement

Existing committed run, no new runs started.
`run-cf87de38ecf0` — scenario `basic_survival`, seed `d0f4ca9756`, 735 ticks.

| agent | age @ tick 1 | age @ tick 735 | delta | lifecycle events |
|---|---|---|---|---|
| person-000 | 14,245 | 14,979 | **734** | 735 |
| person-001 | 29,134 | 29,868 | **734** | 735 |
| person-002 | 19,572 | 20,306 | **734** | 735 |
| person-003 | 7,242 | 7,976 | **734** | 735 |
| person-004 | 18,630 | 19,364 | **734** | 735 |
| person-005 | 21,758 | 22,492 | **734** | 735 |

**Exactly 1 age_tick per tick, every agent, 735 events each with no gaps.** The
code read and the measurement agree; there is no hidden cadence, gate or
multiplier.

## 3. The year framing is unsupported — and this is the finding that matters

The migration premise holds that a tick is treated as ~1 year, so a 1,000-tick
run ages agents by ~1,000 years. **The first half is not supported by anything
in the codebase; the second half is true only if you supply the year reading
yourself.**

- **`grep -rni "year" backend/` returns nothing.** No constant, comment, field
  or label anywhere asserts a year.
- **The only time-unit anchor in the codebase is `DAY_LENGTH_TICKS = 100`**
  (`core/constants.py:16`), used by `time_phase()` for dawn/day/dusk/night. That
  makes a tick **1/100 of a day**, not a year.
- Read against that anchor the existing numbers are internally coherent:
  genesis ages 3,000–30,000 ticks = **30–300 days**; elder at 40,000 ticks =
  **400 days**. Read as years they are not: genesis agents would be
  7,242–29,868 **years** old, and an "elder" threshold of 40,000 years is not a
  quantity anyone chose.

**Consequence for scoping.** A 1,000-tick run advances age by exactly 1,000
`age_ticks` — which the codebase's own day anchor reads as **10 days**, not
1,000 years. So this is not a defect in how age advances; the mechanism is
consistent with itself. Any migration here is a decision about **what a tick
should mean**, not a repair of a broken or missing ageing mechanism. That is a
different, and much larger, question than the premise implied.

**Not classified (b):** no birth-time field exists, so age is not derived and
this cannot be dismissed as a display defect.
**Not classified (c):** age does advance, and it does gate one behaviour, so an
ageing system exists.

## 4. FLAG — hard-rail collision, not resolved here

Any conversion of tick-denominated constants would collide with `CLAUDE.md`'s
extend-only rail. Recorded so a later scoping session sees it before designing:

| Constant | Location | Inside the 7A–7D / 8A rail? |
|---|---|---|
| `SUPPORT_FRESHNESS_TICKS = 4` | `group_state_contracts.py:33` | **YES — Stage 7B.** Hard-railed extend-only |
| `STRUCTURE_WEAR_INTERVAL = 5` | `core/constants.py:59` | No — ecology/Layer C, but tick-denominated |
| Tend band (`STRUCTURE_TEND_CONDITION_FLOOR/CEILING`) | `core/constants.py:70-71` | No — Layer C Variety Leg 1 |
| Reciprocity recency decay (`DECAY_PER_TICK`) | `reciprocity_trust.py:27` | No — Phase 5B5 |

`SUPPORT_FRESHNESS_TICKS` is the sharp one: it is Stage 7B, so it may only be
extended via new registries / schema-version bumps / new hooks, never
re-denominated in place. It is also already load-bearing for
`test_concurrent_stage7b_…` (CORE-INTEGRITY-002), where a 4-tick window governs
whether supports are derived at all.

`ELDER_MIN_AGE_TICKS` and `CHILD_MAX_AGE_TICKS` (`core/constants.py:33-34`) are
tick-denominated too and would move under any re-denomination.

## Limitations

1. One run measured (`basic_survival`, 735 ticks, 6 agents). The mechanism is
   scenario-independent by code-read, but only this lineage was measured.
2. The frozen `living_settlement` 320 lineage was **not** available: the harness
   runs in-process and does not persist to MongoDB, so no committed run data
   exists for it.
3. No new runs were started, per instruction.
4. Whether a tick *should* be a day, a year, or anything else is a design
   question this check does not touch.
