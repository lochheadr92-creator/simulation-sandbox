"""Capability Stage 7A emergent association and group recognition tests."""
from __future__ import annotations

import copy
from collections import Counter

from api.association_projection import build_association_projection
from core.commit_pipeline import run_commit_frame
from core.hashing import canonical_hash, canonical_json
from core.mutations import apply_mutation, snapshot_for_hash
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    CANDIDATE_EXPIRY_TICKS,
    LIMITS,
    MEMBER_REMOVAL_GRACE_TICKS,
    RECOGNISED_DISSOLUTION_TICKS,
    advance_association_registry,
    association_capacity_diagnostics,
    association_current_truth_summary,
    association_pair_id,
    build_association_proposal,
    derive_association_evidence,
    group_candidate_id,
    make_association_evidence,
    validate_association_proposal,
)
from domains.base import DomainOutput
from scenarios import get_scenario
from tools.living_agent_harness import run_living_agent_harness


def _person(entity_id: str, x: int = 0, y: int = 0) -> dict:
    return {
        "type": "person",
        "alive": True,
        "position": {"x": x, "y": y},
        "last_event_id": f"evt-genesis-{entity_id}",
    }


def _entities(*person_ids: str) -> dict:
    return {
        person_id: _person(person_id, index, 0)
        for index, person_id in enumerate(person_ids)
    }


def _evidence(pair, category: str, tick: int, suffix: str | None = None) -> dict:
    suffix = suffix or f"{category}-{tick}"
    return make_association_evidence(pair, category, tick, [f"evt-{suffix}"])


def _commit_observations(
    entities: dict,
    tick: int,
    observations: list[dict],
    order: int = 0,
):
    proposal = build_association_proposal(entities, tick, observations=observations)
    assert proposal is not None
    accepted, rejected, next_order = run_commit_frame(
        entities,
        [DomainOutput(proposals=[proposal])],
        tick,
        "stage7a-test-lineage",
        "stage7a-test-run",
        order,
        f"frame-{tick}",
    )
    assert not rejected
    assert len(accepted) == 1
    return accepted, next_order


def _run_pair(category: str, ticks: int, pair=("person-a", "person-b")):
    entities = _entities(*pair)
    events = []
    order = 0
    for tick in range(1, ticks + 1):
        accepted, order = _commit_observations(
            entities, tick, [_evidence(pair, category, tick)], order,
        )
        events.extend(accepted)
    return entities, events, order


def _only_candidate(entities: dict) -> dict:
    candidates = entities[ASSOCIATION_REGISTRY_ID]["group_candidates"]
    assert len(candidates) == 1
    return next(iter(candidates.values()))


def test_one_interaction_does_not_create_or_recognise_group():
    entities, _events, _order = _run_pair("caregiving", 1)
    assert entities[ASSOCIATION_REGISTRY_ID]["group_candidates"] == {}


def test_repeated_meaningful_cooperation_creates_candidate():
    entities, _events, _order = _run_pair("cooperation", 2)
    candidate = _only_candidate(entities)
    assert candidate["recognition_state"] == "candidate"
    assert candidate["member_ids"] == ["person-a", "person-b"]


def test_sustained_qualifying_evidence_promotes_recognition():
    entities, _events, _order = _run_pair("cooperation", 5)
    candidate = _only_candidate(entities)
    assert candidate["recognition_state"] == "recognised"
    assert candidate["recognition_event_id"]


def test_repeated_proximity_alone_does_not_create_household():
    entities, _events, _order = _run_pair("proximity", 20)
    candidates = entities[ASSOCIATION_REGISTRY_ID]["group_candidates"]
    assert not any(
        candidate["group_type"] == "household_like"
        for candidate in candidates.values()
    )
    assert not any(
        candidate["recognition_state"] == "recognised"
        for candidate in candidates.values()
    )


def test_caregiving_and_shared_shelter_infer_household_like_groups():
    caregiving, _events, _order = _run_pair("caregiving", 3)
    shared_shelter, _events2, _order2 = _run_pair("shared_shelter", 3)
    for entities in (caregiving, shared_shelter):
        candidate = _only_candidate(entities)
        assert candidate["group_type"] == "household_like"
        assert candidate["recognition_state"] == "recognised"


