"""Culture Pass — Tier A: deterministic pipeline contracts (CULTURE_PASS.md).

Every test drives real domain activation and/or the real commit pipeline
(run_commit_frame), mirroring the Surplus Pass Tier A structure. The culture
layer rides the EXISTING proposal set: aid is an offer_trade proposal under
the people-aid-v1 contract; norms, collective memory, aid eligibility and
gate-keeping live in the per-person `culture_state` field (surplus-enabled
persons only). Stable reason codes on the rejection paths, replay safety, and
two-run hash equality with culture active.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.commit_pipeline import run_commit_frame
from core.constants import (
    AID_CONTRACT_VERSION,
    AID_GIVER_MIN_FOOD,
    AID_QUANTITY,
    AID_RECEIVER_MIN_HUNGER,
    CULTURE_MEMORY_HALF_LIFE_TICKS,
    CULTURE_MEMORY_MAX_ENTRIES,
    CULTURE_STATE_VERSION,
    ENGINE_VERSION,
    TRADE_CONTRACT_VERSION,
    TRADE_MIN_RETAIN,
    TRADE_QUANTITY,
)
from core.hashing import canonical_hash
from core.mutations import apply_mutation
from core.rng import DeterministicRNG
from domains.base import ActivationFrame, DomainOutput
from domains.interaction_memory import KIND_HELPED, build_fact
from domains.people_culture import (
    _seeded_receive_x100,
    effective_weight_x100,
    empty_culture_state,
    gate_status,
    record_trade_outcome,
    update_culture_state,
)
from domains.people_domain import PeopleDomain
from domains.perception import empty_knowledge

TICK = 5
LINEAGE = "culture-pass-lineage"


def _person(entity_id, position, *, hunger=100, food=0, inventory=0, capacity=30,
            action=None, stored=None, storage=None, culture=None,
            living_agent=None, knowledge=None, plan_goal=None):
    action = action or {"type": "idle", "status": "completed", "ticks_spent": 0}
    if plan_goal is not None:
        plan = {"goal": plan_goal, "steps": [plan_goal], "step_index": 0,
                "status": "active", "created_tick": TICK}
    else:
        plan = {"goal": None, "steps": [], "step_index": 0, "status": "completed"}
    person = {
        "type": "person", "position": dict(position), "alive": True,
        "hunger": hunger, "thirst": 100, "energy": 900,
        "inventory": inventory, "food_inventory": food,
        "carried_resources": {"wood": inventory, "food": food},
        "inventory_capacity": capacity,
        "has_shelter": False, "knowledge": knowledge or empty_knowledge(),
        "carried_item_ids": [],
        "action": action,
        "plan": plan,
        "paused": None,
        "last_event_id": f"evt-genesis-{entity_id}",
    }
    if storage is not None:
        person["storage_location"] = dict(storage)
        person["stored_resources"] = dict(stored or {"wood": 0, "food": 0})
    if culture is not None:
        person["culture_state"] = copy.deepcopy(culture)
    if living_agent is not None:
        person["living_agent"] = living_agent
    return person


def _terrain(size=8):
    return [["grass"] * size for _ in range(size)]


def _action(action_type, **overrides):
    action = {
        "type": action_type, "status": "performing", "target_entity_id": None,
        "target_pos": None, "ticks_spent": 0, "ticks_required": 1,
        "interruptible": True, "started_tick": TICK,
    }
    action.update(overrides)
    return action


def _activate(entities, due_ids, tick=TICK):
    frame = ActivationFrame(
        "run", tick, ENGINE_VERSION, "agent", entities, _terrain(), due_ids,
        DeterministicRNG("culture-pass"),
    )
    frame.night = False
    return PeopleDomain().activate(frame)


def _commit(entities, proposals, tick=TICK):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))], tick, LINEAGE, "run",
        0, f"frame-{tick}",
    )


def _aid_action(**overrides):
    return _action(
        "offer_trade", target_entity_id="person-r",
        give_field="food_inventory", receive_field=None,
        give_quantity=AID_QUANTITY, receive_quantity=0, aid=True,
        **overrides,
    )


def _aid_fixture():
    return {
        # Satiated giver holding meat beyond the keep threshold; hungry ally.
        "person-g": _person(
            "person-g", {"x": 2, "y": 2}, food=8, hunger=100,
            storage={"x": 2, "y": 2}, stored={"wood": 0, "food": 0},
            action=_aid_action(),
            plan_goal="OFFER_TRADE",
        ),
        "person-r": _person(
            "person-r", {"x": 3, "y": 2}, hunger=700, food=0,
            storage={"x": 3, "y": 2}, stored={"wood": 0, "food": 0},
        ),
    }


# ---------------------------------------------------------------------------
# aid: commits through the Core pipeline under the aid contract
# ---------------------------------------------------------------------------

def test_aid_commits_one_sided_gift():
    entities = _aid_fixture()
    proposal = _activate(entities, ["person-g"]).proposals[0]
    assert proposal["proposal_type"] == "offer_trade"
    assert proposal["trade"]["contract_version"] == AID_CONTRACT_VERSION
    assert proposal["trade"]["receive_quantity"] == 0

    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    assert len(accepted) == 1
    event = accepted[0]
    assert event["trade"]["giver_id"] == "person-g"
    assert event["trade"]["receiver_id"] == "person-r"
    assert {"person-g", "person-r"} <= set(event["touched_scope"])
    giver, receiver = entities["person-g"], entities["person-r"]
    # One-sided: giver decrements surplus, receiver gains, nothing comes back.
    assert giver["food_inventory"] == 8 - AID_QUANTITY
    assert giver["inventory"] == 0
    assert receiver["food_inventory"] == AID_QUANTITY
    assert giver["carried_resources"] == {"wood": 0, "food": 8 - AID_QUANTITY}
    assert receiver["carried_resources"] == {"wood": 0, "food": AID_QUANTITY}


def test_aid_replay_safe():
    entities = _aid_fixture()
    proposal = _activate(entities, ["person-g"]).proposals[0]
    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    replayed = _aid_fixture()
    apply_mutation(replayed, copy.deepcopy(accepted[0]["mutation"]))
    assert replayed == entities


def _aid_proposal(entities, *, mutation=None, trade=None, preconditions=None):
    giver = entities["person-g"]
    receiver = entities["person-r"]
    trade = trade or {
        "contract_version": AID_CONTRACT_VERSION,
        "giver_id": "person-g", "receiver_id": "person-r",
        "give_field": "food_inventory", "give_quantity": AID_QUANTITY,
        "receive_field": None, "receive_quantity": 0,
    }
    mutation = mutation or {
        "entity_updates": {
            "person-g": {
                "inventory": giver["inventory"],
                "food_inventory": giver["food_inventory"] - AID_QUANTITY,
                "carried_resources": {
                    "wood": giver["inventory"],
                    "food": giver["food_inventory"] - AID_QUANTITY,
                },
            },
            "person-r": {
                "inventory": receiver["inventory"],
                "food_inventory": receiver["food_inventory"] + AID_QUANTITY,
                "carried_resources": {
                    "wood": receiver["inventory"],
                    "food": receiver["food_inventory"] + AID_QUANTITY,
                },
            },
        },
        "new_entities": {},
    }
    preconditions = preconditions or [
        {"entity_id": "person-g", "field": "alive", "op": "eq", "value": True},
        {"entity_id": "person-g", "field": "food_inventory", "op": "gte",
         "value": AID_GIVER_MIN_FOOD},
        {"entity_id": "person-r", "field": "alive", "op": "eq", "value": True},
        {"entity_id": "person-r", "field": "hunger", "op": "gte",
         "value": AID_RECEIVER_MIN_HUNGER},
        {"entity_id": "person-r", "field": "food_inventory", "op": "eq",
         "value": receiver["food_inventory"]},
        {"entity_id": "person-r", "field": "inventory", "op": "eq",
         "value": receiver["inventory"]},
        {"entity_id": "person-r", "field": "position", "op": "eq",
         "value": dict(receiver["position"])},
    ]
    return {
        "proposal_family": "people_action", "proposal_type": "offer_trade",
        "proposer_engine_id": "people", "proposer_engine_version": "2.1.0",
        "entity_id": "person-g", "causal_parent_event_ids": [], "is_exogenous": True,
        "requested_time": TICK, "phase": "agent", "engine_priority": 10,
        "touched_scope": ["person-g", "person-r"],
        "preconditions": preconditions, "mutation": mutation,
        "trade": trade, "explanation": "test aid",
    }


def test_aid_invalid_terms_reject():
    entities = _aid_fixture()
    before = copy.deepcopy(entities)
    trade = {
        "contract_version": AID_CONTRACT_VERSION,
        "giver_id": "person-g", "receiver_id": "person-r",
        "give_field": "food_inventory", "give_quantity": AID_QUANTITY,
        "receive_field": "inventory", "receive_quantity": 1,  # reciprocity leg: not aid
    }
    accepted, rejected, _ = _commit(entities, [_aid_proposal(entities, trade=trade)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "aid.invalid_terms"
    assert entities == before


def test_aid_insufficient_surplus_rejects_without_mutation():
    entities = _aid_fixture()
    entities["person-g"]["food_inventory"] = AID_GIVER_MIN_FOOD - 1
    entities["person-g"]["carried_resources"] = {"wood": 0, "food": AID_GIVER_MIN_FOOD - 1}
    before = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(entities, [_aid_proposal(entities)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "aid.insufficient_surplus"
    assert entities == before


def test_aid_receiver_not_in_need_rejects_without_mutation():
    entities = _aid_fixture()
    entities["person-r"]["hunger"] = AID_RECEIVER_MIN_HUNGER - 1
    before = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(entities, [_aid_proposal(entities)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "aid.receiver_not_in_need"
    assert entities == before


def test_aid_out_of_range_rejects_without_mutation():
    entities = _aid_fixture()
    entities["person-r"]["position"] = {"x": 7, "y": 7}
    before = copy.deepcopy(entities)
    proposal = _aid_proposal(
        entities,
        preconditions=[
            {"entity_id": "person-g", "field": "alive", "op": "eq", "value": True},
            {"entity_id": "person-g", "field": "food_inventory", "op": "gte",
             "value": AID_GIVER_MIN_FOOD},
            {"entity_id": "person-r", "field": "alive", "op": "eq", "value": True},
            {"entity_id": "person-r", "field": "hunger", "op": "gte",
             "value": AID_RECEIVER_MIN_HUNGER},
            {"entity_id": "person-r", "field": "food_inventory", "op": "eq",
             "value": entities["person-r"]["food_inventory"]},
            {"entity_id": "person-r", "field": "inventory", "op": "eq",
             "value": entities["person-r"]["inventory"]},
            {"entity_id": "person-r", "field": "position", "op": "eq",
             "value": {"x": 7, "y": 7}},
        ],
    )
    accepted, rejected, _ = _commit(entities, [proposal])
    assert accepted == []
    assert rejected[0]["reason_code"] == "aid.out_of_range"
    assert entities == before


def test_aid_receiver_capacity_exceeded_rejects_without_mutation():
    entities = _aid_fixture()
    entities["person-r"]["inventory"] = 30
    entities["person-r"]["carried_resources"] = {"wood": 30, "food": 0}
    before = copy.deepcopy(entities)
    proposal = _aid_proposal(entities, mutation={
        "entity_updates": {
            "person-g": {
                "inventory": entities["person-g"]["inventory"],
                "food_inventory": entities["person-g"]["food_inventory"] - AID_QUANTITY,
                "carried_resources": {
                    "wood": entities["person-g"]["inventory"],
                    "food": entities["person-g"]["food_inventory"] - AID_QUANTITY,
                },
            },
            "person-r": {
                "inventory": 30,
                "food_inventory": AID_QUANTITY,
                "carried_resources": {"wood": 30, "food": AID_QUANTITY},
            },
        },
        "new_entities": {},
    })
    accepted, rejected, _ = _commit(entities, [proposal])
    assert accepted == []
    assert rejected[0]["reason_code"] == "aid.receiver_capacity_exceeded"
    assert entities == before


def test_aid_invalid_mutation_rejects_without_mutation():
    entities = _aid_fixture()
    before = copy.deepcopy(entities)
    partial = {
        "entity_updates": {
            "person-g": {"food_inventory": entities["person-g"]["food_inventory"] - AID_QUANTITY},
        },
        "new_entities": {},
    }
    accepted, rejected, _ = _commit(entities, [_aid_proposal(entities, mutation=partial)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "aid.invalid_mutation"
    assert entities == before


def test_aid_missing_preconditions_reject_without_mutation():
    entities = _aid_fixture()
    before = copy.deepcopy(entities)
    proposal = _aid_proposal(entities, preconditions=[
        {"entity_id": "person-g", "field": "alive", "op": "eq", "value": True},
    ])
    accepted, rejected, _ = _commit(entities, [proposal])
    assert accepted == []
    assert rejected[0]["reason_code"] == "aid.invalid_preconditions"
    assert entities == before


def test_aid_arbitrary_wood_mutation_rejects():
    # Cairn S3: the aid validator re-derives the wood leg against live state
    # too — aid moves meat, never wood.
    entities = _aid_fixture()
    before = copy.deepcopy(entities)
    giver = entities["person-g"]
    receiver = entities["person-r"]
    mutation = {
        "entity_updates": {
            "person-g": {
                "inventory": 99,  # arbitrary wood write, mirror aligned
                "food_inventory": giver["food_inventory"] - AID_QUANTITY,
                "carried_resources": {"wood": 99, "food": giver["food_inventory"] - AID_QUANTITY},
            },
            "person-r": {
                "inventory": receiver["inventory"],
                "food_inventory": receiver["food_inventory"] + AID_QUANTITY,
                "carried_resources": {
                    "wood": receiver["inventory"],
                    "food": receiver["food_inventory"] + AID_QUANTITY,
                },
            },
        },
        "new_entities": {},
    }
    accepted, rejected, _ = _commit(entities, [_aid_proposal(entities, mutation=mutation)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "aid.invalid_mutation"
    assert entities == before


# ---------------------------------------------------------------------------
# adversarial-review regression tests (Cairn S2/S4/S5)
# ---------------------------------------------------------------------------

def _barter_proposal(entities, give_qty, receive_qty, *, mutation=None,
                     preconditions=None, retain_pin=True):
    giver = entities["person-g"]
    receiver = entities["person-r"]
    mutation = mutation or {
        "entity_updates": {
            "person-g": {
                "inventory": giver["inventory"] - give_qty,
                "food_inventory": giver["food_inventory"] + receive_qty,
                "carried_resources": {
                    "wood": giver["inventory"] - give_qty,
                    "food": giver["food_inventory"] + receive_qty,
                },
            },
            "person-r": {
                "inventory": receiver["inventory"] + give_qty,
                "food_inventory": receiver["food_inventory"] - receive_qty,
                "carried_resources": {
                    "wood": receiver["inventory"] + give_qty,
                    "food": receiver["food_inventory"] - receive_qty,
                },
            },
        },
        "new_entities": {},
    }
    if preconditions is None:
        preconditions = [
            {"entity_id": "person-g", "field": "alive", "op": "eq", "value": True},
            {"entity_id": "person-g", "field": "inventory", "op": "gte",
             "value": give_qty + TRADE_MIN_RETAIN},
            {"entity_id": "person-r", "field": "alive", "op": "eq", "value": True},
            {"entity_id": "person-r", "field": "food_inventory", "op": "eq",
             "value": receiver["food_inventory"]},
            {"entity_id": "person-r", "field": "inventory", "op": "eq",
             "value": receiver["inventory"]},
            {"entity_id": "person-r", "field": "position", "op": "eq",
             "value": dict(receiver["position"])},
        ]
        if retain_pin:
            preconditions.append(
                {"entity_id": "person-r", "field": "food_inventory", "op": "gte",
                 "value": receive_qty + TRADE_MIN_RETAIN},
            )
    return {
        "proposal_family": "people_action", "proposal_type": "offer_trade",
        "proposer_engine_id": "people", "proposer_engine_version": "2.1.0",
        "entity_id": "person-g", "causal_parent_event_ids": [], "is_exogenous": True,
        "requested_time": TICK, "phase": "agent", "engine_priority": 10,
        "touched_scope": ["person-g", "person-r"],
        "preconditions": preconditions,
        "mutation": mutation,
        "trade": {
            "contract_version": TRADE_CONTRACT_VERSION,
            "giver_id": "person-g", "receiver_id": "person-r",
            "give_field": "inventory", "give_quantity": give_qty,
            "receive_field": "food_inventory", "receive_quantity": receive_qty,
        },
        "explanation": "test norm-priced trade",
    }


def test_trade_capacity_overflow_rejects_without_mutation():
    # Cairn S2: norm-priced terms (give 2 / receive 3) net +1 carry; an agent
    # at capacity must not overflow through an accepted proposal.
    entities = _barter_fixture()
    entities["person-g"]["inventory"] = 29  # 29 + 1 food = 30/30 capacity
    entities["person-g"]["carried_resources"] = {"wood": 29, "food": 1}
    before = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(entities, [_barter_proposal(entities, 2, 3)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "trade.capacity_exceeded"
    assert entities == before


def test_trade_receiver_retain_required_and_bites():
    # Cairn S5: without the retain pin the proposal fails Core's required-set
    # check; with it, a 4-stock receiver cannot pay 3.
    entities = _barter_fixture()
    entities["person-r"]["food_inventory"] = 4
    entities["person-r"]["carried_resources"] = {"wood": 1, "food": 4}
    before = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(
        entities, [_barter_proposal(entities, 2, 3, retain_pin=False)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "trade.invalid_preconditions"
    accepted2, rejected2, _ = _commit(
        entities, [_barter_proposal(entities, 2, 3, retain_pin=True)])
    assert accepted2 == []
    assert rejected2[0]["reason_code"] == "precondition.failed"
    assert entities == before


def test_memory_cap_committed_at_max_and_eviction_reports_change():
    # Cairn S4: eviction runs after insert, so committed state never exceeds
    # the cap, and cap deletions count as change.
    state = empty_culture_state()
    for i in range(CULTURE_MEMORY_MAX_ENTRIES + 3):
        changed = record_trade_outcome(
            state, giver_id="person-g", receiver_id=f"person-{i:03d}",
            give_field="inventory", give_quantity=2,
            receive_field="food_inventory", receive_quantity=2,
            tick=i, source="own", ref_id=f"evt-{i}", generosity=None,
        )
        assert changed
        assert len(state["memory"]) <= CULTURE_MEMORY_MAX_ENTRIES


def test_offer_terms_clamped_for_retain_and_capacity():
    # Cairn S2/S5 emission mirrors: the generator never emits a self-doomed
    # offer — retain clamps the ask against a thin partner, room clamps it
    # against a full pack.
    culture = empty_culture_state()
    culture["norms"]["inventory>food_inventory"] = {
        "give_field": "inventory", "receive_field": "food_inventory",
        "expected_give_x100": 200, "expected_receive_x100": 300,  # greedy ask
        "accepts": 1, "witnessed": 0, "last_tick": TICK - 1,
    }
    # Retain: partner holds exactly TRADE_MIN_SURPLUS food (4) -> ask clamps to 2.
    partner = _person("person-b", {"x": 3, "y": 2}, inventory=1, food=4,
                      storage={"x": 3, "y": 2})
    partner["id"] = "person-b"
    giver = _person("person-a", {"x": 2, "y": 2}, inventory=6, food=1,
                    storage={"x": 2, "y": 2}, culture=culture)
    entities = {"person-a": giver, "person-b": partner}
    _scores, context = _scores_for(giver, entities, _trade_sightings(partner))
    assert context["trade_receive_quantity"] == 2

    # Capacity: giver at 29/29 (room 0) -> no net inflow, ask clamps to give.
    full = _person("person-a", {"x": 2, "y": 2}, inventory=28, food=1,
                   capacity=29, storage={"x": 2, "y": 2}, culture=culture)
    partner_full = _person("person-b", {"x": 3, "y": 2}, inventory=1, food=10,
                           storage={"x": 3, "y": 2})
    partner_full["id"] = "person-b"
    entities = {"person-a": full, "person-b": partner_full}
    _scores, context = _scores_for(full, entities, _trade_sightings(partner_full))
    assert context["trade_give_quantity"] == 2
    assert context["trade_receive_quantity"] == 2


# ---------------------------------------------------------------------------
# collective memory: own-trade recording, witnessing, decay, gate
# ---------------------------------------------------------------------------

def _barter_fixture():
    return {
        "person-g": _person(
            "person-g", {"x": 2, "y": 2}, inventory=6, food=1,
            storage={"x": 2, "y": 2}, stored={"wood": 0, "food": 0},
            action=_action(
                "offer_trade", target_entity_id="person-r",
                give_field="inventory", receive_field="food_inventory",
                give_quantity=TRADE_QUANTITY, receive_quantity=TRADE_QUANTITY,
                aid=False,
            ),
            plan_goal="OFFER_TRADE",
        ),
        "person-r": _person(
            "person-r", {"x": 3, "y": 2}, inventory=1, food=6,
            storage={"x": 3, "y": 2}, stored={"wood": 0, "food": 0},
        ),
    }


def test_own_accepted_trade_is_recorded_next_activation_once():
    entities = _barter_fixture()
    proposal = _activate(entities, ["person-g"]).proposals[0]
    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    assert entities["person-g"]["action"]["accepted_event_id"] == accepted[0]["id"]

    # Next activation: the committed action carries terms + accepted_event_id,
    # so the outcome lands in culture_state (memory entry + norm accept).
    output = _activate(entities, ["person-g"], tick=TICK + 1)
    update = output.proposals[0]["mutation"]["entity_updates"]["person-g"]
    culture = update["culture_state"]
    assert culture["version"] == CULTURE_STATE_VERSION
    assert len(culture["memory"]) == 1
    entry = next(iter(culture["memory"].values()))
    assert entry["giver_id"] == "person-g"
    assert entry["receiver_id"] == "person-r"
    assert entry["give_field"] == "inventory"
    assert entry["receive_field"] == "food_inventory"
    assert entry["tick"] == TICK
    assert entry["source"] == "own"
    norm = culture["norms"]["inventory>food_inventory"]
    assert norm["accepts"] == 1
    # The CAS pin guards the write; first write pins the absent field.
    pins = output.proposals[0]["preconditions"]
    assert any(
        p["entity_id"] == "person-g" and p["field"] == "culture_state"
        and p["op"] == "eq" and p["value"] is None
        for p in pins
    )

    accepted2, rejected2, _ = _commit(entities, output.proposals, tick=TICK + 1)
    assert rejected2 == []
    assert entities["person-g"]["culture_state"] == culture

    # Third activation: no new outcome, so culture_state does not rewrite.
    output3 = _activate(entities, ["person-g"], tick=TICK + 2)
    update3 = output3.proposals[0]["mutation"]["entity_updates"]["person-g"]
    assert "culture_state" not in update3


def _trade_signal(signal_id, position, giver, receiver, created_tick):
    return {
        "type": "signal", "schema_version": "physical-signal-v1",
        "position": dict(position), "signal_kind": "social", "strength": 500,
        "source_entity_id": giver, "source_action_id": "action-x",
        "source_event_id": None,
        "message": {
            "action_type": "trade", "target_ids": [receiver],
            "give_field": "inventory", "give_quantity": TRADE_QUANTITY,
            "receive_field": "food_inventory", "receive_quantity": TRADE_QUANTITY,
        },
        "truth_status": "physical_evidence", "propagation_depth": 0,
        "created_tick": created_tick, "expires_tick": created_tick + 4,
    }


def test_witnessed_trade_signal_is_recorded_with_terms():
    entities = {
        "person-w": _person(
            "person-w", {"x": 2, "y": 2},
            storage={"x": 2, "y": 2}, stored={"wood": 0, "food": 0},
        ),
        "signal-t": _trade_signal("signal-t", {"x": 3, "y": 2}, "person-g", "person-r", TICK - 1),
    }
    output = _activate(entities, ["person-w"])
    update = output.proposals[0]["mutation"]["entity_updates"]["person-w"]
    culture = update["culture_state"]
    assert len(culture["memory"]) == 1
    entry = next(iter(culture["memory"].values()))
    assert entry["source"] == "witness"
    assert entry["giver_id"] == "person-g"
    assert entry["receiver_id"] == "person-r"
    assert entry["give_quantity"] == TRADE_QUANTITY
    norm = culture["norms"]["inventory>food_inventory"]
    assert norm["witnessed"] == 1
    assert norm["accepts"] == 0


def test_memory_half_life_decay_and_eviction():
    state = empty_culture_state()
    record_trade_outcome(
        state, giver_id="person-g", receiver_id="person-r",
        give_field="inventory", give_quantity=2,
        receive_field="food_inventory", receive_quantity=2,
        tick=0, source="own", ref_id="evt-0-0-x", generosity=None,
    )
    entry = next(iter(state["memory"].values()))
    half = CULTURE_MEMORY_HALF_LIFE_TICKS
    assert effective_weight_x100(entry, 0) == 100
    assert effective_weight_x100(entry, half) == 50
    assert effective_weight_x100(entry, 2 * half) == 25
    assert effective_weight_x100(entry, 7 * half) == 0
    # A later touch evicts the fully decayed entry.
    record_trade_outcome(
        state, giver_id="person-g", receiver_id="person-r",
        give_field="inventory", give_quantity=2,
        receive_field="food_inventory", receive_quantity=2,
        tick=7 * half, source="own", ref_id="evt-late", generosity=None,
    )
    ticks = {entry["tick"] for entry in state["memory"].values()}
    assert ticks == {7 * half}


def test_gate_status_counts_barter_only():
    state = empty_culture_state()
    assert gate_status(state, "person-x", 10) == "non_trader"
    record_trade_outcome(
        state, giver_id="person-g", receiver_id="person-x",
        give_field="food_inventory", give_quantity=2,
        receive_field=None, receive_quantity=0,  # aid: not exchange
        tick=0, source="own", ref_id="evt-aid", generosity=None,
    )
    assert gate_status(state, "person-x", 10) == "non_trader"
    record_trade_outcome(
        state, giver_id="person-x", receiver_id="person-r",
        give_field="inventory", give_quantity=2,
        receive_field="food_inventory", receive_quantity=2,
        tick=0, source="witness", ref_id="evt-barter", generosity=None,
    )
    assert gate_status(state, "person-x", 10) == "trader"
    # Fully decayed history no longer confers trader status.
    assert gate_status(state, "person-x", 7 * CULTURE_MEMORY_HALF_LIFE_TICKS) == "non_trader"


def test_repeated_detection_does_not_double_count():
    # Adversarial find (culture self-review): an own-trade action record
    # survives a rejected follow-up proposal, and witness signals live 4
    # ticks — re-observation must not re-fire the norm EMA or counters.
    state = empty_culture_state()
    for _ in range(3):
        record_trade_outcome(
            state, giver_id="person-g", receiver_id="person-r",
            give_field="inventory", give_quantity=2,
            receive_field="food_inventory", receive_quantity=2,
            tick=0, source="own", ref_id="evt-0-0-x", generosity=None,
        )
    assert len(state["memory"]) == 1
    assert state["norms"]["inventory>food_inventory"]["accepts"] == 1
    assert state["norms"]["inventory>food_inventory"]["expected_give_x100"] == 200


def test_persistent_signal_recorded_once_across_activations():
    person = _person("person-w", {"x": 2, "y": 2},
                     storage={"x": 2, "y": 2})
    entities = {
        "person-w": person,
        "signal-t": _trade_signal("signal-t", {"x": 3, "y": 2}, "person-g", "person-r", TICK - 1),
    }
    state1, changed1 = update_culture_state(
        person, "person-w", person["knowledge"], entities, person["position"], TICK, None)
    assert changed1
    assert state1["norms"]["inventory>food_inventory"]["witnessed"] == 1
    # Same signal still in the frame next activation: nothing new to record.
    person_next = {**person, "culture_state": state1}
    _state2, changed2 = update_culture_state(
        person_next, "person-w", person["knowledge"], entities,
        person_next["position"], TICK + 1, None)
    assert not changed2


# ---------------------------------------------------------------------------
# norms: seeding, terms on the offer, and the aid gate in scoring
# ---------------------------------------------------------------------------

def _scores_for(person, entities, perception_delta=None, tick=TICK):
    from domains.people_utility import score_candidates
    candidates, context = score_candidates(
        {**person, "id": person.get("id") or "person-a"},
        person["knowledge"], person["position"], tick, False,
        person["action"], _terrain(),
        entities=entities, perception_delta=perception_delta,
    )
    return {c["goal"]: c for c in candidates}, context


def _trade_sightings(partner):
    return {"person_sightings": {partner["id"]: {"position": dict(partner["position"])}}}


def test_norm_terms_ride_the_offer():
    partner = _person("person-b", {"x": 3, "y": 2}, inventory=1, food=6,
                      storage={"x": 3, "y": 2})
    partner["id"] = "person-b"
    culture = empty_culture_state()
    culture["norms"]["inventory>food_inventory"] = {
        "give_field": "inventory", "receive_field": "food_inventory",
        "expected_give_x100": 200, "expected_receive_x100": 300,
        "accepts": 2, "witnessed": 0, "last_tick": TICK - 1,
    }
    giver = _person("person-a", {"x": 2, "y": 2}, inventory=6, food=1,
                    storage={"x": 2, "y": 2}, culture=culture)
    entities = {"person-a": giver, "person-b": partner}
    scores, context = _scores_for(giver, entities, _trade_sightings(partner))
    offer = scores["OFFER_TRADE"]
    assert offer["availability"] == 1.0
    assert offer["aid"] is False
    assert context["trade_partner_id"] == "person-b"
    assert context["trade_give_quantity"] == 2
    assert context["trade_receive_quantity"] == 3  # the norm's expected terms


def test_norm_seed_follows_generosity_trait():
    assert _seeded_receive_x100(70) == 100
    assert _seeded_receive_x100(30) == 300
    assert _seeded_receive_x100(None) == TRADE_QUANTITY * 100

    partner = _person("person-b", {"x": 3, "y": 2}, inventory=1, food=6,
                      storage={"x": 3, "y": 2})
    partner["id"] = "person-b"
    for generosity, expected in ((70, 1), (30, 3), (50, 2)):
        giver = _person(
            "person-a", {"x": 2, "y": 2}, inventory=6, food=1,
            storage={"x": 2, "y": 2},
            living_agent={"schema_version": "living-agent-v1",
                          "traits": {"generosity": generosity}},
        )
        entities = {"person-a": giver, "person-b": partner}
        _scores, context = _scores_for(giver, entities, _trade_sightings(partner))
        assert context["trade_receive_quantity"] == expected


def _support_knowledge(observer_id, subject_id, tick):
    fact = build_fact(
        kind=KIND_HELPED, observer_id=observer_id, subject_id=subject_id,
        counterparty_id=observer_id, interaction_id="ix-1",
        accepted_event_id=f"evt-{tick}-0-abc", accepted_event_tick=tick,
        interaction_kind="offer", recorded_tick=tick,
    )
    knowledge = empty_knowledge()
    knowledge["interaction_memory"] = {
        "version": "interaction-memory-v1", "facts": {fact["fact_id"]: fact},
    }
    return knowledge


def test_gate_excludes_non_traders_from_aid():
    receiver = _person("person-r", {"x": 3, "y": 2}, hunger=700, food=0,
                       storage={"x": 3, "y": 2})
    receiver["id"] = "person-r"
    giver = _person(
        "person-g", {"x": 2, "y": 2}, food=8, hunger=100,
        storage={"x": 2, "y": 2},
        knowledge=_support_knowledge("person-g", "person-r", TICK - 1),
    )
    giver["id"] = "person-g"
    entities = {"person-g": giver, "person-r": receiver}
    delta = _trade_sightings(receiver)

    # Ally by support, but a non-trader: the gate excludes them from aid.
    scores, context = _scores_for(giver, entities, delta)
    offer = scores["OFFER_TRADE"]
    assert offer["availability"] == 0.0
    assert offer["aid"] is False
    assert offer["gate_blocked"] == 1
    assert context["trade_partner_id"] is None

    # One remembered barter opens the gate: aid becomes available.
    culture = empty_culture_state()
    record_trade_outcome(
        culture, giver_id="person-r", receiver_id="person-q",
        give_field="inventory", give_quantity=2,
        receive_field="food_inventory", receive_quantity=2,
        tick=TICK - 2, source="witness", ref_id="sig-1", generosity=None,
    )
    giver["culture_state"] = culture
    scores, context = _scores_for(giver, entities, delta)
    offer = scores["OFFER_TRADE"]
    assert offer["availability"] == 1.0
    assert offer["aid"] is True
    assert context["trade_partner_id"] == "person-r"
    assert context["trade_aid"] is True
    assert context["trade_give_field"] == "food_inventory"
    assert context["trade_receive_field"] is None
    assert context["trade_give_quantity"] == AID_QUANTITY
    assert context["trade_receive_quantity"] == 0


def test_legacy_person_never_touches_culture():
    # No storage_location: the whole culture layer stays inert and the
    # proposal carries no culture_state (legacy scenarios byte-identical).
    entities = {
        "person-a": _person("person-a", {"x": 2, "y": 2}),
        "signal-t": _trade_signal("signal-t", {"x": 3, "y": 2}, "person-g", "person-r", TICK - 1),
    }
    output = _activate(entities, ["person-a"])
    update = output.proposals[0]["mutation"]["entity_updates"]["person-a"]
    assert "culture_state" not in update
    assert output.diagnostics["person-a"]["culture"]["enabled"] is False


# ---------------------------------------------------------------------------
# Two-run Tier A hash equality with culture active
# ---------------------------------------------------------------------------

def test_two_identical_runs_hash_match_with_culture_active():
    from scenarios.registry import get_scenario
    import scenarios  # noqa: F401  (registration side effects)
    from core.kernel import build_genesis, run_tick
    from core.constants import SCHEMA_VERSION
    from core.mutations import snapshot_for_hash

    scenario = get_scenario("surplus_forage")

    def _trace(run_id, ticks=40):
        seed = "culture-tier-a"
        lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
        _world, entities, genesis, _genesis_rejected, order_index = build_genesis(
            seed, scenario, lineage_key)
        rng = DeterministicRNG(seed)
        frame_hashes = []
        for tick in range(1, ticks + 1):
            accepted, _rejected, order_index, _diagnostics = run_tick(
                run_id, entities, _world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
            )
            frame_hashes.append(canonical_hash(snapshot_for_hash(entities, tick, lineage_key)))
        return entities, genesis, frame_hashes

    entities_a, events_a, hashes_a = _trace("culture-run-a")
    entities_b, events_b, hashes_b = _trace("culture-run-b")
    assert entities_a == entities_b
    assert hashes_a == hashes_b
    assert [canonical_hash(e) for e in events_a] == [canonical_hash(e) for e in events_b]
