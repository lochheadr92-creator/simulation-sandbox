"""AnimalDomain: simple agent engine - wander / graze / flee / rest.

Behaviour emerges from need + situation, never from a fixed script:
    score(goal) = f(needs, proximity to threat, time of day)
The highest-scoring goal is selected; all others are recorded as rejected
candidates so the causal inspector can show genuine alternatives.
"""
from domains.base import DomainEngine, DomainOutput
from core.constants import is_night
from core.geometry import manhattan, is_passable, find_nearest_entity

FLEE_RADIUS = 3
REST_THRESHOLD = 400


class AnimalDomain(DomainEngine):
    engine_id = "animal"
    engine_version = "1.0.0"
    engine_priority = 20
    phase = "agent"

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        night = is_night(frame.simulation_time)

        for eid in frame.due_entity_ids:
            e = frame.entities.get(eid)
            if not e or e["type"] != "animal" or not e.get("alive", True):
                continue

            if e["energy"] <= 0 and e["hunger"] >= 1000:
                proposal = self._death_proposal(e, eid, frame.simulation_time)
                proposals.append(proposal)
                diagnostics[eid] = {"candidates": [], "selected_goal": "DEATH", "explanation": proposal["explanation"]}
                continue

            rng = frame.rng.stream(f"animal.{eid}.decision.{frame.simulation_time}")
            pos = e["position"]
            nearest_person = find_nearest_entity(frame.entities, pos, "person", lambda p: p.get("alive", True))
            threatened = nearest_person is not None and manhattan(pos, nearest_person["position"]) <= FLEE_RADIUS

            candidates = [
                {"goal": "FLEE", "score": 900 if threatened else 0},
                {"goal": "REST", "score": max(0, REST_THRESHOLD - e["energy"]) * (2 if night else 1)},
                {"goal": "GRAZE", "score": 200 if e["hunger"] > 400 else 60},
                {"goal": "WANDER", "score": 30 if not night else 10},
            ]
            best = max(candidates, key=lambda c: c["score"])
            rejected_goals = [c for c in candidates if c["goal"] != best["goal"]]

            hunger = min(1000, e["hunger"] + 6)
            energy = max(0, e["energy"] - (6 if night else 4))
            new_pos = dict(pos)
            action_type = "wander"
            explanation = ""

            if best["goal"] == "FLEE":
                action_type = "flee"
                dx = pos["x"] - nearest_person["position"]["x"]
                dy = pos["y"] - nearest_person["position"]["y"]
                target = {"x": pos["x"] + (1 if dx >= 0 else -1), "y": pos["y"] + (1 if dy >= 0 else -1)}
                if is_passable(target, frame.terrain):
                    new_pos = target
                explanation = f"person within flee radius {FLEE_RADIUS}; fleeing away"
            elif best["goal"] == "REST":
                action_type = "rest"
                energy = min(1000, energy + 70)
                explanation = f"energy={e['energy']} below threshold; resting"
            elif best["goal"] == "GRAZE":
                action_type = "graze"
                hunger = max(0, hunger - 250)
                explanation = f"hunger={e['hunger']} high; grazing on grass"
            else:
                action_type = "wander"
                dx, dy = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)])
                candidate = {"x": pos["x"] + dx, "y": pos["y"] + dy}
                if is_passable(candidate, frame.terrain):
                    new_pos = candidate
                explanation = "no urgent need; wandering"

            entity_updates = {eid: {
                "position": new_pos, "hunger": hunger, "energy": energy,
                "current_goal": best["goal"], "current_action": action_type,
            }}

            proposals.append({
                "proposal_family": "animal_action",
                "proposal_type": action_type,
                "proposer_engine_id": self.engine_id,
                "proposer_engine_version": self.engine_version,
                "entity_id": eid,
                "causal_parent_event_ids": [e["last_event_id"]] if e.get("last_event_id") else [],
                "is_exogenous": not e.get("last_event_id"),
                "requested_time": frame.simulation_time,
                "phase": "agent",
                "engine_priority": self.engine_priority,
                "touched_scope": [eid],
                "preconditions": [],
                "mutation": {"entity_updates": entity_updates, "new_entities": {}},
                "explanation": explanation,
            })
            diagnostics[eid] = {
                "candidates": candidates, "selected_goal": best["goal"],
                "rejected_goals": rejected_goals, "night": night, "explanation": explanation,
            }

        return DomainOutput(proposals=proposals, diagnostics=diagnostics)

    def _death_proposal(self, e, eid, tick):
        return {
            "proposal_family": "animal_action",
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
            "explanation": f"critical: energy=0 with hunger={e['hunger']} -> death",
        }
