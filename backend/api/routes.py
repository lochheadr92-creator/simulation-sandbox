import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.db import db
from core.constants import time_phase, RECENT_HORIZON_TICKS
from core.commit_pipeline import run_commit_frame
from core.hashing import canonical_hash
from core.interventions import build_intervention_proposal
from core.run_service import (
    create_run, get_run, list_runs, load_entities, save_entities_delta,
    step_run, set_run_status, fork_run, lineage_key_for_run,
    ForkNotFound, ForkConflict, ForkCompatibilityError, ForkIntegrityError,
    TransactionUnavailable,
    ConcurrentModification, CommitStatusUnknown, FrameCapacityError,
    RunIntegrityMismatch, RunQuarantined, RunUnderMaintenance,
    FramePersistenceError, RunVersionCompatibilityError,
)
from core.replay_service import verify_replay, verify_determinism
from core import history_service
from domains.base import DomainOutput
from domains.lifecycle_domain import lifecycle_diag_key
from api.age_projection import project_entity_age, project_entity_ages
from api.cognitive_projection import build_cognitive_projection
from api.living_agent_projection import build_living_agent_projection
from api.association_projection import build_association_projection
from api.group_state_projection import build_group_state_projection
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_state_contracts import GROUP_STATE_REGISTRY_ID
from scenarios import list_scenarios, get_scenario

router = APIRouter()


# ---------- request models ----------

class CreateRunRequest(BaseModel):
    seed: Optional[str] = None
    scenario_id: str = "basic_survival"


class StepRequest(BaseModel):
    ticks: int = 1


class ForkRunRequest(BaseModel):
    fork_tick: int
    branch_key: str = "default"
    expected_boundary_event_id: Optional[str] = None
    expected_forked_from_state_hash: Optional[str] = None


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


@router.post("/runs/{run_id}/fork")
async def api_fork_run(run_id: str, body: ForkRunRequest):
    try:
        return await fork_run(
            run_id,
            body.fork_tick,
            branch_key=body.branch_key,
            expected_boundary_event_id=body.expected_boundary_event_id,
            expected_forked_from_state_hash=body.expected_forked_from_state_hash,
        )
    except ForkNotFound as exc:
        raise HTTPException(404, str(exc))
    except ForkConflict as exc:
        raise HTTPException(409, str(exc))
    except (ForkCompatibilityError, ForkIntegrityError) as exc:
        raise HTTPException(412, str(exc))
    except TransactionUnavailable as exc:
        raise HTTPException(503, str(exc))


@router.post("/runs/{run_id}/step")
async def api_step_run(run_id: str, body: StepRequest):
    try:
        frames = await step_run(run_id, max(1, min(body.ticks, 50)))
    except RunVersionCompatibilityError as exc:
        raise HTTPException(409, {
            "error_code": "RUN_VERSION_UNSUPPORTED",
            "detail": str(exc),
        })
    except ValueError:
        raise HTTPException(404, "run not found")
    except ConcurrentModification as exc:
        raise HTTPException(409, {
            "error_code": "CONCURRENT_MODIFICATION",
            "detail": str(exc),
        })
    except RunUnderMaintenance as exc:
        raise HTTPException(409, {
            "error_code": "RUN_UNDER_MAINTENANCE",
            "detail": str(exc),
        })
    except RunQuarantined as exc:
        raise HTTPException(409, {
            "error_code": "RUN_QUARANTINED",
            "detail": str(exc),
        })
    except RunIntegrityMismatch as exc:
        raise HTTPException(409, {
            "error_code": "RUN_INTEGRITY_MISMATCH",
            "detail": str(exc),
        })
    except FrameCapacityError as exc:
        raise HTTPException(413, {
            "error_code": getattr(exc, "code", "FRAME_CAPACITY_EXCEEDED"),
            "detail": str(exc),
        })
    except CommitStatusUnknown as exc:
        raise HTTPException(503, {
            "error_code": "COMMIT_STATUS_UNKNOWN",
            "detail": str(exc),
        })
    except TransactionUnavailable as exc:
        raise HTTPException(503, {
            "error_code": "TRANSACTION_UNAVAILABLE",
            "detail": str(exc),
        })
    except FramePersistenceError as exc:
        raise HTTPException(500, {
            "error_code": getattr(exc, "code", "DB_TX_FAILURE"),
            "detail": str(exc),
        })
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
        # Derived age_years added on the way out only; age_ticks stays the
        # stored truth and is untouched. See api/age_projection.py.
        "entities": project_entity_ages(entities),
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
    entity = project_entity_age(entity)

    diag = await db.activation_diagnostics.find_one({"run_id": run_id, "entity_id": entity_id}, {"_id": 0})
    lifecycle_diag = await db.activation_diagnostics.find_one(
        {"run_id": run_id, "entity_id": lifecycle_diag_key(entity_id)}, {"_id": 0},
    )
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
            next_event = await db.accepted_events.find_one(
                {"run_id": run_id, "id": parents[0]}, {"_id": 0},
            )
            if not next_event:
                anchor = next((
                    item for item in run.get("external_causal_anchors", [])
                    if item.get("event_id") == parents[0]
                ), None)
                if anchor:
                    chain.append({
                        "event_id": anchor["event_id"],
                        "event_type": anchor["event_type"],
                        "simulation_time": anchor["simulation_time"],
                        "explanation": "validated external causal anchor from parent lineage",
                        "external_parent_lineage": anchor["parent_lineage_key"],
                    })
                break
            current = next_event
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
            "schema_version": knowledge.get("schema_version"),
            "explored_tiles": len(knowledge.get("known_tiles", [])),
            "known_water_tiles": len(knowledge.get("known_water_tiles", [])),
            "known_trees": len(knowledge.get("known_trees", {})),
            "known_shelters": len(knowledge.get("known_shelters", {})),
            "known_carcasses": len(knowledge.get("known_carcasses", {})),
            "known_animals": len(knowledge.get("known_animals", {})),
            "known_people": len(knowledge.get("known_people", {})),
            "known_dangers": len(knowledge.get("known_dangers", {})),
            "fact_count": len(knowledge.get("facts", {})),
            "note": "personal knowledge — not current world truth; last-known positions may be stale",
        }

    return {
        "entity": {"id": entity_id, **entity},
        "diagnostics": diag["diagnostics"] if diag else None,
        "lifecycle_diagnostics": lifecycle_diag["diagnostics"] if lifecycle_diag else None,
        "accepted_action": accepted_events[0] if accepted_events else None,
        "recent_accepted_events": accepted_events,
        "recent_rejected_proposals": rejected_events,
        "causal_chain": chain,
        "action_history": action_history,
        "knowledge_summary": knowledge_summary,
    }


