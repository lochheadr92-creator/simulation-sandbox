# Layer C Social Density Leg 2 — Session 2, step 1: `warn` semantic-opportunity definition

**Status: PROPOSED FOR CRITICISM. No instrument built. Nothing measured.**

**Plan:** `memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md` §Phase 1,
Session 2 — "semantic-opportunity definitions built only for actions Session 1
classifies C≈0. Each definition derived from the action's own prerequisite
semantics, evaluated against world state, **documented per action so it can be
criticised**."

**Scope:** `warn` only, per the user's selection. Session 1 resolved the other
seven target actions to a measured monotone counter; `warn` was the sole
INSUFFICIENT EVIDENCE verdict.

**Why `warn` and only `warn`** (from `leg2_session1_funnel_report.md`, VERIFIED):
its self-cap is 2, the scout consumed 1, so the gate was **open for 100% of
24,000 alive-person-ticks**; `animal-threat` was alive for all 3,000 ticks; and
`warn` was still generated exactly once, at tick 1, winning and committing with
zero preemption. The blocker is upstream of stage C.

---

## 1. The prerequisite, verbatim

`domains/living_settlement_domain.py:401` (VERIFIED, commit `77b8287d`):

```python
if role == "scout" and animals and visible_person_ids and _action_count(entity, "warn") < 2:
```

with, from the same function:

```python
animals            = _observation_map(delta, "animal")   # observations of type "animal"
people             = _observation_map(delta, "person")   # observations of type "person"
visible_person_ids = sorted(people)
```

Four conjuncts. Two are cheap canonical-state reads (`role`, the counter) and
were already measured in Session 1. **The two perception conjuncts are the
unmeasured surface**, and they are what this definition is about.

## 2. What makes an entity appear in `delta["observations"]`

`domains/living_agent_cognition.py:162-258`, `perceive_living` (VERIFIED). For a
subject `s` to be observed by observer `o` at tick `t`, **all** must hold:

| # | Condition | Source |
|---|---|---|
| P1 | `s` has a `position` | `:186-189` |
| P2 | `manhattan(pos_o, pos_s) <= effective_radius` | `:190-195` |
| P3 | `_has_line_of_sight(pos_o, pos_s, terrain)` — Bresenham, blocked by `OPAQUE_TERRAIN` | `:202-203` |
| P4 | entity budget not spent: `entity_count < LIMITS.perceived_entities_per_observation` (24) | `:208-209` |
| P5 | `_visible_properties(s)` is non-empty | `:211-213` |

where (`:80-95`, `:174-175`):

```
radius_penalty   = (1000-energy)//300 + (1000-health)//350
                 + weather.visibility_penalty (clamped 0..4)
                 + (1 if night and not has_light else 0)
effective_radius = max(1, VISION_RADIUS - radius_penalty)      # VISION_RADIUS = 4
```

Three facts that bound the definition's practical content, all VERIFIED:

- **P3 is vacuous in this scenario.** `OPAQUE_TERRAIN = {"wall","cliff","dense_forest"}`;
  `collective_groups` inherits `ground_terrain: "grass"` with `water_blob_count: 0`.
  No opaque tile exists, so line-of-sight never blocks. *It is still evaluated and
  counted* — a vacuous conjunct asserted rather than measured is how instruments
  lie.
- **P4 is not binding.** `person` and `animal` are not in `OBJECT_TYPES`, so both
  consume the 24-entity budget; the world holds 8 people and 1 animal. Counted
  anyway, for the same reason.
- **P5 is a real conjunct.** For `person` it requires a non-empty
  `base["person_sightings"][id]`, for `animal` a non-empty
  `base["animal_sightings"][id]`, both produced by `perceive()`. Non-emptiness is
  NOT assumed here; it is measured.

### The scout is the camp's most degraded perceiver

`scenarios/living_settlement.py:46-47` gives `person-007` (the only `scout`)
`health: 350`, `energy: 420`, `injury.severity: 650` at genesis. So at genesis,
clear weather, daytime:

```
radius_penalty   = (1000-420)//300 + (1000-350)//350 + 0 + 0 = 1 + 1 = 2
effective_radius = max(1, 4 - 2) = 2
```

At night (`is_night(t) ⇔ t % 100 >= 60`, i.e. **40% of all ticks**) the penalty is
3 and `effective_radius = 1`. Bad weather can add up to 4 more, with the floor
holding it at 1. A healthy agent perceives at radius 4; the scout at 1–2.

`warn` requires an animal **and** a person simultaneously inside that radius.

### The definition reproduces the single observed firing

`collective_groups` positions (`scenarios/collective_groups.py:30-39`): scout
`person-007` at (6,6); `animal-threat` at (7,6), distance 1; `person-001` at
(5,6), distance 1. Both within `effective_radius = 2`. Session 1 measured `warn`
committed at tick 1 **targeting `person-001`** — the lowest-sorted visible person.
The derivation reproduces the observed event, which is the minimum bar for
trusting it. It does not yet explain the 2,999 ticks that follow.

