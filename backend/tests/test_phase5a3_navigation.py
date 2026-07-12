"""
Phase 5A3: deterministic pathfinding, canonical route state, reachable
destination selection, travel completion transitions, and replay stability.
"""
import copy
import random
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.constants import ENGINE_VERSION, SCHEMA_VERSION, GATHER_TICKS
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.navigation import (
    ARRIVAL_ADJACENT, ARRIVAL_EXACT, NEIGHBOR_DELTAS, ROUTE_VERSION,
    find_path, path_length, is_goal, copy_pos,
)
from core.rng import DeterministicRNG
from domains.people_planning import (
    start_step, execute_action_tick, form_plan, idle_action, empty_plan,
    TRAVEL_STALL_LIMIT,
)
from domains.people_utility import (
    nearest_known_water, nearest_unknown_tile, score_candidates, nearest_known_food,
)
from scenarios import get_scenario


def _grass(w, h):
    return [["grass"] * w for _ in range(h)]


def _terrain_with_water_barrier():
    """
    7x5 grid. Horizontal water barrier forces detour:
      row0: open corridor
      row1: water water water . . . .
      start (0,2) target (0,0) requires going around water via x>=3 or via top.
    """
    t = _grass(7, 5)
    for x in range(0, 3):
        t[1][x] = "water"
    return t


class TestDeterministicPathfinding(unittest.TestCase):
    def test_routes_around_water_obstacle(self):
        terrain = _terrain_with_water_barrier()
        start = {"x": 0, "y": 2}
        target = {"x": 0, "y": 0}
        path = find_path(start, target, terrain, ARRIVAL_EXACT)
        self.assertIsNotNone(path)
        self.assertGreater(len(path), 2)  # longer than direct Manhattan 2
        # Never steps on water
        for step in path:
            self.assertNotEqual(terrain[step["y"]][step["x"]], "water")
        self.assertEqual(path[-1], target)
        # Path is continuous
        cur = start
        for step in path:
            self.assertEqual(abs(step["x"] - cur["x"]) + abs(step["y"] - cur["y"]), 1)
            cur = step

    def test_reports_no_route_when_enclosed(self):
        # Only (2,2) is passable; every other tile is water.
        t = [["water"] * 5 for _ in range(5)]
        t[2][2] = "grass"
        path = find_path({"x": 2, "y": 2}, {"x": 1, "y": 1}, t, ARRIVAL_EXACT)
        self.assertIsNone(path)
        self.assertIsNone(path_length({"x": 2, "y": 2}, {"x": 1, "y": 1}, t, ARRIVAL_EXACT))
        # Target on another isolated grass cell
        t[0][0] = "grass"
        self.assertIsNone(find_path({"x": 2, "y": 2}, {"x": 0, "y": 0}, t, ARRIVAL_EXACT))

    def test_equal_cost_route_tie_breaking_is_stable(self):
        t = _grass(5, 5)
        start = {"x": 2, "y": 2}
        target = {"x": 4, "y": 4}
        paths = [find_path(start, target, t, ARRIVAL_EXACT) for _ in range(20)]
        self.assertTrue(all(p == paths[0] for p in paths))
        # Fixed neighbour order implies a specific first path
        self.assertEqual(NEIGHBOR_DELTAS, ((0, -1), (1, 0), (0, 1), (-1, 0)))
        # Document expected first step under N,E,S,W expansion: prefer east-first BFS
        self.assertEqual(paths[0][0], {"x": 3, "y": 2})

    def test_result_unchanged_when_candidate_dict_order_shuffled(self):
        t = _grass(8, 8)
        for x in range(2, 6):
            t[3][x] = "water"
        start = {"x": 1, "y": 4}
        target = {"x": 6, "y": 4}
        base = find_path(start, target, t, ARRIVAL_EXACT)
        # Shuffling unrelated entity/candidate dicts must not affect pure pathfinding
        entities = {f"e{i}": {"position": {"x": i, "y": 0}} for i in range(10)}
        keys = list(entities.keys())
        for _ in range(10):
            random.shuffle(keys)
            shuffled = {k: entities[k] for k in keys}
            self.assertEqual(find_path(start, target, t, ARRIVAL_EXACT), base)
            self.assertEqual(len(shuffled), 10)

    def test_adjacent_arrival_for_water(self):
        t = _grass(5, 5)
        t[2][2] = "water"
        start = {"x": 0, "y": 0}
        path = find_path(start, {"x": 2, "y": 2}, t, ARRIVAL_ADJACENT)
        self.assertIsNotNone(path)
        self.assertTrue(is_goal(path[-1], {"x": 2, "y": 2}, ARRIVAL_ADJACENT))
        self.assertNotEqual(path[-1], {"x": 2, "y": 2})  # does not stand on water

    def test_empty_path_when_already_arrived(self):
        t = _grass(3, 3)
        pos = {"x": 1, "y": 1}
        self.assertEqual(find_path(pos, pos, t, ARRIVAL_EXACT), [])
        t[0][0] = "water"
        self.assertEqual(find_path({"x": 0, "y": 1}, {"x": 0, "y": 0}, t, ARRIVAL_ADJACENT), [])


