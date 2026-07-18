# Simulation Sandbox Capability Roadmap

## Purpose

This document defines the long-range capability order for Simulation Sandbox.

It is separate from `memory/ROADMAP.md`, which remains the technical execution roadmap for architecture, persistence, replay, transactions, projections, forks, validation, and other implementation work.

The three planning documents have different responsibilities:

- `Domain Plan.txt`: what the simulation may eventually support.
- `memory/CAPABILITY_ROADMAP.md`: the dependency order in which major simulation capabilities become real.
- `memory/ROADMAP.md`: the currently authorised technical implementation sequence.

Technical phase numbers and capability stage numbers are not interchangeable.

> **Authority note (2026-07-14):** This document is authoritative for **capability
> sequencing and stage status**. `ROADMAP.md` is authoritative for **Core,
> persistence, replay, transaction, and technical-phase** mechanics. Where the
> two disagree on group-scale capability status, this document prevails; where
> they disagree on Core/persistence mechanics, `ROADMAP.md` prevails. See
> `DOMAIN_MAPPING.md` for the Capability-Stage ↔ Technical-Phase bridge.

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

The project is currently strengthening the deterministic authority spine through the technical roadmap.

Current work includes areas such as:

- proposal, validation, commit, and rejection authority
- deterministic ordering
- keyed RNG
- replay and divergence verification
- transactional persistence
- canonical ongoing actions
- forks and lineage
- causal records
- observer-specific projections
- frontend inspection and diagnostics

These systems are foundations for the capability stages below.

They are not substitutes for the capabilities below.

# Capability Stage 6 - Living Agents

**Status: Implemented and verified (2026-07-13).** The versioned contracts,
6A–6D packages, bounded `living_settlement` scenario, read-only inspector, and
two-run 320-tick deterministic acceptance gate are complete. See
[`CAPABILITY-STAGE-6-LIVING-AGENTS.md`](CAPABILITY-STAGE-6-LIVING-AGENTS.md).

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

The implemented loop is connected through canonical entity state, proposal
validation, accepted mutations/events, bounded perception/knowledge/memory,
relationship and commitment consequences, future decisions, API projection,
and frontend inspection. Rejected proposals do not mutate canonical truth.

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

Status: **Implemented and acceptance-verified.**

Stage 7A adds a proposal-only association domain, one bounded canonical
association registry, content-derived pair/group identities, weighted accepted-
event evidence, deterministic candidate creation and recognition, complete-link
membership growth, member removal, weakening, expiry, dissolution, Core
validation/provenance stamping, generic persistence/replay, and a read-only
diagnostic API projection.

The Stage 6 `living_settlement` activation remains unchanged. Stage 7A uses the
explicit `emergent_groups` scenario so new accepted association events do not
rewrite the validated Stage 6 deterministic trace.

Verified gate: 22 focused tests passed; 3 live concurrency tests passed; the
broad backend set passed 231 tests with only the four known Docker-path API
modules excluded; two independent 320-tick traces and one final confirmation
matched canonical state hash
`4016f097c3bab6ff1fd9590c5e46731144dff1f6e5c868910c5a0da3bb4ec4e2`
and association summary hash
`01af6144c2fdaac92fe4b451cb12ffffaae7976fdf29d6f78f16581132185701`.
Maximum canonical association state was 28 records, 9 candidates, 0 retained
dissolutions, and 128,981 registry bytes.

## Stage 7B - Bounded Shared Group State and Collective Proposal Contract

Status: **Implemented and locally acceptance-verified.**

Stage 7B adds a separately versioned `group-shared-state-registry-v1`, a
proposal-only `group_state` domain, a narrow `collective-group-proposal-v1`
contract, Core validation/provenance stamping, generic persistence/replay
integration, a read-only diagnostic API projection, and an explicit
`collective_groups` scenario.

The only implemented shared fact categories are `shared_shelter` and
`shared_storage`. A collective proposal requires a currently recognised Stage
7A group, two explicit current group members, fresh accepted Stage 7A evidence,
an accepted association-registry causal parent, deterministic proposal identity,
and revision preconditions for both association and group-state registries.

