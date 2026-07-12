"""Phase 5A2 fork contract tests using an in-memory async Mongo seam."""
import asyncio
import copy
from functools import wraps
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, OperationFailure

from core import db as core_db
from core import replay_service, retention_service, run_service
from core.storage import frame_transaction as frame_tx
from core.commit_pipeline import run_commit_frame
from core.constants import HASH_POLICY_VERSION
from core.forking import (
    ForkContractError, build_external_anchor_manifest, content_hash_for_fork,
)
from core.hashing import canonical_hash
from core.history_service import classify_milestones, provenance_for_entity
from core.mutations import snapshot_for_hash
from domains.base import DomainOutput
from api.routes import ForkRunRequest, api_fork_run


def async_test(function):
    @wraps(function)
    def run(*args, **kwargs):
        return asyncio.run(function(*args, **kwargs))
    return run


def _matches(document, query):
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(document, clause) for clause in expected):
                return False
            continue
        actual = document.get(key)
        if isinstance(expected, dict):
            for operator, value in expected.items():
                if operator == "$lte" and not (actual is not None and actual <= value):
                    return False
                if operator == "$gte" and not (actual is not None and actual >= value):
                    return False
                if operator == "$lt" and not (actual is not None and actual < value):
                    return False
                if operator == "$in" and actual not in value:
                    return False
                if operator == "$ne" and actual == value:
                    return False
                if operator == "$exists":
                    present = key in document
                    if bool(value) != present:
                        return False
        elif actual != expected:
            return False
    return True


def _project(document, projection):
    result = copy.deepcopy(document)
    if not projection:
        return result
    included = [key for key, value in projection.items() if value and key != "_id"]
    if included:
        return {key: result[key] for key in included if key in result}
    for key, value in projection.items():
        if not value:
            result.pop(key, None)
    return result


class FakeCursor:
    def __init__(self, documents):
        self.documents = copy.deepcopy(documents)

    def sort(self, key_or_list, direction=None):
        keys = key_or_list if isinstance(key_or_list, list) else [(key_or_list, direction)]
        for key, order in reversed(keys):
            self.documents.sort(key=lambda doc: doc.get(key), reverse=order == -1)
        return self

    async def to_list(self, length):
        return copy.deepcopy(self.documents[:length])


