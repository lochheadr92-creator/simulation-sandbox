"""Desert Oasis - second demonstration scenario (Phase 3 architectural
proof). Intentionally different from Wilderness Survival: arid sand
terrain, a single small oasis instead of a lake, scarce trees, and NO
animal domain enabled at all - proving that a scenario can opt out of an
entire domain engine with zero Core changes. Reuses the exact same People
domain (perception/planning/utility/interruption) and Ecology domain
unmodified; only configuration differs."""
from scenarios.base import Scenario
from scenarios.registry import register_scenario

SCENARIO = Scenario(
    id="desert_oasis",
    name="Desert Oasis",
    description=(
        "Arid sand terrain around a single small oasis pool with scarce trees and no wildlife - "
        "survival hinges on the oasis and scarce forage. Reuses the same People behaviour engine "
        "in a harsher, more contested world; the Animal domain is disabled entirely for this scenario."
    ),
    enabled_domains=["ecology", "people"],
    world_gen={
        "width": 20, "height": 20,
        "ground_terrain": "sand",
        "water_blob_count": 1, "water_radius_range": (1, 2),
        "num_people": 6, "num_animals": 0, "num_trees": 6,
        "tree_resource_range": (25, 45),
        "person_hunger_range": (150, 350), "person_thirst_range": (200, 400), "person_energy_range": (600, 900),
    },
    presentation={"ground_label": "sand dunes", "water_label": "oasis pool"},
)

register_scenario(SCENARIO)
