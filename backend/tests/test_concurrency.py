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
from domains.group_state_contracts import GROUP_STATE_REGISTRY_ID


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


# --- CORE-INTEGRITY-002 revision accounting -------------------------------
# These tests used to assert `registry["revision"] == before + 1` after a
# concurrent step, i.e. that every step bumps the domain's revision. That is
# NOT an engine guarantee, and asserting it produced a false race signal for
# months. Measured serially, with no concurrency at all
# (backend/tools/_probe_ci002_serial_revision.py, emergent_groups, API path):
# 2 of 12 and 5 of 16 steps left the association revision unchanged, up to
# three consecutively.
#
# Why: both association_contracts.py:793 and group_state_contracts.py:434 bump
# `revision` UNCONDITIONALLY once a proposal is built, so the revision advances
# iff that proposal is ACCEPTED. Acceptance is not guaranteed --
# _valid_causal_parent_ids (run_service.py:288-292) scopes valid causal parents
# to each currently-live entity's CURRENT last_event_id, so a proposal citing
# an older evidence event is rejected with `causality.invalid_parent`
# (commit_pipeline.py:470). A rejected or absent proposal leaves the revision
# unchanged on a perfectly healthy tick.
#
# The real invariant, and the one that still catches a genuine lost update:
#     revision delta == number of accepted proposals from that engine
# accepted=1/delta=0 is the lost update; accepted=0/delta=1 is a phantom write;
# accepted=0/delta=0 is the legitimate no-op this file used to fail on.
# Single-attempt wait-for-precondition TIMEOUT, not a delay: a seed whose
# precondition becomes true at tick 14 fires at tick 14 regardless of this
# value. A ceiling costs nothing when the precondition arrives early; its only
# job is to bound failure.
#
# THIS NUMBER IS PRAGMATIC, NOT DERIVED. Say so plainly rather than dressing it
# up. The 30-seed measurement
# (memory/evidence/core-integrity-002/FORMATION-DISTRIBUTION-2026-07-26.md)
# found formation between ticks 11 and 187, bimodally -- 24/30 by tick 42, then
# nothing until 80, then a tail to 187 -- and the upper tail is UNCONVERGED at
# n=30 (the running maximum tripled inside the first 7 samples). No timeout can
# honestly be derived from that. 400 is chosen well above the observed maximum
# *because* the tail is unbounded, not because the evidence supports 400.
#
# NO RETRIES BY DESIGN. Retrying on a fresh seed would preferentially discard
# slow-forming worlds and keep fast-forming ones, biasing the sampled
# population -- which matters precisely because formation timing may correlate
# with registry churn and contention, i.e. with what this canary observes.
GROUP_STATE_SETUP_TIMEOUT_TICKS = 400


async def _domain_proposal_outcome(db, run_id: str, tick: int, engine_id: str):
    """(accepted_count, rejections) emitted by `engine_id` during `tick`."""
    accepted = await db.accepted_events.count_documents({
        "run_id": run_id, "simulation_time": tick,
        "proposer_engine_id": engine_id,
    })
    rejected_docs = await db.rejected_proposals.find(
        {"run_id": run_id, "simulation_time": tick}, {"_id": 0},
    ).to_list(length=200)
    rejections = [
        (doc.get("reason_code"), (doc.get("reason_detail") or "")[:120])
        for doc in rejected_docs
        if (doc.get("proposal_snapshot") or {}).get("proposer_engine_id") == engine_id
    ]
    return accepted, rejections


def _revision_report(engine_id, tick, before, after, accepted, rejections, extra=""):
    return (
        f"{engine_id} revision accounting failed at tick {tick}: "
        f"revision {before} -> {after} (delta {after - before}); "
        f"accepted proposals from {engine_id}: {accepted}; "
        f"rejections: {rejections or 'none'}.{extra} "
        f"A delta of 0 with 0 accepted is a LEGITIMATE no-op, not a failure; "
        f"a delta of 0 with 1 accepted is the CORE-INTEGRITY-002 lost update."
    )


