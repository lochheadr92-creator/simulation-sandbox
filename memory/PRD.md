# Simulation Sandbox — PRD

## Original Problem Statement
Build a browser-based **deterministic living-world simulation platform** with an integrated sandbox for observing, inspecting, replaying, experimenting with, and extending autonomous worlds. The simulation is the product; the sandbox is the interface. Not a game, not an AI demo, not a story generator.

Governing doctrine (from uploaded documents: Source of Truth v2, Core Commit Pipeline Spec #27, Domain Engine Contract Spec #28, Verification & Test Doctrine Spec #32, Main/Sister Engine conversation summary):
- The simulation is truth. Only Core-accepted events mutate canonical state.
- Every durable change requires a causal origin; every accepted change must be replayable; every decision must be inspectable.
- Same seed + scenario + engine version + external interventions ⇒ identical accepted events and identical state hashes.
- Core owns time/scheduling/ordering/validation/conflict-resolution/hashing/replay/storage and must remain domain-agnostic.
- Domains only observe, propose, and request work — never mutate, never approve their own work, never talk to each other directly.
- Sandbox observes/replays/inspects/configures/submits interventions through the same authoritative pipeline — never owns truth.
- Causal inspection must show real evidence (state, needs, goals, candidates, scores, rejected candidates, accepted action, causal chain) — never fabricated.

## User Choices (gathered before implementation)
1. Phase 1 world scope: **Minimal** — People (needs/goals/gather/shelter) + Animals (wander/graze/flee) + finite tree/water resources. No weather/disease/economy domains.
2. Simulation execution model: **Continuous autoplay** with Play/Pause/Step/Speed controls.
3. Tech stack: **React + FastAPI + MongoDB** (platform defaults).
4. Determinism approach: **Integer/fixed-point state values + per-named-stream seeded RNG** (no global random, no floats in hashed state).
5. LLM/narration: **None in Phase 1** — pure deterministic kernel + sandbox.
6. Additional request: **Day/night cycle** — implemented as Core-derived time-of-day (not a separate domain) affecting rest thresholds and animal activity, plus a canvas lighting overlay.

## Architecture v2 (implemented)

**Core (domain-agnostic, `/app/backend/core/`)**
- `hashing.py` — canonical JSON + SHA256 hashing, excludes storage metadata.
- `rng.py` — `DeterministicRNG`: named streams seeded by `sha256(run_seed::stream_name)`; stream names embed entity+tick so determinism never depends on call order.
- `mutations.py` — generic `{new_entities, entity_updates, removed_entities}` envelope; `apply_mutation()` and `snapshot_for_hash()` are the ONLY things that touch entity state, and Core never interprets domain semantics (keeps Core truly domain-agnostic).
- `commit_pipeline.py` — normalize → deterministic order `(time, phase, engine_priority, content_hash)` → validate (scope exists, causal parents, generic preconditions) → sequential commit-time revalidation (this is how resource contention resolves deterministically) → hash.
- `kernel.py` — pure, DB-free: `build_genesis()`, `run_tick()`.
- `run_service.py` / `replay_service.py` — DB orchestration, replay verification, and **determinism verification** (re-simulates a shadow run from the same seed + replays recorded interventions, compares full hash sequence).
- `interventions.py` — sandbox interventions (`boost_need`, `spawn_tree`, `kill_entity`) normalized into `ExternalInfluenceRecord`s and submitted through the same commit pipeline as domain proposals (doctrine's "paired model").

**Domains (proposal-only, `/app/backend/domains/`)**
- `people_domain.py` — needs (hunger/thirst/energy) → scored candidate goals (SEEK_WATER/SEEK_FOOD/REST/BUILD_SHELTER/GATHER_SURPLUS/WANDER) → one action proposal; all candidates+scores recorded as diagnostics for causal inspection.
- `animal_domain.py` — FLEE/REST/GRAZE/WANDER scored candidates.
- `ecology_domain.py` — tree regrowth, scheduled cadence (every 5 ticks), exogenous.

**Sandbox (React, `/app/frontend/src/`)**
- `WorldCanvas.jsx` — HTML5 canvas renderer (terrain/trees/people/animals/shelters/day-night overlay), click-to-select.
- `EntityInspector.jsx` — causal inspection: state/needs, candidate goals+scores, accepted action, Core-rejected proposals, causal chain timeline.
- `EventLog.jsx`, `RejectionsLog.jsx`, `DeterminismPanel.jsx` (Verify Replay / Verify Determinism), `InterventionsPanel.jsx`.
- `ControlBar.jsx` — Play/Pause/Step/Speed/tick/day-night/hash display. `NewRunModal.jsx` — scenario+seed.

**API** (`/app/backend/api/routes.py`, all under `/api`): `POST /runs`, `GET /runs/{id}/state`, `POST /runs/{id}/step`, `GET /runs/{id}/entities/{id}/causal`, `GET /runs/{id}/events`, `GET /runs/{id}/rejections`, `POST /runs/{id}/interventions`, `POST /runs/{id}/replay/verify`, `POST /runs/{id}/replay/determinism`.

## What's Been Implemented (as of Feb 2026, first milestone)
- Deterministic Core kernel with full proposal→event commit pipeline, generic domain-agnostic mutation/precondition system, canonical hashing, and two independent proofs: replay integrity (reapply recorded events) and full determinism (shadow re-simulation including replayed interventions).
- 3 domain engines (People/Animal/Ecology), all proposal-only, contract-compliant (no mutation, no storage, no LLM, no wall-clock, Core-issued named RNG only).
- Genuinely autonomous world: people survive/compete/cooperate/gather/build shelter/respond to day-night; animals wander/graze/flee; finite tree resources deplete+regrow; resource contention resolves deterministically with real rejection reason codes.
- Full sandbox UI: world canvas, autoplay controls, 5-tab inspector (Entity/Events/Rejections/Determinism/Intervene) — all causal data is genuine simulation evidence, no fabricated explanations.
- Testing: 22/22 backend pytest cases + full frontend Playwright pass (`/app/backend/tests/test_simulation_sandbox.py`). No bugs found in first test pass.

## Phase 2 — Behavior Enrichment (completed Feb 2026)
Goal: make the world visibly more alive WITHOUT new domains or LLM. Delivered entirely inside the existing People domain (`animal_domain.py`/Core untouched in spirit; only schema field additions):

- **Multi-stage actions** (`people_planning.py::execute_action_tick`) — travel/gather/eat/drink/sleep/build_shelter/wander each span multiple ticks with `ticks_spent`/`ticks_required`, individually observable per tick.
- **Behavior planning** (`people_planning.py::PLAN_STEPS`/`form_plan`) — short multi-step plans (e.g. SEEK_WATER → [TRAVEL_WATER, DRINK], BUILD_SHELTER → [TRAVEL_TREE, GATHER, TRAVEL_SITE, BUILD]) with `step_index` advancing as steps complete.
- **Knowledge / resource memory** (`perception.py`) — each person perceives a vision-radius delta every tick and merges it into their own persistent canonical `knowledge` field (`known_tiles`, `known_water_tiles`, `known_trees`, `known_shelters`). All utility lookups (`people_utility.py::nearest_known_*`) read exclusively from this field — never a global/omniscient search. Sets are converted to sorted lists before merge to preserve canonical-hash determinism.
- **Exploration** — `nearest_unknown_tile()` + EXPLORE goal walks toward the nearest unknown passable tile; `urgent_but_blind` severity bonus makes EXPLORE win when a critical need has no known target yet (resolves "thirsty but blind" without ever forcing an unreachable goal).
- **Better utility scoring** (`people_utility.py::score_candidates`) — `severity*W + predicted*W - travel*W - interrupt*W + availability*W - risk*W`, all 7 candidates (SEEK_WATER/SEEK_FOOD/SLEEP/BUILD_SHELTER/GATHER_SURPLUS/EXPLORE/WANDER) scored every fresh decision with every input exposed for inspection.
- **Deterministic interruptions** (`people_domain.py::activate`) — a critical need (≥`CRITICAL_THRESHOLD`) with a *known* target pauses an in-progress interruptible action (paused action/plan stored verbatim) and resumes it once the critical need clears — verified end-to-end with exact expected explanation strings.
- **Improved inspection** (`EntityInspector.jsx`) — Current Action (status/progress bar/target), Current Plan (step badges w/ active/done coloring), Known Resources (explored tiles / known water / trees / shelters), full Utility Breakdown table, Decision Explanation + rng_stream reference, Accepted Action, Action History, Rejected Proposals, Causal Chain — all genuine, non-fabricated evidence.
- **Safety net**: `TRAVEL_STALL_LIMIT=25` ticks aborts a travel step that cannot make progress (unreachable/boxed-in target) and cleanly triggers a replan rather than deadlocking — resolved two real lock-ups found during implementation (unreachable SEEK_WATER, EXPLORE pathing to unreachable water).

### Testing evidence (Phase 2 close-out, Feb 2026)
- **Backend**: 35/35 pytest pass (22 Phase 1 regression + 13 new Phase 2 cases in `/app/backend/tests/test_phase2.py`).
- **Frontend**: 100% of tested Phase 2 + Phase 1 regression flows passed (Playwright) — action/plan/knowledge/utility-breakdown panels all confirmed showing real, changing data across ticks; critical interrupt + resume observed with exact expected explanation text.
- **Replay verify**: PASS (real `verified_ticks`/`frames_checked`).
- **Determinism verify**: PASS (real `final_state_hash`, same-seed dual-run hash sequences identical).
- **Doctrine check**: no LLM calls, no hidden persistent state outside canonical entity fields, no domain mutating state directly, no float/global-random usage in hashed state — knowledge/action/plan all flow through the standard `entity_updates` mutation envelope; Core remains domain-agnostic and unchanged.
- **Deviations from spec**: none functional. One design nuance confirmed intentional (not a bug): a critical need only force-interrupts when its target is already *known* — if unknown, EXPLORE's `urgent_but_blind` bonus takes over at the next fresh decision instead of interrupting toward an unreachable goal.
- **Known limitation**: resource contention (concurrent-gather rejection) is structurally implemented (Core preconditions on `claimed_tick`/`resource`) and covered by Phase 1 tests, but was not freshly re-triggered in the Phase 2 test session (probabilistic — needs 2+ people adjacent to the same tree in the same tick).
- Test report: `/app/test_reports/iteration_2.json`. Git: branch `Main`, test-file commit `2e717b5` (no production code changed by testing agent, only new `test_phase2.py`).

## Deferred / Backlog (explicitly out of scope, by design)
- Receipts, checkpoints, projection-cache layer, multi-lineage branch/fork/migration, Pressure Graph substrate — full Source-of-Truth-v2 record taxonomy beyond what's needed for the invariants.
- Additional domains/scenarios (Weather, Disease, Economy, AI Town, Medieval Kingdom, etc.) — architecture supports adding these as pure scenario config + new domain engines with zero Core changes. Explicitly forbidden for Phase 2.
- Multi-rate/state-dependent scheduling beyond the current fixed cadences (agents=1 tick, ecology=5 ticks).
- Run persistence UI (list/switch between existing runs) — backend endpoint exists (`GET /runs`), not yet wired into the frontend.
- LLM/narration — still explicitly out of scope.

## Next Action Items
- P1: Add a "Load Existing Run" picker in the sandbox (backend already supports it).
- P1: Add a second scenario (e.g. a small "Ecology" variant) to prove the domain-agnostic Core claim without touching Core code.
- P2: Deliberately reproduce resource contention (2 people forced adjacent to same tree via intervention) as a durable regression test.
- P2: Add automated nondeterminism-detection tests (per Verification Doctrine Spec #32) as a CI-style check.
