"""Phase 5B3 food-interaction-v1 protocol helpers.

Canonical interaction entities are event-backed and reconstructable. Domains
propose transitions; Core validates and mutates. Fulfilment reuses the 5B1
food-transfer-v1 primitive (never a second inventory mutation path).
"""
from __future__ import annotations

from core.constants import (
    CRITICAL_THRESHOLD,
    FOOD_INTERACTION_EXPIRY_TICKS,
    FOOD_INTERACTION_PROTOCOL_VERSION,
    FOOD_INTERACTION_RANGE,
    FOOD_TRANSFER_QUANTITY,
    FOOD_TRANSFER_SURPLUS,
)
from core.hashing import canonical_hash

PROTOCOL_VERSION = FOOD_INTERACTION_PROTOCOL_VERSION
ENTITY_TYPE = "food_interaction"

KIND_REQUEST = "request_food"
KIND_OFFER = "offer_food"
INTERACTION_KINDS = frozenset({KIND_REQUEST, KIND_OFFER})

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_FULFILLED = "fulfilled"
STATUS_REFUSED = "refused"
STATUS_EXPIRED = "expired"
STATUS_INVALIDATED = "invalidated"

ACTIVE_STATUSES = frozenset({STATUS_PENDING, STATUS_ACCEPTED})
TERMINAL_STATUSES = frozenset({
    STATUS_FULFILLED, STATUS_REFUSED, STATUS_EXPIRED, STATUS_INVALIDATED,
})

RESPONSE_ACCEPT = "accept"
RESPONSE_REFUSE = "refuse"

PROPOSAL_CREATE = "create_food_interaction"
PROPOSAL_RESPOND = "respond_food_interaction"
PROPOSAL_FULFIL = "fulfil_food_interaction"
PROPOSAL_EXPIRE = "expire_food_interaction"
PROPOSAL_INVALIDATE = "invalidate_food_interaction"
INTERACTION_PROPOSAL_TYPES = frozenset({
    PROPOSAL_CREATE, PROPOSAL_RESPOND, PROPOSAL_FULFIL, PROPOSAL_EXPIRE, PROPOSAL_INVALIDATE,
})

# Stable terminal / rejection reason codes
REASON_EXPIRED = "food_interaction.expired"
REASON_REFUSED = "food_interaction.refused"
REASON_PARTICIPANT_MISSING = "food_interaction.participant_missing"
REASON_PARTICIPANT_NOT_LIVING = "food_interaction.participant_not_living"
REASON_NOT_ADJACENT = "food_interaction.not_adjacent"
REASON_TRANSFER_INELIGIBLE = "food_interaction.transfer_ineligible"
REASON_LOST_SUPPLY = "food_interaction.lost_supply"
REASON_INCONSISTENT = "food_interaction.inconsistent"
REASON_DUPLICATE_ACTIVE = "food_interaction.duplicate_active"
REASON_NOT_PENDING = "food_interaction.not_pending"
REASON_NOT_ACCEPTED = "food_interaction.not_accepted"
REASON_TERMINAL = "food_interaction.terminal"
REASON_RESPONSE_UNAUTHORIZED = "food_interaction.response_unauthorized"
REASON_FULFIL_UNAUTHORIZED = "food_interaction.fulfil_unauthorized"
REASON_INVALID_KIND = "food_interaction.invalid_kind"
REASON_INVALID_VERSION = "food_interaction.invalid_version"
REASON_INVALID_TRANSITION = "food_interaction.invalid_transition"
REASON_INVALID_MUTATION = "food_interaction.invalid_mutation"
REASON_INVALID_SCOPE = "food_interaction.invalid_scope"
REASON_INVALID_QUANTITY = "food_interaction.invalid_quantity"
REASON_AWARENESS = "food_interaction.awareness_missing"
REASON_NOT_YET_EXPIRED = "food_interaction.not_yet_expired"
REASON_ALREADY_EXPIRED = "food_interaction.already_past_expiry"


def derive_interaction_id(kind: str, initiator_id: str, responder_id: str, created_tick: int) -> str:
    """Content-derived interaction identity (no UUID / wall-clock / DB identity)."""
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "kind": kind,
        "initiator_id": initiator_id,
        "responder_id": responder_id,
        "created_tick": created_tick,
        "resource_kind": "food",
        "quantity": FOOD_TRANSFER_QUANTITY,
    }
    return f"fi-{canonical_hash(payload)[:16]}"


