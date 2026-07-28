"""Capability Stage 6D social action, relationship, and information tests."""
import copy

from core.commit_pipeline import run_commit_frame
from core.mutations import apply_mutation
from domains.base import DomainOutput
from domains.living_agent_actions import build_physical_action_proposal
from domains.living_agent_cognition import perceive_living
from domains.living_agent_contracts import LIMITS, SOCIAL_ACTION_TYPES, empty_living_agent_state
from domains.living_agent_social import (
    advance_commitment_deadlines,
    apply_observed_social_information,
    build_social_action_proposal,
)
from domains.perception import empty_knowledge


def _person(entity_id, position, *, food=0, wood=0):
    return {
        "type": "person", "position": dict(position), "alive": True,
        "health": 900, "energy": 800, "hunger": 400, "thirst": 300,
        "inventory": wood, "food_inventory": food,
        "carried_resources": {"wood": wood, "food": food},
        "inventory_capacity": 30, "carried_item_ids": [],
        "knowledge": empty_knowledge(),
        "living_agent": empty_living_agent_state(entity_id, 0),
        "last_event_id": f"evt-{entity_id}",
    }


def _terrain(size=9):
    return [["grass"] * size for _ in range(size)]


def _plan(action):
    return {
        "plan_id": f"plan-{action}", "goal_id": f"goal-{action}",
        "goal": action.upper(), "step_index": 0,
    }


def _commit(entities, proposal, tick, order=0):
    return run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], tick,
        "lineage", "run", order, f"frame-{tick}",
    )


def test_required_social_action_vocabulary_is_explicit():
    assert {
        "request_help", "offer_help", "cooperate", "refuse", "warn",
        "share_information", "conceal_information", "lie", "give", "trade",
        "threaten", "apologise", "promise", "repay", "confront", "compete",
        "reconcile",
    } <= SOCIAL_ACTION_TYPES


def test_direct_cooperation_changes_only_participant_relationships_and_forms_debt():
    entities = {
        "person-a": _person("person-a", {"x": 1, "y": 1}),
        "person-b": _person("person-b", {"x": 2, "y": 1}),
        "person-c": _person("person-c", {"x": 7, "y": 7}),
    }
    proposal = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-b", plan=_plan("cooperate"),
    )
    accepted, rejected, _ = _commit(entities, proposal, 1)

    assert not rejected and accepted
    relation = entities["person-b"]["living_agent"]["relationships"]["person-a"]
    assert relation["trust"] > 0
    assert relation["perceived_reliability"] > 0
    assert accepted[0]["id"] in relation["causal_event_ids"]
    debts = entities["person-b"]["living_agent"]["commitments"].values()
    assert any(item["commitment_kind"] == "debt" and item["status"] == "active" for item in debts)
    assert entities["person-c"]["living_agent"]["relationships"] == {}


def test_witnessed_threat_changes_witness_but_unwitnessed_entity_does_not_react():
    entities = {
        "person-a": _person("person-a", {"x": 2, "y": 2}),
        "person-b": _person("person-b", {"x": 3, "y": 2}),
        "person-w": _person("person-w", {"x": 2, "y": 4}),
        "person-u": _person("person-u", {"x": 8, "y": 8}),
    }
    threat = build_social_action_proposal(
        entities, actor_id="person-a", action_type="threaten", tick=1,
        target_id="person-b", plan=_plan("threaten"),
    )
    accepted, rejected, _ = _commit(entities, threat, 1)
    assert not rejected and accepted

    witness_delta = perceive_living(
        "person-w", entities["person-w"], entities, _terrain(), 2,
    )
    witness_state, _knowledge, consequences, _ = apply_observed_social_information(
        entities["person-w"]["living_agent"], entities["person-w"]["knowledge"],
        observer_id="person-w", observations=witness_delta["observations"], tick=2,
    )
    assert consequences
    assert witness_state["relationships"]["person-a"]["fear"] > 0

    unwitnessed_delta = perceive_living(
        "person-u", entities["person-u"], entities, _terrain(), 2,
    )
    unwitnessed_state, _knowledge, consequences, _ = apply_observed_social_information(
        entities["person-u"]["living_agent"], entities["person-u"]["knowledge"],
        observer_id="person-u", observations=unwitnessed_delta["observations"], tick=2,
    )
    assert consequences == []
    assert unwitnessed_state["relationships"] == {}


