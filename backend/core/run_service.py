"""DB-facing orchestration: create/load/step runs. All Mongo access lives
here; core.kernel stays pure and DB-free."""
import uuid
from datetime import datetime, timezone

from core.db import db
from core.rng import DeterministicRNG
from core.kernel import build_genesis, run_tick
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.retention_service import prune_old_rejections
from scenarios import get_scenario


def lineage_key_for(seed: str, engine_version: str = ENGINE_VERSION, schema_version: str = SCHEMA_VERSION) -> str:
    """Defaults to the CURRENT engine/schema constants (used at genesis
    time, when no run doc exists yet). Every other caller that already has
    a run doc MUST pass that run's OWN stored engine_version/schema_version
    - otherwise, if these constants are ever bumped in a later session, a
    LOADED older run would recompute a lineage_key that never matches what
    was actually used to produce its stored hashes, silently breaking
    replay/determinism for that run. This is what makes "load an existing
    run and continue/replay it" safe across engine version bumps."""
    return f"{seed}|{schema_version}|{engine_version}"


async def create_run(seed: str, scenario_id: str = "basic_survival"):
    scenario = get_scenario(scenario_id)
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    lineage_key = lineage_key_for(seed)
    world, entities, accepted, rejected, next_order = build_genesis(seed, scenario, lineage_key)

    for e in accepted:
        e["run_id"] = run_id
    for r in rejected:
        r["run_id"] = run_id

    ending_hash = accepted[-1]["post_state_hash"] if accepted else None

    run_doc = {
        "id": run_id,
        "seed": seed,
        "scenario_id": scenario_id,
        "scenario_name": scenario.name,
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "current_tick": 0,
        "next_order_index": next_order,
        "status": "paused",
        "last_state_hash": ending_hash,
        "width": world["width"],
        "height": world["height"],
        "terrain": world["terrain"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.kernel_runs.insert_one(dict(run_doc))
    if accepted:
        await db.accepted_events.insert_many([dict(e) for e in accepted])
    if rejected:
        await db.rejected_proposals.insert_many([dict(r) for r in rejected])

    ent_docs = []
    for eid, e in entities.items():
        d = dict(e)
        d["id"] = eid
        d["run_id"] = run_id
        ent_docs.append(d)
    if ent_docs:
        await db.entities.insert_many(ent_docs)

    await db.commit_frames.insert_one({
        "id": f"{run_id}-frame-genesis", "run_id": run_id, "tick": 0,
        "starting_state_hash": None, "ending_state_hash": ending_hash,
        "accepted_event_ids": [e["id"] for e in accepted],
        "rejected_proposal_ids": [r["id"] for r in rejected],
    })
    return await get_run(run_id)


async def get_run(run_id: str):
    return await db.kernel_runs.find_one({"id": run_id}, {"_id": 0})


async def list_runs():
    return await db.kernel_runs.find({}, {"_id": 0, "terrain": 0}).sort("created_at", -1).to_list(200)


async def load_entities(run_id: str) -> dict:
    docs = await db.entities.find({"run_id": run_id}, {"_id": 0}).to_list(5000)
    entities = {}
    for d in docs:
        eid = d.pop("id")
        d.pop("run_id", None)
        entities[eid] = d
    return entities


async def save_entities_delta(run_id: str, entities: dict, touched_ids: set):
    for eid in touched_ids:
        if eid in entities:
            doc = dict(entities[eid])
            doc["id"] = eid
            doc["run_id"] = run_id
            await db.entities.replace_one({"run_id": run_id, "id": eid}, doc, upsert=True)
        else:
            await db.entities.delete_one({"run_id": run_id, "id": eid})


async def step_run(run_id: str, n_ticks: int = 1):
    run = await get_run(run_id)
    if not run:
        raise ValueError("run not found")

    enabled_domains = get_scenario(run["scenario_id"]).enabled_domains
    entities = await load_entities(run_id)
    rng = DeterministicRNG(run["seed"])
    terrain = run["terrain"]
    order_index = run["next_order_index"]
    lineage_key = lineage_key_for(run["seed"], run.get("engine_version", ENGINE_VERSION), run.get("schema_version", SCHEMA_VERSION))
    frames_summary = []

    for _ in range(n_ticks):
        next_tick = run["current_tick"] + 1
        starting_hash = run["last_state_hash"]

        accepted, rejected, order_index, diagnostics = run_tick(
            run_id, entities, terrain, next_tick, rng, order_index, lineage_key, enabled_domains,
        )
        for e in accepted:
            e["run_id"] = run_id
        for r in rejected:
            r["run_id"] = run_id

        touched = set()
        for e in accepted:
            touched.update(e["mutation"].get("new_entities", {}).keys())
            touched.update(e["mutation"].get("entity_updates", {}).keys())
            touched.update(e["mutation"].get("removed_entities", []))

        ending_hash = accepted[-1]["post_state_hash"] if accepted else starting_hash

        if accepted:
            await db.accepted_events.insert_many([dict(e) for e in accepted])
        if rejected:
            await db.rejected_proposals.insert_many([dict(r) for r in rejected])
        for eid, diag in diagnostics.items():
            await db.activation_diagnostics.replace_one(
                {"run_id": run_id, "entity_id": eid},
                {"run_id": run_id, "entity_id": eid, "tick": next_tick, "diagnostics": diag},
                upsert=True,
            )
        await save_entities_delta(run_id, entities, touched)
        await db.commit_frames.insert_one({
            "id": f"{run_id}-frame-{next_tick}", "run_id": run_id, "tick": next_tick,
            "starting_state_hash": starting_hash, "ending_state_hash": ending_hash,
            "accepted_event_ids": [e["id"] for e in accepted],
            "rejected_proposal_ids": [r["id"] for r in rejected],
        })

        run["current_tick"] = next_tick
        run["last_state_hash"] = ending_hash
        frames_summary.append({
            "tick": next_tick, "accepted_count": len(accepted), "rejected_count": len(rejected),
            "ending_state_hash": ending_hash,
        })

    await db.kernel_runs.update_one({"id": run_id}, {"$set": {
        "current_tick": run["current_tick"], "last_state_hash": run["last_state_hash"],
        "next_order_index": order_index, "status": "running",
    }})
    await prune_old_rejections(run_id, run["current_tick"])
    return frames_summary


async def set_run_status(run_id: str, status: str):
    await db.kernel_runs.update_one({"id": run_id}, {"$set": {"status": status}})
