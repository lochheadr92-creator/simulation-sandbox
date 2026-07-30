# Revised Domain Roadmap

> Post-stabilisation charter for the simulation-sandbox people and ecology stack.  
> Each phase defines scope, dependencies, state model, growth cap, acceptance gate, and named Session-A decisions.  
> New constants, thresholds, and contracts are written at Session A from measured evidence. Inherited values may appear only with their role and provenance status stated. An unresolved source is blocking: the value must be traced to an owning contract or re-ratified from measurement before it can gate a phase.

---

## Roadmap numbering and inherited gates

- **Phases 1–2 already exist:** Phase 1 is the Surplus / Economy pass and Phase 2 is the Culture pass. Phase 0 stabilises and commits both; new delivery begins at Phase 3.
- **Phase numbers are roadmap delivery units. Stage numbers are repository lineage identifiers.** References such as Stage 8C and Stage 11 / 5F3 retain their existing contract or backlog meaning and do not imply roadmap order.
- **Inherited verification horizons and thresholds:**
  - The 500-tick culture census is owned by `CULTURE_PASS.md` and blocks Phase 0 exit.
  - The `collective_groups` **≤400 ms/tick commit-time benchmark** is the strict Phase 0 landing benchmark. **Provenance status: unresolved in the prior roadmap.** Its harness and owning contract must be identified, or the threshold re-ratified, before Phase 0 can pass.
  - The `collective_groups` **≤1.2 s average tick standing guardrail** is the cross-domain regression ceiling carried from the prior roadmap; it is not a substitute for the stricter Phase 0 benchmark. **Provenance status: unresolved.** Phase 0 must identify its owning contract or re-ratify it before later phases rely on it.
  - The 320-tick social census horizon is carried from the prior Phase 7 gate. **Provenance status: unresolved.** Phase 7 Session A must cite or re-ratify it before use.
  - The 1,000-tick surplus and herd horizons are carried from the Surplus Pass evidence and must remain cited in the owning pass documents.

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
6. **Complete the blocking verifications:**
   - 500-tick culture census; fill `CULTURE_PASS.md` “Measured emergence”.
   - `collective_groups` commit-time benchmark at the inherited ≤400 ms/tick gate; record harness and provenance.
   - Chunked-vs-continuous determinism check.
   - Surplus Tier B 1,000-tick re-run; update the owning pass document.

The four verifications may trail the individual code commits in items 4–5, but none may trail **Phase 0 exit**.

**Acceptance gate:** Full suite green including the frozen pin; surplus and culture committed on capability branches; all four blocking verifications pass; both pass documents contain the measured values, harness details, and inherited-gate provenance.

---

## Phase 3 — Emotion Pass

**Goal:** Re-land the quarantined emotion layer under contract as a biasing layer only.

**Scope — in:** Emotion state on living agents; utility biasing via intensity gradients; decay; compat backfill for legacy agents.  
**Scope — out:** Personality, mood history, emotion-driven plan forcing.

**Dependencies:** Phase 0.

**State model:** `living_agent.emotions` — fixed-kind bounded-int map (`emotion-v1`). No history, no per-event records.

**Growth cap:** Fixed-size map; zero growth.

### Session-A decisions and classification

- **(a) Scenario-knob gating:** Use the `assign_storage_location` pattern so `EmotionDomain` registration is scenario-gated, preserving legacy byte-identity when the knob is off.
- **(b) Integer-only arithmetic:** Replace the float gradient (`intensity / 1000`) with an integer-equivalent bias.
- **(c1) Gradient-only utility biasing:** Classified as an **extension of existing decision logic**. It is probe-before-contract. Session A must show that bounded emotion gradients can alter candidate ordering without bypassing survival dominance or the Culture invariant.
- **(c2) Pipeline-competing `FLEE` / `CONFRONT` / `CELEBRATE` / `MOURN` proposals:** Classified as **new decision logic**, not an extension. If selected, they require their own proposal contract and a post-build acceptance gate proving organic candidate generation, validator compliance, and no forced-action path. They cannot be smuggled into the gradient-only contract.

