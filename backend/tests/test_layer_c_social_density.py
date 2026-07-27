"""Layer C, Social Density Leg 1 -- Tier A deterministic mechanism gate.

Contract: memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG1.md section 9, Tier A.

The leg changes exactly one thing in production: STORE_SURPLUS's inline
eligibility literal `food >= 3` became the named constant
STORE_SURPLUS_MIN_FOOD = 2. Score (1350), goal/action names, target selection,
candidate ordering, transfer quantity, planner and executor are unchanged.

These tests pin the eligibility boundary and the survival-dominance property
around it. They are deliberately Tier A -- deterministic fixture/injection --
because the whole change is a comparison operator's right-hand side; the
organic half of the gate (two distinct actors committing `store` in a
5,000-tick collective_groups run) is a separate phase and is NOT covered here.
"""
import copy

import pytest

from core.constants import (
    ENGINE_VERSION,
    SCHEMA_VERSION,
    STORE_SURPLUS_MIN_FOOD,
)
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from domains.living_settlement_domain import build_settlement_candidates
from scenarios import get_scenario


def _lineage(seed: str) -> str:
    return f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"


def _storage_delta(*, access: str = "shared", visible: bool = True,
                   position: dict | None = None) -> dict:
    """One observation of `storage-camp`, or nothing at all.

    `access` carries the shared/private distinction the domain gates on:
    `("public", "shared")` are eligible, anything else is not.
    """
    if not visible:
        return {"observations": []}
    return {
        "observations": [{
            "observation_type": "storage",
            "observed_subject_id": "storage-camp",
            "properties": {
                "access": access,
                "position": position or {"x": 5, "y": 5},
            },
        }]
    }


def _entity(food: int, *, role: str = "resident") -> dict:
    return {
        "type": "person",
        "alive": True,
        "stage6_role": role,
        # Adjacent to the observed storage at (5,5); the domain's exploration
        # fallback reads position unconditionally, so it is not optional.
        "position": {"x": 5, "y": 6},
        "carried_resources": {"food": food, "wood": 0},
    }


def _store_candidates(candidates: list[dict]) -> list[dict]:
    return [c for c in candidates if c.get("goal") == "STORE_SURPLUS"]


def _build(food: int, *, access: str = "shared", visible: bool = True,
           pressures: dict | None = None) -> list[dict]:
    state = {"pressures": pressures or {}}
    return build_settlement_candidates(
        "person-001", _entity(food), state, {},
        _storage_delta(access=access, visible=visible), 1,
    )


# ---------------------------------------------------------------------------
# Tier A 1-3: the eligibility boundary itself.
# ---------------------------------------------------------------------------

def test_the_named_constant_is_the_measured_threshold():
    """Pins the constant's value, so a silent drift to 1 (which would let an
    actor store its last food unit) or back to 3 (measured dead) fails here
    rather than in a 5,000-tick run.
    """
    assert STORE_SURPLUS_MIN_FOOD == 2


def test_one_food_is_below_threshold_and_yields_no_store_candidate():
    """Tier A 1. One unit is the actor's last unit; storing it would break the
    keep-one guarantee the threshold exists to provide.
    """
    assert _store_candidates(_build(1)) == []


def test_zero_food_yields_no_store_candidate():
    assert _store_candidates(_build(0)) == []


def test_two_food_yields_exactly_one_store_candidate():
    """Tier A 2, positive half: the threshold's whole purpose. Two units is the
    highest carried-food value the measured 5,000-tick trajectory ever attains
    (carried_food_histogram_at_decision = {'0': 35878, '1': 1579, '2': 64}).
    """
    stores = _store_candidates(_build(2))

    assert len(stores) == 1
    candidate = stores[0]
    assert candidate["direct_action_type"] == "store"
    assert candidate["target_entity_id"] == "storage-camp"
    assert candidate["resource_kind"] == "food"


def test_three_food_remains_eligible():
    """Tier A 2, regression half: lowering the threshold must not accidentally
    turn it into an equality check. The old threshold's population stays valid.
    """
    stores = _store_candidates(_build(3))
    assert len(stores) == 1


