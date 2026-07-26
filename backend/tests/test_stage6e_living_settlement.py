import copy

import pytest

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation
from core.rng import DeterministicRNG
from domains.living_agent_contracts import LIMITS
from scenarios import get_scenario
from tools.living_agent_harness import run_living_agent_harness


def _lineage(seed: str) -> str:
    return f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"


def test_living_settlement_scenario_is_explicit_and_bounded():
    scenario = get_scenario("living_settlement")

    assert scenario.enabled_domains == [
        "weather", "ecology", "lifecycle", "living_settlement", "animal",
    ]
    assert scenario.world_gen["num_people"] == 8
    assert len(scenario.world_gen["person_profiles"]) == 8
    assert len(scenario.world_gen["person_positions"]) == 8
    explicit_ids = {
        spec["id"] for spec in scenario.world_gen["extra_genesis_specs"]
    }
    assert {
        "weather-000", "storage-camp", "storage-private", "tool-axe",
        "tool-hammer", "shelter-damaged", "water-camp", "food-patch",
        "wood-pile", "animal-threat", "signal-false-rumour",
    }.issubset(explicit_ids)


# SPLIT 2026-07-27 (age-realism re-baseline leg, stage 1).
#
# This test previously mixed two different kinds of claim:
#
#   STRUCTURAL INVARIANTS -- the loop closes, state stays bounded, the run
#   replays. True for any seed.
#
#   A TRACE CENSUS -- "these exact 15 action types occur in this 30-tick window
#   on this one seed". A property of one trajectory, not of the engine.
#
# The census kind broke on every re-baseline and was patched in place each time,
# leaving a weaker test behind: `false_belief_count` was reduced to `>= 0` after
# Layer C Variety Leg 1, and the broken-commitment assertion to a bare
# `sum(...) >= 1` after the Stage 6 Liveness Pass (both notes below). The genesis
# RNG re-stream made it three, losing `warn`.
#
# So the census moved OUT of assertions and into the dated baseline register in
# `memory/evidence/genesis-rng/SHARED-SPAWN-STREAM-2026-07-26.md`, and what
# stays here is only what was MEASURED seed-robust across 5 seeds
# (stage6-integrated, living-agents-stage6, stage6-order, stage6-information,
# warn-probe-b). Two of them are now parametrised so seed-robustness is
# enforced rather than asserted.
#
# Moved to the register, with the measurement that moved it:
#   * the 15-type census -- `warn` absent on 4 of 5 seeds. The other 14 types
#     ARE seed-robust and are still asserted below.
#   * `reported_claim_count >= 1` -- fails on 2 of 5 seeds. It was passing here
#     only because pytest short-circuits: the census assertion above it failed
#     first, so this one was never reached.
#
# `warn`'s mechanism is NOT dropped -- it moved to a stronger pair of
# deterministic fixtures below, which assert the action COMMITS through the real
# pipeline rather than hoping one seed's geometry produces it.
@pytest.mark.parametrize("seed", ["stage6-integrated", "living-agents-stage6"])
def test_integrated_camp_closes_the_living_agent_loop_and_replays(seed):
    result = run_living_agent_harness(seed, ticks=30)
    summary = result["summary"]

    # 14 of the original 15 types. `warn` is excluded deliberately -- see the
    # register and the fixture pair below; it is not a silent relaxation.
    assert {
        "move", "drink", "consume", "gather", "retrieve", "repair",
        "cooperate", "lie", "share_information", "promise",
        "trade", "threaten", "apologise", "reconcile",
    }.issubset(summary["actions_by_type"])
    assert summary["decisions_by_kind"]["critical_interrupt"] >= 1
    assert summary["decisions_by_kind"]["resumption"] >= 1
    assert summary["decisions_by_kind"]["failed_plan_replan"] >= 1
    assert summary["rejected_proposal_count"] >= 1
    assert summary["resource_depletion"] >= 1
    assert summary["weather_conditions"] == ["rain"]

    # `reported_claim_count >= 1` REMOVED here -- measured trace-dependent
    # (fails on 2 of 5 seeds). Recorded in the baseline register instead. It had
    # never actually been exercised on a failing run: the census assertion above
    # it failed first and pytest short-circuits.
    # After Layer C Variety Leg 1 (memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md,
    # the upkeep drive), idle-time agents now often tend a mildly worn shelter
    # instead of resting/wandering -- the same class of deterministic-trace
    # perturbation the Stage 6 Liveness Pass note below already documents.
    # Verified directly (see the leg's close-out) that this shifts which agent
    # reaches the genesis false rumour (expires tick 4) before the window ends,
    # so false_belief_count no longer reliably lands >=1 in this specific
    # 30-tick trace; confirmed at 30/40/50/60 ticks, so it is not a timing
    # margin issue. This assertion is intentionally trace-agnostic -- the
    # dedicated, non-vacuous false-belief net now lives in
    # test_false_belief_detection_flags_a_known_deceptive_report below (adversarial
    # review finding F-04, memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md).
    assert summary["false_belief_count"] >= 0
    assert summary["deceptive_claim_count"] == 0
    assert summary["contradicted_claim_count"] >= 1
    assert summary["final_relationship_count"] > 8
    # Commitments form and are tracked through the integrated loop. The specific
    # "broken" terminal state is trace-dependent: after the Stage 6 Liveness
    # re-baseline (passive shelter wear perturbs the deterministic schedule), the
    # first breach shifts just past this 30-tick window and now lands after the
    # tick-40 storm transition, so it can no longer co-occur with the
    # weather_conditions == ["rain"] window asserted above. The broken-commitment
    # path is covered directly by test_stage6d_social_relationships. See
    # STAGE-6-LIVENESS-PASS.md.
    assert sum(summary["commitment_statuses"].values()) >= 1

    maximums = summary["max_state_counts"]
    assert maximums["memories"] <= LIMITS.memories_per_entity
    assert maximums["relationships"] <= LIMITS.relationship_records
    assert maximums["commitments"] <= LIMITS.commitments_per_entity
    assert maximums["decision_history"] <= LIMITS.decision_receipts_retained
    assert maximums["causal_links"] <= LIMITS.causal_links_retained


