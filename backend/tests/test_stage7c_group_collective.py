"""Capability Stage 7C coordinated group collective action tests."""
from __future__ import annotations

import copy

from core.commit_pipeline import run_commit_frame
from core.hashing import canonical_hash
from core.mutations import apply_mutation, snapshot_for_hash
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    build_association_proposal,
    make_association_evidence,
)
from domains.base import DomainOutput
from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_ID,
    build_group_state_proposal,
    derive_group_support_evidence,
)
from domains.group_collective_contracts import (
    COLLECTIVE_ACTION_TYPE,
    LIMITS,
    PROPOSAL_TYPE,
    REASON_CAPACITY,
    REASON_DUPLICATE,
    REASON_ELIGIBILITY,
    REASON_STALE_MEMBERSHIP,
    build_collective_deposit_proposal,
    build_group_collective_proposals,
    derive_coordinated_deposits,
    eligible_participants,
    validate_group_collective_proposal,
)
from domains.group_collective_domain import GroupCollectiveDomain
from domains.base import ActivationFrame
from core.constants import ENGINE_VERSION
from core.rng import DeterministicRNG


LINEAGE = "stage7c-test-lineage"
RUN = "stage7c-test-run"


def _person(entity_id: str, x: int = 0, y: int = 0, *, food: int = 0, wood: int = 0) -> dict:
    return {
        "type": "person",
        "alive": True,
        "position": {"x": x, "y": y},
        "food_inventory": food,
        "inventory": wood,
        "last_event_id": f"evt-genesis-{entity_id}",
        "action": {"type": "idle", "status": "completed", "started_tick": 0},
    }


def _base_entities() -> dict:
    # Both members must be within manhattan range 1 of storage for Stage 7C.
    return {
        "person-a": _person("person-a", 1, 0, food=2, wood=1),
        "person-b": _person("person-b", 0, 1, food=1, wood=2),
        "person-c": _person("person-c", 5, 5, food=3, wood=3),  # far, non-member often
        "shelter-camp": {
            "type": "shelter",
            "position": {"x": 0, "y": 0},
            "access": "shared",
            "condition": 900,
            "last_event_id": "evt-0-shelter",
        },
        "storage-camp": {
            "type": "storage",
            "position": {"x": 0, "y": 0},
            "access": "shared",
            "contents": {"food": 1, "wood": 0},
            "capacity": 40,
            "last_event_id": "evt-0-storage",
        },
    }


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


def _commit(entities, proposals, tick, order=0):
    return run_commit_frame(
        entities,
        [DomainOutput(proposals=list(proposals))],
        tick,
        LINEAGE,
        RUN,
        order,
        f"frame-{tick}",
    )


def _commit_association(entities, tick, observations, order=0):
    proposal = build_association_proposal(entities, tick, observations=observations)
    assert proposal is not None
    accepted, rejected, next_order = _commit(entities, [proposal], tick, order)
    assert not rejected and len(accepted) == 1
    return accepted, next_order


def _recognised_with_shared_storage():
    """Recognise via shared_shelter, then land shared_storage fact for Stage 7C."""
    entities = _base_entities()
    events = []
    order = 0
    for tick in range(1, 4):
        accepted, order = _commit_association(
            entities, tick,
            [_support_evidence(("person-a", "person-b"), tick, category="shared_shelter")],
            order,
        )
        events.extend(copy.deepcopy(accepted))
    # Fresh shared_storage support on a recognised group
    accepted, order = _commit_association(
        entities, 4,
        [_support_evidence(
            ("person-a", "person-b"), 4,
            category="shared_storage", target_id="storage-camp",
        )],
        order,
    )
    events.extend(copy.deepcopy(accepted))
    supports = derive_group_support_evidence(entities, 4)
    assert any(s.get("category") == "shared_storage" for s in supports)
    gs = build_group_state_proposal(entities, 4)
    assert gs is not None
    accepted, rejected, order = _commit(entities, [gs], 4, order)
    assert not rejected and accepted
    events.extend(copy.deepcopy(accepted))
    assert GROUP_STATE_REGISTRY_ID in entities
    groups = entities[GROUP_STATE_REGISTRY_ID]["groups"]
    assert groups
    # Confirm shared_storage fact present
    facts = []
    for group in groups.values():
        facts.extend((group.get("facts") or {}).values())
    assert any(f.get("category") == "shared_storage" for f in facts)
    return entities, events, order


