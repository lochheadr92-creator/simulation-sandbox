# Simulation Sandbox Capability Roadmap

## Purpose

This document defines the long-range capability order for Simulation Sandbox.

It is separate from `memory/ROADMAP.md`, which remains the technical execution roadmap for architecture, persistence, replay, transactions, projections, forks, validation, and other implementation work.

The three planning documents have different responsibilities:

- `Domain Plan.txt`: what the simulation may eventually support.
- `memory/CAPABILITY_ROADMAP.md`: the dependency order in which major simulation capabilities become real.
- `memory/ROADMAP.md`: the currently authorised technical implementation sequence.

Technical phase numbers and capability stage numbers are not interchangeable.

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

## Stage 7B boundary — Planned, not authorised

Stage 7B may introduce a separately versioned shared-group state and narrowly
bounded collective proposal contract. It must not begin by treating recognition
as consent or authority. Shared inventory, collective goals/actions, leadership,
obedience, culture, settlement governance, warfare, politics, and player control
remain absent until separately contracted and accepted.

# Capability Stage 8 - Culture, Norms, Beliefs, and Knowledge Transmission

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

# Immediate next capability

With Capability Stage 7A verified, the next dependency-ordered capability is:

**Capability Stage 7B - Bounded Shared Group State and Collective Proposals**

Stage 7B is not authorised by Stage 7A completion alone. It requires its own
bounded contract, implementation request, checkpoint plan, and acceptance gate.
