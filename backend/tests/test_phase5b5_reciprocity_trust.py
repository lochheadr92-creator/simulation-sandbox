"""Phase 5B5 — Derived reciprocity and trust (reciprocity-trust-v1)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.commit_pipeline import run_commit_frame
from core.constants import CRITICAL_THRESHOLD, FOOD_TRANSFER_SURPLUS
from core.food_interaction import (
    KIND_OFFER,
    KIND_REQUEST,
    RESPONSE_ACCEPT,
    RESPONSE_REFUSE,
    STATUS_ACCEPTED,
    STATUS_FULFILLED,
)
from core.hashing import canonical_hash
from core.mutations import apply_mutation
from domains.base import DomainOutput
from domains.food_interaction_proposals import (
    build_create_proposal,
    build_expire_proposal,
    build_fulfil_proposal,
    build_invalidate_proposal,
    build_respond_proposal,
    _responder_should_accept,
)
from domains.interaction_memory import (
    KIND_HELPED,
    KIND_OFFERED,
    KIND_REFUSED,
    KIND_REQUESTED,
    KIND_WITNESSED,
    build_fact,
    list_interaction_facts,
    merge_interaction_memory,
)
from domains.perception import SOCIAL_OBSERVATION_VERSION, empty_knowledge
from domains.reciprocity_trust import (
    CAUTION_AUTO_REFUSE_THRESHOLD,
    DECAY_PER_TICK,
    RECIPROCITY_TRUST_VERSION,
    SCORE_MAX,
    caution_score_for,
    derive_subject_view,
    list_subject_views,
    should_auto_accept_with_caution,
    support_score_for,
)
from domains.people_utility import eligible_food_recipient


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


def _person(position, *, hunger=100, food=0, knowledge=None, last_event_id=None, alive=True):
    p = {
        "type": "person",
        "position": dict(position),
        "alive": alive,
        "hunger": hunger,
        "thirst": 100,
        "energy": 900,
        "inventory": 0,
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
    a_k, b_k = empty_knowledge(), empty_knowledge()
    a_k["known_people"]["person-b"] = _social_obs(
        "person-b", appears_to_carry_food=True, tick=tick, pos={"x": 3, "y": 2},
    )
    b_k["known_people"]["person-a"] = _social_obs(
        "person-a", apparent_urgent_need="critical", tick=tick, pos={"x": 2, "y": 2},
    )
    return {
        "person-a": _person({"x": 2, "y": 2}, hunger=CRITICAL_THRESHOLD, knowledge=a_k, last_event_id="ea"),
        "person-b": _person({"x": 3, "y": 2}, food=FOOD_TRANSFER_SURPLUS, knowledge=b_k, last_event_id="eb"),
    }


def _commit(entities, proposals, tick=5, order_start=0):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))],
        tick, "phase5b5-lineage", "run-5b5", order_start, f"frame-{tick}",
    )


def _merge(entities, oid, tick=5):
    k, _, _ = merge_interaction_memory(
        entities[oid].get("knowledge") or empty_knowledge(),
        observer_id=oid, entities=entities, tick=tick,
    )
    entities[oid]["knowledge"] = k
    return k


def _fulfil_lifecycle(entities, tick=5):
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=tick, entities=entities,
    )
    acc, _, n = _commit(entities, [create], tick=tick)
    iid = acc[0]["interaction"]["interaction_id"]
    resp = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=tick, entities=entities,
    )
    _, _, n = _commit(entities, [resp], tick=tick, order_start=n)
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=tick, entities=entities)
    acc_f, rej, n = _commit(entities, [fulfil], tick=tick, order_start=n)
    assert rej == [] and entities[iid]["status"] == STATUS_FULFILLED
    return iid, acc + acc_f, n


def _inject_fact(knowledge, fact):
    im = knowledge.setdefault("interaction_memory", {"version": "interaction-memory-v1", "facts": {}})
    im["facts"][fact["fact_id"]] = fact
    return knowledge


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_identical_fact_histories_and_ticks_produce_identical_signals():
    k = empty_knowledge()
    f = build_fact(
        kind=KIND_HELPED, observer_id="a", subject_id="b", counterparty_id="b",
        interaction_id="fi-1", accepted_event_id="evt-10-0-aaaaaaaa",
        accepted_event_tick=10, interaction_kind=KIND_REQUEST, recorded_tick=10,
    )
    _inject_fact(k, f)
    v1 = derive_subject_view(k, observer_id="a", subject_id="b", current_tick=12)
    v2 = derive_subject_view(copy.deepcopy(k), observer_id="a", subject_id="b", current_tick=12)
    assert v1 == v2
    assert v1["version"] == RECIPROCITY_TRUST_VERSION
    assert v1["derived"] is True
    assert v1["canonical"] is False


def test_entity_and_fact_insertion_order_do_not_change_signals():
    facts = [
        build_fact(
            kind=KIND_HELPED, observer_id="a", subject_id="b", counterparty_id="b",
            interaction_id="fi-1", accepted_event_id="evt-5-0-aaaaaaaa",
            accepted_event_tick=5, interaction_kind=KIND_REQUEST, recorded_tick=5,
        ),
        build_fact(
            kind=KIND_REFUSED, observer_id="a", subject_id="b", counterparty_id="b",
            interaction_id="fi-2", accepted_event_id="evt-6-0-bbbbbbbb",
            accepted_event_tick=6, interaction_kind=KIND_REQUEST, recorded_tick=6,
        ),
    ]

    def view(order):
        k = empty_knowledge()
        for f in order:
            _inject_fact(k, f)
        return derive_subject_view(k, observer_id="a", subject_id="b", current_tick=10)

    assert view(facts) == view(list(reversed(facts)))


def test_direct_help_positive_support():
    entities = _pair()
    _fulfil_lifecycle(entities)
    k = _merge(entities, "person-a")
    view = derive_subject_view(k, observer_id="person-a", subject_id="person-b", current_tick=5)
    assert view["support_score"] > 0
    assert view["fact_counts"]["helped"] == 1


def test_accepted_refusal_produces_caution():
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
    _commit(entities, [refuse], order_start=n)
    k = _merge(entities, "person-a")
    view = derive_subject_view(k, observer_id="person-a", subject_id="person-b", current_tick=5)
    assert view["caution_score"] > 0
    assert view["fact_counts"]["refused"] == 1


def test_expiry_does_not_count_as_refusal():
    entities = _pair(tick=10)
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=10, entities=entities,
    )
    acc, _, n = _commit(entities, [create], tick=10)
    iid = acc[0]["interaction"]["interaction_id"]
    exp = entities[iid]["expires_tick"]
    expire = build_expire_proposal(
        interaction=entities[iid], tick=exp, entity_id="person-a", entities=entities,
    )
    _commit(entities, [expire], tick=exp, order_start=n)
    k = _merge(entities, "person-a", tick=exp)
    view = derive_subject_view(k, observer_id="person-a", subject_id="person-b", current_tick=exp)
    assert view["caution_score"] == 0
    assert view["fact_counts"]["refused"] == 0


def test_invalidation_does_not_count_as_refusal():
    entities = _pair()
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    acc, _, n = _commit(entities, [create])
    iid = acc[0]["interaction"]["interaction_id"]
    resp = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
    )
    _, _, n = _commit(entities, [resp], order_start=n)
    entities["person-b"]["food_inventory"] = 0
    inv = build_invalidate_proposal(
        interaction=entities[iid], tick=5, entity_id="person-a",
        entities=entities, reason="food_interaction.lost_supply",
    )
    _commit(entities, [inv], order_start=n)
    k = _merge(entities, "person-a")
    view = derive_subject_view(k, observer_id="person-a", subject_id="person-b", current_tick=5)
    assert view["caution_score"] == 0
    assert view["support_score"] == 0  # no help


def test_accepted_unfulfilled_not_help():
    entities = _pair()
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    acc, _, n = _commit(entities, [create])
    iid = acc[0]["interaction"]["interaction_id"]
    resp = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
    )
    _commit(entities, [resp], order_start=n)
    assert entities[iid]["status"] == STATUS_ACCEPTED
    k = _merge(entities, "person-a")
    view = derive_subject_view(k, observer_id="person-a", subject_id="person-b", current_tick=5)
    assert view["support_score"] == 0
    assert view["fact_counts"]["helped"] == 0


def test_witnessed_weaker_than_direct_help():
    tick = 5
    k_help = empty_knowledge()
    k_wit = empty_knowledge()
    _inject_fact(k_help, build_fact(
        kind=KIND_HELPED, observer_id="a", subject_id="b", counterparty_id="b",
        interaction_id="fi-h", accepted_event_id="evt-5-0-aaaaaaaa",
        accepted_event_tick=tick, interaction_kind=KIND_REQUEST, recorded_tick=tick,
    ))
    _inject_fact(k_wit, build_fact(
        kind=KIND_WITNESSED, observer_id="a", subject_id="b", counterparty_id="c",
        interaction_id="fi-w", accepted_event_id="evt-5-0-bbbbbbbb",
        accepted_event_tick=tick, interaction_kind=KIND_REQUEST, recorded_tick=tick,
    ))
    s_help = derive_subject_view(k_help, observer_id="a", subject_id="b", current_tick=tick)["support_score"]
    s_wit = derive_subject_view(k_wit, observer_id="a", subject_id="b", current_tick=tick)["support_score"]
    assert s_help > s_wit > 0


def test_request_or_offer_alone_not_help():
    k = empty_knowledge()
    _inject_fact(k, build_fact(
        kind=KIND_REQUESTED, observer_id="a", subject_id="b", counterparty_id="b",
        interaction_id="fi-r", accepted_event_id="evt-5-0-aaaaaaaa",
        accepted_event_tick=5, interaction_kind=KIND_REQUEST, recorded_tick=5,
    ))
    _inject_fact(k, build_fact(
        kind=KIND_OFFERED, observer_id="a", subject_id="b", counterparty_id="b",
        interaction_id="fi-o", accepted_event_id="evt-5-0-bbbbbbbb",
        accepted_event_tick=5, interaction_kind=KIND_OFFER, recorded_tick=5,
    ))
    view = derive_subject_view(k, observer_id="a", subject_id="b", current_tick=5)
    assert view["support_score"] == 0
    assert view["confidence_score"] > 0


def test_recency_uses_canonical_ticks_and_decays():
    k = empty_knowledge()
    _inject_fact(k, build_fact(
        kind=KIND_HELPED, observer_id="a", subject_id="b", counterparty_id="b",
        interaction_id="fi-1", accepted_event_id="evt-1-0-aaaaaaaa",
        accepted_event_tick=1, interaction_kind=KIND_REQUEST, recorded_tick=1,
    ))
    fresh = derive_subject_view(k, observer_id="a", subject_id="b", current_tick=1)["support_score"]
    old = derive_subject_view(k, observer_id="a", subject_id="b", current_tick=1 + 60)["support_score"]
    assert fresh > old
    # fully decayed
    dead = derive_subject_view(
        k, observer_id="a", subject_id="b", current_tick=1 + (100 // DECAY_PER_TICK) + 1,
    )["support_score"]
    assert dead == 0


def test_scores_remain_bounded():
    k = empty_knowledge()
    for i in range(30):
        _inject_fact(k, build_fact(
            kind=KIND_HELPED, observer_id="a", subject_id="b", counterparty_id="b",
            interaction_id=f"fi-{i}", accepted_event_id=f"evt-{i}-0-{'a'*8}",
            accepted_event_tick=100, interaction_kind=KIND_REQUEST, recorded_tick=100,
        ))
    view = derive_subject_view(k, observer_id="a", subject_id="b", current_tick=100)
    assert 0 <= view["support_score"] <= SCORE_MAX
    assert 0 <= view["caution_score"] <= SCORE_MAX
    assert 0 <= view["confidence_score"] <= SCORE_MAX
    assert -SCORE_MAX <= view["reciprocity_net"] <= SCORE_MAX


def test_missing_evidence_is_neutral():
    k = empty_knowledge()
    view = derive_subject_view(k, observer_id="a", subject_id="unknown", current_tick=5)
    assert view["support_score"] == 0
    assert view["caution_score"] == 0
    assert view["confidence_score"] == 0
    assert view["reciprocity_net"] == 0


def test_directional_views_can_differ():
    # A was helped by B; B has no helped fact about A
    k_a = empty_knowledge()
    k_b = empty_knowledge()
    _inject_fact(k_a, build_fact(
        kind=KIND_HELPED, observer_id="a", subject_id="b", counterparty_id="b",
        interaction_id="fi-1", accepted_event_id="evt-5-0-aaaaaaaa",
        accepted_event_tick=5, interaction_kind=KIND_REQUEST, recorded_tick=5,
    ))
    _inject_fact(k_b, build_fact(
        kind=KIND_HELPED, observer_id="b", subject_id="a", counterparty_id="a",
        interaction_id="fi-1", accepted_event_id="evt-5-0-aaaaaaaa",
        accepted_event_tick=5, interaction_kind=KIND_REQUEST, recorded_tick=5,
    ))
    # Add refusal only on B's view of A
    _inject_fact(k_b, build_fact(
        kind=KIND_REFUSED, observer_id="b", subject_id="a", counterparty_id="a",
        interaction_id="fi-2", accepted_event_id="evt-6-0-bbbbbbbb",
        accepted_event_tick=6, interaction_kind=KIND_REQUEST, recorded_tick=6,
    ))
    va = derive_subject_view(k_a, observer_id="a", subject_id="b", current_tick=6)
    vb = derive_subject_view(k_b, observer_id="b", subject_id="a", current_tick=6)
    assert va != vb
    assert vb["caution_score"] > va["caution_score"]


def test_projection_rebuild_is_pure_and_does_not_mutate_facts():
    k = empty_knowledge()
    f = build_fact(
        kind=KIND_HELPED, observer_id="a", subject_id="b", counterparty_id="b",
        interaction_id="fi-1", accepted_event_id="evt-5-0-aaaaaaaa",
        accepted_event_tick=5, interaction_kind=KIND_REQUEST, recorded_tick=5,
    )
    _inject_fact(k, f)
    before = copy.deepcopy(list_interaction_facts(k))
    v1 = derive_subject_view(k, observer_id="a", subject_id="b", current_tick=5)
    v2 = derive_subject_view(k, observer_id="a", subject_id="b", current_tick=5)
    assert v1 == v2
    assert list_interaction_facts(k) == before


def test_replay_lifecycle_then_projection_matches():
    entities = _pair()
    iid, events, n = _fulfil_lifecycle(entities)
    for oid in ("person-a", "person-b"):
        _merge(entities, oid)
    live = derive_subject_view(
        entities["person-a"]["knowledge"],
        observer_id="person-a", subject_id="person-b", current_tick=5,
    )

    replayed = _pair()
    for event in events:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    _merge(replayed, "person-a")
    rebuilt = derive_subject_view(
        replayed["person-a"]["knowledge"],
        observer_id="person-a", subject_id="person-b", current_tick=5,
    )
    assert live == rebuilt


def test_behavioural_influence_stable_recipient_ordering():
    # Two eligible recipients; higher support preferred then id
    giver = _person({"x": 2, "y": 2}, food=FOOD_TRANSFER_SURPLUS)
    giver["id"] = "giver"
    k = empty_knowledge()
    _inject_fact(k, build_fact(
        kind=KIND_HELPED, observer_id="giver", subject_id="person-z", counterparty_id="person-z",
        interaction_id="fi-z", accepted_event_id="evt-5-0-aaaaaaaa",
        accepted_event_tick=5, interaction_kind=KIND_REQUEST, recorded_tick=5,
    ))
    giver["knowledge"] = k
    entities = {
        "giver": giver,
        "person-a": _person({"x": 3, "y": 2}, hunger=CRITICAL_THRESHOLD),
        "person-z": _person({"x": 2, "y": 3}, hunger=CRITICAL_THRESHOLD),
    }
    delta = {
        "person_sightings": {
            "person-a": {"position": {"x": 3, "y": 2}},
            "person-z": {"position": {"x": 2, "y": 3}},
        },
    }
    # person-z has support, person-a does not → z wins despite id order
    assert eligible_food_recipient(giver, giver["position"], entities, delta, tick=5) == "person-z"
    # Without support, id order: person-a
    giver2 = _person({"x": 2, "y": 2}, food=FOOD_TRANSFER_SURPLUS)
    giver2["id"] = "giver"
    giver2["knowledge"] = empty_knowledge()
    assert eligible_food_recipient(giver2, giver2["position"], entities, delta, tick=5) == "person-a"


def test_caution_blocks_auto_accept_not_hard_eligibility():
    entities = _pair()
    # Build accepted-request interaction entity path
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    acc, _, n = _commit(entities, [create])
    iid = acc[0]["interaction"]["interaction_id"]
    # Inject high caution on responder about initiator
    k = empty_knowledge()
    for i in range(5):
        _inject_fact(k, build_fact(
            kind=KIND_REFUSED, observer_id="person-b", subject_id="person-a",
            counterparty_id="person-a", interaction_id=f"fi-{i}",
            accepted_event_id=f"evt-5-{i}-{'b'*8}",
            accepted_event_tick=5, interaction_kind=KIND_REQUEST, recorded_tick=5,
        ))
    entities["person-b"]["knowledge"] = k
    caution = caution_score_for(k, "person-b", "person-a", 5)
    assert caution >= CAUTION_AUTO_REFUSE_THRESHOLD
    assert _responder_should_accept(entities, entities[iid], tick=5) is False
    # Without tick/caution path, hard eligibility alone still true
    assert _responder_should_accept(entities, entities[iid], tick=None) is True


def test_core_still_rejects_invalid_fulfil_regardless_of_trust():
    entities = _pair()
    create = build_create_proposal(
        kind=KIND_REQUEST, initiator_id="person-a", responder_id="person-b",
        tick=5, entities=entities,
    )
    acc, _, n = _commit(entities, [create])
    iid = acc[0]["interaction"]["interaction_id"]
    resp = build_respond_proposal(
        interaction=entities[iid], response=RESPONSE_ACCEPT, tick=5, entities=entities,
    )
    _, _, n = _commit(entities, [resp], order_start=n)
    entities["person-b"]["food_inventory"] = 0  # lose supply
    # High support would not allow invalid transfer
    k = empty_knowledge()
    _inject_fact(k, build_fact(
        kind=KIND_HELPED, observer_id="person-b", subject_id="person-a",
        counterparty_id="person-a", interaction_id="fi-old",
        accepted_event_id="evt-1-0-aaaaaaaa", accepted_event_tick=1,
        interaction_kind=KIND_REQUEST, recorded_tick=1,
    ))
    entities["person-b"]["knowledge"] = k
    fulfil = build_fulfil_proposal(interaction=entities[iid], tick=5, entities=entities)
    acc_f, rej, _ = _commit(entities, [fulfil], order_start=n)
    assert acc_f == [] and rej
    assert entities["person-a"]["food_inventory"] == 0


def test_no_canonical_mutable_trust_field_on_entities():
    entities = _pair()
    _fulfil_lifecycle(entities)
    for oid in ("person-a", "person-b"):
        _merge(entities, oid)
        assert "trust" not in entities[oid]
        assert "reciprocity" not in entities[oid]
        view = derive_subject_view(
            entities[oid]["knowledge"], observer_id=oid,
            subject_id="person-b" if oid == "person-a" else "person-a",
            current_tick=5,
        )
        assert view["derived"] is True
