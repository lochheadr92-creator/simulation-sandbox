"""DB-facing orchestration for run creation, stepping, and Phase 5A forks."""
import copy
import uuid
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from core.db import client, db
from core.rng import DeterministicRNG, RNG_NAMESPACE, RNG_POLICY_VERSION
from core.kernel import build_genesis, run_tick
from core.constants import (
    ENGINE_VERSION, SCHEMA_VERSION, HASH_POLICY_VERSION,
    LEGACY_HASH_POLICY_VERSION, FORK_SEMANTICS_VERSION,
)
from core.hashing import canonical_hash
from core.mutations import apply_mutation, snapshot_for_hash
from core.forking import (
    FORK_RNG_MODEL, ForkContractError, build_external_anchor_manifest,
    build_fork_genesis_event, build_lineage_record, content_hash_for_fork, derive_fork_identity,
    fork_lineage_input, hash_world_context, schema_context_hash,
    validate_external_anchor_manifest, world_context_for_run,
)
from core.retention_service import prune_old_rejections
from scenarios import get_scenario


class ForkError(RuntimeError):
    pass


class ForkNotFound(ForkError):
    pass


class ForkConflict(ForkError):
    pass


class ForkCompatibilityError(ForkError):
    pass


class ForkIntegrityError(ForkError):
    pass


class TransactionUnavailable(ForkError):
    pass


def lineage_key_for(seed: str, engine_version: str = ENGINE_VERSION,
                    schema_version: str = SCHEMA_VERSION) -> str:
    """Legacy/root lineage derivation retained for existing tick-zero runs."""
    return f"{seed}|{schema_version}|{engine_version}"


def lineage_key_for_run(run: dict) -> str:
    return run.get("lineage_key") or lineage_key_for(
        run["seed"], run.get("engine_version", ENGINE_VERSION),
        run.get("schema_version", SCHEMA_VERSION),
    )


def hash_policy_for_run(run: dict) -> str:
    return run.get("hash_policy_version", LEGACY_HASH_POLICY_VERSION)


def rng_for_run(run: dict) -> DeterministicRNG:
    return DeterministicRNG(
        run["seed"],
        namespace=run.get("rng_namespace", RNG_NAMESPACE),
        policy_version=run.get("rng_policy_version", RNG_POLICY_VERSION),
    )


def _frame_hash(entities: dict, tick: int, lineage_key: str, run: dict,
                prior_hash: str | None, accepted: list) -> str:
    if accepted:
        return accepted[-1]["post_state_hash"]
    if hash_policy_for_run(run) == HASH_POLICY_VERSION:
        return canonical_hash(snapshot_for_hash(entities, tick, lineage_key))
    return prior_hash


def reconstruct_entities(events: list) -> dict:
    entities = {}
    for event in sorted(events, key=lambda e: (e["simulation_time"], e["order_index"])):
        apply_mutation(entities, copy.deepcopy(event["mutation"]))
    return entities


def _root_genesis_context(run_doc: dict, world_context: dict) -> dict:
    return {
        "version": "world-genesis-v1",
        "world_context": copy.deepcopy(world_context),
        "world_context_hash": run_doc["world_context_hash"],
        "schema_context_hash": run_doc["schema_context_hash"],
        "engine_version": run_doc["engine_version"],
        "schema_version": run_doc["schema_version"],
        "hash_policy_version": run_doc["hash_policy_version"],
        "rng_policy_version": run_doc["rng_policy_version"],
        "rng_namespace": run_doc["rng_namespace"],
    }


