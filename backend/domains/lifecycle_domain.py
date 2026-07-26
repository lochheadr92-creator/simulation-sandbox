"""Lifecycle domain (Phase 4B): ageing, health decline, injury foundation,
and natural death for PEOPLE only - proposal-only, exactly like every other
domain. It never mutates state directly; it only proposes.

Scope (explicitly bounded per Phase 4 doctrine): people-only ageing/health/
injury/death. Animals get a SEPARATE, much smaller extension (health +
injured flag mutated by the People domain's own HUNT action, and their
EXISTING starvation-death path in animal_domain.py is left completely
unmodified) - see people_planning.py's "hunt_strike" action and
ecology_domain.py's carcass-decay addition for that half of the story.

Per-tick flow for each living person:
  1. age_ticks += 1; life_stage re-derived purely from age (child/adult/
     elder - CHILD is never spawned by genesis since there is no birth
     mechanic in this phase; life_stage is informational/observational
     except for the elder age-decline health cost below).
  2. health deteriorates by a fixed amount per active cause this tick
     (dehydration/starvation/exposure/age-decline), or regenerates by a
     fixed amount if NO deterioration cause is active this tick.
  3. injury is a simple threshold-derived foundation state (injured=True
     the tick health first drops below INJURY_HEALTH_THRESHOLD; clears
     once health recovers back above it) - not a separate mechanic, no
     random rolls, fully deterministic from health alone.
  4. if health reaches 0, propose death with a real, inspectable cause
     (whichever deterioration cause was active, in a fixed priority
     order) instead of an opaque number.

Ordering note: this domain runs in the "environment" phase at priority 1
(right after ecology's 0, before ANY agent-phase proposal). This guarantees
a person's death proposal - if any - commits BEFORE that same person's own
PeopleDomain action proposal is evaluated in the SAME tick, so the
person-domain's now-added `alive == True` precondition correctly rejects
the stale action instead of letting a dead person act, with zero Core
changes required (Core's existing sequential commit-time revalidation is
exactly the mechanism that makes this work).

Diagnostics are stored under `f"{entity_id}::lifecycle"` (a distinct key
from the plain entity_id PeopleDomain diagnostics use) so the two domains'
per-tick diagnostics for the same person never overwrite each other in the
generic `diagnostics` dict merge performed by the kernel.
"""
from domains.base import DomainEngine, DomainOutput
from core.constants import (
    STARVATION_HEALTH_DECAY,
    DEHYDRATION_HEALTH_DECAY, EXPOSURE_HEALTH_DECAY, AGE_DECLINE_HEALTH_DECAY,
    HEALTH_REGEN, INJURY_HEALTH_THRESHOLD, MAX_HEALTH, CRITICAL_THRESHOLD,
    life_stage_for_age,
)


def lifecycle_diag_key(entity_id: str) -> str:
    return f"{entity_id}::lifecycle"


