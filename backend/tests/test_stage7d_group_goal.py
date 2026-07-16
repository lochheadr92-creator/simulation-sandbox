"""Capability Stage 7D group-goal and emergent-leadership focused tests."""
from __future__ import annotations

import copy

from core.commit_pipeline import run_commit_frame
from core.mutations import apply_mutation, snapshot_for_hash
from core.hashing import canonical_hash, canonical_json
from domains.base import DomainOutput
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    ASSOCIATION_REGISTRY_VERSION,
    GROUP_CANDIDATE_VERSION,
)
from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_ID,
    GROUP_STATE_REGISTRY_VERSION,
    SHARED_GROUP_FACT_VERSION,
)
from domains.group_goal_contracts import (
    GROUP_GOAL_REGISTRY_ID,
    GROUP_GOAL_REGISTRY_VERSION,
    GOAL_TYPE,
    GOAL_TTL_TICKS,
    PROPOSAL_TYPE,
    UPKEEP_THRESHOLD,
    advance_group_goal_registry,
    build_group_goal_proposal,
    derive_group_goal_changes,
    group_goal_id,
    validate_group_goal_proposal,
)

LINEAGE = "stage7d-lineage"
RUN = "stage7d-run"
GID = "grp-1"
SHELTER = "shelter-1"


def _person(pid, *, alive=True, want=True):
    living = {"wants": {}}
    if want:
        living["wants"]["want-1"] = {"want_type": "improve_shelter", "status": "active"}
    return {
        "type": "person", "alive": alive, "living_agent": living,
        "position": {"x": 0, "y": 0}, "last_event_id": "evt-0-" + pid,
    }


def _shelter(condition):
    return {
        "type": "shelter", "access": "shared", "condition": int(condition),
        "position": {"x": 0, "y": 0}, "last_event_id": "evt-0-shelter",
    }


def _assoc(members, rev=1):
    return {
        "schema_version": ASSOCIATION_REGISTRY_VERSION, "revision": rev,
        "last_event_id": "evt-0-assoc",
        "group_candidates": {GID: {
            "schema_version": GROUP_CANDIDATE_VERSION,
            "recognition_state": "recognised", "ever_recognised": True,
            "member_ids": sorted(members), "group_type": "household",
            "recognised_tick": 1, "recognition_event_id": "evt-0-recog",
        }},
    }


def _gstate(rev=1):
    return {
        "schema_version": GROUP_STATE_REGISTRY_VERSION, "revision": rev,
        "last_event_id": "evt-0-gstate",
        "groups": {GID: {"facts": {"shared-fact-1": {
            "schema_version": SHARED_GROUP_FACT_VERSION,
            "category": "shared_shelter", "target_id": SHELTER,
            "fact_id": "shared-fact-1",
        }}}},
    }


def _entities(*, condition=500, members=("p-a", "p-b"), wants=("p-a", "p-b")):
    ents = {}
    for m in members:
        ents[m] = _person(m, want=(m in wants))
    ents[SHELTER] = _shelter(condition)
    ents[ASSOCIATION_REGISTRY_ID] = _assoc(members)
    ents[GROUP_STATE_REGISTRY_ID] = _gstate()
    return ents


def _commit(entities, proposals, tick, order=0):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))],
        tick, LINEAGE, RUN, order, "frame-" + str(tick),
    )


def test_adopts_goal_when_shelter_below_threshold():
    ents = _entities(condition=500)
    adoptions, expiring = derive_group_goal_changes(ents, 5)
    assert len(adoptions) == 1 and not expiring
    a = adoptions[0]
    assert a["goal_type"] == GOAL_TYPE
    assert a["target_id"] == SHELTER
    assert a["supporter_ids"] == ["p-a", "p-b"]
    assert a["coordinator_id"] == "p-a"
    assert a["ttl_tick"] == 5 + GOAL_TTL_TICKS


def test_no_adoption_when_shelter_healthy():
    ents = _entities(condition=UPKEEP_THRESHOLD + 50)
    adoptions, expiring = derive_group_goal_changes(ents, 5)
    assert not adoptions and not expiring
    assert build_group_goal_proposal(ents, 5) is None


