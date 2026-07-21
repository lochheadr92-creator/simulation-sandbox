"""Capability Stage 7B shared-group state and collective proposal tests."""
from __future__ import annotations

import copy

from api.group_state_projection import build_group_state_projection
from core.commit_pipeline import run_commit_frame
from core.hashing import canonical_hash, canonical_json
from core.mutations import apply_mutation, snapshot_for_hash
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    RECOGNISED_DISSOLUTION_TICKS,
    build_association_proposal,
    make_association_evidence,
)
from domains.base import DomainOutput
from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_ID,
    LIMITS,
    advance_group_state_registry,
    build_group_state_proposal,
    collective_proposal_key,
    derive_group_support_evidence,
    group_state_capacity_diagnostics,
    group_state_current_truth_summary,
    make_group_support_evidence,
    shared_group_fact_id,
    stamp_group_state_provenance,
)
from scenarios import get_scenario
from tools.living_agent_harness import run_living_agent_harness


def _person(entity_id: str, x: int = 0, y: int = 0) -> dict:
    return {
        "type": "person",
        "alive": True,
        "position": {"x": x, "y": y},
        "last_event_id": f"evt-genesis-{entity_id}",
        "action": {
            "type": "idle",
            "status": "completed",
            "started_tick": 0,
        },
    }


def _base_entities(*person_ids: str) -> dict:
    entities = {
        person_id: _person(person_id, index, 0)
        for index, person_id in enumerate(person_ids)
    }
    entities["shelter-camp"] = {
        "type": "shelter",
        "position": {"x": 0, "y": 0},
        "access": "shared",
        "condition": 900,
        "last_event_id": "evt-0-shelter",
    }
    entities["storage-camp"] = {
        "type": "storage",
        "position": {"x": 0, "y": 1},
        "access": "shared",
        "contents": {"food": 2},
        "capacity": 10,
        "last_event_id": "evt-0-storage",
    }
    return entities


def _support_evidence(pair=("person-a", "person-b"), tick: int = 1,
                      *, category: str = "shared_shelter",
                      target_id: str = "shelter-camp") -> dict:
    return make_association_evidence(
        list(pair),
        category,
        tick,
        [f"evt-{pair[0]}-{tick}", f"evt-{pair[1]}-{tick}", f"evt-0-{target_id}"],
        condition_ids=[target_id],
    )


def _commit_association(entities: dict, tick: int, observations: list[dict], order: int = 0):
    proposal = build_association_proposal(entities, tick, observations=observations)
    assert proposal is not None
    accepted, rejected, next_order = run_commit_frame(
        entities,
        [DomainOutput(proposals=[proposal])],
        tick,
        "stage7b-test-lineage",
        "stage7b-test-run",
        order,
        f"frame-association-{tick}",
    )
    assert not rejected
    assert len(accepted) == 1
    return accepted, next_order


def _recognised_entities(category: str = "shared_shelter", people=("person-a", "person-b")):
    entities = _base_entities(*people, "person-c")
    events = []
    order = 0
    for tick in range(1, 4):
        accepted, order = _commit_association(
            entities, tick, [_support_evidence(people, tick, category=category)], order,
        )
        events.extend(copy.deepcopy(accepted))
    return entities, events, order


def _candidate_entities():
    entities = _base_entities("person-a", "person-b", "person-c")
    events = []
    order = 0
    for tick in range(1, 3):
        accepted, order = _commit_association(
            entities, tick, [_support_evidence(("person-a", "person-b"), tick)], order,
        )
        events.extend(copy.deepcopy(accepted))
    return entities, events, order


def _group_id(entities: dict) -> str:
    groups = entities[ASSOCIATION_REGISTRY_ID]["group_candidates"]
    assert groups
    return sorted(groups)[0]


def _latest_support(entities: dict, tick: int = 4) -> dict:
    supports = derive_group_support_evidence(entities, tick)
    assert supports
    return supports[0]


def _commit_group_state(entities: dict, tick: int, order: int = 0):
    proposal = build_group_state_proposal(entities, tick)
    assert proposal is not None
    accepted, rejected, next_order = run_commit_frame(
        entities,
        [DomainOutput(proposals=[proposal])],
        tick,
        "stage7b-test-lineage",
        "stage7b-test-run",
        order,
        f"frame-group-state-{tick}",
    )
    assert not rejected
    assert len(accepted) == 1
    return accepted, next_order


