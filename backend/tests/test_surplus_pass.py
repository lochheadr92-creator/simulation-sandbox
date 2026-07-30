"""Surplus Pass — Tier A: deterministic pipeline contracts (SURPLUS_PASS.md).

Every test drives real domain activation and/or the real commit pipeline
(run_commit_frame). No harness runs, no wall-clock assertions. The four new
proposal types (gather_excess / store / retrieve / offer_trade) must generate,
validate and commit through the standard Core path, with stable reason codes
on the rejection paths, byte-exact replay, and two-run hash equality.
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
    ENGINE_VERSION,
    GATHER_TICKS,
    GATHER_YIELD,
    RETRIEVE_MAX_QUANTITY,
    SURPLUS_KEEP_FOOD,
    SURPLUS_KEEP_WOOD,
    TRADE_CONTRACT_VERSION,
    TRADE_MIN_RETAIN,
    TRADE_QUANTITY,
)
from core.hashing import canonical_hash
from core.mutations import apply_mutation
from core.rng import DeterministicRNG
from domains.base import ActivationFrame, DomainOutput
from domains.people_domain import PeopleDomain
from domains.perception import empty_knowledge

TICK = 5
LINEAGE = "surplus-pass-lineage"


def _person(entity_id, position, *, hunger=100, food=0, inventory=0, capacity=30,
            action=None, stored=None, storage=None, last_event_id=None, plan_goal=None):
    action = action or {"type": "idle", "status": "completed", "ticks_spent": 0}
    if plan_goal is not None:
        # Active plan so compat_plan mints plan_id/goal_id: the living-action
        # validator requires causal state on every committed action.
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
        "has_shelter": False, "knowledge": empty_knowledge(),
        "carried_item_ids": [],
        "action": action,
        "plan": plan,
        "paused": None,
        "last_event_id": last_event_id or f"evt-genesis-{entity_id}",
    }
    if storage is not None:
        person["storage_location"] = dict(storage)
        person["stored_resources"] = dict(stored or {"wood": 0, "food": 0})
    return person


def _tree(tree_id="tree-000", position=None, resource=60):
    return {
        "type": "tree", "position": dict(position or {"x": 4, "y": 4}),
        "resource": resource, "max_resource": max(resource, 60), "alive": True,
        "resource_kind": "wood", "quality": 500,
        "regeneration_rule": "ecology_interval", "claimed_tick": None,
    }


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
        DeterministicRNG("surplus-pass"),
    )
    frame.night = False
    return PeopleDomain().activate(frame)


def _commit(entities, proposals, tick=TICK):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))], tick, LINEAGE, "run",
        0, f"frame-{tick}",
    )


# ---------------------------------------------------------------------------
# gather_excess
# ---------------------------------------------------------------------------

def test_gather_excess_commits_with_capacity_bound_and_ownership_stamp():
    entities = {
        "person-a": _person(
            "person-a", {"x": 4, "y": 4}, inventory=25, capacity=30,
            storage={"x": 1, "y": 1},
            action=_action(
                "gather_excess", target_entity_id="tree-000",
                target_pos={"x": 4, "y": 4}, ticks_required=GATHER_TICKS,
                ticks_spent=GATHER_TICKS - 1, target_kind="tree",
            ),
            plan_goal="GATHER_EXCESS",
        ),
        "tree-000": _tree(),
    }
    proposals = _activate(entities, ["person-a"]).proposals
    proposal = proposals[0]
    assert proposal["proposal_type"] == "gather_excess"
    assert proposal["living_action"]["action_type"] == "gather"

    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    assert len(accepted) == 1
    # Room is 30 - 25 = 5, below GATHER_YIELD: the capacity bound bites.
    assert entities["person-a"]["inventory"] == 30
    assert entities["person-a"]["carried_resources"] == {"wood": 30, "food": 0}
    assert entities["tree-000"]["resource"] == 60 - 5
    assert entities["tree-000"]["claimed_tick"] == TICK
    # resource_ownership stamps the gatherer of record.
    assert entities["tree-000"]["resource_ownership"] == "person-a"


def test_gather_excess_full_carry_fails_without_mutation():
    entities = {
        "person-a": _person(
            "person-a", {"x": 4, "y": 4}, inventory=30, capacity=30,
            storage={"x": 1, "y": 1},
            action=_action(
                "gather_excess", target_entity_id="tree-000",
                target_pos={"x": 4, "y": 4}, ticks_required=GATHER_TICKS,
                ticks_spent=GATHER_TICKS - 1, target_kind="tree",
            ),
            plan_goal="GATHER_EXCESS",
        ),
        "tree-000": _tree(),
    }
    before = copy.deepcopy(entities)
    proposal = _activate(entities, ["person-a"]).proposals[0]
    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    assert len(accepted) == 1
    # The action records its failure; the tree is untouched.
    assert entities["tree-000"]["resource"] == before["tree-000"]["resource"]
    assert entities["tree-000"].get("resource_ownership") is None
    assert entities["person-a"]["inventory"] == 30
    assert entities["person-a"]["action"]["status"] == "failed"


def test_legacy_gather_has_no_ownership_stamp_and_stays_unbounded():
    entities = {
        "person-a": _person(
            "person-a", {"x": 4, "y": 4}, inventory=25, capacity=30,
            action=_action(
                "gather", target_entity_id="tree-000",
                target_pos={"x": 4, "y": 4}, ticks_required=GATHER_TICKS,
                ticks_spent=GATHER_TICKS - 1, target_kind="tree",
            ),
            plan_goal="GATHER_SURPLUS",
        ),
        "tree-000": _tree(),
    }
    proposal = _activate(entities, ["person-a"]).proposals[0]
    assert proposal["proposal_type"] == "gather"
    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    # No storage_location: legacy semantics — full yield, no capacity bound,
    # no ownership stamp.
    assert entities["person-a"]["inventory"] == 25 + GATHER_YIELD
    assert entities["tree-000"].get("resource_ownership") is None
    assert "stored_resources" not in entities["person-a"]


# ---------------------------------------------------------------------------
# store / retrieve
# ---------------------------------------------------------------------------

def test_store_moves_surplus_above_keep_thresholds():
    entities = {
        "person-a": _person(
            "person-a", {"x": 1, "y": 1}, inventory=10, food=6,
            storage={"x": 1, "y": 1}, stored={"wood": 0, "food": 0},
            action=_action("store"),
            plan_goal="STORE",
        ),
    }
    proposal = _activate(entities, ["person-a"]).proposals[0]
    assert proposal["proposal_type"] == "store"
    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    person = entities["person-a"]
    assert person["inventory"] == SURPLUS_KEEP_WOOD
    assert person["food_inventory"] == SURPLUS_KEEP_FOOD
    assert person["stored_resources"] == {
        "wood": 10 - SURPLUS_KEEP_WOOD, "food": 6 - SURPLUS_KEEP_FOOD,
    }
    assert person["carried_resources"] == {"wood": SURPLUS_KEEP_WOOD, "food": SURPLUS_KEEP_FOOD}


def test_store_away_from_storage_fails_without_moving_resources():
    entities = {
        "person-a": _person(
            "person-a", {"x": 5, "y": 5}, inventory=10,
            storage={"x": 1, "y": 1}, stored={"wood": 0, "food": 0},
            action=_action("store"),
            plan_goal="STORE",
        ),
    }
    proposal = _activate(entities, ["person-a"]).proposals[0]
    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    person = entities["person-a"]
    assert person["inventory"] == 10
    assert person["stored_resources"] == {"wood": 0, "food": 0}
    assert person["action"]["status"] == "failed"


def test_retrieve_pulls_stored_food_within_capacity():
    entities = {
        "person-a": _person(
            "person-a", {"x": 1, "y": 1}, hunger=700, food=0, inventory=0,
            storage={"x": 1, "y": 1}, stored={"wood": 4, "food": 5},
            action=_action("retrieve"),
            plan_goal="RETRIEVE",
        ),
    }
    proposal = _activate(entities, ["person-a"]).proposals[0]
    assert proposal["proposal_type"] == "retrieve"
    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    person = entities["person-a"]
    assert person["food_inventory"] == RETRIEVE_MAX_QUANTITY
    assert person["stored_resources"] == {"wood": 4, "food": 5 - RETRIEVE_MAX_QUANTITY}
    assert person["carried_resources"] == {"wood": 0, "food": RETRIEVE_MAX_QUANTITY}


def test_store_retrieve_roundtrip_is_replay_safe():
    entities = {
        "person-a": _person(
            "person-a", {"x": 1, "y": 1}, inventory=6, food=2,
            storage={"x": 1, "y": 1}, stored={"wood": 0, "food": 0},
            action=_action("store"),
            plan_goal="STORE",
        ),
    }
    proposal = _activate(entities, ["person-a"]).proposals[0]
    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []

    replayed = {
        "person-a": _person(
            "person-a", {"x": 1, "y": 1}, inventory=6, food=2,
            storage={"x": 1, "y": 1}, stored={"wood": 0, "food": 0},
            action=_action("store"),
            plan_goal="STORE",
        ),
    }
    apply_mutation(replayed, copy.deepcopy(accepted[0]["mutation"]))
    assert replayed == entities


# ---------------------------------------------------------------------------
# offer_trade
# ---------------------------------------------------------------------------

def _trade_fixture():
    return {
        # Wood-rich, food-scarce giver; food-rich, wood-scarce receiver.
        "person-g": _person(
            "person-g", {"x": 2, "y": 2}, inventory=6, food=1,
            storage={"x": 2, "y": 2}, stored={"wood": 0, "food": 0},
            action=_action(
                "offer_trade", target_entity_id="person-r",
                give_field="inventory", receive_field="food_inventory",
                give_quantity=TRADE_QUANTITY, receive_quantity=TRADE_QUANTITY,
            ),
            plan_goal="OFFER_TRADE",
        ),
        "person-r": _person(
            "person-r", {"x": 3, "y": 2}, inventory=1, food=6,
            storage={"x": 3, "y": 2}, stored={"wood": 0, "food": 0},
        ),
    }


def test_offer_trade_commits_atomic_swap():
    entities = _trade_fixture()
    proposal = _activate(entities, ["person-g"]).proposals[0]
    assert proposal["proposal_type"] == "offer_trade"
    assert proposal["trade"]["contract_version"] == TRADE_CONTRACT_VERSION

    accepted, rejected, _ = _commit(entities, [proposal])
    assert rejected == []
    assert len(accepted) == 1
    event = accepted[0]
    assert event["trade"]["giver_id"] == "person-g"
    # Evidence-signal entities ride along in scope (established people-domain
    # machinery); the two trading parties must both be present.
    assert {"person-g", "person-r"} <= set(event["touched_scope"])
    giver, receiver = entities["person-g"], entities["person-r"]
    assert giver["inventory"] == 6 - TRADE_QUANTITY
    assert giver["food_inventory"] == 1 + TRADE_QUANTITY
    assert receiver["food_inventory"] == 6 - TRADE_QUANTITY
    assert receiver["inventory"] == 1 + TRADE_QUANTITY
    # Equal-quantity swap: carry totals invariant, mirrors aligned.
    assert giver["inventory"] + giver["food_inventory"] == 7
    assert receiver["inventory"] + receiver["food_inventory"] == 7
    assert giver["carried_resources"] == {"wood": giver["inventory"], "food": giver["food_inventory"]}
    assert receiver["carried_resources"] == {"wood": receiver["inventory"], "food": receiver["food_inventory"]}


def _trade_proposal(entities, *, mutation=None, trade=None, preconditions=None):
    giver = entities["person-g"]
    receiver = entities["person-r"]
    trade = trade or {
        "contract_version": TRADE_CONTRACT_VERSION,
        "giver_id": "person-g", "receiver_id": "person-r",
        "give_field": "inventory", "give_quantity": TRADE_QUANTITY,
        "receive_field": "food_inventory", "receive_quantity": TRADE_QUANTITY,
    }
    mutation = mutation or {
        "entity_updates": {
            "person-g": {
                "inventory": giver["inventory"] - TRADE_QUANTITY,
                "food_inventory": giver["food_inventory"] + TRADE_QUANTITY,
                "carried_resources": {
                    "wood": giver["inventory"] - TRADE_QUANTITY,
                    "food": giver["food_inventory"] + TRADE_QUANTITY,
                },
            },
            "person-r": {
                "inventory": receiver["inventory"] + TRADE_QUANTITY,
                "food_inventory": receiver["food_inventory"] - TRADE_QUANTITY,
                "carried_resources": {
                    "wood": receiver["inventory"] + TRADE_QUANTITY,
                    "food": receiver["food_inventory"] - TRADE_QUANTITY,
                },
            },
        },
        "new_entities": {},
    }
    preconditions = preconditions or [
        {"entity_id": "person-g", "field": "alive", "op": "eq", "value": True},
        {"entity_id": "person-g", "field": "inventory", "op": "gte",
         "value": TRADE_QUANTITY + TRADE_MIN_RETAIN},
        {"entity_id": "person-r", "field": "alive", "op": "eq", "value": True},
        # Culture Pass (S5): receiver post-trade retain joined the required set.
        {"entity_id": "person-r", "field": "food_inventory", "op": "gte",
         "value": TRADE_QUANTITY + TRADE_MIN_RETAIN},
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
        "trade": trade, "explanation": "test trade",
    }


def test_trade_insufficient_surplus_rejects_without_mutation():
    entities = _trade_fixture()
    entities["person-g"]["inventory"] = 2  # below TRADE_MIN_SURPLUS
    before = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(entities, [_trade_proposal(entities)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "trade.insufficient_surplus"
    assert entities == before


def test_trade_out_of_range_rejects_without_mutation():
    entities = _trade_fixture()
    entities["person-r"]["position"] = {"x": 7, "y": 7}
    before = copy.deepcopy(entities)
    proposal = _trade_proposal(
        entities,
        preconditions=[
            {"entity_id": "person-g", "field": "alive", "op": "eq", "value": True},
            {"entity_id": "person-g", "field": "inventory", "op": "gte",
             "value": TRADE_QUANTITY + TRADE_MIN_RETAIN},
            {"entity_id": "person-r", "field": "alive", "op": "eq", "value": True},
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
    assert rejected[0]["reason_code"] == "trade.out_of_range"
    assert entities == before


def test_trade_invalid_mutation_rejects_without_mutation():
    entities = _trade_fixture()
    before = copy.deepcopy(entities)
    partial = {
        "entity_updates": {
            "person-g": {"inventory": entities["person-g"]["inventory"] - TRADE_QUANTITY},
        },
        "new_entities": {},
    }
    accepted, rejected, _ = _commit(entities, [_trade_proposal(entities, mutation=partial)])
    assert accepted == []
    assert rejected[0]["reason_code"] == "trade.invalid_mutation"
    assert entities == before


def test_trade_missing_preconditions_reject_without_mutation():
    entities = _trade_fixture()
    before = copy.deepcopy(entities)
    proposal = _trade_proposal(entities, preconditions=[
        {"entity_id": "person-g", "field": "alive", "op": "eq", "value": True},
    ])
    accepted, rejected, _ = _commit(entities, [proposal])
    assert accepted == []
    assert rejected[0]["reason_code"] == "trade.invalid_preconditions"
    assert entities == before


def test_duplicate_trade_is_deterministic_and_replay_safe():
    first = _trade_fixture()
    proposal = _trade_proposal(first)
    accepted, rejected, _ = _commit(first, [proposal, copy.deepcopy(proposal)])
    assert len(accepted) == 1
    assert len(rejected) == 1
    # The second copy is re-derived against post-first-trade state: the stale
    # mutation no longer matches (or its CAS pins fail at revalidation).
    assert rejected[0]["reason_code"] in (
        "trade.invalid_mutation", "trade.insufficient_surplus", "precondition.failed",
    )

    replayed = _trade_fixture()
    apply_mutation(replayed, copy.deepcopy(accepted[0]["mutation"]))
    assert replayed == first

    second = _trade_fixture()
    second_accepted, second_rejected, _ = _commit(second, [_trade_proposal(second)])
    assert second_rejected == []
    assert canonical_hash(accepted[0]) == canonical_hash(second_accepted[0])
    assert second == first


# ---------------------------------------------------------------------------
# Utility shapes (spec: relative ordering, not absolute scores)
# ---------------------------------------------------------------------------

def _scores_for(person, entities):
    from domains.people_utility import score_candidates
    knowledge = person.get("knowledge") or empty_knowledge()
    candidates, _context = score_candidates(
        {**person, "id": "person-a"}, knowledge, person["position"], TICK, False,
        person["action"], _terrain(), entities=entities, perception_delta=None,
    )
    return {c["goal"]: c for c in candidates}


def test_gather_excess_below_eat_when_hungry_but_nonzero_when_satiated():
    tree_knowledge = empty_knowledge()
    tree_knowledge["known_trees"] = {
        "tree-000": {"position": {"x": 4, "y": 4}, "last_known_resource": 60},
    }
    entities = {"person-a": None, "tree-000": _tree()}  # placeholder, replaced below

    hungry = _person("person-a", {"x": 4, "y": 4}, hunger=700, storage={"x": 1, "y": 1})
    hungry["knowledge"] = tree_knowledge
    entities["person-a"] = hungry
    scores = _scores_for(hungry, entities)
    assert scores["SEEK_FOOD"]["score"] > scores["GATHER_EXCESS"]["score"]
    assert scores["GATHER_EXCESS"]["availability"] == 0.0  # gated off when hungry

    satiated = _person("person-a", {"x": 4, "y": 4}, hunger=100, storage={"x": 1, "y": 1})
    satiated["knowledge"] = tree_knowledge
    entities["person-a"] = satiated
    scores = _scores_for(satiated, entities)
    assert scores["GATHER_EXCESS"]["availability"] > 0.0
    assert scores["GATHER_EXCESS"]["score"] > scores["WANDER"]["score"]


def test_store_utility_rises_with_carry_load():
    light = _person("person-a", {"x": 2, "y": 2}, inventory=10, food=2,
                    storage={"x": 1, "y": 1})
    heavy = _person("person-a", {"x": 2, "y": 2}, inventory=25, food=3,
                    storage={"x": 1, "y": 1})
    entities = {"person-a": light}
    light_score = _scores_for(light, entities)["STORE"]["score"]
    entities["person-a"] = heavy
    heavy_score = _scores_for(heavy, entities)["STORE"]["score"]
    assert heavy_score > light_score
    assert _scores_for(heavy, entities)["STORE"]["availability"] == 1.0


def test_retrieve_utility_rises_with_hunger():
    base = dict(inventory=0, food=0, storage={"x": 1, "y": 1},
                stored={"wood": 0, "food": 5})
    calm = _person("person-a", {"x": 1, "y": 1}, hunger=560, **base)
    urgent = _person("person-a", {"x": 1, "y": 1}, hunger=800, **base)
    entities = {"person-a": calm}
    calm_score = _scores_for(calm, entities)["RETRIEVE"]["score"]
    entities["person-a"] = urgent
    urgent_scores = _scores_for(urgent, entities)
    assert urgent_scores["RETRIEVE"]["score"] > calm_score
    assert urgent_scores["RETRIEVE"]["availability"] == 1.0


def test_trade_utility_requires_complementary_partner_in_range():
    giver = _person("person-a", {"x": 2, "y": 2}, inventory=6, food=1,
                    storage={"x": 2, "y": 2})
    partner = _person("person-b", {"x": 3, "y": 2}, inventory=1, food=6,
                      storage={"x": 3, "y": 2})
    entities = {"person-a": giver, "person-b": partner}
    delta = {"person_sightings": {"person-b": {"position": dict(partner["position"])}}}
    from domains.people_utility import score_candidates
    candidates, context = score_candidates(
        {**giver, "id": "person-a"}, giver["knowledge"], giver["position"],
        TICK, False, giver["action"], _terrain(),
        entities=entities, perception_delta=delta,
    )
    by_goal = {c["goal"]: c for c in candidates}
    assert by_goal["OFFER_TRADE"]["availability"] == 1.0
    assert context["trade_partner_id"] == "person-b"
    assert context["trade_give_field"] == "inventory"
    assert context["trade_receive_field"] == "food_inventory"

    # Same surplus profile on both sides: not complementary, no candidate.
    twin = _person("person-b", {"x": 3, "y": 2}, inventory=6, food=1,
                   storage={"x": 3, "y": 2})
    entities["person-b"] = twin
    candidates, context = score_candidates(
        {**giver, "id": "person-a"}, giver["knowledge"], giver["position"],
        TICK, False, giver["action"], _terrain(),
        entities=entities, perception_delta=delta,
    )
    assert {c["goal"]: c for c in candidates}["OFFER_TRADE"]["availability"] == 0.0
    assert context["trade_partner_id"] is None


# ---------------------------------------------------------------------------
# Two-run Tier A hash equality (deterministic RNG seeded by tick + agent id)
# ---------------------------------------------------------------------------

def test_two_identical_runs_hash_match_and_replay_holds():
    from scenarios.registry import get_scenario
    import scenarios  # noqa: F401  (registration side effects)
    from core.kernel import build_genesis, run_tick
    from core.constants import SCHEMA_VERSION
    from core.mutations import snapshot_for_hash

    scenario = get_scenario("surplus_forage")

    def _trace(run_id, ticks=40):
        seed = "surplus-tier-a"
        lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
        _world, entities, genesis, _genesis_rejected, order_index = build_genesis(
            seed, scenario, lineage_key)
        genesis_entities = copy.deepcopy(entities)
        rng = DeterministicRNG(seed)
        frame_hashes = []
        for tick in range(1, ticks + 1):
            accepted, _rejected, order_index, _diagnostics = run_tick(
                run_id, entities, _world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
            )
            frame_hashes.append(canonical_hash(snapshot_for_hash(entities, tick, lineage_key)))
        return genesis_entities, entities, genesis, frame_hashes

    genesis_a, entities_a, events_a, hashes_a = _trace("surplus-run-a")
    genesis_b, entities_b, events_b, hashes_b = _trace("surplus-run-b")
    assert entities_a == entities_b
    assert hashes_a == hashes_b
    assert [canonical_hash(e) for e in events_a] == [canonical_hash(e) for e in events_b]
    # Genesis minted the Tier A surplus state on every person.
    persons = [e for e in genesis_a.values() if e.get("type") == "person"]
    assert len(persons) == 20
    for person in persons:
        storage = person["storage_location"]
        assert storage == person["position"]  # home tile defaults to spawn tile
        assert isinstance(storage, dict) and set(storage) == {"x", "y"}
        assert person["stored_resources"] == {"wood": 0, "food": 0}
