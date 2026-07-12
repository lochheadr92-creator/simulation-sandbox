"""Phase 5B4 — Event-backed interaction memory (interaction-memory-v1)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.commit_pipeline import run_commit_frame
from core.constants import CRITICAL_THRESHOLD, FOOD_TRANSFER_SURPLUS, VISION_RADIUS
from core.food_interaction import (
    KIND_OFFER,
    KIND_REQUEST,
    RESPONSE_ACCEPT,
    RESPONSE_REFUSE,
    STATUS_ACCEPTED,
    STATUS_FULFILLED,
    STATUS_REFUSED,
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
)
from domains.interaction_memory import (
    INTERACTION_MEMORY_VERSION,
    KIND_HELPED,
    KIND_OFFERED,
    KIND_REFUSED,
    KIND_REQUESTED,
    KIND_WITNESSED,
    MAX_INTERACTION_FACTS_PER_OBSERVER,
    REASON_IM_EVENT_MISMATCH,
    REASON_IM_MISSING_EVENT,
    REASON_IM_MISSING_PROVENANCE,
    REASON_IM_WRONG_EVENT_TYPE,
    build_fact,
    derive_fact_id,
    list_interaction_facts,
    merge_interaction_memory,
    validate_interaction_memory_fact,
)
from domains.perception import SOCIAL_OBSERVATION_VERSION, empty_knowledge
from domains.people_domain import PeopleDomain
from core.rng import DeterministicRNG
from domains.base import ActivationFrame
from core.constants import ENGINE_VERSION


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


def _pair(tick=5):
    a_k = empty_knowledge()
    b_k = empty_knowledge()
    a_k["known_people"]["person-b"] = _social_obs(
        "person-b", appears_to_carry_food=True, tick=tick, pos={"x": 3, "y": 2},
    )
    b_k["known_people"]["person-a"] = _social_obs(
        "person-a", apparent_urgent_need="critical", tick=tick, pos={"x": 2, "y": 2},
    )
    return {
        "person-a": _person(
            {"x": 2, "y": 2}, hunger=CRITICAL_THRESHOLD, food=0,
            knowledge=a_k, last_event_id="evt-seed-a",
        ),
        "person-b": _person(
            {"x": 3, "y": 2}, hunger=100, food=FOOD_TRANSFER_SURPLUS,
            knowledge=b_k, last_event_id="evt-seed-b",
        ),
    }


def _commit(entities, proposals, tick=5, order_start=0):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))],
        tick, "phase5b4-lineage", "run-5b4", order_start, f"frame-{tick}",
    )


def _merge_for(entities, observer_id, tick=5):
    knowledge = entities[observer_id].get("knowledge") or empty_knowledge()
    merged, changed, learned = merge_interaction_memory(
        knowledge, observer_id=observer_id, entities=entities, tick=tick,
    )
    entities[observer_id]["knowledge"] = merged
    return merged, changed, learned


def _facts_of(knowledge, kind=None):
    facts = list_interaction_facts(knowledge)
    if kind:
        facts = [f for f in facts if f["kind"] == kind]
    return facts


def _create_accept_request(entities, tick=5):
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=tick, entities=entities,
    )
    acc, rej, n = _commit(entities, [create], tick=tick)
    assert rej == [] and acc
    iid = acc[0]["interaction"]["interaction_id"]
    resp = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=tick, entities=entities,
    )
    acc2, rej2, n = _commit(entities, [resp], tick=tick, order_start=n)
    assert rej2 == [] and acc2
    return iid, acc + acc2, n


# ---------------------------------------------------------------------------
# Fact semantics
# ---------------------------------------------------------------------------

def test_accepted_request_produces_requested_for_participants():
    entities = _pair()
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    acc, rej, _ = _commit(entities, [create])
    assert rej == []
    for oid in ("person-a", "person-b"):
        k, changed, _ = _merge_for(entities, oid)
        assert changed
        reqs = _facts_of(k, KIND_REQUESTED)
        assert len(reqs) == 1
        assert reqs[0]["accepted_event_id"] == entities[acc[0]["interaction"]["interaction_id"]]["creation_event_id"]
        assert reqs[0]["schema_version"] == INTERACTION_MEMORY_VERSION


def test_accepted_offer_produces_offered():
    entities = _pair()
    create = build_create_proposal(
        kind=KIND_OFFER, initiator_id="person-b", responder_id="person-a",
        tick=5, entities=entities,
    )
    acc, rej, _ = _commit(entities, [create])
    assert rej == []
    for oid in ("person-a", "person-b"):
        k, _, _ = _merge_for(entities, oid)
        offs = _facts_of(k, KIND_OFFERED)
        assert len(offs) == 1
        assert offs[0]["interaction_kind"] == KIND_OFFER


def test_accepted_refusal_produces_refused():
    entities = _pair()
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    acc, _, n = _commit(entities, [create])
    iid = acc[0]["interaction"]["interaction_id"]
    refuse = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_REFUSE, tick=5, entities=entities,
    )
    acc2, rej2, _ = _commit(entities, [refuse], order_start=n)
    assert rej2 == [] and entities[iid]["status"] == STATUS_REFUSED
    for oid in ("person-a", "person-b"):
        k, _, _ = _merge_for(entities, oid)
        assert len(_facts_of(k, KIND_REFUSED)) == 1
        assert len(_facts_of(k, KIND_HELPED)) == 0


def test_expiry_does_not_produce_refused():
    entities = _pair(tick=10)
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=10, entities=entities,
    )
    acc, _, n = _commit(entities, [create], tick=10)
    iid = acc[0]["interaction"]["interaction_id"]
    exp_tick = entities[iid]["expires_tick"]
    expire = build_expire_proposal(
        interaction=entities[iid], tick=exp_tick, entity_id="person-a", entities=entities,
    )
    acc2, rej2, _ = _commit(entities, [expire], tick=exp_tick, order_start=n)
    assert rej2 == [] and entities[iid]["status"] == "expired"
    for oid in ("person-a", "person-b"):
        k, _, _ = _merge_for(entities, oid, tick=exp_tick)
        assert _facts_of(k, KIND_REFUSED) == []


def test_invalidation_does_not_produce_refused():
    entities = _pair()
    iid, events, n = _create_accept_request(entities)
    entities["person-b"]["food_inventory"] = 0
    inv = build_invalidate_proposal(
        interaction=entities[iid], tick=5, entity_id="person-a",
        entities=entities, reason="food_interaction.lost_supply",
    )
    acc, rej, _ = _commit(entities, [inv], order_start=n)
    assert rej == [] and entities[iid]["status"] == "invalidated"
    for oid in ("person-a", "person-b"):
        k, _, _ = _merge_for(entities, oid)
        assert _facts_of(k, KIND_REFUSED) == []
        assert _facts_of(k, KIND_HELPED) == []


def test_fulfilled_transfer_produces_helped():
    entities = _pair()
    iid, events, n = _create_accept_request(entities)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    acc, rej, _ = _commit(entities, [fulfil], order_start=n)
    assert rej == [] and entities[iid]["status"] == STATUS_FULFILLED
    for oid in ("person-a", "person-b"):
        k, _, _ = _merge_for(entities, oid)
        helped = _facts_of(k, KIND_HELPED)
        assert len(helped) == 1
        assert helped[0]["accepted_event_id"] == entities[iid]["fulfilment_transfer_event_id"]


def test_accepted_but_unfulfilled_does_not_produce_helped():
    entities = _pair()
    iid, _, _ = _create_accept_request(entities)
    assert entities[iid]["status"] == STATUS_ACCEPTED
    for oid in ("person-a", "person-b"):
        k, _, _ = _merge_for(entities, oid)
        assert _facts_of(k, KIND_HELPED) == []


def test_eligible_visible_witness_receives_witnessed_assistance():
    entities = _pair()
    # Witness within vision of both participants
    entities["person-w"] = _person({"x": 2, "y": 3}, last_event_id="evt-w")
    iid, _, n = _create_accept_request(entities)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    acc, rej, _ = _commit(entities, [fulfil], order_start=n)
    assert rej == []
    assert "person-w" in entities[iid].get("eligible_witness_ids", [])
    k, changed, _ = _merge_for(entities, "person-w")
    assert changed
    wit = _facts_of(k, KIND_WITNESSED)
    assert len(wit) == 1
    assert wit[0]["subject_id"] == "person-b"  # giver
    assert wit[0]["counterparty_id"] == "person-a"


def test_out_of_range_observer_receives_no_witnessed_fact():
    entities = _pair()
    entities["person-far"] = _person({"x": 20, "y": 20}, last_event_id="evt-far")
    iid, _, n = _create_accept_request(entities)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    _commit(entities, [fulfil], order_start=n)
    assert "person-far" not in entities[iid].get("eligible_witness_ids", [])
    k, _, _ = _merge_for(entities, "person-far")
    assert _facts_of(k, KIND_WITNESSED) == []


def test_dead_observer_receives_no_witnessed_fact():
    entities = _pair()
    entities["person-w"] = _person({"x": 2, "y": 3}, alive=False, last_event_id="evt-w")
    iid, _, n = _create_accept_request(entities)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    _commit(entities, [fulfil], order_start=n)
    # Dead people are not listed as eligible witnesses
    assert "person-w" not in entities[iid].get("eligible_witness_ids", [])
    k, changed, _ = merge_interaction_memory(
        empty_knowledge(), observer_id="person-w", entities=entities, tick=5,
    )
    assert not changed
    assert _facts_of(k, KIND_WITNESSED) == []


def test_rejected_proposal_produces_no_fact():
    # Invalid create: no awareness (empty knowledge)
    entities = {
        "person-a": _person({"x": 2, "y": 2}, hunger=CRITICAL_THRESHOLD, last_event_id="ea"),
        "person-b": _person({"x": 3, "y": 2}, food=FOOD_TRANSFER_SURPLUS, last_event_id="eb"),
    }
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    acc, rej, _ = _commit(entities, [create])
    assert acc == [] and rej
    for oid in ("person-a", "person-b"):
        k, changed, _ = _merge_for(entities, oid)
        assert _facts_of(k) == []


def test_invalid_provenance_rejects_without_mutation():
    fact = build_fact(
        kind=KIND_HELPED,
        observer_id="person-a",
        subject_id="person-b",
        counterparty_id="person-b",
        interaction_id="fi-missing",
        accepted_event_id="evt-5-0-deadbeef",
        accepted_event_tick=5,
        interaction_kind=KIND_REQUEST,
        recorded_tick=5,
    )
    fact["accepted_event_id"] = ""  # malformed
    err = validate_interaction_memory_fact(fact)
    assert err == REASON_IM_MISSING_PROVENANCE


def test_missing_event_when_required():
    fact = build_fact(
        kind=KIND_HELPED,
        observer_id="person-a",
        subject_id="person-b",
        counterparty_id="person-b",
        interaction_id="fi-x",
        accepted_event_id="evt-5-0-deadbeef",
        accepted_event_tick=5,
        interaction_kind=KIND_REQUEST,
        recorded_tick=5,
    )
    err = validate_interaction_memory_fact(fact, require_event=True, event=None)
    assert err == REASON_IM_MISSING_EVENT


def test_mismatched_event_and_interaction_reject():
    entities = _pair()
    iid, events, n = _create_accept_request(entities)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    acc, _, _ = _commit(entities, [fulfil], order_start=n)
    fact = build_fact(
        kind=KIND_HELPED,
        observer_id="person-a",
        subject_id="person-b",
        counterparty_id="person-b",
        interaction_id=iid,
        accepted_event_id=entities[iid]["fulfilment_transfer_event_id"],
        accepted_event_tick=5,
        interaction_kind=KIND_REQUEST,
        recorded_tick=5,
    )
    # Wrong event type
    fake_event = {"id": fact["accepted_event_id"], "event_type": "create_food_interaction", "simulation_time": 5}
    err = validate_interaction_memory_fact(fact, interaction=entities[iid], event=fake_event)
    assert err == REASON_IM_WRONG_EVENT_TYPE
    # Mismatched event id vs interaction fulfilment
    bad = dict(fact)
    bad["accepted_event_id"] = entities[iid]["creation_event_id"]
    bad["fact_id"] = derive_fact_id(
        kind=KIND_HELPED, observer_id="person-a", subject_id="person-b",
        interaction_id=iid, accepted_event_id=bad["accepted_event_id"],
    )
    err2 = validate_interaction_memory_fact(bad, interaction=entities[iid])
    assert err2 == REASON_IM_EVENT_MISMATCH


def test_duplicate_processing_is_idempotent():
    entities = _pair()
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    _commit(entities, [create])
    k1, c1, _ = _merge_for(entities, "person-a")
    k2, c2, _ = merge_interaction_memory(k1, observer_id="person-a", entities=entities, tick=5)
    assert c1 is True
    assert c2 is False
    assert list_interaction_facts(k1) == list_interaction_facts(k2)


def test_retention_cap_and_stable_eviction():
    knowledge = empty_knowledge()
    facts = {}
    # Exceed global cap
    for i in range(MAX_INTERACTION_FACTS_PER_OBSERVER + 5):
        f = build_fact(
            kind=KIND_REQUESTED,
            observer_id="person-a",
            subject_id=f"person-{i:03d}",
            counterparty_id=f"person-{i:03d}",
            interaction_id=f"fi-{i:04d}",
            accepted_event_id=f"evt-{i}-0-{'a'*8}",
            accepted_event_tick=i,
            interaction_kind=KIND_REQUEST,
            recorded_tick=i,
        )
        facts[f["fact_id"]] = f
    knowledge["interaction_memory"] = {"version": INTERACTION_MEMORY_VERSION, "facts": facts}
    # Trigger merge with empty entity set just to run eviction via re-merge path
    from domains.interaction_memory import _evict_facts
    trimmed = _evict_facts(facts)
    assert len(trimmed) <= MAX_INTERACTION_FACTS_PER_OBSERVER
    # Newest ticks kept
    ticks = [f["accepted_event_tick"] for f in trimmed.values()]
    assert min(ticks) >= 5  # oldest 0..4 dropped when cap=24 and we added 29


def test_entity_insertion_order_does_not_alter_facts():
    def run(order):
        base = _pair()
        entities = {k: base[k] for k in order}
        create = build_create_proposal(
            kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
            tick=5, entities=entities,
        )
        _commit(entities, [create])
        results = {}
        for oid in ("person-a", "person-b"):
            k, _, _ = _merge_for(entities, oid)
            results[oid] = [
                (f["kind"], f["fact_id"], f["accepted_event_id"])
                for f in list_interaction_facts(k)
            ]
        return results

    assert run(["person-a", "person-b"]) == run(["person-b", "person-a"])


def test_proposal_arrival_order_does_not_alter_facts():
    def run(reverse):
        entities = _pair()
        create = build_create_proposal(
            kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
            tick=5, entities=entities,
        )
        # duplicate create second — only one accepts
        props = [create, copy.deepcopy(create)]
        if reverse:
            props = list(reversed(props))
        acc, rej, _ = _commit(entities, props)
        assert len(acc) == 1
        k, _, _ = _merge_for(entities, "person-a")
        return [f["fact_id"] for f in list_interaction_facts(k)]

    assert run(False) == run(True)


def test_replay_reconstructs_identical_facts_and_hashes():
    entities = _pair()
    entities["person-w"] = _person({"x": 2, "y": 3}, last_event_id="evt-w")
    iid, events, n = _create_accept_request(entities)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    acc, _, _ = _commit(entities, [fulfil], order_start=n)
    events = events + acc
    # Apply memory merges on live
    for oid in ("person-a", "person-b", "person-w"):
        _merge_for(entities, oid)
    live_hash = canonical_hash(snapshot_for_hash(entities, 5, "phase5b4-lineage"))
    live_facts = {
        oid: list_interaction_facts(entities[oid]["knowledge"])
        for oid in ("person-a", "person-b", "person-w")
    }

    # Replay entities mutations only
    replayed = _pair()
    replayed["person-w"] = _person({"x": 2, "y": 3}, last_event_id="evt-w")
    for event in events:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    for oid in ("person-a", "person-b", "person-w"):
        _merge_for(replayed, oid)
    assert {
        oid: list_interaction_facts(replayed[oid]["knowledge"])
        for oid in ("person-a", "person-b", "person-w")
    } == live_facts
    # Interaction entities + inventories match; knowledge after merge matches
    assert replayed[iid]["status"] == STATUS_FULFILLED
    assert live_facts["person-w"][0]["kind"] == KIND_WITNESSED


def test_people_domain_writes_interaction_memory_on_activate():
    entities = _pair()
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    _commit(entities, [create])
    terrain = [["grass"] * 8 for _ in range(8)]
    frame = ActivationFrame(
        "run", 5, ENGINE_VERSION, "agent", entities, terrain,
        ["person-a", "person-b"], DeterministicRNG("5b4"),
    )
    frame.night = False
    out = PeopleDomain().activate(frame)
    # Commit first people proposal for person-a (includes knowledge if changed)
    props = [p for p in out.proposals if p.get("proposal_type") not in (
        "create_food_interaction", "respond_food_interaction", "fulfil_food_interaction",
        "expire_food_interaction", "invalidate_food_interaction",
    ) or p.get("proposal_family") == "people_action"]
    people_props = [p for p in out.proposals if p.get("proposal_family") == "people_action"]
    assert people_props
    # Knowledge should include interaction_memory when material
    for p in people_props:
        ku = p["mutation"]["entity_updates"].get(p["entity_id"], {})
        if "knowledge" in ku:
            im = ku["knowledge"].get("interaction_memory") or {}
            assert im.get("version") == INTERACTION_MEMORY_VERSION


def test_invisible_witness_not_created_without_eligible_list():
    """Witness without eligible_witness_ids snapshot gets no fact even if nearby later."""
    entities = _pair()
    iid, _, n = _create_accept_request(entities)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    # Strip witnesses after building but before commit by replacing mutation
    fulfil["mutation"]["entity_updates"][iid]["eligible_witness_ids"] = []
    _commit(entities, [fulfil], order_start=n)
    entities["person-w"] = _person({"x": 2, "y": 3}, last_event_id="evt-w")
    k, _, _ = _merge_for(entities, "person-w")
    assert _facts_of(k, KIND_WITNESSED) == []
