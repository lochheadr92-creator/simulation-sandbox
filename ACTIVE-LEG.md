# Active Leg A — social actions must survive commit

Declared 2026-07-28. Supersedes the "plan continuation repair" framing, which
was built on a wrong diagnosis. Corrected below with the evidence.

---

## STATUS: PASS WITH LIMITATIONS — implemented at `d8f00eb6`, independently verified

Finalised 2026-07-28: open item 2 resolved (the residue is a pin-capture
mismatch, not reciprocal pairs), item 1 deferred to the retarget leg with the
fix point located, item 3 closed as a documented known limitation. See
"Finalise 2026-07-28" below.

Verified on a clean `git archive` of `d8f00eb6` (not the implementer's worktree,
not the dirty main checkout): **33 passed in 111.6s** across
`test_frozen_baseline_hashes`, `test_stage6d_social_relationships`,
`test_component_ownership_invariants`, `test_stage6e_living_settlement`.
Replay equality holds; the hash pin moved in the same commit with census
evidence, per `ENGINE-CONSTITUTION.md`.

**What the fix achieved (VERIFIED, 320 ticks, clean tree):**

| | before | after |
|---|---:|---:|
| `living_agent_eq_failed` rejections | **1263** | **0** |
| accepted events | 4,868 | 5,088 |
| `cooperate` | 55 | **152** |
| `repay` | 44 | **94** |
| `request_help` | 130 | 57 |
| top-3 dominance | 74.6% | 70.6% |
| total rejections | 1,422 | 1,320 |

The whole-blob false positive is gone, and disjoint concurrent social actions
now compose instead of colliding. Rejections that remain are path-named and
diagnosable.

**LIKELY (not verified): the help loop is closing.** `request_help` fell 73
while `cooperate` rose 97 — consistent with requests no longer repeating
because the response finally commits. First sign of a social loop completing
rather than churning. Needs a causal check, not a correlation.

### Open item 1 — the actor-side write was not narrowed

(DEFERRED 2026-07-28 to the retarget leg — the live fix point is the domain's
cognition-carrier write, not the builder; see the Finalise block below.)

The target write became a merge spec, but the **actor** still writes
`updates[actor_id]["living_agent"] = actor_state` — the whole blob, from a
frame-start base — in the base update and in all three commitment branches.
The actor's whole-blob *pin* was removed at the same time.

So the actor side now writes wholesale with nothing guarding it: if another
agent merged a record into that actor's blob earlier in the same frame, the
actor's own write silently reverts it. This is the "visible rejection becomes
real data loss" trade this leg exists to avoid, currently live on one side.

Fix: apply `_living_agent_write_diff` to the actor write too, and pin whatever
the actor genuinely depends on beyond the counterpart record.

### Open item 2 — one hot record carries 91% of the remaining rejections

(RESOLVED 2026-07-28 — mostly not reciprocal pairs and not item 1; the pinned
record is perception-volatile. See the Finalise block below.)

`rejection_census` after the fix:

```
living_agent.relationships.person-000_eq_failed   1049
living_agent.relationships.person-001_eq_failed     52
living_agent.relationships.person-002_eq_failed     17
...all others                                    <= 12
condition_eq_failed                                156
```

1049 of 1155 path-named rejections land on a single agent's record.
The commit message attributes the residue to reciprocal pairs — but the
census's own `reciprocal_pairs` field is `[]` in **both** arms, so that
explanation is unconfirmed by the instrument that was built to test it.
Open item 1 is the obvious suspect and should be ruled in or out first.

### Open item 3 — `warn` went 1 → 0

(CLOSED 2026-07-28 as a documented known limitation — see the Finalise block
below.)

The behaviour that started this investigation is now extinct in the organic
320-tick baseline. The fixture tests pass; the world produces none. Seven
singletons still fire once, `warn` fires zero times. The fix multiplied the two
already-common social actions and did nothing for the eight rare ones.

This does **not** invalidate the leg — the commit-survival defect was real and
is fixed — but the leg's own success test is not met, and the singleton family
remains the actual product problem.

---

