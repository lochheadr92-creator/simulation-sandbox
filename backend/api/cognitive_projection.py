"""Bounded, read-only cognitive projection for the canvas.

This module intentionally derives a display view from a selected observer and
the pinned canonical state.  It does not write knowledge, actions, events, or
diagnostics, and is not consumed by simulation decisions.
"""
from __future__ import annotations

from copy import deepcopy

from domains.perception import PERCEPTION_RULE_VERSION, perceive


COGNITIVE_PROJECTION_VERSION = "cognitive-overlay-v1"
MAX_PROJECTED_TILES = 200
MAX_GHOST_MARKERS = 24
MAX_DISCOVERY_PULSES = 12
MAX_ROUTE_POINTS = 64


def _coord(value):
    if isinstance(value, str):
        x, y = value.split(",", 1)
        return {"x": int(x), "y": int(y)}
    return {"x": int(value["x"]), "y": int(value["y"])}


def _bounded_coords(values, limit):
    return [_coord(value) for value in sorted(values)[:limit]]


def _ghosts(knowledge, perceived_ids):
    ghosts = []
    for kind, key in (("animal", "known_animals"), ("person", "known_people"), ("danger", "known_dangers")):
        for subject_id, record in sorted((knowledge.get(key) or {}).items()):
            if subject_id in perceived_ids or not record.get("position"):
                continue
            ghosts.append({
                "id": subject_id,
                "kind": kind,
                "position": _coord(record["position"]),
                "last_seen_tick": record.get("last_seen_tick"),
                "label": f"last-known {kind}",
            })
    return ghosts[:MAX_GHOST_MARKERS]


def _discoveries(knowledge, tick):
    discoveries = []
    for fact_id, fact in sorted((knowledge.get("facts") or {}).items()):
        if fact.get("first_known_tick") != tick or not fact.get("location"):
            continue
        discoveries.append({
            "id": fact_id,
            "kind": fact.get("fact_type", "fact"),
            "position": _coord(fact["location"]),
        })
    return discoveries[:MAX_DISCOVERY_PULSES]


def _route(action):
    action = action or {}
    path = action.get("remaining_path") or []
    return {
        "status": action.get("status"),
        "purpose": action.get("travel_purpose"),
        "target": deepcopy(action.get("target_pos")),
        "arrival_mode": action.get("arrival_mode"),
        "arrival_action": action.get("arrival_action"),
        "unreachable": bool(action.get("unreachable")),
        "invalidation_reason": action.get("invalidation_reason"),
        "remaining_path": [_coord(point) for point in path[:MAX_ROUTE_POINTS]],
        "truncated": len(path) > MAX_ROUTE_POINTS,
    }


def build_cognitive_projection(observer, entities, terrain, tick, diagnostics=None):
    """Build a bounded observer-specific canvas projection without mutation."""
    knowledge = observer.get("knowledge") or {}
    observer_id = observer.get("id")
    living_person = observer.get("type") == "person" and observer.get("alive", True)
    current = perceive(observer["position"], entities, terrain, tick, observer_id) if living_person else {}
    perceived_tiles = _bounded_coords(current.get("new_tiles", []), MAX_PROJECTED_TILES)
    perceived_ids = {d["subject_id"] for d in current.get("detections", [])}
    planning = (diagnostics or {}).get("planning") or {}
    selected_goal = planning.get("selected_goal") or (observer.get("plan") or {}).get("goal")
    if selected_goal == "EXPLORE":
        target_origin = "unknown_frontier"
    elif planning.get("target_from_knowledge"):
        target_origin = "personal_knowledge_or_current_perception"
    else:
        target_origin = None

    return {
        "projection_version": COGNITIVE_PROJECTION_VERSION,
        "observer_id": observer_id,
        "observer_alive": bool(observer.get("alive", True)),
        "world_tick": tick,
        "knowledge_schema_version": knowledge.get("schema_version"),
        "perception_rule_version": current.get("perception_rule_version", PERCEPTION_RULE_VERSION),
        "perception_radius": current.get("radius") if living_person else 0,
        "current_perception": {
            "tiles": perceived_tiles,
            "entity_ids": sorted(perceived_ids)[:MAX_GHOST_MARKERS],
        },
        "known_tiles": _bounded_coords(knowledge.get("known_tiles", []), MAX_PROJECTED_TILES),
        "last_known_entities": _ghosts(knowledge, perceived_ids),
        "new_discoveries": _discoveries(knowledge, tick),
        "route": _route(observer.get("action")),
        "planning": {
            "goal": selected_goal,
            "target_origin": target_origin,
            "explore_neighbour_only": planning.get("explore_neighbour_only"),
        },
        "limits": {
            "max_tiles": MAX_PROJECTED_TILES,
            "max_ghost_markers": MAX_GHOST_MARKERS,
            "max_discovery_pulses": MAX_DISCOVERY_PULSES,
            "max_route_points": MAX_ROUTE_POINTS,
        },
        "stale_knowledge_warning": "Last-known markers are personal memory, not current world truth.",
    }
