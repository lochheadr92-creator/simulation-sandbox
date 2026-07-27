# Layer C Social Density Leg 2 — bounded second-seed diagnostic

**Purpose:** determine whether `warn`'s semantic-opportunity absence reproduces
under a different deterministic seed, or whether the Session 2 result primarily
reflects one seed-specific animal trajectory.

**This run tests seed sensitivity of the causal mechanism only.** It does not
validate the primary seed's 3,000-tick reference-family rates, concentration
figures, commit attrition, scoring margins, or long-horizon `group_state`
headroom. Two seeds can corroborate a mechanism; they cannot establish full
generalisation.

No mechanism, constant, threshold, contract, slice, tuning, world-generation,
perception, movement, role, counter, or action-selection change was made. No new
diagnostic behaviour was added — both committed probes ran unmodified on the
second seed.

---

## 1. Run record

| field | run 1 — `warn` A/B | run 2 — singleton funnel |
|---|---|---|
| commit | `f0b410e3d091a94d39255e672fc3b3cf2b2012da` | same |
| seed | `living-agents-stage6-alt` | same |
| scenario | `collective_groups` (unchanged) | same |
| probe | `_probe_layer_c_warn_opportunity.py` | `_probe_layer_c_singleton_funnel.py` |
| probe blob SHA | `b6eeefd5875b62fa33037597478b8ead3b01f662` | `1bc936fc8601482f64853998551834f99b1061cc` |
| command | `python -m tools._probe_layer_c_warn_opportunity <out> 1200 "living-agents-stage6-alt"` | `python -m tools._probe_layer_c_singleton_funnel <out> 1200 "living-agents-stage6-alt"` |
| completed ticks | **1,200 / 1,200** | **1,200 / 1,200** |
| wall time | **609.5 s** | **501.0 s** |
| exit | **0 — normal** | **0 — normal** |
| `status` | `complete` | `complete` |
| `replay_matches_entities` | true | true |
| `final_state_hash` | `8d900c97dbf349ed0ff583003963d4c9367bb836f43a31d91bb1bc33014669ca` | `8d900c97dbf349ed0ff583003963d4c9367bb836f43a31d91bb1bc33014669ca` |

Probe blob SHAs were verified identical to the committed versions before running,
so the neutrality already established at `f0b410e3` carries and was not repeated.
The two probes are independent instruments (one patches the candidate builder,
one does not) and produced **the same final state hash**, which is an incidental
cross-probe consistency check.

`warn` probe `neutrality.verdict` reads `NOT_COMPARABLE` with
`patch_is_inert: null`. That is correct behaviour, not a regression: the
automatic comparison is keyed to `ticks == 3000 && seed == living-agents-stage6`.
The per-run cross-check (c) still executed: **1,200 decisions compared, 0
mismatches.**

Conservation: **0 unbalanced identities** across all 11 actions × 3 identities.
`candidate_cap_saturated_decisions`: **0** — no pre-scoring truncation anywhere,
so stage C = stage D is proven for every decision on this seed.

---

## 2. `warn` on the second seed

### Stage A — semantic opportunities

| measure | value |
|---|---|
| scout decisions | 1,200 |
| **semantic opportunities** | **1** |
| **opportunity ticks** | **[1]** |
| opportunity rate | 0.000833 |

Co-occurrence: `animal ✗ / person ✓` **1,179**; `animal ✗ / person ✗` 20;
`animal ✓ / person ✓` **1**; `animal ✓ / person ✗` 0.
Animal observations per 1,000-tick window: **1, 0**.

### Stage B — all four conjuncts

| conjunct | true | false |
|---|---|---|
| `role_ok` | 1,200 | 0 |
| `counter_open` | **1,200** | **0** |
| `person_observed` | 1,180 | 20 |
| `animal_observed` | **1** | **1,199** |
| all four true | 1 | — |

`warn_action_count_histogram`: `{"0": 1200}` — the counter **never incremented**,
so the self-cap never closed and is not the blocker. `animal_observed` is again
the sole binding conjunct, failing 1,199 / 1,200 (99.92%).

### Stages A → H

