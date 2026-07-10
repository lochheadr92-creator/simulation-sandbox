"""Utility scoring (Phase 2) - transparent, multi-factor, fully inspectable.

    score = severity*W_SEVERITY + predicted*W_PREDICTED - travel*W_TRAVEL
            - interrupt*W_INTERRUPT + availability*W_AVAILABILITY - risk*W_RISK

Every input that feeds the score is returned in the breakdown dict so the
causal inspector can show genuine evidence for every candidate - never an
opaque number. Nothing here is random; all lookups go through the actor's
own `knowledge` (resource memory), never an omniscient global search.
"""
from core.geometry import manhattan
from core.constants import SEEK_THRESHOLD

W_SEVERITY = 1.0
W_PREDICTED = 0.5
W_TRAVEL = 3.0
W_INTERRUPT = 5.0
W_AVAILABILITY = 90.0
W_RISK = 70.0

HUNGER_RATE = 8
THIRST_RATE = 10


UNAVAILABLE_NEED_CAP = 45  # hard cap on severity/predicted contribution when a goal has
                            # no known target - guarantees EXPLORE always wins over an
                            # unreachable goal, no matter how extreme the need gets,
                            # preventing a permanent "critically thirsty but never finds
                            # water" deadlock.


def _score(goal, severity, predicted, travel_cost, availability, risk, interrupt_cost):
    need_term = severity * W_SEVERITY + predicted * W_PREDICTED
    if availability <= 0:
        need_term = min(need_term, UNAVAILABLE_NEED_CAP)
    score = (need_term - travel_cost * W_TRAVEL - interrupt_cost * W_INTERRUPT
             + availability * W_AVAILABILITY - risk * W_RISK)
    return {
        "goal": goal, "severity": round(severity, 1), "predicted_severity": round(predicted, 1),
        "travel_cost": travel_cost, "availability": availability, "risk": risk,
        "interruption_cost": interrupt_cost, "score": round(score, 2),
    }


def nearest_known_water(pos, knowledge):
    best, best_d = None, None
    for key in knowledge.get("known_water_tiles", []):
        x, y = (int(v) for v in key.split(","))
        d = manhattan(pos, {"x": x, "y": y})
        if best_d is None or d < best_d:
            best_d, best = d, {"x": x, "y": y}
    return best, best_d


def nearest_known_tree(pos, knowledge, min_resource=1):
    best, best_d, best_id = None, None, None
    for tid, info in knowledge.get("known_trees", {}).items():
        if info.get("last_known_resource", 0) < min_resource:
            continue
        d = manhattan(pos, info["position"])
        if best_d is None or d < best_d:
            best_d, best, best_id = d, info["position"], tid
    return best_id, best, best_d


def nearest_known_shelter(pos, knowledge, owner_id=None):
    best, best_d, best_id = None, None, None
    for sid, info in knowledge.get("known_shelters", {}).items():
        if owner_id is not None and info.get("owner_id") != owner_id:
            continue
        d = manhattan(pos, info["position"])
        if best_d is None or d < best_d:
            best_d, best, best_id = d, info["position"], sid
    return best_id, best, best_d


def nearest_unknown_tile(pos, knowledge, terrain, width, height):
    """Only considers PASSABLE unknown tiles as travel targets - walking
    toward an unknown water tile would never "arrive" since water tiles are
    impassable. Water tiles still get discovered naturally via vision radius
    once the actor is near their (passable) shore."""
    known = set(knowledge.get("known_tiles", []))
    best, best_d = None, None
    for y in range(height):
        for x in range(width):
            if terrain[y][x] == "water":
                continue
            key = f"{x},{y}"
            if key in known:
                continue
            d = manhattan(pos, {"x": x, "y": y})
            if best_d is None or d < best_d:
                best_d, best = d, {"x": x, "y": y}
    return best, best_d


def score_candidates(e, knowledge, pos, tick, night, current_action, terrain):
    height = len(terrain)
    width = len(terrain[0]) if height else 0
    hunger, thirst, energy = e["hunger"], e["thirst"], e["energy"]
    interrupt_cost = 0
    if current_action and current_action.get("status") in ("travelling", "performing"):
        interrupt_cost = current_action.get("ticks_spent", 0)

    def interrupt_for(action_types):
        if current_action and current_action.get("type") not in action_types and current_action.get("status") in ("travelling", "performing"):
            return interrupt_cost
        return 0

    candidates = []

    water_pos, water_d = nearest_known_water(pos, knowledge)
    travel = water_d if water_d is not None else 0
    predicted = thirst + THIRST_RATE * travel
    avail = 1.0 if water_pos else 0.0
    sev = thirst if thirst >= SEEK_THRESHOLD else thirst * 0.25
    candidates.append(_score("SEEK_WATER", sev, predicted, travel, avail, 0, interrupt_for(("drink", "travel"))))

    tree_id, tree_pos, tree_d = nearest_known_tree(pos, knowledge)
    can_eat_from_inventory = e["inventory"] > 0
    travel = 0 if can_eat_from_inventory else (tree_d if tree_d is not None else 0)
    predicted = hunger + HUNGER_RATE * travel
    avail = 1.0 if (can_eat_from_inventory or tree_id) else 0.0
    sev = hunger if hunger >= SEEK_THRESHOLD else hunger * 0.25
    candidates.append(_score("SEEK_FOOD", sev, predicted, travel, avail, 0, interrupt_for(("eat", "gather", "travel"))))

    rest_threshold = 600 if night else 300
    deficit = max(0, rest_threshold - energy)
    shelter_id, shelter_pos, shelter_d = nearest_known_shelter(pos, knowledge, owner_id=e.get("id"))
    sleep_travel = shelter_d if shelter_pos else 0
    candidates.append(_score("SLEEP", deficit * 1.4, deficit * 1.4, sleep_travel, 1.0, 0, interrupt_for(("sleep", "travel"))))

    want_shelter = e["inventory"] >= 10 and not e.get("has_shelter")
    build_avail = 1.0 if want_shelter else 0.0
    candidates.append(_score("BUILD_SHELTER", 240 if want_shelter else 0, 240 if want_shelter else 0,
                              0, build_avail, 0, interrupt_cost))

    gather_avail = 1.0 if (tree_id and tree_d is not None and tree_d <= 1) else 0.0
    candidates.append(_score("GATHER_SURPLUS", 95 if (gather_avail and e["inventory"] < 20) else 0,
                              0, 0, gather_avail, 0, interrupt_cost))

    frontier, frontier_d = nearest_unknown_tile(pos, knowledge, terrain, width, height)
    explore_avail = 1.0 if frontier else 0.0
    urgent_but_blind = (hunger >= SEEK_THRESHOLD or thirst >= SEEK_THRESHOLD) and not (water_pos or tree_id)
    explore_sev = 55 + (35 if urgent_but_blind else 0)
    explore_risk = 35 if night else 0
    candidates.append(_score("EXPLORE", explore_sev, explore_sev, frontier_d or 0, explore_avail, explore_risk, interrupt_cost))

    candidates.append(_score("WANDER", 25, 25, 0, 1.0, 0, interrupt_cost))

    context = {
        "water_target": water_pos, "tree_target_id": tree_id, "tree_target_pos": tree_pos,
        "shelter_target_id": shelter_id, "shelter_target_pos": shelter_pos,
        "frontier_target": frontier, "shelter_site": dict(pos),
    }
    return candidates, context
