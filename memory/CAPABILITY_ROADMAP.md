# Simulation Sandbox Capability Roadmap

## Purpose

This document defines the long-range capability order for Simulation Sandbox. It is the strategic compass: **what** each capability stage delivers, the **dependency order**, the **acceptance criteria**, and **where it currently stands** — not the forensic record of any single verification run. Run-specific evidence (exact test counts, scenario hashes, byte peaks, tick traces) lives in the per-stage contract docs and dated verification records; this document points to them.

The planning documents have distinct responsibilities:

- `Domain Plan.txt`: what the simulation may eventually support.
- `memory/CAPABILITY_ROADMAP.md` (this file): the dependency order in which major simulation capabilities become real, their status, and their acceptance criteria.
- `memory/MACRO-ROADMAP.md`: the long-range planning lens over Stages 9–15 — per-stage charters, pre-flight dependency friction, and cross-stage dependency spine. Non-binding direction; never carries the frontier.
- `memory/ROADMAP.md`: the currently authorised technical implementation sequence (Core, persistence, replay, transactions, projections, forks, validation).
- `AGENT_WORKFLOW.md`: how an agent executes a leg (session-start, gate-and-stop, verification, commit discipline). Operational, not strategic — kept out of this file.

Technical phase numbers and capability stage numbers are not interchangeable.

> **Authority note:** This document is authoritative for **capability sequencing and stage status**. `ROADMAP.md` is authoritative for **Core, persistence, replay, transaction, and technical-phase** mechanics. Where the two disagree on group-scale capability status, this document prevails; where they disagree on Core/persistence mechanics, `ROADMAP.md` prevails. See `DOMAIN_MAPPING.md` for the Capability-Stage ↔ Technical-Phase bridge.

Completing Technical Phase 5 does not mean the project is ready for player implementation.

## Core dependency chain

The intended progression is:

Internal pressures
-> perception and knowledge
-> memory
-> wants and goals
-> reasoning and planning
-> canonical action
-> physical consequence
-> social consequence
-> groups
-> culture
-> economy
-> institutions
-> ecology and demography
-> meaningful history
-> historical legibility
-> player embodiment
-> player-facing presentation

A later capability must not be treated as complete while the capabilities it depends on remain disconnected.

## Current position

The live frontier, and the reasons the frontier is where it is, are stated once in **Frontier and immediate next capability** (below). The deterministic authority spine (proposal/validation/commit, keyed RNG, replay, transactional persistence, forks, projections) is foundational to every stage here and is tracked in `ROADMAP.md`; it is a foundation for the capability stages, never a substitute for them.

# Capability Stage 6 - Living Agents

**Status: Implemented (v1) — acceptance-verified.** The versioned contracts, 6A–6D packages, bounded `living_settlement` scenario, read-only inspector, and two-run 320-tick deterministic acceptance gate are complete. **Verification evidence:** see [`CAPABILITY-STAGE-6-LIVING-AGENTS.md`](CAPABILITY-STAGE-6-LIVING-AGENTS.md).

## Goal

Create agents that perceive, remember, want, reason, plan, act, interact, experience consequences, and change future behaviour through one deterministic and inspectable loop.

Stage 6 is one integrated capability milestone.

Its internal packages may be implemented separately, but Stage 6 is not complete until 6A through 6E operate together.

## 6A - Internal State, Perception, Knowledge, and Memory

Implement:

- biological pressures
- psychological pressures
- social pressures
- individual preferences and tolerances
- wants distinct from immediate needs
- limited perception
- attention and visibility rules
- explicit knowledge
- confidence and provenance
- stale, incomplete, incorrect, inferred, and reported knowledge
- bounded meaningful memory
- memory significance, repetition, confidence, contradiction, and decay

Agents must act from information available to them rather than omniscient world state.

## 6B - Goals, Reasoning, and Planning

Implement:

- multiple candidate goals
- needs and wants contributing to goals
- threat and opportunity recognition
- obligations and relationship pressures
- deterministic goal scoring
- inspectable decision receipts
- deterministic tie-breaking
- bounded multi-step planning
- prerequisites
- tools and resource requirements
- branches and fallbacks
- interruption
- resumption
- replanning
- abandonment
- completion

