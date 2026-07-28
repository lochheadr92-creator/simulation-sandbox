# Active Leg B — people obey the day

Declared 2026-07-28. Leg A closed PASS WITH LIMITATIONS —
`memory/archive/legs/LEG-A-SOCIAL-COMMIT-SURVIVAL-2026-07-28.md`.

## Domain objective

The settlement has a readable daily rhythm: people rest and stay in at night,
gather and tend by day, and cluster socially around dusk — so you can glance at
the world and tell roughly what time it is.

## Trigger

The world clock. `is_night(tick)` already exists at `core/constants.py:171`,
the kernel uses it (`core/kernel.py:112`) and `animal_domain.py:33` uses it.
**Animals already live by the day cycle. People do not.** Nothing new is
created; an existing signal is connected to a domain that ignores it.

## Decision

A soft phase multiplier applied to existing candidate scores in
`build_settlement_candidates` — **weighting, not gating**. A hungry person
still gathers at night. An exhausted person still rests at noon. Survival
dominance is untouched: the multiplier never lets a phase preference outrank
urgent need (constitution, behavioural invariant 1).

No new candidates, no new state, no new events, no new domain. Derived from
`tick`, so determinism is unaffected.

## Action

Existing actions, redistributed across the day. No new event types.

## State consequence

None beyond the action mix itself. This leg deliberately adds no state — it is
the cheapest possible visible win and the smallest possible blast radius.

## Visual consequence

- The world view visibly quiets at night and busies by day.
- The event log reads as a day: rest clusters, then gather/tend clusters.
- The Inspector's explanation for a chosen goal names the phase when it
  mattered.

## Success test

Take the action census per 100-tick window and compare against phase. The mix
must **vary with the phase** rather than being flat — that is the whole product
of this leg, and this project has never had a metric showing time meaning
anything.

## Failure conditions

- The mix stays flat (multiplier too weak to matter).
- Behaviour becomes synchronised and robotic — everyone asleep at once, nobody
  ever gathering at night (multiplier too strong; it has become a ban).
- Survival dominance is displaced (a phase preference outranks urgent need).
- Top-3 dominance rises: `rest` swallowing the night is not rhythm, it is a
  worse loop.

## Sessions

- **A — definition and activation.** Confirm the phase signal reaches the
  settlement domain; census the current mix per window to prove it is flat now.
- **B — thin implementation.** One multiplier table, applied post-scoring,
  pre-selection.
- **C — integration.** Determinism, replay, and a check that survival
  dominance still holds.
- **D — presentation.** Phase visible in the UI; explanation names it.
- **E — freeze.** Regression test, known limitations, commit, move on.

The frozen hash will move. Update the pin in the same commit and say what moved
it — normal path, no ceremony.

## Carried forward from Leg A — do before any *social* domain

Not blocking this leg (day rhythm is scoring, not commit), but blocking Leg 1
information sharing and every other social domain:

**The pin-capture mismatch.** ~955 of 1,155 remaining rejections are
self-doomed at build time: the actor-side pin is captured from the domain's
perception-enriched working blob, so it can never match the pre-perception
committed record when the actor observed a fresh signal from the target.
Fix: capture the actor-side pin from the committed frame-start blob.

**The composition-point write.** `living_settlement_domain.py:777` rewrites
`actor_update["living_agent"]` wholesale, which is why narrowing the social
builder alone would crash (`derive_internal_pressures` subscripts
`state["traits"]`). The diff belongs at that composition point.

Both live in the file Ryan has uncommitted, so they ride with his retarget
commit. Projected residue after both: ~230 honest rejections (LIKELY, projected
from census partitions, not run) — roughly **925 more social actions per 320
ticks** than commit today.

**Warn's real bottleneck is candidate generation.** Exactly one `social_warn`
proposal exists in 320 ticks. It is not a commit-survival problem and never
was. It belongs to a social domain leg, not here.
