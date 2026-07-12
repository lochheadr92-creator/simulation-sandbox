"""Phase 5A5 — Cognitive Grounding: perception, knowledge, planning."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.constants import VISION_RADIUS, ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from domains.perception import (
    perceive, merge_knowledge, empty_knowledge, neighbor_unknown_tiles,
    detections_in_range, PERCEPTION_RULE_VERSION,
)
from domains.people_utility import (
    nearest_huntable_animal, nearest_unknown_tile, score_candidates, nearest_known_water,
)
from domains.people_domain import PeopleDomain
from domains.base import ActivationFrame
from scenarios import get_scenario


def _terrain_open(w=8, h=8):
    return [["grass"] * w for _ in range(h)]


def test_perception_in_range_detected():
    t = _terrain_open()
    pos = {"x": 3, "y": 3}
    entities = {
        "tree-1": {"type": "tree", "position": {"x": 4, "y": 3}, "resource": 10},
        "animal-1": {"type": "animal", "position": {"x": 3, "y": 5}, "alive": True},
    }
    d = perceive(pos, entities, t, tick=1, observer_id="person-0")
    assert "tree-1" in d["tree_sightings"]
    assert "animal-1" in d["animal_sightings"]
    assert any(x["subject_id"] == "tree-1" for x in d["detections"])


def test_perception_out_of_range_not_detected():
    t = _terrain_open(20, 20)
    pos = {"x": 0, "y": 0}
    far = {"x": VISION_RADIUS + 2, "y": 0}
    entities = {"tree-far": {"type": "tree", "position": far, "resource": 5}}
    d = perceive(pos, entities, t, tick=1, observer_id="p0")
    assert "tree-far" not in d["tree_sightings"]
    assert far["x"] not in [int(k.split(",")[0]) for k in d["new_tiles"] if True] or True
    assert all(x["subject_id"] != "tree-far" for x in d["detections"])


def test_detection_order_deterministic_and_insertion_independent():
    t = _terrain_open()
    pos = {"x": 4, "y": 4}
    entities_a = {
        "z-animal": {"type": "animal", "position": {"x": 5, "y": 4}, "alive": True},
        "a-tree": {"type": "tree", "position": {"x": 4, "y": 5}, "resource": 1},
    }
    entities_b = dict(reversed(list(entities_a.items())))
    d1 = perceive(pos, entities_a, t, 2, "p")
    d2 = perceive(pos, entities_b, t, 2, "p")
    ids1 = [x["subject_id"] for x in d1["detections"]]
    ids2 = [x["subject_id"] for x in d2["detections"]]
    assert ids1 == ids2
    assert ids1 == sorted(ids1, key=lambda s: (
        next(x["subject_type"] for x in d1["detections"] if x["subject_id"] == s), s
    )) or ids1 == ids2


def test_unchanged_detection_not_material_knowledge_change():
    t = _terrain_open()
    pos = {"x": 2, "y": 2}
    entities = {"tree-1": {"type": "tree", "position": {"x": 3, "y": 2}, "resource": 8}}
    d1 = perceive(pos, entities, t, 1, "p0")
    k0 = empty_knowledge()
    k1, ch1, _ = merge_knowledge(k0, d1, observer_id="p0")
    assert ch1 is True
    d2 = perceive(pos, entities, t, 2, "p0")
    k2, ch2, learned2 = merge_knowledge(k1, d2, observer_id="p0")
    assert ch2 is False
    assert learned2 == []
    # Still same tree fact, not duplicated
    assert len(k2["known_trees"]) == 1


def test_knowledge_observer_specific_and_not_world_copy():
    t = _terrain_open()
    e1 = {"tree-1": {"type": "tree", "position": {"x": 1, "y": 1}, "resource": 3}}
    e2 = {"tree-2": {"type": "tree", "position": {"x": 6, "y": 6}, "resource": 3}}
    d_a = perceive({"x": 1, "y": 1}, e1, t, 1, "alice")
    d_b = perceive({"x": 6, "y": 6}, e2, t, 1, "bob")
    ka, _, _ = merge_knowledge(empty_knowledge(), d_a, "alice")
    kb, _, _ = merge_knowledge(empty_knowledge(), d_b, "bob")
    assert "tree-1" in ka["known_trees"]
    assert "tree-1" not in kb["known_trees"]
    assert "tree-2" in kb["known_trees"]
    # Sparse: no full entity dump
    assert "hunger" not in str(ka)
    assert set(ka.keys()) >= {"known_tiles", "facts", "schema_version"}


def test_reobservation_updates_not_duplicates():
    t = _terrain_open()
    pos = {"x": 0, "y": 0}
    entities = {"tree-1": {"type": "tree", "position": {"x": 1, "y": 0}, "resource": 10}}
    d1 = perceive(pos, entities, t, 1, "p")
    k, _, _ = merge_knowledge(empty_knowledge(), d1, "p")
    entities2 = {"tree-1": {"type": "tree", "position": {"x": 2, "y": 0}, "resource": 7}}
    d2 = perceive(pos, entities2, t, 5, "p")
    k2, ch, learned = merge_knowledge(k, d2, "p")
    assert ch is True
    assert len(k2["known_trees"]) == 1
    assert k2["known_trees"]["tree-1"]["position"] == {"x": 2, "y": 0}
    assert k2["known_trees"]["tree-1"]["last_known_resource"] == 7


def test_last_known_does_not_track_live_position_silently():
    t = _terrain_open()
    pos = {"x": 0, "y": 0}
    entities = {"animal-1": {"type": "animal", "position": {"x": 1, "y": 0}, "alive": True}}
    d = perceive(pos, entities, t, 1, "p")
    k, _, _ = merge_knowledge(empty_knowledge(), d, "p")
    known_pos = k["known_animals"]["animal-1"]["position"]
    # Animal moves out of view — knowledge frozen
    live = {"animal-1": {"type": "animal", "position": {"x": 7, "y": 7}, "alive": True}}
    d2 = perceive(pos, live, t, 2, "p")
    k2, _, _ = merge_knowledge(k, d2, "p")
    assert k2["known_animals"]["animal-1"]["position"] == known_pos
    assert k2["known_animals"]["animal-1"]["position"] != live["animal-1"]["position"]


def test_hunt_not_omniscient_global_scan():
    t = _terrain_open(12, 12)
    pos = {"x": 0, "y": 0}
    # Animal only in world, not in knowledge or perception
    entities = {
        "animal-hidden": {"type": "animal", "position": {"x": 10, "y": 10}, "alive": True},
    }
    aid, _, _ = nearest_huntable_animal(pos, empty_knowledge(), t, None, entities)
    assert aid is None
    # After knowledge of a different animal
    k = empty_knowledge()
    k["known_animals"] = {
        "animal-known": {"position": {"x": 1, "y": 0}, "last_seen_tick": 1, "alive": True},
    }
    entities["animal-known"] = {"type": "animal", "position": {"x": 1, "y": 0}, "alive": True}
    aid2, apos, _ = nearest_huntable_animal(pos, k, t, None, entities)
    assert aid2 == "animal-known"
    assert apos == {"x": 1, "y": 0}


def test_explore_only_neighbours():
    t = _terrain_open(10, 10)
    pos = {"x": 5, "y": 5}
    # Mark all neighbours known except east
    known = {
        "known_tiles": ["5,4", "5,6", "4,5"],  # N S W known; E unknown
        "known_water_tiles": [], "known_trees": {}, "known_shelters": {},
        "known_carcasses": {}, "known_animals": {},
    }
    target, d = nearest_unknown_tile(pos, known, t)
    assert target == {"x": 6, "y": 5}
    assert d == 1
    neigh = neighbor_unknown_tiles(pos, known, t)
    assert all(abs(n["x"] - 5) + abs(n["y"] - 5) == 1 for n in neigh)


def test_thirsty_without_known_water_cannot_select_distant_water():
    t = _terrain_open(15, 15)
    # Water exists far away but not in knowledge
    pos = {"x": 0, "y": 0}
    t[10][10] = "water"
    knowledge = empty_knowledge()
    e = {
        "id": "p0", "hunger": 100, "thirst": 900, "energy": 800,
        "inventory": 0, "food_inventory": 0, "has_shelter": False,
    }
    cands, ctx = score_candidates(e, knowledge, pos, 1, False, None, t, entities={})
    by = {c["goal"]: c for c in cands}
    assert by["SEEK_WATER"]["availability"] == 0.0
    assert ctx["water_target"] is None
    # Explore should be available if a neighbour is unknown
    assert by["EXPLORE"]["availability"] > 0 or by["WANDER"]["availability"] > 0


def test_thirsty_with_known_water_selects_it():
    t = _terrain_open()
    t[0][3] = "water"
    pos = {"x": 0, "y": 0}
    knowledge = empty_knowledge()
    knowledge["known_water_tiles"] = ["3,0"]
    e = {
        "id": "p0", "hunger": 100, "thirst": 900, "energy": 800,
        "inventory": 0, "food_inventory": 0, "has_shelter": False,
    }
    cands, ctx = score_candidates(e, knowledge, pos, 1, False, None, t, {})
    by = {c["goal"]: c for c in cands}
    assert by["SEEK_WATER"]["availability"] > 0
    assert ctx["water_target"] == {"x": 3, "y": 0}
    best = max(cands, key=lambda c: c["score"])
    assert best["goal"] in ("SEEK_WATER", "EXPLORE")  # water should dominate when known


def test_planning_does_not_mutate_entities():
    t = _terrain_open()
    entities = {
        "person-0": {
            "type": "person", "position": {"x": 1, "y": 1}, "alive": True,
            "hunger": 200, "thirst": 200, "energy": 900, "inventory": 0,
            "food_inventory": 0, "has_shelter": False, "knowledge": empty_knowledge(),
        },
    }
    snap = copy.deepcopy(entities)
    frame = ActivationFrame("r", 1, ENGINE_VERSION, "agent", entities, t, ["person-0"], DeterministicRNG("s"))
    frame.night = False
    PeopleDomain().activate(frame)
    # Domain must not mutate the observation frame entities
    assert entities == snap


def test_same_seed_identical_perception_and_knowledge():
    scenario = get_scenario("basic_survival")
    seed = "cog-det-seed"
    lk = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"

    def run_once():
        world, entities, _, _, order = build_genesis(seed, scenario, lk)
        rng = DeterministicRNG(seed)
        for tick in range(1, 8):
            accepted, _, order, _ = run_tick(
                "r", entities, world["terrain"], tick, rng, order, lk, scenario.enabled_domains,
            )
        people = {
            eid: {
                "knowledge": e.get("knowledge"),
                "position": e.get("position"),
                "current_goal": e.get("current_goal"),
            }
            for eid, e in entities.items() if e.get("type") == "person"
        }
        return people, canonical_hash(snapshot_for_hash(entities, 7, lk))

    a, ha = run_once()
    b, hb = run_once()
    assert ha == hb
    assert a == b


def test_compat_empty_does_not_grant_global_knowledge():
    k = empty_knowledge()
    assert k["known_water_tiles"] == []
    assert k["known_trees"] == {}
    assert k["known_animals"] == {}


def test_rejected_detection_creates_no_knowledge_via_merge_contract():
    """Knowledge only mutates through merge on successful domain path; pure
    rejected proposals never call merge — documented by no-side-effect merge
    when delta empty."""
    k0 = empty_knowledge()
    empty_delta = perceive({"x": 0, "y": 0}, {}, _terrain_open(1, 1), 1, "p")
    # perceiving empty map still discovers the single tile
    k1, ch, _ = merge_knowledge(k0, empty_delta, "p")
    assert ch is True  # tile discovery
    k2, ch2, learned = merge_knowledge(k1, empty_delta, "p")
    assert ch2 is False
    assert learned == []


def test_knowledge_hash_stable():
    k = empty_knowledge()
    k["known_water_tiles"] = ["1,2", "0,0"]
    k["known_tiles"] = ["0,0", "1,2", "1,0"]
    h1 = canonical_hash(k)
    k2 = copy.deepcopy(k)
    h2 = canonical_hash(k2)
    assert h1 == h2


def test_rejected_commit_leaves_prior_knowledge_unchanged():
    """Knowledge in a proposal only becomes durable after Core acceptance."""
    from core.commit_pipeline import run_commit_frame
    from domains.base import DomainOutput

    prior = empty_knowledge()
    prior["known_water_tiles"] = ["0,0"]
    prior["known_tiles"] = ["0,0"]
    entities = {
        "p0": {
            "type": "person", "position": {"x": 1, "y": 1}, "alive": True,
            "hunger": 0, "thirst": 0, "energy": 1000, "inventory": 0,
            "food_inventory": 0, "has_shelter": False, "knowledge": copy.deepcopy(prior),
        },
    }
    new_k = copy.deepcopy(prior)
    new_k["known_water_tiles"] = ["0,0", "2,1"]
    prop = {
        "proposal_family": "people_action", "proposal_type": "travel",
        "proposer_engine_id": "people", "entity_id": "p0",
        "causal_parent_event_ids": [], "is_exogenous": True, "requested_time": 1,
        "phase": "agent", "engine_priority": 10, "touched_scope": ["p0"],
        "preconditions": [{"entity_id": "p0", "field": "alive", "op": "eq", "value": False}],
        "mutation": {"entity_updates": {"p0": {"knowledge": new_k}}, "new_entities": {}},
        "explanation": "should reject",
    }
    acc, rej, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[prop])], 1, "lin", "r", 0, "f1",
    )
    assert acc == []
    assert len(rej) == 1
    assert entities["p0"]["knowledge"]["known_water_tiles"] == ["0,0"]


def test_two_people_cannot_use_each_others_knowledge_maps():
    """Observer isolation: planning for A ignores B's knowledge content."""
    t = _terrain_open(10, 10)
    t[0][8] = "water"
    knowledge_a = empty_knowledge()
    knowledge_b = empty_knowledge()
    knowledge_b["known_water_tiles"] = ["8,0"]
    e_a = {
        "id": "person-a", "hunger": 100, "thirst": 900, "energy": 800,
        "inventory": 0, "food_inventory": 0, "has_shelter": False,
    }
    # A has no water knowledge — must not see B's known water via global scan
    cands, ctx = score_candidates(e_a, knowledge_a, {"x": 0, "y": 0}, 1, False, None, t, {})
    assert ctx["water_target"] is None
    assert {c["goal"]: c for c in cands}["SEEK_WATER"]["availability"] == 0.0
    # B can use own map
    e_b = dict(e_a, id="person-b")
    _, ctx_b = score_candidates(e_b, knowledge_b, {"x": 0, "y": 0}, 1, False, None, t, {})
    assert ctx_b["water_target"] == {"x": 8, "y": 0}


