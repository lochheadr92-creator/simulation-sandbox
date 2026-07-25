"""Capability Stage 6 contract, compatibility, and bound tests."""
import copy

import pytest

from core.hashing import canonical_hash
from core.rng import DeterministicRNG
from domains.living_agent_contracts import (
    ACTION_SCHEMA_VERSION,
    LIMITS,
    LIVING_AGENT_SCHEMA_VERSION,
    LivingAgentCompatibilityError,
    PRESSURE_KINDS,
    SOCIAL_ACTION_TYPES,
    PHYSICAL_ACTION_TYPES,
    compat_action,
    compat_living_agent_state,
    compat_plan,
    default_affordances,
    empty_living_agent_state,
    stage6_schema_manifest,
)


def test_identical_seed_and_entity_produce_identical_traits_and_pressures():
    left = empty_living_agent_state("person-001", 0, DeterministicRNG("stage6-seed"))
    right = empty_living_agent_state("person-001", 0, DeterministicRNG("stage6-seed"))
    other = empty_living_agent_state("person-002", 0, DeterministicRNG("stage6-seed"))

    assert left == right
    assert left["traits"] != other["traits"]
    assert tuple(left["pressures"]) == PRESSURE_KINDS
    assert all(row["individual_weight"] > 0 for row in left["pressures"].values())


def test_compatibility_is_copy_only_and_enforces_all_limits():
    state = empty_living_agent_state("person-001", 0)
    state["memories"] = {
        f"memory-{i:03d}": {"last_recalled_tick": i} for i in range(LIMITS.memories_per_entity + 7)
    }
    state["relationships"] = {
        f"person-{i:03d}": {"last_changed_tick": i} for i in range(LIMITS.relationship_records + 7)
    }
    state["decision_history"] = list(range(LIMITS.decision_receipts_retained + 7))
    original = copy.deepcopy(state)

    normalized = compat_living_agent_state(state, "person-001", 10)

    assert state == original
    assert len(normalized["memories"]) == LIMITS.memories_per_entity
    assert len(normalized["relationships"]) == LIMITS.relationship_records
    assert len(normalized["decision_history"]) == LIMITS.decision_receipts_retained
    assert list(normalized["memories"]) == sorted(normalized["memories"])


def test_unknown_canonical_schema_fails_closed():
    with pytest.raises(LivingAgentCompatibilityError, match="unsupported living-agent schema"):
        compat_living_agent_state({"schema_version": "future-v99"}, "person-001", 2)


def test_seeded_traits_stream_is_stateful_across_calls_not_a_pure_function():
    """Demonstrates the actual risk the guard below exists for: seeded_traits'
    RNG stream is keyed only by entity_id (domains/living_agent_contracts.py),
    and core.rng.DeterministicRNG.stream caches + keeps advancing the same
    stream object across calls -- so calling it twice for the same entity on
    the same rng instance does NOT reproduce the first draw."""
    rng = DeterministicRNG("stage6-seed")
    first = empty_living_agent_state("person-001", 0, rng)
    second = empty_living_agent_state("person-001", 0, rng)
    assert first["traits"] != second["traits"]


def test_reaching_seeded_traits_with_incomplete_committed_traits_fails_closed():
    """KIMI review, 2026-07-25: an entity with existing living_agent state
    but missing/incomplete committed traits must not silently reseed from
    the tick-less, already-advanced RNG stream -- that value would depend on
    how many times this entity's stream happened to be touched before now,
    not just (seed, entity_id): non-reproducible, and not reachable in any
    shipped scenario today (every shipped scenario's genesis persons commit
    full traits on their true first tick)."""
    incomplete = empty_living_agent_state("person-001", 0)  # rng=None: default_traits, complete
    del incomplete["traits"]["risk_tolerance"]
    with pytest.raises(LivingAgentCompatibilityError, match="incomplete or missing committed traits"):
        compat_living_agent_state(incomplete, "person-001", 2, DeterministicRNG("stage6-seed"))

    missing_entirely = empty_living_agent_state("person-001", 0)
    del missing_entirely["traits"]
    with pytest.raises(LivingAgentCompatibilityError, match="incomplete or missing committed traits"):
        compat_living_agent_state(missing_entirely, "person-001", 2, DeterministicRNG("stage6-seed"))


def test_incomplete_traits_still_lenient_when_rng_is_none():
    """The guard is scoped to rng is not None (the only case with an actual
    reproducibility risk): rng=None callers use the stateless, hash-based
    default_traits fallback, so they keep their exact prior (lenient)
    behaviour -- this must NOT start raising."""
    incomplete = empty_living_agent_state("person-001", 0)
    del incomplete["traits"]["risk_tolerance"]
    normalized = compat_living_agent_state(incomplete, "person-001", 2)
    assert "risk_tolerance" in normalized["traits"]  # backfilled from default_traits, not an error


def test_legacy_plan_and_action_upgrade_without_losing_existing_fields():
    plan = compat_plan(
        {"goal": "SEEK_WATER", "steps": ["TRAVEL_WATER", "DRINK"], "step_index": 1, "status": "active"},
        actor_id="person-001",
        tick=4,
    )
    action = compat_action(
        {"type": "drink", "status": "performing", "ticks_spent": 0, "ticks_required": 1},
        actor_id="person-001",
        tick=4,
        plan=plan,
    )

    assert plan["steps"] == ["TRAVEL_WATER", "DRINK"]
    assert plan["step_records"][0]["status"] == "completed"
    assert action["schema_version"] == ACTION_SCHEMA_VERSION
    assert action["plan_id"] == plan["plan_id"]
    assert action["actor_id"] == "person-001"


def test_affordance_defaults_and_action_catalog_are_explicit():
    storage = default_affordances({"type": "storage", "access": "shared"})
    tool = default_affordances({"type": "tool"})

    assert storage["storage"] is True
    assert storage["openable"] is True
    assert storage["access"] == "shared"
    assert tool["tool"] is True
    assert tool["carryable"] is True
    assert {"move", "gather", "store", "retrieve", "repair", "take", "help", "warn"} <= PHYSICAL_ACTION_TYPES
    assert {"request_help", "lie", "promise", "reconcile", "trade"} <= SOCIAL_ACTION_TYPES


def test_schema_manifest_is_stable_and_complete():
    first = stage6_schema_manifest()
    second = stage6_schema_manifest()
    assert first == second
    assert first["living_agent"] == LIVING_AGENT_SCHEMA_VERSION
    assert canonical_hash(first) == canonical_hash(second)
    assert first["limits"]["planning_depth"] == LIMITS.planning_depth
