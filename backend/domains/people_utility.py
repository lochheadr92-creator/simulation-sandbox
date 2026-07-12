"""Utility scoring (Phase 2) - transparent, multi-factor, fully inspectable.
Phase 5B: travel cost is path length of a reachable route (not Manhattan);
unreachable targets are excluded from availability.

    score = severity*W_SEVERITY + predicted*W_PREDICTED - travel*W_TRAVEL
            - interrupt*W_INTERRUPT + availability*W_AVAILABILITY - risk*W_RISK

Every input that feeds the score is returned in the breakdown dict so the
causal inspector can show genuine evidence for every candidate - never an
opaque number. Nothing here is random; all lookups go through the actor's
own `knowledge` (resource memory), never an omniscient global search.
"""
from core.geometry import manhattan
from core.navigation import ARRIVAL_ADJACENT, ARRIVAL_EXACT, path_length
from core.constants import (
    SEEK_THRESHOLD, VISION_RADIUS, GATHER_TICKS, HUNT_TICKS,
    CRITICAL_THRESHOLD, FOOD_TRANSFER_SURPLUS,
)

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


def _score(goal, severity, predicted, travel_cost, availability, risk, interrupt_cost,
           extra=None):
    need_term = severity * W_SEVERITY + predicted * W_PREDICTED
    if availability <= 0:
        need_term = min(need_term, UNAVAILABLE_NEED_CAP)
    score = (need_term - travel_cost * W_TRAVEL - interrupt_cost * W_INTERRUPT
             + availability * W_AVAILABILITY - risk * W_RISK)
    row = {
        "goal": goal, "severity": round(severity, 1), "predicted_severity": round(predicted, 1),
        "travel_cost": travel_cost, "availability": availability, "risk": risk,
        "interruption_cost": interrupt_cost, "score": round(score, 2),
    }
    if extra:
        row.update(extra)
    return row


def nearest_known_water(pos, knowledge, terrain=None):
    """Nearest *reachable* known water by adjacent-arrival path length.

    When terrain is omitted (legacy callers), falls back to Manhattan.
    Unreachable water is skipped when terrain is provided.
    """
    best, best_d = None, None
    for key in sorted(knowledge.get("known_water_tiles", [])):
        x, y = (int(v) for v in key.split(","))
        wpos = {"x": x, "y": y}
        if terrain is not None:
            d = path_length(pos, wpos, terrain, ARRIVAL_ADJACENT)
            if d is None:
                continue
        else:
            d = manhattan(pos, wpos)
        if best_d is None or d < best_d:
            best_d, best = d, wpos
    return best, best_d


def nearest_known_tree(pos, knowledge, min_resource=1, terrain=None):
    best, best_d, best_id, best_res = None, None, None, 0
    known_trees = knowledge.get("known_trees", {})
    for tid in sorted(known_trees):
        info = known_trees[tid]
        res = info.get("last_known_resource", 0)
        if res < min_resource:
            continue
        tpos = info["position"]
        if terrain is not None:
            d = path_length(pos, tpos, terrain, ARRIVAL_EXACT)
            if d is None:
                continue
        else:
            d = manhattan(pos, tpos)
        if best_d is None or d < best_d:
            best_d, best, best_id, best_res = d, tpos, tid, res
    return best_id, best, best_d, best_res


def nearest_known_shelter(pos, knowledge, owner_id=None, terrain=None):
    best, best_d, best_id = None, None, None
    known_shelters = knowledge.get("known_shelters", {})
    for sid in sorted(known_shelters):
        info = known_shelters[sid]
        if owner_id is not None and info.get("owner_id") != owner_id:
            continue
        spos = info["position"]
        if terrain is not None:
            d = path_length(pos, spos, terrain, ARRIVAL_EXACT)
            if d is None:
                continue
        else:
            d = manhattan(pos, spos)
        if best_d is None or d < best_d:
            best_d, best, best_id = d, spos, sid
    return best_id, best, best_d