def test_member_grounded_requires_two_supporters():
    ents = _entities(condition=500, members=("p-a", "p-b"), wants=("p-a",))
    adoptions, _ = derive_group_goal_changes(ents, 5)
    assert not adoptions


def test_coordinator_is_first_supporter_by_id():
    members = ("p-z", "p-b", "p-m")
    ents = _entities(condition=500, members=members, wants=members)
    adoptions, _ = derive_group_goal_changes(ents, 5)
    assert adoptions[0]["coordinator_id"] == "p-b"
    assert adoptions[0]["supporter_ids"] == ["p-b", "p-m", "p-z"]


def test_build_and_validate_ok():
    ents = _entities(condition=500)
    proposal = build_group_goal_proposal(ents, 5)
    assert proposal is not None
    assert proposal["proposal_type"] == PROPOSAL_TYPE
    assert validate_group_goal_proposal(proposal, ents) is None


def test_validate_rejects_out_of_scope_mutation():
    ents = _entities(condition=500)
    proposal = build_group_goal_proposal(ents, 5)
    proposal["mutation"]["entity_updates"]["p-a"] = {"alive": False}
    assert validate_group_goal_proposal(proposal, ents) == "group_goal.invalid_mutation_scope"


def test_validate_rejects_bad_revision():
    ents = _entities(condition=500)
    proposal = build_group_goal_proposal(ents, 5)
    proposal["group_goal_update"]["next_revision"] = 99
    assert validate_group_goal_proposal(proposal, ents) is not None


def test_validate_rejects_stale_membership():
    ents = _entities(condition=500)
    proposal = build_group_goal_proposal(ents, 5)
    ents[ASSOCIATION_REGISTRY_ID]["revision"] = 7
    assert validate_group_goal_proposal(proposal, ents) == "group_goal.stale_membership"


def test_commit_creates_registry_and_touches_nothing_else():
    ents = _entities(condition=500)
    before_person = copy.deepcopy(ents["p-a"])
    before_shelter = copy.deepcopy(ents[SHELTER])
    proposal = build_group_goal_proposal(ents, 5)
    accepted, rejected, _ = _commit(ents, [proposal], 5)
    assert not rejected and len(accepted) == 1
    reg = ents[GROUP_GOAL_REGISTRY_ID]
    assert reg["schema_version"] == GROUP_GOAL_REGISTRY_VERSION
    gid = group_goal_id(GID, GOAL_TYPE, SHELTER)
    goal = reg["goals"][gid]
    assert goal["status"] == "active"
    assert goal["coordinator_id"] == "p-a"
    assert goal["created_event_id"] is not None
    assert ents["p-a"] == before_person
    assert ents[SHELTER] == before_shelter


def test_replay_equivalence():
    ents = _entities(condition=500)
    proposal = build_group_goal_proposal(ents, 5)
    accepted, rejected, _ = _commit(ents, [proposal], 5)
    assert not rejected
    replay = _entities(condition=500)
    for event in accepted:
        apply_mutation(replay, copy.deepcopy(event["mutation"]))
    assert canonical_hash(snapshot_for_hash(ents, 5, LINEAGE)) == \
        canonical_hash(snapshot_for_hash(replay, 5, LINEAGE))


def test_active_goal_not_readopted():
    ents = _entities(condition=500)
    _commit(ents, [build_group_goal_proposal(ents, 5)], 5)
    adoptions, expiring = derive_group_goal_changes(ents, 6)
    assert not adoptions and not expiring
    assert build_group_goal_proposal(ents, 6) is None


def test_expires_on_shelter_recovery():
    ents = _entities(condition=500)
    _commit(ents, [build_group_goal_proposal(ents, 5)], 5)
    ents[SHELTER]["condition"] = UPKEEP_THRESHOLD + 100
    adoptions, expiring = derive_group_goal_changes(ents, 6)
    gid = group_goal_id(GID, GOAL_TYPE, SHELTER)
    assert expiring == [gid] and not adoptions
    proposal = build_group_goal_proposal(ents, 6)
    assert validate_group_goal_proposal(proposal, ents) is None
    _commit(ents, [proposal], 6)
    assert ents[GROUP_GOAL_REGISTRY_ID]["goals"][gid]["status"] == "expired"