| stage | count | conversion |
|---|---|---|
| A semantic opportunities | 1 | — |
| B all gates true | 1 | 100% of A |
| C candidate generated | 1 | 100% of B |
| D scored | 1 | 100% (score 23,329) |
| E won | **1** | 100% — `WARN_DANGER` was the winner |
| F preempted / invalidated | 0 / 0 | — |
| F **commit rejected** | **1** — `precondition.failed` | **100% of won** |
| G committed | **0** | **0%** |
| H in committed stream | **0** | — |

### Scout observation radius and distances

`effective_radius` histogram: `{1: 196, 2: 372, 3: 364, 4: 268}` — full radius 4
in 22.3% of decisions, ≥3 in 52.7%.

| distribution | min | p25 | median | p90 | max | mean |
|---|---|---|---|---|---|---|
| scout → nearest **animal** | **1** | 11 | **11** | 12 | 13 | 11.46 |
| scout → nearest animal, when not observed (n=1,199) | 3 | 11 | 11 | 12 | 13 | 11.46 |
| scout → nearest **person** | 0 | 0 | **0** | 1 | 3 | 0.20 |

`VISION_RADIUS = 4`. P3 vacuous again (terrain `{"grass": 144}`, zero
`OPAQUE_TERRAIN`); P4 never binding (limit 24, **0** hits).

### Did the animal ever enter observable range?

**Once, at tick 1, for exactly one tick out of 1,200.** At that tick the animal
was at distance 1, the scout at `effective_radius` 2 (health 350, energy 420,
daytime). After tick 1 the animal never re-entered observable range: its distance
sits at 11–13 (p25 11, p90 12) for the remaining 1,199 decisions, and its closest
non-observed approach was distance 3.

**Did `warn` convert the opportunity?** Partially — and this is where the seeds
differ. The opportunity converted through A→B→C→D→E: candidate generated, scored
23,329, and **won** its decision. It then failed at commit with
`precondition.failed`, so **`warn` committed zero times on this seed**.

---

## 3. The other seven targets on the second seed

| action | firing tick | scored | won | committed | self-cap closed | % of alive-person-ticks |
|---|---|---|---|---|---|---|
| `promise` | **2** | 1 | 1 | 1 | 1,199 | 12.7% |
| `share_information` | **4** | 4 | 4 | 1 | 1,197 | 12.7% |
| `threaten` | **8** | 1 | 1 | 1 | 1,193 | 12.6% |
| `lie` | **10** | 6 | 3 | 1 | 1,191 | 12.6% |
| `trade` | **10** | 10 | 6 | 1 | 1,191 | 12.6% |
| `apologise` | **15** | 4 | 4 | 1 | 1,186 | 12.6% |
| `reconcile` | **16** | 1 | 1 | 1 | 1,185 | 12.6% |
| `warn` | — (none) | 1 | 1 | **0** | **0** | **0.0%** |

All seven fire **exactly once**, in ticks 2–16, from a single actor each, and
never again. Every counter closes within a few ticks of its firing and stays
closed: 12.6–12.7% of alive-person-ticks is exactly one actor of eight.
Targets committed by window: window 0 — all seven; window 1 — **none**.

**The consumed-monotone-counter classification reproduces exactly.**

---

## 4. Direct comparison with the primary seed

### 4a. Mechanism invariants — reproduced on both seeds

| invariant | primary (3,000) | second (1,200) |
|---|---|---|
| `warn` semantic opportunities | 1, at tick 1 | 1, at tick 1 |
| `animal_observed` is the sole binding conjunct | 2,999/3,000 fail | 1,199/1,200 fail |
| `warn` self-cap never closes | 0.0% closed | 0.0% closed |
| nearest-animal median distance | 12 | 11 |
| nearest-animal min / max | 1 / 13 | 1 / 13 |
| nearest-**person** median distance | 0 | 0 |
| animal observations after tick 1 | **0** | **0** |
| other seven: fire once then never | ticks 1–14 | ticks 2–16 |
| other seven: counter closed ≈ 1 actor of 8 | 12.4–12.5% | 12.6–12.7% |
| P3 vacuous / P4 non-binding | yes / 0 hits | yes / 0 hits |
| conservation identities unbalanced | 0 | 0 |
| cross-check (c) mismatches | 0 / 3,000 | 0 / 1,200 |

