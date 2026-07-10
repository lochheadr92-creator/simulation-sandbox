"""Persistent History and Causal Memory (Phase 4A).

Everything here is a PROJECTION over `accepted_events` (and the current
canonical `entities` documents) - never a second source of truth, never
authoritative for replay. Nothing is fabricated: every field returned is
either a stored fact (event, mutation value, entity field) or a mechanical
derivation from stored facts (counts, first-occurrence detection, position
matches). Where the spec's example vocabulary (relationships, repairs,
structure destruction, migration) has no corresponding mechanic in this
world model, this module returns an explicit `not applicable` note rather
than inventing data.

Two DB-touching async helpers live here too (`tile_history`,
`chronological_events_for_run`) since they are simple, bounded, read-only
queries - everything else is a pure function of already-fetched event
lists, easy to unit test and to prove "rebuildable" (it IS rebuilt, from
scratch, on every single call).
"""
from core.db import db
from core.constants import SHELTER_COST

NOT_APPLICABLE = "not applicable to this world model (no such mechanic exists yet)"


def entity_touch_query(run_id: str, entity_id: str) -> dict:
    """Every accepted event that is causally about this entity: it was the
    proposer's own entity, OR it was a secondary touched party (e.g. a
    gathered tree, a hunted animal), OR it was created by the event (a new
    shelter/carcass). touched_scope + new_entities cover cases the plain
    `entity_id` field misses (a hunter's hunt_strike event has entity_id ==
    the HUNTER, not the animal it kills - but the animal IS in touched_scope)."""
    return {
        "run_id": run_id,
        "$or": [
            {"entity_id": entity_id},
            {"touched_scope": entity_id},
            {f"mutation.new_entities.{entity_id}": {"$exists": True}},
        ],
    }


async def chronological_events_for_run(run_id: str, limit: int = 5000) -> list:
    return await db.accepted_events.find({"run_id": run_id}, {"_id": 0}).sort("order_index", 1).to_list(limit)


async def events_for_entity(run_id: str, entity_id: str, limit: int = 500) -> list:
    return await db.accepted_events.find(
        entity_touch_query(run_id, entity_id), {"_id": 0},
    ).sort("order_index", 1).to_list(limit)


async def tile_history(run_id: str, x: int, y: int, limit: int = 50, scan_window: int = 3000) -> list:
    """Bounded chronological list of accepted events whose mutation placed
    ANY entity at (x, y) - a pure projection, never simulation truth or
    replay authority. Scans the most recent `scan_window` events (bounded)
    and returns up to `limit` matches, most recent first."""
    events = await db.accepted_events.find({"run_id": run_id}, {"_id": 0}).sort("order_index", -1).to_list(scan_window)
    target = {"x": x, "y": y}
    matches = []
    for ev in events:
        mutation = ev.get("mutation", {})
        touched = any(upd.get("position") == target for upd in mutation.get("entity_updates", {}).values())
        if not touched:
            touched = any(spec.get("position") == target for spec in mutation.get("new_entities", {}).values())
        if touched:
            matches.append(ev)
            if len(matches) >= limit:
                break
    return matches


# ---------- generic, reusable event predicates (used by both milestones and provenance) ----------

def death_entity_id(ev: dict):
    """Robust death detector: ANY entity_updates entry (primary OR
    secondary) setting alive=False. Deliberately generic so it catches
    LifecycleDomain deaths, AnimalDomain starvation deaths, AND
    People-authored hunt-kill events (hunter is the proposer, but the
    ANIMAL is who dies) with one rule."""
    for eid, upd in ev.get("mutation", {}).get("entity_updates", {}).items():
        if upd.get("alive") is False:
            return eid
    return None


def injury_entity_id(ev: dict):
    """An event that newly injures an entity without killing it this tick."""
    for eid, upd in ev.get("mutation", {}).get("entity_updates", {}).items():
        if upd.get("alive") is False:
            continue
        if upd.get("injured") is True:
            return eid
        injury = upd.get("injury")
        if isinstance(injury, dict) and injury.get("injured") is True:
            return eid
    return None


def resource_exhausted_entity_id(ev: dict):
    if ev.get("event_type") not in ("gather", "decay"):
        return None
    for eid, upd in ev.get("mutation", {}).get("entity_updates", {}).items():
        if upd.get("resource") == 0:
            return eid
    return None