async def create_run(seed: str, scenario_id: str = "basic_survival"):
    scenario = get_scenario(scenario_id)
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    lineage_key = lineage_key_for(seed)
    world, entities, accepted, rejected, next_order = build_genesis(
        seed, scenario, lineage_key,
    )

    for event in accepted:
        event["run_id"] = run_id
    for rejection in rejected:
        rejection["run_id"] = run_id

    ending_hash = accepted[-1]["post_state_hash"] if accepted else None
    run_doc = {
        "id": run_id,
        "seed": seed,
        "scenario_id": scenario_id,
        "scenario_name": scenario.name,
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "schema_context_hash": schema_context_hash(),
        "hash_policy_version": HASH_POLICY_VERSION,
        "rng_policy_version": RNG_POLICY_VERSION,
        "rng_namespace": RNG_NAMESPACE,
        "genesis_kind": "world",
        "genesis_tick": 0,
        "lineage_key": lineage_key,
        "current_tick": 0,
        "next_order_index": next_order,
        "status": "paused",
        "last_state_hash": ending_hash,
        "width": world["width"],
        "height": world["height"],
        "terrain": world["terrain"],
        "replay_horizon": "run-full",
        "source_horizon": "world-genesis",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    world_context = world_context_for_run(run_doc, scenario)
    run_doc["world_context_hash"] = hash_world_context(world_context)
    if accepted:
        accepted[0]["genesis_context"] = _root_genesis_context(
            run_doc, world_context,
        )

    await db.kernel_runs.insert_one(dict(run_doc))
    if accepted:
        await db.accepted_events.insert_many([dict(e) for e in accepted])
    if rejected:
        await db.rejected_proposals.insert_many([dict(r) for r in rejected])

    entity_docs = []
    for entity_id, entity in entities.items():
        doc = dict(entity)
        doc["id"] = entity_id
        doc["run_id"] = run_id
        entity_docs.append(doc)
    if entity_docs:
        await db.entities.insert_many(entity_docs)

    await db.commit_frames.insert_one({
        "id": f"{run_id}-frame-genesis", "run_id": run_id, "tick": 0,
        "starting_state_hash": None, "ending_state_hash": ending_hash,
        "accepted_event_ids": [e["id"] for e in accepted],
        "rejected_proposal_ids": [r["id"] for r in rejected],
        "hash_policy_version": HASH_POLICY_VERSION,
    })
    return await get_run(run_id)


async def get_run(run_id: str):
    return await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})


async def list_runs():
    return await db.kernel_runs.find({}, {"_id": 0, "terrain": 0}).sort(
        "created_at", -1,
    ).to_list(200)


async def load_entities(run_id: str) -> dict:
    docs = await db.entities.find({"run_id": run_id}, {"_id": 0}).to_list(5000)
    entities = {}
    for doc in docs:
        entity_id = doc.pop("id")
        doc.pop("run_id", None)
        entities[entity_id] = doc
    return entities


async def save_entities_delta(run_id: str, entities: dict, touched_ids: set,
                              session=None):
    for entity_id in touched_ids:
        if entity_id in entities:
            doc = dict(entities[entity_id])
            doc["id"] = entity_id
            doc["run_id"] = run_id
            await db.entities.replace_one(
                {"run_id": run_id, "id": entity_id}, doc, upsert=True,
                session=session,
            )
        else:
            await db.entities.delete_one(
                {"run_id": run_id, "id": entity_id}, session=session,
            )


async def _valid_causal_parent_ids(run_id: str, entities: dict, run: dict) -> set:
    referenced = {
        entity.get("last_event_id") for entity in entities.values()
        if entity.get("last_event_id")
    }
    external = validate_external_anchor_manifest(
        run.get("external_causal_anchors", []),
    )
    internal_needed = referenced - external
    internal = set()
    if internal_needed:
        cursor = db.accepted_events.find(
            {"run_id": run_id, "id": {"$in": sorted(internal_needed)}},
            {"_id": 0, "id": 1},
        )
        internal = {doc["id"] for doc in await cursor.to_list(len(internal_needed))}
    missing = referenced - external - internal
    if missing:
        raise ForkIntegrityError(
            f"canonical entity state references missing causal events: {sorted(missing)}"
        )
    return referenced