The two worlds are independently generated — different positions, attributes and
RNG stream — yet both park the animal in the same 11–13 distance band, three
times `VISION_RADIUS`, after a single adjacent tick-1 encounter.

### 4b. Seed-sensitive quantities — differ, and are not part of the mechanism

| quantity | primary | second |
|---|---|---|
| **`warn` commits** | **1** (tick 1) | **0** (won, then `precondition.failed`) |
| scout health median / p25 | 984 / 950 | **742 / 487** |
| scout `effective_radius` = 4 | 31.6% | **22.3%** |
| deaths | 0 through 3,000 | **1 by tick ~1,200** (alive 8 → 7) |
| `group_state.payload_limit` rejections | **0** through 3,000 | **72** within 1,200 |
| `living_action.actor_unavailable` | absent | 1 |
| firing tick spread | 1–14 | 2–16 |
| `trade` scored / won | 5 / 1 | 10 / 6 |
| `lie` scored / won | 2 / 2 | 6 / 3 |

### 4c. Changed causal classification

**One primary-seed sub-claim is falsified and is corrected here.** The Session 2
report stated that `warn` *"converts every opportunity it receives, end to end,
with zero loss at every stage."* That was true on the primary seed but is **not a
general property**: on the second seed the single opportunity won its decision
and was then refused by the commit pipeline (`precondition.failed`), yielding
zero commits. Conversion efficiency is therefore a **seed-sensitive quantity**,
not a mechanism invariant.

**`warn`'s recurrence classification does not change.** It remains
*never-generated via semantic-opportunity absence*: on both seeds the counter
stays open, the role holds, people are continuously available, and the binding
failure is that the animal is not observable. The commit rejection sits
downstream of the mechanism under test and, if anything, makes `warn` scarcer
still.

No other causal classification changed. The other seven remain
*prerequisite-never-recurs via a consumed monotone counter* on both seeds.

---

## 5. Cross-seed classification

# CORROBORATED

**Evidence.** The stated criterion is "the second seed shows the same causal
pattern of persistent semantic-opportunity absence." It does:

1. **Opportunity scarcity reproduces at the same magnitude.** One opportunity in
   1,200 scout decisions against one in 3,000 — both confined to tick 1, both
   with zero animal observations in every subsequent window.
2. **The same conjunct binds.** `animal_observed` fails ≥99.9% on both seeds;
   `person_observed` fails <2% on both; `role_ok` and `counter_open` never fail
   on either.
3. **The distance distributions are near-identical across independently
   generated worlds** — median 11 vs 12, identical min 1 and max 13, identical
   p25 11 and p90 12. This is the discriminating observation: a seed-specific
   trajectory would not be expected to reproduce a distance band this closely.
4. **It reproduces despite a materially worse scout.** Seed 2's scout is more
   degraded (health median 742 vs 984, p25 487 vs 950; full radius in 22.3% of
   decisions vs 31.6%). If perceptual degradation were driving the result, the
   seeds should diverge. They do not — which independently confirms the Session 2
   finding that *distance*, not degradation, is the binding factor.

**Why not CONTRADICTED.** The second seed does not regularly present reachable
animal observations: one observation in 1,200 decisions, with the animal outside
even a healthy scout's maximum radius on 1,199 of them. `warn`'s causal
classification is unchanged.

**Why not INDETERMINATE.** The evidence points one way on every stage-A and
stage-B measure, with no conflicting signal. The one divergence (commit
rejection) is downstream of the mechanism under test and has been recorded as a
seed-sensitive quantity rather than folded into the classification.

**No new pass threshold was invented.** The classification rests on the direction
and consistency of the measurements, not on a numeric bar chosen after seeing
them. The pre-registered <20-opportunity rule still triggers on both seeds; that
is reported, not redefined.

**Limits, restated.** Two seeds corroborate a mechanism; they do not establish
full generalisation. This diagnostic says nothing about the primary seed's
reference-family rates, concentration, commit attrition, scoring margins, or
long-horizon `group_state` headroom — and the second seed's own harsher
conditions (a death by tick 1,200, 72 `group_state.payload_limit` rejections
where the primary had none through 3,000) are noted precisely because they are
*not* evidence about those quantities either.
