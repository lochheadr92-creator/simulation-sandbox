"""Stage 8B Leg 1 proposal-only norm-carriage domain (formation backfill +
transmission). Contract: memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md.
"""
from __future__ import annotations

from domains.base import DomainEngine, DomainOutput
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_goal_contracts import GROUP_GOAL_REGISTRY_ID
from domains.group_norm_contracts import GROUP_NORM_REGISTRY_ID
from domains.group_carriage_contracts import (
    GROUP_CARRIAGE_REGISTRY_ID,
    build_group_carriage_proposal,
    group_carriage_diagnostics,
)


class GroupCarriageDomain(DomainEngine):
    engine_id = "group_carriage"
    engine_version = "1.0.0"
    # Prior-frame semantics (see the contract's Commit ordering section, and
    # group_carriage_contracts.py's module docstring): this domain reads
    # group-norm-000 (87) and group-goal-000 (88) as of end-of-tick-(T-1),
    # like every domain in this kernel, regardless of engine_priority.
    # engine_priority = 86 only ensures its own pinned revisions of those two
    # registries are revalidated BEFORE group_norm/group_goal's own proposals
    # this same tick get a chance to bump them - avoiding a same-tick
    # stale-precondition rejection, one layer below 8A's own 87-before-88 fix.
    engine_priority = 86  # before group_norm (87), group_goal (88), group_state (89), association (90)
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        if (ASSOCIATION_REGISTRY_ID in entities
                and GROUP_GOAL_REGISTRY_ID in entities
                and GROUP_NORM_REGISTRY_ID in entities):
            return [GROUP_CARRIAGE_REGISTRY_ID]
        return []

    def activate(self, frame) -> DomainOutput:
        if not frame.due_entity_ids:
            return DomainOutput()
        proposals = []
        proposal = build_group_carriage_proposal(frame.entities, frame.simulation_time)
        if proposal is not None:
            proposals.append(proposal)
        diagnostics = {}
        registry = None
        if proposal is not None:
            mutation = proposal["mutation"]
            registry = (
                (mutation.get("new_entities") or {}).get(GROUP_CARRIAGE_REGISTRY_ID)
                or (mutation.get("entity_updates") or {}).get(GROUP_CARRIAGE_REGISTRY_ID)
            )
        elif GROUP_CARRIAGE_REGISTRY_ID in frame.entities:
            registry = frame.entities[GROUP_CARRIAGE_REGISTRY_ID]
        if registry:
            diagnostics[GROUP_CARRIAGE_REGISTRY_ID] = group_carriage_diagnostics(
                registry, frame.simulation_time,
            )
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)
