"""PeopleDomain: needs -> goals -> actions, with genuine candidate scoring.

Layers considered per decision (per doctrine's NPC framing): current
temporary condition (hunger/thirst/energy), acquired state (inventory,
has_shelter), and immediate situation (nearby tree/water, day/night).
Every candidate goal and its score is recorded in diagnostics so causal
inspection shows REAL evidence, never a fabricated explanation.
"""
from domains.base import DomainEngine, DomainOutput
from core.constants import SHELTER_COST
from core.geometry import manhattan, step_toward, is_water_adjacent, find_nearest_water, find_nearest_entity, is_passable

SEEK_THRESHOLD = 650
REST_THRESHOLD_DAY = 300
REST_THRESHOLD_NIGHT = 600


class PeopleDomain(DomainEngine):
    engine_id = "people"
    engine_version = "1.0.0"
    engine_priority = 10
    phase = "agent"

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        night = frame.night if hasattr(frame, "night") else False

        for eid in frame.due_entity_ids:
            e = frame.entities.get(eid)
            if not e or e["type"] != "person" or not e.get("alive", True):
                continue

            if e["energy"] <= 0 and (e["hunger"] >= 1000 or e["thirst"] >= 1000):
                proposal = self._death_proposal(e, eid, frame.simulation_time)
                proposals.append(proposal)
                diagnostics[eid] = {"candidates": [], "selected_goal": "DEATH", "explanation": proposal["explanation"]}
                continue

            rng = frame.rng.stream(f"people.{eid}.decision.{frame.simulation_time}")
            pos = e["position"]
            nearest_tree = find_nearest_entity(frame.entities, pos, "tree", lambda t: t["resource"] > 0)
            nearest_water = find_nearest_water(pos, frame.terrain)
            can_gather_here = nearest_tree is not None and manhattan(pos, nearest_tree["position"]) <= 1
            can_drink_here = is_water_adjacent(pos, frame.terrain)
            rest_threshold = REST_THRESHOLD_NIGHT if night else REST_THRESHOLD_DAY
            energy_deficit = max(0, rest_threshold - e["energy"])

            candidates = [
                {"goal": "SEEK_WATER", "score": e["thirst"] if e["thirst"] >= SEEK_THRESHOLD else e["thirst"] * 0.3},
                {"goal": "SEEK_FOOD", "score": e["hunger"] if (e["hunger"] >= SEEK_THRESHOLD and (e["inventory"] > 0 or nearest_tree)) else e["hunger"] * 0.3},
                {"goal": "REST", "score": energy_deficit * 1.5},
                {"goal": "BUILD_SHELTER", "score": 260 if (e["inventory"] >= SHELTER_COST and not e.get("has_shelter")) else 0},
                {"goal": "GATHER_SURPLUS", "score": 130 if (can_gather_here and e["inventory"] < 20) else 0},
                {"goal": "WANDER", "score": 45},
            ]
            best = max(candidates, key=lambda c: c["score"])
            rejected_goals = [c for c in candidates if c["goal"] != best["goal"]]

            proposal = self._build_proposal(
                e, eid, best["goal"], nearest_tree, nearest_water, frame.terrain,
                frame.simulation_time, night, can_gather_here, can_drink_here, rng,
            )
            proposals.append(proposal)
            diagnostics[eid] = {
                "candidates": candidates, "selected_goal": best["goal"],
                "rejected_goals": rejected_goals, "night": night, "explanation": proposal["explanation"],
            }

        return DomainOutput(proposals=proposals, diagnostics=diagnostics)

    def _death_proposal(self, e, eid, tick):
        return {
            "proposal_family": "people_action",
            "proposal_type": "death",
            "proposer_engine_id": self.engine_id,
            "proposer_engine_version": self.engine_version,
            "entity_id": eid,
            "causal_parent_event_ids": [e["last_event_id"]] if e.get("last_event_id") else [],
            "is_exogenous": not e.get("last_event_id"),
            "requested_time": tick,
            "phase": "agent",
            "engine_priority": self.engine_priority,
            "touched_scope": [eid],
            "preconditions": [{"entity_id": eid, "field": "alive", "op": "eq", "value": True}],
            "mutation": {"entity_updates": {eid: {"alive": False, "current_goal": "DEAD", "current_action": "death"}},
                         "new_entities": {}},
            "explanation": f"critical: energy=0 with hunger={e['hunger']} thirst={e['thirst']} -> death",
        }

    def _build_proposal(self, e, eid, goal, nearest_tree, nearest_water, terrain, tick, night,
                         can_gather_here, can_drink_here, rng):
        hunger = min(1000, e["hunger"] + 8)
        thirst = min(1000, e["thirst"] + 10)
        energy = max(0, e["energy"] - (7 if night else 5))
        inventory = e["inventory"]
        pos = dict(e["position"])
        entity_updates = {}
        new_entities = {}
        touched_scope = [eid]
        preconditions = []
        action_type = "wander"
        has_shelter_after = e.get("has_shelter", False)
        explanation = ""

        if goal == "SEEK_WATER":
            if can_drink_here:
                action_type = "drink"
                thirst = 0
                explanation = f"thirst={e['thirst']} >= threshold; adjacent to water -> drink"
            elif nearest_water:
                action_type = "move"
                pos = step_toward(pos, nearest_water, terrain)
                explanation = f"thirst={e['thirst']} high; moving toward water at {nearest_water}"
            else:
                explanation = "thirsty but no known water source; wandering"

        elif goal == "SEEK_FOOD":
            if inventory > 0:
                action_type = "eat"
                inventory -= 1
                hunger = max(0, hunger - 400)
                explanation = f"hunger={e['hunger']} high; ate from inventory"
            elif can_gather_here:
                action_type = "gather"
                amount = min(10, nearest_tree["resource"])
                tree_id = nearest_tree["id"]
                touched_scope.append(tree_id)
                preconditions.append({"entity_id": tree_id, "field": "claimed_tick", "op": "neq", "value": tick})
                preconditions.append({"entity_id": tree_id, "field": "resource", "op": "gte", "value": amount})
                entity_updates[tree_id] = {"resource": nearest_tree["resource"] - amount, "claimed_tick": tick}
                inventory += amount
                explanation = f"hunger={e['hunger']} high, no food stored; gathered {amount} from {tree_id}"
            elif nearest_tree:
                action_type = "move"
                pos = step_toward(pos, nearest_tree["position"], terrain)
                explanation = f"hunger={e['hunger']} high; moving toward tree at {nearest_tree['position']}"
            else:
                explanation = "hungry but no known food source; wandering"

        elif goal == "REST":
            action_type = "rest"
            energy = min(1000, energy + (90 if e.get("has_shelter") else 55))
            explanation = f"energy={e['energy']} below threshold (night={night}); resting"

        elif goal == "BUILD_SHELTER":
            action_type = "build_shelter"
            shelter_id = f"shelter-{eid.split('-')[-1]}"
            inventory -= SHELTER_COST
            touched_scope.append(shelter_id)
            new_entities[shelter_id] = {"type": "shelter", "position": dict(pos), "alive": True, "owner_id": eid}
            has_shelter_after = True
            explanation = f"inventory={e['inventory']} >= cost {SHELTER_COST}; built shelter {shelter_id}"

        elif goal == "GATHER_SURPLUS":
            action_type = "gather"
            amount = min(10, nearest_tree["resource"])
            tree_id = nearest_tree["id"]
            touched_scope.append(tree_id)
            preconditions.append({"entity_id": tree_id, "field": "claimed_tick", "op": "neq", "value": tick})
            preconditions.append({"entity_id": tree_id, "field": "resource", "op": "gte", "value": amount})
            entity_updates[tree_id] = {"resource": nearest_tree["resource"] - amount, "claimed_tick": tick}
            inventory += amount
            explanation = f"idle capacity; gathering surplus {amount} from {tree_id}"

        else:
            action_type = "wander"
            dx, dy = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)])
            candidate = {"x": pos["x"] + dx, "y": pos["y"] + dy}
            if is_passable(candidate, terrain):
                pos = candidate
            explanation = "no urgent need; wandering"

        entity_updates[eid] = {
            "position": pos, "hunger": hunger, "thirst": thirst, "energy": energy,
            "inventory": inventory, "has_shelter": has_shelter_after,
            "current_goal": goal, "current_action": action_type,
        }

        return {
            "proposal_family": "people_action",
            "proposal_type": action_type,
            "proposer_engine_id": self.engine_id,
            "proposer_engine_version": self.engine_version,
            "entity_id": eid,
            "causal_parent_event_ids": [e["last_event_id"]] if e.get("last_event_id") else [],
            "is_exogenous": not e.get("last_event_id"),
            "requested_time": tick,
            "phase": "agent",
            "engine_priority": self.engine_priority,
            "touched_scope": touched_scope,
            "preconditions": preconditions,
            "mutation": {"entity_updates": entity_updates, "new_entities": new_entities},
            "explanation": explanation,
        }
