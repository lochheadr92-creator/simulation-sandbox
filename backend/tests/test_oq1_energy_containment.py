"""OQ-1 containment: a stale physical-action energy write must fail closed.

Evidence: memory/evidence/layer-a-living-agent-cas/OQ1-ENERGY-COLLISION-RESOLUTION.md

CONTAINMENT, NOT COMPOSITION. These tests assert that a committed `cooperate`
energy benefit is NOT silently erased by a later same-frame physical write built
from the stale frame-start value. They deliberately do NOT assert the composed
result (565 + 40 - 5 = 600, or 565 + 40 + 75 = 680): composition is not
implemented and is not authorised.
"""
import copy

from core.commit_pipeline import run_commit_frame
from core.constants import EFFORT_TRANSFER_TARGET_ENERGY_GAIN
from domains.base import DomainOutput
from domains.living_agent_social import build_social_action_proposal


LINEAGE = "oq1-containment"


def _person(eid: str, energy: int, x: int = 5, y: int = 5) -> dict:
    return {
        "id": eid, "type": "person", "alive": True,
        "position": {"x": x, "y": y},
        "energy": energy, "hunger": 300, "thirst": 300, "health": 1000,
        "carried_resources": {"food": 0, "wood": 0},
        "living_agent": {"schema_version": "living-agent-v1", "relationships": {},
                         "commitments": {}, "wants": {}, "memories": {},
                         "decision_history": [], "causal_links": []},
        "knowledge": {"facts": {}, "known_tiles": []},
    }


def _stale_energy_proposal(actor_id: str, stale_energy: int, tick: int,
                           delta: int = -5) -> dict:
    """A minimal physical-shaped proposal carrying the OQ-1 pattern:

    an ABSOLUTE energy write computed from `stale_energy` (the frame-start read)
    plus the containment precondition pinning that same frame-start value.
    """
    return {
        "proposal_family": "living_action",
        "proposal_type": "living_action",
        "proposer_engine_id": "living_settlement",
        "proposer_engine_version": "test",
        "entity_id": actor_id,
        # Exogenous so the frame's causality guard does not reject this before
        # preconditions are evaluated -- these tests must exercise the ENERGY
        # precondition, not `causality.missing_parent`.
        "causal_parent_event_ids": [],
        "is_exogenous": True,
        "requested_time": tick,
        "phase": "agent",
        # Higher than the social proposal's 10 so the frame commits `cooperate`
        # FIRST and this stale write second -- the ordering measured in all 97
        # real collisions (social_cooperate wins, the physical write clobbers).
        # Without this the two tie on order_key and content_hash decides, which
        # can silently invert the case under test.
        "engine_priority": 20,
        "touched_scope": [actor_id],
        "preconditions": [
            {"entity_id": actor_id, "field": "alive", "op": "eq", "value": True},
            # The containment precondition under test.
            {"entity_id": actor_id, "field": "energy", "op": "eq",
             "value": stale_energy},
        ],
        "mutation": {"entity_updates": {
            actor_id: {"energy": max(0, stale_energy + delta)},
        }, "new_entities": {}},
        "explanation": "stale-base physical energy write",
    }


def _frame(entities, proposals, tick):
    return run_commit_frame(
        entities, [DomainOutput(proposals=proposals)], tick, LINEAGE,
        "run-oq1", 0, f"frame-{tick}",
    )


# --- 1. cooperate writes +40 -------------------------------------------------

def test_cooperate_writes_the_target_energy_gain():
    entities = {"person-a": _person("person-a", 900), "person-b": _person("person-b", 565)}
    proposal = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-b", plan={"goal": "RESPOND_HELP", "steps": ["COOPERATE"]},
    )
    accepted, rejected, _ = _frame(entities, [proposal], 1)
    assert len(accepted) == 1 and not rejected
    assert entities["person-b"]["energy"] == 565 + EFFORT_TRANSFER_TARGET_ENERGY_GAIN == 605


# --- 2/5. the worked case: stale write must not erase the benefit ------------

def test_stale_physical_write_cannot_erase_a_committed_cooperate_benefit():
    """Frame start 565 -> cooperate commits 605 -> stale -5 write built from 565.

    The stale write must FAIL CLOSED. The recorded silent-loss values (640 from a
    stale rest, or 560 from a stale -5) must not appear. Composition (600) is NOT
    asserted -- it is not implemented.
    """
    entities = {"person-a": _person("person-a", 900), "person-b": _person("person-b", 565)}
    cooperate = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-b", plan={"goal": "RESPOND_HELP", "steps": ["COOPERATE"]},
    )
    stale = _stale_energy_proposal("person-b", stale_energy=565, tick=1)

    accepted, rejected, _ = _frame(entities, [cooperate, stale], 1)

    assert entities["person-b"]["energy"] == 605, "cooperation benefit was not preserved"
    assert entities["person-b"]["energy"] not in (560, 640), "stale base silently won"
    assert len(rejected) == 1
    assert rejected[0]["entity_id"] == "person-b"
    assert rejected[0]["reason_code"] == "precondition.failed"
    assert rejected[0]["reason_detail"] == "energy_eq_failed"
    assert len(accepted) == 1


