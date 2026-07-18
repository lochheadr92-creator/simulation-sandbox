"""Stage 8A proposal-only emergent-norm domain (shelter-upkeep norm)."""
from __future__ import annotations

from domains.base import DomainEngine, DomainOutput
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_goal_contracts import GROUP_GOAL_REGISTRY_ID
from domains.group_norm_contracts import (
    GROUP_NORM_REGISTRY_ID,
    build_group_norm_proposal,
    group_norm_diagnostics,
)


class GroupNormDomain(DomainEngine):
    engine_id = "group_norm"
    engine_version = "1.0.0"
    # Prior-frame semantics: group_norm reads the Stage 7D group-goal registry (88)
    # to count repeated adoptions. It commits BEFORE group_goal (88), group_state
    # (89) and association (90) churn their revisions this tick, so its pinned
    # upstream revisions still match at commit-time revalidation (the same fix that
    # cleared the Stage 7D same-frame stale_membership rejection, one level deeper).
    # The cost is a documented one-tick lag: at tick T it sees the group-goal
    # registry as of end-of-tick T-1, so it counts each adoption exactly one tick
    # after group_goal commits it. Deterministic and harmless over long runs.
    engine_priority = 87  # before group_goal (88), group_state (89), association (90)
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        if ASSOCIATION_REGISTRY_ID in entities and GROUP_GOAL_REGISTRY_ID in entities:
            return [GROUP_NORM_REGISTRY_ID]
        return []

    def activate(self, frame) -> DomainOutput:
        if not frame.due_entity_ids:
            return DomainOutput()
        proposals = []
        proposal = build_group_norm_proposal(frame.entities, frame.simulation_time)
        if proposal is not None:
            proposals.append(proposal)
        diagnostics = {}
        registry = None
        if proposal is not None:
            mutation = proposal["mutation"]
            registry = (
                (mutation.get("new_entities") or {}).get(GROUP_NORM_REGISTRY_ID)
                or (mutation.get("entity_updates") or {}).get(GROUP_NORM_REGISTRY_ID)
            )
        elif GROUP_NORM_REGISTRY_ID in frame.entities:
            registry = frame.entities[GROUP_NORM_REGISTRY_ID]
        if registry:
            diagnostics[GROUP_NORM_REGISTRY_ID] = group_norm_diagnostics(
                registry, frame.simulation_time,
            )
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)
