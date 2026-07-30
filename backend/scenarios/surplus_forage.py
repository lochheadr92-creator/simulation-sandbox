"""Surplus Forage - Surplus Pass benchmark/invariant scenario (SURPLUS_PASS.md).

Wilderness-survival layout scaled to 20 people with home storage assigned at
spawn (`assign_storage_location`). This is the only scenario whose persons
carry `storage_location`/`stored_resources`, so it is the only one where the
surplus proposal types (gather_excess / store / retrieve / offer_trade) can
fire. Same domain set as basic_survival: pure Needs + Resource flow.
"""
from scenarios.base import Scenario
from scenarios.registry import register_scenario

SCENARIO = Scenario(
    id="surplus_forage",
    name="Surplus Forage",
    description="Grassland with a lake and abundant trees; 20 people with home storage, carry capacity and barter trade.",
    enabled_domains=["ecology", "lifecycle", "people", "animal"],
    world_gen={
        "width": 26, "height": 26,
        "ground_terrain": "grass",
        "water_blob_count": 1, "water_radius_range": (2, 3),
        "num_people": 20, "num_animals": 36, "num_trees": 34,
        "tree_resource_range": (50, 90),
        "person_hunger_range": (100, 300), "person_thirst_range": (100, 300), "person_energy_range": (700, 1000),
        "animal_hunger_range": (100, 300), "animal_energy_range": (700, 1000),
        "assign_storage_location": True,
    },
    presentation={"ground_label": "grassland", "water_label": "lake"},
)

register_scenario(SCENARIO)
