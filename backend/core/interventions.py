"""External interventions: the sandbox user is 'just another participant'.

Every intervention is normalized into an ExternalInfluenceRecord (stored)
and then submitted as a proposal through the SAME commit pipeline used by
domain engines - it can be validated, rejected, or accepted exactly like
any other proposal. This is the doctrine's 'paired model' for external
influence (Source of Truth v2, Section 8).
"""


def build_intervention_proposal(itype: str, payload: dict, entities: dict, tick: int, influence_id: str):
    if itype == "boost_need":
        eid = payload.get("entity_id")
        field = payload.get("field")
        delta = payload.get("delta", 0)
        if eid not in entities or field not in ("hunger", "thirst", "energy"):
            return None
        new_value = max(0, min(1000, entities[eid][field] + delta))
        return {
            "proposal_family": "external_influence", "proposal_type": "boost_need",
            "proposer_engine_id": "sandbox_external", "proposer_engine_version": "1.0.0",
            "entity_id": eid, "causal_parent_event_ids": [], "is_exogenous": True,
            "requested_time": tick, "phase": "agent", "engine_priority": 999,
            "touched_scope": [eid], "preconditions": [],
            "mutation": {"entity_updates": {eid: {field: new_value}}, "new_entities": {}},
            "explanation": f"external intervention: {field} {'+' if delta >= 0 else ''}{delta} (influence={influence_id})",
        }

    if itype == "spawn_tree":
        x, y = payload.get("x", 0), payload.get("y", 0)
        amount = payload.get("resource", 60)
        new_id = f"tree-ext-{influence_id[-6:]}"
        return {
            "proposal_family": "external_influence", "proposal_type": "spawn_tree",
            "proposer_engine_id": "sandbox_external", "proposer_engine_version": "1.0.0",
            "entity_id": new_id, "causal_parent_event_ids": [], "is_exogenous": True,
            "requested_time": tick, "phase": "environment", "engine_priority": -1,
            "touched_scope": [new_id], "preconditions": [],
            "mutation": {"entity_updates": {}, "new_entities": {new_id: {
                "type": "tree", "position": {"x": x, "y": y}, "resource": amount,
                "max_resource": amount, "alive": True,
            }}},
            "explanation": f"external intervention: spawn tree at ({x},{y}) (influence={influence_id})",
        }

    if itype == "kill_entity":
        eid = payload.get("entity_id")
        if eid not in entities:
            return None
        return {
            "proposal_family": "external_influence", "proposal_type": "kill_entity",
            "proposer_engine_id": "sandbox_external", "proposer_engine_version": "1.0.0",
            "entity_id": eid, "causal_parent_event_ids": [], "is_exogenous": True,
            "requested_time": tick, "phase": "agent", "engine_priority": 999,
            "touched_scope": [eid],
            "preconditions": [{"entity_id": eid, "field": "alive", "op": "eq", "value": True}],
            "mutation": {"entity_updates": {eid: {"alive": False, "current_goal": "DEAD", "current_action": "external_kill"}},
                         "new_entities": {}},
            "explanation": f"external intervention: kill entity (influence={influence_id})",
        }

    return None