def test_coordinated_travel_infers_travelling_working_group():
    entities, _events, _order = _run_pair("coordinated_travel", 6)
    candidate = _only_candidate(entities)
    assert candidate["group_type"] == "travelling_working"
    assert candidate["recognition_state"] == "recognised"


def test_equivalent_inputs_and_member_order_create_same_identity():
    forward = [_evidence(["person-a", "person-b"], "caregiving", tick) for tick in (1, 2)]
    reverse = [
        make_association_evidence(
            ["person-b", "person-a"], "caregiving", item["tick"], item["source_event_ids"],
        )
        for item in forward
    ]
    first, _ = advance_association_registry(None, forward, ["person-a", "person-b"], 2)
    second, _ = advance_association_registry(None, list(reversed(reverse)), ["person-b", "person-a"], 2)
    assert first == second
    first_candidate = next(iter(first["group_candidates"].values()))
    formation = first_candidate["formation_evidence_summary"]["decisive_event_ids"]
    assert first_candidate["candidate_id"] == group_candidate_id(
        first_candidate["founding_pair_id"], first_candidate["first_supported_tick"], formation,
    )


def test_unrelated_person_is_not_absorbed_through_one_bridge_link():
    entities = _entities("person-a", "person-b", "person-c")
    order = 0
    for tick in range(1, 4):
        accepted, order = _commit_observations(
            entities, tick, [_evidence(["person-a", "person-b"], "caregiving", tick)], order,
        )
        assert accepted
    for tick in range(4, 7):
        _accepted, order = _commit_observations(
            entities, tick, [
                _evidence(["person-a", "person-b"], "caregiving", tick),
                _evidence(["person-a", "person-c"], "caregiving", tick),
            ], order,
        )
    member_sets = {
        tuple(candidate["member_ids"])
        for candidate in entities[ASSOCIATION_REGISTRY_ID]["group_candidates"].values()
    }
    assert ("person-a", "person-b") in member_sets
    assert ("person-a", "person-b", "person-c") not in member_sets


def test_membership_grows_only_with_complete_link_evidence():
    entities = _entities("person-a", "person-b", "person-c")
    order = 0
    for tick in range(1, 4):
        _accepted, order = _commit_observations(
            entities, tick, [_evidence(["person-a", "person-b"], "caregiving", tick)], order,
        )
    for tick in range(4, 6):
        _accepted, order = _commit_observations(
            entities, tick, [
                _evidence(["person-a", "person-b"], "caregiving", tick),
                _evidence(["person-a", "person-c"], "caregiving", tick),
                _evidence(["person-b", "person-c"], "caregiving", tick),
            ], order,
        )
    candidate = _only_candidate(entities)
    assert candidate["member_ids"] == ["person-a", "person-b", "person-c"]
    assert candidate["membership_evidence"]["person-c"]


def test_membership_shrinks_when_added_member_support_disappears():
    entities = _entities("person-a", "person-b", "person-c")
    order = 0
    for tick in range(1, 4):
        _accepted, order = _commit_observations(
            entities, tick, [_evidence(["person-a", "person-b"], "caregiving", tick)], order,
        )
    for tick in range(4, 6):
        _accepted, order = _commit_observations(
            entities, tick, [
                _evidence(["person-a", "person-b"], "caregiving", tick),
                _evidence(["person-a", "person-c"], "caregiving", tick),
                _evidence(["person-b", "person-c"], "caregiving", tick),
            ], order,
        )
    assert "person-c" in _only_candidate(entities)["member_ids"]
    end_tick = 5 + MEMBER_REMOVAL_GRACE_TICKS
    for tick in range(6, end_tick + 1):
        _accepted, order = _commit_observations(
            entities, tick, [_evidence(["person-a", "person-b"], "caregiving", tick)], order,
        )
    candidate = _only_candidate(entities)
    assert candidate["member_ids"] == ["person-a", "person-b"]
    assert candidate["last_removed_member_ids"] == ["person-c"]


def test_candidate_expires_without_continuing_support():
    entities, _events, order = _run_pair("cooperation", 2)
    for tick in range(3, 2 + CANDIDATE_EXPIRY_TICKS + 1):
        _accepted, order = _commit_observations(entities, tick, [], order)
    registry = entities[ASSOCIATION_REGISTRY_ID]
    assert registry["group_candidates"] == {}
    assert registry["dissolved_history"][-1]["final_state"] == "expired"


