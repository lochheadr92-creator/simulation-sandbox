"""
Phase 5A4a — atomic transactional tick persistence (live Mongo replica set).
"""
from __future__ import annotations

import asyncio
import copy
import os
import sys
import uuid
from functools import wraps
from pathlib import Path

import pytest
from bson import BSON

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SIM_SANDBOX_TX_INJECT", "1")

from core.db import db, ensure_indexes
from core.hashing import canonical_hash
from core.mutations import snapshot_for_hash
from core.run_service import (
    create_run, get_run, load_entities, step_run, build_precomputed_frame,
    lineage_key_for_run,
)
from core.storage.frame_transaction import (
    ConcurrentModification,
    FrameCapacityError,
    InjectedTransactionFailure,
    PrecomputedFrame,
    RunIntegrityMismatch,
    RunUnderMaintenance,
    acquire_maintenance,
    clear_test_failure_injection,
    enable_test_failure_injection,
    commit_frame_atomically,
    head_revision_of,
    inspect_projection_integrity,
    rebuild_projection_atomically,
    release_maintenance,
    resolve_commit_status,
    validate_frame_capacity,
    bson_size,
    MAX_ENTITY_BSON_BYTES,
)
from tests.helpers.synthetic_transfer import overlapping_transfer_batch, progressive_commit


# Shared loop so Motor is not bound to a closed asyncio.run() loop.
_LOOP = None


def _loop():
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_LOOP)
    return _LOOP


def async_test(function):
    @wraps(function)
    def run(*args, **kwargs):
        return _loop().run_until_complete(function(*args, **kwargs))
    return run


async def _setup():
    # Drop incompatible legacy index if present from an earlier attempt.
    try:
        await db.commit_frames.drop_index("uq_run_frame_identity")
    except Exception:
        pass
    await ensure_indexes()
    clear_test_failure_injection()


async def _fresh_run(seed=None):
    seed = seed or f"tx-{uuid.uuid4().hex[:8]}"
    return await create_run(seed, "basic_survival")


@async_test
async def test_successful_atomic_tick():
    await _setup()
    run = await _fresh_run("tx-success")
    before = await get_run(run["id"])
    frames = await step_run(run["id"], 1)
    after = await get_run(run["id"])
    assert len(frames) == 1
    assert after["current_tick"] == before["current_tick"] + 1
    assert head_revision_of(after) == head_revision_of(before) + 1
    frame = await db.commit_frames.find_one(
        {"run_id": run["id"], "tick": after["current_tick"]}, {"_id": 0},
    )
    assert frame is not None
    assert frame["ending_state_hash"] == after["last_state_hash"]
    assert frame.get("frame_identity_hash")


@async_test
async def test_events_and_projections_committed_together():
    await _setup()
    run = await _fresh_run("tx-together")
    await step_run(run["id"], 3)
    after = await get_run(run["id"])
    assert after["current_tick"] == 3
    assert await db.commit_frames.count_documents({"run_id": run["id"]}) >= 4  # genesis + 3


INJECT_POINTS = [
    "before_events", "after_events", "after_rejections", "after_entities",
    "after_commit_frame", "before_cas", "after_cas",
]


@async_test
async def test_all_injected_failures_leave_no_partial_frame():
    await _setup()
    for point in INJECT_POINTS:
        run = await _fresh_run(f"tx-inj-{point[:10]}")
        head = await get_run(run["id"])
        tick0 = head["current_tick"]
        rev0 = head_revision_of(head)
        order0 = head["next_order_index"]
        hash0 = head["last_state_hash"]
        events0 = await db.accepted_events.count_documents({"run_id": run["id"]})
        frames0 = await db.commit_frames.count_documents({"run_id": run["id"]})
        rejections0 = await db.rejected_proposals.count_documents({"run_id": run["id"]})

        enable_test_failure_injection(point)
        try:
            with pytest.raises(InjectedTransactionFailure):
                await step_run(run["id"], 1)
        finally:
            clear_test_failure_injection()

        head2 = await get_run(run["id"])
        assert head2["current_tick"] == tick0, point
        assert head_revision_of(head2) == rev0, point
        assert head2["next_order_index"] == order0, point
        assert head2["last_state_hash"] == hash0, point
        assert await db.accepted_events.count_documents({"run_id": run["id"]}) == events0, point
        assert await db.commit_frames.count_documents({"run_id": run["id"]}) == frames0, point
        assert await db.rejected_proposals.count_documents({"run_id": run["id"]}) == rejections0, point

        frames = await step_run(run["id"], 1)
        assert len(frames) == 1, point
        head3 = await get_run(run["id"])
        assert head3["current_tick"] == tick0 + 1, point
        assert head_revision_of(head3) == rev0 + 1, point