### Finalise 2026-07-28 — items 1–3 closed out

Re-verified on a clean `git archive` of `a04939b7` (not the dirty checkout):
the three analysis runs below each reproduced the pinned trajectory exactly —
final hash `e80743460e46be4cf73086854988baa9aa92de27cbff9b5e777430497a0317b2`,
5,088 accepted, 1,320 rejected, replay equality True. Evidence:
`memory/evidence/frozen-hash/leg-a-2026-07-28-hot-record-{r1,v2,v3}.json`.
No code changed in this close-out, so the frozen constants do not move.

**Item 1 — DEFERRED to the retarget leg; the live fix point is located and it
is not in the social builder.** Every per-entity proposal — social or not —
passes through the settlement domain's cognition carrier, which rewrites
`actor_update["living_agent"]` wholesale from a frame-start base
(`living_settlement_domain.py:777` @ `a04939b7`; `:810` in the working tree
with the uncommitted retarget). Narrowing only the builder's actor write feeds
a `{__merge__}` spec into
`resulting_state = copy.deepcopy(actor_update.get("living_agent") or state)`
(`:752`), and `derive_internal_pressures` immediately subscripts
`state["traits"]` (`living_agent_cognition.py:432`) — the harness would crash
on the first social tick (VERIFIED by code reading; deliberately not run). The
real fix is at the composition point: diff the enriched blob against the
frame-start base and emit a merge spec at `:777`. That file holds Ryan's
uncommitted Leg-2 R1 retarget, so this handoff is his to pick up.

**Item 2 — RESOLVED: the residue is mostly not reciprocal pairs, and item 1
was never the cause.** Three census rounds over the pinned trajectory:

- 233/1155 (20%) have an accepted same-tick reciprocal action that wrote the
  pinned record — the genuine class the pin exists for (VERIFIED, r1).
- 922/1155 have **no same-tick writer of the record on the actor's blob at
  all** (VERIFIED, v2 writer census: only 233 same-tick `social_cooperate` /
  `social_repay` / `social_request_help` merge-spec writes found).
- 955/1155 (83%) are actor-side pins whose pinned **value** is stamped with
  the rejection tick itself: the pin was captured from the domain's
  perception-ENRICHED working actor blob
  (`working_actor["living_agent"] = state`, after
  `apply_observed_social_information`), while commit revalidation compares it
  against the PRE-perception committed record. When the actor observed a fresh
  signal from the target, the two can never match — the proposal is
  self-doomed at build time (VERIFIED, v3: `pin_stamped_this_tick` = 955;
  stale-stamp genuine class ≈ 195; 3 target-side, the target's own
  earlier-committing enriched write).

So what "writes `person-000`'s record 1,049 times" is mostly **nothing
in-frame**: person-000 is the most-observed agent (281 social touchpoints vs
143 next — VERIFIED, r1 activity census), so every observer's record about it
is refreshed by perception nearly every tick, self-dooming nearly every action
aimed at it — visible as stuck loops (person-001 `cooperate`→person-000
rejected at ticks 90–101 consecutively). The census's `reciprocal_pairs: []`
was an accepted-events-only scan, structurally blind to pairs whose second
half was rejected. Correction on the record: the `d8f00eb6` commit message's
attribution of all 1,155 to "genuine reciprocal collisions" was wrong for the
~83% — that class is the pin-capture mismatch above, and it is corrected here.
The fix is the pin-capture contract — capture the actor-side record pin from
the committed frame-start blob, not the enriched working blob — which lives at
the same builder↔domain boundary as item 1, in the same file, and goes with it
to the retarget leg. Projected residue after both fixes: ~230 honest
rejections (LIKELY, projected from the census partitions — not run).

**Item 3 — CLOSED as known limitation.** Exactly ONE `social_warn` proposal is
generated in the entire post-fix 320-tick world (tick 2, person-007 →
person-001), and it lost the genuine reciprocal collision to person-001's
committed cooperate (pinned `None` vs the record the cooperate created —
VERIFIED, r1 `warn_proposals_all`). So `warn` 1 → 0 is no longer a
commit-survival problem: candidate GENERATION is the bottleneck — one
candidate in 320 ticks — and the single generated candidate was legitimately
contested. Per the finalise brief, no scores, thresholds, or priorities were
tuned; the singleton family is a separate domain problem.

