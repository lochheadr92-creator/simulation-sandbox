"""CORE-INTEGRITY-004: proposal commit ordering must be content-independent.

Previously `order_key`'s final tie-break was `content_hash`, computed over
`core_fields` including `preconditions` and `mutation`. Since `PHASE_RANK` has
two ranks and `engine_priority` is domain-level, nearly every agent proposal
tied on the first three components, so CONTENT decided behavioural order.

These tests pin the corrected contract: changing non-ordering content must not
reorder anything, and ambiguous semantic identities must fail closed rather than
silently reverting to content-derived ordering.
"""
import copy
import random

import pytest

from core.commit_pipeline import (
    AmbiguousProposalOrderError,
    assert_unique_order_keys,
    normalize_proposal,
    order_key,
    run_commit_frame,
)
from domains.base import DomainOutput


def _proposal(entity_id: str, *, ptype: str = "living_action",
              engine: str = "living_settlement", priority: int = 10,
              tick: int = 1, phase: str = "agent", updates=None,
              preconditions=None):
    return {
        "proposal_family": "living_action",
        "proposal_type": ptype,
        "proposer_engine_id": engine,
        "proposer_engine_version": "test",
        "entity_id": entity_id,
        "causal_parent_event_ids": [],
        "is_exogenous": True,
        "requested_time": tick,
        "phase": phase,
        "engine_priority": priority,
        "touched_scope": [entity_id],
        "preconditions": list(preconditions or []),
        "mutation": {"entity_updates": {entity_id: dict(updates or {"hunger": 1})},
                     "new_entities": {}},
        "explanation": f"{ptype} for {entity_id}",
    }


def _entities(ids):
    return {i: {"id": i, "type": "person", "alive": True, "hunger": 0,
                "energy": 500, "position": {"x": 1, "y": 1}} for i in ids}


def _order(proposals):
    """Final committed order, expressed as stable entity/type pairs."""
    normalized = [normalize_proposal(p, i) for i, p in enumerate(proposals)]
    return [(p["entity_id"], p["proposal_type"])
            for p in sorted(normalized, key=order_key)]


# --- 1. inactive precondition must not reorder --------------------------------

def test_inactive_precondition_does_not_change_order():
    base = [_proposal(f"person-00{i}") for i in range(8)]
    with_pre = [
        _proposal(f"person-00{i}",
                  preconditions=[{"entity_id": f"person-00{i}", "field": "energy",
                                  "op": "eq", "value": 500}])
        for i in range(8)
    ]
    assert _order(base) == _order(with_pre)


def test_the_demonstrated_tick1_living_settlement_case():
    """The exact case proven to reshuffle under content-hash ordering.

    Eight people, one agent-phase proposal each, all tying on
    (requested_time, phase, engine_priority). Under the old key the order was
    decided by content_hash and an inactive precondition permuted it entirely.
    """
    people = [f"person-00{i}" for i in range(8)]
    plain = [_proposal(p) for p in people]
    inactive = [
        _proposal(p, preconditions=[{"entity_id": p, "field": "energy",
                                     "op": "eq", "value": 500}])
        for p in people
    ]
    expected = [(p, "living_action") for p in people]
    assert _order(plain) == expected
    assert _order(inactive) == expected


# --- 2/3/4. other non-ordering content must not reorder -----------------------

def test_added_receipt_metadata_does_not_change_order():
    base = [_proposal(f"person-00{i}") for i in range(6)]
    tagged = []
    for i in range(6):
        p = _proposal(f"person-00{i}")
        p["living_action"] = {"action_type": "rest", "diagnostic_note": "x" * (i + 1)}
        tagged.append(p)
    assert _order(base) == _order(tagged)


def test_mutation_key_reordering_does_not_change_order():
    forward = [_proposal(f"person-00{i}", updates={"hunger": 1, "thirst": 2, "energy": 3})
               for i in range(6)]
    reversed_keys = [_proposal(f"person-00{i}", updates={"energy": 3, "thirst": 2, "hunger": 1})
                     for i in range(6)]
    assert _order(forward) == _order(reversed_keys)


