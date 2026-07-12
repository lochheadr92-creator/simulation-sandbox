# Capability Stage 6 — Living Agents contract

## Status

Approved integrated capability stage. This document defines the executable
Stage 6 schema, authority, compatibility, and bounded-growth contract. It does
not mark Stage 6 complete; completion requires the 6A–6E closed-loop gates.

## Authority and data flow

Stage 6 preserves the existing authority spine:

1. Core pins a read-only activation frame and issues named deterministic RNG.
2. Living-agent code derives perceptions, pressure updates, candidates, plans,
   actions, and consequences from that frame and existing canonical state.
3. The domain submits proposals only.
4. Core orders, validates, revalidates, accepts or rejects, and applies the
   generic mutation envelope.
5. Accepted events remain the durable truth and replay source.
6. Entity records are replaceable projections of accepted mutations.
7. UI and narrative are read-only projections and never feed decisions.

No LLM, wall clock, UUID, database insertion order, frontend state, diagnostic
record, or process-local cache may determine a living-agent decision.

## Versioned canonical schemas

| Record | Version | Compatibility rule |
|---|---|---|
| Living-agent state | `living-agent-v1` | Missing state gets deterministic defaults; unknown versions fail closed. |
| Internal pressure | `internal-pressure-v1` | All 14 pressure kinds are present with integer bounded fields. |
| Want | `want-v1` | Content-derived identity; bounded status lifecycle. |
| Memory | `agent-memory-v1` | Event/observation provenance required; deterministic eviction. |
| Relationship | `relationship-v1` | Observer-owned multidimensional state; event-backed changes only. |
| Commitment | `commitment-v1` | Explicit creator, beneficiary, obligation, cause, due/status fields. |
| Decision receipt | `decision-receipt-v1` | Structured inputs/components/tie-break; no free-form hidden reasoning. |
| Plan | `living-plan-v1` | Legacy string steps retained alongside bounded structured step records. |
| Action | `living-action-v1` | Legacy fields retained; canonical provenance and progress fields added. |
| Affordance | `affordance-v1` | Explicit capability/access flags with deterministic defaults. |

The executable manifest is `domains.living_agent_contracts.stage6_schema_manifest`.
Schema changes must update that manifest and focused compatibility tests.

## Deterministic limits

| Surface | Limit | Trade-off |
|---|---:|---|
| Memories per entity | 32 | Preserves significant recent/repeated records, not a raw diary. |
| Memories per subject | 8 | Prevents one subject crowding out all other experience. |
| Perceived entities per observation | 24 | Keeps dense scenes bounded. |
| Perceived objects per observation | 24 | Keeps resource/object scanning bounded. |
| Goal candidates per decision | 16 | Bounded heuristic choice, not combinatorial search. |
| Plan depth | 8 | Short actionable plans; long work requires replanning. |
| Plan branches | 2 | One primary route plus a bounded alternative. |
| Fallback depth | 2 | Prevents recursive fallback trees. |
| Active plans/actions per entity | 1 / 1 | Paused work is canonical history, not parallel hidden execution. |
| Relationship records | 16 | Active-world social horizon only. |
| Commitments per entity | 12 | Important promises/debts only. |
| Social recipients per transmission | 4 | No global broadcast. |
| Information propagation depth | 2 | Rumours remain local and causally traceable. |
| Witnesses processed per event | 8 | Dense crowds are deterministically truncated. |
| Causal links retained per entity | 32 | Accepted events remain the unbounded durable source. |
| Decision receipts retained | 12 | Current/recent explanations, not unlimited diagnostics. |
| Diagnostic records retained | 16 | Operational visibility without canonical growth. |
| Signal entities created per tick | 16 | Bounds noise, tracks, smoke, and social signals. |
| Signal lifetime | 4 ticks | Signals are ephemeral canonical causes, not permanent objects. |
| Long-run acceptance test | 320 ticks | Hundreds-tick proof with bounded CI runtime. |

Resolution tiers beyond active-world detail remain deferred. There are no
spawn-rate, target-population, or population-balancing mechanics in Stage 6.

## Compatibility and migration

- Existing entities without Stage 6 state are upgraded in proposal calculation
  using deterministic compatibility defaults. The upgrade becomes canonical
  only if Core accepts the containing proposal.
- Existing `plan` and `action` shapes retain all prior fields and gain versioned
  fields through compatibility helpers.
- Missing fields never invent observations, relationships, commitments, or
  world knowledge.
- Unknown Stage 6 record versions fail clearly; they are not reinterpreted.
- Engine/schema version changes require explicit run compatibility checks.
- Recorded-event replay continues to apply stored mutations without consulting
  projections or current UI code.

## Package gates

1. Contracts and schemas: manifest, limits, copy-only compatibility, fail-closed tests.
2. 6A: internal state, bounded perception/knowledge, wants, and memories are canonical.
3. 6B: multiple stable candidates produce a structured receipt and canonical plan.
4. 6C: plans produce Core-validated canonical actions and physical consequences.
5. 6D: causally available social information changes relationships/commitments.
6. 6E: a 320-tick integrated scenario closes the loop and replays identically.

Stage 6 is not complete until every gate passes together.