class FakeCollection:
    def __init__(self, database, name):
        self.database = database
        self.name = name
        self.documents = []
        self.indexes = []

    def _read_documents(self, session):
        if session is not None and session.snapshot is not None:
            return session.snapshot[self.name]
        return self.documents

    def _check_transaction(self, session):
        if session is not None and not self.database.transaction_supported:
            raise OperationFailure(
                "Transaction numbers are only allowed on a replica set member",
                code=20,
            )

    async def find_one(self, query, projection=None, session=None, sort=None):
        self._check_transaction(session)
        if (session is not None and self.name == "kernel_runs"
                and self.database.capture_event is not None
                and not self.database.capture_event.is_set()
                and query.get("id") == self.database.capture_run_id):
            # Fire once so an interleaved step_run (also session-scoped) does not
            # re-enter the capture wait and deadlock with the test harness.
            self.database.capture_event.set()
            await self.database.release_event.wait()
        matches = [
            document for document in self._read_documents(session)
            if _matches(document, query)
        ]
        if sort:
            for key, order in reversed(sort):
                matches.sort(key=lambda doc: doc.get(key), reverse=order == -1)
        if matches:
            return _project(matches[0], projection)
        return None

    def find(self, query, projection=None, session=None):
        self._check_transaction(session)
        return FakeCursor([
            _project(document, projection)
            for document in self._read_documents(session)
            if _matches(document, query)
        ])

    def _unique_key(self, document):
        if self.name == "kernel_runs":
            return (document.get("id"),)
        if self.name == "accepted_events":
            return document.get("run_id"), document.get("id")
        if self.name == "commit_frames":
            return document.get("run_id"), document.get("tick")
        if self.name == "entities":
            return document.get("run_id"), document.get("id")
        if self.name == "lineage_records":
            return (document.get("id"),)
        return None

    def _check_unique(self, document, replacing=None):
        key = self._unique_key(document)
        for existing in self.documents:
            if existing is replacing:
                continue
            if key is not None and self._unique_key(existing) == key:
                raise DuplicateKeyError(f"duplicate key in {self.name}: {key}")
            if self.name == "kernel_runs":
                for field in ("creation_command_hash", "fork_identity_hash"):
                    value = document.get(field)
                    if value is not None and existing.get(field) == value:
                        raise DuplicateKeyError(f"duplicate {field}: {value}")
            if self.name == "lineage_records":
                value = document.get("child_lineage_key")
                if value is not None and existing.get("child_lineage_key") == value:
                    raise DuplicateKeyError(f"duplicate child lineage: {value}")

    async def insert_one(self, document, session=None):
        self.database.before_write()
        candidate = copy.deepcopy(document)
        self._check_unique(candidate)
        self.documents.append(candidate)
        return SimpleNamespace(inserted_id=candidate.get("id"))

    async def insert_many(self, documents, session=None, ordered=True):
        inserted = []
        for document in documents:
            result = await self.insert_one(document, session=session)
            inserted.append(result.inserted_id)
        return SimpleNamespace(inserted_ids=inserted)

    async def replace_one(self, query, document, upsert=False, session=None):
        self.database.before_write()
        for index, existing in enumerate(self.documents):
            if _matches(existing, query):
                candidate = copy.deepcopy(document)
                self._check_unique(candidate, replacing=existing)
                self.documents[index] = candidate
                return SimpleNamespace(matched_count=1)
        if upsert:
            candidate = copy.deepcopy(document)
            self._check_unique(candidate)
            self.documents.append(candidate)
        return SimpleNamespace(matched_count=0)

    async def update_one(self, query, update, upsert=False, session=None):
        self.database.before_write()
        target = next((doc for doc in self.documents if _matches(doc, query)), None)
        inserted = target is None
        if target is None:
            if not upsert:
                return SimpleNamespace(matched_count=0)
            target = copy.deepcopy(query)
            self.documents.append(target)
        if inserted:
            target.update(copy.deepcopy(update.get("$setOnInsert", {})))
        target.update(copy.deepcopy(update.get("$set", {})))
        for field, amount in update.get("$inc", {}).items():
            target[field] = target.get(field, 0) + amount
        for field, operation in update.get("$push", {}).items():
            target.setdefault(field, []).extend(copy.deepcopy(operation.get("$each", [])))
        return SimpleNamespace(matched_count=0 if inserted else 1)

    async def delete_one(self, query, session=None):
        self.database.before_write()
        for index, document in enumerate(self.documents):
            if _matches(document, query):
                del self.documents[index]
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    async def delete_many(self, query, session=None):
        self.database.before_write()
        before = len(self.documents)
        self.documents[:] = [doc for doc in self.documents if not _matches(doc, query)]
        return SimpleNamespace(deleted_count=before - len(self.documents))

    async def count_documents(self, query, session=None):
        return sum(1 for document in self.documents if _matches(document, query))

    async def create_index(self, *args, **kwargs):
        self.indexes.append((copy.deepcopy(args), copy.deepcopy(kwargs)))
        return kwargs.get("name", "index")

    async def drop_index(self, name):
        return None


class FakeDatabase:
    COLLECTIONS = (
        "kernel_runs", "accepted_events", "rejected_proposals", "entities",
        "commit_frames", "activation_diagnostics", "external_influences",
        "lineage_records", "recovery_records", "entities_rebuild_tmp",
    )

    def __init__(self):
        self.transaction_supported = True
        self.write_count = 0
        self.fail_on_write = None
        self.capture_event = None
        self.release_event = None
        self.capture_run_id = None
        for name in self.COLLECTIONS:
            setattr(self, name, FakeCollection(self, name))

    def before_write(self):
        self.write_count += 1
        if self.fail_on_write == self.write_count:
            raise RuntimeError("injected transaction write failure")

    def snapshot(self):
        return {
            name: copy.deepcopy(getattr(self, name).documents)
            for name in self.COLLECTIONS
        }

    def restore(self, snapshot):
        for name, documents in snapshot.items():
            getattr(self, name).documents[:] = copy.deepcopy(documents)