def nearest_known_carcass(pos, knowledge, min_resource=1, terrain=None):
    """Mirrors nearest_known_tree - carcasses are tracked in resource
    memory exactly like trees (Phase 4B: minimal survival food chain)."""
    best, best_d, best_id, best_res = None, None, None, 0
    known_carcasses = knowledge.get("known_carcasses", {})
    for cid in sorted(known_carcasses):
        info = known_carcasses[cid]
        res = info.get("last_known_resource", 0)
        if res < min_resource:
            continue
        cpos = info["position"]
        if terrain is not None:
            d = path_length(pos, cpos, terrain, ARRIVAL_EXACT)
            if d is None:
                continue
        else:
            d = manhattan(pos, cpos)
        if best_d is None or d < best_d:
            best_d, best, best_id, best_res = d, cpos, cid, res
    return best_id, best, best_d, best_res


def nearest_known_food(pos, knowledge, min_resource=1, terrain=None):
    """A person's food source can be a tree (foraged wood/food, unchanged
    since Phase 2) OR a carcass (meat, Phase 4B) - whichever known *reachable*
    source is nearer by path length wins. Returns (id, pos, distance, kind, resource)."""
    tree_id, tree_pos, tree_d, tree_res = nearest_known_tree(pos, knowledge, min_resource, terrain)
    carcass_id, carcass_pos, carcass_d, carcass_res = nearest_known_carcass(
        pos, knowledge, min_resource, terrain)
    if tree_id and (carcass_id is None or tree_d <= carcass_d):
        return tree_id, tree_pos, tree_d, "tree", tree_res
    if carcass_id:
        return carcass_id, carcass_pos, carcass_d, "carcass", carcass_res
    return None, None, None, "tree", 0


def nearest_huntable_animal(pos, knowledge, terrain=None, perception_delta=None, entities=None):
    """Hunt targets from personal knowledge and/or this-tick perception only.

    Never scans the full entity table for animals the observer has not
    perceived or retained. Prefer currently perceived live animals; fall back
    to last-known positions from knowledge (may be stale — strike can fail).
    """
    entities = entities or {}
    known = dict((knowledge or {}).get("known_animals", {}))
    sighted = dict((perception_delta or {}).get("animal_sightings", {}))
    candidate_ids = sorted(set(known) | set(sighted))
    best, best_d, best_id = None, None, None
    for eid in candidate_ids:
        live = entities.get(eid)
        if live is not None:
            if live.get("type") != "animal" or not live.get("alive", True):
                continue
            if (live.get("action") or {}).get("type") == "flee":
                continue
            apos = live["position"]
            # Live target must still be in vision for a current strike plan
            if manhattan(pos, apos) > VISION_RADIUS and eid not in known:
                continue
        else:
            info = known.get(eid) or sighted.get(eid)
            if not info:
                continue
            apos = info.get("position")
            if not apos:
                continue
        if terrain is not None:
            d = path_length(pos, apos, terrain, ARRIVAL_EXACT)
            if d is None:
                continue
        else:
            d = manhattan(pos, apos)
        # Prefer currently perceived over stale-only knowledge at equal distance
        prefer = 0 if eid in sighted else 1
        rank = (d, prefer, eid)
        best_rank = None if best_id is None else (
            best_d, 0 if best_id in sighted else 1, best_id,
        )
        if best_rank is None or rank < best_rank:
            best_d, best, best_id = d, dict(apos), eid
    return best_id, best, best_d


def nearest_unknown_tile(pos, knowledge, terrain, width=None, height=None):
    """Exploration target: first passable unknown 4-neighbour (N,E,S,W).

    No full-map frontier scan (Phase 5A5). If every neighbour is known or
    blocked, returns (None, None) so utility can fall through to WANDER.
    """
    from domains.perception import neighbor_unknown_tiles
    neighbours = neighbor_unknown_tiles(pos, knowledge, terrain)
    if not neighbours:
        return None, None
    # neighbour_unknown_tiles already uses fixed NEIGHBOR_DELTAS order
    target = neighbours[0]
    return target, 1


def _resource_availability(resource_amount, carried=False):
    """Bounded availability from known remaining resource (or carried food)."""
    if carried:
        return 1.0
    if not resource_amount:
        return 0.0
    # Cap at 1.0 once resource covers a full gather yield-ish amount.
    return min(1.0, float(resource_amount) / 40.0)


