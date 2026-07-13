"""Bounded read-only Stage 7B shared-group state projection."""
from __future__ import annotations

import copy

from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_VERSION,
    LIMITS,
)


def build_group_state_projection(
    registry: dict,
    *,
    diagnostics: dict | None = None,
) -> dict:
    if registry.get("schema_version") != GROUP_STATE_REGISTRY_VERSION:
        raise ValueError("unsupported group-state registry projection schema")
    groups = registry.get("groups") or {}
    return {
        "projection_version": "group-state-projection-v1",
        "registry_version": registry.get("schema_version"),
        "revision": int(registry.get("revision", 0)),
        "groups": [
            {
                "group_id": group.get("group_id"),
                "group_type": group.get("group_type"),
                "member_ids": list(group.get("member_ids") or []),
                "recognised_tick": group.get("recognised_tick"),
                "recognition_event_id": group.get("recognition_event_id"),
                "association_revision_seen": group.get("association_revision_seen"),
                "revision": int(group.get("revision", 0)),
                "facts": [
                    {
                        "fact_id": fact.get("fact_id"),
                        "category": fact.get("category"),
                        "target_id": fact.get("target_id"),
                        "participant_ids": list(fact.get("participant_ids") or []),
                        "support_count": int(fact.get("support_count", 0)),
                        "created_tick": fact.get("created_tick"),
                        "last_supported_tick": fact.get("last_supported_tick"),
                        "created_event_id": fact.get("created_event_id"),
                        "last_event_id": fact.get("last_event_id"),
                        "support_event_ids": list(fact.get("support_event_ids") or [])[-8:],
                        "support_evidence_ids": list(fact.get("support_evidence_ids") or [])[-8:],
                        "support_history": copy.deepcopy(
                            (fact.get("support_history") or [])[-LIMITS.support_history_per_fact:]
                        ),
                    }
                    for fact in (group.get("facts") or {}).values()
                ],
                "latest_collective_proposals": copy.deepcopy(
                    (group.get("latest_collective_proposals") or [])[
                        -LIMITS.collective_proposals_retained:
                    ]
                ),
            }
            for group in (groups[group_id] for group_id in sorted(groups)[:LIMITS.groups])
        ],
        "processed_proposal_count": len(registry.get("processed_proposal_keys") or []),
        "diagnostics": copy.deepcopy(diagnostics or {}),
        "caps": {
            "groups": LIMITS.groups,
            "facts_per_group": LIMITS.facts_per_group,
            "support_history_per_fact": LIMITS.support_history_per_fact,
            "processed_proposal_keys": LIMITS.processed_proposal_keys,
            "support_items_per_proposal": LIMITS.support_items_per_proposal,
            "proposal_bytes": LIMITS.proposal_bytes,
        },
    }