def test_the_store_candidate_score_is_unchanged_at_1350():
    """The contract forbids score calibration. 1350 is load-bearing: it sits
    below every survival-triggered base (lowest is 1200 + severity), which is
    what keeps invariant C-6 true. Pinned so a future 'small nudge' is visible.
    """
    assert _store_candidates(_build(2))[0]["score"] == 1350


@pytest.mark.parametrize("food", [0, 1, 2, 3])
def test_private_storage_never_yields_a_candidate_at_any_inventory(food):
    """Tier A 3, first half. `storage-private` exists in living_settlement
    precisely so access control is testable; a private store is not a shared
    one no matter how much food the actor carries.
    """
    assert _store_candidates(_build(food, access="private")) == []


@pytest.mark.parametrize("food", [0, 1, 2, 3])
def test_invisible_storage_never_yields_a_candidate_at_any_inventory(food):
    """Tier A 3, second half. Perception grounds the candidate: an actor that
    cannot see a shared store cannot intend to use one. This is the C-1/C-6
    'member-grounded, reads pinned perception' property in miniature.
    """
    assert _store_candidates(_build(food, visible=False)) == []


def test_public_access_is_eligible_alongside_shared():
    """The domain gates on `("public", "shared")`. Both must stay eligible."""
    assert len(_store_candidates(_build(2, access="public"))) == 1


# ---------------------------------------------------------------------------
# Tier A 4-5: competition. Survival dominance and vocabulary preservation.
# ---------------------------------------------------------------------------

_STARVING = {"hunger": {"severity": 900}, "thirst": {"severity": 0}}


def test_store_surplus_outranks_only_idle_filler_when_nothing_is_urgent():
    """Tier A 4, first half: with no survival pressure the store candidate is
    the strongest thing on the list, so unchanged scoring *can* select it.

    SCOPE LIMIT, stated deliberately: this asserts the candidate is top-scoring,
    not that select_goal returns it -- selection also consults plan continuity
    and group influence. Commit-through-pipeline is covered below.
    """
    candidates = _build(2)
    stores = _store_candidates(candidates)
    assert stores, "no store candidate to compete"

    best_other = max(
        (c["score"] for c in candidates if c.get("goal") != "STORE_SURPLUS"),
        default=0,
    )
    assert stores[0]["score"] > best_other


def test_urgent_hunger_still_outranks_storing_surplus():
    """Tier A 4, second half -- invariant C-6. A starving actor holding two food
    units must eat, not tidy. EAT_CARRIED scores 1850 + severity against
    STORE_SURPLUS's flat 1350, so the margin is structural, not incidental.
    """
    candidates = _build(2, pressures=_STARVING)
    stores = _store_candidates(candidates)
    assert stores, "store candidate should still be generated, just outranked"

    eat = [c for c in candidates if c.get("goal") == "EAT_CARRIED"]
    assert eat, "starving actor with food should have EAT_CARRIED"
    assert eat[0]["score"] > stores[0]["score"]


def test_activating_the_candidate_does_not_crowd_out_warn_danger():
    """Tier A 5. The measured shadow saw candidate lists peak at 5 against a cap
    of 16, so truncation is not expected -- but WARN_DANGER is generated *after*
    STORE_SURPLUS in build order, so it is the one that would be lost first if
    the cap were ever approached. Pinned as a required-vocabulary guard.
    """
    delta = _storage_delta()
    delta["observations"].extend([
        {"observation_type": "animal", "observed_subject_id": "animal-threat",
         "properties": {"position": {"x": 6, "y": 6}}},
        {"observation_type": "person", "observed_subject_id": "person-002",
         "properties": {"position": {"x": 5, "y": 6}}},
    ])
    candidates = build_settlement_candidates(
        "person-001", _entity(2, role="scout"), {"pressures": {}}, {}, delta, 1,
    )

    goals = [c.get("goal") for c in candidates]
    assert "STORE_SURPLUS" in goals
    assert "WARN_DANGER" in goals


# ---------------------------------------------------------------------------
# Tier A 6-7: commit through the real pipeline, conservation, replay.
# ---------------------------------------------------------------------------

