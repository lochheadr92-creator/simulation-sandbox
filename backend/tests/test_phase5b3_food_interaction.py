"""Phase 5B3 — Request, Offer and Response Protocol (food-interaction-v1)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.commit_pipeline import run_commit_frame
from core.constants import (
    CRITICAL_THRESHOLD,
    FOOD_INTERACTION_EXPIRY_TICKS,
    FOOD_TRANSFER_SURPLUS,
)
from core.food_interaction import (
    KIND_OFFER,
    KIND_REQUEST,
    PROTOCOL_VERSION,
    REASON_ALREADY_EXPIRED,
    REASON_DUPLICATE_ACTIVE,
    REASON_EXPIRED,
    REASON_FULFIL_UNAUTHORIZED,
    REASON_LOST_SUPPLY,
    REASON_NOT_PENDING,
    REASON_NOT_YET_EXPIRED,
    REASON_PARTICIPANT_NOT_LIVING,
    REASON_REFUSED,
    REASON_RESPONSE_UNAUTHORIZED,
    REASON_TERMINAL,
    RESPONSE_ACCEPT,
    RESPONSE_REFUSE,
    STATUS_ACCEPTED,
    STATUS_EXPIRED,
    STATUS_FULFILLED,
    STATUS_INVALIDATED,
    STATUS_PENDING,
    STATUS_REFUSED,
    derive_interaction_id,
    expires_tick_for,
    giver_and_receiver,
)
from core.hashing import canonical_hash
from core.mutations import apply_mutation, snapshot_for_hash
from domains.base import DomainOutput
from domains.food_interaction_proposals import (
    build_create_proposal,
    build_expire_proposal,
    build_fulfil_proposal,
    build_invalidate_proposal,
    build_respond_proposal,
    propose_stranded_accepted_invalidations,
)
from domains.perception import SOCIAL_OBSERVATION_VERSION, empty_knowledge


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _social_obs(subject_id, *, appears_to_carry_food=False, apparent_urgent_need="none", tick=0, pos=None):
    return {
        "subject_id": subject_id,
        "last_seen_tick": tick,
        "position": pos or {"x": 0, "y": 0},
        "alive": True,
        "social_observation_version": SOCIAL_OBSERVATION_VERSION,
        "visible_action_kind": None,
        "visible_action_status": None,
        "appears_injured": False,
        "apparent_urgent_need": apparent_urgent_need,
        "appears_to_carry_food": appears_to_carry_food,
    }


def _person(position, *, hunger=100, food=0, inventory=0, alive=True, knowledge=None, last_event_id=None):
    p = {
        "type": "person",
        "position": dict(position),
        "alive": alive,
        "hunger": hunger,
        "thirst": 100,
        "energy": 900,
        "inventory": inventory,
        "food_inventory": food,
        "has_shelter": False,
        "knowledge": knowledge if knowledge is not None else empty_knowledge(),
        "action": {"type": "idle", "status": "completed", "ticks_spent": 0},
        "plan": {"goal": None, "steps": [], "step_index": 0, "status": "completed"},
    }
    if last_event_id:
        p["last_event_id"] = last_event_id
    return p


def _pair_entities(
    *,
    a_food=0,
    b_food=FOOD_TRANSFER_SURPLUS,
    a_hunger=CRITICAL_THRESHOLD,
    b_hunger=100,
    a_knows_b_carries=True,
    b_knows_a_need="critical",
    tick=5,
):
    """A at (2,2), B at (3,2) — adjacent. Default request: A requests from B."""
    a_knowledge = empty_knowledge()
    b_knowledge = empty_knowledge()
    if a_knows_b_carries is not None:
        a_knowledge["known_people"]["person-b"] = _social_obs(
            "person-b",
            appears_to_carry_food=bool(a_knows_b_carries),
            apparent_urgent_need="none",
            tick=tick,
            pos={"x": 3, "y": 2},
        )
    if b_knows_a_need is not None:
        b_knowledge["known_people"]["person-a"] = _social_obs(
            "person-a",
            appears_to_carry_food=False,
            apparent_urgent_need=b_knows_a_need,
            tick=tick,
            pos={"x": 2, "y": 2},
        )
    return {
        "person-a": _person(
            {"x": 2, "y": 2}, hunger=a_hunger, food=a_food, knowledge=a_knowledge,
            last_event_id="evt-seed-a",
        ),
        "person-b": _person(
            {"x": 3, "y": 2}, hunger=b_hunger, food=b_food, knowledge=b_knowledge,
            last_event_id="evt-seed-b",
        ),
    }


def _commit(entities, proposals, tick=5, order_start=0, lineage="phase5b3-lineage"):
    return run_commit_frame(
        entities,
        [DomainOutput(proposals=list(proposals))],
        tick,
        lineage,
        "run-5b3",
        order_start,
        f"frame-{tick}",
    )


def _create(entities, kind, initiator, responder, tick=5):
    return build_create_proposal(
        kind=kind,
        initiator_id=initiator,
        responder_id=responder,
        tick=tick,
        entities=entities,
    )


def _accept_lifecycle_request(entities, tick=5):
    """Create + accept a request_food interaction; return (iid, entities, events)."""
    create = _create(entities, KIND_REQUEST, "person-a", "person-b", tick=tick)
    accepted, rejected, nxt = _commit(entities, [create], tick=tick)
    assert rejected == [] and len(accepted) == 1
    iid = accepted[0]["interaction"]["interaction_id"]
    respond = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=tick, entities=entities,
    )
    accepted2, rejected2, nxt2 = _commit(entities, [respond], tick=tick, order_start=nxt)
    assert rejected2 == [] and len(accepted2) == 1
    return iid, accepted + accepted2, nxt2


def _accept_lifecycle_offer(entities, tick=5):
    create = _create(entities, KIND_OFFER, "person-b", "person-a", tick=tick)
    accepted, rejected, nxt = _commit(entities, [create], tick=tick)
    assert rejected == [] and len(accepted) == 1
    iid = accepted[0]["interaction"]["interaction_id"]
    respond = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=tick, entities=entities,
    )
    accepted2, rejected2, nxt2 = _commit(entities, [respond], tick=tick, order_start=nxt)
    assert rejected2 == [] and len(accepted2) == 1
    return iid, accepted + accepted2, nxt2


# ---------------------------------------------------------------------------
# 1. Request lifecycle
# ---------------------------------------------------------------------------

def test_request_lifecycle_pending_accepted_fulfilled_with_conservation():
    entities = _pair_entities()
    total_before = entities["person-a"]["food_inventory"] + entities["person-b"]["food_inventory"]
    iid, events, nxt = _accept_lifecycle_request(entities)
    assert entities[iid]["status"] == STATUS_ACCEPTED
    assert entities[iid]["kind"] == KIND_REQUEST
    assert entities[iid]["protocol_version"] == PROTOCOL_VERSION
    giver, receiver = giver_and_receiver(entities[iid])
    assert giver == "person-b" and receiver == "person-a"

    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    accepted, rejected, _ = _commit(entities, [fulfil], order_start=nxt)
    assert rejected == [] and len(accepted) == 1
    assert entities[iid]["status"] == STATUS_FULFILLED
    assert entities[iid]["fulfilment_transfer_event_id"] == accepted[0]["id"]
    assert accepted[0]["transfer"]["giver_id"] == "person-b"
    assert accepted[0]["transfer"]["receiver_id"] == "person-a"
    assert entities["person-a"]["food_inventory"] == 1
    assert entities["person-b"]["food_inventory"] == FOOD_TRANSFER_SURPLUS - 1
    assert entities["person-a"]["food_inventory"] + entities["person-b"]["food_inventory"] == total_before


# ---------------------------------------------------------------------------
# 2. Offer lifecycle
# ---------------------------------------------------------------------------

def test_offer_lifecycle_pending_accepted_fulfilled_with_conservation():
    entities = _pair_entities(a_food=0, b_food=FOOD_TRANSFER_SURPLUS, a_hunger=CRITICAL_THRESHOLD)
    total_before = entities["person-a"]["food_inventory"] + entities["person-b"]["food_inventory"]
    iid, events, nxt = _accept_lifecycle_offer(entities)
    assert entities[iid]["kind"] == KIND_OFFER
    giver, receiver = giver_and_receiver(entities[iid])
    assert giver == "person-b" and receiver == "person-a"

    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    accepted, rejected, _ = _commit(entities, [fulfil], order_start=nxt)
    assert rejected == []
    assert entities[iid]["status"] == STATUS_FULFILLED
    assert entities[iid]["fulfilment_transfer_event_id"] == accepted[0]["id"]
    assert entities["person-a"]["food_inventory"] == 1
    assert entities["person-b"]["food_inventory"] == FOOD_TRANSFER_SURPLUS - 1
    assert entities["person-a"]["food_inventory"] + entities["person-b"]["food_inventory"] == total_before


# ---------------------------------------------------------------------------
# 3. Refusal
# ---------------------------------------------------------------------------

def test_responder_can_refuse_terminal_immutable_no_inventory_mutation():
    entities = _pair_entities()
    before_food = (entities["person-a"]["food_inventory"], entities["person-b"]["food_inventory"])
    create = _create(entities, KIND_REQUEST, "person-a", "person-b")
    accepted, rejected, nxt = _commit(entities, [create])
    assert rejected == []
    iid = accepted[0]["interaction"]["interaction_id"]
    refuse = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_REFUSE, tick=5, entities=entities,
    )
    accepted2, rejected2, nxt2 = _commit(entities, [refuse], order_start=nxt)
    assert rejected2 == []
    assert entities[iid]["status"] == STATUS_REFUSED
    assert entities[iid]["terminal_reason"] == REASON_REFUSED
    assert (entities["person-a"]["food_inventory"], entities["person-b"]["food_inventory"]) == before_food

    # Terminal immutable: accept after refuse rejected
    retry = build_respond_proposal(
        interaction={**entities[iid], "status": STATUS_PENDING},  # stale view attempt
        response=RESPONSE_ACCEPT, tick=5, entities=entities,
    )
    # Use live entity status by rebuilding from live after force-status in proposal meta mismatch
    retry = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
    )
    # Force mutation as if pending (malicious) - Core checks live status
    retry["mutation"]["entity_updates"][iid]["status"] = STATUS_ACCEPTED
    retry["interaction"]["response"] = RESPONSE_ACCEPT
    retry["interaction"]["status"] = STATUS_ACCEPTED
    acc3, rej3, _ = _commit(entities, [retry], order_start=nxt2)
    assert acc3 == []
    assert rej3[0]["reason_code"] == REASON_TERMINAL
    assert entities[iid]["status"] == STATUS_REFUSED
    assert (entities["person-a"]["food_inventory"], entities["person-b"]["food_inventory"]) == before_food


# ---------------------------------------------------------------------------
# 4. Response authority
# ---------------------------------------------------------------------------

def test_response_authority_initiator_and_unrelated_rejected():
    entities = _pair_entities()
    entities["person-c"] = _person({"x": 4, "y": 2}, last_event_id="evt-c")
    create = _create(entities, KIND_REQUEST, "person-a", "person-b")
    accepted, rejected, nxt = _commit(entities, [create])
    iid = accepted[0]["interaction"]["interaction_id"]

    # Initiator cannot respond
    bad = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
    )
    bad["entity_id"] = "person-a"
    acc, rej, nxt = _commit(entities, [bad], order_start=nxt)
    assert acc == []
    assert rej[0]["reason_code"] == REASON_RESPONSE_UNAUTHORIZED

    # Unrelated cannot respond
    bad2 = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_REFUSE, tick=5, entities=entities,
    )
    bad2["entity_id"] = "person-c"
    acc2, rej2, _ = _commit(entities, [bad2], order_start=nxt)
    assert acc2 == []
    assert rej2[0]["reason_code"] == REASON_RESPONSE_UNAUTHORIZED
    assert entities[iid]["status"] == STATUS_PENDING


# ---------------------------------------------------------------------------
# 5. Expiry
# ---------------------------------------------------------------------------

def test_expiry_boundary_response_before_expire_at_boundary_reject_after():
    created_tick = 10
    entities = _pair_entities(tick=created_tick)
    create = _create(entities, KIND_REQUEST, "person-a", "person-b", tick=created_tick)
    accepted, rejected, nxt = _commit(entities, [create], tick=created_tick)
    assert rejected == []
    iid = accepted[0]["interaction"]["interaction_id"]
    exp = entities[iid]["expires_tick"]
    assert exp == expires_tick_for(created_tick)
    assert exp == created_tick + FOOD_INTERACTION_EXPIRY_TICKS

    # Response permitted while current_tick < expires_tick
    before = exp - 1
    respond = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=before, entities=entities,
    )
    # Fresh entities copy for the pre-boundary path
    ents_ok = copy.deepcopy(entities)
    acc_ok, rej_ok, _ = _commit(ents_ok, [respond], tick=before, order_start=nxt)
    assert rej_ok == [] and ents_ok[iid]["status"] == STATUS_ACCEPTED

    # At boundary: expires (current_tick >= expires_tick)
    ents_exp = copy.deepcopy(entities)
    expire = build_expire_proposal(
        interaction=ents_exp[iid], tick=exp, entity_id="person-a", entities=ents_exp,
    )
    acc_e, rej_e, nxt_e = _commit(ents_exp, [expire], tick=exp, order_start=nxt)
    assert rej_e == [] and ents_exp[iid]["status"] == STATUS_EXPIRED
    assert ents_exp[iid]["terminal_reason"] == REASON_EXPIRED
    food_before = (ents_exp["person-a"]["food_inventory"], ents_exp["person-b"]["food_inventory"])

    # Response after expiry rejected; no inventory mutation
    respond_late = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=exp, entities=ents_exp,
    )
    acc_l, rej_l, _ = _commit(ents_exp, [respond_late], tick=exp, order_start=nxt_e)
    assert acc_l == []
    assert rej_l[0]["reason_code"] in (REASON_TERMINAL, REASON_ALREADY_EXPIRED)
    assert (ents_exp["person-a"]["food_inventory"], ents_exp["person-b"]["food_inventory"]) == food_before

    # Expire before boundary rejected
    ents_early = copy.deepcopy(entities)
    early = build_expire_proposal(
        interaction=ents_early[iid], tick=before, entity_id="person-b", entities=ents_early,
    )
    acc_x, rej_x, _ = _commit(ents_early, [early], tick=before, order_start=nxt)
    assert acc_x == []
    assert rej_x[0]["reason_code"] == REASON_NOT_YET_EXPIRED


# ---------------------------------------------------------------------------
# 6. Invalidation
# ---------------------------------------------------------------------------

def test_invalidation_dead_participant_and_lost_supply_no_partial_mutation():
    entities = _pair_entities()
    iid, events, nxt = _accept_lifecycle_request(entities)
    food_before = (entities["person-a"]["food_inventory"], entities["person-b"]["food_inventory"])

    # Dead giver
    entities["person-b"]["alive"] = False
    inv = build_invalidate_proposal(
        interaction=entities[iid], tick=5, entity_id="person-a",
        entities=entities, reason=REASON_PARTICIPANT_NOT_LIVING,
    )
    acc, rej, nxt = _commit(entities, [inv], order_start=nxt)
    assert rej == [] and entities[iid]["status"] == STATUS_INVALIDATED
    assert entities[iid]["terminal_reason"] == REASON_PARTICIPANT_NOT_LIVING
    assert (entities["person-a"]["food_inventory"], entities["person-b"]["food_inventory"]) == food_before

    # Lost supply on a fresh accepted interaction
    entities2 = _pair_entities()
    iid2, _, nxt2 = _accept_lifecycle_request(entities2)
    entities2["person-b"]["food_inventory"] = 0
    inv2 = build_invalidate_proposal(
        interaction=entities2[iid2], tick=5, entity_id="person-b",
        entities=entities2, reason=REASON_LOST_SUPPLY,
    )
    acc2, rej2, _ = _commit(entities2, [inv2], order_start=nxt2)
    assert rej2 == [] and entities2[iid2]["status"] == STATUS_INVALIDATED
    assert entities2[iid2]["terminal_reason"] == REASON_LOST_SUPPLY
    assert entities2["person-a"]["food_inventory"] == 0

    # Failed 5B1 eligibility: rejected fulfil does not mutate; maintenance invalidates.
    entities3 = _pair_entities()
    iid3, _, nxt3 = _accept_lifecycle_request(entities3)
    entities3["person-b"]["food_inventory"] = 1  # below surplus
    fulfil = build_fulfil_proposal(interaction=entities3[iid3], tick=5, entities=entities3)
    before3 = copy.deepcopy(entities3)
    acc3, rej3, nxt3 = _commit(entities3, [fulfil], order_start=nxt3)
    assert acc3 == []
    assert entities3["person-a"]["food_inventory"] == before3["person-a"]["food_inventory"]
    assert entities3["person-b"]["food_inventory"] == before3["person-b"]["food_inventory"]
    # Rejected fulfil must not leave accepted stranded past the maintenance boundary.
    maint = propose_stranded_accepted_invalidations(entities3, tick=5)
    assert len(maint) == 1
    acc_m, rej_m, _ = _commit(entities3, maint, order_start=nxt3)
    assert rej_m == [] and len(acc_m) == 1
    assert entities3[iid3]["status"] == STATUS_INVALIDATED
    assert entities3[iid3]["terminal_reason"] == REASON_LOST_SUPPLY
    assert entities3[iid3]["status"] != STATUS_EXPIRED


# ---------------------------------------------------------------------------
# 7. Duplicate protection
# ---------------------------------------------------------------------------

def test_duplicate_create_accept_fulfil_and_retry_after_terminal():
    entities = _pair_entities()
    create = _create(entities, KIND_REQUEST, "person-a", "person-b")
    accepted, rejected, nxt = _commit(entities, [create, copy.deepcopy(create)])
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["reason_code"] == REASON_DUPLICATE_ACTIVE
    iid = accepted[0]["interaction"]["interaction_id"]

    respond = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
    )
    accepted2, rejected2, nxt = _commit(entities, [respond, copy.deepcopy(respond)], order_start=nxt)
    assert len(accepted2) == 1
    assert len(rejected2) == 1
    assert rejected2[0]["reason_code"] in (REASON_TERMINAL, REASON_NOT_PENDING, "precondition.failed")
    assert entities[iid]["status"] == STATUS_ACCEPTED

    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    accepted3, rejected3, nxt = _commit(entities, [fulfil, copy.deepcopy(fulfil)], order_start=nxt)
    assert len(accepted3) == 1
    assert len(rejected3) == 1
    assert entities[iid]["status"] == STATUS_FULFILLED
    assert entities["person-a"]["food_inventory"] == 1
    assert entities["person-b"]["food_inventory"] == 1

    # Retry after fulfilment cannot reopen or re-transfer
    retry = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    before = copy.deepcopy(entities)
    acc4, rej4, _ = _commit(entities, [retry], order_start=nxt)
    assert acc4 == []
    assert rej4[0]["reason_code"] == REASON_TERMINAL
    assert entities["person-a"]["food_inventory"] == before["person-a"]["food_inventory"]
    assert entities["person-b"]["food_inventory"] == before["person-b"]["food_inventory"]


# ---------------------------------------------------------------------------
# 8. Contention
# ---------------------------------------------------------------------------

def _contention_entities():
    """person-b has exactly FOOD_TRANSFER_SURPLUS; requesters a and c adjacent."""
    return {
        "person-a": _person(
            {"x": 2, "y": 2}, hunger=CRITICAL_THRESHOLD, food=0, last_event_id="ea",
            knowledge={"schema_version": "knowledge-v2", "known_tiles": [], "known_water_tiles": [],
                       "known_trees": {}, "known_shelters": {}, "known_carcasses": {},
                       "known_animals": {}, "known_people": {
                           "person-b": _social_obs("person-b", appears_to_carry_food=True, tick=5, pos={"x": 3, "y": 2}),
                       }, "known_dangers": {}, "facts": {}},
        ),
        "person-b": _person(
            {"x": 3, "y": 2}, hunger=100, food=FOOD_TRANSFER_SURPLUS, last_event_id="eb",
            knowledge=empty_knowledge(),
        ),
        "person-c": _person(
            {"x": 3, "y": 3}, hunger=CRITICAL_THRESHOLD, food=0, last_event_id="ec",
            knowledge={"schema_version": "knowledge-v2", "known_tiles": [], "known_water_tiles": [],
                       "known_trees": {}, "known_shelters": {}, "known_carcasses": {},
                       "known_animals": {}, "known_people": {
                           "person-b": _social_obs("person-b", appears_to_carry_food=True, tick=5, pos={"x": 3, "y": 2}),
                       }, "known_dangers": {}, "facts": {}},
        ),
    }


def _run_contention_to_terminal(entities, *, shuffle_fulfil=True, shuffle_create=False):
    """Create+accept two requests, contend fulfils, then maintenance-invalidate loser.

    Returns (iids, all_accepted_events, final_entities_order_index).
    """
    all_events = []
    create_a = _create(entities, KIND_REQUEST, "person-a", "person-b", tick=5)
    create_c = _create(entities, KIND_REQUEST, "person-c", "person-b", tick=5)
    creates = [create_c, create_a] if shuffle_create else [create_a, create_c]
    acc, rej, nxt = _commit(entities, creates, tick=5)
    assert len(acc) == 2 and rej == []
    all_events.extend(acc)
    iids = sorted(e["interaction"]["interaction_id"] for e in acc)
    for iid in iids:
        resp = build_respond_proposal(
            interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
        )
        a, r, nxt = _commit(entities, [resp], tick=5, order_start=nxt)
        assert r == [] and a
        all_events.extend(a)

    fulfils = [build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities) for iid in iids]
    if shuffle_fulfil:
        fulfils = list(reversed(fulfils))
    acc_f, rej_f, nxt = _commit(entities, fulfils, tick=5, order_start=nxt)
    assert len(acc_f) == 1
    assert len(rej_f) == 1
    all_events.extend(acc_f)

    # Rejected fulfil must not mutate; loser is still accepted until maintenance.
    winners = [iid for iid in iids if entities[iid]["status"] == STATUS_FULFILLED]
    losers = [iid for iid in iids if entities[iid]["status"] == STATUS_ACCEPTED]
    assert len(winners) == 1 and len(losers) == 1

    maint = propose_stranded_accepted_invalidations(entities, tick=5)
    assert len(maint) == 1
    assert maint[0]["proposal_type"] == "invalidate_food_interaction"
    assert maint[0]["interaction"]["interaction_id"] == losers[0]
    acc_m, rej_m, nxt = _commit(entities, maint, tick=5, order_start=nxt)
    assert rej_m == [] and len(acc_m) == 1
    all_events.extend(acc_m)

    assert entities[winners[0]]["status"] == STATUS_FULFILLED
    assert entities[losers[0]]["status"] == STATUS_INVALIDATED
    assert entities[losers[0]]["terminal_reason"] == REASON_LOST_SUPPLY
    assert entities[losers[0]]["status"] != STATUS_EXPIRED
    # No accepted interaction remains stranded.
    assert all(
        entities[iid]["status"] != STATUS_ACCEPTED for iid in iids
    )
    total_food = sum(entities[p]["food_inventory"] for p in ("person-a", "person-b", "person-c"))
    assert total_food == FOOD_TRANSFER_SURPLUS
    assert entities["person-b"]["food_inventory"] == 1
    assert all(entities[p]["food_inventory"] >= 0 for p in ("person-a", "person-b", "person-c"))
    return iids, winners[0], losers[0], all_events, nxt


def test_contention_two_interactions_one_unit_deterministic_winner_and_invalidated_loser():
    """Two accepted interactions compete; winner fulfils; loser is invalidated."""
    entities = _contention_entities()
    iids, winner, loser, events, _ = _run_contention_to_terminal(entities, shuffle_fulfil=True)

    assert entities[winner]["fulfilment_transfer_event_id"] == next(
        e["id"] for e in events if e["event_type"] == "fulfil_food_interaction"
    )
    assert entities[loser]["terminal_reason"] == REASON_LOST_SUPPLY
    # Exactly one transfer event
    transfer_events = [e for e in events if e.get("transfer")]
    assert len(transfer_events) == 1

    # Determinism: shuffled proposal arrival yields same winner/loser/trace/hash
    def run_once(shuffle_fulfil, shuffle_create):
        ents = _contention_entities()
        ids, w, l, evs, _ = _run_contention_to_terminal(
            ents, shuffle_fulfil=shuffle_fulfil, shuffle_create=shuffle_create,
        )
        return (
            ids,
            w,
            l,
            [e["event_type"] for e in evs],
            [e["id"] for e in evs],
            {iid: (ents[iid]["status"], ents[iid].get("terminal_reason")) for iid in ids},
            {p: ents[p]["food_inventory"] for p in ("person-a", "person-b", "person-c")},
            canonical_hash(snapshot_for_hash(ents, 5, "phase5b3-lineage")),
        )

    assert run_once(True, False) == run_once(False, True) == run_once(True, True)


def test_contention_replay_reconstructs_fulfilled_winner_and_invalidated_loser():
    entities = _contention_entities()
    iids, winner, loser, events, _ = _run_contention_to_terminal(entities, shuffle_fulfil=True)
    live = copy.deepcopy(entities)

    replayed = _contention_entities()
    for event in events:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    assert replayed[winner]["status"] == STATUS_FULFILLED
    assert replayed[loser]["status"] == STATUS_INVALIDATED
    assert replayed[loser]["terminal_reason"] == REASON_LOST_SUPPLY
    assert replayed[winner]["fulfilment_transfer_event_id"] == live[winner]["fulfilment_transfer_event_id"]
    for p in ("person-a", "person-b", "person-c"):
        assert replayed[p]["food_inventory"] == live[p]["food_inventory"]
    # Replay does not perform another transfer
    assert sum(replayed[p]["food_inventory"] for p in ("person-a", "person-b", "person-c")) == FOOD_TRANSFER_SURPLUS


def test_accepted_never_expires_only_invalidates_when_unfulfillable():
    """Expiry is pending-only; accepted unfulfillable interactions invalidate."""
    entities = _pair_entities()
    iid, _, nxt = _accept_lifecycle_request(entities, tick=5)
    entities["person-b"]["food_inventory"] = 0
    # Expire proposal against accepted must reject
    expire = build_expire_proposal(
        interaction=entities[iid], tick=5 + FOOD_INTERACTION_EXPIRY_TICKS,
        entity_id="person-a", entities=entities,
    )
    # Force expires_tick into the past on live entity without changing status
    acc, rej, nxt = _commit(entities, [expire], tick=5 + FOOD_INTERACTION_EXPIRY_TICKS, order_start=nxt)
    assert acc == []
    assert entities[iid]["status"] == STATUS_ACCEPTED
    maint = propose_stranded_accepted_invalidations(entities, tick=5)
    acc_m, rej_m, _ = _commit(entities, maint, tick=5, order_start=nxt)
    assert rej_m == [] and entities[iid]["status"] == STATUS_INVALIDATED
    assert entities[iid]["terminal_reason"] == REASON_LOST_SUPPLY


# ---------------------------------------------------------------------------
# 9. Determinism
# ---------------------------------------------------------------------------

def test_determinism_shuffled_entity_and_proposal_order():
    def run(entity_order, proposal_shuffle):
        people = {
            "person-a": _person(
                {"x": 2, "y": 2}, hunger=CRITICAL_THRESHOLD, food=0, last_event_id="ea",
                knowledge={"version": "knowledge-v2", "known_tiles": {}, "known_water": {},
                           "known_trees": {}, "known_food": {}, "known_shelters": {},
                           "known_animals": {}, "known_people": {
                               "person-b": _social_obs("person-b", appears_to_carry_food=True, tick=5, pos={"x": 3, "y": 2}),
                           }, "known_dangers": {}, "facts": {}},
            ),
            "person-b": _person(
                {"x": 3, "y": 2}, hunger=100, food=FOOD_TRANSFER_SURPLUS, last_event_id="eb",
                knowledge={"version": "knowledge-v2", "known_tiles": {}, "known_water": {},
                           "known_trees": {}, "known_food": {}, "known_shelters": {},
                           "known_animals": {}, "known_people": {
                               "person-a": _social_obs("person-a", apparent_urgent_need="critical", tick=5, pos={"x": 2, "y": 2}),
                           }, "known_dangers": {}, "facts": {}},
            ),
        }
        entities = {k: people[k] for k in entity_order}
        create = _create(entities, KIND_REQUEST, "person-a", "person-b")
        acc, rej, n = _commit(entities, [create], tick=5)
        assert rej == []
        iid = acc[0]["interaction"]["interaction_id"]
        respond = build_respond_proposal(
            interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
        )
        acc2, rej2, n = _commit(entities, [respond], tick=5, order_start=n)
        assert rej2 == []
        fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
        props = [fulfil]
        if proposal_shuffle:
            props = list(reversed(props))
        acc3, rej3, _ = _commit(entities, props, tick=5, order_start=n)
        assert rej3 == []
        events = acc + acc2 + acc3
        return (
            [e["event_type"] for e in events],
            [e["id"] for e in events],
            canonical_hash(snapshot_for_hash(entities, 5, "phase5b3-lineage")),
            entities[iid]["status"],
            entities["person-a"]["food_inventory"],
            entities["person-b"]["food_inventory"],
        )

    r1 = run(["person-a", "person-b"], False)
    r2 = run(["person-b", "person-a"], True)
    assert r1 == r2


# ---------------------------------------------------------------------------
# 10. Replay
# ---------------------------------------------------------------------------

def test_replay_reconstructs_lifecycle_and_does_not_double_transfer():
    entities = _pair_entities()
    all_events = []
    create = _create(entities, KIND_REQUEST, "person-a", "person-b", tick=5)
    acc, rej, n = _commit(entities, [create], tick=5)
    assert rej == []
    all_events.extend(acc)
    iid = acc[0]["interaction"]["interaction_id"]

    resp = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
    )
    acc, rej, n = _commit(entities, [resp], tick=5, order_start=n)
    assert rej == []
    all_events.extend(acc)

    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    acc, rej, n = _commit(entities, [fulfil], tick=5, order_start=n)
    assert rej == []
    all_events.extend(acc)
    live = copy.deepcopy(entities)

    # Replay mutations only
    replayed = _pair_entities()
    for event in all_events:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    assert replayed[iid]["status"] == STATUS_FULFILLED
    assert replayed[iid]["fulfilment_transfer_event_id"] == all_events[-1]["id"]
    assert replayed["person-a"]["food_inventory"] == live["person-a"]["food_inventory"]
    assert replayed["person-b"]["food_inventory"] == live["person-b"]["food_inventory"]
    # Replay path does not re-run transfer logic — only apply_mutation
    assert replayed["person-a"]["food_inventory"] == 1

    # Expiry replay
    ents = _pair_entities(tick=10)
    create = _create(ents, KIND_REQUEST, "person-a", "person-b", tick=10)
    acc, _, n = _commit(ents, [create], tick=10)
    iid = acc[0]["interaction"]["interaction_id"]
    exp_tick = ents[iid]["expires_tick"]
    expire = build_expire_proposal(
        interaction=ents[iid], tick=exp_tick, entity_id="person-a", entities=ents,
    )
    acc2, _, _ = _commit(ents, [expire], tick=exp_tick, order_start=n)
    events = acc + acc2
    r2 = _pair_entities(tick=10)
    for event in events:
        apply_mutation(r2, copy.deepcopy(event["mutation"]))
    assert r2[iid]["status"] == STATUS_EXPIRED
    assert r2[iid]["terminal_reason"] == REASON_EXPIRED


# ---------------------------------------------------------------------------
# Identity / version
# ---------------------------------------------------------------------------

def test_interaction_id_is_content_derived_and_stable():
    a = derive_interaction_id(KIND_REQUEST, "person-a", "person-b", 5)
    b = derive_interaction_id(KIND_REQUEST, "person-a", "person-b", 5)
    c = derive_interaction_id(KIND_REQUEST, "person-a", "person-b", 6)
    d = derive_interaction_id(KIND_OFFER, "person-a", "person-b", 5)
    assert a == b and a.startswith("fi-")
    assert a != c and a != d


def test_initiator_cannot_fulfil_request():
    """For request_food, initiator is receiver — fulfil must be by giver (responder)."""
    entities = _pair_entities()
    iid, _, nxt = _accept_lifecycle_request(entities)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    fulfil["entity_id"] = "person-a"  # initiator/receiver
    acc, rej, _ = _commit(entities, [fulfil], order_start=nxt)
    assert acc == []
    assert rej[0]["reason_code"] in (REASON_FULFIL_UNAUTHORIZED, "food_transfer.invalid_ownership")
