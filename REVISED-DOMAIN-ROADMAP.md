# Revised Domain Roadmap

> Post-stabilisation charter for the simulation-sandbox people and ecology stack.  
> Each phase defines scope, dependencies, state model, growth cap, acceptance gate, and named Session-A decisions.  
> Constants, thresholds, and contracts are written at Session A from measured evidence — they do not appear here.

---

## Phase 0 — Stabilisation

**Goal:** Restore a clean, committed baseline from the current floating surplus and culture passes, and disposition the adversarial review findings.

**Scope:** Review-sequence only. No new domain behaviour. No FRONTIER debts, no HANDOFF R1/pin-capture items.

**Dependencies:** None. This phase is the precondition for every phase that follows.

**State model:** No new state.

**Growth cap:** No growth.

### Exit criteria

1. **Quarantine the emotion layer.** Revert the ungated `EmotionDomain` registration in `backend/domains/registry.py`, the `emotions` block mint/backfill in `backend/domains/living_agent_contracts.py`, and the `_apply_emotion_gradient` hunk in `backend/domains/living_settlement_domain.py`. Move `emotion_domain.py` and `emotion_contracts.py` to a holding branch for Phase 3.
2. **Run the frozen-baseline pin first** (`backend/tests/test_frozen_baseline_hashes.py`). This is the cheapest falsifier of the legacy byte-identity claim. The surplus-session pre-existing failures (frozen pin + `test_stage6e_living_settlement` ×3 + `test_stage7b_group_state`) should clear with the quarantine.
3. **Fix S2–S6 (and S7 comments):**
   - **S2/S5:** Capacity bounds in `validate_people_trade`, mirrored at emission in `people_culture.select_trade_partner`; receiver-retain precondition.
   - **S3:** Wood leg re-derived against live values in `validate_people_aid`.
   - **S4:** `_evict_decayed` run after insert, with deletions folded into the `changed` signal; committed-cap Tier A assertion.
   - **S6:** Parenthesised union in `refresh_aid_eligible`.
   - **S7:** Comment drift in aid severity and proposal-type baseline.
4. **Commit the surplus pass** as its own leg on a capability branch (not `frontend/*`).
5. **Commit the culture pass** after fixes re-green Tier A.
6. **Pending verifications:** 500-tick culture census (fill CULTURE_PASS.md "Measured emergence"), `collective_groups` benchmark (≤400 ms/tick gate), chunked-vs-continuous determinism check, surplus Tier B 1,000-tick re-run.

**Acceptance gate:** Full suite green including the frozen pin; both passes committed on a capability branch; both pass docs updated with measured values.

---

## Phase 3 — Emotion Pass

**Goal:** Re-land the quarantined emotion layer under contract as a biasing layer only.

**Scope — in:** Emotion state on living agents; utility biasing via intensity gradients; decay; compat backfill for legacy agents.  
**Scope — out:** Personality, mood history, emotion-driven plan forcing.

**Dependencies:** Phase 0.

**State model:** `living_agent.emotions` — fixed-kind bounded-int map (`emotion-v1`). No history, no per-event records.

**Growth cap:** Fixed-size map; zero growth.

### Session-A decisions (to be resolved from evidence)

- **(a) Scenario-knob gating:** Use the `assign_storage_location` pattern so `EmotionDomain` registration is scenario-gated, preserving legacy byte-identity when the knob is off.
- **(b) Integer-only arithmetic:** Replace the float gradient (`intensity / 1000`) with an integer-equivalent bias.
- **(c) Interruptive action proposals:** `FLEE` / `CONFRONT` / `CELEBRATE` / `MOURN` as pipeline-competing proposals vs gradient-only utility biasing. DOMAIN_MAPPING permits biasing utility, never forcing actions; whether pipeline-competing proposals "invent a candidate" must be resolved against the culture invariant explicitly.

**Acceptance gate:**
- Tier A: contract tests (delta determinism, bounds, decay, compat backfill, legacy byte-identity with knob off, two-run hash equality with knob on).
- Tier B: census in threat scenario showing measurable fear-driven behavioural divergence; survival dominance holds.

---

## Phase 4 — Kinship & Households

**Goal:** Genesis kin/household structure for the people stack.

**Scope — in:** Kin-aware aid and trade partner selection; household storage semantics.  
**Scope — out:** Births, marriage, inheritance (Stage 11 / 5F3 territory — explicit boundary).

**Dependencies:** Phase 0 (surplus + culture committed).

**State model:** Kin block on person (`household_id` + bounded kin list, fixed at genesis); `assign_households` genesis knob in `world/generator.py` mirroring `assign_storage_location`; `surplus_forage` opts in, legacy byte-identical.

**Growth cap:** Fixed at genesis; zero growth (no births exist).

### Session-A decisions (to be resolved from evidence)

- Household-shared `storage_location` vs kin-access rules on personal stores.
- How sharing respects the surplus pass's `resource_ownership` invariant.
- Whether kin aid rides `offer_trade` / `people-aid-v1` (preferred) or needs one new proposal type.

**Acceptance gate:**
- Tier A: commit / replay / validator tests.
- Tier B: kin-preference measurable in aid distribution; household-clustered visit-frequency entropy.

---

## Phase 5 — Animal & Ecology Renewal

**Goal:** Sustained herd dynamics below regional carrying capacity.

