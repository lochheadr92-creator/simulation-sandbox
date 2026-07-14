"""Stage 7C — Group behaviour and collective action (narrow coordinated deposit).

Agency model
------------
A recognised Stage 7A group with a Stage 7B ``shared_storage`` fact supplies
*context only*.  It does not think, score privately, or mutate world state.

Deterministic evaluation over current membership, member state, shared fact,
and storage entity selects:
  - eligible participants (not every member);
  - initiator = lexicographically first eligible living member id;
  - one bounded action type: ``coordinated_storage_deposit``.

The proposal is authored with ``entity_id = initiator`` and lists all
participants.  Core validates, revalidates preconditions, and alone mutates
inventories and storage contents.

No group brain, no leadership, no obedience, no shared inventory ownership
beyond the existing storage entity, no Stage 8 institutions.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from core.geometry import manhattan
from core.hashing import canonical_hash, canonical_json
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


COLLECTIVE_ACTION_VERSION = "group-collective-action-v1"
COLLECTIVE_ACTION_TYPE = "coordinated_storage_deposit"
PROPOSAL_TYPE = "group_coordinated_storage_deposit"
PROPOSAL_FAMILY = "group_collective_action"

MAX_PARTICIPANTS = 4
MAX_COLLECTIVE_ACTIONS_PER_TICK = 4
MAX_PROCESSED_KEYS = 64
ACTION_RANGE = 1  # same adjacency convention as 5B1 transfer


@dataclass(frozen=True)
class CollectiveLimits:
    max_participants: int = MAX_PARTICIPANTS
    max_actions_per_tick: int = MAX_COLLECTIVE_ACTIONS_PER_TICK
    processed_keys: int = MAX_PROCESSED_KEYS
    causal_parents: int = 16
    proposal_bytes: int = 16 * 1024


LIMITS = CollectiveLimits()

# Stable reason codes
REASON_INVALID = "group_collective.invalid"
REASON_NO_GROUP = "group_collective.group_not_recognised"
REASON_NO_FACT = "group_collective.shared_storage_missing"
REASON_BAD_TARGET = "group_collective.invalid_storage"
REASON_PARTICIPANTS = "group_collective.invalid_participants"
REASON_INITIATOR = "group_collective.invalid_initiator"
REASON_ELIGIBILITY = "group_collective.participant_ineligible"
REASON_CAPACITY = "group_collective.storage_capacity"
REASON_DUPLICATE = "group_collective.duplicate_action"
REASON_STALE_MEMBERSHIP = "group_collective.stale_membership"
REASON_SCOPE = "group_collective.invalid_scope"
REASON_MUTATION = "group_collective.invalid_mutation"
REASON_VERSION = "group_collective.invalid_version"


def _is_available(person: dict) -> bool:
    if not person or person.get("type") != "person" or not person.get("alive", True):
        return False
    action = person.get("action") or {}
    status = action.get("status")
    if status in ("travelling", "performing"):
        return False
    return True


def _person_resources(person: dict) -> dict:
    """Prefer living-agent carried_resources; fall back to legacy inventory fields."""
    carried = person.get("carried_resources")
    if isinstance(carried, dict):
        return {
            "food": max(0, int(carried.get("food", 0) or 0)),
            "wood": max(0, int(carried.get("wood", 0) or 0)),
        }
    return {
        "food": max(0, int(person.get("food_inventory", 0) or 0)),
        "wood": max(0, int(person.get("inventory", 0) or 0)),
    }


def _carried_deposit(person: dict) -> tuple[str, str, int] | None:
    """Return (resource_key, source_field, before_value); food preferred then wood."""
    resources = _person_resources(person)
    if resources["food"] > 0:
        # source_field names the legacy mirror field for precondition equality;
        # carried_resources is also mutated when present.
        return "food", "food_inventory", resources["food"]
    if resources["wood"] > 0:
        return "wood", "inventory", resources["wood"]
    return None


def _storage_total(storage: dict) -> int:
    contents = storage.get("contents") or {}
    return sum(int(v) for v in contents.values() if isinstance(v, (int, float)))


def _recognised_groups(association: dict) -> dict:
    return {
        gid: cand
        for gid, cand in sorted((association.get("group_candidates") or {}).items())
        if cand.get("schema_version") == GROUP_CANDIDATE_VERSION
        and cand.get("recognition_state") == "recognised"
        and cand.get("ever_recognised") is True
    }


def _shared_storage_facts(group_state_registry: dict, group_id: str) -> list[dict]:
    group = (group_state_registry.get("groups") or {}).get(group_id) or {}
    facts = []
    for fact_id, fact in sorted((group.get("facts") or {}).items()):
        if fact.get("schema_version") != SHARED_GROUP_FACT_VERSION:
            continue
        if fact.get("category") != "shared_storage":
            continue
        if not fact.get("target_id"):
            continue
        facts.append(fact)
    return facts


def eligible_participants(
    entities: dict,
    member_ids: list[str],
    storage_id: str,
) -> list[dict]:
    """Return sorted eligibility rows for members who can deposit now."""
    storage = entities.get(storage_id) or {}
    storage_pos = storage.get("position")
    if not storage_pos:
        return []
    rows = []
    for mid in sorted(set(member_ids)):
        person = entities.get(mid)
        if not _is_available(person):
            continue
        pos = person.get("position")
        if not pos or manhattan(pos, storage_pos) > ACTION_RANGE:
            continue
        deposit = _carried_deposit(person)
        if not deposit:
            continue
        resource_key, field, before_value = deposit
        rows.append({
            "person_id": mid,
            "resource_key": resource_key,
            "source_field": field,
            "quantity": 1,
            "before_value": int(before_value),
        })
    return rows


def collective_action_key(action: dict) -> str:
    return "gca-" + canonical_hash([
        COLLECTIVE_ACTION_VERSION,
        action.get("action_type"),
        action.get("group_id"),
        action.get("storage_id"),
        action.get("initiator_id"),
        action.get("participant_ids") or [],
        action.get("deposits") or [],
        action.get("tick"),
    ])[:24]


def derive_coordinated_deposits(entities: dict, tick: int) -> list[dict]:
    """Pure derivation of candidate collective deposit actions for this tick."""
    association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    group_state = entities.get(GROUP_STATE_REGISTRY_ID) or {}
    if association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return []
    if group_state.get("schema_version") != GROUP_STATE_REGISTRY_VERSION:
        return []
    recognised = _recognised_groups(association)
    if not recognised:
        return []

    actions = []
    for group_id, candidate in recognised.items():
        members = list(candidate.get("member_ids") or [])
        for fact in _shared_storage_facts(group_state, group_id):
            storage_id = fact["target_id"]
            storage = entities.get(storage_id)
            if not isinstance(storage, dict) or storage.get("type") not in ("storage", "container"):
                continue
            if storage.get("access") not in ("shared", "public"):
                continue
            participants = eligible_participants(entities, members, storage_id)
            if len(participants) < 2:
                continue
            participants = participants[:LIMITS.max_participants]
            capacity = int(storage.get("capacity", 0) or 0)
            total = _storage_total(storage)
            deposits = []
            projected = total
            for row in participants:
                if capacity and projected + 1 > capacity:
                    break
                deposits.append({
                    "person_id": row["person_id"],
                    "resource_key": row["resource_key"],
                    "source_field": row["source_field"],
                    "quantity": 1,
                    "before_value": row["before_value"],
                })
                projected += 1
            if len(deposits) < 2:
                continue
            participant_ids = [d["person_id"] for d in deposits]
            initiator_id = participant_ids[0]
            action = {
                "schema_version": COLLECTIVE_ACTION_VERSION,
                "action_type": COLLECTIVE_ACTION_TYPE,
                "group_id": group_id,
                "group_type": candidate.get("group_type"),
                "storage_id": storage_id,
                "shared_fact_id": fact.get("fact_id"),
                "initiator_id": initiator_id,
                "participant_ids": participant_ids,
                "deposits": deposits,
                "tick": int(tick),
                "association_revision": int(association.get("revision", 0)),
                "group_state_revision": int(group_state.get("revision", 0)),
                "recognition_event_id": candidate.get("recognition_event_id"),
                "association_event_id": association.get("last_event_id"),
                "group_state_event_id": group_state.get("last_event_id"),
            }
            action["action_key"] = collective_action_key(action)
            actions.append(action)
    actions.sort(key=lambda a: (a["group_id"], a["storage_id"], a["action_key"]))
    return actions[:LIMITS.max_actions_per_tick]


def build_collective_deposit_proposal(entities: dict, tick: int, action: dict) -> dict | None:
    """Build one Core proposal for a coordinated storage deposit."""
    initiator_id = action["initiator_id"]
    storage_id = action["storage_id"]
    storage = entities.get(storage_id) or {}
    initiator = entities.get(initiator_id) or {}
    if not initiator or not storage:
        return None

    entity_updates = {}
    contents = dict(storage.get("contents") or {})
    for dep in action["deposits"]:
        pid = dep["person_id"]
        person = entities.get(pid) or {}
        field = dep["source_field"]
        resource_key = dep["resource_key"]
        resources = _person_resources(person)
        before = int(resources.get(resource_key, 0) or 0)
        if before < 1 or int(dep["before_value"]) != before:
            return None
        after_resources = dict(resources)
        after_resources[resource_key] = before - 1
        person_update = {
            field: before - 1,
            "inventory": int(after_resources.get("wood", 0)),
            "food_inventory": int(after_resources.get("food", 0)),
            # Mark performing collective work this tick for contention visibility
            "action": {
                **dict(person.get("action") or {}),
                "type": "group_collective_deposit",
                "status": "completed",
                "ticks_spent": 1,
                "started_tick": int(tick),
            },
        }
        if isinstance(person.get("carried_resources"), dict) or person.get("carried_resources") is None:
            # Keep living-agent carried_resources authoritative when present.
            person_update["carried_resources"] = after_resources
        entity_updates[pid] = person_update
        contents[resource_key] = int(contents.get(resource_key, 0) or 0) + 1
    entity_updates[storage_id] = {
        "contents": contents,
        "last_collective_action_key": action["action_key"],
        "last_collective_action_tick": int(tick),
    }

    # Processed-key window on storage (bounded)
    processed = list(storage.get("collective_processed_keys") or [])
    if action["action_key"] in processed:
        return None
    processed = (processed + [action["action_key"]])[-LIMITS.processed_keys:]
    entity_updates[storage_id]["collective_processed_keys"] = processed

    parent_ids = []
    for key in ("group_state_event_id", "association_event_id", "recognition_event_id"):
        if action.get(key):
            parent_ids.append(action[key])
    if initiator.get("last_event_id"):
        parent_ids.append(initiator["last_event_id"])
    # Stable unique parents, bounded
    seen = set()
    causal = []
    for pid in parent_ids:
        if pid and pid not in seen:
            seen.add(pid)
            causal.append(pid)
        if len(causal) >= LIMITS.causal_parents:
            break
    if not causal:
        return None

    preconditions = [
        {
            "entity_id": ASSOCIATION_REGISTRY_ID,
            "field": "revision",
            "op": "eq",
            "value": int(action["association_revision"]),
        },
        {
            "entity_id": GROUP_STATE_REGISTRY_ID,
            "field": "revision",
            "op": "eq",
            "value": int(action["group_state_revision"]),
        },
    ]
    for dep in action["deposits"]:
        person = entities.get(dep["person_id"]) or {}
        preconditions.append({
            "entity_id": dep["person_id"],
            "field": "alive",
            "op": "eq",
            "value": True,
        })
        # Prefer carried_resources CAS when living-agent shape is present.
        if isinstance(person.get("carried_resources"), dict):
            preconditions.append({
                "entity_id": dep["person_id"],
                "field": "carried_resources",
                "op": "eq",
                "value": dict(person.get("carried_resources") or {}),
            })
        else:
            preconditions.append({
                "entity_id": dep["person_id"],
                "field": dep["source_field"],
                "op": "eq",
                "value": dep["before_value"],
            })

    touched = sorted(set(
        [initiator_id, storage_id, ASSOCIATION_REGISTRY_ID, GROUP_STATE_REGISTRY_ID]
        + list(action["participant_ids"])
    ))

    meta = copy.deepcopy(action)
    meta["proposal_schema"] = COLLECTIVE_ACTION_VERSION

    proposal = {
        "proposal_family": PROPOSAL_FAMILY,
        "proposal_type": PROPOSAL_TYPE,
        "proposer_engine_id": "group_collective",
        "proposer_engine_version": "1.0.0",
        "entity_id": initiator_id,
        "causal_parent_event_ids": causal,
        "is_exogenous": False,
        "requested_time": int(tick),
        "phase": "agent",
        "engine_priority": 88,  # after group_state (89) so shared facts exist first in priority? lower number = higher priority
        # PHASE_RANK then engine_priority: lower engine_priority commits first.
        # group_state is 89; use 90 so shared-state updates can land first same tick,
        # then collective action sees them next activation. Same-tick: we only
        # read existing shared facts from pinned frame, so 90 is fine.
        "touched_scope": touched,
        "preconditions": preconditions,
        "mutation": {"entity_updates": entity_updates, "new_entities": {}},
        "collective_action": meta,
        "explanation": (
            f"coordinated storage deposit group={action['group_id']} "
            f"storage={storage_id} participants={len(action['participant_ids'])} "
            f"initiator={initiator_id}"
        ),
    }
    # Fix engine_priority comment: want collective AFTER group_state when both
    # fire. group_state=89; collective should be higher number (later).
    proposal["engine_priority"] = 90
    return proposal


def build_group_collective_proposals(entities: dict, tick: int) -> list[dict]:
    actions = derive_coordinated_deposits(entities, tick)
    proposals = []
    for action in actions:
        proposal = build_collective_deposit_proposal(entities, tick, action)
        if proposal is not None:
            payload = len(canonical_json(proposal["collective_action"]).encode("utf-8"))
            if payload > LIMITS.proposal_bytes:
                continue
            proposals.append(proposal)
    return proposals


def validate_group_collective_proposal(proposal: dict, entities: dict) -> str | None:
    """Core-owned validation. None means ok; non-None is stable reason code."""
    if proposal.get("proposal_type") != PROPOSAL_TYPE:
        return None
    meta = proposal.get("collective_action") or {}
    if meta.get("schema_version") != COLLECTIVE_ACTION_VERSION:
        return REASON_VERSION
    if meta.get("action_type") != COLLECTIVE_ACTION_TYPE:
        return REASON_INVALID

    group_id = meta.get("group_id")
    storage_id = meta.get("storage_id")
    initiator_id = meta.get("initiator_id")
    participant_ids = meta.get("participant_ids") or []
    deposits = meta.get("deposits") or []

    if proposal.get("entity_id") != initiator_id:
        return REASON_INITIATOR
    if not isinstance(participant_ids, list) or participant_ids != sorted(set(participant_ids)):
        return REASON_PARTICIPANTS
    if len(participant_ids) < 2 or len(participant_ids) > LIMITS.max_participants:
        return REASON_PARTICIPANTS
    if initiator_id != participant_ids[0]:
        return REASON_INITIATOR
    if [d.get("person_id") for d in deposits] != participant_ids:
        return REASON_PARTICIPANTS

    scope = set(proposal.get("touched_scope") or [])
    required = set(participant_ids) | {
        storage_id, ASSOCIATION_REGISTRY_ID, GROUP_STATE_REGISTRY_ID, initiator_id,
    }
    if not required.issubset(scope):
        return REASON_SCOPE

    association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    group_state = entities.get(GROUP_STATE_REGISTRY_ID) or {}
    if association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return REASON_NO_GROUP
    if group_state.get("schema_version") != GROUP_STATE_REGISTRY_VERSION:
        return REASON_NO_FACT

    recognised = _recognised_groups(association)
    candidate = recognised.get(group_id)
    if not candidate:
        return REASON_NO_GROUP
    members = set(candidate.get("member_ids") or [])
    if not set(participant_ids).issubset(members):
        return REASON_STALE_MEMBERSHIP

    facts = _shared_storage_facts(group_state, group_id)
    if not any(f.get("target_id") == storage_id for f in facts):
        return REASON_NO_FACT

    storage = entities.get(storage_id)
    if not isinstance(storage, dict) or storage.get("type") not in ("storage", "container"):
        return REASON_BAD_TARGET
    if storage.get("access") not in ("shared", "public"):
        return REASON_BAD_TARGET

    processed = set(storage.get("collective_processed_keys") or [])
    action_key = meta.get("action_key")
    if action_key and action_key in processed:
        return REASON_DUPLICATE
    if storage.get("last_collective_action_key") == action_key:
        return REASON_DUPLICATE

    # Live eligibility revalidation
    live_rows = {
        row["person_id"]: row
        for row in eligible_participants(entities, list(members), storage_id)
    }
    capacity = int(storage.get("capacity", 0) or 0)
    contents = dict(storage.get("contents") or {})
    projected = _storage_total(storage)

    updates = (proposal.get("mutation") or {}).get("entity_updates") or {}
    for dep in deposits:
        pid = dep["person_id"]
        person = entities.get(pid)
        if not person or not person.get("alive", True):
            return REASON_ELIGIBILITY
        if pid not in live_rows:
            return REASON_ELIGIBILITY
        row = live_rows[pid]
        if row["source_field"] != dep["source_field"] or row["resource_key"] != dep["resource_key"]:
            return REASON_ELIGIBILITY
        resources = _person_resources(person)
        if int(resources.get(dep["resource_key"], 0) or 0) < 1:
            return REASON_ELIGIBILITY
        if int(resources.get(dep["resource_key"], 0) or 0) != int(dep["before_value"]):
            return REASON_ELIGIBILITY
        person_update = updates.get(pid) or {}
        if person_update.get(dep["source_field"]) != int(dep["before_value"]) - 1:
            return REASON_MUTATION
        if person_update.get("food_inventory") is None or person_update.get("inventory") is None:
            return REASON_MUTATION
        key = dep["resource_key"]
        projected += 1
        contents[key] = int(contents.get(key, 0) or 0) + 1
    if capacity and projected > capacity:
        return REASON_CAPACITY

    storage_update = updates.get(storage_id) or {}
    expected = dict(storage.get("contents") or {})
    for dep in deposits:
        k = dep["resource_key"]
        expected[k] = int(expected.get(k, 0) or 0) + 1
    if storage_update.get("contents") != expected:
        return REASON_MUTATION

    # Revision preconditions must match current registries
    assoc_rev = int(association.get("revision", 0))
    gs_rev = int(group_state.get("revision", 0))
    if int(meta.get("association_revision", -1)) != assoc_rev:
        return REASON_STALE_MEMBERSHIP
    if int(meta.get("group_state_revision", -1)) != gs_rev:
        return REASON_STALE_MEMBERSHIP

    return None


def stamp_collective_action_provenance(proposal: dict, mutation: dict, event_id: str) -> None:
    if proposal.get("proposal_type") != PROPOSAL_TYPE:
        return
    meta = proposal.get("collective_action")
    if isinstance(meta, dict):
        meta["accepted_event_id"] = event_id
    # Stamp last_event_id on all touched people and storage
    updates = mutation.setdefault("entity_updates", {})
    for eid in proposal.get("touched_scope") or []:
        if eid in (ASSOCIATION_REGISTRY_ID, GROUP_STATE_REGISTRY_ID):
            continue
        if eid in updates:
            updates[eid]["last_event_id"] = event_id


def collective_action_diagnostics(actions: list[dict], tick: int) -> dict:
    return {
        "tick": int(tick),
        "candidate_count": len(actions),
        "action_types": sorted({a.get("action_type") for a in actions}),
        "groups": sorted({a.get("group_id") for a in actions}),
        "limits": {
            "max_participants": LIMITS.max_participants,
            "max_actions_per_tick": LIMITS.max_actions_per_tick,
            "processed_keys": LIMITS.processed_keys,
        },
    }