Agents may make reasonable mistakes when their knowledge is stale, incomplete, or false.

## 6C - Canonical Actions and Physical Affordances

Implement:

- authoritative multi-stage action state
- movement
- gathering
- carrying
- storing
- retrieving
- consuming
- drinking
- resting
- tool use
- construction
- repair
- damage
- access
- giving and taking
- physical affordances
- inventory and storage
- tool durability
- resource depletion
- ownership and access
- tracks, noise, smoke, debris, wear, and environmental evidence

Actions must create persistent canonical world changes.

Descriptive events without corresponding world-state consequences do not satisfy this stage.

## 6D - Social Interaction and Relationship Consequences

Implement:

- requests
- offers
- cooperation
- refusal
- warning
- information sharing
- concealment and deception
- giving and trade
- threats
- apology
- promises
- repayment
- confrontation
- competition
- reconciliation
- multidimensional relationships
- trust
- affection
- fear
- respect
- resentment
- obligation
- familiarity
- perceived reliability
- explicit promises, favours, and debts
- causal information propagation
- rumour, contradiction, and confidence change

An entity must not react socially to an event it did not perceive or learn about through a causal route.

## 6E - Integrated Living-Agent Validation

Validate Stage 6 using a bounded scenario containing approximately:

- 6 to 12 entities
- a small camp or settlement
- food and water pressure
- tools and storage
- shelters
- changing weather
- family and non-family relationships
- incomplete knowledge
- competing goals
- at least one environmental or external threat

The scenario must demonstrate over hundreds of ticks:

- differing agent priorities
- needs and wants competing
- limited and incorrect knowledge
- plan creation
- action execution
- interruption
- failure
- replanning
- resource movement
- physical world change
- helping and obstruction
- promises and debts
- trust and resentment changes
- witnessed and unwitnessed consequences
- memory affecting later behaviour
- information propagation
- delayed consequences
- deterministic replay

## Stage 6 completion gate

The complete loop must be inspectable:

Pressure
-> want or concern
-> goal candidates
-> selected goal
-> plan
-> canonical action
-> proposal
-> accepted event
-> world consequence
-> perception
-> knowledge
-> memory
-> internal or relationship change
-> future decision

Stage 6 must not be marked complete if any link remains disconnected.

The implemented loop is connected through canonical entity state, proposal validation, accepted mutations/events, bounded perception/knowledge/memory, relationship and commitment consequences, future decisions, API projection, and frontend inspection. Rejected proposals do not mutate canonical truth.

# Capability Stage 7 - Households, Groups, and Collective Behaviour

## Goal

Allow persistent social structures to emerge from individual relationships, shared needs, repeated cooperation, conflict, and history.

Implement:

- households
- family units
- work groups
- camps and settlements
- shared inventories
- shared shelter and infrastructure
- division of labour
- group membership
- leadership
- group goals
- collective decisions
- contribution and free-rider pressure
- internal disputes
- alliances
- rivalries
- group reputation
- group memory
- membership change
- group formation, splitting, merging, and collapse

Groups must arise from canonical relationships and events rather than appearing as unsupported labels.

## Stage 7A — Emergent Association and Group Recognition

**Status: Implemented (v1) — acceptance-verified.** **Verification evidence:** see [`CAPABILITY-STAGE-7A-EMERGENT-GROUPS.md`](CAPABILITY-STAGE-7A-EMERGENT-GROUPS.md); recorded scenario baseline in the Milestone changelog.

Stage 7A adds a proposal-only association domain, one bounded canonical association registry, content-derived pair/group identities, weighted accepted-event evidence, deterministic candidate creation and recognition, complete-link membership growth, member removal, weakening, expiry, dissolution, Core validation/provenance stamping, generic persistence/replay, and a read-only diagnostic API projection.

The Stage 6 `living_settlement` activation remains unchanged. Stage 7A uses the explicit `emergent_groups` scenario so new accepted association events do not rewrite the validated Stage 6 deterministic trace.

Acceptance: focused Stage 7A suite passes; live concurrency tests pass; the broad backend regression is green (excluding the four known Docker-path API modules); independent 320-tick traces match the recorded canonical state and association-summary baselines; association state stays within its hard cap with target headroom.

