# Surplus Pass — Phase 1 of the Revised Domain Roadmap

Carry capacity, home storage, and basic surplus behaviour for the people
stack (the current Needs + Resource flow: `people_domain` /
`people_planning` / `people_utility`). No emotion, social, culture, market,
or profession machinery is touched. Everything below flows through the
standard Core proposal pipeline; no domain mutates state directly.

## What was added

### Canonical state (Tier A — inside the frozen hash)

| Spec field | Implementation | Notes |
|---|---|---|
| `carry_capacity: float` | existing `inventory_capacity` (int, default 30) | Declared at genesis since Phase 2 but **never enforced**; now enforced for surplus-enabled persons on every gather path (`gather`, `gather_excess`) and on `retrieve`. Legacy gathers for non-surplus persons stay unbounded — legacy scenarios are byte-identical. |
| `current_carry: Dict[resource_id, float]` | existing `inventory` (wood) + `food_inventory` (meat) scalars, mirrored into `carried_resources` on every proposal | Quantities are ints, matching house convention. |
| `storage_location: (x, y)` | new `storage_location: {"x", "y"}` person field | Minted at spawn tile by the generic genesis knob `assign_storage_location` (`world/generator.py:153`). Write-once; never rewritten. Only persons with this field are "surplus-enabled" — this is the gate that keeps every legacy scenario byte-identical. |
| `stored_resources: Dict[resource_id, float]` | new `stored_resources: {"wood", "food"}` person field | Entity-level store owned by the person, deposited/withdrawn only while standing on `storage_location`. Single writer (`people_domain`), whole-map CAS on store/retrieve. |
| `resource_ownership: agent_id` | stamped on tree/carcass stocks by `gather_excess` commits | Informational "last gatherer of record"; no access control reads it. Ownership of gathered units is otherwise intrinsic (per-agent carry/store maps) and fully traceable through the accepted-event log. |

### Proposal types (all submitted to Core; ordering/acceptance unchanged)

| `proposal_type` | Trigger | Effect |
|---|---|---|
| `gather_excess` | hunger < 500, known source with stock ≥ 20, carry room > 0 | Multi-tick gather bounded by carry room; stamps `resource_ownership`. |
| `store` | carry total ≥ 12 and movable surplus ≥ 4, standing on home tile | Deposits everything above keep thresholds (2 wood, 4 meat) into `stored_resources`. |
| `retrieve` | hunger ≥ 550, stored meat > 0, no carried meat, standing on home tile | Pulls up to 3 meat (bounded by carry room). |
| `offer_trade` | complementary-surplus partner within Manhattan 2 | Atomic equal-quantity barter (2 for 2) between the two parties' carried stocks. Barter only — no obligation ledger. |

Generation uses only the pinned frame + the existing
`frame.rng.stream(f"people.{eid}.decision.{tick}")` stream (seeded by tick +
agent id); no new RNG call sites were added. Commit ordering, validation,
and acceptance are the unmodified Core pipeline. The trade contract rides a
new conditional `trade` metadata key (same pattern as `association_update`),
so content hashes of every existing proposal family are unchanged, and a
Core-owned `validate_people_trade` (modelled on `validate_food_transfer`)
re-derives both parties' expected mutations from live state.

### Utility integration (`people_utility.score_candidates`)

- `GATHER_EXCESS`: severity 60–190 scaled by satiation + stock abundance;
  gated off when hunger ≥ 500, so eat-when-hungry always wins. Availability
  is zero without a nearby abundant source.
- `STORE`: severity rises with carry load (40 + 4·load, capped 240),
  discounted by path distance to home.
- `RETRIEVE`: severity = hunger, discounted by path distance to home; only
  available with stored meat and an empty meat carry.
- `OFFER_TRADE`: flat 320 (+40 when the received resource is meat and
  hunger ≥ 400), only available with a complementary partner in range;
  sized to beat the satiated-idle alternatives (~300–420) inside its rare
  availability window.
- Satiated surplus persons with no meat stock also get a HUNT severity
  floor (520 — must clear `_score`'s `W_RISK`-weighted hunt risk penalty of
  ~350 and still beat GATHER_EXCESS) — meat is the retrievable/tradable
  food, and a wood-only economy never produces complementary trade profiles.
  Surplus-enabled hunters may also target *injured* fleeing animals
  (finishing wounded prey); healthy fleeing animals stay untargetable.
  The floor is suppressed while a freshly-sighted known carcass still holds
  meat (`CARCASS_KNOWLEDGE_STALE_TICKS = 25`, covering a full ~20-tick decay
  cycle): agents harvest what is already dead before killing more, which
  keeps the kill rate sustainable.

### Enabling fix (pre-existing defect, required for any of this to work)

`people_domain` plan-step transitions emitted the raw `start_step` action
(no `actor_id`), so `validate_living_action_proposal` rejected **every**
transition proposal with `living_action.invalid_actor` and every multi-step
plan deadlocked one tile from its target (verified on HEAD: `basic_survival`
60-tick = 340 such rejections, zero eat/drink events). The transition path
now wraps the action with `compat_action` like every other path
(`people_domain.py`). This changes people-stack trajectories by letting
intended behaviour commit; it affects no frozen pin (the only literal
baseline, `living_settlement` 320, does not enable the people domain).

### Scenario