@router.get("/runs/{run_id}/entities/{entity_id}/cognitive-projection")
async def api_get_cognitive_projection(run_id: str, entity_id: str):
    """Return a bounded, observer-specific display projection.

    It is deliberately separate from the state endpoint: this payload contains
    only the selected person's cognitive view and never writes canonical state.
    """
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    observer = await db.entities.find_one({"run_id": run_id, "id": entity_id}, {"_id": 0, "run_id": 0})
    if not observer:
        raise HTTPException(404, "entity not found")
    if observer.get("type") != "person":
        raise HTTPException(400, "cognitive projection requires a person observer")

    entities = await db.entities.find({"run_id": run_id}, {"_id": 0, "run_id": 0}).to_list(5000)
    entity_map = {entity["id"]: entity for entity in entities}
    diag = await db.activation_diagnostics.find_one(
        {"run_id": run_id, "entity_id": entity_id}, {"_id": 0},
    )
    return build_cognitive_projection(
        observer, entity_map, run["terrain"], run["current_tick"],
        diagnostics=diag.get("diagnostics") if diag else None,
    )


@router.get("/runs/{run_id}/entities/{entity_id}/living-agent")
async def api_get_living_agent_projection(run_id: str, entity_id: str):
    """Return a bounded read-only explanation of one person's owned state."""
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    entity = await db.entities.find_one(
        {"run_id": run_id, "id": entity_id}, {"_id": 0, "run_id": 0},
    )
    if not entity:
        raise HTTPException(404, "entity not found")
    if entity.get("type") != "person":
        raise HTTPException(400, "living-agent projection requires a person")
    diag = await db.activation_diagnostics.find_one(
        {"run_id": run_id, "entity_id": entity_id}, {"_id": 0},
    )
    return build_living_agent_projection(
        entity, run["current_tick"],
        diagnostics=diag.get("diagnostics") if diag else None,
    )


@router.get("/runs/{run_id}/associations")
async def api_get_association_projection(run_id: str):
    """Return bounded read-only group recognition and causal explanations."""
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    registry = await db.entities.find_one(
        {"run_id": run_id, "id": ASSOCIATION_REGISTRY_ID},
        {"_id": 0, "run_id": 0},
    )
    if not registry:
        raise HTTPException(404, "association registry not found")
    people = await db.entities.find(
        {"run_id": run_id, "type": "person", "alive": {"$ne": False}},
        {"_id": 0, "id": 1},
    ).to_list(5000)
    diag = await db.activation_diagnostics.find_one(
        {"run_id": run_id, "entity_id": ASSOCIATION_REGISTRY_ID}, {"_id": 0},
    )
    return build_association_projection(
        registry,
        people=[person["id"] for person in people],
        diagnostics=diag.get("diagnostics") if diag else None,
    )


@router.get("/runs/{run_id}/group-state")
async def api_get_group_state_projection(run_id: str):
    """Return bounded read-only shared-group state and support provenance."""
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    registry = await db.entities.find_one(
        {"run_id": run_id, "id": GROUP_STATE_REGISTRY_ID},
        {"_id": 0, "run_id": 0},
    )
    if not registry:
        raise HTTPException(404, "group state registry not found")
    diag = await db.activation_diagnostics.find_one(
        {"run_id": run_id, "entity_id": GROUP_STATE_REGISTRY_ID}, {"_id": 0},
    )
    return build_group_state_projection(
        registry,
        diagnostics=diag.get("diagnostics") if diag else None,
    )