def test_recognised_group_weakens_then_dissolves():
    entities, _events, order = _run_pair("caregiving", 3)
    for tick in range(4, 7):
        _accepted, order = _commit_observations(entities, tick, [], order)
    assert _only_candidate(entities)["recognition_state"] == "weakening"
    for tick in range(7, 3 + RECOGNISED_DISSOLUTION_TICKS + 1):
        _accepted, order = _commit_observations(entities, tick, [], order)
    registry = entities[ASSOCIATION_REGISTRY_ID]
    assert registry["group_candidates"] == {}
    assert registry["dissolved_history"][-1]["final_state"] == "dissolved"


def test_formation_and_dissolution_have_accepted_causal_provenance():
    entities, events, order = _run_pair("caregiving", 3)
    candidate = _only_candidate(entities)
    assert candidate["formation_event_id"] in {event["id"] for event in events}
    assert candidate["formation_evidence_summary"]["decisive_event_ids"]
    for tick in range(4, 3 + RECOGNISED_DISSOLUTION_TICKS + 1):
        accepted, order = _commit_observations(entities, tick, [], order)
        events.extend(accepted)
    history = entities[ASSOCIATION_REGISTRY_ID]["dissolved_history"][-1]
    assert history["dissolution_event_id"] in {event["id"] for event in events}
    assert history["dissolution_cause_event_ids"]


def test_replay_rebuilds_identical_group_state_and_hash():
    initial = _entities("person-a", "person-b")
    entities = copy.deepcopy(initial)
    events = []
    order = 0
    for tick in range(1, 6):
        accepted, order = _commit_observations(
            entities, tick, [_evidence(["person-a", "person-b"], "cooperation", tick)], order,
        )
        events.extend(copy.deepcopy(accepted))
    replayed = copy.deepcopy(initial)
    for event in events:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    assert replayed == entities
    assert canonical_hash(snapshot_for_hash(replayed, 5, "stage7a-test-lineage")) \
        == canonical_hash(snapshot_for_hash(entities, 5, "stage7a-test-lineage"))


def test_restart_resume_preserves_identical_groups():
    uninterrupted = _entities("person-a", "person-b")
    resumed = copy.deepcopy(uninterrupted)
    first_order = second_order = 0
    for tick in range(1, 4):
        _accepted, first_order = _commit_observations(
            uninterrupted, tick, [_evidence(["person-a", "person-b"], "caregiving", tick)], first_order,
        )
        _accepted, second_order = _commit_observations(
            resumed, tick, [_evidence(["person-a", "person-b"], "caregiving", tick)], second_order,
        )
    resumed = copy.deepcopy(resumed)  # storage/restart boundary
    for tick in range(4, 8):
        observation = [_evidence(["person-a", "person-b"], "caregiving", tick)]
        _accepted, first_order = _commit_observations(uninterrupted, tick, observation, first_order)
        _accepted, second_order = _commit_observations(resumed, tick, observation, second_order)
    assert resumed == uninterrupted
    assert second_order == first_order


def test_duplicate_identical_proposals_accept_once_without_duplicate_group():
    entities = _entities("person-a", "person-b")
    observations = [
        _evidence(["person-a", "person-b"], "caregiving", 1, "care-1"),
        _evidence(["person-a", "person-b"], "caregiving", 2, "care-2"),
    ]
    proposal = build_association_proposal(entities, 2, observations=observations)
    accepted, rejected, next_order = run_commit_frame(
        entities,
        [DomainOutput(proposals=[copy.deepcopy(proposal), copy.deepcopy(proposal)])],
        2,
        "stage7a-test-lineage",
        "stage7a-test-run",
        0,
        "frame-2",
    )
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["reason_code"] == "association.duplicate_registry"
    assert next_order == 1
    assert len(entities[ASSOCIATION_REGISTRY_ID]["group_candidates"]) == 1


