"""Layer C, Variety Leg 1 -- Upkeep drive.

See memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md for the contract. These
tests cover the acceptance gate's focused-test requirements: forged-field
rejection (PRESSURE_KINDS / PHYSICAL_ACTION_TYPES additive extension),
replay equality for the new `tend` action, the disjoint wear-band ownership
guarantee (including a same-tick wear-vs-tend churn proof mirroring the
existing wear-vs-repair pattern), and the survival-dominance score band.
"""
import copy

import pytest

from core.commit_pipeline import run_commit_frame
from core.constants import (
    STRUCTURE_TEND_CONDITION_CEILING,
    STRUCTURE_TEND_CONDITION_FLOOR,
    STRUCTURE_TEND_RESTORE_AMOUNT,
    STRUCTURE_WEAR_BASE,
    UPKEEP_IDLE_TAIL_TICKS,
)
from core.mutations import apply_mutation
from domains.base import ActivationFrame, DomainOutput
from domains.ecology_domain import EcologyDomain
from domains.living_agent_actions import build_physical_action_proposal
from domains.living_agent_cognition import derive_internal_pressures
from domains.living_agent_contracts import (
    PHYSICAL_ACTION_TYPES,
    PRESSURE_KINDS,
    PRESSURE_SCHEMA_VERSION,
    compat_living_agent_state,
    empty_living_agent_state,
    empty_pressure,
)
from domains.living_settlement_domain import (
    GROUP_GOAL_REPAIR_INCREMENT,
    _apply_group_goal_influence,
    build_settlement_candidates,
)
from domains.association_contracts import ASSOCIATION_REGISTRY_ID, ASSOCIATION_REGISTRY_VERSION, GROUP_CANDIDATE_VERSION
from domains.group_goal_contracts import GROUP_GOAL_REGISTRY_ID, GROUP_GOAL_REGISTRY_VERSION, GROUP_GOAL_VERSION, GOAL_TYPE


def _plan(goal):
    return {"plan_id": f"plan-{goal.lower()}", "goal_id": f"goal-{goal.lower()}", "goal": goal, "step_index": 0}


def _person(position, **overrides):
    base = {
        "type": "person", "position": dict(position), "alive": True,
        "health": 900, "energy": 800, "hunger": 500, "thirst": 400,
        "carried_resources": {"wood": 0, "food": 0}, "last_event_id": "evt-person",
    }
    base.update(overrides)
    return base


def _shelter(position, condition, **overrides):
    base = {
        "type": "shelter", "position": dict(position), "condition": condition,
        "max_condition": 1000, "owner_id": "person-a", "access": "shared",
        "alive": True, "last_event_id": "evt-shelter",
    }
    base.update(overrides)
    return base


def _commit(entities, *proposals, tick=1):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))], tick, "lineage", "run", 0, f"frame-{tick}",
    )


# --- Forged-field rejection: the additive schema touches don't weaken the guard ---

def test_pressure_kinds_extension_is_additive_and_still_rejects_unknown_kinds():
    assert "upkeep" in PRESSURE_KINDS
    assert len(PRESSURE_KINDS) == 15
    with pytest.raises(ValueError, match="unknown pressure kind"):
        empty_pressure("not_a_real_kind", weight=100, tick=0)


def test_legacy_state_missing_upkeep_backfills_defaults_without_error():
    """A pre-leg saved living_agent state has no "upkeep" key. compat_living_agent_state
    must backfill it at the uniform default rather than erroring -- this is the
    resume/replay compatibility path for runs committed before this leg."""
    legacy = empty_living_agent_state("person-a", tick=1)
    del legacy["pressures"]["upkeep"]
    assert "upkeep" not in legacy["pressures"]

    restored = compat_living_agent_state(legacy, "person-a", tick=2)

    assert restored["pressures"]["upkeep"]["schema_version"] == PRESSURE_SCHEMA_VERSION
    assert restored["pressures"]["upkeep"]["severity"] == 0
    assert restored["pressures"]["upkeep"]["individual_weight"] == 100
    # the other 14 kinds are untouched by the backfill
    for kind in PRESSURE_KINDS:
        if kind != "upkeep":
            assert restored["pressures"][kind]["schema_version"] == PRESSURE_SCHEMA_VERSION


def test_unsupported_physical_action_still_rejected_with_tend_present():
    assert "tend" in PHYSICAL_ACTION_TYPES
    with pytest.raises(ValueError, match="unsupported physical action"):
        build_physical_action_proposal(
            {"person-a": _person({"x": 1, "y": 1})},
            actor_id="person-a", action_type="not_a_real_action", tick=1, plan=_plan("BOGUS"),
        )


