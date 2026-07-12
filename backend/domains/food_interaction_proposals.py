"""Proposal builders for Phase 5B3 food-interaction-v1.

Domains propose; Core validates and mutates. Fulfilment always attaches a
food-transfer-v1 payload so inventory mutation reuses the 5B1 primitive.
"""
from __future__ import annotations

from core.constants import (
    CRITICAL_THRESHOLD,
    FOOD_TRANSFER_QUANTITY,
    FOOD_TRANSFER_SURPLUS,
)
from core.food_interaction import (
    ENTITY_TYPE,
    KIND_OFFER,
    KIND_REQUEST,
    PROPOSAL_CREATE,
    PROPOSAL_EXPIRE,
    PROPOSAL_FULFIL,
    PROPOSAL_INVALIDATE,
    PROPOSAL_RESPOND,
    PROTOCOL_VERSION,
    REASON_EXPIRED,
    REASON_REFUSED,
    RESPONSE_ACCEPT,
    RESPONSE_REFUSE,
    STATUS_ACCEPTED,
    STATUS_EXPIRED,
    STATUS_FULFILLED,
    STATUS_INVALIDATED,
    STATUS_PENDING,
    STATUS_REFUSED,
    build_interaction_record,
    create_awareness_ok,
    find_active_equivalent,
    giver_and_receiver,
    invalidation_reason,
    is_expired_at,
    participants_adjacent,
    response_permitted_at,
)


ENGINE_ID = "people"
ENGINE_VERSION = "2.1.0"
ENGINE_PRIORITY = 10


def _base_proposal(*, entity_id, tick, proposal_type, explanation, causal_parents, is_exogenous):
    return {
        "proposal_family": "food_interaction",
        "proposal_type": proposal_type,
        "proposer_engine_id": ENGINE_ID,
        "proposer_engine_version": ENGINE_VERSION,
        "entity_id": entity_id,
        "causal_parent_event_ids": list(causal_parents or []),
        "is_exogenous": bool(is_exogenous),
        "requested_time": tick,
        "phase": "agent",
        "engine_priority": ENGINE_PRIORITY,
        "explanation": explanation,
    }


def _interaction_meta(record: dict, **extra) -> dict:
    meta = {
        "protocol_version": PROTOCOL_VERSION,
        "interaction_id": record["interaction_id"],
        "kind": record["kind"],
        "initiator_id": record["initiator_id"],
        "responder_id": record["responder_id"],
        "resource_kind": "food",
        "quantity": FOOD_TRANSFER_QUANTITY,
        "status": record.get("status"),
        "created_tick": record["created_tick"],
        "expires_tick": record["expires_tick"],
        "causal_parent_event_ids": list(record.get("causal_parent_event_ids") or []),
    }
    meta.update(extra)
    return meta


def build_create_proposal(
    *,
    kind: str,
    initiator_id: str,
    responder_id: str,
    tick: int,
    entities: dict,
    explanation: str = "create food interaction",
) -> dict:
    initiator = entities[initiator_id]
    causal = [initiator["last_event_id"]] if initiator.get("last_event_id") else []
    record = build_interaction_record(
        kind=kind,
        initiator_id=initiator_id,
        responder_id=responder_id,
        created_tick=tick,
        causal_parent_event_ids=causal,
    )
    iid = record["interaction_id"]
    proposal = _base_proposal(
        entity_id=initiator_id,
        tick=tick,
        proposal_type=PROPOSAL_CREATE,
        explanation=explanation,
        causal_parents=causal,
        is_exogenous=not bool(causal),
    )
    proposal["touched_scope"] = [initiator_id, responder_id, iid]
    proposal["preconditions"] = [
        {"entity_id": initiator_id, "field": "alive", "op": "eq", "value": True},
        {"entity_id": responder_id, "field": "alive", "op": "eq", "value": True},
    ]
    proposal["mutation"] = {
        "new_entities": {iid: dict(record)},
        "entity_updates": {},
    }
    proposal["interaction"] = _interaction_meta(record, status=STATUS_PENDING, transition="create")
    return proposal


