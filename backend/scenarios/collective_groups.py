"""Capability Stage 7B/7C shared-group state and collective action scenario."""
import copy
from dataclasses import replace

from scenarios.emergent_groups import SCENARIO as EMERGENT_GROUPS
from scenarios.registry import register_scenario


# Place two camp members adjacent to shared storage so Stage 7C coordinated
# deposit is organically reachable once 7A recognition + 7B shared_storage
# facts form. Positions remain ordinary genesis inputs (not test injection).
_WORLD = dict(EMERGENT_GROUPS.world_gen)

# Stage 6 Liveness Pass (change 3 of 3): make the settlement's food supply
# self-sustaining over a 1,000-tick horizon so the camp does not collapse from
# chronic starvation before Stage 7D goals can be observed active at the end of
# the run. The inherited food-patch is a non-regrowing type=="resource" pool of
# 12 (only trees regrow), so eight agents starve out by ~tick 790. We raise it
# to mirror the settlement's water_source (quantity 999): food becomes as
# available as water, letting >=2 members survive to tick 1000 and hold their
# collective shelter goal to the end. Contained to this scenario only:
# extra_genesis_specs is DEEP-COPIED first because dict(world_gen) is a shallow
# copy that would otherwise share (and mutate) the frozen living_settlement /
# emergent_groups genesis list. See STAGE-6-LIVENESS-PASS.md.
_SPECS = copy.deepcopy(_WORLD.get("extra_genesis_specs") or [])
for _spec in _SPECS:
    if _spec.get("id") == "food-patch":
        _spec["quantity"] = 999
_WORLD["extra_genesis_specs"] = _SPECS
_WORLD["person_positions"] = [
    {"x": 5, "y": 4},  # adjacent to storage-camp (5,5)
    {"x": 5, "y": 6},  # adjacent to storage-camp (5,5)
    {"x": 4, "y": 5},
    {"x": 6, "y": 5},
    {"x": 6, "y": 4},
    {"x": 4, "y": 6},
    {"x": 4, "y": 4},
    {"x": 6, "y": 6},
]
_PROFILES = [dict(profile) for profile in (_WORLD.get("person_profiles") or [])]
if len(_PROFILES) >= 2:
    # Ensure two storage-adjacent people begin with depositable surplus.
    _PROFILES[0] = {
        **_PROFILES[0],
        "carried_resources": {"food": 2, "wood": 1},
        "hunger": min(int(_PROFILES[0].get("hunger", 400)), 500),
    }
    _PROFILES[1] = {
        **_PROFILES[1],
        "carried_resources": {"food": 2, "wood": 1},
    }
_WORLD["person_profiles"] = _PROFILES


SCENARIO = replace(
    EMERGENT_GROUPS,
    id="collective_groups",
    name="Bounded Shared Group State Camp",
    description=(
        "The emergent-groups camp with bounded shared group facts, the "
        "strict Stage 7B collective-support contract, and Stage 7C "
        "coordinated storage deposit. Groups remain non-magical: members "
        "and Core authority produce collective consequences."
    ),
    enabled_domains=[
        *EMERGENT_GROUPS.enabled_domains,
        "group_state",
        "group_collective",
        "group_goal",
        "group_norm",
        "group_carriage",
    ],
    world_gen=_WORLD,
    presentation={
        **EMERGENT_GROUPS.presentation,
        "capability_stage": "8B",
    },
)

register_scenario(SCENARIO)