def _run_reject(entities: dict, proposal: dict, tick: int = 4):
    before = copy.deepcopy(entities)
    accepted, rejected, _order = run_commit_frame(
        entities,
        [DomainOutput(proposals=[proposal])],
        tick,
        "stage7b-test-lineage",
        "stage7b-test-run",
        0,
        f"frame-reject-{tick}",
    )
    assert not accepted
    assert rejected
    assert entities == before
    return rejected[0]["reason_code"]


def _capacity_pressure_fixture() -> tuple[dict, list[dict]]:
    association = {
        "schema_version": "association-registry-v1",
        "revision": 1,
        "group_candidates": {},
    }
    supports = []
    for group_index in range(7):
        group_id = f"group-capacity-{group_index:02d}"
        association["group_candidates"][group_id] = {
            "schema_version": "group-candidate-v1",
            "candidate_id": group_id,
            "group_type": "household_like",
            "recognition_state": "recognised",
            "ever_recognised": True,
            "member_ids": ["person-a", "person-b"],
            "recognised_tick": 1,
            "recognition_event_id": f"evt-recognised-{group_index}",
        }
        for category, target_prefix in (
            ("shared_shelter", "shelter"),
            ("shared_storage", "storage"),
        ):
            target_id = f"{target_prefix}-capacity-{group_index:02d}"
            for support_index in range(12):
                supports.append(make_group_support_evidence(
                    group_id=group_id,
                    category=category,
                    target_id=target_id,
                    participant_ids=["person-a", "person-b"],
                    tick=support_index + 1,
                    support_event_ids=[
                        f"evt-a-{group_index}-{category}-{support_index}",
                        f"evt-b-{group_index}-{category}-{support_index}",
                    ],
                    support_evidence_ids=[
                        f"assoc-evidence-{group_index}-{category}-{support_index}",
                    ],
                    association_record_ids=[f"association-{group_index}"],
                    association_registry_revision=1,
                    association_event_id="evt-association",
                ))
    return association, supports


def _support_from_association(entities: dict, group_id: str | None = None,
                              *, participant_ids=("person-a", "person-b"),
                              tick: int = 3, category: str = "shared_shelter",
                              target_id: str = "shelter-camp") -> dict:
    group_id = group_id or _group_id(entities)
    evidence = _support_evidence(participant_ids, tick, category=category, target_id=target_id)
    association = entities[ASSOCIATION_REGISTRY_ID]
    return make_group_support_evidence(
        group_id=group_id,
        category=category,
        target_id=target_id,
        participant_ids=list(participant_ids),
        tick=tick,
        support_event_ids=evidence["source_event_ids"],
        support_evidence_ids=[evidence["evidence_id"]],
        association_record_ids=[evidence["pair_id"]],
        association_registry_revision=int(association["revision"]),
        association_event_id=association.get("last_event_id"),
    )


def test_recognised_group_can_acquire_valid_shared_state_through_accepted_cause():
    entities, _events, order = _recognised_entities()
    accepted, _order = _commit_group_state(entities, 4, order)
    registry = entities[GROUP_STATE_REGISTRY_ID]
    assert accepted[0]["event_type"] == "update_group_shared_state"
    assert len(registry["groups"]) == 1
    group = registry["groups"][_group_id(entities)]
    fact = next(iter(group["facts"].values()))
    assert fact["category"] == "shared_shelter"
    assert fact["target_id"] == "shelter-camp"
    assert fact["created_event_id"] == accepted[0]["id"]


def test_unrecognised_group_cannot_acquire_shared_state():
    entities, _events, _order = _candidate_entities()
    group_id = _group_id(entities)
    support = _support_from_association(entities, group_id)
    proposal = build_group_state_proposal(entities, 4, supports=[support], filter_processed=False)
    assert _run_reject(entities, proposal) == "group_state.group_not_recognised"


def test_recognition_alone_does_not_create_shared_state():
    entities, _events, _order = _recognised_entities(category="caregiving")
    assert build_group_state_proposal(entities, 4) is None
    assert GROUP_STATE_REGISTRY_ID not in entities


def test_recognition_alone_cannot_authorise_collective_proposal():
    entities, _events, _order = _recognised_entities()
    proposal = build_group_state_proposal(entities, 4)
    proposal["group_state_update"]["support_items"] = []
    proposal["group_state_update"]["proposal_keys"] = []
    proposal["group_state_update"]["support_count"] = 0
    assert _run_reject(entities, proposal) == "group_state.missing_collective_support"