def expires_tick_for(created_tick: int) -> int:
    return created_tick + FOOD_INTERACTION_EXPIRY_TICKS


def is_expired_at(interaction: dict, current_tick: int) -> bool:
    """True when the interaction expires at current_tick (response no longer permitted)."""
    return current_tick >= int(interaction.get("expires_tick", 0))


def response_permitted_at(interaction: dict, current_tick: int) -> bool:
    return (
        interaction.get("status") == STATUS_PENDING
        and current_tick < int(interaction.get("expires_tick", 0))
    )


def giver_and_receiver(interaction: dict) -> tuple[str, str]:
    """Return (giver_id, receiver_id) for fulfilment direction by kind."""
    kind = interaction.get("kind")
    initiator = interaction.get("initiator_id")
    responder = interaction.get("responder_id")
    if kind == KIND_REQUEST:
        return responder, initiator
    if kind == KIND_OFFER:
        return initiator, responder
    return None, None


def build_interaction_record(
    *,
    kind: str,
    initiator_id: str,
    responder_id: str,
    created_tick: int,
    status: str = STATUS_PENDING,
    terminal_reason: str | None = None,
    creation_event_id: str | None = None,
    acceptance_event_id: str | None = None,
    fulfilment_transfer_event_id: str | None = None,
    causal_parent_event_ids: list | None = None,
) -> dict:
    """Build the canonical food-interaction-v1 entity body (no last_event_id)."""
    interaction_id = derive_interaction_id(kind, initiator_id, responder_id, created_tick)
    return {
        "type": ENTITY_TYPE,
        "protocol_version": PROTOCOL_VERSION,
        "interaction_id": interaction_id,
        "kind": kind,
        "initiator_id": initiator_id,
        "responder_id": responder_id,
        "resource_kind": "food",
        "quantity": FOOD_TRANSFER_QUANTITY,
        "status": status,
        "created_tick": created_tick,
        "expires_tick": expires_tick_for(created_tick),
        "terminal_reason": terminal_reason,
        "creation_event_id": creation_event_id,
        "acceptance_event_id": acceptance_event_id,
        "fulfilment_transfer_event_id": fulfilment_transfer_event_id,
        "causal_parent_event_ids": list(causal_parent_event_ids or []),
    }


def participants_adjacent(entities: dict, a_id: str, b_id: str) -> bool:
    a = entities.get(a_id) or {}
    b = entities.get(b_id) or {}
    ap, bp = a.get("position"), b.get("position")
    if not ap or not bp:
        return False
    return abs(ap["x"] - bp["x"]) + abs(ap["y"] - bp["y"]) == FOOD_INTERACTION_RANGE


def find_active_equivalent(
    entities: dict, kind: str, initiator_id: str, responder_id: str, exclude_id: str | None = None,
) -> str | None:
    """Return interaction entity id of an active equivalent, if any."""
    for eid in sorted(entities):
        if exclude_id and eid == exclude_id:
            continue
        ent = entities[eid]
        if ent.get("type") != ENTITY_TYPE:
            continue
        if ent.get("protocol_version") != PROTOCOL_VERSION:
            continue
        if ent.get("kind") != kind:
            continue
        if ent.get("initiator_id") != initiator_id or ent.get("responder_id") != responder_id:
            continue
        if ent.get("status") in ACTIVE_STATUSES:
            return eid
    return None


def social_fact(entities: dict, observer_id: str, subject_id: str) -> dict | None:
    """Return initiator-owned social observation of subject, if present."""
    observer = entities.get(observer_id) or {}
    knowledge = observer.get("knowledge") or {}
    known = knowledge.get("known_people") or {}
    fact = known.get(subject_id)
    if not fact:
        return None
    if fact.get("social_observation_version") != "social-observation-v1":
        # Still allow if coarse fields exist (compat); prefer versioned records.
        if "appears_to_carry_food" not in fact and "apparent_urgent_need" not in fact:
            return None
    return fact


