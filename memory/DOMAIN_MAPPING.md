# Domain Plan ↔ Roadmap Mapping

## Authority

| Document | Role |
|---|---|
| [Domain Plan](../Domain%20Plan.txt) | Long-range capability vision and domain catalogue. Conceptual layer ordering. |
| [ROADMAP.md](ROADMAP.md) | **Execution authority** for current phase order, dependencies, status, scope, acceptance gates, and explicit deferrals. |
| This document | Alignment bridge only. Does not authorise work. |

**Delivery policy:** closely related phases may ship as one sequential work package under the roadmap section *Delivery model — visible vertical slices with hardening checkpoints*. Package delivery does not merge phase identities, bypass dependencies, or mark soft-gate work complete. See [ROADMAP.md](ROADMAP.md).

### Binding rules

1. **A domain appearing in the Domain Plan does not authorise implementation.**
2. **Implementation requires an explicit roadmap phase or approved phase contract** in `memory/ROADMAP.md` (or a linked ADR/phase contract the roadmap cites).
3. **Partial foundations must not be described as complete domain implementations.**
4. **Repository code and phase status must not be inferred from the Domain Plan alone.** Use the roadmap status labels and recorded verification evidence.
5. When this mapping and the Domain Plan disagree on *what exists in vision*, prefer the Domain Plan for catalogue breadth. When they disagree on *what may be built now*, prefer the roadmap.

Related doctrine: [SOURCE-OF-TRUTH-v2.md](SOURCE-OF-TRUTH-v2.md), [ADR-001-fork-semantics.md](ADR-001-fork-semantics.md).

---

## Coverage status vocabulary

| Status | Meaning |
|---|---|
| **implemented foundation** | Durable Core/capability base in place; not a product “domain complete” claim. |
| **implemented narrow slice** | Bounded phase delivered; long-range domain remains incomplete. |
| **active** | Next or current execution focus on the roadmap. |
| **planned** | Explicit future phase on the roadmap; not started. |
| **partially represented** | Some related code or phase exists; vision domain is not covered. |
| **explicitly deferred** | Roadmap or phase contract forbids starting now. |
| **unassigned** | In Domain Plan vision; no complete execution phase yet. |
| **prohibited from implicit implementation** | Must not be absorbed into unrelated phases without a new roadmap assignment. |

---

## Narrow-scope distinctions (mandatory)

These prevent silent overclaiming:

| Claim that is **false** | Correct statement |
|---|---|
| 5A5 is full cognition | **5A5** covers **Perception, Knowledge, and Planning foundations only** (plus Needs-driven urgency already in utility). |
| 5B1 is the Economy Domain | **5B1** is giver-owned **food transfer** only — not Economy, markets, or property law. |
| 5B2 is Relationships / Memory / Emotion | **5B2** is **social-observation-v1** coarse visible facts only — not Relationships, Personality, Emotion, or general Memory. |
| 5B3 is dialogue / barter / trust | **5B3 `food-interaction-v1`** is a bounded **request / offer / response / expiry / invalidation / fulfilment** protocol only. Not dialogue, bargaining, trust, reputation, mood, personality, barter, or generic resource exchange. |
| 5B4 is the Memory Domain | **5B4** is an **interaction-memory-v1 slice** only, not the complete Memory Domain. |
| 5B5 is universal trust | **5B5** is **derived reciprocity-trust-v1** signals — not a freely mutable universal trust or relationship system. |
| 5C is a macroeconomy | **5C** is **resource organisation foundations** — not a complete macroeconomy. |
| 5D completes environment | **5D** foundations do **not** automatically satisfy full Ecology, Terrain, Climate, Animal, or Weather domains. |
| 5F is population control | **5F** reproduction is **deterministic lifecycle behaviour**, not spawn-driven population control. |
| Phase 6 is open | **Phase 6** settlements and civilisation remain **deferred**. |

---

## Domain-to-phase mapping table

### Core and cognition