def build_respond_proposal(
    *,
    interaction: dict,
    response: str,
    tick: int,
    entities: dict,
    explanation: str = "respond food interaction",
) -> dict:
    iid = interaction["interaction_id"]
    responder_id = interaction["responder_id"]
    responder = entities[responder_id]
    causal = []
    if interaction.get("last_event_id"):
        causal.append(interaction["last_event_id"])
    elif interaction.get("creation_event_id"):
        causal.append(interaction["creation_event_id"])
    elif responder.get("last_event_id"):
        causal.append(responder["last_event_id"])
    status = STATUS_ACCEPTED if response == RESPONSE_ACCEPT else STATUS_REFUSED
    terminal = None if response == RESPONSE_ACCEPT else REASON_REFUSED
    proposal = _base_proposal(
        entity_id=responder_id,
        tick=tick,
        proposal_type=PROPOSAL_RESPOND,
        explanation=explanation,
        causal_parents=causal,
        is_exogenous=not bool(causal),
    )
    proposal["touched_scope"] = [
        interaction["initiator_id"], interaction["responder_id"], iid,
    ]
    proposal["preconditions"] = [
        {"entity_id": iid, "field": "status", "op": "eq", "value": STATUS_PENDING},
        {"entity_id": responder_id, "field": "alive", "op": "eq", "value": True},
    ]
    updates = {"status": status, "terminal_reason": terminal}
    proposal["mutation"] = {"entity_updates": {iid: updates}, "new_entities": {}}
    proposal["interaction"] = _interaction_meta(
        interaction, status=status, response=response, terminal_reason=terminal, transition="respond",
    )
    return proposal


def build_fulfil_proposal(
    *,
    interaction: dict,
    tick: int,
    entities: dict,
    explanation: str = "fulfil food interaction via food-transfer-v1",
) -> dict:
    iid = interaction["interaction_id"]
    giver_id, receiver_id = giver_and_receiver(interaction)
    giver = entities[giver_id]
    receiver = entities[receiver_id]
    causal = []
    if interaction.get("last_event_id"):
        causal.append(interaction["last_event_id"])
    elif interaction.get("acceptance_event_id"):
        causal.append(interaction["acceptance_event_id"])
    elif giver.get("last_event_id"):
        causal.append(giver["last_event_id"])
    proposal = _base_proposal(
        entity_id=giver_id,
        tick=tick,
        proposal_type=PROPOSAL_FULFIL,
        explanation=explanation,
        causal_parents=causal,
        is_exogenous=not bool(causal),
    )
    proposal["touched_scope"] = [
        interaction["initiator_id"], interaction["responder_id"], iid, giver_id, receiver_id,
    ]
    # de-dupe scope while preserving stability
    proposal["touched_scope"] = list(dict.fromkeys(proposal["touched_scope"]))
    proposal["preconditions"] = [
        {"entity_id": iid, "field": "status", "op": "eq", "value": STATUS_ACCEPTED},
        {"entity_id": giver_id, "field": "alive", "op": "eq", "value": True},
        {"entity_id": giver_id, "field": "food_inventory", "op": "gte", "value": FOOD_TRANSFER_SURPLUS},
        {"entity_id": receiver_id, "field": "alive", "op": "eq", "value": True},
        {"entity_id": receiver_id, "field": "hunger", "op": "gte", "value": CRITICAL_THRESHOLD},
        {"entity_id": receiver_id, "field": "food_inventory", "op": "eq", "value": 0},
        {"entity_id": receiver_id, "field": "inventory", "op": "eq", "value": 0},
    ]
    proposal["mutation"] = {
        "entity_updates": {
            giver_id: {"food_inventory": giver["food_inventory"] - FOOD_TRANSFER_QUANTITY},
            receiver_id: {"food_inventory": receiver.get("food_inventory", 0) + FOOD_TRANSFER_QUANTITY},
            iid: {"status": STATUS_FULFILLED, "terminal_reason": None},
        },
        "new_entities": {},
    }
    proposal["transfer"] = {
        "contract_version": "food-transfer-v1",
        "giver_id": giver_id,
        "receiver_id": receiver_id,
        "field": "food_inventory",
        "quantity": FOOD_TRANSFER_QUANTITY,
    }
    proposal["interaction"] = _interaction_meta(
        interaction, status=STATUS_FULFILLED, transition="fulfil",
    )
    return proposal


