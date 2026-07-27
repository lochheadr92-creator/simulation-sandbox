# Layer C Social Density Leg 2 — Session 2 report: `warn` stage A/B

**Plan:** `memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md` §Phase 1,
Session 2. **Definition under test** (committed for criticism, then approved):
`leg2_session2_warn_opportunity_definition.md`. **Scope:** `warn` only.

**Run:** `collective_groups`, seed `living-agents-stage6`, 3,000 ticks, commit
`77b8287d` in a detached worktree at HEAD. `status: complete`,
`replay_matches_entities: true`, 1,700 s. Evidence:
`leg2_session2_warn_opportunity_3000.json`.

---

## 1. Instrumentation neutrality — VERIFIED PASS

Approach (a) — the probe monkeypatches `build_settlement_candidates` (restored in
a `finally`) so it reads the exact `delta` the gate reads.

| check | result |
|---|---|
| Session 1 **unpatched** hash @3,000 | `fb032eaf6fa5041cea73e6172943ce31203809c1c3dab90b893aba8025597d7a` |
| This **patched** run's hash @3,000 | `fb032eaf6fa5041cea73e6172943ce31203809c1c3dab90b893aba8025597d7a` |
| `patch_is_inert` | **true** |
| Cross-check (c): decisions compared / mismatches | **3,000 / 0** |
| `verdict` | **NEUTRAL** |

Byte equality over exactly the measured window, against a run made before the
patch existed. Cross-check (c) confirms the patch-captured observation count and
attention profile equal the domain's own `diagnostics[...]["perception"]` record
on all 3,000 decisions — so the probe read what the gate read, which is the
failure mode independent recomputation would have hidden.

### P3 and P4 established, not assumed

- **P3 (line of sight):** the generated terrain is `{"grass": 144}` with **zero**
  `OPAQUE_TERRAIN` tiles. `P3_line_of_sight_can_block: false`. Vacuous in this
  scenario, by scan rather than by intuition.
- **P4 (entity budget):** entity observations per decision median 7, max 7,
  against a declared limit of 24. **0 budget hits.** Never binding.

---

## 2. Stage A — semantic opportunities

Per the ratified definition: a tick is a `warn` semantic opportunity iff the
scout, alive and due, observes **both** an animal and another person under
P1–P5. Role and self-cap are excluded from stage A by design.

| measure | value |
|---|---|
| scout decisions | 3,000 |
| **stage A semantic opportunities** | **1** (tick 1) |
| opportunity rate | 0.000333 |

**Co-occurrence of the two perception conjuncts**

| animal observed | person observed | decisions |
|---|---|---|
| ✗ | ✓ | **2,974** |
| ✗ | ✗ | 25 |
| ✓ | ✓ | **1** |
| ✓ | ✗ | 0 |

Per 1,000-tick window — animal observations: **1, 0, 0**. Person observations:
975, 1,000, 1,000. Two thousand consecutive scout decisions across windows 1 and
2 contain **zero** animal observations.

## 3. Stage B — all four conjuncts, independently

Never first-false-only, per the plan.

| conjunct | true | false |
|---|---|---|
| `role_ok` | 3,000 | 0 |
| `counter_open` | **3,000** | **0** |
| `person_observed` | 2,975 | 25 |
| `animal_observed` | **1** | **2,999** |
| all four true | 1 | — |

`warn_action_count` histogram: `{0: 1, 1: 2999}` — the counter went 0→1 at tick 1
and stayed at 1 against a cap of 2. **The self-cap never closed and is not the
blocker**, confirming Session 1's finding with the gate now directly instrumented.

**`animal_observed` is the sole binding conjunct**, failing 2,999 of 3,000
decisions (99.97%).

## 4. Attribution — distance, not degradation

| measure | nearest animal | nearest person |
|---|---|---|
| median distance | **12** | **0** |
| mean | 11.56 | 0.21 |
| p25 / p90 | 11 / 12 | 0 / 1 |
| min / max | 1 / 13 | 0 / 3 |
| median when NOT observed | 12 (n=2,999) | 2 (n=25) |

`VISION_RADIUS = 4`. The animal sits at a median distance of **12 — three times
the maximum possible radius**. People are typically on the same tile as the
scout (median 0); the camp is packed.

**Perceptual degradation is NOT the explanation, and this corrects the emphasis
in the definition document.** That doc computed the scout's genesis profile
(health 350, energy 420, injured ⇒ `effective_radius` 2) and framed it as the
likely constraint. Measured over the run, the scout heals:

| | genesis | run median | run max |
|---|---|---|---|
| health | 350 | **984** | 1,000 |
| energy | 420 | **990** | 1,000 |