| Domain Plan domain | Roadmap phase or contract | Coverage status | Current bounded scope | Remaining scope | Execution status |
|---|---|---|---|---|---|
| Core Authority | Core kernel + SoT v2; Phases 1–4, 5A | implemented foundation | Time, ordering, validation, mutation, hashing, lineage, storage authority | Scale/tiering, multi-rate scheduling expansions | implemented foundation |
| Scheduler / Commit Pipeline | Spec #27 / `commit_pipeline`; Phase 1+ | implemented foundation | Normalize → order → validate → revalidate → apply | Advanced multi-rate / work-request scheduling | implemented foundation |
| Replay and Determinism | `replay_service` + verification doctrine; 5A1–5A2 | implemented foundation | Event replay + shadow determinism; fork genesis | Live fork success path on replica-set Mongo (5A2 Verification Pending) | implemented foundation / verification pending (infra) |
| Perception | **5A5** (+ earlier vision-radius foundation) | implemented narrow slice | Integer Manhattan vision; detections; material knowledge writes | Hearing, full LOS models, multi-sense, remote sensing | implemented narrow slice |
| Knowledge | **5A5** (`knowledge-v2`) | implemented narrow slice | Observer-owned sparse facts; caps; no full world copy | Confidence models, long-horizon knowledge, global knowledge | implemented narrow slice |
| Planning | **5A5** (+ multi-stage actions Ph2) | implemented narrow slice | Needs-driven goals; knowledge/detection targets; multi-tick actions | Strategic planning, broad motive libraries, hidden planner state | implemented narrow slice |
| Needs | Phase 1–2 utility / 5A5 | implemented narrow slice | Hunger, thirst, energy; critical/seek thresholds | Warmth, safety, social needs, curiosity, comfort as full domains | partially represented |
| General Memory (Memory Domain) | **Unassigned** (see below); **5B4** is not this | unassigned / prohibited from implicit implementation | None as complete Memory Domain | Personal experiences, free-form history, teaching memory, etc. | unassigned |
| Interaction Memory | **5B4** | implemented narrow slice | `interaction-memory-v1`: helped/refused/requested/offered/witnessed_assistance with event provenance | Full Memory Domain, unbounded social history | implemented narrow slice |
| Emotion | **Unassigned** | unassigned / prohibited from implicit implementation | None | Fear, happiness, anger, temporary state; may later bias utility only | unassigned |
| Personality | **Unassigned** | unassigned / prohibited from implicit implementation | None | Long-term traits; may later bias utility only; never force actions | unassigned |
| Habit | **Unassigned** | unassigned / prohibited from implicit implementation | None | Routines after repeated deterministic work patterns exist | unassigned |
| Learning | **Unassigned** | unassigned / prohibited from implicit implementation | None | Skills/experience after bounded activity provenance exists | unassigned |

### Social

| Domain Plan domain | Roadmap phase or contract | Coverage status | Current bounded scope | Remaining scope | Execution status |
|---|---|---|---|---|---|
| Food Transfer | **5B1** | implemented narrow slice | `GIVE_FOOD` / `food-transfer-v1`; one unit; adjacency; conservation | Generic inventory, multi-resource transfer | implemented narrow slice |
| Social Observation | **5B2** | implemented narrow slice | `social-observation-v1` coarse visible facts | Private inventory, telepathy, global social knowledge | implemented narrow slice |
| Social Interaction Protocol | **5B3** | implemented narrow slice | `food-interaction-v1` request/offer lifecycle + 5B1 fulfilment | Dialogue, bargaining, multi-party, generic protocols | implementation complete (focused-verified; 5A2 infra boundary) |
| Relationships | **5F1** (+ Domain Plan Relationship Domain) | planned / partial future | Roadmap: durable pairing foundations | Trust vectors, rivalry, debt, full relationship calculus | planned |
| Reciprocity / Trust | **5B5** | implemented narrow slice | `reciprocity-trust-v1` derived scores; narrow ranking/auto-accept influence | Universal mutable trust, reputation networks | implemented narrow slice |
| Persistent Social Motives | **5B6** | planned | One reserve-maintenance motive | Broad motive libraries, personality-driven motives | planned |
| Family / Kinship | **5F1–5F4** | planned | Pairing, shared-resource bond, parent links, kin facts | Clans, inheritance, multi-household systems | planned |
| Reproduction | **5F3** | planned | One deterministic birth path; fixed costs/cooldowns | Pregnancy sim, genetics tables, animal reproduction | planned |
| Population | Emergent via lifecycle + **5F**; doctrine | partially represented / explicitly deferred as control system | Ageing/death (Phase 4); birth later via 5F | Spawn-rate population control is **prohibited** | doctrine: emergent only |
| Social (conversation/cooperation beyond food protocol) | Beyond 5B3–5B6 | partially represented | Food help protocol + observation | Conversation, teaching, threatening, arguing | unassigned / deferred beyond declared 5B slices |

### Resource and production

