"""Capability Stage 6A internal state, perception, knowledge, and memory."""
import copy

from core.commit_pipeline import run_commit_frame
from core.mutations import apply_mutation
from core.rng import DeterministicRNG
from domains.base import ActivationFrame, DomainOutput
from domains.living_agent_cognition import (
    derive_internal_pressures,
    merge_knowledge_claim,
    merge_meaningful_memories,
    merge_observations_into_knowledge,
    perceive_living,
    refresh_wants,
)
from domains.living_agent_contracts import LIMITS, empty_living_agent_state
from domains.people_domain import PeopleDomain
from domains.perception import empty_knowledge


def _person(position, *, energy=900, hunger=200, thirst=200):
    return {
        "type": "person",
        "position": dict(position),
        "hunger": hunger,
        "thirst": thirst,
        "energy": energy,
        "inventory": 0,
        "food_inventory": 0,
        "has_shelter": False,
        "current_goal": "IDLE",
        "alive": True,
        "action": {
            "type": "idle", "status": "completed", "target_entity_id": None,
            "target_pos": None, "ticks_spent": 0, "ticks_required": 0,
            "interruptible": True, "started_tick": 0,
        },
        "plan": {"goal": None, "steps": [], "step_index": 0, "status": "completed"},
        "paused": None,
        "knowledge": empty_knowledge(),
        "age_ticks": 5000,
        "life_stage": "adult",
        "health": 1000,
        "injury": {"injured": False, "severity": 0, "cause": None},
        "last_event_id": "evt-0-0-genesis",
    }


def _terrain(width=9, height=9, fill="grass"):
    return [[fill for _ in range(width)] for _ in range(height)]


def test_identical_inputs_produce_identical_pressures_and_trait_weighted_urgency():
    entity = _person({"x": 2, "y": 2}, energy=300, hunger=760, thirst=820)
    knowledge = empty_knowledge()
    delta = {"person_sightings": {}, "danger_sightings": {"animal-1": {}}}
    state = empty_living_agent_state("person-001", 0, DeterministicRNG("pressure-seed"))

    left = derive_internal_pressures(entity, state, knowledge, delta, 4, night=True)
    right = derive_internal_pressures(entity, state, knowledge, delta, 4, night=True)

    assert left == right
    assert left["pressures"]["thirst"]["severity"] == 820
    assert left["pressures"]["fatigue"]["severity"] == 700
    assert left["pressures"]["safety"]["severity"] > 0
    assert left["pressures"]["exposure"]["source"] == "environment:weather_or_night"


def test_multifactor_perception_is_bounded_obstructed_and_never_leaks_private_state():
    terrain = _terrain()
    terrain[1][2] = "wall"
    observer = _person({"x": 1, "y": 1})
    private_person = _person({"x": 1, "y": 3}, hunger=999, thirst=999)
    private_person["plan"] = {"goal": "SECRET", "steps": ["SECRET"], "step_index": 0, "status": "active"}
    entities = {
        "person-observer": observer,
        "person-private": private_person,
        "tool-hidden": {
            "type": "tool", "position": {"x": 3, "y": 1}, "tool_kind": "axe",
            "durability": 900, "owner_id": "person-private", "last_event_id": "evt-tool",
        },
    }

    visible = perceive_living("person-observer", observer, entities, terrain, 3)
    subjects = {item["observed_subject_id"]: item for item in visible["observations"]}

    assert "person-private" in subjects
    assert "tool-hidden" not in subjects
    person_properties = subjects["person-private"]["properties"]
    assert "hunger" not in person_properties
    assert "thirst" not in person_properties
    assert "plan" not in person_properties
    assert subjects["person-private"]["information_kind"] == "direct"

    exhausted = _person({"x": 1, "y": 1}, energy=0)
    reduced = perceive_living("person-observer", exhausted, entities, terrain, 3, night=True)
    assert reduced["effective_radius"] < visible["effective_radius"]
    assert len(reduced["observations"]) <= LIMITS.perceived_entities_per_observation


def test_entity_insertion_order_does_not_change_observation_or_knowledge():
    terrain = _terrain()
    observer = _person({"x": 4, "y": 4})
    entities = {
        "person-observer": observer,
        "tool-b": {"type": "tool", "position": {"x": 5, "y": 4}, "tool_kind": "knife", "durability": 300},
        "person-a": _person({"x": 3, "y": 4}),
        "storage-z": {"type": "storage", "position": {"x": 4, "y": 5}, "open": True, "access": "shared", "contents": {"food": 2}},
    }
    reversed_entities = dict(reversed(list(entities.items())))

    left = perceive_living("person-observer", observer, entities, terrain, 5)
    right = perceive_living("person-observer", observer, reversed_entities, terrain, 5)
    assert left["observations"] == right["observations"]

    left_k, left_changed, _ = merge_observations_into_knowledge(empty_knowledge(), left["observations"])
    right_k, right_changed, _ = merge_observations_into_knowledge(empty_knowledge(), right["observations"])
    assert left_changed is right_changed is True
    assert left_k == right_k