def test_lie_does_not_leak_deception_and_later_contradiction_harms_reliability():
    entities = {
        "person-liar": _person("person-liar", {"x": 1, "y": 1}),
        "person-target": _person("person-target", {"x": 2, "y": 1}),
        "person-corrector": _person("person-corrector", {"x": 2, "y": 2}),
    }
    false_claim = {
        "claim": {
            "subject_id": "storage-1", "fact_type": "storage",
            "properties": {"open": True, "access": "public"}, "confidence": 700,
        }
    }
    lie = build_social_action_proposal(
        entities, actor_id="person-liar", action_type="lie", tick=1,
        target_id="person-target", plan=_plan("lie"), message=false_claim,
    )
    accepted, rejected, order = _commit(entities, lie, 1)
    assert not rejected and accepted
    target_facts = entities["person-target"]["knowledge"]["facts"]
    lie_fact = next(fact for fact in target_facts.values() if fact.get("source_entity_id") == "person-liar")
    assert lie_fact["deceptive_source_claim"] is False
    assert lie_fact["source_event_id"] == accepted[0]["id"]
    before_reliability = entities["person-target"]["living_agent"]["relationships"]["person-liar"]["perceived_reliability"]

    correction = build_social_action_proposal(
        entities, actor_id="person-corrector", action_type="share_information", tick=2,
        target_id="person-target", plan=_plan("correct"),
        message={"claim": {
            "subject_id": "storage-1", "fact_type": "storage",
            "properties": {"open": False, "access": "private"}, "confidence": 950,
        }},
    )
    accepted2, rejected2, _ = _commit(entities, correction, 2, order)
    assert not rejected2 and accepted2
    liar_relation = entities["person-target"]["living_agent"]["relationships"]["person-liar"]
    assert liar_relation["perceived_reliability"] < before_reliability
    assert liar_relation["resentment"] > 0


def test_promise_completion_and_broken_deadline_are_explicit():
    entities = {
        "person-a": _person("person-a", {"x": 1, "y": 1}),
        "person-b": _person("person-b", {"x": 2, "y": 1}),
    }
    promise = build_social_action_proposal(
        entities, actor_id="person-a", action_type="promise", tick=1,
        target_id="person-b", plan=_plan("promise"),
        obligation="repair the shelter", due_tick=3,
    )
    accepted, rejected, order = _commit(entities, promise, 1)
    assert not rejected and accepted
    commitment = next(iter(entities["person-a"]["living_agent"]["commitments"].values()))
    assert commitment["status"] == "active"
    assert commitment["created_event_id"] == accepted[0]["id"]

    repay = build_social_action_proposal(
        entities, actor_id="person-a", action_type="repay", tick=2,
        target_id="person-b", plan=_plan("repay"),
    )
    accepted2, rejected2, _ = _commit(entities, repay, 2, order)
    assert not rejected2 and accepted2
    completed = entities["person-a"]["living_agent"]["commitments"][commitment["commitment_id"]]
    assert completed["status"] == "completed"
    assert completed["completed_tick"] == 2

    fresh = empty_living_agent_state("person-a", 0)
    fresh["commitments"][commitment["commitment_id"]] = {
        **commitment, "status": "active", "due_tick": 1,
    }
    overdue, consequences = advance_commitment_deadlines(fresh, owner_id="person-a", tick=3)
    assert overdue["commitments"][commitment["commitment_id"]]["status"] == "broken"
    assert consequences[0]["kind"] == "broken_promise"


def test_refusal_apology_and_reconciliation_move_distinct_dimensions():
    entities = {
        "person-a": _person("person-a", {"x": 1, "y": 1}),
        "person-b": _person("person-b", {"x": 2, "y": 1}),
    }
    order = 0
    for tick, action in enumerate(("refuse", "apologise", "reconcile"), start=1):
        proposal = build_social_action_proposal(
            entities, actor_id="person-a", action_type=action, tick=tick,
            target_id="person-b", plan=_plan(action),
        )
        accepted, rejected, order = _commit(entities, proposal, tick, order)
        assert accepted and not rejected
    relation = entities["person-b"]["living_agent"]["relationships"]["person-a"]
    assert relation["familiarity"] > 0
    assert relation["trust"] > 0
    assert relation["resentment"] < 60