def build_expire_proposal(
    *,
    interaction: dict,
    tick: int,
    entity_id: str,
    entities: dict,
    explanation: str = "expire food interaction",
) -> dict:
    iid = interaction["interaction_id"]
    actor = entities[entity_id]
    causal = []
    if interaction.get("last_event_id"):
        causal.append(interaction["last_event_id"])
    elif actor.get("last_event_id"):
        causal.append(actor["last_event_id"])
    proposal = _base_proposal(
        entity_id=entity_id,
        tick=tick,
        proposal_type=PROPOSAL_EXPIRE,
        explanation=explanation,
        causal_parents=causal,
        is_exogenous=not bool(causal),
    )
    proposal["touched_scope"] = [
        interaction["initiator_id"], interaction["responder_id"], iid,
    ]
    proposal["preconditions"] = [
        {"entity_id": iid, "field": "status", "op": "eq", "value": STATUS_PENDING},
    ]
    proposal["mutation"] = {
        "entity_updates": {
            iid: {"status": STATUS_EXPIRED, "terminal_reason": REASON_EXPIRED},
        },
        "new_entities": {},
    }
    proposal["interaction"] = _interaction_meta(
        interaction, status=STATUS_EXPIRED, terminal_reason=REASON_EXPIRED, transition="expire",
    )
    return proposal


def build_invalidate_proposal(
    *,
    interaction: dict,
    tick: int,
    entity_id: str,
    entities: dict,
    reason: str,
    explanation: str = "invalidate food interaction",
) -> dict:
    iid = interaction["interaction_id"]
    actor = entities.get(entity_id) or {}
    causal = []
    if interaction.get("last_event_id"):
        causal.append(interaction["last_event_id"])
    elif actor.get("last_event_id"):
        causal.append(actor["last_event_id"])
    proposal = _base_proposal(
        entity_id=entity_id,
        tick=tick,
        proposal_type=PROPOSAL_INVALIDATE,
        explanation=explanation,
        causal_parents=causal,
        is_exogenous=not bool(causal),
    )
    proposal["touched_scope"] = [
        interaction["initiator_id"], interaction["responder_id"], iid,
    ]
    proposal["preconditions"] = [
        {"entity_id": iid, "field": "status", "op": "eq", "value": interaction["status"]},
    ]
    proposal["mutation"] = {
        "entity_updates": {
            iid: {"status": STATUS_INVALIDATED, "terminal_reason": reason},
        },
        "new_entities": {},
    }
    proposal["interaction"] = _interaction_meta(
        interaction, status=STATUS_INVALIDATED, terminal_reason=reason, transition="invalidate",
    )
    return proposal


def iter_interactions_for(entities: dict, person_id: str) -> list[tuple[str, dict]]:
    found = []
    for eid in sorted(entities):
        ent = entities[eid]
        if ent.get("type") != ENTITY_TYPE:
            continue
        if person_id in (ent.get("initiator_id"), ent.get("responder_id")):
            found.append((eid, ent))
    return found


def maintenance_proposer(entities: dict, interaction: dict) -> str:
    """Stable proposer for expire/invalidate: first living participant by id, else initiator."""
    participants = sorted({interaction.get("initiator_id"), interaction.get("responder_id")} - {None})
    for pid in participants:
        person = entities.get(pid) or {}
        if person.get("type") == "person" and person.get("alive", True):
            return pid
    return interaction.get("initiator_id") or participants[0]


def propose_stranded_accepted_invalidations(entities: dict, tick: int) -> list[dict]:
    """Propose accepted -> invalidated for every accepted interaction that cannot fulfil.

    This is the deterministic protocol-maintenance boundary after contention or
    other canonical state changes (lost supply, death, missing participant,
    adjacency loss, transfer ineligibility). Rejected fulfil proposals never
    mutate state; this follow-up accepted invalidate does.
    """
    proposals = []
    for eid in sorted(entities):
        interaction = entities[eid]
        if interaction.get("type") != ENTITY_TYPE:
            continue
        if interaction.get("status") != STATUS_ACCEPTED:
            continue
        reason = invalidation_reason(entities, interaction)
        if not reason:
            continue
        proposer = maintenance_proposer(entities, interaction)
        proposals.append(build_invalidate_proposal(
            interaction=interaction,
            tick=tick,
            entity_id=proposer,
            entities=entities,
            reason=reason,
            explanation=f"invalidate stranded accepted interaction ({reason})",
        ))
    return proposals