Recognition alone does not create shared state or authorise collective action.
Membership does not imply consent. Stage 7B proposals may mutate only
`group-shared-state-000`; they cannot mutate person state, move resources,
spend inventory, create group goals, install leadership, command members, or
bypass existing individual validators.

The Stage 6 `living_settlement` and Stage 7A `emergent_groups` activations
remain unchanged. Stage 7B uses the explicit `collective_groups` scenario so
new accepted group-state events do not rewrite validated Stage 6 or 7A traces.

Verified gate: 24 focused Stage 7B tests passed; Stage 7A + Stage 7B focused
tests passed 46; affected Stage 6/7 tests passed 69; live Mongo concurrency
tests passed 4; the broad backend set passed 256 tests with only the four known
Docker-path API modules excluded; two independent 320-tick `collective_groups`
traces matched canonical state hash
`86a7dc7fa994d95d6c8c7016ddc127bf7f9d6f7d7b34eb610769a8dcb05482df`,
association summary hash
`e286f69d8e3baa60289c014681c9c60f2279b6a1f3c72ff413aaf623e6d7a550`,
and group-state summary hash
`aab2c7565d74d0747f28c544e75701afc54661b706cf1c6a8f9072b27d603fae`.

## Stage 7B.1 - Shared Group-State and Association Capacity Hardening

Status: **Implemented and acceptance-verified.**

Stage 7B.1 preserves the Stage 7A/7B authority and scenario boundaries while
removing replay-redundant canonical bookkeeping. Association recent-evidence
rows use a backward-compatible compact representation and category summaries
retain two specific event references plus the existing aggregate provenance.
Group-state compaction removes duplicated group-level proposal summaries before
fact-local support history and preserves the existing processed-key window.

The 128 KiB association and 64 KiB group-state hard caps are unchanged.
Operational targets are 96 KiB and 48 KiB respectively. Exact read-only byte
composition, peak tick/headroom, retained-history counts, capacity rejection
reasons, replay equality, resume-boundary equality, and post-320 current-truth
changes are reported by the living-agent harness.

Acceptance requires two matching 1,000-tick `collective_groups` runs, replay
and resume equality, no payload-cap rejection caused by historical state, green
Stage 6/7 regressions, and at least 20% peak headroom in both registries.

Verified gate: focused Stage 7A/7B tests passed 50; Stage 6C through 7B passed
73; live Mongo concurrency passed 4; and the broad backend gate passed 260
tests with the same four Docker-path exclusions and one existing warning. Two
1,000-tick traces with seed `stage7b1-capacity`, including a tick-320 restart
boundary, matched exactly. Association peaked at 95,628 / 131,072 bytes
(27.042% headroom) at tick 540; group state peaked at 49,374 / 65,536 bytes
(24.661% headroom) at tick 37. No payload-cap rejection occurred, and useful
association truth changed on 401 post-320 ticks. Final state hash:
`31f27b2c15be45d76946b898c0d0dcd791edfe49ce52b49758a0b2517b686d89`.

## Stage 7C - Group Behaviour and Collective Action

Status: **Mechanism-verified; organic emergence deferred (Stage 9-blocked)**
(committed `ca2419e0`, 2026-07-14). See
[`CAPABILITY-STAGE-7C-GROUP-COLLECTIVE.md`](CAPABILITY-STAGE-7C-GROUP-COLLECTIVE.md).

Gates **met** (15 focused tests + a 1,000-tick `collective_groups` run,
2026-07-14): `group_collective` persistence + replay survival, integrated
6→7A→7B→7C determinism (`repeat_matches`/`replay` true with the domain live),
read-only projection safety, and capacity headroom above target.

Gate **deferred, not open**: organic long-run reachability. A 1,000-tick seeded
run produced 0 collective proposals because storage actions are effectively
absent (agents have no surplus to store), so the `shared_storage` fact 7C
consumes never forms — only `shared_shelter` does. Reliable surplus is a
**Stage 9 (Economy)** capability, downstream of 7C; forcing it via Stage 6
planner tuning was tested and rejected. Organic emergence is therefore
dependency-blocked on Stage 9, and the seeded scenario stands as 7C's mechanism
proof. This removes 7C from the critical path for the next-stage decision.

