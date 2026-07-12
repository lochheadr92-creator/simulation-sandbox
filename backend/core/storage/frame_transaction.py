"""Phase 5A4a — atomic transactional tick-frame persistence.

Authority model (unchanged):
  accepted_events      canonical world-mutation history
  rejected_proposals   Core-owned rejection audit for the frame
  entities             current entity projection
  commit_frames        frame boundary + hash records
  kernel_runs          operational run root / head

Transaction contents (frame-critical only):
  1. accepted events
  2. rejected proposals for this frame
  3. changed entity projections
  4. commit-frame document
  5. kernel-run head CAS (tick, last_state_hash, next_order_index, head_revision)

Excluded from the transaction (safe outside; failure does not invalidate truth):
  - activation_diagnostics  (rebuildable presentation)
  - rejected_proposals prune (retention policy, not frame validity)
  - timeline / milestone projections (derived)

Deterministic frame identity never uses wall-clock, UUIDs, or process identity.
Run documents are keyed by application field ``id`` (not Mongo ``_id``).
"""
from __future__ import annotations

import asyncio
import copy
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from bson import BSON
from pymongo.errors import (
    ConnectionFailure,
    DuplicateKeyError,
    OperationFailure,
    PyMongoError,
)
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import ReadPreference
from pymongo.write_concern import WriteConcern

from core.db import client, db
from core.hashing import canonical_hash
from core.mutations import snapshot_for_hash


# ---------------------------------------------------------------------------
# Capacity limits (fail-fast; not gameplay)
# ---------------------------------------------------------------------------
MAX_ENTITY_BSON_BYTES = 10 * 1024 * 1024
MAX_ACCEPTED_EVENT_BSON_BYTES = 10 * 1024 * 1024
MAX_REJECTION_BSON_BYTES = 5 * 1024 * 1024
MAX_COMMIT_FRAME_BSON_BYTES = 5 * 1024 * 1024
MAX_RUN_HEAD_BSON_BYTES = 1 * 1024 * 1024
MAX_CANONICAL_FRAME_BYTES = 40 * 1024 * 1024
MAX_CHANGED_ENTITIES_PER_FRAME = 5000
MAX_ACCEPTED_EVENTS_PER_FRAME = 2000
MAX_REJECTIONS_PER_FRAME = 5000
MAX_CANONICAL_WRITES_PER_FRAME = 12000

TX_MAX_ATTEMPTS = 10
TX_DEADLINE_SECONDS = 15.0
TX_RETRY_BASE_DELAY_SECONDS = 0.01
TX_RETRY_MAX_DELAY_SECONDS = 0.25

# Test-only failure injection. Production never enables this set.
# Points: before_events, after_events, after_rejections, after_entities,
#         after_commit_frame, before_cas, after_cas, during_commit
_TEST_INJECT: set[str] = set()


def _injection_enabled() -> bool:
    return bool(_TEST_INJECT) and os.environ.get("SIM_SANDBOX_TX_INJECT") == "1"


def enable_test_failure_injection(*points: str) -> None:
    """Test-only. Requires SIM_SANDBOX_TX_INJECT=1 in the environment."""
    if os.environ.get("SIM_SANDBOX_TX_INJECT") != "1":
        raise RuntimeError("failure injection requires SIM_SANDBOX_TX_INJECT=1")
    _TEST_INJECT.clear()
    _TEST_INJECT.update(points)


def clear_test_failure_injection() -> None:
    _TEST_INJECT.clear()


def _maybe_inject(point: str) -> None:
    if _injection_enabled() and point in _TEST_INJECT:
        raise InjectedTransactionFailure(point)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class FramePersistenceError(Exception):
    code = "DB_TX_FAILURE"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        if code:
            self.code = code
        self.message = message


class ConcurrentModification(FramePersistenceError):
    code = "CONCURRENT_MODIFICATION"


class CommitStatusUnknown(FramePersistenceError):
    code = "COMMIT_STATUS_UNKNOWN"


