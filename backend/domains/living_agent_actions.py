"""Capability Stage 6C canonical physical actions and affordances.

Builders in this module operate on a pinned frame and return proposals only.
`validate_living_action_proposal` is called by Core before any mutation applies.
"""
from __future__ import annotations

import copy

from core.hashing import canonical_hash
from domains.living_agent_contracts import (
    ACTION_SCHEMA_VERSION,
    AFFORDANCE_SCHEMA_VERSION,
    LIMITS,
    PHYSICAL_ACTION_TYPES,
    SOCIAL_ACTION_TYPES,
    compat_action,
    default_affordances,
)


RUNTIME_ACTION_MAP = {
    "travel": "move",
    "wander": "move",
    "gather": "gather",
    "eat": "consume",
    "drink": "drink",
    "sleep": "rest",
    "build_shelter": "construct",
    "hunt_strike": "damage",
    "give_food": "give",
    "idle": "rest",
}

ESTABLISHED_ACTION_EFFECTS = {
    "travel": ("position_change", "tracks"),
    "wander": ("position_change", "tracks"),
    "gather": ("resource_depletion", "inventory_change", "noise", "debris"),
    "eat": ("inventory_change", "internal_state_change"),
    "drink": ("internal_state_change",),
    "sleep": ("internal_state_change",),
    "build_shelter": ("resource_change", "structure_created", "noise", "debris"),
    "hunt_strike": ("health_change", "damage", "noise"),
    "give_food": ("resource_change", "inventory_change", "social_signal"),
    "idle": ("internal_state_change",),
}

LIVING_ACTION_PROPOSAL_VERSION = "living-action-proposal-v1"
RESOURCE_TRANSFER_VERSION = "resource-transfer-v1"


def canonical_action_type(runtime_type: str | None) -> str:
    return RUNTIME_ACTION_MAP.get(runtime_type, runtime_type or "rest")


def established_action_effects(runtime_type: str | None) -> list[str]:
    return list(ESTABLISHED_ACTION_EFFECTS.get(runtime_type, ("canonical_state_change",)))


def living_action_metadata(action: dict, plan: dict | None = None) -> dict:
    plan = plan or {}
    action_type = canonical_action_type(action.get("type"))
    return {
        "schema_version": LIVING_ACTION_PROPOSAL_VERSION,
        "action_schema_version": ACTION_SCHEMA_VERSION,
        "action_id": action.get("action_id"),
        "action_type": action_type,
        "runtime_action_type": action.get("type"),
        "actor_id": action.get("actor_id"),
        "participants": list(action.get("participants") or []),
        "target_entity_ids": list(action.get("target_entity_ids") or []),
        "target_location": copy.deepcopy(action.get("target_pos")),
        "causal_goal_id": action.get("causal_goal_id") or plan.get("goal_id"),
        "plan_id": action.get("plan_id") or plan.get("plan_id"),
        "plan_step_index": int(action.get("plan_step_index", plan.get("step_index", 0))),
        "stage": action.get("current_stage") or action.get("status"),
        "required_tools": list(action.get("required_tools") or []),
        "required_resources": copy.deepcopy(action.get("required_resources") or {}),
        "reserved_resources": copy.deepcopy(action.get("reserved_resources") or {}),
        "start_tick": int(action.get("started_tick", 0)),
        "expected_duration": int(action.get("expected_duration", action.get("ticks_required", 0))),
        "progress": int(action.get("progress", 0)),
        "interruptible": bool(action.get("interruptible", True)),
        "interruption_cost": int(action.get("interruption_cost", 0)),
        "failure_conditions": list(action.get("failure_conditions") or []),
        "fallback": action.get("fallback"),
        "completion_outcome": copy.deepcopy(action.get("completion_outcome")),
        "cancellation_reason": action.get("cancellation_reason"),
        "resource_transfer": copy.deepcopy(action.get("resource_transfer")),
        "access_violation": bool(action.get("access_violation", False)),
        "physical_effects": list(
            action.get("physical_effects") or established_action_effects(action.get("type"))
        ),
        "source_proposal_ids": list(action.get("source_proposal_ids") or []),
        "accepted_event_ids": list(action.get("accepted_event_ids") or []),
    }


def _resources(entity: dict) -> dict:
    if isinstance(entity.get("carried_resources"), dict):
        return {str(key): max(0, int(value)) for key, value in entity["carried_resources"].items()}
    return {
        "wood": max(0, int(entity.get("inventory", 0))),
        "food": max(0, int(entity.get("food_inventory", 0))),
    }


