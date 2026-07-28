# Active Leg A — social actions must survive commit

Declared 2026-07-28. Supersedes the "plan continuation repair" framing, which
was built on a wrong diagnosis. Corrected below with the evidence.

## What we thought

A multi-step plan whose participant moves emits **no proposal at all** for two
ticks and is then replanned away. Framing: a planner defect, fix the
continuation branch, invariant "continue / re-approach / wait / fail / complete,
never silence".

## What is actually happening (VERIFIED)

The plan continuation worked perfectly. person-007 generated the WARN_DANGER
continuation candidate, it won selection, it produced a plan, and it **proposed
`social_warn`**. The proposal was then **rejected at commit**:

```
tick 2  person-007
  rejection_stage : commit_revalidation
  reason_code     : precondition.failed
  reason_detail   : living_agent_eq_failed
  proposed        : social_warn
                    "plan_continuation: selected WARN_DANGER -> warn"
```

At the same tick, person-001 committed `social_cooperate` **on person-007**.
The social proposal builder pins the participant's entire `living_agent` blob
as a precondition; person-007's own action, built from a frame-start base,
failed the equality check and was discarded. At tick 3 it happened again. At
tick 4 the replanned REPAY_DEBT finally landed.

This is the documented asymmetric-CAS lost update (`OQ1-ENERGY-COLLISION-
RESOLUTION`, `REGISTRY-COMPONENT-OWNERSHIP` F4): `build_social_action_proposal`
CASes the whole `living_agent` blob while `build_physical_action_proposal` pins
only `alive`.

**Scale:** every rejection in the first 12 ticks of both arms is this one
failure — 19/19 in the baseline, 18/18 with the retarget, 100%
`precondition.failed / living_agent_eq_failed`.

## Why this is the leg

A social action pins both participants. So the more social the world becomes,
the more social actions collide, and the loser is silently discarded. **The
world cannot become more social, because becoming more social destroys social
actions.** That is a far better explanation for eight behaviours firing once
per 320 ticks than any scoring or reachability theory.

It also explains the retarget's paradox exactly: `social_cooperate` +145% and
`social_repay` +175% *while* the single `warn` firing disappeared. More social
traffic, more collisions, casualties among the rarest actions first.

And it blocks Leg 1. Information sharing is a two-participant social action. It
will be killed whenever either participant is doing anything else that tick —
which, in a world we are deliberately making more social, is often.

Permitted under maintenance-freeze rule 1: *the current domain cannot
activate*.

## Scope — one invariant

**A social action must not be discarded because an unrelated field of a
participant changed in the same frame.**

Preconditions must pin what the action actually reads and modifies, not the
whole `living_agent` blob. Two agents interacting with the same person in one
frame is normal life, not a conflict.

Out of scope: the containment guard explored in the OQ-1 arms work (it converts
a silent loss into a visible rejection — worth having, but it does not make the
action survive). Not a rewrite of the commit pipeline. One subsystem, per rule 7.

## Acceptance

**Primary metric: zero social actions discarded for `living_agent_eq_failed`
where the concurrent change did not touch a field the action depends on.**
Not a target social-event count.

Deterministic cases:

- two agents act socially on the same third party in one frame → both survive
  or one fails for a *stated, real* reason
- a genuine conflict (both modifying the same field) → one fails explicitly,
  with the field named
- participant dies mid-frame → explicit failure, named
- physical action on a participant of a social action → both survive
- replay equality holds across all of the above

Behavioural regression, the known case: person-007 selects WARN_DANGER,
person-001 cooperates with person-007 the same tick, **both commit**. No
`living_agent_eq_failed`, no silent replan to REPAY_DEBT.

Broad run, 320 ticks: rejections by reason (expect the
`living_agent_eq_failed` class to collapse), completed social actions,
singleton counts, top-3 dominance, hash determinism.

## Then, in order

1. **Leg B — day rhythm.** `is_night()` exists at `core/constants.py:171`; the
   kernel and animals use it, people do not. **Soft score multipliers, not
   behavioural bans** — a hungry person still gathers at night, an exhausted
   one still rests at noon. Target: visible settlement rhythm, not synchronised
   bedtime.
2. **Leg C — threat aftermath.** Bounded alert window per
   `animal_domain.py`'s `FLEE_PERSIST_TICKS` shape, but biasing *among* flee /
   warn / seek-ally / protect / observe. Existing candidates only; no fear
   system.
3. **Leg D — signals that do something.** 681–860 expirations per 320 ticks is
   a disconnected producer/consumer contract. Consumption requires: observable,
   unexpired, relevant to current knowledge or needs, not already acknowledged,
   provenance still valid. Prove one relay: signal → observer acts → observer
   tells another → second agent acts.
4. **Leg E — relationship causality in the Inspector.** The event that created
   a debt, its current state, decisions it influenced, repayment or expiry. Not
   a dashboard.
5. **Then Leg 1 — information sharing**, and the rest of Tier 1.

## Retarget commit

Keep it causally separable. The retarget is target *selection*; this leg is
commit *survival*. Same session is fine; distinguish them in the commit so
later behavioural changes stay attributable.
