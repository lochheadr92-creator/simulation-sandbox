import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.db import db
from core.constants import time_phase
from core.commit_pipeline import run_commit_frame
from core.interventions import build_intervention_proposal
from core.run_service import (
    create_run, get_run, list_runs, load_entities, save_entities_delta,
    step_run, set_run_status, lineage_key_for,
)
from core.replay_service import verify_replay, verify_determinism
from domains.base import DomainOutput
from scenarios import list_scenarios, get_scenario

router = APIRouter()


# ---------- request models ----------

class CreateRunRequest(BaseModel):
    seed: Optional[str] = None
    scenario_id: str = "basic_survival"


class StepRequest(BaseModel):
    ticks: int = 1


class InterventionRequest(BaseModel):
    type: str
    payload: dict = {}


# ---------- scenarios ----------

@router.get("/scenarios")
async def get_scenarios():
    return {"scenarios": [
        {"id": s.id, "name": s.name, "description": s.description,
         "enabled_domains": s.enabled_domains, "presentation": s.presentation}
        for s in list_scenarios()
    ]}


# ---------- runs ----------

@router.post("/runs")
async def api_create_run(body: CreateRunRequest):
    seed = body.seed or uuid.uuid4().hex[:10]
    try:
        get_scenario(body.scenario_id)
    except KeyError:
        raise HTTPException(400, "unknown scenario_id")
    run = await create_run(seed, body.scenario_id)
    return run


@router.get("/runs")
async def api_list_runs():
    return {"runs": await list_runs()}


@router.get("/runs/{run_id}")
async def api_get_run(run_id: str):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    run = dict(run)
    run.pop("terrain", None)
    return run


@router.post("/runs/{run_id}/step")
async def api_step_run(run_id: str, body: StepRequest):
    try:
        frames = await step_run(run_id, max(1, min(body.ticks, 50)))
    except ValueError:
        raise HTTPException(404, "run not found")
    return {"frames": frames}


@router.post("/runs/{run_id}/pause")
async def api_pause_run(run_id: str):
    await set_run_status(run_id, "paused")
    return {"status": "paused"}


@router.get("/runs/{run_id}/state")
async def api_get_state(run_id: str):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    entities = await db.entities.find({"run_id": run_id}, {"_id": 0, "run_id": 0}).to_list(5000)
    return {
        "id": run["id"], "seed": run["seed"], "scenario_id": run["scenario_id"],
        "scenario_name": run.get("scenario_name"),
        "current_tick": run["current_tick"], "time_phase": time_phase(run["current_tick"]),
        "status": run["status"], "last_state_hash": run["last_state_hash"],
        "width": run["width"], "height": run["height"], "terrain": run["terrain"],
        "entities": entities,
    }


@router.get("/runs/{run_id}/events")
async def api_get_events(run_id: str, limit: int = 150):
    events = await db.accepted_events.find({"run_id": run_id}, {"_id": 0}).sort("order_index", -1).to_list(limit)
    return {"events": events}


@router.get("/runs/{run_id}/rejections")
async def api_get_rejections(run_id: str, limit: int = 150):
    rejections = await db.rejected_proposals.find({"run_id": run_id}, {"_id": 0}).sort("simulation_time", -1).to_list(limit)
    return {"rejections": rejections}