class FakeTransaction:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        # Snapshot-isolation without a global exclusive lock so a mid-transaction
        # capture wait (parent-progress concurrency test) can interleave a step.
        self.session.snapshot = self.session.client.database.snapshot()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            self.session.client.database.restore(self.session.snapshot)
        self.session.snapshot = None
        return False


class FakeSession:
    def __init__(self, client):
        self.client = client
        self.snapshot = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def start_transaction(self, **kwargs):
        return FakeTransaction(self)


class FakeClient:
    def __init__(self, database):
        self.database = database
        self.lock = asyncio.Lock()

    async def start_session(self):
        return FakeSession(self)


@pytest.fixture
def storage(monkeypatch):
    database = FakeDatabase()
    fake_client = FakeClient(database)
    monkeypatch.setattr(run_service, "db", database)
    monkeypatch.setattr(run_service, "client", fake_client)
    monkeypatch.setattr(replay_service, "db", database)
    monkeypatch.setattr(retention_service, "db", database)
    # Phase 5A4a adapter holds its own module-level db/client references.
    monkeypatch.setattr(frame_tx, "db", database)
    monkeypatch.setattr(frame_tx, "client", fake_client)
    return database


async def _new_parent(ticks=0):
    parent = await run_service.create_run("phase5-fork-seed", "basic_survival")
    if ticks:
        await run_service.step_run(parent["id"], ticks)
    return await run_service.get_run(parent["id"])


def _run_documents(database, run_id):
    return {
        name: copy.deepcopy([
            document for document in getattr(database, name).documents
            if document.get("run_id") == run_id or (
                name == "kernel_runs" and document.get("id") == run_id
            )
        ])
        for name in FakeDatabase.COLLECTIONS
    }


@async_test
async def test_fork_from_later_tick_is_state_equivalent_and_parent_untouched(storage):
    parent = await _new_parent(ticks=3)
    before = _run_documents(storage, parent["id"])
    child = await run_service.fork_run(parent["id"], 2)

    assert child["genesis_tick"] == child["current_tick"] == 2
    assert child["next_order_index"] == child["parent_next_order_index"]
    assert child["lineage_key"] != parent["lineage_key"]
    assert child["child_genesis_state_hash"] != child["forked_from_state_hash"]
    assert _run_documents(storage, parent["id"]) == before

    child_events = [
        event for event in storage.accepted_events.documents
        if event["run_id"] == child["id"]
    ]
    assert [event["event_type"] for event in child_events] == ["fork_genesis"]
    source_events = [
        event for event in storage.accepted_events.documents
        if event["run_id"] == parent["id"] and event["simulation_time"] <= 2
    ]
    source_entities = run_service.reconstruct_entities(source_events)
    fork_entities = run_service.reconstruct_entities(child_events)
    assert source_entities == fork_entities
    assert content_hash_for_fork(
        fork_entities, 2, child["world_context_hash"],
    ) == child["source_content_hash"]
    lineage_record = next(
        record for record in storage.lineage_records.documents
        if record["id"] == child["lineage_record_id"]
    )
    assert lineage_record["mutates_world_state"] is False
    assert lineage_record["mutates_simulation_time"] is False


@async_test
async def test_fork_from_genesis_boundary_and_idempotent_repeat(storage):
    parent = await _new_parent()
    child1 = await run_service.fork_run(parent["id"], 0)
    child2 = await run_service.fork_run(parent["id"], 0)
    assert child1["id"] == child2["id"]
    assert child1["creation_command_hash"] == child2["creation_command_hash"]
    assert len([
        run for run in storage.kernel_runs.documents
        if run.get("creation_command_hash") == child1["creation_command_hash"]
    ]) == 1