class FrameCapacityError(FramePersistenceError):
    code = "FRAME_CAPACITY_EXCEEDED"


class RunIntegrityMismatch(FramePersistenceError):
    code = "RUN_INTEGRITY_MISMATCH"


class RunUnderMaintenance(FramePersistenceError):
    code = "RUN_UNDER_MAINTENANCE"


class RunQuarantined(FramePersistenceError):
    code = "RUN_QUARANTINED"


class TransactionUnavailable(FramePersistenceError):
    code = "TRANSACTION_UNAVAILABLE"


class InjectedTransactionFailure(FramePersistenceError):
    code = "INJECTED_FAILURE"

    def __init__(self, point: str):
        super().__init__(f"injected failure at {point}", "INJECTED_FAILURE")
        self.point = point


# ---------------------------------------------------------------------------
# Precomputed frame
# ---------------------------------------------------------------------------
@dataclass
class PrecomputedFrame:
    run_id: str
    expected_tick: int
    new_tick: int
    expected_head_revision: int
    expected_state_hash: Optional[str]
    expected_next_order_index: int
    starting_state_hash: Optional[str]
    ending_state_hash: Optional[str]
    next_order_index: int
    accepted_events: list
    rejected_proposals: list
    entity_docs: list  # full projection docs for changed entities
    removed_entity_ids: list
    commit_frame: dict
    hash_policy_version: str
    schema_context_hash: Optional[str] = None
    engine_version: Optional[str] = None
    schema_version: Optional[str] = None
    frame_identity_hash: str = ""
    diagnostics: dict = field(default_factory=dict)  # not persisted in TX

    def compute_identity(self) -> str:
        payload = {
            "run_id": self.run_id,
            "expected_head_revision": self.expected_head_revision,
            "expected_tick": self.expected_tick,
            "new_tick": self.new_tick,
            "starting_state_hash": self.starting_state_hash,
            "ending_state_hash": self.ending_state_hash,
            "accepted_event_ids": [e["id"] for e in self.accepted_events],
            "rejected_proposal_ids": [r["id"] for r in self.rejected_proposals],
            "next_order_index": self.next_order_index,
            "hash_policy_version": self.hash_policy_version,
            "schema_context_hash": self.schema_context_hash,
            "engine_version": self.engine_version,
            "schema_version": self.schema_version,
        }
        self.frame_identity_hash = canonical_hash(payload)
        self.commit_frame = dict(self.commit_frame)
        self.commit_frame["frame_identity_hash"] = self.frame_identity_hash
        return self.frame_identity_hash


def head_revision_of(run: dict) -> int:
    """Legacy runs without head_revision are treated as revision 0 once integrity passes."""
    if "head_revision" not in run:
        return 0
    return int(run["head_revision"])


def bson_size(document: dict) -> int:
    return len(BSON.encode(document))