def check_revision_accounting(engine_id, tick, before, after, accepted,
                              rejections=(), extra=""):
    """Pure discriminator. Raises AssertionError on a genuine violation only.

    Kept separate from the DB lookup so it can be exercised directly -- a
    canary that cannot be shown to fire is not a canary. See
    test_revision_accounting_discriminator_fires_only_on_real_violations.
    """
    report = _revision_report(engine_id, tick, before, after, accepted, rejections, extra)
    assert accepted <= 1, f"more than one accepted proposal in a single tick. {report}"
    assert after - before == accepted, report


async def _assert_revision_accounting(db, run_id, tick, engine_id, registry_before,
                                      registry_after, extra=""):
    """The concurrency canary. Fails only on a genuine invariant violation."""
    accepted, rejections = await _domain_proposal_outcome(db, run_id, tick, engine_id)
    check_revision_accounting(
        engine_id, tick, int(registry_before["revision"]),
        int(registry_after["revision"]), accepted, rejections, extra,
    )


def test_revision_accounting_discriminator_fires_only_on_real_violations():
    """Proves the CORE-INTEGRITY-002 canary can still fail, and on what.

    Without this, replacing the old assertion could silently produce an
    always-green test -- strictly worse than the false positive it removed.
    Needs no database.
    """
    # Legitimate, must PASS: the exact shapes measured serially.
    check_revision_accounting("association", 8, 7, 8, accepted=1)   # accepted -> +1
    check_revision_accounting("association", 8, 7, 7, accepted=0,   # rejected -> no-op
                              rejections=[("causality.invalid_parent", "")])
    check_revision_accounting("association", 8, 7, 7, accepted=0)   # absent  -> no-op

    # Genuine violations, must FAIL.
    with pytest.raises(AssertionError):  # THE lost update: accepted but no bump
        check_revision_accounting("association", 8, 7, 7, accepted=1)
    with pytest.raises(AssertionError):  # phantom write: bump with no accept
        check_revision_accounting("association", 8, 7, 8, accepted=0)
    with pytest.raises(AssertionError):  # double accept in one tick
        check_revision_accounting("association", 8, 7, 9, accepted=2)
    with pytest.raises(AssertionError):  # two accepted, only one applied
        check_revision_accounting("association", 8, 7, 8, accepted=2)


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
    # Replaces the invalid `revision == before + 1`; see the module note above.
    await _assert_revision_accounting(
        db, run["id"], after["current_tick"], "association",
        registry_before, registry,
        extra=f" concurrent statuses: {[status for status, _v in results]}.",
    )