**Scope — in:** Herd reproduction; grazing/regrowth coupling; migration pressure when over capacity.  
**Scope — out:** Predators, packs, territories, full plant ecology.

**Dependencies:** None on Phases 3–4.  
**Hard prerequisite decision:** The per-parameter-per-entity RNG keying debt (FRONTIER.md, authorised, unimplemented) must land or be explicitly scoped around — births mint new entity IDs.

**State model:** Bounded reproductive fields on animal entity; per-region herd cap.

**Growth cap:** Herd count capped by carrying capacity; no unbounded minting.

### Session-A probes (to be run before contracting)

1. **Domain-minted entities post-genesis:** Mechanism exists (`new_entities` mutations in weather / interventions). Design a `spawn_entity`-family birth proposal with provenance.
2. **RNG stream keying for minted IDs:** Ensure births don't shift other entities' draws.

**Acceptance gate:**
- Tier A: mint / replay / determinism tests.
- Tier B: herd persists 1,000 ticks under hunting pressure without extermination (fixes the Surplus Pass finite-herd limitation); surplus Tier B invariants still pass with renewal on; tick-time guardrail.

---

## Phase 6 — Weather–Behaviour Coupling

**Goal:** Connect the existing `weather_domain.py` cycle to people behaviour.

**Scope — in:** At most two staged effects (e.g. rain/storm suppresses gather scores and raises shelter/rest; visibility penalty feeds perception).  
**Scope — out:** New weather states, climate, seasons, regional weather.

**Dependencies:** None hard. Session-A check: does `surplus_forage` mint a weather entity (knob if needed); `living_settlement` already runs it.

**State model:** None new — effects ride the existing weather entity fields.

**Growth cap:** n/a (no new state).

### Doctrine carried from Leg B's measured failure

- Census the action mix per condition FIRST (Leg B skipped Session A).
- Weighting-not-gating; magnitude that can actually move selection; never dampen survival-class goals.

**Acceptance gate:**
- Tier B: action mix varies by weather condition; survival dominance holds; legacy scenarios byte-identical where no weather entity exists.

---

## Phase 7 — Social Queue Leg 1: Information Sharing (+ commit unblockers)

**Goal:** Agents share knowledge facts within interaction range, riding existing social-signal machinery.

**Scope — in:** Information sharing (resource locations, dangers).  
**Scope — out:** The remaining Tier-1 backlog (social approach, helping/refusal, relationship adjustment, group cooperation, shared shelter, resource conflict) — listed as the post-Phase-7 queue, not contracted here.

**Dependencies:** None on Phases 3–6, but sequenced last because its prerequisite fixes live in `living_settlement_domain.py`, which Phase 3 also settles.  
**Callable sequencing decision:** May be pulled forward to immediately after Phase 3 without breaking any dependency.

**In-leg prerequisites (maintenance freeze rule):** The domain cannot activate until:
- Pin-capture mismatch fix: actor-side pin from the committed frame-start blob, not the perception-enriched working blob.
- Composition-point write fix (`living_settlement_domain.py:777`): narrow the diff, no wholesale `actor_update["living_agent"]` rewrite.
- R1 retarget decision: commit or drop, re-measured under a statistical gate per `CORE-INTEGRITY-004`.

**State model:** None new beyond what the two fixes touch; information sharing rides existing knowledge / signal state.

**Growth cap:** Shared-fact records bounded per knowledge caps already in force.

**Acceptance gate:**
- Organic information-sharing events in census.
- `warn` fires >0 in 320 ticks (candidate-generation bottleneck addressed).
- Social-commit rejection census falls toward the projected ~230 honest rejections.

---

## Cross-cutting delivery rules

Applies to every phase.

- **Genesis-knob gating** for legacy byte-identity; Core proposal pipeline only; keyed deterministic RNG.
- **Tier A contract tests + Tier B census invariants** per phase (surplus / culture pattern); benchmark guardrail ≤1.2 s avg tick on `collective_groups`; the `surplus_forage` per-event rehash cost is the standing signal to watch.
- **One pass doc per phase** at repo root; adversarial review before commit; each phase committed as its own leg on a capability branch, never `frontend/*`.
- **Operating model:** Sessions A–E, 70/20/10 budget, PASS WITH LIMITATIONS is healthy; containment pass scheduled after Phase 5 (every 2–3 domains per DYNAMICS-BACKLOG).
- **Explicitly parked (out of scope):** Leg B day-rhythm (failed WIP branch kept unmerged), FRONTIER open items (OQ-1, GOAL-SCORING, organic gates), HANDOFF items beyond the R1 decision point inside Phase 7.

---

## Sequencing rationale

1. **Phase 3 (Emotion)** — clears the last floating WIP; independent; small blast radius.
2. **Phase 4 (Kinship)** — people-stack continuity; fills the gap culture named; the genesis-knob pattern is proven twice by this point.
3. **Phase 5 (Animals)** — sustains Phase 1's economy; independent stack; probe-gated risk.
4. **Phase 6 (Weather)** — machine exists; thin; independent.
5. **Phase 7 (Social queue)** — largest blast radius; its fixes land better on a file Phase 3 has already settled.

**Alternative considered and rejected:** Social queue first — it offers the biggest measured unlock (~925 social actions / 320t), but the user scoped Phase 0 to review-only, emotion WIP should not float across more phases, and Phases 4–6 are cheaper visible wins that honour "ranked by visible life added."

---

*Document status: Draft — pending Session A for each phase.*