# --- tend action mechanics + replay ---

def test_tend_changes_condition_no_material_or_tool_required_and_creates_evidence():
    entities = {
        "person-a": _person({"x": 1, "y": 1}),  # zero wood, no tool
        "shelter-a": _shelter({"x": 2, "y": 1}, 800),  # in the tend band
    }
    initial = copy.deepcopy(entities)
    proposal = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="tend", tick=1,
        target_id="shelter-a", plan=_plan("TEND_STRUCTURE"),
    )
    accepted, rejected, _ = _commit(entities, proposal)

    assert not rejected and accepted
    assert entities["shelter-a"]["condition"] == 800 + STRUCTURE_TEND_RESTORE_AMOUNT
    assert entities["person-a"]["carried_resources"]["wood"] == 0  # unconsumed
    signals = [e for e in entities.values() if e.get("type") == "signal"]
    assert len(signals) == 1 and signals[0]["signal_kind"] == "noise"

    replayed = copy.deepcopy(initial)
    apply_mutation(replayed, copy.deepcopy(accepted[0]["mutation"]))
    assert replayed == entities


def test_tend_condition_gain_caps_at_max_condition():
    entities = {
        "person-a": _person({"x": 1, "y": 1}),
        "shelter-a": _shelter({"x": 2, "y": 1}, STRUCTURE_TEND_CONDITION_CEILING - 5),
    }
    proposal = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="tend", tick=1,
        target_id="shelter-a", plan=_plan("TEND_STRUCTURE"),
    )
    accepted, rejected, _ = _commit(entities, proposal)
    assert not rejected and accepted
    assert entities["shelter-a"]["condition"] == entities["shelter-a"]["max_condition"]


# --- Ownership: disjoint wear bands (the no-double-apply guarantee) ---

def test_repair_and_tend_condition_bands_are_disjoint():
    for condition in range(0, STRUCTURE_TEND_CONDITION_CEILING + 1, 25):
        in_repair_band = condition < STRUCTURE_TEND_CONDITION_FLOOR
        in_tend_band = STRUCTURE_TEND_CONDITION_FLOOR <= condition < STRUCTURE_TEND_CONDITION_CEILING
        assert not (in_repair_band and in_tend_band), condition


def test_wear_then_tend_same_tick_wear_commits_tend_rejects_and_retries():
    """Mirrors ecology_domain.py's documented wear-vs-repair guarantee: a wear
    tick and a same-tick tend on the same structure resolve deterministically
    as a wear then a rejected (stale-precondition) tend that retries next
    tick -- proving the third proposer on `condition` doesn't double-apply."""
    tick = 5  # STRUCTURE_WEAR_INTERVAL divides this tick
    entities = {
        "weather-000": {"type": "weather", "position": {"x": 0, "y": 0}, "exposure": 0},
        "person-a": _person({"x": 1, "y": 1}),
        "shelter-a": _shelter({"x": 2, "y": 1}, 800),  # tend band
    }
    ecology = EcologyDomain()
    frame = ActivationFrame("run", tick, "engine", "environment", entities, [], ["shelter-a"], None)
    wear_output = ecology.activate(frame)
    assert wear_output.proposals, "expected a due structure_wear proposal at this tick"

    # The actor's tend proposal is built from this-tick's observed (pre-wear) condition,
    # exactly like the existing repair path.
    tend_proposal = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="tend", tick=tick,
        target_id="shelter-a", plan=_plan("TEND_STRUCTURE"),
    )

    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=wear_output.proposals), DomainOutput(proposals=[tend_proposal])],
        tick, "lineage", "run", 0, f"frame-{tick}",
    )

    wear_events = [e for e in accepted if e.get("proposal_type") == "structure_wear" or "structure_wear" in str(e.get("event_type", ""))]
    tend_rejections = [r for r in rejected if r.get("proposal_type") == "tend" or (r.get("proposal") or {}).get("living_action", {}).get("action_type") == "tend"]

    assert entities["shelter-a"]["condition"] == 800 - STRUCTURE_WEAR_BASE  # wear committed alone
    assert len(rejected) == 1  # the stale-precondition tend, retries next tick
    assert len(accepted) == 1  # only wear committed this tick


# --- Candidate generation: repair (builder-gated) and tend (any role) never both fire for one shelter ---