def test_valid_member_supported_collective_proposal_is_accepted():
    entities, _events, order = _recognised_entities()
    accepted, _order = _commit_group_state(entities, 4, order)
    assert accepted[0]["group_state_update"]["support_count"] >= 1
    projection = build_group_state_projection(entities[GROUP_STATE_REGISTRY_ID])
    assert projection["groups"][0]["facts"][0]["support_count"] >= 1
    assert projection["groups"][0]["facts"][0]["support_history"]


def test_non_member_support_is_rejected():
    entities, _events, _order = _recognised_entities()
    support = _support_from_association(
        entities, participant_ids=("person-a", "person-c"),
    )
    proposal = build_group_state_proposal(entities, 4, supports=[support], filter_processed=False)
    assert _run_reject(entities, proposal) == "group_state.non_member_support"


def test_stale_membership_revision_is_rejected():
    entities, _events, _order = _recognised_entities()
    proposal = build_group_state_proposal(entities, 4)
    entities[ASSOCIATION_REGISTRY_ID]["revision"] += 1
    assert _run_reject(entities, proposal) == "group_state.stale_membership"


def test_stale_support_is_rejected():
    entities, _events, _order = _recognised_entities()
    support = _support_from_association(entities)
    proposal = build_group_state_proposal(entities, 20, supports=[support], filter_processed=False)
    assert _run_reject(entities, proposal, tick=20) == "group_state.stale_support"


def test_dissolved_group_cannot_perform_new_collective_mutation():
    entities, _events, _order = _recognised_entities()
    group_id = _group_id(entities)
    candidate = entities[ASSOCIATION_REGISTRY_ID]["group_candidates"].pop(group_id)
    entities[ASSOCIATION_REGISTRY_ID]["dissolved_history"].append({
        "schema_version": candidate["schema_version"],
        "candidate_id": group_id,
        "founding_pair_id": candidate["founding_pair_id"],
        "group_type": candidate["group_type"],
        "final_member_ids": candidate["member_ids"],
        "final_state": "dissolved",
        "first_supported_tick": 1,
        "recognised_tick": candidate["recognised_tick"],
        "dissolved_tick": 4,
        "formation_event_ids": candidate["causal_event_ids"][:2],
        "dissolution_cause_event_ids": candidate["causal_event_ids"][:2],
    })
    support = _support_from_association(entities, group_id)
    proposal = build_group_state_proposal(entities, 4, supports=[support], filter_processed=False)
    assert _run_reject(entities, proposal) == "group_state.group_dissolved"


def test_one_member_cannot_silently_consent_for_another():
    entities, _events, _order = _recognised_entities()
    support = _latest_support(entities)
    support["support_event_ids"] = ["evt-person-a-3", "evt-0-shelter-camp"]
    support["proposal_key"] = collective_proposal_key(support)
    proposal = build_group_state_proposal(entities, 4, supports=[support], filter_processed=False)
    assert _run_reject(entities, proposal) == "group_state.invalid_participation"


def test_collective_proposal_cannot_mutate_unrelated_individual_state():
    entities, _events, _order = _recognised_entities()
    proposal = build_group_state_proposal(entities, 4)
    proposal["mutation"]["entity_updates"]["person-c"] = {"health": 1}
    proposal["touched_scope"].append("person-c")
    proposal["group_state_update"]["payload_bytes"] = len(
        canonical_json(proposal["mutation"]["new_entities"][GROUP_STATE_REGISTRY_ID]).encode("utf-8")
    )
    assert _run_reject(entities, proposal) == "group_state.invalid_mutation_scope"


def test_deterministic_collective_proposal_identity():
    entities, _events, _order = _recognised_entities()
    group_id = _group_id(entities)
    first = _support_from_association(entities, group_id, participant_ids=("person-a", "person-b"))
    second = make_group_support_evidence(
        group_id=group_id,
        category="shared_shelter",
        target_id="shelter-camp",
        participant_ids=["person-b", "person-a"],
        tick=3,
        support_event_ids=list(reversed(first["support_event_ids"])),
        support_evidence_ids=list(reversed(first["support_evidence_ids"])),
        association_record_ids=list(reversed(first["association_record_ids"])),
        association_registry_revision=first["association_registry_revision"],
        association_event_id=first["association_event_id"],
    )
    assert first["support_id"] == second["support_id"]
    assert first["proposal_key"] == second["proposal_key"]
    assert first["fact_id"] == second["fact_id"]


