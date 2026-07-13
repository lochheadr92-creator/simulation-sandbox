"""Stage 7B proposal-only bounded shared-group state domain."""
from __future__ import annotations

from domains.base import DomainEngine, DomainOutput
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_ID,
    build_duplicate_group_state_probe,
    build_group_state_proposal,
    group_state_diagnostics,
)


class GroupStateDomain(DomainEngine):
    engine_id = "group_state"
    engine_version = "1.0.0"
    engine_priority = 89
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        has_association_registry = ASSOCIATION_REGISTRY_ID in entities
        return [GROUP_STATE_REGISTRY_ID] if has_association_registry else []

    def activate(self, frame) -> DomainOutput:
        if not frame.due_entity_ids:
            return DomainOutput()
        proposals = []
        proposal = build_group_state_proposal(frame.entities, frame.simulation_time)
        if proposal is not None:
            proposals.append(proposal)
        if frame.simulation_time % 20 == 0:
            duplicate_probe = build_duplicate_group_state_probe(
                frame.entities, frame.simulation_time,
            )
            if duplicate_probe is not None:
                proposals.append(duplicate_probe)
        diagnostics = {}
        registry = None
        if proposal is not None:
            mutation = proposal["mutation"]
            registry = (
                (mutation.get("new_entities") or {}).get(GROUP_STATE_REGISTRY_ID)
                or (mutation.get("entity_updates") or {}).get(GROUP_STATE_REGISTRY_ID)
            )
        elif GROUP_STATE_REGISTRY_ID in frame.entities:
            registry = frame.entities[GROUP_STATE_REGISTRY_ID]
        if registry:
            diagnostics[GROUP_STATE_REGISTRY_ID] = group_state_diagnostics(
                registry, frame.simulation_time,
            )
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)