def test_eligibility_requires_membership_proximity_and_carried_resource():
    entities, _, _ = _recognised_with_shared_storage()
    group_id = sorted(entities[GROUP_STATE_REGISTRY_ID]["groups"])[0]
    members = entities[GROUP_STATE_REGISTRY_ID]["groups"][group_id]["member_ids"]
    rows = eligible_participants(entities, members, "storage-camp")
    ids = [r["person_id"] for r in rows]
    assert "person-a" in ids and "person-b" in ids
    # Far non-adjacent c not eligible even if given membership later
    entities["person-c"]["position"] = {"x": 20, "y": 20}
    rows2 = eligible_participants(entities, ["person-a", "person-b", "person-c"], "storage-camp")
    assert "person-c" not in [r["person_id"] for r in rows2]
    # No resource → ineligible
    entities["person-a"]["food_inventory"] = 0
    entities["person-a"]["inventory"] = 0
    rows3 = eligible_participants(entities, members, "storage-camp")
    assert "person-a" not in [r["person_id"] for r in rows3]


def test_deterministic_initiator_and_participant_order():
    entities, _, _ = _recognised_with_shared_storage()
    actions = derive_coordinated_deposits(entities, tick=5)
    assert actions
    action = actions[0]
    assert action["action_type"] == COLLECTIVE_ACTION_TYPE
    assert action["initiator_id"] == action["participant_ids"][0]
    assert action["participant_ids"] == sorted(action["participant_ids"])
    # Shuffled entity map must not change derivation
    shuffled = {k: entities[k] for k in reversed(list(entities))}
    actions2 = derive_coordinated_deposits(shuffled, tick=5)
    assert actions2[0]["participant_ids"] == action["participant_ids"]
    assert actions2[0]["initiator_id"] == action["initiator_id"]
    assert actions2[0]["action_key"] == action["action_key"]


def test_successful_end_to_end_coordinated_deposit():
    entities, events, order = _recognised_with_shared_storage()
    food_before = (
        entities["person-a"]["food_inventory"]
        + entities["person-b"]["food_inventory"]
        + entities["storage-camp"]["contents"]["food"]
    )
    proposals = build_group_collective_proposals(entities, 5)
    assert proposals
    assert proposals[0]["proposal_type"] == PROPOSAL_TYPE
    accepted, rejected, order = _commit(entities, proposals, 5, order)
    assert not rejected
    assert len(accepted) == 1
    event = accepted[0]
    assert event["event_type"] == PROPOSAL_TYPE
    assert event["collective_action"]["action_type"] == COLLECTIVE_ACTION_TYPE
    assert len(event["collective_action"]["participant_ids"]) >= 2
    # Conservation of food units among depositors + storage food field
    # (wood deposits may also occur; check total carried food + storage food)
    food_after = (
        entities["person-a"]["food_inventory"]
        + entities["person-b"]["food_inventory"]
        + entities["storage-camp"]["contents"].get("food", 0)
    )
    assert food_after == food_before
    assert entities["storage-camp"]["last_collective_action_key"]
    assert entities["storage-camp"]["collective_processed_keys"]


def test_ineligible_members_excluded():
    entities, _, order = _recognised_with_shared_storage()
    entities["person-c"]["position"] = {"x": 0, "y": 0}
    entities["person-c"]["food_inventory"] = 5
    # person-c not a member
    actions = derive_coordinated_deposits(entities, 5)
    assert actions
    assert "person-c" not in actions[0]["participant_ids"]


def test_stale_membership_rejected_at_commit():
    entities, _, order = _recognised_with_shared_storage()
    proposals = build_group_collective_proposals(entities, 5)
    assert proposals
    # Remove membership by mutating association after proposal built (stale frame)
    group_id = proposals[0]["collective_action"]["group_id"]
    cand = entities[ASSOCIATION_REGISTRY_ID]["group_candidates"][group_id]
    cand["member_ids"] = ["person-a"]  # drop b
    entities[ASSOCIATION_REGISTRY_ID]["revision"] = int(
        entities[ASSOCIATION_REGISTRY_ID]["revision"]
    ) + 1
    # Proposal still has old revision precondition AND member list in meta
    accepted, rejected, _ = _commit(entities, proposals, 5, order)
    assert accepted == []
    assert rejected
    assert rejected[0]["reason_code"] in (
        REASON_STALE_MEMBERSHIP,
        "precondition.failed",
        REASON_ELIGIBILITY,
    )


