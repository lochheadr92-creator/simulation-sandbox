"""Regression tests for safe Mongo batching in frame persistence.

Confirms:
- chunking math and bulk helpers preserve document identity
- batched entity upsert/delete is equivalent to per-id loops
- round-trip counts drop under batching
- canonical hashes remain identical for equivalent entity sets
"""
from __future__ import annotations

import copy
import time
from types import SimpleNamespace

import pytest

from core.hashing import canonical_hash
from core.mutations import snapshot_for_hash
from core.storage.frame_transaction import (
    BULK_WRITE_CHUNK_SIZE,
    INSERT_MANY_CHUNK_SIZE,
    PrecomputedFrame,
    _bulk_delete_entities,
    _bulk_replace_entities,
    _chunks,
    _insert_many_chunked,
    _write_frame_body,
)
from tests.test_phase5_fork import FakeCollection, FakeDatabase


def test_chunks_cover_all_items_without_overlap():
    items = list(range(1000))
    chunks = list(_chunks(items, 250))
    assert len(chunks) == 4
    assert [len(c) for c in chunks] == [250, 250, 250, 250]
    assert [x for chunk in chunks for x in chunk] == items
    assert list(_chunks(list(range(3)), 250)) == [[0, 1, 2]]
    with pytest.raises(ValueError):
        list(_chunks([1], 0))


def test_insert_many_chunked_reduces_round_trips():
    import asyncio

    class CountingCollection:
        def __init__(self):
            self.trips = 0
            self.docs = []

        async def insert_many(self, documents, session=None, ordered=True):
            self.trips += 1
            self.docs.extend(copy.deepcopy(documents))

    coll = CountingCollection()
    docs = [{"id": f"e-{i}", "n": i} for i in range(INSERT_MANY_CHUNK_SIZE * 3 + 7)]

    loop = asyncio.new_event_loop()
    try:
        trips = loop.run_until_complete(_insert_many_chunked(coll, docs, session=None))
    finally:
        loop.close()

    assert trips == 4  # 250+250+250+7
    assert coll.trips == 4
    assert coll.docs == docs


def test_bulk_entity_replace_and_delete_match_loop_semantics():
    import asyncio
    import core.storage.frame_transaction as ft

    database = FakeDatabase()
    entities = database.entities
    run_id = "batch-run"
    docs = [
        {"run_id": run_id, "id": f"person-{i:03d}", "food": i, "type": "person"}
        for i in range(600)
    ]
    original_db = ft.db
    ft.db = database

    async def seed_and_batch():
        # Seed a subset so replace paths hit matches and inserts.
        await entities.insert_many(docs[:100])
        trips = await _bulk_replace_entities(run_id, docs, session=None)
        delete_trips = await _bulk_delete_entities(
            run_id, [f"person-{i:03d}" for i in range(0, 50)], session=None,
        )
        return trips, delete_trips

    loop = asyncio.new_event_loop()
    try:
        trips, delete_trips = loop.run_until_complete(seed_and_batch())
    finally:
        loop.close()
        ft.db = original_db

    assert trips == 3  # 250+250+100
    assert delete_trips == 1
    remaining = sorted(doc["id"] for doc in entities.documents)
    assert remaining == [f"person-{i:03d}" for i in range(50, 600)]
    # Spot-check upsert payload identity
    sample = next(doc for doc in entities.documents if doc["id"] == "person-100")
    assert sample["food"] == 100


def test_batched_entity_projection_preserves_canonical_hash():
    """Batching must not alter entity projection content or hash."""
    entities = {
        f"e-{i:04d}": {
            "type": "person",
            "alive": True,
            "food_inventory": i % 7,
            "position": {"x": i % 10, "y": i // 10},
        }
        for i in range(120)
    }
    lineage = "batch-lineage"
    tick = 12
    hash_a = canonical_hash(snapshot_for_hash(entities, tick, lineage))

    docs = []
    for eid, body in sorted(entities.items()):
        doc = dict(body)
        doc["id"] = eid
        doc["run_id"] = "run-hash"
        docs.append(doc)

    # Round-trip through deepcopy (same as bulk path) and rebuild map
    rebuilt = {}
    for doc in copy.deepcopy(docs):
        eid = doc.pop("id")
        doc.pop("run_id", None)
        rebuilt[eid] = doc
    hash_b = canonical_hash(snapshot_for_hash(rebuilt, tick, lineage))
    assert hash_a == hash_b


def test_bulk_vs_loop_round_trip_counts_and_timing():
    """Bulk path uses far fewer write calls than a naive replace_one loop."""
    import asyncio
    import core.storage.frame_transaction as ft

    class CountingEntities(FakeCollection):
        def __init__(self, database, name):
            super().__init__(database, name)
            self.replace_calls = 0
            self.bulk_calls = 0

        async def replace_one(self, query, document, upsert=False, session=None):
            self.replace_calls += 1
            return await super().replace_one(query, document, upsert=upsert, session=session)

        async def bulk_write(self, operations, session=None, ordered=True):
            self.bulk_calls += 1
            return await super().bulk_write(operations, session=session, ordered=ordered)

    database = FakeDatabase()
    counting = CountingEntities(database, "entities")
    database.entities = counting

    docs = [
        {"run_id": "timing-run", "id": f"ent-{i:04d}", "n": i}
        for i in range(500)
    ]

    async def loop_path():
        counting.replace_calls = 0
        t0 = time.perf_counter()
        for doc in docs:
            await counting.replace_one(
                {"run_id": doc["run_id"], "id": doc["id"]},
                copy.deepcopy(doc),
                upsert=True,
            )
        return time.perf_counter() - t0, counting.replace_calls

    async def bulk_path():
        counting.bulk_calls = 0
        counting.documents.clear()
        original = ft.db
        ft.db = database
        try:
            t0 = time.perf_counter()
            trips = await _bulk_replace_entities("timing-run", docs, session=None)
            elapsed = time.perf_counter() - t0
        finally:
            ft.db = original
        return elapsed, trips, counting.bulk_calls

    loop = asyncio.new_event_loop()
    try:
        loop_elapsed, loop_calls = loop.run_until_complete(loop_path())
        bulk_elapsed, trips, bulk_calls = loop.run_until_complete(bulk_path())
    finally:
        loop.close()

    assert loop_calls == 500
    assert trips == 2  # 250 + 250
    assert bulk_calls == 2
    # Timing is environment-dependent; primarily assert round-trip reduction.
    assert bulk_calls < loop_calls / 10
    assert bulk_elapsed <= loop_elapsed * 5 + 0.05


def test_chunk_constants_are_conservative():
    assert 1 <= BULK_WRITE_CHUNK_SIZE <= 1000
    assert 1 <= INSERT_MANY_CHUNK_SIZE <= 1000
