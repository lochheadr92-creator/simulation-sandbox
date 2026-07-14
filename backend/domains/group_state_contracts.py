"""Stage 7B bounded shared-group state and collective proposal contract.

This module is pure: it reads a pinned canonical frame, derives narrowly
eligible collective support from accepted Stage 7A evidence, proposes the next
bounded shared-state registry, and leaves all mutation authority to Core.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from core.hashing import canonical_byte_composition, canonical_hash, canonical_json
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    ASSOCIATION_REGISTRY_VERSION,
    GROUP_CANDIDATE_VERSION,
    association_pair_id,
)


GROUP_STATE_REGISTRY_ID = "group-shared-state-000"
GROUP_STATE_REGISTRY_VERSION = "group-shared-state-registry-v1"
SHARED_GROUP_STATE_VERSION = "shared-group-state-v1"
SHARED_GROUP_FACT_VERSION = "shared-group-fact-v1"
GROUP_SUPPORT_EVIDENCE_VERSION = "group-support-evidence-v1"
GROUP_COLLECTIVE_PROPOSAL_VERSION = "collective-group-proposal-v1"

ALLOWED_SHARED_FACT_CATEGORIES = frozenset({"shared_shelter", "shared_storage"})
FACT_TARGET_TYPES = {
    "shared_shelter": frozenset({"shelter", "structure"}),
    "shared_storage": frozenset({"storage", "container"}),
}
SUPPORT_FRESHNESS_TICKS = 4


@dataclass(frozen=True)
class GroupStateLimits:
    groups: int = 16
    facts_per_group: int = 8
    support_history_per_fact: int = 8
    minimum_support_history_per_fact: int = 1
    participants_per_support: int = 8
    provenance_refs: int = 16
    collective_proposals_retained: int = 12
    minimum_collective_proposals_retained: int = 1
    processed_proposal_keys: int = 96
    support_items_per_proposal: int = 16
    causal_parents_per_proposal: int = 32
    payload_target_bytes: int = 48 * 1024
    proposal_bytes: int = 64 * 1024


LIMITS = GroupStateLimits()


class GroupStateContractError(ValueError):
    """Raised when canonical Stage 7B state cannot be interpreted safely."""


def empty_group_state_registry(tick: int = 0) -> dict:
    return {
        "type": "group_shared_state_registry",
        "schema_version": GROUP_STATE_REGISTRY_VERSION,
        "revision": 0,
        "groups": {},
        "processed_proposal_keys": [],
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
    }


def shared_group_fact_id(group_id: str, category: str, target_id: str) -> str:
    if category not in ALLOWED_SHARED_FACT_CATEGORIES:
        raise ValueError(f"unsupported shared fact category: {category}")
    if not group_id or not target_id:
        raise ValueError("shared fact identity requires group and target")
    return "shared-fact-" + canonical_hash([
        SHARED_GROUP_FACT_VERSION,
        str(group_id),
        str(category),
        str(target_id),
    ])[:20]


def collective_proposal_key(support: dict) -> str:
    return "collective-" + canonical_hash([
        GROUP_COLLECTIVE_PROPOSAL_VERSION,
        support.get("group_id"),
        support.get("category"),
        support.get("target_id"),
        support.get("participant_ids") or [],
        support.get("support_event_ids") or [],
        support.get("support_evidence_ids") or [],
    ])[:24]


def _bounded_ids(values, limit: int = LIMITS.provenance_refs) -> list[str]:
    return sorted(set(str(value) for value in (values or []) if value))[-limit:]


def _recognised_groups(association_registry: dict) -> dict:
    return {
        group_id: candidate
        for group_id, candidate in sorted(
            (association_registry.get("group_candidates") or {}).items()
        )
        if candidate.get("schema_version") == GROUP_CANDIDATE_VERSION
        and candidate.get("recognition_state") == "recognised"
        and candidate.get("ever_recognised") is True
    }


def _dissolved_group_ids(association_registry: dict) -> set[str]:
    return {
        row.get("candidate_id")
        for row in association_registry.get("dissolved_history") or []
        if row.get("final_state") == "dissolved"
    } - {None}


def _target_is_permitted(entities: dict, category: str, target_id: str) -> bool:
    target = entities.get(target_id)
    if not isinstance(target, dict) or target.get("type") not in FACT_TARGET_TYPES[category]:
        return False
    if category == "shared_shelter":
        return target.get("access") in ("shared", "public")
    if category == "shared_storage":
        return target.get("access") in ("shared", "public")
    return False


def make_group_support_evidence(
    *,
    group_id: str,
    category: str,
    target_id: str,
    participant_ids: list[str],
    tick: int,
    support_event_ids: list[str],
    support_evidence_ids: list[str],
    association_record_ids: list[str],
    association_registry_revision: int,
    association_event_id: str | None,
) -> dict:
    participants = sorted(set(str(person_id) for person_id in participant_ids))
    if len(participants) != 2:
        raise ValueError("Stage 7B support requires exactly two explicit participants")
    if category not in ALLOWED_SHARED_FACT_CATEGORIES:
        raise ValueError(f"unsupported shared fact category: {category}")
    if not target_id:
        raise ValueError("shared fact support requires target_id")
    support_events = _bounded_ids(support_event_ids)
    evidence_ids = _bounded_ids(support_evidence_ids, 4)
    if len([event_id for event_id in support_events if not event_id.startswith("evt-0-")]) < 2:
        raise ValueError("collective support requires two participant accepted events")
    support = {
        "schema_version": GROUP_SUPPORT_EVIDENCE_VERSION,
        "group_id": str(group_id),
        "category": category,
        "target_id": str(target_id),
        "participant_ids": participants,
        "tick": int(tick),
        "support_event_ids": support_events,
        "support_evidence_ids": evidence_ids,
        "association_record_ids": _bounded_ids(association_record_ids, 4),
        "association_registry_revision": int(association_registry_revision),
        "association_event_id": association_event_id,
    }
    support["support_id"] = "group-support-" + canonical_hash([
        GROUP_SUPPORT_EVIDENCE_VERSION,
        support["group_id"],
        support["category"],
        support["target_id"],
        support["participant_ids"],
        support["tick"],
        support["support_event_ids"],
        support["support_evidence_ids"],
    ])[:20]
    support["proposal_key"] = collective_proposal_key(support)
    support["fact_id"] = shared_group_fact_id(
        support["group_id"], support["category"], support["target_id"],
    )
    return support


def derive_group_support_evidence(entities: dict, tick: int) -> list[dict]:
    association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    if association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return []
    recognised = _recognised_groups(association)
    if not recognised:
        return []
    records = association.get("association_records") or {}
    supports: dict[str, dict] = {}
    for group_id, candidate in recognised.items():
        members = set(candidate.get("member_ids") or [])
        for pair_id, record in sorted(records.items()):
            for evidence in sorted(
                record.get("recent_evidence") or [],
                key=lambda item: item.get("evidence_id", ""),
            ):
                category = evidence.get("category")
                if category not in ALLOWED_SHARED_FACT_CATEGORIES:
                    continue
                participant_ids = sorted(
                    evidence.get("person_ids") or record.get("person_ids") or []
                )
                if len(participant_ids) != 2 or not set(participant_ids).issubset(members):
                    continue
                if int(tick) - int(evidence.get("tick", -999999)) > SUPPORT_FRESHNESS_TICKS:
                    continue
                target_ids = list(evidence.get("condition_ids") or [])
                target_id = target_ids[0] if target_ids else None
                if not target_id or not _target_is_permitted(entities, category, target_id):
                    continue
                source_event_ids = list(evidence.get("source_event_ids") or [])
                support = make_group_support_evidence(
                    group_id=group_id,
                    category=category,
                    target_id=target_id,
                    participant_ids=participant_ids,
                    tick=int(evidence["tick"]),
                    support_event_ids=source_event_ids,
                    support_evidence_ids=[evidence["evidence_id"]],
                    association_record_ids=[pair_id],
                    association_registry_revision=int(association.get("revision", 0)),
                    association_event_id=association.get("last_event_id"),
                )
                supports[support["support_id"]] = support
    return [supports[key] for key in sorted(supports)]


def _group_state_template(group_id: str, candidate: dict, tick: int) -> dict:
    return {
        "schema_version": SHARED_GROUP_STATE_VERSION,
        "group_id": group_id,
        "group_type": candidate.get("group_type"),
        "member_ids": sorted(candidate.get("member_ids") or [])[:LIMITS.participants_per_support],
        "recognised_tick": candidate.get("recognised_tick"),
        "recognition_event_id": candidate.get("recognition_event_id"),
        "association_revision_seen": None,
        "revision": 0,
        "facts": {},
        "latest_collective_proposals": [],
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
    }


def _fact_template(support: dict) -> dict:
    return {
        "schema_version": SHARED_GROUP_FACT_VERSION,
        "fact_id": support["fact_id"],
        "category": support["category"],
        "target_id": support["target_id"],
        "participant_ids": list(support["participant_ids"]),
        "support_count": 0,
        "support_event_ids": [],
        "support_evidence_ids": [],
        "support_history": [],
        "created_tick": int(support["tick"]),
        "last_supported_tick": int(support["tick"]),
        "created_event_id": None,
        "last_event_id": None,
        "pending_event_tick": int(support["tick"]),
        "pending_transition": "created",
        "revision": 0,
    }


def _compact_registry(registry: dict) -> None:
    groups = registry.get("groups") or {}
    ranked_groups = sorted(
        groups.items(),
        key=lambda pair: (
            -int(pair[1].get("last_updated_tick", 0)),
            pair[0],
        ),
    )[:LIMITS.groups]
    compacted_groups = {}
    for group_id, group in ranked_groups:
        facts = group.get("facts") or {}
        ranked_facts = sorted(
            facts.items(),
            key=lambda pair: (
                -int(pair[1].get("last_supported_tick", 0)),
                pair[0],
            ),
        )[:LIMITS.facts_per_group]
        new_facts = {}
        for fact_id, fact in ranked_facts:
            fact = copy.deepcopy(fact)
            fact["support_event_ids"] = _bounded_ids(fact.get("support_event_ids") or [])
            fact["support_evidence_ids"] = _bounded_ids(
                fact.get("support_evidence_ids") or [],
                LIMITS.provenance_refs,
            )
            fact["support_history"] = list(
                fact.get("support_history") or []
            )[-LIMITS.support_history_per_fact:]
            new_facts[fact_id] = fact
        group = copy.deepcopy(group)
        group["facts"] = {key: new_facts[key] for key in sorted(new_facts)}
        group["latest_collective_proposals"] = list(
            group.get("latest_collective_proposals") or []
        )[-LIMITS.collective_proposals_retained:]
        compacted_groups[group_id] = group
    registry["groups"] = {key: compacted_groups[key] for key in sorted(compacted_groups)}
    registry["processed_proposal_keys"] = list(
        registry.get("processed_proposal_keys") or []
    )[-LIMITS.processed_proposal_keys:]

    for proposal_limit in range(
        LIMITS.collective_proposals_retained - 1,
        LIMITS.minimum_collective_proposals_retained - 1,
        -1,
    ):
        if len(canonical_json(registry).encode("utf-8")) <= LIMITS.payload_target_bytes:
            return
        for group in (registry.get("groups") or {}).values():
            group["latest_collective_proposals"] = list(
                group.get("latest_collective_proposals") or []
            )[-proposal_limit:]
    for history_limit in range(
        LIMITS.support_history_per_fact - 1,
        LIMITS.minimum_support_history_per_fact - 1,
        -1,
    ):
        if len(canonical_json(registry).encode("utf-8")) <= LIMITS.payload_target_bytes:
            return
        for group in (registry.get("groups") or {}).values():
            for fact in (group.get("facts") or {}).values():
                fact["support_history"] = list(
                    fact.get("support_history") or []
                )[-history_limit:]
    if len(canonical_json(registry).encode("utf-8")) <= LIMITS.proposal_bytes:
        return
    for processed_limit in (64, 32, 16):
        if len(canonical_json(registry).encode("utf-8")) <= LIMITS.proposal_bytes:
            return
        registry["processed_proposal_keys"] = list(
            registry.get("processed_proposal_keys") or []
        )[-processed_limit:]


def advance_group_state_registry(
    existing: dict | None,
    supports: list[dict],
    association_registry: dict,
    tick: int,
) -> tuple[dict, list[dict]]:
    if existing:
        if existing.get("schema_version") != GROUP_STATE_REGISTRY_VERSION:
            raise GroupStateContractError(
                f"unsupported group state schema: {existing.get('schema_version')}"
            )
        registry = copy.deepcopy(existing)
    else:
        registry = empty_group_state_registry(tick)
    recognised = _recognised_groups(association_registry)
    processed = list(registry.get("processed_proposal_keys") or [])
    processed_set = set(processed)
    transitions = []
    groups = copy.deepcopy(registry.get("groups") or {})

    for support in sorted(supports, key=lambda item: item["support_id"]):
        proposal_key = support["proposal_key"]
        if proposal_key in processed_set:
            continue
        group_id = support["group_id"]
        candidate = recognised.get(group_id)
        if not candidate:
            continue
        group = copy.deepcopy(groups.get(group_id) or _group_state_template(group_id, candidate, tick))
        group["member_ids"] = sorted(candidate.get("member_ids") or [])[:LIMITS.participants_per_support]
        group["group_type"] = candidate.get("group_type")
        group["recognised_tick"] = candidate.get("recognised_tick")
        group["recognition_event_id"] = candidate.get("recognition_event_id")
        group["association_revision_seen"] = int(association_registry.get("revision", 0))
        facts = copy.deepcopy(group.get("facts") or {})
        fact = copy.deepcopy(facts.get(support["fact_id"]) or _fact_template(support))
        transition = "created" if fact["support_count"] == 0 else "supported"
        fact["participant_ids"] = list(support["participant_ids"])
        fact["support_count"] = min(9999, int(fact.get("support_count", 0)) + 1)
        fact["support_event_ids"] = _bounded_ids(
            list(fact.get("support_event_ids") or []) + support["support_event_ids"]
        )
        fact["support_evidence_ids"] = _bounded_ids(
            list(fact.get("support_evidence_ids") or []) + support["support_evidence_ids"]
        )
        fact["support_history"] = (list(fact.get("support_history") or []) + [{
            "support_id": support["support_id"],
            "proposal_key": proposal_key,
            "tick": int(support["tick"]),
            "participant_ids": list(support["participant_ids"]),
            "support_event_ids": list(support["support_event_ids"])[-4:],
            "support_evidence_ids": list(support["support_evidence_ids"])[-4:],
        }])[-LIMITS.support_history_per_fact:]
        fact["last_supported_tick"] = int(support["tick"])
        fact["pending_event_tick"] = int(tick)
        fact["pending_transition"] = transition
        fact["revision"] = int(fact.get("revision", 0)) + 1
        facts[support["fact_id"]] = fact
        group["facts"] = {key: facts[key] for key in sorted(facts)}
        group["revision"] = int(group.get("revision", 0)) + 1
        group["last_updated_tick"] = int(tick)
        group["latest_collective_proposals"] = (
            list(group.get("latest_collective_proposals") or []) + [{
                "schema_version": GROUP_COLLECTIVE_PROPOSAL_VERSION,
                "proposal_key": proposal_key,
                "category": support["category"],
                "target_id": support["target_id"],
                "participant_ids": list(support["participant_ids"]),
                "support_event_ids": list(support["support_event_ids"])[-4:],
                "support_evidence_ids": list(support["support_evidence_ids"])[-4:],
                "tick": int(tick),
                "accepted_event_id": None,
            }]
        )[-LIMITS.collective_proposals_retained:]
        groups[group_id] = group
        processed.append(proposal_key)
        processed_set.add(proposal_key)
        transitions.append({
            "group_id": group_id,
            "fact_id": support["fact_id"],
            "category": support["category"],
            "target_id": support["target_id"],
            "kind": transition,
            "proposal_key": proposal_key,
        })

    registry["groups"] = groups
    registry["processed_proposal_keys"] = processed
    registry["revision"] = int(registry.get("revision", 0)) + 1
    registry["last_updated_tick"] = int(tick)
    _compact_registry(registry)
    return registry, transitions


def _bounded_supports(supports: list[dict], existing: dict | None = None) -> list[dict]:
    processed = set((existing or {}).get("processed_proposal_keys") or [])
    kept = []
    parents: set[str] = set()
    for support in sorted(copy.deepcopy(supports), key=lambda item: item["support_id"]):
        if support.get("proposal_key") in processed:
            continue
        next_parents = parents | set(support.get("support_event_ids") or [])
        association_event_id = support.get("association_event_id")
        if association_event_id:
            next_parents.add(association_event_id)
        if len(next_parents) > LIMITS.causal_parents_per_proposal:
            continue
        kept.append(support)
        parents = next_parents
        if len(kept) >= LIMITS.support_items_per_proposal:
            break
    return kept


def build_group_state_proposal(
    entities: dict,
    tick: int,
    *,
    supports: list[dict] | None = None,
    filter_processed: bool = True,
) -> dict | None:
    association = entities.get(ASSOCIATION_REGISTRY_ID)
    if not isinstance(association, dict) or association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return None
    existing = entities.get(GROUP_STATE_REGISTRY_ID)
    if supports is None:
        supports = derive_group_support_evidence(entities, tick)
    supports = _bounded_supports(supports, existing if filter_processed else None)
    if not supports:
        return None
    registry, transitions = advance_group_state_registry(existing, supports, association, tick)
    association_parent = association.get("last_event_id")
    continuity_parent = (existing or {}).get("last_event_id")
    parent_ids = _bounded_ids(
        ([association_parent] if association_parent else [])
        + ([continuity_parent] if continuity_parent else []),
        LIMITS.causal_parents_per_proposal,
    )
    if not parent_ids:
        return None

    if existing:
        mutation = {"entity_updates": {GROUP_STATE_REGISTRY_ID: registry}, "new_entities": {}}
        prior_revision = int(existing.get("revision", 0))
        preconditions = [{
            "entity_id": GROUP_STATE_REGISTRY_ID,
            "field": "revision",
            "op": "eq",
            "value": prior_revision,
        }]
    else:
        mutation = {"new_entities": {GROUP_STATE_REGISTRY_ID: registry}, "entity_updates": {}}
        prior_revision = None
        preconditions = []
    preconditions.append({
        "entity_id": ASSOCIATION_REGISTRY_ID,
        "field": "revision",
        "op": "eq",
        "value": int(association.get("revision", 0)),
    })

    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    metadata = {
        "schema_version": GROUP_COLLECTIVE_PROPOSAL_VERSION,
        "registry_id": GROUP_STATE_REGISTRY_ID,
        "association_registry_id": ASSOCIATION_REGISTRY_ID,
        "association_registry_revision": int(association.get("revision", 0)),
        "prior_revision": prior_revision,
        "next_revision": int(registry["revision"]),
        "support_items": copy.deepcopy(supports),
        "support_count": len(supports),
        "proposal_keys": [support["proposal_key"] for support in supports],
        "transitions": copy.deepcopy(transitions[:LIMITS.support_items_per_proposal]),
        "group_count": len(registry["groups"]),
        "fact_count": sum(len(group.get("facts") or {}) for group in registry["groups"].values()),
        "payload_bytes": payload_bytes,
    }
    return {
        "proposal_family": "group_collective",
        "proposal_type": "update_group_shared_state",
        "proposer_engine_id": "group_state",
        "proposer_engine_version": "1.0.0",
        "entity_id": GROUP_STATE_REGISTRY_ID,
        "causal_parent_event_ids": parent_ids,
        "is_exogenous": False,
        "requested_time": int(tick),
        "phase": "agent",
        "engine_priority": 89,
        "touched_scope": [GROUP_STATE_REGISTRY_ID, ASSOCIATION_REGISTRY_ID],
        "preconditions": preconditions,
        "mutation": mutation,
        "group_state_update": metadata,
        "explanation": (
            f"bounded shared-group state revision {registry['revision']}; "
            f"supports={len(supports)} transitions={len(transitions)}"
        ),
    }


def build_duplicate_group_state_probe(entities: dict, tick: int) -> dict | None:
    """Build one deterministic invalid duplicate proposal for diagnostics.

    This is used only by the Stage 7B scenario domain to prove rejected
    collective proposals cause no partial mutation.
    """
    registry = entities.get(GROUP_STATE_REGISTRY_ID)
    association = entities.get(ASSOCIATION_REGISTRY_ID)
    if not isinstance(registry, dict) or not isinstance(association, dict):
        return None
    for group in (registry.get("groups") or {}).values():
        for fact in (group.get("facts") or {}).values():
            history = list(fact.get("support_history") or [])
            if not history:
                continue
            support_row = history[-1]
            try:
                support = make_group_support_evidence(
                    group_id=group["group_id"],
                    category=fact["category"],
                    target_id=fact["target_id"],
                    participant_ids=support_row["participant_ids"],
                    tick=int(support_row["tick"]),
                    support_event_ids=support_row["support_event_ids"],
                    support_evidence_ids=support_row["support_evidence_ids"],
                    association_record_ids=[],
                    association_registry_revision=int(association.get("revision", 0)),
                    association_event_id=association.get("last_event_id"),
                )
            except ValueError:
                continue
            proposal = build_group_state_proposal(
                entities, tick, supports=[support], filter_processed=False,
            )
            if proposal:
                proposal["explanation"] = "diagnostic duplicate collective proposal rejection"
                proposal["engine_priority"] = 91
                return proposal
    return None


def _proposed_registry(proposal: dict) -> dict | None:
    mutation = proposal.get("mutation") or {}
    return (
        (mutation.get("new_entities") or {}).get(GROUP_STATE_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(GROUP_STATE_REGISTRY_ID)
    )


def _invalid_group_reason(association: dict, group_id: str) -> str | None:
    candidate = (association.get("group_candidates") or {}).get(group_id)
    if candidate and candidate.get("recognition_state") == "recognised":
        return None
    if group_id in _dissolved_group_ids(association):
        return "group_state.group_dissolved"
    return "group_state.group_not_recognised"


def _validate_support_item(support: dict, proposal: dict, entities: dict, tick: int) -> str | None:
    if not isinstance(support, dict) or support.get("schema_version") != GROUP_SUPPORT_EVIDENCE_VERSION:
        return "group_state.invalid_support"
    group_id = support.get("group_id")
    category = support.get("category")
    target_id = support.get("target_id")
    participant_ids = support.get("participant_ids")
    if category not in ALLOWED_SHARED_FACT_CATEGORIES:
        return "group_state.invalid_category"
    if not isinstance(participant_ids, list) or participant_ids != sorted(set(participant_ids)) or len(participant_ids) != 2:
        return "group_state.invalid_participants"
    association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    group_reason = _invalid_group_reason(association, group_id)
    if group_reason:
        return group_reason
    candidate = (association.get("group_candidates") or {}).get(group_id) or {}
    members = set(candidate.get("member_ids") or [])
    if not set(participant_ids).issubset(members):
        return "group_state.non_member_support"
    for participant_id in participant_ids:
        participant = entities.get(participant_id)
        if not participant or participant.get("type") != "person" or not participant.get("alive", True):
            return "group_state.invalid_participant"
    if not _target_is_permitted(entities, category, target_id):
        return "group_state.invalid_target"
    support_tick = int(support.get("tick", -999999))
    if support_tick > int(tick) or int(tick) - support_tick > SUPPORT_FRESHNESS_TICKS:
        return "group_state.stale_support"
    support_events = list(support.get("support_event_ids") or [])
    if len(support_events) > LIMITS.provenance_refs:
        return "group_state.provenance_limit"
    if len([event_id for event_id in support_events if not event_id.startswith("evt-0-")]) < 2:
        return "group_state.invalid_participation"
    if support.get("association_event_id") not in set(proposal.get("causal_parent_event_ids") or []):
        return "group_state.invalid_provenance"
    evidence_ids = list(support.get("support_evidence_ids") or [])
    if not evidence_ids:
        return "group_state.invalid_support"
    records = (association.get("association_records") or {})
    pair_id = association_pair_id(participant_ids)
    record = records.get(pair_id)
    if not record:
        return "group_state.missing_association_evidence"
    found = False
    for evidence in record.get("recent_evidence") or []:
        if evidence.get("evidence_id") not in evidence_ids:
            continue
        if (
            evidence.get("category") == category
            and sorted(evidence.get("person_ids") or record.get("person_ids") or []) == participant_ids
            and target_id in (evidence.get("condition_ids") or [])
            and set(support_events).issubset(set(evidence.get("source_event_ids") or []))
        ):
            found = True
            break
    if not found:
        return "group_state.missing_association_evidence"
    expected_fact = shared_group_fact_id(group_id, category, target_id)
    if support.get("fact_id") != expected_fact:
        return "group_state.invalid_fact_identity"
    expected_key = collective_proposal_key(support)
    if support.get("proposal_key") != expected_key:
        return "group_state.invalid_proposal_key"
    existing = entities.get(GROUP_STATE_REGISTRY_ID) or {}
    if expected_key in (existing.get("processed_proposal_keys") or []):
        return "group_state.duplicate_collective_proposal"
    return None


def validate_group_state_proposal(proposal: dict, entities: dict) -> str | None:
    metadata = proposal.get("group_state_update")
    if metadata is None:
        return None
    if not isinstance(metadata, dict) or metadata.get("schema_version") != GROUP_COLLECTIVE_PROPOSAL_VERSION:
        return "group_state.invalid_proposal_version"
    if proposal.get("entity_id") != GROUP_STATE_REGISTRY_ID or metadata.get("registry_id") != GROUP_STATE_REGISTRY_ID:
        return "group_state.invalid_registry_id"
    if metadata.get("association_registry_id") != ASSOCIATION_REGISTRY_ID:
        return "group_state.invalid_association_registry"
    association = entities.get(ASSOCIATION_REGISTRY_ID)
    if not isinstance(association, dict) or association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return "group_state.association_registry_missing"
    if int(metadata.get("association_registry_revision", -1)) != int(association.get("revision", -2)):
        return "group_state.stale_membership"

    mutation = proposal.get("mutation") or {}
    new_entities = mutation.get("new_entities") or {}
    entity_updates = mutation.get("entity_updates") or {}
    removed = mutation.get("removed_entities") or []
    allowed_new = set(new_entities) <= {GROUP_STATE_REGISTRY_ID}
    allowed_updates = set(entity_updates) <= {GROUP_STATE_REGISTRY_ID}
    if not allowed_new or not allowed_updates or removed:
        return "group_state.invalid_mutation_scope"
    registry = _proposed_registry(proposal)
    if not isinstance(registry, dict) or registry.get("schema_version") != GROUP_STATE_REGISTRY_VERSION:
        return "group_state.invalid_registry_schema"
    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    if payload_bytes > LIMITS.proposal_bytes or int(metadata.get("payload_bytes", -1)) != payload_bytes:
        return "group_state.payload_limit"

    existing = entities.get(GROUP_STATE_REGISTRY_ID)
    new_registry = GROUP_STATE_REGISTRY_ID in new_entities
    if existing and new_registry:
        return "group_state.duplicate_registry"
    expected_revision = int(existing.get("revision", 0)) + 1 if existing else 1
    if int(registry.get("revision", -1)) != expected_revision:
        return "group_state.invalid_revision"
    if metadata.get("prior_revision") != (int(existing.get("revision", 0)) if existing else None):
        return "group_state.invalid_revision"
    if int(metadata.get("next_revision", -1)) != expected_revision:
        return "group_state.invalid_revision"

    required = {
        (condition.get("entity_id"), condition.get("field"), condition.get("op"), condition.get("value"))
        for condition in (proposal.get("preconditions") or [])
    }
    if (ASSOCIATION_REGISTRY_ID, "revision", "eq", int(association.get("revision", 0))) not in required:
        return "group_state.missing_association_precondition"
    if existing and (GROUP_STATE_REGISTRY_ID, "revision", "eq", int(existing.get("revision", 0))) not in required:
        return "group_state.missing_revision_precondition"

    supports = metadata.get("support_items")
    if not isinstance(supports, list) or not supports:
        return "group_state.missing_collective_support"
    if len(supports) > LIMITS.support_items_per_proposal:
        return "group_state.support_limit"
    seen_keys = []
    for support in supports:
        reason = _validate_support_item(
            support, proposal, entities, int(proposal.get("requested_time", 0)),
        )
        if reason:
            return reason
        seen_keys.append(support["proposal_key"])
    if seen_keys != metadata.get("proposal_keys"):
        return "group_state.metadata_mismatch"
    if len(seen_keys) != len(set(seen_keys)):
        return "group_state.duplicate_collective_proposal"

    try:
        expected_registry, transitions = advance_group_state_registry(
            existing, supports, association, int(proposal.get("requested_time", 0)),
        )
    except (TypeError, ValueError, GroupStateContractError):
        return "group_state.invalid_registry_schema"
    if expected_registry != registry:
        return "group_state.mutation_mismatch"
    if int(metadata.get("group_count", -1)) != len(registry.get("groups") or {}):
        return "group_state.metadata_mismatch"
    fact_count = sum(len(group.get("facts") or {}) for group in (registry.get("groups") or {}).values())
    if int(metadata.get("fact_count", -1)) != fact_count:
        return "group_state.metadata_mismatch"
    if len(registry.get("groups") or {}) > LIMITS.groups:
        return "group_state.group_limit"
    if len(registry.get("processed_proposal_keys") or []) > LIMITS.processed_proposal_keys:
        return "group_state.processed_limit"
    forbidden = {"goals", "inventory", "leader_id", "culture", "authority", "obedience"}
    for group in (registry.get("groups") or {}).values():
        if group.get("schema_version") != SHARED_GROUP_STATE_VERSION or forbidden & set(group):
            return "group_state.invalid_group_state"
        if len(group.get("facts") or {}) > LIMITS.facts_per_group:
            return "group_state.fact_limit"
        if len(group.get("latest_collective_proposals") or []) > LIMITS.collective_proposals_retained:
            return "group_state.proposal_history_limit"
        for fact_id, fact in (group.get("facts") or {}).items():
            if (
                fact.get("schema_version") != SHARED_GROUP_FACT_VERSION
                or fact_id != fact.get("fact_id")
                or fact.get("category") not in ALLOWED_SHARED_FACT_CATEGORIES
                or shared_group_fact_id(group["group_id"], fact["category"], fact["target_id"]) != fact_id
                or len(fact.get("participant_ids") or []) > LIMITS.participants_per_support
                or len(fact.get("support_event_ids") or []) > LIMITS.provenance_refs
                or len(fact.get("support_history") or []) > LIMITS.support_history_per_fact
            ):
                return "group_state.invalid_fact"
    if metadata.get("transitions") != transitions[:LIMITS.support_items_per_proposal]:
        return "group_state.metadata_mismatch"
    return None


def stamp_group_state_provenance(proposal: dict, mutation: dict, event_id: str) -> None:
    metadata = proposal.get("group_state_update")
    if not isinstance(metadata, dict):
        return
    registry = (
        (mutation.get("new_entities") or {}).get(GROUP_STATE_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(GROUP_STATE_REGISTRY_ID)
    )
    if not isinstance(registry, dict):
        return
    tick = int(proposal.get("requested_time", 0))
    proposal_keys = set(metadata.get("proposal_keys") or [])
    for group in (registry.get("groups") or {}).values():
        for fact in (group.get("facts") or {}).values():
            if int(fact.get("pending_event_tick") or -1) == tick:
                if fact.get("created_event_id") is None:
                    fact["created_event_id"] = event_id
                fact["last_event_id"] = event_id
                fact["pending_event_tick"] = None
                fact["pending_transition"] = None
        for row in group.get("latest_collective_proposals") or []:
            if row.get("proposal_key") in proposal_keys and row.get("accepted_event_id") is None:
                row["accepted_event_id"] = event_id
    metadata["accepted_event_id"] = event_id


def group_state_diagnostics(registry: dict, tick: int) -> dict:
    groups = registry.get("groups") or {}
    facts = [
        fact
        for group in groups.values()
        for fact in (group.get("facts") or {}).values()
    ]
    return {
        "schema_version": "group-state-diagnostics-v1",
        "tick": int(tick),
        "registry_revision": int(registry.get("revision", 0)),
        "group_count": len(groups),
        "fact_count": len(facts),
        "processed_proposal_count": len(registry.get("processed_proposal_keys") or []),
        "latest_fact_ids": sorted(fact.get("fact_id") for fact in facts if fact.get("fact_id"))[:32],
        "caps": {
            "groups": LIMITS.groups,
            "facts_per_group": LIMITS.facts_per_group,
            "support_history_per_fact": LIMITS.support_history_per_fact,
            "minimum_support_history_per_fact": LIMITS.minimum_support_history_per_fact,
            "participants_per_support": LIMITS.participants_per_support,
            "provenance_refs": LIMITS.provenance_refs,
            "collective_proposals_retained": LIMITS.collective_proposals_retained,
            "processed_proposal_keys": LIMITS.processed_proposal_keys,
            "minimum_collective_proposals_retained": LIMITS.minimum_collective_proposals_retained,
            "support_items_per_proposal": LIMITS.support_items_per_proposal,
            "causal_parents_per_proposal": LIMITS.causal_parents_per_proposal,
            "payload_target_bytes": LIMITS.payload_target_bytes,
            "proposal_bytes": LIMITS.proposal_bytes,
        },
    }


def group_state_capacity_diagnostics(registry: dict) -> dict:
    """Return an exact, non-canonical semantic partition of registry bytes."""
    provenance_fields = {
        "accepted_event_id", "created_event_id", "creation_event_id",
        "last_event_id", "recognition_event_id", "support_event_ids",
        "support_evidence_ids",
    }

    def classify(path: tuple, _value, _is_key: bool) -> str | None:
        fields = {part for part in path if isinstance(part, str)}
        if "processed_proposal_keys" in fields:
            return "processed_proposal_key_bytes"
        if fields & provenance_fields:
            return "provenance_reference_bytes"
        if "latest_collective_proposals" in fields:
            return "retained_proposal_summary_bytes"
        if "support_history" in fields:
            return "historical_support_evidence_bytes"
        if fields & {"groups", "facts"}:
            return "current_truth_bytes"
        return None

    composition = {
        "current_truth_bytes": 0,
        "historical_support_evidence_bytes": 0,
        "processed_proposal_key_bytes": 0,
        "retained_proposal_summary_bytes": 0,
        "provenance_reference_bytes": 0,
        "other_structural_overhead_bytes": 0,
    }
    composition.update(canonical_byte_composition(registry, classify))
    return {
        "total_serialized_bytes": len(canonical_json(registry).encode("utf-8")),
        **composition,
    }


def group_state_current_truth_summary(registry: dict) -> dict:
    """Build a read-only diagnostic summary; it is not canonical authority."""
    groups = {}
    for group_id, group in sorted((registry.get("groups") or {}).items()):
        facts = {}
        for fact_id, fact in sorted((group.get("facts") or {}).items()):
            facts[fact_id] = {
                "category": fact.get("category"),
                "target_id": fact.get("target_id"),
                "participant_ids": list(fact.get("participant_ids") or []),
                "support_count": int(fact.get("support_count", 0)),
                "created_tick": fact.get("created_tick"),
                "last_supported_tick": fact.get("last_supported_tick"),
                "revision": int(fact.get("revision", 0)),
            }
        groups[group_id] = {
            "group_type": group.get("group_type"),
            "member_ids": list(group.get("member_ids") or []),
            "recognised_tick": group.get("recognised_tick"),
            "revision": int(group.get("revision", 0)),
            "facts": facts,
        }
    return {"groups": groups}
