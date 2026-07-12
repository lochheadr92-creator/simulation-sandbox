"""Capability Stage 6C canonical actions, affordances, and consequences."""
import copy

import pytest

from core.commit_pipeline import run_commit_frame
from core.mutations import apply_mutation
from domains.base import ActivationFrame, DomainOutput
from domains.ecology_domain import EcologyDomain
from domains.living_agent_actions import (
    build_physical_action_proposal,
    validate_living_action_proposal,
)
from domains.living_agent_contracts import PHYSICAL_ACTION_TYPES
from scenarios.wilderness_survival import SCENARIO
from core.kernel import build_genesis


def _person(position, *, food=0, wood=0, health=900, energy=800, last_event_id="evt-person"):
    return {
        "type": "person", "position": dict(position), "alive": True,
        "health": health, "energy": energy, "hunger": 500, "thirst": 400,
        "inventory": wood, "food_inventory": food,
        "carried_resources": {"wood": wood, "food": food},
        "inventory_capacity": 30, "carried_item_ids": [],
        "last_event_id": last_event_id,
    }


def _plan(goal="STORE_SURPLUS"):
    return {
        "plan_id": f"plan-{goal.lower()}", "goal_id": f"goal-{goal.lower()}",
        "goal": goal, "step_index": 0,
    }


def _commit(entities, proposal, tick=1):
    return run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], tick, "lineage", "run", 0, f"frame-{tick}",
    )


def test_required_physical_action_vocabulary_is_executable_contract_surface():
    required = {
        "move", "gather", "carry", "store", "retrieve", "consume", "drink", "rest",
        "use_tool", "construct", "repair", "damage", "open", "access", "give", "take",
        "help", "warn", "request", "refuse",
    }
    assert required <= PHYSICAL_ACTION_TYPES


def test_store_and_retrieve_conserve_resources_and_replay_exactly():
    initial = {
        "person-a": _person({"x": 1, "y": 1}, food=3),
        "storage-a": {
            "type": "storage", "position": {"x": 2, "y": 1}, "contents": {"food": 1},
            "capacity": 10, "owner_id": "person-a", "access": "private",
            "open": True, "last_event_id": "evt-storage",
        },
    }
    entities = copy.deepcopy(initial)
    store = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="store", tick=1,
        target_id="storage-a", resource_kind="food", quantity=2, plan=_plan(),
    )
    accepted, rejected, order = _commit(entities, store)

    assert not rejected
    assert entities["person-a"]["carried_resources"]["food"] == 1
    assert entities["storage-a"]["contents"]["food"] == 3
    assert entities["person-a"]["carried_resources"]["food"] + entities["storage-a"]["contents"]["food"] == 4
    event = accepted[0]
    assert event["living_action"]["resource_transfer"]["quantity"] == 2

    replayed = copy.deepcopy(initial)
    apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    assert replayed == entities

    retrieve = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="retrieve", tick=2,
        target_id="storage-a", resource_kind="food", quantity=1, plan=_plan("RETRIEVE"),
    )
    accepted2, rejected2, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[retrieve])], 2, "lineage", "run", order, "frame-2",
    )
    assert not rejected2 and accepted2
    assert entities["person-a"]["carried_resources"]["food"] == 2
    assert entities["storage-a"]["contents"]["food"] == 2


def test_tampered_nonconserving_transfer_rejects_without_mutation():
    entities = {
        "person-a": _person({"x": 1, "y": 1}, food=3),
        "storage-a": {
            "type": "storage", "position": {"x": 2, "y": 1}, "contents": {"food": 1},
            "capacity": 10, "owner_id": "person-a", "access": "private",
            "last_event_id": "evt-storage",
        },
    }
    proposal = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="store", tick=1,
        target_id="storage-a", resource_kind="food", quantity=1, plan=_plan(),
    )
    proposal["mutation"]["entity_updates"]["storage-a"]["contents"]["food"] = 9
    before = copy.deepcopy(entities)

    accepted, rejected, _ = _commit(entities, proposal)

    assert not accepted
    assert rejected[0]["reason_code"] == "living_action.nonconserving_transfer"
    assert entities == before


