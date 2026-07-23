"""Stage 8B Leg 1 norm-carriage/transmission focused + integrated tests.

Contract: memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md.
"""
from __future__ import annotations

import copy

from core.commit_pipeline import run_commit_frame
from core.mutations import apply_mutation
from domains.base import DomainOutput
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    ASSOCIATION_REGISTRY_VERSION,
    GROUP_CANDIDATE_VERSION,
)
from domains.group_goal_contracts import (
    GROUP_GOAL_REGISTRY_ID,
    GROUP_GOAL_REGISTRY_VERSION,
    GROUP_GOAL_VERSION,
    GOAL_TYPE,
    group_goal_id,
)
from domains.group_norm_contracts import (
    GROUP_NORM_REGISTRY_ID,
    GROUP_NORM_REGISTRY_VERSION,
    GROUP_NORM_VERSION,
    NORM_TYPE,
    NORM_DECAY_TICKS,
    group_norm_id,
)
from domains.group_carriage_contracts import (
    GROUP_CARRIAGE_REGISTRY_ID,
    GROUP_CARRIAGE_REGISTRY_VERSION,
    GROUP_CARRIAGE_VERSION,
    PROPOSAL_TYPE,
    LIMITS,
    SOURCE_BACKFILL,
    SOURCE_TRANSMISSION,
    TRANSMISSION_QUALIFYING_EVENT_TYPES,
    advance_group_carriage_registry,
    build_group_carriage_proposal,
    carrier_key,
    derive_group_carriage_changes,
    empty_group_carriage_registry,
    split_carrier_key,
    validate_group_carriage_proposal,
)

LINEAGE = "stage8b-leg1-lineage"
RUN = "stage8b-leg1-run"
GID = "grp-1"
SHELTER = "shelter-1"


def _person(pid, *, alive=True, action=None):
    ent = {
        "type": "person", "alive": alive, "living_agent": {"wants": {}},
        "position": {"x": 0, "y": 0}, "last_event_id": "evt-0-" + pid,
    }
    if action is not None:
        ent["action"] = action
    return ent


def _qualifying_action(target_id, *, event_id="evt-social-1", action_type=None):
    """A committed action of the sole confirmed qualifying type (Decision 4)."""
    etype = (action_type or TRANSMISSION_QUALIFYING_EVENT_TYPES[0].removeprefix("social_"))
    return {
        "type": etype, "status": "completed", "target_entity_id": target_id,
        "accepted_event_id": event_id,
    }


def _assoc(members=("p-a", "p-b"), *, group_id=GID, rev=1, recognised=True):
    cand = {
        "schema_version": GROUP_CANDIDATE_VERSION,
        "recognition_state": "recognised" if recognised else "dissolved",
        "ever_recognised": True,
        "member_ids": sorted(members), "group_type": "household",
        "recognised_tick": 1, "recognition_event_id": "evt-0-recog",
    }
    return {
        "schema_version": ASSOCIATION_REGISTRY_VERSION, "revision": rev,
        "last_event_id": "evt-0-assoc",
        "group_candidates": {group_id: cand},
    }


def _goal_registry(*, supporters, target=SHELTER, group_id=GID, rev=1,
                   status="active", last_updated=1, key="k3"):
    goal_id = group_goal_id(group_id, GOAL_TYPE, target)
    return {
        "type": "group_goal_registry",
        "schema_version": GROUP_GOAL_REGISTRY_VERSION,
        "revision": rev, "last_event_id": "evt-0-goal",
        "goals": {goal_id: {
            "schema_version": GROUP_GOAL_VERSION, "goal_id": goal_id,
            "group_id": group_id, "goal_type": GOAL_TYPE, "target_id": target,
            "status": status, "adopted_via_key": key,
            "last_updated_tick": last_updated,
            "supporter_ids": sorted(supporters),
        }},
        "processed_goal_keys": [key],
    }


def _norm_registry(*, group_id=GID, target=SHELTER, tick=10, status="active",
                   deadline=None, rev=1, norm_id=None):
    nid = norm_id or group_norm_id(group_id, NORM_TYPE)
    return {
        "type": "group_norm_registry", "schema_version": GROUP_NORM_REGISTRY_VERSION,
        "revision": rev, "last_event_id": "evt-0-norm",
        "norms": {nid: {
            "schema_version": GROUP_NORM_VERSION, "norm_id": nid,
            "group_id": group_id, "norm_type": NORM_TYPE, "target_id": target,
            "status": status, "formation_count": 3, "formed_tick": tick,
            "created_tick": tick, "last_updated_tick": tick, "last_adoption_tick": tick,
            "decay_deadline_tick": (tick + NORM_DECAY_TICKS) if deadline is None else deadline,
            "formed_via_key": "k3", "created_event_id": "evt", "last_event_id": "evt",
            "revision": 1,
        }},
        "group_progress": {}, "processed_norm_keys": ["k3"],
    }


