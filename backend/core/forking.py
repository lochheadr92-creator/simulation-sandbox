"""Pure Phase 5A fork contract helpers.

This module has no DB, wall-clock, UUID, RNG, or process-global state. It
defines deterministic identity, version metadata, immutable world context,
and the authoritative fork-genesis event shape used by run/replay services.
"""
import copy

from core.constants import (
    ENGINE_VERSION, SCHEMA_VERSION, HASH_POLICY_VERSION,
    FORK_SEMANTICS_VERSION,
)
from core.hashing import canonical_hash, state_content_hash
from core.mutations import snapshot_for_hash
from core.rng import RNG_NAMESPACE, RNG_POLICY_VERSION


SCHEMA_CONTEXT_KIND = "simulation-schema-context-v1"
FORK_RNG_MODEL = "rng-fork-exact-v1"
FORK_GENESIS_VERSION = "fork-genesis-v1"
WORLD_CONTEXT_VERSION = "immutable-world-context-v1"
LINEAGE_RECORD_VERSION = "lineage-record-v1"


class ForkContractError(ValueError):
    pass


def schema_context(engine_version: str = ENGINE_VERSION,
                   schema_version: str = SCHEMA_VERSION,
                   hash_policy_version: str = HASH_POLICY_VERSION) -> dict:
    return {
        "kind": SCHEMA_CONTEXT_KIND,
        "engine_version": engine_version,
        "schema_version": schema_version,
        "hash_policy_version": hash_policy_version,
        "accepted_event_schema": "accepted-event-v1",
        "entity_mutation_schema": "entity-mutation-v1",
        "world_genesis_schema": "world-genesis-v1",
        "fork_genesis_schema": FORK_GENESIS_VERSION,
    }


def schema_context_hash(**versions) -> str:
    return canonical_hash(schema_context(**versions))


def world_context_for_run(run: dict, scenario) -> dict:
    return {
        "version": WORLD_CONTEXT_VERSION,
        "scenario_id": run["scenario_id"],
        "scenario": {
            "enabled_domains": list(scenario.enabled_domains),
            "world_gen": copy.deepcopy(scenario.world_gen),
        },
        "width": run["width"],
        "height": run["height"],
        "terrain": copy.deepcopy(run["terrain"]),
    }


def hash_world_context(world_context: dict) -> str:
    return canonical_hash(world_context)


def event_anchor_payload(event: dict, parent_lineage_key: str) -> dict:
    return {
        "event_id": event["id"],
        "parent_lineage_key": parent_lineage_key,
        "event_type": event["event_type"],
        "simulation_time": event["simulation_time"],
        "order_index": event["order_index"],
        "post_state_hash": event["post_state_hash"],
        "causal_parent_event_ids": list(event.get("causal_parent_event_ids", [])),
    }


def event_anchor(event: dict, parent_lineage_key: str) -> dict:
    payload = event_anchor_payload(event, parent_lineage_key)
    return {**payload, "event_header_hash": canonical_hash(payload)}


def validate_external_anchor_manifest(manifest: list) -> set:
    valid = set()
    for anchor in manifest:
        payload = {k: anchor[k] for k in (
            "event_id", "parent_lineage_key", "event_type", "simulation_time",
            "order_index", "post_state_hash", "causal_parent_event_ids",
        )}
        if canonical_hash(payload) != anchor.get("event_header_hash"):
            raise ForkContractError(f"invalid external causal anchor: {anchor.get('event_id')}")
        if anchor["event_id"] in valid:
            raise ForkContractError(f"duplicate external causal anchor: {anchor['event_id']}")
        valid.add(anchor["event_id"])
    return valid


def build_external_anchor_manifest(entities: dict, boundary_event: dict | None,
                                   source_events_by_id: dict,
                                   parent_lineage_key: str,
                                   inherited_anchors: list | None = None) -> list:
    referenced_ids = {
        entity.get("last_event_id") for entity in entities.values()
        if entity.get("last_event_id")
    }
    if boundary_event:
        referenced_ids.add(boundary_event["id"])

    inherited_anchors = inherited_anchors or []
    validate_external_anchor_manifest(inherited_anchors)
    inherited_by_id = {
        anchor["event_id"]: copy.deepcopy(anchor) for anchor in inherited_anchors
    }
    anchors = []
    for event_id in sorted(referenced_ids):
        event = source_events_by_id.get(event_id)
        if event:
            anchors.append(event_anchor(event, parent_lineage_key))
        elif event_id in inherited_by_id:
            anchors.append(inherited_by_id[event_id])
        else:
            raise ForkContractError(f"causal anchor not found in parent stream: {event_id}")
    validate_external_anchor_manifest(anchors)
    return anchors


def fork_lineage_input(*, parent_lineage_key: str, fork_tick: int,
                       boundary_identity: str, boundary_order_index: int,
                       forked_from_state_hash: str, source_hash: str,
                       world_hash: str, branch_key: str, engine_version: str,
                       schema_hash: str, rng_policy_version: str,
                       rng_namespace: str) -> dict:
    return {
        "kind": "fork-lineage-v1",
        "parent_lineage_key": parent_lineage_key,
        "fork_tick": fork_tick,
        "boundary_identity": boundary_identity,
        "boundary_order_index": boundary_order_index,
        "forked_from_state_hash": forked_from_state_hash,
        "source_content_hash": source_hash,
        "world_context_hash": world_hash,
        "branch_key": branch_key,
        "engine_version": engine_version,
        "schema_context_hash": schema_hash,
        "rng_policy_version": rng_policy_version,
        "rng_namespace": rng_namespace,
        "fork_semantics_version": FORK_SEMANTICS_VERSION,
    }


