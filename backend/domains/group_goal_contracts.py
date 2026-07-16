"""Stage 7D - Group goals and emergent leadership (bounded shelter-upkeep goal).

Agency model
------------
A recognised Stage 7A group with a Stage 7B ``shared_shelter`` fact whose target
shelter is below an upkeep threshold, and at least two current members who each
individually hold an active ``improve_shelter`` want, may adopt ONE canonical
``maintain_shared_shelter`` collective goal.

The module is pure. It reads a pinned canonical frame, derives adoptions and
expiries, proposes the next bounded group-goal registry, and leaves all mutation
authority to Core.

Non-goals: no obedience, no command authority, no voting, no group planner, no
member/world mutation. The coordinator is a recorded first-eligible member id
only. The goal cannot want what no member wants.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from core.hashing import canonical_byte_composition, canonical_hash, canonical_json
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    ASSOCIATION_REGISTRY_VERSION,
    GROUP_CANDIDATE_VERSION,
)
from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_ID,
    GROUP_STATE_REGISTRY_VERSION,
    SHARED_GROUP_FACT_VERSION,
)


GROUP_GOAL_REGISTRY_ID = "group-goal-000"
GROUP_GOAL_REGISTRY_VERSION = "group-goal-registry-v1"
GROUP_GOAL_VERSION = "group-goal-v1"

GOAL_TYPE = "maintain_shared_shelter"
PROPOSAL_TYPE = "group_adopt_collective_goal"
PROPOSAL_FAMILY = "group_goal"

# Determinism-visible constants (fixed before implementation, per contract).
UPKEEP_THRESHOLD = 750          # shelter condition strictly below this needs upkeep
GOAL_TTL_TICKS = 48             # goal expires this many ticks after last update
MIN_SUPPORTERS = 2
SUPPORT_WANT_TYPE = "improve_shelter"


@dataclass(frozen=True)
class GroupGoalLimits:
    goals: int = 16
    supporters_per_goal: int = 8
    processed_goal_keys: int = 96
    causal_parents: int = 16
    provenance_refs: int = 16
    payload_target_bytes: int = 24 * 1024
    proposal_bytes: int = 32 * 1024


LIMITS = GroupGoalLimits()


class GroupGoalContractError(ValueError):
    """Raised when canonical Stage 7D state cannot be interpreted safely."""


# Stable reason codes
REASON_INVALID = "group_goal.invalid"
REASON_VERSION = "group_goal.invalid_version"
REASON_REGISTRY_ID = "group_goal.invalid_registry_id"
REASON_ASSOCIATION = "group_goal.association_registry_missing"
REASON_GROUP_STATE = "group_goal.group_state_missing"
REASON_STALE = "group_goal.stale_membership"
REASON_SCOPE = "group_goal.invalid_mutation_scope"
REASON_SCHEMA = "group_goal.invalid_registry_schema"
REASON_REVISION = "group_goal.invalid_revision"
REASON_PAYLOAD = "group_goal.payload_limit"
REASON_MUTATION = "group_goal.mutation_mismatch"
REASON_METADATA = "group_goal.metadata_mismatch"
REASON_LIMIT = "group_goal.goal_limit"
REASON_GOAL = "group_goal.invalid_goal"


def empty_group_goal_registry(tick: int = 0) -> dict:
    return {
        "type": "group_goal_registry",
        "schema_version": GROUP_GOAL_REGISTRY_VERSION,
        "revision": 0,
        "goals": {},
        "processed_goal_keys": [],
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
    }


def _bounded_ids(values, limit: int = LIMITS.provenance_refs) -> list[str]:
    return sorted(set(str(value) for value in (values or []) if value))[-limit:]


def group_goal_id(group_id: str, goal_type: str, target_id: str) -> str:
    if not group_id or not target_id:
        raise ValueError("group goal identity requires group and target")
    return "group-goal-" + canonical_hash([
        GROUP_GOAL_VERSION, str(group_id), str(goal_type), str(target_id),
    ])[:20]


def group_goal_key(adoption: dict) -> str:
    return "goaladopt-" + canonical_hash([
        GROUP_GOAL_VERSION,
        adoption.get("group_id"),
        adoption.get("goal_type"),
        adoption.get("target_id"),
        adoption.get("coordinator_id"),
        adoption.get("supporter_ids") or [],
        adoption.get("fact_id"),
        adoption.get("tick"),
    ])[:24]


def _recognised_groups(association: dict) -> dict:
    return {
        gid: cand
        for gid, cand in sorted((association.get("group_candidates") or {}).items())
        if cand.get("schema_version") == GROUP_CANDIDATE_VERSION
        and cand.get("recognition_state") == "recognised"
        and cand.get("ever_recognised") is True
    }


def _shared_shelter_facts(group_state: dict, group_id: str) -> list[dict]:
    group = (group_state.get("groups") or {}).get(group_id) or {}
    facts = []
    for _fid, fact in sorted((group.get("facts") or {}).items()):
        if fact.get("schema_version") != SHARED_GROUP_FACT_VERSION:
            continue
        if fact.get("category") != "shared_shelter":
            continue
        if not fact.get("target_id"):
            continue
        facts.append(fact)
    return facts


def _holds_improve_shelter_want(person: dict) -> bool:
    living = person.get("living_agent")
    if not isinstance(living, dict):
        return False
    wants = living.get("wants")
    if not isinstance(wants, dict):
        return False
    for want in wants.values():
        if (
            isinstance(want, dict)
            and want.get("want_type") == SUPPORT_WANT_TYPE
            and want.get("status") == "active"
        ):
            return True
    return False


def _eligible_supporters(entities: dict, member_ids: list[str]) -> list[str]:
    supporters = []
    for mid in sorted(set(member_ids)):
        person = entities.get(mid)
        if not isinstance(person, dict) or person.get("type") != "person":
            continue
        if not person.get("alive", True):
            continue
        if _holds_improve_shelter_want(person):
            supporters.append(mid)
    return supporters


def _shelter_condition(shelter: dict) -> int:
    # Condition may live at top level or under properties (projection shape).
    if "condition" in shelter:
        return int(shelter.get("condition", 1000) or 0)
    props = shelter.get("properties") or {}
    return int(props.get("condition", 1000) or 0)


def derive_group_goal_changes(entities: dict, tick: int) -> tuple[list[dict], list[str]]:
    """Return (adoptions, expiring_goal_ids) for this tick.

    Pure derivation over recognised membership, shared_shelter facts, shelter
    condition, and member improve_shelter wants.
    """
    association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    group_state = entities.get(GROUP_STATE_REGISTRY_ID) or {}
    registry = entities.get(GROUP_GOAL_REGISTRY_ID) or {}
    if association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return [], []
    if group_state.get("schema_version") != GROUP_STATE_REGISTRY_VERSION:
        return [], []
    recognised = _recognised_groups(association)

    existing_goals = (registry.get("goals") or {}) if isinstance(registry, dict) else {}
    adoptions: list[dict] = []
    for group_id, candidate in recognised.items():
        members = list(candidate.get("member_ids") or [])
        for fact in _shared_shelter_facts(group_state, group_id):
            target_id = fact["target_id"]
            shelter = entities.get(target_id)
            if not isinstance(shelter, dict) or shelter.get("type") not in ("shelter", "structure"):
                continue
            if _shelter_condition(shelter) >= UPKEEP_THRESHOLD:
                continue
            supporters = _eligible_supporters(entities, members)
            if len(supporters) < MIN_SUPPORTERS:
                continue
            supporters = supporters[:LIMITS.supporters_per_goal]
            gid = group_goal_id(group_id, GOAL_TYPE, target_id)
            existing = existing_goals.get(gid)
            if existing and existing.get("status") == "active":
                continue  # already adopted and live; refresh happens via expiry rules
            adoption = {
                "schema_version": GROUP_GOAL_VERSION,
                "goal_id": gid,
                "group_id": group_id,
                "group_type": candidate.get("group_type"),
                "goal_type": GOAL_TYPE,
                "target_id": target_id,
                "fact_id": fact.get("fact_id"),
                "coordinator_id": supporters[0],
                "supporter_ids": supporters,
                "tick": int(tick),
                "ttl_tick": int(tick) + GOAL_TTL_TICKS,
                "association_revision": int(association.get("revision", 0)),
                "group_state_revision": int(group_state.get("revision", 0)),
                "recognition_event_id": candidate.get("recognition_event_id"),
                "association_event_id": association.get("last_event_id"),
                "group_state_event_id": group_state.get("last_event_id"),
            }
            adoption["goal_key"] = group_goal_key(adoption)
            adoptions.append(adoption)

    # Expiry: recovery above threshold, supporter loss below minimum, or TTL.
    expiring: list[str] = []
    for gid, goal in sorted(existing_goals.items()):
        if goal.get("status") != "active":
            continue
        target_id = goal.get("target_id")
        shelter = entities.get(target_id) or {}
        recovered = (
            not isinstance(shelter, dict)
            or _shelter_condition(shelter) >= UPKEEP_THRESHOLD
        )
        group_id = goal.get("group_id")
        candidate = recognised.get(group_id) or {}
        members = list(candidate.get("member_ids") or [])
        supporters = _eligible_supporters(entities, members)
        lost_support = len(supporters) < MIN_SUPPORTERS or not candidate
        expired_ttl = int(tick) >= int(goal.get("ttl_tick", tick))
        if recovered or lost_support or expired_ttl:
            expiring.append(gid)

    adoptions.sort(key=lambda a: (a["group_id"], a["target_id"], a["goal_key"]))
    return adoptions[:LIMITS.goals], sorted(set(expiring))


def _goal_record(adoption: dict, tick: int) -> dict:
    return {
        "schema_version": GROUP_GOAL_VERSION,
        "goal_id": adoption["goal_id"],
        "group_id": adoption["group_id"],
        "group_type": adoption.get("group_type"),
        "goal_type": adoption["goal_type"],
        "target_id": adoption["target_id"],
        "fact_id": adoption.get("fact_id"),
        "coordinator_id": adoption["coordinator_id"],
        "supporter_ids": list(adoption["supporter_ids"]),
        "status": "active",
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
        "ttl_tick": int(adoption["ttl_tick"]),
        "adopted_via_key": adoption["goal_key"],
        "association_revision": int(adoption["association_revision"]),
        "group_state_revision": int(adoption["group_state_revision"]),
        "created_event_id": None,
        "last_event_id": None,
        "pending_event_tick": int(tick),
        "pending_transition": "adopted",
        "revision": 1,
    }


def _compact_registry(registry: dict) -> None:
    goals = registry.get("goals") or {}
    ranked = sorted(
        goals.items(),
        key=lambda pair: (
            0 if pair[1].get("status") == "active" else 1,
            -int(pair[1].get("last_updated_tick", 0)),
            pair[0],
        ),
    )[:LIMITS.goals]
    registry["goals"] = {key: goals[key] for key, _ in sorted(ranked)}
    registry["processed_goal_keys"] = list(
        registry.get("processed_goal_keys") or []
    )[-LIMITS.processed_goal_keys:]


def advance_group_goal_registry(
    existing: dict | None,
    adoptions: list[dict],
    expiring: list[str],
    tick: int,
) -> tuple[dict, list[dict]]:
    if existing:
        if existing.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
            raise GroupGoalContractError(
                f"unsupported group goal schema: {existing.get('schema_version')}"
            )
        registry = copy.deepcopy(existing)
    else:
        registry = empty_group_goal_registry(tick)

    goals = copy.deepcopy(registry.get("goals") or {})
    processed = list(registry.get("processed_goal_keys") or [])
    processed_set = set(processed)
    transitions: list[dict] = []

    for adoption in sorted(adoptions, key=lambda a: a["goal_key"]):
        key = adoption["goal_key"]
        if key in processed_set:
            continue
        gid = adoption["goal_id"]
        goals[gid] = _goal_record(adoption, tick)
        processed.append(key)
        processed_set.add(key)
        transitions.append({
            "goal_id": gid,
            "group_id": adoption["group_id"],
            "target_id": adoption["target_id"],
            "coordinator_id": adoption["coordinator_id"],
            "kind": "adopted",
            "goal_key": key,
        })

    for gid in sorted(set(expiring)):
        goal = goals.get(gid)
        if not goal or goal.get("status") != "active":
            continue
        goal = copy.deepcopy(goal)
        goal["status"] = "expired"
        goal["last_updated_tick"] = int(tick)
        goal["pending_event_tick"] = int(tick)
        goal["pending_transition"] = "expired"
        goal["revision"] = int(goal.get("revision", 0)) + 1
        goals[gid] = goal
        transitions.append({
            "goal_id": gid,
            "group_id": goal.get("group_id"),
            "target_id": goal.get("target_id"),
            "coordinator_id": goal.get("coordinator_id"),
            "kind": "expired",
            "goal_key": goal.get("adopted_via_key"),
        })

    registry["goals"] = {key: goals[key] for key in sorted(goals)}
    registry["processed_goal_keys"] = processed
    registry["revision"] = int(registry.get("revision", 0)) + 1
    registry["last_updated_tick"] = int(tick)
    _compact_registry(registry)
    transitions.sort(key=lambda t: (t["kind"], t["goal_id"]))
    return registry, transitions


def _proposed_registry(proposal: dict) -> dict | None:
    mutation = proposal.get("mutation") or {}
    return (
        (mutation.get("new_entities") or {}).get(GROUP_GOAL_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(GROUP_GOAL_REGISTRY_ID)
    )


def build_group_goal_proposal(
    entities: dict,
    tick: int,
    *,
    adoptions: list[dict] | None = None,
    expiring: list[str] | None = None,
) -> dict | None:
    association = entities.get(ASSOCIATION_REGISTRY_ID)
    group_state = entities.get(GROUP_STATE_REGISTRY_ID)
    if not isinstance(association, dict) or association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return None
    if not isinstance(group_state, dict) or group_state.get("schema_version") != GROUP_STATE_REGISTRY_VERSION:
        return None
    existing = entities.get(GROUP_GOAL_REGISTRY_ID)
    if adoptions is None or expiring is None:
        adoptions, expiring = derive_group_goal_changes(entities, tick)
    if not adoptions and not expiring:
        return None

    registry, transitions = advance_group_goal_registry(existing, adoptions, expiring, tick)

    parents = []
    for adoption in adoptions:
        for key in ("group_state_event_id", "association_event_id", "recognition_event_id"):
            if adoption.get(key):
                parents.append(adoption[key])
    if not parents:
        for key in ("last_event_id",):
            if isinstance(group_state, dict) and group_state.get(key):
                parents.append(group_state[key])
            if isinstance(association, dict) and association.get(key):
                parents.append(association[key])
    parent_ids = _bounded_ids(parents, LIMITS.causal_parents)
    if not parent_ids:
        return None

    if existing:
        mutation = {"entity_updates": {GROUP_GOAL_REGISTRY_ID: registry}, "new_entities": {}}
        prior_revision = int(existing.get("revision", 0))
        preconditions = [{
            "entity_id": GROUP_GOAL_REGISTRY_ID, "field": "revision",
            "op": "eq", "value": prior_revision,
        }]
    else:
        mutation = {"new_entities": {GROUP_GOAL_REGISTRY_ID: registry}, "entity_updates": {}}
        prior_revision = None
        preconditions = []
    preconditions.append({
        "entity_id": ASSOCIATION_REGISTRY_ID, "field": "revision",
        "op": "eq", "value": int(association.get("revision", 0)),
    })
    preconditions.append({
        "entity_id": GROUP_STATE_REGISTRY_ID, "field": "revision",
        "op": "eq", "value": int(group_state.get("revision", 0)),
    })

    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    metadata = {
        "schema_version": GROUP_GOAL_VERSION,
        "registry_id": GROUP_GOAL_REGISTRY_ID,
        "association_registry_revision": int(association.get("revision", 0)),
        "group_state_registry_revision": int(group_state.get("revision", 0)),
        "prior_revision": prior_revision,
        "next_revision": int(registry["revision"]),
        "adoptions": copy.deepcopy(adoptions),
        "expiring_goal_ids": sorted(set(expiring)),
        "adoption_keys": [a["goal_key"] for a in adoptions],
        "transitions": copy.deepcopy(transitions),
        "goal_count": len(registry["goals"]),
        "active_goal_count": sum(
            1 for g in registry["goals"].values() if g.get("status") == "active"
        ),
        "payload_bytes": payload_bytes,
    }
    return {
        "proposal_family": PROPOSAL_FAMILY,
        "proposal_type": PROPOSAL_TYPE,
        "proposer_engine_id": "group_goal",
        "proposer_engine_version": "1.0.0",
        "entity_id": GROUP_GOAL_REGISTRY_ID,
        "causal_parent_event_ids": parent_ids,
        "is_exogenous": False,
        "requested_time": int(tick),
        "phase": "agent",
        # Commit before Stage 7A/7B revision churn (see GroupGoalDomain).
        "engine_priority": 88,  # before group_state (89), association (90)
        "touched_scope": [GROUP_GOAL_REGISTRY_ID, ASSOCIATION_REGISTRY_ID, GROUP_STATE_REGISTRY_ID],
        "preconditions": preconditions,
        "mutation": mutation,
        "group_goal_update": metadata,
        "explanation": (
            f"group goal registry revision {registry['revision']}; "
            f"adoptions={len(adoptions)} expiries={len(expiring)}"
        ),
    }


def validate_group_goal_proposal(proposal: dict, entities: dict) -> str | None:
    """Core-owned validation. None means ok; non-None is a stable reason code."""
    metadata = proposal.get("group_goal_update")
    if metadata is None:
        return None
    if not isinstance(metadata, dict) or metadata.get("schema_version") != GROUP_GOAL_VERSION:
        return REASON_VERSION
    if proposal.get("entity_id") != GROUP_GOAL_REGISTRY_ID or metadata.get("registry_id") != GROUP_GOAL_REGISTRY_ID:
        return REASON_REGISTRY_ID

    association = entities.get(ASSOCIATION_REGISTRY_ID)
    group_state = entities.get(GROUP_STATE_REGISTRY_ID)
    if not isinstance(association, dict) or association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return REASON_ASSOCIATION
    if not isinstance(group_state, dict) or group_state.get("schema_version") != GROUP_STATE_REGISTRY_VERSION:
        return REASON_GROUP_STATE
    if int(metadata.get("association_registry_revision", -1)) != int(association.get("revision", -2)):
        return REASON_STALE
    if int(metadata.get("group_state_registry_revision", -1)) != int(group_state.get("revision", -2)):
        return REASON_STALE

    mutation = proposal.get("mutation") or {}
    new_entities = mutation.get("new_entities") or {}
    entity_updates = mutation.get("entity_updates") or {}
    removed = mutation.get("removed_entities") or []
    if set(new_entities) - {GROUP_GOAL_REGISTRY_ID} or set(entity_updates) - {GROUP_GOAL_REGISTRY_ID} or removed:
        return REASON_SCOPE
    registry = _proposed_registry(proposal)
    if not isinstance(registry, dict) or registry.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
        return REASON_SCHEMA

    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    if payload_bytes > LIMITS.proposal_bytes or int(metadata.get("payload_bytes", -1)) != payload_bytes:
        return REASON_PAYLOAD

    existing = entities.get(GROUP_GOAL_REGISTRY_ID)
    if existing and GROUP_GOAL_REGISTRY_ID in new_entities:
        return REASON_REVISION
    expected_revision = int(existing.get("revision", 0)) + 1 if existing else 1
    if int(registry.get("revision", -1)) != expected_revision:
        return REASON_REVISION
    if metadata.get("prior_revision") != (int(existing.get("revision", 0)) if existing else None):
        return REASON_REVISION
    if int(metadata.get("next_revision", -1)) != expected_revision:
        return REASON_REVISION

    required = {
        (c.get("entity_id"), c.get("field"), c.get("op"), c.get("value"))
        for c in (proposal.get("preconditions") or [])
    }
    if (ASSOCIATION_REGISTRY_ID, "revision", "eq", int(association.get("revision", 0))) not in required:
        return REASON_STALE
    if (GROUP_STATE_REGISTRY_ID, "revision", "eq", int(group_state.get("revision", 0))) not in required:
        return REASON_STALE
    if existing and (GROUP_GOAL_REGISTRY_ID, "revision", "eq", int(existing.get("revision", 0))) not in required:
        return REASON_REVISION

    adoptions = metadata.get("adoptions")
    expiring = metadata.get("expiring_goal_ids")
    if not isinstance(adoptions, list) or not isinstance(expiring, list):
        return REASON_METADATA
    if len(adoptions) > LIMITS.goals:
        return REASON_LIMIT

    # Re-derive from the pinned frame and require byte-equality (determinism).
    derived_adoptions, derived_expiring = derive_group_goal_changes(
        entities, int(proposal.get("requested_time", 0)),
    )
    derived_keys = {a["goal_key"] for a in derived_adoptions}
    for adoption in adoptions:
        if not isinstance(adoption, dict) or adoption.get("goal_key") not in derived_keys:
            return REASON_METADATA
        if adoption.get("goal_type") != GOAL_TYPE:
            return REASON_GOAL
        supporters = adoption.get("supporter_ids") or []
        if len(supporters) < MIN_SUPPORTERS or supporters != sorted(set(supporters)):
            return REASON_GOAL
        if adoption.get("coordinator_id") != supporters[0]:
            return REASON_GOAL
    if sorted(set(expiring)) != derived_expiring:
        return REASON_METADATA

    try:
        expected_registry, transitions = advance_group_goal_registry(
            existing, adoptions, expiring, int(proposal.get("requested_time", 0)),
        )
    except (TypeError, ValueError, GroupGoalContractError):
        return REASON_SCHEMA
    if expected_registry != registry:
        return REASON_MUTATION
    if metadata.get("transitions") != transitions:
        return REASON_METADATA
    if int(metadata.get("goal_count", -1)) != len(registry.get("goals") or {}):
        return REASON_METADATA
    if len(registry.get("goals") or {}) > LIMITS.goals:
        return REASON_LIMIT

    forbidden = {"inventory", "culture", "authority", "obedience", "orders", "law"}
    for goal in (registry.get("goals") or {}).values():
        if goal.get("schema_version") != GROUP_GOAL_VERSION or forbidden & set(goal):
            return REASON_GOAL
        if goal.get("goal_type") != GOAL_TYPE:
            return REASON_GOAL
        supporters = goal.get("supporter_ids") or []
        if goal.get("status") == "active" and goal.get("coordinator_id") not in supporters:
            return REASON_GOAL
        if len(supporters) > LIMITS.supporters_per_goal:
            return REASON_GOAL
    return None


def stamp_group_goal_provenance(proposal: dict, mutation: dict, event_id: str) -> None:
    metadata = proposal.get("group_goal_update")
    if not isinstance(metadata, dict):
        return
    registry = (
        (mutation.get("new_entities") or {}).get(GROUP_GOAL_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(GROUP_GOAL_REGISTRY_ID)
    )
    if not isinstance(registry, dict):
        return
    tick = int(proposal.get("requested_time", 0))
    for goal in (registry.get("goals") or {}).values():
        if int(goal.get("pending_event_tick") or -1) == tick:
            if goal.get("created_event_id") is None:
                goal["created_event_id"] = event_id
            goal["last_event_id"] = event_id
            goal["pending_event_tick"] = None
            goal["pending_transition"] = None
    metadata["accepted_event_id"] = event_id


def group_goal_diagnostics(registry: dict, tick: int) -> dict:
    goals = registry.get("goals") or {}
    return {
        "schema_version": "group-goal-diagnostics-v1",
        "tick": int(tick),
        "registry_revision": int(registry.get("revision", 0)),
        "goal_count": len(goals),
        "active_goal_count": sum(1 for g in goals.values() if g.get("status") == "active"),
        "processed_goal_count": len(registry.get("processed_goal_keys") or []),
        "coordinators": sorted({
            g.get("coordinator_id") for g in goals.values()
            if g.get("status") == "active" and g.get("coordinator_id")
        }),
        "caps": {
            "goals": LIMITS.goals,
            "supporters_per_goal": LIMITS.supporters_per_goal,
            "processed_goal_keys": LIMITS.processed_goal_keys,
            "causal_parents": LIMITS.causal_parents,
            "payload_target_bytes": LIMITS.payload_target_bytes,
            "proposal_bytes": LIMITS.proposal_bytes,
        },
        "constants": {
            "upkeep_threshold": UPKEEP_THRESHOLD,
            "goal_ttl_ticks": GOAL_TTL_TICKS,
            "min_supporters": MIN_SUPPORTERS,
        },
    }


def group_goal_capacity_diagnostics(registry: dict) -> dict:
    provenance_fields = {
        "accepted_event_id", "created_event_id", "last_event_id",
        "recognition_event_id", "association_event_id", "group_state_event_id",
    }

    def classify(path: tuple, _value, _is_key: bool) -> str | None:
        fields = {part for part in path if isinstance(part, str)}
        if "processed_goal_keys" in fields:
            return "processed_goal_key_bytes"
        if fields & provenance_fields:
            return "provenance_reference_bytes"
        if "goals" in fields:
            return "current_truth_bytes"
        return None

    composition = {
        "current_truth_bytes": 0,
        "processed_goal_key_bytes": 0,
        "provenance_reference_bytes": 0,
        "other_structural_overhead_bytes": 0,
    }
    composition.update(canonical_byte_composition(registry, classify))
    return {
        "total_serialized_bytes": len(canonical_json(registry).encode("utf-8")),
        **composition,
    }


def group_goal_current_truth_summary(registry: dict) -> dict:
    goals = {}
    for gid, goal in sorted((registry.get("goals") or {}).items()):
        goals[gid] = {
            "group_id": goal.get("group_id"),
            "goal_type": goal.get("goal_type"),
            "target_id": goal.get("target_id"),
            "coordinator_id": goal.get("coordinator_id"),
            "supporter_ids": list(goal.get("supporter_ids") or []),
            "status": goal.get("status"),
            "created_tick": goal.get("created_tick"),
            "ttl_tick": goal.get("ttl_tick"),
            "revision": int(goal.get("revision", 0)),
        }
    return {"goals": goals}