@async_test
async def test_fork_of_fork_carries_validated_external_anchors(storage):
    parent = await _new_parent(ticks=1)
    child = await run_service.fork_run(parent["id"], 1, branch_key="child")
    grandchild = await run_service.fork_run(child["id"], 1, branch_key="grandchild")
    assert grandchild["parent_run_id"] == child["id"]
    assert grandchild["parent_lineage_key"] == child["lineage_key"]
    assert grandchild["external_causal_anchors"]
    assert (await replay_service.verify_replay(grandchild["id"]))["status"] == "pass"


@async_test
async def test_fork_api_request_creates_and_returns_child(storage):
    parent = await _new_parent(ticks=1)
    child = await api_fork_run(parent["id"], ForkRunRequest(
        fork_tick=1, branch_key="api",
    ))
    assert child["parent_run_id"] == parent["id"]
    assert child["genesis_tick"] == 1


@async_test
async def test_required_unique_indexes_are_declared(storage, monkeypatch):
    monkeypatch.setattr(core_db, "db", storage)
    await core_db.ensure_indexes()
    run_index_names = {kwargs.get("name") for _args, kwargs in storage.kernel_runs.indexes}
    assert {"uq_run_id", "uq_fork_creation_command", "uq_fork_identity"} <= run_index_names
    assert any(kwargs.get("name") == "uq_run_event_id" and kwargs.get("unique")
               for _args, kwargs in storage.accepted_events.indexes)
    assert any(kwargs.get("name") == "uq_run_frame_tick" and kwargs.get("unique")
               for _args, kwargs in storage.commit_frames.indexes)
    assert any(kwargs.get("name") == "uq_lineage_record_id" and kwargs.get("unique")
               for _args, kwargs in storage.lineage_records.indexes)


@async_test
async def test_concurrent_identical_requests_create_one_child(storage):
    parent = await _new_parent(ticks=1)
    children = await asyncio.gather(*[
        run_service.fork_run(parent["id"], 1, branch_key="parallel")
        for _ in range(4)
    ])
    assert len({child["id"] for child in children}) == 1
    identity = children[0]["fork_identity_hash"]
    assert len([
        run for run in storage.kernel_runs.documents
        if run.get("fork_identity_hash") == identity
    ]) == 1


@async_test
async def test_concurrent_parent_progress_cannot_shift_captured_boundary(storage):
    parent = await _new_parent(ticks=2)
    storage.capture_event = asyncio.Event()
    storage.release_event = asyncio.Event()
    storage.capture_run_id = parent["id"]
    fork_task = asyncio.create_task(run_service.fork_run(
        parent["id"], 2, branch_key="barrier",
    ))
    await storage.capture_event.wait()
    await run_service.step_run(parent["id"], 1)
    storage.release_event.set()
    child = await fork_task
    assert child["genesis_tick"] == child["forked_from_tick"] == 2
    assert (await run_service.get_run(parent["id"]))["current_tick"] == 3


@async_test
async def test_conflict_and_injected_failure_leave_no_partial_child(storage):
    parent = await _new_parent(ticks=1)
    baseline = storage.snapshot()
    with pytest.raises(run_service.ForkConflict):
        await run_service.fork_run(
            parent["id"], 1, branch_key="conflict",
            expected_forked_from_state_hash="not-the-boundary-hash",
        )
    assert storage.snapshot() == baseline

    storage.write_count = 0
    storage.fail_on_write = 3
    with pytest.raises(RuntimeError, match="injected transaction"):
        await run_service.fork_run(parent["id"], 1, branch_key="atomic-failure")
    storage.fail_on_write = None
    assert storage.snapshot() == baseline


