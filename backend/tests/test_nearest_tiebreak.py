"""Regression: nearest-target selection must be insertion-order independent.

History (2026-07-14 assessment, Task C): equidistant candidates in
`find_nearest_entity` / `nearest_huntable_animal` could in principle follow
dict iteration order - Mongo `find()` natural order on the live path vs
genesis insertion order in the determinism shadow - changing proposal
CONTENT and false-failing determinism verification. Both selectors resolve
ties deterministically today: `find_nearest_entity` iterates ids in sorted
order with a strict `<` comparison (first hit == smallest id at a tied
distance) and `nearest_huntable_animal` ranks candidates by an explicit
`(distance, sighted-preference, entity_id)` tuple. These tests pin that
contract for both insertion orders so a future refactor cannot silently
reintroduce order dependence.

Pure unit tests: no server, no Mongo, no env.
"""
from core.geometry import find_nearest_entity
from domains.people_utility import nearest_huntable_animal


def _animal(x, y):
    return {"type": "animal", "alive": True, "position": {"x": x, "y": y}}


class TestFindNearestEntityTieBreak:
    def test_equidistant_tie_returns_smaller_id_insertion_order_ab(self):
        entities = {
            "animal-b": _animal(2, 0),
            "animal-a": _animal(0, 2),
        }
        best = find_nearest_entity(entities, {"x": 0, "y": 0}, "animal")
        assert best["id"] == "animal-a"

    def test_equidistant_tie_returns_smaller_id_insertion_order_ba(self):
        entities = {
            "animal-a": _animal(0, 2),
            "animal-b": _animal(2, 0),
        }
        best = find_nearest_entity(entities, {"x": 0, "y": 0}, "animal")
        assert best["id"] == "animal-a"

    def test_strictly_nearer_candidate_still_beats_id_order(self):
        entities = {
            "animal-a": _animal(0, 3),
            "animal-z": _animal(1, 0),
        }
        best = find_nearest_entity(entities, {"x": 0, "y": 0}, "animal")
        assert best["id"] == "animal-z"


class TestNearestHuntableAnimalTieBreak:
    @staticmethod
    def _knowledge(order):
        animals = {
            "animal-a": {"position": {"x": 0, "y": 2}},
            "animal-b": {"position": {"x": 2, "y": 0}},
        }
        return {"known_animals": {key: animals[key] for key in order}}

    def test_equidistant_tie_returns_smaller_id_both_insertion_orders(self):
        pos = {"x": 0, "y": 0}
        for order in (("animal-a", "animal-b"), ("animal-b", "animal-a")):
            best_id, best_pos, best_d = nearest_huntable_animal(
                pos, self._knowledge(order),
            )
            assert best_id == "animal-a", f"insertion order {order} changed the winner"
            assert best_d == 2
            assert best_pos == {"x": 0, "y": 2}

    def test_currently_sighted_beats_stale_knowledge_at_equal_distance(self):
        pos = {"x": 0, "y": 0}
        knowledge = {"known_animals": {"animal-a": {"position": {"x": 0, "y": 2}}}}
        delta = {"animal_sightings": {"animal-b": {"position": {"x": 2, "y": 0}}}}
        best_id, _, best_d = nearest_huntable_animal(
            pos, knowledge, perception_delta=delta,
        )
        assert best_id == "animal-b"  # sighted preference is the documented middle rank key
        assert best_d == 2

    def test_strictly_nearer_candidate_still_beats_sighted_preference(self):
        pos = {"x": 0, "y": 0}
        knowledge = {"known_animals": {"animal-z": {"position": {"x": 0, "y": 1}}}}
        delta = {"animal_sightings": {"animal-a": {"position": {"x": 2, "y": 0}}}}
        best_id, _, best_d = nearest_huntable_animal(
            pos, knowledge, perception_delta=delta,
        )
        assert best_id == "animal-z"
        assert best_d == 1