def test_reported_false_and_contradictory_information_remains_explicitly_uncertain():
    knowledge = empty_knowledge()
    observation = {
        "observation_id": "obs-direct",
        "perceiving_entity_id": "person-a",
        "observed_subject_id": "storage-1",
        "observation_type": "storage",
        "observed_tick": 2,
        "confidence": 950,
        "information_kind": "direct",
        "source_event_id": "evt-storage",
        "properties": {"open": False, "access": "private"},
    }
    knowledge, _, _ = merge_observations_into_knowledge(knowledge, [observation])
    knowledge, claim = merge_knowledge_claim(
        knowledge,
        observer_id="person-a",
        subject_id="storage-1",
        fact_type="storage",
        properties={"open": True, "access": "public"},
        tick=3,
        provenance_kind="reported",
        confidence=600,
        source_entity_id="person-liar",
        source_event_id="evt-lie",
        deceptive=True,
    )

    assert claim["status"] == "contradicted"
    assert claim["deceptive_source_claim"] is True
    assert claim["contradiction_count"] >= 1
    assert claim["provenance_kind"] == "reported"
    assert claim["stale_after_tick"] == 15


def test_memory_retention_preserves_significant_threat_and_enforces_caps():
    state = empty_living_agent_state("person-a", 0)
    observations = []
    learned = []
    for index in range(LIMITS.memories_per_entity + 12):
        subject = f"resource-{index:03d}"
        observations.append({
            "observation_id": f"obs-{index:03d}",
            "observed_subject_id": subject,
            "observation_type": "resource",
            "confidence": 700,
            "source_event_id": f"evt-{index}",
            "properties": {"resource_kind": "wood"},
        })
        learned.append({"subject": subject})
    observations.append({
        "observation_id": "obs-threat",
        "observed_subject_id": "signal-threat",
        "observation_type": "signal",
        "confidence": 1000,
        "source_event_id": "evt-threat",
        "properties": {"signal_kind": "warning"},
    })

    merged, updated = merge_meaningful_memories(
        state,
        actor_id="person-a",
        tick=10,
        observations=observations,
        learned=learned,
    )

    assert len(merged["memories"]) == LIMITS.memories_per_entity
    assert any(item["memory_kind"] == "threat_observed" for item in merged["memories"].values())
    assert len(updated) == len(observations)


def test_wants_are_persistent_desired_outcomes_not_forced_actions():
    state = empty_living_agent_state("person-a", 0)
    state["pressures"]["curiosity"]["urgency"] = 600
    state["pressures"]["comfort"]["urgency"] = 500

    refreshed = refresh_wants(state, "person-a", 4)
    types = {item["want_type"] for item in refreshed["wants"].values()}

    assert "explore_unknown_area" in types
    assert "improve_shelter" in types
    assert all("action" not in item for item in refreshed["wants"].values())
    assert refreshed == refresh_wants(refreshed, "person-a", 4)


def test_core_stamps_knowledge_and_memory_acquisition_event_for_replay():
    entities = {"person-a": _person({"x": 1, "y": 1})}
    state = empty_living_agent_state("person-a", 1)
    state["memories"] = {
        "memory-1": {
            "last_recalled_tick": 1,
            "acquired_event_id": None,
        }
    }
    knowledge = empty_knowledge()
    knowledge["facts"]["fact-1"] = {
        "first_known_tick": 1,
        "learned_event_id": None,
    }
    proposal = {
        "proposal_family": "people_action",
        "proposal_type": "observe",
        "proposer_engine_id": "test",
        "proposer_engine_version": "1",
        "entity_id": "person-a",
        "causal_parent_event_ids": [],
        "is_exogenous": True,
        "requested_time": 1,
        "phase": "agent",
        "engine_priority": 1,
        "touched_scope": ["person-a"],
        "preconditions": [],
        "mutation": {"entity_updates": {"person-a": {"living_agent": state, "knowledge": knowledge}}, "new_entities": {}},
        "explanation": "test acquisition",
    }

    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], 1, "lineage", "run", 0, "frame-1",
    )

    assert not rejected
    event = accepted[0]
    update = event["mutation"]["entity_updates"]["person-a"]
    assert update["living_agent"]["memories"]["memory-1"]["acquired_event_id"] == event["id"]
    assert update["knowledge"]["facts"]["fact-1"]["learned_event_id"] == event["id"]
    replayed = {"person-a": _person({"x": 1, "y": 1})}
    apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    assert replayed == entities


def test_people_domain_proposes_integrated_stage6a_state_without_mutating_frame():
    terrain = _terrain(7, 7)
    terrain[3][2] = "water"
    entities = {
        "person-a": _person({"x": 3, "y": 3}, hunger=740, thirst=800),
        "person-b": _person({"x": 4, "y": 3}, hunger=950, thirst=300),
        "tree-a": {
            "type": "tree", "position": {"x": 3, "y": 4}, "resource": 20,
            "max_resource": 20, "alive": True, "claimed_tick": None,
            "last_event_id": "evt-tree",
        },
    }
    before = copy.deepcopy(entities)
    frame = ActivationFrame(
        "run", 1, "engine", "agent", entities, terrain, ["person-a"],
        DeterministicRNG("stage6-domain"),
    )
    frame.night = False

    output = PeopleDomain().activate(frame)
    proposal = output.proposals[0]
    update = proposal["mutation"]["entity_updates"]["person-a"]

    assert entities == before
    assert update["living_agent"]["schema_version"] == "living-agent-v1"
    assert set(update["living_agent"]["pressures"]) >= {"thirst", "hunger", "belonging", "fear"}
    assert len(update["living_agent"]["memories"]) <= LIMITS.memories_per_entity
    assert output.diagnostics["person-a"]["living_agent"]["perception_version"] == "living-perception-v1"
    person_facts = [
        fact for fact in update["knowledge"]["facts"].values()
        if fact.get("subject") == "person-b"
    ]
    assert person_facts
    assert all("hunger" not in (fact.get("properties") or {}) for fact in person_facts)