@async_test
async def test_cas_mismatch_returns_concurrent_modification():
    await _setup()
    run = await _fresh_run("tx-cas")
    head = await get_run(run["id"])
    entities = await load_entities(run["id"])
    frame = build_precomputed_frame(
        head, entities, [], [], head["current_tick"] + 1,
        head["last_state_hash"], head["last_state_hash"],
        head["next_order_index"], head["next_order_index"], set(),
    )
    await db.kernel_runs.update_one({"id": run["id"]}, {"$inc": {"head_revision": 1}})
    with pytest.raises(ConcurrentModification):
        await commit_frame_atomically(frame)
    head2 = await get_run(run["id"])
    assert head2["current_tick"] == head["current_tick"]


@async_test
async def test_cas_mismatch_never_writes_frame():
    await _setup()
    run = await _fresh_run("tx-cas-noretry")
    head = await get_run(run["id"])
    entities = await load_entities(run["id"])
    frame = build_precomputed_frame(
        head, entities, [], [], head["current_tick"] + 1,
        head["last_state_hash"], "deadbeef" * 8,
        head["next_order_index"], head["next_order_index"] + 1, set(),
    )
    await db.kernel_runs.update_one({"id": run["id"]}, {"$set": {"head_revision": 999}})
    with pytest.raises(ConcurrentModification):
        await commit_frame_atomically(frame)
    assert await db.commit_frames.find_one(
        {"run_id": run["id"], "tick": head["current_tick"] + 1}
    ) is None


def test_bson_size_uses_exact_encoding():
    doc = {"a": 1, "b": "x" * 100}
    assert bson_size(doc) == len(BSON.encode(doc))
    assert bson_size(doc) != sys.getsizeof(doc)


def test_oversized_entity_fails_before_transaction():
    huge = {"id": "e1", "run_id": "r", "blob": "x" * (MAX_ENTITY_BSON_BYTES + 1000)}
    frame = PrecomputedFrame(
        run_id="r", expected_tick=0, new_tick=1, expected_head_revision=0,
        expected_state_hash="h", expected_next_order_index=0,
        starting_state_hash="h", ending_state_hash="h2", next_order_index=0,
        accepted_events=[], rejected_proposals=[], entity_docs=[huge],
        removed_entity_ids=[], commit_frame={"id": "f", "run_id": "r", "tick": 1},
        hash_policy_version="tick-bound-v1",
    )
    frame.compute_identity()
    with pytest.raises(FrameCapacityError) as ei:
        validate_frame_capacity(frame)
    assert ei.value.code == "ENTITY_DOCUMENT_EXCEEDS_LIMIT"


def test_oversized_event_fails_preflight():
    huge_event = {"id": "evt-1", "run_id": "r", "payload": "y" * (11 * 1024 * 1024)}
    frame = PrecomputedFrame(
        run_id="r", expected_tick=0, new_tick=1, expected_head_revision=0,
        expected_state_hash="h", expected_next_order_index=0,
        starting_state_hash="h", ending_state_hash="h2", next_order_index=1,
        accepted_events=[huge_event], rejected_proposals=[], entity_docs=[],
        removed_entity_ids=[], commit_frame={"id": "f", "run_id": "r", "tick": 1},
        hash_policy_version="tick-bound-v1",
    )
    frame.compute_identity()
    with pytest.raises(FrameCapacityError) as ei:
        validate_frame_capacity(frame)
    assert ei.value.code == "EVENT_DOCUMENT_EXCEEDS_LIMIT"


def test_oversized_rejection_fails_preflight():
    huge = {"id": "rej-1", "run_id": "r", "blob": "z" * (6 * 1024 * 1024)}
    frame = PrecomputedFrame(
        run_id="r", expected_tick=0, new_tick=1, expected_head_revision=0,
        expected_state_hash="h", expected_next_order_index=0,
        starting_state_hash="h", ending_state_hash="h2", next_order_index=0,
        accepted_events=[], rejected_proposals=[huge], entity_docs=[],
        removed_entity_ids=[], commit_frame={"id": "f", "run_id": "r", "tick": 1},
        hash_policy_version="tick-bound-v1",
    )
    frame.compute_identity()
    with pytest.raises(FrameCapacityError) as ei:
        validate_frame_capacity(frame)
    assert ei.value.code == "REJECTION_DOCUMENT_EXCEEDS_LIMIT"


