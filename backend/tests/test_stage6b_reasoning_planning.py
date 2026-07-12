"""Capability Stage 6B goals, receipts, stable scoring, and planning."""
import copy
import itertools

from core.rng import DeterministicRNG
from domains.living_agent_contracts import LIMITS, empty_living_agent_state
from domains.living_agent_reasoning import (
    build_decision_receipt,
    form_structured_plan,
    record_decision,
    score_goal_candidates,
    select_goal,
    update_plan_progress,
)
from domains.people_planning import form_plan
from domains.perception import empty_knowledge


def _base_candidates():
    return [
        {"goal": "EXPLORE", "score": 100, "availability": 1, "risk": 5, "travel_cost": 1, "target_pos": {"x": 2, "y": 1}},
        {"goal": "SEEK_WATER", "score": 100, "availability": 1, "risk": 0, "travel_cost": 1, "target_pos": {"x": 1, "y": 2}},
        {"goal": "GIVE_FOOD", "score": 40, "availability": 1, "risk": 0, "travel_cost": 0, "recipient_id": "person-b"},
    ]


def _state():
    state = empty_living_agent_state("person-a", 0, DeterministicRNG("reasoning"))
    state["pressures"]["thirst"].update({"urgency": 800, "predicted_severity": 950})
    state["pressures"]["curiosity"].update({"urgency": 300, "predicted_severity": 500})
    state["wants"] = {
        "want-explore": {
            "want_id": "want-explore", "want_type": "explore_unknown_area",
            "status": "active", "strength": 500,
        }
    }
    state["memories"] = {
        "memory-water": {
            "memory_id": "memory-water", "memory_kind": "resource_discovered",
            "significance": 700, "confidence": 900, "last_recalled_tick": 4,
        }
    }
    return state


def test_candidate_input_order_never_changes_scores_or_winner():
    state = _state()
    knowledge = empty_knowledge()
    expected = None
    for ordering in itertools.permutations(_base_candidates()):
        scored = score_goal_candidates(
            list(ordering), actor_id="person-a", state=state, knowledge=knowledge, tick=5,
        )
        snapshot = (scored, select_goal(scored))
        if expected is None:
            expected = snapshot
        assert snapshot == expected
    assert expected[1]["goal"] == "SEEK_WATER"


def test_memory_wants_pressures_and_uncertainty_all_contribute_explicit_components():
    scored = score_goal_candidates(
        _base_candidates(), actor_id="person-a", state=_state(),
        knowledge=empty_knowledge(), tick=5,
    )
    by_goal = {row["goal"]: row for row in scored}

    assert by_goal["SEEK_WATER"]["score_components"]["pressure"] > 0
    assert by_goal["SEEK_WATER"]["score_components"]["memory"] > 0
    assert by_goal["EXPLORE"]["score_components"]["want"] > 0
    assert by_goal["SEEK_WATER"]["score_components"]["uncertainty"] < 0
    assert len(scored) <= LIMITS.candidate_goals_per_decision


def test_stable_tie_break_uses_confidence_then_goal_id():
    candidates = [
        {"goal": "B", "goal_id": "goal-b", "score_total": 100, "knowledge_confidence": 400},
        {"goal": "A", "goal_id": "goal-a", "score_total": 100, "knowledge_confidence": 600},
    ]
    assert select_goal(candidates)["goal"] == "A"
    tied = [{**row, "knowledge_confidence": 600} for row in candidates]
    assert select_goal(list(reversed(tied)))["goal"] == "A"


def test_decision_receipt_is_structured_bounded_and_canonical():
    state = _state()
    knowledge = empty_knowledge()
    candidates = score_goal_candidates(
        _base_candidates(), actor_id="person-a", state=state, knowledge=knowledge, tick=5,
    )
    selected = select_goal(candidates)
    legacy = form_plan(selected["goal"], {"id": "person-a", "inventory": 0, "food_inventory": 0}, {"water_target": {"x": 1, "y": 2}}, 5)
    plan = form_structured_plan(
        legacy, actor_id="person-a", tick=5, selected=selected,
        context={"water_target": {"x": 1, "y": 2}},
    )
    receipt = build_decision_receipt(
        actor_id="person-a", tick=5, state=state, knowledge=knowledge,
        candidates=candidates, selected=selected, plan=plan, decision_kind="new_goal",
    )

    assert receipt["schema_version"] == "decision-receipt-v1"
    assert receipt["selected_goal"] == "SEEK_WATER"
    assert receipt["plan_id"] == plan["plan_id"]
    assert receipt["tie_break"]["rule"].startswith("score_desc")
    assert isinstance(receipt["current_pressures"], list)
    assert isinstance(receipt["candidate_goals"][0]["score_components"], dict)
    assert "free_form_reasoning" not in receipt


def test_recorded_decision_and_causal_links_remain_bounded():
    state = _state()
    for tick in range(LIMITS.decision_receipts_retained + 6):
        receipt = {
            "receipt_id": f"receipt-{tick}", "tick": tick,
            "selected_goal_id": f"goal-{tick}", "want_references": [],
            "memory_references": [], "candidate_goals": [{"pressure_kinds": ["hunger"]}],
        }
        state = record_decision(state, receipt, {"plan_id": f"plan-{tick}"})
    assert len(state["decision_history"]) == LIMITS.decision_receipts_retained
    assert len(state["causal_links"]) <= LIMITS.causal_links_retained
    assert state["current_decision"]["receipt_id"] == f"receipt-{LIMITS.decision_receipts_retained + 5}"


def test_structured_plan_has_requirements_failure_and_fallback_contracts():
    selected = {
        "goal": "BUILD_SHELTER", "goal_id": "goal-build", "target_pos": {"x": 3, "y": 3},
        "action_time": 3,
    }
    legacy = form_plan(
        "BUILD_SHELTER", {"id": "person-a", "inventory": 10, "food_inventory": 0},
        {"tree_target_id": "tree-a", "tree_target_pos": {"x": 2, "y": 2}, "shelter_site": {"x": 3, "y": 3}},
        7,
    )
    plan = form_structured_plan(
        legacy, actor_id="person-a", tick=7, selected=selected,
        context={"required_tools": ["tool-axe"]},
    )

    assert plan["schema_version"] == "living-plan-v1"
    assert plan["goal_id"] == "goal-build"
    assert len(plan["steps"]) <= LIMITS.planning_depth
    assert all("failure_conditions" in row for row in plan["step_records"])
    assert any(row["required_resources"] == {"wood": 10} for row in plan["step_records"])
    assert any(row["required_tools"] == ["tool-axe"] for row in plan["step_records"])


def test_plan_progress_records_failure_without_hidden_state():
    plan = {
        "steps": ["TRAVEL_WATER"], "step_records": [{"step_type": "TRAVEL_WATER", "status": "pending"}],
        "step_index": 0, "status": "active",
    }
    failed = update_plan_progress(
        plan, {"status": "failed", "invalidation_reason": "target_disappeared"}, tick=8,
    )
    assert failed["step_records"][0]["status"] == "failed"
    assert failed["failure_reason"] == "target_disappeared"
    assert plan["step_records"][0]["status"] == "pending"