---

## 3. Proposed definition

> **A tick `t` is a `warn` SEMANTIC OPPORTUNITY iff, for the scout `o`, evaluated
> against the pinned entity frame at `t`:**
>
> - **A0** `o` is alive and due for decision at `t`;
> - **A1** ∃ an entity `a` with `type == "animal"` satisfying P1–P5 for `o` at `t`;
> - **A2** ∃ an entity `p ≠ o` with `type == "person"` satisfying P1–P5 for `o` at `t`.

**Deliberately excluded from stage A:** `role == "scout"` and
`_action_count(warn) < 2`. Those are stage-B gates and are already measured. Stage
A asks only *"did the world present the situation `warn` is about?"* — a scout
seeing a person and a threat at once. Folding the counter into A would make a
consumed gate look like an absent opportunity, which is the exact conflation the
plan's classification scheme exists to prevent.

**Deliberately NOT part of the definition:** the animal being *alive*. `warn`'s
code gate does not test `alive`; it tests observability. A dead animal that is
still observable would satisfy the real gate, so the definition tracks the gate,
not my intuition about it. (`animal_alive_ticks = 3000` was measured in Session 1,
so this is not load-bearing here — but the definition should not silently be
stricter than the code it models.)

### Stage-B gate instrumentation to pair with it

Per the plan, **all** gate-failure counts, never first-false-only. Per decision of
the scout, record independently: `role_ok`, `animal_observed`, `person_observed`,
`counter_open`, plus the co-occurrence matrix of the two perception conjuncts, so
"animal but no person" is distinguishable from "person but no animal" and from
"neither". Additionally record per decision: `effective_radius`,
`radius_penalty` and its four components, `night`, scout `health`/`energy`,
`min_distance_to_any_animal`, `min_distance_to_any_person` — all read from the
frame, so a failure can be attributed to *distance* versus *degradation* rather
than merely observed.

---

## 4. The instrumentation choice — the neutrality decision, unresolved

The plan calls in-loop A–B probes "the entire neutrality risk surface." Three
options, with the tradeoff stated rather than chosen:

| | Approach | Neutrality | Fidelity |
|---|---|---|---|
| **(a)** | Monkeypatch `build_settlement_candidates`, read the `delta` the builder actually saw (Leg 1's pattern) | Patches live code. Leg 1's shadow achieved byte-identical hashes, so precedent exists — but it must be re-proven | **Exact.** Measures the very object the gate reads |
| **(b)** | Recompute P1–P5 independently from canonical `entities` each tick, no patch | Neutral by construction, like Session 1's probe | Risks silent divergence from the builder's `delta`. A definition that disagrees with the code it models is worse than no measurement |
| **(c)** | Use the `perception` row already in `diagnostics` (`{version, count, attention}`) | Neutral by construction; already returned and discarded | **Insufficient alone.** Gives `attention`/`radius_penalty` and a total observation count, but no per-type breakdown — cannot separate A1 from A2 |

My recommendation, offered for criticism rather than acted on: **(a) plus (c) as a
cross-check** — patch to read the real `delta`, and independently assert that the
patched run's `perception.count` and `attention` match the unpatched run's,
alongside the standard byte-identical-hash neutrality gate that Session 1 already
established as the standard. (b) alone would let a subtly wrong reimplementation
of P1–P5 masquerade as a finding about the world.

**Not decided. Not built.**

---

## 5. What this definition would settle, and what it cannot

**Would settle:** whether `warn`'s recurrence blocker is *opportunity scarcity*
(A1∧A2 rarely co-occurs) or something else entirely. If A1∧A2 holds often while
C stays at 1, the gate-level story is wrong and the finding moves elsewhere —
that outcome would refute §2's framing, and the instrument is built to allow it.

**Cannot settle:** *why* the opportunity is or is not scarce. Perceptual
degradation, agent dispersal, and the animal's flee behaviour
(`animal_domain.py:82`, "person within flee radius; fleeing") are candidate
explanations; the recorded distances and radius components would rank them, but
attribution is a further step and is **not** claimed here.

**Explicitly not claimed:** that the animal's flee rule causes the scarcity. That
is a live hypothesis suggested by a one-line code read, nothing more. It is
recorded so the measurement can refute it.

## 6. Carried-forward caveat

`warn`'s INSUFFICIENT EVIDENCE verdict rests on **one observation in one seed**.
The pre-registered comparison seed did not run (§6 of the Session 1 report). This
definition is therefore being designed around a single-seed observation, which
the user accepted when selecting `warn`-only scope over second-seed-first. It is
restated here so it cannot be lost between sessions.
