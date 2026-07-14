"""Stage 7A deterministic association evidence and group-candidate contracts.

The functions in this module are pure.  They inspect a pinned canonical frame,
produce a bounded next registry value, and build proposals.  Core validates and
stamps accepted-event provenance before the generic mutation path applies it.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from itertools import combinations

from core.hashing import canonical_byte_composition, canonical_hash, canonical_json


ASSOCIATION_REGISTRY_ID = "association-registry-000"
ASSOCIATION_REGISTRY_VERSION = "association-registry-v1"
ASSOCIATION_EVIDENCE_VERSION = "association-evidence-v1"
GROUP_CANDIDATE_VERSION = "group-candidate-v1"
ASSOCIATION_PROPOSAL_VERSION = "association-proposal-v1"

GROUP_TYPES = (
    "household_like",
    "travelling_working",
    "persistent_association",
)

EVIDENCE_WEIGHTS = {
    "caregiving": 7,
    "shared_shelter": 7,
    "resource_sharing": 6,
    "mutual_protection": 5,
    "cooperation": 5,
    "shared_storage": 5,
    "coordinated_travel": 4,
    "dependency": 4,
    "coordinated_action": 3,
    "proximity": 1,
    "conflict": -8,
    "separation": -2,
}
POSITIVE_CATEGORIES = frozenset(
    category for category, weight in EVIDENCE_WEIGHTS.items() if weight > 0
)
MEANINGFUL_CATEGORIES = POSITIVE_CATEGORIES - {"proximity"}
HOUSEHOLD_CATEGORIES = frozenset({"caregiving", "shared_shelter", "dependency"})
TRAVELLING_WORKING_CATEGORIES = frozenset({
    "cooperation", "shared_storage", "coordinated_travel", "coordinated_action",
})

DIRECT_ACTION_CATEGORIES = {
    "help": "caregiving",
    "offer_help": "caregiving",
    "give": "resource_sharing",
    "cooperate": "cooperation",
    "warn": "mutual_protection",
    "request_help": "dependency",
    "promise": "dependency",
    "repay": "dependency",
    "trade": "coordinated_action",
    "refuse": "conflict",
    "threaten": "conflict",
    "confront": "conflict",
    "compete": "conflict",
    "take": "conflict",
}


@dataclass(frozen=True)
class AssociationLimits:
    records: int = 48
    records_per_person: int = 8
    evidence_categories: int = len(EVIDENCE_WEIGHTS)
    detailed_evidence_per_record: int = 8
    category_provenance_refs: int = 2
    provenance_refs: int = 16
    candidates: int = 24
    members_per_candidate: int = 8
    dissolved_history: int = 8
    processed_evidence_ids: int = 96
    evidence_items_per_proposal: int = 64
    causal_parents_per_proposal: int = 32
    payload_target_bytes: int = 96 * 1024
    proposal_bytes: int = 128 * 1024


LIMITS = AssociationLimits()

PAIR_STRENGTH_MAX = 100
CATEGORY_SCORE_MAX = 100
CANDIDATE_CREATE_STRENGTH = 9
MEMBER_LINK_STRENGTH = 8
RECOGNITION_STRENGTH = 18
RECOGNITION_SUPPORT_TICKS = 3
HOUSEHOLD_TYPE_SCORE = 10
TRAVELLING_WORKING_TYPE_SCORE = 8
WEAKEN_AFTER_TICKS = 3
MEMBER_REMOVAL_GRACE_TICKS = 5
CANDIDATE_EXPIRY_TICKS = 6
RECOGNISED_DISSOLUTION_TICKS = 8
PAIR_EXPIRY_TICKS = 12


class AssociationContractError(ValueError):
    """Raised when canonical Stage 7A state cannot be interpreted safely."""


def association_pair_id(person_ids: list[str] | tuple[str, str]) -> str:
    members = sorted(set(str(person_id) for person_id in person_ids))
    if len(members) != 2:
        raise ValueError("association evidence requires exactly two distinct people")
    return "association-" + canonical_hash([
        ASSOCIATION_EVIDENCE_VERSION,
        members,
    ])[:20]


def group_candidate_id(
    founding_pair_id: str,
    first_supported_tick: int,
    formation_event_ids: list[str],
) -> str:
    decisive = sorted(set(str(event_id) for event_id in formation_event_ids))[:4]
    if not decisive:
        raise ValueError("group identity requires accepted formation evidence")
    return "group-" + canonical_hash([
        GROUP_CANDIDATE_VERSION,
        founding_pair_id,
        int(first_supported_tick),
        decisive,
    ])[:20]


def make_association_evidence(
    person_ids: list[str] | tuple[str, str],
    category: str,
    tick: int,
    source_event_ids: list[str] | tuple[str, ...],
    *,
    condition_ids: list[str] | tuple[str, ...] = (),
) -> dict:
    members = sorted(set(str(person_id) for person_id in person_ids))
    if len(members) != 2:
        raise ValueError("association evidence requires exactly two distinct people")
    if category not in EVIDENCE_WEIGHTS:
        raise ValueError(f"unsupported association evidence category: {category}")
    event_ids = sorted(set(str(event_id) for event_id in source_event_ids if event_id))
    if not event_ids:
        raise ValueError("association evidence requires accepted-event provenance")
    conditions = sorted(set(str(condition_id) for condition_id in condition_ids if condition_id))
    evidence_id = "assoc-evidence-" + canonical_hash([
        ASSOCIATION_EVIDENCE_VERSION,
        members,
        category,
        int(tick),
        event_ids,
        conditions,
    ])[:20]
    contribution = EVIDENCE_WEIGHTS[category]
    return {
        "schema_version": ASSOCIATION_EVIDENCE_VERSION,
        "evidence_id": evidence_id,
        "pair_id": association_pair_id(members),
        "person_ids": members,
        "category": category,
        "contribution": contribution,
        "polarity": "reinforce" if contribution > 0 else "weaken",
        "tick": int(tick),
        "source_event_ids": event_ids[:LIMITS.provenance_refs],
        "condition_ids": conditions[:4],
    }


def empty_association_registry(tick: int = 0) -> dict:
    return {
        "type": "association_registry",
        "schema_version": ASSOCIATION_REGISTRY_VERSION,
        "revision": 0,
        "association_records": {},
        "group_candidates": {},
        "dissolved_history": [],
        "processed_evidence_ids": [],
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
    }


def _bounded_event_ids(values) -> list[str]:
    return sorted(set(str(value) for value in (values or []) if value))[-LIMITS.provenance_refs:]


def _compact_evidence_detail(evidence: dict) -> dict:
    """Keep the non-derivable evidence fields needed by Stage 7B validation."""
    return {
        "evidence_id": evidence["evidence_id"],
        "category": evidence["category"],
        "tick": int(evidence["tick"]),
        "source_event_ids": list(evidence.get("source_event_ids") or []),
        "condition_ids": list(evidence.get("condition_ids") or []),
    }


def _position_distance(left: dict | None, right: dict | None) -> int | None:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return None
    if not all(key in left and key in right for key in ("x", "y")):
        return None
    return abs(int(left["x"]) - int(right["x"])) + abs(int(left["y"]) - int(right["y"]))


def _accepted_action(entity: dict) -> dict | None:
    action = entity.get("action")
    if not isinstance(action, dict) or not action.get("accepted_event_id"):
        return None
    return action


def _action_target_person(action: dict, actor_id: str, people: dict) -> str | None:
    candidates = list(action.get("participants") or []) + list(action.get("target_entity_ids") or [])
    target_id = action.get("target_entity_id")
    if target_id:
        candidates.append(target_id)
    valid = sorted({
        candidate for candidate in candidates
        if candidate != actor_id and candidate in people
    })
    return valid[0] if valid else None


def _near_shared_shelter(left: dict, right: dict, entities: dict) -> str | None:
    for entity_id, entity in sorted(entities.items()):
        if entity.get("type") not in ("shelter", "structure"):
            continue
        if entity.get("structure_kind") not in (None, "shelter"):
            continue
        if entity.get("access") not in ("shared", "public"):
            continue
        if (_position_distance(left.get("position"), entity.get("position")) or 0) <= 1 \
                and (_position_distance(right.get("position"), entity.get("position")) or 0) <= 1:
            return entity_id
    return None


def derive_association_evidence(entities: dict, tick: int) -> list[dict]:
    """Derive bounded pair evidence only from accepted canonical conditions."""
    people = {
        entity_id: entity for entity_id, entity in sorted(entities.items())
        if entity.get("type") == "person" and entity.get("alive", True)
    }
    observations: dict[str, dict] = {}

    def add(item: dict) -> None:
        observations[item["evidence_id"]] = item

    for actor_id, actor in people.items():
        action = _accepted_action(actor)
        if not action:
            continue
        category = DIRECT_ACTION_CATEGORIES.get(action.get("type"))
        target_id = _action_target_person(action, actor_id, people)
        if category and target_id:
            add(make_association_evidence(
                [actor_id, target_id],
                category,
                int(action.get("started_tick", tick)),
                [action["accepted_event_id"]],
                condition_ids=[action.get("action_id")],
            ))

    for left_id, right_id in combinations(sorted(people), 2):
        left, right = people[left_id], people[right_id]
        left_action, right_action = _accepted_action(left), _accepted_action(right)
        left_parent = (left_action or {}).get("accepted_event_id") or left.get("last_event_id")
        right_parent = (right_action or {}).get("accepted_event_id") or right.get("last_event_id")
        parents = [event_id for event_id in (left_parent, right_parent) if event_id]
        distance = _position_distance(left.get("position"), right.get("position"))
        if parents and distance is not None and distance <= 1:
            add(make_association_evidence(
                [left_id, right_id], "proximity", tick, parents,
                condition_ids=[f"distance:{distance}"],
            ))

        if left_action and right_action:
            left_tick = int(left_action.get("started_tick", -1))
            right_tick = int(right_action.get("started_tick", -1))
            action_parents = [left_action["accepted_event_id"], right_action["accepted_event_id"]]
            if (left_action.get("type") == right_action.get("type") == "move"
                    and left_tick == right_tick and distance is not None and distance <= 2):
                add(make_association_evidence(
                    [left_id, right_id], "coordinated_travel", max(left_tick, right_tick),
                    action_parents,
                ))
            if left_action.get("type") == right_action.get("type") == "rest" and left_tick == right_tick:
                shelter_id = _near_shared_shelter(left, right, entities)
                if shelter_id:
                    shelter = entities[shelter_id]
                    shelter_event = shelter.get("last_event_id") or shelter.get("creation_event_id")
                    add(make_association_evidence(
                        [left_id, right_id], "shared_shelter", max(left_tick, right_tick),
                        action_parents + ([shelter_event] if shelter_event else []),
                        condition_ids=[shelter_id],
                    ))
            storage_actions = {"store", "retrieve", "access"}
            left_targets = sorted(left_action.get("target_entity_ids") or [])
            right_targets = sorted(right_action.get("target_entity_ids") or [])
            shared_targets = sorted(set(left_targets) & set(right_targets))
            if (left_action.get("type") in storage_actions
                    and right_action.get("type") in storage_actions
                    and abs(left_tick - right_tick) <= 4 and shared_targets):
                storage_id = shared_targets[0]
                storage = entities.get(storage_id) or {}
                if storage.get("type") in ("storage", "container") and storage.get("access") in ("shared", "public"):
                    add(make_association_evidence(
                        [left_id, right_id], "shared_storage", max(left_tick, right_tick),
                        action_parents, condition_ids=[storage_id],
                    ))

        pair_id = association_pair_id([left_id, right_id])
        registry = entities.get(ASSOCIATION_REGISTRY_ID) or {}
        if (pair_id in (registry.get("association_records") or {})
                and parents and distance is not None and distance >= 6):
            add(make_association_evidence(
                [left_id, right_id], "separation", tick, parents,
                condition_ids=[f"distance:{distance}"],
            ))

    return [observations[key] for key in sorted(observations)]


def _bounded_observations(observations: list[dict]) -> list[dict]:
    kept = []
    parent_ids: set[str] = set()
    for evidence in sorted(observations, key=lambda item: item["evidence_id"]):
        candidate_parents = parent_ids | set(evidence.get("source_event_ids") or [])
        if len(candidate_parents) > LIMITS.causal_parents_per_proposal:
            continue
        kept.append(copy.deepcopy(evidence))
        parent_ids = candidate_parents
        if len(kept) >= LIMITS.evidence_items_per_proposal:
            break
    return kept


def _empty_record(person_ids: list[str], tick: int) -> dict:
    pair_id = association_pair_id(person_ids)
    return {
        "schema_version": ASSOCIATION_EVIDENCE_VERSION,
        "pair_id": pair_id,
        "person_ids": sorted(person_ids),
        "strength": 0,
        "first_supported_tick": int(tick),
        "last_support_tick": None,
        "last_updated_tick": int(tick),
        "support_ticks": [],
        "categories": {},
        "recent_evidence": [],
        "causal_event_ids": [],
    }


def _meaningful_score(record: dict) -> int:
    return sum(
        int(summary.get("score", 0))
        for category, summary in (record.get("categories") or {}).items()
        if category in MEANINGFUL_CATEGORIES
    )


def _qualifying_link(record: dict | None) -> bool:
    return bool(
        record
        and int(record.get("strength", 0)) >= MEMBER_LINK_STRENGTH
        and len(set(record.get("support_ticks") or [])) >= 2
        and _meaningful_score(record) > 0
    )


def _record_for(records: dict, left_id: str, right_id: str) -> dict | None:
    return records.get(association_pair_id([left_id, right_id]))


def _category_totals(records: list[dict]) -> dict[str, int]:
    totals = {}
    for record in records:
        for category, summary in (record.get("categories") or {}).items():
            totals[category] = min(
                CATEGORY_SCORE_MAX,
                totals.get(category, 0) + int(summary.get("score", 0)),
            )
    return {key: totals[key] for key in sorted(totals)}


def _infer_group_type(category_totals: dict) -> str:
    household = sum(int(category_totals.get(category, 0)) for category in HOUSEHOLD_CATEGORIES)
    travelling = sum(
        int(category_totals.get(category, 0))
        for category in TRAVELLING_WORKING_CATEGORIES
    )
    if household >= HOUSEHOLD_TYPE_SCORE and household >= travelling:
        return "household_like"
    if travelling >= TRAVELLING_WORKING_TYPE_SCORE:
        return "travelling_working"
    return "persistent_association"


def _candidate_records(candidate: dict, records: dict) -> list[dict]:
    out = []
    for left_id, right_id in combinations(candidate.get("member_ids") or [], 2):
        record = _record_for(records, left_id, right_id)
        if record:
            out.append(record)
    return out


def _history_summary(candidate: dict, state: str, tick: int) -> dict:
    event_ids = _bounded_event_ids(
        list(candidate.get("causal_event_ids") or [])
        + list((candidate.get("formation_evidence_summary") or {}).get("decisive_event_ids") or [])
    )
    return {
        "schema_version": GROUP_CANDIDATE_VERSION,
        "candidate_id": candidate["candidate_id"],
        "founding_pair_id": candidate.get("founding_pair_id"),
        "group_type": candidate.get("group_type"),
        "final_member_ids": sorted(candidate.get("member_ids") or []),
        "final_state": state,
        "first_supported_tick": int(candidate.get("first_supported_tick", tick)),
        "recognised_tick": candidate.get("recognised_tick"),
        "dissolved_tick": int(tick),
        "formation_event_ids": event_ids[:8],
        "dissolution_cause_event_ids": event_ids[-8:],
        "dissolution_event_id": None,
        "pending_transition": state,
        "pending_transition_tick": int(tick),
    }


def _prune_records(records: dict) -> dict:
    ranked = sorted(
        records.items(),
        key=lambda pair: (
            -int(pair[1].get("strength", 0)),
            -int(pair[1].get("last_support_tick") or -1),
            pair[0],
        ),
    )
    counts: dict[str, int] = {}
    kept = {}
    for pair_id, record in ranked:
        people = record.get("person_ids") or []
        if len(kept) >= LIMITS.records:
            break
        if any(counts.get(person_id, 0) >= LIMITS.records_per_person for person_id in people):
            continue
        kept[pair_id] = record
        for person_id in people:
            counts[person_id] = counts.get(person_id, 0) + 1
    return {key: kept[key] for key in sorted(kept)}


def _fit_registry_payload(registry: dict) -> None:
    """Deterministically compact detail while preserving bounded summaries."""
    records = registry.get("association_records") or {}
    for detail_limit in range(LIMITS.detailed_evidence_per_record - 1, 0, -1):
        if len(canonical_json(registry).encode("utf-8")) <= LIMITS.payload_target_bytes:
            return
        for record in records.values():
            record["recent_evidence"] = list(record.get("recent_evidence") or [])[-detail_limit:]
    if len(canonical_json(registry).encode("utf-8")) <= LIMITS.proposal_bytes:
        return
    for detail_limit in (0,):
        if len(canonical_json(registry).encode("utf-8")) <= LIMITS.proposal_bytes:
            return
        for record in records.values():
            record["recent_evidence"] = list(record.get("recent_evidence") or [])[-detail_limit:] \
                if detail_limit else []
    for processed_limit in (64, 32, 16):
        if len(canonical_json(registry).encode("utf-8")) <= LIMITS.proposal_bytes:
            return
        registry["processed_evidence_ids"] = list(
            registry.get("processed_evidence_ids") or []
        )[-processed_limit:]


def _apply_evidence(registry: dict, observations: list[dict], tick: int) -> None:
    records = copy.deepcopy(registry.get("association_records") or {})
    processed = list(registry.get("processed_evidence_ids") or [])
    processed_set = set(processed)

    for record in records.values():
        record["recent_evidence"] = [
            _compact_evidence_detail(evidence)
            for evidence in (record.get("recent_evidence") or [])
        ]
        for summary in (record.get("categories") or {}).values():
            summary["source_event_ids"] = _bounded_event_ids(
                summary.get("source_event_ids") or []
            )[-LIMITS.category_provenance_refs:]
        elapsed = max(0, int(tick) - int(record.get("last_updated_tick", tick)))
        record["strength"] = max(0, int(record.get("strength", 0)) - elapsed)
        for category, summary in (record.get("categories") or {}).items():
            if category in POSITIVE_CATEGORIES:
                summary["score"] = max(0, int(summary.get("score", 0)) - elapsed)
        record["last_updated_tick"] = int(tick)

    for evidence in sorted(observations, key=lambda item: item["evidence_id"]):
        evidence_id = evidence["evidence_id"]
        if evidence_id in processed_set:
            continue
        pair_id = evidence["pair_id"]
        record = copy.deepcopy(records.get(pair_id) or _empty_record(evidence["person_ids"], tick))
        contribution = int(evidence["contribution"])
        record["strength"] = max(
            0,
            min(PAIR_STRENGTH_MAX, int(record.get("strength", 0)) + contribution),
        )
        category = evidence["category"]
        categories = copy.deepcopy(record.get("categories") or {})
        summary = copy.deepcopy(categories.get(category) or {
            "score": 0,
            "support_count": 0,
            "first_tick": int(evidence["tick"]),
            "last_tick": int(evidence["tick"]),
            "source_event_ids": [],
        })
        summary["score"] = min(
            CATEGORY_SCORE_MAX,
            int(summary.get("score", 0)) + abs(contribution),
        )
        summary["support_count"] = min(9999, int(summary.get("support_count", 0)) + 1)
        summary["last_tick"] = int(evidence["tick"])
        summary["source_event_ids"] = _bounded_event_ids(
            list(summary.get("source_event_ids") or []) + evidence["source_event_ids"]
        )[-LIMITS.category_provenance_refs:]
        categories[category] = summary
        record["categories"] = {
            key: categories[key]
            for key in sorted(categories)[:LIMITS.evidence_categories]
        }
        if contribution > 0:
            support_ticks = sorted(set(
                list(record.get("support_ticks") or []) + [int(evidence["tick"])]
            ))
            record["support_ticks"] = support_ticks[-LIMITS.provenance_refs:]
            record["last_support_tick"] = int(evidence["tick"])
            record["first_supported_tick"] = min(
                int(record.get("first_supported_tick", evidence["tick"])),
                int(evidence["tick"]),
            )
        record["last_updated_tick"] = int(tick)
        detail = _compact_evidence_detail(evidence)
        recent = list(record.get("recent_evidence") or [])
        recent.append(detail)
        record["recent_evidence"] = recent[-LIMITS.detailed_evidence_per_record:]
        record["causal_event_ids"] = _bounded_event_ids(
            list(record.get("causal_event_ids") or []) + evidence["source_event_ids"]
        )
        records[pair_id] = record
        processed.append(evidence_id)
        processed_set.add(evidence_id)

    records = {
        pair_id: record for pair_id, record in records.items()
        if int(record.get("strength", 0)) > 0
        or int(tick) - int(record.get("last_support_tick") or tick) < PAIR_EXPIRY_TICKS
    }
    registry["association_records"] = _prune_records(records)
    registry["processed_evidence_ids"] = processed[-LIMITS.processed_evidence_ids:]


def _update_candidates(registry: dict, people: list[str], tick: int) -> list[dict]:
    records = registry.get("association_records") or {}
    candidates = copy.deepcopy(registry.get("group_candidates") or {})
    history = copy.deepcopy(registry.get("dissolved_history") or [])
    transitions = []
    removed_ids = []

    for candidate_id in sorted(candidates):
        candidate = candidates[candidate_id]
        members = sorted(set(candidate.get("member_ids") or []) & set(people))
        founding = set(candidate.get("founding_member_ids") or [])
        membership_evidence = copy.deepcopy(candidate.get("membership_evidence") or {})
        membership_changed = False

        for outsider_id in sorted(set(people) - set(members)):
            if len(members) >= LIMITS.members_per_candidate:
                break
            links = [_record_for(records, outsider_id, member_id) for member_id in members]
            if links and all(_qualifying_link(link) for link in links):
                members.append(outsider_id)
                members.sort()
                membership_evidence[outsider_id] = _bounded_event_ids([
                    event_id
                    for link in links
                    for event_id in (link.get("causal_event_ids") or [])
                ])[:4]
                membership_changed = True

        removed_members = []
        if len(members) > 2:
            for member_id in sorted(set(members) - founding):
                links = [
                    _record_for(records, member_id, other_id)
                    for other_id in members if other_id != member_id
                ]
                latest = max(
                    [int(link.get("last_support_tick") or -1) for link in links if link] or [-1]
                )
                if int(tick) - latest >= MEMBER_REMOVAL_GRACE_TICKS and len(members) - len(removed_members) > 2:
                    removed_members.append(member_id)
            if removed_members:
                members = [member_id for member_id in members if member_id not in removed_members]
                membership_changed = True

        candidate["member_ids"] = members
        candidate["membership_evidence"] = {
            member_id: _bounded_event_ids(membership_evidence.get(member_id) or [])[:4]
            for member_id in members
        }
        if removed_members:
            candidate["last_removed_member_ids"] = removed_members[:4]
            candidate["last_removal_reason"] = "support_grace_elapsed"

        internal_records = _candidate_records(candidate, records)
        required_edges = len(members) * (len(members) - 1) // 2
        complete = len(internal_records) == required_edges and required_edges > 0
        strength = min(
            [int(record.get("strength", 0)) for record in internal_records] or [0]
        ) if complete else 0
        support_ticks = sorted({
            support_tick
            for record in internal_records
            for support_tick in (record.get("support_ticks") or [])
        })
        latest_support = max(
            [int(record.get("last_support_tick") or -1) for record in internal_records] or [-1]
        )
        categories = _category_totals(internal_records)
        candidate["strength"] = strength
        candidate["confidence"] = min(1000, strength * 40 + len(support_ticks) * 20)
        candidate["group_type"] = _infer_group_type(categories)
        candidate["category_scores"] = categories
        candidate["most_recent_support_tick"] = max(
            int(candidate.get("most_recent_support_tick", -1)), latest_support,
        )
        candidate["causal_event_ids"] = _bounded_event_ids([
            event_id for record in internal_records
            for event_id in (record.get("causal_event_ids") or [])
        ])

        gap = int(tick) - int(candidate.get("most_recent_support_tick", tick))
        ever_recognised = bool(candidate.get("ever_recognised"))
        if (not ever_recognised and strength >= RECOGNITION_STRENGTH
                and len(support_ticks) >= RECOGNITION_SUPPORT_TICKS
                and int(tick) - int(candidate.get("first_supported_tick", tick)) >= 2):
            candidate["recognition_state"] = "recognised"
            candidate["ever_recognised"] = True
            candidate["recognised_tick"] = int(tick)
            candidate["weakening_since_tick"] = None
            candidate["pending_transition"] = "recognised"
            candidate["pending_transition_tick"] = int(tick)
            transitions.append({"candidate_id": candidate_id, "kind": "recognised"})
            ever_recognised = True
        elif ever_recognised and gap >= WEAKEN_AFTER_TICKS:
            if candidate.get("recognition_state") != "weakening":
                candidate["weakening_since_tick"] = int(tick)
                candidate["pending_transition"] = "weakened"
                candidate["pending_transition_tick"] = int(tick)
                transitions.append({"candidate_id": candidate_id, "kind": "weakened"})
            candidate["recognition_state"] = "weakening"
        elif ever_recognised:
            candidate["recognition_state"] = "recognised"
            candidate["weakening_since_tick"] = None

        if membership_changed:
            candidate["pending_transition"] = "membership_changed"
            candidate["pending_transition_tick"] = int(tick)
            transitions.append({
                "candidate_id": candidate_id,
                "kind": "membership_changed",
                "removed_member_ids": removed_members,
            })

        terminal_state = None
        if ever_recognised and gap >= RECOGNISED_DISSOLUTION_TICKS:
            terminal_state = "dissolved"
        elif not ever_recognised and gap >= CANDIDATE_EXPIRY_TICKS:
            terminal_state = "expired"
        if terminal_state:
            history.append(_history_summary(candidate, terminal_state, tick))
            transitions.append({"candidate_id": candidate_id, "kind": terminal_state})
            removed_ids.append(candidate_id)
        else:
            candidates[candidate_id] = candidate

    for candidate_id in removed_ids:
        candidates.pop(candidate_id, None)

    terminal_ids = {row.get("candidate_id") for row in history}
    terminal_pairs = {
        row.get("founding_pair_id"): int(row.get("dissolved_tick", -1))
        for row in history if row.get("founding_pair_id")
    }
    for pair_id, record in sorted(records.items()):
        if int(record.get("strength", 0)) < CANDIDATE_CREATE_STRENGTH:
            continue
        if len(set(record.get("support_ticks") or [])) < 2 or _meaningful_score(record) <= 0:
            continue
        members = sorted(record.get("person_ids") or [])
        if any(set(members).issubset(set(candidate.get("member_ids") or [])) for candidate in candidates.values()):
            continue
        if (pair_id in terminal_pairs
                and int(record.get("last_support_tick") or -1) <= terminal_pairs[pair_id]):
            continue
        formation_events = _bounded_event_ids(record.get("causal_event_ids") or [])
        candidate_id = group_candidate_id(
            pair_id, int(record.get("first_supported_tick", tick)), formation_events,
        )
        if candidate_id in candidates or candidate_id in terminal_ids:
            continue
        categories = _category_totals([record])
        candidates[candidate_id] = {
            "schema_version": GROUP_CANDIDATE_VERSION,
            "candidate_id": candidate_id,
            "founding_pair_id": pair_id,
            "founding_member_ids": members,
            "member_ids": members,
            "group_type": _infer_group_type(categories),
            "recognition_state": "candidate",
            "ever_recognised": False,
            "strength": int(record.get("strength", 0)),
            "confidence": min(1000, int(record.get("strength", 0)) * 40),
            "first_supported_tick": int(record.get("first_supported_tick", tick)),
            "most_recent_support_tick": int(record.get("last_support_tick") or tick),
            "recognised_tick": None,
            "weakening_since_tick": None,
            "category_scores": categories,
            "formation_evidence_summary": {
                "category_scores": categories,
                "decisive_event_ids": formation_events[:8],
                "support_ticks": list(record.get("support_ticks") or [])[-8:],
            },
            "membership_evidence": {
                member_id: formation_events[:4] for member_id in members
            },
            "causal_event_ids": formation_events,
            "last_removed_member_ids": [],
            "last_removal_reason": None,
            "formation_event_id": None,
            "recognition_event_id": None,
            "last_transition_event_id": None,
            "pending_transition": "formed",
            "pending_transition_tick": int(tick),
        }
        transitions.append({"candidate_id": candidate_id, "kind": "formed"})

    ranked = sorted(
        candidates.items(),
        key=lambda pair: (
            pair[1].get("recognition_state") != "recognised",
            -int(pair[1].get("strength", 0)),
            pair[0],
        ),
    )
    kept = dict(ranked[:LIMITS.candidates])
    for candidate_id, candidate in ranked[LIMITS.candidates:]:
        history.append(_history_summary(candidate, "pruned", tick))
        transitions.append({"candidate_id": candidate_id, "kind": "pruned"})
    registry["group_candidates"] = {key: kept[key] for key in sorted(kept)}
    registry["dissolved_history"] = sorted(
        history,
        key=lambda row: (int(row.get("dissolved_tick", 0)), row.get("candidate_id", "")),
    )[-LIMITS.dissolved_history:]
    return transitions


def advance_association_registry(
    existing: dict | None,
    observations: list[dict],
    people: list[str],
    tick: int,
) -> tuple[dict, list[dict]]:
    if existing:
        if existing.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
            raise AssociationContractError(
                f"unsupported association registry schema: {existing.get('schema_version')}"
            )
        registry = copy.deepcopy(existing)
    else:
        registry = empty_association_registry(tick)
    _apply_evidence(registry, observations, tick)
    transitions = _update_candidates(registry, sorted(set(people)), tick)
    registry["revision"] = int(registry.get("revision", 0)) + 1
    registry["last_updated_tick"] = int(tick)
    _fit_registry_payload(registry)
    return registry, transitions


def build_association_proposal(
    entities: dict,
    tick: int,
    *,
    observations: list[dict] | None = None,
) -> dict | None:
    existing = entities.get(ASSOCIATION_REGISTRY_ID)
    observations = _bounded_observations(copy.deepcopy(
        derive_association_evidence(entities, tick) if observations is None else observations
    ))
    if not existing and not observations:
        return None
    people = sorted(
        entity_id for entity_id, entity in entities.items()
        if entity.get("type") == "person" and entity.get("alive", True)
    )
    registry, transitions = advance_association_registry(existing, observations, people, tick)
    source_event_ids = _bounded_event_ids([
        event_id for evidence in observations
        for event_id in (evidence.get("source_event_ids") or [])
    ])
    retained_event_ids = [
        event_id
        for record in ((existing or {}).get("association_records") or {}).values()
        for event_id in (record.get("causal_event_ids") or [])
    ]
    continuity_parent = (existing or {}).get("last_event_id")
    if source_event_ids:
        parent_ids = sorted(set(
            source_event_ids + ([continuity_parent] if continuity_parent else [])
        ))
    else:
        parent_ids = _bounded_event_ids(
            ([continuity_parent] if continuity_parent else []) + retained_event_ids
        )
    if not parent_ids:
        return None

    if existing:
        mutation = {"entity_updates": {ASSOCIATION_REGISTRY_ID: registry}}
        preconditions = [{
            "entity_id": ASSOCIATION_REGISTRY_ID,
            "field": "revision",
            "op": "eq",
            "value": int(existing.get("revision", 0)),
        }]
    else:
        mutation = {"new_entities": {ASSOCIATION_REGISTRY_ID: registry}}
        preconditions = []

    metadata = {
        "schema_version": ASSOCIATION_PROPOSAL_VERSION,
        "registry_id": ASSOCIATION_REGISTRY_ID,
        "prior_revision": int(existing.get("revision", -1)) if existing else None,
        "next_revision": int(registry["revision"]),
        "source_event_ids": source_event_ids,
        "evidence_ids": [item["evidence_id"] for item in observations][
            -LIMITS.processed_evidence_ids:
        ],
        "transitions": copy.deepcopy(transitions[:LIMITS.candidates]),
        "record_count": len(registry["association_records"]),
        "candidate_count": len(registry["group_candidates"]),
        "payload_bytes": len(canonical_json(registry).encode("utf-8")),
    }
    return {
        "proposal_family": "emergent_association",
        "proposal_type": "update_association_registry",
        "proposer_engine_id": "association",
        "proposer_engine_version": "1.0.0",
        "entity_id": ASSOCIATION_REGISTRY_ID,
        "causal_parent_event_ids": parent_ids,
        "is_exogenous": False,
        "requested_time": int(tick),
        "phase": "agent",
        "engine_priority": 90,
        "touched_scope": [ASSOCIATION_REGISTRY_ID],
        "preconditions": preconditions,
        "mutation": mutation,
        "association_update": metadata,
        "explanation": (
            f"bounded association revision {registry['revision']}; "
            f"evidence={len(observations)} transitions={len(transitions)}"
        ),
    }


def _proposed_registry(proposal: dict) -> dict | None:
    mutation = proposal.get("mutation") or {}
    return (
        (mutation.get("new_entities") or {}).get(ASSOCIATION_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(ASSOCIATION_REGISTRY_ID)
    )


def validate_association_proposal(proposal: dict, entities: dict) -> str | None:
    metadata = proposal.get("association_update")
    if metadata is None:
        return None
    if not isinstance(metadata, dict) or metadata.get("schema_version") != ASSOCIATION_PROPOSAL_VERSION:
        return "association.invalid_proposal_version"
    if proposal.get("entity_id") != ASSOCIATION_REGISTRY_ID or metadata.get("registry_id") != ASSOCIATION_REGISTRY_ID:
        return "association.invalid_registry_id"
    registry = _proposed_registry(proposal)
    if not isinstance(registry, dict) or registry.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return "association.invalid_registry_schema"
    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    if payload_bytes > LIMITS.proposal_bytes or int(metadata.get("payload_bytes", -1)) != payload_bytes:
        return "association.payload_limit"

    existing = entities.get(ASSOCIATION_REGISTRY_ID)
    new_registry = ASSOCIATION_REGISTRY_ID in ((proposal.get("mutation") or {}).get("new_entities") or {})
    if existing and new_registry:
        return "association.duplicate_registry"
    expected_revision = int(existing.get("revision", 0)) + 1 if existing else 1
    if int(registry.get("revision", -1)) != expected_revision:
        return "association.invalid_revision"
    if existing:
        required = {
            (condition.get("entity_id"), condition.get("field"), condition.get("op"), condition.get("value"))
            for condition in (proposal.get("preconditions") or [])
        }
        if (ASSOCIATION_REGISTRY_ID, "revision", "eq", int(existing.get("revision", 0))) not in required:
            return "association.missing_revision_precondition"

    records = registry.get("association_records")
    candidates = registry.get("group_candidates")
    history = registry.get("dissolved_history")
    processed = registry.get("processed_evidence_ids")
    if not isinstance(records, dict) or len(records) > LIMITS.records:
        return "association.record_limit"
    if not isinstance(candidates, dict) or len(candidates) > LIMITS.candidates:
        return "association.candidate_limit"
    if not isinstance(history, list) or len(history) > LIMITS.dissolved_history:
        return "association.history_limit"
    if not isinstance(processed, list) or len(processed) > LIMITS.processed_evidence_ids:
        return "association.processed_limit"

    per_person: dict[str, int] = {}
    for pair_id, record in records.items():
        members = record.get("person_ids") if isinstance(record, dict) else None
        if (record.get("schema_version") != ASSOCIATION_EVIDENCE_VERSION
                or pair_id != record.get("pair_id")
                or not isinstance(members, list)
                or members != sorted(set(members))
                or len(members) != 2
                or association_pair_id(members) != pair_id):
            return "association.invalid_record"
        if any(
            member_id not in entities or entities[member_id].get("type") != "person"
            for member_id in members
        ):
            return "association.invalid_person"
        for member_id in members:
            per_person[member_id] = per_person.get(member_id, 0) + 1
            if per_person[member_id] > LIMITS.records_per_person:
                return "association.per_person_limit"
        if len(record.get("categories") or {}) > LIMITS.evidence_categories:
            return "association.category_limit"
        if not set(record.get("categories") or {}).issubset(EVIDENCE_WEIGHTS):
            return "association.invalid_category"
        for category, summary in (record.get("categories") or {}).items():
            if (not isinstance(summary, dict)
                    or len(summary.get("source_event_ids") or []) > LIMITS.category_provenance_refs
                    or int(summary.get("score", -1)) < 0
                    or int(summary.get("score", -1)) > CATEGORY_SCORE_MAX):
                return "association.invalid_category"
        if len(record.get("recent_evidence") or []) > LIMITS.detailed_evidence_per_record:
            return "association.evidence_limit"
        for evidence in record.get("recent_evidence") or []:
            if not isinstance(evidence, dict):
                return "association.invalid_evidence"
            try:
                expected = make_association_evidence(
                    record.get("person_ids") or [],
                    evidence.get("category"),
                    int(evidence.get("tick", 0)),
                    evidence.get("source_event_ids") or [],
                    condition_ids=evidence.get("condition_ids") or [],
                )
            except (TypeError, ValueError):
                return "association.invalid_evidence"
            if evidence not in (expected, _compact_evidence_detail(expected)):
                return "association.invalid_evidence"
        if len(record.get("causal_event_ids") or []) > LIMITS.provenance_refs:
            return "association.provenance_limit"
        if not 0 <= int(record.get("strength", -1)) <= PAIR_STRENGTH_MAX:
            return "association.invalid_strength"

    forbidden = {"goals", "collective_goal", "inventory", "leader_id", "culture", "owner_id"}
    for candidate_id, candidate in candidates.items():
        members = candidate.get("member_ids") if isinstance(candidate, dict) else None
        formation = (candidate.get("formation_evidence_summary") or {}).get("decisive_event_ids") or []
        if (candidate.get("schema_version") != GROUP_CANDIDATE_VERSION
                or candidate_id != candidate.get("candidate_id")
                or candidate.get("group_type") not in GROUP_TYPES
                or candidate.get("recognition_state") not in ("candidate", "recognised", "weakening")
                or not isinstance(members, list)
                or members != sorted(set(members))
                or not 2 <= len(members) <= LIMITS.members_per_candidate
                or forbidden & set(candidate)):
            return "association.invalid_candidate"
        if any(
            member_id not in entities or entities[member_id].get("type") != "person"
            for member_id in members
        ):
            return "association.invalid_member"
        try:
            expected_id = group_candidate_id(
                candidate.get("founding_pair_id"),
                int(candidate.get("first_supported_tick", 0)),
                formation,
            )
        except (TypeError, ValueError):
            return "association.invalid_candidate_identity"
        if expected_id != candidate_id:
            return "association.invalid_candidate_identity"
        if len(candidate.get("causal_event_ids") or []) > LIMITS.provenance_refs:
            return "association.provenance_limit"
        if not set(candidate.get("category_scores") or {}).issubset(EVIDENCE_WEIGHTS):
            return "association.invalid_category"

    for row in history:
        members = row.get("final_member_ids") if isinstance(row, dict) else None
        if (not isinstance(row, dict)
                or row.get("schema_version") != GROUP_CANDIDATE_VERSION
                or row.get("group_type") not in GROUP_TYPES
                or row.get("final_state") not in ("expired", "dissolved", "pruned")
                or not row.get("candidate_id")
                or not row.get("founding_pair_id")
                or not isinstance(members, list)
                or members != sorted(set(members))
                or not 2 <= len(members) <= LIMITS.members_per_candidate
                or forbidden & set(row)
                or len(row.get("formation_event_ids") or []) > 8
                or len(row.get("dissolution_cause_event_ids") or []) > 8):
            return "association.invalid_history"
        if any(
            member_id not in entities or entities[member_id].get("type") != "person"
            for member_id in members
        ):
            return "association.invalid_member"

    parent_ids = set(proposal.get("causal_parent_event_ids") or [])
    if not set(metadata.get("source_event_ids") or []).issubset(parent_ids):
        return "association.invalid_provenance"
    if int(metadata.get("record_count", -1)) != len(records) \
            or int(metadata.get("candidate_count", -1)) != len(candidates):
        return "association.metadata_mismatch"
    return None


def stamp_association_provenance(proposal: dict, mutation: dict, event_id: str) -> None:
    metadata = proposal.get("association_update")
    if not isinstance(metadata, dict):
        return
    registry = (
        (mutation.get("new_entities") or {}).get(ASSOCIATION_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(ASSOCIATION_REGISTRY_ID)
    )
    if not isinstance(registry, dict):
        return
    tick = int(proposal.get("requested_time", 0))
    for candidate in (registry.get("group_candidates") or {}).values():
        pending_tick = candidate.get("pending_transition_tick")
        if pending_tick is None or int(pending_tick) != tick:
            continue
        transition = candidate.get("pending_transition")
        if transition == "formed":
            candidate["formation_event_id"] = event_id
        elif transition == "recognised":
            candidate["recognition_event_id"] = event_id
        candidate["last_transition_event_id"] = event_id
        candidate["pending_transition"] = None
        candidate["pending_transition_tick"] = None
    for history in registry.get("dissolved_history") or []:
        pending_tick = history.get("pending_transition_tick")
        if pending_tick is not None and int(pending_tick) == tick:
            history["dissolution_event_id"] = event_id
            history["pending_transition"] = None
            history["pending_transition_tick"] = None
    metadata["accepted_event_id"] = event_id


def association_diagnostics(registry: dict, tick: int) -> dict:
    candidates = registry.get("group_candidates") or {}
    return {
        "schema_version": "association-diagnostics-v1",
        "tick": int(tick),
        "registry_revision": int(registry.get("revision", 0)),
        "record_count": len(registry.get("association_records") or {}),
        "candidate_count": len(candidates),
        "recognised_count": sum(
            1 for candidate in candidates.values()
            if candidate.get("recognition_state") == "recognised"
        ),
        "weakening_count": sum(
            1 for candidate in candidates.values()
            if candidate.get("recognition_state") == "weakening"
        ),
        "dissolved_retained": len(registry.get("dissolved_history") or []),
        "candidate_ids": sorted(candidates)[:LIMITS.candidates],
        "caps": {
            "records": LIMITS.records,
            "records_per_person": LIMITS.records_per_person,
            "detailed_evidence_per_record": LIMITS.detailed_evidence_per_record,
            "category_provenance_refs": LIMITS.category_provenance_refs,
            "provenance_refs": LIMITS.provenance_refs,
            "candidates": LIMITS.candidates,
            "members_per_candidate": LIMITS.members_per_candidate,
            "dissolved_history": LIMITS.dissolved_history,
            "processed_evidence_ids": LIMITS.processed_evidence_ids,
            "evidence_items_per_proposal": LIMITS.evidence_items_per_proposal,
            "causal_parents_per_proposal": LIMITS.causal_parents_per_proposal,
            "payload_target_bytes": LIMITS.payload_target_bytes,
            "proposal_bytes": LIMITS.proposal_bytes,
        },
    }


def association_capacity_diagnostics(registry: dict) -> dict:
    """Return an exact, non-canonical semantic partition of registry bytes."""
    provenance_fields = {
        "accepted_event_id", "causal_event_ids", "creation_event_id",
        "decisive_event_ids", "dissolution_cause_event_ids",
        "dissolution_event_id", "formation_event_id", "formation_event_ids",
        "last_event_id", "last_transition_event_id", "membership_evidence",
        "recognition_event_id", "source_event_ids",
    }
    history_fields = {
        "dissolved_history", "formation_evidence_summary", "recent_evidence",
        "support_ticks",
    }

    def classify(path: tuple, _value, _is_key: bool) -> str | None:
        fields = {part for part in path if isinstance(part, str)}
        if "processed_evidence_ids" in fields:
            return "processed_evidence_id_bytes"
        if fields & provenance_fields:
            return "provenance_reference_bytes"
        if fields & history_fields:
            return "historical_support_evidence_bytes"
        if fields & {"association_records", "group_candidates"}:
            return "current_truth_bytes"
        return None

    composition = {
        "current_truth_bytes": 0,
        "historical_support_evidence_bytes": 0,
        "processed_evidence_id_bytes": 0,
        "retained_proposal_summary_bytes": 0,
        "provenance_reference_bytes": 0,
        "other_structural_overhead_bytes": 0,
    }
    composition.update(canonical_byte_composition(registry, classify))
    return {
        "total_serialized_bytes": len(canonical_json(registry).encode("utf-8")),
        **composition,
    }


def association_current_truth_summary(registry: dict) -> dict:
    """Build a read-only diagnostic summary; it is not canonical authority."""
    records = {}
    for pair_id, record in sorted((registry.get("association_records") or {}).items()):
        records[pair_id] = {
            "person_ids": list(record.get("person_ids") or []),
            "strength": int(record.get("strength", 0)),
            "first_supported_tick": record.get("first_supported_tick"),
            "last_support_tick": record.get("last_support_tick"),
            "categories": {
                category: {
                    key: summary.get(key)
                    for key in ("score", "support_count", "first_tick", "last_tick")
                }
                for category, summary in sorted((record.get("categories") or {}).items())
            },
        }
    candidates = {}
    for candidate_id, candidate in sorted((registry.get("group_candidates") or {}).items()):
        candidates[candidate_id] = {
            "group_type": candidate.get("group_type"),
            "recognition_state": candidate.get("recognition_state"),
            "member_ids": list(candidate.get("member_ids") or []),
            "strength": int(candidate.get("strength", 0)),
            "confidence": int(candidate.get("confidence", 0)),
            "category_scores": copy.deepcopy(candidate.get("category_scores") or {}),
            "first_supported_tick": candidate.get("first_supported_tick"),
            "most_recent_support_tick": candidate.get("most_recent_support_tick"),
            "recognised_tick": candidate.get("recognised_tick"),
            "weakening_since_tick": candidate.get("weakening_since_tick"),
        }
    return {"association_records": records, "group_candidates": candidates}