**Acceptance gate:**
- Tier A: contract tests (delta determinism, bounds, decay, compat backfill, legacy byte-identity with knob off, two-run hash equality with knob on).
- Tier B, gradient branch: census in a threat scenario showing measurable fear-driven behavioural divergence; survival dominance holds.
- Tier B, proposal branch if selected: each new proposal appears organically under its enabling condition; the Culture invariant and survival dominance both hold.

---

## Phase 4 — Kinship & Households

**Goal:** Genesis kin/household structure for the people stack.

**Scope — in:** Kin-aware aid and trade partner selection; household storage semantics.  
**Scope — out:** Births, marriage, inheritance (Stage 11 / 5F3 territory — explicit repository-lineage boundary).

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

**Hard prerequisite decision:** Session A must select one of two named determinism-safe paths:

- **Path A — keyed minting:** Land the authorised per-parameter-per-entity RNG keying debt before births mint new entity IDs.
- **Path B — dormant herd pool:** Pre-mint a structurally capped pool of dormant herd entities at genesis. Births activate an existing dormant entity rather than minting an ID. This removes post-genesis ID creation from the reproduction path and makes the herd cap structural.

No unnamed “scope around” path is permitted.

**State model:** Bounded reproductive fields on animal entities; per-region herd cap; under Path B, a bounded dormant/active lifecycle flag on the genesis herd pool.

**Growth cap:** Herd capacity is structural. Path A rejects births at the regional cap. Path B cannot exceed the pre-minted regional pool.

### Session-A probes (to be run before contracting)

1. **Path A feasibility:** Verify `spawn_entity`-family provenance, replay behaviour, and RNG isolation for minted IDs.
2. **Path B feasibility:** Verify that dormant entities are byte-stable while inactive and activation does not perturb unrelated entity draws.
3. **Select the lower-risk path** from measured determinism, complexity, and tick-cost evidence; record the rejected path and rollback point.

**Acceptance gate:**
- Tier A: activation-or-mint, replay, cap, and determinism tests for the selected path.
- Tier B: herd persists for the inherited 1,000-tick horizon under hunting pressure without extermination; Surplus Pass Tier B invariants still pass with renewal on; the standing tick-time guardrail holds.

---

## Phase 6 — Weather–Behaviour Coupling

**Goal:** Connect the existing `weather_domain.py` cycle to people behaviour.

**Scope — in:** At most two staged effects (e.g. rain/storm suppresses gather scores and raises shelter/rest; visibility penalty feeds perception).  
**Scope — out:** New weather states, climate, seasons, regional weather.

**Dependencies:** None hard. Session-A check: does `surplus_forage` mint a weather entity (knob if needed); `living_settlement` already runs it.

**State model:** None new — effects ride the existing weather entity fields.

**Growth cap:** n/a (no new state).

### Doctrine carried from Leg B's measured failure

- Census the action mix per condition first; Leg B skipped Session A.
- Weighting-not-gating; magnitude that can actually move selection; never dampen survival-class goals.

**Acceptance gate:**
- Tier A: legacy byte-identity where no weather entity exists; deterministic replay with the coupling enabled.
- Tier B: action mix varies measurably by weather condition; survival dominance holds.

---

## Phase 7 — Social Queue Leg 1: Information Sharing (+ commit unblockers)

**Goal:** Agents share knowledge facts within interaction range, riding existing social-signal machinery.

**Scope — in:** Information sharing (resource locations, dangers).  
**Scope — out:** The remaining Tier-1 backlog (social approach, helping/refusal, relationship adjustment, group cooperation, shared shelter, resource conflict) — listed as the post-Phase-7 queue, not contracted here.

**Dependencies:** None on Phases 3–6, but sequenced last because its prerequisite fixes live in `living_settlement_domain.py`, which Phase 3 also settles.

**Callable sequencing decision:** The caller is the **Phase 3 gate review**. Pull Phase 7 forward to immediately after Phase 3 only when Phase 3 has passed, `living_settlement_domain.py` is stable, and the pin-capture/composition fixes can land as an isolated maintenance leg without reopening the emotion contract. Otherwise Phase 7 remains last.

**In-leg prerequisites (maintenance freeze rule):** The domain cannot activate until:
- Pin-capture mismatch fix: actor-side pin from the committed frame-start blob, not the perception-enriched working blob.
- Composition-point write fix (`living_settlement_domain.py:777`): narrow the diff, no wholesale `actor_update["living_agent"]` rewrite.
- R1 retarget decision: commit or drop, re-measured under a statistical gate per `CORE-INTEGRITY-004`.

