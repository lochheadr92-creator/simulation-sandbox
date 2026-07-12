from api.living_agent_projection import (
    MAX_BELIEFS,
    MAX_CANDIDATES,
    build_living_agent_projection,
)
from domains.living_agent_contracts import empty_living_agent_state


def _person():
    state = empty_living_agent_state("person-001", 0)
    state["pressures"] = {
        "hunger": {"severity": 800, "predicted_severity": 850, "urgency": 700, "source": "canonical:hunger"},
    }
    state["wants"] = {
        "want-food": {
            "want_id": "want-food", "want_type": "find_food", "desired_outcome": "eat",
            "target_id": None, "status": "active", "strength": 800,
            "source_pressures": ["hunger"], "blocked_reason": None,
        },
    }
    state["current_decision"] = {
        "receipt_id": "decision-1", "tick": 8, "decision_kind": "new_goal",
        "selected_goal": "GATHER_FOOD", "selected_goal_id": "goal-1", "selected_score": 900,
        "selection_reason": "highest deterministic score", "uncertainty": 300,
        "knowledge_used": ["reported-food"], "memory_references": [], "want_references": ["want-food"],
        "relationship_references": [], "assumptions": ["food remains"], "predicted_risks": {},
        "candidate_goals": [
            {"goal_id": f"goal-{index}", "goal": f"GOAL_{index}", "score_total": index}
            for index in range(MAX_CANDIDATES + 5)
        ],
    }
    facts = {
        f"fact-{index}": {
            "fact_id": f"fact-{index}", "subject": "storage-private", "fact_type": "storage",
            "properties": {"access": "public"}, "confidence": 600,
            "provenance_kind": "reported", "status": "unconfirmed",
            "source_entity_id": "person-005", "source_event_id": "evt-rumour",
            "last_confirmed_tick": index, "stale_after_tick": 5, "contradiction_count": 0,
        }
        for index in range(MAX_BELIEFS + 5)
    }
    return {
        "id": "person-001", "type": "person", "stage6_role": "scout",
        "position": {"x": 1, "y": 1}, "living_agent": state,
        "knowledge": {"schema_version": "knowledge-v2", "facts": facts},
        "current_goal": "GATHER_FOOD",
        "plan": {"schema_version": "living-plan-v1", "plan_id": "plan-1", "goal": "GATHER_FOOD",
                 "goal_id": "goal-1", "status": "active", "steps": ["MOVE", "GATHER"], "step_index": 0},
        "action": {"schema_version": "living-action-v1", "action_id": "action-1", "type": "move",
                   "status": "completed", "target_pos": {"x": 2, "y": 1}, "physical_effects": ["position_change"]},
    }


def test_projection_is_bounded_and_keeps_uncertain_beliefs_actor_owned():
    projection = build_living_agent_projection(_person(), 10, diagnostics={"selected_goal": "GATHER_FOOD"})

    assert projection["projection_version"] == "living-agent-projection-v1"
    assert projection["entity_id"] == "person-001"
    assert len(projection["knowledge"]["beliefs"]) == MAX_BELIEFS
    assert projection["knowledge"]["summary"]["truncated"] is True
    assert all(row["may_be_wrong"] and row["stale"] for row in projection["knowledge"]["beliefs"])
    assert len(projection["why"]["candidates"]) == MAX_CANDIDATES
    assert projection["trying"]["plan"]["goal"] == "GATHER_FOOD"
    assert projection["diagnostics"]["selected_goal"] == "GATHER_FOOD"
    assert projection["diagnostics"]["candidates"] == []
    assert "does not compare" in projection["truth_boundary"]


def test_projection_does_not_mutate_canonical_input():
    person = _person()
    before = person["knowledge"]["facts"]["fact-0"]["properties"].copy()

    projection = build_living_agent_projection(person, 10)
    projection["knowledge"]["beliefs"][0]["properties"]["access"] = "changed"

    assert person["knowledge"]["facts"]["fact-0"]["properties"] == before