`surplus_forage` (`backend/scenarios/surplus_forage.py`): 26×26 grassland,
1 lake, 20 people, 36 animals, 34 trees, `assign_storage_location: true`,
domains `["ecology", "lifecycle", "people", "animal"]`.

## Contract tiers

- **Tier A — deterministic contracts** (`backend/tests/test_surplus_pass.py`,
  18 tests): every proposal type through real activation + real
  `run_commit_frame`; capacity bound; ownership stamp; keep thresholds;
  trade validator reason codes (`trade.invalid_terms`,
  `trade.invalid_ownership`, `trade.invalid_scope`,
  `trade.participant_missing`, `trade.participant_not_living`,
  `trade.out_of_range`, `trade.insufficient_surplus`,
  `trade.invalid_mutation`, `trade.invalid_preconditions`); duplicate-trade
  replay safety; two-identical-runs hash equality over event hashes, frame
  hashes, and final entities on `surplus_forage`.
- **Tier B — organic invariants**
  (`backend/tests/test_surplus_pass_invariants.py`): one shared 1,000-tick
  census, asserting: ≥20% of 20 agents store surplus by tick 500; ≥5
  `offer_trade` events in 1,000 ticks; per-agent visit-frequency entropy
  shows home-tile attraction plus foraging spread (median home share ≥ 3%,
  median unique tiles ≥ 6, median normalized entropy ≤ 0.93).

## Test commands

Run from `backend/` with the repo-root venv:

```
# Tier A (fast fixtures + two 40-tick traces)
../.venv/Scripts/python.exe -m pytest tests/test_surplus_pass.py -q

# Tier B (one shared 1,000-tick census; slow)
../.venv/Scripts/python.exe -m pytest tests/test_surplus_pass_invariants.py -q

# Headless scenario run
../.venv/Scripts/python.exe -m tools.living_agent_harness --scenario surplus_forage --ticks 500 --seed surplus-smoke
```

## Performance

- Benchmark guardrail (`collective_groups`, 500 ticks, seed
  living-agents-stage6): **367.6 ms/tick** final (220.3 ms/tick on an
  earlier same-tree run; run-to-run variance on a shared machine, both far
  under the 1,200 ms/tick limit).
- `surplus_forage` 500-tick: **~2,848 ms/tick**. Flag, not a regression:
  tick cost scales with accepted events/tick (~70 here — hunting, storing,
  trading — vs ~7 in collective_groups), and each accepted event re-hashes
  world state (`spliced_snapshot_json`). This is pre-existing engine cost
  amplified by the people stack now committing as designed (see enabling
  fix); no new proposal families were added beyond the four here. Per the
  pass's own guardrail, treat this as the rehashing-cost signal to watch
  before adding further proposal types to this scenario.

## Measured emergence (seed surplus-smoke / surplus-tier-b)

500-tick probe on `surplus_forage` (seed surplus-smoke, final tuning):
- `offer_trade`: **10 accepted** (plus 7 race-casualty rejections across
  `trade.invalid_mutation` / `trade.out_of_range` — partner state moved
  between proposal and commit; the CAS paths Tier A covers deliberately).
- First organic `retrieve` events; 12/20 persons held stored meat, 20/20
  stored wood; 251 meat-offerer person-ticks; 17/20 persons alive at t500.
- Hunts: 140 strikes; animal herd 36 → 29 (t100) → 19 (t200) → 12 (t300)
  → 8 (t400) → 4 (t500). The carcass-gate flattens the kill curve late
  (8 → 4 over the last 200 ticks) but does not fully stop the decline —
  see Known limitations.
- Tier B census (seed surplus-tier-b, 1,000 ticks): all three invariants
  pass — ≥20% stored surplus by tick 500, ≥5 `offer_trade` events,
  home-vs-forage visit-entropy thresholds.

## Known limitations

- **Barter only.** "Future obligation" trade is deliberately not built (no
  social/commitment machinery in this pass). Trade complementarity is
  purely resource-based.
- **Ints, not floats.** Spec types said float; house canonical state uses
  ints throughout, so quantities are ints.
- **Capacity enforcement is scoped.** `inventory_capacity` binds only
  surplus-enabled persons (legacy gather paths and scenarios unchanged).
- **Storage is virtual and personal.** `stored_resources` lives on the
  person, gated by presence on the home tile; there is no storage entity,
  no shared stores, no theft. The Stage 6 entity-backed storage system is a
  separate, pre-existing stack.
- **`resource_ownership` is informational** (last gatherer of record on a
  stock; flips between gatherers). It confers no rights.
- **Lethality is upstream-tuned.** Early-run starvation exists in the
  people stack on long horizons; the surplus loop reduces but does not
  eliminate it. Not changed by this pass.
- **The herd is finite.** Animals do not reproduce in this scenario, so the
  meat supply declines over long horizons (36 → 4 over 500 ticks, with the
  decline flattening late as encounters rarefy). The carcass-gate prevents
  boom-bust extermination but cannot create new meat; a breeding/population
  dynamic is out of scope for this pass.
- **Hunting quirks inherited.** A landed strike plan completes even if the
  target has since moved (no range re-check in `execute_action_tick`), and
  animals flee diagonally faster than people walk, so healthy uncornered
  prey is effectively uncatchable. Both are pre-existing people-stack
  behaviour, unchanged here.
- Tier B thresholds are calibrated to seed `surplus-tier-b` on
  `surplus_forage`; they are invariants of the scenario, not universal
  constants.