class LifecycleDomain(DomainEngine):
    engine_id = "lifecycle"
    engine_version = "1.0.0"
    engine_priority = 1
    phase = "environment"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        return [eid for eid, e in entities.items() if e["type"] == "person" and e.get("alive", True)]

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        night = getattr(frame, "night", False)

        for eid in frame.due_entity_ids:
            e = frame.entities.get(eid)
            if not e or e["type"] != "person" or not e.get("alive", True):
                continue

            age = e.get("age_ticks", 0) + 1
            life_stage = life_stage_for_age(age)

            causes = []
            if e.get("thirst", 0) >= CRITICAL_THRESHOLD:
                causes.append(("dehydration", DEHYDRATION_HEALTH_DECAY))
            if e.get("hunger", 0) >= CRITICAL_THRESHOLD:
                causes.append(("starvation", STARVATION_HEALTH_DECAY))
            if night and not e.get("has_shelter", False):
                causes.append(("exposure", EXPOSURE_HEALTH_DECAY))
            if life_stage == "elder":
                causes.append(("age_decline", AGE_DECLINE_HEALTH_DECAY))

            health = e.get("health", MAX_HEALTH)
            health = max(0, health - sum(d for _, d in causes)) if causes else min(MAX_HEALTH, health + HEALTH_REGEN)

            prior_injury = e.get("injury") or {"injured": False, "severity": 0, "cause": None}
            dominant_cause = causes[0][0] if causes else None
            if health <= 0:
                proposals.append(self._death_proposal(e, eid, frame.simulation_time, dominant_cause or "unknown", age, life_stage))
                diagnostics[lifecycle_diag_key(eid)] = {
                    "age_ticks": age, "life_stage": life_stage, "health": 0,
                    "injury": {"injured": True, "severity": MAX_HEALTH, "cause": dominant_cause},
                    "deterioration_causes": [c for c, _ in causes],
                    "explanation": f"health reached 0 (cause: {dominant_cause or 'unknown'}) -> death",
                }
                continue

            newly_injured = (not prior_injury.get("injured")) and health < INJURY_HEALTH_THRESHOLD
            if newly_injured:
                injury = {"injured": True, "severity": MAX_HEALTH - health, "cause": dominant_cause}
            elif prior_injury.get("injured") and health >= INJURY_HEALTH_THRESHOLD:
                injury = {"injured": False, "severity": 0, "cause": None}
            elif prior_injury.get("injured"):
                injury = {"injured": True, "severity": MAX_HEALTH - health, "cause": prior_injury.get("cause")}
            else:
                injury = {"injured": False, "severity": 0, "cause": None}

            proposal_type = "injury" if newly_injured else "lifecycle_tick"
            explanation = (
                f"newly injured (cause: {dominant_cause}, health={health})" if newly_injured
                else f"age={age} stage={life_stage} health={health}" + (
                    f" deteriorating ({', '.join(c for c, _ in causes)})" if causes else " (regenerating)")
            )

            proposals.append({
                "proposal_family": "lifecycle_process",
                "proposal_type": proposal_type,
                "proposer_engine_id": self.engine_id,
                "proposer_engine_version": self.engine_version,
                "entity_id": eid,
                "causal_parent_event_ids": [e["last_event_id"]] if e.get("last_event_id") else [],
                "is_exogenous": not e.get("last_event_id"),
                "requested_time": frame.simulation_time,
                "phase": self.phase,
                "engine_priority": self.engine_priority,
                "touched_scope": [eid],
                "preconditions": [{"entity_id": eid, "field": "alive", "op": "eq", "value": True}],
                "mutation": {"entity_updates": {eid: {
                    "age_ticks": age, "life_stage": life_stage, "health": health, "injury": injury,
                }}, "new_entities": {}},
                "explanation": explanation,
            })
            diagnostics[lifecycle_diag_key(eid)] = {
                "age_ticks": age, "life_stage": life_stage, "health": health, "injury": injury,
                "deterioration_causes": [c for c, _ in causes], "explanation": explanation,
            }

        return DomainOutput(proposals=proposals, diagnostics=diagnostics)

    def _death_proposal(self, e, eid, tick, cause, age, life_stage):
        return {
            "proposal_family": "lifecycle_process",
            "proposal_type": "death",
            "proposer_engine_id": self.engine_id,
            "proposer_engine_version": self.engine_version,
            "entity_id": eid,
            "causal_parent_event_ids": [e["last_event_id"]] if e.get("last_event_id") else [],
            "is_exogenous": not e.get("last_event_id"),
            "requested_time": tick,
            "phase": self.phase,
            "engine_priority": self.engine_priority,
            "touched_scope": [eid],
            "preconditions": [{"entity_id": eid, "field": "alive", "op": "eq", "value": True}],
            "mutation": {"entity_updates": {eid: {
                "alive": False, "current_goal": "DEAD", "health": 0, "age_ticks": age, "life_stage": life_stage,
                "death_cause": cause, "death_tick": tick,
                "action": {"type": "death", "status": "completed", "target_entity_id": None, "target_pos": None,
                           "ticks_spent": 0, "ticks_required": 0, "interruptible": False, "started_tick": tick},
                "plan": {"goal": None, "steps": [], "step_index": 0, "status": "abandoned"},
                "paused": None,
            }}, "new_entities": {}},
            "explanation": f"critical: health reached 0 (cause: {cause}, age={age}, stage={life_stage}) -> death",
        }