def _contents(entity: dict) -> dict:
    return {
        str(key): max(0, int(value))
        for key, value in (entity.get("contents") or {}).items()
    }


def _quantity(entity: dict) -> tuple[str, int]:
    if "quantity" in entity:
        return "quantity", max(0, int(entity.get("quantity", 0)))
    return "resource", max(0, int(entity.get("resource", 0)))


def _same_or_adjacent(left: dict | None, right: dict | None) -> bool:
    if not left or not right:
        return False
    return abs(left["x"] - right["x"]) + abs(left["y"] - right["y"]) <= 1


def _can_access(actor_id: str, target: dict) -> bool:
    access = target.get("access", "public")
    return (
        access in ("public", "shared")
        or target.get("owner_id") == actor_id
        or actor_id in (target.get("permitted_entity_ids") or [])
    )


def _sync_legacy_resource_fields(update: dict, resources: dict) -> None:
    update["carried_resources"] = copy.deepcopy(resources)
    update["inventory"] = int(resources.get("wood", 0))
    update["food_inventory"] = int(resources.get("food", 0))


def _signal_spec(
    *,
    actor_id: str,
    action_id: str,
    action_type: str,
    tick: int,
    position: dict,
    signal_kind: str,
    strength: int,
    message: dict | None = None,
) -> tuple[str, dict]:
    signal_id = "signal-" + canonical_hash([
        actor_id, action_id, action_type, tick, signal_kind, position, message,
    ])[:16]
    spec = {
        "type": "signal",
        "schema_version": "physical-signal-v1",
        "position": copy.deepcopy(position),
        "signal_kind": signal_kind,
        "strength": max(0, min(1000, int(strength))),
        "source_entity_id": actor_id,
        "source_action_id": action_id,
        "source_event_id": None,
        "message": copy.deepcopy(message),
        "truth_status": "physical_evidence",
        "propagation_depth": 0,
        "created_tick": int(tick),
        "expires_tick": int(tick) + LIMITS.signal_lifetime_ticks,
        "affordances": default_affordances({"type": "signal"}),
    }
    return signal_id, spec


def evidence_signal_for_action(action: dict, *, position: dict, tick: int):
    # The established 5B GIVE_FOOD contract has an exact two-party touched
    # scope and accepted transfer provenance. Keep that public contract stable;
    # generic Stage 6 give/help/social actions use the signal path below.
    if action.get("type") == "give_food":
        return None
    effects = set(action.get("physical_effects") or established_action_effects(action.get("type")))
    if "noise" in effects:
        signal_kind, strength = "noise", 700
    elif "tracks" in effects:
        signal_kind, strength = "tracks", 420
    elif "social_signal" in effects:
        signal_kind, strength = "social", 500
    else:
        return None
    return _signal_spec(
        actor_id=action.get("actor_id"),
        action_id=action.get("action_id"),
        action_type=canonical_action_type(action.get("type")),
        tick=tick,
        position=position,
        signal_kind=signal_kind,
        strength=strength,
        message={
            "action_type": canonical_action_type(action.get("type")),
            "target_ids": list(action.get("target_entity_ids") or []),
        } if signal_kind == "social" else None,
    )


def social_signal_spec(
    *, actor_id: str, action_id: str, action_type: str, tick: int,
    position: dict, message: dict | None, recipient_ids: list[str],
    witness_ids: list[str], truth_status: str, propagation_depth: int = 0,
) -> tuple[str, dict]:
    signal_id, spec = _signal_spec(
        actor_id=actor_id,
        action_id=action_id,
        action_type=action_type,
        tick=tick,
        position=position,
        signal_kind="speech" if action_type in (
            "request_help", "offer_help", "refuse", "warn",
            "share_information", "lie", "apologise", "promise",
        ) else "social",
        strength=600,
        message=message,
    )
    spec["recipient_ids"] = sorted(set(recipient_ids))[:LIMITS.social_propagation_recipients]
    spec["witness_ids"] = sorted(set(witness_ids))[:LIMITS.witnesses_processed_per_event]
    spec["truth_status"] = truth_status
    spec["propagation_depth"] = min(int(propagation_depth), LIMITS.information_propagation_depth)
    return signal_id, spec