# ---------------------------------------------------------------------------
# WARN_DANGER fixture PAIR. Replaces the organic `warn` census assertion the
# split above removed, and is strictly stronger: it drives the real domain's
# goal selection and asserts the action COMMITS through run_commit_frame,
# instead of hoping one seed's geometry produces a three-way coincidence.
#
# Distinct from test_stage6c_physical_actions.py's warn coverage, which builds a
# warn proposal directly and so never exercises goal selection at all.
# ---------------------------------------------------------------------------

_SATED = {"hunger": 0, "thirst": 0, "energy": 1000, "health": 1000,
          "injury": {"injured": False, "severity": 0, "cause": None}}


def _two_person_warn_camp(*, parched: bool):
    """living_settlement reduced to a scout and one adjacent neighbour.

    Two people rather than eight for a measured reason, not for convenience: in
    the full camp the scout at (5,6) is BOXED IN by its own campmates. Reaching
    person-000 at (4,4) requires stepping onto (4,5) or (5,5), both occupied, so
    WARN_DANGER's `MOVE_TO_TARGET` step fails its precondition every tick and the
    plan is replanned away before the terminal WARN. Placing the target adjacent
    removes the move step, which is what allows the action to commit at all.
    """
    scenario = copy.deepcopy(get_scenario("living_settlement"))
    wg = scenario.world_gen
    wg["num_people"] = 2
    wg["person_positions"] = [{"x": 5, "y": 5}, {"x": 5, "y": 6}]
    scout = dict(_SATED, stage6_role="scout")
    if parched:
        scout.update({"thirst": 1000, "hunger": 1000})
    wg["person_profiles"] = [dict(_SATED, stage6_role="caretaker"), scout]
    for spec in wg["extra_genesis_specs"]:
        if spec.get("id") == "animal-threat":
            spec["position"] = {"x": 6, "y": 6}
    return scenario


def _run_warn_camp(*, parched: bool, ticks: int = 12, seed: str = "warn-fixture"):
    """Drive the fixture through the real kernel; return committed warn events."""
    scenario = _two_person_warn_camp(parched=parched)
    lineage = _lineage(seed)
    world, entities, genesis, _rejected, order_index = build_genesis(
        seed, scenario, lineage,
    )
    valid_parent_ids = {event["id"] for event in genesis}
    rng = DeterministicRNG(seed)
    cache: dict = {}
    warn_events = []
    selected_goals = []
    for tick in range(1, ticks + 1):
        accepted, _rej, order_index, diagnostics = run_tick(
            "warn-fixture", entities, world["terrain"], tick, rng, order_index,
            lineage, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
            entity_json_cache=cache,
        )
        for event in accepted:
            valid_parent_ids.add(event["id"])
            if (event.get("living_action") or {}).get("action_type") == "warn":
                warn_events.append(event)
        diag = diagnostics.get("person-001") or {}
        if diag.get("selected_goal"):
            selected_goals.append(diag["selected_goal"])
    return warn_events, selected_goals, entities