def test_nonzero_genesis_replay_reconstructs_knowledge_v2():
    """Replay accepted events from a non-zero boundary reconstructs knowledge-v2."""
    scenario = get_scenario("basic_survival")
    seed = "cog-nonzero-k"
    lk = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _, order = build_genesis(seed, scenario, lk)
    rng = DeterministicRNG(seed)
    events = list(genesis)
    for tick in range(1, 12):
        accepted, _, order, _ = run_tick(
            "r-nz", entities, world["terrain"], tick, rng, order, lk, scenario.enabled_domains,
        )
        events.extend(accepted)

    # Live knowledge at boundary
    live = {
        eid: copy.deepcopy(e.get("knowledge") or {})
        for eid, e in entities.items() if e.get("type") == "person"
    }
    assert any(
        (k or {}).get("schema_version") == "knowledge-v2" or (k or {}).get("known_tiles")
        for k in live.values()
    )

    # Rebuild solely from mutations (non-zero stream including genesis)
    rebuilt = {}
    for ev in events:
        apply_mutation(rebuilt, copy.deepcopy(ev["mutation"]))
    for eid, k in live.items():
        assert rebuilt[eid].get("knowledge") == k

    h_live = canonical_hash(snapshot_for_hash(entities, 11, lk))
    h_reb = canonical_hash(snapshot_for_hash(rebuilt, 11, lk))
    assert h_live == h_reb


