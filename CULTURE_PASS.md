# Culture Pass — Phase 2 of the Revised Domain Roadmap

Norms, aid, collective memory and gate-keeping for the people stack, hooked
into the surplus pipeline (`gather → store → offer_trade → accept_trade →
consume`). Nothing here replaces that pipeline, and **no new proposal types
are added**: aid rides the existing `offer_trade` proposal type under a new
contract version, and norms/memory/gate-keeping only bias or suppress the
existing `OFFER_TRADE` candidate — the constitution's culture invariant
("influence boosts or suppresses existing candidates only; never invents one,
never outranks urgent survival") is the design's spine. The rehash-cost
constraint from the Surplus Pass is respected: the proposal set is unchanged,
so accepted-event counts (and therefore per-event world rehash cost) grow only
by the aid/barter events that actually happen.

Everything flows through the standard Core proposal pipeline; no domain
mutates state directly. All cultural state is canonical, decision-affecting
state on the person (constitutional property: never generated text), and there
is no hidden group mind — "collective" memory lives on members and propagates
through canonical signals with provenance.

## Interpretations named (house rule: name the gap)

- **"Kin/ally ties."** The people stack has no kin structure (no genesis
  field, zero write sites — kinship exists only in the living_settlement
  stack's `person_profiles`). Aid therefore keys on the two canonical ties
  that DO exist: reciprocity-trust `support_score` (derived from
  interaction-memory facts) and remembered trade counterparties (collective
  memory). Kin would need its own genesis/Stage-6D leg.
- **"Shared memory structure per group."** `surplus_forage` runs no group
  domains, and persons carry no group id. Collective memory is implemented
  per-person and shared *by witnessing*: every accepted `offer_trade` mints a
  social signal carrying the full terms, and any observer in `VISION_RADIUS`
  records the same exchange. The "group" is the emergent witness network, not
  a stored entity.
- **"Gate_status check on collective action proposals."** The
  `group_collective` stack (collective_groups scenario) has no trade history
  and no surplus, so a gate there would be dead machinery — the documented
  Layer-E trap. The one collective benefit this pass introduces is aid, so
  the gate is enforced there: aid proposals exclude receivers with no
  non-decayed barter participation. Barter itself is never gated (exchange is
  how you become a trader).
- **"Acceptance/rejection rates."** A rejected proposal leaves no canonical
  trace on the actor (constitutional property 1), so agents cannot observe
  their own rejections. Norms learn from ACCEPTED outcomes only (own trades +
  witnessed trades); the mechanism that lowers rejection rates is bias toward
  terms and partners that history shows actually commit. The census measures
  the rejection rate externally from Core rejection records.

## Canonical state (Tier A — inside the hash)

| Field | Shape | Notes |
|---|---|---|
| `culture_state` | `{"version": "people-culture-v1", "norms": {...}, "memory": {...}, "aid_eligible": {...}}` person field | Minted lazily on first trade-relevant activation; **surplus-enabled persons only** (the `storage_location` gate), so every legacy scenario stays byte-identical. Whole-map CAS on write; the owner is the single writer. Written only on change (bounded-growth discipline, same as `knowledge`). |
| `norms[pair]` | `{give_field, receive_field, expected_give_x100, expected_receive_x100, accepts, witnessed, last_tick}` | pair key `"inventory>food_inventory"` / `"food_inventory>inventory"`. Integer x100 fixed point; EMA shift 2 toward observed accepted terms. Seeded by the committed `generosity` trait (≥60 asks 1, ≤40 asks 3, else 2). |
| `memory[id]` | `{giver_id, receiver_id, give_field, give_quantity, receive_field, receive_quantity, tick, source, weight_x100}` | source `own` (committed action's stamped `accepted_event_id`) or `witness` (trade signal in vision). Half-life `CULTURE_MEMORY_HALF_LIFE_TICKS = 100`: effective weight `100 >> (age // 100)`, evicted at 0; hard cap 16 entries. |
| `aid_eligible[subject]` | `{tick, basis}` (`support` / `trade`) | Derived flags for inspection; bounded 8; first-confirmed tick is kept so stable ties don't rewrite state every tick. |

## Trade terms become cultural

Pre-culture, `offer_trade` always offered `TRADE_QUANTITY` for
`TRADE_QUANTITY`, and the equal-swap shape was **load-bearing**: it kept both
parties' carry totals invariant, which is what made skipping a capacity check
sound. The Culture Pass prices offers from the agent's norm tuple (clamped:
give ≤ stock − `TRADE_MIN_RETAIN`, receive ≤ `TRADE_QUANTITY + 1`, both legs
bounded by post-trade retain and by each party's carry room), so give can
differ from receive — and the invariants equality used to buy for free are
now re-derived explicitly (adversarial review, Cairn S2/S5/S3):

- `validate_people_trade` rejects carry overflows (`trade.capacity_exceeded`)
  and requires a receiver post-trade retain pin
  (`(receiver, receive_field, gte, receive_qty + TRADE_MIN_RETAIN)`).
- `validate_people_aid` re-derives all four legs against live state (meat
  moves, wood never does).
- `select_trade_partner` mirrors every bound at emission, so agents never
  knowingly emit a self-doomed offer.

A population that witnesses the same accepted trades converges on shared
terms — measurable as cross-agent agreement on modal (give, receive).

Aid terms: `give_field = food_inventory`, `give_quantity = AID_QUANTITY (2)`,
`receive_field = None`, `receive_quantity = 0`, contract `people-aid-v1`.

## Proposal flow (existing types only)

| Mechanism | Hook | Effect |
|---|---|---|
| Norms | `score_candidates` OFFER_TRADE partner/terms selection; `update_culture_state` EMA | Offers use current norm terms; partner ranking prefers remembered counterparties, then id order. |
| Collective memory | `update_culture_state` each activation (own accepted action + witness scan) | Trade outcomes recorded with provenance; queried before every offer. |
| Aid | OFFER_TRADE candidate fallback when no barter profile exists; `offer_trade` action with `aid: true` | One-sided meat gift; `validate_people_aid` (Core) re-derives the material flow: giver keeps ≥ `SURPLUS_KEEP_FOOD`, receiver hunger ≥ 550, receiver capacity, carry mirrors. Ally/gate semantics stay domain-side. |
| Gate-keeping | `gate_status(subject)` in aid receiver selection | Receivers with no non-decayed BARTER entry are excluded from aid; aid entries never confer trader status. |

Aid severity: `AID_SEVERITY (280) + generosity // 2` — always below barter's
320+, so aid is what a satiated, stocked agent does when exchange is
unavailable. Aid requires giver hunger ≤ 400, giver carried food ≥ 6
(`SURPLUS_KEEP_FOOD + AID_QUANTITY`), receiver within `TRADE_RANGE`.

## Trade signals carry terms

`evidence_signal_for_action` extends the `social` signal message for
`offer_trade` actions only with `{give_field, give_quantity, receive_field,
receive_quantity}`. Every other action family's signal payload is
byte-identical. Signals still expire after `LIMITS.signal_lifetime_ticks`
(4 ticks) via the ecology sweep.

## Contract tiers

- **Tier A — deterministic contracts** (`backend/tests/test_culture_pass.py`,
  18 tests): aid commits one-sided gifts through real activation + real
  `run_commit_frame`; aid validator reason codes (`aid.invalid_terms`,
  `aid.invalid_ownership`, `aid.invalid_scope`, `aid.participant_missing`,
  `aid.invalid_participant`, `aid.participant_not_living`, `aid.out_of_range`,
  `aid.insufficient_surplus`, `aid.receiver_not_in_need`,
  `aid.receiver_capacity_exceeded`, `aid.invalid_mutation`,
  `aid.invalid_preconditions`); aid replay safety; own-trade recording next
  activation with dedupe + CAS pin; witness recording with terms; half-life
  decay and eviction; gate counts barter only; norm seeding by generosity;
  norm terms ride the offer; gate excludes non-traders from aid; legacy
  persons untouched; two-identical-runs hash equality on `surplus_forage`
  with culture active.
- **Tier B — emergence invariants**
  (`backend/tests/test_culture_pass_invariants.py`): one shared 500-tick
  census (seed `culture-tier-b`) driven by `backend/tools/culture_census.py`
  (the same driver the chunked probe uses), asserting: barter still fires;
  ≥2 aid events; norm convergence ≥50% modal agreement on some pair with ≥2
  holders; memory query hit rate ≥20%; gate excludes ≥1 aid-eligible
  non-trader AND zero aid events reach receivers with no earlier barter
  participation (verified from the event stream); ≥20% of agents still
  accumulate stored surplus by tick 500 (the aid-doesn't-collapse-the-curve
  probe, Surplus Pass Tier B parity).

## Test commands

Run from `backend/` with the repo-root venv:

```
# Tier A (fast fixtures + two 40-tick traces)
../.venv/Scripts/python.exe -m pytest tests/test_culture_pass.py -q

# Tier B (one shared 500-tick census; slow)
../.venv/Scripts/python.exe -m pytest tests/test_culture_pass_invariants.py -q

# Chunked census (for machines where 500 ticks exceeds one invocation;
# repeat until "complete": true)
../.venv/Scripts/python.exe -m tools._probe_culture_census --seed culture-tier-b \
    --ticks 500 --chunk 60 --state ../test_reports/culture_census_state.pkl \
    --report ../test_reports/culture_census_500.json

# Tick-time regression probe (collective_groups benchmark)
../.venv/Scripts/python.exe -m tools._probe_culture_tick_time --ticks 500 \
    --report ../test_reports/culture_tick_time.json
```

## Performance

- Benchmark guardrail (`collective_groups`, 500 ticks, seed
  living-agents-stage6): culture never activates in this scenario (no
  surplus-enabled persons); the only cost is one early-return validator call
  per offer_trade-free proposal. **PENDING local run** (gate: ≤ 400 ms/tick
  average; surplus pass measured 367.6 ms/tick final).

## Frozen-baseline attribution (VERIFIED 2026-07-30, this machine)

`test_frozen_baseline_hashes.py` **FAILS on this tree** (101.5s run,
`test_reports/frozen_baseline_culture.log`): living_settlement@320
final_state_hash is `5ffaf4ba7bb669ea09bfe13c1537cae1bc1d37c4be6eaceb38358c8603858c76`
vs ratified `e80743460e46be4cf73086854988baa9aa92de27cbff9b5e777430497a0317b2`;
accepted events 5,774 vs ratified 5,088. Per the module docstring this is a
STOP, not a pin to edit. Attribution (`tools/_probe_frozen_attribution.py`,
`test_reports/frozen_attribution.json`, two 320-tick variants + static
decomposition):

- **Culture layer: zero contribution.** living_settlement enables no `people`
  domain and mints no `storage_location`; the aid validator and trade-signal
  terms early-return/scope to `offer_trade` only; the probe variants (culture
  present in both) are byte-identical to each other.
- **Emotion leg (people-stack emotion work in this tree): the mover.** Its
  `living_agent_contracts.py` hunk mints an `emotion-v1` block into every
  `living_agent` state and backfills it via compat, changing canonical state
  on every living_agent-bearing proposal — under CORE-INTEGRITY-004 content
  ordering, that propagates chaotically (+686 accepted events). The emotion
  domain itself fires **zero** events (not in `enabled_domains`), and
  `_apply_emotion_gradient` is inert (minted intensities stay 0 < 100
  without the domain updating them).
- **Surplus pass: zero contribution** (pressure-wiring keys name goals the
  settlement stack never scores; `assign_storage_location` unset there).
- The R1 retarget from HANDOFF.md is NOT in this tree (committed or reverted
  before this pass began; the only `living_settlement_domain.py` hunk is the
  emotion gradient).

Disposition (re-baseline vs quarantine of the emotion leg) is the owner's
call — see the module docstring's STOP procedure; this section is the
explained-diff input to that decision.

- `surplus_forage` per-tick cost is dominated by the pre-existing per-event
  world rehash (documented in SURPLUS_PASS.md as the signal to watch).
  Culture adds per-activation work (witness signal scan, culture-state
  compat) measured at ~+0.13 s/tick on the 80-tick two-run trace (285.2s vs
  274.5s locally) and adds no new proposal families.

## Measured emergence (seed culture-tier-b)

**PENDING — 500-tick census runs chunked locally; fill from
`test_reports/culture_census_500.json` when complete.**

Tier A runs (VERIFIED locally, this machine):
- `tests/test_culture_pass.py`: 17 fast fixtures + two-run hash equality,
  18/18 green (two-run: 285.2s).
- `tests/test_surplus_pass.py`: 17 fast fixtures + two-run hash equality,
  18/18 green — the surplus pass is unaffected by the culture layer (two-run:
  274.5s).

## Known limitations

- **Norms learn from accepted outcomes only.** Rejection-side learning is
  structurally impossible without an actor-visible rejection record (see
  Interpretations). If a terms-pair never commits, agents never unlearn it —
  they only learn what DOES commit.
- **Witnessing needs line-of-sight.** Agents outside `VISION_RADIUS` of a
  trade never record it; memory coverage is spatial, so "the group's" memory
  is genuinely uneven (a feature, but it bounds convergence to trade
  clusters).
- **Aid is meat-only and one-way.** Wood aid, stored-surplus aid, and
  conditional/reciprocal aid are out of scope; the aid contract is the
  minimal one-sided gift.
- **The gate is exactly one benefit deep.** Non-traders are excluded from
  aid only; shared shelter, communal foraging and other collective benefits
  don't exist in the people stack yet, so there is nothing else to gate.
- **Tier B thresholds are calibrated to seed `culture-tier-b` on
  `surplus_forage`**; they are invariants of the scenario, not universal
  constants.
- **Surplus Pass Tier B (1,000-tick, seed surplus-tier-b) was not re-run
  locally** in this pass's session budget. Culture changes trade terms for
  generosity-extreme agents, so its trajectories move; its thresholds (≥5
  trades/1,000 ticks, ≥20% stored by 500) are low bars against the culture
  census's measured rates, but that is LIKELY, not VERIFIED.

## Review record

- Self-review packet (implementer, disclosed):
  `memory/reviews/CULTURE-PASS-ADVERSARIAL-REVIEW-PACKET-2026-07-30.md` —
  caught the norm double-count (fixed, regression-tested).
- External adversarial review (Claude/Cairn, read-only):
  `CULTURE_PASS_ADVERSARIAL_REVIEW.md`. Findings S2–S6 fixed in this tree
  (barter capacity re-derivation `trade.capacity_exceeded`, aid wood-leg
  re-derivation, memory cap enforced post-insert, receiver post-trade retain
  pin, set-precedence parenthesization), each with a Tier A regression test.
  S1 (undisclosed emotion layer in the tree — the frozen-baseline run
  attributes movement: culture additive vs people-stack emotion leg) and the
  surplus-first commit sequencing are owner decisions per the standing
  no-commit rule.
