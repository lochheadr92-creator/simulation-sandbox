"""Stage 8A - Emergent norms (bounded shelter-upkeep norm; smallest culture proof).

Agency model
------------
When a recognised Stage 7A group has re-adopted the Stage 7D
``maintain_shared_shelter`` goal at least ``NORM_FORMATION_COUNT`` distinct times
(counted by unique adoption instance, deduped per group by the goal's
``adopted_via_key``), a single canonical ``shelter_upkeep_norm`` crystallises for
that group. The norm influences member decisions (a read-only, survival-suppressed
nudge to an already-available REPAIR_SHELTER candidate for the norm shelter), is
inherited by later group members via current membership (transmission), and decays
then expires if the group stops re-adopting for ``NORM_DECAY_TICKS`` or dissolves.

The module is pure. It reads a pinned canonical frame (association + Stage 7D
group-goal registry + the existing group-norm registry), derives formations /
refreshes / expiries / per-group adoption-count updates, proposes the next bounded
group-norm registry, and leaves all mutation authority to Core.

Non-goals: no obedience, no command, no enforcement/punishment, no multiple norm
types, no per-individual teaching, no member/world mutation. Culture here is ONE
emergent, decision-affecting norm - nothing more (Stage 8B widens it).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from core.hashing import canonical_byte_composition, canonical_hash, canonical_json
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    ASSOCIATION_REGISTRY_VERSION,
    GROUP_CANDIDATE_VERSION,
)
from domains.group_goal_contracts import (
    GROUP_GOAL_REGISTRY_ID,
    GROUP_GOAL_REGISTRY_VERSION,
    GOAL_TYPE as GROUP_GOAL_TYPE,
)


GROUP_NORM_REGISTRY_ID = "group-norm-000"
GROUP_NORM_REGISTRY_VERSION = "group-norm-registry-v1"
GROUP_NORM_VERSION = "group-norm-v1"

NORM_TYPE = "shelter_upkeep_norm"
PROPOSAL_TYPE = "group_form_norm"
PROPOSAL_FAMILY = "group_norm"

# Determinism-visible constants (fixed in the Stage 8A contract, justified from the
# per-group adoption probe: all 7 recognised groups re-adopt >=3 times/1000 ticks,
# ceiling 4; adoptions recur in ~306-tick weather cycles).
NORM_FORMATION_COUNT = 3        # distinct re-adoptions before a norm crystallises
NORM_DECAY_TICKS = 300          # no-re-adoption window before the norm expires
NORM_MAX_STRENGTH = 1000        # strength at formation / refresh
NORM_WEAKENING_STRENGTH = 500   # active vs weakening display band (no behaviour cliff)


@dataclass(frozen=True)
class GroupNormLimits:
    norms: int = 16               # max norms retained in the registry (bounded state)
    formations_per_tick: int = 4  # max NEW norms formed per tick across all groups
    tracked_groups: int = 32      # max per-group adoption-progress records retained
    processed_norm_keys: int = 96
    causal_parents: int = 16
    provenance_refs: int = 16
    payload_target_bytes: int = 24 * 1024
    proposal_bytes: int = 32 * 1024


LIMITS = GroupNormLimits()


class GroupNormContractError(ValueError):
    """Raised when canonical Stage 8A state cannot be interpreted safely."""


# Stable reason codes
REASON_INVALID = "group_norm.invalid"
REASON_VERSION = "group_norm.invalid_version"
REASON_REGISTRY_ID = "group_norm.invalid_registry_id"
REASON_ASSOCIATION = "group_norm.association_registry_missing"
REASON_GROUP_GOAL = "group_norm.group_goal_missing"
REASON_STALE = "group_norm.stale_membership"
REASON_SCOPE = "group_norm.invalid_mutation_scope"
REASON_SCHEMA = "group_norm.invalid_registry_schema"
REASON_REVISION = "group_norm.invalid_revision"
REASON_PAYLOAD = "group_norm.payload_limit"
REASON_MUTATION = "group_norm.mutation_mismatch"
REASON_METADATA = "group_norm.metadata_mismatch"
REASON_LIMIT = "group_norm.norm_limit"
REASON_NORM = "group_norm.invalid_norm"


def empty_group_norm_registry(tick: int = 0) -> dict:
    return {
        "type": "group_norm_registry",
        "schema_version": GROUP_NORM_REGISTRY_VERSION,
        "revision": 0,
        "norms": {},
        "group_progress": {},
        "processed_norm_keys": [],
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
    }


def _bounded_ids(values, limit: int = LIMITS.provenance_refs) -> list[str]:
    return sorted(set(str(value) for value in (values or []) if value))[-limit:]


def group_norm_id(group_id: str, norm_type: str) -> str:
    if not group_id:
        raise ValueError("group norm identity requires a group id")
    return "group-norm-" + canonical_hash([
        GROUP_NORM_VERSION, str(group_id), str(norm_type),
    ])[:20]


def group_norm_key(formation: dict) -> str:
    return "normform-" + canonical_hash([
        GROUP_NORM_VERSION,
        formation.get("group_id"),
        formation.get("norm_type"),
        formation.get("formation_count"),
        formation.get("target_id"),
        formation.get("formed_via_key"),
        formation.get("tick"),
    ])[:24]


def _recognised_groups(association: dict) -> dict:
    return {
        gid: cand
        for gid, cand in sorted((association.get("group_candidates") or {}).items())
        if cand.get("schema_version") == GROUP_CANDIDATE_VERSION
        and cand.get("recognition_state") == "recognised"
        and cand.get("ever_recognised") is True
    }


def _group_active_goal(goal_registry: dict, group_id: str) -> dict | None:
    """The group's current active maintain_shared_shelter goal record, or None.

    One active goal per group is a Stage 7D invariant, so there is at most one.
    """
    best = None
    for goal in (goal_registry.get("goals") or {}).values():
        if not isinstance(goal, dict):
            continue
        if goal.get("group_id") != group_id:
            continue
        if goal.get("status") != "active" or goal.get("goal_type") != GROUP_GOAL_TYPE:
            continue
        if best is None or int(goal.get("last_updated_tick", 0)) > int(best.get("last_updated_tick", 0)):
            best = goal
    return best


def norm_strength(norm: dict, tick: int) -> int:
    """Lazily-derived remaining strength (avoids per-tick registry churn).

    Linear from NORM_MAX_STRENGTH at the last adoption to 0 at the decay deadline.
    Expired norms report 0.
    """
    if norm.get("status") != "active":
        return 0
    deadline = int(norm.get("decay_deadline_tick", tick))
    remaining = deadline - int(tick)
    if remaining <= 0:
        return 0
    return max(0, min(NORM_MAX_STRENGTH, NORM_MAX_STRENGTH * remaining // NORM_DECAY_TICKS))


def norm_display_status(norm: dict, tick: int) -> str:
    if norm.get("status") != "active":
        return "expired"
    if int(tick) >= int(norm.get("decay_deadline_tick", tick)):
        return "expired"
    return "active" if norm_strength(norm, tick) >= NORM_WEAKENING_STRENGTH else "weakening"


def _norm_is_live(norm: dict, tick: int) -> bool:
    """A committed-active norm whose decay deadline has not yet passed."""
    return (
        isinstance(norm, dict)
        and norm.get("status") == "active"
        and int(tick) < int(norm.get("decay_deadline_tick", tick))
    )


def derive_group_norm_changes(entities: dict, tick: int) -> dict:
    """Return the deterministic Stage 8A changes for this tick.

    {"progress_updates": {group_id: {adoption_count, last_counted_key,
                                     last_adoption_tick}},
     "formations": [formation_record, ...],
     "refreshes": [{"group_id": ..., "target_id": ...}, ...],
     "expiries": [norm_id, ...]}

    Reads the pinned association + Stage 7D group-goal registry + existing
    group-norm registry. Counting is by unique goal ``adopted_via_key`` per group
    (an O(1) ``last_counted_key`` comparison is exact because keys embed tick).
    """
    empty = {"progress_updates": {}, "formations": [], "refreshes": [], "expiries": []}
    association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    goal_registry = entities.get(GROUP_GOAL_REGISTRY_ID) or {}
    norm_registry = entities.get(GROUP_NORM_REGISTRY_ID) or {}
    if association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return empty
    if goal_registry.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
        return empty

    recognised = _recognised_groups(association)
    existing_norms = (norm_registry.get("norms") or {}) if isinstance(norm_registry, dict) else {}
    existing_progress = (norm_registry.get("group_progress") or {}) if isinstance(norm_registry, dict) else {}

    # 1. Per-group: observe a new adoption instance (adopted_via_key changed).
    progress_updates: dict = {}
    for group_id in recognised:
        goal = _group_active_goal(goal_registry, group_id)
        if goal is None:
            continue
        key = goal.get("adopted_via_key")
        if not key:
            continue
        prior = existing_progress.get(group_id) or {}
        if key != prior.get("last_counted_key"):
            progress_updates[group_id] = {
                "adoption_count": int(prior.get("adoption_count", 0)) + 1,
                "last_counted_key": key,
                "last_adoption_tick": int(tick),
            }

    # 2. Formations (count reaches threshold, no live norm) and refreshes
    #    (group with a live norm re-adopted -> reset its decay deadline).
    formations: list[dict] = []
    refreshes: list[dict] = []  # [{"group_id", "target_id"}]
    for group_id in sorted(progress_updates):
        upd = progress_updates[group_id]
        norm_id = group_norm_id(group_id, NORM_TYPE)
        existing_norm = existing_norms.get(norm_id)
        # A re-adoption REFRESHES any still-active norm (even one exactly at its
        # decay deadline this tick): the group re-affirmed the norm, so it is
        # revived, not formed-then-expired. Refreshing (rather than re-forming)
        # also keeps this group out of the expiry set below, so a single tick can
        # never both form a fresh record AND clobber it to expired via the stale
        # deadline of the same norm_id.
        goal = _group_active_goal(goal_registry, group_id)
        if isinstance(existing_norm, dict) and existing_norm.get("status") == "active":
            # Re-affirm the live norm, re-pointing it at the shelter the group is
            # currently keeping (the 7D target can shift if a different shared
            # shelter is the degraded one now); a stale target would keep the
            # influence boosting the wrong shelter.
            refreshes.append({
                "group_id": group_id,
                "target_id": (goal.get("target_id") if goal else None) or existing_norm.get("target_id"),
            })
            continue
        if upd["adoption_count"] < NORM_FORMATION_COUNT:
            continue
        target_id = goal.get("target_id") if goal else None
        if not target_id:
            continue
        candidate = recognised.get(group_id) or {}
        formation = {
            "schema_version": GROUP_NORM_VERSION,
            "norm_id": norm_id,
            "group_id": group_id,
            "group_type": candidate.get("group_type"),
            "norm_type": NORM_TYPE,
            "target_id": target_id,
            "formation_count": upd["adoption_count"],
            "formed_via_key": upd["last_counted_key"],
            "tick": int(tick),
            "decay_deadline_tick": int(tick) + NORM_DECAY_TICKS,
            "recognition_event_id": candidate.get("recognition_event_id"),
            "association_event_id": association.get("last_event_id"),
            "group_goal_event_id": goal_registry.get("last_event_id"),
        }
        formation["norm_key"] = group_norm_key(formation)
        formations.append(formation)

    # 3. Expiries: a live norm past its decay deadline (and not refreshed this
    #    tick) or whose group dissolved.
    refreshed_groups = {r["group_id"] for r in refreshes}
    expiries: list[str] = []
    for norm_id, norm in sorted(existing_norms.items()):
        if norm.get("status") != "active":
            continue
        group_id = norm.get("group_id")
        dissolved = group_id not in recognised
        past_deadline = int(tick) >= int(norm.get("decay_deadline_tick", tick))
        if dissolved or (past_deadline and group_id not in refreshed_groups):
            expiries.append(norm_id)

    formations.sort(key=lambda f: (f["group_id"], f["norm_key"]))
    return {
        "progress_updates": {gid: progress_updates[gid] for gid in sorted(progress_updates)},
        "formations": formations[:LIMITS.formations_per_tick],
        "refreshes": sorted(refreshes, key=lambda r: r["group_id"]),
        "expiries": sorted(set(expiries)),
    }


def _norm_record(formation: dict, tick: int) -> dict:
    return {
        "schema_version": GROUP_NORM_VERSION,
        "norm_id": formation["norm_id"],
        "group_id": formation["group_id"],
        "group_type": formation.get("group_type"),
        "norm_type": formation["norm_type"],
        "target_id": formation["target_id"],
        "status": "active",
        "formation_count": int(formation["formation_count"]),
        "formed_tick": int(tick),
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
        "last_adoption_tick": int(tick),
        "decay_deadline_tick": int(formation["decay_deadline_tick"]),
        "formed_via_key": formation["formed_via_key"],
        "created_event_id": None,
        "last_event_id": None,
        "pending_event_tick": int(tick),
        "pending_transition": "formed",
        "revision": 1,
    }


def _compact_registry(registry: dict) -> None:
    norms = registry.get("norms") or {}
    ranked = sorted(
        norms.items(),
        key=lambda pair: (
            0 if pair[1].get("status") == "active" else 1,
            -int(pair[1].get("last_updated_tick", 0)),
            pair[0],
        ),
    )[:LIMITS.norms]
    registry["norms"] = {key: norms[key] for key, _ in sorted(ranked)}
    # Progress compaction must NEVER evict a group that holds an ACTIVE norm: if it
    # did, that group's unchanged goal key would read as a fresh adoption next tick
    # and spuriously refresh the norm (defeating the decay rule). Active norms are
    # capped at LIMITS.norms (16) <= LIMITS.tracked_groups (32), so retaining all of
    # them plus the most-recent others always fits.
    active_norm_groups = {
        n.get("group_id") for n in registry["norms"].values() if n.get("status") == "active"
    }
    progress = registry.get("group_progress") or {}
    ranked_progress = sorted(
        progress.items(),
        key=lambda pair: (
            0 if pair[0] in active_norm_groups else 1,
            -int(pair[1].get("last_adoption_tick", 0)),
            pair[0],
        ),
    )[:LIMITS.tracked_groups]
    registry["group_progress"] = {key: progress[key] for key, _ in sorted(ranked_progress)}
    registry["processed_norm_keys"] = list(
        registry.get("processed_norm_keys") or []
    )[-LIMITS.processed_norm_keys:]


def advance_group_norm_registry(
    existing: dict | None,
    changes: dict,
    tick: int,
) -> tuple[dict, list[dict]]:
    if existing:
        if existing.get("schema_version") != GROUP_NORM_REGISTRY_VERSION:
            raise GroupNormContractError(
                f"unsupported group norm schema: {existing.get('schema_version')}"
            )
        registry = copy.deepcopy(existing)
    else:
        registry = empty_group_norm_registry(tick)

    norms = copy.deepcopy(registry.get("norms") or {})
    progress = copy.deepcopy(registry.get("group_progress") or {})
    processed = list(registry.get("processed_norm_keys") or [])
    processed_set = set(processed)
    transitions: list[dict] = []

    # Per-group adoption-count updates.
    for group_id in sorted(changes.get("progress_updates") or {}):
        progress[group_id] = copy.deepcopy(changes["progress_updates"][group_id])

    # Formations.
    for formation in sorted(changes.get("formations") or [], key=lambda f: f["norm_key"]):
        key = formation["norm_key"]
        if key in processed_set:
            continue
        norm_id = formation["norm_id"]
        norms[norm_id] = _norm_record(formation, tick)
        processed.append(key)
        processed_set.add(key)
        transitions.append({
            "norm_id": norm_id,
            "group_id": formation["group_id"],
            "target_id": formation["target_id"],
            "kind": "formed",
            "norm_key": key,
        })

    # Refreshes: reset the decay deadline for a live norm whose group re-adopted,
    # re-pointing it at the shelter the group is currently keeping.
    for refresh in sorted(changes.get("refreshes") or [], key=lambda r: r["group_id"]):
        group_id = refresh["group_id"]
        norm_id = group_norm_id(group_id, NORM_TYPE)
        norm = norms.get(norm_id)
        if not norm or norm.get("status") != "active":
            continue
        norm = copy.deepcopy(norm)
        if refresh.get("target_id"):
            norm["target_id"] = refresh["target_id"]
        norm["last_adoption_tick"] = int(tick)
        norm["decay_deadline_tick"] = int(tick) + NORM_DECAY_TICKS
        norm["last_updated_tick"] = int(tick)
        norm["pending_event_tick"] = int(tick)
        norm["pending_transition"] = "refreshed"
        norm["revision"] = int(norm.get("revision", 0)) + 1
        norms[norm_id] = norm
        transitions.append({
            "norm_id": norm_id,
            "group_id": norm.get("group_id"),
            "target_id": norm.get("target_id"),
            "kind": "refreshed",
            "norm_key": norm.get("formed_via_key"),
        })

    # Expiries.
    for norm_id in sorted(set(changes.get("expiries") or [])):
        norm = norms.get(norm_id)
        if not norm or norm.get("status") != "active":
            continue
        norm = copy.deepcopy(norm)
        norm["status"] = "expired"
        norm["last_updated_tick"] = int(tick)
        norm["pending_event_tick"] = int(tick)
        norm["pending_transition"] = "expired"
        norm["revision"] = int(norm.get("revision", 0)) + 1
        norms[norm_id] = norm
        transitions.append({
            "norm_id": norm_id,
            "group_id": norm.get("group_id"),
            "target_id": norm.get("target_id"),
            "kind": "expired",
            "norm_key": norm.get("formed_via_key"),
        })

    registry["norms"] = {key: norms[key] for key in sorted(norms)}
    registry["group_progress"] = {key: progress[key] for key in sorted(progress)}
    registry["processed_norm_keys"] = processed
    registry["revision"] = int(registry.get("revision", 0)) + 1
    registry["last_updated_tick"] = int(tick)
    _compact_registry(registry)
    transitions.sort(key=lambda t: (t["kind"], t["norm_id"]))
    return registry, transitions


def _has_changes(changes: dict) -> bool:
    return bool(
        (changes.get("progress_updates"))
        or (changes.get("formations"))
        or (changes.get("refreshes"))
        or (changes.get("expiries"))
    )


def _proposed_registry(proposal: dict) -> dict | None:
    mutation = proposal.get("mutation") or {}
    return (
        (mutation.get("new_entities") or {}).get(GROUP_NORM_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(GROUP_NORM_REGISTRY_ID)
    )


def build_group_norm_proposal(
    entities: dict,
    tick: int,
    *,
    changes: dict | None = None,
) -> dict | None:
    association = entities.get(ASSOCIATION_REGISTRY_ID)
    goal_registry = entities.get(GROUP_GOAL_REGISTRY_ID)
    if not isinstance(association, dict) or association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return None
    if not isinstance(goal_registry, dict) or goal_registry.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
        return None
    existing = entities.get(GROUP_NORM_REGISTRY_ID)
    if changes is None:
        changes = derive_group_norm_changes(entities, tick)
    if not _has_changes(changes):
        return None

    registry, transitions = advance_group_norm_registry(existing, changes, tick)

    parents = []
    for formation in changes.get("formations") or []:
        for key in ("group_goal_event_id", "association_event_id", "recognition_event_id"):
            if formation.get(key):
                parents.append(formation[key])
    if not parents:
        if goal_registry.get("last_event_id"):
            parents.append(goal_registry["last_event_id"])
        if association.get("last_event_id"):
            parents.append(association["last_event_id"])
    parent_ids = _bounded_ids(parents, LIMITS.causal_parents)
    if not parent_ids:
        return None

    if existing:
        mutation = {"entity_updates": {GROUP_NORM_REGISTRY_ID: registry}, "new_entities": {}}
        prior_revision = int(existing.get("revision", 0))
        preconditions = [{
            "entity_id": GROUP_NORM_REGISTRY_ID, "field": "revision",
            "op": "eq", "value": prior_revision,
        }]
    else:
        mutation = {"new_entities": {GROUP_NORM_REGISTRY_ID: registry}, "entity_updates": {}}
        prior_revision = None
        preconditions = []
    preconditions.append({
        "entity_id": ASSOCIATION_REGISTRY_ID, "field": "revision",
        "op": "eq", "value": int(association.get("revision", 0)),
    })
    preconditions.append({
        "entity_id": GROUP_GOAL_REGISTRY_ID, "field": "revision",
        "op": "eq", "value": int(goal_registry.get("revision", 0)),
    })

    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    metadata = {
        "schema_version": GROUP_NORM_VERSION,
        "registry_id": GROUP_NORM_REGISTRY_ID,
        "association_registry_revision": int(association.get("revision", 0)),
        "group_goal_registry_revision": int(goal_registry.get("revision", 0)),
        "prior_revision": prior_revision,
        "next_revision": int(registry["revision"]),
        "changes": copy.deepcopy(changes),
        "formation_keys": [f["norm_key"] for f in (changes.get("formations") or [])],
        "transitions": copy.deepcopy(transitions),
        "norm_count": len(registry["norms"]),
        "active_norm_count": sum(
            1 for n in registry["norms"].values() if n.get("status") == "active"
        ),
        "payload_bytes": payload_bytes,
    }
    return {
        "proposal_family": PROPOSAL_FAMILY,
        "proposal_type": PROPOSAL_TYPE,
        "proposer_engine_id": "group_norm",
        "proposer_engine_version": "1.0.0",
        "entity_id": GROUP_NORM_REGISTRY_ID,
        "causal_parent_event_ids": parent_ids,
        "is_exogenous": False,
        "requested_time": int(tick),
        "phase": "agent",
        # Commit before Stage 7D group_goal (88) / 7A / 7B revision churn.
        "engine_priority": 87,  # before group_goal (88), group_state (89), association (90)
        "touched_scope": [GROUP_NORM_REGISTRY_ID, GROUP_GOAL_REGISTRY_ID, ASSOCIATION_REGISTRY_ID],
        "preconditions": preconditions,
        "mutation": mutation,
        "group_norm_update": metadata,
        "explanation": (
            f"group norm registry revision {registry['revision']}; "
            f"formations={len(changes.get('formations') or [])} "
            f"refreshes={len(changes.get('refreshes') or [])} "
            f"expiries={len(changes.get('expiries') or [])}"
        ),
    }


def validate_group_norm_proposal(proposal: dict, entities: dict) -> str | None:
    """Core-owned validation. None means ok; non-None is a stable reason code."""
    metadata = proposal.get("group_norm_update")
    if metadata is None:
        # A proposal that writes the norm registry WITHOUT the group_norm_update
        # marker must not slip past norm validation (marker-gated bypass).
        mutation = proposal.get("mutation") or {}
        if (GROUP_NORM_REGISTRY_ID in (mutation.get("new_entities") or {})
                or GROUP_NORM_REGISTRY_ID in (mutation.get("entity_updates") or {})):
            return REASON_INVALID
        return None
    if not isinstance(metadata, dict) or metadata.get("schema_version") != GROUP_NORM_VERSION:
        return REASON_VERSION
    if proposal.get("entity_id") != GROUP_NORM_REGISTRY_ID or metadata.get("registry_id") != GROUP_NORM_REGISTRY_ID:
        return REASON_REGISTRY_ID

    association = entities.get(ASSOCIATION_REGISTRY_ID)
    goal_registry = entities.get(GROUP_GOAL_REGISTRY_ID)
    if not isinstance(association, dict) or association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return REASON_ASSOCIATION
    if not isinstance(goal_registry, dict) or goal_registry.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
        return REASON_GROUP_GOAL
    if int(metadata.get("association_registry_revision", -1)) != int(association.get("revision", -2)):
        return REASON_STALE
    if int(metadata.get("group_goal_registry_revision", -1)) != int(goal_registry.get("revision", -2)):
        return REASON_STALE

    mutation = proposal.get("mutation") or {}
    new_entities = mutation.get("new_entities") or {}
    entity_updates = mutation.get("entity_updates") or {}
    removed = mutation.get("removed_entities") or []
    if set(new_entities) - {GROUP_NORM_REGISTRY_ID} or set(entity_updates) - {GROUP_NORM_REGISTRY_ID} or removed:
        return REASON_SCOPE
    # The registry must live in EXACTLY ONE of new_entities / entity_updates.
    # Otherwise a forged entity_updates overlay could ride in behind the validated
    # new_entities payload (_proposed_registry only inspects one) and still be
    # applied by apply_mutation at commit time.
    if GROUP_NORM_REGISTRY_ID in new_entities and GROUP_NORM_REGISTRY_ID in entity_updates:
        return REASON_SCOPE
    registry = _proposed_registry(proposal)
    if not isinstance(registry, dict) or registry.get("schema_version") != GROUP_NORM_REGISTRY_VERSION:
        return REASON_SCHEMA

    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    if payload_bytes > LIMITS.proposal_bytes or int(metadata.get("payload_bytes", -1)) != payload_bytes:
        return REASON_PAYLOAD

    existing = entities.get(GROUP_NORM_REGISTRY_ID)
    if existing and GROUP_NORM_REGISTRY_ID in new_entities:
        return REASON_REVISION
    expected_revision = int(existing.get("revision", 0)) + 1 if existing else 1
    if int(registry.get("revision", -1)) != expected_revision:
        return REASON_REVISION
    if metadata.get("prior_revision") != (int(existing.get("revision", 0)) if existing else None):
        return REASON_REVISION
    if int(metadata.get("next_revision", -1)) != expected_revision:
        return REASON_REVISION

    required = {
        (c.get("entity_id"), c.get("field"), c.get("op"), c.get("value"))
        for c in (proposal.get("preconditions") or [])
    }
    if (ASSOCIATION_REGISTRY_ID, "revision", "eq", int(association.get("revision", 0))) not in required:
        return REASON_STALE
    if (GROUP_GOAL_REGISTRY_ID, "revision", "eq", int(goal_registry.get("revision", 0))) not in required:
        return REASON_STALE
    if existing and (GROUP_NORM_REGISTRY_ID, "revision", "eq", int(existing.get("revision", 0))) not in required:
        return REASON_REVISION

    changes = metadata.get("changes")
    if not isinstance(changes, dict):
        return REASON_METADATA
    formations = changes.get("formations")
    if not isinstance(formations, list) or not isinstance(changes.get("expiries"), list):
        return REASON_METADATA
    if len(formations) > LIMITS.formations_per_tick:
        return REASON_LIMIT
    # One formation per group per tick (one norm per group).
    formation_group_ids = [f.get("group_id") for f in formations if isinstance(f, dict)]
    if len(formation_group_ids) != len(set(formation_group_ids)):
        return REASON_LIMIT

    # Re-derive from the current canonical frame and require CANONICAL BYTE
    # equality (not Python ==, under which True == 1 while their canonical JSON
    # differs) - a forged norm_id / strength / count / target / deadline, or a
    # type-variant scalar, cannot survive a byte-exact check against the freshly
    # derived changes.
    derived = derive_group_norm_changes(entities, int(proposal.get("requested_time", 0)))
    if canonical_json(changes) != canonical_json(derived):
        return REASON_METADATA
    formation_keys = [f.get("norm_key") for f in formations]
    if len(formation_keys) != len(set(formation_keys)):
        return REASON_METADATA
    if list(metadata.get("formation_keys") or []) != formation_keys:
        return REASON_METADATA
    # Defense-in-depth: explicit identity / grounding invariants on each formation.
    for formation in formations:
        if formation.get("norm_type") != NORM_TYPE:
            return REASON_NORM
        if formation.get("norm_id") != group_norm_id(formation.get("group_id"), NORM_TYPE):
            return REASON_NORM
        if int(formation.get("formation_count", 0)) < NORM_FORMATION_COUNT:
            return REASON_NORM
        if int(formation.get("decay_deadline_tick", -1)) != int(formation.get("tick", 0)) + NORM_DECAY_TICKS:
            return REASON_NORM
        if not formation.get("target_id"):
            return REASON_NORM

    # Advance the TRUSTED freshly-derived changes (not the submission) and require
    # the submitted registry + transitions to be byte-exact against the result.
    try:
        expected_registry, transitions = advance_group_norm_registry(
            existing, derived, int(proposal.get("requested_time", 0)),
        )
    except (TypeError, ValueError, GroupNormContractError):
        return REASON_SCHEMA
    if canonical_json(expected_registry) != canonical_json(registry):
        return REASON_MUTATION
    if canonical_json(metadata.get("transitions")) != canonical_json(transitions):
        return REASON_METADATA
    if int(metadata.get("norm_count", -1)) != len(registry.get("norms") or {}):
        return REASON_METADATA
    if int(metadata.get("active_norm_count", -1)) != sum(
        1 for n in (registry.get("norms") or {}).values() if n.get("status") == "active"
    ):
        return REASON_METADATA
    if len(registry.get("norms") or {}) > LIMITS.norms:
        return REASON_LIMIT

    forbidden = {"inventory", "authority", "obedience", "orders", "law", "command", "punishment"}
    active_group_ids: list[str] = []
    for norm in (registry.get("norms") or {}).values():
        if norm.get("schema_version") != GROUP_NORM_VERSION or forbidden & set(norm):
            return REASON_NORM
        if norm.get("norm_type") != NORM_TYPE:
            return REASON_NORM
        if norm.get("norm_id") != group_norm_id(norm.get("group_id"), NORM_TYPE):
            return REASON_NORM
        if int(norm.get("decay_deadline_tick", -1)) != int(norm.get("last_adoption_tick", 0)) + NORM_DECAY_TICKS:
            return REASON_NORM
        if norm.get("status") == "active":
            active_group_ids.append(norm.get("group_id"))
    # One active norm per group in the resulting registry.
    if len(active_group_ids) != len(set(active_group_ids)):
        return REASON_LIMIT
    return None


def stamp_group_norm_provenance(proposal: dict, mutation: dict, event_id: str) -> None:
    metadata = proposal.get("group_norm_update")
    if not isinstance(metadata, dict):
        return
    registry = (
        (mutation.get("new_entities") or {}).get(GROUP_NORM_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(GROUP_NORM_REGISTRY_ID)
    )
    if not isinstance(registry, dict):
        return
    tick = int(proposal.get("requested_time", 0))
    for norm in (registry.get("norms") or {}).values():
        if int(norm.get("pending_event_tick") or -1) == tick:
            if norm.get("created_event_id") is None:
                norm["created_event_id"] = event_id
            norm["last_event_id"] = event_id
            norm["pending_event_tick"] = None
            norm["pending_transition"] = None
    metadata["accepted_event_id"] = event_id


def group_norm_diagnostics(registry: dict, tick: int) -> dict:
    norms = registry.get("norms") or {}
    return {
        "schema_version": "group-norm-diagnostics-v1",
        "tick": int(tick),
        "registry_revision": int(registry.get("revision", 0)),
        "norm_count": len(norms),
        "active_norm_count": sum(1 for n in norms.values() if n.get("status") == "active"),
        "weakening_norm_count": sum(
            1 for n in norms.values() if norm_display_status(n, tick) == "weakening"
        ),
        "processed_norm_count": len(registry.get("processed_norm_keys") or []),
        "tracked_group_count": len(registry.get("group_progress") or {}),
        "caps": {
            "norms": LIMITS.norms,
            "formations_per_tick": LIMITS.formations_per_tick,
            "tracked_groups": LIMITS.tracked_groups,
            "processed_norm_keys": LIMITS.processed_norm_keys,
            "causal_parents": LIMITS.causal_parents,
            "payload_target_bytes": LIMITS.payload_target_bytes,
            "proposal_bytes": LIMITS.proposal_bytes,
        },
        "constants": {
            "norm_formation_count": NORM_FORMATION_COUNT,
            "norm_decay_ticks": NORM_DECAY_TICKS,
            "norm_weakening_strength": NORM_WEAKENING_STRENGTH,
        },
    }


def group_norm_capacity_diagnostics(registry: dict) -> dict:
    provenance_fields = {
        "accepted_event_id", "created_event_id", "last_event_id",
        "recognition_event_id", "association_event_id", "group_goal_event_id",
    }

    def classify(path: tuple, _value, _is_key: bool) -> str | None:
        fields = {part for part in path if isinstance(part, str)}
        if "processed_norm_keys" in fields:
            return "processed_norm_key_bytes"
        if "group_progress" in fields:
            return "progress_tracking_bytes"
        if fields & provenance_fields:
            return "provenance_reference_bytes"
        if "norms" in fields:
            return "current_truth_bytes"
        return None

    composition = {
        "current_truth_bytes": 0,
        "processed_norm_key_bytes": 0,
        "progress_tracking_bytes": 0,
        "provenance_reference_bytes": 0,
        "other_structural_overhead_bytes": 0,
    }
    composition.update(canonical_byte_composition(registry, classify))
    return {
        "total_serialized_bytes": len(canonical_json(registry).encode("utf-8")),
        **composition,
    }


def group_norm_current_truth_summary(registry: dict, tick: int = 0) -> dict:
    norms = {}
    for nid, norm in sorted((registry.get("norms") or {}).items()):
        norms[nid] = {
            "group_id": norm.get("group_id"),
            "norm_type": norm.get("norm_type"),
            "target_id": norm.get("target_id"),
            "status": norm.get("status"),
            "display_status": norm_display_status(norm, tick),
            "strength": norm_strength(norm, tick),
            "formation_count": int(norm.get("formation_count", 0)),
            "formed_tick": norm.get("formed_tick"),
            "last_adoption_tick": norm.get("last_adoption_tick"),
            "decay_deadline_tick": norm.get("decay_deadline_tick"),
            "revision": int(norm.get("revision", 0)),
        }
    return {"norms": norms}
