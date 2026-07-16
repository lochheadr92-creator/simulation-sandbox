"""Capability Stage 6A deterministic cognition primitives.

The functions in this module are pure transforms over a pinned observation
frame and canonical agent state.  They never write storage or mutate the
supplied objects.  Knowledge and memories may be wrong; the important contract
is that their provenance is explicit and no undeclared world fields leak in.
"""
from __future__ import annotations

import copy

from core.geometry import manhattan
from core.hashing import canonical_hash
from domains.living_agent_contracts import (
    KNOWLEDGE_PROVENANCE_TYPES,
    LIMITS,
    MEMORY_SCHEMA_VERSION,
    PRESSURE_SCHEMA_VERSION,
    WANT_SCHEMA_VERSION,
    compat_living_agent_state,
)
from domains.perception import _compat_knowledge, perceive


LIVING_PERCEPTION_VERSION = "living-perception-v1"
LIVING_KNOWLEDGE_VERSION = "living-knowledge-provenance-v1"

OPAQUE_TERRAIN = frozenset({"wall", "cliff", "dense_forest"})
OBJECT_TYPES = frozenset({
    "tool", "item", "resource", "storage", "container", "structure",
    "signal", "water_source",
})


def _bounded(value, low=0, high=1000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = low
    return max(low, min(high, parsed))


def _line_points(start: dict, end: dict) -> list[tuple[int, int]]:
    """Integer Bresenham points excluding endpoints, in stable order."""
    x0, y0 = int(start["x"]), int(start["y"])
    x1, y1 = int(end["x"]), int(end["y"])
    dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
    dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
    err = dx + dy
    points = []
    while (x0, y0) != (x1, y1):
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
        if (x0, y0) != (x1, y1):
            points.append((x0, y0))
    return points


def _has_line_of_sight(start: dict, end: dict, terrain: list) -> bool:
    height = len(terrain)
    width = len(terrain[0]) if height else 0
    for x, y in _line_points(start, end):
        if not (0 <= x < width and 0 <= y < height):
            return False
        if terrain[y][x] in OPAQUE_TERRAIN:
            return False
    return True


def _attention_profile(observer: dict, *, night: bool, weather: dict | None) -> dict:
    fatigue = 1000 - _bounded(observer.get("energy", 1000))
    health_deficit = 1000 - _bounded(observer.get("health", 1000))
    visibility_penalty = _bounded((weather or {}).get("visibility_penalty", 0), 0, 4)
    penalty = fatigue // 300 + health_deficit // 350 + visibility_penalty
    if night and not observer.get("has_light", False):
        penalty += 1
    attention = _bounded(1000 - fatigue // 2 - health_deficit // 3 - visibility_penalty * 100)
    return {
        "attention": attention,
        "fatigue_penalty": fatigue // 300,
        "health_penalty": health_deficit // 350,
        "lighting_penalty": 1 if night and not observer.get("has_light", False) else 0,
        "weather_penalty": visibility_penalty,
        "radius_penalty": penalty,
    }


def _visible_properties(entity_id: str, entity: dict, base_delta: dict) -> dict:
    """Return only properties supported by declared outward visibility rules."""
    entity_type = entity.get("type")
    if entity_type == "person":
        return copy.deepcopy((base_delta.get("person_sightings") or {}).get(entity_id) or {})
    if entity_type == "animal":
        return copy.deepcopy((base_delta.get("animal_sightings") or {}).get(entity_id) or {})
    if entity_type == "tree":
        return copy.deepcopy((base_delta.get("tree_sightings") or {}).get(entity_id) or {})
    if entity_type == "shelter":
        visible = copy.deepcopy((base_delta.get("shelter_sightings") or {}).get(entity_id) or {})
        if "condition" in entity:
            visible["condition"] = _bounded(entity.get("condition"))
        return visible
    if entity_type == "carcass":
        return copy.deepcopy((base_delta.get("carcass_sightings") or {}).get(entity_id) or {})
    if entity_type == "signal":
        return {
            "signal_kind": entity.get("signal_kind"),
            "strength": _bounded(entity.get("strength", 0)),
            "source_entity_id": entity.get("source_entity_id"),
            "source_action_id": entity.get("source_action_id"),
            "source_event_id": entity.get("source_event_id") or entity.get("last_event_id"),
            "message": copy.deepcopy(entity.get("message")),
            "propagation_depth": int(entity.get("propagation_depth", 0)),
        }
    if entity_type in ("storage", "container"):
        # Contents are visible only when explicitly public/open.  Capacity and
        # access markings are outward properties.
        visible = {
            "owner_id": entity.get("owner_id"),
            "access": entity.get("access", "public"),
            "open": bool(entity.get("open", False)),
            "condition": _bounded(entity.get("condition", 1000)),
        }
        if visible["open"] and visible["access"] in ("public", "shared"):
            visible["visible_contents"] = copy.deepcopy(entity.get("contents") or {})
        return visible
    if entity_type == "tool":
        durability = _bounded(entity.get("durability", 0))
        return {
            "tool_kind": entity.get("tool_kind"),
            "owner_id": entity.get("owner_id"),
            "durability_band": (durability // 100) * 100,
            "carried_by": entity.get("carried_by"),
        }
    if entity_type in ("item", "resource", "water_source"):
        return {
            "resource_kind": entity.get("resource_kind"),
            "quantity_band": (_bounded(entity.get("quantity", entity.get("resource", 0))) // 5) * 5,
            "quality_band": (_bounded(entity.get("quality", 500)) // 100) * 100,
            "owner_id": entity.get("owner_id"),
            "carried_by": entity.get("carried_by"),
        }
    if entity_type == "structure":
        return {
            "structure_kind": entity.get("structure_kind"),
            "owner_id": entity.get("owner_id"),
            "access": entity.get("access", "public"),
            "condition": _bounded(entity.get("condition", 1000)),
        }
    return {}


def perceive_living(
    observer_id: str,
    observer: dict,
    entities: dict,
    terrain: list,
    tick: int,
    *,
    night: bool = False,
    weather: dict | None = None,
    radius: int = 4,
) -> dict:
    """Build a bounded multifactor observation package from a pinned frame."""
    profile = _attention_profile(observer, night=night, weather=weather)
    effective_radius = max(1, int(radius) - profile["radius_penalty"])
    pos = observer["position"]
    base = perceive(pos, entities, terrain, tick, observer_id=observer_id, radius=effective_radius)

    observations = []
    entity_count = 0
    object_count = 0
    for subject_id in sorted(entities):
        if subject_id == observer_id:
            continue
        subject = entities[subject_id]
        subject_pos = subject.get("position")
        subject_type = subject.get("type")
        if not subject_pos:
            continue
        distance = manhattan(pos, subject_pos)
        source = "vision"
        signal_strength = _bounded(subject.get("strength", 0)) if subject_type == "signal" else 0
        signal_range = max(effective_radius, signal_strength // 200) if signal_strength else effective_radius
        if distance > signal_range:
            continue
        if subject_type == "signal" and subject.get("signal_kind") in ("speech", "social", "warning"):
            allowed = set(subject.get("recipient_ids") or []) | set(subject.get("witness_ids") or [])
            if allowed and observer_id not in allowed:
                continue
        if subject_type == "signal" and subject.get("signal_kind") in ("noise", "warning", "speech"):
            source = "hearing"
        elif not _has_line_of_sight(pos, subject_pos, terrain):
            continue

        is_object = subject_type in OBJECT_TYPES
        if is_object and object_count >= LIMITS.perceived_objects_per_observation:
            continue
        if not is_object and entity_count >= LIMITS.perceived_entities_per_observation:
            continue

        properties = _visible_properties(subject_id, subject, base)
        if subject_type not in OBJECT_TYPES and not properties:
            continue
        # Position is perceptible without becoming omniscient canonical state.
        # Candidate generation needs the observed location in order to form a
        # path toward an entity; keep it inside this bounded observation only.
        properties.setdefault("position", copy.deepcopy(subject_pos))
        confidence = _bounded(
            1000 - distance * 90 - profile["weather_penalty"] * 80
            - profile["lighting_penalty"] * 100 - profile["fatigue_penalty"] * 60,
            100,
            1000,
        )
        if source == "hearing":
            confidence = _bounded(confidence - 120 + signal_strength // 5, 100, 1000)
        observation_id = "obs-" + canonical_hash([
            LIVING_PERCEPTION_VERSION, observer_id, subject_id, subject_type, tick, source,
        ])[:16]
        observations.append({
            "observation_id": observation_id,
            "schema_version": LIVING_PERCEPTION_VERSION,
            "perceiving_entity_id": observer_id,
            "observed_subject_id": subject_id,
            "observation_type": subject_type,
            "observed_tick": int(tick),
            "source": source,
            "confidence": confidence,
            "properties": properties,
            "information_kind": "direct",
            "distance": distance,
            "source_event_id": subject.get("last_event_id"),
        })
        if is_object:
            object_count += 1
        else:
            entity_count += 1

    observations.sort(key=lambda item: (
        item["observation_type"], item["distance"], item["observed_subject_id"],
    ))
    base["observations"] = observations
    base["living_perception_version"] = LIVING_PERCEPTION_VERSION
    base["effective_radius"] = effective_radius
    base["attention"] = profile
    base["limits"] = {
        "entities": LIMITS.perceived_entities_per_observation,
        "objects": LIMITS.perceived_objects_per_observation,
    }
    return base


def _observation_fact_id(observation: dict) -> str:
    return f"observed:{observation['observation_type']}:{observation['observed_subject_id']}"


def merge_observations_into_knowledge(knowledge: dict, observations: list[dict]):
    """Merge direct observation facts; identical refreshes are non-material."""
    merged = _compat_knowledge(knowledge)
    facts = copy.deepcopy(merged.get("facts") or {})
    changed = False
    learned = []
    for observation in sorted(
        observations or [], key=lambda item: item.get("observation_id", ""),
    ):
        if observation.get("information_kind") != "direct":
            continue
        fact_id = _observation_fact_id(observation)
        properties = copy.deepcopy(observation.get("properties") or {})
        properties_hash = canonical_hash(properties)
        prior = facts.get(fact_id)
        prior_hash = prior.get("properties_hash") if isinstance(prior, dict) else None
        if prior is not None and prior_hash == properties_hash:
            # Tick-only reconfirmation remains reproducible from current
            # perception and does not force a canonical rewrite.
            continue
        contradiction_count = int((prior or {}).get("contradiction_count", 0))
        if prior is not None and prior_hash != properties_hash:
            contradiction_count += 1
        facts[fact_id] = {
            "fact_id": fact_id,
            "schema_version": LIVING_KNOWLEDGE_VERSION,
            "observer_id": observation.get("perceiving_entity_id"),
            "fact_type": observation.get("observation_type"),
            "subject": observation.get("observed_subject_id"),
            "properties": properties,
            "properties_hash": properties_hash,
            "confidence": _bounded(observation.get("confidence", 0)),
            "provenance_kind": "direct",
            "source_entity_id": observation.get("observed_subject_id"),
            "source_event_id": observation.get("source_event_id"),
            "observation_id": observation.get("observation_id"),
            "first_known_tick": int((prior or {}).get("first_known_tick", observation.get("observed_tick", 0))),
            "last_confirmed_tick": int(observation.get("observed_tick", 0)),
            "confirmation_count": int((prior or {}).get("confirmation_count", 0)) + 1,
            "contradiction_count": contradiction_count,
            "status": "confirmed",
            "stale_after_tick": int(observation.get("observed_tick", 0)) + 20,
            "learned_event_id": None,
        }
        changed = True
        learned.append({
            "kind": "observation",
            "subject": observation.get("observed_subject_id"),
            "fact_id": fact_id,
            "update": "new" if prior is None else "contradicted_or_changed",
        })

    # Preserve the existing global fact bound used by knowledge-v2.
    if len(facts) > 120:
        ranked = sorted(
            facts.items(),
            key=lambda pair: (int(pair[1].get("last_confirmed_tick", 0)), pair[0]),
            reverse=True,
        )[:120]
        facts = {key: value for key, value in sorted(ranked)}
        changed = True
    merged["facts"] = facts
    return merged, changed, learned


def merge_knowledge_claim(
    knowledge: dict,
    *,
    observer_id: str,
    subject_id: str,
    fact_type: str,
    properties: dict,
    tick: int,
    provenance_kind: str,
    confidence: int,
    source_entity_id: str | None,
    source_event_id: str | None,
    deceptive: bool = False,
) -> tuple[dict, dict]:
    """Merge a reported/inferred/rumoured claim without asserting its truth."""
    if provenance_kind not in KNOWLEDGE_PROVENANCE_TYPES - {"direct"}:
        raise ValueError(f"invalid claim provenance: {provenance_kind}")
    merged = _compat_knowledge(knowledge)
    facts = copy.deepcopy(merged.get("facts") or {})
    source_key = source_entity_id or "unknown"
    fact_id = f"claim:{fact_type}:{subject_id}:{source_key}"
    properties = copy.deepcopy(properties or {})
    properties_hash = canonical_hash(properties)
    prior = facts.get(fact_id)
    contradiction_count = int((prior or {}).get("contradiction_count", 0))
    if prior and prior.get("properties_hash") != properties_hash:
        contradiction_count += 1

    contradictory_ids = sorted(
        key for key, fact in facts.items()
        if fact.get("subject") == subject_id
        and fact.get("fact_type") == fact_type
        and fact.get("properties_hash") not in (None, properties_hash)
    )
    contradiction_count += len(contradictory_ids)
    status = "contradicted" if contradictory_ids else "unconfirmed"
    facts[fact_id] = {
        "fact_id": fact_id,
        "schema_version": LIVING_KNOWLEDGE_VERSION,
        "observer_id": observer_id,
        "fact_type": fact_type,
        "subject": subject_id,
        "properties": properties,
        "properties_hash": properties_hash,
        "confidence": _bounded(confidence),
        "provenance_kind": provenance_kind,
        "source_entity_id": source_entity_id,
        "source_event_id": source_event_id,
        "first_known_tick": int((prior or {}).get("first_known_tick", tick)),
        "last_confirmed_tick": int(tick),
        "confirmation_count": int((prior or {}).get("confirmation_count", 0)) + 1,
        "contradiction_count": contradiction_count,
        "contradicts": contradictory_ids[:8],
        "status": status,
        "deceptive_source_claim": bool(deceptive),
        "stale_after_tick": int(tick) + 12,
        "learned_event_id": None,
    }
    merged["facts"] = facts
    return merged, copy.deepcopy(facts[fact_id])


def _relationship_counts(state: dict) -> tuple[int, int]:
    positive = 0
    feared = 0
    for relation in (state.get("relationships") or {}).values():
        if relation.get("affection", 0) > 150 or relation.get("trust", 0) > 150:
            positive += 1
        if relation.get("fear", 0) > 300 or relation.get("resentment", 0) > 300:
            feared += 1
    return positive, feared


def derive_internal_pressures(
    entity: dict,
    state: dict,
    knowledge: dict,
    perception_delta: dict,
    tick: int,
    *,
    night: bool = False,
    weather: dict | None = None,
) -> dict:
    """Derive all required pressures from canonical state and owned knowledge."""
    out = copy.deepcopy(state)
    prior_pressures = state.get("pressures") or {}
    visible_people = len((perception_delta or {}).get("person_sightings") or {})
    visible_dangers = len((perception_delta or {}).get("danger_sightings") or {})
    positive_relations, feared_relations = _relationship_counts(state)
    active_commitments = sum(
        1 for item in (state.get("commitments") or {}).values()
        if item.get("status") in ("active", "overdue", "disputed")
    )
    threat_memories = sum(
        1 for item in (state.get("memories") or {}).values()
        if item.get("memory_kind") in ("threat_observed", "harm_received")
        and item.get("confidence", 0) >= 300
    )
    traits = state["traits"]
    injury = entity.get("injury") or {}
    injury_severity = _bounded(injury.get("severity", 1000 - entity.get("health", 1000)))
    exposure = (
        (350 if night and not entity.get("has_shelter", False) else 0)
        + _bounded((weather or {}).get("exposure", 0))
    )
    known_tiles = len(knowledge.get("known_tiles") or [])
    raw = {
        "thirst": (_bounded(entity.get("thirst", 0)), "canonical:thirst"),
        "hunger": (_bounded(entity.get("hunger", 0)), "canonical:hunger"),
        "fatigue": (1000 - _bounded(entity.get("energy", 1000)), "canonical:energy"),
        "exposure": (_bounded(exposure), "environment:weather_or_night"),
        "pain": (_bounded(injury_severity * 4 // 5), "canonical:injury"),
        "injury_severity": (injury_severity, "canonical:injury"),
        "safety": (_bounded(visible_dangers * 280 + feared_relations * 90 + (1000 - entity.get("health", 1000)) // 2), "perceived:danger"),
        # Stage 6 Liveness Pass: use the natural exposure->comfort coupling
        # (full exposure, was an arbitrary exposure//2 halving) so sustained
        # exposure (night + storm) carries comfort urgency across the 150
        # want-activation gate for the shelterless camp members simultaneously,
        # making improve_shelter an active want for >=2 members. The full
        # coupling does NOT overshoot in the sustained camp: once the companion
        # food fix keeps agents alive, well-fed members self-shelter (the 350
        # night term zeroes out under a functional shelter), so only members
        # whose shared shelter has worn below usability stay exposed -- the peak
        # sits well under the starving all-shelterless baseline while still
        # clearing 150 with margin. Determinism-visible; re-baselines the
        # living_settlement hash intentionally. See STAGE-6-LIVENESS-PASS.md.
        "comfort": (_bounded(exposure + (1000 - entity.get("energy", 1000)) // 3), "derived:exposure_and_fatigue"),
        "social_contact": (_bounded(700 - min(visible_people, 3) * 240), "perceived:nearby_people"),
        "belonging": (_bounded(650 - positive_relations * 160), "owned:relationships"),
        "curiosity": (_bounded(720 - min(known_tiles, 200) * 3), "owned:knowledge_extent"),
        "attachment": (_bounded(520 - positive_relations * 130), "owned:relationships"),
        "fear": (_bounded(visible_dangers * 260 + feared_relations * 100 + threat_memories * 40), "perceived_or_remembered:threat"),
        "perceived_obligation": (_bounded(active_commitments * 190), "owned:commitments"),
    }

    tolerance_bias = {
        "fear": traits["risk_tolerance"] - traits["caution"],
        "safety": traits["risk_tolerance"] - traits["caution"],
        "social_contact": 50 - traits["sociability"],
        "belonging": 50 - traits["sociability"],
        "curiosity": 50 - traits["curiosity"],
        "comfort": 50 - traits["comfort_preference"],
        "perceived_obligation": 50 - traits["obligation_sensitivity"],
    }
    pressures = {}
    for kind, (severity, source) in raw.items():
        previous = prior_pressures.get(kind) or {}
        previous_severity = _bounded(previous.get("severity", severity))
        rate = severity - previous_severity
        tolerance = _bounded(500 + tolerance_bias.get(kind, 0) * 4, 250, 750)
        weight = _bounded(previous.get("individual_weight", 100), 1, 200)
        urgency = _bounded(max(0, severity - tolerance) * weight // 100)
        last_change_tick = int(previous.get("last_meaningful_change_tick", tick))
        if abs(rate) >= 20:
            last_change_tick = int(tick)
        pressures[kind] = {
            "schema_version": PRESSURE_SCHEMA_VERSION,
            "kind": kind,
            "severity": severity,
            "rate_of_change": rate,
            "predicted_severity": _bounded(severity + rate * 3),
            "tolerance": tolerance,
            "urgency": urgency,
            "recent_satisfaction": _bounded(max(0, previous_severity - severity)),
            "individual_weight": weight,
            "source": source,
            "last_meaningful_change_tick": last_change_tick,
        }
    out["pressures"] = pressures
    out["last_updated_tick"] = int(tick)
    return out


def _want_id(actor_id: str, want_type: str, target_id: str | None) -> str:
    return "want-" + canonical_hash([WANT_SCHEMA_VERSION, actor_id, want_type, target_id])[:16]


def refresh_wants(state: dict, actor_id: str, tick: int) -> dict:
    """Persist desired outcomes distinct from immediate pressure responses."""
    out = copy.deepcopy(state)
    wants = copy.deepcopy(state.get("wants") or {})
    generated = []
    p = state.get("pressures") or {}
    relationships = state.get("relationships") or {}
    commitments = state.get("commitments") or {}

    def propose(want_type, outcome, strength, sources, target_id=None):
        if strength <= 0:
            return
        generated.append((want_type, outcome, _bounded(strength), list(sources), target_id))

    propose("improve_shelter", "improve or repair a safe shelter", p.get("comfort", {}).get("urgency", 0), ["comfort", "exposure"])
    propose("store_surplus_food", "store surplus food for future scarcity", max(0, 500 - p.get("hunger", {}).get("severity", 0)), ["hunger_prediction"])
    propose("explore_unknown_area", "learn what lies beyond known ground", p.get("curiosity", {}).get("urgency", 0), ["curiosity"])
    propose("gain_safety", "reach or create a safer place", max(p.get("safety", {}).get("urgency", 0), p.get("fear", {}).get("urgency", 0)), ["safety", "fear"])

    for subject_id, relation in sorted(relationships.items()):
        if relation.get("kinship") or relation.get("affection", 0) >= 300:
            propose("stay_near_family", "remain near a valued person", relation.get("affection", 0), ["attachment"], subject_id)
        if relation.get("resentment", 0) >= 350 or relation.get("fear", 0) >= 350:
            propose("avoid_person", "avoid a feared or disliked person", max(relation.get("resentment", 0), relation.get("fear", 0)), ["relationship"], subject_id)

    for commitment_id, commitment in sorted(commitments.items()):
        if commitment.get("status") in ("active", "overdue", "disputed"):
            propose(
                "repay_obligation",
                commitment.get("obligation") or "fulfil an obligation",
                400 + p.get("perceived_obligation", {}).get("urgency", 0),
                ["commitment", commitment_id],
                commitment.get("beneficiary_id"),
            )

    active_ids = set()
    for want_type, outcome, strength, sources, target_id in generated:
        want_id = _want_id(actor_id, want_type, target_id)
        active_ids.add(want_id)
        prior = wants.get(want_id) or {}
        if prior.get("status") in ("fulfilled", "abandoned", "replaced"):
            continue
        wants[want_id] = {
            "schema_version": WANT_SCHEMA_VERSION,
            "want_id": want_id,
            "want_type": want_type,
            "desired_outcome": outcome,
            "target_id": target_id,
            "status": "active" if strength >= 150 else "dormant",
            "strength": strength,
            "source_pressures": sources,
            "created_tick": int(prior.get("created_tick", tick)),
            "last_updated_tick": int(tick),
            "fulfilled_tick": prior.get("fulfilled_tick"),
            "blocked_reason": prior.get("blocked_reason"),
            "replacement_want_id": prior.get("replacement_want_id"),
        }

    for want_id in sorted(set(wants) - active_ids):
        if wants[want_id].get("status") == "active":
            wants[want_id]["status"] = "dormant"
            wants[want_id]["last_updated_tick"] = int(tick)

    ranked = sorted(
        wants.items(),
        key=lambda pair: (
            pair[1].get("status") == "active",
            int(pair[1].get("strength", 0)),
            int(pair[1].get("last_updated_tick", 0)),
            pair[0],
        ),
        reverse=True,
    )[:LIMITS.candidate_goals_per_decision]
    out["wants"] = {key: value for key, value in sorted(ranked)}
    return out


def _memory_score(memory: dict, tick: int) -> int:
    age = max(0, int(tick) - int(memory.get("last_recalled_tick", memory.get("recorded_tick", 0))))
    return (
        int(memory.get("significance", 0)) * 4
        + int(memory.get("repetition", 0)) * 50
        + int(memory.get("confidence", 0))
        + int(memory.get("emotional_relevance", 0)) * 2
        + (200 if memory.get("direct_involvement") else 0)
        + int(memory.get("relationship_relevance", 0))
        - int(memory.get("contradiction_count", 0)) * 40
        - age * int(memory.get("decay_rate", 2))
    )


def _trim_memories(memories: dict, tick: int) -> dict:
    by_subject = {}
    for memory_id, memory in sorted(memories.items()):
        by_subject.setdefault(memory.get("subject_id") or "none", []).append((memory_id, memory))
    subject_trimmed = {}
    for rows in by_subject.values():
        keep = sorted(
            rows, key=lambda pair: (_memory_score(pair[1], tick), pair[0]), reverse=True,
        )[:LIMITS.memories_per_subject]
        subject_trimmed.update(keep)
    keep = sorted(
        subject_trimmed.items(),
        key=lambda pair: (_memory_score(pair[1], tick), pair[0]),
        reverse=True,
    )[:LIMITS.memories_per_entity]
    return {key: value for key, value in sorted(keep)}


def _upsert_memory(
    memories: dict,
    *,
    actor_id: str,
    kind: str,
    subject_id: str | None,
    tick: int,
    confidence: int,
    significance: int,
    emotional_relevance: int,
    direct_involvement: bool,
    relationship_relevance: int,
    source_event_id: str | None,
    observation_id: str | None,
    properties: dict | None,
) -> dict:
    memory_id = "memory-" + canonical_hash([
        MEMORY_SCHEMA_VERSION, actor_id, kind, subject_id,
    ])[:16]
    prior = memories.get(memory_id) or {}
    source_event_ids = list(prior.get("source_event_ids") or [])
    if source_event_id and source_event_id not in source_event_ids:
        source_event_ids.append(source_event_id)
    source_event_ids = source_event_ids[-8:]
    memories[memory_id] = {
        "schema_version": MEMORY_SCHEMA_VERSION,
        "memory_id": memory_id,
        "owner_id": actor_id,
        "memory_kind": kind,
        "subject_id": subject_id,
        "recorded_tick": int(prior.get("recorded_tick", tick)),
        "last_recalled_tick": int(tick),
        "repetition": min(999, int(prior.get("repetition", 0)) + 1),
        "significance": _bounded(max(significance, prior.get("significance", 0))),
        "confidence": _bounded(confidence),
        "emotional_relevance": _bounded(max(emotional_relevance, prior.get("emotional_relevance", 0))),
        "direct_involvement": bool(direct_involvement or prior.get("direct_involvement")),
        "contradiction_count": int(prior.get("contradiction_count", 0)),
        "decay_rate": int(prior.get("decay_rate", 2)),
        "relationship_relevance": _bounded(max(relationship_relevance, prior.get("relationship_relevance", 0))),
        "source_event_ids": source_event_ids,
        "observation_id": observation_id or prior.get("observation_id"),
        "properties": copy.deepcopy(properties or prior.get("properties") or {}),
        "acquired_event_id": prior.get("acquired_event_id"),
        "status": "active",
    }
    return memories[memory_id]


def merge_meaningful_memories(
    state: dict,
    *,
    actor_id: str,
    tick: int,
    observations: list[dict] | None = None,
    learned: list[dict] | None = None,
    action_result: dict | None = None,
) -> tuple[dict, list[dict]]:
    """Consolidate meaningful experience and enforce deterministic retention."""
    out = copy.deepcopy(state)
    memories = copy.deepcopy(state.get("memories") or {})
    learned_subjects = {
        item.get("subject") for item in (learned or []) if item.get("subject")
    }
    updated = []
    for observation in sorted(observations or [], key=lambda item: item.get("observation_id", "")):
        subject_id = observation.get("observed_subject_id")
        kind = observation.get("observation_type")
        properties = observation.get("properties") or {}
        meaningful_kind = None
        significance = 0
        emotional = 0
        relation = 0
        if kind == "danger" or (kind == "signal" and properties.get("signal_kind") in ("warning", "smoke", "noise")):
            meaningful_kind, significance, emotional = "threat_observed", 700, 650
        elif kind == "signal" and properties.get("signal_kind") in ("speech", "social"):
            meaningful_kind, significance, emotional, relation = "social_information", 520, 260, 420
        elif kind in ("tree", "carcass", "resource", "water_source", "storage", "tool") and subject_id in learned_subjects:
            meaningful_kind, significance = "resource_discovered", 420
        elif kind == "person" and (properties.get("appears_injured") or properties.get("apparent_urgent_need") in ("distressed", "critical")):
            meaningful_kind, significance, emotional, relation = "social_information", 500, 350, 300
        if not meaningful_kind:
            continue
        record = _upsert_memory(
            memories,
            actor_id=actor_id,
            kind=meaningful_kind,
            subject_id=subject_id,
            tick=tick,
            confidence=observation.get("confidence", 0),
            significance=significance,
            emotional_relevance=emotional,
            direct_involvement=False,
            relationship_relevance=relation,
            source_event_id=observation.get("source_event_id"),
            observation_id=observation.get("observation_id"),
            properties=properties,
        )
        updated.append(copy.deepcopy(record))

    if action_result:
        action = action_result.get("action") or {}
        status = action.get("status")
        if status in ("completed", "failed", "paused", "cancelled"):
            memory_kind = {
                "completed": "successful_action",
                "failed": "failed_action",
                "paused": "interruption",
                "cancelled": "interruption",
            }[status]
            significance = 430 if status == "completed" else 620
            record = _upsert_memory(
                memories,
                actor_id=actor_id,
                kind=memory_kind,
                subject_id=action.get("target_entity_id") or action.get("type"),
                tick=tick,
                confidence=1000,
                significance=significance,
                emotional_relevance=300 if status != "completed" else 120,
                direct_involvement=True,
                relationship_relevance=250 if action.get("participants") else 0,
                source_event_id=None,
                observation_id=None,
                properties={
                    "action_type": action.get("type"),
                    "action_status": status,
                    "failure_reason": action.get("invalidation_reason") or action.get("cancellation_reason"),
                },
            )
            updated.append(copy.deepcopy(record))

    # Decay confidence only for records not refreshed this tick. This is
    # canonical and bounded; accepted events remain the full historical source.
    refreshed = {item["memory_id"] for item in updated}
    for memory_id, memory in memories.items():
        if memory_id in refreshed:
            continue
        age = max(0, int(tick) - int(memory.get("last_recalled_tick", tick)))
        if age and age % 10 == 0:
            memory["confidence"] = _bounded(memory.get("confidence", 0) - memory.get("decay_rate", 2) * 5)
    out["memories"] = _trim_memories(memories, tick)
    return out, updated


def prepare_living_state(
    entity: dict,
    *,
    entity_id: str,
    tick: int,
    rng,
    knowledge: dict,
    perception_delta: dict,
    night: bool,
    weather: dict | None = None,
) -> dict:
    """Compatibility + pressure + memory + want pipeline for one activation."""
    state = compat_living_agent_state(entity.get("living_agent"), entity_id, tick, rng)
    state = derive_internal_pressures(
        entity, state, knowledge, perception_delta, tick, night=night, weather=weather,
    )
    state, _ = merge_meaningful_memories(
        state,
        actor_id=entity_id,
        tick=tick,
        observations=perception_delta.get("observations") or [],
        learned=[],
    )
    state = refresh_wants(state, entity_id, tick)
    return state