def derive_fork_identity(*, parent_run_id: str, expected_boundary_event_id: str | None,
                         expected_state_hash: str | None, lineage_input: dict) -> dict:
    fork_identity_hash = canonical_hash(lineage_input)
    child_lineage_key = canonical_hash({
        "kind": "child-lineage-key-v1",
        "fork_identity_hash": fork_identity_hash,
    })
    creation_command = {
        "kind": "fork-command-v1",
        "parent_run_id": parent_run_id,
        "fork_identity_hash": fork_identity_hash,
        "expected_boundary_event_id": expected_boundary_event_id,
        "expected_forked_from_state_hash": expected_state_hash,
    }
    creation_command_hash = canonical_hash(creation_command)
    return {
        "fork_identity_hash": fork_identity_hash,
        "child_lineage_key": child_lineage_key,
        "creation_command_hash": creation_command_hash,
        "child_run_id": f"run-fork-{creation_command_hash[:24]}",
    }


def build_fork_genesis_event(*, child_run_id: str, child_lineage_key: str,
                             genesis_tick: int, boundary_order_index: int,
                             entities: dict, world_context: dict,
                             metadata: dict, external_causal_anchors: list) -> dict:
    mutation = {
        "new_entities": copy.deepcopy(entities),
        "entity_updates": {},
        "removed_entities": [],
    }
    post_state_hash = canonical_hash(snapshot_for_hash(
        entities, genesis_tick, child_lineage_key,
    ))
    event_id = f"evt-fork-{metadata['fork_identity_hash'][:24]}"
    frame_id = f"{child_run_id}-frame-genesis-{genesis_tick}"
    return {
        "id": event_id,
        "run_id": child_run_id,
        "frame_id": frame_id,
        "event_family": "genesis",
        "event_type": "fork_genesis",
        "simulation_time": genesis_tick,
        "order_index": boundary_order_index,
        "stream_sequence": 0,
        "consumes_simulation_order": False,
        "causal_parent_event_ids": [metadata["boundary_event_id"]]
        if metadata.get("boundary_event_id") else [],
        "preconditions": [],
        "external_causal_anchors": copy.deepcopy(external_causal_anchors),
        "is_exogenous": True,
        "engine_version": metadata["engine_version"],
        "schema_version": metadata["schema_version"],
        "schema_context_hash": metadata["schema_context_hash"],
        "fork_semantics_version": metadata["fork_semantics_version"],
        "entity_id": "__fork_genesis__",
        "touched_scope": sorted(entities),
        "mutation": mutation,
        "genesis_context": {
            "version": FORK_GENESIS_VERSION,
            "world_context": copy.deepcopy(world_context),
            **copy.deepcopy(metadata),
        },
        "post_state_hash": post_state_hash,
        "source_proposal_id": None,
        "proposer_engine_id": "core_fork",
        "explanation": (
            f"fork genesis from {metadata['parent_run_id']} at tick {genesis_tick}"
        ),
    }


def build_lineage_record(*, fork_event: dict, metadata: dict) -> dict:
    """Build the non-mutating Core administrative record for fork ancestry."""
    record = {
        "id": metadata["lineage_record_id"],
        "record_type": "lineage_creation",
        "record_version": LINEAGE_RECORD_VERSION,
        "authority": "core",
        "mutates_world_state": False,
        "mutates_simulation_time": False,
        "child_run_id": metadata["child_run_id"],
        "child_lineage_key": metadata["child_lineage_key"],
        "parent_run_id": metadata["parent_run_id"],
        "parent_lineage_key": metadata["parent_lineage_key"],
        "effective_boundary": {
            "simulation_time": metadata["genesis_tick"],
            "fork_genesis_event_id": fork_event["id"],
            "boundary_identity": metadata["boundary_identity"],
            "boundary_order_index": metadata["boundary_order_index"],
        },
        "forked_from_state_hash": metadata["forked_from_state_hash"],
        "source_content_hash": metadata["source_content_hash"],
        "world_context_hash": metadata["world_context_hash"],
        "schema_context_hash": metadata["schema_context_hash"],
        "engine_version": metadata["engine_version"],
        "schema_version": metadata["schema_version"],
        "rng_policy_version": metadata["rng_policy_version"],
        "rng_namespace": metadata["rng_namespace"],
        "rng_fork_model": metadata["rng_fork_model"],
        "fork_semantics_version": metadata["fork_semantics_version"],
        "fork_identity_hash": metadata["fork_identity_hash"],
        "creation_command_hash": metadata["creation_command_hash"],
        "branch_key": metadata["branch_key"],
        "replay_horizon": "child-full",
        "source_horizon": "parent-full-at-creation",
    }
    return {**record, "record_hash": canonical_hash(record)}


def validate_lineage_record(record: dict) -> None:
    payload = {key: value for key, value in record.items()
               if key not in ("_id", "record_hash")}
    if record.get("record_version") != LINEAGE_RECORD_VERSION:
        raise ForkContractError("unsupported lineage record version")
    if record.get("mutates_world_state") is not False or record.get("mutates_simulation_time") is not False:
        raise ForkContractError("lineage administrative record cannot mutate world truth")
    if canonical_hash(payload) != record.get("record_hash"):
        raise ForkContractError("lineage administrative record hash mismatch")


def content_hash_for_fork(entities: dict, tick: int, world_hash: str) -> str:
    return state_content_hash(entities, tick, world_hash)
