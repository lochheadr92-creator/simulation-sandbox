"""Multi-stage actions + short plans (Phase 2; extended in Phase 4B with a
minimal hunting/carcass step for the survival food chain; Phase 5B navigation
stores canonical routes and advances them deterministically).

Canonical `action` shape:
    {"type", "status", "target_entity_id", "target_pos", "ticks_spent",
     "ticks_required", "interruptible", "started_tick", "arrival_action",
     "shelter_bonus", "target_kind",
     # travel route fields (Phase 5B; present when type == travel)
     "arrival_mode", "travel_purpose", "remaining_path", "route_length",
     "planned_from", "route_version", "unreachable", "invalidation_reason"}
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
from core.geometry import manhattan, is_water_adjacent, is_passable
from core.navigation import (
    ARRIVAL_ADJACENT, ARRIVAL_EXACT, ROUTE_VERSION,
    copy_pos, find_path, is_goal, pos_eq,
)
from core.constants import (GATHER_TICKS, BUILD_TICKS, SHELTER_COST, GATHER_YIELD,
                             SLEEP_ENERGY_TARGET, CRITICAL_THRESHOLD, HUNT_TICKS, HUNT_DAMAGE,
                             ANIMAL_MAX_HEALTH, CARCASS_MEAT_YIELD, CARCASS_HARVEST_YIELD,
                             MEAT_HUNGER_REDUCTION, FOOD_TRANSFER_QUANTITY,
                             FOOD_TRANSFER_SURPLUS, RETRIEVE_MAX_QUANTITY,
                             SURPLUS_KEEP_FOOD, SURPLUS_KEEP_WOOD, TRADE_CONTRACT_VERSION,
                             TRADE_MIN_RETAIN, TRADE_QUANTITY, TRADE_RANGE,
                             AID_CONTRACT_VERSION, AID_GIVER_MIN_FOOD,
                             AID_RECEIVER_MIN_HUNGER)
from domains.living_agent_contracts import compat_plan
from domains.living_agent_contracts import default_affordances

TRAVEL_STALL_LIMIT = 25  # deterministic safety net: abandon a travel step that
                          # cannot make progress rather than looping forever.

PLAN_STEPS = {
    "SEEK_WATER": ["TRAVEL_WATER", "DRINK"],
    "SEEK_FOOD": ["EAT"],                      # rewritten to a travel+gather variant in form_plan() if no food carried
    "SLEEP": ["SLEEP"],                        # rewritten to travel-then-sleep in form_plan() if a shelter is known
    "BUILD_SHELTER": ["TRAVEL_TREE", "GATHER", "TRAVEL_SITE", "BUILD"],
    "GATHER_SURPLUS": ["GATHER"],
    "HUNT": ["TRAVEL_ANIMAL", "HUNT_STRIKE"],   # Phase 4B: minimal survival food-chain extension
    "GIVE_FOOD": ["GIVE_FOOD"],
    "EXPLORE": ["TRAVEL_FRONTIER"],
    "WANDER": ["WANDER_STEP"],
    # Surplus Pass (SURPLUS_PASS.md): home-storage loop + barter trade.
    "GATHER_EXCESS": ["TRAVEL_EXCESS", "GATHER_EXCESS"],
    "STORE": ["TRAVEL_STORAGE", "STORE"],
    "RETRIEVE": ["TRAVEL_STORAGE", "RETRIEVE"],
    "OFFER_TRADE": ["OFFER_TRADE"],
}

# Travel step -> (arrival_mode, arrival_action or None)
# Passable destinations use exact-tile arrival; impassable water uses adjacent.
TRAVEL_ARRIVAL = {
    "TRAVEL_WATER": (ARRIVAL_ADJACENT, "DRINK"),
    "TRAVEL_TREE": (ARRIVAL_EXACT, "GATHER"),
    "TRAVEL_FOOD": (ARRIVAL_EXACT, "GATHER_FOOD"),
    "TRAVEL_SITE": (ARRIVAL_EXACT, "BUILD"),
    "TRAVEL_SHELTER": (ARRIVAL_EXACT, "SLEEP"),
    "TRAVEL_FRONTIER": (ARRIVAL_EXACT, None),
    "TRAVEL_ANIMAL": (ARRIVAL_EXACT, "HUNT_STRIKE"),
    "TRAVEL_EXCESS": (ARRIVAL_EXACT, "GATHER_EXCESS"),
    "TRAVEL_STORAGE": (ARRIVAL_EXACT, None),
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
        "food_recipient_id": action.get("target_entity_id"),
        "excess_target_id": action.get("target_entity_id"),
        "excess_target_pos": action.get("target_pos"),
        "excess_target_kind": action.get("target_kind", "tree"),
        "storage_target": action.get("target_pos"),
        "trade_partner_id": action.get("target_entity_id"),
        # Culture Pass: every OFFER_TRADE field must survive the
        # action -> context -> start_step round trip (surplus-pass defect
        # class: fields dropped here silently reset to defaults mid-plan).
        "trade_give_field": action.get("give_field"),
        "trade_receive_field": action.get("receive_field"),
        "trade_give_quantity": action.get("give_quantity"),
        "trade_receive_quantity": action.get("receive_quantity"),
        "trade_aid": bool(action.get("aid")),
    }


def form_plan(goal, e, context, tick, candidate=None, replan_of=None):
    steps = list(PLAN_STEPS.get(goal, ["WANDER_STEP"]))
    if goal == "SEEK_FOOD" and e["inventory"] <= 0 and e.get("food_inventory", 0) <= 0 and context.get("food_target_id"):
        steps = ["TRAVEL_FOOD", "GATHER_FOOD", "EAT"]
    if goal == "SLEEP" and context.get("shelter_target_id"):
        steps = ["TRAVEL_SHELTER", "SLEEP"]
    actor_id = e.get("id") or e.get("entity_id") or "legacy-person"
    plan = compat_plan(
        {
            "goal": goal,
            "goal_id": (candidate or {}).get("goal_id"),
            "steps": steps,
            "step_index": 0,
            "status": "active",
            "created_tick": tick,
            "replan_of": replan_of,
        },
        actor_id=actor_id,
        tick=tick,
    )
    return plan


def _bind_route(action, pos, terrain, arrival_mode, invalidation_reason=None):
    """Attach a freshly computed deterministic route to a travel action."""
    target = action.get("target_pos")
    path = find_path(pos, target, terrain, arrival_mode) if target is not None else None
    action["arrival_mode"] = arrival_mode
    action["planned_from"] = copy_pos(pos)
    action["route_version"] = ROUTE_VERSION
    action["invalidation_reason"] = invalidation_reason
    if path is None:
        action["remaining_path"] = []
        action["route_length"] = None
        action["unreachable"] = True
        return action, False
    action["remaining_path"] = [copy_pos(p) for p in path]
    action["route_length"] = len(path)
    action["unreachable"] = False
    return action, True


def start_step(step, e, eid, context, terrain, tick, pos):
    base = {"ticks_spent": 0, "interruptible": True, "started_tick": tick,
            "target_entity_id": None, "target_pos": None, "ticks_required": 0, "arrival_action": None}
    if step in TRAVEL_ARRIVAL:
        arrival_mode, arrival_action = TRAVEL_ARRIVAL[step]
        target = None
        target_entity_id = None
        target_kind = None
        if step == "TRAVEL_WATER":
            target = context.get("water_target")
        elif step == "TRAVEL_TREE":
            target_entity_id = context.get("tree_target_id")
            target = context.get("tree_target_pos")
        elif step == "TRAVEL_FOOD":
            target_entity_id = context.get("food_target_id")
            target = context.get("food_target_pos")
            target_kind = context.get("food_target_kind", "tree")
        elif step == "TRAVEL_SITE":
            target = context.get("shelter_site", pos)
        elif step == "TRAVEL_SHELTER":
            target_entity_id = context.get("shelter_target_id")
            target = context.get("shelter_target_pos")
        elif step == "TRAVEL_FRONTIER":
            target = context.get("frontier_target")
        elif step == "TRAVEL_ANIMAL":
            target_entity_id = context.get("animal_target_id")
            target = context.get("animal_target_pos")
        elif step == "TRAVEL_EXCESS":
            target_entity_id = context.get("excess_target_id")
            target = context.get("excess_target_pos")
            target_kind = context.get("excess_target_kind", "tree")
        elif step == "TRAVEL_STORAGE":
            target = context.get("storage_target")
        action = {
            **base,
            "type": "travel",
            "status": "travelling",
            "target_entity_id": target_entity_id,
            "target_pos": copy_pos(target) if target else None,
            "arrival_action": arrival_action,
            "travel_purpose": step,
        }
        if target_kind is not None:
            action["target_kind"] = target_kind
        action, _ok = _bind_route(action, pos, terrain, arrival_mode)
        return action
    if step == "GATHER":
        return {**base, "type": "gather", "status": "performing", "target_entity_id": context.get("tree_target_id"),
                "target_pos": copy_pos(context.get("tree_target_pos")) if context.get("tree_target_pos") else None,
                "ticks_required": GATHER_TICKS, "target_kind": "tree"}
    if step == "GATHER_FOOD":
        return {**base, "type": "gather", "status": "performing", "target_entity_id": context.get("food_target_id"),
                "target_pos": copy_pos(context.get("food_target_pos")) if context.get("food_target_pos") else None,
                "ticks_required": GATHER_TICKS,
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
                "target_pos": copy_pos(context.get("animal_target_pos")) if context.get("animal_target_pos") else None,
                "ticks_required": HUNT_TICKS}
    if step == "GIVE_FOOD":
        return {**base, "type": "give_food", "status": "performing",
                "target_entity_id": context.get("food_recipient_id"),
                "target_pos": dict(pos), "ticks_required": 1}
    if step == "GATHER_EXCESS":
        return {**base, "type": "gather_excess", "status": "performing",
                "target_entity_id": context.get("excess_target_id"),
                "target_pos": copy_pos(context.get("excess_target_pos")) if context.get("excess_target_pos") else None,
                "ticks_required": GATHER_TICKS,
                "target_kind": context.get("excess_target_kind", "tree")}
    if step == "STORE":
        return {**base, "type": "store", "status": "performing",
                "target_pos": dict(pos), "ticks_required": 1}
    if step == "RETRIEVE":
        return {**base, "type": "retrieve", "status": "performing",
                "target_pos": dict(pos), "ticks_required": 1}
    if step == "OFFER_TRADE":
        # Culture Pass: quantities come from the agent's norm tuple (defaults
        # keep pre-culture actions valid); aid offers are one-sided gifts
        # (receive_field None, receive_quantity 0) under the aid contract.
        aid = bool(context.get("trade_aid"))
        return {**base, "type": "offer_trade", "status": "performing",
                "target_entity_id": context.get("trade_partner_id"),
                "give_field": context.get("trade_give_field"),
                "receive_field": None if aid else context.get("trade_receive_field"),
                "give_quantity": int(context.get("trade_give_quantity") or TRADE_QUANTITY),
                "receive_quantity": 0 if aid else int(context.get("trade_receive_quantity") or TRADE_QUANTITY),
                "aid": aid,
                "target_pos": dict(pos), "ticks_required": 1}
    return {**base, "type": "wander", "status": "performing"}


def _validate_travel_route(action, pos, target, terrain, arrival_mode, entities):
    """Return (invalidation_reason_or_None, updated_target).

    Recompute is allowed only when a reason is returned (caller recomputes once).
    """
    if not target:
        return "missing_target", target

    tid = action.get("target_entity_id")
    if tid:
        live = entities.get(tid)
        if not live:
            return "target_disappeared", target
        if live.get("type") == "animal" and not live.get("alive", True):
            return "target_disappeared", target
        if live.get("type") in ("tree", "carcass") and live.get("resource", 0) <= 0:
            return "target_disappeared", target
        live_pos = live.get("position")
        if live_pos is not None and not pos_eq(live_pos, target):
            return "target_moved", copy_pos(live_pos)

    if action.get("unreachable"):
        return "destination_unreachable", target

    if is_goal(pos, target, arrival_mode):
        return None, target  # already arrived; no invalidation

    remaining = action.get("remaining_path") or []
    if not remaining:
        return "route_exhausted", target

    if action.get("route_version") != ROUTE_VERSION:
        return "route_version_mismatch", target

    next_step = remaining[0]
    if not is_passable(next_step, terrain):
        return "next_tile_impassable", target
    if manhattan(pos, next_step) != 1:
        return "position_desync", target

    return None, target


def _execute_travel(e, action, entities, terrain):
    """Advance travel by at most one deterministic route step."""
    pos = dict(e["position"])
    new_action = dict(action)
    target = copy_pos(action.get("target_pos"))
    arrival_mode = action.get("arrival_mode") or ARRIVAL_EXACT
    # Legacy safety: DRINK-bound travel without arrival_mode is adjacent.
    if action.get("arrival_mode") is None and action.get("arrival_action") == "DRINK":
        arrival_mode = ARRIVAL_ADJACENT
        new_action["arrival_mode"] = arrival_mode

    inv_reason, target = _validate_travel_route(new_action, pos, target, terrain, arrival_mode, entities)
    recomputed = False
    recompute_reason = None

    if inv_reason in ("target_disappeared", "missing_target"):
        new_action["status"] = "failed"
        new_action["invalidation_reason"] = inv_reason
        new_action["target_pos"] = target
        return {
            "pos": pos, "action": new_action, "advance_plan": True,
            "explanation": f"travel failed: {inv_reason}",
        }

    if inv_reason is not None:
        # Explicit recompute under the recorded reason (not silent every tick).
        recompute_reason = inv_reason
        new_action["target_pos"] = target
        new_action, ok = _bind_route(new_action, pos, terrain, arrival_mode, invalidation_reason=inv_reason)
        recomputed = True
        if not ok:
            new_action["status"] = "failed"
            return {
                "pos": pos, "action": new_action, "advance_plan": True,
                "explanation": f"route invalidated ({inv_reason}); no alternate path to {target}",
            }

    if is_goal(pos, target, arrival_mode):
        new_action["status"] = "completed"
        new_action["remaining_path"] = []
        new_action["invalidation_reason"] = None
        return {
            "pos": pos, "action": new_action, "advance_plan": True,
            "explanation": f"arrived at {target} (mode={arrival_mode})",
        }

    if action.get("ticks_spent", 0) >= TRAVEL_STALL_LIMIT:
        new_action["status"] = "failed"
        new_action["invalidation_reason"] = "travel_stall_limit"
        return {
            "pos": pos, "action": new_action, "advance_plan": True,
            "explanation": f"unable to make progress toward {target} after {TRAVEL_STALL_LIMIT} ticks; abandoning",
        }

    remaining = list(new_action.get("remaining_path") or [])
    if not remaining:
        new_action["status"] = "failed"
        new_action["invalidation_reason"] = "route_exhausted"
        return {
            "pos": pos, "action": new_action, "advance_plan": True,
            "explanation": f"route exhausted before arrival at {target}",
        }

    next_step = remaining[0]
    pos = copy_pos(next_step)
    remaining = remaining[1:]
    new_action["remaining_path"] = remaining
    new_action["ticks_spent"] = action.get("ticks_spent", 0) + 1
    new_action["status"] = "travelling"
    # Keep invalidation_reason only on the recompute tick for inspector visibility.
    new_action["invalidation_reason"] = recompute_reason

    left = len(remaining)
    purpose = new_action.get("travel_purpose") or "travel"
    arrival = new_action.get("arrival_action")
    bits = []
    if recomputed:
        bits.append(f"route recomputed ({recompute_reason})")
    bits.append(f"travelling ({purpose}) toward {target}")
    bits.append(f"{left} route steps remaining")
    if arrival:
        bits.append(f"then {arrival}")

    return {
        "pos": pos, "action": new_action, "advance_plan": False,
        "explanation": "; ".join(bits),
    }


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
    # Surplus Pass: home-store map, tracked only for surplus-enabled persons
    # (None keeps legacy proposals byte-identical; see SURPLUS_PASS.md).
    stored = (
        dict(e.get("stored_resources") or {"wood": 0, "food": 0})
        if e.get("storage_location") is not None else None
    )

    touched_scope = [eid]
    preconditions = []
    new_entities = {}
    advance_plan = False
    new_action = dict(action)
    explanation = ""
    atype = action["type"]

    if atype == "travel":
        travel = _execute_travel(e, action, entities, terrain)
        pos = travel["pos"]
        new_action = travel["action"]
        advance_plan = travel["advance_plan"]
        explanation = travel["explanation"]

    elif atype in ("gather", "gather_excess"):
        target_id = action.get("target_entity_id")
        kind = action.get("target_kind", "tree")
        live_target = entities.get(target_id) if target_id else None
        if not live_target or live_target.get("resource", 0) <= 0:
            new_action["status"] = "failed"
            advance_plan = True
            explanation = f"target {target_id} depleted or gone; abandoning {atype}"
        else:
            ticks_spent = action.get("ticks_spent", 0) + 1
            new_action["ticks_spent"] = ticks_spent
            touched_scope.append(target_id)
            preconditions.append({"entity_id": target_id, "field": "claimed_tick", "op": "neq", "value": tick})
            preconditions.append({"entity_id": target_id, "field": "resource", "op": "gte", "value": 1})
            if ticks_spent >= action.get("ticks_required", GATHER_TICKS):
                yield_amount = CARCASS_HARVEST_YIELD if kind == "carcass" else GATHER_YIELD
                amount = min(yield_amount, live_target["resource"])
                # Carry capacity binds every surplus-enabled gather, and is the
                # defining bound of gather_excess (legacy gathers stay unbounded).
                capacity_bounded = atype == "gather_excess" or e.get("storage_location") is not None
                if capacity_bounded:
                    capacity = int(e.get("inventory_capacity", 30))
                    room = capacity - (inventory + food_inventory)
                    amount = min(amount, max(0, room))
                if amount <= 0 and capacity_bounded:
                    new_action["status"] = "failed"
                    advance_plan = True
                    explanation = f"carry capacity full; abandoning {atype} on {target_id}"
                else:
                    if kind == "carcass":
                        food_inventory += amount
                    else:
                        inventory += amount
                    new_action["status"] = "completed"
                    advance_plan = True
                    explanation = f"finished gathering {amount} {'meat' if kind == 'carcass' else 'wood'} from {target_id}"
                    delta = {"id": target_id, "resource": live_target["resource"] - amount, "claimed_tick": tick}
                    if atype == "gather_excess":
                        delta["resource_ownership"] = eid
                    new_action[f"_{kind}_delta"] = delta
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

    elif atype == "give_food":
        receiver_id = action.get("target_entity_id")
        receiver = entities.get(receiver_id) if receiver_id else None
        # The Core revalidates the full contract.  This domain-side branch only
        # builds the candidate mutation from the pinned activation frame.
        if receiver:
            food_inventory -= FOOD_TRANSFER_QUANTITY
            touched_scope.append(receiver_id)
            preconditions.extend([
                {"entity_id": eid, "field": "food_inventory", "op": "gte", "value": FOOD_TRANSFER_SURPLUS},
                {"entity_id": receiver_id, "field": "alive", "op": "eq", "value": True},
                {"entity_id": receiver_id, "field": "hunger", "op": "gte", "value": CRITICAL_THRESHOLD},
                {"entity_id": receiver_id, "field": "food_inventory", "op": "eq", "value": 0},
                {"entity_id": receiver_id, "field": "inventory", "op": "eq", "value": 0},
            ])
            new_action["_food_transfer"] = {
                "contract_version": "food-transfer-v1",
                "giver_id": eid,
                "receiver_id": receiver_id,
                "field": "food_inventory",
                "quantity": FOOD_TRANSFER_QUANTITY,
                "receiver_food_inventory": receiver.get("food_inventory", 0),
            }
            explanation = f"gave {FOOD_TRANSFER_QUANTITY} food to {receiver_id}"
        else:
            explanation = "food recipient unavailable; transfer proposal will be rejected"
        new_action["status"] = "completed"
        advance_plan = True

    elif atype == "store":
        storage_pos = e.get("storage_location")
        if stored is None or not storage_pos or manhattan(pos, storage_pos) != 0:
            new_action["status"] = "failed"
            advance_plan = True
            explanation = "not at storage location; store failed"
        else:
            wood_deposit = max(0, inventory - SURPLUS_KEEP_WOOD)
            food_deposit = max(0, food_inventory - SURPLUS_KEEP_FOOD)
            if wood_deposit or food_deposit:
                inventory -= wood_deposit
                food_inventory -= food_deposit
                stored["wood"] = stored.get("wood", 0) + wood_deposit
                stored["food"] = stored.get("food", 0) + food_deposit
                preconditions.append({
                    "entity_id": eid, "field": "stored_resources", "op": "eq",
                    "value": dict(e.get("stored_resources") or {"wood": 0, "food": 0}),
                })
                explanation = f"stored surplus at home ({wood_deposit} wood, {food_deposit} meat)"
            else:
                explanation = "no surplus above keep thresholds; nothing stored"
            new_action["status"] = "completed"
            advance_plan = True

    elif atype == "retrieve":
        storage_pos = e.get("storage_location")
        if stored is None or not storage_pos or manhattan(pos, storage_pos) != 0:
            new_action["status"] = "failed"
            advance_plan = True
            explanation = "not at storage location; retrieve failed"
        else:
            capacity = int(e.get("inventory_capacity", 30))
            room = max(0, capacity - (inventory + food_inventory))
            qty = min(RETRIEVE_MAX_QUANTITY, int(stored.get("food", 0)), room)
            if qty > 0:
                stored["food"] = stored.get("food", 0) - qty
                food_inventory += qty
                preconditions.append({
                    "entity_id": eid, "field": "stored_resources", "op": "eq",
                    "value": dict(e.get("stored_resources") or {"wood": 0, "food": 0}),
                })
                explanation = f"retrieved {qty} meat from home storage"
            else:
                explanation = "nothing retrievable (store empty or carry full)"
            new_action["status"] = "completed"
            advance_plan = True

    elif atype == "offer_trade":
        partner_id = action.get("target_entity_id")
        partner = entities.get(partner_id) if partner_id else None
        give_field = action.get("give_field")
        receive_field = action.get("receive_field")
        give_qty = int(action.get("give_quantity", TRADE_QUANTITY))
        aid = bool(action.get("aid"))
        receive_qty = 0 if aid else int(action.get("receive_quantity", TRADE_QUANTITY))
        # Culture Pass: aid terms are one-sided (food gift, nothing back).
        terms_ok = give_field in ("inventory", "food_inventory") and (
            (aid and give_field == "food_inventory" and receive_field is None)
            or (not aid and receive_field in ("inventory", "food_inventory")
                and give_field != receive_field)
        )
        if (
            not partner or partner.get("type") != "person" or not partner.get("alive", True)
            or manhattan(pos, partner.get("position", {})) > TRADE_RANGE
            or not terms_ok
        ):
            new_action["status"] = "failed"
            advance_plan = True
            explanation = f"trade partner {partner_id} unavailable or out of range; abandoning offer"
        elif aid:
            # Aid (people-aid-v1): a one-sided meat gift to a hungry ally.
            # Bypasses barter reciprocity but decrements the giver's surplus.
            food_inventory -= give_qty
            touched_scope.append(partner_id)
            preconditions.extend([
                {"entity_id": eid, "field": "food_inventory", "op": "gte", "value": AID_GIVER_MIN_FOOD},
                {"entity_id": partner_id, "field": "alive", "op": "eq", "value": True},
                {"entity_id": partner_id, "field": "hunger", "op": "gte", "value": AID_RECEIVER_MIN_HUNGER},
                {"entity_id": partner_id, "field": "food_inventory", "op": "eq", "value": partner.get("food_inventory", 0)},
                {"entity_id": partner_id, "field": "inventory", "op": "eq", "value": partner.get("inventory", 0)},
                {"entity_id": partner_id, "field": "position", "op": "eq", "value": dict(partner.get("position") or {})},
            ])
            new_action["_trade"] = {
                "contract_version": AID_CONTRACT_VERSION,
                "giver_id": eid,
                "receiver_id": partner_id,
                "give_field": give_field,
                "give_quantity": give_qty,
                "receive_field": None,
                "receive_quantity": 0,
                "receiver_food_inventory": partner.get("food_inventory", 0),
                "receiver_inventory": partner.get("inventory", 0),
            }
            explanation = f"gave {give_qty} meat to {partner_id} (aid, no reciprocity expected)"
            new_action["status"] = "completed"
            advance_plan = True
        else:
            if give_field == "inventory":
                inventory -= give_qty
            else:
                food_inventory -= give_qty
            if receive_field == "inventory":
                inventory += receive_qty
            else:
                food_inventory += receive_qty
            touched_scope.append(partner_id)
            preconditions.extend([
                {"entity_id": eid, "field": give_field, "op": "gte", "value": give_qty + TRADE_MIN_RETAIN},
                {"entity_id": partner_id, "field": "alive", "op": "eq", "value": True},
                # Culture Pass (S5): the receiver's post-trade retain is
                # pinned too — norm-priced receive quantities can exceed
                # TRADE_QUANTITY, where TRADE_MIN_SURPLUS alone no longer
                # implies retain.
                {"entity_id": partner_id, "field": receive_field, "op": "gte", "value": receive_qty + TRADE_MIN_RETAIN},
                {"entity_id": partner_id, "field": "food_inventory", "op": "eq", "value": partner.get("food_inventory", 0)},
                {"entity_id": partner_id, "field": "inventory", "op": "eq", "value": partner.get("inventory", 0)},
                {"entity_id": partner_id, "field": "position", "op": "eq", "value": dict(partner.get("position") or {})},
            ])
            new_action["_trade"] = {
                "contract_version": TRADE_CONTRACT_VERSION,
                "giver_id": eid,
                "receiver_id": partner_id,
                "give_field": give_field,
                "give_quantity": give_qty,
                "receive_field": receive_field,
                "receive_quantity": receive_qty,
                "receiver_food_inventory": partner.get("food_inventory", 0),
                "receiver_inventory": partner.get("inventory", 0),
            }
            explanation = f"traded {give_qty} {give_field} for {receive_qty} {receive_field} with {partner_id}"
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
            shelter = {
                "type": "shelter", "position": dict(pos), "alive": True,
                "owner_id": eid, "access": "private", "condition": 1000,
                "max_condition": 1000,
            }
            shelter["affordances"] = default_affordances(shelter)
            new_entities[shelter_id] = shelter
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
        candidate = {"x": pos["x"] + dx, "y": pos["y"] + dy}
        if is_passable(candidate, terrain):
            pos = candidate
        new_action["status"] = "completed"
        advance_plan = True
        explanation = "no urgent need; wandered one step"

    return {
        "pos": pos, "hunger": hunger, "thirst": thirst, "energy": energy, "inventory": inventory,
        "food_inventory": food_inventory, "has_shelter": has_shelter, "action": new_action,
        "stored_resources": stored,
        "advance_plan": advance_plan, "touched_scope": touched_scope, "preconditions": preconditions,
        "new_entities": new_entities, "event_type": atype, "explanation": explanation,
    }
