"""Stage 7C proposal-only group collective action domain.

Reads pinned association + shared-group state + member entities. Emits
coordinated storage-deposit proposals. Never mutates state directly.
"""
from __future__ import annotations

from domains.base import DomainEngine, DomainOutput
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_state_contracts import GROUP_STATE_REGISTRY_ID
from domains.group_collective_contracts import (
    build_group_collective_proposals,
    collective_action_diagnostics,
    derive_coordinated_deposits,
)


class GroupCollectiveDomain(DomainEngine):
    engine_id = "group_collective"
    engine_version = "1.0.0"
    engine_priority = 90
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        if ASSOCIATION_REGISTRY_ID in entities and GROUP_STATE_REGISTRY_ID in entities:
            return [GROUP_STATE_REGISTRY_ID]
        return []

    def activate(self, frame) -> DomainOutput:
        if not frame.due_entity_ids:
            return DomainOutput()
        proposals = build_group_collective_proposals(frame.entities, frame.simulation_time)
        actions = derive_coordinated_deposits(frame.entities, frame.simulation_time)
        diagnostics = {
            GROUP_STATE_REGISTRY_ID: collective_action_diagnostics(
                actions, frame.simulation_time,
            ),
        }
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)