def _base_action(actor_id: str, action_type: str, tick: int, plan: dict | None, target_id: str | None) -> dict:
    plan = plan or {}
    action = compat_action(
        {
            "type": action_type,
            "status": "completed",
            "current_stage": "completed",
            "target_entity_id": target_id,
            "target_entity_ids": [target_id] if target_id else [],
            "target_pos": None,
            "ticks_spent": 1,
            "ticks_required": 1,
            "started_tick": tick,
            "interruptible": True,
            "progress": 1000,
            "physical_effects": [],
        },
        actor_id=actor_id,
        tick=tick,
        plan=plan,
    )
    return action


def build_physical_action_proposal(
    entities: dict,
    *,
    actor_id: str,
    action_type: str,
    tick: int,
    target_id: str | None = None,
    target_pos: dict | None = None,
    resource_kind: str = "wood",
    quantity: int = 1,
    tool_id: str | None = None,
    plan: dict | None = None,
    goal_id: str | None = None,
    allow_unauthorized: bool = False,
    message: dict | None = None,
) -> dict:
    """Build one complete deterministic physical-action proposal."""
    if action_type not in PHYSICAL_ACTION_TYPES:
        raise ValueError(f"unsupported physical action: {action_type}")
    actor = entities.get(actor_id)
    if not actor or actor.get("type") != "person":
        raise ValueError("physical action actor must be a person")
    quantity = max(1, int(quantity))
    target = entities.get(target_id) if target_id else None
    plan = copy.deepcopy(plan or {})
    if not plan.get("plan_id"):
        plan["plan_id"] = "plan-" + canonical_hash([actor_id, tick, action_type, target_id])[:16]
    if not plan.get("goal_id"):
        plan["goal_id"] = goal_id or "goal-" + canonical_hash([actor_id, tick, action_type])[:16]
    plan.setdefault("goal", action_type.upper())
    plan.setdefault("step_index", 0)
    if goal_id:
        plan["goal_id"] = goal_id
    action = _base_action(actor_id, action_type, tick, plan, target_id)
    action["target_pos"] = copy.deepcopy(target_pos or (target or {}).get("position"))
    updates = {actor_id: {}}
    new_entities = {}
    removed_entities = []
    touched = [actor_id]
    preconditions = [
        {"entity_id": actor_id, "field": "alive", "op": "eq", "value": True},
    ]
    effects = []
    resources = _resources(actor)
    actor_update = updates[actor_id]
    transfer = None

    def require_target():
        if target is None:
            raise ValueError(f"{action_type} requires target_id")
        if target_id not in touched:
            touched.append(target_id)

    def require_adjacent():
        require_target()
        if not _same_or_adjacent(actor.get("position"), target.get("position")):
            raise ValueError(f"{action_type} target must be adjacent")

    def apply_tool_wear(amount=1):
        if not tool_id:
            return
        tool = entities.get(tool_id)
        if not tool or tool.get("type") != "tool":
            raise ValueError("required tool missing")
        durability = max(0, int(tool.get("durability", 0)))
        updates[tool_id] = {"durability": max(0, durability - amount)}
        touched.append(tool_id)
        preconditions.append({"entity_id": tool_id, "field": "durability", "op": "gte", "value": amount})
        action["required_tools"] = [tool_id]
        effects.append("tool_wear")

    if action_type == "move":
        if target_pos is None:
            raise ValueError("move requires target_pos")
        if not _same_or_adjacent(actor.get("position"), target_pos):
            raise ValueError("move is limited to one adjacent step")
        actor_update["position"] = copy.deepcopy(target_pos)
        effects.extend(["position_change", "tracks"])

    elif action_type == "gather":
        require_adjacent()
        field, available = _quantity(target)
        amount = min(quantity, available)
        if amount <= 0:
            raise ValueError("gather target depleted")
        new_resources = copy.deepcopy(resources)
        new_resources[resource_kind] = new_resources.get(resource_kind, 0) + amount
        _sync_legacy_resource_fields(actor_update, new_resources)
        updates[target_id] = {field: available - amount}
        preconditions.extend([
            {"entity_id": actor_id, "field": "carried_resources", "op": "eq", "value": actor.get("carried_resources", resources)},
            {"entity_id": target_id, "field": field, "op": "gte", "value": amount},
        ])
        transfer = _transfer(actor_id=target_id, target_id=actor_id, resource_kind=resource_kind, quantity=amount,
                             source_before={resource_kind: available}, target_before=resources,
                             source_field=field, target_field="carried_resources")
        apply_tool_wear()
        effects.extend(["resource_depletion", "inventory_change", "noise", "debris"])

    elif action_type == "carry":
        require_adjacent()
        if target.get("type") not in ("tool", "item", "resource"):
            raise ValueError("target is not carryable")
        carried = list(actor.get("carried_item_ids") or [])
        if target_id not in carried:
            carried.append(target_id)
        actor_update["carried_item_ids"] = sorted(carried)
        updates[target_id] = {"carried_by": actor_id, "position": copy.deepcopy(actor["position"])}
        effects.extend(["possession_change", "inventory_change"])

    elif action_type in ("store", "retrieve", "give", "take"):
        require_adjacent()
        if action_type in ("store", "retrieve", "take") and target.get("type") not in ("storage", "container"):
            raise ValueError(f"{action_type} target must be storage")
        permitted = _can_access(actor_id, target)
        if not permitted and not (action_type == "take" and allow_unauthorized):
            raise ValueError("access denied")
        action["access_violation"] = not permitted
        if action_type in ("store", "give"):
            source_id, destination_id = actor_id, target_id
            source_map = resources
            destination_map = _resources(target) if action_type == "give" else _contents(target)
            source_field = "carried_resources"
            destination_field = "carried_resources" if action_type == "give" else "contents"
        else:
            source_id, destination_id = target_id, actor_id
            source_map = _contents(target)
            destination_map = resources
            source_field, destination_field = "contents", "carried_resources"
        if source_map.get(resource_kind, 0) < quantity:
            raise ValueError("insufficient resource")
        if action_type in ("store", "retrieve", "take"):
            capacity = int(target.get("capacity", 0))
            if action_type == "store" and sum(destination_map.values()) + quantity > capacity:
                raise ValueError("storage capacity exceeded")
        source_after = copy.deepcopy(source_map)
        destination_after = copy.deepcopy(destination_map)
        source_after[resource_kind] -= quantity
        destination_after[resource_kind] = destination_after.get(resource_kind, 0) + quantity
        if source_id == actor_id:
            _sync_legacy_resource_fields(actor_update, source_after)
        else:
            updates[source_id] = {source_field: source_after}
        if destination_id == actor_id:
            _sync_legacy_resource_fields(actor_update, destination_after)
        else:
            updates[destination_id] = {destination_field: destination_after}
            if destination_field == "carried_resources":
                updates[destination_id]["inventory"] = destination_after.get("wood", 0)
                updates[destination_id]["food_inventory"] = destination_after.get("food", 0)
        preconditions.extend([
            {"entity_id": source_id, "field": source_field, "op": "eq", "value": source_map},
            {"entity_id": destination_id, "field": destination_field, "op": "eq", "value": destination_map},
        ])
        transfer = _transfer(
            actor_id=source_id, target_id=destination_id, resource_kind=resource_kind,
            quantity=quantity, source_before=source_map, target_before=destination_map,
            source_field=source_field, target_field=destination_field,
        )
        effects.extend(["resource_change", "inventory_change", "ownership_or_possession_change"])

    elif action_type == "consume":
        if resources.get(resource_kind, 0) < quantity:
            raise ValueError("nothing consumable carried")
        after = copy.deepcopy(resources)
        after[resource_kind] -= quantity
        _sync_legacy_resource_fields(actor_update, after)
        actor_update["hunger"] = max(0, int(actor.get("hunger", 0)) - 400 * quantity)
        preconditions.append({"entity_id": actor_id, "field": "carried_resources", "op": "eq", "value": actor.get("carried_resources", resources)})
        effects.extend(["inventory_change", "internal_state_change"])

    elif action_type == "drink":
        if target_id:
            require_adjacent()
            if target.get("type") != "water_source":
                raise ValueError("drink target must be a water source")
        actor_update["thirst"] = 0
        effects.append("internal_state_change")

    elif action_type == "rest":
        actor_update["energy"] = min(1000, int(actor.get("energy", 0)) + 80)
        effects.append("internal_state_change")

    elif action_type == "use_tool":
        apply_tool_wear()
        effects.append("tool_use")

    elif action_type == "construct":
        if resources.get("wood", 0) < quantity:
            raise ValueError("insufficient construction material")
        after = copy.deepcopy(resources)
        after["wood"] -= quantity
        _sync_legacy_resource_fields(actor_update, after)
        structure_id = "structure-" + canonical_hash([actor_id, tick, target_pos, quantity])[:16]
        new_entities[structure_id] = {
            "type": "structure", "schema_version": "structure-v1",
            "structure_kind": "shelter", "position": copy.deepcopy(target_pos or actor["position"]),
            "condition": 1000, "max_condition": 1000, "owner_id": actor_id,
            "access": "private", "affordances": default_affordances({"type": "structure"}),
        }
        touched.append(structure_id)
        effects.extend(["resource_change", "structure_created", "debris", "noise"])

    elif action_type in ("repair", "damage"):
        require_adjacent()
        condition = int(target.get("condition", target.get("health", 0)))
        field = "condition" if "condition" in target else "health"
        delta = 120 if action_type == "repair" else -120
        if action_type == "repair":
            if resources.get("wood", 0) < quantity:
                raise ValueError("repair material unavailable")
            after = copy.deepcopy(resources)
            after["wood"] -= quantity
            _sync_legacy_resource_fields(actor_update, after)
        updates[target_id] = {field: max(0, min(int(target.get("max_condition", 1000)), condition + delta))}
        preconditions.append({"entity_id": target_id, "field": field, "op": "eq", "value": condition})
        apply_tool_wear()
        effects.extend(["condition_change", "tool_wear", "noise", "debris"])

    elif action_type in ("open", "access"):
        require_adjacent()
        if not _can_access(actor_id, target):
            raise ValueError("access denied")
        updates[target_id] = {"open": True}
        effects.append("access_change")

    elif action_type == "help":
        require_adjacent()
        if target.get("type") != "person" or not target.get("alive", True):
            raise ValueError("help target must be living person")
        updates[target_id] = {
            "health": min(1000, int(target.get("health", 1000)) + 50),
            "energy": min(1000, int(target.get("energy", 0)) + 40),
        }
        actor_update["energy"] = max(0, int(actor.get("energy", 0)) - 20)
        action["participants"] = [target_id]
        effects.extend(["health_change", "social_signal"])

    elif action_type in ("warn", "request", "refuse"):
        if target_id:
            require_adjacent()
            action["participants"] = [target_id]
        effects.extend(["new_knowledge_signal", "social_signal"])

    action["physical_effects"] = sorted(set(effects))
    if transfer:
        action["resource_transfer"] = transfer
    if tool_id:
        action["required_tools"] = [tool_id]
    action["completion_outcome"] = {"effects": action["physical_effects"]}
    actor_update["action"] = action
    actor_update["current_goal"] = (plan or {}).get("goal")

    # Meaningful actions leave bounded evidence that later observers can
    # perceive. Pure rest/drink/consume do not create a world signal.
    signal_kind = None
    if action_type == "move":
        signal_kind = "tracks"
    elif action_type in ("gather", "construct", "repair", "damage", "use_tool"):
        signal_kind = "noise"
    elif action_type in ("warn", "request", "refuse", "help", "give", "take"):
        signal_kind = "speech" if action_type in ("warn", "request", "refuse") else "social"
    if signal_kind and len(new_entities) < LIMITS.signal_entities_per_tick:
        signal_id, signal = _signal_spec(
            actor_id=actor_id, action_id=action["action_id"], action_type=action_type,
            tick=tick, position=actor.get("position") or target_pos,
            signal_kind=signal_kind, strength=700 if signal_kind == "noise" else 500,
            message=message or ({"action_type": action_type, "target_id": target_id} if signal_kind in ("speech", "social") else None),
        )
        new_entities[signal_id] = signal
        touched.append(signal_id)
        action["physical_effects"] = sorted(set(action["physical_effects"] + [signal_kind]))

    metadata = living_action_metadata(action, plan)
    return {
        "proposal_family": "living_agent_action",
        "proposal_type": f"living_{action_type}",
        "proposer_engine_id": "living_actions",
        "proposer_engine_version": "1.0.0",
        "entity_id": actor_id,
        "causal_parent_event_ids": sorted({
            event_id for event_id in (actor.get("last_event_id"), (target or {}).get("last_event_id"))
            if event_id
        }),
        "is_exogenous": not bool(actor.get("last_event_id") or (target or {}).get("last_event_id")),
        "requested_time": int(tick),
        "phase": "agent",
        "engine_priority": 10,
        "touched_scope": sorted(set(touched)),
        "preconditions": preconditions,
        "mutation": {
            "entity_updates": updates,
            "new_entities": new_entities,
            **({"removed_entities": removed_entities} if removed_entities else {}),
        },
        "living_action": metadata,
        "explanation": f"{actor_id} performs {action_type}",
    }