def test_access_rules_fail_closed_but_explicit_unauthorized_take_is_inspectable():
    entities = {
        "person-a": _person({"x": 1, "y": 1}),
        "storage-b": {
            "type": "storage", "position": {"x": 2, "y": 1}, "contents": {"food": 2},
            "capacity": 10, "owner_id": "person-b", "access": "private",
            "last_event_id": "evt-storage",
        },
    }
    with pytest.raises(ValueError, match="access denied"):
        build_physical_action_proposal(
            entities, actor_id="person-a", action_type="retrieve", tick=1,
            target_id="storage-b", resource_kind="food", plan=_plan("RETRIEVE"),
        )

    taking = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="take", tick=1,
        target_id="storage-b", resource_kind="food", plan=_plan("TAKE"),
        allow_unauthorized=True,
    )
    accepted, rejected, _ = _commit(entities, taking)
    assert not rejected and accepted
    assert accepted[0]["living_action"]["access_violation"] is True
    assert entities["person-a"]["carried_resources"]["food"] == 1


def test_repair_changes_structure_uses_material_wears_tool_and_creates_evidence():
    entities = {
        "person-a": _person({"x": 1, "y": 1}, wood=2),
        "shelter-a": {
            "type": "shelter", "position": {"x": 2, "y": 1}, "condition": 500,
            "max_condition": 1000, "owner_id": "person-a", "access": "private",
            "last_event_id": "evt-shelter",
        },
        "tool-a": {
            "type": "tool", "position": {"x": 1, "y": 1}, "tool_kind": "hammer",
            "durability": 5, "owner_id": "person-a", "access": "private",
            "carried_by": "person-a", "last_event_id": "evt-tool",
        },
    }
    proposal = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="repair", tick=1,
        target_id="shelter-a", tool_id="tool-a", quantity=1, plan=_plan("REPAIR"),
    )
    accepted, rejected, _ = _commit(entities, proposal)

    assert not rejected and accepted
    assert entities["shelter-a"]["condition"] == 620
    assert entities["tool-a"]["durability"] == 4
    assert entities["person-a"]["carried_resources"]["wood"] == 1
    signals = [entity for entity in entities.values() if entity.get("type") == "signal"]
    assert len(signals) == 1
    assert signals[0]["source_event_id"] == accepted[0]["id"]
    assert signals[0]["signal_kind"] == "noise"


def test_signal_expiry_is_proposal_only_and_bounded():
    entities = {
        "person-a": _person({"x": 1, "y": 1}),
        "person-b": _person({"x": 2, "y": 1}, last_event_id="evt-b"),
    }
    warn = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="warn", tick=1,
        target_id="person-b", plan=_plan("WARN"), message={"danger": "smoke"},
    )
    accepted, rejected, order = _commit(entities, warn)
    assert not rejected and accepted
    signal_id = next(key for key, value in entities.items() if value.get("type") == "signal")
    expires = entities[signal_id]["expires_tick"]

    domain = EcologyDomain()
    frame = ActivationFrame(
        "run", expires, "engine", "environment", entities, [], [signal_id], None,
    )
    output = domain.activate(frame)
    assert signal_id in entities
    accepted2, rejected2, _ = run_commit_frame(
        entities, [output], expires, "lineage", "run", order, f"frame-{expires}",
    )
    assert not rejected2 and accepted2
    assert signal_id not in entities


def test_world_genesis_has_explicit_affordances_and_inventory_contracts():
    _world, entities, accepted, rejected, _ = build_genesis("stage6-affordances", SCENARIO, "lineage")
    assert accepted and not rejected
    person = next(entity for entity in entities.values() if entity["type"] == "person")
    tree = next(entity for entity in entities.values() if entity["type"] == "tree")

    assert person["carried_resources"] == {"wood": 0, "food": 0}
    assert person["inventory_capacity"] == 30
    assert person["affordances"]["schema_version"] == "affordance-v1"
    assert tree["affordances"]["gatherable"] is True
    assert tree["resource_kind"] == "wood"


def test_validator_rejects_missing_causal_plan_and_action_mismatch():
    entities = {
        "person-a": _person({"x": 1, "y": 1}),
    }
    proposal = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="rest", tick=1, plan=_plan("REST"),
    )
    proposal["living_action"]["plan_id"] = None
    assert validate_living_action_proposal(proposal, entities) == "living_action.missing_causal_state"
    proposal["living_action"]["plan_id"] = "plan-rest"
    proposal["mutation"]["entity_updates"]["person-a"]["action"]["action_id"] = "different"
    assert validate_living_action_proposal(proposal, entities) == "living_action.action_mismatch"