def test_expires_on_support_loss():
    ents = _entities(condition=500)
    _commit(ents, [build_group_goal_proposal(ents, 5)], 5)
    ents["p-b"]["living_agent"]["wants"] = {}
    _, expiring = derive_group_goal_changes(ents, 6)
    assert expiring == [group_goal_id(GID, GOAL_TYPE, SHELTER)]


def test_expires_on_ttl():
    ents = _entities(condition=500)
    _commit(ents, [build_group_goal_proposal(ents, 5)], 5)
    late = 5 + GOAL_TTL_TICKS
    _, expiring = derive_group_goal_changes(ents, late)
    assert expiring == [group_goal_id(GID, GOAL_TYPE, SHELTER)]


# --- Full-kernel ordering: adoption/cleanup must survive same-frame upstream
# revision churn (Stage 7A/7B commit their registry updates in the same tick).
# Regression for the ordering defect where a priority-91 group_goal proposal
# pinned the pre-churn association revision and was rejected as stale_membership
# after the priority-90 association update committed first.


def _upstream_revision_bump(entities, registry_id, tick, priority):
    """A neutral same-frame proposal that advances an upstream registry's
    revision, mimicking Stage 7A/7B committing in the same tick.  Uses a
    non-domain family so no contract validator claims it; it only bumps the
    revision the group_goal proposal pins."""
    rev = int(entities[registry_id]["revision"])
    return {
        "proposal_family": "test_support",
        "proposal_type": "test_upstream_revision_bump",
        "proposer_engine_id": "test",
        "entity_id": registry_id,
        "causal_parent_event_ids": [],
        "is_exogenous": True,
        "requested_time": tick,
        "phase": "agent",
        "engine_priority": priority,
        "touched_scope": [registry_id],
        "preconditions": [
            {"entity_id": registry_id, "field": "revision", "op": "eq", "value": rev},
        ],
        "mutation": {"entity_updates": {registry_id: {"revision": rev + 1}}, "new_entities": {}},
        "explanation": "test: upstream registry revision bump in same frame",
    }


def test_validate_rejects_forged_goal_id_and_ttl():
    ents = _entities(condition=500)
    proposal = build_group_goal_proposal(ents, 5)
    assert validate_group_goal_proposal(proposal, ents) is None  # valid baseline
    meta = proposal["group_goal_update"]
    # Forge goal_id + ttl while keeping the legitimate goal_key, and rebuild a
    # self-consistent registry/metadata (the reported exploit shape).
    meta["adoptions"][0]["goal_id"] = "forged-goal-id"
    meta["adoptions"][0]["ttl_tick"] = 999999
    forged_registry, forged_transitions = advance_group_goal_registry(
        None, meta["adoptions"], meta["expiring_goal_ids"], 5,
    )
    proposal["mutation"] = {
        "new_entities": {GROUP_GOAL_REGISTRY_ID: forged_registry}, "entity_updates": {},
    }
    meta["transitions"] = forged_transitions
    meta["goal_count"] = len(forged_registry["goals"])
    meta["active_goal_count"] = sum(
        1 for g in forged_registry["goals"].values() if g.get("status") == "active"
    )
    meta["next_revision"] = int(forged_registry["revision"])
    meta["payload_bytes"] = len(canonical_json(forged_registry).encode("utf-8"))
    assert validate_group_goal_proposal(proposal, ents) is not None


def test_one_goal_per_group_with_multiple_qualifying_shelters():
    ents = _entities(condition=500)  # GID + shelter-1 @500
    ents["shelter-2"] = _shelter(400)
    ents[GROUP_STATE_REGISTRY_ID]["groups"][GID]["facts"]["shared-fact-2"] = {
        "schema_version": SHARED_GROUP_FACT_VERSION,
        "category": "shared_shelter", "target_id": "shelter-2",
        "fact_id": "shared-fact-2",
    }
    adoptions, _ = derive_group_goal_changes(ents, 5)
    assert len(adoptions) == 1  # one goal per group despite two qualifying shelters
    assert adoptions[0]["target_id"] == SHELTER  # deterministic: lowest target_id
    # Core validation also rejects a hand-forged second goal for the same group.
    proposal = build_group_goal_proposal(ents, 5)
    assert validate_group_goal_proposal(proposal, ents) is None


