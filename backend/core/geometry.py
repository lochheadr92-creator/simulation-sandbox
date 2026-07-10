"""Pure, deterministic grid geometry helpers shared by domain engines."""


def manhattan(a: dict, b: dict) -> int:
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])


def is_passable(pos: dict, terrain: list) -> bool:
    h = len(terrain)
    w = len(terrain[0]) if h else 0
    if pos["x"] < 0 or pos["y"] < 0 or pos["x"] >= w or pos["y"] >= h:
        return False
    return terrain[pos["y"]][pos["x"]] != "water"


def step_toward(pos: dict, target: dict, terrain: list) -> dict:
    dx = target["x"] - pos["x"]
    dy = target["y"] - pos["y"]
    candidates = []
    if abs(dx) >= abs(dy) and dx != 0:
        candidates.append({"x": pos["x"] + (1 if dx > 0 else -1), "y": pos["y"]})
    if dy != 0:
        candidates.append({"x": pos["x"], "y": pos["y"] + (1 if dy > 0 else -1)})
    if dx != 0 and abs(dx) < abs(dy):
        candidates.append({"x": pos["x"] + (1 if dx > 0 else -1), "y": pos["y"]})
    for c in candidates:
        if is_passable(c, terrain):
            return c
    return dict(pos)


def is_water_adjacent(pos: dict, terrain: list) -> bool:
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            x, y = pos["x"] + dx, pos["y"] + dy
            if 0 <= y < len(terrain) and 0 <= x < len(terrain[0]):
                if terrain[y][x] == "water":
                    return True
    return False


def find_nearest_water(pos: dict, terrain: list):
    best = None
    best_d = None
    for y, row in enumerate(terrain):
        for x, t in enumerate(row):
            if t == "water":
                d = manhattan(pos, {"x": x, "y": y})
                if best_d is None or d < best_d:
                    best_d = d
                    best = {"x": x, "y": y}
    return best


def find_nearest_entity(entities: dict, pos: dict, etype: str, predicate=None):
    best = None
    best_d = None
    for eid, e in entities.items():
        if e["type"] != etype:
            continue
        if predicate and not predicate(e):
            continue
        d = manhattan(pos, e["position"])
        if best_d is None or d < best_d:
            best_d = d
            best = {**e, "id": eid}
    return best