@async_test
async def test_integrity_mismatch_blocks_stepping():
    await _setup()
    run = await _fresh_run("tx-integ")
    await step_run(run["id"], 1)
    person = await db.entities.find_one({"run_id": run["id"], "type": "person"}, {"_id": 0})
    await db.entities.update_one(
        {"run_id": run["id"], "id": person["id"]},
        {"$set": {"hunger": 999999}},
    )
    with pytest.raises(RunIntegrityMismatch):
        await step_run(run["id"], 1)


@async_test
async def test_maintenance_blocks_stepping_and_advances_revision():
    await _setup()
    run = await _fresh_run("tx-maint")
    before = head_revision_of(await get_run(run["id"]))
    await acquire_maintenance(run["id"], "op-1")
    after = await get_run(run["id"])
    assert after["maintenance_mode"] is True
    assert head_revision_of(after) == before + 1
    with pytest.raises(RunUnderMaintenance):
        await step_run(run["id"], 1)
    await release_maintenance(run["id"], "op-1")
    await step_run(run["id"], 1)


@async_test
async def test_manual_rebuild_restores_projections():
    await _setup()
    run = await _fresh_run("tx-rebuild")
    await step_run(run["id"], 5)
    head = await get_run(run["id"])
    lineage = lineage_key_for_run(head)
    person = await db.entities.find_one({"run_id": run["id"], "type": "person"})
    await db.entities.update_one(
        {"_id": person["_id"]}, {"$set": {"hunger": 1}},
    )
    op = "rebuild-test-1"
    await db.kernel_runs.update_one({"id": run["id"]}, {"$set": {"status": "paused"}})
    await acquire_maintenance(run["id"], op)
    result = await rebuild_projection_atomically(
        run["id"], op, lineage, head["last_state_hash"], head["current_tick"],
    )
    assert result["rebuilt_hash"] == head["last_state_hash"]
    await release_maintenance(run["id"], op, status="paused")
    report = await inspect_projection_integrity(run["id"], lineage, head["hash_policy_version"])
    assert report["ok"] is True


@async_test
async def test_failed_rebuild_leaves_quarantined():
    await _setup()
    run = await _fresh_run("tx-rebuild-fail")
    await step_run(run["id"], 2)
    head = await get_run(run["id"])
    lineage = lineage_key_for_run(head)
    op = "rebuild-fail-1"
    await acquire_maintenance(run["id"], op)
    with pytest.raises(RunIntegrityMismatch):
        await rebuild_projection_atomically(
            run["id"], op, lineage, "not-the-real-hash", head["current_tick"],
        )
    await release_maintenance(run["id"], op, quarantine=True)
    head2 = await get_run(run["id"])
    assert head2.get("quarantined") is True


def test_100_overlapping_transfers_conserve_resources():
    entities = {
        "A": {"type": "node", "resource": 40},
        "B": {"type": "node", "resource": 40},
        "C": {"type": "node", "resource": 40},
    }
    total0 = sum(e["resource"] for e in entities.values())
    batch = overlapping_transfer_batch(entities, tick=1)
    assert len(batch) == 100
    accepted, rejected, _ = progressive_commit(
        entities, batch, 1, "lin|test", "run-x", 0, "frame-1",
    )
    total1 = sum(e["resource"] for e in entities.values())
    assert total1 == total0
    assert all(e["resource"] >= 0 for e in entities.values())
    assert len(accepted) + len(rejected) == 100
    assert len(accepted) > 0


def test_reversed_proposal_arrival_identical_result():
    def run_once(reverse=False):
        entities = {
            "A": {"type": "node", "resource": 40},
            "B": {"type": "node", "resource": 40},
            "C": {"type": "node", "resource": 40},
        }
        batch = overlapping_transfer_batch(entities, tick=7)
        if reverse:
            batch = list(reversed(batch))
        accepted, rejected, nxt = progressive_commit(
            entities, batch, 7, "lin|rev", "run-r", 0, "frame-7",
        )
        return {
            "entities": copy.deepcopy(entities),
            "accepted_ids": [a["id"] for a in accepted],
            "rejected_ids": [r["id"] for r in rejected],
            "hash": canonical_hash(snapshot_for_hash(entities, 7, "lin|rev")),
            "next": nxt,
        }

    a = run_once(False)
    b = run_once(True)
    assert a["accepted_ids"] == b["accepted_ids"]
    assert a["rejected_ids"] == b["rejected_ids"]
    assert a["entities"] == b["entities"]
    assert a["hash"] == b["hash"]