def validate_frame_capacity(frame: PrecomputedFrame) -> None:
    if len(frame.accepted_events) > MAX_ACCEPTED_EVENTS_PER_FRAME:
        raise FrameCapacityError(
            f"accepted events {len(frame.accepted_events)} > {MAX_ACCEPTED_EVENTS_PER_FRAME}",
            "FRAME_CAPACITY_EXCEEDED",
        )
    if len(frame.rejected_proposals) > MAX_REJECTIONS_PER_FRAME:
        raise FrameCapacityError(
            f"rejections {len(frame.rejected_proposals)} > {MAX_REJECTIONS_PER_FRAME}",
            "FRAME_CAPACITY_EXCEEDED",
        )
    changed = len(frame.entity_docs) + len(frame.removed_entity_ids)
    if changed > MAX_CHANGED_ENTITIES_PER_FRAME:
        raise FrameCapacityError(
            f"changed entities {changed} > {MAX_CHANGED_ENTITIES_PER_FRAME}",
            "FRAME_CAPACITY_EXCEEDED",
        )
    write_count = (
        len(frame.accepted_events)
        + len(frame.rejected_proposals)
        + len(frame.entity_docs)
        + len(frame.removed_entity_ids)
        + 2  # commit_frame + run head
    )
    if write_count > MAX_CANONICAL_WRITES_PER_FRAME:
        raise FrameCapacityError(
            f"canonical writes {write_count} > {MAX_CANONICAL_WRITES_PER_FRAME}",
            "FRAME_CAPACITY_EXCEEDED",
        )

    total = 0
    for event in frame.accepted_events:
        size = bson_size(event)
        total += size
        if size > MAX_ACCEPTED_EVENT_BSON_BYTES:
            raise FrameCapacityError(
                f"accepted event {event.get('id')} is {size} bytes",
                "EVENT_DOCUMENT_EXCEEDS_LIMIT",
            )
    for rejection in frame.rejected_proposals:
        size = bson_size(rejection)
        total += size
        if size > MAX_REJECTION_BSON_BYTES:
            raise FrameCapacityError(
                f"rejection {rejection.get('id')} is {size} bytes",
                "REJECTION_DOCUMENT_EXCEEDS_LIMIT",
            )
    for doc in frame.entity_docs:
        size = bson_size(doc)
        total += size
        if size > MAX_ENTITY_BSON_BYTES:
            raise FrameCapacityError(
                f"entity {doc.get('id')} is {size} bytes",
                "ENTITY_DOCUMENT_EXCEEDS_LIMIT",
            )
    cf_size = bson_size(frame.commit_frame)
    total += cf_size
    if cf_size > MAX_COMMIT_FRAME_BSON_BYTES:
        raise FrameCapacityError(
            f"commit frame is {cf_size} bytes",
            "COMMIT_FRAME_EXCEEDS_LIMIT",
        )
    # Approximate head patch size (fields set on CAS)
    head_patch = {
        "current_tick": frame.new_tick,
        "last_state_hash": frame.ending_state_hash,
        "next_order_index": frame.next_order_index,
        "head_revision": frame.expected_head_revision + 1,
    }
    head_size = bson_size(head_patch)
    total += head_size
    if head_size > MAX_RUN_HEAD_BSON_BYTES:
        raise FrameCapacityError(
            f"run head patch is {head_size} bytes",
            "RUN_HEAD_EXCEEDS_LIMIT",
        )
    if total > MAX_CANONICAL_FRAME_BYTES:
        raise FrameCapacityError(
            f"aggregate frame BSON {total} exceeds {MAX_CANONICAL_FRAME_BYTES}",
            "FRAME_CAPACITY_EXCEEDED",
        )


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, OperationFailure):
        labels = set(getattr(exc, "has_error_label", lambda _: False) and [])
        # PyMongo exposes has_error_label method
        try:
            if exc.has_error_label("TransientTransactionError"):
                return True
        except Exception:
            pass
        # WriteConflict
        if getattr(exc, "code", None) in (112, 24):
            return True
    if isinstance(exc, ConnectionFailure):
        return True
    return False


def _is_unknown_commit(exc: BaseException) -> bool:
    if isinstance(exc, OperationFailure):
        try:
            if exc.has_error_label("UnknownTransactionCommitResult"):
                return True
        except Exception:
            pass
    return False


def _tx_unsupported(exc: BaseException) -> bool:
    if isinstance(exc, OperationFailure):
        msg = str(exc).lower()
        if "transaction numbers are only allowed" in msg:
            return True
        if "replica set" in msg and "transaction" in msg:
            return True
        if getattr(exc, "code", None) in (20, 303):
            return True
    return False


