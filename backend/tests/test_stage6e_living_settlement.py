import copy

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


def test_integrated_camp_closes_the_living_agent_loop_and_replays():
    result = run_living_agent_harness(
        "stage6-integrated", ticks=30,
    )
    summary = result["summary"]

    assert {
        "move", "drink", "consume", "gather", "retrieve", "repair",
        "cooperate", "warn", "lie", "share_information", "promise",
        "trade", "threaten", "apologise", "reconcile",
    }.issubset(summary["actions_by_type"])
    assert summary["decisions_by_kind"]["critical_interrupt"] >= 1
    assert summary["decisions_by_kind"]["resumption"] >= 1
    assert summary["decisions_by_kind"]["failed_plan_replan"] >= 1
    assert summary["rejected_proposal_count"] >= 1
    assert summary["resource_depletion"] >= 1
    assert summary["weather_conditions"] == ["rain"]

    assert summary["reported_claim_count"] >= 1
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
