# Source of Truth v2 Reconciliation Record

This document records how Source of Truth v1.2 was reconciled into Source of Truth v2. It is historical documentation only. It does not override the Constitution, Source of Truth v2, accepted architecture decisions, or current project contracts.

**Clarification:** Dice Reactions-specific implementations and inherited specifications for utility, NPC decisions, relationships, information flow, and economics were removed from Simulation Sandbox. This does not prohibit independently designed deterministic decision, social, or resource-allocation systems. Such systems must operate from version-pinned observation frames, submit proposals only, preserve deterministic replay, and leave canonical mutation authority with Core.

## Retained from v1.2

The following general principles from v1.2 were retained because they independently fit Simulation Sandbox:

1. **State Is Truth** – The principle that reality exists within state, not within narrative or generated output. This is foundational to the canonical truth model.

2. **Causality as prime law** – Everything important must have a cause. Every meaningful event should be traceable.

3. **Event sourcing** – The principle that state is derived from events, events are immutable, and history is the ultimate source of truth.

4. **The persistence mandate** – Nothing important should vanish without reason. Important actions, events, and consequences persist.

5. **Compression and horizon** – The distinction between byte-exact replay, deep reconstruction, and archival retention.

6. **Scar principle** – Significant events leave traces. This maps to the required causal anchors and lineage boundaries.

7. **Independent motion** – The world continues changing without player involvement. This is implicit in the Core owning simulation time and event ordering.

8. **Administrative records have effective boundaries** – Schema migrations, version changes, and policy changes require explicit effective boundaries.

9. **Memory and identity persistence** – Entities maintain continuity across time through canonical records and event history.

## Revised from v1.2

The following concepts from v1.2 were substantially revised:

| v1.2 Concept | Revision |
|--------------|----------|
| Pressure | Removed entirely. Not a Simulation Sandbox concept. |
| Context Gravity | Removed. Not a Simulation Sandbox concept. |
| Utility AI | Dice Reactions-specific implementations and inherited specifications were removed. Independently designed deterministic decision systems remain permitted when they use version-pinned observation frames, submit proposals only, preserve replay, and leave mutation authority with Core. |
| NPC Decision Engine | Dice Reactions-specific implementations and inherited specifications were removed. Independently designed deterministic actor decisions remain permitted under the Core/domain authority boundary. |
| Relationship Calculus | Dice Reactions-specific implementations were removed. Bounded event-backed social facts and derived social signals may be designed independently under deterministic replay and Core authority. |
| Memory Retrieval System | Dice Reactions-specific implementations were removed. Bounded observer-owned facts may be retained when versioned, replayable, and unable to replace accepted-event truth. |
| Scar Theory | Reduced to "causal anchors" and "lineage boundaries" in the compression and administrative records sections. |
| Living World Doctrine | General principles (causality, persistence, independent motion, event sourcing) retained; narrative-game framing removed. |
| Settlement Organism Theory | General entity principles (lifecycle, identity, state) retained; Dice Reactions-specific settlement architecture removed. Future settlement systems require their own deterministic Core-authority contract. |
| Resource Flow Theory | Dice Reactions-specific resource-flow theory was removed. Independently designed deterministic ownership and resource-allocation systems remain permitted under Core authority. |
| Information Theory | Dice Reactions-specific information theory was removed. Bounded versioned observation and knowledge systems remain permitted when they do not create canonical truth. |

## Removed from v1.2

The following were completely removed as they are unrelated to Simulation Sandbox:

- All Dice Reactions-specific pressure ecology systems
- All Dice Reactions-specific context gravity mechanics
- All Dice Reactions-specific utility, NPC decision, relationship, and memory-retrieval implementations
- All Dice Reactions-specific settlement organism theory specifics
- All Dice Reactions-specific resource-flow theory specifics
- All Dice Reactions-specific information-theory implementations
- All scar theory as a standalone system
- All LLM decision-making (LLMs may assist with presentation but cannot create truth)
- All story-engine terminology (narrative, storytelling, story generation)
- All Dice Reactions-specific language
- All rolling state, hidden D20, resolution bands
- All "Dead World Test" and "Living World Test" framing

## Major Conflicts Resolved

| Conflict | Resolution |
|----------|------------|
| v1.2 treated receipts, checkpoints, and projections as event families; v2 treats them as Core administrative records | v2 doctrine prevails |
| v1.2 allowed external influence to be treated as a simulation event; v2 uses paired model | v2 doctrine prevails |
| v1.2 had broad "canonical causal records" without clear boundaries; v2 narrows to replay/reconstruction/explanation only | v2 doctrine prevails |
| v1.2 assumed Dice Reactions NPC storytelling systems | v2 rejects that inherited architecture while permitting independently designed deterministic decision and social systems under version-pinned observation and Core mutation authority |
| v1.2 had unclear administrative record boundaries; v2 requires deterministic effective boundaries | v2 doctrine prevails |

## Unresolved Ambiguities

The following remain open for policy decisions:

1. **Minimum recent replay horizon** – The exact duration of byte-exact replay guarantee needs policy setting.
2. **Minimum deep reconstruction horizon** – The exact duration of deep causal reconstruction needs policy setting.
3. **Receipt requirement scope** – Which event families require receipts needs policy setting.
4. **Migration lineage rules** – When an import creates a new lineage versus a compatibility representation needs policy setting.

These are explicitly noted as open decisions in Section 20.1 of Source of Truth v2 and do not block architectural review.