def test_invalid_group_proposal_is_rejected_without_mutation():
    entities = _entities("person-a", "person-b")
    proposal = build_association_proposal(entities, 2, observations=[
        _evidence(["person-a", "person-b"], "caregiving", 1, "care-1"),
        _evidence(["person-a", "person-b"], "caregiving", 2, "care-2"),
    ])
    registry = proposal["mutation"]["new_entities"][ASSOCIATION_REGISTRY_ID]
    candidate = next(iter(registry["group_candidates"].values()))
    candidate["member_ids"] = list(reversed(candidate["member_ids"]))
    proposal["association_update"]["payload_bytes"] = len(
        canonical_json(registry).encode("utf-8")
    )
    before = copy.deepcopy(entities)
    accepted, rejected, _order = run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], 2,
        "stage7a-test-lineage", "stage7a-test-run", 0, "frame-2",
    )
    assert not accepted
    assert rejected[0]["reason_code"] == "association.invalid_candidate"
    assert entities == before


def test_canonical_state_and_proposal_payload_remain_within_explicit_caps():
    people = [f"person-{index:02d}" for index in range(30)]
    registry = None
    for tick in range(1, 121):
        observations = []
        for offset in range(15):
            left = people[(tick + offset * 2) % len(people)]
            right = people[(tick + offset * 2 + 1) % len(people)]
            observations.append(_evidence([left, right], "cooperation", tick, f"{tick}-{offset}"))
        registry, _transitions = advance_association_registry(registry, observations, people, tick)
    counts = Counter()
    for record in registry["association_records"].values():
        assert len(record["recent_evidence"]) <= LIMITS.detailed_evidence_per_record
        assert len(record["causal_event_ids"]) <= LIMITS.provenance_refs
        for person_id in record["person_ids"]:
            counts[person_id] += 1
    assert len(registry["association_records"]) <= LIMITS.records
    assert max(counts.values()) <= LIMITS.records_per_person
    assert len(registry["group_candidates"]) <= LIMITS.candidates
    assert len(registry["dissolved_history"]) <= LIMITS.dissolved_history
    assert len(registry["processed_evidence_ids"]) <= LIMITS.processed_evidence_ids

    entities = {person_id: _person(person_id) for person_id in people}
    entities[ASSOCIATION_REGISTRY_ID] = registry
    proposal = build_association_proposal(entities, 122, observations=[])
    assert proposal["association_update"]["payload_bytes"] <= LIMITS.proposal_bytes
    assert validate_association_proposal(proposal, entities) is None


def test_compact_evidence_preserves_current_truth_provenance_and_exact_accounting():
    people = ["person-a", "person-b"]
    observations = [
        _evidence(people, "caregiving", tick, f"compact-{tick}")
        for tick in range(1, 6)
    ]
    registry, _ = advance_association_registry(None, observations, people, 5)
    record = next(iter(registry["association_records"].values()))

    assert len(record["recent_evidence"]) == 5
    assert set(record["recent_evidence"][-1]) == {
        "evidence_id", "category", "tick", "source_event_ids", "condition_ids",
    }
    assert len(record["categories"]["caregiving"]["source_event_ids"]) \
        == LIMITS.category_provenance_refs
    assert record["causal_event_ids"]

    composition = association_capacity_diagnostics(registry)
    assert composition["total_serialized_bytes"] == sum(
        value for key, value in composition.items() if key != "total_serialized_bytes"
    )
    assert composition["current_truth_bytes"] > 0
    assert composition["historical_support_evidence_bytes"] > 0
    assert composition["provenance_reference_bytes"] > 0


def test_legacy_full_evidence_normalises_without_changing_current_truth():
    people = ["person-a", "person-b"]
    full_evidence = _evidence(people, "caregiving", 1, "legacy-full")
    registry, _ = advance_association_registry(None, [full_evidence], people, 1)
    record = next(iter(registry["association_records"].values()))
    record["recent_evidence"] = [copy.deepcopy(full_evidence)]
    before = association_current_truth_summary(registry)

    normalised, _ = advance_association_registry(registry, [], people, 1)
    normalised_record = next(iter(normalised["association_records"].values()))
    assert association_current_truth_summary(normalised) == before
    assert normalised_record["recent_evidence"] == [{
        "evidence_id": full_evidence["evidence_id"],
        "category": full_evidence["category"],
        "tick": full_evidence["tick"],
        "source_event_ids": full_evidence["source_event_ids"],
        "condition_ids": full_evidence["condition_ids"],
    }]