async def step_run(run_id: str, n_ticks: int = 1):
    run = await get_run(run_id)
    if not run:
        raise ValueError("run not found")

    scenario = get_scenario(run["scenario_id"])
    entities = await load_entities(run_id)
    rng = rng_for_run(run)
    terrain = run["terrain"]
    order_index = run["next_order_index"]
    lineage_key = lineage_key_for_run(run)
    frames_summary = []

    for _ in range(n_ticks):
        next_tick = run["current_tick"] + 1
        starting_hash = run["last_state_hash"]
        valid_causal_ids = await _valid_causal_parent_ids(run_id, entities, run)

        accepted, rejected, order_index, diagnostics = run_tick(
            run_id, entities, terrain, next_tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_causal_ids,
        )
        for event in accepted:
            event["run_id"] = run_id
        for rejection in rejected:
            rejection["run_id"] = run_id

        touched = set()
        for event in accepted:
            touched.update(event["mutation"].get("new_entities", {}).keys())
            touched.update(event["mutation"].get("entity_updates", {}).keys())
            touched.update(event["mutation"].get("removed_entities", []))

        ending_hash = _frame_hash(
            entities, next_tick, lineage_key, run, starting_hash, accepted,
        )

        if accepted:
            await db.accepted_events.insert_many([dict(e) for e in accepted])
        if rejected:
            await db.rejected_proposals.insert_many([dict(r) for r in rejected])
        for entity_id, diagnostics_for_entity in diagnostics.items():
            await db.activation_diagnostics.replace_one(
                {"run_id": run_id, "entity_id": entity_id},
                {"run_id": run_id, "entity_id": entity_id, "tick": next_tick,
                 "diagnostics": diagnostics_for_entity},
                upsert=True,
            )
        await save_entities_delta(run_id, entities, touched)
        await db.commit_frames.insert_one({
            "id": f"{run_id}-frame-{next_tick}", "run_id": run_id,
            "tick": next_tick, "starting_state_hash": starting_hash,
            "ending_state_hash": ending_hash,
            "accepted_event_ids": [e["id"] for e in accepted],
            "rejected_proposal_ids": [r["id"] for r in rejected],
            "hash_policy_version": hash_policy_for_run(run),
        })

        run["current_tick"] = next_tick
        run["last_state_hash"] = ending_hash
        frames_summary.append({
            "tick": next_tick, "accepted_count": len(accepted),
            "rejected_count": len(rejected), "ending_state_hash": ending_hash,
        })

    await db.kernel_runs.update_one({"id": run_id}, {"$set": {
        "current_tick": run["current_tick"],
        "last_state_hash": run["last_state_hash"],
        "next_order_index": order_index,
        "status": "running",
    }})
    await prune_old_rejections(run_id, run["current_tick"])
    return frames_summary


def _validate_fork_compatibility(parent: dict):
    required = (
        "lineage_key", "schema_context_hash", "world_context_hash",
        "hash_policy_version", "rng_policy_version", "rng_namespace",
        "genesis_kind", "genesis_tick",
    )
    missing = [field for field in required if field not in parent]
    if missing:
        raise ForkCompatibilityError(
            f"parent predates the forkable schema context: missing {missing}"
        )
    if parent["engine_version"] != ENGINE_VERSION or parent["schema_version"] != SCHEMA_VERSION:
        raise ForkCompatibilityError("parent engine/schema is not executable by this process")
    if parent["hash_policy_version"] != HASH_POLICY_VERSION:
        raise ForkCompatibilityError("parent hash policy is not fork-compatible")
    if parent["rng_policy_version"] != RNG_POLICY_VERSION or parent["rng_namespace"] != RNG_NAMESPACE:
        raise ForkCompatibilityError("parent RNG context is not fork-compatible")
    expected_schema_hash = schema_context_hash(
        engine_version=parent["engine_version"],
        schema_version=parent["schema_version"],
        hash_policy_version=parent["hash_policy_version"],
    )
    if parent["schema_context_hash"] != expected_schema_hash:
        raise ForkCompatibilityError("parent schema-context hash mismatch")