def test_changing_mutation_values_does_not_change_relative_order():
    a = [_proposal(f"person-00{i}", updates={"hunger": i}) for i in range(6)]
    b = [_proposal(f"person-00{i}", updates={"hunger": 900 - i}) for i in range(6)]
    assert _order(a) == _order(b)


# --- 5. submission shuffling must not change commit order ---------------------

def test_shuffling_submission_order_does_not_change_commit_order():
    people = [f"person-00{i}" for i in range(8)]
    baseline = _order([_proposal(p) for p in people])
    rng = random.Random(4)
    for _ in range(10):
        shuffled = [_proposal(p) for p in people]
        rng.shuffle(shuffled)
        assert _order(shuffled) == baseline


# --- 6/7. deterministic ordering across actors and types ----------------------

def test_two_actors_same_proposal_type_are_deterministically_ordered():
    assert _order([_proposal("person-002"), _proposal("person-001")]) == [
        ("person-001", "living_action"), ("person-002", "living_action")]


def test_one_actor_multiple_proposal_types_is_deterministically_ordered():
    got = _order([_proposal("person-001", ptype="living_action"),
                  _proposal("person-001", ptype="give_food")])
    assert got == [("person-001", "give_food"), ("person-001", "living_action")]


# --- 8/9. duplicates fail closed ---------------------------------------------

def test_duplicate_semantic_identity_with_different_content_fails_closed():
    """Same semantic key, DIFFERENT content => order matters and is ambiguous."""
    dup = [_proposal("person-001"), _proposal("person-001", updates={"hunger": 99})]
    normalized = [normalize_proposal(p, i) for i, p in enumerate(dup)]
    with pytest.raises(AmbiguousProposalOrderError) as exc:
        assert_unique_order_keys(normalized, tick=1)
    message = str(exc.value)
    assert "person-001" in message and "tick 1" in message
    assert "proposal_id" in message
    assert "0x" not in message, "error must not expose object reprs"


def test_duplicate_rail_fires_through_the_commit_frame():
    entities = _entities(["person-001"])
    dup = [_proposal("person-001"), _proposal("person-001", updates={"hunger": 99})]
    with pytest.raises(AmbiguousProposalOrderError):
        run_commit_frame(entities, [DomainOutput(proposals=dup)], 1, "lin", "run", 0, "f-1")


def test_identical_duplicate_proposals_are_not_ambiguous():
    """Same semantic key AND same content => the same proposal.

    Relative order is unobservable, the engine already dedupes these, and the
    rail must NOT fire. `content_hash` is consulted only to recognise sameness,
    never to order different proposals.
    """
    dup = [_proposal("person-001"), _proposal("person-001")]
    normalized = [normalize_proposal(p, i) for i, p in enumerate(dup)]
    assert normalized[0]["content_hash"] == normalized[1]["content_hash"]
    assert assert_unique_order_keys(normalized, tick=1) is None

    entities = _entities(["person-001"])
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[_proposal("person-001"), _proposal("person-001")])],
        1, "lin", "run", 0, "f-1")
    assert len(accepted) + len(rejected) == 2, "both proposals must reach the commit loop"


def test_unique_frame_does_not_trip_the_rail():
    normalized = [normalize_proposal(_proposal(f"person-00{i}"), i) for i in range(8)]
    assert_unique_order_keys(normalized, tick=1) is None


# --- 10/11. content_hash retains its identity role ----------------------------

def test_content_hash_still_changes_when_content_changes():
    a = normalize_proposal(_proposal("person-001", updates={"hunger": 1}), 0)
    b = normalize_proposal(_proposal("person-001", updates={"hunger": 2}), 0)
    assert a["content_hash"] != b["content_hash"]
    assert a["proposal_id"] != b["proposal_id"]
    # ...but they order identically: content no longer decides behaviour.
    assert order_key(a) == order_key(b)