def test_overlapping_clusters_remain_separate_and_deterministic():
    def run(reverse=False):
        people = ["person-a", "person-b", "person-c", "person-d", "person-e"]
        registry = None
        for tick in range(1, 4):
            observations = [
                _evidence(["person-a", "person-b"], "caregiving", tick, f"ab-{tick}"),
                _evidence(["person-a", "person-c"], "caregiving", tick, f"ac-{tick}"),
                _evidence(["person-b", "person-c"], "caregiving", tick, f"bc-{tick}"),
                _evidence(["person-c", "person-d"], "cooperation", tick, f"cd-{tick}"),
                _evidence(["person-c", "person-e"], "cooperation", tick, f"ce-{tick}"),
                _evidence(["person-d", "person-e"], "cooperation", tick, f"de-{tick}"),
            ]
            if reverse:
                observations.reverse()
            registry, _ = advance_association_registry(
                registry, observations, list(reversed(people)) if reverse else people, tick,
            )
        return registry

    first = run()
    second = run(reverse=True)
    assert first == second
    member_sets = {tuple(candidate["member_ids"]) for candidate in first["group_candidates"].values()}
    assert ("person-a", "person-b", "person-c") in member_sets
    assert ("person-c", "person-d", "person-e") in member_sets
    assert ("person-a", "person-b", "person-c", "person-d", "person-e") not in member_sets


def test_accepted_actions_derive_weighted_categories_and_projection_explanations():
    entities = _entities("person-a", "person-b", "person-c")
    entities["person-a"]["action"] = {
        "type": "help",
        "actor_id": "person-a",
        "participants": ["person-b"],
        "accepted_event_id": "evt-help",
        "action_id": "action-help",
        "started_tick": 1,
    }
    observations = derive_association_evidence(entities, 2)
    caregiving = [item for item in observations if item["category"] == "caregiving"]
    assert len(caregiving) == 1
    assert caregiving[0]["source_event_ids"] == ["evt-help"]

    recognised, _events, _order = _run_pair("caregiving", 3)
    registry = recognised[ASSOCIATION_REGISTRY_ID]
    projection = build_association_projection(
        registry, people=["person-a", "person-b", "person-c"],
    )
    group = projection["groups"][0]
    assert group["formation_evidence"]["decisive_event_ids"]
    assert {row["person_id"] for row in group["member_explanations"]} == {"person-a", "person-b"}
    assert group["excluded_people"] == [{
        "person_id": "person-c",
        "reason": "missing_qualifying_complete_link",
        "missing_member_ids": ["person-a", "person-b"],
    }]


def test_stage7a_scenario_extends_without_changing_stage6_activation():
    stage6 = get_scenario("living_settlement")
    stage7a = get_scenario("emergent_groups")
    assert "association" not in stage6.enabled_domains
    assert stage7a.enabled_domains == [*stage6.enabled_domains, "association"]
    assert stage7a.world_gen == stage6.world_gen
    assert stage7a.presentation["capability_stage"] == "7A"


def test_integrated_stage7a_kernel_creates_bounded_replayable_groups():
    first = run_living_agent_harness(
        "stage7a-focused-integration", ticks=8, scenario_id="emergent_groups",
    )
    second = run_living_agent_harness(
        "stage7a-focused-integration", ticks=8, run_id="stage7a-repeat",
        scenario_id="emergent_groups",
    )
    summary = first["summary"]
    assert summary["accepted_by_type"]["update_association_registry"] == 8
    assert summary["final_association_record_count"] > 0
    assert summary["final_group_candidate_count"] > 0
    assert summary["max_state_counts"]["association_records"] <= LIMITS.records
    assert summary["max_state_counts"]["group_candidates"] <= LIMITS.candidates
    assert summary["max_state_counts"]["dissolved_groups"] <= LIMITS.dissolved_history
    assert summary["max_state_counts"]["association_registry_bytes"] <= LIMITS.proposal_bytes
    assert first["event_hashes"] == second["event_hashes"]
    assert first["frame_hashes"] == second["frame_hashes"]
    assert first["final_state_hash"] == second["final_state_hash"]
    assert summary["association_summary_hash"] == second["summary"]["association_summary_hash"]