| Domain Plan domain | Roadmap phase or contract | Coverage status | Current bounded scope | Remaining scope | Execution status |
|---|---|---|---|---|---|
| Resource Ownership | **5C1** | planned | Versioned owner refs for existing resource entities | Land/property law, taxation | planned |
| Storage | **5C2** | planned | Bounded stockpiles; deposit/withdraw | Warehouses, theft logistics, spoilage systems | planned |
| Logistics | Domain Plan; not a standalone Phase 5 stage | unassigned / partially via 5C | Carrying is person inventory only today | Transport networks, distribution | unassigned |
| Work | **5C3** (cooperative work tasks) | planned | One multi-person productive task | Professions, job markets, arbitrary work graphs | planned |
| Production / Crafting | **5C3** (+ Domain Plan Crafting) | planned / unassigned for full crafting | One bounded cooperative output path | Recipes, tools, equipment trees | partially planned / remaining unassigned |
| Allocation | **5C4** | planned | Planner chooses among owned resources/storage/tasks | Central planning, markets | planned |
| Economy | Domain Plan Economy Domain | explicitly deferred as complete domain | 5B1 transfer + 5C foundations only | Markets, currency, specialisation, macroeconomy | prohibited from treating 5B1/5C as complete |
| Barter / Markets / Currency | **5C5** barter slice; markets/currency deferred | planned (barter only) / deferred | Bilateral barter after 5B3 + 5C1–5C4 | Money, market clearing, credit, wages | planned narrow / deferred remainder |

### Environment

| Domain Plan domain | Roadmap phase or contract | Coverage status | Current bounded scope | Remaining scope | Execution status |
|---|---|---|---|---|---|
| Canonical World State | **5D1** | planned | Singleton `world-000` via genesis events | Broader global mutable domain state | planned (parallel track if social blocked) |
| Terrain | World gen + navigation; Domain Plan Terrain | partially represented | Static terrain grid; passability; day/night | Rivers, mud, snow, flooding, erosion dynamics | partially represented |
| Resources | Trees/water/carcass meat; Domain Plan Resource | partially represented | Finite trees, water tiles, meat harvest | Stone, ore, clay, multi-resource economy | partially represented |
| Ecology | Ecology domain engine; Domain Plan Ecology | partially represented | Tree regrowth, carcass decay | Competition, bushes, full plant ecology | partially represented |
| Animals | Animal domain; hunt chain Phase 4 | partially represented | Wander/graze/flee; hunt→carcass | Migration, packs, territories, reproduction | partially represented |
| Weather | **5D2–5D3** | planned | One global weather transition + staged effects | Regional weather, forecasting | planned |
| Climate | Domain Plan Climate | explicitly deferred | None | Droughts, biome evolution, long-term shifts | explicitly deferred |

### Conflict and civilisation

| Domain Plan domain | Roadmap phase or contract | Coverage status | Current bounded scope | Remaining scope | Execution status |
|---|---|---|---|---|---|
| Social Conflict | **5E** | planned | Taking, detection, conflict motives, combat stages | Factions, warfare, tactics | planned |
| Crime | **5E1–5E2** (unauthorised taking + detection) | planned (narrow) | One taking + observation consequences | Full crime catalogue, justice systems | planned narrow |
| Investigation | Domain Plan Investigation | unassigned | None (history provenance is Core, not investigation domain) | Evidence, deduction, crime solving | unassigned |
| Settlements | **Phase 6** | explicitly deferred | None | Detection, infrastructure, expansion | deferred |
| Government | Domain Plan Government | explicitly deferred | None | Laws, leadership, taxation | deferred |
| Culture | Domain Plan Culture | explicitly deferred | None | Customs, norms, festivals | deferred |
| Religion | Domain Plan Religion | explicitly deferred | None | Beliefs, rituals | deferred |
| Technology | Domain Plan Technology | explicitly deferred | None | Invention, research | deferred |
| Education | Domain Plan Education | explicitly deferred | None | Schools, apprenticeship | deferred |
| Language | Domain Plan Language | explicitly deferred | None | Dialects, vocabulary evolution | deferred |
| Reputation | Domain Plan Reputation | explicitly deferred | None | Fame, community trust | deferred (not 5B5) |
| Civilisation | **Phase 6** / Domain Plan Civilization | explicitly deferred | None | Cities, kingdoms, empires | deferred |

---

## Unassigned cognition domains

The following Domain Plan cognition domains remain **long-range vision only**. They do **not** currently have complete execution phases.