def create_awareness_ok(entities: dict, kind: str, initiator_id: str, responder_id: str) -> bool:
    """Domain/Core awareness gate: bounded social observation, not omniscient inventory."""
    fact = social_fact(entities, initiator_id, responder_id)
    if not fact:
        return False
    initiator = entities.get(initiator_id) or {}
    if kind == KIND_REQUEST:
        # Requester uses own need + visible appears_to_carry_food; never private inventory scan.
        if initiator.get("hunger", 0) < CRITICAL_THRESHOLD:
            return False
        return bool(fact.get("appears_to_carry_food"))
    if kind == KIND_OFFER:
        if initiator.get("food_inventory", 0) < FOOD_TRANSFER_SURPLUS:
            return False
        return fact.get("apparent_urgent_need") in ("distressed", "critical")
    return False


def invalidation_reason(entities: dict, interaction: dict) -> str | None:
    """Return a stable reason if the interaction can no longer continue/fulfil."""
    if interaction.get("protocol_version") != PROTOCOL_VERSION:
        return REASON_INCONSISTENT
    if interaction.get("status") in TERMINAL_STATUSES:
        return None
    initiator_id = interaction.get("initiator_id")
    responder_id = interaction.get("responder_id")
    initiator = entities.get(initiator_id)
    responder = entities.get(responder_id)
    if not initiator or not responder:
        return REASON_PARTICIPANT_MISSING
    if initiator.get("type") != "person" or responder.get("type") != "person":
        return REASON_INCONSISTENT
    if not initiator.get("alive", True) or not responder.get("alive", True):
        return REASON_PARTICIPANT_NOT_LIVING
    if interaction.get("status") == STATUS_ACCEPTED:
        giver_id, receiver_id = giver_and_receiver(interaction)
        if not giver_id or not receiver_id:
            return REASON_INCONSISTENT
        if not participants_adjacent(entities, giver_id, receiver_id):
            return REASON_NOT_ADJACENT
        giver = entities.get(giver_id) or {}
        receiver = entities.get(receiver_id) or {}
        if giver.get("food_inventory", 0) < FOOD_TRANSFER_SURPLUS:
            return REASON_LOST_SUPPLY
        if receiver.get("hunger", 0) < CRITICAL_THRESHOLD:
            return REASON_TRANSFER_INELIGIBLE
        if receiver.get("food_inventory", 0) != 0 or receiver.get("inventory", 0) != 0:
            return REASON_TRANSFER_INELIGIBLE
    return None


def validate_food_interaction(proposal: dict, entities: dict, tick: int) -> str | None:
    """Core-owned validation for food-interaction-v1 proposal types. None = ok."""
    ptype = proposal.get("proposal_type")
    if ptype not in INTERACTION_PROPOSAL_TYPES:
        return None

    meta = proposal.get("interaction") or {}
    if meta.get("protocol_version") != PROTOCOL_VERSION:
        return REASON_INVALID_VERSION
    if meta.get("resource_kind") != "food" or meta.get("quantity") != FOOD_TRANSFER_QUANTITY:
        return REASON_INVALID_QUANTITY

    kind = meta.get("kind")
    if kind not in INTERACTION_KINDS:
        return REASON_INVALID_KIND

    interaction_id = meta.get("interaction_id")
    initiator_id = meta.get("initiator_id")
    responder_id = meta.get("responder_id")
    if not interaction_id or not initiator_id or not responder_id or initiator_id == responder_id:
        return REASON_INCONSISTENT

    scope = set(proposal.get("touched_scope") or [])
    required_scope = {initiator_id, responder_id, interaction_id}
    if not required_scope.issubset(scope):
        return REASON_INVALID_SCOPE

    if ptype == PROPOSAL_CREATE:
        return _validate_create(proposal, entities, tick, meta, interaction_id, initiator_id, responder_id, kind)
    if ptype == PROPOSAL_RESPOND:
        return _validate_respond(proposal, entities, tick, meta, interaction_id)
    if ptype == PROPOSAL_FULFIL:
        return _validate_fulfil(proposal, entities, tick, meta, interaction_id)
    if ptype == PROPOSAL_EXPIRE:
        return _validate_expire(proposal, entities, tick, meta, interaction_id)
    if ptype == PROPOSAL_INVALIDATE:
        return _validate_invalidate(proposal, entities, tick, meta, interaction_id)
    return REASON_INVALID_TRANSITION