## Stage 7B - Bounded Shared Group State and Collective Proposal Contract

**Status: Implemented (v1) — acceptance-verified.** **Verification evidence:** see [`CAPABILITY-STAGE-7B-SHARED-GROUP-STATE.md`](CAPABILITY-STAGE-7B-SHARED-GROUP-STATE.md); recorded scenario baseline in the Milestone changelog.

Stage 7B adds a separately versioned `group-shared-state-registry-v1`, a proposal-only `group_state` domain, a narrow `collective-group-proposal-v1` contract, Core validation/provenance stamping, generic persistence/replay integration, a read-only diagnostic API projection, and an explicit `collective_groups` scenario.

The only implemented shared fact categories are `shared_shelter` and `shared_storage`. A collective proposal requires a currently recognised Stage 7A group, two explicit current group members, fresh accepted Stage 7A evidence, an accepted association-registry causal parent, deterministic proposal identity, and revision preconditions for both association and group-state registries.

Recognition alone does not create shared state or authorise collective action. Membership does not imply consent. Stage 7B proposals may mutate only `group-shared-state-000`; they cannot mutate person state, move resources, spend inventory, create group goals, install leadership, command members, or bypass existing individual validators.

The Stage 6 `living_settlement` and Stage 7A `emergent_groups` activations remain unchanged. Stage 7B uses the explicit `collective_groups` scenario so new accepted group-state events do not rewrite validated Stage 6 or 7A traces.

Acceptance: focused Stage 7B suite passes; affected Stage 6/7 suites pass; live Mongo concurrency tests pass; the broad backend regression is green (same Docker-path exclusions); independent 320-tick `collective_groups` traces match the recorded canonical state, association-summary, and group-state-summary baselines.

## Stage 7B.1 - Shared Group-State and Association Capacity Hardening

**Status: Implemented (v1) — acceptance-verified.** **Verification evidence:** see [`CAPABILITY-STAGE-7B-SHARED-GROUP-STATE.md`](CAPABILITY-STAGE-7B-SHARED-GROUP-STATE.md); recorded scenario baseline in the Milestone changelog.

Stage 7B.1 preserves the Stage 7A/7B authority and scenario boundaries while removing replay-redundant canonical bookkeeping. Association recent-evidence rows use a backward-compatible compact representation and category summaries retain two specific event references plus the existing aggregate provenance. Group-state compaction removes duplicated group-level proposal summaries before fact-local support history and preserves the existing processed-key window.

The association and group-state hard caps (128 KiB / 64 KiB) are unchanged; operational targets are 96 KiB / 48 KiB. Exact read-only byte composition, peak tick/headroom, retained-history counts, capacity rejection reasons, replay equality, resume-boundary equality, and post-320 current-truth changes are reported by the living-agent harness.

Acceptance: two matching 1,000-tick `collective_groups` runs including a mid-run restart boundary; replay and resume equality; no payload-cap rejection caused by historical state; green Stage 6/7 regressions; and at least 20% peak headroom in both registries.

## Stage 7C - Group Behaviour and Collective Action

**Status: Mechanism-verified; organic emergence Deferred — Stage-9-blocked** (see Global deferral register). **Verification evidence:** see [`CAPABILITY-STAGE-7C-GROUP-COLLECTIVE.md`](CAPABILITY-STAGE-7C-GROUP-COLLECTIVE.md).

Gates **met**: `group_collective` persistence + replay survival, integrated 6→7A→7B→7C determinism (`repeat`/`replay` true with the domain live), read-only projection safety, and capacity headroom above target — proven by the focused suite and a 1,000-tick `collective_groups` run.

Gate **deferred, not open**: organic long-run reachability. A seeded 1,000-tick run produced 0 collective proposals because storage actions are effectively absent (agents have no surplus to store), so the `shared_storage` fact 7C consumes never forms — only `shared_shelter` does. Reliable surplus is a **Stage 9 (Economy)** capability, downstream of 7C; forcing it via Stage 6 planner tuning was tested and rejected. Organic emergence is therefore dependency-blocked on Stage 9, and the seeded scenario stands as 7C's mechanism proof. This removes 7C from the critical path for the next-stage decision.

