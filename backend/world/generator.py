"""Deterministic world generation.

Phase 3: fully generic - every scenario (Wilderness Survival, Desert
Oasis, and any future one) goes through this SAME function. Nothing here
branches on a scenario id; every knob (terrain labels, water size/count,
entity counts, stat ranges) comes from `scenario.world_gen`. This is what
lets a brand-new scenario be added as pure configuration.

Terrain is generated once as static scenario configuration - it never
mutates, so it is not event-sourced. Entities (trees, people, animals) DO
mutate over time (resource depletion, needs, position) so they are created
as genesis accepted events, giving them causal origin like everything else.
"""
from core.rng import DeterministicRNG
from core.constants import MAX_HEALTH, ANIMAL_MAX_HEALTH
from domains.living_agent_contracts import empty_living_agent_state


def generate_world(seed: str, scenario):
    cfg = scenario.world_gen
    width, height = cfg["width"], cfg["height"]
    ground = cfg.get("ground_terrain", "grass")
    rng = DeterministicRNG(seed)
    terrain_rng = rng.stream("world_gen.terrain")
    spawn_rng = rng.stream("world_gen.spawn")

    terrain = [[ground for _ in range(width)] for _ in range(height)]

    water_radius_lo, water_radius_hi = cfg.get("water_radius_range", (2, 3))
    for _ in range(cfg.get("water_blob_count", 1)):
        r = terrain_rng.randint(water_radius_lo, water_radius_hi)
        margin = r + 2
        cx = terrain_rng.randint(margin, max(margin, width - margin - 1))
        cy = terrain_rng.randint(margin, max(margin, height - margin - 1))
        for y in range(height):
            for x in range(width):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2 + terrain_rng.choice([-1, 0, 0, 1]):
                    terrain[y][x] = "water"

    def random_empty_tile():
        for _ in range(1000):
            x = spawn_rng.randint(0, width - 1)
            y = spawn_rng.randint(0, height - 1)
            if terrain[y][x] != "water":
                return x, y
        raise RuntimeError("no empty tile found during world generation")

    genesis_specs = []

    tree_lo, tree_hi = cfg.get("tree_resource_range", (40, 80))
    for _ in range(cfg.get("num_trees", 0)):
        x, y = random_empty_tile()
        amount = spawn_rng.randint(tree_lo, tree_hi)
        genesis_specs.append({
            "type": "tree", "position": {"x": x, "y": y},
            "resource": amount, "max_resource": amount, "alive": True,
        })

    p_hunger = cfg.get("person_hunger_range", (100, 300))
    p_thirst = cfg.get("person_thirst_range", (100, 300))
    p_energy = cfg.get("person_energy_range", (700, 1000))
    p_age = cfg.get("person_age_range", (3000, 30000))  # all genesis people start as adults (no birth mechanic)
    for person_index in range(cfg.get("num_people", 0)):
        x, y = random_empty_tile()
        person_id = f"person-{person_index:03d}"
        genesis_specs.append({
            "type": "person", "position": {"x": x, "y": y},
            "hunger": spawn_rng.randint(*p_hunger), "thirst": spawn_rng.randint(*p_thirst),
            "energy": spawn_rng.randint(*p_energy), "inventory": 0, "food_inventory": 0, "has_shelter": False,
            "current_goal": "IDLE", "alive": True,
            "action": {"type": "idle", "status": "completed", "target_entity_id": None, "target_pos": None,
                       "ticks_spent": 0, "ticks_required": 0, "interruptible": True, "started_tick": 0},
            "plan": {"goal": None, "steps": [], "step_index": 0, "status": "completed"},
            "paused": None,
            "knowledge": {"known_tiles": [], "known_water_tiles": [], "known_trees": {},
                          "known_shelters": {}, "known_carcasses": {}},
            "age_ticks": spawn_rng.randint(*p_age), "life_stage": "adult",
            "health": MAX_HEALTH, "injury": {"injured": False, "severity": 0, "cause": None},
            "death_cause": None, "death_tick": None,
            "living_agent": empty_living_agent_state(person_id, 0, rng),
        })

    a_hunger = cfg.get("animal_hunger_range", (100, 300))
    a_energy = cfg.get("animal_energy_range", (700, 1000))
    for _ in range(cfg.get("num_animals", 0)):
        x, y = random_empty_tile()
        genesis_specs.append({
            "type": "animal", "position": {"x": x, "y": y},
            "hunger": spawn_rng.randint(*a_hunger), "energy": spawn_rng.randint(*a_energy),
            "current_goal": "IDLE", "alive": True,
            "action": {"type": "idle", "status": "completed", "ticks_spent": 0, "flee_ticks_remaining": 0},
            "health": ANIMAL_MAX_HEALTH, "injured": False, "death_cause": None, "death_tick": None,
        })

    return {"width": width, "height": height, "terrain": terrain, "genesis_specs": genesis_specs}