def shelter_completed_entity_id(ev: dict):
    for eid, spec in ev.get("mutation", {}).get("new_entities", {}).items():
        if spec.get("type") == "shelter":
            return eid
    return None


def _milestone(mtype, ev, entity_id, explanation):
    return {
        "milestone_type": mtype, "event_id": ev["id"], "tick": ev["simulation_time"],
        "order_index": ev["order_index"], "entity_id": entity_id, "explanation": explanation,
    }


def classify_milestones(events: list) -> list:
    """`events` must be sorted chronologically (order_index ascending) for
    the WHOLE run. Approved milestone set only (Phase 4 scope decision):
    first_shelter, shelter_completed (recurring), first_resource_exhausted,
    first_major_discovery, first_injury, first_death. Migration, relationship
    changes, repairs and structure destruction are explicitly NOT modelled
    (no such mechanic exists) and are never fabricated here."""
    milestones = []
    first_shelter_done = first_exhausted_done = first_injury_done = first_death_done = False

    for ev in events:
        if not first_shelter_done and ev.get("event_type") == "build_shelter":
            milestones.append(_milestone("first_shelter", ev, ev["entity_id"], "first shelter construction started"))
            first_shelter_done = True

        shelter_id = shelter_completed_entity_id(ev)
        if shelter_id:
            milestones.append(_milestone("shelter_completed", ev, shelter_id, f"{shelter_id} completed"))

        if not first_exhausted_done:
            exhausted_id = resource_exhausted_entity_id(ev)
            if exhausted_id:
                milestones.append(_milestone("first_resource_exhausted", ev, exhausted_id, f"{exhausted_id} fully depleted"))
                first_exhausted_done = True

        if not first_injury_done:
            injured_id = injury_entity_id(ev)
            if injured_id:
                milestones.append(_milestone("first_injury", ev, injured_id, f"{injured_id} injured"))
                first_injury_done = True

        if not first_death_done:
            dead_id = death_entity_id(ev)
            if dead_id:
                milestones.append(_milestone("first_death", ev, dead_id, f"{dead_id} died"))
                first_death_done = True

    disc_ev, disc_id = _first_discovery_event(events)
    if disc_ev:
        milestones.append(_milestone("first_major_discovery", disc_ev, disc_id, f"{disc_id} made their first major discovery"))

    milestones.sort(key=lambda m: m["order_index"])
    return milestones


def _first_discovery_event(events: list):
    seen_any = {}
    for ev in events:
        for eid, upd in ev.get("mutation", {}).get("entity_updates", {}).items():
            knowledge = upd.get("knowledge")
            if not knowledge:
                continue
            had_before = seen_any.get(eid, False)
            has_now = bool(knowledge.get("known_trees")) or bool(knowledge.get("known_water_tiles")) or bool(knowledge.get("known_carcasses"))
            if has_now and not had_before:
                return ev, eid
            if has_now:
                seen_any[eid] = True
    return None, None


def build_timeline(events: list, milestones: list) -> list:
    by_event_id = {}
    for m in milestones:
        by_event_id.setdefault(m["event_id"], []).append(m["milestone_type"])
    timeline = []
    for ev in events:
        timeline.append({
            "event_id": ev["id"], "tick": ev["simulation_time"], "order_index": ev["order_index"],
            "event_type": ev["event_type"], "event_family": ev["event_family"], "entity_id": ev["entity_id"],
            "touched_scope": ev.get("touched_scope", []), "is_exogenous": ev.get("is_exogenous", False),
            "explanation": ev.get("explanation", ""), "causal_parent_event_ids": ev.get("causal_parent_event_ids", []),
            "milestones": by_event_id.get(ev["id"], []),
        })
    return timeline


def _discoveries_for_person(events: list, entity_id: str) -> list:
    discoveries = []
    prev_counts = None
    for ev in events:
        upd = ev.get("mutation", {}).get("entity_updates", {}).get(entity_id)
        if not upd or "knowledge" not in upd:
            continue
        k = upd["knowledge"]
        counts = (len(k.get("known_trees", {})), len(k.get("known_water_tiles", [])),
                  len(k.get("known_carcasses", {})), len(k.get("known_shelters", {})))
        if prev_counts is not None and sum(counts) > sum(prev_counts):
            discoveries.append({"tick": ev["simulation_time"], "event_id": ev["id"],
                                 "known_trees": counts[0], "known_water_tiles": counts[1],
                                 "known_carcasses": counts[2], "known_shelters": counts[3]})
        prev_counts = counts
    return discoveries