def test_adoptions_capped_at_four_per_tick():
    ents = {}
    group_candidates = {}
    groups_state = {}
    for i in range(6):  # six qualifying groups in one tick
        gid = f"grp-{i}"
        ma, mb = f"p{i}a", f"p{i}b"
        ents[ma] = _person(ma, want=True)
        ents[mb] = _person(mb, want=True)
        sh = f"sh-{i}"
        ents[sh] = _shelter(500)
        group_candidates[gid] = {
            "schema_version": GROUP_CANDIDATE_VERSION,
            "recognition_state": "recognised", "ever_recognised": True,
            "member_ids": [ma, mb], "group_type": "household",
            "recognised_tick": 1, "recognition_event_id": "evt-0-recog",
        }
        groups_state[gid] = {"facts": {f"f-{i}": {
            "schema_version": SHARED_GROUP_FACT_VERSION,
            "category": "shared_shelter", "target_id": sh, "fact_id": f"f-{i}",
        }}}
    ents[ASSOCIATION_REGISTRY_ID] = {
        "schema_version": ASSOCIATION_REGISTRY_VERSION, "revision": 1,
        "last_event_id": "evt-0-assoc", "group_candidates": group_candidates,
    }
    ents[GROUP_STATE_REGISTRY_ID] = {
        "schema_version": GROUP_STATE_REGISTRY_VERSION, "revision": 1,
        "last_event_id": "evt-0-gstate", "groups": groups_state,
    }
    adoptions, _ = derive_group_goal_changes(ents, 5)
    assert len(adoptions) == 4  # capped at adoptions_per_tick
    assert len({a["group_id"] for a in adoptions}) == 4  # all distinct groups


def test_adoption_survives_same_frame_association_and_group_state_churn():
    ents = _entities(condition=500)
    goal_proposal = build_group_goal_proposal(ents, 5)
    assert goal_proposal is not None
    # Stage 7A (association, priority 90) and Stage 7B (group_state, priority 89)
    # both commit a revision bump in the same frame, before group_goal previously
    # ran at priority 91.
    frame = [
        _upstream_revision_bump(ents, ASSOCIATION_REGISTRY_ID, 5, 90),
        _upstream_revision_bump(ents, GROUP_STATE_REGISTRY_ID, 5, 89),
        goal_proposal,
    ]
    accepted, rejected, _ = _commit(ents, frame, 5)
    goal_events = [e for e in accepted if e["event_type"] == PROPOSAL_TYPE]
    goal_rejections = [r for r in rejected if r["entity_id"] == GROUP_GOAL_REGISTRY_ID]
    assert not goal_rejections, f"group_goal rejected under churn: {goal_rejections}"
    assert len(goal_events) == 1
    gid = group_goal_id(GID, GOAL_TYPE, SHELTER)
    assert ents[GROUP_GOAL_REGISTRY_ID]["goals"][gid]["status"] == "active"


def test_expiry_survives_same_frame_association_and_group_state_churn():
    ents = _entities(condition=500)
    _commit(ents, [build_group_goal_proposal(ents, 5)], 5)
    gid = group_goal_id(GID, GOAL_TYPE, SHELTER)
    assert ents[GROUP_GOAL_REGISTRY_ID]["goals"][gid]["status"] == "active"
    # Shelter recovers; the goal must expire even while upstream registries churn
    # in the same frame.
    ents[SHELTER]["condition"] = UPKEEP_THRESHOLD + 100
    expiry_proposal = build_group_goal_proposal(ents, 6)
    assert expiry_proposal is not None
    frame = [
        _upstream_revision_bump(ents, ASSOCIATION_REGISTRY_ID, 6, 90),
        _upstream_revision_bump(ents, GROUP_STATE_REGISTRY_ID, 6, 89),
        expiry_proposal,
    ]
    accepted, rejected, _ = _commit(ents, frame, 6)
    goal_rejections = [r for r in rejected if r["entity_id"] == GROUP_GOAL_REGISTRY_ID]
    assert not goal_rejections, f"group_goal expiry rejected under churn: {goal_rejections}"
    assert ents[GROUP_GOAL_REGISTRY_ID]["goals"][gid]["status"] == "expired"