def _norm_id(group_id=GID):
    return group_norm_id(group_id, NORM_TYPE)


def _entities(*, members=("p-a", "p-b"), supporters=("p-a",), recognised=True,
             norm_status="active", carriage=None):
    ents = {m: _person(m) for m in members}
    ents[ASSOCIATION_REGISTRY_ID] = _assoc(members, recognised=recognised)
    ents[GROUP_GOAL_REGISTRY_ID] = _goal_registry(supporters=supporters)
    ents[GROUP_NORM_REGISTRY_ID] = _norm_registry(status=norm_status)
    if carriage is not None:
        ents[GROUP_CARRIAGE_REGISTRY_ID] = carriage
    return ents


def _commit(entities, proposals, tick, order=0):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))],
        tick, LINEAGE, RUN, order, "frame-" + str(tick),
    )


# --- formation backfill ---------------------------------------------------

def test_backfill_grants_carriage_to_supporters_only():
    # 3 members, 2 supporters (p-c is the organically-produced non-supporter
    # per the confirmed contract's probe evidence pattern).
    ents = _entities(members=("p-a", "p-b", "p-c"), supporters=("p-a", "p-b"))
    changes = derive_group_carriage_changes(ents, 11)
    backfilled_people = {b["person_id"] for b in changes["backfills"]}
    assert backfilled_people == {"p-a", "p-b"}
    assert "p-c" not in backfilled_people
    assert not changes["transmissions"]  # p-c has no qualifying interaction yet
    registry, transitions = advance_group_carriage_registry(None, changes, 11)
    nid = _norm_id()
    assert carrier_key(nid, "p-a") in registry["carriers"]
    assert carrier_key(nid, "p-b") in registry["carriers"]
    assert carrier_key(nid, "p-c") not in registry["carriers"]
    for rec in registry["carriers"].values():
        assert rec["source"] == SOURCE_BACKFILL
        assert rec["learned_from"] is None
    assert nid in registry["backfilled_norm_ids"]
    assert len(transitions) == 2


def test_backfill_is_one_time_not_resynced_to_later_readoption():
    # Once backfilled, a later re-adoption with a DIFFERENT supporter set must
    # NOT retroactively grant carriage - backfill is tied to the adoption that
    # triggered formation, never continuously synced (Decision 1).
    ents = _entities(members=("p-a", "p-b", "p-c"), supporters=("p-a", "p-b"))
    changes = derive_group_carriage_changes(ents, 11)
    registry, _ = advance_group_carriage_registry(None, changes, 11)
    ents[GROUP_CARRIAGE_REGISTRY_ID] = registry
    # A later re-adoption now supports p-c too (goal's current supporter_ids
    # widened) - must NOT trigger a fresh backfill for p-c.
    ents[GROUP_GOAL_REGISTRY_ID] = _goal_registry(
        supporters=("p-a", "p-b", "p-c"), key="k4", last_updated=400,
    )
    changes2 = derive_group_carriage_changes(ents, 401)
    assert not changes2["backfills"]  # already backfilled_norm_ids -> no re-derivation


def test_backfill_retries_next_tick_if_no_active_goal_yet():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a", "p-b"))
    ents[GROUP_GOAL_REGISTRY_ID]["goals"] = {}  # no active goal record visible yet
    changes = derive_group_carriage_changes(ents, 11)
    assert not changes["backfills"]


# --- transmission (imitation-only, N=1, social_request_help only) ---------

