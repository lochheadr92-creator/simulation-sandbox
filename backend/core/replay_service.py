"""Replay & determinism verification.

Two distinct proofs, matching Verification Doctrine (Spec #32):

1. verify_replay: reapplies the RECORDED accepted-event mutations from
   genesis and checks every frame's stored ending_state_hash still matches.
   Proves storage/event-log integrity - no LLM, no re-simulation.

2. verify_determinism: creates a brand-new SHADOW run with the identical
   seed and re-runs the domains/commit-pipeline from genesis through the
   same number of ticks, then compares the full hash sequence against the
   original. Proves the doctrine's core claim: same seed + scenario +
   engine version => identical accepted events and identical state hashes.

Phase 4A addition: on a divergence, both functions now return a rich,
focused FIRST-DIVERGENCE report (expected/actual events, touched scope,
changed state paths, order-index/RNG-stream references, causal parents)
instead of a bare hash mismatch - see _build_divergence_report(). This is
purely diagnostic; it never changes what "pass"/"fail" means and never
becomes a second source of truth for replay correctness.
"""
from core.db import db
from core.hashing import canonical_hash
from core.mutations import apply_mutation, snapshot_for_hash
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.run_service import lineage_key_for
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.commit_pipeline import run_commit_frame
from core.interventions import build_intervention_proposal
from domains.base import DomainOutput
from scenarios import get_scenario


def _lineage_key_for_run(run: dict) -> str:
    return lineage_key_for(run["seed"], run.get("engine_version", ENGINE_VERSION), run.get("schema_version", SCHEMA_VERSION))


def _order_index_sequence(events: list) -> list:
    return [{"entity_id": ev["entity_id"], "event_type": ev["event_type"],
              "order_index": ev["order_index"], "event_id": ev["id"]} for ev in events]


async def _build_divergence_report(run_id: str, tick: int, expected_events: list, expected_entities: dict,
                                    actual_events: list, actual_entities: dict) -> dict:
    """A focused diff at the FIRST divergent tick - not a full world dump."""
    expected_rejected = await db.rejected_proposals.find(
        {"run_id": run_id, "simulation_time": tick}, {"_id": 0},
    ).to_list(200)

    touched_union = sorted(set(
        [eid for ev in expected_events for eid in ev.get("touched_scope", [])]
        + [eid for ev in actual_events for eid in ev.get("touched_scope", [])]
    ))

    changed_state_paths = {}
    for eid in touched_union:
        exp_e = expected_entities.get(eid, {})
        act_e = actual_entities.get(eid, {})
        diffs = {}
        for key in set(exp_e.keys()) | set(act_e.keys()):
            if exp_e.get(key) != act_e.get(key):
                diffs[key] = {"expected": exp_e.get(key), "actual": act_e.get(key)}
        if diffs:
            changed_state_paths[eid] = diffs

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
            pid for ev in expected_events + actual_events for pid in ev.get("causal_parent_event_ids", [])
        )),
    }


async def verify_replay(run_id: str):
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise ValueError("run not found")

    lineage_key = _lineage_key_for_run(run)
    frames = await db.commit_frames.find({"run_id": run_id}, {"_id": 0}).sort("tick", 1).to_list(100000)
    all_events = await db.accepted_events.find({"run_id": run_id}, {"_id": 0}).sort("order_index", 1).to_list(200000)
    events_by_tick = {}
    for ev in all_events:
        events_by_tick.setdefault(ev["simulation_time"], []).append(ev)

    entities = {}
    for ev in events_by_tick.get(0, []):
        apply_mutation(entities, ev["mutation"])

    genesis_hash = canonical_hash(snapshot_for_hash(entities, 0, lineage_key))
    genesis_frame = next((f for f in frames if f["tick"] == 0), None)
    if genesis_frame and genesis_frame["ending_state_hash"] and genesis_hash != genesis_frame["ending_state_hash"]:
        return {
            "status": "fail", "diverged_at_tick": 0, "reason": "genesis_hash_mismatch",
            "expected_hash": genesis_frame["ending_state_hash"], "actual_hash": genesis_hash,
            "accepted_events_this_tick": _order_index_sequence(events_by_tick.get(0, [])),
            "note": ("verify_replay recomputes hashes by replaying stored mutations only (no independent "
                     "resimulation); for a full expected-vs-actual state/RNG diff use verify_determinism."),
        }

    for frame in frames:
        tick = frame["tick"]
        if tick == 0:
            continue
        for ev in events_by_tick.get(tick, []):
            apply_mutation(entities, ev["mutation"])
        recomputed = canonical_hash(snapshot_for_hash(entities, tick, lineage_key))
        if recomputed != frame["ending_state_hash"]:
            return {
                "status": "fail", "diverged_at_tick": tick, "reason": "hash_mismatch",
                "expected_hash": frame["ending_state_hash"], "actual_hash": recomputed,
                "accepted_events_this_tick": _order_index_sequence(events_by_tick.get(tick, [])),
                "note": ("verify_replay recomputes hashes by replaying stored mutations only (no independent "
                         "resimulation); for a full expected-vs-actual state/RNG diff use verify_determinism."),
            }

    return {"status": "pass", "verified_ticks": run["current_tick"], "frames_checked": len(frames)}