async def _wait_before_retry(attempt: int, deadline: float) -> None:
    """Yield to a competing transaction before retrying a transient failure."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return
    delay = min(
        TX_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
        TX_RETRY_MAX_DELAY_SECONDS,
        remaining,
    )
    await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Integrity
# ---------------------------------------------------------------------------
async def inspect_projection_integrity(run_id: str, lineage_key: str,
                                        hash_policy_version: str) -> dict:
    """Read-only integrity report. Does not repair."""
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        return {"ok": False, "code": "RUN_NOT_FOUND", "detail": "run not found"}

    if run.get("maintenance_mode") is True:
        return {"ok": False, "code": "RUN_UNDER_MAINTENANCE", "detail": "maintenance active"}
    if run.get("quarantined") is True:
        return {"ok": False, "code": "RUN_QUARANTINED", "detail": "run quarantined"}

    latest_frame = await db.commit_frames.find_one(
        {"run_id": run_id},
        {"_id": 0},
        sort=[("tick", -1)],
    )
    issues = []
    if latest_frame is None:
        if run.get("current_tick", 0) != 0:
            issues.append("missing_commit_frame")
    else:
        if latest_frame.get("tick") != run.get("current_tick"):
            issues.append(
                f"tick_mismatch frame={latest_frame.get('tick')} head={run.get('current_tick')}"
            )
        if latest_frame.get("ending_state_hash") != run.get("last_state_hash"):
            issues.append("ending_hash_mismatch")

    max_event = await db.accepted_events.find_one(
        {"run_id": run_id},
        {"_id": 0, "order_index": 1},
        sort=[("order_index", -1)],
    )
    if max_event is not None:
        next_expected = max_event["order_index"] + 1
        if run.get("next_order_index", 0) < next_expected:
            issues.append(
                f"order_index_behind head={run.get('next_order_index')} max_event={max_event['order_index']}"
            )

    # Projection hash vs authoritative ending hash.
    # Under tick-bound-v1 (and any frame with accepted events) the head hash is
    # the entity snapshot at current_tick. Legacy empty frames may carry a prior
    # tick's hash without rebinding the tick in the snapshot — skip that case.
    entity_docs = await db.entities.find({"run_id": run_id}, {"_id": 0}).to_list(10000)
    entities = {}
    for doc in entity_docs:
        eid = doc.pop("id")
        doc.pop("run_id", None)
        entities[eid] = doc
    tick = run.get("current_tick", 0)
    projected_hash = canonical_hash(snapshot_for_hash(entities, tick, lineage_key))
    frame_has_events = bool(latest_frame and latest_frame.get("accepted_event_ids"))
    tick_bound = hash_policy_version == "tick-bound-v1" or run.get("hash_policy_version") == "tick-bound-v1"
    if run.get("last_state_hash") and projected_hash != run["last_state_hash"]:
        if tick_bound or frame_has_events or tick == 0:
            issues.append("projection_hash_mismatch")

    if issues:
        return {"ok": False, "code": "RUN_INTEGRITY_MISMATCH", "detail": "; ".join(issues)}
    return {"ok": True, "code": "OK", "detail": "consistent", "head_revision": head_revision_of(run)}


async def assert_run_steppable(run: dict, lineage_key: str) -> None:
    if run.get("maintenance_mode") is True:
        raise RunUnderMaintenance("run is under maintenance")
    if run.get("quarantined") is True:
        raise RunQuarantined("run is quarantined")
    report = await inspect_projection_integrity(
        run["id"], lineage_key, run.get("hash_policy_version", ""),
    )
    if not report["ok"]:
        code = report["code"]
        if code == "RUN_UNDER_MAINTENANCE":
            raise RunUnderMaintenance(report["detail"])
        if code == "RUN_QUARANTINED":
            raise RunQuarantined(report["detail"])
        raise RunIntegrityMismatch(report["detail"])


# ---------------------------------------------------------------------------
# Resolve unknown commit
# ---------------------------------------------------------------------------
async def resolve_commit_status(frame: PrecomputedFrame) -> str:
    """Return 'committed', 'absent', or 'unknown' for a deterministic frame."""
    stored = await db.commit_frames.find_one(
        {"run_id": frame.run_id, "tick": frame.new_tick},
        {"_id": 0},
    )
    if stored is None:
        # Confirm head did not advance past expected
        run = await db.kernel_runs.find_one({"id": frame.run_id}, {"_id": 0})
        if not run:
            return "unknown"
        if (
            run.get("current_tick") == frame.expected_tick
            and head_revision_of(run) == frame.expected_head_revision
            and run.get("last_state_hash") == frame.expected_state_hash
        ):
            return "absent"
        # Head moved differently — competing write or partial legacy
        return "unknown"

    if stored.get("frame_identity_hash") and stored.get("frame_identity_hash") != frame.frame_identity_hash:
        return "unknown"
    if stored.get("ending_state_hash") != frame.ending_state_hash:
        return "unknown"
    if stored.get("starting_state_hash") != frame.starting_state_hash:
        return "unknown"
    stored_ids = list(stored.get("accepted_event_ids") or [])
    expected_ids = [e["id"] for e in frame.accepted_events]
    if stored_ids != expected_ids:
        return "unknown"

    run = await db.kernel_runs.find_one({"id": frame.run_id}, {"_id": 0})
    if not run:
        return "unknown"
    if run.get("current_tick") != frame.new_tick:
        return "unknown"
    if run.get("last_state_hash") != frame.ending_state_hash:
        return "unknown"
    if run.get("next_order_index") != frame.next_order_index:
        return "unknown"
    return "committed"


# ---------------------------------------------------------------------------
# Atomic commit
# ---------------------------------------------------------------------------
async def _write_frame_body(session, frame: PrecomputedFrame) -> None:
    _maybe_inject("before_events")
    if frame.accepted_events:
        await db.accepted_events.insert_many(
            [copy.deepcopy(e) for e in frame.accepted_events],
            session=session,
            ordered=True,
        )
    _maybe_inject("after_events")

    if frame.rejected_proposals:
        await db.rejected_proposals.insert_many(
            [copy.deepcopy(r) for r in frame.rejected_proposals],
            session=session,
            ordered=True,
        )
    _maybe_inject("after_rejections")

    for doc in frame.entity_docs:
        await db.entities.replace_one(
            {"run_id": frame.run_id, "id": doc["id"]},
            copy.deepcopy(doc),
            upsert=True,
            session=session,
        )
    for eid in frame.removed_entity_ids:
        await db.entities.delete_one(
            {"run_id": frame.run_id, "id": eid},
            session=session,
        )
    _maybe_inject("after_entities")

    await db.commit_frames.insert_one(copy.deepcopy(frame.commit_frame), session=session)
    _maybe_inject("after_commit_frame")

    _maybe_inject("before_cas")
    result = await db.kernel_runs.update_one(
        {
            "id": frame.run_id,
            "head_revision": frame.expected_head_revision,
            "maintenance_mode": {"$ne": True},
            "quarantined": {"$ne": True},
            "current_tick": frame.expected_tick,
            "next_order_index": frame.expected_next_order_index,
        },
        {
            "$set": {
                "current_tick": frame.new_tick,
                "last_state_hash": frame.ending_state_hash,
                "next_order_index": frame.next_order_index,
                "status": "running",
            },
            "$inc": {"head_revision": 1},
        },
        session=session,
    )
    if result.matched_count == 0:
        raise ConcurrentModification(
            f"CAS lost for run {frame.run_id} at revision {frame.expected_head_revision}"
        )
    _maybe_inject("after_cas")


async def _semantic_head_matches(run: dict, frame: PrecomputedFrame) -> bool:
    if run is None:
        return False
    if head_revision_of(run) != frame.expected_head_revision:
        return False
    if run.get("current_tick") != frame.expected_tick:
        return False
    if run.get("last_state_hash") != frame.expected_state_hash:
        return False
    if run.get("next_order_index") != frame.expected_next_order_index:
        return False
    if run.get("maintenance_mode") is True:
        return False
    if run.get("quarantined") is True:
        return False
    return True


async def commit_frame_atomically(frame: PrecomputedFrame) -> dict:
    """Persist a precomputed deterministic frame in one Mongo transaction.

    Frame must already be fully calculated (no domain activation here).
    """
    if not frame.frame_identity_hash:
        frame.compute_identity()
    validate_frame_capacity(frame)

    deadline = time.monotonic() + TX_DEADLINE_SECONDS
    attempt = 0
    last_error: BaseException | None = None

    while attempt < TX_MAX_ATTEMPTS:
        attempt += 1
        if time.monotonic() > deadline:
            raise FramePersistenceError(
                f"transaction deadline exceeded after {attempt - 1} attempts",
                "DB_TX_FAILURE",
            )

        # Outside-tx revalidation (before opening a transaction)
        head = await db.kernel_runs.find_one({"id": frame.run_id}, {"_id": 0})
        if not await _semantic_head_matches(head, frame):
            # Idempotent success if this exact frame already committed
            status = await resolve_commit_status(frame)
            if status == "committed":
                return {
                    "status": "already_committed",
                    "frame_identity_hash": frame.frame_identity_hash,
                    "tick": frame.new_tick,
                    "head_revision": head_revision_of(head) if head else None,
                }
            raise ConcurrentModification(
                f"head changed before transaction for run {frame.run_id}"
            )

        session = await client.start_session()
        try:
            async with session.start_transaction(
                read_concern=ReadConcern("snapshot"),
                write_concern=WriteConcern("majority"),
                read_preference=ReadPreference.PRIMARY,
            ):
                try:
                    head_in_tx = await db.kernel_runs.find_one(
                        {"id": frame.run_id}, {"_id": 0}, session=session,
                    )
                    # Normalize missing head_revision inside CAS path for legacy docs.
                    if head_in_tx is not None and "head_revision" not in head_in_tx:
                        if frame.expected_head_revision != 0:
                            raise ConcurrentModification("legacy head revision mismatch")
                        await db.kernel_runs.update_one(
                            {
                                "id": frame.run_id,
                                "head_revision": {"$exists": False},
                                "current_tick": frame.expected_tick,
                            },
                            {"$set": {
                                "head_revision": 0,
                                "maintenance_mode": False,
                                "quarantined": False,
                            }},
                            session=session,
                        )
                        head_in_tx = await db.kernel_runs.find_one(
                            {"id": frame.run_id}, {"_id": 0}, session=session,
                        )

                    if not await _semantic_head_matches(head_in_tx, frame):
                        raise ConcurrentModification(
                            f"head changed inside transaction for run {frame.run_id}"
                        )

                    await _write_frame_body(session, frame)
                    _maybe_inject("during_commit")
                except ConcurrentModification:
                    raise
                except InjectedTransactionFailure:
                    raise
                except Exception as exc:
                    last_error = exc
                    if _tx_unsupported(exc):
                        raise TransactionUnavailable(
                            "Mongo deployment does not support multi-document transactions"
                        ) from exc
                    if _is_unknown_commit(exc):
                        # Exit context (abort), then resolve outside
                        raise
                    if isinstance(exc, DuplicateKeyError) or getattr(exc, "code", None) == 11000:
                        raise
                    if _is_transient(exc):
                        raise
                    raise FramePersistenceError(str(exc), "DB_TX_FAILURE") from exc

            return {
                "status": "committed",
                "frame_identity_hash": frame.frame_identity_hash,
                "tick": frame.new_tick,
                "head_revision": frame.expected_head_revision + 1,
                "attempts": attempt,
            }
        except ConcurrentModification:
            raise
        except InjectedTransactionFailure:
            raise
        except TransactionUnavailable:
            raise
        except FramePersistenceError:
            raise
        except Exception as exc:
            last_error = exc
            if _is_unknown_commit(exc):
                status = await resolve_commit_status(frame)
                if status == "committed":
                    return {
                        "status": "committed_resolved",
                        "frame_identity_hash": frame.frame_identity_hash,
                        "tick": frame.new_tick,
                        "head_revision": frame.expected_head_revision + 1,
                        "attempts": attempt,
                    }
                if status == "absent":
                    if attempt >= TX_MAX_ATTEMPTS or time.monotonic() > deadline:
                        raise FramePersistenceError(
                            "commit failed and frame confirmed absent",
                            "DB_TX_FAILURE",
                        ) from exc
                    await _wait_before_retry(attempt, deadline)
                    continue
                raise CommitStatusUnknown(
                    "commit result unknown; frame state not safely resolvable"
                ) from exc
            if isinstance(exc, DuplicateKeyError) or getattr(exc, "code", None) == 11000:
                status = await resolve_commit_status(frame)
                if status == "committed":
                    return {
                        "status": "already_committed",
                        "frame_identity_hash": frame.frame_identity_hash,
                        "tick": frame.new_tick,
                        "head_revision": frame.expected_head_revision + 1,
                        "attempts": attempt,
                    }
                raise ConcurrentModification(
                    f"competing frame at tick boundary for run {frame.run_id}"
                ) from exc
            if _is_transient(exc):
                head_now = await db.kernel_runs.find_one({"id": frame.run_id}, {"_id": 0})
                if not await _semantic_head_matches(head_now, frame):
                    status = await resolve_commit_status(frame)
                    if status == "committed":
                        return {
                            "status": "already_committed",
                            "frame_identity_hash": frame.frame_identity_hash,
                            "tick": frame.new_tick,
                            "head_revision": frame.expected_head_revision + 1,
                            "attempts": attempt,
                        }
                    raise ConcurrentModification(
                        f"head changed during transient conflict for run {frame.run_id}"
                    ) from exc
                if attempt >= TX_MAX_ATTEMPTS or time.monotonic() > deadline:
                    raise FramePersistenceError(
                        f"transient transaction errors exhausted: {exc}",
                        "DB_TX_FAILURE",
                    ) from exc
                await _wait_before_retry(attempt, deadline)
                continue
            if _tx_unsupported(exc):
                raise TransactionUnavailable(
                    "Mongo deployment does not support multi-document transactions"
                ) from exc
            raise FramePersistenceError(str(exc), "DB_TX_FAILURE") from exc
        finally:
            if hasattr(session, "end_session"):
                end = session.end_session()
                if asyncio.iscoroutine(end):
                    await end

    raise FramePersistenceError(
        f"transaction attempts exhausted; last error: {last_error}",
        "DB_TX_FAILURE",
    )


# ---------------------------------------------------------------------------
# Maintenance / recovery
# ---------------------------------------------------------------------------
async def acquire_maintenance(run_id: str, operation_id: str, *,
                              force: bool = False,
                              reason: str | None = None,
                              operator: str = "operator") -> dict:
    """Acquire exclusive maintenance via head_revision CAS."""
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise FramePersistenceError("run not found", "RUN_NOT_FOUND")

    if run.get("maintenance_mode") is True and not force:
        raise RunUnderMaintenance("maintenance already active")
    if run.get("maintenance_mode") is True and force:
        # Force may only reclaim a demonstrably stale lease, not a valid active one
        # without admin path; still block if lease looks active (no TTL in v1 unless marked stale).
        if not run.get("maintenance_stale"):
            raise RunUnderMaintenance("cannot force-override active valid maintenance lease")

    expected_rev = head_revision_of(run)
    if "head_revision" not in run:
        await db.kernel_runs.update_one(
            {"id": run_id, "head_revision": {"$exists": False}},
            {"$set": {"head_revision": 0}},
        )
        expected_rev = 0

    result = await db.kernel_runs.update_one(
        {
            "id": run_id,
            "head_revision": expected_rev,
            "maintenance_mode": {"$ne": True} if not force else {"$exists": True},
        },
        {
            "$set": {
                "maintenance_mode": True,
                "maintenance_operation_id": operation_id,
                "maintenance_stale": False,
                "status": "maintenance",
            },
            "$inc": {"head_revision": 1},
        },
    )
    if result.matched_count == 0:
        raise ConcurrentModification("failed to acquire maintenance")
    return {
        "run_id": run_id,
        "operation_id": operation_id,
        "starting_head_revision": expected_rev,
        "head_revision": expected_rev + 1,
        "forced": force,
        "reason": reason,
        "operator": operator,
    }


async def release_maintenance(run_id: str, operation_id: str, *,
                              quarantine: bool = False,
                              status: str = "paused") -> None:
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise FramePersistenceError("run not found", "RUN_NOT_FOUND")
    if run.get("maintenance_operation_id") != operation_id:
        raise ConcurrentModification("maintenance operation mismatch")
    expected_rev = head_revision_of(run)
    result = await db.kernel_runs.update_one(
        {
            "id": run_id,
            "head_revision": expected_rev,
            "maintenance_operation_id": operation_id,
        },
        {
            "$set": {
                "maintenance_mode": False,
                "maintenance_operation_id": None,
                "maintenance_stale": False,
                "quarantined": quarantine,
                "status": "quarantined" if quarantine else status,
            },
            "$inc": {"head_revision": 1},
        },
    )
    if result.matched_count == 0:
        raise ConcurrentModification("failed to release maintenance")


async def write_recovery_record(record: dict) -> None:
    """Immutable RecoveryRecord — insert only, never update."""
    await db.recovery_records.insert_one(copy.deepcopy(record))


async def rebuild_projection_atomically(
    run_id: str,
    operation_id: str,
    lineage_key: str,
    expected_ending_hash: str,
    current_tick: int,
) -> dict:
    """Rebuild entity projections from accepted_events under maintenance.

    Rebuilds into temporary docs, verifies hash, then swaps atomically.
    """
    from core.mutations import apply_mutation

    events = await db.accepted_events.find(
        {"run_id": run_id}, {"_id": 0},
    ).sort([("simulation_time", 1), ("order_index", 1)]).to_list(1_000_000)

    entities: dict = {}
    for event in events:
        apply_mutation(entities, copy.deepcopy(event["mutation"]))

    rebuilt_hash = canonical_hash(snapshot_for_hash(entities, current_tick, lineage_key))
    if rebuilt_hash != expected_ending_hash:
        raise RunIntegrityMismatch(
            f"rebuilt hash {rebuilt_hash} != expected {expected_ending_hash}"
        )

    tmp_coll = db.entities_rebuild_tmp
    await tmp_coll.delete_many({"run_id": run_id, "operation_id": operation_id})
    docs = []
    for eid in sorted(entities):
        doc = dict(entities[eid])
        doc["id"] = eid
        doc["run_id"] = run_id
        doc["operation_id"] = operation_id
        docs.append(doc)
    if docs:
        await tmp_coll.insert_many(docs)

    session = await client.start_session()
    try:
        async with session.start_transaction(
            read_concern=ReadConcern("snapshot"),
            write_concern=WriteConcern("majority"),
            read_preference=ReadPreference.PRIMARY,
        ):
            run = await db.kernel_runs.find_one(
                {"id": run_id}, {"_id": 0}, session=session,
            )
            if not run or run.get("maintenance_operation_id") != operation_id:
                raise ConcurrentModification("maintenance lost during rebuild")
            await db.entities.delete_many({"run_id": run_id}, session=session)
            if docs:
                clean = []
                for d in docs:
                    c = dict(d)
                    c.pop("operation_id", None)
                    clean.append(c)
                await db.entities.insert_many(clean, session=session)
            await db.kernel_runs.update_one(
                {"id": run_id, "maintenance_operation_id": operation_id},
                {"$set": {"projection_watermark_tick": current_tick,
                          "projection_watermark_hash": rebuilt_hash}},
                session=session,
            )
    finally:
        if hasattr(session, "end_session"):
            end = session.end_session()
            if asyncio.iscoroutine(end):
                await end
        await tmp_coll.delete_many({"run_id": run_id, "operation_id": operation_id})

    return {"rebuilt_hash": rebuilt_hash, "entity_count": len(entities)}