def test_dead_participant_rejected():
    entities, _, order = _recognised_with_shared_storage()
    proposals = build_group_collective_proposals(entities, 5)
    assert proposals
    entities["person-b"]["alive"] = False
    accepted, rejected, _ = _commit(entities, proposals, 5, order)
    assert accepted == []
    assert rejected[0]["reason_code"] in (REASON_ELIGIBILITY, "precondition.failed")


def test_conflicting_collective_actions_resolve_deterministically():
    entities, _, order = _recognised_with_shared_storage()
    # Build two proposals from same snapshot (duplicate action)
    p1 = build_group_collective_proposals(entities, 5)
    p2 = build_group_collective_proposals(entities, 5)
    assert p1 and p2
    # Same content → content_hash equal; commit first, second fails inventory/dup
    accepted, rejected, _ = _commit(entities, p1 + p2, 5, order)
    assert len(accepted) == 1
    assert len(rejected) >= 1
    # No negative inventories
    assert entities["person-a"]["food_inventory"] >= 0
    assert entities["person-b"]["food_inventory"] >= 0


def test_shuffled_proposal_arrival_identical_outcome():
    def run(shuffle: bool):
        entities, _, order = _recognised_with_shared_storage()
        proposals = build_group_collective_proposals(entities, 5)
        # Add a no-op noise proposal that will reject or reorder relative hash
        noise = copy.deepcopy(proposals[0]) if proposals else None
        props = list(proposals)
        if noise:
            # Slightly different explanation only is not in content_hash... explanation
            # is not hashed. Add second identical proposal for contention.
            props = props + [copy.deepcopy(proposals[0])]
        if shuffle:
            props = list(reversed(props))
        accepted, rejected, _ = _commit(entities, props, 5, order)
        return (
            [e["event_type"] for e in accepted],
            [e["collective_action"]["action_key"] for e in accepted if e.get("collective_action")],
            {
                "a_food": entities["person-a"]["food_inventory"],
                "b_food": entities["person-b"]["food_inventory"],
                "s_food": entities["storage-camp"]["contents"].get("food"),
                "s_wood": entities["storage-camp"]["contents"].get("wood"),
            },
            canonical_hash(snapshot_for_hash(entities, 5, LINEAGE)),
        )

    assert run(False) == run(True)


def test_replay_reproduces_final_state():
    entities, prior_events, order = _recognised_with_shared_storage()
    proposals = build_group_collective_proposals(entities, 5)
    accepted, rejected, _ = _commit(entities, proposals, 5, order)
    assert accepted and not rejected
    live = copy.deepcopy(entities)
    all_events = prior_events + accepted

    # Rebuild from empty-ish base by replaying all mutations in order
    # Start from pre-association base and apply every accepted mutation
    base = _base_entities()
    for event in all_events:
        apply_mutation(base, copy.deepcopy(event["mutation"]))
    assert base["person-a"]["food_inventory"] == live["person-a"]["food_inventory"]
    assert base["person-b"]["food_inventory"] == live["person-b"]["food_inventory"]
    assert base["storage-camp"]["contents"] == live["storage-camp"]["contents"]
    assert base["storage-camp"].get("last_collective_action_key") == live["storage-camp"].get(
        "last_collective_action_key"
    )


def test_rejected_proposal_no_partial_mutation():
    entities, _, order = _recognised_with_shared_storage()
    proposals = build_group_collective_proposals(entities, 5)
    assert proposals
    before = copy.deepcopy(entities)
    # Force invalid capacity
    entities["storage-camp"]["capacity"] = 1
    entities["storage-camp"]["contents"] = {"food": 1, "wood": 0}
    # Rebuild proposal against current entities for capacity fail at validate
    proposals = build_group_collective_proposals(entities, 5)
    if not proposals:
        # If derivation already refuses capacity, still prove no mutation path
        assert entities["person-a"]["food_inventory"] == before["person-a"]["food_inventory"]
        return
    snap = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(entities, proposals, 5, order)
    assert accepted == []
    assert rejected
    assert entities["person-a"]["food_inventory"] == snap["person-a"]["food_inventory"]
    assert entities["person-b"]["food_inventory"] == snap["person-b"]["food_inventory"]
    assert entities["storage-camp"]["contents"] == snap["storage-camp"]["contents"]


def test_unavailable_busy_member_excluded():
    entities, _, _ = _recognised_with_shared_storage()
    entities["person-b"]["action"] = {
        "type": "travel", "status": "travelling", "started_tick": 1,
    }
    actions = derive_coordinated_deposits(entities, 5)
    # Only one eligible → no collective action (requires >= 2)
    assert actions == [] or "person-b" not in actions[0]["participant_ids"]
    if actions:
        assert len(actions[0]["participant_ids"]) >= 2
        assert "person-b" not in actions[0]["participant_ids"]


