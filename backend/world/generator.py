"""Deterministic world generation.

Terrain (grass/water) is generated once as static scenario configuration -
it never mutates in Phase 1, so it is not event-sourced. Entities (trees,
people, animals) DO mutate over time (resource depletion, needs, position)
so they are created as genesis accepted events, giving them causal origin
like everything else in the world.
"""
from core.rng import DeterministicRNG

SCENARIOS = {
    "basic_survival": {
        "width": 20, "height": 20, "num_people": 6, "num_animals": 6, "num_trees": 16,
        "description": "Open terrain, a lake, scattered trees, autonomous people and animals.",
    }
}


def generate_world(seed: str, scenario_id: str = "basic_survival"):
    cfg = SCENARIOS[scenario_id]
    width, height = cfg["width"], cfg["height"]
    rng = DeterministicRNG(seed)
    terrain_rng = rng.stream("world_gen.terrain")
    spawn_rng = rng.stream("world_gen.spawn")

    terrain = [["grass" for _ in range(width)] for _ in range(height)]

    lake_cx = terrain_rng.randint(4, width - 5)
    lake_cy = terrain_rng.randint(4, height - 5)
    lake_r = terrain_rng.randint(2, 3)
    for y in range(height):
        for x in range(width):
            if (x - lake_cx) ** 2 + (y - lake_cy) ** 2 <= lake_r ** 2 + terrain_rng.choice([-1, 0, 0, 1]):
                terrain[y][x] = "water"

    def random_empty_tile():
        for _ in range(1000):
            x = spawn_rng.randint(0, width - 1)
            y = spawn_rng.randint(0, height - 1)
            if terrain[y][x] != "water":
                return x, y
        raise RuntimeError("no empty tile found during world generation")

    genesis_specs = []

    for _ in range(cfg["num_trees"]):
        x, y = random_empty_tile()
        amount = spawn_rng.randint(40, 80)
        genesis_specs.append({
            "type": "tree", "position": {"x": x, "y": y},
            "resource": amount, "max_resource": amount, "alive": True,
        })

    for _ in range(cfg["num_people"]):
        x, y = random_empty_tile()
        genesis_specs.append({
            "type": "person", "position": {"x": x, "y": y},
            "hunger": spawn_rng.randint(100, 300), "thirst": spawn_rng.randint(100, 300),
            "energy": spawn_rng.randint(700, 1000), "inventory": 0, "has_shelter": False,
            "current_goal": "IDLE", "alive": True,
            "action": {"type": "idle", "status": "completed", "target_entity_id": None, "target_pos": None,
                       "ticks_spent": 0, "ticks_required": 0, "interruptible": True, "started_tick": 0},
            "plan": {"goal": None, "steps": [], "step_index": 0, "status": "completed"},
            "paused": None,
            "knowledge": {"known_tiles": [], "known_water_tiles": [], "known_trees": {}, "known_shelters": {}},
        })

    for _ in range(cfg["num_animals"]):
        x, y = random_empty_tile()
        genesis_specs.append({
            "type": "animal", "position": {"x": x, "y": y},
            "hunger": spawn_rng.randint(100, 300), "energy": spawn_rng.randint(700, 1000),
            "current_goal": "IDLE", "alive": True,
            "action": {"type": "idle", "status": "completed", "ticks_spent": 0, "flee_ticks_remaining": 0},
        })

    return {"width": width, "height": height, "terrain": terrain, "genesis_specs": genesis_specs}