@router.get("/runs/{run_id}/entities/{entity_id}/causal")
async def api_get_causal(run_id: str, entity_id: str):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    entity = await db.entities.find_one({"run_id": run_id, "id": entity_id}, {"_id": 0, "run_id": 0})
    if not entity:
        raise HTTPException(404, "entity not found")

    diag = await db.activation_diagnostics.find_one({"run_id": run_id, "entity_id": entity_id}, {"_id": 0})
    accepted_events = await db.accepted_events.find(
        {"run_id": run_id, "entity_id": entity_id}, {"_id": 0},
    ).sort("order_index", -1).to_list(20)
    rejected_events = await db.rejected_proposals.find(
        {"run_id": run_id, "entity_id": entity_id}, {"_id": 0},
    ).sort("simulation_time", -1).to_list(20)

    chain = []
    if accepted_events:
        current = accepted_events[0]
        visited = set()
        depth = 0
        while current and depth < 12:
            chain.append({
                "event_id": current["id"], "event_type": current["event_type"],
                "simulation_time": current["simulation_time"], "explanation": current.get("explanation", ""),
            })
            visited.add(current["id"])
            parents = current.get("causal_parent_event_ids", [])
            if not parents or parents[0] in visited:
                break
            current = await db.accepted_events.find_one({"run_id": run_id, "id": parents[0]}, {"_id": 0})
            depth += 1

    action_history = []
    for ev in accepted_events[:15]:
        upd = ev.get("mutation", {}).get("entity_updates", {}).get(entity_id, {})
        act = upd.get("action")
        if act:
            action_history.append({
                "tick": ev["simulation_time"], "event_type": ev["event_type"],
                "action_type": act.get("type"), "action_status": act.get("status"),
                "ticks_spent": act.get("ticks_spent"), "explanation": ev.get("explanation", ""),
            })

    knowledge = entity.get("knowledge")
    knowledge_summary = None
    if knowledge:
        knowledge_summary = {
            "explored_tiles": len(knowledge.get("known_tiles", [])),
            "known_water_tiles": len(knowledge.get("known_water_tiles", [])),
            "known_trees": len(knowledge.get("known_trees", {})),
            "known_shelters": len(knowledge.get("known_shelters", {})),
        }

    return {
        "entity": {"id": entity_id, **entity},
        "diagnostics": diag["diagnostics"] if diag else None,
        "accepted_action": accepted_events[0] if accepted_events else None,
        "recent_accepted_events": accepted_events,
        "recent_rejected_proposals": rejected_events,
        "causal_chain": chain,
        "action_history": action_history,
        "knowledge_summary": knowledge_summary,
    }


# ---------- interventions ----------

@router.post("/runs/{run_id}/interventions")
async def api_submit_intervention(run_id: str, body: InterventionRequest):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")

    entities = await load_entities(run_id)
    influence_id = f"infl-{uuid.uuid4().hex[:10]}"
    await db.external_influences.insert_one({
        "id": influence_id, "run_id": run_id, "intervention_type": body.type,
        "payload": body.payload, "simulation_time": run["current_tick"],
    })

    proposal = build_intervention_proposal(body.type, body.payload, entities, run["current_tick"], influence_id)
    if proposal is None:
        raise HTTPException(400, "invalid intervention type or payload")

    lineage_key = lineage_key_for(run["seed"])
    accepted, rejected, next_order = run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], run["current_tick"], lineage_key,
        run_id, run["next_order_index"], f"{run_id}-ext-{influence_id}",
    )
    for e in accepted:
        e["run_id"] = run_id
    for r in rejected:
        r["run_id"] = run_id

    touched = set()
    for e in accepted:
        touched.update(e["mutation"].get("new_entities", {}).keys())
        touched.update(e["mutation"].get("entity_updates", {}).keys())

    ending_hash = accepted[-1]["post_state_hash"] if accepted else run["last_state_hash"]
    if accepted:
        await db.accepted_events.insert_many([dict(e) for e in accepted])
    if rejected:
        await db.rejected_proposals.insert_many([dict(r) for r in rejected])
    await save_entities_delta(run_id, entities, touched)
    await db.kernel_runs.update_one({"id": run_id}, {"$set": {
        "last_state_hash": ending_hash, "next_order_index": next_order,
    }})
    # Keep the commit_frame's ending_state_hash for this tick in sync so that
    # replay/determinism verification sees the post-intervention hash too.
    await db.commit_frames.update_one(
        {"run_id": run_id, "tick": run["current_tick"]},
        {"$set": {"ending_state_hash": ending_hash},
         "$setOnInsert": {"id": f"{run_id}-frame-{run['current_tick']}", "starting_state_hash": None,
                           "accepted_event_ids": [], "rejected_proposal_ids": []}},
        upsert=True,
    )

    return {"accepted": accepted, "rejected": rejected, "influence_id": influence_id}


# ---------- replay / determinism ----------

@router.post("/runs/{run_id}/replay/verify")
async def api_verify_replay(run_id: str):
    try:
        return await verify_replay(run_id)
    except ValueError:
        raise HTTPException(404, "run not found")


@router.post("/runs/{run_id}/replay/determinism")
async def api_verify_determinism(run_id: str):
    try:
        return await verify_determinism(run_id)
    except ValueError:
        raise HTTPException(404, "run not found")