# --- 3. precondition passes when nothing intervened --------------------------

def test_precondition_passes_when_energy_unchanged():
    entities = {"person-b": _person("person-b", 565)}
    stale = _stale_energy_proposal("person-b", stale_energy=565, tick=1)
    accepted, rejected, _ = _frame(entities, [stale], 1)
    assert not rejected
    assert len(accepted) == 1
    assert entities["person-b"]["energy"] == 560


# --- 4. deterministic failure when energy changed ----------------------------

def test_precondition_fails_deterministically_when_energy_changed():
    outcomes = []
    for _ in range(5):
        entities = {"person-a": _person("person-a", 900),
                    "person-b": _person("person-b", 565)}
        cooperate = build_social_action_proposal(
            entities, actor_id="person-a", action_type="cooperate", tick=1,
            target_id="person-b", plan={"goal": "RESPOND_HELP", "steps": ["COOPERATE"]},
        )
        stale = _stale_energy_proposal("person-b", stale_energy=565, tick=1)
        accepted, rejected, _ = _frame(entities, [cooperate, stale], 1)
        outcomes.append((
            entities["person-b"]["energy"],
            tuple(r["reason_detail"] for r in rejected),
            len(accepted),
        ))
    assert len(set(outcomes)) == 1, f"non-deterministic: {set(outcomes)}"
    assert outcomes[0] == (605, ("energy_eq_failed",), 1)


# --- 5. the trade-off, asserted explicitly -----------------------------------

def test_containment_tradeoff_whole_proposal_is_rejected_not_just_the_energy_write():
    """CONTAINMENT TRADE-OFF, pinned so it cannot be lost.

    Core rejects at PROPOSAL granularity -- there is no field-level partial
    commit. So the actor's non-energy effects in that proposal are dropped too.
    This is the cost of containment and is NOT the final fix.
    """
    entities = {"person-a": _person("person-a", 900), "person-b": _person("person-b", 565)}
    cooperate = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-b", plan={"goal": "RESPOND_HELP", "steps": ["COOPERATE"]},
    )
    stale = _stale_energy_proposal("person-b", stale_energy=565, tick=1)
    stale["mutation"]["entity_updates"]["person-b"]["position"] = {"x": 9, "y": 9}
    stale["mutation"]["entity_updates"]["person-b"]["hunger"] = 999

    accepted, rejected, _ = _frame(entities, [cooperate, stale], 1)

    assert len(rejected) == 1
    # The co-located effects are lost with the proposal -- position and hunger
    # never applied. This is the trade-off, asserted rather than assumed.
    assert entities["person-b"]["position"] == {"x": 5, "y": 5}
    assert entities["person-b"]["hunger"] == 300
    assert entities["person-b"]["energy"] == 605


# --- 6. replay equivalence ----------------------------------------------------

def test_replay_reproduces_the_same_outcome():
    from core.mutations import apply_mutation

    entities = {"person-a": _person("person-a", 900), "person-b": _person("person-b", 565)}
    cooperate = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-b", plan={"goal": "RESPOND_HELP", "steps": ["COOPERATE"]},
    )
    stale = _stale_energy_proposal("person-b", stale_energy=565, tick=1)
    accepted, rejected, _ = _frame(entities, [cooperate, stale], 1)

    replayed = {"person-a": _person("person-a", 900), "person-b": _person("person-b", 565)}
    for event in accepted:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    assert replayed["person-b"]["energy"] == entities["person-b"]["energy"] == 605


# --- 7. no unrelated proposal is affected -------------------------------------

def test_unrelated_actor_proposal_is_unaffected():
    entities = {"person-a": _person("person-a", 900),
                "person-b": _person("person-b", 565),
                "person-c": _person("person-c", 700)}
    cooperate = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-b", plan={"goal": "RESPOND_HELP", "steps": ["COOPERATE"]},
    )
    stale_b = _stale_energy_proposal("person-b", stale_energy=565, tick=1)
    fine_c = _stale_energy_proposal("person-c", stale_energy=700, tick=1)

    accepted, rejected, _ = _frame(entities, [cooperate, stale_b, fine_c], 1)

    assert [r["entity_id"] for r in rejected] == ["person-b"]
    assert entities["person-c"]["energy"] == 695, "unrelated actor was affected"
    assert entities["person-b"]["energy"] == 605