Stage 7C adds a proposal-only `group_collective` domain and the narrow `coordinated_storage_deposit` action (`group-collective-action-v1`). Recognised Stage 7A membership plus Stage 7B `shared_storage` facts supply context only. Eligible living members adjacent to the shared storage deposit carried resources under a deterministic initiator (first eligible member id). Core validates, revalidates, and alone mutates person inventories and storage contents.

The group is not a super-agent: no private group planner, no leadership, no obedience, no automatic inclusion of all members. The `collective_groups` scenario enables `group_collective` after `group_state`.

Leadership, voting, governance, warfare, diplomacy, culture, religion, politics, and Stage 8 institutions remain out of scope.

## Stage 7D - Group Goals and Leadership Coordination

**Status: Implemented (v1) — verified via the Stage 6 Liveness Pass.** **Verification evidence:** see [`CAPABILITY-STAGE-7D-GROUP-GOALS-LEADERSHIP.md`](CAPABILITY-STAGE-7D-GROUP-GOALS-LEADERSHIP.md) and [`STAGE-6-LIVENESS-PASS.md`](STAGE-6-LIVENESS-PASS.md).

Stage 7D adds proposal-only group goals (e.g. `maintain_shared_shelter`) that recognised groups adopt from repeated shared-shelter degradation, with a read-only survival-dominated influence hook and a coordinator record that is a record, not a commander. Organic adoption is exercised in the `collective_groups` run. Same guardrails as 7C: no hidden group mind; influence never outranks survival; forbidden fields absent.

# Capability Stage 8 - Culture, Norms, Beliefs, and Knowledge Transmission

**Status: Partially complete — core-culture-loop delivery in progress, gate-and-stop by leg.** Leg 8A **Emergent Norms** is Implemented (v1, mechanism-verified) and committed; its organic influence-firing gate is **Deferred — scenario-dynamics-blocked** (see Global deferral register). Leg 8B Leg 1 **Norm Transmission** is VERIFIED and close-out committed (2026-07-24). Stage 8C's first leg, **Leg A Aid Exchange**, is **Deferred — Stage-9-blocked** (two gated attempts, 2026-07-24; G1 unreachable under scenario scarcity — see Global deferral register and the leg contract; no Leg A code committed). Legs 8C (plurality / enforcement) → 8D (divergence / diffusion / conflict / event-change) follow, each spec'd from measured evidence and confirmed at a STOP. The Stage 8 item list below is graded at the Stage 8 close-out audit (Implemented / Deferred-Stage-9-blocked / Deferred-content-stage); **the stage is not marked complete because the core loop exists.** Hard boundary: nothing that requires Stage 9 surplus/economy. **Verification evidence:** see [`CAPABILITY-STAGE-8A-EMERGENT-NORMS.md`](CAPABILITY-STAGE-8A-EMERGENT-NORMS.md), [`CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md`](CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md), and the active leg contract.

## Goal

Allow repeated behaviour, shared history, environment, teaching, and group identity to form persistent cultures.

Implement:

- norms
- customs
- rituals
- traditions
- taboos
- values
- social expectations
- identity
- naming conventions
- symbolic objects
- beliefs
- myths
- teaching
- imitation
- generational knowledge transfer
- cultural adaptation
- cultural divergence
- cultural diffusion
- cultural conflict
- norm enforcement
- norm change after major events

Culture must affect decisions and consequences.

It must not exist only as generated descriptive text.

The same act may be interpreted differently by different cultures because their ownership, obligation, authority, family, or resource-sharing rules differ.

# Capability Stage 9 - Production, Ownership, Trade, and Economy

Long-range charter, per-stage pre-flight dependency friction, and provisional leg carve live in [`MACRO-ROADMAP.md`](MACRO-ROADMAP.md). This section holds the capability definition and item list only.

## Goal

Create an economy arising from scarcity, labour, tools, skills, ownership, transport, storage, demand, and exchange.

Implement:

- labour
- skills
- productivity
- production chains
- extraction
- processing
- crafting
- maintenance
- tool quality
- storage
- spoilage
- transport and logistics
- ownership
- possession
- shared property
- access rights
- demand
- scarcity
- barter
- trade
- value estimation
- contracts
- obligations
- specialisation
- surplus
- shortages
- wealth differences
- inheritance
- theft
- coercive exchange
- economic dependency

