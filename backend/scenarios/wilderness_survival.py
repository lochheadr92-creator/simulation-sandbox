"""Wilderness Survival - the original Phase 1/2 scenario (kept as scenario
id "basic_survival" for backward compatibility with existing runs/tests).
Open grassland, a central lake, scattered trees, people + animals."""
from scenarios.base import Scenario
from scenarios.registry import register_scenario

SCENARIO = Scenario(
    id="basic_survival",
    name="Wilderness Survival",
    description="Open grassland with a central lake, scattered trees, autonomous people and animals.",
    enabled_domains=["ecology", "lifecycle", "people", "animal"],
    world_gen={
        "width": 20, "height": 20,
        "ground_terrain": "grass",
        "water_blob_count": 1, "water_radius_range": (2, 3),
        "num_people": 6, "num_animals": 6, "num_trees": 16,
        "tree_resource_range": (40, 80),
        "person_hunger_range": (100, 300), "person_thirst_range": (100, 300), "person_energy_range": (700, 1000),
        "animal_hunger_range": (100, 300), "animal_energy_range": (700, 1000),
    },
    presentation={"ground_label": "grassland", "water_label": "lake"},
)

register_scenario(SCENARIO)