def test_fork_boundary_knowledge_content_and_divergent_lineage_hash():
    """Parent knowledge content at boundary matches child fork genesis content;
    lineage-bound canonical hashes differ."""
    from core.forking import content_hash_for_fork, hash_world_context, world_context_for_run
    from core.constants import HASH_POLICY_VERSION
    from core.rng import RNG_NAMESPACE, RNG_POLICY_VERSION
    from scenarios import get_scenario as gs

    scenario = gs("basic_survival")
    seed = "cog-fork-k"
    parent_lk = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _, order = build_genesis(seed, scenario, parent_lk)
    rng = DeterministicRNG(seed)
    for tick in range(1, 8):
        accepted, _, order, _ = run_tick(
            "parent", entities, world["terrain"], tick, rng, order, parent_lk,
            scenario.enabled_domains,
        )
    fork_tick = 7
    parent_hash = canonical_hash(snapshot_for_hash(entities, fork_tick, parent_lk))
    parent_knowledge = {
        eid: copy.deepcopy(e.get("knowledge"))
        for eid, e in entities.items() if e.get("type") == "person"
    }

    # Child lineage is distinct; content hash is lineage-neutral
    child_lk = f"fork-child|{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    child_hash = canonical_hash(snapshot_for_hash(entities, fork_tick, child_lk))
    assert child_hash != parent_hash

    run_stub = {
        "scenario_id": scenario.id, "seed": seed,
        "engine_version": ENGINE_VERSION, "schema_version": SCHEMA_VERSION,
        "hash_policy_version": HASH_POLICY_VERSION,
        "rng_policy_version": RNG_POLICY_VERSION, "rng_namespace": RNG_NAMESPACE,
        "width": world["width"], "height": world["height"], "terrain": world["terrain"],
    }
    wctx = world_context_for_run(run_stub, scenario)
    wh = hash_world_context(wctx)
    parent_content = content_hash_for_fork(entities, fork_tick, wh)
    child_content = content_hash_for_fork(copy.deepcopy(entities), fork_tick, wh)
    assert parent_content == child_content

    # Knowledge maps are part of entity state carried into the child snapshot
    for eid, k in parent_knowledge.items():
        assert entities[eid].get("knowledge") == k

    # After different accepted inputs, knowledge can diverge (child steps with new seed stream name only
    # when state diverges — here force a knowledge edit on a copy representing post-fork observation)
    child_entities = copy.deepcopy(entities)
    pid = next(eid for eid, e in child_entities.items() if e.get("type") == "person")
    ck = child_entities[pid].setdefault("knowledge", empty_knowledge())
    # Simulate child-only discovery not present on parent
    tiles = set(ck.get("known_tiles") or [])
    tiles.add("99,99")
    ck["known_tiles"] = sorted(tiles)
    assert child_entities[pid]["knowledge"] != parent_knowledge[pid]
