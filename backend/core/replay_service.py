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
"""
from core.db import db
from core.hashing import canonical_hash
from core.mutations import apply_mutation, snapshot_for_hash
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.run_service import lineage_key_for
from core.commit_pipeline import run_commit_frame
from core.interventions import build_intervention_proposal
from domains.base import DomainOutput
from scenarios import get_scenario


async def verify_replay(run_id: str):
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise ValueError("run not found")

    lineage_key = lineage_key_for(run["seed"])
    frames = await db.commit_frames.find({"run_id": run_id}, {"_id": 0}).sort("tick", 1).to_list(100000)
    entities = {}

    genesis_events = await db.accepted_events.find(
        {"run_id": run_id, "event_family": "genesis"}, {"_id": 0},
    ).sort("order_index", 1).to_list(10000)
    for ev in genesis_events:
        apply_mutation(entities, ev["mutation"])

    genesis_hash = canonical_hash(snapshot_for_hash(entities, 0, lineage_key))
    genesis_frame = next((f for f in frames if f["tick"] == 0), None)
    if genesis_frame and genesis_frame["ending_state_hash"] and genesis_hash != genesis_frame["ending_state_hash"]:
        return {"status": "fail", "diverged_at_tick": 0, "reason": "genesis_hash_mismatch"}

    for frame in frames:
        tick = frame["tick"]
        if tick == 0:
            continue
        events = await db.accepted_events.find(
            {"run_id": run_id, "simulation_time": tick}, {"_id": 0},
        ).sort("order_index", 1).to_list(10000)
        for ev in events:
            apply_mutation(entities, ev["mutation"])
        recomputed = canonical_hash(snapshot_for_hash(entities, tick, lineage_key))
        if recomputed != frame["ending_state_hash"]:
            return {
                "status": "fail", "diverged_at_tick": tick, "reason": "hash_mismatch",
                "expected": frame["ending_state_hash"], "recomputed": recomputed,
            }

    return {"status": "pass", "verified_ticks": run["current_tick"], "frames_checked": len(frames)}


async def verify_determinism(run_id: str):
    """Re-simulates a shadow run from the same seed AND replays the same
    recorded external interventions at their original ticks, then compares
    the full hash sequence. This proves the doctrine's full claim: same
    seed + scenario + engine version + external interventions => identical
    accepted events and identical state hashes."""
    run = await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise ValueError("run not found")

    original_frames = await db.commit_frames.find({"run_id": run_id}, {"_id": 0}).sort("tick", 1).to_list(100000)
    original_hashes = {f["tick"]: f["ending_state_hash"] for f in original_frames}

    influences = await db.external_influences.find({"run_id": run_id}, {"_id": 0}).sort("simulation_time", 1).to_list(10000)
    influences_by_tick = {}
    for infl in influences:
        influences_by_tick.setdefault(infl["simulation_time"], []).append(infl)

    lineage_key = lineage_key_for(run["seed"])
    scenario = get_scenario(run["scenario_id"])
    shadow_run_id = "shadow-" + run_id
    world, shadow_entities, shadow_accepted, _rej, order_index = build_genesis(run["seed"], scenario, lineage_key)
    shadow_hashes = {0: shadow_accepted[-1]["post_state_hash"] if shadow_accepted else None}

    for infl in influences_by_tick.get(0, []):
        proposal = build_intervention_proposal(infl["intervention_type"], infl["payload"], shadow_entities, 0, infl["id"])
        if proposal:
            acc, _r, order_index = run_commit_frame(
                shadow_entities, [DomainOutput(proposals=[proposal])], 0, lineage_key,
                shadow_run_id, order_index, f"shadow-ext-{infl['id']}",
            )
            if acc:
                shadow_hashes[0] = acc[-1]["post_state_hash"]

    rng = DeterministicRNG(run["seed"])
    terrain = world["terrain"]
    for tick in range(1, run["current_tick"] + 1):
        accepted, _rejected, order_index, _diag = run_tick(
            shadow_run_id, shadow_entities, terrain, tick, rng, order_index, lineage_key, scenario.enabled_domains,
        )
        shadow_hashes[tick] = accepted[-1]["post_state_hash"] if accepted else shadow_hashes.get(tick - 1)

        for infl in influences_by_tick.get(tick, []):
            proposal = build_intervention_proposal(infl["intervention_type"], infl["payload"], shadow_entities, tick, infl["id"])
            if proposal:
                acc, _r, order_index = run_commit_frame(
                    shadow_entities, [DomainOutput(proposals=[proposal])], tick, lineage_key,
                    shadow_run_id, order_index, f"shadow-ext-{infl['id']}",
                )
                if acc:
                    shadow_hashes[tick] = acc[-1]["post_state_hash"]

    for tick, orig_hash in original_hashes.items():
        shadow_hash = shadow_hashes.get(tick)
        if orig_hash != shadow_hash:
            return {
                "status": "fail", "diverged_at_tick": tick,
                "original_hash": orig_hash, "shadow_hash": shadow_hash,
                "interventions_replayed": len(influences),
            }

    final_tick = run["current_tick"]
    return {
        "status": "pass",
        "compared_ticks": len(original_hashes),
        "seed": run["seed"],
        "interventions_replayed": len(influences),
        "final_state_hash": original_hashes.get(final_tick),
    }