@async_test
async def test_concurrent_stage7b_steps_do_not_duplicate_shared_state_or_head():
    db = core_db.db
    await core_db.ensure_indexes()
    clear_test_failure_injection()
    # Bounded wait for the exact precondition, replacing a fixed 12-tick setup.
    # `group-shared-state-000` does not exist at tick 12, and its formation tick
    # is SEED-VARIABLE (see the measured distribution above). `create_run`'s
    # first argument IS the seed and these tests pass a fresh uuid, so a fixed
    # setup length is a lottery. The seed cannot simply be pinned --
    # lineage_records.child_lineage_key is unique, so repeated runs on one seed
    # would collide.
    #
    # The cap is sized from the distribution rather than inflated blindly: a
    # very large cap would park the concurrent steps deep in quiescence and
    # mask the contention this test exists to watch. Waiting for the CONDITION
    # and firing immediately puts them at the earliest tick the registry is
    # live, i.e. when it is most actively churning. Median case fires ~tick 30.
    seed = f"stage7b-conc-{uuid.uuid4().hex[:8]}"
    run = await create_run(seed, "collective_groups")
    registry_before = None
    for _ in range(GROUP_STATE_SETUP_TIMEOUT_TICKS):
        await step_run(run["id"], 1)
        candidate = await db.entities.find_one(
            {"run_id": run["id"], "id": GROUP_STATE_REGISTRY_ID}, {"_id": 0},
        )
        if candidate is not None and (candidate.get("groups") or {}):
            registry_before = candidate
            break
    before = await get_run(run["id"])
    assoc_at_firing = await db.entities.find_one(
        {"run_id": run["id"], "id": ASSOCIATION_REGISTRY_ID}, {"_id": 0},
    )
    formation = (
        f"seed={seed} run={run['id']} firing_tick={before['current_tick']} "
        f"assoc_rev={(assoc_at_firing or {}).get('revision')} "
        f"group_state_rev={(registry_before or {}).get('revision')} "
        f"head_rev={head_revision_of(before)}"
    )
    if registry_before is None:
        pytest.fail(
            f"{GROUP_STATE_REGISTRY_ID} never carried a non-empty `groups` map "
            f"within the {GROUP_STATE_SETUP_TIMEOUT_TICKS}-tick timeout. "
            f"{formation}. This is a SETUP precondition, not a concurrency "
            f"result -- the test never reached its concurrent step, so it says "
            f"nothing about CAS behaviour. Do not widen the timeout without a "
            f"fresh measured distribution, and do not add retries: discarding "
            f"slow-forming seeds biases the sampled population toward exactly "
            f"the low-churn worlds this canary least needs to watch."
        )
    firing_tick = before["current_tick"]
    revision_before = head_revision_of(before)

    async def attempt():
        try:
            return ("ok", await step_run(run["id"], 1))
        except ConcurrentModification:
            return ("cas", None)

    results = await asyncio.gather(attempt(), attempt())
    # Formation context is carried into EVERY post-concurrency failure below,
    # so a future failure can be correlated with formation timing without
    # repeating this investigation.
    ctx = f"[{formation} statuses={[s for s, _v in results]}]"
    assert any(status == "ok" for status, _value in results), \
        f"no concurrent step succeeded. {ctx}"
    after = await get_run(run["id"])
    assert after["current_tick"] == before["current_tick"] + 1, \
        f"tick advanced {before['current_tick']} -> {after['current_tick']}, expected +1. {ctx}"
    assert head_revision_of(after) == revision_before + 1, \
        f"head revision {revision_before} -> {head_revision_of(after)}, expected +1. {ctx}"
    frames = await db.commit_frames.count_documents({
        "run_id": run["id"], "tick": after["current_tick"],
    })
    assert frames == 1, f"expected exactly 1 commit frame, found {frames}. {ctx}"

    registry = await db.entities.find_one(
        {"run_id": run["id"], "id": GROUP_STATE_REGISTRY_ID}, {"_id": 0},
    )
    assert registry is not None, f"group-state registry vanished. {ctx}"
    fact_ids = [
        fact_id
        for group in (registry.get("groups") or {}).values()
        for fact_id in (group.get("facts") or {})
    ]
    assert len(fact_ids) == len(set(fact_ids)), f"duplicate fact ids. {ctx}"
    # Replaces this test's copy of the same invalid `revision == before + 1`.
    await _assert_revision_accounting(
        db, run["id"], after["current_tick"], "group_state",
        registry_before, registry,
        extra=(f" head revision {revision_before} -> {head_revision_of(after)}. {ctx}"),
    )
    shared_state_events = await db.accepted_events.count_documents({
        "run_id": run["id"],
        "simulation_time": after["current_tick"],
        "event_type": "update_group_shared_state",
    })
    assert shared_state_events <= 1, (
        f"{shared_state_events} update_group_shared_state events in one tick, "
        f"expected at most 1. {ctx}"
    )
    # Pass diagnostics: kept on the passing path too, so the formation timing of
    # a healthy run is visible in -s / -rA output and comparable against a
    # future failure.
    print(f"stage7b OK {ctx}")