def _validate_create(proposal, entities, tick, meta, interaction_id, initiator_id, responder_id, kind):
    if proposal.get("entity_id") != initiator_id:
        return REASON_INCONSISTENT
    if interaction_id != derive_interaction_id(kind, initiator_id, responder_id, tick):
        return REASON_INCONSISTENT
    if meta.get("created_tick") != tick or meta.get("expires_tick") != expires_tick_for(tick):
        return REASON_INCONSISTENT
    if meta.get("status") != STATUS_PENDING:
        return REASON_INVALID_TRANSITION
    if interaction_id in entities:
        return REASON_DUPLICATE_ACTIVE
    if find_active_equivalent(entities, kind, initiator_id, responder_id):
        return REASON_DUPLICATE_ACTIVE

    initiator = entities.get(initiator_id)
    responder = entities.get(responder_id)
    if not initiator or not responder:
        return REASON_PARTICIPANT_MISSING
    if initiator.get("type") != "person" or responder.get("type") != "person":
        return REASON_INCONSISTENT
    if not initiator.get("alive", True) or not responder.get("alive", True):
        return REASON_PARTICIPANT_NOT_LIVING
    if not participants_adjacent(entities, initiator_id, responder_id):
        return REASON_NOT_ADJACENT
    if not create_awareness_ok(entities, kind, initiator_id, responder_id):
        return REASON_AWARENESS

    new_ents = (proposal.get("mutation") or {}).get("new_entities") or {}
    record = new_ents.get(interaction_id)
    if not record or record.get("type") != ENTITY_TYPE:
        return REASON_INVALID_MUTATION
    expected = build_interaction_record(
        kind=kind,
        initiator_id=initiator_id,
        responder_id=responder_id,
        created_tick=tick,
        causal_parent_event_ids=meta.get("causal_parent_event_ids") or proposal.get("causal_parent_event_ids") or [],
    )
    # Proposal may omit event-stamped fields; compare structural body.
    for key in (
        "type", "protocol_version", "interaction_id", "kind", "initiator_id", "responder_id",
        "resource_kind", "quantity", "status", "created_tick", "expires_tick",
    ):
        if record.get(key) != expected.get(key):
            return REASON_INVALID_MUTATION
    if record.get("terminal_reason") is not None:
        return REASON_INVALID_MUTATION
    return None


def _load_live(entities, interaction_id):
    live = entities.get(interaction_id)
    if not live or live.get("type") != ENTITY_TYPE:
        return None, REASON_PARTICIPANT_MISSING
    if live.get("protocol_version") != PROTOCOL_VERSION:
        return None, REASON_INCONSISTENT
    return live, None


def _validate_respond(proposal, entities, tick, meta, interaction_id):
    response = meta.get("response")
    if response not in (RESPONSE_ACCEPT, RESPONSE_REFUSE):
        return REASON_INVALID_TRANSITION
    live, err = _load_live(entities, interaction_id)
    if err:
        return err
    if live.get("status") in TERMINAL_STATUSES:
        return REASON_TERMINAL
    if live.get("status") != STATUS_PENDING:
        return REASON_NOT_PENDING
    if proposal.get("entity_id") != live.get("responder_id"):
        return REASON_RESPONSE_UNAUTHORIZED
    if is_expired_at(live, tick):
        return REASON_ALREADY_EXPIRED
    if not response_permitted_at(live, tick):
        return REASON_ALREADY_EXPIRED

    # Revalidate participants and adjacency at response time.
    initiator_id, responder_id = live["initiator_id"], live["responder_id"]
    initiator, responder = entities.get(initiator_id), entities.get(responder_id)
    if not initiator or not responder:
        return REASON_PARTICIPANT_MISSING
    if not initiator.get("alive", True) or not responder.get("alive", True):
        return REASON_PARTICIPANT_NOT_LIVING
    if not participants_adjacent(entities, initiator_id, responder_id):
        return REASON_NOT_ADJACENT

    target_status = STATUS_ACCEPTED if response == RESPONSE_ACCEPT else STATUS_REFUSED
    terminal_reason = None if response == RESPONSE_ACCEPT else REASON_REFUSED
    updates = ((proposal.get("mutation") or {}).get("entity_updates") or {}).get(interaction_id) or {}
    if updates.get("status") != target_status:
        return REASON_INVALID_MUTATION
    if response == RESPONSE_REFUSE and updates.get("terminal_reason") != REASON_REFUSED:
        return REASON_INVALID_MUTATION
    if response == RESPONSE_ACCEPT and updates.get("terminal_reason") not in (None,):
        return REASON_INVALID_MUTATION
    # Meta must match live identity
    for key in ("kind", "initiator_id", "responder_id", "created_tick", "expires_tick"):
        if meta.get(key) != live.get(key):
            return REASON_INCONSISTENT
    return None


