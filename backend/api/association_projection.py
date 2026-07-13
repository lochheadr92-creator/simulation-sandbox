"""Bounded read-only Stage 7A association explanation projection."""
from __future__ import annotations

import copy
from itertools import combinations

from domains.association_contracts import (
    ASSOCIATION_REGISTRY_VERSION,
    GROUP_CANDIDATE_VERSION,
    LIMITS,
    MEMBER_LINK_STRENGTH,
    association_pair_id,
)


def _candidate_projection(candidate: dict, records: dict, people: list[str]) -> dict:
    members = list(candidate.get("member_ids") or [])
    member_reasons = []
    for member_id in members:
        supporting_pairs = []
        source_event_ids = []
        for other_id in members:
            if other_id == member_id:
                continue
            record = records.get(association_pair_id([member_id, other_id])) or {}
            if int(record.get("strength", 0)) >= MEMBER_LINK_STRENGTH:
                supporting_pairs.append(record.get("pair_id"))
                source_event_ids.extend(record.get("causal_event_ids") or [])
        member_reasons.append({
            "person_id": member_id,
            "supporting_pair_ids": sorted(set(supporting_pairs)),
            "source_event_ids": sorted(set(source_event_ids))[-4:],
        })

    excluded = []
    for person_id in sorted(set(people) - set(members))[:16]:
        missing = []
        for member_id in members:
            record = records.get(association_pair_id([person_id, member_id])) or {}
            if int(record.get("strength", 0)) < MEMBER_LINK_STRENGTH:
                missing.append(member_id)
        excluded.append({
            "person_id": person_id,
            "reason": "missing_qualifying_complete_link",
            "missing_member_ids": missing,
        })

    return {
        "schema_version": GROUP_CANDIDATE_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "group_type": candidate.get("group_type"),
        "recognition_state": candidate.get("recognition_state"),
        "member_ids": members,
        "strength": int(candidate.get("strength", 0)),
        "confidence": int(candidate.get("confidence", 0)),
        "first_supported_tick": candidate.get("first_supported_tick"),
        "most_recent_support_tick": candidate.get("most_recent_support_tick"),
        "recognised_tick": candidate.get("recognised_tick"),
        "weakening_since_tick": candidate.get("weakening_since_tick"),
        "formation_evidence": copy.deepcopy(candidate.get("formation_evidence_summary") or {}),
        "category_scores": copy.deepcopy(candidate.get("category_scores") or {}),
        "last_removed_member_ids": list(candidate.get("last_removed_member_ids") or []),
        "last_removal_reason": candidate.get("last_removal_reason"),
        "formation_event_id": candidate.get("formation_event_id"),
        "recognition_event_id": candidate.get("recognition_event_id"),
        "last_transition_event_id": candidate.get("last_transition_event_id"),
        "member_explanations": member_reasons,
        "excluded_people": excluded,
    }


def build_association_projection(
    registry: dict,
    *,
    people: list[str] | None = None,
    diagnostics: dict | None = None,
) -> dict:
    if registry.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        raise ValueError("unsupported association registry projection schema")
    people = sorted(set(people or []))
    records = registry.get("association_records") or {}
    candidates = registry.get("group_candidates") or {}
    ranked_records = sorted(
        records.values(),
        key=lambda record: (
            -int(record.get("strength", 0)),
            record.get("pair_id", ""),
        ),
    )[:24]
    return {
        "projection_version": "association-projection-v1",
        "registry_version": registry.get("schema_version"),
        "revision": int(registry.get("revision", 0)),
        "groups": [
            _candidate_projection(candidates[candidate_id], records, people)
            for candidate_id in sorted(candidates)[:LIMITS.candidates]
        ],
        "association_records": [
            {
                "pair_id": record.get("pair_id"),
                "person_ids": list(record.get("person_ids") or []),
                "strength": int(record.get("strength", 0)),
                "first_supported_tick": record.get("first_supported_tick"),
                "last_support_tick": record.get("last_support_tick"),
                "categories": copy.deepcopy(record.get("categories") or {}),
                "decisive_event_ids": list(record.get("causal_event_ids") or [])[-8:],
            }
            for record in ranked_records
        ],
        "dissolved_history": copy.deepcopy(
            (registry.get("dissolved_history") or [])[-LIMITS.dissolved_history:]
        ),
        "diagnostics": copy.deepcopy(diagnostics or {}),
        "caps": {
            "groups": LIMITS.candidates,
            "members_per_group": LIMITS.members_per_candidate,
            "displayed_records": 24,
            "dissolved_history": LIMITS.dissolved_history,
        },
    }
