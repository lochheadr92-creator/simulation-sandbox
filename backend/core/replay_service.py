"""Recorded replay and deterministic shadow re-simulation."""
import copy

from core.db import db
from core.hashing import canonical_hash
from core.mutations import apply_mutation, snapshot_for_hash
from core.kernel import build_genesis, run_tick
from core.run_service import (
    hash_policy_for_run, lineage_key_for_run, reconstruct_entities, rng_for_run,
)
from core.constants import HASH_POLICY_VERSION
from core.commit_pipeline import run_commit_frame
from core.interventions import build_intervention_proposal
from core.forking import (
    ForkContractError, content_hash_for_fork, hash_world_context,
    validate_external_anchor_manifest, validate_lineage_record,
)
from domains.base import DomainOutput
from scenarios import get_scenario


def _order_index_sequence(events: list) -> list:
    return [{
        "entity_id": event["entity_id"],
        "event_type": event["event_type"],
        "order_index": event["order_index"],
        "event_id": event["id"],
    } for event in events]


def _events_by_tick(events: list) -> dict:
    grouped = {}
    for event in events:
        grouped.setdefault(event["simulation_time"], []).append(event)
    for tick_events in grouped.values():
        tick_events.sort(key=lambda event: event["order_index"])
    return grouped


def _valid_shadow_causal_ids(entities: dict, external_anchors: set) -> set:
    return external_anchors | {
        entity.get("last_event_id") for entity in entities.values()
        if entity.get("last_event_id")
    }


def _recomputed_frame_hash(run: dict, entities: dict, tick: int,
                           lineage_key: str, prior_hash: str | None,
                           tick_events: list) -> str:
    if tick_events or hash_policy_for_run(run) == HASH_POLICY_VERSION:
        return canonical_hash(snapshot_for_hash(entities, tick, lineage_key))
    return prior_hash


def _fork_genesis_event(run: dict, events: list) -> dict:
    matches = [event for event in events if event.get("event_type") == "fork_genesis"]
    if len(matches) != 1:
        raise ForkContractError("fork stream must contain exactly one fork_genesis event")
    event = matches[0]
    if event["simulation_time"] != run["genesis_tick"]:
        raise ForkContractError("fork_genesis tick does not match stored genesis_tick")
    return event


def _verify_fork_genesis(run: dict, fork_event: dict) -> dict | None:
    context = fork_event.get("genesis_context") or {}
    world_context = context.get("world_context")
    if not world_context:
        return {"status": "fail", "reason": "fork_genesis_world_context_missing"}
    world_hash = hash_world_context(world_context)
    if world_hash != run.get("world_context_hash") or world_hash != context.get("world_context_hash"):
        return {"status": "fail", "reason": "fork_genesis_world_context_hash_mismatch"}

    genesis_entities = reconstruct_entities([fork_event])
    source_hash = content_hash_for_fork(
        genesis_entities, run["genesis_tick"], world_hash,
    )
    if source_hash != run.get("source_content_hash") or source_hash != context.get("source_content_hash"):
        return {"status": "fail", "reason": "fork_genesis_source_content_hash_mismatch"}

    child_hash = canonical_hash(snapshot_for_hash(
        genesis_entities, run["genesis_tick"], lineage_key_for_run(run),
    ))
    if child_hash != run.get("child_genesis_state_hash") or child_hash != fork_event.get("post_state_hash"):
        return {"status": "fail", "reason": "fork_genesis_child_hash_mismatch"}
    try:
        anchor_ids = validate_external_anchor_manifest(
            fork_event.get("external_causal_anchors", []),
        )
        run_anchor_ids = validate_external_anchor_manifest(
            run.get("external_causal_anchors", []),
        )
    except ForkContractError as exc:
        return {"status": "fail", "reason": "fork_genesis_anchor_invalid", "detail": str(exc)}
    if anchor_ids != run_anchor_ids:
        return {"status": "fail", "reason": "fork_genesis_anchor_manifest_mismatch"}
    return None


async def _verify_fork_lineage_record(run: dict, fork_event: dict) -> dict | None:
    record_id = run.get("lineage_record_id")
    context = fork_event.get("genesis_context") or {}
    if not record_id or context.get("lineage_record_id") != record_id:
        return {"status": "fail", "reason": "fork_lineage_record_reference_mismatch"}
    record = await db.lineage_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        return {"status": "fail", "reason": "fork_lineage_record_missing"}
    try:
        validate_lineage_record(record)
    except ForkContractError as exc:
        return {"status": "fail", "reason": "fork_lineage_record_invalid", "detail": str(exc)}
    if (record.get("record_hash") != run.get("lineage_record_hash")
            or record.get("record_hash") != context.get("lineage_record_hash")
            or record.get("child_lineage_key") != lineage_key_for_run(run)
            or record.get("fork_identity_hash") != run.get("fork_identity_hash")
            or record.get("effective_boundary", {}).get("fork_genesis_event_id") != fork_event.get("id")):
        return {"status": "fail", "reason": "fork_lineage_record_context_mismatch"}
    return None