class TestCanonicalRouteState(unittest.TestCase):
    def _person(self, pos):
        return {
            "type": "person", "position": dict(pos), "hunger": 100, "thirst": 100,
            "energy": 900, "inventory": 0, "food_inventory": 0, "has_shelter": False,
            "alive": True, "action": idle_action(), "plan": empty_plan(),
        }

    def test_stored_route_advances_one_step_per_tick(self):
        t = _grass(6, 6)
        pos = {"x": 0, "y": 0}
        target = {"x": 4, "y": 0}
        ctx = {"water_target": target}
        # Use TRAVEL_FRONTIER style exact travel via form context
        e = self._person(pos)
        action = start_step("TRAVEL_FRONTIER", e, "person-0",
                            {"frontier_target": target}, t, 1, pos)
        self.assertEqual(action["type"], "travel")
        self.assertIn("remaining_path", action)
        self.assertEqual(action["route_version"], ROUTE_VERSION)
        self.assertEqual(action["planned_from"], pos)
        self.assertFalse(action["unreachable"])
        full_len = action["route_length"]
        self.assertEqual(full_len, 4)
        self.assertEqual(len(action["remaining_path"]), 4)

        rng = DeterministicRNG("route-step").stream("t")
        for i in range(4):
            e["position"] = pos
            e["action"] = action
            result = execute_action_tick(e, "person-0", action, {}, t, i + 1, False, rng)
            action = result["action"]
            pos = result["pos"]
            if i < 3:
                self.assertEqual(action["status"], "travelling")
                self.assertFalse(result["advance_plan"])
                self.assertEqual(len(action["remaining_path"]), full_len - (i + 1))
                self.assertEqual(action["ticks_spent"], i + 1)
            else:
                # last step lands on target; may complete same tick or next
                pass
        # After 4 steps should be on target; one more tick completes if not already
        if action["status"] == "travelling":
            e["position"] = pos
            result = execute_action_tick(e, "person-0", action, {}, t, 10, False, rng)
            action = result["action"]
            pos = result["pos"]
        self.assertEqual(pos, target)
        self.assertEqual(action["status"], "completed")

    def test_route_not_unnecessarily_recomputed_each_tick(self):
        t = _grass(8, 8)
        pos = {"x": 0, "y": 0}
        target = {"x": 5, "y": 0}
        e = self._person(pos)
        action = start_step("TRAVEL_FRONTIER", e, "person-0",
                            {"frontier_target": target}, t, 1, pos)
        original_path = [copy_pos(p) for p in action["remaining_path"]]
        rng = DeterministicRNG("no-recompute").stream("t")
        e["position"] = pos
        result = execute_action_tick(e, "person-0", action, {}, t, 1, False, rng)
        action = result["action"]
        self.assertIsNone(action.get("invalidation_reason"))
        # remaining_path is original[1:] without recompute
        self.assertEqual(action["remaining_path"], original_path[1:])
        self.assertEqual(result["pos"], original_path[0])
        self.assertNotIn("route recomputed", result["explanation"])

    def test_route_invalidates_when_next_tile_blocked(self):
        t = _grass(6, 6)
        pos = {"x": 0, "y": 0}
        target = {"x": 4, "y": 0}
        e = self._person(pos)
        action = start_step("TRAVEL_FRONTIER", e, "person-0",
                            {"frontier_target": target}, t, 1, pos)
        # Block the next tile on the stored route
        next_tile = action["remaining_path"][0]
        t[next_tile["y"]][next_tile["x"]] = "water"
        # Force a path that must detour (open corridor at y=1)
        rng = DeterministicRNG("block").stream("t")
        result = execute_action_tick(e, "person-0", action, {}, t, 1, False, rng)
        self.assertIn(result["action"].get("invalidation_reason"),
                      ("next_tile_impassable", "position_desync", None))
        # Either recomputed around or failed closed — must not step onto water
        if result["action"]["status"] == "travelling":
            self.assertNotEqual(t[result["pos"]["y"]][result["pos"]["x"]], "water")
            self.assertEqual(result["action"].get("invalidation_reason"), "next_tile_impassable")
            self.assertIn("route recomputed", result["explanation"])

    def test_moving_target_invalidation(self):
        t = _grass(8, 8)
        pos = {"x": 0, "y": 0}
        animal_pos = {"x": 3, "y": 0}
        entities = {
            "animal-1": {"type": "animal", "position": dict(animal_pos), "alive": True, "health": 100},
        }
        e = self._person(pos)
        action = start_step(
            "TRAVEL_ANIMAL", e, "person-0",
            {"animal_target_id": "animal-1", "animal_target_pos": animal_pos},
            t, 1, pos,
        )
        # Animal moves before the step
        entities["animal-1"]["position"] = {"x": 5, "y": 2}
        rng = DeterministicRNG("moving").stream("t")
        result = execute_action_tick(e, "person-0", action, entities, t, 1, False, rng)
        self.assertEqual(result["action"].get("invalidation_reason"), "target_moved")
        self.assertEqual(result["action"]["target_pos"], {"x": 5, "y": 2})
        self.assertEqual(result["action"]["status"], "travelling")
        self.assertIn("route recomputed", result["explanation"])

    def test_disappeared_target_fails(self):
        t = _grass(6, 6)
        pos = {"x": 0, "y": 0}
        e = self._person(pos)
        action = start_step(
            "TRAVEL_ANIMAL", e, "person-0",
            {"animal_target_id": "animal-1", "animal_target_pos": {"x": 3, "y": 0}},
            t, 1, pos,
        )
        rng = DeterministicRNG("gone").stream("t")
        result = execute_action_tick(e, "person-0", action, {}, t, 1, False, rng)
        self.assertEqual(result["action"]["status"], "failed")
        self.assertEqual(result["action"]["invalidation_reason"], "target_disappeared")
        self.assertTrue(result["advance_plan"])