def test_duplicate_identical_proposal_does_not_duplicate_canonical_effect():
    entities, _events, _order = _recognised_entities()
    proposal = build_group_state_proposal(entities, 4)
    accepted, rejected, _next_order = run_commit_frame(
        entities,
        [DomainOutput(proposals=[copy.deepcopy(proposal), copy.deepcopy(proposal)])],
        4,
        "stage7b-test-lineage",
        "stage7b-test-run",
        0,
        "frame-dup",
    )
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["reason_code"] == "group_state.duplicate_registry"
    facts = next(iter(entities[GROUP_STATE_REGISTRY_ID]["groups"].values()))["facts"]
    assert len(facts) == 1


def test_expected_revision_conflict_rejection():
    entities, _events, order = _recognised_entities()
    _accepted, order = _commit_group_state(entities, 4, order)
    accepted, order = _commit_association(
        entities, 4, [_support_evidence(("person-a", "person-b"), 4)], order,
    )
    assert accepted
    proposal = build_group_state_proposal(entities, 5)
    entities[GROUP_STATE_REGISTRY_ID]["revision"] += 1
    assert _run_reject(entities, proposal, tick=5) == "group_state.invalid_revision"


def test_provenance_survives_acceptance():
    entities, _events, order = _recognised_entities()
    accepted, _order = _commit_group_state(entities, 4, order)
    event_id = accepted[0]["id"]
    registry = entities[GROUP_STATE_REGISTRY_ID]
    fact = next(iter(next(iter(registry["groups"].values()))["facts"].values()))
    proposal_row = next(iter(registry["groups"].values()))["latest_collective_proposals"][-1]
    assert accepted[0]["group_state_update"]["accepted_event_id"] == event_id
    assert fact["created_event_id"] == event_id
    assert fact["last_event_id"] == event_id
    assert proposal_row["accepted_event_id"] == event_id


def test_replay_reproduces_exact_shared_group_state():
    initial = _base_entities("person-a", "person-b", "person-c")
    entities = copy.deepcopy(initial)
    events = []
    order = 0
    for tick in range(1, 4):
        accepted, order = _commit_association(
            entities, tick, [_support_evidence(("person-a", "person-b"), tick)], order,
        )
        events.extend(copy.deepcopy(accepted))
    accepted, order = _commit_group_state(entities, 4, order)
    events.extend(copy.deepcopy(accepted))
    replayed = copy.deepcopy(initial)
    for event in events:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    assert replayed == entities
    assert canonical_hash(snapshot_for_hash(replayed, 4, "stage7b-test-lineage")) \
        == canonical_hash(snapshot_for_hash(entities, 4, "stage7b-test-lineage"))


def test_resume_reconstructs_exact_shared_group_state():
    uninterrupted, _events, order_a = _recognised_entities()
    resumed = copy.deepcopy(uninterrupted)
    order_b = order_a
    _accepted, order_a = _commit_group_state(uninterrupted, 4, order_a)
    _accepted, order_b = _commit_group_state(resumed, 4, order_b)
    resumed = copy.deepcopy(resumed)
    accepted, order_a = _commit_association(
        uninterrupted, 4, [_support_evidence(("person-a", "person-b"), 4)], order_a,
    )
    accepted, order_b = _commit_association(
        resumed, 4, [_support_evidence(("person-a", "person-b"), 4)], order_b,
    )
    assert accepted
    _accepted, order_a = _commit_group_state(uninterrupted, 5, order_a)
    _accepted, order_b = _commit_group_state(resumed, 5, order_b)
    assert resumed == uninterrupted
    assert order_b == order_a