Stage 7C adds a proposal-only `group_collective` domain and the narrow
`coordinated_storage_deposit` action (`group-collective-action-v1`). Recognised
Stage 7A membership plus Stage 7B `shared_storage` facts supply context only.
Eligible living members adjacent to the shared storage deposit carried
resources under a deterministic initiator (first eligible member id). Core
validates, revalidates, and alone mutates person inventories and storage
contents.

The group is not a super-agent: no private group planner, no leadership,
no obedience, no automatic inclusion of all members. The
`collective_groups` scenario enables `group_collective` after `group_state`.

Focused gate: 15 Stage 7C tests passed; Stage 7A + 7B + 7C focused suite passed
65. Leadership, voting, governance, warfare, diplomacy, culture, religion,
politics, and Stage 8 institutions remain out of scope.

# Capability Stage 8 - Culture, Norms, Beliefs, and Knowledge Transmission

**Status (2026-07-18): partially complete — core-culture-loop delivery in progress,
gate-and-stop by leg (`STAGE-8-MASTER-PROMPT.md`).** Leg 8A **Emergent Norms** is
mechanism-verified and committed (one `shelter_upkeep_norm` forms from repeated 7D
adoptions, influences an already-existing repair choice, decays; contract
`CAPABILITY-STAGE-8A-EMERGENT-NORMS.md`). Its organic influence-firing gate is
**Deferred — unobserved** (scenario horizon does not exercise the repair seam in the
norm window; recorded with tick evidence). Legs 8B (Transmission) → 8C (plurality /
enforcement) → 8D (divergence / diffusion / conflict / event-change) follow, each
spec'd from measured evidence and confirmed at a STOP. The Stage 8 item list below
is graded at the Stage 8 close-out audit (Implemented / Deferred-Stage-9-blocked /
Deferred-content-stage); the stage is **not** marked complete because the core loop
exists. Hard boundary: nothing that requires Stage 9 surplus/economy.

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

# Global completion rules

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

Partial implementation should be recorded as:

- Planned
- In progress
- Implemented - verification pending
- Blocked
- Deferred

Do not mark an entire capability stage complete because one mechanic within it exists.

# Frontier and immediate next capability

**Frontier (2026-07-18):** Stages 6, 7A, 7B, 7B.1, 7C, and **7D** are implemented
and committed. Stage 7C is mechanism-verified (organic emergence deferred as
Stage-9-blocked). Stage 7D is verified via the Stage 6 Liveness Pass (`f6850d0b`).
**Stage 8A (Emergent Norms) is mechanism-verified and committed** — one
`shelter_upkeep_norm` crystallises from repeated Stage 7D adoptions, influences an
already-existing repair choice (read-only, survival-dominant, transmission-inclusive),
and decays; its gate-5 *organic influence firing* is **Deferred — unobserved**
because the `collective_groups` horizon does not exercise the repair seam in the
norm-active window (repairs cease ~tick 236; norms form 377+; disjoint), evidenced
and recorded in `CAPABILITY-STAGE-8A-EMERGENT-NORMS.md`. Stage 8A is **partially
complete (core loop / mechanism-verified)**, not complete.

**The single frontier is: Stage 8B (Transmission) — decision + contract.** Per the
Stage 8 gate-and-stop plan (`STAGE-8-MASTER-PROMPT.md`), 8B makes norm carriage
per-individual and observable (teaching/imitation via the 6C/6D seams) so culture
outlives its originators. Its contract is written from measured probes of the
committed 8A run and confirmed at a STOP before implementation. In parallel, the
technical **5A2** live-transaction gate (transaction-capable Mongo) remains
unexercised. **Stage 9 (Economy)** stays on the critical path for 7C's organic
emergence (surplus-blocked) but is out of bounds until Stage 8's core loop closes.

Guardrail (all Stage 7/8 culture work): no hidden group mind — norms, goals, and
leadership remain proposal-only, Core-authored, member-grounded; influence never
outranks survival; forbidden fields (`inventory, authority, obedience, orders, law,
command, punishment`) absent from every record. No obedience, warfare, diplomacy,
politics, religion, economy, or player control until separately contracted.
