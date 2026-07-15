"""Stage 7D proposal-only group-goal and emergent-leadership domain."""
from __future__ import annotations

from domains.base import DomainEngine, DomainOutput
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_state_contracts import GROUP_STATE_REGISTRY_ID
from domains.group_goal_contracts import (
    GROUP_GOAL_REGISTRY_ID,
    build_group_goal_proposal,
    group_goal_diagnostics,
)


class GroupGoalDomain(DomainEngine):
    engine_id = "group_goal"
    engine_version = "1.0.0"
    engine_priority = 91  # after group_state (89) and group_collective (90)
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        if ASSOCIATION_REGISTRY_ID in entities and GROUP_STATE_REGISTRY_ID in entities:
            return [GROUP_GOAL_REGISTRY_ID]
        return []

    def activate(self, frame) -> DomainOutput:
        if not frame.due_entity_ids:
            return DomainOutput()
        proposals = []
        proposal = build_group_goal_proposal(frame.entities, frame.simulation_time)
        if proposal is not None:
            proposals.append(proposal)
        diagnostics = {}
        registry = None
        if proposal is not None:
            mutation = proposal["mutation"]
            registry = (
                (mutation.get("new_entities") or {}).get(GROUP_GOAL_REGISTRY_ID)
                or (mutation.get("entity_updates") or {}).get(GROUP_GOAL_REGISTRY_ID)
            )
        elif GROUP_GOAL_REGISTRY_ID in frame.entities:
            registry = frame.entities[GROUP_GOAL_REGISTRY_ID]
        if registry:
            diagnostics[GROUP_GOAL_REGISTRY_ID] = group_goal_diagnostics(
                registry, frame.simulation_time,
            )
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)