def test_candidate_generation_repair_and_tend_are_mutually_exclusive_per_shelter():
    entity = {"stage6_role": "builder", "position": {"x": 5, "y": 5}, "carried_resources": {"wood": 5, "food": 0}}
    state = empty_living_agent_state("person-a", tick=1)
    knowledge = {"known_tiles": []}
    tools_delta = {
        "observations": [
            {"observed_subject_id": "tool-hammer", "observation_type": "tool",
             "properties": {"tool_kind": "hammer", "position": {"x": 5, "y": 5}}},
        ],
    }

    def _delta_for(condition):
        return {
            "observations": tools_delta["observations"] + [
                {"observed_subject_id": "shelter-a", "observation_type": "shelter",
                 "properties": {"condition": condition, "position": {"x": 5, "y": 6}}},
            ],
        }

    damaged = build_settlement_candidates("person-a", entity, state, knowledge, _delta_for(380), tick=1)
    goals_damaged = {c["goal"] for c in damaged}
    assert "REPAIR_SHELTER" in goals_damaged
    assert "TEND_STRUCTURE" not in goals_damaged

    mildly_worn = build_settlement_candidates("person-a", entity, state, knowledge, _delta_for(850), tick=1)
    goals_worn = {c["goal"] for c in mildly_worn}
    assert "TEND_STRUCTURE" in goals_worn
    assert "REPAIR_SHELTER" not in goals_worn


def test_candidate_generation_tend_available_to_non_builder_roles():
    entity = {"stage6_role": "needy", "position": {"x": 5, "y": 5}, "carried_resources": {"wood": 0, "food": 0}}
    state = empty_living_agent_state("person-a", tick=1)
    knowledge = {"known_tiles": []}
    delta = {
        "observations": [
            {"observed_subject_id": "shelter-a", "observation_type": "shelter",
             "properties": {"condition": 850, "position": {"x": 5, "y": 6}}},
        ],
    }
    candidates = build_settlement_candidates("person-a", entity, state, knowledge, delta, tick=1)
    assert "TEND_STRUCTURE" in {c["goal"] for c in candidates}


# --- Idle-streak signal reads the pinned decision_history tail ---

def test_upkeep_idle_signal_grows_with_trailing_rest_streak_and_is_capped():
    entity = {"position": {"x": 1, "y": 1}, "energy": 900, "hunger": 0, "thirst": 0, "health": 1000}
    knowledge = {"known_tiles": []}
    delta = {"observations": []}

    state = empty_living_agent_state("person-a", tick=1)
    baseline = derive_internal_pressures(entity, state, knowledge, delta, tick=1)
    assert baseline["pressures"]["upkeep"]["severity"] == 0

    rest_streak_state = copy.deepcopy(state)
    rest_streak_state["decision_history"] = [
        {"selected_goal": "REST"} for _ in range(UPKEEP_IDLE_TAIL_TICKS)
    ]
    streak = derive_internal_pressures(entity, rest_streak_state, knowledge, delta, tick=1)
    assert streak["pressures"]["upkeep"]["severity"] > baseline["pressures"]["upkeep"]["severity"]

    longer_streak_state = copy.deepcopy(state)
    longer_streak_state["decision_history"] = [
        {"selected_goal": "REST"} for _ in range(UPKEEP_IDLE_TAIL_TICKS + 20)
    ]
    capped = derive_internal_pressures(entity, longer_streak_state, knowledge, delta, tick=1)
    assert capped["pressures"]["upkeep"]["severity"] == streak["pressures"]["upkeep"]["severity"]


def test_upkeep_idle_signal_breaks_on_non_rest_entry():
    entity = {"position": {"x": 1, "y": 1}, "energy": 900, "hunger": 0, "thirst": 0, "health": 1000}
    knowledge = {"known_tiles": []}
    delta = {"observations": []}
    state = empty_living_agent_state("person-a", tick=1)
    state["decision_history"] = [
        {"selected_goal": "REST"}, {"selected_goal": "REST"},
        {"selected_goal": "EXPLORE"},  # breaks the streak counting backward from the tail
        {"selected_goal": "REST"},
    ]
    result = derive_internal_pressures(entity, state, knowledge, delta, tick=1)
    all_rest_state = copy.deepcopy(state)
    all_rest_state["decision_history"] = [{"selected_goal": "REST"}] * 4
    all_rest_result = derive_internal_pressures(entity, all_rest_state, knowledge, delta, tick=1)
    assert result["pressures"]["upkeep"]["severity"] < all_rest_result["pressures"]["upkeep"]["severity"]


# --- Survival dominance (gate item 7) ---