`effective_radius` histogram: `{1: 281, 2: 792, 3: 978, 4: 949}` — full radius 4
in 949 decisions, ≥3 in 1,927 of 3,000. `radius_penalty` components show injury
receding (`health_penalty` 0 in 2,572; `fatigue_penalty` 0 in 2,995) and the
residual penalty coming from night (750 decisions) and weather (1,500). **Even at
full radius 4 the animal at distance 11–13 is unreachable.** The single
opportunity occurred at the scout's *worst* radius (2, health 350, tick 1)
purely because the animal was then at distance 1.

One margin effect, recorded for completeness: `nearest_animal_distance_when_not_observed`
has min 3, so on at least one occasion the animal was within a healthy scout's
radius but outside the scout's radius at that moment. Marginal against a median
of 12; noted, not load-bearing.

**The flee-rule hypothesis is retired.** The definition doc recorded, explicitly
as unclaimed, that `animal_domain.py:82`'s flee behaviour might cause the
scarcity by oscillating the animal in and out of range. Measured: the animal is
not oscillating. It is parked at distance 11–13 (p25 11, p90 12) for the entire
run. The hypothesis is refuted by the instrument built to allow refuting it.

## 5. Funnel with stage A filled in, and classification

| stage | count | conversion |
|---|---|---|
| A semantic opportunities | 1 | — |
| B all gates true | 1 | 100% of A |
| C candidate generated | 1 | 100% of B |
| D scored | 1 | 100% |
| E won | 1 | 100% |
| F preempted / invalidated / rejected | 0 | — |
| G committed | 1 | 100% |
| H in committed replay-visible stream | 1 | 100% |

**`warn` converts every opportunity it receives, end to end, with zero loss at
every stage. It receives one in 3,000 ticks.**

> **CORRECTED 2026-07-27 by the second-seed diagnostic**
> (`leg2_seed2_diagnostic_report.md`). The conversion claim above holds on THIS
> seed but is **not** a general property. On seed `living-agents-stage6-alt` the
> single opportunity converted A→B→C→D→E — candidate generated, scored 23,329,
> and won its decision — then failed at commit with `precondition.failed`,
> giving **zero** `warn` commits. Conversion efficiency is a **seed-sensitive
> quantity**, not a mechanism invariant.
>
> The classification below is **unaffected and was CORROBORATED** cross-seed:
> the counter stays open on both seeds, `animal_observed` is the sole binding
> conjunct on both (≥99.9% failure), and the nearest-animal distance band is
> near-identical (median 11 vs 12, same min 1 / max 13). The commit rejection
> sits downstream of the mechanism under test.

**Classification: never-generated — semantic-opportunity absence.** This is a
*different mechanism* from the other seven singletons. Those are
prerequisite-never-recurs via a **consumed monotone counter** (an internal gate
that closes permanently). `warn`'s counter never closes; its prerequisite fails
because **the world stops presenting the situation** — the `animal-threat` entity
relocates away from the camp and stays there. Same funnel shape, different cause.

Explicitly NOT concluded: that the pathway is broken. It is measurably intact and
perfectly efficient. Low volume has not been converted into "pathway broken"
anywhere in this report.

## 6. Evidence-sufficiency verdict

Stage A is now measured, so the plan's pre-registered rule is evaluable for the
first time: **1 semantic opportunity at 3,000 ticks is below the threshold of 20,
so the rule triggers extension to 5,000.**

**Extension to 5,000 was NOT run.** Recommendation, offered for the user to
override:

- **The horizon is saturated; the seed is not.** Windows 1 and 2 already contain
  2,000 consecutive scout decisions with zero animal observations, and the
  animal's distance distribution is tight and stationary (p25 11, median 12,
  p90 12). Another 2,000 ticks of the same configuration would add
  approximately 2,000 more non-opportunities and could not plausibly reach 20.
- **The informative extension is a different seed, not a longer run.** The
  binding variable is one animal's trajectory in one world. A second seed varies
  it; a longer horizon does not. The pre-registered comparison seed never ran
  (Session 1 §6, three terminated attempts).

**Verdict: `warn` — MECHANISM VERIFIED, GENERALISATION INSUFFICIENT.** The funnel
is complete, conservation holds, and the binding conjunct is identified with the
gate directly instrumented and the instrument proven byte-neutral. What remains
unsupported is whether "the animal leaves and does not return" is a structural
property of the scenario or an artifact of this seed's animal trajectory. That
distinction matters more than usual here: a contract addressing a
seed-specific wandering animal would be very different from one addressing a
structural feature.

## 7. Scope

No mechanism, constant, contract change, behavioural slice, utility tuning, new
canonical state, or fix is proposed. `animal_domain` behaviour was read
(one line) and is not modified. Stage 5E conflict/escalation remains out of
scope.