Economic values must emerge from world conditions and agent decisions rather than arbitrary fixed prices alone.

# Capability Stage 10 - Institutions, Governance, Law, and Conflict Resolution

Long-range charter and pre-flight friction: [`MACRO-ROADMAP.md`](MACRO-ROADMAP.md).

## Goal

Allow communities to create persistent systems for coordination, authority, rules, enforcement, and shared projects.

Implement:

- leadership
- authority
- legitimacy
- succession
- councils and collective decisions
- rules and laws
- dispute resolution
- restitution
- punishment
- enforcement
- public contributions
- taxation where appropriate
- communal property
- public works
- offices and roles
- corruption
- favouritism
- resistance
- rebellion
- diplomacy
- treaties
- organised conflict
- war and peace

Institutions must have historical causes, participants, supporters, opponents, and consequences.

They must not appear as unsupported world-generation templates.

# Capability Stage 11 - Ecology, Demography, Lifecycles, and World-Scale Change

Long-range charter and pre-flight friction: [`MACRO-ROADMAP.md`](MACRO-ROADMAP.md).

## Goal

Make population and environment evolve independently of any player.

Implement:

- relationships and reproduction
- fertility
- conception
- pregnancy
- birth
- childhood and development
- ageing
- illness
- injury
- disability
- death
- family lines
- inheritance
- population movement
- migration
- settlement growth
- settlement decline
- settlement abandonment
- predator-prey relationships
- plant and resource cycles
- seasons
- weather patterns
- disease spread
- ecological depletion
- ecological recovery
- disasters
- climate pressure
- technological spread
- cultural spread
- population bottlenecks

Population must remain lifecycle-driven.

Do not introduce target-population spawning or population-balancing creation mechanics.

# Capability Stage 12 - Integrated Historical Burn-In

Long-range charter and pre-flight friction: [`MACRO-ROADMAP.md`](MACRO-ROADMAP.md).

## Goal

Run the complete pre-player world for long periods so history emerges from actual simulation systems.

Burn-in should be capable of creating:

- family histories
- births and deaths
- old injuries
- grudges
- friendships
- debts
- inherited property
- trade routes
- abandoned structures
- settlement growth and collapse
- resource depletion
- cultural traditions
- territorial claims
- leadership changes
- laws
- rebellions
- wars
- alliances
- ecological damage
- ecological recovery
- inventions
- lost knowledge
- extinct groups
- institutions with traceable origins

Burn-in is not complete merely because many ticks elapsed.

Meaningful history requires the earlier social, cultural, economic, institutional, ecological, and demographic systems to exist first.

Burn-in also acts as a deterministic long-run stress test.

# Capability Stage 13 - Historical Compression and World Legibility

Long-range charter and pre-flight friction: [`MACRO-ROADMAP.md`](MACRO-ROADMAP.md).

## Goal

Make large amounts of canonical history understandable without losing traceability.

Implement:

- significance scoring
- event summarisation
- historical periods and eras
- entity biographies
- family histories
- settlement histories
- faction histories
- cultural histories
- economic summaries
- territorial histories
- institutional origins
- preserved causal ancestry
- drill-down from summaries to accepted events
- why-is-the-world-like-this queries
- first-divergence inspection
- bounded diagnostic retention
- durable preservation of major events

Historical compression must not replace canonical accepted events as the source of truth.

# Capability Stage 14 - Player Entry and Embodiment

Long-range charter and pre-flight friction: [`MACRO-ROADMAP.md`](MACRO-ROADMAP.md).

## Goal

Insert a player-controlled actor into an already functioning world without creating a separate reality for the player.

Support:

- selecting or generating an origin
- selecting an existing or new actor where allowed
- location and household context
- faction or cultural affiliation
- inherited relationships
- physical needs
- limited perception
- knowledge boundaries
- memory
- ownership
- laws
- cultural expectations
- social reputation
- economic constraints
- injury
- mortality
- consequences
- world reactions

The player must use the same action, consequence, social, economic, institutional, and physical rules as other agents.

