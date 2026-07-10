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

## Deferred / Backlog (explicitly out of scope for MVP, by design)
- Receipts, checkpoints, projection-cache layer, multi-lineage branch/fork/migration, Pressure Graph substrate — full Source-of-Truth-v2 record taxonomy beyond what's needed for the invariants.
- Additional domains/scenarios (Weather, Disease, Economy, AI Town, Medieval Kingdom, etc.) — architecture supports adding these as pure scenario config + new domain engines with zero Core changes.
- Multi-rate/state-dependent scheduling beyond the current fixed cadences (agents=1 tick, ecology=5 ticks).
- Run persistence UI (list/switch between existing runs) — backend endpoint exists (`GET /runs`), not yet wired into the frontend.

## Next Action Items
- P1: Add a "Load Existing Run" picker in the sandbox (backend already supports it).
- P1: Add a second scenario (e.g. a small "Ecology" variant) to prove the domain-agnostic Core claim without touching Core code.
- P2: Add automated nondeterminism-detection tests (per Verification Doctrine Spec #32) as a CI-style check.