@async_test
async def test_transaction_unsupported_fails_before_writes(storage):
    parent = await _new_parent(ticks=1)
    before = storage.snapshot()
    storage.write_count = 0
    storage.transaction_supported = False
    with pytest.raises(run_service.TransactionUnavailable):
        await run_service.fork_run(parent["id"], 1)
    assert storage.write_count == 0
    assert storage.snapshot() == before

    with pytest.raises(HTTPException) as api_error:
        await api_fork_run(parent["id"], ForkRunRequest(fork_tick=1))
    assert api_error.value.status_code == 503


@async_test
async def test_nonzero_child_replay_determinism_and_exact_continuation(storage):
    parent = await _new_parent(ticks=2)
    child = await run_service.fork_run(parent["id"], 2)
    await run_service.step_run(parent["id"], 2)
    await run_service.step_run(child["id"], 2)

    parent_entities = await run_service.load_entities(parent["id"])
    child_entities = await run_service.load_entities(child["id"])
    assert parent_entities == child_entities
    child_replay = await replay_service.verify_replay(child["id"])
    child_determinism = await replay_service.verify_determinism(child["id"])
    assert child_replay["status"] == "pass"
    assert child_replay["genesis_tick"] == 2
    assert child_determinism["status"] == "pass"

    # Parent raw history is not required after the accepted fork boundary.
    storage.accepted_events.documents[:] = [
        event for event in storage.accepted_events.documents
        if event["run_id"] != parent["id"]
    ]
    await run_service.step_run(child["id"], 1)
    assert (await replay_service.verify_replay(child["id"]))["status"] == "pass"
    assert (await replay_service.verify_determinism(child["id"]))["status"] == "pass"


@async_test
async def test_corrupt_projections_rebuild_from_child_stream(storage):
    parent = await _new_parent(ticks=2)
    child = await run_service.fork_run(parent["id"], 2)
    await run_service.step_run(child["id"], 1)
    expected_events = [
        event for event in storage.accepted_events.documents
        if event["run_id"] == child["id"]
    ]
    expected_entities = run_service.reconstruct_entities(expected_events)

    storage.entities.documents[:] = [
        document for document in storage.entities.documents
        if document["run_id"] != child["id"]
    ] + [{"run_id": child["id"], "id": "corrupt", "type": "corrupt"}]
    child_doc = next(run for run in storage.kernel_runs.documents if run["id"] == child["id"])
    child_doc["terrain"] = [["corrupt"]]

    result = await run_service.rebuild_run_projections(child["id"])
    assert result["entities_rebuilt"] == len(expected_entities)
    assert await run_service.load_entities(child["id"]) == expected_entities
    rebuilt = await run_service.get_run(child["id"])
    assert rebuilt["terrain"] != [["corrupt"]]


@async_test
async def test_schema_mismatch_and_authoritative_corruption_fail_closed(storage):
    parent = await _new_parent(ticks=1)
    parent_doc = next(run for run in storage.kernel_runs.documents if run["id"] == parent["id"])
    parent_doc["schema_context_hash"] = "corrupt"
    before = storage.snapshot()
    with pytest.raises(run_service.ForkCompatibilityError):
        await run_service.fork_run(parent["id"], 1)
    assert storage.snapshot() == before

    parent_doc = next(run for run in storage.kernel_runs.documents if run["id"] == parent["id"])
    parent_doc["schema_context_hash"] = run_service.schema_context_hash()
    child = await run_service.fork_run(parent["id"], 1)
    fork_event = next(
        event for event in storage.accepted_events.documents
        if event["run_id"] == child["id"] and event["event_type"] == "fork_genesis"
    )
    first_entity = next(iter(fork_event["mutation"]["new_entities"].values()))
    first_entity["alive"] = not first_entity.get("alive", True)
    result = await replay_service.verify_replay(child["id"])
    assert result["status"] == "fail"
    assert "fork_genesis" in result["reason"]


