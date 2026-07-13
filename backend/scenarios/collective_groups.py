"""Capability Stage 7B shared-group state scenario activation."""
from dataclasses import replace

from scenarios.emergent_groups import SCENARIO as EMERGENT_GROUPS
from scenarios.registry import register_scenario


SCENARIO = replace(
    EMERGENT_GROUPS,
    id="collective_groups",
    name="Bounded Shared Group State Camp",
    description=(
        "The emergent-groups camp with bounded shared group facts and the "
        "strict collective proposal contract enabled; group agency remains disabled."
    ),
    enabled_domains=[*EMERGENT_GROUPS.enabled_domains, "group_state"],
    presentation={
        **EMERGENT_GROUPS.presentation,
        "capability_stage": "7B",
    },
)

register_scenario(SCENARIO)
