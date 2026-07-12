"""Phase 5B — giver-owned food transfer contract."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.commit_pipeline import run_commit_frame
from core.constants import CRITICAL_THRESHOLD, ENGINE_VERSION, FOOD_TRANSFER_SURPLUS
from core.hashing import canonical_hash
from core.mutations import apply_mutation
from core.rng import DeterministicRNG
from domains.base import ActivationFrame, DomainOutput
from domains.people_domain import PeopleDomain
from domains.people_utility import eligible_food_recipient
from domains.perception import empty_knowledge, perceive


def _person(position, *, hunger=100, food=0, inventory=0, alive=True):
    return {
        "type": "person", "position": dict(position), "alive": alive,
        "hunger": hunger, "thirst": 100, "energy": 900, "inventory": inventory,
        "food_inventory": food, "has_shelter": False, "knowledge": empty_knowledge(),
        "action": {"type": "idle", "status": "completed", "ticks_spent": 0},
        "plan": {"goal": None, "steps": [], "step_index": 0, "status": "completed"},
    }


def _entities(giver_food=FOOD_TRANSFER_SURPLUS):
    return {
        "person-giver": _person({"x": 2, "y": 2}, food=giver_food),
        "person-receiver": _person({"x": 3, "y": 2}, hunger=CRITICAL_THRESHOLD),
    }


def _proposal(entities, *, entity_id="person-giver", transfer=None, mutation=None):
    transfer = transfer or {
        "contract_version": "food-transfer-v1", "giver_id": "person-giver",
        "receiver_id": "person-receiver", "field": "food_inventory", "quantity": 1,
    }
    mutation = mutation or {
        "entity_updates": {
            "person-giver": {"food_inventory": entities["person-giver"]["food_inventory"] - 1},
            "person-receiver": {"food_inventory": entities["person-receiver"]["food_inventory"] + 1},
        },
        "new_entities": {},
    }
    return {
        "proposal_family": "people_action", "proposal_type": "give_food",
        "proposer_engine_id": "people", "proposer_engine_version": "2.1.0",
        "entity_id": entity_id, "causal_parent_event_ids": [], "is_exogenous": True,
        "requested_time": 5, "phase": "agent", "engine_priority": 10,
        "touched_scope": ["person-giver", "person-receiver"],
        "preconditions": [
            {"entity_id": "person-giver", "field": "alive", "op": "eq", "value": True},
            {"entity_id": "person-giver", "field": "food_inventory", "op": "gte", "value": FOOD_TRANSFER_SURPLUS},
            {"entity_id": "person-receiver", "field": "alive", "op": "eq", "value": True},
            {"entity_id": "person-receiver", "field": "hunger", "op": "gte", "value": CRITICAL_THRESHOLD},
            {"entity_id": "person-receiver", "field": "food_inventory", "op": "eq", "value": 0},
            {"entity_id": "person-receiver", "field": "inventory", "op": "eq", "value": 0},
        ],
        "mutation": mutation, "transfer": transfer, "explanation": "test transfer",
    }


def _commit(entities, proposals):
    return run_commit_frame(
        entities, [DomainOutput(proposals=proposals)], 5, "phase5b-lineage", "run", 0, "frame-5",
    )


def test_giver_candidate_selects_stable_adjacent_recipient_and_commits_atomically():
    entities = _entities()
    entities["person-alpha"] = _person({"x": 2, "y": 3}, hunger=CRITICAL_THRESHOLD)
    terrain = [["grass"] * 8 for _ in range(8)]
    delta = perceive(entities["person-giver"]["position"], entities, terrain, 5, "person-giver")
    assert eligible_food_recipient(entities["person-giver"], entities["person-giver"]["position"], entities, delta) == "person-alpha"

    frame = ActivationFrame(
        "run", 5, ENGINE_VERSION, "agent", entities, terrain, ["person-giver"], DeterministicRNG("phase5b"),
    )
    frame.night = False
    proposal = PeopleDomain().activate(frame).proposals[0]
    assert proposal["proposal_type"] == "give_food"
    assert proposal["transfer"]["receiver_id"] == "person-alpha"

    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    assert len(accepted) == 1
    event = accepted[0]
    assert event["transfer"]["giver_id"] == "person-giver"
    assert set(event["touched_scope"]) == {"person-giver", "person-alpha"}
    assert entities["person-giver"]["food_inventory"] == 1
    assert entities["person-alpha"]["food_inventory"] == 1
    assert entities["person-giver"]["food_inventory"] + entities["person-alpha"]["food_inventory"] == FOOD_TRANSFER_SURPLUS


def test_insufficient_inventory_is_rejected_without_mutation():
    entities = _entities(giver_food=FOOD_TRANSFER_SURPLUS - 1)
    before = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(entities, [_proposal(entities)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "food_transfer.insufficient_food"
    assert entities == before


def test_invalid_ownership_is_rejected_without_mutation():
    entities = _entities()
    before = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(entities, [_proposal(entities, entity_id="person-receiver")])
    assert accepted == []
    assert rejected[0]["reason_code"] == "food_transfer.invalid_ownership"
    assert entities == before


def test_duplicate_proposal_is_deterministic_and_replay_safe():
    first_entities = _entities()
    proposal = _proposal(first_entities)
    accepted, rejected, _ = _commit(first_entities, [proposal, copy.deepcopy(proposal)])
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["reason_code"] == "food_transfer.insufficient_food"

    replayed = _entities()
    apply_mutation(replayed, copy.deepcopy(accepted[0]["mutation"]))
    assert replayed == first_entities

    second_entities = _entities()
    second_accepted, second_rejected, _ = _commit(second_entities, [_proposal(second_entities)])
    assert second_rejected == []
    assert canonical_hash(accepted[0]) == canonical_hash(second_accepted[0])
    assert second_entities == first_entities


def test_invalid_partial_mutation_rolls_back_before_core_apply():
    entities = _entities()
    before = copy.deepcopy(entities)
    partial = {
        "entity_updates": {"person-giver": {"food_inventory": FOOD_TRANSFER_SURPLUS - 1}},
        "new_entities": {},
    }
    accepted, rejected, _ = _commit(entities, [_proposal(entities, mutation=partial)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "food_transfer.invalid_mutation"
    assert entities == before
