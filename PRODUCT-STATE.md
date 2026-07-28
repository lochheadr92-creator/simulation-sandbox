# Product state — what the world actually does

Honest, measured, updated when the world changes. Not a roadmap. Not a status
report. If a number here is stale, re-measure it or delete it.

Last measured: 2026-07-28, `living_settlement`, 320 ticks, 8 people, seed
`living-agents-stage6`.

## The world today

| metric | ratified baseline | with the R1 retarget (uncommitted) |
|---|---:|---:|
| actions per 100 ticks | 356 | 411 |
| top-3 action dominance | **74.6%** | **62.8%** |
| social share of all actions | 20.8% | 33.0% |
| action types firing exactly once in 320 ticks | **8** | 7 |
| action types never firing | 0 | 1 (`warn`) |
| population survival | 8/8 | 8/8 |
| replay equality | exact | exact |

**The headline: three actions — rest, move, tend — are three-quarters of
everything that happens.** Eight further behaviours (warn, share_information,
trade, lie, threaten, apologise, promise, reconcile) fire exactly once each in
320 ticks. The 5,000-tick control says they still stand at one firing each at
tick 5,000. They are not rare; they are decorative.

Zero group norms and zero group goals emerged across 5,000 ticks.

**What the retarget shows.** Ranking REQUEST_HELP by nearest target instead of
entity-id order drops top-3 dominance from 74.6% to 62.8% and lifts social
share from 20.8% to 33.0%. That is the first measured movement toward a world
worth watching. It also lost the single `warn` firing — see the backlog.

## What a player can see right now

The UI runs (`frontend/`, port 3010): scenario picker, seeded runs, world view,
and an Inspector with Entity / Groups / Timeline / Events / Interactions tabs.
Live playback suites have not been run against current code.

## What is not measured yet

- Unique actors per action, and per-pair concentration. Rate alone can flatter
  a world where one agent does everything.
- Recurrence across 100/500-tick windows.
- Percentage of events that alter a later decision.
- Relationship changes that persist and matter.

Those are the metrics that decide whether the world is alive. Building them is
backlog item 0.