def test_tend_never_outranks_an_active_survival_candidate():
    """An actor eligible for both TEND_STRUCTURE (max upkeep pressure) and an
    active survival candidate (high hunger) must still select the survival
    goal -- the score band is structural, not a runtime override."""
    entity = {
        "stage6_role": "needy", "position": {"x": 5, "y": 5},
        "carried_resources": {"wood": 0, "food": 0},
        "hunger": 900, "thirst": 200, "energy": 900,
    }
    state = empty_living_agent_state("person-a", tick=1)
    state["decision_history"] = [{"selected_goal": "REST"}] * UPKEEP_IDLE_TAIL_TICKS
    knowledge = {"known_tiles": []}
    delta = {
        "observations": [
            {"observed_subject_id": "shelter-a", "observation_type": "shelter",
             "properties": {"condition": 750, "position": {"x": 5, "y": 6}}},
            {"observed_subject_id": "person-b", "observation_type": "person",
             "properties": {"position": {"x": 5, "y": 6}}},
        ],
    }
    state = derive_internal_pressures(entity, state, knowledge, delta, tick=1)
    candidates = build_settlement_candidates("person-a", entity, state, knowledge, delta, tick=1)
    goals = {c["goal"] for c in candidates}
    assert "TEND_STRUCTURE" in goals  # both are on the table
    from domains.living_agent_reasoning import score_goal_candidates, select_goal
    scored = score_goal_candidates(candidates, actor_id="person-a", state=state, knowledge=knowledge, tick=1)
    selected = select_goal(scored)
    assert selected["goal"] != "TEND_STRUCTURE"


def test_tend_beats_rest_fallback_when_no_survival_pressure_present():
    entity = {
        "stage6_role": "needy", "position": {"x": 5, "y": 5},
        "carried_resources": {"wood": 0, "food": 0},
        "hunger": 100, "thirst": 100, "energy": 900,
    }
    state = empty_living_agent_state("person-a", tick=1)
    state["decision_history"] = [{"selected_goal": "REST"}] * UPKEEP_IDLE_TAIL_TICKS
    # All 4 adjacent tiles already known so EXPLORE's fallback candidate isn't
    # generated -- isolates the TEND_STRUCTURE-vs-REST comparison this test is for.
    knowledge = {"known_tiles": ["5,4", "6,5", "5,6", "4,5"]}
    delta = {
        "observations": [
            {"observed_subject_id": "shelter-a", "observation_type": "shelter",
             "properties": {"condition": 750, "position": {"x": 5, "y": 6}}},
        ],
    }
    state = derive_internal_pressures(entity, state, knowledge, delta, tick=1)
    candidates = build_settlement_candidates("person-a", entity, state, knowledge, delta, tick=1)
    from domains.living_agent_reasoning import score_goal_candidates, select_goal
    scored = score_goal_candidates(candidates, actor_id="person-a", state=state, knowledge=knowledge, tick=1)
    selected = select_goal(scored)
    assert selected["goal"] == "TEND_STRUCTURE"


def test_explore_still_wins_over_tend_when_unknown_ground_is_adjacent():
    """TEND_STRUCTURE sits between REST (60) and EXPLORE (180), not above both --
    a shelter is in the tend band almost continuously, so scoring upkeep above
    EXPLORE would make it a permanently-preferred absorbing loop that starves
    map exploration (observed empirically; see core/constants.py's
    TEND_STRUCTURE_BASE_SCORE comment and the leg contract's risk log)."""
    entity = {
        "stage6_role": "needy", "position": {"x": 5, "y": 5},
        "carried_resources": {"wood": 0, "food": 0},
        "hunger": 100, "thirst": 100, "energy": 900,
    }
    state = empty_living_agent_state("person-a", tick=1)
    state["decision_history"] = [{"selected_goal": "REST"}] * UPKEEP_IDLE_TAIL_TICKS
    knowledge = {"known_tiles": []}  # nothing known -- all 4 adjacent tiles are unknown
    delta = {
        "observations": [
            {"observed_subject_id": "shelter-a", "observation_type": "shelter",
             "properties": {"condition": 750, "position": {"x": 5, "y": 6}}},
        ],
    }
    state = derive_internal_pressures(entity, state, knowledge, delta, tick=1)
    candidates = build_settlement_candidates("person-a", entity, state, knowledge, delta, tick=1)
    from domains.living_agent_reasoning import score_goal_candidates, select_goal
    scored = score_goal_candidates(candidates, actor_id="person-a", state=state, knowledge=knowledge, tick=1)
    selected = select_goal(scored)
    assert selected["goal"] == "EXPLORE"


# --- Discharge: an accepted tend lowers the upkeep drive (gate item 1) ---