Player entry must not reset or invalidate existing world history.

# Capability Stage 15 - Player-Facing Interaction and Narrative Projection

Long-range charter and pre-flight friction: [`MACRO-ROADMAP.md`](MACRO-ROADMAP.md).

## Goal

Present the canonical simulation through understandable controls, feedback, and narrative without allowing presentation systems to create truth.

Implement:

- player action controls
- interaction selection
- dialogue interfaces
- maps
- journals
- discovered history
- rumours
- relationship presentation
- inventory and ownership presentation
- plans and commitments
- consequence feedback
- accessible explanations
- uncertainty and knowledge boundaries
- narrative projection
- event summarisation
- causal explanation
- player-facing timeline
- appropriate consequence previews
- accessibility and usability systems

Narrative remains output.

Canonical simulation state and accepted events remain truth.

# Global completion rules (the decade test)

A capability stage may only be marked complete when:

1. Its canonical state is explicit and versioned.
2. Its behaviour is deterministic.
3. Its actions use the proposal and commit authority spine.
4. Its outcomes survive persistence and replay.
5. Rejected proposals cannot mutate truth.
6. Its cause-and-effect chain is inspectable.
7. Its frontend projection cannot mutate truth.
8. Its performance limits are explicit.
9. Its integrated tests pass.
10. Its documentation matches the implementation.

Partial implementation should be recorded as one of: **Planned · In progress · Implemented — verification pending · Blocked · Deferred** (deferrals additionally carry a taxonomy category and a register row, below).

Do not mark an entire capability stage complete because one mechanic within it exists.

## Protected baselines (guardrail — not forensic dust)

Two classes of hash exist, and only one is disposable:

- **Frozen regression baseline** — the `living_settlement` 320-tick final-state hash. It is a **tripwire**: any change that moves it is a Stage-6-dynamics change and requires explicit re-baseline authorisation at a STOP. It stays named here, in the authority doc, because it is a protected constant, not a run artifact. Its current value is recorded in `CLAUDE.md` / `CAPABILITY-DOCTRINE.md`.
- **Scenario baselines** — the per-stage `collective_groups` / `emergent_groups` / association / group-state summary hashes. These **re-baseline by design** whenever a culture scenario intentionally changes. They are recorded, dated, in the Milestone changelog and in the relevant contract doc — not in the stage prose, which would rot.

## Deferral taxonomy

Every deferred gate item across every capability stage is classified as exactly one of the following four categories. A deferral without its required record is an **open gate**, not a closed one. Never invent a fifth category ad hoc; if none of the four fits, stop and propose one for explicit ratification before using it.

- **Deferred — Stage-9-blocked**: the gate honestly requires surplus/economy mechanics that do not exist before Stage 9. Required record: the concrete Stage 9 dependency (7C-style — name the specific mechanic, e.g. "requires reliable resource surplus to produce `shared_storage` facts").
- **Deferred — content stage**: the item is myth, ritual, symbolic-object, naming-convention, or generational-myth material reserved for a later content-authoring pass, per ratified core-loop scope decisions. Required record: the scope decision that excluded it and where it was made.
- **Deferred — scenario-dynamics-blocked**: the mechanism is implemented and mechanism-verified through the real commit pipeline, but the *scenario's* dynamics never produce the conditions the organic gate measures — a property of the chosen scenario, not an implementation defect. Required record: (a) the blocking measurement (probe/tick evidence the conditions cannot co-occur); (b) the concrete unblock condition (an alternative/extended scenario, or an authorised dynamics change with its re-baseline consequence named); (c) an explicit statement that no threshold was lowered to manufacture a firing.
- **Deferred — demography-blocked (Stage 11)**: the gate requires lifecycle events (births/deaths) that the simulated horizon does not produce. Required record: the probe evidence showing zero in-horizon lifecycle events.

## Global deferral register

Every deferred gate item, in one place. A row here is the decision reference; the required forensic record lives in the named contract doc.

