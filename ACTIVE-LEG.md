# Active Domain Leg 1 — Information Sharing (vertical slice)

Declared 2026-07-28. One leg at a time. When this closes it moves to
`memory/archive/legs/` and the next Tier 1 domain takes its place.

## Domain objective

People who possess useful information can share it with nearby trusted people,
and the receiver makes a better later decision because of it.

## Trigger

- Agent A holds a knowledge fact about a resource location.
- Agent B does not hold that fact.
- A and B are within social range.
- B has food or water pressure, or an intent the fact bears on.

## Decision

Existing factors only — need, relationship, distance, cost, urgency, recent
history. No new scoring model in version one. Sharing competes against the
agent's other candidates on the existing scale; if it never wins, that is a
finding for Session A, not a licence to invent a modifier.

## Action

`share_information` event carrying sender, receiver, fact id, tick, provenance.
The candidate site already exists in
`backend/domains/living_settlement_domain.py` and fires exactly once per
320-tick run.

## State consequence

Receiver gains the fact as a **reported** (non-direct) knowledge claim.
`merge_knowledge_claim(knowledge, observer_id, subject_id, fact_type,
properties, tick, provenance_kind, confidence, source_entity_id,
source_event_id, deceptive)` in `living_agent_cognition.py:331` already does
exactly this and already rejects `provenance_kind="direct"` for claims — the
receive path is built, it is simply not being fed. Interaction memory records
the exchange; relationship may shift slightly; the receiver's later navigation
or resource choice may differ.

Facts are bounded at 120 per agent (`living_agent_cognition.py:319`).

## Visual consequence

- The two agents face each other and pause.
- A brief information indicator on the exchange.
- The receiver's knowledge panel in the Inspector gains the fact, marked
  *reported*, with the sender named.
- Timeline reads in plain language: *"Mara told Eli about food at (12, 7)."*
- When the receiver later acts on it, the explanation names the source.

## Success test

One observable causal chain, in a controlled scenario:

> Eli does not know about the food source → Mara shares its location → Eli
> travels there → Eli reaches food he would not otherwise have reached.

Control branch: same seed, sharing suppressed. Eli does not reach it.

## Failure conditions (the ones worth naming)

- The opportunity never occurs.
- The action loses every priority contest.
- The receiver cannot store the fact.
- The knowledge never affects a later decision.
- The behaviour occurs but is invisible.

---

## Session plan

### Session A — definition and activation ← WE ARE HERE

1. Build the smallest deterministic scenario that naturally needs this: ~4
   agents, one holding a resource-location fact, one hungry and uninformed,
   starting within social range, long enough for the knowledge to change an
   action, nothing unrelated dominating the run. Existing scenarios are too
   busy — `living_settlement` is 8 people and 5 trees, `wilderness_survival` is
   6 people and 6 animals.
2. Small opportunity probe. Log only: eligible sender, eligible receiver, the
   relevant fact, prerequisite results, and why each opportunity was accepted
   or rejected. **Not** a multi-stage tracer.
3. If no opportunities appear, fix the scenario or the prerequisite logic
   before implementing anything.
4. Identify blockers only — do not fix them yet unless they stop activation.

**Known blocker candidate.** Sharing requires A to reach B and then act — a
multi-step plan. Measured 2026-07-28: a multi-step plan whose participant moves
emits no proposal at all for two ticks and is replanned away. If the probe
shows opportunities occurring but never completing, that defect is the cause,
and fixing it is permitted under maintenance-freeze rule 1 (*the current domain
cannot activate*) — inside this leg, not as its own project.

### Session B — thin implementation

Opportunity, decision, event, authoritative consequence. No personality, no
dialogue, no trust matrices, no cultural modifiers, no deception, no rumours,
no LLM. Deterministic and correct first.

### Session C — integration

The receiver must **use** the fact. A domain does not count because an event
fired. Determinism and fork tests.

### Session D — presentation

Indicator, plain-language event line, selected-agent explanation, causal link
from the share to the later action. Tested in the normal UI, not a debug view.

### Session E — hardening and freeze

Boundedness, regression tests, known limitations, commit, move on. Do not keep
polishing.

## Out of scope for this leg

Rumours, deception, language, multi-hop propagation, fact decay, trust-weighted
credibility. `merge_knowledge_claim` already carries a `deceptive` flag — leave
it alone. Version one shares true resource locations between agents who are
already near each other.
