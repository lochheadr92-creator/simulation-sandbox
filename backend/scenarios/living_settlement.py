"""Capability Stage 6 integrated living-agent camp scenario."""
from scenarios.base import Scenario
from scenarios.registry import register_scenario


FAMILY_A = {
    "person-001": {"familiarity": 800, "trust": 500, "affection": 700, "kinship": "sibling"},
}
FAMILY_B = {
    "person-003": {"familiarity": 750, "trust": 450, "affection": 650, "kinship": "sibling"},
}


SCENARIO = Scenario(
    id="living_settlement",
    name="Living Agents Camp",
    description=(
        "Eight people in a compact camp face food, water, damaged shelter, changing weather, "
        "an external animal threat, incomplete knowledge, social obligations, and contested stores."
    ),
    enabled_domains=["weather", "ecology", "lifecycle", "living_settlement", "animal"],
    world_gen={
        "width": 12, "height": 12, "ground_terrain": "grass",
        "water_blob_count": 0,
        "num_people": 8, "num_animals": 0, "num_trees": 5,
        "tree_resource_range": (20, 35),
        "person_hunger_range": (250, 450), "person_thirst_range": (250, 450),
        "person_energy_range": (650, 900),
        "person_positions": [
            {"x": 4, "y": 4}, {"x": 5, "y": 4}, {"x": 4, "y": 5}, {"x": 5, "y": 5},
            {"x": 6, "y": 4}, {"x": 6, "y": 5}, {"x": 4, "y": 6}, {"x": 5, "y": 6},
        ],
        "person_profiles": [
            {"stage6_role": "needy", "hunger": 880, "thirst": 620, "energy": 900,
             "relationships": FAMILY_A},
            {"stage6_role": "caretaker", "carried_resources": {"food": 3, "wood": 0},
             "relationships": {"person-000": {"familiarity": 800, "trust": 500, "affection": 700, "kinship": "sibling"}}},
            {"stage6_role": "builder", "thirst": 590,
             "carried_resources": {"food": 0, "wood": 10}, "relationships": FAMILY_B},
            {"stage6_role": "steward", "carried_resources": {"food": 1, "wood": 1},
             "relationships": {"person-002": {"familiarity": 750, "trust": 450, "affection": 650, "kinship": "sibling"}}},
            {"stage6_role": "hoarder", "carried_resources": {"food": 1, "wood": 0}},
            {"stage6_role": "rumourmonger", "carried_resources": {"food": 1, "wood": 0}},
            {"stage6_role": "skeptic", "hunger": 850, "energy": 900,
             "carried_resources": {"food": 0, "wood": 1}},
            {"stage6_role": "scout", "health": 350, "energy": 420,
             "injury": {"injured": True, "severity": 650, "cause": "animal_threat"}},
        ],
        "extra_genesis_specs": [
            {"id": "weather-000", "type": "weather", "position": {"x": 5, "y": 5},
             "condition": "clear", "exposure": 0, "visibility_penalty": 0,
             "temperature": 650, "rain": 0, "cycle_index": 0,
             "last_transition_tick": 0, "forecast": "rain"},
            {"id": "storage-camp", "type": "storage", "position": {"x": 5, "y": 5},
             "contents": {"food": 1, "wood": 12}, "capacity": 40,
             "owner_id": "person-003", "access": "shared", "open": True, "condition": 900},
            {"id": "storage-private", "type": "storage", "position": {"x": 7, "y": 5},
             "contents": {"food": 4, "wood": 2}, "capacity": 12,
             "owner_id": "person-004", "access": "private", "open": False, "condition": 900},
            {"id": "tool-axe", "type": "tool", "position": {"x": 5, "y": 5},
             "tool_kind": "axe", "durability": 18, "effectiveness": 700,
             "owner_id": "person-003", "access": "shared", "carried_by": None},
            {"id": "tool-hammer", "type": "tool", "position": {"x": 5, "y": 5},
             "tool_kind": "hammer", "durability": 16, "effectiveness": 650,
             "owner_id": "person-002", "access": "shared", "carried_by": None},
            {"id": "shelter-family", "type": "shelter", "position": {"x": 4, "y": 4},
             "owner_id": "person-000", "access": "shared", "condition": 850,
             "max_condition": 1000, "alive": True},
            {"id": "shelter-damaged", "type": "shelter", "position": {"x": 6, "y": 5},
             "owner_id": "person-002", "access": "shared", "condition": 380,
             "max_condition": 1000, "alive": True},
            {"id": "water-camp", "type": "water_source", "position": {"x": 3, "y": 4},
             "resource_kind": "water", "quantity": 999, "quality": 800,
             "owner_id": None, "access": "public"},
            {"id": "food-patch", "type": "resource", "position": {"x": 3, "y": 5},
             "resource_kind": "food", "quantity": 12, "quality": 600,
             "owner_id": None, "access": "public"},
            {"id": "wood-pile", "type": "resource", "position": {"x": 7, "y": 4},
             "resource_kind": "wood", "quantity": 18, "quality": 650,
             "owner_id": "person-003", "access": "shared"},
            {"id": "animal-threat", "type": "animal", "position": {"x": 7, "y": 6},
             "hunger": 700, "energy": 800, "current_goal": "HUNT", "alive": True,
             "action": {"type": "wander", "status": "performing", "flee_ticks_remaining": 0},
             "health": 100, "injured": False, "death_cause": None, "death_tick": None},
            {"id": "signal-false-rumour", "type": "signal", "position": {"x": 5, "y": 5},
             "schema_version": "physical-signal-v1", "signal_kind": "speech", "strength": 700,
             "source_entity_id": "person-005", "source_action_id": "genesis-rumour",
             "source_event_id": None,
             "recipient_ids": ["person-000", "person-002", "person-006"],
             "witness_ids": ["person-001", "person-003"],
             "message": {"action_type": "share_information", "actor_id": "person-005",
                         "target_id": "person-000", "claim": {"subject_id": "storage-private",
                         "fact_type": "storage", "properties": {"open": True, "access": "public",
                         "visible_contents": {"food": 9}}, "confidence": 650}},
             "truth_status": "deceptive", "propagation_depth": 0,
             "created_tick": 0, "expires_tick": 4},
        ],
    },
    presentation={"ground_label": "camp clearing", "water_label": "spring", "capability_stage": 6},
)

register_scenario(SCENARIO)