def test_caps_and_deterministic_compaction_hold():
    association = {
        "schema_version": "association-registry-v1",
        "revision": 1,
        "group_candidates": {},
    }
    supports = []
    for index in range(40):
        group_id = f"group-{index:02d}"
        association["group_candidates"][group_id] = {
            "schema_version": "group-candidate-v1",
            "candidate_id": group_id,
            "group_type": "household_like",
            "recognition_state": "recognised",
            "ever_recognised": True,
            "member_ids": ["person-a", "person-b"],
            "recognised_tick": 1,
            "recognition_event_id": f"evt-rec-{index}",
        }
        supports.append(make_group_support_evidence(
            group_id=group_id,
            category="shared_shelter",
            target_id=f"shelter-{index:02d}",
            participant_ids=["person-a", "person-b"],
            tick=index + 1,
            support_event_ids=[f"evt-a-{index}", f"evt-b-{index}"],
            support_evidence_ids=[f"assoc-evidence-{index}"],
            association_record_ids=[f"association-{index}"],
            association_registry_revision=1,
            association_event_id="evt-association",
        ))
    first, _ = advance_group_state_registry(None, supports, association, 50)
    second, _ = advance_group_state_registry(None, list(reversed(supports)), association, 50)
    assert first == second
    assert len(first["groups"]) <= LIMITS.groups
    assert len(first["processed_proposal_keys"]) <= LIMITS.processed_proposal_keys
    assert len(canonical_json(first).encode("utf-8")) <= LIMITS.proposal_bytes


def test_capacity_compaction_preserves_truth_evidence_duplicates_and_order():
    association, supports = _capacity_pressure_fixture()
    first, _ = advance_group_state_registry(None, supports, association, 50)
    second, _ = advance_group_state_registry(None, list(reversed(supports)), association, 50)
    assert first == second

    facts = [
        fact
        for group in first["groups"].values()
        for fact in group["facts"].values()
    ]
    assert len(facts) == 14
    assert all(fact["support_count"] == 12 for fact in facts)
    assert all(len(fact["support_history"]) >= LIMITS.minimum_support_history_per_fact for fact in facts)
    assert all(fact["support_event_ids"] and fact["support_evidence_ids"] for fact in facts)
    assert all(
        len(group["latest_collective_proposals"])
        >= LIMITS.minimum_collective_proposals_retained
        for group in first["groups"].values()
    )
    assert sum(
        len(group["latest_collective_proposals"])
        for group in first["groups"].values()
    ) < 7 * LIMITS.collective_proposals_retained
    assert len(first["processed_proposal_keys"]) == LIMITS.processed_proposal_keys
    assert len(canonical_json(first).encode("utf-8")) <= LIMITS.payload_target_bytes

    composition = group_state_capacity_diagnostics(first)
    assert composition["total_serialized_bytes"] == sum(
        value for key, value in composition.items() if key != "total_serialized_bytes"
    )
    assert composition["retained_proposal_summary_bytes"] \
        < composition["historical_support_evidence_bytes"]

    support_by_key = {support["proposal_key"]: support for support in supports}
    duplicate = support_by_key[first["processed_proposal_keys"][-1]]
    current_truth = group_state_current_truth_summary(first)
    duplicate_result, transitions = advance_group_state_registry(
        first, [duplicate], association, 51,
    )
    assert not transitions
    assert group_state_current_truth_summary(duplicate_result) == current_truth


def test_compacted_registry_replays_and_resumes_with_stamped_provenance():
    association, supports = _capacity_pressure_fixture()
    midpoint = len(supports) // 2
    first, _ = advance_group_state_registry(None, supports[:midpoint], association, 50)
    first_mutation = {
        "new_entities": {GROUP_STATE_REGISTRY_ID: first},
        "entity_updates": {},
    }
    stamp_group_state_provenance({
        "requested_time": 50,
        "group_state_update": {
            "proposal_keys": [support["proposal_key"] for support in supports[:midpoint]],
        },
    }, first_mutation, "evt-capacity-first")

    final, _ = advance_group_state_registry(first, supports[midpoint:], association, 51)
    final_mutation = {
        "new_entities": {},
        "entity_updates": {GROUP_STATE_REGISTRY_ID: final},
    }
    stamp_group_state_provenance({
        "requested_time": 51,
        "group_state_update": {
            "proposal_keys": [support["proposal_key"] for support in supports[midpoint:]],
        },
    }, final_mutation, "evt-capacity-final")

    replayed = {}
    apply_mutation(replayed, copy.deepcopy(first_mutation))
    resumed = copy.deepcopy(replayed)
    apply_mutation(replayed, copy.deepcopy(final_mutation))
    apply_mutation(resumed, copy.deepcopy(final_mutation))
    expected = {GROUP_STATE_REGISTRY_ID: final}
    assert replayed == expected
    assert resumed == expected
    assert canonical_hash(replayed) == canonical_hash(resumed)
    provenance_ids = {
        fact["last_event_id"]
        for group in final["groups"].values()
        for fact in group["facts"].values()
    }
    assert provenance_ids <= {"evt-capacity-first", "evt-capacity-final"}
    assert "evt-capacity-final" in provenance_ids


