"""Stage 7A proposal-only emergent association domain."""
from __future__ import annotations

from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    association_diagnostics,
    build_association_proposal,
)
from domains.base import DomainEngine, DomainOutput


class AssociationDomain(DomainEngine):
    engine_id = "association"
    engine_version = "1.0.0"
    engine_priority = 90
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        has_people = any(
            entity.get("type") == "person" and entity.get("alive", True)
            for entity in entities.values()
        )
        return [ASSOCIATION_REGISTRY_ID] if has_people else []

    def activate(self, frame) -> DomainOutput:
        if not frame.due_entity_ids:
            return DomainOutput()
        proposal = build_association_proposal(frame.entities, frame.simulation_time)
        if proposal is None:
            return DomainOutput()
        mutation = proposal["mutation"]
        registry = (
            (mutation.get("new_entities") or {}).get(ASSOCIATION_REGISTRY_ID)
            or (mutation.get("entity_updates") or {}).get(ASSOCIATION_REGISTRY_ID)
        )
        return DomainOutput(
            proposals=[proposal],
            diagnostics={
                ASSOCIATION_REGISTRY_ID: association_diagnostics(
                    registry, frame.simulation_time,
                )
            },
        )