def test_synthetic_transmission_fires_independent_of_organic_event():
    # Required rider (b): deterministic synthetic fixture, independent of the
    # organic scenario's tick-699 event. p-a is already a carrier (backfilled);
    # p-b (non-carrier member) directs a qualifying action at p-a.
    carriage = empty_group_carriage_registry(0)
    nid = _norm_id()
    key_a = carrier_key(nid, "p-a")
    carriage["carriers"][key_a] = {
        "schema_version": GROUP_CARRIAGE_VERSION, "group_id": GID,
        "source": SOURCE_BACKFILL, "learned_from": None, "via_event_id": "evt",
        "learned_tick": 5, "revision": 1, "created_event_id": "evt",
        "last_event_id": "evt",
    }
    carriage["backfilled_norm_ids"] = [nid]
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-b"] = _person("p-b", action=_qualifying_action("p-a", event_id="evt-transmit-1"))
    changes = derive_group_carriage_changes(ents, 20)
    assert not changes["backfills"]  # p-a already backfilled
    assert len(changes["transmissions"]) == 1
    t = changes["transmissions"][0]
    assert t["person_id"] == "p-b"
    assert t["learned_from"] == "p-a"
    assert t["via_event_id"] == "evt-transmit-1"
    assert t["norm_id"] == nid
    registry, transitions = advance_group_carriage_registry(carriage, changes, 20)
    key_b = carrier_key(nid, "p-b")
    assert key_b in registry["carriers"]
    rec = registry["carriers"][key_b]
    assert rec["source"] == SOURCE_TRANSMISSION
    assert rec["learned_from"] == "p-a"
    assert rec["via_event_id"] == "evt-transmit-1"
    assert rec["learned_tick"] == 20
    assert len(transitions) == 1
    assert transitions[0]["kind"] == SOURCE_TRANSMISSION


def _base_carriage_with_carrier_a():
    carriage = empty_group_carriage_registry(0)
    nid = _norm_id()
    key_a = carrier_key(nid, "p-a")
    carriage["carriers"][key_a] = {
        "schema_version": GROUP_CARRIAGE_VERSION, "group_id": GID,
        "source": SOURCE_BACKFILL, "learned_from": None, "via_event_id": "evt",
        "learned_tick": 5, "revision": 1, "created_event_id": "evt",
        "last_event_id": "evt",
    }
    carriage["backfilled_norm_ids"] = [nid]
    return carriage


def test_non_qualifying_event_type_does_not_transmit():
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-b"] = _person("p-b", action=_qualifying_action(
        "p-a", event_id="evt-x", action_type="cooperate",
    ))
    changes = derive_group_carriage_changes(ents, 20)
    assert not changes["transmissions"]


def test_carrier_initiated_action_does_not_transmit_teaching_is_non_goal():
    # Decision 2 (confirmed): teaching (carrier-initiated) has zero organic
    # evidence and is a named non-goal - only observer/non-carrier-initiated
    # (imitation) qualifies. p-a (carrier) directs the qualifying action AT
    # p-b (non-carrier); p-b itself has no committed action -> no transmission.
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-a"] = _person("p-a", action=_qualifying_action("p-b", event_id="evt-y"))
    changes = derive_group_carriage_changes(ents, 20)
    assert not changes["transmissions"]


def test_wrong_target_does_not_transmit():
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b", "p-c"), supporters=("p-a",), carriage=carriage)
    # p-b's qualifying action targets p-c (also a non-carrier), not the carrier p-a.
    ents["p-b"] = _person("p-b", action=_qualifying_action("p-c", event_id="evt-z"))
    changes = derive_group_carriage_changes(ents, 20)
    assert not changes["transmissions"]


def test_transmission_fires_at_exactly_n_equals_1():
    # TRANSMISSION_COUNT = 1 (the measured floor): the FIRST qualifying
    # interaction transmits immediately - no accumulation window.
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-b"] = _person("p-b", action=_qualifying_action("p-a", event_id="evt-first"))
    changes = derive_group_carriage_changes(ents, 20)
    assert len(changes["transmissions"]) == 1


def test_already_carrier_is_never_re_transmitted():
    carriage = _base_carriage_with_carrier_a()
    nid = _norm_id()
    key_b = carrier_key(nid, "p-b")
    carriage["carriers"][key_b] = {
        "schema_version": GROUP_CARRIAGE_VERSION, "group_id": GID,
        "source": SOURCE_TRANSMISSION, "learned_from": "p-a", "via_event_id": "evt-prior",
        "learned_tick": 15, "revision": 1, "created_event_id": "evt",
        "last_event_id": "evt",
    }
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-b"] = _person("p-b", action=_qualifying_action("p-a", event_id="evt-second"))
    changes = derive_group_carriage_changes(ents, 30)
    assert not changes["transmissions"]  # p-b already carries - not re-derived


# --- decay independence (Decision 6) ---------------------------------------