async def _build_divergence_report(run_id: str, tick: int,
                                   expected_events: list, expected_entities: dict,
                                   actual_events: list, actual_entities: dict) -> dict:
    expected_rejected = await db.rejected_proposals.find(
        {"run_id": run_id, "simulation_time": tick}, {"_id": 0},
    ).to_list(200)
    touched_union = sorted(set(
        [eid for event in expected_events for eid in event.get("touched_scope", [])]
        + [eid for event in actual_events for eid in event.get("touched_scope", [])]
    ))
    changed_state_paths = {}
    for entity_id in touched_union:
        expected_entity = expected_entities.get(entity_id, {})
        actual_entity = actual_entities.get(entity_id, {})
        differences = {}
        for key in set(expected_entity) | set(actual_entity):
            if expected_entity.get(key) != actual_entity.get(key):
                differences[key] = {
                    "expected": expected_entity.get(key),
                    "actual": actual_entity.get(key),
                }
        if differences:
            changed_state_paths[entity_id] = differences
    rng_refs = sorted(
        {f"people.{eid}.decision.{tick}" for eid in touched_union}
        | {f"animal.{eid}.decision.{tick}" for eid in touched_union}
    )
    return {
        "expected_accepted_events": _order_index_sequence(expected_events),
        "actual_accepted_events": _order_index_sequence(actual_events),
        "expected_rejected_reason_codes": [r.get("reason_code") for r in expected_rejected],
        "touched_scope_union": touched_union,
        "changed_state_paths": changed_state_paths,
        "expected_order_index_sequence": [e["order_index"] for e in expected_events],
        "actual_order_index_sequence": [e["order_index"] for e in actual_events],
        "deterministic_draw_references": rng_refs,
        "relevant_causal_parents": sorted(set(
            parent_id for event in expected_events + actual_events
            for parent_id in event.get("causal_parent_event_ids", [])
        )),
    }


async def verify_replay(run_id: str):
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise ValueError("run not found")

    genesis_tick = run.get("genesis_tick", 0)
    lineage_key = lineage_key_for_run(run)
    frames = await db.commit_frames.find(
        {"run_id": run_id}, {"_id": 0},
    ).sort("tick", 1).to_list(None)
    all_events = await db.accepted_events.find(
        {"run_id": run_id}, {"_id": 0},
    ).sort([("simulation_time", 1), ("order_index", 1)]).to_list(None)
    events_by_tick = _events_by_tick(all_events)

    if run.get("genesis_kind", "world") == "fork":
        try:
            fork_event = _fork_genesis_event(run, all_events)
        except ForkContractError as exc:
            return {"status": "fail", "reason": "fork_genesis_invalid", "detail": str(exc)}
        fork_failure = _verify_fork_genesis(run, fork_event)
        if fork_failure:
            return fork_failure
        lineage_failure = await _verify_fork_lineage_record(run, fork_event)
        if lineage_failure:
            return lineage_failure

    entities = {}
    prior_hash = None
    frames_by_tick = {frame["tick"]: frame for frame in frames}
    expected_ticks = range(genesis_tick, run["current_tick"] + 1)
    for tick in expected_ticks:
        frame = frames_by_tick.get(tick)
        if not frame:
            return {"status": "fail", "diverged_at_tick": tick, "reason": "frame_missing"}
        tick_events = events_by_tick.get(tick, [])
        for event in tick_events:
            apply_mutation(entities, copy.deepcopy(event["mutation"]))
        recomputed = _recomputed_frame_hash(
            run, entities, tick, lineage_key, prior_hash, tick_events,
        )
        if recomputed != frame["ending_state_hash"]:
            return {
                "status": "fail", "diverged_at_tick": tick,
                "reason": "genesis_hash_mismatch" if tick == genesis_tick else "hash_mismatch",
                "expected_hash": frame["ending_state_hash"],
                "actual_hash": recomputed,
                "accepted_events_this_tick": _order_index_sequence(tick_events),
            }
        prior_hash = recomputed

    return {
        "status": "pass",
        "verified_ticks": run["current_tick"] - genesis_tick,
        "frames_checked": len(frames),
        "genesis_tick": genesis_tick,
        "genesis_kind": run.get("genesis_kind", "world"),
        "source_horizon": run.get("source_horizon"),
    }


