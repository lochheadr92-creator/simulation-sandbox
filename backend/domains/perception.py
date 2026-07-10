"""Perception & Knowledge (Phase 2).

Doctrine constraint honoured here: actors only know what they have
genuinely discovered. Each activation, an actor perceives everything within
its vision radius and MERGES it into its own persistent `knowledge` state.
Knowledge is canonical (event-sourced, replayable) - it flows through the
same generic entity_updates envelope as everything else, so Core needs no
changes at all.

Decision logic (people_utility.py) must read FROM `knowledge`, never do an
omniscient global search - that is what makes "prefer known water over
wandering" and "unknown areas require exploration" genuinely emerge.
"""
from core.geometry import manhattan
from core.constants import VISION_RADIUS


def empty_knowledge() -> dict:
    return {"known_tiles": [], "known_water_tiles": [], "known_trees": {}, "known_shelters": {}}


def perceive(pos: dict, entities: dict, terrain: list, tick: int, radius: int = VISION_RADIUS) -> dict:
    """Returns a knowledge DELTA (not yet merged) visible from `pos` right now."""
    height = len(terrain)
    width = len(terrain[0]) if height else 0
    new_tiles = []
    new_water = []

    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if abs(dx) + abs(dy) > radius:
                continue
            x, y = pos["x"] + dx, pos["y"] + dy
            if 0 <= x < width and 0 <= y < height:
                key = f"{x},{y}"
                new_tiles.append(key)
                if terrain[y][x] == "water":
                    new_water.append(key)

    tree_sightings = {}
    shelter_sightings = {}
    for eid, e in entities.items():
        if e["type"] == "tree" and manhattan(pos, e["position"]) <= radius:
            tree_sightings[eid] = {
                "last_seen_tick": tick, "last_known_resource": e["resource"], "position": dict(e["position"]),
            }
        elif e["type"] == "shelter" and e.get("alive", True) and manhattan(pos, e["position"]) <= radius:
            shelter_sightings[eid] = {
                "last_seen_tick": tick, "position": dict(e["position"]), "owner_id": e.get("owner_id"),
            }

    return {"new_tiles": new_tiles, "new_water": new_water,
            "tree_sightings": tree_sightings, "shelter_sightings": shelter_sightings}


def merge_knowledge(existing: dict, delta: dict):
    """Merges a perception delta into existing knowledge. Returns (merged, discovered_new_tile: bool).

    Uses sets internally for correct union semantics, but always returns
    SORTED lists - this is required for canonical hashing determinism
    (set iteration order is not stable/hashable).
    """
    known_tiles = set(existing.get("known_tiles", []))
    known_water = set(existing.get("known_water_tiles", []))
    known_trees = dict(existing.get("known_trees", {}))
    known_shelters = dict(existing.get("known_shelters", {}))

    discovered_new = bool(set(delta["new_tiles"]) - known_tiles)

    known_tiles |= set(delta["new_tiles"])
    known_water |= set(delta["new_water"])
    known_trees.update(delta["tree_sightings"])
    known_shelters.update(delta["shelter_sightings"])

    merged = {
        "known_tiles": sorted(known_tiles),
        "known_water_tiles": sorted(known_water),
        "known_trees": known_trees,
        "known_shelters": known_shelters,
    }
    return merged, discovered_new