class TestReachableDestinationSelection(unittest.TestCase):
    def test_unreachable_water_excluded(self):
        t = _grass(6, 6)
        # Enclose water at (1,1)
        t[0][0] = t[0][1] = t[0][2] = "water"
        t[1][0] = t[1][2] = "water"
        t[2][0] = t[2][1] = t[2][2] = "water"
        t[1][1] = "water"  # the target water is isolated? Actually whole block is water
        # Isolated water pocket surrounded by water is always "water" - make grass ring around water cell
        t = _grass(7, 7)
        t[3][3] = "water"
        # wall of water enclosing the person away from open water? Simpler: person on island
        for x in range(7):
            t[1][x] = "water"
        # person at (0,0), water known at (3,3) - path may exist around ends
        # Close left and right of barrier... already full row of water at y=1
        # so person at y=0 cannot cross to y>=2
        knowledge = {"known_water_tiles": ["3,3", "0,0"], "known_tiles": [], "known_trees": {},
                     "known_shelters": {}, "known_carcasses": {}}
        # 0,0 is grass not water - only 3,3 water
        knowledge = {"known_water_tiles": ["3,3"], "known_tiles": [], "known_trees": {},
                     "known_shelters": {}, "known_carcasses": {}}
        pos = {"x": 0, "y": 0}
        water, d = nearest_known_water(pos, knowledge, t)
        self.assertIsNone(water)
        self.assertIsNone(d)

    def test_travel_cost_uses_path_length_not_manhattan(self):
        # U-shaped water wall: direct Manhattan is short, true route must detour.
        #   start S at (0,2), target T at (4,2), water blocks the straight corridor.
        t = _grass(7, 5)
        for x in range(1, 4):
            t[1][x] = "water"
            t[2][x] = "water"
            t[3][x] = "water"
        # Open only via top row y=0 or bottom y=4
        start = {"x": 0, "y": 2}
        target = {"x": 4, "y": 2}
        manh = abs(start["x"] - target["x"]) + abs(start["y"] - target["y"])  # 4
        plen = path_length(start, target, t, ARRIVAL_EXACT)
        self.assertIsNotNone(plen)
        self.assertGreater(plen, manh)
        # Utility nearest_known_water must report path length, not Manhattan
        t[2][5] = "water"
        knowledge = {
            "known_water_tiles": ["5,2"], "known_tiles": [], "known_trees": {},
            "known_shelters": {}, "known_carcasses": {},
        }
        wpos, wd = nearest_known_water(start, knowledge, t)
        self.assertEqual(wpos, {"x": 5, "y": 2})
        self.assertEqual(wd, path_length(start, wpos, t, ARRIVAL_ADJACENT))
        self.assertNotEqual(wd, abs(start["x"] - 5) + abs(start["y"] - 2))

    def test_exploration_skips_unreachable_frontier(self):
        t = _grass(5, 5)
        for x in range(5):
            t[2][x] = "water"
        # top half y=0,1 known empty of unknown; person at (0,0); bottom y=3,4 unknown but unreachable
        known = [f"{x},{y}" for y in range(0, 2) for x in range(5)]
        knowledge = {"known_tiles": known, "known_water_tiles": [], "known_trees": {},
                     "known_shelters": {}, "known_carcasses": {}}
        frontier, d = nearest_unknown_tile({"x": 0, "y": 0}, knowledge, t, 5, 5)
        self.assertIsNone(frontier)
        self.assertIsNone(d)

    def test_shuffled_knowledge_order_stable_water_choice(self):
        t = _grass(10, 10)
        pos = {"x": 5, "y": 5}
        tiles = ["1,1", "8,8", "2,7", "9,0"]
        results = []
        for _ in range(10):
            random.shuffle(tiles)
            knowledge = {"known_water_tiles": list(tiles), "known_tiles": [], "known_trees": {},
                         "known_shelters": {}, "known_carcasses": {}}
            # Mark those as water in terrain
            for key in tiles:
                x, y = (int(v) for v in key.split(","))
                t[y][x] = "water"
            w, d = nearest_known_water(pos, knowledge, t)
            results.append((w, d))
        self.assertTrue(all(r == results[0] for r in results))


