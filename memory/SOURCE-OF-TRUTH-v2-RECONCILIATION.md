# Source of Truth v2 Reconciliation Record

This document records how Source of Truth v1.2 was reconciled into Source of Truth v2. It is historical documentation only. It does not override the Constitution, Source of Truth v2, accepted architecture decisions, or current project contracts.

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
| Utility AI | Removed. Not a Simulation Sandbox concept. |
| NPC Decision Engine | Removed. Not a Simulation Sandbox concept. |
| Relationship Calculus | Removed. Not a Simulation Sandbox concept. |
| Memory Retrieval System | Removed. Not a Simulation Sandbox concept. |
| Scar Theory | Reduced to "causal anchors" and "lineage boundaries" in the compression and administrative records sections. |
| Living World Doctrine | General principles (causality, persistence, independent motion, event sourcing) retained; narrative-game framing removed. |
| Settlement Organism Theory | General entity principles (lifecycle, identity, state) retained; settlement-specific simulation removed. |
| Resource Flow Theory | General entity principles (ownership, persistence, causal anchors) retained; economic simulation removed. |
| Information Theory | Removed. Not a Simulation Sandbox concept. |

## Removed from v1.2

The following were completely removed as they are unrelated to Simulation Sandbox:

- All pressure ecology systems
- All context gravity mechanics
- All utility AI and NPC decision engines
- All relationship calculus and memory retrieval
- All settlement organism theory specifics
- All resource flow theory specifics
- All information theory
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
| v1.2 assumed NPC storytelling systems; v2 has no such assumption | v2 doctrine prevails |
| v1.2 had unclear administrative record boundaries; v2 requires deterministic effective boundaries | v2 doctrine prevails |

## Unresolved Ambiguities

The following remain open for policy decisions:

1. **Minimum recent replay horizon** – The exact duration of byte-exact replay guarantee needs policy setting.
2. **Minimum deep reconstruction horizon** – The exact duration of deep causal reconstruction needs policy setting.
3. **Receipt requirement scope** – Which event families require receipts needs policy setting.
4. **Migration lineage rules** – When an import creates a new lineage versus a compatibility representation needs policy setting.

These are explicitly noted as open decisions in Section 20.1 of Source of Truth v2 and do not block architectural review.