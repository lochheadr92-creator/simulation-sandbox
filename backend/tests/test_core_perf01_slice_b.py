"""CORE-PERF-01 Slice B -- fragment-cached world-snapshot serialization.

memory/CORE-PERF-01-TICK-VALIDATION-COST.md: the dominant per-tick cost
(Stage 1b, ~44% of wall on its own) is `canonical_hash(snapshot_for_hash(
entities, tick, lineage_key))` inside `run_commit_pipeline`, called once per
*accepted proposal* and re-serializing the entire world every time. Slice B
caches per-entity JSON fragments and splices them instead. The whole safety
argument (per the ratified proposal) is a byte-equality property check:
spliced output must always equal the direct `canonical_json(snapshot_for_
hash(...))` computation. These are the property/unit tests named in that
argument's item (1); item (2) (debug-assert-mode on every event) and item (3)
(the frozen-hash gate) are evidenced in memory/evidence/core-perf-01-slice-b/.
"""
import copy

from core.commit_pipeline import run_commit_frame
from core.hashing import canonical_hash, hash_canonical_json_string
from core.mutations import (
    apply_mutation,
    invalidate_entity_json_cache,
    snapshot_for_hash,
    spliced_snapshot_json,
)
from domains.base import DomainOutput


def _assert_splice_matches_direct(entities, tick, lineage, cache):
    spliced = spliced_snapshot_json(entities, tick, lineage, cache)
    direct = canonical_hash(snapshot_for_hash(entities, tick, lineage))
    assert hash_canonical_json_string(spliced) == direct


def test_spliced_snapshot_matches_direct_computation_on_a_cold_cache():
    entities = {
        "person-a": {"type": "person", "position": {"x": 1, "y": 1}, "health": 900},
        "shelter-a": {"type": "shelter", "position": {"x": 2, "y": 1}, "condition": 800},
    }
    cache = {}
    _assert_splice_matches_direct(entities, 5, "lineage-x", cache)
    assert set(cache) == {"person-a", "shelter-a"}


def test_spliced_snapshot_matches_direct_computation_on_empty_entities():
    _assert_splice_matches_direct({}, 0, "lineage-x", {})


def test_cache_reuse_across_calls_matches_direct_when_untouched():
    entities = {
        "person-a": {"type": "person", "health": 900},
        "person-b": {"type": "person", "health": 850},
    }
    cache = {}
    _assert_splice_matches_direct(entities, 1, "lineage-x", cache)
    # Second call, nothing changed, cache fully warm -- must still match, and
    # must not need to recompute anything (fragments are byte-identical
    # objects, proving they were reused rather than rebuilt).
    fragment_before = cache["person-a"]
    _assert_splice_matches_direct(entities, 2, "lineage-x", cache)
    assert cache["person-a"] is fragment_before


def test_invalidation_is_required_for_correctness_after_an_update():
    """Directly proves invalidate_entity_json_cache is load-bearing: without
    it, a stale cached fragment produces a WRONG spliced hash after a
    mutation; with it, the splice is correct again. This is the exact
    failure mode the whole mechanism must never allow into a real run."""
    entities = {"person-a": {"type": "person", "health": 900}}
    cache = {}
    spliced_snapshot_json(entities, 1, "lineage-x", cache)  # warm the cache

    mutation = {"entity_updates": {"person-a": {"health": 500}}}
    apply_mutation(entities, mutation)

    # Stale cache, NOT invalidated: splice now disagrees with direct.
    stale_spliced = spliced_snapshot_json(entities, 1, "lineage-x", dict(cache))
    stale_hash = hash_canonical_json_string(stale_spliced)
    direct_hash = canonical_hash(snapshot_for_hash(entities, 1, "lineage-x"))
    assert stale_hash != direct_hash, (
        "expected a stale, un-invalidated cache to diverge -- if this "
        "assertion fails, the whole cache mechanism could silently mask a "
        "missed invalidation site"
    )

    # Same cache, invalidated correctly: splice agrees again.
    invalidate_entity_json_cache(cache, mutation)
    _assert_splice_matches_direct(entities, 1, "lineage-x", cache)


def test_invalidation_covers_new_entities_and_removed_entities():
    entities = {"person-a": {"type": "person", "health": 900}}
    cache = {}
    spliced_snapshot_json(entities, 1, "lineage-x", cache)

    mutation = {
        "new_entities": {"shelter-a": {"type": "shelter", "condition": 900}},
        "entity_updates": {},
        "removed_entities": ["person-a"],
    }
    apply_mutation(entities, mutation)
    invalidate_entity_json_cache(cache, mutation)

    assert "shelter-a" not in cache  # new entity: not cached until next splice
    assert "person-a" not in cache  # removed entity: evicted, never resurface
    _assert_splice_matches_direct(entities, 2, "lineage-x", cache)
    assert "person-a" not in spliced_snapshot_json(entities, 2, "lineage-x", cache)


def test_entity_fields_needing_default_str_fallback_still_match():
    """canonical_json uses `default=str` for values json.dumps can't natively
    encode (e.g. a set). The per-entity fragment must handle this exactly
    like the direct whole-world serialization does."""
    entities = {"person-a": {"type": "person", "tags": {"a", "b", "c"}}}
    _assert_splice_matches_direct(entities, 1, "lineage-x", {})


def test_run_commit_frame_with_entity_json_cache_produces_identical_hashes_to_without():
    """End-to-end: a real commit frame, with and without the cache enabled,
    must produce byte-identical accepted-event post_state_hash values --
    this is the actual guarantee run_commit_frame's callers depend on."""
    def _entities():
        return {
            "person-a": {"type": "person", "position": {"x": 1, "y": 1}, "health": 900},
            "person-b": {"type": "person", "position": {"x": 2, "y": 1}, "health": 850},
        }

    proposal = {
        "proposal_family": "food",
        "proposal_type": "consume",
        "proposer_engine_id": "test",
        "entity_id": "person-a",
        "causal_parent_event_ids": [],
        "is_exogenous": True,
        "requested_time": 1,
        "phase": "agent",
        "touched_scope": ["person-a"],
        "preconditions": [],
        "mutation": {"entity_updates": {"person-a": {"health": 800}}},
    }

    entities_nocache = _entities()
    accepted_nocache, _r1, _o1 = run_commit_frame(
        entities_nocache, [DomainOutput(proposals=[copy.deepcopy(proposal)])],
        1, "lineage-x", "run", 0, "frame-1",
    )

    entities_cached = _entities()
    accepted_cached, _r2, _o2 = run_commit_frame(
        entities_cached, [DomainOutput(proposals=[copy.deepcopy(proposal)])],
        1, "lineage-x", "run", 0, "frame-1",
        entity_json_cache={}, debug_assert_fragment_cache=True,
    )

    assert accepted_nocache and accepted_cached
    assert accepted_nocache[0]["post_state_hash"] == accepted_cached[0]["post_state_hash"]
    assert entities_nocache == entities_cached