def eligible_food_recipient(giver, pos, entities, perception_delta=None, tick=None):
    """Return the stable first adjacent recipient visible to the giver.

    Eligibility deliberately starts from this activation's bounded person
    sightings.  The live entity view is consulted only to resolve those
    observed subjects' canonical state; it is never scanned for recipients.

    Among equally eligible recipients, prefer higher 5B5 support_score, then
    recipient_id ascending (hard 5B1 survival eligibility is unchanged).
    """
    sightings = (perception_delta or {}).get("person_sightings", {})
    candidates = []
    for recipient_id in sorted(sightings):
        recipient = entities.get(recipient_id)
        if not recipient or recipient.get("type") != "person":
            continue
        if not recipient.get("alive", True):
            continue
        if manhattan(pos, recipient.get("position", {})) != 1:
            continue
        if recipient.get("hunger", 0) < CRITICAL_THRESHOLD:
            continue
        # `inventory` remains the legacy carried food source.  It is not
        # transferable in 5B, but it still makes the recipient ineligible.
        if recipient.get("food_inventory", 0) != 0 or recipient.get("inventory", 0) != 0:
            continue
        candidates.append(recipient_id)
    if not candidates:
        return None
    # 5B5 ranking influence: support desc, then id asc. Survival gate already applied.
    from domains.reciprocity_trust import support_score_for
    knowledge = giver.get("knowledge") or {}
    observer_id = giver.get("id")
    # giver entity may not carry id field; callers pass entity with id sometimes.
    # score_candidates uses e without always setting id — use None-safe.
    current_tick = 0 if tick is None else int(tick)

    def rank_key(rid):
        support = 0
        if observer_id:
            support = support_score_for(knowledge, observer_id, rid, current_tick)
        return (-support, rid)

    candidates.sort(key=rank_key)
    return candidates[0]


