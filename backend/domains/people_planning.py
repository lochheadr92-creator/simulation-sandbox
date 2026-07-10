"""Multi-stage actions + short plans (Phase 2; extended in Phase 4B with a
minimal hunting/carcass step for the survival food chain).

Canonical `action` shape:
    {"type", "status", "target_entity_id", "target_pos", "ticks_spent",
     "ticks_required", "interruptible", "started_tick", "arrival_action",
     "shelter_bonus", "target_kind"}
status in: planned | travelling | performing | paused | completed | failed | cancelled

Canonical `plan` shape:
    {"goal", "steps": [...], "step_index", "status"}
status in: active | completed | abandoned

Every function here is a pure, deterministic transform of
(entity, knowledge, terrain, tick) -> new action/plan + mutation deltas.
Core never interprets any of this; it only applies whatever ends up in the
generic entity_updates envelope, so the authority boundary is untouched.

Phase 4B hunting note: "gather" is now kind-aware (`target_kind` is "tree"
for wood/food foraging, unchanged since Phase 2, or "carcass" for meat -
harvested meat goes to the person's separate `food_inventory`, never
`inventory`, so meat can never appear without a genuine harvest action
with a real causal parent). "hunt_strike" mutates a THIRD-PARTY animal
entity's health/alive fields directly via the `_animal_delta` side-channel
- this is the exact same established pattern "gather" already uses to
mutate a tree's `resource` via `_tree_delta`/`_carcass_delta` (any domain
may propose a mutation on any entity id; Core's precondition-driven commit
ordering is what resolves conflicts, not domain ownership).
"""
from core.geometry import step_toward, manhattan, is_water_adjacent
from core.constants import (GATHER_TICKS, BUILD_TICKS, SHELTER_COST, GATHER_YIELD,
                             SLEEP_ENERGY_TARGET, CRITICAL_THRESHOLD, HUNT_TICKS, HUNT_DAMAGE,
                             ANIMAL_MAX_HEALTH, CARCASS_MEAT_YIELD, CARCASS_HARVEST_YIELD,
                             MEAT_HUNGER_REDUCTION)

TRAVEL_STALL_LIMIT = 25  # deterministic safety net: abandon a travel step that
                          # cannot make progress (e.g. a target boxed in by water)
                          # rather than looping forever - triggers a clean replan.

PLAN_STEPS = {
    "SEEK_WATER": ["TRAVEL_WATER", "DRINK"],
    "SEEK_FOOD": ["EAT"],                      # rewritten to a travel+gather variant in form_plan() if no food carried
    "SLEEP": ["SLEEP"],                        # rewritten to travel-then-sleep in form_plan() if a shelter is known
    "BUILD_SHELTER": ["TRAVEL_TREE", "GATHER", "TRAVEL_SITE", "BUILD"],
    "GATHER_SURPLUS": ["GATHER"],
    "HUNT": ["TRAVEL_ANIMAL", "HUNT_STRIKE"],   # Phase 4B: minimal survival food-chain extension
    "EXPLORE": ["TRAVEL_FRONTIER"],
    "WANDER": ["WANDER_STEP"],
}


def idle_action():
    return {"type": "idle", "status": "completed", "target_entity_id": None, "target_pos": None,
            "ticks_spent": 0, "ticks_required": 0, "interruptible": True, "started_tick": 0}


def empty_plan():
    return {"goal": None, "steps": [], "step_index": 0, "status": "completed"}


def check_critical_interrupt(e):
    if e["thirst"] >= CRITICAL_THRESHOLD:
        return "SEEK_WATER"
    if e["hunger"] >= CRITICAL_THRESHOLD:
        return "SEEK_FOOD"
    return None


def context_from_action(action, pos):
    """Reconstructs a minimal targeting context for the NEXT plan step from
    the just-completed action - avoids re-scoring utility mid-plan."""
    return {
        "tree_target_id": action.get("target_entity_id"),
        "tree_target_pos": action.get("target_pos"),
        "water_target": action.get("target_pos"),
        "shelter_target_id": action.get("target_entity_id"),
        "shelter_target_pos": action.get("target_pos"),
        "shelter_site": action.get("target_pos") or pos,
        "frontier_target": None,
        "food_target_id": action.get("target_entity_id"),
        "food_target_pos": action.get("target_pos"),
        "food_target_kind": action.get("target_kind", "tree"),
        "animal_target_id": action.get("target_entity_id"),
        "animal_target_pos": action.get("target_pos"),
    }