**State model:** None new beyond what the two fixes touch; information sharing rides existing knowledge / signal state.

**Growth cap:** Shared-fact records bounded per knowledge caps already in force.

### Session-A probe

Measure the current social-commit rejection distribution and ratify an honest-rejection band. The historical projection is evidence for the probe, not an acceptance threshold.

**Acceptance gate:**
- Organic information-sharing events appear in census.
- `warn` fires >0 within the inherited 320-tick census horizon; the candidate-generation bottleneck is addressed.
- Social-commit rejections fall inside the Session-A-ratified honest-rejection band without weakening validators or bypassing the proposal pipeline.

---

## Cross-cutting delivery rules

Applies to every phase.

- **Genesis-knob gating** for legacy byte-identity; Core proposal pipeline only; keyed deterministic RNG.
- **Tier A contract tests + Tier B census invariants** per phase, following the Surplus / Culture pattern.
- **Standing behavioural probe:** Every behaviour-changing phase must name a disabled-vs-enabled or condition-vs-control probe before implementation. Tier A green with no measurable world-level divergence cannot receive a clean PASS; it is either PASS WITH LIMITATIONS with an explicit blocker or a failed gate.
- **Two distinct performance gates:** Phase 0 uses the strict ≤400 ms/tick `collective_groups` commit benchmark. After landing, every phase must remain below the ≤1.2 s average-tick standing regression ceiling. The `surplus_forage` per-event rehash cost remains the standing signal to watch.
- **One pass document per phase** at repo root; adversarial review before commit; each phase committed as its own leg on a capability branch, never `frontend/*`.
- **Failure disposition:** Any phase that fails its acceptance gate returns the baseline to the last accepted commit and moves its WIP to a named holding branch with evidence and failure notes. No unaccepted WIP may float past the next phase boundary.
- **Operating model:** Sessions A–E, 70/20/10 budget, PASS WITH LIMITATIONS is healthy; containment pass scheduled after Phase 5 (every 2–3 domains per `DYNAMICS-BACKLOG`).
- **Explicitly parked (out of scope):** Leg B day-rhythm (failed WIP branch kept unmerged), FRONTIER open items `OQ-1` and `GOAL-SCORING`, and HANDOFF items beyond the R1 decision point inside Phase 7. Organic behaviour is not globally parked; it is governed by the standing behavioural probe above.

---

## Charter terminal condition

This charter exits domain-expansion mode when all of the following are true:

1. Phase 0 and every phase selected for this charter are committed as accepted capability legs, or explicitly parked with no WIP affecting the accepted baseline.
2. Full-suite, replay, frozen-pin, and chunked-vs-continuous determinism checks pass on the terminal baseline.
3. Every enabled behaviour-changing domain passes its standing behavioural probe and preserves its survival, ownership, growth, and compatibility invariants.
4. The strict landing benchmarks and the standing performance guardrail remain green at their applicable gates.
5. A terminal adversarial review records remaining FRONTIER, HANDOFF, Stage, and backlog work into a successor roadmap rather than silently extending this charter.

Meeting this condition closes **this roadmap**, not simulation development as a whole.

---

## Sequencing rationale

1. **Phase 3 (Emotion)** — clears the last floating WIP; independent; small blast radius.
2. **Phase 4 (Kinship)** — people-stack continuity; fills the gap culture named; the genesis-knob pattern is proven twice by this point.
3. **Phase 5 (Animals)** — sustains Phase 1's economy; independent stack; probe-gated risk.
4. **Phase 6 (Weather)** — machine exists; thin; independent.
5. **Phase 7 (Social queue)** — largest blast radius; its fixes land better on a file Phase 3 has already settled, unless the Phase 3 gate review invokes the named pull-forward condition.

**Alternative considered and rejected:** Social queue first. It offers the largest measured social unlock, but Phase 0 is review-only, emotion WIP should not float across more phases, and Phases 4–6 are cheaper visible wins that honour “ranked by visible life added”.

---

*Document status: Commit-ready charter — Phase-specific constants and contracts remain pending their named Session-A decisions.*