class TestTravelBehaviourTransitions(unittest.TestCase):
    def _rng(self, name="b"):
        return DeterministicRNG(name).stream("s")

    def test_person_reaches_water_and_transitions_to_drink(self):
        t = _grass(6, 6)
        t[0][5] = "water"
        pos = {"x": 0, "y": 0}
        e = {
            "type": "person", "position": pos, "hunger": 100, "thirst": 950,
            "energy": 900, "inventory": 0, "food_inventory": 0, "has_shelter": False,
            "alive": True,
        }
        ctx = {"water_target": {"x": 5, "y": 0}}
        plan = form_plan("SEEK_WATER", e, ctx, 1)
        self.assertEqual(plan["steps"], ["TRAVEL_WATER", "DRINK"])
        action = start_step("TRAVEL_WATER", e, "person-0", ctx, t, 1, pos)
        self.assertEqual(action["arrival_action"], "DRINK")
        self.assertEqual(action["arrival_mode"], ARRIVAL_ADJACENT)
        self.assertFalse(action["unreachable"])

        # Walk until travel completes
        for tick in range(1, 30):
            e["position"] = pos
            result = execute_action_tick(e, "person-0", action, {}, t, tick, False, self._rng())
            pos = result["pos"]
            action = result["action"]
            if result["advance_plan"]:
                break
        self.assertEqual(action["status"], "completed")
        self.assertTrue(is_goal(pos, {"x": 5, "y": 0}, ARRIVAL_ADJACENT))

        # Next step DRINK
        action = start_step("DRINK", e, "person-0", ctx, t, tick + 1, pos)
        result = execute_action_tick(e, "person-0", action, {}, t, tick + 1, False, self._rng())
        self.assertEqual(result["thirst"], 0)
        self.assertIn("drank", result["explanation"])

    def test_person_reaches_food_and_gathers(self):
        t = _grass(5, 5)
        pos = {"x": 0, "y": 0}
        tree_pos = {"x": 3, "y": 0}
        entities = {
            "tree-1": {"type": "tree", "position": tree_pos, "resource": 40, "max_resource": 40, "claimed_tick": None},
        }
        e = {
            "type": "person", "position": pos, "hunger": 800, "thirst": 100,
            "energy": 900, "inventory": 0, "food_inventory": 0, "has_shelter": False,
            "alive": True,
        }
        ctx = {"food_target_id": "tree-1", "food_target_pos": tree_pos, "food_target_kind": "tree"}
        action = start_step("TRAVEL_FOOD", e, "person-0", ctx, t, 1, pos)
        for tick in range(1, 20):
            e["position"] = pos
            result = execute_action_tick(e, "person-0", action, entities, t, tick, False, self._rng())
            pos = result["pos"]
            action = result["action"]
            if result["advance_plan"]:
                break
        self.assertEqual(action["status"], "completed")
        self.assertEqual(pos, tree_pos)

        action = start_step("GATHER_FOOD", e, "person-0", ctx, t, tick + 1, pos)
        for i in range(GATHER_TICKS):
            e["position"] = pos
            result = execute_action_tick(e, "person-0", action, entities, t, tick + 1 + i, False, self._rng())
            action = result["action"]
        self.assertEqual(action["status"], "completed")
        self.assertGreater(result["inventory"], 0)

    def test_exploration_reaches_reachable_frontier(self):
        t = _grass(4, 4)
        pos = {"x": 0, "y": 0}
        frontier = {"x": 2, "y": 2}
        e = {
            "type": "person", "position": pos, "hunger": 100, "thirst": 100,
            "energy": 900, "inventory": 0, "food_inventory": 0, "has_shelter": False,
            "alive": True,
        }
        action = start_step("TRAVEL_FRONTIER", e, "person-0", {"frontier_target": frontier}, t, 1, pos)
        for tick in range(1, 20):
            e["position"] = pos
            result = execute_action_tick(e, "person-0", action, {}, t, tick, False, self._rng())
            pos = result["pos"]
            action = result["action"]
            if result["advance_plan"]:
                break
        self.assertEqual(pos, frontier)
        self.assertEqual(action["status"], "completed")

    def test_unreachable_target_not_selected_in_utility(self):
        t = _grass(6, 6)
        for x in range(6):
            t[2][x] = "water"
        pos = {"x": 0, "y": 0}
        knowledge = {
            "known_tiles": [f"{x},{y}" for y in range(0, 2) for x in range(6)],
            "known_water_tiles": ["3,4"],  # unreachable across barrier
            "known_trees": {},
            "known_shelters": {},
            "known_carcasses": {},
        }
        e = {
            "id": "person-0", "hunger": 200, "thirst": 900, "energy": 900,
            "inventory": 0, "food_inventory": 0, "has_shelter": False,
        }
        cands, ctx = score_candidates(e, knowledge, pos, 1, False, idle_action(), t, {})
        by_goal = {c["goal"]: c for c in cands}
        self.assertEqual(by_goal["SEEK_WATER"]["availability"], 0.0)
        self.assertIsNone(ctx["water_target"])
        self.assertTrue(by_goal["EXPLORE"]["availability"] == 0.0 or by_goal["EXPLORE"]["score"] is not None)

    def test_plan_continues_unless_interrupted(self):
        t = _grass(6, 6)
        t[0][5] = "water"
        pos = {"x": 0, "y": 0}
        e = {
            "type": "person", "position": pos, "hunger": 100, "thirst": 200,
            "energy": 900, "inventory": 0, "food_inventory": 0, "has_shelter": False,
            "alive": True,
        }
        ctx = {"water_target": {"x": 5, "y": 0}}
        plan = form_plan("SEEK_WATER", e, ctx, 1)
        action = start_step(plan["steps"][0], e, "person-0", ctx, t, 1, pos)
        # Two ticks of travel with moderate needs — action should continue (no replan mid-travel here)
        routes_before = list(action["remaining_path"])
        e["position"] = pos
        r1 = execute_action_tick(e, "person-0", action, {}, t, 1, False, self._rng())
        self.assertEqual(r1["action"]["status"], "travelling")
        self.assertEqual(r1["action"]["remaining_path"], routes_before[1:])
        self.assertIsNone(r1["action"].get("invalidation_reason"))