def test_trade_is_conserving_and_replay_safe():
    initial = {
        "person-a": _person("person-a", {"x": 1, "y": 1}, food=2),
        "person-b": _person("person-b", {"x": 2, "y": 1}, wood=2),
    }
    entities = copy.deepcopy(initial)
    proposal = build_social_action_proposal(
        entities, actor_id="person-a", action_type="trade", tick=1,
        target_id="person-b", plan=_plan("trade"),
        message={"trade": {"offer_kind": "food", "request_kind": "wood", "quantity": 1}},
    )
    accepted, rejected, _ = _commit(entities, proposal, 1)
    assert not rejected and accepted
    assert entities["person-a"]["carried_resources"] == {"wood": 1, "food": 1}
    assert entities["person-b"]["carried_resources"] == {"wood": 1, "food": 1}

    replayed = copy.deepcopy(initial)
    apply_mutation(replayed, copy.deepcopy(accepted[0]["mutation"]))
    assert replayed == entities


def test_tampered_propagation_and_exchange_reject_without_mutation():
    entities = {
        "person-a": _person("person-a", {"x": 1, "y": 1}, food=2),
        "person-b": _person("person-b", {"x": 2, "y": 1}, wood=2),
    }
    proposal = build_social_action_proposal(
        entities, actor_id="person-a", action_type="trade", tick=1,
        target_id="person-b", plan=_plan("trade"),
        message={"trade": {"offer_kind": "food", "request_kind": "wood", "quantity": 1}},
    )
    proposal["social_action"]["recipient_ids"] = [f"person-{i}" for i in range(LIMITS.social_propagation_recipients + 1)]
    before = copy.deepcopy(entities)
    accepted, rejected, _ = _commit(entities, proposal, 1)
    assert not accepted
    assert rejected[0]["reason_code"] == "social_action.recipient_limit"
    assert entities == before


def test_concealment_does_not_create_information_route_or_bystander_reaction():
    entities = {
        "person-a": _person("person-a", {"x": 1, "y": 1}),
        "person-b": _person("person-b", {"x": 2, "y": 1}),
    }
    proposal = build_social_action_proposal(
        entities, actor_id="person-a", action_type="conceal_information", tick=1,
        target_id="person-b", plan=_plan("conceal"),
        message={"claim": {"subject_id": "water", "fact_type": "water", "properties": {"safe": False}}},
    )
    accepted, rejected, _ = _commit(entities, proposal, 1)
    assert accepted and not rejected
    assert accepted[0]["social_action"]["information_route"] == "concealed"
    assert not any(entity.get("type") == "signal" for entity in entities.values())
    assert entities["person-b"]["knowledge"] == empty_knowledge()


def test_two_social_actions_on_the_same_person_in_one_frame_both_commit():
    """Active Leg A regression: a social action must not be discarded because
    an unrelated field of a participant changed in the same frame.

    The verified defect: person-007 selects WARN_DANGER (social_warn toward
    person-004) in the same tick that person-001 commits social_cooperate on
    person-007. build_social_action_proposal used to pin each participant's
    whole living_agent blob as an eq precondition, so whichever proposal
    committed first changed person-007's blob and the other was discarded at
    commit_revalidation with precondition.failed / living_agent_eq_failed --
    100% of early-tick rejections -- even though the two actions write
    provably disjoint relationship records (person-007's own warn writes
    relationships[person-004]; the cooperate writes relationships[person-001]
    plus one debt commitment).
    """
    entities = {
        "person-007": _person("person-007", {"x": 1, "y": 1}),
        "person-001": _person("person-001", {"x": 2, "y": 1}),
        "person-004": _person("person-004", {"x": 1, "y": 2}),
    }
    warn = build_social_action_proposal(
        entities, actor_id="person-007", action_type="warn", tick=1,
        target_id="person-004", plan=_plan("warn"),
        message={"claim": {
            "subject_id": "wolf-1", "fact_type": "animal",
            "properties": {"hostile": True}, "confidence": 800,
        }},
    )
    cooperate = build_social_action_proposal(
        entities, actor_id="person-001", action_type="cooperate", tick=1,
        target_id="person-007", plan=_plan("cooperate"),
    )
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[warn, cooperate])], 1,
        "lineage", "run", 0, "frame-1",
    )

    # Both must commit: no living_agent_eq_failed discard (and therefore, in
    # the live world, no silent replan of person-007's WARN_DANGER to
    # REPAY_DEBT on the following ticks).
    assert rejected == []
    assert len(accepted) == 2

    # Each action's own relationship consequence lands on disjoint records.
    assert entities["person-007"]["living_agent"]["relationships"]["person-004"]["last_cause"] == "warn"
    assert entities["person-004"]["living_agent"]["relationships"]["person-007"]["last_cause"] == "warn"
    assert entities["person-001"]["living_agent"]["relationships"]["person-007"]["last_cause"] == "cooperate"
    debts = entities["person-001"]["living_agent"]["commitments"].values()
    assert any(item["commitment_kind"] == "debt" and item["status"] == "active" for item in debts)


