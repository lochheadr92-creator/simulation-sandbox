from tools._probe_layer_c_social_density import (
    STORE_GOAL,
    SocialDensityCensus,
)


def _storage_delta(*, visible: bool) -> dict:
    if not visible:
        return {"observations": []}
    return {
        "observations": [{
            "observation_type": "storage",
            "observed_subject_id": "storage-camp",
            "properties": {"access": "shared", "position": {"x": 5, "y": 5}},
        }]
    }


def _person(food: int, action_type: str = "rest") -> dict:
    return {
        "type": "person",
        "alive": True,
        "carried_resources": {"food": food},
        "action": {"type": action_type},
    }


def _store_candidate(goal_id: str = "goal-store", score: int = 1_350) -> dict:
    return {
        "goal": STORE_GOAL,
        "goal_id": goal_id,
        "score": 1_350,
        "score_total": score,
    }


def _store_diagnostics(*, selected_goal: str, selected_goal_id: str,
                       selected_score: int, candidates: list[dict],
                       lost_by: int | None = None) -> dict:
    alternatives = []
    if lost_by is not None:
        alternatives.append({
            "goal": STORE_GOAL,
            "goal_id": "goal-store",
            "score_total": 1_350,
            "lost_by": lost_by,
        })
    return {
        "selected_goal": selected_goal,
        "goal_id": selected_goal_id,
        "candidates": candidates,
        "decision_receipt": {
            "selected_goal_id": selected_goal_id,
            "selected_score": selected_score,
            "rejected_alternatives": alternatives,
        },
    }


def _accepted_storage_path(*, tick: int, action_type: str) -> dict:
    return {
        "id": f"evt-{tick}",
        "event_type": "living_agent_physical_action",
        "entity_id": "person-001",
        "living_action": {
            "action_type": action_type,
            "causal_goal_id": "goal-store",
            "resource_transfer": {"resource_kind": "food", "quantity": 1},
        },
        "mutation": {
            "entity_updates": {
                "person-001": {
                    "action": {
                        "type": action_type,
                        "target_entity_ids": ["storage-camp"] if action_type == "store" else [],
                    },
                    "plan": {"status": "active" if action_type == "move" else "completed"},
                }
            }
        },
    }


def test_gate_census_distinguishes_non_coincident_prerequisites():
    census = SocialDensityCensus()
    census.observe_candidate_build(
        actor_id="person-001", entity=_person(2), delta=_storage_delta(visible=True),
        tick=1, candidates=[],
    )
    census.observe_candidate_build(
        actor_id="person-002", entity=_person(3), delta=_storage_delta(visible=False),
        tick=1, candidates=[],
    )

    metrics = census.metrics()
    assert metrics["causal_classification"] == (
        "A_STORAGE_VISIBILITY_AND_FOOD_NEVER_COINCIDE"
    )
    assert metrics["candidate_gate_counts"] == {
        "decision_opportunities": 2,
        "food_ge_3": 1,
        "shared_storage_visible": 1,
    }
    assert metrics["carried_food_histogram_at_decision"] == {"2": 1, "3": 1}


def test_joint_eligibility_without_candidate_is_reported_before_scoring():
    census = SocialDensityCensus()
    census.observe_candidate_build(
        actor_id="person-001", entity=_person(3), delta=_storage_delta(visible=True),
        tick=4, candidates=[],
    )

    assert census.classify() == "A_ELIGIBLE_BUT_BASE_CANDIDATE_MISSING"
    assert census.metrics()["candidate_gate_counts"][
        "eligible_but_base_candidate_missing"
    ] == 1