def score_candidates(e, knowledge, pos, tick, night, current_action, terrain,
                     entities=None, perception_delta=None):
    """Score plan goals from Needs urgency + personal Knowledge only.

    `entities` may be consulted only to resolve currently perceived subjects
    already present in knowledge/perception_delta (never as a global target scan).
    """
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

    water_pos, water_d = nearest_known_water(pos, knowledge, terrain)
    travel = water_d if water_d is not None else 0
    predicted = thirst + THIRST_RATE * travel
    avail = 1.0 if water_pos else 0.0
    sev = thirst if thirst >= SEEK_THRESHOLD else thirst * 0.25
    candidates.append(_score(
        "SEEK_WATER", sev, predicted, travel, avail, 0, interrupt_for(("drink", "travel")),
        extra={"path_length": water_d, "reachable": bool(water_pos), "target_pos": water_pos},
    ))

    tree_id, tree_pos, tree_d, tree_res = nearest_known_tree(pos, knowledge, terrain=terrain)
    food_id, food_pos, food_d, food_kind, food_res = nearest_known_food(pos, knowledge, terrain=terrain)
    has_carried_food = e["inventory"] > 0 or e.get("food_inventory", 0) > 0
    travel = 0 if has_carried_food else (food_d if food_d is not None else 0)
    # Include gather duration in predicted need growth when travel is required.
    action_time = 0 if has_carried_food else (GATHER_TICKS if food_id else 0)
    predicted = hunger + HUNGER_RATE * (travel + action_time)
    avail = _resource_availability(food_res, carried=has_carried_food) if (has_carried_food or food_id) else 0.0
    if has_carried_food:
        avail = 1.0
    sev = hunger if hunger >= SEEK_THRESHOLD else hunger * 0.25
    candidates.append(_score(
        "SEEK_FOOD", sev, predicted, travel, avail, 0, interrupt_for(("eat", "gather", "travel")),
        extra={
            "path_length": food_d if not has_carried_food else 0,
            "reachable": bool(has_carried_food or food_id),
            "target_pos": food_pos if not has_carried_food else None,
            "target_resource": food_res if not has_carried_food else None,
            "action_time": action_time,
        },
    ))

    recipient_id = None
    if e.get("food_inventory", 0) >= FOOD_TRANSFER_SURPLUS:
        # Ensure observer id is available for 5B5 ranking
        if e.get("id") is None and entities:
            # best-effort: match by identity in entities map is not available; leave unset
            pass
        recipient_id = eligible_food_recipient(
            e, pos, entities or {}, perception_delta, tick=tick,
        )
    recipient = (entities or {}).get(recipient_id) if recipient_id else None
    recipient_hunger = recipient.get("hunger", 0) if recipient else 0
    candidates.append(_score(
        "GIVE_FOOD", recipient_hunger, recipient_hunger, 0,
        1.0 if recipient_id else 0.0, 0, interrupt_for(("give_food",)),
        extra={
            "recipient_id": recipient_id,
            "recipient_hunger": recipient_hunger,
            "giver_surplus": e.get("food_inventory", 0) >= FOOD_TRANSFER_SURPLUS,
            "selection_rule": "adjacent_eligible_person_id_ascending",
        },
    ))

    rest_threshold = 600 if night else 300
    deficit = max(0, rest_threshold - energy)
    shelter_id, shelter_pos, shelter_d = nearest_known_shelter(pos, knowledge, owner_id=e.get("id"), terrain=terrain)
    sleep_travel = shelter_d if shelter_pos else 0
    candidates.append(_score(
        "SLEEP", deficit * 1.4, deficit * 1.4, sleep_travel, 1.0, 0, interrupt_for(("sleep", "travel")),
        extra={"path_length": shelter_d, "reachable": True, "target_pos": shelter_pos},
    ))

    want_shelter = e["inventory"] >= 10 and not e.get("has_shelter")
    build_avail = 1.0 if want_shelter else 0.0
    # Build plan may require a reachable tree; if none, still score but availability reflects want.
    build_travel = tree_d if (want_shelter and tree_d is not None) else 0
    candidates.append(_score(
        "BUILD_SHELTER", 240 if want_shelter else 0, 240 if want_shelter else 0,
        build_travel, build_avail, 0, interrupt_cost,
        extra={"path_length": tree_d if want_shelter else 0, "reachable": bool(tree_id) if want_shelter else True},
    ))

    # Surplus gather when already on or adjacent to a reachable tree (historical adjacency).
    gather_avail = 1.0 if (tree_id and tree_d is not None and tree_d <= 1) else 0.0
    candidates.append(_score(
        "GATHER_SURPLUS", 95 if (gather_avail and e["inventory"] < 20) else 0,
        0, 0, gather_avail, 0, interrupt_cost,
        extra={"path_length": tree_d, "reachable": bool(tree_id and tree_d is not None and tree_d <= 1)},
    ))

    animal_id, animal_pos, animal_d = nearest_huntable_animal(
        pos, knowledge, terrain, perception_delta=perception_delta, entities=entities or {},
    )
    hunt_avail = 1.0 if animal_id else 0.0
    hunt_travel = animal_d if animal_d is not None else 0
    hunt_predicted = hunger + HUNGER_RATE * (hunt_travel + HUNT_TICKS)
    hunt_sev = (hunger if hunger >= SEEK_THRESHOLD else hunger * 0.25) * 0.7  # discounted: slower/riskier than foraging
    hunt_risk = 15 if night else 5
    candidates.append(_score(
        "HUNT", hunt_sev, hunt_predicted, hunt_travel, hunt_avail, hunt_risk, interrupt_for(("hunt_strike", "travel")),
        extra={
            "path_length": animal_d, "reachable": bool(animal_id), "target_pos": animal_pos,
            "action_time": HUNT_TICKS, "target_source": "knowledge_or_perception",
        },
    ))

    frontier, frontier_d = nearest_unknown_tile(pos, knowledge, terrain, width, height)
    explore_avail = 1.0 if frontier else 0.0
    urgent_but_blind = (hunger >= SEEK_THRESHOLD or thirst >= SEEK_THRESHOLD) and not (water_pos or food_id)
    explore_sev = 55 + (35 if urgent_but_blind else 0)
    explore_risk = 35 if night else 0
    candidates.append(_score(
        "EXPLORE", explore_sev, explore_sev, frontier_d or 0, explore_avail, explore_risk, interrupt_cost,
        extra={
            "path_length": frontier_d, "reachable": bool(frontier), "target_pos": frontier,
            "explore_mode": "neighbour_only", "urgent_without_known_solution": urgent_but_blind,
        },
    ))

    candidates.append(_score(
        "WANDER", 25, 25, 0, 1.0, 0, interrupt_cost,
        extra={"path_length": 0, "reachable": True},
    ))

    context = {
        "water_target": water_pos, "tree_target_id": tree_id, "tree_target_pos": tree_pos,
        "shelter_target_id": shelter_id, "shelter_target_pos": shelter_pos,
        "frontier_target": frontier, "shelter_site": dict(pos),
        "food_target_id": food_id, "food_target_pos": food_pos, "food_target_kind": food_kind,
        "animal_target_id": animal_id, "animal_target_pos": animal_pos,
        "food_recipient_id": recipient_id,
    }
    return candidates, context