def test_event_id_still_carries_content_hash():
    """`event_id` = evt-{tick}-{order}-{content_hash[:8]} -- unchanged by CI-004.

    `content_hash` is a PROPOSAL field, not an event field, so the proposal is
    normalized here to obtain the expected prefix.
    """
    proposal = _proposal("person-001")
    expected_prefix = normalize_proposal(copy.deepcopy(proposal), 0)["content_hash"][:8]
    entities = _entities(["person-001"])
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], 1, "lin", "run", 0, "f-1")
    assert not rejected and len(accepted) == 1
    event_id = accepted[0]["id"]
    assert event_id.startswith("evt-1-0-")
    assert event_id.endswith(expected_prefix), (
        "content_hash must still contribute proposal identity to the event id")


# --- 12/13. replay and resume ------------------------------------------------

def test_replay_reconstructs_identical_ordering_keys():
    proposals = [_proposal(f"person-00{i}") for i in range(8)]
    first = [normalize_proposal(copy.deepcopy(p), i) for i, p in enumerate(proposals)]
    replay = [normalize_proposal(copy.deepcopy(p), i) for i, p in enumerate(proposals)]
    assert [order_key(p) for p in first] == [order_key(p) for p in replay]


def test_resume_midrun_preserves_ordering():
    """Ordering depends only on the proposal, never on run history."""
    people = [f"person-00{i}" for i in range(5)]
    at_tick_1 = _order([_proposal(p, tick=1) for p in people])
    at_tick_900 = _order([_proposal(p, tick=900) for p in people])
    assert [e for e, _ in at_tick_1] == [e for e, _ in at_tick_900]


# --- 14. key is composed of stable scalars only -------------------------------

def test_order_key_is_only_stable_scalars():
    """Every component is a stable string/int, or a canonical tuple of them.

    The 7th component is `tuple(sorted(touched_scope))` -- an explicitly
    canonicalised (sorted) tuple of strings, which is a deterministic,
    cross-platform-stable comparison value. Nothing in the key may be a float,
    a bool, a set, a dict, or anything carrying runtime object identity.
    """
    key = order_key(normalize_proposal(_proposal("person-001"), 0))

    def stable(component):
        if isinstance(component, bool):
            return False
        if isinstance(component, (str, int)):
            return True
        if isinstance(component, tuple):
            return all(isinstance(x, str) for x in component)
        return False

    assert all(stable(c) for c in key), key
    scope = key[-1]
    assert isinstance(scope, tuple) and list(scope) == sorted(scope), (
        "touched_scope component must be canonically sorted")


def test_touched_scope_component_is_content_insensitive():
    """The 7th component must not move when non-ordering content changes."""
    plain = normalize_proposal(_proposal("person-001"), 0)
    with_pre = normalize_proposal(_proposal(
        "person-001",
        preconditions=[{"entity_id": "person-001", "field": "energy",
                        "op": "eq", "value": 500}]), 0)
    other_mutation = normalize_proposal(
        _proposal("person-001", updates={"hunger": 987}), 0)
    assert order_key(plain) == order_key(with_pre) == order_key(other_mutation)


def test_same_actor_same_type_different_scope_is_deterministically_ordered():
    """The food-interaction contention shape: one actor, two same-type
    proposals, distinguished only by what they act upon."""
    a = _proposal("person-b", ptype="fulfil_food_interaction")
    a["touched_scope"] = ["fi-bbb", "person-b", "person-c"]
    b = _proposal("person-b", ptype="fulfil_food_interaction")
    b["touched_scope"] = ["fi-aaa", "person-a", "person-b"]
    normalized = [normalize_proposal(p, i) for i, p in enumerate([a, b])]
    assert_unique_order_keys(normalized, tick=5)
    ordered = sorted(normalized, key=order_key)
    assert ordered[0]["touched_scope"][0] == "fi-aaa"
    # ...and submission order does not matter.
    reverse = [normalize_proposal(p, i) for i, p in enumerate([b, a])]
    assert [order_key(p) for p in sorted(reverse, key=order_key)] == \
           [order_key(p) for p in ordered]


def test_phase_and_priority_still_dominate_entity_identity():
    """Environment phase must still commit before agent phase regardless of id."""
    env = _proposal("person-009", phase="environment", engine="ecology", priority=-2)
    agent = _proposal("person-000", phase="agent", priority=10)
    assert _order([agent, env])[0] == ("person-009", "living_action")