def propose_protocol_steps_for_person(entities: dict, person_id: str, tick: int) -> list[dict]:
    """Deterministic protocol maintenance proposals for one person activation.

    Order: expire/invalidate existing, then respond, then fulfil, then create.
    Accepted interactions that can no longer fulfil are invalidated (never expired).
    At most one create and one respond/fulfil path per person per tick to keep
    proposal pressure bounded.
    """
    proposals = []
    person = entities.get(person_id)
    if not person or person.get("type") != "person" or not person.get("alive", True):
        return proposals

    # 1) Maintain existing interactions (invalidate before fulfil; never expire accepted)
    for iid, interaction in iter_interactions_for(entities, person_id):
        status = interaction.get("status")
        if status == STATUS_PENDING and is_expired_at(interaction, tick):
            proposals.append(build_expire_proposal(
                interaction=interaction, tick=tick, entity_id=person_id, entities=entities,
            ))
            continue
        inv = invalidation_reason(entities, interaction)
        if inv and status in (STATUS_PENDING, STATUS_ACCEPTED):
            proposals.append(build_invalidate_proposal(
                interaction=interaction, tick=tick, entity_id=person_id,
                entities=entities, reason=inv,
            ))
            continue
        if (
            status == STATUS_PENDING
            and person_id == interaction.get("responder_id")
            and response_permitted_at(interaction, tick)
        ):
            # Auto-accept when the 5B1 transfer would be eligible for the giver.
            if _responder_should_accept(entities, interaction):
                proposals.append(build_respond_proposal(
                    interaction=interaction, response=RESPONSE_ACCEPT, tick=tick, entities=entities,
                    explanation="auto-accept food interaction",
                ))
            continue
        if status == STATUS_ACCEPTED:
            giver_id, _ = giver_and_receiver(interaction)
            if person_id == giver_id and invalidation_reason(entities, interaction) is None:
                proposals.append(build_fulfil_proposal(
                    interaction=interaction, tick=tick, entities=entities,
                ))

    # 2) Create at most one new interaction when none active for the pair/kind.
    create = _maybe_create(entities, person_id, tick)
    if create:
        proposals.append(create)
    return proposals


def _responder_should_accept(entities: dict, interaction: dict) -> bool:
    giver_id, receiver_id = giver_and_receiver(interaction)
    giver = entities.get(giver_id) or {}
    receiver = entities.get(receiver_id) or {}
    if giver.get("food_inventory", 0) < FOOD_TRANSFER_SURPLUS:
        return False
    if receiver.get("hunger", 0) < CRITICAL_THRESHOLD:
        return False
    if receiver.get("food_inventory", 0) != 0 or receiver.get("inventory", 0) != 0:
        return False
    if not participants_adjacent(entities, giver_id, receiver_id):
        return False
    return True


def _maybe_create(entities: dict, person_id: str, tick: int) -> dict | None:
    """Create request or offer using bounded social facts + adjacency."""
    # Prefer request when critically hungry; else offer when surplus.
    person = entities[person_id]
    knowledge = person.get("knowledge") or {}
    known_people = knowledge.get("known_people") or {}

    # Request path
    if person.get("hunger", 0) >= CRITICAL_THRESHOLD and person.get("food_inventory", 0) == 0:
        for other_id in sorted(known_people):
            if other_id == person_id:
                continue
            if find_active_equivalent(entities, KIND_REQUEST, person_id, other_id):
                continue
            if not create_awareness_ok(entities, KIND_REQUEST, person_id, other_id):
                continue
            if not participants_adjacent(entities, person_id, other_id):
                continue
            other = entities.get(other_id)
            if not other or not other.get("alive", True):
                continue
            return build_create_proposal(
                kind=KIND_REQUEST,
                initiator_id=person_id,
                responder_id=other_id,
                tick=tick,
                entities=entities,
                explanation=f"request food from {other_id}",
            )

    # Offer path
    if person.get("food_inventory", 0) >= FOOD_TRANSFER_SURPLUS:
        for other_id in sorted(known_people):
            if other_id == person_id:
                continue
            if find_active_equivalent(entities, KIND_OFFER, person_id, other_id):
                continue
            if not create_awareness_ok(entities, KIND_OFFER, person_id, other_id):
                continue
            if not participants_adjacent(entities, person_id, other_id):
                continue
            other = entities.get(other_id)
            if not other or not other.get("alive", True):
                continue
            return build_create_proposal(
                kind=KIND_OFFER,
                initiator_id=person_id,
                responder_id=other_id,
                tick=tick,
                entities=entities,
                explanation=f"offer food to {other_id}",
            )
    return None
