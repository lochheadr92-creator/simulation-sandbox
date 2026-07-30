"""Layer C, Social Density Leg 2 -- R1 REQUEST_HELP targeting.

Contract: memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md,
"RATIFIED CONTRACT -- R1".

Ratified rule, for REQUEST_HELP ONLY: from the existing eligible visible-person
set, select the person at minimum existing spatial distance; resolve
equal-distance ties with the existing deterministic entity-ID ordering.

These are the contract's focused-test requirements. They pin the targeting
surface only -- they do not assert selection wins arbitration, and they do not
pin any organic incident (the `warn` lesson: positive fixtures assert through
the pipeline, never selection-as-invariant).
"""
import copy

from domains.living_agent_contracts import empty_living_agent_state
from domains.living_settlement_domain import build_settlement_candidates


HUNGRY = 700          # >= 600, the REQUEST_HELP pressure gate
ACTOR = "person-004"  # deliberately NOT the lowest id in the fixtures below


def _person_observation(person_id: str, distance: int, x: int = 0, y: int = 0) -> dict:
    return {
        "observed_subject_id": person_id,
        "observation_type": "person",
        "distance": int(distance),
        "properties": {"position": {"x": x, "y": y}},
    }


def _state(actor_id: str = ACTOR, hunger: int = HUNGRY) -> dict:
    state = empty_living_agent_state(actor_id, tick=1)
    state["pressures"] = {"hunger": {"severity": hunger, "urgency": hunger}}
    return state


def _entity(role: str = "resident") -> dict:
    return {
        "stage6_role": role,
        "position": {"x": 5, "y": 5},
        "carried_resources": {"food": 0, "wood": 0},
    }


def _request_candidate(candidates: list[dict]) -> dict | None:
    return next((c for c in candidates if c.get("goal") == "REQUEST_HELP"), None)


def _build(delta: dict, *, entity: dict | None = None, actor_id: str = ACTOR) -> list[dict]:
    return build_settlement_candidates(
        actor_id, entity or _entity(), _state(actor_id), {"known_tiles": []},
        delta, 1,
    )


# --- 1. Uniquely nearest wins -------------------------------------------------

def test_request_help_selects_the_uniquely_nearest_visible_person():
    delta = {"observations": [
        _person_observation("person-000", distance=4),
        _person_observation("person-001", distance=3),
        _person_observation("person-002", distance=1),   # nearest, highest-but-one id
        _person_observation("person-003", distance=2),
    ]}
    request = _request_candidate(_build(delta))
    assert request is not None
    assert request["target_entity_id"] == "person-002"


# --- 2. Equal-distance ties resolve by existing entity-ID ordering -------------

def test_equal_distance_tie_resolves_by_lowest_entity_id():
    delta = {"observations": [
        _person_observation("person-005", distance=2),
        _person_observation("person-001", distance=2),   # tied, lowest id
        _person_observation("person-003", distance=2),
    ]}
    request = _request_candidate(_build(delta))
    assert request is not None
    assert request["target_entity_id"] == "person-001"


def test_tie_break_only_applies_within_the_nearest_cohort():
    """The lowest id overall must NOT win if it is not in the nearest cohort."""
    delta = {"observations": [
        _person_observation("person-000", distance=9),   # lowest id, far away
        _person_observation("person-006", distance=2),   # nearest cohort
        _person_observation("person-007", distance=2),   # nearest cohort
    ]}
    request = _request_candidate(_build(delta))
    assert request is not None
    assert request["target_entity_id"] == "person-006"


# --- 3. A farther lower-ID person does not beat a nearer higher-ID person ------

def test_farther_lower_id_does_not_beat_nearer_higher_id():
    delta = {"observations": [
        _person_observation("person-000", distance=8),
        _person_observation("person-007", distance=1),
    ]}
    request = _request_candidate(_build(delta))
    assert request is not None
    assert request["target_entity_id"] == "person-007"
    # And the pre-R1 behaviour is genuinely gone, not coincidentally satisfied.
    assert request["target_entity_id"] != sorted(
        ["person-000", "person-007"],
    )[0]


# --- 4. Eligible-person filtering is unchanged --------------------------------

