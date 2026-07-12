"""Focused contract tests for the 5A6 read-only cognitive canvas projection."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from api.cognitive_projection import (
    MAX_GHOST_MARKERS, MAX_PROJECTED_TILES, MAX_ROUTE_POINTS,
    build_cognitive_projection,
)
from core.hashing import canonical_hash


def _world():
    terrain = [["grass"] * 12 for _ in range(12)]
    alice = {
        "id": "alice", "type": "person", "alive": True, "position": {"x": 1, "y": 1},
        "action": {"type": "travel", "status": "travelling", "travel_purpose": "TRAVEL_WATER",
                   "target_pos": {"x": 8, "y": 1}, "arrival_mode": "adjacent", "arrival_action": "DRINK",
                   "remaining_path": [{"x": x, "y": 1} for x in range(2, 90)]},
        "plan": {"goal": "SEEK_WATER"},
        "knowledge": {
            "schema_version": "knowledge-v2", "known_tiles": ["1,1", "2,1", "9,9"],
            "known_animals": {"animal-stale": {"position": {"x": 2, "y": 1}, "last_seen_tick": 4}},
            "known_people": {"bob": {"position": {"x": 9, "y": 9}, "last_seen_tick": 2}},
            "known_dangers": {},
            "facts": {"animal:animal-stale": {"first_known_tick": 5, "fact_type": "animal", "location": {"x": 2, "y": 1}}},
        },
    }
    bob = {"id": "bob", "type": "person", "alive": True, "position": {"x": 10, "y": 10}, "knowledge": {"known_tiles": ["10,10"]}}
    animal = {"id": "animal-stale", "type": "animal", "alive": True, "position": {"x": 10, "y": 1}}
    return terrain, {"alice": alice, "bob": bob, "animal-stale": animal}


def test_projection_is_observer_specific_and_bounded():
    terrain, entities = _world()
    alice = build_cognitive_projection(entities["alice"], entities, terrain, 5)
    bob = build_cognitive_projection(entities["bob"], entities, terrain, 5)
    assert alice["observer_id"] == "alice"
    assert {"x": 9, "y": 9} in alice["known_tiles"]
    assert {"x": 9, "y": 9} not in bob["known_tiles"]
    assert len(alice["known_tiles"]) <= MAX_PROJECTED_TILES
    assert len(alice["last_known_entities"]) <= MAX_GHOST_MARKERS
    assert len(alice["route"]["remaining_path"]) == MAX_ROUTE_POINTS
    assert alice["route"]["truncated"] is True


def test_projection_distinguishes_perception_retained_knowledge_and_stale_positions():
    terrain, entities = _world()
    projection = build_cognitive_projection(entities["alice"], entities, terrain, 5)
    assert {"x": 1, "y": 1} in projection["current_perception"]["tiles"]
    assert {"x": 9, "y": 9} in projection["known_tiles"]
    ghost = next(marker for marker in projection["last_known_entities"] if marker["id"] == "animal-stale")
    assert ghost["position"] == {"x": 2, "y": 1}
    assert ghost["position"] != entities["animal-stale"]["position"]
    assert ghost["label"] == "last-known animal"


def test_projection_is_read_only_and_does_not_change_canonical_inputs():
    terrain, entities = _world()
    before = canonical_hash({"terrain": terrain, "entities": entities})
    entities_before = copy.deepcopy(entities)
    build_cognitive_projection(entities["alice"], entities, terrain, 5)
    assert entities == entities_before
    assert canonical_hash({"terrain": terrain, "entities": entities}) == before


def test_dead_observer_retains_knowledge_without_new_perception():
    terrain, entities = _world()
    entities["alice"]["alive"] = False
    projection = build_cognitive_projection(entities["alice"], entities, terrain, 5)
    assert projection["current_perception"]["tiles"] == []
    assert projection["known_tiles"]
    assert projection["perception_radius"] == 0