async def verify_determinism(run_id: str):
    """Re-simulates a shadow run from the same seed AND replays the same
    recorded external interventions at their original ticks, then compares
    the full hash sequence tick-by-tick (stopping at the FIRST divergence,
    if any, to build a focused diagnostic report rather than a full dump).
    Proves the doctrine's full claim: same seed + scenario + engine version
    + external interventions => identical accepted events and hashes."""
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise ValueError("run not found")

    original_frames = await db.commit_frames.find({"run_id": run_id}, {"_id": 0}).sort("tick", 1).to_list(100000)
    original_hashes = {f["tick"]: f["ending_state_hash"] for f in original_frames}

    all_original_events = await db.accepted_events.find({"run_id": run_id}, {"_id": 0}).sort("order_index", 1).to_list(200000)
    original_events_by_tick = {}
    for ev in all_original_events:
        original_events_by_tick.setdefault(ev["simulation_time"], []).append(ev)

    influences = await db.external_influences.find({"run_id": run_id}, {"_id": 0}).sort("simulation_time", 1).to_list(10000)
    influences_by_tick = {}
    for infl in influences:
        influences_by_tick.setdefault(infl["simulation_time"], []).append(infl)

    lineage_key = _lineage_key_for_run(run)
    scenario = get_scenario(run["scenario_id"])
    shadow_run_id = "shadow-" + run_id
    world, shadow_entities, shadow_accepted, _rej, order_index = build_genesis(run["seed"], scenario, lineage_key)
    shadow_hashes = {0: shadow_accepted[-1]["post_state_hash"] if shadow_accepted else None}
    shadow_events_by_tick = {0: list(shadow_accepted)}

    original_entities = {}
    for ev in original_events_by_tick.get(0, []):
        apply_mutation(original_entities, ev["mutation"])

    for infl in influences_by_tick.get(0, []):
        proposal = build_intervention_proposal(infl["intervention_type"], infl["payload"], shadow_entities, 0, infl["id"])
        if proposal:
            acc, _r, order_index = run_commit_frame(
                shadow_entities, [DomainOutput(proposals=[proposal])], 0, lineage_key,
                shadow_run_id, order_index, f"shadow-ext-{infl['id']}",
            )
            if acc:
                shadow_hashes[0] = acc[-1]["post_state_hash"]
                shadow_events_by_tick[0].extend(acc)

    if original_hashes.get(0) != shadow_hashes.get(0):
        report = await _build_divergence_report(run_id, 0, original_events_by_tick.get(0, []), original_entities,
                                                  shadow_events_by_tick.get(0, []), shadow_entities)
        return {"status": "fail", "diverged_at_tick": 0, "expected_hash": original_hashes.get(0),
                "actual_hash": shadow_hashes.get(0), "interventions_replayed": len(influences), **report}

    rng = DeterministicRNG(run["seed"])
    terrain = world["terrain"]
    for tick in range(1, run["current_tick"] + 1):
        for ev in original_events_by_tick.get(tick, []):
            apply_mutation(original_entities, ev["mutation"])

        accepted, _rejected, order_index, _diag = run_tick(
            shadow_run_id, shadow_entities, terrain, tick, rng, order_index, lineage_key, scenario.enabled_domains,
        )
        shadow_hashes[tick] = accepted[-1]["post_state_hash"] if accepted else shadow_hashes.get(tick - 1)
        shadow_events_by_tick[tick] = list(accepted)

        for infl in influences_by_tick.get(tick, []):
            proposal = build_intervention_proposal(infl["intervention_type"], infl["payload"], shadow_entities, tick, infl["id"])
            if proposal:
                acc, _r, order_index = run_commit_frame(
                    shadow_entities, [DomainOutput(proposals=[proposal])], tick, lineage_key,
                    shadow_run_id, order_index, f"shadow-ext-{infl['id']}",
                )
                if acc:
                    shadow_hashes[tick] = acc[-1]["post_state_hash"]
                    shadow_events_by_tick[tick].extend(acc)

        if original_hashes.get(tick) != shadow_hashes.get(tick):
            report = await _build_divergence_report(run_id, tick, original_events_by_tick.get(tick, []), original_entities,
                                                      shadow_events_by_tick.get(tick, []), shadow_entities)
            return {"status": "fail", "diverged_at_tick": tick, "expected_hash": original_hashes.get(tick),
                    "actual_hash": shadow_hashes.get(tick), "interventions_replayed": len(influences), **report}

    final_tick = run["current_tick"]
    return {
        "status": "pass",
        "compared_ticks": len(original_hashes),
        "seed": run["seed"],
        "interventions_replayed": len(influences),
        "final_state_hash": original_hashes.get(final_tick),
    }