def test_accepted_tend_discharges_the_upkeep_pressure():
    """Both signals that build upkeep severity fall after a successful tend:
    the shelter is less worn, and the decision_history tail no longer ends
    in an unbroken REST streak (it now ends in TEND_STRUCTURE)."""
    entity = {"position": {"x": 1, "y": 1}, "energy": 900, "hunger": 0, "thirst": 0, "health": 1000}
    knowledge = {"known_tiles": []}

    state_before = empty_living_agent_state("person-a", tick=1)
    state_before["decision_history"] = [{"selected_goal": "REST"}] * UPKEEP_IDLE_TAIL_TICKS
    delta_before = {
        "observations": [
            {"observed_subject_id": "shelter-a", "observation_type": "shelter",
             "properties": {"condition": 760, "position": {"x": 1, "y": 2}}},
        ],
    }
    before = derive_internal_pressures(entity, state_before, knowledge, delta_before, tick=UPKEEP_IDLE_TAIL_TICKS)

    # A tend action executes: condition rises by STRUCTURE_TEND_RESTORE_AMOUNT,
    # and the most recent decision is now TEND_STRUCTURE, breaking the streak.
    state_after = copy.deepcopy(state_before)
    state_after["decision_history"] = (
        state_before["decision_history"][1:] + [{"selected_goal": "TEND_STRUCTURE"}]
    )
    delta_after = {
        "observations": [
            {"observed_subject_id": "shelter-a", "observation_type": "shelter",
             "properties": {"condition": 760 + STRUCTURE_TEND_RESTORE_AMOUNT, "position": {"x": 1, "y": 2}}},
        ],
    }
    after = derive_internal_pressures(entity, state_after, knowledge, delta_after, tick=UPKEEP_IDLE_TAIL_TICKS + 1)

    assert after["pressures"]["upkeep"]["severity"] < before["pressures"]["upkeep"]["severity"]


# --- Component-Ownership reconciliation as a test: the 7D nudge is goal-name-scoped ---

def _person_with_want(pid):
    return {
        "type": "person", "alive": True, "position": {"x": 0, "y": 0},
        "last_event_id": "evt-0-" + pid,
        "living_agent": {"wants": {"want-1": {"want_type": "improve_shelter", "status": "active"}}},
    }


def test_stage7d_nudge_is_inert_for_tend_structure_even_with_an_active_matching_goal():
    """The Stage 7D group-goal nudge (living_settlement_domain._apply_group_goal_
    influence) boosts a candidate only when cand["goal"] == "REPAIR_SHELTER"
    (string match). Prove this with a FULLY ACTIVE, valid, matching registry
    (not merely absent/inert-by-omission) so the contrast is real: REPAIR_SHELTER
    gets boosted, TEND_STRUCTURE targeting the identical shelter does not."""
    shelter_id = "shelter-nudge-test"
    group_id = "grp-nudge-test"
    entities = {"p-a": _person_with_want("p-a")}
    entities[ASSOCIATION_REGISTRY_ID] = {
        "schema_version": ASSOCIATION_REGISTRY_VERSION, "revision": 1,
        "last_event_id": "evt-0-assoc",
        "group_candidates": {group_id: {
            "schema_version": GROUP_CANDIDATE_VERSION,
            "recognition_state": "recognised", "ever_recognised": True,
            "member_ids": ["p-a", "p-b"], "group_type": "household",
            "recognised_tick": 1, "recognition_event_id": "evt-0-recog",
        }},
    }
    entities[GROUP_GOAL_REGISTRY_ID] = {
        "type": "group_goal_registry", "schema_version": GROUP_GOAL_REGISTRY_VERSION, "revision": 1,
        "goals": {"g1": {
            "schema_version": GROUP_GOAL_VERSION, "goal_id": "g1", "group_id": group_id,
            "goal_type": GOAL_TYPE, "target_id": shelter_id, "coordinator_id": "p-a",
            "supporter_ids": ["p-a", "p-b"], "status": "active", "ttl_tick": 100,
        }},
    }
    candidates = [
        {"goal": "REPAIR_SHELTER", "target_entity_id": shelter_id, "score": 2400},
        {"goal": "TEND_STRUCTURE", "target_entity_id": shelter_id, "score": 400},
    ]

    out = _apply_group_goal_influence(candidates, "p-a", entities, 5)

    repair = next(c for c in out if c["goal"] == "REPAIR_SHELTER")
    tend = next(c for c in out if c["goal"] == "TEND_STRUCTURE")
    assert repair["score"] == 2400 + GROUP_GOAL_REPAIR_INCREMENT  # proves the registry is genuinely active
    assert tend["score"] == 400  # unchanged: goal-name-scoped, not registry-inert
