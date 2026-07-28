# Dynamics backlog

The only living document. Overwrite it freely; it carries no history and owes
no audit trail. If it disagrees with an archived doc, this one wins.

## What we are building toward

A world where:

- **things happen and have consequences** — a threat, an injury, a shortage,
  and the settlement visibly reorganises around it;
- **there is a daily rhythm** — you can tell roughly what time it is by what
  people are doing;
- **people have ongoing relationships** — you can follow two agents over time
  and see a thread: help, debt, repayment, falling out, repair;
- **it surprises us** — outcomes nobody scripted, explainable afterwards.

## The five checks (these replace the old gates)

Every behavioural or domain slice must pass all five:

1. **Visible** — a player can see the difference in the world, the inspector,
   or the event history.
2. **Consequential** — the behaviour changes later decisions or state.
3. **Recurrent** — it happens across time, with multiple actors. One scripted
   firing is not a behaviour.
4. **Diverse** — it doesn't just replace `rest` with a new dominant loop.
   Watch top-3 dominance.
5. **Deterministic** — same version, seed and inputs reproduce exactly.

Judged by watching the world and reading the numbers below — not by event-count
bands, not by pre-registration.

## Metrics that decide it

- distinct meaningful actions per 100 ticks
- unique actors performing each action
- recurrence across 100- and 500-tick windows
- share of events that alter a later decision
- relationship changes that persist and matter
- dominance share of the top three actions
- population survival and participation
- replay equality

## Queue

**0. Build the liveness instrument.** Unique actors per action, recurrence per
window, top-3 dominance, social share — computed from a run and printed. Every
item below is judged with it, so it comes first. Small: it reads
`summary.actions_by_type` and the accepted event stream, both of which already
exist.

**1. Commit the R1 retarget.** First change that measurably moved the world
(top-3 dominance 74.6% → 62.8%, social share 20.8% → 33.0%). It fails the old
±3% band; that band is retired. Update the hash pin in the same commit.

**2. Fix warn.** Under the retarget, `social_warn` goes 1 → 0. Diagnosed
2026-07-28: WARN_DANGER is still generated and still wins selection at frame-1
with a byte-identical plan id, then person-007 emits *no proposal at all* at
frames 2–3 (zero rejections — it isn't being refused), and the plan is
replanned to REPAY_DEBT at frame-4. The correlate is that person-001, the
warn's intended participant, is busy cooperating. A two-step plan that stalls
silently when its participant moves is an engine-level defect, not a tuning
issue, and it will keep eating multi-step social behaviour.

**3. Make the eight singletons recur.** share_information, trade, lie,
threaten, apologise, promise, reconcile, warn. Each fires once per 320 ticks
and once per 5,000. Find why each dies — candidate never generated, generated
and outscored, or won and preempted — and fix the cheapest ones first.

**4. Give the day a shape.** Nothing in the world distinguishes morning from
evening. Rhythm is the cheapest route to "alive" that doesn't need new social
machinery.

**5. Run the live UI suites and merge the frontend.** The branch is built,
reviewed, fixed and pushed; its playback suites have never run against current
code. Until they do, nobody can watch the world with confidence.

## Known engine debts (do not fix unless they block the above)

- Group-contract identity is content-dependent, so `collective_groups` has no
  stable A/B surface. Blocks the energy-lost-update remediation only.
- Per-parameter-per-entity RNG keying is owed before anything touches
  population counts.
- `collective_groups`' 1,000-tick hash has not been re-measured since
  `2d68ac16`.