def _genesis_context_from_events(events: list) -> dict:
    for event in events:
        context = event.get("genesis_context")
        if context:
            return context
    raise ForkIntegrityError("accepted stream has no authoritative genesis context")


async def _fork_run_transaction(parent_run_id: str, fork_tick: int,
                                branch_key: str,
                                expected_boundary_event_id: str | None,
                                expected_forked_from_state_hash: str | None,
                                session) -> dict:
    parent = await db.kernel_runs.find_one(
        {"id": parent_run_id}, {"_id": 0}, session=session,
    )
    if not parent:
        raise ForkNotFound("parent run not found")
    _validate_fork_compatibility(parent)
    if not isinstance(fork_tick, int) or fork_tick < parent["genesis_tick"] or fork_tick > parent["current_tick"]:
        raise ForkConflict("fork_tick is outside the parent's retained run range")
    if not isinstance(branch_key, str) or not branch_key or len(branch_key) > 64:
        raise ForkConflict("branch_key must be a non-empty string of at most 64 characters")

    frame = await db.commit_frames.find_one(
        {"run_id": parent_run_id, "tick": fork_tick}, {"_id": 0},
        session=session,
    )
    if not frame:
        raise ForkIntegrityError("parent boundary frame is missing")

    cursor = db.accepted_events.find(
        {"run_id": parent_run_id, "simulation_time": {"$lte": fork_tick}},
        {"_id": 0}, session=session,
    ).sort([("simulation_time", 1), ("order_index", 1)])
    events = await cursor.to_list(None)
    if not events:
        raise ForkIntegrityError("parent accepted stream is empty")

    reconstructed = reconstruct_entities(events)
    events_at_boundary = [e for e in events if e["simulation_time"] == fork_tick]
    boundary_event = events_at_boundary[-1] if events_at_boundary else None
    boundary_order_index = (
        boundary_event["order_index"] if boundary_event
        else max((e["order_index"] for e in events), default=-1)
    )
    boundary_event_id = boundary_event["id"] if boundary_event else None
    boundary_identity = boundary_event_id or (
        f"empty-frame:{frame['id']}:{fork_tick}:{frame['ending_state_hash']}"
    )
    if (expected_boundary_event_id is not None
            and expected_boundary_event_id != boundary_event_id):
        raise ForkConflict("expected boundary event does not match selected boundary")

    parent_lineage_key = lineage_key_for_run(parent)
    recomputed_parent_hash = canonical_hash(snapshot_for_hash(
        reconstructed, fork_tick, parent_lineage_key,
    ))
    forked_from_state_hash = frame["ending_state_hash"]
    if recomputed_parent_hash != forked_from_state_hash:
        raise ForkIntegrityError("reconstructed parent state hash does not match boundary frame")
    if (expected_forked_from_state_hash is not None
            and expected_forked_from_state_hash != forked_from_state_hash):
        raise ForkConflict("expected source state hash does not match selected boundary")

    genesis_context = _genesis_context_from_events(events)
    world_context = copy.deepcopy(genesis_context["world_context"])
    world_hash = hash_world_context(world_context)
    if world_hash != parent["world_context_hash"]:
        raise ForkIntegrityError("parent immutable world-context hash mismatch")

    source_hash = content_hash_for_fork(reconstructed, fork_tick, world_hash)
    source_events_by_id = {event["id"]: event for event in events}
    try:
        anchors = build_external_anchor_manifest(
            reconstructed, boundary_event, source_events_by_id,
            parent_lineage_key,
            inherited_anchors=parent.get("external_causal_anchors", []),
        )
    except ForkContractError as exc:
        raise ForkIntegrityError(str(exc)) from exc

    inherited_order_floor = (
        parent.get("parent_next_order_index", 0)
        if parent.get("genesis_kind") == "fork" else 0
    )
    parent_next_order_index = max(inherited_order_floor, max(
        (e["order_index"] for e in events if e.get("consumes_simulation_order", True)),
        default=-1,
    ) + 1)
    lineage_input = fork_lineage_input(
        parent_lineage_key=parent_lineage_key,
        fork_tick=fork_tick,
        boundary_identity=boundary_identity,
        boundary_order_index=boundary_order_index,
        forked_from_state_hash=forked_from_state_hash,
        source_hash=source_hash,
        world_hash=world_hash,
        branch_key=branch_key,
        engine_version=parent["engine_version"],
        schema_hash=parent["schema_context_hash"],
        rng_policy_version=parent["rng_policy_version"],
        rng_namespace=parent["rng_namespace"],
    )
    identity = derive_fork_identity(
        parent_run_id=parent_run_id,
        expected_boundary_event_id=expected_boundary_event_id,
        expected_state_hash=expected_forked_from_state_hash,
        lineage_input=lineage_input,
    )

    existing = await db.kernel_runs.find_one(
        {"$or": [
            {"id": identity["child_run_id"]},
            {"fork_identity_hash": identity["fork_identity_hash"]},
        ]},
        {"_id": 0}, session=session,
    )
    if existing:
        if existing.get("creation_command_hash") == identity["creation_command_hash"]:
            return existing
        raise ForkConflict("deterministic child identity already exists with different content")

    metadata = {
        "parent_run_id": parent_run_id,
        "parent_lineage_key": parent_lineage_key,
        "boundary_frame_id": frame["id"],
        "boundary_event_id": boundary_event_id,
        "boundary_identity": boundary_identity,
        "boundary_order_index": boundary_order_index,
        "parent_next_order_index": parent_next_order_index,
        "parent_stream_head_at_creation": {
            "current_tick": parent["current_tick"],
            "next_order_index": parent["next_order_index"],
            "last_state_hash": parent["last_state_hash"],
        },
        "parent_simulation_tick": fork_tick,
        "genesis_tick": fork_tick,
        "forked_from_state_hash": forked_from_state_hash,
        "source_content_hash": source_hash,
        "world_context_hash": world_hash,
        "engine_version": parent["engine_version"],
        "schema_version": parent["schema_version"],
        "schema_context_hash": parent["schema_context_hash"],
        "hash_policy_version": parent["hash_policy_version"],
        "rng_policy_version": parent["rng_policy_version"],
        "rng_namespace": parent["rng_namespace"],
        "rng_fork_model": FORK_RNG_MODEL,
        "fork_semantics_version": FORK_SEMANTICS_VERSION,
        "branch_key": branch_key,
        **identity,
    }
    metadata["lineage_record_id"] = f"lineage-{identity['fork_identity_hash'][:24]}"
    fork_event = build_fork_genesis_event(
        child_run_id=identity["child_run_id"],
        child_lineage_key=identity["child_lineage_key"],
        genesis_tick=fork_tick,
        boundary_order_index=boundary_order_index,
        entities=reconstructed,
        world_context=world_context,
        metadata=metadata,
        external_causal_anchors=anchors,
    )
    child_genesis_hash = fork_event["post_state_hash"]
    fork_event["genesis_context"]["child_genesis_state_hash"] = child_genesis_hash
    lineage_record = build_lineage_record(
        fork_event=fork_event, metadata=metadata,
    )
    fork_event["genesis_context"]["lineage_record_id"] = lineage_record["id"]
    fork_event["genesis_context"]["lineage_record_hash"] = lineage_record["record_hash"]

    child_run = {
        "id": identity["child_run_id"],
        "seed": parent["seed"],
        "scenario_id": parent["scenario_id"],
        "scenario_name": parent.get("scenario_name"),
        "engine_version": parent["engine_version"],
        "schema_version": parent["schema_version"],
        "schema_context_hash": parent["schema_context_hash"],
        "hash_policy_version": parent["hash_policy_version"],
        "rng_policy_version": parent["rng_policy_version"],
        "rng_namespace": parent["rng_namespace"],
        "rng_fork_model": FORK_RNG_MODEL,
        "genesis_kind": "fork",
        "genesis_tick": fork_tick,
        "lineage_key": identity["child_lineage_key"],
        "parent_run_id": parent_run_id,
        "parent_lineage_key": parent_lineage_key,
        "forked_from_tick": fork_tick,
        "forked_from_state_hash": forked_from_state_hash,
        "source_content_hash": source_hash,
        "world_context_hash": world_hash,
        "boundary_frame_id": frame["id"],
        "boundary_event_id": boundary_event_id,
        "boundary_identity": boundary_identity,
        "boundary_order_index": boundary_order_index,
        "parent_next_order_index": parent_next_order_index,
        "parent_stream_head_at_creation": copy.deepcopy(
            metadata["parent_stream_head_at_creation"],
        ),
        "fork_semantics_version": FORK_SEMANTICS_VERSION,
        "fork_identity_hash": identity["fork_identity_hash"],
        "creation_command_hash": identity["creation_command_hash"],
        "branch_key": branch_key,
        "child_genesis_state_hash": child_genesis_hash,
        "lineage_record_id": lineage_record["id"],
        "lineage_record_hash": lineage_record["record_hash"],
        "external_causal_anchors": copy.deepcopy(anchors),
        "replay_horizon": "child-full",
        "source_horizon": "parent-full-at-creation",
        "current_tick": fork_tick,
        "next_order_index": parent_next_order_index,
        "status": "paused",
        "last_state_hash": child_genesis_hash,
        "width": world_context["width"],
        "height": world_context["height"],
        "terrain": copy.deepcopy(world_context["terrain"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    entity_docs = [
        {"id": entity_id, "run_id": child_run["id"], **copy.deepcopy(entity)}
        for entity_id, entity in sorted(reconstructed.items())
    ]
    genesis_frame = {
        "id": fork_event["frame_id"],
        "run_id": child_run["id"],
        "tick": fork_tick,
        "starting_state_hash": None,
        "ending_state_hash": child_genesis_hash,
        "accepted_event_ids": [fork_event["id"]],
        "rejected_proposal_ids": [],
        "hash_policy_version": parent["hash_policy_version"],
        "genesis_kind": "fork",
        "forked_from_state_hash": forked_from_state_hash,
    }

    # Verify the selected parent head/boundary once more through the same
    # transaction snapshot immediately before child writes. Parent documents
    # are never updated by this operation.
    verified_parent = await db.kernel_runs.find_one(
        {"id": parent_run_id}, {"_id": 0}, session=session,
    )
    verified_frame = await db.commit_frames.find_one(
        {"run_id": parent_run_id, "tick": fork_tick}, {"_id": 0},
        session=session,
    )
    if (verified_parent != parent or not verified_frame
            or verified_frame.get("id") != frame.get("id")
            or verified_frame.get("ending_state_hash") != forked_from_state_hash):
        raise ForkIntegrityError("parent stream head or selected boundary changed in transaction snapshot")

    await db.lineage_records.insert_one(copy.deepcopy(lineage_record), session=session)
    await db.kernel_runs.insert_one(copy.deepcopy(child_run), session=session)
    await db.accepted_events.insert_one(copy.deepcopy(fork_event), session=session)
    if entity_docs:
        await db.entities.insert_many(entity_docs, session=session)
    await db.commit_frames.insert_one(genesis_frame, session=session)
    return copy.deepcopy(child_run)


def _is_transaction_unsupported(exc: OperationFailure) -> bool:
    message = str(exc).lower()
    return exc.code in {20, 303, 40573} or "transaction" in message and (
        "not supported" in message or "only allowed" in message
        or "replica set" in message
    )


async def fork_run(parent_run_id: str, fork_tick: int, branch_key: str = "default",
                   expected_boundary_event_id: str | None = None,
                   expected_forked_from_state_hash: str | None = None) -> dict:
    try:
        async with await client.start_session() as session:
            async with session.start_transaction(
                read_concern=ReadConcern("snapshot"),
                write_concern=WriteConcern("majority"),
            ):
                return await _fork_run_transaction(
                    parent_run_id, fork_tick, branch_key,
                    expected_boundary_event_id,
                    expected_forked_from_state_hash,
                    session,
                )
    except DuplicateKeyError:
        # A concurrent identical transaction won. Verify and return exactly
        # that deterministic child; never create a sibling.
        parent = await get_run(parent_run_id)
        if not parent:
            raise ForkNotFound("parent run not found")
        # Re-running resolves the same deterministic identity and reaches the
        # existing-child branch under a new snapshot.
        async with await client.start_session() as session:
            async with session.start_transaction(
                read_concern=ReadConcern("snapshot"),
                write_concern=WriteConcern("majority"),
            ):
                return await _fork_run_transaction(
                    parent_run_id, fork_tick, branch_key,
                    expected_boundary_event_id,
                    expected_forked_from_state_hash,
                    session,
                )
    except OperationFailure as exc:
        if _is_transaction_unsupported(exc):
            raise TransactionUnavailable(
                "Mongo deployment does not support required fork transactions"
            ) from exc
        raise


async def _rebuild_run_projections_transaction(run_id: str, session) -> dict:
    run = await db.kernel_runs.find_one(
        {"id": run_id}, {"_id": 0}, session=session,
    )
    if not run:
        raise ValueError("run not found")
    cursor = db.accepted_events.find(
        {"run_id": run_id}, {"_id": 0}, session=session,
    ).sort([("simulation_time", 1), ("order_index", 1)])
    events = await cursor.to_list(None)
    if not events:
        raise ForkIntegrityError("accepted stream is empty")
    entities = reconstruct_entities(events)
    genesis_context = _genesis_context_from_events(events)
    world_context = copy.deepcopy(genesis_context["world_context"])
    if hash_world_context(world_context) != run.get("world_context_hash"):
        raise ForkIntegrityError("authoritative world-context hash mismatch")
    frames = await db.commit_frames.find(
        {"run_id": run_id}, {"_id": 0}, session=session,
    ).sort("tick", 1).to_list(None)
    if not frames:
        raise ForkIntegrityError("commit-frame stream is empty")
    latest_frame = frames[-1]
    inherited_order_floor = (
        run.get("parent_next_order_index", 0)
        if run.get("genesis_kind") == "fork" else 0
    )
    next_order_index = max(inherited_order_floor, max(
        (event["order_index"] for event in events
         if event.get("consumes_simulation_order", True)),
        default=-1,
    ) + 1)

    await db.entities.delete_many({"run_id": run_id}, session=session)
    entity_docs = [
        {"id": entity_id, "run_id": run_id, **copy.deepcopy(entity)}
        for entity_id, entity in sorted(entities.items())
    ]
    if entity_docs:
        await db.entities.insert_many(entity_docs, session=session)
    await db.kernel_runs.update_one({"id": run_id}, {"$set": {
        "width": world_context["width"],
        "height": world_context["height"],
        "terrain": copy.deepcopy(world_context["terrain"]),
        "current_tick": latest_frame["tick"],
        "last_state_hash": latest_frame["ending_state_hash"],
        "next_order_index": next_order_index,
    }}, session=session)
    return {"run_id": run_id, "entities_rebuilt": len(entity_docs),
            "current_tick": latest_frame["tick"]}


async def rebuild_run_projections(run_id: str) -> dict:
    """Rebuild mutable entity/world caches from authoritative accepted data."""
    try:
        async with await client.start_session() as session:
            async with session.start_transaction(
                read_concern=ReadConcern("snapshot"),
                write_concern=WriteConcern("majority"),
            ):
                return await _rebuild_run_projections_transaction(run_id, session)
    except OperationFailure as exc:
        if _is_transaction_unsupported(exc):
            raise TransactionUnavailable(
                "Mongo deployment does not support required rebuild transactions"
            ) from exc
        raise


async def set_run_status(run_id: str, status: str):
    await db.kernel_runs.update_one({"id": run_id}, {"$set": {"status": status}})