def provenance_for_entity(entity_id: str, entity: dict, events: list) -> dict:
    """`events` must be the entity_touch_query result, sorted chronologically
    (ascending order_index). Returns ONLY facts derived from `entity`/`events`."""
    etype = entity.get("type") if entity else None
    genesis = next((ev for ev in events if ev.get("is_exogenous") and ev.get("simulation_time") == 0), None)
    common = {
        "entity_id": entity_id, "entity_type": etype,
        "spawned_at_tick": genesis["simulation_time"] if genesis else None,
        "spawned_event_id": genesis["id"] if genesis else None,
        "total_events_on_record": len(events),
    }

    if etype == "person":
        death_ev = next((ev for ev in events if death_entity_id(ev) == entity_id), None)
        injuries = [ev for ev in events if injury_entity_id(ev) == entity_id]
        action_counts = {}
        for ev in events:
            if ev.get("entity_id") == entity_id:
                action_counts[ev["event_type"]] = action_counts.get(ev["event_type"], 0) + 1
        return {**common, "origin": "genesis spawn" if genesis else "unknown", "action_counts": action_counts,
                "discoveries": _discoveries_for_person(events, entity_id)[:15],
                "injuries": [{"tick": ev["simulation_time"], "event_id": ev["id"], "explanation": ev.get("explanation")} for ev in injuries],
                "death": ({"tick": death_ev["simulation_time"], "event_id": death_ev["id"],
                           "cause": entity.get("death_cause"), "explanation": death_ev.get("explanation")} if death_ev else None),
                "relationships": None, "relationships_note": NOT_APPLICABLE}

    if etype == "animal":
        death_ev = next((ev for ev in events if death_entity_id(ev) == entity_id), None)
        hunt_events = [ev for ev in events if ev["event_type"] == "hunt_strike" and entity_id in ev.get("touched_scope", [])]
        action_counts = {}
        for ev in events:
            if ev.get("entity_id") == entity_id:
                action_counts[ev["event_type"]] = action_counts.get(ev["event_type"], 0) + 1
        return {**common, "origin": "genesis spawn" if genesis else "unknown", "action_counts": action_counts,
                "hunted_by_events": [{"tick": ev["simulation_time"], "event_id": ev["id"], "hunter_id": ev["entity_id"],
                                       "explanation": ev.get("explanation")} for ev in hunt_events],
                "death": ({"tick": death_ev["simulation_time"], "event_id": death_ev["id"],
                           "cause": entity.get("death_cause"), "explanation": death_ev.get("explanation")} if death_ev else None)}

    if etype == "tree":
        harvests = [ev for ev in events if ev["event_type"] == "gather"]
        depletion = next((ev for ev in events if resource_exhausted_entity_id(ev) == entity_id), None)
        return {**common,
                "harvest_history": [{"tick": ev["simulation_time"], "harvester_id": ev["entity_id"], "explanation": ev.get("explanation")} for ev in harvests],
                "regrowth_event_count": len([ev for ev in events if ev["event_type"] == "regrow"]),
                "depleted": bool(depletion), "depleted_at_tick": depletion["simulation_time"] if depletion else None,
                "current_resource": entity.get("resource"), "max_resource": entity.get("max_resource")}

    if etype == "carcass":
        harvests = [ev for ev in events if ev["event_type"] == "gather"]
        return {**common, "source_animal_id": entity.get("source_animal_id"),
                "harvest_history": [{"tick": ev["simulation_time"], "harvester_id": ev["entity_id"]} for ev in harvests],
                "decay_event_count": len([ev for ev in events if ev["event_type"] == "decay"]),
                "current_resource": entity.get("resource"), "max_resource": entity.get("max_resource")}

    if etype == "shelter":
        build_ev = next((ev for ev in events if shelter_completed_entity_id(ev) == entity_id), None)
        return {**common, "builder_id": entity.get("owner_id"),
                "construction_event": ({"tick": build_ev["simulation_time"], "event_id": build_ev["id"]} if build_ev else None),
                "resources_consumed": SHELTER_COST if build_ev else None,
                "repairs": None, "repairs_note": NOT_APPLICABLE,
                "destruction": None, "destruction_note": NOT_APPLICABLE}

    return common