| Deferred item | Category | Unblock condition | Frontier impact |
|---|---|---|---|
| 7C organic collective emergence | Stage-9-blocked | Reliable resource surplus so `shared_storage` facts form (Stage 9 economy). Planner-tuning route tested and rejected. | Not blocking: 7C mechanism verified; not on the critical path. Re-gate at Stage 9. |
| 8A gate-5 organic influence firing | scenario-dynamics-blocked | A `collective_groups`-family scenario where a repair-candidate window and a norm-active window co-occur (repairs cease ~tick 236; norms active 377+; disjoint by construction). No threshold was lowered. | Does not block 8B transmission mechanics. Resolved by the ruled purpose-built culture scenario. |
| 8C Leg A aid-exchange organic completion (G1) | Stage-9-blocked | A reliable food surplus so a responder holds carried food ≥ 2 at request time (measured: sole responder holds exactly 1 for the whole window; ≥1 re-creates the aid-caused death, ≥2 never fires — no calibration target). Full v2 build preserved; revival re-enters at the proven A1 design. See `CAPABILITY-STAGE-8C-LEGA-AID-EXCHANGE.md` attempt-2 record. | Does not block the next 8C leg. Re-gate at Stage 9 alongside 7C. |
| Generational knowledge transfer | demography-blocked (Stage 11) | In-horizon births (probe evidence). Expected at 8B; lands at Stage 11 (11A) if the horizon shows no births. | Does not block the 8B taught/imitated pathway. |
| Myths, rituals, symbolic objects, naming conventions, beliefs-as-lore | content stage | A ratified content-authoring pass. **Landing stage UNASSIGNED — decision required** (fold into 12/13, or an explicit content stage). | Out of the Stage 8 core-loop scope; does not block 8B–8D mechanics. |
| Stage 9 economy (whole stage) | (hard sequence boundary, not a taxonomy deferral) | Stage 8 core loop closes. | Hard stop: no production/surplus/ownership/trade/currency until then. Also gates 7C's re-gate. |

## Test-suite flake ledger (separate from capability deferrals)

`test-flake` classifies *test-infrastructure* non-determinism (a test intermittently fails under identical code and environment) — orthogonal to whether a capability gate is honestly deferred. It is **not** a fifth deferral category; the four-category list stays closed. Required record for any sighting: test name, assertion signature, observed vs expected, run counts on both baseline and current side, the baseline comparison SHA, and the environment-parity method used to rule out confounds. Full sighting narratives live in `memory/evidence/` and git history, not here.

**Open canary — P1 stabilisation ticket (do not lose):** under `asyncio.gather` CAS contention, the `revision` increment is observed as `N == N` (no-op where +1 expected) in `test_concurrent_stage7a_steps_do_not_duplicate_groups_or_head` and (suspected, same shape) `test_concurrent_stage7b_steps_do_not_duplicate_shared_state_or_head`. Confirmed a **pre-existing test-flake** by a controlled 10-run scratch-DB A/B against a pre-change worktree (identical failure signature both sides ⇒ not change-caused; sighting 2026-07-19, detail in `memory/evidence/`). But it is a correctness canary in an optimistic-concurrency event-sourced engine: determine whether it is a genuine engine lost-update (a second concurrent `step_run` silently no-ops instead of retrying/erroring) or a test-side read race, via instrumentation. Not yet investigated.

# Frontier and immediate next capability

**Frontier:** Stages 6, 7A, 7B, 7B.1, 7C (mechanism-verified; organic emergence Stage-9-blocked), and 7D are implemented and committed. Stage 8A is Implemented (v1, mechanism-verified); its gate-5 organic firing is Deferred — scenario-dynamics-blocked (register above).

**Frontier: see `FRONTIER.md`.** *(Historical: as of 2026-07-24 the frontier moved to Layer C — Behaviour Enrichment. Do not take a frontier from this archived file.)* Stage 8B Leg 1 (Norm Transmission / individual carriage) is
**VERIFIED and close-out committed (2026-07-24)** — see
[`CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md`](CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md)
and `memory/evidence/stage-8b-leg1/`. 8B made norm carriage per-individual and
observable (formation backfill + imitation via `social_request_help`) so culture
can outlive originators under carriage-only eligibility. Stage 8C's first leg
(**Leg A Aid Exchange**) ran two gated implementation attempts on 2026-07-24 and
is **Deferred — Stage-9-blocked** (register above; contract:
[`CAPABILITY-STAGE-8C-LEGA-AID-EXCHANGE.md`](CAPABILITY-STAGE-8C-LEGA-AID-EXCHANGE.md));
no Leg A code is committed. The next 8C leg (plurality / enforcement family) is
spec'd from measured evidence and confirmed at a STOP, at the user's
initiative — gate-and-stop discipline unchanged.