def form_plan(goal, e, context, tick):
    steps = list(PLAN_STEPS.get(goal, ["WANDER_STEP"]))
    if goal == "SEEK_FOOD" and e["inventory"] <= 0 and e.get("food_inventory", 0) <= 0 and context.get("food_target_id"):
        steps = ["TRAVEL_FOOD", "GATHER_FOOD", "EAT"]
    if goal == "SLEEP" and context.get("shelter_target_id"):
        steps = ["TRAVEL_SHELTER", "SLEEP"]
    return {"goal": goal, "steps": steps, "step_index": 0, "status": "active"}


def start_step(step, e, eid, context, terrain, tick, pos):
    base = {"ticks_spent": 0, "interruptible": True, "started_tick": tick,
            "target_entity_id": None, "target_pos": None, "ticks_required": 0, "arrival_action": None}
    if step == "TRAVEL_WATER":
        return {**base, "type": "travel", "status": "travelling", "target_pos": context["water_target"], "arrival_action": "DRINK"}
    if step == "TRAVEL_TREE":
        return {**base, "type": "travel", "status": "travelling", "target_entity_id": context["tree_target_id"],
                "target_pos": context["tree_target_pos"], "arrival_action": "GATHER"}
    if step == "TRAVEL_FOOD":
        return {**base, "type": "travel", "status": "travelling", "target_entity_id": context.get("food_target_id"),
                "target_pos": context.get("food_target_pos"), "arrival_action": "GATHER_FOOD",
                "target_kind": context.get("food_target_kind", "tree")}
    if step == "TRAVEL_SITE":
        return {**base, "type": "travel", "status": "travelling", "target_pos": context.get("shelter_site", pos), "arrival_action": "BUILD"}
    if step == "TRAVEL_SHELTER":
        return {**base, "type": "travel", "status": "travelling", "target_entity_id": context.get("shelter_target_id"),
                "target_pos": context.get("shelter_target_pos"), "arrival_action": "SLEEP"}
    if step == "TRAVEL_FRONTIER":
        return {**base, "type": "travel", "status": "travelling", "target_pos": context.get("frontier_target")}
    if step == "TRAVEL_ANIMAL":
        return {**base, "type": "travel", "status": "travelling", "target_entity_id": context.get("animal_target_id"),
                "target_pos": context.get("animal_target_pos"), "arrival_action": "HUNT_STRIKE"}
    if step == "GATHER":
        return {**base, "type": "gather", "status": "performing", "target_entity_id": context.get("tree_target_id"),
                "target_pos": context.get("tree_target_pos"), "ticks_required": GATHER_TICKS, "target_kind": "tree"}
    if step == "GATHER_FOOD":
        return {**base, "type": "gather", "status": "performing", "target_entity_id": context.get("food_target_id"),
                "target_pos": context.get("food_target_pos"), "ticks_required": GATHER_TICKS,
                "target_kind": context.get("food_target_kind", "tree")}
    if step == "EAT":
        return {**base, "type": "eat", "status": "performing", "target_pos": dict(pos), "ticks_required": 1}
    if step == "DRINK":
        return {**base, "type": "drink", "status": "performing", "target_pos": dict(pos), "ticks_required": 1}
    if step == "SLEEP":
        return {**base, "type": "sleep", "status": "performing", "target_pos": dict(pos),
                "shelter_bonus": bool(context.get("shelter_target_id"))}
    if step == "BUILD":
        return {**base, "type": "build_shelter", "status": "performing", "target_pos": dict(pos), "ticks_required": BUILD_TICKS}
    if step == "HUNT_STRIKE":
        return {**base, "type": "hunt_strike", "status": "performing", "target_entity_id": context.get("animal_target_id"),
                "target_pos": context.get("animal_target_pos"), "ticks_required": HUNT_TICKS}
    return {**base, "type": "wander", "status": "performing"}


