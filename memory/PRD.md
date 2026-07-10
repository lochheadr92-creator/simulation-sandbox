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

## Phase 3 — Scenario Architecture Proof (completed Feb 2026)
Goal: prove the Core is genuinely domain-agnostic — a second, intentionally different scenario runs on the exact same Core with zero Core code changes. Architectural proof, not content expansion.

### What was built
- **Formal Scenario layer** (`/app/backend/scenarios/`): `base.py` defines an immutable `Scenario` dataclass (`id`, `name`, `description`, `enabled_domains: list[str]`, `world_gen: dict`, `presentation: dict`). `registry.py` provides `register_scenario()`/`get_scenario()`/`list_scenarios()`. Two scenario files (`wilderness_survival.py`, `desert_oasis.py`) each define one `Scenario` instance and self-register on import; `__init__.py` triggers both. Adding a third scenario in the future = one new file + one import line, nothing else.
- **Domain registry** (`/app/backend/domains/registry.py`): `DOMAIN_REGISTRY = {"ecology": EcologyDomain(), "people": PeopleDomain(), "animal": AnimalDomain()}`. The Domain Engine Contract (`domains/base.py`) gained one new method, `select_due_ids(entities, tick)`, moving entity-type-filtering logic (which was previously hardcoded inline in the kernel) into each concrete domain — this is what let the kernel stop knowing what "person"/"animal"/"tree" mean.
- **Kernel became scenario-agnostic** (`core/kernel.py`): `run_tick(...)` now takes a generic `enabled_domains: list` and loops `for domain_id in enabled_domains: domain = DOMAIN_REGISTRY[domain_id]; due = domain.select_due_ids(...); domain.activate(...)`. `build_genesis(seed, scenario, lineage_key)` now takes the `Scenario` object directly. **Verified via static-analysis pytest tests that `kernel.py` contains zero hardcoded entity-type or scenario-id string literals and imports no concrete domain class.**
- **Generic world generator** (`world/generator.py`): `generate_world(seed, scenario)` is driven entirely by `scenario.world_gen` (width/height, `ground_terrain`, `water_blob_count`/`water_radius_range`, entity counts, stat ranges) — no scenario-id branching anywhere in the function.
- **Second scenario — Desert Oasis** (`desert_oasis.py`): sand ground terrain, one small oasis (radius 1–2 vs the lake's 2–3), only 6 scarce trees (vs 16), harsher starting hunger/thirst/energy ranges, and **`enabled_domains = ["ecology", "people"]` — the Animal domain is fully disabled for this scenario**, proving domains are opt-in per scenario with zero Core changes. Reuses the exact same People domain (perception/planning/utility/interruption) unmodified.
- **Orchestration layer updated minimally** (`core/run_service.py`, `core/replay_service.py`, `api/routes.py`): resolve `scenario_id → Scenario` via the registry and thread `enabled_domains`/`scenario` through to the kernel. These are the only Core-adjacent files touched — `commit_pipeline.py`, `hashing.py`, `mutations.py`, `rng.py`, `interventions.py`, `geometry.py`, `db.py` are **100% untouched** (git-diff verified).
- **Frontend**: `NewRunModal.jsx` shows scenario friendly name + description + a live "domains: ..." line; `ControlBar.jsx` adds a scenario-name badge (`run-scenario-badge`) so an active run's scenario is always visible; `WorldCanvas.jsx` extended its terrain color map with `sand` (generic `COLORS[terrain[y][x]] || COLORS.grass` lookup, no per-scenario branching in canvas code).
- `ENGINE_VERSION` bumped `0.2.0 → 0.3.0` (kernel signature changed); dead unused constants (`GRID_WIDTH`/`GRID_HEIGHT`/`NUM_PEOPLE`/`NUM_ANIMALS`/`NUM_TREES`) removed from `core/constants.py`, fully superseded by per-scenario `world_gen`.

### Testing evidence (Phase 3, Feb 2026)
- **Backend**: 54/54 pytest pass (22 Phase 1 + 13 Phase 2 regression + 19 new Phase 3 tests in `/app/backend/tests/test_phase3.py`), including 5 static-analysis tests that directly assert `kernel.py` has no `"person"`/`"animal"`/`"tree"`/scenario-id literals and imports no concrete domain class.
- **Frontend**: 100% of tested flows pass — scenario picker, per-scenario terrain colors (sand vs grass), scenario badge, EntityInspector showing identical Phase 2 richness for a Desert Oasis person (proving unmodified People-domain reuse).
- **Replay verify**: PASS for both scenarios. **Determinism verify**: PASS for both scenarios, including a same-seed dual-run hash-sequence match specific to Desert Oasis.
- **Doctrine check**: `commit_pipeline.py`/`hashing.py`/`mutations.py`/`rng.py` never reference `scenarios` or `scenario_id` (asserted by test). No LLM, no new forbidden domains (weather/disease/economy/etc.), no scenario-specific branching inside the Core.
- **Files changed**: `scenarios/*` (new), `domains/registry.py` (new), `domains/base.py`, `domains/{people,animal,ecology}_domain.py` (added `select_due_ids`), `core/kernel.py`, `core/run_service.py`, `core/replay_service.py`, `core/constants.py`, `api/routes.py`, `world/generator.py`, `frontend/{NewRunModal,ControlBar,WorldCanvas}.jsx`, `backend/tests/test_phase3.py` + `conftest.py` (test-infra only).
- **Known limitation**: no in-app side-by-side comparison view between two running scenarios — a developer compares by switching the active run and reading the scenario badge (deliberately minimal, per "do not redesign the UI").
- Test report: `/app/test_reports/iteration_3.json`. Branch `Main`.

## Deferred / Backlog (explicitly out of scope, by design)
- Receipts, checkpoints, projection-cache layer, multi-lineage branch/fork/migration, Pressure Graph substrate.
- Weather, Disease, Economy, population growth/birth, combat, politics, religion, complex social systems, LLM/narration — still explicitly out of scope.
- Multi-rate/state-dependent scheduling beyond the current fixed cadences (agents=1 tick, ecology=5 ticks, Core-owned, not yet scenario-configurable).
- Run persistence UI (list/switch between existing runs) — backend endpoint exists (`GET /runs`), not yet wired into the frontend.
- In-app side-by-side scenario comparison view.

## Next Action Items
- P1: Add a "Load Existing Run" picker in the sandbox (backend already supports it).
- P2: Deliberately reproduce resource contention (2 people forced adjacent to same tree via intervention) as a durable regression test.
- P2: Add automated nondeterminism-detection tests (per Verification Doctrine Spec #32) as a CI-style check.
- P2: Consider a 3rd scenario purely to further stress the registration mechanism (zero-Core-change proof) once there's a concrete need.