@async_test
async def test_corrupt_lineage_administrative_record_fails_replay(storage):
    parent = await _new_parent(ticks=1)
    child = await run_service.fork_run(parent["id"], 1, branch_key="lineage-corruption")
    record = next(
        item for item in storage.lineage_records.documents
        if item["id"] == child["lineage_record_id"]
    )
    record["parent_lineage_key"] = "tampered"
    result = await replay_service.verify_replay(child["id"])
    assert result["status"] == "fail"
    assert result["reason"] == "fork_lineage_record_invalid"


@async_test
async def test_tick_correct_empty_frame_and_existing_world_genesis_replay(storage):
    parent = await _new_parent()
    root_replay = await replay_service.verify_replay(parent["id"])
    root_determinism = await replay_service.verify_determinism(parent["id"])
    assert root_replay["status"] == root_determinism["status"] == "pass"

    entities = await run_service.load_entities(parent["id"])
    empty_tick_hash = canonical_hash(snapshot_for_hash(
        entities, 1, parent["lineage_key"],
    ))
    assert empty_tick_hash != parent["last_state_hash"]
    storage.commit_frames.documents.append({
        "id": f"{parent['id']}-frame-1", "run_id": parent["id"], "tick": 1,
        "starting_state_hash": parent["last_state_hash"],
        "ending_state_hash": empty_tick_hash,
        "accepted_event_ids": [], "rejected_proposal_ids": [],
        "hash_policy_version": HASH_POLICY_VERSION,
    })
    parent_doc = next(run for run in storage.kernel_runs.documents if run["id"] == parent["id"])
    parent_doc["current_tick"] = 1
    parent_doc["last_state_hash"] = empty_tick_hash
    assert (await replay_service.verify_replay(parent["id"]))["status"] == "pass"
    child = await run_service.fork_run(parent["id"], 1, branch_key="empty-frame")
    assert child["forked_from_state_hash"] == empty_tick_hash
    assert child["boundary_event_id"] is None
    assert child["boundary_identity"].startswith("empty-frame:")


def test_external_causal_anchors_require_actual_parent_events():
    entities = {"person-000": {"last_event_id": "missing-event"}}
    with pytest.raises(ForkContractError, match="not found"):
        build_external_anchor_manifest(entities, None, {}, "parent-lineage")


def test_commit_pipeline_rejects_unvalidated_causal_parent():
    entities = {"person-000": {
        "type": "person", "alive": True, "last_event_id": "evt-real",
    }}
    proposal = {
        "proposal_family": "test", "proposal_type": "act",
        "proposer_engine_id": "test", "proposer_engine_version": "1",
        "entity_id": "person-000",
        "causal_parent_event_ids": ["evt-fake"], "is_exogenous": False,
        "requested_time": 1, "phase": "agent", "engine_priority": 1,
        "touched_scope": ["person-000"], "preconditions": [],
        "mutation": {"entity_updates": {"person-000": {"alive": True}},
                     "new_entities": {}},
    }
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], 1, "lineage", "run", 0,
        "frame", valid_causal_parent_event_ids={"evt-real"},
    )
    assert not accepted
    assert rejected[0]["reason_code"] == "causality.invalid_parent"


def test_fork_genesis_is_provenance_not_a_fabricated_milestone():
    event = {
        "id": "evt-fork", "event_type": "fork_genesis", "event_family": "genesis",
        "simulation_time": 12, "order_index": 20, "entity_id": "__fork_genesis__",
        "is_exogenous": True, "touched_scope": ["person-000", "shelter-000"],
        "causal_parent_event_ids": ["evt-parent"],
        "mutation": {"entity_updates": {}, "new_entities": {
            "person-000": {"type": "person", "alive": True},
            "shelter-000": {"type": "shelter", "alive": True, "owner_id": "person-000"},
        }},
    }
    assert classify_milestones([event]) == []
    provenance = provenance_for_entity(
        "person-000", {"type": "person", "alive": True}, [event],
    )
    assert provenance["origin"] == "fork snapshot"
    assert provenance["spawned_at_tick"] == 12