# ---------- history: timeline, milestones, provenance, tile history (Phase 4A) ----------

@router.get("/runs/{run_id}/timeline")
async def api_get_timeline(run_id: str, limit: int = 300, entity_id: Optional[str] = None, milestone_only: bool = False):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    events = await history_service.chronological_events_for_run(run_id)
    milestones = history_service.classify_milestones(events)
    timeline = history_service.build_timeline(events, milestones)
    if entity_id:
        timeline = [t for t in timeline if t["entity_id"] == entity_id or entity_id in t["touched_scope"]]
    if milestone_only:
        timeline = [t for t in timeline if t["milestones"]]
    timeline = list(reversed(timeline))[:limit]
    return {"timeline": timeline, "recent_horizon_ticks": RECENT_HORIZON_TICKS, "total_events_in_run": len(events)}


@router.get("/runs/{run_id}/milestones")
async def api_get_milestones(run_id: str):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    events = await history_service.chronological_events_for_run(run_id)
    milestones = history_service.classify_milestones(events)
    return {"milestones": list(reversed(milestones))}


@router.get("/runs/{run_id}/entities/{entity_id}/provenance")
async def api_get_provenance(run_id: str, entity_id: str):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    entity = await db.entities.find_one({"run_id": run_id, "id": entity_id}, {"_id": 0, "run_id": 0})
    if not entity:
        raise HTTPException(404, "entity not found")
    events = await history_service.events_for_entity(run_id, entity_id)
    return history_service.provenance_for_entity(entity_id, entity, events)


@router.get("/runs/{run_id}/tiles/{x}/{y}/history")
async def api_get_tile_history(run_id: str, x: int, y: int, limit: int = 50):
    run = await get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    events = await history_service.tile_history(run_id, x, y, limit=limit)
    return {"x": x, "y": y, "events": events,
            "note": "projection over accepted events only - never simulation truth or replay authority"}


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

    lineage_key = lineage_key_for_run(run)
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

    # Integrity fix (KIMI review, 2026-07-25): CAS on next_order_index. The
    # filter only matches if it still equals the value read at the top of
    # this request (`run["next_order_index"]`, passed as the order_index
    # base to run_commit_frame above) -- a concurrent tick-commit or another
    # intervention advancing it in between must not be silently overwritten
    # (this endpoint previously had no CAS at all here). Does not achieve
    # the same full multi-document atomicity as the real transactional
    # pipeline (core/storage/frame_transaction.py::commit_frame_atomically)
    # -- the accepted_events/rejected_proposals/entities writes above are
    # not rolled back if this specific check fails -- but it closes the
    # specific defect named (a silent, racy next_order_index overwrite) and
    # is backstopped by core/db.py's new uq_run_order_index unique index.
    kernel_runs_result = await db.kernel_runs.update_one(
        {"id": run_id, "next_order_index": run["next_order_index"]},
        {"$set": {"last_state_hash": ending_hash, "next_order_index": next_order}},
    )
    if kernel_runs_result.matched_count == 0:
        raise HTTPException(409, {
            "error_code": "CONCURRENT_MODIFICATION",
            "detail": f"run {run_id} changed concurrently (next_order_index no "
                      "longer matches the value read for this intervention); "
                      "retry the intervention",
        })

    # Integrity fix (KIMI review, 2026-07-25): recompute a content-derived
    # frame_identity_hash for this write instead of leaving it stale/
    # omitted (the prior code $set the frame's ending_state_hash and $push'd
    # event ids without ever touching frame_identity_hash at all). Narrower
    # than PrecomputedFrame.compute_identity() (core/storage/frame_
    # transaction.py) -- that formula folds in expected_head_revision and
    # hash_policy_version, which this ad-hoc intervention path does not
    # track -- but it is still a genuine fingerprint of this write's own
    # content, and it is scoped by tick so it cannot collide with another
    # tick's identity hash under core.db's uq_run_frame_identity unique
    # index (partial, only for string-typed frame_identity_hash values).
    accepted_event_ids = [e["id"] for e in accepted]
    rejected_proposal_ids = [r["id"] for r in rejected]
    frame_identity_hash = canonical_hash({
        "run_id": run_id,
        "tick": run["current_tick"],
        "ending_state_hash": ending_hash,
        "accepted_event_ids": accepted_event_ids,
        "rejected_proposal_ids": rejected_proposal_ids,
        "next_order_index": next_order,
    })
    # Keep the commit_frame's ending_state_hash for this tick in sync so that
    # replay/determinism verification sees the post-intervention hash too.
    await db.commit_frames.update_one(
        {"run_id": run_id, "tick": run["current_tick"]},
        {"$set": {"ending_state_hash": ending_hash, "frame_identity_hash": frame_identity_hash},
         "$setOnInsert": {"id": f"{run_id}-frame-{run['current_tick']}", "starting_state_hash": None,
                           "tick": run["current_tick"]},
         "$push": {
             "accepted_event_ids": {"$each": accepted_event_ids},
             "rejected_proposal_ids": {"$each": rejected_proposal_ids},
         }},
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