---

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

## Implementation spec (located 2026-07-28, ready to execute)

**The defect, exactly.** `domains/living_agent_social.py:326-336`:

```python
touched = [actor_id]
preconditions = [
    {"entity_id": actor_id, "field": "alive",        "op": "eq", "value": True},
    {"entity_id": actor_id, "field": "living_agent", "op": "eq", "value": actor.get("living_agent")},
]
if target:
    updates[target_id] = {"living_agent": target_state}     # whole-blob WRITE
    preconditions.extend([
        {"entity_id": target_id, "field": "alive",        "op": "eq", "value": True},
        {"entity_id": target_id, "field": "living_agent", "op": "eq", "value": target.get("living_agent")},
    ])                                                       # whole-blob READ
```

Compare `build_physical_action_proposal` (`living_agent_actions.py:261`), which
pins `alive` only.

**Why narrowing the precondition alone is wrong.** `core/mutations.py:15`
`apply_mutation` does `entities[eid].update(updates)` — a top-level field
replace. `living_agent` is one field holding a dict, so the social action
*writes the whole blob back* from a frame-start base. Loosen the precondition
without changing the write and a concurrent change to any other sub-key is
silently clobbered: we would trade a visible rejection for actual data loss.
Strictly worse.

**What the social action actually changes (VERIFIED, decisive).**
`apply_relationship_consequence` (`living_agent_social.py:77`) modifies exactly
one path. Its own CORE-PERF-01 comment at lines 89–92 states it:

> the only per-key write is `relationships[subject_id] = relation`
> (a whole-record replacement)

And in `updates[actor_id]`, `action` / `plan` / `current_goal` are already
separate top-level fields. **So the only reason either side writes
`living_agent` at all is one relationship record.**

Two agents acting on the same person in one frame therefore write
`relationships[person-001]` and `relationships[person-004]` — provably disjoint
keys. The whole-blob CAS is a false positive by construction. That is why 100%
of rejections are this one failure.

The genuine collision is narrow and worth keeping: a reciprocal pair in the
same tick (007→001 and 001→007) really does write both relationship records
twice. Pinning the *path* surfaces that honestly as one rejection instead of
killing both.

**So the fix is: shrink the write, then the pin follows** — three touch points,
not four:

1. `core/commit_pipeline.py:120` `evaluate_preconditions` — accept an optional
   `path` on a condition and compare the value at that path inside the field's
   dict rather than the whole field. No `path` ⇒ today's behaviour exactly.
   Failure string must name the path so rejections stay diagnosable.
2. `core/mutations.py:15` `apply_mutation` — a merge semantic for dict-valued
   field updates so a proposal can write only the sub-keys it changed. Keep
   whole-field replace as the default; merge is opt-in per update.
3. `domains/living_agent_social.py:326-336` — **this is the actual fix.** Both
   sides write `living_agent.relationships[counterpart]` only, not the blob.
   The whole-blob `eq` precondition goes; in its place, pin that one
   relationship record. `alive` stays on both sides.

`domains/living_settlement_domain.py:548` `_replace_living_preconditions`
becomes vestigial once no whole-blob `living_agent` conditions are emitted —
check it, don't pre-emptively rewrite it.

Order matters: **do 3 first with the write narrowed and no pin at all**, run
the 320-tick comparison, and see whether any genuine reciprocal collision
actually occurs in practice. If it does, add 1 and 2 to catch it honestly. If
it never does, 1 and 2 may not be needed at all — which would make this a
single-file change.

Determinism note: merge order must be deterministic (sorted keys) or invariant
4 breaks. The frozen hash **will** move — more actions commit. Update the pin
in the same commit and say what moved it, per `ENGINE-CONSTITUTION.md`.

Start on a clean context. The hash move plus regression suite is real work even
if step 3 turns out to be the whole fix.

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