_SATED = {"hunger": 0, "thirst": 0, "energy": 1000, "health": 1000,
          "injury": {"injured": False, "severity": 0, "cause": None}}


def _adjacent_storage_camp(food: int = 2):
    """living_settlement reduced to one sated resident standing next to the
    shared store, carrying `food`.

    Adjacency is not convenience: it removes WARN_DANGER's lesson from
    test_stage6e_living_settlement.py, where a plan whose first step is
    MOVE_TO_TARGET is replanned away before its terminal step. Placing the
    actor beside the target isolates the eligibility change under test.
    """
    scenario = copy.deepcopy(get_scenario("living_settlement"))
    wg = scenario.world_gen
    storage_pos = next(
        spec["position"] for spec in wg["extra_genesis_specs"]
        if spec.get("id") == "storage-camp"
    )
    wg["num_people"] = 1
    wg["person_positions"] = [{"x": storage_pos["x"], "y": storage_pos["y"] + 1}]
    wg["person_profiles"] = [dict(
        _SATED, stage6_role="resident",
        carried_resources={"food": food, "wood": 0},
    )]
    return scenario, storage_pos


def _run_storage_camp(*, food: int = 2, ticks: int = 8,
                      seed: str = "store-fixture"):
    scenario, _pos = _adjacent_storage_camp(food)
    lineage = _lineage(seed)
    world, entities, genesis, _rejected, order_index = build_genesis(
        seed, scenario, lineage,
    )
    valid_parent_ids = {event["id"] for event in genesis}
    rng = DeterministicRNG(seed)
    cache: dict = {}
    store_events = []
    selected_goals = []
    for tick in range(1, ticks + 1):
        accepted, _rej, order_index, diagnostics = run_tick(
            seed, entities, world["terrain"], tick, rng, order_index,
            lineage, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
            entity_json_cache=cache,
        )
        for event in accepted:
            valid_parent_ids.add(event["id"])
            if (event.get("living_action") or {}).get("action_type") == "store":
                store_events.append(event)
        diag = diagnostics.get("person-000") or {}
        if diag.get("selected_goal"):
            selected_goals.append(diag["selected_goal"])
    return store_events, selected_goals, entities


def test_store_commits_through_the_real_pipeline_and_conserves_food():
    """Tier A 6. The whole point of the leg: an eligible actor actually places a
    unit into shared storage through Core's validate/commit path.

    Asserts COMMIT, not selection -- the same distinction the WARN_DANGER
    fixture pair was built around, and for the same reason: STORE_SURPLUS
    winning a scoring round proves nothing if the action never lands.
    """
    store_events, selected_goals, entities = _run_storage_camp(food=2)

    assert store_events, (
        f"no `store` action committed; selected goals were {selected_goals}"
    )
    assert "STORE_SURPLUS" in selected_goals

    first = store_events[0]
    assert first["entity_id"] == "person-000"
    transfer = first["living_action"]["resource_transfer"]
    assert transfer["resource_kind"] == "food"
    assert transfer["quantity"] == 1, "transfer quantity must remain one unit"

    # Keep-one guarantee: two in, one stored, at least one retained.
    remaining = (entities["person-000"].get("carried_resources") or {}).get("food", 0)
    assert remaining >= 1


def test_an_actor_at_one_food_never_commits_a_store():
    """Tier A 6, negative control on the same fixture. Below threshold nothing
    is generated, so nothing can commit -- this is what stops the change from
    being laundered into 'agents store their last meal'.
    """
    store_events, _goals, entities = _run_storage_camp(food=1)

    assert store_events == []
    remaining = (entities["person-000"].get("carried_resources") or {}).get("food", 0)
    assert remaining == 1


def test_the_committed_store_is_replay_exact():
    """Tier A 7, replay half. Determinism invariant C-2: the same seed and
    scenario reproduce the same committed store, byte for byte.
    """
    first_events, first_goals, _e1 = _run_storage_camp(food=2)
    second_events, second_goals, _e2 = _run_storage_camp(food=2)

    assert first_goals == second_goals
    assert [e["id"] for e in first_events] == [e["id"] for e in second_events]
    assert first_events == second_events