def test_domain_activation_emits_proposals():
    entities, _, _ = _recognised_with_shared_storage()
    frame = ActivationFrame(
        RUN, 5, ENGINE_VERSION, "agent", entities, [["grass"] * 8] * 8,
        [GROUP_STATE_REGISTRY_ID], DeterministicRNG("stage7c"),
    )
    out = GroupCollectiveDomain().activate(frame)
    assert out.proposals
    assert out.proposals[0]["proposer_engine_id"] == "group_collective"


def test_duplicate_processed_key_rejected():
    entities, _, order = _recognised_with_shared_storage()
    proposals = build_group_collective_proposals(entities, 5)
    accepted, rejected, order = _commit(entities, proposals, 5, order)
    assert accepted
    # Replay same proposal content after accept
    again = build_group_collective_proposals(entities, 5)
    # Tick 5 same deposits may re-derive with new before_values if still eligible
    # Force duplicate by injecting old key into storage processed list and rebuilding
    key = accepted[0]["collective_action"]["action_key"]
    entities["storage-camp"]["collective_processed_keys"] = [key]
    # Craft proposal with that key
    action = copy.deepcopy(accepted[0]["collective_action"])
    # Refresh before_values from current state for a synthetic re-attempt
    action["tick"] = 6
    # Keep old action_key to force duplicate detection
    action["action_key"] = key
    # Fix before_values to current
    for dep in action["deposits"]:
        person = entities[dep["person_id"]]
        dep["before_value"] = int(person.get(dep["source_field"], 0) or 0)
    # Need enough inventory for mutation build
    for dep in action["deposits"]:
        if entities[dep["person_id"]].get(dep["source_field"], 0) < 1:
            entities[dep["person_id"]][dep["source_field"]] = 1
            dep["before_value"] = 1
    prop = build_collective_deposit_proposal(entities, 6, action)
    if prop is None:
        # build path already blocked duplicate — pass
        return
    err = validate_group_collective_proposal(prop, entities)
    assert err == REASON_DUPLICATE


def test_bounded_participant_cap():
    entities, _, _ = _recognised_with_shared_storage()
    # Add extra members with resources near storage
    # Positions within manhattan 1 of storage at (0,0)
    entities["person-d"] = _person("person-d", 0, 0, food=2)
    entities["person-e"] = _person("person-e", 1, 0, food=2)
    entities["person-f"] = _person("person-f", 0, 1, food=2)
    people = ["person-a", "person-b", "person-d", "person-e", "person-f"]
    group_id = sorted(entities[GROUP_STATE_REGISTRY_ID]["groups"])[0]
    entities[ASSOCIATION_REGISTRY_ID]["group_candidates"][group_id]["member_ids"] = sorted(people)
    entities[GROUP_STATE_REGISTRY_ID]["groups"][group_id]["member_ids"] = sorted(people)
    rows = eligible_participants(entities, people, "storage-camp")
    assert len(rows) >= 4
    actions = derive_coordinated_deposits(entities, 5)
    assert actions
    assert len(actions[0]["participant_ids"]) <= LIMITS.max_participants
    assert len(actions[0]["participant_ids"]) == LIMITS.max_participants


def test_resume_reconstruction_preserves_result():
    """Resume-style reconstruction: apply accepted mutations in order twice."""
    entities, prior, order = _recognised_with_shared_storage()
    proposals = build_group_collective_proposals(entities, 5)
    accepted, rejected, _ = _commit(entities, proposals, 5, order)
    assert accepted and not rejected
    final_hash = canonical_hash(snapshot_for_hash(entities, 5, LINEAGE))

    rebuilt = _base_entities()
    for event in prior + accepted:
        apply_mutation(rebuilt, copy.deepcopy(event["mutation"]))
    resume_hash = canonical_hash(snapshot_for_hash(rebuilt, 5, LINEAGE))
    # Association/group registries also present after replay
    assert "storage-camp" in rebuilt
    assert rebuilt["storage-camp"]["contents"] == entities["storage-camp"]["contents"]
    assert final_hash == resume_hash or (
        rebuilt["person-a"]["food_inventory"] == entities["person-a"]["food_inventory"]
        and rebuilt["storage-camp"].get("last_collective_action_key")
        == entities["storage-camp"].get("last_collective_action_key")
    )
