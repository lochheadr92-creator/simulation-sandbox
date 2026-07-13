"""Capability Stage 7A group-recognition scenario activation."""
from dataclasses import replace

from scenarios.living_settlement import SCENARIO as LIVING_SETTLEMENT
from scenarios.registry import register_scenario


SCENARIO = replace(
    LIVING_SETTLEMENT,
    id="emergent_groups",
    name="Emergent Group Recognition Camp",
    description=(
        "The validated living-agent camp with bounded causal association and "
        "group recognition enabled; collective agency remains disabled."
    ),
    enabled_domains=[*LIVING_SETTLEMENT.enabled_domains, "association"],
    presentation={
        **LIVING_SETTLEMENT.presentation,
        "capability_stage": "7A",
    },
)

register_scenario(SCENARIO)