def test_proposal_payload_ceiling_is_enforced():
    entities, _events, _order = _recognised_entities()
    proposal = build_group_state_proposal(entities, 4)
    registry = proposal["mutation"]["new_entities"][GROUP_STATE_REGISTRY_ID]
    registry["padding"] = "x" * (LIMITS.proposal_bytes + 1)
    proposal["group_state_update"]["payload_bytes"] = len(
        canonical_json(registry).encode("utf-8")
    )
    assert _run_reject(entities, proposal) == "group_state.payload_limit"


def test_stage7a_association_behaviour_remains_unchanged():
    stage6 = get_scenario("living_settlement")
    stage7a = get_scenario("emergent_groups")
    stage7b = get_scenario("collective_groups")
    assert "group_state" not in stage6.enabled_domains
    assert "group_state" not in stage7a.enabled_domains
    assert stage7b.enabled_domains == [
        *stage7a.enabled_domains, "group_state", "group_collective", "group_goal",
        "group_norm", "group_carriage",
    ]
    assert "group_collective" not in stage7a.enabled_domains
    result = run_living_agent_harness(
        "stage7a-unchanged-under-7b-tests", ticks=8, scenario_id="emergent_groups",
    )
    assert "update_group_shared_state" not in result["summary"]["accepted_by_type"]
    assert result["summary"]["final_shared_group_fact_count"] == 0


def test_stage6_scenario_behaviour_remains_unchanged():
    first = run_living_agent_harness(
        "stage6-unchanged-under-7b-tests", ticks=5, scenario_id="living_settlement",
    )
    second = run_living_agent_harness(
        "stage6-unchanged-under-7b-tests", ticks=5, run_id="stage6-repeat",
        scenario_id="living_settlement",
    )
    assert "association" not in get_scenario("living_settlement").enabled_domains
    assert "group_state" not in get_scenario("living_settlement").enabled_domains
    assert first["event_hashes"] == second["event_hashes"]
    assert first["frame_hashes"] == second["frame_hashes"]
    assert first["summary"]["final_shared_group_fact_count"] == 0


def test_invalid_stage7b_proposal_fails_without_partial_mutation():
    entities, _events, _order = _recognised_entities()
    support = _support_from_association(
        entities, participant_ids=("person-a", "person-c"),
    )
    proposal = build_group_state_proposal(entities, 4, supports=[support], filter_processed=False)
    before = copy.deepcopy(entities)
    reason = _run_reject(entities, proposal)
    assert reason == "group_state.non_member_support"
    assert GROUP_STATE_REGISTRY_ID not in entities
    assert entities == before


def test_integrated_stage7b_kernel_creates_bounded_replayable_group_state():
    first = run_living_agent_harness(
        "stage7b-focused-integration", ticks=12, scenario_id="collective_groups",
    )
    second = run_living_agent_harness(
        "stage7b-focused-integration", ticks=12, run_id="stage7b-repeat",
        scenario_id="collective_groups",
        resume_at_tick=6,
    )
    summary = first["summary"]
    assert summary["accepted_by_type"]["update_group_shared_state"] > 0
    assert summary["final_shared_group_state_count"] > 0
    assert summary["final_shared_group_fact_count"] > 0
    assert summary["max_state_counts"]["shared_group_states"] <= LIMITS.groups
    assert summary["max_state_counts"]["shared_group_facts"] <= LIMITS.groups * LIMITS.facts_per_group
    assert summary["max_state_counts"]["group_state_registry_bytes"] <= LIMITS.proposal_bytes
    assert first["event_hashes"] == second["event_hashes"]
    assert first["frame_hashes"] == second["frame_hashes"]
    assert first["final_state_hash"] == second["final_state_hash"]
    assert summary["group_state_summary_hash"] == second["summary"]["group_state_summary_hash"]
    assert summary["replay_matches_final_entities"] is True
    assert second["summary"]["replay_matches_final_entities"] is True
    for capacity in summary["capacity"].values():
        composition = capacity["peak_composition"]
        assert composition["total_serialized_bytes"] == sum(
            value for key, value in composition.items() if key != "total_serialized_bytes"
        )


def test_recognised_group_dissolution_boundary_for_future_stage():
    assert RECOGNISED_DISSOLUTION_TICKS >= 1