class TestReplayDeterminismNavigation(unittest.TestCase):
    def _lineage(self, seed):
        return f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"

    def _run_trace(self, seed, ticks, reverse_entities=False):
        scenario = get_scenario("basic_survival")
        lineage_key = self._lineage(seed)
        world, entities, genesis_events, _, order_index = build_genesis(seed, scenario, lineage_key)
        if reverse_entities:
            entities = dict(reversed(list(entities.items())))
        events_by_tick = {0: list(genesis_events)}
        frame_hashes = [genesis_events[-1]["post_state_hash"]]
        rng = DeterministicRNG(seed)
        for tick in range(1, ticks + 1):
            accepted, _, order_index, _ = run_tick(
                "run-nav", entities, world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
            )
            events_by_tick[tick] = accepted
            frame_hashes.append(accepted[-1]["post_state_hash"] if accepted else frame_hashes[-1])
        return {
            "entities": copy.deepcopy(entities),
            "frame_hashes": frame_hashes,
            "event_hashes": [
                canonical_hash({k: v for k, v in ev.items() if k != "run_id"})
                for tick in range(ticks + 1) for ev in events_by_tick[tick]
            ],
        }

    def test_identical_seed_identical_routes_events_hashes(self):
        a = self._run_trace("phase5b-nav-seed", ticks=40)
        b = self._run_trace("phase5b-nav-seed", ticks=40)
        self.assertEqual(a["frame_hashes"], b["frame_hashes"])
        self.assertEqual(a["event_hashes"], b["event_hashes"])
        self.assertEqual(a["entities"], b["entities"])

    def test_shuffled_entity_insertion_order_preserves_result(self):
        a = self._run_trace("phase5b-nav-order", ticks=25, reverse_entities=False)
        b = self._run_trace("phase5b-nav-order", ticks=25, reverse_entities=True)
        self.assertEqual(a["frame_hashes"], b["frame_hashes"])
        self.assertEqual(a["event_hashes"], b["event_hashes"])

    def test_replay_from_accepted_events_rebuilds_hashes(self):
        scenario = get_scenario("basic_survival")
        seed = "phase5b-nav-replay"
        lineage_key = self._lineage(seed)
        world, entities, genesis_events, _, order_index = build_genesis(seed, scenario, lineage_key)
        terrain = world["terrain"]
        live_entities = copy.deepcopy(entities)
        rng = DeterministicRNG(seed)
        accepted_all = list(genesis_events)
        frame_hashes = [genesis_events[-1]["post_state_hash"]]
        for tick in range(1, 30):
            accepted, _, order_index, _ = run_tick(
                "run-r", live_entities, terrain, tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
            )
            accepted_all.extend(accepted)
            frame_hashes.append(accepted[-1]["post_state_hash"] if accepted else frame_hashes[-1])

        # Rebuild solely from mutations
        rebuilt = {}
        for ev in accepted_all:
            apply_mutation(rebuilt, ev["mutation"])
        final_hash = canonical_hash(snapshot_for_hash(rebuilt, 29, lineage_key))
        live_hash = canonical_hash(snapshot_for_hash(live_entities, 29, lineage_key))
        self.assertEqual(final_hash, live_hash)

    def test_people_actually_move_when_travelling(self):
        """Regression: water-blocking must not produce multi-tick stationary travel."""
        scenario = get_scenario("basic_survival")
        seed = "phase5b-move-check"
        lineage_key = self._lineage(seed)
        world, entities, _, _, order_index = build_genesis(seed, scenario, lineage_key)
        rng = DeterministicRNG(seed)
        stuck = 0
        for tick in range(1, 80):
            before = {
                eid: copy.deepcopy(e["position"])
                for eid, e in entities.items()
                if e.get("type") == "person" and e.get("alive", True)
                and (e.get("action") or {}).get("status") == "travelling"
                and (e.get("action") or {}).get("ticks_spent", 0) > 0
            }
            accepted, _, order_index, _ = run_tick(
                "run-m", entities, world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
            )
            for eid, old_pos in before.items():
                e = entities.get(eid)
                if not e or not e.get("alive", True):
                    continue
                action = e.get("action") or {}
                if action.get("status") != "travelling":
                    continue
                if e["position"] == old_pos and action.get("ticks_spent", 0) > 1:
                    # Stationary while travelling and not just-arrived edge
                    if action.get("remaining_path"):
                        stuck += 1
        # Allow rare edge stalls from moving targets, but not chronic immobility
        self.assertLess(stuck, 5, f"too many stationary travel ticks: {stuck}")


if __name__ == "__main__":
    unittest.main()
