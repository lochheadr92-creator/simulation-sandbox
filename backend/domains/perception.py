"""Perception & Knowledge (Phase 2; grounded in Phase 5A5 Cognitive slice).

Doctrine:
  Actors only know what they have genuinely discovered via bounded perception.
  Decision logic (people_utility) must read FROM knowledge / this-tick
  detections — never an omniscient global entity scan for targets.

Knowledge is sparse, observer-owned, and mutates only when an accepted
people_action (or equivalent) commits a material knowledge change.
"""
from core.geometry import manhattan, is_passable
from core.constants import VISION_RADIUS
from core.hashing import canonical_hash

PERCEPTION_RULE_VERSION = "perception-manhattan-v1"
KNOWLEDGE_SCHEMA_VERSION = "knowledge-v2"

# Bounded growth caps (hard integer limits; deterministic replacement by age)
MAX_KNOWN_TILES = 200
MAX_KNOWN_WATER = 40
MAX_KNOWN_TREES = 30
MAX_KNOWN_SHELTERS = 10
MAX_KNOWN_CARCASSES = 15
MAX_KNOWN_ANIMALS = 15
MAX_KNOWN_PEOPLE = 15
MAX_KNOWN_DANGERS = 10
MAX_DETECTIONS_PER_ACTIVATION = 48


def empty_knowledge() -> dict:
    return {
        "schema_version": KNOWLEDGE_SCHEMA_VERSION,
        "known_tiles": [],
        "known_water_tiles": [],
        "known_trees": {},
        "known_shelters": {},
        "known_carcasses": {},
        "known_animals": {},
        "known_people": {},
        "known_dangers": {},
        "facts": {},
    }


def _compat_knowledge(existing: dict | None) -> dict:
    """Deterministic compatibility: never invent world knowledge; only fill shape."""
    base = empty_knowledge()
    if not existing:
        return base
    out = dict(base)
    for key in ("known_tiles", "known_water_tiles"):
        if key in existing:
            out[key] = list(existing[key])
    for key in ("known_trees", "known_shelters", "known_carcasses",
                "known_animals", "known_people", "known_dangers", "facts"):
        if key in existing and isinstance(existing[key], dict):
            out[key] = dict(existing[key])
    out["schema_version"] = KNOWLEDGE_SCHEMA_VERSION
    return out


def _fact_id(fact_type: str, subject: str) -> str:
    return f"{fact_type}:{subject}"


def _make_fact(observer_id, fact_type, subject, location, tick, confidence=100,
               source_event_id=None, extra=None):
    fid = _fact_id(fact_type, subject)
    body = {
        "fact_id": fid,
        "observer_id": observer_id,
        "fact_type": fact_type,
        "subject": subject,
        "location": dict(location) if location else None,
        "confidence": int(confidence),
        "source_event_id": source_event_id,
        "first_known_tick": tick,
        "last_confirmed_tick": tick,
        "status": "confirmed",
        "schema_version": KNOWLEDGE_SCHEMA_VERSION,
        "perception_rule_version": PERCEPTION_RULE_VERSION,
    }
    if extra:
        body.update(extra)
    return fid, body


def perceive(pos: dict, entities: dict, terrain: list, tick: int,
             observer_id: str | None = None, radius: int = VISION_RADIUS) -> dict:
    """Bounded perception from a pinned observation frame.

    Returns a detection package (not yet merged). Entity iteration uses sorted
    IDs so proposal/dict arrival order cannot change detection order.
    """
    height = len(terrain)
    width = len(terrain[0]) if height else 0
    tiles = []
    water = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if abs(dx) + abs(dy) > radius:
                continue
            x, y = pos["x"] + dx, pos["y"] + dy
            if 0 <= x < width and 0 <= y < height:
                key = f"{x},{y}"
                tiles.append(key)
                if terrain[y][x] == "water":
                    water.append(key)

    tree_sightings = {}
    shelter_sightings = {}
    carcass_sightings = {}
    animal_sightings = {}
    person_sightings = {}
    danger_sightings = {}
    detections = []

    for eid in sorted(entities):
        e = entities[eid]
        et = e.get("type")
        epos = e.get("position")
        if not epos:
            continue
        dist = manhattan(pos, epos)
        if dist > radius:
            continue
        if et == "tree":
            tree_sightings[eid] = {
                "last_seen_tick": tick,
                "last_known_resource": e.get("resource", 0),
                "position": dict(epos),
            }
            detections.append(_detection(observer_id, eid, "tree", pos, epos, dist, tick))
        elif et == "shelter" and e.get("alive", True):
            shelter_sightings[eid] = {
                "last_seen_tick": tick,
                "position": dict(epos),
                "owner_id": e.get("owner_id"),
            }
            detections.append(_detection(observer_id, eid, "shelter", pos, epos, dist, tick))
        elif et == "carcass":
            carcass_sightings[eid] = {
                "last_seen_tick": tick,
                "last_known_resource": e.get("resource", 0),
                "position": dict(epos),
                "source_animal_id": e.get("source_animal_id"),
            }
            detections.append(_detection(observer_id, eid, "carcass", pos, epos, dist, tick))
        elif et == "animal" and e.get("alive", True):
            animal_sightings[eid] = {
                "last_seen_tick": tick,
                "position": dict(epos),
                "alive": True,
                "injured": bool(e.get("injured")),
                "action_type": (e.get("action") or {}).get("type"),
            }
            detections.append(_detection(observer_id, eid, "animal", pos, epos, dist, tick))
            if (e.get("action") or {}).get("type") == "flee" or e.get("injured"):
                danger_sightings[eid] = {
                    "last_seen_tick": tick,
                    "position": dict(epos),
                    "kind": "animal_threat",
                }
                detections.append(_detection(observer_id, eid, "danger", pos, epos, dist, tick))
        elif et == "person" and e.get("alive", True) and eid != observer_id:
            person_sightings[eid] = {
                "last_seen_tick": tick,
                "position": dict(epos),
                "alive": True,
            }
            detections.append(_detection(observer_id, eid, "person", pos, epos, dist, tick))

        if len(detections) >= MAX_DETECTIONS_PER_ACTIVATION:
            break

    # Stable detection order: by (type, subject, distance)
    detections = sorted(detections, key=lambda d: (d["subject_type"], d["subject_id"], d["distance"]))
    detections = detections[:MAX_DETECTIONS_PER_ACTIVATION]

    return {
        "new_tiles": tiles,
        "new_water": water,
        "tree_sightings": tree_sightings,
        "shelter_sightings": shelter_sightings,
        "carcass_sightings": carcass_sightings,
        "animal_sightings": animal_sightings,
        "person_sightings": person_sightings,
        "danger_sightings": danger_sightings,
        "detections": detections,
        "observer_pos": dict(pos),
        "tick": tick,
        "radius": radius,
        "perception_rule_version": PERCEPTION_RULE_VERSION,
    }


