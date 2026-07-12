"""Deterministic grid pathfinding and arrival rules.

Pure functions only — domains call these to plan routes; Core never pathfinds.
Selected routes must be stored in canonical entity action state (not diagnostics).

Equal-cost paths resolve identically via BFS first-visit with a fixed neighbour
expansion order. No set/dict iteration order, no random tie-breaks, no global
mutation during path calculation.
"""
from collections import deque

from core.geometry import is_passable, manhattan

# Fixed 4-neighbour expansion order (N, E, S, W). First visit wins in BFS.
NEIGHBOR_DELTAS = (
    (0, -1),  # N
    (1, 0),   # E
    (0, 1),   # S
    (-1, 0),  # W
)

ARRIVAL_EXACT = "exact"
ARRIVAL_ADJACENT = "adjacent"

ROUTE_VERSION = 1


def pos_key(pos):
    return (pos["x"], pos["y"])


def pos_eq(a, b):
    return a is not None and b is not None and a["x"] == b["x"] and a["y"] == b["y"]


def copy_pos(pos):
    if pos is None:
        return None
    return {"x": int(pos["x"]), "y": int(pos["y"])}


def is_goal(pos, target, arrival_mode):
    """Canonical arrival: exact tile for passable destinations; adjacent for
    impassable resources (water). manhattan <= 1 for adjacent covers standing
    on the target tile if it were passable (water never is)."""
    if pos is None or target is None:
        return False
    if arrival_mode == ARRIVAL_ADJACENT:
        return manhattan(pos, target) <= 1
    return pos_eq(pos, target)


def _passable_neighbors(pos, terrain):
    for dx, dy in NEIGHBOR_DELTAS:
        n = {"x": pos["x"] + dx, "y": pos["y"] + dy}
        if is_passable(n, terrain):
            yield n


def find_path(start, target, terrain, arrival_mode=ARRIVAL_EXACT):
    """Deterministic BFS path from start to goal under arrival_mode.

    Returns:
      - [] if already at goal
      - list of positions (exclusive of start, inclusive of goal tile) on success
      - None if unreachable
    """
    if start is None or target is None:
        return None
    start = copy_pos(start)
    target = copy_pos(target)

    if is_goal(start, target, arrival_mode):
        return []

    if arrival_mode == ARRIVAL_EXACT and not is_passable(target, terrain):
        return None

    start_k = pos_key(start)
    parent = {start_k: None}
    queue = deque([start])

    while queue:
        cur = queue.popleft()
        for n in _passable_neighbors(cur, terrain):
            nk = pos_key(n)
            if nk in parent:
                continue
            parent[nk] = pos_key(cur)
            if is_goal(n, target, arrival_mode):
                path = []
                ck = nk
                while ck != start_k:
                    path.append({"x": ck[0], "y": ck[1]})
                    ck = parent[ck]
                    if ck is None:
                        break
                path.reverse()
                return path
            queue.append(n)
    return None


def path_length(start, target, terrain, arrival_mode=ARRIVAL_EXACT):
    """Route step count, or None if unreachable. 0 means already arrived."""
    path = find_path(start, target, terrain, arrival_mode)
    if path is None:
        return None
    return len(path)


def remaining_route_steps(action):
    path = action.get("remaining_path") if action else None
    if not path:
        return 0
    return len(path)