def test_reciprocal_social_pair_in_one_frame_fails_once_with_the_record_named():
    """Active Leg A, genuine-collision half: person-007 warns person-001 while
    person-001 cooperates on person-007 in the SAME frame (the verified tick-2
    case). Both actions modify BOTH relationship records --
    007.relationships[person-001] and 001.relationships[person-007] -- so this
    is a real write conflict, not the false positive: exactly one proposal
    commits, and the other fails explicitly at commit_revalidation with the
    record path named in reason_detail -- never the old undiagnosable
    whole-blob `living_agent_eq_failed`, and never both-commit-silently (which
    would lose one side's relationship deltas with no retry)."""
    entities = {
        "person-007": _person("person-007", {"x": 1, "y": 1}),
        "person-001": _person("person-001", {"x": 2, "y": 1}),
    }
    warn = build_social_action_proposal(
        entities, actor_id="person-007", action_type="warn", tick=1,
        target_id="person-001", plan=_plan("warn"),
        message={"claim": {
            "subject_id": "wolf-1", "fact_type": "animal",
            "properties": {"hostile": True}, "confidence": 800,
        }},
    )
    cooperate = build_social_action_proposal(
        entities, actor_id="person-001", action_type="cooperate", tick=1,
        target_id="person-007", plan=_plan("cooperate"),
    )
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[warn, cooperate])], 1,
        "lineage", "run", 0, "frame-1",
    )

    assert len(accepted) == 1
    assert len(rejected) == 1
    rejection = rejected[0]
    assert rejection["rejection_stage"] == "commit_revalidation"
    assert rejection["reason_code"] == "precondition.failed"
    assert rejection["reason_detail"] != "living_agent_eq_failed"
    assert rejection["reason_detail"].startswith("living_agent.relationships.")
    assert rejection["reason_detail"].endswith("_eq_failed")

    # The survivor's effects are complete on both participants: its own
    # relationship consequence on each side plus, for cooperate, the debt.
    survivor = accepted[0]["social_action"]
    actor_blob = entities[survivor["actor_id"]]["living_agent"]
    target_blob = entities[survivor["target_id"]]["living_agent"]
    assert actor_blob["relationships"][survivor["target_id"]]["last_cause"] == survivor["action_type"]
    assert target_blob["relationships"][survivor["actor_id"]]["last_cause"] == survivor["action_type"]


def test_social_action_fails_named_when_a_participant_dies_mid_frame():
    """Acceptance: participant dies mid-frame -> explicit failure, named. The
    alive pin on both participants is what remains of the old blob CAS, and it
    must keep firing."""
    entities = {
        "person-a": _person("person-a", {"x": 1, "y": 1}),
        "person-b": _person("person-b", {"x": 2, "y": 1}),
    }
    proposal = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-b", plan=_plan("cooperate"),
    )
    # Another committed proposal kills the target before this one revalidates.
    entities["person-b"]["alive"] = False
    accepted, rejected, _ = _commit(entities, proposal, 1)
    assert not accepted
    assert rejected[0]["reason_code"] == "precondition.failed"
    assert rejected[0]["reason_detail"] == "alive_eq_failed"


def test_physical_action_on_a_social_participant_does_not_block_the_social_action():
    """Acceptance: physical action on a participant of a social action -> both
    survive. Physical proposals pin alive only, so a person can be helped and
    still gather in the same frame."""
    entities = {
        "person-a": _person("person-a", {"x": 1, "y": 1}),
        "person-b": _person("person-b", {"x": 2, "y": 1}),
    }
    cooperate = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-b", plan=_plan("cooperate"),
    )
    rest = build_physical_action_proposal(
        entities, actor_id="person-b", action_type="rest", tick=1,
    )
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[cooperate, rest])], 1,
        "lineage", "run", 0, "frame-1",
    )
    assert rejected == []
    assert len(accepted) == 2
    relation = entities["person-a"]["living_agent"]["relationships"]["person-b"]
    assert relation["last_cause"] == "cooperate"
