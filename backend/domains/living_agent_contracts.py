"""Capability Stage 6 canonical contracts and deterministic bounds.

This module contains shapes and compatibility helpers only.  It has no storage
access and never mutates the supplied entity.  Domain engines may use the
helpers to build proposals; Core remains the only canonical mutation authority.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from core.hashing import canonical_hash


LIVING_AGENT_SCHEMA_VERSION = "living-agent-v1"
PRESSURE_SCHEMA_VERSION = "internal-pressure-v1"
WANT_SCHEMA_VERSION = "want-v1"
MEMORY_SCHEMA_VERSION = "agent-memory-v1"
RELATIONSHIP_SCHEMA_VERSION = "relationship-v1"
COMMITMENT_SCHEMA_VERSION = "commitment-v1"
DECISION_RECEIPT_VERSION = "decision-receipt-v1"
PLAN_SCHEMA_VERSION = "living-plan-v1"
ACTION_SCHEMA_VERSION = "living-action-v1"
AFFORDANCE_SCHEMA_VERSION = "affordance-v1"


PRESSURE_KINDS = (
    "thirst",
    "hunger",
    "fatigue",
    "exposure",
    "pain",
    "injury_severity",
    "safety",
    "comfort",
    "social_contact",
    "belonging",
    "curiosity",
    "attachment",
    "fear",
    "perceived_obligation",
)

TRAIT_KINDS = (
    "risk_tolerance",
    "sociability",
    "curiosity",
    "persistence",
    "generosity",
    "caution",
    "comfort_preference",
    "obligation_sensitivity",
)

PHYSICAL_ACTION_TYPES = frozenset({
    "move", "gather", "carry", "store", "retrieve", "consume", "drink",
    "rest", "use_tool", "construct", "repair", "damage", "open", "access",
    "give", "take", "help", "warn", "request", "refuse",
})

SOCIAL_ACTION_TYPES = frozenset({
    "request_help", "offer_help", "cooperate", "refuse", "warn",
    "share_information", "conceal_information", "lie", "give", "trade",
    "threaten", "apologise", "promise", "repay", "confront", "compete",
    "reconcile",
})

KNOWLEDGE_PROVENANCE_TYPES = frozenset({
    "direct", "remembered", "inferred", "reported", "rumoured",
})


@dataclass(frozen=True)
class LivingAgentLimits:
    memories_per_entity: int = 32
    memories_per_subject: int = 8
    perceived_entities_per_observation: int = 24
    perceived_objects_per_observation: int = 24
    candidate_goals_per_decision: int = 16
    planning_depth: int = 8
    planning_branches: int = 2
    fallback_depth: int = 2
    active_plans_per_entity: int = 1
    active_actions_per_entity: int = 1
    relationship_records: int = 16
    commitments_per_entity: int = 12
    social_propagation_recipients: int = 4
    information_propagation_depth: int = 2
    witnesses_processed_per_event: int = 8
    causal_links_retained: int = 32
    decision_receipts_retained: int = 12
    diagnostic_records_retained: int = 16
    signal_entities_per_tick: int = 16
    signal_lifetime_ticks: int = 4
    long_run_test_ticks: int = 320


LIMITS = LivingAgentLimits()


class LivingAgentCompatibilityError(ValueError):
    """Raised when canonical Stage 6 state cannot be interpreted safely."""


def _bounded_int(value, low=0, high=1000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = low
    return max(low, min(high, parsed))


def _stable_id(prefix: str, *parts) -> str:
    digest = canonical_hash([str(part) for part in parts])[:16]
    return f"{prefix}-{digest}"


def seeded_traits(entity_id: str, rng) -> dict:
    """Return stable per-entity traits from one Core-issued named stream."""
    stream = rng.stream(f"living_agent.traits.{entity_id}.{LIVING_AGENT_SCHEMA_VERSION}")
    return {
        "schema_version": LIVING_AGENT_SCHEMA_VERSION,
        **{name: stream.randint(25, 75) for name in TRAIT_KINDS},
    }


def default_traits(entity_id: str) -> dict:
    """Deterministic no-RNG compatibility fallback for direct unit callers."""
    values = {}
    for name in TRAIT_KINDS:
        digest = canonical_hash([LIVING_AGENT_SCHEMA_VERSION, entity_id, name])
        values[name] = 25 + (int(digest[:8], 16) % 51)
    return {"schema_version": LIVING_AGENT_SCHEMA_VERSION, **values}


def empty_pressure(kind: str, *, weight: int, tick: int) -> dict:
    if kind not in PRESSURE_KINDS:
        raise ValueError(f"unknown pressure kind: {kind}")
    return {
        "schema_version": PRESSURE_SCHEMA_VERSION,
        "kind": kind,
        "severity": 0,
        "rate_of_change": 0,
        "predicted_severity": 0,
        "tolerance": 500,
        "urgency": 0,
        "recent_satisfaction": 0,
        "individual_weight": _bounded_int(weight, 1, 200),
        "source": "compatibility_default",
        "last_meaningful_change_tick": int(tick),
    }


def _pressure_weight(kind: str, traits: dict) -> int:
    if kind == "curiosity":
        return 50 + traits["curiosity"]
    if kind in ("social_contact", "belonging", "attachment"):
        return 50 + traits["sociability"]
    if kind == "perceived_obligation":
        return 50 + traits["obligation_sensitivity"]
    if kind == "comfort":
        return 50 + traits["comfort_preference"]
    if kind in ("fear", "safety"):
        return 50 + traits["caution"]
    return 100


def empty_living_agent_state(entity_id: str, tick: int, rng=None) -> dict:
    traits = seeded_traits(entity_id, rng) if rng is not None else default_traits(entity_id)
    pressures = {
        kind: empty_pressure(kind, weight=_pressure_weight(kind, traits), tick=tick)
        for kind in PRESSURE_KINDS
    }
    return {
        "schema_version": LIVING_AGENT_SCHEMA_VERSION,
        "traits": traits,
        "pressures": pressures,
        "wants": {},
        "memories": {},
        "relationships": {},
        "commitments": {},
        "current_decision": None,
        "decision_history": [],
        "causal_links": [],
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
    }


def _bounded_dict(value, limit: int, *, tick_field: str) -> dict:
    if not isinstance(value, dict):
        return {}
    ranked = sorted(
        ((str(key), copy.deepcopy(item)) for key, item in value.items() if isinstance(item, dict)),
        key=lambda pair: (int(pair[1].get(tick_field, 0)), pair[0]),
        reverse=True,
    )[:limit]
    return {key: item for key, item in sorted(ranked, key=lambda pair: pair[0])}


def _compat_pressure(kind: str, value: dict | None, traits: dict, tick: int) -> dict:
    base = empty_pressure(kind, weight=_pressure_weight(kind, traits), tick=tick)
    if isinstance(value, dict):
        if value.get("schema_version") not in (None, PRESSURE_SCHEMA_VERSION):
            raise LivingAgentCompatibilityError(
                f"unsupported pressure schema for {kind}: {value.get('schema_version')}"
            )
        for field in base:
            if field in value:
                base[field] = copy.deepcopy(value[field])
    base["schema_version"] = PRESSURE_SCHEMA_VERSION
    base["kind"] = kind
    for field in (
        "severity", "predicted_severity", "tolerance", "urgency",
        "recent_satisfaction",
    ):
        base[field] = _bounded_int(base[field])
    base["rate_of_change"] = _bounded_int(base["rate_of_change"], -1000, 1000)
    base["individual_weight"] = _bounded_int(base["individual_weight"], 1, 200)
    base["last_meaningful_change_tick"] = int(base["last_meaningful_change_tick"])
    return base


def compat_living_agent_state(existing: dict | None, entity_id: str, tick: int, rng=None) -> dict:
    """Copy and normalize Stage 6 state without inventing observations or events."""
    if not existing:
        return empty_living_agent_state(entity_id, tick, rng)
    if not isinstance(existing, dict):
        raise LivingAgentCompatibilityError("living_agent state must be an object")
    version = existing.get("schema_version")
    if version != LIVING_AGENT_SCHEMA_VERSION:
        raise LivingAgentCompatibilityError(f"unsupported living-agent schema: {version}")

    state = empty_living_agent_state(entity_id, existing.get("created_tick", tick), rng)
    supplied_traits = existing.get("traits")
    if isinstance(supplied_traits, dict):
        if supplied_traits.get("schema_version") not in (None, LIVING_AGENT_SCHEMA_VERSION):
            raise LivingAgentCompatibilityError(
                f"unsupported trait schema: {supplied_traits.get('schema_version')}"
            )
        for name in TRAIT_KINDS:
            if name in supplied_traits:
                state["traits"][name] = _bounded_int(supplied_traits[name], 0, 100)

    state["pressures"] = {
        kind: _compat_pressure(
            kind,
            (existing.get("pressures") or {}).get(kind),
            state["traits"],
            tick,
        )
        for kind in PRESSURE_KINDS
    }
    state["wants"] = _bounded_dict(
        existing.get("wants"), LIMITS.candidate_goals_per_decision,
        tick_field="last_updated_tick",
    )
    state["memories"] = _bounded_dict(
        existing.get("memories"), LIMITS.memories_per_entity,
        tick_field="last_recalled_tick",
    )
    state["relationships"] = _bounded_dict(
        existing.get("relationships"), LIMITS.relationship_records,
        tick_field="last_changed_tick",
    )
    state["commitments"] = _bounded_dict(
        existing.get("commitments"), LIMITS.commitments_per_entity,
        tick_field="last_changed_tick",
    )
    history = existing.get("decision_history")
    state["decision_history"] = copy.deepcopy(history[-LIMITS.decision_receipts_retained:]) \
        if isinstance(history, list) else []
    state["current_decision"] = copy.deepcopy(existing.get("current_decision"))
    links = existing.get("causal_links")
    state["causal_links"] = copy.deepcopy(links[-LIMITS.causal_links_retained:]) \
        if isinstance(links, list) else []
    state["last_updated_tick"] = int(existing.get("last_updated_tick", tick))
    return state


def compat_plan(plan: dict | None, *, actor_id: str, tick: int) -> dict:
    """Upgrade legacy Phase 2 plans to the versioned Stage 6 shape."""
    plan = copy.deepcopy(plan) if isinstance(plan, dict) else {}
    steps = list(plan.get("steps") or [])[:LIMITS.planning_depth]
    goal = plan.get("goal")
    created_tick = int(plan.get("created_tick", tick))
    plan_id = plan.get("plan_id") or _stable_id("plan", actor_id, created_tick, goal, steps)
    step_records = plan.get("step_records")
    if not isinstance(step_records, list) or len(step_records) != len(steps):
        step_records = [
            {
                "index": index,
                "step_type": step,
                "status": "completed" if index < int(plan.get("step_index", 0)) else "pending",
                "prerequisites": [],
                "required_participants": [],
                "required_tools": [],
                "required_resources": {},
                "fallback_step": None,
            }
            for index, step in enumerate(steps)
        ]
    return {
        **plan,
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_id": plan_id,
        "goal": goal,
        "goal_id": plan.get("goal_id") or (
            _stable_id("goal", actor_id, created_tick, goal) if goal else None
        ),
        "steps": steps,
        "step_records": step_records[:LIMITS.planning_depth],
        "step_index": min(max(0, int(plan.get("step_index", 0))), len(steps)),
        "status": plan.get("status", "completed" if not steps else "active"),
        "created_tick": created_tick,
        "branch_count": min(int(plan.get("branch_count", 0)), LIMITS.planning_branches),
        "fallback_depth": min(int(plan.get("fallback_depth", 0)), LIMITS.fallback_depth),
        "failure_reason": plan.get("failure_reason"),
        "replan_of": plan.get("replan_of"),
    }


def compat_action(action: dict | None, *, actor_id: str, tick: int, plan: dict | None = None) -> dict:
    """Upgrade legacy actions while retaining every established field."""
    action = copy.deepcopy(action) if isinstance(action, dict) else {}
    plan = plan or {}
    started_tick = int(action.get("started_tick", tick))
    action_type = action.get("type", "idle")
    required = max(0, int(action.get("ticks_required", 0)))
    spent = max(0, int(action.get("ticks_spent", 0)))
    progress = 1000 if action.get("status") == "completed" else (
        min(1000, (spent * 1000) // required) if required else 0
    )
    return {
        **action,
        "schema_version": ACTION_SCHEMA_VERSION,
        "action_id": action.get("action_id") or _stable_id(
            "action", actor_id, started_tick, action_type, plan.get("plan_id"), plan.get("step_index", 0),
        ),
        "type": action_type,
        "actor_id": actor_id,
        "participants": list(action.get("participants") or [])[:LIMITS.social_propagation_recipients],
        "target_entity_ids": list(action.get("target_entity_ids") or (
            [action["target_entity_id"]] if action.get("target_entity_id") else []
        )),
        "causal_goal_id": action.get("causal_goal_id") or plan.get("goal_id"),
        "plan_id": action.get("plan_id") or plan.get("plan_id"),
        "plan_step_index": int(action.get("plan_step_index", plan.get("step_index", 0))),
        "current_stage": action.get("current_stage") or action.get("status", "planned"),
        "required_tools": list(action.get("required_tools") or []),
        "required_resources": copy.deepcopy(action.get("required_resources") or {}),
        "reserved_resources": copy.deepcopy(action.get("reserved_resources") or {}),
        "expected_duration": required,
        "progress": _bounded_int(action.get("progress", progress)),
        "interruption_cost": max(0, int(action.get("interruption_cost", spent))),
        "failure_conditions": list(action.get("failure_conditions") or []),
        "fallback": action.get("fallback"),
        "completion_outcome": copy.deepcopy(action.get("completion_outcome")),
        "cancellation_reason": action.get("cancellation_reason"),
        "causal_parent_event_ids": list(action.get("causal_parent_event_ids") or []),
        "source_proposal_id": action.get("source_proposal_id"),
        "accepted_event_id": action.get("accepted_event_id"),
        "source_proposal_ids": list(action.get("source_proposal_ids") or []),
        "accepted_event_ids": list(action.get("accepted_event_ids") or []),
        "physical_effects": list(action.get("physical_effects") or []),
        "resource_transfer": copy.deepcopy(action.get("resource_transfer")),
        "access_violation": bool(action.get("access_violation", False)),
    }


def default_affordances(entity: dict) -> dict:
    """Return explicit general affordances for established entity types."""
    entity_type = entity.get("type")
    flags = {
        "gatherable": entity_type in ("tree", "carcass", "resource"),
        "carryable": entity_type in ("tool", "item", "resource"),
        "storage": entity_type in ("storage", "container"),
        "consumable": bool(entity.get("consumable")) or entity_type == "food",
        "drinkable": entity_type == "water_source",
        "tool": entity_type == "tool",
        "shelter": entity_type == "shelter",
        "repairable": entity_type in ("shelter", "tool", "structure"),
        "damageable": entity_type in ("tree", "tool", "shelter", "structure"),
        "openable": entity_type in ("storage", "container", "structure"),
        "ownable": entity_type not in ("signal", "weather"),
    }
    return {
        "schema_version": AFFORDANCE_SCHEMA_VERSION,
        **flags,
        "access": entity.get("access", "public"),
        "movement_cost": max(1, int(entity.get("movement_cost", 1))),
        "exposure_modifier": int(entity.get("exposure_modifier", 0)),
        "emits": list(entity.get("emits") or []),
    }


def stage6_schema_manifest() -> dict:
    """Hashable manifest stored in tests/docs and usable by compatibility gates."""
    return {
        "living_agent": LIVING_AGENT_SCHEMA_VERSION,
        "pressure": PRESSURE_SCHEMA_VERSION,
        "want": WANT_SCHEMA_VERSION,
        "memory": MEMORY_SCHEMA_VERSION,
        "relationship": RELATIONSHIP_SCHEMA_VERSION,
        "commitment": COMMITMENT_SCHEMA_VERSION,
        "decision_receipt": DECISION_RECEIPT_VERSION,
        "plan": PLAN_SCHEMA_VERSION,
        "action": ACTION_SCHEMA_VERSION,
        "affordance": AFFORDANCE_SCHEMA_VERSION,
        "limits": LIMITS.__dict__,
        "physical_action_types": sorted(PHYSICAL_ACTION_TYPES),
        "social_action_types": sorted(SOCIAL_ACTION_TYPES),
    }