def test_eligible_set_is_ranked_not_filtered():
    """Every visible person remains eligible; R1 reorders, it never excludes."""
    observations = [
        _person_observation(f"person-00{i}", distance=i + 1) for i in range(4)
    ]
    delta = {"observations": observations}
    request = _request_candidate(_build(delta))
    assert request is not None
    # Nearest is person-000 here, so selection matches the old rule -- the point
    # is that no observation was dropped from consideration.
    assert request["target_entity_id"] == "person-000"

    # With a non-person observation present, person selection is unaffected.
    delta_mixed = {"observations": observations + [
        {"observed_subject_id": "tool-axe", "observation_type": "tool",
         "properties": {"tool_kind": "axe", "position": {"x": 1, "y": 1}}},
    ]}
    assert _request_candidate(_build(delta_mixed))["target_entity_id"] == "person-000"


def test_no_visible_person_yields_no_request_help_candidate():
    delta = {"observations": []}
    assert _request_candidate(_build(delta)) is None


def test_pressure_gate_is_unchanged():
    """Below the hunger gate, REQUEST_HELP is still not generated."""
    delta = {"observations": [_person_observation("person-001", distance=1)]}
    candidates = build_settlement_candidates(
        ACTOR, _entity(), _state(hunger=100), {"known_tiles": []}, delta, 1,
    )
    assert _request_candidate(candidates) is None


# --- 5. warn retains its existing targeting behaviour -------------------------

def test_warn_still_targets_lowest_visible_id_not_nearest():
    """R1 is REQUEST_HELP-only. `warn` is PARKED and must be untouched."""
    delta = {"observations": [
        _person_observation("person-000", distance=9),   # lowest id, farthest
        _person_observation("person-006", distance=1),   # nearest
        {"observed_subject_id": "animal-threat", "observation_type": "animal",
         "properties": {"position": {"x": 6, "y": 6}}, "distance": 1},
    ]}
    scout = _entity(role="scout")
    candidates = build_settlement_candidates(
        "person-007", scout, _state("person-007", hunger=0), {"known_tiles": []},
        delta, 1,
    )
    warn = next((c for c in candidates if c.get("goal") == "WARN_DANGER"), None)
    assert warn is not None
    # Unchanged: warn still uses visible_person_ids[0], NOT the nearest person.
    assert warn["target_entity_id"] == "person-000"


# --- 6. Deterministic repeat from identical state -----------------------------

def test_repeat_from_identical_state_produces_identical_selection():
    delta = {"observations": [
        _person_observation("person-002", distance=3),
        _person_observation("person-005", distance=1),
        _person_observation("person-001", distance=1),
        _person_observation("person-007", distance=2),
    ]}
    first = _request_candidate(_build(copy.deepcopy(delta)))
    for _ in range(5):
        again = _request_candidate(_build(copy.deepcopy(delta)))
        assert again["target_entity_id"] == first["target_entity_id"]
    assert first["target_entity_id"] == "person-001"


def test_selection_is_independent_of_observation_list_order():
    base = [
        _person_observation("person-006", distance=1),
        _person_observation("person-002", distance=4),
        _person_observation("person-003", distance=1),
    ]
    forward = _request_candidate(_build({"observations": list(base)}))
    reverse = _request_candidate(_build({"observations": list(reversed(base))}))
    assert forward["target_entity_id"] == reverse["target_entity_id"] == "person-003"


# --- 7. No unrelated action candidate changes ---------------------------------

def test_other_candidate_families_are_unaffected():
    """Only REQUEST_HELP's target moves; the rest of the candidate set is stable."""
    delta = {"observations": [
        _person_observation("person-000", distance=7),
        _person_observation("person-006", distance=1),
    ]}
    candidates = _build(delta)
    by_goal = {c["goal"]: c for c in candidates}

    assert by_goal["REQUEST_HELP"]["target_entity_id"] == "person-006"
    # REST is always appended as the deterministic fallback and is untouched.
    assert "REST" in by_goal
    assert by_goal["REST"]["direct_action_type"] == "rest"
    # No role-gated social candidate leaks in for a plain resident.
    for goal in ("WARN_DANGER", "SHARE_RUMOUR", "APOLOGISE", "RECONCILE",
                 "VERIFY_INFORMATION", "TRADE_RESOURCES", "THREATEN"):
        assert goal not in by_goal


def test_request_help_candidate_shape_is_unchanged():
    """Score, action type, obligation and due tick are untouched by R1."""
    delta = {"observations": [_person_observation("person-006", distance=1)]}
    request = _request_candidate(_build(delta))
    assert request["direct_action_type"] == "request_help"
    assert request["score"] == 1200 + HUNGRY
    assert request["obligation"] == "help obtain food"
    assert request["due_tick"] == 1 + 8
    assert request["target_pos"] == {"x": 0, "y": 0}