def test_carrier_survives_norm_expiry_no_forgetting():
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",),
                     norm_status="expired", carriage=carriage)
    changes = derive_group_carriage_changes(ents, 400)
    assert not changes["backfills"] and not changes["transmissions"]
    proposal = build_group_carriage_proposal(ents, 400)
    assert proposal is None  # nothing to propose; carrier record untouched
    nid = _norm_id()
    assert carrier_key(nid, "p-a") in ents[GROUP_CARRIAGE_REGISTRY_ID]["carriers"]


# --- build / validate / forged-field rejection ------------------------------

def test_build_and_validate_ok():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    assert proposal is not None
    assert proposal["proposal_type"] == PROPOSAL_TYPE
    assert proposal["engine_priority"] == 86
    assert validate_group_carriage_proposal(proposal, ents) is None


def test_validate_rejects_forged_person_id():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    reg = proposal["mutation"]["new_entities"][GROUP_CARRIAGE_REGISTRY_ID]
    (key, rec), = reg["carriers"].items()
    rec["person_id"] = "p-forged"
    assert validate_group_carriage_proposal(proposal, ents) is not None


def test_validate_rejects_forged_learned_from():
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-b"] = _person("p-b", action=_qualifying_action("p-a", event_id="evt-t"))
    proposal = build_group_carriage_proposal(ents, 20)
    reg = proposal["mutation"]["entity_updates"][GROUP_CARRIAGE_REGISTRY_ID]
    nid = _norm_id()
    rec = reg["carriers"][carrier_key(nid, "p-b")]
    rec["learned_from"] = "p-forged"
    assert validate_group_carriage_proposal(proposal, ents) is not None


def test_validate_rejects_markerless_carriage_registry_write():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    del proposal["group_carriage_update"]
    assert validate_group_carriage_proposal(proposal, ents) is not None


def test_validate_rejects_out_of_scope_mutation():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    proposal["mutation"]["new_entities"]["p-a"] = {"alive": False}
    assert validate_group_carriage_proposal(proposal, ents) is not None


def test_validate_rejects_backfill_carrier_with_learned_from_set():
    # Defense-in-depth: a backfill-source record must never carry a
    # learned_from (that would misrepresent it as transmission).
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    reg = proposal["mutation"]["new_entities"][GROUP_CARRIAGE_REGISTRY_ID]
    (key, rec), = reg["carriers"].items()
    rec["learned_from"] = "p-b"
    assert validate_group_carriage_proposal(proposal, ents) is not None


# --- commit / replay / idempotence / capacity -------------------------------

def test_commit_creates_registry_and_touches_nothing_else():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    before_b = copy.deepcopy(ents["p-b"])
    proposal = build_group_carriage_proposal(ents, 11)
    accepted, rejected, _ = _commit(ents, [proposal], 11)
    assert not rejected
    assert len(accepted) == 1
    assert ents["p-b"] == before_b
    nid = _norm_id()
    assert carrier_key(nid, "p-a") in ents[GROUP_CARRIAGE_REGISTRY_ID]["carriers"]


def test_provenance_stamped_on_commit():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    accepted, rejected, _ = _commit(ents, [proposal], 11)
    assert not rejected
    nid = _norm_id()
    rec = ents[GROUP_CARRIAGE_REGISTRY_ID]["carriers"][carrier_key(nid, "p-a")]
    assert rec["created_event_id"] == accepted[0]["id"]
    assert rec["last_event_id"] == accepted[0]["id"]
    assert "pending_event_tick" not in rec
    assert "pending_transition" not in rec


def test_replay_equivalence():
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-b"] = _person("p-b", action=_qualifying_action("p-a", event_id="evt-r"))
    prior = copy.deepcopy(ents[GROUP_CARRIAGE_REGISTRY_ID])
    proposal = build_group_carriage_proposal(ents, 20)
    accepted, rejected, _ = _commit(ents, [proposal], 20)
    assert not rejected
    rebuilt = {GROUP_CARRIAGE_REGISTRY_ID: prior}
    for event in accepted:
        apply_mutation(rebuilt, copy.deepcopy(event["mutation"]))
    assert rebuilt[GROUP_CARRIAGE_REGISTRY_ID] == ents[GROUP_CARRIAGE_REGISTRY_ID]