def test_warn_danger_commits_when_a_sated_scout_has_an_adjacent_target():
    """POSITIVE half of the pair: the WARN_DANGER goal reaches a committed
    `warn` action through the real commit pipeline.

    Asserts COMMIT, not selection, and the distinction is the whole point:
    organically WARN_DANGER already WINS the selection and still never commits
    (measured -- won at ticks 1 and 2 on seed stage6-integrated, `warn` absent
    from actions_by_type for all 320 ticks). A selection-only assertion would
    therefore have been vacuous.

    SCOPE LIMIT, stated deliberately: this fixture removes the move step by
    placing the target adjacent, so it does NOT cover multi-step plan survival
    -- i.e. whether a WARN_DANGER plan that must first travel to its target
    survives to its terminal step. That is exactly the property the organic
    trace loses, and it is recorded as a deferral, not covered here.
    """
    warn_events, selected_goals, _entities = _run_warn_camp(parched=False)

    assert warn_events, (
        "no `warn` action committed; WARN_DANGER selected goals were "
        f"{selected_goals}"
    )
    assert "WARN_DANGER" in selected_goals
    first = warn_events[0]
    assert first["event_type"] == "social_warn"
    assert first["entity_id"] == "person-001"
    assert first["living_action"]["action_type"] == "warn"

    # The domain caps a scout at two warns (`_action_count(entity, "warn") < 2`,
    # living_settlement_domain.py). Pinned so the cap cannot drift unnoticed,
    # and so this fixture cannot silently degrade into a one-shot check.
    assert len(warn_events) == 2, (
        f"expected exactly 2 warns before the cap closes, got {len(warn_events)}"
    )


def test_survival_pressure_displaces_warn_danger_and_that_is_correct():
    """NEGATIVE half of the pair: invariant C-6 -- influence and social goals
    never outrank urgent survival.

    Identical fixture, scout parched and starving. WARN_DANGER must NOT commit,
    and that is the CORRECT outcome, not a defect: a dying agent prioritising a
    neighbourly warning over water would violate survival dominance.

    NOTE ON WHAT THIS IS NOT. This is not the mechanism that suppressed `warn`
    in the organic trace. There the preemptor was REPAY_DEBT (score 27477 vs
    WARN_DANGER 23435) -- a social obligation, NOT a survival goal. That
    obligation-preemption is recorded as measured evidence in the deferral
    register; it is deliberately NOT asserted here as correct, because whether a
    debt should outrank a predator warning is an open scoring question parked
    for a future scoring-contract leg.
    """
    warn_events, selected_goals, _entities = _run_warn_camp(parched=True)

    assert not warn_events, (
        "a parched, starving scout committed a `warn` -- survival dominance "
        f"(C-6) is broken. Selected goals: {selected_goals}"
    )
    assert selected_goals, "fixture produced no decisions; it would be vacuous"
    assert set(selected_goals) & {
        "DRINK_WATER", "EAT_CARRIED", "RETRIEVE_FOOD", "GATHER_FOOD",
    }, (
        "expected survival goals to win for a parched scout; got "
        f"{sorted(set(selected_goals))}"
    )


def test_short_captured_trace_has_causality_and_replays_exactly():
    result = run_living_agent_harness(
        "stage6-replay", ticks=3, capture_events=True,
    )
    known_event_ids = set()
    signal_events = 0
    for event in result["accepted_events"]:
        if not event.get("is_exogenous"):
            assert event["causal_parent_event_ids"]
            assert set(event["causal_parent_event_ids"]).issubset(known_event_ids)
        for new_entity in event.get("mutation", {}).get("new_entities", {}).values():
            assert new_entity["creation_event_id"] == event["id"]
            assert new_entity["last_event_id"] == event["id"]
            if new_entity.get("type") == "signal":
                signal_events += 1
                assert new_entity["source_event_id"] == event["id"]
        living_action = event.get("living_action")
        if living_action:
            assert event["source_proposal_id"] in living_action["source_proposal_ids"]
            assert event["id"] in living_action["accepted_event_ids"]
        known_event_ids.add(event["id"])
    assert signal_events >= 1

    rebuilt = {}
    for event in result["accepted_events"]:
        apply_mutation(rebuilt, copy.deepcopy(event["mutation"]))
    assert rebuilt == result["entities"]


