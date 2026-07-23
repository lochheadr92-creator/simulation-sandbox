"""Stage 8B Leg 1 - Norm carriage and transmission (culture outlives its
originators). Contract: memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md.

Agency model
------------
After Stage 8A, norm eligibility was a property of *current group membership*.
This module makes it a property of the *person*: exactly one source of truth
(carriage, never membership) grants the Stage 8A norm-influence nudge.

  * **Formation backfill.** When a ``shelter_upkeep_norm`` forms for a group
    (Stage 8A ``group_form_norm``), this module reads the Stage 7D goal that
    drove it and grants carriage to its ``supporter_ids`` - the members who
    actually voted for it. Members present who did not support it are NOT
    backfilled; they are the organically-produced non-carriers transmission
    can reach. This happens once per norm (idempotent by ``backfilled_norm_ids``),
    the first tick this module observes the norm exists in a committed
    ``group-norm-000``.
  * **Transmission.** A living, current, non-carrier member of a norm-holding
    group who directs a qualifying accepted social action (the Constants
    Registry's ``TRANSMISSION_QUALIFYING_EVENT_TYPES``) at a current carrier of
    that norm becomes a carrier themselves, on the
    ``TRANSMISSION_COUNT``-th such qualifying interaction. The trigger rides
    the existing accepted-action seam already used by Stage 7A
    (``entity["action"]``/``accepted_event_id``; see
    ``association_contracts.py``'s ``_accepted_action``) - no second
    communication engine is introduced.

Carriage is deliberately independent of current membership: a carrier who
leaves the group keeps what they learned (no contract specifies forgetting),
and a post-formation supporter is NOT automatically a carrier - the only path
in is formation backfill (once) or transmission.

Commit ordering: this module runs at ``engine_priority = 86`` - one below
``group_norm`` (87) - so its pinned ``group-goal-000`` (88) and
``group-norm-000`` (87) revisions are revalidated before those domains' own
proposals get a chance to bump them this same tick (avoiding a same-tick
stale-precondition rejection, one layer deeper than 8A's own fix). Like every
domain in this kernel, it evaluates from the single ``entities_view`` frozen at
the end of the *previous* tick regardless of priority (see
``core/kernel.py:73``) - ``engine_priority`` governs commit/validation order
only, never proposal-building visibility. A norm formed at tick T is
backfilled at T+1; a qualifying social action accepted at tick T is detected
and turned into a transmission event at T+1.

Non-goals (this leg): teaching (carrier-initiated transmission - zero organic
evidence), carriage expiry/forgetting, generational transfer, multiple
transmission mechanisms, widening the qualifying-event-type set beyond what is
in the Constants Registry below.
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
from domains.group_norm_contracts import (
    GROUP_NORM_REGISTRY_ID,
    GROUP_NORM_REGISTRY_VERSION,
    NORM_TYPE as GROUP_NORM_TYPE,
    _norm_is_live,
)


GROUP_CARRIAGE_REGISTRY_ID = "group-carriage-000"
GROUP_CARRIAGE_REGISTRY_VERSION = "group-carriage-registry-v1"
GROUP_CARRIAGE_VERSION = "group-carriage-v1"

PROPOSAL_TYPE = "group_carry_norm"
PROPOSAL_FAMILY = "group_carriage"

SOURCE_BACKFILL = "formation_backfill"
SOURCE_TRANSMISSION = "transmission"

# Constants Registry (confirmed contract, riders a/b/c). Extension is a
# constants change plus a contract-amendment note - never a rewrite of the
# detection code below.
TRANSMISSION_COUNT = 1  # the Nth qualifying interaction transmits; N=1 is the
# measured floor (exactly one qualifying interaction exists in the standard
# 1,000-tick collective_groups horizon - see the contract's probe evidence).
# At N=1 no per-(norm, person) counter is needed: the first qualifying
# interaction transmits immediately. A future N>1 would need a bounded
# `transmission_progress` sub-registry mirroring group_norm's `group_progress`
# pattern - do not hand-roll counting logic into the trigger check below.
TRANSMISSION_QUALIFYING_EVENT_TYPES = ("social_request_help",)
# A data constant (tuple), not a structural code assumption - the detection
# code below checks membership in this tuple, it never spells out the string.


@dataclass(frozen=True)
class GroupCarriageLimits:
    carriers: int = 128           # norms cap (16) x members_per_candidate cap (8)
    backfilled_norm_ids: int = 16  # 1:1 with the norms cap (one backfill per norm)
    processed_transmission_keys: int = 96
    new_records_per_tick: int = 64  # >= formations_per_tick(4) x members_per_candidate(8)
    causal_parents: int = 16
    provenance_refs: int = 16
    payload_target_bytes: int = 24 * 1024
    proposal_bytes: int = 32 * 1024


LIMITS = GroupCarriageLimits()


class GroupCarriageContractError(ValueError):
    """Raised when canonical Stage 8B Leg 1 state cannot be interpreted safely."""


# Stable reason codes
REASON_INVALID = "group_carriage.invalid"
REASON_VERSION = "group_carriage.invalid_version"
REASON_REGISTRY_ID = "group_carriage.invalid_registry_id"
REASON_ASSOCIATION = "group_carriage.association_registry_missing"
REASON_GROUP_GOAL = "group_carriage.group_goal_missing"
REASON_GROUP_NORM = "group_carriage.group_norm_missing"
REASON_STALE = "group_carriage.stale_membership"
REASON_SCOPE = "group_carriage.invalid_mutation_scope"
REASON_SCHEMA = "group_carriage.invalid_registry_schema"
REASON_REVISION = "group_carriage.invalid_revision"
REASON_PAYLOAD = "group_carriage.payload_limit"
REASON_MUTATION = "group_carriage.mutation_mismatch"
REASON_METADATA = "group_carriage.metadata_mismatch"
REASON_LIMIT = "group_carriage.carrier_limit"
REASON_CARRIER = "group_carriage.invalid_carrier"

FORBIDDEN_FIELDS = frozenset({
    "inventory", "authority", "obedience", "orders", "law", "command", "punishment",
})


def empty_group_carriage_registry(tick: int = 0) -> dict:
    return {
        "type": "group_carriage_registry",
        "schema_version": GROUP_CARRIAGE_REGISTRY_VERSION,
        "revision": 0,
        "carriers": {},
        "backfilled_norm_ids": [],
        "processed_transmission_keys": [],
        "created_tick": int(tick),
        "last_updated_tick": int(tick),
    }


def _bounded_ids(values, limit: int = LIMITS.provenance_refs) -> list[str]:
    return sorted(set(str(value) for value in (values or []) if value))[-limit:]


def carrier_key(norm_id: str, person_id: str) -> str:
    return f"{norm_id}:{person_id}"


def split_carrier_key(key: str) -> tuple[str, str]:
    """Inverse of ``carrier_key``: (norm_id, person_id).

    The key is the record's single stored copy of both ids (Leg 1 contract
    amendment, F2c): they are NOT repeated inside the record body. A norm_id
    is ``"group-norm-" + hex`` and a person_id is ``"person-NNN"``, neither of
    which contains ``":"``, so one rpartition is exact and lossless.
    """
    norm_id, _sep, person_id = key.rpartition(":")
    return norm_id, person_id


def carrier_norm_id(key: str) -> str:
    return split_carrier_key(key)[0]


def carrier_person_id(key: str) -> str:
    return split_carrier_key(key)[1]


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

    Mirrors group_norm_contracts._group_active_goal exactly (each contracts
    module owns its small derivations rather than cross-importing another
    module's private helper - the established convention in this codebase:
    group_collective_contracts, group_goal_contracts, group_norm_contracts,
    and group_state_contracts each define their own _recognised_groups too).
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


def _accepted_action(entity: dict) -> dict | None:
    """The entity's committed action, if any (mirrors association_contracts.py's
    ``_accepted_action`` - the same accepted-action seam Stage 7A already reads,
    not invented here)."""
    action = entity.get("action")
    if not isinstance(action, dict) or not action.get("accepted_event_id"):
        return None
    return action


def derive_group_carriage_changes(entities: dict, tick: int) -> dict:
    """Return the deterministic Stage 8B Leg 1 changes for this tick.

    {"backfills": [{"norm_id", "group_id", "person_id", "source_event_id"}],
     "transmissions": [{"norm_id", "group_id", "person_id", "learned_from",
                         "via_event_id", "carrier_key"}]}

    Reads the pinned association + Stage 7D group-goal registry + Stage 8A
    group-norm registry + the existing carriage registry (for idempotence).
    """
    empty = {"backfills": [], "transmissions": []}
    association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    goal_registry = entities.get(GROUP_GOAL_REGISTRY_ID) or {}
    norm_registry = entities.get(GROUP_NORM_REGISTRY_ID) or {}
    carriage_registry = entities.get(GROUP_CARRIAGE_REGISTRY_ID) or {}
    if association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return empty
    if goal_registry.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
        return empty
    if norm_registry.get("schema_version") != GROUP_NORM_REGISTRY_VERSION:
        return empty

    recognised = _recognised_groups(association)
    norms = norm_registry.get("norms") or {}
    existing_carriers = (
        (carriage_registry.get("carriers") or {}) if isinstance(carriage_registry, dict) else {}
    )
    backfilled_norm_ids = set(
        (carriage_registry.get("backfilled_norm_ids") or []) if isinstance(carriage_registry, dict) else []
    )
    processed_transmission_keys = set(
        (carriage_registry.get("processed_transmission_keys") or [])
        if isinstance(carriage_registry, dict) else []
    )

    # 1. Formation backfill: a norm not yet backfilled grants carriage to the
    #    supporters of the goal that currently drives it (the same one that
    #    triggered its formation, given the observed adoption cadence is far
    #    longer than the one-tick lag this module reads with). One-time,
    #    idempotent by backfilled_norm_ids - never re-synced to a later
    #    re-adoption's supporter set.
    backfills: list[dict] = []
    for norm_id, norm in sorted(norms.items()):
        if norm.get("norm_type") != GROUP_NORM_TYPE:
            continue
        if norm_id in backfilled_norm_ids:
            continue
        group_id = norm.get("group_id")
        goal = _group_active_goal(goal_registry, group_id)
        if goal is None:
            continue  # retry next tick; nothing to backfill from yet
        supporters = sorted(set(goal.get("supporter_ids") or []))
        if not supporters:
            continue
        source_event_id = norm.get("last_event_id") or norm.get("created_event_id")
        for person_id in supporters:
            backfills.append({
                "norm_id": norm_id,
                "group_id": group_id,
                "person_id": person_id,
                "source_event_id": source_event_id,
            })

    # 2. Transmission: for each live norm, each current living non-carrier
    #    member whose committed action (as of the frame this module reads -
    #    always one tick behind the action's own accepted tick) is a
    #    qualifying interaction directed at a current carrier of that norm.
    transmissions: list[dict] = []
    for norm_id, norm in sorted(norms.items()):
        if norm.get("norm_type") != GROUP_NORM_TYPE or not _norm_is_live(norm, tick):
            continue
        group_id = norm.get("group_id")
        group = recognised.get(group_id) or {}
        member_ids = set(group.get("member_ids") or [])
        carrier_person_ids = {
            carrier_person_id(key) for key in existing_carriers
            if carrier_norm_id(key) == norm_id
        }
        for person_id in sorted(member_ids - carrier_person_ids):
            key = carrier_key(norm_id, person_id)
            if key in processed_transmission_keys:
                continue
            person = entities.get(person_id)
            if not isinstance(person, dict) or person.get("type") != "person" or not person.get("alive", True):
                continue
            action = _accepted_action(person)
            if not action:
                continue
            committed_event_type = f"social_{action.get('type')}"
            if committed_event_type not in TRANSMISSION_QUALIFYING_EVENT_TYPES:
                continue
            target_id = action.get("target_entity_id")
            if target_id not in carrier_person_ids:
                continue
            transmissions.append({
                "norm_id": norm_id,
                "group_id": group_id,
                "person_id": person_id,
                "learned_from": target_id,
                "via_event_id": action.get("accepted_event_id"),
                "carrier_key": key,
            })

    backfills.sort(key=lambda b: (b["norm_id"], b["person_id"]))
    transmissions.sort(key=lambda t: (t["norm_id"], t["person_id"]))
    return {
        "backfills": backfills[:LIMITS.new_records_per_tick],
        "transmissions": transmissions[:LIMITS.new_records_per_tick],
    }


def _carrier_record(entry: dict, source: str, tick: int) -> dict:
    """Build the stored record.

    Leg 1 contract amendment (F2c, byte slimming): ``carrier_id``,
    ``norm_id`` and ``person_id`` are deliberately NOT stored in the record
    body — all three are recoverable from the registry key that indexes this
    record (``split_carrier_key``), and storing them again tripled the
    per-record cost of the two longest strings in the schema. Provenance is
    untouched: ``via_event_id`` (the causal event), ``created_event_id`` /
    ``last_event_id`` (the commit event), ``learned_from`` and
    ``learned_tick`` all remain, each stored exactly once.

    Leg 1 contract amendment 2 (invariant-4 headroom): no ``pending_*``
    staging keys. Unlike ``group_norm`` (which reuses that marker on refresh
    /expiry of an EXISTING record), carriage records are write-once, so the
    proposal's own ``transitions`` list already identifies exactly which
    registry keys are new this tick — ``stamp_group_carriage_provenance``
    reads that instead of a marker embedded in the record itself.
    """
    return {
        "schema_version": GROUP_CARRIAGE_VERSION,
        "group_id": entry["group_id"],
        "source": source,
        "learned_from": entry.get("learned_from"),
        "via_event_id": entry.get("via_event_id") or entry.get("source_event_id"),
        "learned_tick": int(tick),
        "revision": 1,
        "created_event_id": None,
        "last_event_id": None,
    }


def _has_changes(changes: dict) -> bool:
    return bool((changes.get("backfills")) or (changes.get("transmissions")))


def advance_group_carriage_registry(
    existing: dict | None,
    changes: dict,
    tick: int,
    *,
    known_norm_ids: set | None = None,
) -> tuple[dict, list[dict]]:
    """Advance the carriage registry.

    ``known_norm_ids`` is every norm_id present in the Stage 8A norm registry
    this frame, at ANY status. Leg 1 contract amendment (F3): the
    ``backfilled_norm_ids`` tracking set is pruned to these rather than
    truncated lexicographically. The old ``sorted(set(...))[-cap:]`` evicted by
    id ordering while ``group_norm`` compacts by (active, recency) - a
    mismatch under which an ACTIVE norm could be dropped from tracking while
    still present in ``norms``, and would then be re-backfilled against the
    CURRENT supporter set, silently granting carriage to people who were not
    supporters at formation. Pruning to known norms makes that impossible:
    anything still in ``norms`` is still tracked, and anything absent cannot
    be re-derived by ``derive_group_carriage_changes`` (which only iterates
    ``norms``) so it needs no tracking entry. The set is thereby bounded by
    the norm registry's own cap rather than by a second, independent one.

    ``known_norm_ids=None`` means "prune nothing" - used only by focused tests
    that advance a registry without a norm frame in hand.
    """
    if existing:
        if existing.get("schema_version") != GROUP_CARRIAGE_REGISTRY_VERSION:
            raise GroupCarriageContractError(
                f"unsupported group carriage schema: {existing.get('schema_version')}"
            )
        registry = copy.deepcopy(existing)
    else:
        registry = empty_group_carriage_registry(tick)

    carriers = copy.deepcopy(registry.get("carriers") or {})
    backfilled_norm_ids = list(registry.get("backfilled_norm_ids") or [])
    backfilled_set = set(backfilled_norm_ids)
    processed = list(registry.get("processed_transmission_keys") or [])
    processed_set = set(processed)
    transitions: list[dict] = []

    room = LIMITS.carriers - len(carriers)

    # Backfills: group by norm_id so a norm is only marked backfilled once ALL
    # of its supporters (from this batch) have been written - a norm never
    # ends up half-backfilled and silently skipped forever.
    by_norm: dict[str, list[dict]] = {}
    for entry in sorted(changes.get("backfills") or [], key=lambda b: (b["norm_id"], b["person_id"])):
        by_norm.setdefault(entry["norm_id"], []).append(entry)
    for norm_id in sorted(by_norm):
        entries = by_norm[norm_id]
        if norm_id in backfilled_set:
            continue
        if room < len(entries):
            continue  # capacity-bounded: retry this norm's backfill next tick
        for entry in entries:
            key = carrier_key(entry["norm_id"], entry["person_id"])
            if key in carriers:
                continue
            carriers[key] = _carrier_record(entry, SOURCE_BACKFILL, tick)
            room -= 1
            transitions.append({
                "carrier_id": key, "norm_id": norm_id, "group_id": entry["group_id"],
                "person_id": entry["person_id"], "kind": SOURCE_BACKFILL,
            })
        backfilled_norm_ids.append(norm_id)
        backfilled_set.add(norm_id)

    # Transmissions: one carrier record per qualifying (norm, person) pair,
    # idempotent by processed_transmission_keys.
    for entry in sorted(
        changes.get("transmissions") or [], key=lambda t: (t["norm_id"], t["person_id"])
    ):
        key = entry["carrier_key"]
        if key in processed_set or key in carriers:
            continue
        if room < 1:
            continue  # capacity-bounded: retry next tick
        carriers[key] = _carrier_record(entry, SOURCE_TRANSMISSION, tick)
        room -= 1
        processed.append(key)
        processed_set.add(key)
        transitions.append({
            "carrier_id": key, "norm_id": entry["norm_id"], "group_id": entry["group_id"],
            "person_id": entry["person_id"], "kind": SOURCE_TRANSMISSION,
        })

    registry["carriers"] = {key: carriers[key] for key in sorted(carriers)}
    # F3: prune to norms that still exist upstream, never truncate by id order.
    tracked = set(backfilled_norm_ids)
    if known_norm_ids is not None:
        tracked &= set(known_norm_ids)
    registry["backfilled_norm_ids"] = sorted(tracked)
    registry["processed_transmission_keys"] = processed[-LIMITS.processed_transmission_keys:]
    registry["revision"] = int(registry.get("revision", 0)) + 1
    registry["last_updated_tick"] = int(tick)
    transitions.sort(key=lambda t: (t["kind"], t["carrier_id"]))
    return registry, transitions


def _proposed_registry(proposal: dict) -> dict | None:
    mutation = proposal.get("mutation") or {}
    return (
        (mutation.get("new_entities") or {}).get(GROUP_CARRIAGE_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(GROUP_CARRIAGE_REGISTRY_ID)
    )


def build_group_carriage_proposal(
    entities: dict,
    tick: int,
    *,
    changes: dict | None = None,
) -> dict | None:
    association = entities.get(ASSOCIATION_REGISTRY_ID)
    goal_registry = entities.get(GROUP_GOAL_REGISTRY_ID)
    norm_registry = entities.get(GROUP_NORM_REGISTRY_ID)
    if not isinstance(association, dict) or association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return None
    if not isinstance(goal_registry, dict) or goal_registry.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
        return None
    if not isinstance(norm_registry, dict) or norm_registry.get("schema_version") != GROUP_NORM_REGISTRY_VERSION:
        return None
    existing = entities.get(GROUP_CARRIAGE_REGISTRY_ID)
    if changes is None:
        changes = derive_group_carriage_changes(entities, tick)
    if not _has_changes(changes):
        return None

    registry, transitions = advance_group_carriage_registry(
        existing, changes, tick,
        known_norm_ids=set(norm_registry.get("norms") or {}),
    )
    if not transitions:
        return None  # every candidate change was capacity-deferred; nothing to commit

    parents = []
    for entry in changes.get("backfills") or []:
        if entry.get("source_event_id"):
            parents.append(entry["source_event_id"])
    for entry in changes.get("transmissions") or []:
        if entry.get("via_event_id"):
            parents.append(entry["via_event_id"])
    if not parents:
        if norm_registry.get("last_event_id"):
            parents.append(norm_registry["last_event_id"])
        if goal_registry.get("last_event_id"):
            parents.append(goal_registry["last_event_id"])
    parent_ids = _bounded_ids(parents, LIMITS.causal_parents)
    if not parent_ids:
        return None

    if existing:
        mutation = {"entity_updates": {GROUP_CARRIAGE_REGISTRY_ID: registry}, "new_entities": {}}
        prior_revision = int(existing.get("revision", 0))
        preconditions = [{
            "entity_id": GROUP_CARRIAGE_REGISTRY_ID, "field": "revision",
            "op": "eq", "value": prior_revision,
        }]
    else:
        mutation = {"new_entities": {GROUP_CARRIAGE_REGISTRY_ID: registry}, "entity_updates": {}}
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
    preconditions.append({
        "entity_id": GROUP_NORM_REGISTRY_ID, "field": "revision",
        "op": "eq", "value": int(norm_registry.get("revision", 0)),
    })

    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    metadata = {
        "schema_version": GROUP_CARRIAGE_VERSION,
        "registry_id": GROUP_CARRIAGE_REGISTRY_ID,
        "association_registry_revision": int(association.get("revision", 0)),
        "group_goal_registry_revision": int(goal_registry.get("revision", 0)),
        "group_norm_registry_revision": int(norm_registry.get("revision", 0)),
        "prior_revision": prior_revision,
        "next_revision": int(registry["revision"]),
        "changes": copy.deepcopy(changes),
        "transitions": copy.deepcopy(transitions),
        "carrier_count": len(registry["carriers"]),
        "payload_bytes": payload_bytes,
    }
    return {
        "proposal_family": PROPOSAL_FAMILY,
        "proposal_type": PROPOSAL_TYPE,
        "proposer_engine_id": "group_carriage",
        "proposer_engine_version": "1.0.0",
        "entity_id": GROUP_CARRIAGE_REGISTRY_ID,
        "causal_parent_event_ids": parent_ids,
        "is_exogenous": False,
        "requested_time": int(tick),
        "phase": "agent",
        "engine_priority": 86,  # before group_norm (87), group_goal (88), group_state (89), association (90)
        "touched_scope": [
            GROUP_CARRIAGE_REGISTRY_ID, GROUP_NORM_REGISTRY_ID,
            GROUP_GOAL_REGISTRY_ID, ASSOCIATION_REGISTRY_ID,
        ],
        "preconditions": preconditions,
        "mutation": mutation,
        "group_carriage_update": metadata,
        "explanation": (
            f"group carriage registry revision {registry['revision']}; "
            f"backfills={len(changes.get('backfills') or [])} "
            f"transmissions={len(changes.get('transmissions') or [])}"
        ),
    }


def validate_group_carriage_proposal(proposal: dict, entities: dict) -> str | None:
    """Core-owned validation. None means ok; non-None is a stable reason code."""
    metadata = proposal.get("group_carriage_update")
    if metadata is None:
        # Marker-gated: a proposal that writes the carriage registry WITHOUT
        # the group_carriage_update marker must not slip past validation.
        mutation = proposal.get("mutation") or {}
        if (GROUP_CARRIAGE_REGISTRY_ID in (mutation.get("new_entities") or {})
                or GROUP_CARRIAGE_REGISTRY_ID in (mutation.get("entity_updates") or {})):
            return REASON_INVALID
        return None
    if not isinstance(metadata, dict) or metadata.get("schema_version") != GROUP_CARRIAGE_VERSION:
        return REASON_VERSION
    if proposal.get("entity_id") != GROUP_CARRIAGE_REGISTRY_ID or metadata.get("registry_id") != GROUP_CARRIAGE_REGISTRY_ID:
        return REASON_REGISTRY_ID

    association = entities.get(ASSOCIATION_REGISTRY_ID)
    goal_registry = entities.get(GROUP_GOAL_REGISTRY_ID)
    norm_registry = entities.get(GROUP_NORM_REGISTRY_ID)
    if not isinstance(association, dict) or association.get("schema_version") != ASSOCIATION_REGISTRY_VERSION:
        return REASON_ASSOCIATION
    if not isinstance(goal_registry, dict) or goal_registry.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
        return REASON_GROUP_GOAL
    if not isinstance(norm_registry, dict) or norm_registry.get("schema_version") != GROUP_NORM_REGISTRY_VERSION:
        return REASON_GROUP_NORM
    if int(metadata.get("association_registry_revision", -1)) != int(association.get("revision", -2)):
        return REASON_STALE
    if int(metadata.get("group_goal_registry_revision", -1)) != int(goal_registry.get("revision", -2)):
        return REASON_STALE
    if int(metadata.get("group_norm_registry_revision", -1)) != int(norm_registry.get("revision", -2)):
        return REASON_STALE

    mutation = proposal.get("mutation") or {}
    new_entities = mutation.get("new_entities") or {}
    entity_updates = mutation.get("entity_updates") or {}
    removed = mutation.get("removed_entities") or []
    if set(new_entities) - {GROUP_CARRIAGE_REGISTRY_ID} or set(entity_updates) - {GROUP_CARRIAGE_REGISTRY_ID} or removed:
        return REASON_SCOPE
    if GROUP_CARRIAGE_REGISTRY_ID in new_entities and GROUP_CARRIAGE_REGISTRY_ID in entity_updates:
        return REASON_SCOPE
    registry = _proposed_registry(proposal)
    if not isinstance(registry, dict) or registry.get("schema_version") != GROUP_CARRIAGE_REGISTRY_VERSION:
        return REASON_SCHEMA

    payload_bytes = len(canonical_json(registry).encode("utf-8"))
    if payload_bytes > LIMITS.proposal_bytes or int(metadata.get("payload_bytes", -1)) != payload_bytes:
        return REASON_PAYLOAD

    existing = entities.get(GROUP_CARRIAGE_REGISTRY_ID)
    if existing and GROUP_CARRIAGE_REGISTRY_ID in new_entities:
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
    if (GROUP_NORM_REGISTRY_ID, "revision", "eq", int(norm_registry.get("revision", 0))) not in required:
        return REASON_STALE
    if existing and (GROUP_CARRIAGE_REGISTRY_ID, "revision", "eq", int(existing.get("revision", 0))) not in required:
        return REASON_REVISION

    changes = metadata.get("changes")
    if not isinstance(changes, dict):
        return REASON_METADATA
    if not isinstance(changes.get("backfills"), list) or not isinstance(changes.get("transmissions"), list):
        return REASON_METADATA

    # Re-derive from the current canonical frame and require CANONICAL BYTE
    # equality (not Python ==) against the submitted changes - a forged
    # person_id / learned_from / via_event_id / event-type cannot survive.
    derived = derive_group_carriage_changes(entities, int(proposal.get("requested_time", 0)))
    if canonical_json(changes) != canonical_json(derived):
        return REASON_METADATA

    # Advance the TRUSTED freshly-derived changes (not the submission) and
    # require the submitted registry + transitions to be byte-exact.
    try:
        expected_registry, transitions = advance_group_carriage_registry(
            existing, derived, int(proposal.get("requested_time", 0)),
            known_norm_ids=set(norm_registry.get("norms") or {}),
        )
    except (TypeError, ValueError, GroupCarriageContractError):
        return REASON_SCHEMA
    if canonical_json(expected_registry) != canonical_json(registry):
        return REASON_MUTATION
    if canonical_json(metadata.get("transitions")) != canonical_json(transitions):
        return REASON_METADATA
    if int(metadata.get("carrier_count", -1)) != len(registry.get("carriers") or {}):
        return REASON_METADATA
    if len(registry.get("carriers") or {}) > LIMITS.carriers:
        return REASON_LIMIT
    if len(registry.get("backfilled_norm_ids") or []) > LIMITS.backfilled_norm_ids:
        return REASON_LIMIT
    if len(registry.get("processed_transmission_keys") or []) > LIMITS.processed_transmission_keys:
        return REASON_LIMIT

    for key, record in (registry.get("carriers") or {}).items():
        if record.get("schema_version") != GROUP_CARRIAGE_VERSION or FORBIDDEN_FIELDS & set(record):
            return REASON_CARRIER
        if record.get("source") not in (SOURCE_BACKFILL, SOURCE_TRANSMISSION):
            return REASON_CARRIER
        norm_id, person_id = split_carrier_key(key)
        if not norm_id or not person_id:
            return REASON_CARRIER
        # F2c: the two ids are stored exactly once, in the key. A record that
        # re-states them is rejected, so the slimming cannot be silently
        # undone by a later writer or a forged proposal.
        if {"carrier_id", "norm_id", "person_id"} & set(record):
            return REASON_CARRIER
        # Amendment 2: no committed record may carry the post-commit staging
        # keys — they are never written (see _carrier_record), so their
        # presence can only mean a forged or stale record.
        if {"pending_event_tick", "pending_transition"} & set(record):
            return REASON_CARRIER
        if record.get("source") == SOURCE_BACKFILL and record.get("learned_from") is not None:
            return REASON_CARRIER
        if record.get("source") == SOURCE_TRANSMISSION and not record.get("learned_from"):
            return REASON_CARRIER
    return None


def stamp_group_carriage_provenance(proposal: dict, mutation: dict, event_id: str) -> None:
    """Stamp created/last event ids on the carrier records this proposal just wrote.

    Amendment 2: no ``pending_event_tick`` marker to scan for — carriage
    records are write-once, so ``metadata["transitions"]`` (built by
    ``advance_group_carriage_registry`` and carried on the proposal
    unchanged) already lists exactly the registry keys created this tick.
    """
    metadata = proposal.get("group_carriage_update")
    if not isinstance(metadata, dict):
        return
    registry = (
        (mutation.get("new_entities") or {}).get(GROUP_CARRIAGE_REGISTRY_ID)
        or (mutation.get("entity_updates") or {}).get(GROUP_CARRIAGE_REGISTRY_ID)
    )
    if not isinstance(registry, dict):
        return
    carriers = registry.get("carriers") or {}
    for transition in metadata.get("transitions") or []:
        record = carriers.get(transition.get("carrier_id"))
        if not isinstance(record, dict):
            continue
        if record.get("created_event_id") is None:
            record["created_event_id"] = event_id
        record["last_event_id"] = event_id
    metadata["accepted_event_id"] = event_id


def group_carriage_diagnostics(registry: dict, tick: int) -> dict:
    carriers = registry.get("carriers") or {}
    return {
        "schema_version": "group-carriage-diagnostics-v1",
        "tick": int(tick),
        "registry_revision": int(registry.get("revision", 0)),
        "carrier_count": len(carriers),
        "backfill_carrier_count": sum(1 for r in carriers.values() if r.get("source") == SOURCE_BACKFILL),
        "transmission_carrier_count": sum(1 for r in carriers.values() if r.get("source") == SOURCE_TRANSMISSION),
        "backfilled_norm_count": len(registry.get("backfilled_norm_ids") or []),
        "processed_transmission_count": len(registry.get("processed_transmission_keys") or []),
        "caps": {
            "carriers": LIMITS.carriers,
            "backfilled_norm_ids": LIMITS.backfilled_norm_ids,
            "processed_transmission_keys": LIMITS.processed_transmission_keys,
            "new_records_per_tick": LIMITS.new_records_per_tick,
            "causal_parents": LIMITS.causal_parents,
            "payload_target_bytes": LIMITS.payload_target_bytes,
            "proposal_bytes": LIMITS.proposal_bytes,
        },
        "constants": {
            "transmission_count": TRANSMISSION_COUNT,
            "transmission_qualifying_event_types": list(TRANSMISSION_QUALIFYING_EVENT_TYPES),
        },
    }


def group_carriage_capacity_diagnostics(registry: dict) -> dict:
    provenance_fields = {
        "accepted_event_id", "created_event_id", "last_event_id", "via_event_id",
    }

    def classify(path: tuple, _value, _is_key: bool) -> str | None:
        fields = {part for part in path if isinstance(part, str)}
        if "processed_transmission_keys" in fields:
            return "processed_transmission_key_bytes"
        # note: carrier keys themselves classify as current_truth_bytes below,
        # since after F2c the key IS the record's identity, not an index into
        # a separately-stored copy.
        if "backfilled_norm_ids" in fields:
            return "backfilled_norm_id_bytes"
        if fields & provenance_fields:
            return "provenance_reference_bytes"
        if "carriers" in fields:
            return "current_truth_bytes"
        return None

    composition = {
        "current_truth_bytes": 0,
        "processed_transmission_key_bytes": 0,
        "backfilled_norm_id_bytes": 0,
        "provenance_reference_bytes": 0,
        "other_structural_overhead_bytes": 0,
    }
    composition.update(canonical_byte_composition(registry, classify))
    return {
        "total_serialized_bytes": len(canonical_json(registry).encode("utf-8")),
        **composition,
    }