def test_repeated_identical_transfer_runs():
    results = []
    for _ in range(3):
        entities = {
            "A": {"type": "node", "resource": 40},
            "B": {"type": "node", "resource": 40},
            "C": {"type": "node", "resource": 40},
        }
        batch = overlapping_transfer_batch(entities, tick=3)
        accepted, rejected, _ = progressive_commit(
            entities, batch, 3, "lin|rep", "run-p", 0, "frame-3",
        )
        results.append((
            [a["id"] for a in accepted],
            [r["id"] for r in rejected],
            copy.deepcopy(entities),
        ))
    assert results[0] == results[1] == results[2]


@async_test
async def test_resolve_commit_status_after_success():
    await _setup()
    run = await _fresh_run("tx-resolve")
    await step_run(run["id"], 1)
    head = await get_run(run["id"])
    cf = await db.commit_frames.find_one(
        {"run_id": run["id"], "tick": head["current_tick"]}, {"_id": 0},
    )
    pre = PrecomputedFrame(
        run_id=run["id"],
        expected_tick=head["current_tick"] - 1,
        new_tick=head["current_tick"],
        expected_head_revision=head_revision_of(head) - 1,
        expected_state_hash=cf["starting_state_hash"],
        expected_next_order_index=0,
        starting_state_hash=cf["starting_state_hash"],
        ending_state_hash=cf["ending_state_hash"],
        next_order_index=head["next_order_index"],
        accepted_events=[{"id": i} for i in cf.get("accepted_event_ids", [])],
        rejected_proposals=[{"id": i} for i in cf.get("rejected_proposal_ids", [])],
        entity_docs=[],
        removed_entity_ids=[],
        commit_frame=cf,
        hash_policy_version=cf.get("hash_policy_version", "tick-bound-v1"),
        frame_identity_hash=cf.get("frame_identity_hash", ""),
    )
    status = await resolve_commit_status(pre)
    assert status == "committed"
    assert cf.get("frame_identity_hash")


@async_test
async def test_new_run_has_head_revision():
    await _setup()
    run = await _fresh_run("tx-rev0")
    assert run.get("head_revision") == 0
    assert run.get("maintenance_mode") is False
    assert run.get("quarantined") is False


@async_test
async def test_idempotent_exact_frame_retry():
    await _setup()
    run = await _fresh_run("tx-idem")
    head = await get_run(run["id"])
    entities = await load_entities(run["id"])
    # Commit empty frame once via step, then re-commit same precomputed frame
    await step_run(run["id"], 1)
    head = await get_run(run["id"])
    # Manually craft already-committed frame matching head
    cf = await db.commit_frames.find_one(
        {"run_id": run["id"], "tick": head["current_tick"]}, {"_id": 0},
    )
    frame = PrecomputedFrame(
        run_id=run["id"],
        expected_tick=head["current_tick"] - 1,
        new_tick=head["current_tick"],
        expected_head_revision=head_revision_of(head) - 1,
        expected_state_hash=cf["starting_state_hash"],
        expected_next_order_index=0,
        starting_state_hash=cf["starting_state_hash"],
        ending_state_hash=cf["ending_state_hash"],
        next_order_index=head["next_order_index"],
        accepted_events=[{"id": i, "run_id": run["id"]} for i in cf.get("accepted_event_ids", [])],
        rejected_proposals=[{"id": i, "run_id": run["id"]} for i in cf.get("rejected_proposal_ids", [])],
        entity_docs=[],
        removed_entity_ids=[],
        commit_frame=dict(cf),
        hash_policy_version=cf.get("hash_policy_version", "tick-bound-v1"),
    )
    frame.frame_identity_hash = cf.get("frame_identity_hash") or frame.compute_identity()
    result = await commit_frame_atomically(frame)
    assert result["status"] in ("already_committed", "committed", "committed_resolved")
    # Head not double-advanced relative to post-step
    head2 = await get_run(run["id"])
    assert head2["current_tick"] == head["current_tick"]
    assert head_revision_of(head2) == head_revision_of(head)