def execute_action_tick(e, eid, action, entities, terrain, tick, night, rng):
    """Advances the CURRENT action by exactly one tick. Returns a result dict
    with the resulting physical/needs deltas, the updated action, and whether
    the active plan step is finished (so the caller can start the next one)."""
    pos = dict(e["position"])
    hunger = min(1000, e["hunger"] + 8)
    thirst = min(1000, e["thirst"] + 10)
    energy = max(0, e["energy"] - (7 if night else 5))
    inventory = e["inventory"]
    food_inventory = e.get("food_inventory", 0)
    has_shelter = e.get("has_shelter", False)

    touched_scope = [eid]
    preconditions = []
    new_entities = {}
    advance_plan = False
    new_action = dict(action)
    explanation = ""
    atype = action["type"]

    if atype == "travel":
        target = action.get("target_pos")
        if not target:
            new_action["status"] = "failed"
            advance_plan = True
            explanation = "travel target no longer known; abandoning step"
        elif manhattan(pos, target) <= 1:
            new_action["status"] = "completed"
            advance_plan = True
            explanation = f"arrived near {target}"
        elif action.get("ticks_spent", 0) >= TRAVEL_STALL_LIMIT:
            new_action["status"] = "failed"
            advance_plan = True
            explanation = f"unable to make progress toward {target} after {TRAVEL_STALL_LIMIT} ticks; abandoning"
        else:
            pos = step_toward(pos, target, terrain)
            new_action["ticks_spent"] = action.get("ticks_spent", 0) + 1
            new_action["status"] = "travelling"
            explanation = f"travelling toward {target} ({manhattan(pos, target)} tiles remaining)"

    elif atype == "gather":
        target_id = action.get("target_entity_id")
        kind = action.get("target_kind", "tree")
        live_target = entities.get(target_id) if target_id else None
        if not live_target or live_target.get("resource", 0) <= 0:
            new_action["status"] = "failed"
            advance_plan = True
            explanation = f"target {target_id} depleted or gone; abandoning gather"
        else:
            ticks_spent = action.get("ticks_spent", 0) + 1
            new_action["ticks_spent"] = ticks_spent
            touched_scope.append(target_id)
            preconditions.append({"entity_id": target_id, "field": "claimed_tick", "op": "neq", "value": tick})
            preconditions.append({"entity_id": target_id, "field": "resource", "op": "gte", "value": 1})
            if ticks_spent >= action.get("ticks_required", GATHER_TICKS):
                yield_amount = CARCASS_HARVEST_YIELD if kind == "carcass" else GATHER_YIELD
                amount = min(yield_amount, live_target["resource"])
                if kind == "carcass":
                    food_inventory += amount
                else:
                    inventory += amount
                new_action["status"] = "completed"
                advance_plan = True
                explanation = f"finished gathering {amount} {'meat' if kind == 'carcass' else 'wood'} from {target_id}"
                new_action[f"_{kind}_delta"] = {"id": target_id, "resource": live_target["resource"] - amount, "claimed_tick": tick}
            else:
                new_action["status"] = "performing"
                explanation = f"gathering from {target_id} ({ticks_spent}/{action.get('ticks_required', GATHER_TICKS)})"

    elif atype == "hunt_strike":
        animal_id = action.get("target_entity_id")
        live_animal = entities.get(animal_id) if animal_id else None
        if not live_animal or live_animal.get("type") != "animal" or not live_animal.get("alive", True):
            new_action["status"] = "failed"
            advance_plan = True
            explanation = f"hunt target {animal_id} gone or already dead; abandoning hunt"
        else:
            ticks_spent = action.get("ticks_spent", 0) + 1
            new_action["ticks_spent"] = ticks_spent
            touched_scope.append(animal_id)
            preconditions.append({"entity_id": animal_id, "field": "alive", "op": "eq", "value": True})
            if ticks_spent >= action.get("ticks_required", HUNT_TICKS):
                new_action["status"] = "completed"
                advance_plan = True
                new_health = max(0, live_animal.get("health", ANIMAL_MAX_HEALTH) - HUNT_DAMAGE)
                if new_health <= 0:
                    carcass_id = f"carcass-{animal_id.split('-')[-1]}-{tick}"
                    new_entities[carcass_id] = {
                        "type": "carcass", "position": dict(live_animal["position"]),
                        "resource": CARCASS_MEAT_YIELD, "max_resource": CARCASS_MEAT_YIELD,
                        "claimed_tick": None, "source_animal_id": animal_id, "spawned_tick": tick,
                    }
                    explanation = f"hunt strike killed {animal_id}; carcass {carcass_id} created"
                    new_action["_animal_delta"] = {
                        "id": animal_id, "health": 0, "alive": False, "current_goal": "DEAD", "injured": True,
                        "death_cause": "hunted", "death_tick": tick,
                        "action": {"type": "death", "status": "completed", "ticks_spent": 0, "flee_ticks_remaining": 0},
                    }
                else:
                    explanation = f"hunt strike injured {animal_id} (health {live_animal.get('health', ANIMAL_MAX_HEALTH)} -> {new_health})"
                    new_action["_animal_delta"] = {"id": animal_id, "health": new_health, "injured": True}
            else:
                new_action["status"] = "performing"
                explanation = f"hunting {animal_id} ({ticks_spent}/{action.get('ticks_required', HUNT_TICKS)})"

    elif atype == "eat":
        if food_inventory > 0:
            food_inventory -= 1
            hunger = max(0, hunger - MEAT_HUNGER_REDUCTION)
            explanation = "ate carried meat"
        elif inventory > 0:
            inventory -= 1
            hunger = max(0, hunger - 400)
            explanation = "ate from carried inventory"
        else:
            explanation = "no food carried; eat step had nothing to consume"
        new_action["status"] = "completed"
        advance_plan = True

    elif atype == "drink":
        if is_water_adjacent(pos, terrain):
            thirst = 0
            explanation = "drank from adjacent water"
        else:
            explanation = "not adjacent to water; drink step failed"
        new_action["status"] = "completed"
        advance_plan = True

    elif atype == "sleep":
        bonus = action.get("shelter_bonus") and has_shelter
        energy = min(1000, energy + (90 if bonus else 55))
        new_action["status"] = "performing"
        explanation = "sleeping at shelter" if bonus else "sleeping in the open"
        if energy >= SLEEP_ENERGY_TARGET:
            new_action["status"] = "completed"
            advance_plan = True
            explanation = "woke up fully rested"

    elif atype == "build_shelter":
        ticks_spent = action.get("ticks_spent", 0) + 1
        new_action["ticks_spent"] = ticks_spent
        if ticks_spent >= action.get("ticks_required", BUILD_TICKS):
            shelter_id = f"shelter-{eid.split('-')[-1]}-{tick}"
            new_entities[shelter_id] = {"type": "shelter", "position": dict(pos), "alive": True, "owner_id": eid}
            inventory = max(0, inventory - SHELTER_COST)
            has_shelter = True
            new_action["status"] = "completed"
            advance_plan = True
            explanation = f"finished building {shelter_id}"
        else:
            new_action["status"] = "performing"
            explanation = f"building shelter ({ticks_spent}/{action.get('ticks_required', BUILD_TICKS)})"

    else:  # wander
        dx, dy = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)])
        from core.geometry import is_passable
        candidate = {"x": pos["x"] + dx, "y": pos["y"] + dy}
        if is_passable(candidate, terrain):
            pos = candidate
        new_action["status"] = "completed"
        advance_plan = True
        explanation = "no urgent need; wandered one step"

    return {
        "pos": pos, "hunger": hunger, "thirst": thirst, "energy": energy, "inventory": inventory,
        "food_inventory": food_inventory, "has_shelter": has_shelter, "action": new_action,
        "advance_plan": advance_plan, "touched_scope": touched_scope, "preconditions": preconditions,
        "new_entities": new_entities, "event_type": atype, "explanation": explanation,
    }
