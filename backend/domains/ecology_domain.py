"""EcologyDomain: narrow, mostly-dormant, source-driven process engine.

Only proposes tree regrowth, and only for trees that are due (scheduled
cadence, see REGROWTH_INTERVAL) and not already at max resource. Regrowth
is an exogenous natural process (no causal parent event required) -
consistent with the doctrine's "non-exogenous durable consequence needs
causal parents" rule.
"""
from domains.base import DomainEngine, DomainOutput
from core.constants import REGROWTH_AMOUNT, REGROWTH_INTERVAL


class EcologyDomain(DomainEngine):
    engine_id = "ecology"
    engine_version = "1.0.0"
    engine_priority = 0
    phase = "environment"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        return [eid for eid, e in entities.items() if e["type"] == "tree" and tick % REGROWTH_INTERVAL == 0]

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        for eid in frame.due_entity_ids:
            e = frame.entities.get(eid)
            if not e or e["type"] != "tree":
                continue
            if e["resource"] >= e["max_resource"]:
                continue
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
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)
