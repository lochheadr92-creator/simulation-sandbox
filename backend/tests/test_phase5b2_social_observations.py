"""Focused Phase 5B2 contract: bounded, observer-owned social observations."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from api.cognitive_projection import build_cognitive_projection
from core.commit_pipeline import run_commit_frame
from core.hashing import canonical_hash
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from domains.base import ActivationFrame, DomainOutput
from domains.people_domain import PeopleDomain
from domains.perception import (
    MAX_KNOWN_PEOPLE,
    SOCIAL_OBSERVATION_VERSION,
    _compat_knowledge,
    empty_knowledge,
    merge_knowledge,
    perceive,
)


def _terrain(width=24, height=8):
    return [["grass"] * width for _ in range(height)]


def _person(position, *, hunger=100, thirst=100, energy=900, food=0, inventory=0,
            injured=False, action=None, alive=True, knowledge=None):
    return {
        "type": "person", "position": dict(position), "alive": alive,
        "hunger": hunger, "thirst": thirst, "energy": energy,
        "food_inventory": food, "inventory": inventory, "has_shelter": False,
        "injury": {"injured": injured, "severity": 800 if injured else 0, "cause": "private" if injured else None},
        "action": action or {
            "type": "idle", "status": "completed", "target_entity_id": None,
            "target_pos": None, "remaining_path": [], "ticks_spent": 0,
        },
        "plan": {"goal": "PRIVATE_GOAL", "steps": ["PRIVATE_STEP"], "step_index": 0, "status": "active"},
        "knowledge": knowledge if knowledge is not None else empty_knowledge(),
    }


def _observed_entities(subject=None):
    return {
        "observer": _person({"x": 1, "y": 1}),
        "subject": subject or _person({"x": 3, "y": 1}),
    }


def _observe_and_merge(entities, tick=7, radius=4):
    delta = perceive(entities["observer"]["position"], entities, _terrain(), tick, "observer", radius)
    return delta, merge_knowledge(empty_knowledge(), delta, "observer")


def test_visible_person_records_only_the_allowed_coarse_social_facts():
    subject = _person(
        {"x": 3, "y": 1}, hunger=701, food=2, inventory=9, injured=True,
        action={
            "type": "travel", "status": "travelling", "target_entity_id": "private-target",
            "target_pos": {"x": 20, "y": 4}, "remaining_path": [{"x": 4, "y": 1}],
            "utility_score": 999,
        },
    )
    _, (knowledge, changed, _) = _observe_and_merge(_observed_entities(subject))
    observation = knowledge["known_people"]["subject"]
    assert changed is True
    assert observation == {
        "subject_id": "subject", "last_seen_tick": 7, "position": {"x": 3, "y": 1}, "alive": True,
        "social_observation_version": SOCIAL_OBSERVATION_VERSION,
        "visible_action_kind": "travel", "visible_action_status": "travelling",
        "appears_injured": True, "apparent_urgent_need": "distressed",
        "appears_to_carry_food": True,
    }
    forbidden = ("hunger", "thirst", "energy", "inventory", "food_inventory", "target", "path", "utility", "goal", "plan")
    assert not any(field in str(observation) for field in forbidden)
    assert knowledge["facts"]["person:subject"]["visible_action_kind"] == "travel"


def test_out_of_range_or_dead_people_produce_no_social_observation():
    entities = _observed_entities(_person({"x": 12, "y": 1}))
    delta, (knowledge, _, _) = _observe_and_merge(entities)
    assert delta["person_sightings"] == {}
    assert knowledge["known_people"] == {}
    entities["subject"] = _person({"x": 2, "y": 1}, alive=False)
    delta, (knowledge, _, _) = _observe_and_merge(entities)
    assert delta["person_sightings"] == {}
    assert knowledge["known_people"] == {}


def test_carried_food_is_boolean_and_urgency_and_injury_use_versioned_coarse_rules():
    critical = _person({"x": 3, "y": 1}, hunger=900, food=1, inventory=7, injured=True)
    _, (knowledge, _, _) = _observe_and_merge(_observed_entities(critical))
    fact = knowledge["known_people"]["subject"]
    assert fact["appears_to_carry_food"] is True
    assert fact["apparent_urgent_need"] == "critical"
    assert fact["appears_injured"] is True
    calm = _person({"x": 3, "y": 1}, hunger=100, thirst=100, energy=0, food=0, inventory=0)
    _, (knowledge, _, _) = _observe_and_merge(_observed_entities(calm))
    assert knowledge["known_people"]["subject"]["apparent_urgent_need"] == "none"
    assert knowledge["known_people"]["subject"]["appears_to_carry_food"] is False


def test_unknown_action_shape_does_not_leak_a_private_action_or_status():
    subject = _person({"x": 3, "y": 1}, action={"type": "private_action", "status": "secret"})
    _, (knowledge, _, _) = _observe_and_merge(_observed_entities(subject))
    observation = knowledge["known_people"]["subject"]
    assert observation["visible_action_kind"] is None
    assert observation["visible_action_status"] is None


def test_identical_reobservation_is_not_a_material_knowledge_write():
    entities = _observed_entities()
    first = perceive(entities["observer"]["position"], entities, _terrain(), 1, "observer")
    knowledge, changed, _ = merge_knowledge(empty_knowledge(), first, "observer")
    second = perceive(entities["observer"]["position"], entities, _terrain(), 2, "observer")
    refreshed, changed_again, learned = merge_knowledge(knowledge, second, "observer")
    assert changed is True
    assert changed_again is False
    assert learned == []
    assert refreshed["known_people"]["subject"]["last_seen_tick"] == 2


def test_changed_visible_action_or_condition_creates_one_material_update():
    entities = _observed_entities()
    _, (knowledge, _, _) = _observe_and_merge(entities, tick=1)
    entities["subject"]["action"] = {"type": "sleep", "status": "performing"}
    entities["subject"]["injury"] = {"injured": True}
    second = perceive(entities["observer"]["position"], entities, _terrain(), 2, "observer")
    updated, changed, learned = merge_knowledge(knowledge, second, "observer")
    assert changed is True
    assert learned == [{"kind": "person", "subject": "subject", "update": "move_or_change"}]
    assert updated["known_people"]["subject"]["visible_action_kind"] == "sleep"
    assert updated["known_people"]["subject"]["appears_injured"] is True
    third = perceive(entities["observer"]["position"], entities, _terrain(), 3, "observer")
    _, changed_again, _ = merge_knowledge(updated, third, "observer")
    assert changed_again is False


def test_stale_social_facts_are_last_known_and_do_not_track_unseen_people():
    entities = _observed_entities()
    _, (knowledge, _, _) = _observe_and_merge(entities, tick=1)
    entities["subject"]["position"] = {"x": 20, "y": 6}
    entities["subject"]["action"] = {"type": "sleep", "status": "performing"}
    delta = perceive(entities["observer"]["position"], entities, _terrain(), 2, "observer")
    stale, changed, _ = merge_knowledge(knowledge, delta, "observer")
    observation = stale["known_people"]["subject"]
    assert changed is False
    assert observation["position"] == {"x": 3, "y": 1}
    assert observation["visible_action_kind"] == "idle"


def test_person_sightings_and_knowledge_are_insertion_order_independent_and_capped():
    entities_a = {"observer": _person({"x": 0, "y": 0})}
    for index in range(MAX_KNOWN_PEOPLE + 1):
        entities_a[f"person-{index:02d}"] = _person({"x": index + 1, "y": 0})
    entities_b = dict(reversed(list(entities_a.items())))
    delta_a = perceive({"x": 0, "y": 0}, entities_a, _terrain(), 4, "observer", radius=100)
    delta_b = perceive({"x": 0, "y": 0}, entities_b, _terrain(), 4, "observer", radius=100)
    ka, _, _ = merge_knowledge(empty_knowledge(), delta_a, "observer")
    kb, _, _ = merge_knowledge(empty_knowledge(), delta_b, "observer")
    assert delta_a["person_sightings"] == delta_b["person_sightings"]
    assert ka == kb
    assert len(ka["known_people"]) == MAX_KNOWN_PEOPLE
    assert "person-00" not in ka["known_people"]


def test_legacy_knowledge_shape_is_readable_without_inventing_social_facts():
    legacy = {"known_people": {"subject": {"position": {"x": 3, "y": 1}, "last_seen_tick": 4}}}
    upgraded = _compat_knowledge(legacy)
    assert upgraded["schema_version"] == "knowledge-v2"
    assert upgraded["known_people"] == legacy["known_people"]
    assert "social_observation_version" not in upgraded["known_people"]["subject"]


def test_projection_is_read_only_observer_specific_and_labels_observed_and_last_known_facts():
    entities = _observed_entities()
    _, (knowledge, _, _) = _observe_and_merge(entities, tick=1)
    entities["observer"]["knowledge"] = knowledge
    before = copy.deepcopy(entities)
    observed = build_cognitive_projection(entities["observer"], entities, _terrain(), 2)
    record = next(item for item in observed["social_observations"] if item["id"] == "subject")
    assert record["observation_state"] == "observed"
    assert record["visible_action_kind"] == "idle"
    assert entities == before
    entities["subject"]["position"] = {"x": 20, "y": 6}
    stale = build_cognitive_projection(entities["observer"], entities, _terrain(), 3)
    record = next(item for item in stale["social_observations"] if item["id"] == "subject")
    assert record["observation_state"] == "last-known"
    assert record["position"] == {"x": 3, "y": 1}


def test_accepted_event_and_replay_retain_social_observation_deterministically():
    entities = _observed_entities(_person({"x": 3, "y": 1}, hunger=700, food=1))
    terrain = _terrain()
    frame = ActivationFrame("run", 5, "engine", "agent", copy.deepcopy(entities), terrain, ["observer"], DeterministicRNG("social-v1"))
    frame.night = False
    proposal = PeopleDomain().activate(frame).proposals[0]
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], 5, "social-lineage", "run", 0, "frame-5",
    )
    assert rejected == []
    assert len(accepted) == 1
    event = accepted[0]
    observation = event["mutation"]["entity_updates"]["observer"]["knowledge"]["known_people"]["subject"]
    assert observation["social_observation_version"] == SOCIAL_OBSERVATION_VERSION
    assert entities["observer"]["last_event_id"] == event["id"]
    replayed = _observed_entities(_person({"x": 3, "y": 1}, hunger=700, food=1))
    apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    assert replayed["observer"]["knowledge"] == entities["observer"]["knowledge"]
    assert canonical_hash(snapshot_for_hash(replayed, 5, "social-lineage")) == canonical_hash(snapshot_for_hash(entities, 5, "social-lineage"))