def _validate_fulfil(proposal, entities, tick, meta, interaction_id):
    live, err = _load_live(entities, interaction_id)
    if err:
        return err
    if live.get("status") in TERMINAL_STATUSES:
        return REASON_TERMINAL
    if live.get("status") != STATUS_ACCEPTED:
        return REASON_NOT_ACCEPTED

    giver_id, receiver_id = giver_and_receiver(live)
    if not giver_id or proposal.get("entity_id") != giver_id:
        return REASON_FULFIL_UNAUTHORIZED

    inv = invalidation_reason(entities, live)
    if inv:
        return inv

    updates = ((proposal.get("mutation") or {}).get("entity_updates") or {}).get(interaction_id) or {}
    if updates.get("status") != STATUS_FULFILLED:
        return REASON_INVALID_MUTATION
    if updates.get("terminal_reason") is not None:
        return REASON_INVALID_MUTATION

    for key in ("kind", "initiator_id", "responder_id", "created_tick", "expires_tick"):
        if meta.get(key) != live.get(key):
            return REASON_INCONSISTENT

    # Transfer payload must match interaction direction; validate_food_transfer checks the rest.
    transfer = proposal.get("transfer") or {}
    if (
        transfer.get("giver_id") != giver_id
        or transfer.get("receiver_id") != receiver_id
        or transfer.get("contract_version") != "food-transfer-v1"
        or transfer.get("field") != "food_inventory"
        or transfer.get("quantity") != FOOD_TRANSFER_QUANTITY
    ):
        return REASON_TRANSFER_INELIGIBLE
    return None


def _validate_expire(proposal, entities, tick, meta, interaction_id):
    live, err = _load_live(entities, interaction_id)
    if err:
        return err
    if live.get("status") in TERMINAL_STATUSES:
        return REASON_TERMINAL
    if live.get("status") != STATUS_PENDING:
        return REASON_NOT_PENDING
    if not is_expired_at(live, tick):
        return REASON_NOT_YET_EXPIRED
    eid = proposal.get("entity_id")
    if eid not in (live.get("initiator_id"), live.get("responder_id")):
        return REASON_RESPONSE_UNAUTHORIZED
    updates = ((proposal.get("mutation") or {}).get("entity_updates") or {}).get(interaction_id) or {}
    if updates.get("status") != STATUS_EXPIRED or updates.get("terminal_reason") != REASON_EXPIRED:
        return REASON_INVALID_MUTATION
    for key in ("kind", "initiator_id", "responder_id", "created_tick", "expires_tick"):
        if meta.get(key) != live.get(key):
            return REASON_INCONSISTENT
    return None


def _validate_invalidate(proposal, entities, tick, meta, interaction_id):
    live, err = _load_live(entities, interaction_id)
    if err:
        return err
    if live.get("status") in TERMINAL_STATUSES:
        return REASON_TERMINAL
    if live.get("status") not in ACTIVE_STATUSES:
        return REASON_INVALID_TRANSITION
    live_reason = invalidation_reason(entities, live)
    if live_reason is None:
        return REASON_INCONSISTENT
    if meta.get("terminal_reason") not in (None, live_reason):
        return REASON_INCONSISTENT
    eid = proposal.get("entity_id")
    if eid not in (live.get("initiator_id"), live.get("responder_id")):
        return REASON_RESPONSE_UNAUTHORIZED
    updates = ((proposal.get("mutation") or {}).get("entity_updates") or {}).get(interaction_id) or {}
    if updates.get("status") != STATUS_INVALIDATED or updates.get("terminal_reason") != live_reason:
        return REASON_INVALID_MUTATION
    for key in ("kind", "initiator_id", "responder_id", "created_tick", "expires_tick"):
        if meta.get(key) != live.get(key):
            return REASON_INCONSISTENT
    return None