def _transfer(*, actor_id, target_id, resource_kind, quantity, source_before,
              target_before, source_field, target_field) -> dict:
    return {
        "schema_version": RESOURCE_TRANSFER_VERSION,
        "source_id": actor_id,
        "destination_id": target_id,
        "resource_kind": resource_kind,
        "quantity": int(quantity),
        "source_before": copy.deepcopy(source_before),
        "destination_before": copy.deepcopy(target_before),
        "source_field": source_field,
        "destination_field": target_field,
    }


def validate_living_action_proposal(proposal: dict, entities: dict) -> str | None:
    """Core-facing semantic validation for Stage 6 action metadata/mutations."""
    meta = proposal.get("living_action")
    if meta is None:
        return None
    if not isinstance(meta, dict) or meta.get("schema_version") != LIVING_ACTION_PROPOSAL_VERSION:
        return "living_action.invalid_version"
    action_type = meta.get("action_type")
    if action_type not in PHYSICAL_ACTION_TYPES | SOCIAL_ACTION_TYPES:
        return "living_action.invalid_type"
    actor_id = meta.get("actor_id")
    if not actor_id or actor_id != proposal.get("entity_id"):
        return "living_action.invalid_actor"
    actor = entities.get(actor_id)
    if not actor or actor.get("type") != "person" or not actor.get("alive", True):
        return "living_action.actor_unavailable"
    action_id = meta.get("action_id")
    if not action_id or not meta.get("plan_id") or not meta.get("causal_goal_id"):
        return "living_action.missing_causal_state"
    updates = (proposal.get("mutation") or {}).get("entity_updates") or {}
    action_update = (updates.get(actor_id) or {}).get("action")
    if not isinstance(action_update, dict) or action_update.get("action_id") != action_id:
        return "living_action.action_mismatch"
    if action_update.get("schema_version") != ACTION_SCHEMA_VERSION:
        return "living_action.invalid_action_schema"
    if len(meta.get("participants") or []) > LIMITS.social_propagation_recipients:
        return "living_action.participant_limit"
    target_ids = set(meta.get("target_entity_ids") or [])
    if not target_ids.issubset(set(proposal.get("touched_scope") or [])):
        return "living_action.invalid_scope"
    for tool_id in meta.get("required_tools") or []:
        tool = entities.get(tool_id)
        if not tool or tool.get("type") != "tool" or int(tool.get("durability", 0)) <= 0:
            return "living_action.tool_unavailable"
        if not _can_access(actor_id, tool) and tool.get("carried_by") != actor_id:
            return "living_action.tool_access_denied"

    transfer = meta.get("resource_transfer")
    if transfer:
        if transfer.get("schema_version") != RESOURCE_TRANSFER_VERSION:
            return "living_action.invalid_transfer_version"
        quantity = int(transfer.get("quantity", 0))
        if quantity <= 0:
            return "living_action.invalid_quantity"
        source_id = transfer.get("source_id")
        destination_id = transfer.get("destination_id")
        source_field = transfer.get("source_field")
        destination_field = transfer.get("destination_field")
        resource_kind = transfer.get("resource_kind")
        source_before = transfer.get("source_before") or {}
        destination_before = transfer.get("destination_before") or {}
        source_after = (updates.get(source_id) or {}).get(source_field)
        destination_after = (updates.get(destination_id) or {}).get(destination_field)
        if source_field in ("resource", "quantity"):
            # Gather uses a scalar source and a map destination.
            scalar_before = int((source_before or {}).get(resource_kind, 0))
            if (updates.get(source_id) or {}).get(source_field) != scalar_before - quantity:
                return "living_action.nonconserving_transfer"
        elif not isinstance(source_after, dict) or source_after.get(resource_kind) != source_before.get(resource_kind, 0) - quantity:
            return "living_action.nonconserving_transfer"
        if not isinstance(destination_after, dict) or destination_after.get(resource_kind) != destination_before.get(resource_kind, 0) + quantity:
            return "living_action.nonconserving_transfer"

    if action_type in ("store", "retrieve", "open", "access"):
        target_id = next(iter(target_ids), None)
        target = entities.get(target_id)
        if not target or not _can_access(actor_id, target):
            return "living_action.access_denied"
    if meta.get("progress", 0) < 0 or meta.get("progress", 0) > 1000:
        return "living_action.invalid_progress"
    if not meta.get("physical_effects") and action_type not in ("rest",):
        return "living_action.missing_consequence"
    return None
