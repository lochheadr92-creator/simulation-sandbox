"""EcologyDomain: narrow, mostly-dormant, source-driven process engine.

Two passive, source-driven natural processes, both scheduled-cadence and
exogenous (no causal parent event required, per doctrine's "non-exogenous
durable consequence needs causal parents" rule):

1. Tree regrowth - only for trees due for the REGROWTH_INTERVAL cadence
   and not already at max resource (unchanged since Phase 1/2).
2. Carcass decay (Phase 4B) - the mirror-image process: a carcass (created
   by the People domain's hunting action - see people_planning.py) loses
   meat every CARCASS_DECAY_INTERVAL ticks until it is fully consumed by
   decay, at which point it is removed from the world entirely. This is
   what makes hunting create real time pressure ("carry food, eat, don't
   let the meat rot") rather than a permanent free resource.
"""
from domains.base import DomainEngine, DomainOutput
from core.constants import (
    REGROWTH_AMOUNT, REGROWTH_INTERVAL, CARCASS_DECAY_INTERVAL, CARCASS_DECAY_AMOUNT,
)


class EcologyDomain(DomainEngine):
    engine_id = "ecology"
    engine_version = "1.1.0"
    engine_priority = 0
    phase = "environment"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        due = []
        for eid, e in entities.items():
            if e["type"] == "tree" and tick % REGROWTH_INTERVAL == 0:
                due.append(eid)
            elif e["type"] == "carcass" and tick % CARCASS_DECAY_INTERVAL == 0 and e.get("resource", 0) > 0:
                due.append(eid)
        return due

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        for eid in frame.due_entity_ids:
            e = frame.entities.get(eid)
            if not e:
                continue
            if e["type"] == "tree":
                self._regrow(e, eid, frame, proposals, diagnostics)
            elif e["type"] == "carcass":
                self._decay(e, eid, frame, proposals, diagnostics)
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)

    def _regrow(self, e, eid, frame, proposals, diagnostics):
        if e["resource"] >= e["max_resource"]:
            return
        new_amount = min(e["max_resource"], e["resource"] + REGROWTH_AMOUNT)
        explanation = f"natural regrowth: resource {e['resource']} -> {new_amount}"
        proposals.append({
            "proposal_family": "ecology_process",
            "proposal_type": "regrow",
            "proposer_engine_id": self.engine_id,
            "proposer_engine_version": self.engine_version,
            "entity_id": eid,
            "causal_parent_event_ids": [],
            "is_exogenous": True,
            "requested_time": frame.simulation_time,
            "phase": "environment",
            "engine_priority": self.engine_priority,
            "touched_scope": [eid],
            "preconditions": [{"entity_id": eid, "field": "resource", "op": "lt", "value": e["max_resource"]}],
            "mutation": {"entity_updates": {eid: {"resource": new_amount}}, "new_entities": {}},
            "explanation": explanation,
        })
        diagnostics[eid] = {"candidates": [], "selected_goal": "REGROW", "explanation": explanation}

    def _decay(self, e, eid, frame, proposals, diagnostics):
        new_amount = max(0, e["resource"] - CARCASS_DECAY_AMOUNT)
        mutation = {"entity_updates": {}, "new_entities": {}}
        if new_amount <= 0:
            mutation["removed_entities"] = [eid]
            explanation = f"carcass fully decayed and removed (was {e['resource']})"
        else:
            mutation["entity_updates"][eid] = {"resource": new_amount}
            explanation = f"carcass decaying: meat {e['resource']} -> {new_amount}"
        proposals.append({
            "proposal_family": "ecology_process",
            "proposal_type": "decay",
            "proposer_engine_id": self.engine_id,
            "proposer_engine_version": self.engine_version,
            "entity_id": eid,
            "causal_parent_event_ids": [],
            "is_exogenous": True,
            "requested_time": frame.simulation_time,
            "phase": "environment",
            "engine_priority": self.engine_priority,
            "touched_scope": [eid],
            "preconditions": [{"entity_id": eid, "field": "resource", "op": "gt", "value": 0}],
            "mutation": mutation,
            "explanation": explanation,
        })
        diagnostics[eid] = {"candidates": [], "selected_goal": "DECAY", "explanation": explanation}