async def verify_determinism(run_id: str):
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise ValueError("run not found")

    genesis_tick = run.get("genesis_tick", 0)
    genesis_kind = run.get("genesis_kind", "world")
    lineage_key = lineage_key_for_run(run)
    scenario = get_scenario(run["scenario_id"])
    frames = await db.commit_frames.find(
        {"run_id": run_id}, {"_id": 0},
    ).sort("tick", 1).to_list(None)
    original_hashes = {frame["tick"]: frame["ending_state_hash"] for frame in frames}
    all_events = await db.accepted_events.find(
        {"run_id": run_id}, {"_id": 0},
    ).sort([("simulation_time", 1), ("order_index", 1)]).to_list(None)
    original_events_by_tick = _events_by_tick(all_events)
    influences = await db.external_influences.find(
        {"run_id": run_id}, {"_id": 0},
    ).sort("simulation_time", 1).to_list(None)
    influences_by_tick = {}
    for influence in influences:
        influences_by_tick.setdefault(influence["simulation_time"], []).append(influence)

    shadow_run_id = "shadow-" + run_id
    external_anchor_ids = set()
    if genesis_kind == "fork":
        try:
            fork_event = _fork_genesis_event(run, all_events)
        except ForkContractError as exc:
            return {"status": "fail", "reason": "fork_genesis_invalid", "detail": str(exc)}
        fork_failure = _verify_fork_genesis(run, fork_event)
        if fork_failure:
            return fork_failure
        lineage_failure = await _verify_fork_lineage_record(run, fork_event)
        if lineage_failure:
            return lineage_failure
        shadow_entities = reconstruct_entities([fork_event])
        world = copy.deepcopy(fork_event["genesis_context"]["world_context"])
        terrain = world["terrain"]
        order_index = run["parent_next_order_index"]
        shadow_hash = run["child_genesis_state_hash"]
        shadow_events_by_tick = {genesis_tick: [copy.deepcopy(fork_event)]}
        external_anchor_ids = validate_external_anchor_manifest(
            run.get("external_causal_anchors", []),
        )
    else:
        world, shadow_entities, shadow_accepted, _rejected, order_index = build_genesis(
            run["seed"], scenario, lineage_key,
        )
        terrain = world["terrain"]
        shadow_hash = shadow_accepted[-1]["post_state_hash"] if shadow_accepted else None
        shadow_events_by_tick = {0: list(shadow_accepted)}

    original_entities = {}
    for event in original_events_by_tick.get(genesis_tick, []):
        apply_mutation(original_entities, copy.deepcopy(event["mutation"]))

    for influence in influences_by_tick.get(genesis_tick, []):
        proposal = build_intervention_proposal(
            influence["intervention_type"], influence["payload"], shadow_entities,
            genesis_tick, influence["id"],
        )
        if proposal:
            accepted, _rejected, order_index = run_commit_frame(
                shadow_entities, [DomainOutput(proposals=[proposal])], genesis_tick,
                lineage_key, shadow_run_id, order_index,
                f"shadow-ext-{influence['id']}",
            )
            if accepted:
                shadow_hash = accepted[-1]["post_state_hash"]
                shadow_events_by_tick.setdefault(genesis_tick, []).extend(accepted)

    if original_hashes.get(genesis_tick) != shadow_hash:
        report = await _build_divergence_report(
            run_id, genesis_tick,
            original_events_by_tick.get(genesis_tick, []), original_entities,
            shadow_events_by_tick.get(genesis_tick, []), shadow_entities,
        )
        return {
            "status": "fail", "diverged_at_tick": genesis_tick,
            "expected_hash": original_hashes.get(genesis_tick),
            "actual_hash": shadow_hash,
            "interventions_replayed": len(influences), **report,
        }

    rng = rng_for_run(run)
    for tick in range(genesis_tick + 1, run["current_tick"] + 1):
        for event in original_events_by_tick.get(tick, []):
            apply_mutation(original_entities, copy.deepcopy(event["mutation"]))

        valid_causal_ids = _valid_shadow_causal_ids(
            shadow_entities, external_anchor_ids,
        )
        accepted, _rejected, order_index, _diagnostics = run_tick(
            shadow_run_id, shadow_entities, terrain, tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_causal_ids,
        )
        shadow_events_by_tick[tick] = list(accepted)
        shadow_hash = (
            accepted[-1]["post_state_hash"] if accepted
            else _recomputed_frame_hash(run, shadow_entities, tick, lineage_key,
                                        shadow_hash, [])
        )

        for influence in influences_by_tick.get(tick, []):
            proposal = build_intervention_proposal(
                influence["intervention_type"], influence["payload"],
                shadow_entities, tick, influence["id"],
            )
            if proposal:
                intervention_events, _r, order_index = run_commit_frame(
                    shadow_entities, [DomainOutput(proposals=[proposal])], tick,
                    lineage_key, shadow_run_id, order_index,
                    f"shadow-ext-{influence['id']}",
                )
                if intervention_events:
                    shadow_hash = intervention_events[-1]["post_state_hash"]
                    shadow_events_by_tick[tick].extend(intervention_events)

        if original_hashes.get(tick) != shadow_hash:
            report = await _build_divergence_report(
                run_id, tick, original_events_by_tick.get(tick, []),
                original_entities, shadow_events_by_tick.get(tick, []),
                shadow_entities,
            )
            return {
                "status": "fail", "diverged_at_tick": tick,
                "expected_hash": original_hashes.get(tick),
                "actual_hash": shadow_hash,
                "interventions_replayed": len(influences), **report,
            }

    return {
        "status": "pass",
        "compared_ticks": len(original_hashes),
        "seed": run["seed"],
        "interventions_replayed": len(influences),
        "final_state_hash": original_hashes.get(run["current_tick"]),
        "genesis_tick": genesis_tick,
        "genesis_kind": genesis_kind,
    }
