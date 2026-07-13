"""Concurrency stress for transactional tick CAS (Phase 5A4a)."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from functools import wraps
from pathlib import Path

import motor.motor_asyncio
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core import db as core_db
from core import run_service, retention_service
from core.storage import frame_transaction as frame_tx
from core.run_service import create_run, get_run, load_entities, step_run, build_precomputed_frame
from core.storage.frame_transaction import (
    ConcurrentModification,
    clear_test_failure_injection,
    commit_frame_atomically,
    head_revision_of,
)
from domains.association_contracts import ASSOCIATION_REGISTRY_ID


def _rebind_motor_to_running_loop():
    """Motor clients bind to the creating loop; rebind after asyncio.run resets."""
    client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])
    database = client[os.environ["DB_NAME"]]
    core_db.client = client
    core_db.db = database
    run_service.db = database
    run_service.client = client
    retention_service.db = database
    frame_tx.db = database
    frame_tx.client = client
    return client, database


def async_test(function):
    @wraps(function)
    def run(*args, **kwargs):
        async def _runner():
            previous_bindings = (
                core_db.client,
                core_db.db,
                run_service.client,
                run_service.db,
                retention_service.db,
                frame_tx.client,
                frame_tx.db,
            )
            client, _ = _rebind_motor_to_running_loop()
            try:
                return await function(*args, **kwargs)
            finally:
                (
                    core_db.client,
                    core_db.db,
                    run_service.client,
                    run_service.db,
                    retention_service.db,
                    frame_tx.client,
                    frame_tx.db,
                ) = previous_bindings
                client.close()
        return asyncio.run(_runner())
    return run


@async_test
async def test_concurrent_identical_steps_single_head_advance():
    db = core_db.db
    await core_db.ensure_indexes()
    clear_test_failure_injection()
    run = await create_run(f"conc-{uuid.uuid4().hex[:8]}", "basic_survival")
    head = await get_run(run["id"])
    rev0 = head_revision_of(head)

    async def attempt():
        try:
            return ("ok", await step_run(run["id"], 1))
        except ConcurrentModification:
            return ("cas", None)

    results = await asyncio.gather(attempt(), attempt())
    statuses = [r[0] for r in results]
    assert statuses.count("ok") >= 1
    head2 = await get_run(run["id"])
    assert head2["current_tick"] == head["current_tick"] + 1
    assert head_revision_of(head2) == rev0 + 1
    assert await db.commit_frames.count_documents(
        {"run_id": run["id"], "tick": head2["current_tick"]}
    ) == 1


@async_test
async def test_stale_precomputed_frame_cas_conflict():
    await core_db.ensure_indexes()
    clear_test_failure_injection()
    run = await create_run(f"stale-{uuid.uuid4().hex[:8]}", "basic_survival")
    head = await get_run(run["id"])
    entities = await load_entities(run["id"])
    await step_run(run["id"], 1)
    stale = build_precomputed_frame(
        head, entities, [], [], head["current_tick"] + 1,
        head["last_state_hash"], "ffff" * 16,
        head["next_order_index"], head["next_order_index"] + 1, set(),
    )
    with pytest.raises(ConcurrentModification):
        await commit_frame_atomically(stale)


@async_test
async def test_concurrent_stage7a_steps_do_not_duplicate_groups_or_head():
    db = core_db.db
    await core_db.ensure_indexes()
    clear_test_failure_injection()
    run = await create_run(
        f"stage7a-conc-{uuid.uuid4().hex[:8]}", "emergent_groups",
    )
    await step_run(run["id"], 6)
    before = await get_run(run["id"])
    revision_before = head_revision_of(before)
    registry_before = await db.entities.find_one(
        {"run_id": run["id"], "id": ASSOCIATION_REGISTRY_ID}, {"_id": 0},
    )
    assert registry_before is not None

    async def attempt():
        try:
            return ("ok", await step_run(run["id"], 1))
        except ConcurrentModification:
            return ("cas", None)

    results = await asyncio.gather(attempt(), attempt())
    assert any(status == "ok" for status, _value in results)
    after = await get_run(run["id"])
    assert after["current_tick"] == before["current_tick"] + 1
    assert head_revision_of(after) == revision_before + 1
    assert await db.commit_frames.count_documents({
        "run_id": run["id"], "tick": after["current_tick"],
    }) == 1

    registry = await db.entities.find_one(
        {"run_id": run["id"], "id": ASSOCIATION_REGISTRY_ID}, {"_id": 0},
    )
    assert registry is not None
    candidate_ids = list((registry.get("group_candidates") or {}).keys())
    assert len(candidate_ids) == len(set(candidate_ids))
    assert int(registry["revision"]) == int(registry_before["revision"]) + 1