def test_duplicate_transmission_idempotent():
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-b"] = _person("p-b", action=_qualifying_action("p-a", event_id="evt-dup"))
    changes = derive_group_carriage_changes(ents, 20)
    reg1, _ = advance_group_carriage_registry(carriage, changes, 20)
    # Re-applying the same changes (e.g. a re-derivation before the entity's
    # action field is overwritten) must not create a second carrier record.
    reg2, transitions2 = advance_group_carriage_registry(reg1, changes, 21)
    assert len(reg2["carriers"]) == len(reg1["carriers"])
    assert not transitions2


def test_backfilled_tracking_never_evicts_a_norm_still_in_the_registry():
    """F3 (contract amendment): the cap-boundary regression.

    The original code truncated `backfilled_norm_ids` with
    `sorted(set(...))[-16:]` - lexicographic - while `group_norm` compacts its
    own norms by (active, recency). Under that mismatch an ACTIVE norm could
    be evicted from the tracking set while still present in `norms`, and the
    next derive would re-backfill it against the CURRENT supporter set,
    granting carriage to people who were never supporters at formation.

    Inject more distinct norms than the cap and assert the invariant directly:
    every norm still present upstream is still tracked.
    """
    over = LIMITS.backfilled_norm_ids + 6
    norm_ids = [f"group-norm-{i:04d}" + "z" * 16 for i in range(over)]
    changes = {"backfills": [], "transmissions": []}
    for nid in norm_ids:
        changes["backfills"].append({
            "norm_id": nid, "group_id": GID, "person_id": "p-a",
            "source_event_id": "evt",
        })
    reg, _ = advance_group_carriage_registry(
        None, changes, 10, known_norm_ids=set(norm_ids),
    )
    tracked = set(reg["backfilled_norm_ids"])
    missing = [nid for nid in norm_ids if nid not in tracked]
    assert not missing, f"norms still upstream but dropped from tracking: {missing}"


def test_backfilled_tracking_prunes_norms_no_longer_upstream():
    """The bound: ids whose norm has left the registry are pruned, so the
    tracking set stays bounded by the norm registry's own cap rather than
    growing without limit."""
    changes = {"backfills": [
        {"norm_id": "group-norm-aaa", "group_id": GID, "person_id": "p-a", "source_event_id": "e"},
        {"norm_id": "group-norm-bbb", "group_id": GID, "person_id": "p-b", "source_event_id": "e"},
    ]}
    reg, _ = advance_group_carriage_registry(
        None, changes, 10, known_norm_ids={"group-norm-aaa", "group-norm-bbb"},
    )
    assert set(reg["backfilled_norm_ids"]) == {"group-norm-aaa", "group-norm-bbb"}
    # 'bbb' is compacted out of group_norm upstream; tracking drops it too.
    reg2, _ = advance_group_carriage_registry(
        reg, {"backfills": [], "transmissions": []}, 11,
        known_norm_ids={"group-norm-aaa"},
    )
    assert set(reg2["backfilled_norm_ids"]) == {"group-norm-aaa"}


def test_record_does_not_restate_ids_held_in_the_key():
    """F2c: norm_id/person_id/carrier_id live in the key exactly once."""
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    reg = proposal["mutation"]["new_entities"][GROUP_CARRIAGE_REGISTRY_ID]
    (key, rec), = reg["carriers"].items()
    assert not ({"carrier_id", "norm_id", "person_id"} & set(rec))
    nid, pid = split_carrier_key(key)
    assert nid == _norm_id() and pid == "p-a"
    # provenance survives the slimming, stored once each
    assert rec["via_event_id"] and rec["learned_tick"] == 11
    assert rec["source"] == SOURCE_BACKFILL and rec["learned_from"] is None


def test_validator_rejects_record_that_restates_key_ids():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    reg = proposal["mutation"]["new_entities"][GROUP_CARRIAGE_REGISTRY_ID]
    (key, rec), = reg["carriers"].items()
    rec["norm_id"] = _norm_id()  # re-stating a key-held id must be rejected
    assert validate_group_carriage_proposal(proposal, ents) is not None


def test_validator_rejects_record_carrying_pending_staging_keys():
    # Amendment 2: pending_event_tick/pending_transition are never written by
    # _carrier_record (stamping now keys off the proposal's own `transitions`
    # list) - a record carrying either key can only be forged or stale.
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    reg = proposal["mutation"]["new_entities"][GROUP_CARRIAGE_REGISTRY_ID]
    (key, rec), = reg["carriers"].items()
    rec["pending_event_tick"] = 11
    assert validate_group_carriage_proposal(proposal, ents) is not None