| Domain | Rule |
|---|---|
| **General Memory** (Memory Domain) | Must not be implemented as free-form personal memory inside 5B4–5B6, 5C, or unrelated phases. |
| **Emotion** | Must not be absorbed into social protocol, trust, or utility rewrites without an assigned phase. |
| **Personality** | Must not become hidden mutable authority or direct action rules. |
| **Habit** | Must not begin before repeated deterministic actions or work patterns exist. |
| **Learning** | Must not begin before bounded activity and skill provenance contracts exist. |

### Constraints (no new invention beyond Domain Plan + roadmap doctrine)

- These domains **remain part of the long-range vision** in [Domain Plan](../Domain%20Plan.txt).
- They **must not be implemented implicitly** inside **5B4, 5B5, 5B6, 5C**, or another unrelated phase.
- A **future roadmap revision** must assign each domain a **bounded phase**, **dependencies**, **state model**, **growth cap**, and **acceptance gate** before implementation begins.
- **5B4** may implement **only** the interaction-memory slice already declared in the roadmap (event-backed helped/refused/requested/offered/witnessed facts). That is **not** the Memory Domain.
- **Emotion** and **Personality**, if later assigned, may **bias deterministic utility** but must **never** directly force actions or create hidden mutable authority (Domain Plan + Core doctrine).
- **Habit** should wait until repeated deterministic actions or work patterns exist.
- **Learning** should wait until bounded activity and skill provenance contracts exist.

---

## Conceptual layers vs execution order

The Domain Plan layer diagram (Foundation → Cognition → Social → Environment → Survival & Production → Society → Advanced Civilization) describes **conceptual dependency direction**: higher-level behaviour should rest on lower-level truth contracts.

The [roadmap](ROADMAP.md) describes **practical implementation order**. Environment (5D) may execute in controlled parallel with social work; that is an **execution sequencing** decision, not a reversal of architectural dependency.

See also the roadmap sections:

- Bounded-growth design gate (every new phase)
- Phase 5 resolution-tier policy (deferred tiering)
- Conceptual versus execution ordering
- Controlled parallel work (5D when social is blocked)

---

## Remaining unresolved domain assignments

Vision domains with **no** complete Phase 5/6 execution assignment yet (non-exhaustive; see Domain Plan for full catalogue):

- General Memory, Emotion, Personality, Habit, Learning  
- Logistics (as a full domain), full Crafting/recipes, full Economy  
- Climate, Disease, Language, Education, Religion, Culture, Technology  
- Reputation, Investigation, Myth & Story, Government  
- Full Settlement/Civilization systems (Phase 6 deferred shell only)

These remain **prohibited from implicit implementation** until the roadmap assigns bounded phases.

---

*Document type: alignment only. Last aligned to Phase 5B5 implementation-complete status; next active social phase **5B6**.*

## Capability roadmap alignment

The long-range capability sequence is defined in [`CAPABILITY_ROADMAP.md`](CAPABILITY_ROADMAP.md).

Use the following distinction when updating this mapping:

- **Domain area**: a broad simulation subject defined by `Domain Plan.txt`.
- **Capability stage**: the dependency-ordered milestone that integrates related domain capabilities.
- **Technical phase**: the implementation work that strengthens or delivers parts of those capabilities.
- **Work package**: a bounded internal implementation slice that does not independently complete the capability stage.

Current major mapping:

| Capability stage | Primary domain coverage |
| --- | --- |
| 6 - Living Agents | Needs, wants, perception, knowledge, memory, goals, reasoning, planning, canonical action, physical interaction, basic social interaction, consequence propagation |
| 7 - Households and Groups | Families, households, camps, settlements, shared resources, leadership, collective behaviour |
| 8 - Culture and Knowledge | Norms, beliefs, traditions, identity, teaching, cultural divergence and transmission |
| 9 - Economy | Labour, production, ownership, storage, logistics, trade, value, contracts, wealth and inheritance |
| 10 - Institutions | Governance, law, authority, enforcement, dispute resolution, diplomacy and organised conflict |
| 11 - Ecology and Demography | Lifecycles, reproduction, ageing, disease, death, migration, seasons, ecosystems and world-scale change |
| 12 - Historical Burn-In | Integrated long-run history generated by Stages 6 through 11 |
| 13 - Historical Legibility | Compression, biographies, timelines, significance, causal drill-down and world explanation |
| 14 - Player Embodiment | Player entry as an actor governed by the same world rules |
| 15 - Player Presentation | Controls, dialogue, maps, journals, narrative projection and accessible explanation |

Player implementation must not be scheduled ahead of the social, cultural, economic, institutional, ecological, demographic, and historical foundations it depends on.
