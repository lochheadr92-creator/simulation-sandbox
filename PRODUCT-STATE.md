# Product state — what the world actually does

Honest, measured, updated when the world changes. Not a roadmap. If a number
here is stale, re-measure it or delete it.

Last measured: 2026-07-28 at `d8f00eb6` (post Leg A), `living_settlement`,
320 ticks, 8 people, seed `living-agents-stage6`, clean tree.

## The world today

| metric | pre Leg A | **now** |
|---|---:|---:|
| accepted events | 4,868 | **5,088** |
| actions per 100 ticks | 356 | **388** |
| top-3 action dominance | 74.6% | **70.6%** |
| social share of all actions | 20.8% | **25.0%** |
| action types firing exactly once in 320 ticks | 8 | **7** |
| action types never firing | 0 | **1 (`warn`)** |
| rejections from whole-blob CAS false positives | 1,263 | **0** |
| population survival | 8/8 | 8/8 |
| replay equality | exact | exact |

**What changed.** Leg A fixed the commit-survival defect: social actions were
being discarded because a concurrent action touched an unrelated part of the
same person. `cooperate` went 55 → 152 and `repay` 44 → 94. `request_help`
fell 130 → 57, which is *probably* the help loop finally closing rather than
requests repeating because the response kept being thrown away — LIKELY, not
established.

**What did not change.** Three actions — rest, move, tend — are still 70.6% of
everything that happens. Seven behaviours still fire exactly once per 320
ticks, and `warn` now fires zero times. The rare social family is untouched by
the fix; it multiplied the two behaviours that were already common.

The 5,000-tick control (pre Leg A) showed those singletons still at one firing
each at tick 5,000, and zero group norms or goals across the whole run. That
has not been re-measured since.

## What a player can see right now

The UI runs (`frontend/`, port 3010, backend on 8000): scenario picker, seeded
runs, world view, Inspector with Entity / Groups / Timeline / Events /
Interactions. The playback suites have still never been run against current
code, and the frontend branch is unmerged.

## What is still not measured

- Unique actors per action, and per-pair concentration. Rate alone can flatter
  a world where one agent does everything — and the Leg A rejection census
  suggests exactly that risk: 91% of remaining rejections involve one agent.
- Recurrence across 100/500-tick windows.
- Percentage of events that alter a later decision.
- Relationship changes that persist and matter.