def test_honest_stamped_record_omits_pending_staging_keys():
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    proposal = build_group_carriage_proposal(ents, 11)
    accepted, rejected, _ = _commit(ents, [proposal], 11)
    assert not rejected
    nid = _norm_id()
    rec = ents[GROUP_CARRIAGE_REGISTRY_ID]["carriers"][carrier_key(nid, "p-a")]
    assert "pending_event_tick" not in rec
    assert "pending_transition" not in rec


def test_capacity_bound_respected():
    reg = empty_group_carriage_registry(0)
    changes = {"backfills": [], "transmissions": []}
    for i in range(LIMITS.carriers + 5):
        pid = f"person-{i:03d}"
        changes["backfills"].append({
            "norm_id": f"norm-{i:03d}", "group_id": f"grp-{i:03d}",
            "person_id": pid, "source_event_id": "evt",
        })
    reg, _ = advance_group_carriage_registry(reg, changes, 10)
    assert len(reg["carriers"]) <= LIMITS.carriers


# --- integrated full-kernel (the class of defect 7D's focused tests missed) --

def _upstream_revision_bump(entities, registry_id, tick, priority):
    rev = int(entities[registry_id]["revision"])
    return {
        "proposal_family": "test_support",
        "proposal_type": "test_upstream_revision_bump",
        "proposer_engine_id": "test", "entity_id": registry_id,
        "causal_parent_event_ids": [], "is_exogenous": True,
        "requested_time": tick, "phase": "agent", "engine_priority": priority,
        "touched_scope": [registry_id],
        "preconditions": [{"entity_id": registry_id, "field": "revision", "op": "eq", "value": rev}],
        "mutation": {"entity_updates": {registry_id: {"revision": rev + 1}}, "new_entities": {}},
        "explanation": "test: upstream registry revision bump in same frame",
    }


def test_carriage_backfill_survives_same_frame_upstream_churn():
    """group_carriage (86) commits before group_norm (87), group_goal (88), and
    association (90), so its pinned upstream revisions still match even when
    all three churn in the same frame - the same class of defect 7D's focused
    tests missed (stale_membership), one layer below 8A's own 87-before-88 fix."""
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",))
    carriage_proposal = build_group_carriage_proposal(ents, 11)
    assert carriage_proposal is not None
    frame = [
        _upstream_revision_bump(ents, ASSOCIATION_REGISTRY_ID, 11, 90),
        _upstream_revision_bump(ents, GROUP_GOAL_REGISTRY_ID, 11, 88),
        _upstream_revision_bump(ents, GROUP_NORM_REGISTRY_ID, 11, 87),
        carriage_proposal,
    ]
    accepted, rejected, _ = _commit(ents, frame, 11)
    carriage_rejections = [r for r in rejected if r["entity_id"] == GROUP_CARRIAGE_REGISTRY_ID]
    assert not carriage_rejections, f"group_carriage rejected under churn: {carriage_rejections}"
    carriage_events = [e for e in accepted if e["event_type"] == PROPOSAL_TYPE]
    assert len(carriage_events) == 1
    nid = _norm_id()
    assert carrier_key(nid, "p-a") in ents[GROUP_CARRIAGE_REGISTRY_ID]["carriers"]


def test_carriage_transmission_survives_same_frame_upstream_churn():
    carriage = _base_carriage_with_carrier_a()
    ents = _entities(members=("p-a", "p-b"), supporters=("p-a",), carriage=carriage)
    ents["p-b"] = _person("p-b", action=_qualifying_action("p-a", event_id="evt-churn"))
    carriage_proposal = build_group_carriage_proposal(ents, 20)
    assert carriage_proposal is not None
    frame = [
        _upstream_revision_bump(ents, ASSOCIATION_REGISTRY_ID, 20, 90),
        _upstream_revision_bump(ents, GROUP_GOAL_REGISTRY_ID, 20, 88),
        _upstream_revision_bump(ents, GROUP_NORM_REGISTRY_ID, 20, 87),
        carriage_proposal,
    ]
    accepted, rejected, _ = _commit(ents, frame, 20)
    carriage_rejections = [r for r in rejected if r["entity_id"] == GROUP_CARRIAGE_REGISTRY_ID]
    assert not carriage_rejections, f"group_carriage rejected under churn: {carriage_rejections}"
    nid = _norm_id()
    assert carrier_key(nid, "p-b") in ents[GROUP_CARRIAGE_REGISTRY_ID]["carriers"]