def test_candidate_loss_records_winner_and_exact_lost_by():
    census = SocialDensityCensus()
    store = _store_candidate()
    winner = {"goal": "REPAY_DEBT", "goal_id": "goal-debt", "score_total": 2_000}
    census.observe_candidate_build(
        actor_id="person-001", entity=_person(3), delta=_storage_delta(visible=True),
        tick=5, candidates=[store],
    )
    census.observe_tick(
        tick=5,
        entities={"person-001": _person(3)},
        accepted=[],
        rejected=[],
        diagnostics={
            "person-001": _store_diagnostics(
                selected_goal="REPAY_DEBT",
                selected_goal_id="goal-debt",
                selected_score=2_000,
                candidates=[store, winner],
                lost_by=650,
            )
        },
    )

    metrics = census.metrics()
    assert metrics["causal_classification"] == "B_STORE_CANDIDATE_ALWAYS_LOSES"
    assert metrics["winners_when_store_candidate_present"] == {"REPAY_DEBT": 1}
    assert metrics["store_candidate_lost_by_distribution"]["median"] == 650


def test_selected_store_path_distinguishes_move_from_store_commit():
    census = SocialDensityCensus()
    store = _store_candidate()
    diagnostics = {
        "person-001": _store_diagnostics(
            selected_goal=STORE_GOAL,
            selected_goal_id="goal-store",
            selected_score=1_350,
            candidates=[store],
        )
    }
    census.observe_candidate_build(
        actor_id="person-001", entity=_person(3), delta=_storage_delta(visible=True),
        tick=8, candidates=[store],
    )
    census.observe_tick(
        tick=8,
        entities={"person-001": _person(3, "move")},
        accepted=[_accepted_storage_path(tick=8, action_type="move")],
        rejected=[],
        diagnostics=diagnostics,
    )
    assert census.classify() == "C_STORE_SELECTED_BUT_ONLY_MOVE_COMMITS"

    census.observe_candidate_build(
        actor_id="person-001", entity=_person(3), delta=_storage_delta(visible=True),
        tick=9, candidates=[store],
    )
    census.observe_tick(
        tick=9,
        entities={
            "person-001": _person(2, "store"),
            "group-shared-state-000": {
                "groups": {
                    "group-001": {
                        "facts": {
                            "fact-storage": {
                                "category": "shared_storage",
                                "target_id": "storage-camp",
                            }
                        }
                    }
                }
            },
        },
        accepted=[_accepted_storage_path(tick=9, action_type="store")],
        rejected=[],
        diagnostics=diagnostics,
    )

    metrics = census.metrics()
    assert metrics["causal_classification"] == "STORE_ORGANICALLY_REACHABLE"
    assert metrics["selected_store_committed_actions"] == {"move": 1, "store": 1}
    assert metrics["storage_actions_by_type"] == {"store": 1}
    assert metrics["store_action_actor_count"] == 1
    assert metrics["storage_targets"] == ["storage-camp"]
    assert metrics["shared_storage_fact_ever_formed"] is True
    assert metrics["first_shared_storage_fact_tick"] == 9
    assert metrics["ticks_with_shared_storage_fact"] == 1
    assert metrics["shared_storage_fact_group_ids"] == ["group-001"]
    assert metrics["shared_storage_fact_targets"] == ["storage-camp"]


def test_threshold_shadow_scores_candidate_without_changing_actual_census():
    census = SocialDensityCensus(shadow_food_threshold=2)
    census.observe_candidate_build(
        actor_id="person-001",
        entity=_person(2),
        delta=_storage_delta(visible=True),
        tick=3,
        candidates=[],
        state={},
        knowledge={},
    )
    fallback = {"goal": "REST", "goal_id": "goal-rest", "score_total": 60}
    census.observe_tick(
        tick=3,
        entities={"person-001": _person(2)},
        accepted=[],
        rejected=[],
        diagnostics={
            "person-001": _store_diagnostics(
                selected_goal="REST",
                selected_goal_id="goal-rest",
                selected_score=60,
                candidates=[fallback],
            )
        },
    )

    metrics = census.metrics()
    shadow = metrics["shadow_store_candidate"]
    assert metrics["causal_classification"] == "A_FOOD_NEVER_REACHES_3"
    assert shadow["food_threshold"] == 2
    assert shadow["joint_opportunity_count"] == 1
    assert shadow["would_win_count"] == 1
    assert shadow["would_win_by_actor"] == {"person-001": 1}
    assert shadow["actual_winners"] == {"REST": 1}
    assert shadow["actual_candidate_count_distribution"]["max"] == 1