def _detection(observer_id, subject_id, subject_type, observer_pos, subject_pos, dist, tick):
    return {
        "observer_id": observer_id,
        "subject_id": subject_id,
        "subject_type": subject_type,
        "detection_tick": tick,
        "observer_pos": dict(observer_pos),
        "subject_pos": dict(subject_pos),
        "distance": dist,
        "perception_rule_version": PERCEPTION_RULE_VERSION,
    }


def _trim_dict(d: dict, max_n: int) -> dict:
    if len(d) <= max_n:
        return d
    # Drop oldest by last_seen_tick / last_confirmed_tick, then key
    def age_key(item):
        k, v = item
        return (v.get("last_seen_tick", v.get("last_confirmed_tick", 0)), k)
    keep = sorted(d.items(), key=age_key, reverse=True)[:max_n]
    return {k: v for k, v in sorted(keep, key=lambda kv: kv[0])}


def merge_knowledge(existing: dict, delta: dict, observer_id: str | None = None,
                    source_event_id: str | None = None):
    """Merge perception delta. Returns (merged, material_change: bool, learned: list).

    material_change is False when nothing new/updated — callers must not rewrite
    identical knowledge every tick (bounded growth).
    """
    existing = _compat_knowledge(existing)
    known_tiles = set(existing.get("known_tiles", []))
    known_water = set(existing.get("known_water_tiles", []))
    known_trees = dict(existing.get("known_trees", {}))
    known_shelters = dict(existing.get("known_shelters", {}))
    known_carcasses = dict(existing.get("known_carcasses", {}))
    known_animals = dict(existing.get("known_animals", {}))
    known_people = dict(existing.get("known_people", {}))
    known_dangers = dict(existing.get("known_dangers", {}))
    facts = dict(existing.get("facts", {}))

    tick = delta.get("tick", 0)
    learned = []
    changed = False

    new_tiles = set(delta.get("new_tiles", []))
    if new_tiles - known_tiles:
        changed = True
        learned.append({"kind": "tiles", "count": len(new_tiles - known_tiles)})
    known_tiles |= new_tiles

    new_water = set(delta.get("new_water", []))
    for key in sorted(new_water - known_water):
        changed = True
        x, y = (int(v) for v in key.split(","))
        fid, fact = _make_fact(observer_id, "water", key, {"x": x, "y": y}, tick,
                               source_event_id=source_event_id)
        if fid in facts:
            facts[fid]["last_confirmed_tick"] = tick
            facts[fid]["location"] = {"x": x, "y": y}
            facts[fid]["status"] = "confirmed"
            if source_event_id:
                facts[fid]["source_event_id"] = source_event_id
        else:
            facts[fid] = fact
        learned.append({"kind": "water", "subject": key})
    known_water |= new_water

    def _content_sig(info, resource_fields):
        return (
            (info.get("position") or {}).get("x"),
            (info.get("position") or {}).get("y"),
            tuple(info.get(f) for f in resource_fields),
        )

    def _upsert_entity_map(store, sightings, fact_type, resource_fields=()):
        nonlocal changed
        for sid in sorted(sightings):
            info = sightings[sid]
            prev = store.get(sid)
            pos = info.get("position")
            sig = _content_sig(info, resource_fields)
            prev_sig = _content_sig(prev, resource_fields) if prev else None
            # Tick-only re-observation of identical content is NOT material —
            # prevents one knowledge rewrite per nearby object per tick.
            if prev is not None and sig == prev_sig:
                store[sid] = {**prev, "last_seen_tick": info.get("last_seen_tick", tick)}
                continue
            changed = True
            learned.append({
                "kind": fact_type,
                "subject": sid,
                "update": "new" if prev is None else "move_or_change",
            })
            store[sid] = dict(info)
            fid, fact = _make_fact(
                observer_id, fact_type, sid, pos, tick,
                source_event_id=source_event_id,
                extra={"last_known_resource": info.get("last_known_resource")},
            )
            if fid in facts:
                facts[fid]["last_confirmed_tick"] = tick
                facts[fid]["location"] = dict(pos) if pos else facts[fid].get("location")
                facts[fid]["status"] = "confirmed"
                if "last_known_resource" in info:
                    facts[fid]["last_known_resource"] = info["last_known_resource"]
                if source_event_id:
                    facts[fid]["source_event_id"] = source_event_id
            else:
                facts[fid] = fact

    _upsert_entity_map(known_trees, delta.get("tree_sightings", {}), "food",
                       ("last_known_resource",))
    # trees also wood — fact_type food for gather targeting; keep tree map
    for sid, info in delta.get("tree_sightings", {}).items():
        # also index as tree fact for inspection
        fid, fact = _make_fact(observer_id, "tree", sid, info.get("position"), tick,
                               source_event_id=source_event_id,
                               extra={"last_known_resource": info.get("last_known_resource")})
        if fid not in facts:
            facts[fid] = fact
        else:
            facts[fid]["last_confirmed_tick"] = tick

    _upsert_entity_map(known_shelters, delta.get("shelter_sightings", {}), "shelter")
    _upsert_entity_map(known_carcasses, delta.get("carcass_sightings", {}), "food",
                       ("last_known_resource",))
    _upsert_entity_map(known_animals, delta.get("animal_sightings", {}), "animal",
                       ("alive", "injured", "action_type"))
    _upsert_entity_map(known_people, delta.get("person_sightings", {}), "person")
    _upsert_entity_map(known_dangers, delta.get("danger_sightings", {}), "danger", ("kind",))

    # Cap growth deterministically
    if len(known_tiles) > MAX_KNOWN_TILES:
        known_tiles = set(sorted(known_tiles)[-MAX_KNOWN_TILES:])
        changed = True
    if len(known_water) > MAX_KNOWN_WATER:
        known_water = set(sorted(known_water)[-MAX_KNOWN_WATER:])
        changed = True
    known_trees = _trim_dict(known_trees, MAX_KNOWN_TREES)
    known_shelters = _trim_dict(known_shelters, MAX_KNOWN_SHELTERS)
    known_carcasses = _trim_dict(known_carcasses, MAX_KNOWN_CARCASSES)
    known_animals = _trim_dict(known_animals, MAX_KNOWN_ANIMALS)
    known_people = _trim_dict(known_people, MAX_KNOWN_PEOPLE)
    known_dangers = _trim_dict(known_dangers, MAX_KNOWN_DANGERS)
    if len(facts) > (
        MAX_KNOWN_WATER + MAX_KNOWN_TREES + MAX_KNOWN_SHELTERS + MAX_KNOWN_CARCASSES
        + MAX_KNOWN_ANIMALS + MAX_KNOWN_PEOPLE + MAX_KNOWN_DANGERS + 20
    ):
        facts = _trim_dict(facts, 120)

    merged = {
        "schema_version": KNOWLEDGE_SCHEMA_VERSION,
        "known_tiles": sorted(known_tiles),
        "known_water_tiles": sorted(known_water),
        "known_trees": known_trees,
        "known_shelters": known_shelters,
        "known_carcasses": known_carcasses,
        "known_animals": known_animals,
        "known_people": known_people,
        "known_dangers": known_dangers,
        "facts": facts,
    }
    return merged, changed, learned


def knowledge_fingerprint(knowledge: dict) -> str:
    return canonical_hash(knowledge or {})


def detections_in_range(pos, entities, radius=VISION_RADIUS):
    """Test helper: sorted subject ids currently in integer Manhattan range."""
    found = []
    for eid in sorted(entities):
        e = entities[eid]
        if e.get("position") and manhattan(pos, e["position"]) <= radius:
            found.append(eid)
    return found


def neighbor_unknown_tiles(pos, knowledge, terrain):
    """Exploration candidates: passable 4-neighbours not in known_tiles.

    Fixed neighbour order N,E,S,W. No full-map scan.
    """
    from core.navigation import NEIGHBOR_DELTAS
    known = set(knowledge.get("known_tiles", []))
    out = []
    for dx, dy in NEIGHBOR_DELTAS:
        n = {"x": pos["x"] + dx, "y": pos["y"] + dy}
        if not is_passable(n, terrain):
            continue
        key = f"{n['x']},{n['y']}"
        if key not in known:
            out.append(n)
    return out