def test_same_seed_and_reversed_entity_map_produce_the_same_trace():
    first = run_living_agent_harness("stage6-order", ticks=12, run_id="stage6-a")
    second = run_living_agent_harness(
        "stage6-order", ticks=12, run_id="stage6-b", reverse_entity_order=True,
    )

    assert first["event_hashes"] == second["event_hashes"]
    assert first["frame_hashes"] == second["frame_hashes"]
    assert first["final_state_hash"] == second["final_state_hash"]
    assert first["entities"] == second["entities"]
    assert first["summary"] == second["summary"]


def test_reported_false_information_is_selective_and_not_truth_leaking():
    result = run_living_agent_harness("stage6-information", ticks=1)
    recipients = {"person-000", "person-002", "person-006"}
    excluded = {"person-004", "person-005", "person-007"}

    for person_id in recipients:
        claims = [
            fact
            for fact in result["entities"][person_id]["knowledge"]["facts"].values()
            if fact.get("subject") == "storage-private"
            and fact.get("provenance_kind") == "reported"
        ]
        assert claims
        assert claims[0]["properties"]["access"] == "public"
        assert claims[0]["deceptive_source_claim"] is False
    for person_id in excluded:
        claims = [
            fact
            for fact in result["entities"][person_id]["knowledge"]["facts"].values()
            if fact.get("subject") == "storage-private"
            and fact.get("provenance_kind") == "reported"
        ]
        assert not claims


def test_false_belief_detection_flags_a_known_deceptive_report():
    """Dedicated, non-vacuous net for false-belief detection (adversarial review
    finding F-04, memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md): the loosened
    `false_belief_count >= 0` assertion above cannot fail, so it no longer catches
    a regression in this counter. This test reuses the same stage6-information
    genesis fixture as test_reported_false_information_is_selective_and_not_truth_
    leaking above: the scenario's genesis `signal-false-rumour` tells person-000/
    002/006 that storage-private is public+open, which the test self-verifies
    mismatches the canonical private+closed storage-private entity -- a real,
    controlled false belief this counter must catch every run. It resolves at
    tick 1, before any leg's idle-time behaviour change can alter which agent
    reaches it, so unlike the 30-tick integrated trace above it is not
    sensitive to that class of drift.
    """
    result = run_living_agent_harness("stage6-information", ticks=1)

    canonical = result["entities"]["storage-private"]
    assert canonical["access"] == "private"
    assert canonical["open"] is False

    mismatched_recipients = 0
    for person_id in ("person-000", "person-002", "person-006"):
        claims = [
            fact
            for fact in result["entities"][person_id]["knowledge"]["facts"].values()
            if fact.get("subject") == "storage-private"
            and fact.get("provenance_kind") == "reported"
        ]
        assert claims
        assert claims[0]["properties"]["access"] == "public"
        assert claims[0]["properties"]["access"] != canonical["access"]
        mismatched_recipients += 1

    assert mismatched_recipients == 3
    assert result["summary"]["false_belief_count"] >= mismatched_recipients


def test_storm_warning_signal_receives_accepted_event_provenance():
    seed = "stage6-storm"
    scenario = get_scenario("living_settlement")
    lineage = _lineage(seed)
    world, entities, genesis, rejected, order = build_genesis(seed, scenario, lineage)
    assert not rejected
    valid_ids = {event["id"] for event in genesis}

    accepted, _rejected, _order, _diagnostics = run_tick(
        "stage6-storm-run", entities, world["terrain"], 40,
        DeterministicRNG(seed), order, lineage, scenario.enabled_domains,
        valid_causal_parent_event_ids=valid_ids,
    )
    weather_event = next(
        event for event in accepted if event["event_type"] == "weather_transition"
    )
    signal = weather_event["mutation"]["new_entities"]["signal-weather-40"]

    assert signal["message"] == {"environmental_threat": "storm"}
    assert signal["source_event_id"] == weather_event["id"]
    assert signal["creation_event_id"] == weather_event["id"]