In parallel, the technical **5A2** live-transaction gate (transaction-capable Mongo) remains unexercised. **Stage 9 (Economy)** stays on the critical path for 7C's organic emergence (surplus-blocked) but is out of bounds until Stage 8's core loop closes.

**Guardrail (all Stage 7/8 culture work):** no hidden group mind — norms, goals, and leadership remain proposal-only, Core-authored, member-grounded; influence never outranks survival; forbidden fields (`inventory, authority, obedience, orders, law, command, punishment`) absent from every record. No obedience, warfare, diplomacy, politics, religion, economy, or player control until separately contracted.

# Parked proposals (not on the critical path)

**PROPOSED — Branch Mode (post-Stage-8 candidate).** Two distinct modes over recorded history. *Replay*: reconstruct and inspect a past run exactly as it occurred from event-sourced history (existing capability; used for verification). *Branch*: resume live simulation from a chosen historical tick with a fresh RNG seed, producing a genuinely divergent but fully traceable new timeline from that point. Rationale: verification requires same-seed determinism (lab condition, one variable at a time); the living simulation should also support natural divergence when re-run from a past state. Branching delivers "same world, new future" without weakening replay-based verification — both modes run on the event-sourcing and snapshot substrate already built. Requirements sketch (unscoped): branch-from-tick with new seed; timeline identity so branched runs are never mistaken for canonical history; ruling on dev-tool vs player-facing. Status: parked pending Leg 1 close-out, the discriminating probe result, and the ruled purpose-built scenario work. Requires its own contract before any implementation. User-proposed and parked.

# Milestone changelog

Timeless-body policy: absolute dates, re-baseline events, and recorded scenario hashes live here, not in the stage prose above. Newest first. Exact per-run test counts and byte peaks live in the per-stage contract docs and `memory/evidence/`.

- **2026-07-21** — Roadmap restructured: forensic run-data (test counts, scenario hashes, byte peaks) moved out of stage prose into contracts + this changelog; Global deferral register added; frozen vs scenario baselines separated (Protected baselines); operational instructions moved to `AGENT_WORKFLOW.md`; Stages 9–15 long-range detail delegated to `MACRO-ROADMAP.md`.
- **2026-07-18** — Stage 8A (Emergent Norms) committed, mechanism-verified; gate-5 organic firing recorded Deferred — scenario-dynamics-blocked.
- **2026-07-14** — Stage 7C committed (`ca2419e0`), mechanism-verified, organic emergence Stage-9-blocked. Stage 7D verified via the Stage 6 Liveness Pass (`f6850d0b`).
- **Recorded scenario baselines (re-baseline by design when the scenario intentionally changes; confirm against the relevant contract doc before trusting):**
  - Stage 7A `emergent_groups` 320-tick: state `4016f097c3bab6ff1fd9590c5e46731144dff1f6e5c868910c5a0da3bb4ec4e2`, association-summary `01af6144c2fdaac92fe4b451cb12ffffaae7976fdf29d6f78f16581132185701`.
  - Stage 7B `collective_groups` 320-tick: state `86a7dc7fa994d95d6c8c7016ddc127bf7f9d6f7d7b34eb610769a8dcb05482df`, association-summary `e286f69d8e3baa60289c014681c9c60f2279b6a1f3c72ff413aaf623e6d7a550`, group-state-summary `aab2c7565d74d0747f28c544e75701afc54661b706cf1c6a8f9072b27d603fae`.
  - Stage 7B.1 `collective_groups` 1,000-tick (seed `stage7b1-capacity`): final-state `31f27b2c15be45d76946b898c0d0dcd791edfe49ce52b49758a0b2517b686d89`.
- **Frozen regression baseline (protected — moves only by authorised re-baseline):** `living_settlement` 320-tick — value in `CLAUDE.md` / `CAPABILITY-DOCTRINE.md`.
