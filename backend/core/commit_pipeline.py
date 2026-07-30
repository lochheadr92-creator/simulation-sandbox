"""
Core Commit Pipeline (Specification #27, right-sized for the MVP kernel).

    proposals -> normalize -> deterministic order -> validate -> commit-time
    revalidate -> transactional apply -> canonical hash

Only this module mutates `entities`. Domain engines never do.

Conflict resolution note: rather than a separate conflict-resolution stage,
this pipeline commits proposals ONE AT A TIME in deterministic order and
re-validates preconditions against the progressively-mutated state before
each commit. This makes contention (e.g. two people gathering the same tree)
resolve naturally and deterministically: the first proposal in order wins,
and the second's precondition fails against the now-updated state -
producing a genuine, inspectable rejection with a stable reason code.
"""
from core.hashing import canonical_hash, hash_canonical_json_string
from core.mutations import (
    MERGE_WRAPPER_KEY,
    apply_mutation,
    invalidate_entity_json_cache,
    snapshot_for_hash,
    spliced_snapshot_json,
)
from core.constants import (
    CRITICAL_THRESHOLD, FOOD_TRANSFER_QUANTITY, FOOD_TRANSFER_SURPLUS,
    TRADE_CONTRACT_VERSION, TRADE_MIN_RETAIN, TRADE_MIN_SURPLUS, TRADE_RANGE,
    AID_CONTRACT_VERSION, AID_GIVER_MIN_FOOD, AID_QUANTITY,
    AID_RECEIVER_MIN_HUNGER,
)
from core.food_interaction import (
    PROPOSAL_CREATE,
    PROPOSAL_FULFIL,
    INTERACTION_PROPOSAL_TYPES,
    validate_food_interaction,
)
from domains.living_agent_actions import validate_living_action_proposal
from domains.living_agent_social import validate_social_action_proposal
from domains.association_contracts import (
    stamp_association_provenance,
    validate_association_proposal,
)
from domains.group_state_contracts import (
    stamp_group_state_provenance,
    validate_group_state_proposal,
)
from domains.group_collective_contracts import (
    stamp_collective_action_provenance,
    validate_group_collective_proposal,
)
from domains.group_goal_contracts import (
    stamp_group_goal_provenance,
    validate_group_goal_proposal,
)
from domains.group_norm_contracts import (
    stamp_group_norm_provenance,
    validate_group_norm_proposal,
)
from domains.group_carriage_contracts import (
    stamp_group_carriage_provenance,
    validate_group_carriage_proposal,
)

PHASE_RANK = {"environment": 0, "agent": 1}

OPS = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
}


def normalize_proposal(p: dict, seq: int) -> dict:
    # NOTE: `seq` (input arrival order) is deliberately excluded from the
    # hashed core_fields - content_hash must be a pure function of the
    # proposal's CONTENT so that shuffling submission order never changes
    # final commit order or outcome (determinism doctrine).
    core_fields = {
        "proposal_family": p["proposal_family"],
        "proposal_type": p["proposal_type"],
        "proposer_engine_id": p["proposer_engine_id"],
        "causal_parent_event_ids": p.get("causal_parent_event_ids", []),
        "entity_id": p["entity_id"],
        "touched_scope": sorted(p.get("touched_scope", [])),
        "preconditions": p.get("preconditions", []),
        "mutation": p.get("mutation", {}),
        "transfer": p.get("transfer"),
        "interaction": p.get("interaction"),
        "living_action": p.get("living_action"),
        "social_action": p.get("social_action"),
        "requested_time": p["requested_time"],
        "phase": p["phase"],
    }
    if p.get("association_update") is not None:
        core_fields["association_update"] = p["association_update"]
    if p.get("trade") is not None:
        core_fields["trade"] = p["trade"]
    if p.get("group_state_update") is not None:
        core_fields["group_state_update"] = p["group_state_update"]
    if p.get("collective_action") is not None:
        core_fields["collective_action"] = p["collective_action"]
    if p.get("group_goal_update") is not None:
        core_fields["group_goal_update"] = p["group_goal_update"]
    if p.get("group_norm_update") is not None:
        core_fields["group_norm_update"] = p["group_norm_update"]
    h = canonical_hash(core_fields)
    p = dict(p)
    p["content_hash"] = h
    p["proposal_id"] = f"prop-{p['requested_time']}-{h[:12]}"
    return p


def order_key(p: dict):
    return (p["requested_time"], PHASE_RANK.get(p["phase"], 99), p.get("engine_priority", 100), p["content_hash"])


def check_scope_exists(p: dict, entities: dict):
    new_ids = set(p.get("mutation", {}).get("new_entities", {}).keys())
    for eid in p.get("touched_scope", []):
        if eid not in entities and eid not in new_ids:
            return f"entity_missing:{eid}"
    return None


def _resolve_field(entity: dict, field: str):
    """Resolve a condition field, optionally a dotted path into a dict-valued
    field (e.g. "living_agent.relationships.person-007"). A dotted field walks
    segment by segment; any missing or non-dict intermediate resolves to None.
    Undotted fields behave exactly as before (top-level entity.get)."""
    if "." not in field:
        return entity.get(field)
    value = entity
    for segment in field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(segment)
    return value


def evaluate_preconditions(preconditions: list, entities: dict):
    for cond in preconditions:
        eid = cond["entity_id"]
        entity = entities.get(eid)
        if entity is None:
            return f"entity_missing:{eid}"
        value = _resolve_field(entity, cond["field"])
        if not OPS[cond["op"]](value, cond["value"]):
            # The failure string names the full path so a path-scoped
            # rejection stays diagnosable to the record that collided.
            return f"{cond['field']}_{cond['op']}_failed"
    return None


def validate_food_transfer(proposal: dict, entities: dict):
    """Core-owned validation for the narrow Phase 5B transfer contract.

    Applies to direct `give_food` (5B1) and `fulfil_food_interaction` (5B3),
    which reuses the same transfer primitive without a second mutation path.
    """
    if proposal.get("proposal_type") not in ("give_food", PROPOSAL_FULFIL):
        return None

    transfer = proposal.get("transfer") or {}
    giver_id = transfer.get("giver_id")
    receiver_id = transfer.get("receiver_id")
    if (transfer.get("contract_version") != "food-transfer-v1"
            or transfer.get("field") != "food_inventory"
            or transfer.get("quantity") != FOOD_TRANSFER_QUANTITY):
        return "food_transfer.invalid_quantity"
    if giver_id != proposal.get("entity_id") or not giver_id or giver_id == receiver_id:
        return "food_transfer.invalid_ownership"
    if giver_id not in proposal.get("touched_scope", []) or receiver_id not in proposal.get("touched_scope", []):
        return "food_transfer.invalid_scope"

    giver = entities.get(giver_id)
    receiver = entities.get(receiver_id)
    if not giver or not receiver:
        return "food_transfer.participant_missing"
    if giver.get("type") != "person" or receiver.get("type") != "person":
        return "food_transfer.invalid_participant"
    if not giver.get("alive", True) or not receiver.get("alive", True):
        return "food_transfer.participant_not_living"
    giver_pos, receiver_pos = giver.get("position"), receiver.get("position")
    if not giver_pos or not receiver_pos or abs(giver_pos["x"] - receiver_pos["x"]) + abs(giver_pos["y"] - receiver_pos["y"]) != 1:
        return "food_transfer.not_adjacent"
    if giver.get("food_inventory", 0) < FOOD_TRANSFER_SURPLUS:
        return "food_transfer.insufficient_food"
    if receiver.get("hunger", 0) < CRITICAL_THRESHOLD:
        return "food_transfer.receiver_not_critical"
    if receiver.get("food_inventory", 0) != 0 or receiver.get("inventory", 0) != 0:
        return "food_transfer.receiver_has_carried_food"

    updates = proposal.get("mutation", {}).get("entity_updates", {})
    giver_update = updates.get(giver_id, {})
    receiver_update = updates.get(receiver_id, {})
    if (giver_update.get("food_inventory") != giver["food_inventory"] - FOOD_TRANSFER_QUANTITY
            or receiver_update.get("food_inventory") != receiver.get("food_inventory", 0) + FOOD_TRANSFER_QUANTITY):
        return "food_transfer.invalid_mutation"

    required = {
        (giver_id, "alive", "eq", True),
        (giver_id, "food_inventory", "gte", FOOD_TRANSFER_SURPLUS),
        (receiver_id, "alive", "eq", True),
        (receiver_id, "hunger", "gte", CRITICAL_THRESHOLD),
        (receiver_id, "food_inventory", "eq", 0),
        (receiver_id, "inventory", "eq", 0),
    }
    seen = {
        (p.get("entity_id"), p.get("field"), p.get("op"), p.get("value"))
        for p in proposal.get("preconditions", [])
    }
    if not required.issubset(seen):
        return "food_transfer.invalid_preconditions"
    return None


def validate_people_trade(proposal: dict, entities: dict):
    """Core-owned validation for the Surplus Pass barter contract.

    Mirrors validate_food_transfer: re-derives the expected two-party swap
    from live state rather than trusting the domain's mutation. Pre-culture
    trades were equal-quantity (carry totals invariant); the Culture Pass
    prices terms from agent norms, so give may differ from receive and
    capacity + post-trade retain are re-derived explicitly for both parties.
    """
    if proposal.get("proposal_type") != "offer_trade":
        return None

    trade = proposal.get("trade") or {}
    if trade.get("contract_version") == AID_CONTRACT_VERSION:
        # One-sided aid gifts carry their own contract; validated by
        # validate_people_aid. Barter rules (equal two-way exchange) do not
        # apply to them.
        return None
    giver_id = trade.get("giver_id")
    receiver_id = trade.get("receiver_id")
    give_field = trade.get("give_field")
    receive_field = trade.get("receive_field")
    give_qty = trade.get("give_quantity")
    receive_qty = trade.get("receive_quantity")
    if trade.get("contract_version") != TRADE_CONTRACT_VERSION:
        return "trade.invalid_contract"
    if (
        give_field not in ("inventory", "food_inventory")
        or receive_field not in ("inventory", "food_inventory")
        or give_field == receive_field
        or not isinstance(give_qty, int) or give_qty <= 0
        or not isinstance(receive_qty, int) or receive_qty <= 0
    ):
        return "trade.invalid_terms"
    if giver_id != proposal.get("entity_id") or not giver_id or giver_id == receiver_id:
        return "trade.invalid_ownership"
    if giver_id not in proposal.get("touched_scope", []) or receiver_id not in proposal.get("touched_scope", []):
        return "trade.invalid_scope"

    giver = entities.get(giver_id)
    receiver = entities.get(receiver_id)
    if not giver or not receiver:
        return "trade.participant_missing"
    if giver.get("type") != "person" or receiver.get("type") != "person":
        return "trade.invalid_participant"
    if not giver.get("alive", True) or not receiver.get("alive", True):
        return "trade.participant_not_living"
    giver_pos, receiver_pos = giver.get("position"), receiver.get("position")
    if (
        not giver_pos or not receiver_pos
        or abs(giver_pos["x"] - receiver_pos["x"]) + abs(giver_pos["y"] - receiver_pos["y"]) > TRADE_RANGE
    ):
        return "trade.out_of_range"
    # Each party must hold the surplus it offers. Post-trade retain is NOT
    # implied by TRADE_MIN_SURPLUS for norm-priced quantities (receive_qty 3
    # against a 4-holder leaves 1 < TRADE_MIN_RETAIN), so it is enforced
    # explicitly in the required precondition set below.
    if giver.get(give_field, 0) < TRADE_MIN_SURPLUS or receiver.get(receive_field, 0) < TRADE_MIN_SURPLUS:
        return "trade.insufficient_surplus"

    updates = proposal.get("mutation", {}).get("entity_updates", {})
    giver_update = updates.get(giver_id, {})
    receiver_update = updates.get(receiver_id, {})
    if (
        giver_update.get(give_field) != giver.get(give_field, 0) - give_qty
        or giver_update.get(receive_field) != giver.get(receive_field, 0) + receive_qty
        or receiver_update.get(receive_field) != receiver.get(receive_field, 0) - receive_qty
        or receiver_update.get(give_field) != receiver.get(give_field, 0) + give_qty
    ):
        return "trade.invalid_mutation"
    # Norm-priced terms make give != receive, so carry totals are no longer
    # invariant (Culture Pass): capacity is re-derived explicitly for both
    # parties. Equal-swap trades are unaffected (net 0 on both sides).
    giver_capacity = int(giver.get("inventory_capacity", 30))
    receiver_capacity = int(receiver.get("inventory_capacity", 30))
    if (
        giver.get("inventory", 0) + giver.get("food_inventory", 0) - give_qty + receive_qty
        > giver_capacity
        or receiver.get("inventory", 0) + receiver.get("food_inventory", 0) - receive_qty + give_qty
        > receiver_capacity
    ):
        return "trade.capacity_exceeded"
    # The versioned carry mirror must stay aligned with the legacy scalars.
    if (
        giver_update.get("carried_resources")
        != {"wood": giver_update.get("inventory"), "food": giver_update.get("food_inventory")}
        or receiver_update.get("carried_resources")
        != {"wood": receiver_update.get("inventory"), "food": receiver_update.get("food_inventory")}
    ):
        return "trade.invalid_mutation"

    required = {
        (giver_id, "alive", "eq", True),
        (giver_id, give_field, "gte", give_qty + TRADE_MIN_RETAIN),
        (receiver_id, "alive", "eq", True),
        (receiver_id, receive_field, "gte", receive_qty + TRADE_MIN_RETAIN),
        (receiver_id, "food_inventory", "eq", receiver.get("food_inventory", 0)),
        (receiver_id, "inventory", "eq", receiver.get("inventory", 0)),
    }
    seen = {
        (p.get("entity_id"), p.get("field"), p.get("op"), p.get("value"))
        for p in proposal.get("preconditions", [])
        if not isinstance(p.get("value"), dict)
    }
    if not required.issubset(seen):
        return "trade.invalid_preconditions"
    # Position values are dicts (unhashable), so the range pin is checked apart.
    if not any(
        p.get("entity_id") == receiver_id and p.get("field") == "position"
        and p.get("op") == "eq" and p.get("value") == receiver_pos
        for p in proposal.get("preconditions", [])
    ):
        return "trade.invalid_preconditions"
    return None


def validate_people_aid(proposal: dict, entities: dict):
    """Core-owned validation for the Culture Pass aid contract (people-aid-v1).

    Aid is a one-sided meat gift riding the existing offer_trade proposal
    type: no reciprocity leg, so the barter checks are bypassed and Core
    re-derives the material flow from live state — giver decrement, receiver
    increment, receiver capacity, versioned carry mirrors. Ally and gate
    semantics are domain-side cultural judgement and are deliberately NOT
    re-derived here: Core validates the transfer, not the relationship.
    """
    if proposal.get("proposal_type") != "offer_trade":
        return None
    trade = proposal.get("trade") or {}
    if trade.get("contract_version") != AID_CONTRACT_VERSION:
        return None

    giver_id = trade.get("giver_id")
    receiver_id = trade.get("receiver_id")
    give_field = trade.get("give_field")
    give_qty = trade.get("give_quantity")
    if (
        give_field != "food_inventory"
        or give_qty != AID_QUANTITY
        or trade.get("receive_field") is not None
        or trade.get("receive_quantity") != 0
    ):
        return "aid.invalid_terms"
    if giver_id != proposal.get("entity_id") or not giver_id or giver_id == receiver_id:
        return "aid.invalid_ownership"
    if giver_id not in proposal.get("touched_scope", []) or receiver_id not in proposal.get("touched_scope", []):
        return "aid.invalid_scope"

    giver = entities.get(giver_id)
    receiver = entities.get(receiver_id)
    if not giver or not receiver:
        return "aid.participant_missing"
    if giver.get("type") != "person" or receiver.get("type") != "person":
        return "aid.invalid_participant"
    if not giver.get("alive", True) or not receiver.get("alive", True):
        return "aid.participant_not_living"
    giver_pos, receiver_pos = giver.get("position"), receiver.get("position")
    if (
        not giver_pos or not receiver_pos
        or abs(giver_pos["x"] - receiver_pos["x"]) + abs(giver_pos["y"] - receiver_pos["y"]) > TRADE_RANGE
    ):
        return "aid.out_of_range"
    # Surplus retention is the aid contract's defining bound: the giver keeps
    # at least SURPLUS_KEEP_FOOD after the gift (AID_GIVER_MIN_FOOD ==
    # SURPLUS_KEEP_FOOD + AID_QUANTITY).
    if giver.get("food_inventory", 0) < AID_GIVER_MIN_FOOD:
        return "aid.insufficient_surplus"
    if receiver.get("hunger", 0) < AID_RECEIVER_MIN_HUNGER:
        return "aid.receiver_not_in_need"
    capacity = int(receiver.get("inventory_capacity", 30))
    if receiver.get("inventory", 0) + receiver.get("food_inventory", 0) + AID_QUANTITY > capacity:
        return "aid.receiver_capacity_exceeded"

    updates = proposal.get("mutation", {}).get("entity_updates", {})
    giver_update = updates.get(giver_id, {})
    receiver_update = updates.get(receiver_id, {})
    # All four legs re-derived against live state: meat moves, wood does not.
    if (
        giver_update.get("food_inventory") != giver.get("food_inventory", 0) - AID_QUANTITY
        or receiver_update.get("food_inventory") != receiver.get("food_inventory", 0) + AID_QUANTITY
        or giver_update.get("inventory") != giver.get("inventory", 0)
        or receiver_update.get("inventory") != receiver.get("inventory", 0)
    ):
        return "aid.invalid_mutation"
    # The versioned carry mirror must stay aligned with the legacy scalars.
    if (
        giver_update.get("carried_resources")
        != {"wood": giver_update.get("inventory"), "food": giver_update.get("food_inventory")}
        or receiver_update.get("carried_resources")
        != {"wood": receiver_update.get("inventory"), "food": receiver_update.get("food_inventory")}
    ):
        return "aid.invalid_mutation"

    required = {
        (giver_id, "alive", "eq", True),
        (giver_id, "food_inventory", "gte", AID_GIVER_MIN_FOOD),
        (receiver_id, "alive", "eq", True),
        (receiver_id, "hunger", "gte", AID_RECEIVER_MIN_HUNGER),
        (receiver_id, "food_inventory", "eq", receiver.get("food_inventory", 0)),
        (receiver_id, "inventory", "eq", receiver.get("inventory", 0)),
    }
    seen = {
        (p.get("entity_id"), p.get("field"), p.get("op"), p.get("value"))
        for p in proposal.get("preconditions", [])
        if not isinstance(p.get("value"), dict)
    }
    if not required.issubset(seen):
        return "aid.invalid_preconditions"
    # Position values are dicts (unhashable), so the range pin is checked apart.
    if not any(
        p.get("entity_id") == receiver_id and p.get("field") == "position"
        and p.get("op") == "eq" and p.get("value") == receiver_pos
        for p in proposal.get("preconditions", [])
    ):
        return "aid.invalid_preconditions"
    return None


def _stamp_food_interaction_provenance(proposal: dict, mutation: dict, event_id: str) -> None:
    """Stamp interaction entity event provenance at Core accept time."""
    if proposal.get("proposal_type") not in INTERACTION_PROPOSAL_TYPES:
        return
    meta = proposal.get("interaction") or {}
    iid = meta.get("interaction_id")
    if not iid:
        return
    ptype = proposal["proposal_type"]
    if ptype == PROPOSAL_CREATE:
        new_ents = mutation.setdefault("new_entities", {})
        if iid in new_ents:
            new_ents[iid]["last_event_id"] = event_id
            new_ents[iid]["creation_event_id"] = event_id
        return
    updates = mutation.setdefault("entity_updates", {}).setdefault(iid, {})
    updates["last_event_id"] = event_id
    if ptype == "respond_food_interaction" and updates.get("status") == "accepted":
        updates["acceptance_event_id"] = event_id
    if ptype == PROPOSAL_FULFIL:
        updates["fulfilment_transfer_event_id"] = event_id


def _stamp_living_agent_provenance(proposal: dict, mutation: dict, event_id: str) -> None:
    """Attach the accepting event to newly acquired cognition records.

    Domains cannot know an accepted event id before Core orders and accepts a
    proposal.  Core stamps only records created at this proposal's tick; the
    resulting mutation is what is persisted and replayed.
    """
    tick = int(proposal.get("requested_time", 0))
    for update in (mutation.get("entity_updates") or {}).values():
        living = update.get("living_agent")
        if isinstance(living, dict) and set(living) == {MERGE_WRAPPER_KEY}:
            # Sub-key merge write (narrowed social-action target write): stamp
            # the records inside the merge spec; apply_mutation merges them.
            living = living.get(MERGE_WRAPPER_KEY) or {}
        if isinstance(living, dict):
            for memory in (living.get("memories") or {}).values():
                if (memory.get("acquired_event_id") is None
                        and int(memory.get("last_recalled_tick", -1)) == tick):
                    memory["acquired_event_id"] = event_id
            for link in living.get("causal_links") or []:
                if link.get("accepted_event_id") is None and int(link.get("tick", -1)) == tick:
                    link["accepted_event_id"] = event_id
            current_decision = living.get("current_decision")
            if (isinstance(current_decision, dict)
                    and current_decision.get("accepted_event_id") is None
                    and int(current_decision.get("tick", -1)) == tick):
                current_decision["accepted_event_id"] = event_id
            for receipt in living.get("decision_history") or []:
                if (receipt.get("accepted_event_id") is None
                        and int(receipt.get("tick", -1)) == tick):
                    receipt["accepted_event_id"] = event_id
            for relation in (living.get("relationships") or {}).values():
                pending_tick = relation.get("pending_event_tick")
                if pending_tick is not None and int(pending_tick) == tick:
                    causal = list(relation.get("causal_event_ids") or [])
                    applied = list(relation.get("applied_event_ids") or [])
                    if event_id not in causal:
                        causal.append(event_id)
                    if event_id not in applied:
                        applied.append(event_id)
                    relation["causal_event_ids"] = causal[-16:]
                    relation["applied_event_ids"] = applied[-16:]
                    relation["pending_event_tick"] = None
                    relation["last_event_id"] = event_id
            for commitment in (living.get("commitments") or {}).values():
                if (commitment.get("created_event_id") is None
                        and int(commitment.get("created_tick", -1)) == tick):
                    commitment["created_event_id"] = event_id
                changed_tick = commitment.get("last_changed_tick")
                if changed_tick is not None and int(changed_tick) == tick:
                    commitment["last_event_id"] = event_id
        knowledge = update.get("knowledge")
        if isinstance(knowledge, dict):
            for fact in (knowledge.get("facts") or {}).values():
                if (fact.get("learned_event_id") is None
                        and int(fact.get("first_known_tick", -1)) == tick):
                    fact["learned_event_id"] = event_id
                    if fact.get("source_event_id") is None:
                        fact["source_event_id"] = event_id


def _stamp_living_action_provenance(
    proposal: dict, mutation: dict, event_id: str,
) -> None:
    meta = proposal.get("living_action")
    if not isinstance(meta, dict):
        return
    proposal_ids = list(meta.get("source_proposal_ids") or [])
    if proposal.get("proposal_id") not in proposal_ids:
        proposal_ids.append(proposal["proposal_id"])
    event_ids = list(meta.get("accepted_event_ids") or [])
    if event_id not in event_ids:
        event_ids.append(event_id)
    meta["source_proposal_ids"] = proposal_ids[-16:]
    meta["accepted_event_ids"] = event_ids[-16:]

    actor_update = (mutation.get("entity_updates") or {}).get(proposal.get("entity_id")) or {}
    action = actor_update.get("action")
    if isinstance(action, dict):
        action["source_proposal_id"] = proposal["proposal_id"]
        action["accepted_event_id"] = event_id
        action["source_proposal_ids"] = list(meta["source_proposal_ids"])
        action["accepted_event_ids"] = list(meta["accepted_event_ids"])
        action["physical_effects"] = list(meta.get("physical_effects") or [])
    for new_entity in (mutation.get("new_entities") or {}).values():
        if new_entity.get("type") == "signal":
            new_entity["source_event_id"] = event_id
            new_entity["last_event_id"] = event_id


def _stamp_new_entity_provenance(mutation: dict, event_id: str) -> None:
    """Give every canonically created entity an accepted-event origin."""
    for new_entity in (mutation.get("new_entities") or {}).values():
        new_entity.setdefault("creation_event_id", event_id)
        new_entity.setdefault("last_event_id", event_id)
        if new_entity.get("type") == "signal" and not new_entity.get("source_event_id"):
            new_entity["source_event_id"] = event_id


def _reject(proposal: dict, stage: str, reason_code: str, detail: str, tick: int,
            rejected: list) -> dict:
    # Integrity fix (KIMI review, 2026-07-25): the id has no order_index or
    # sequence component, so two structurally identical proposals rejected
    # in the same frame (same tick, content_hash prefix, entity_id) produced
    # byte-identical ids. uq_run_rejection_id (core/db.py) is a unique index
    # on (run_id, id), so the second insert fails, the frame aborts, and a
    # retry reproduces the identical collision -- wedging the run
    # permanently. Disambiguate ONLY on an actual collision (checked against
    # this frame's own rejections so far) so the common, non-colliding case
    # keeps its existing id exactly as before.
    base_id = f"rej-{tick}-{proposal['content_hash'][:10]}-{proposal['entity_id']}"
    existing_ids = {row["id"] for row in rejected}
    rejection_id = base_id
    suffix = 2
    while rejection_id in existing_ids:
        rejection_id = f"{base_id}-{suffix}"
        suffix += 1
    return {
        "id": rejection_id,
        "proposal_id": proposal["proposal_id"],
        "proposal_snapshot": proposal,
        "rejection_stage": stage,
        "reason_code": reason_code,
        "reason_detail": detail[:300],
        "simulation_time": tick,
        "entity_id": proposal["entity_id"],
    }


def run_commit_frame(entities: dict, domain_outputs: list, tick: int, lineage_key: str,
                      run_id: str, order_index_start: int, frame_id: str,
                      valid_causal_parent_event_ids: set | None = None,
                      entity_json_cache: dict | None = None,
                      debug_assert_fragment_cache: bool = False):
    """Runs one deterministic commit frame. Mutates `entities` in place.

    Returns (accepted_events, rejected_proposals, next_order_index).

    CORE-PERF-01 Slice B: `entity_json_cache`, when provided, is a caller-
    owned dict (persisted and reused across ticks, same pattern as
    `valid_causal_parent_event_ids`) that this function mutates in place to
    avoid re-serializing the whole world for every accepted proposal's
    canonical hash. `None` (the default) preserves the exact prior behaviour
    -- every existing caller that doesn't pass it is unaffected.
    `debug_assert_fragment_cache=True` additionally computes the hash the
    slow way on every accepted event and raises if it disagrees with the
    cached-splice result; used during the gate, never in normal runs (it
    defeats the optimization's purpose by doing both).
    """
    all_proposals = []
    seq = 0
    for output in domain_outputs:
        for p in output.proposals:
            all_proposals.append(normalize_proposal(p, seq))
            seq += 1

    ordered = sorted(all_proposals, key=order_key)

    accepted_events = []
    rejected = []
    order_index = order_index_start

    for proposal in ordered:
        scope_err = check_scope_exists(proposal, entities)
        if scope_err:
            rejected.append(_reject(proposal, "initial_validation", "precondition.entity_missing", scope_err, tick, rejected))
            continue

        interaction_err = validate_food_interaction(proposal, entities, tick)
        if interaction_err:
            rejected.append(_reject(proposal, "initial_validation", interaction_err, interaction_err, tick, rejected))
            continue

        transfer_err = validate_food_transfer(proposal, entities)
        if transfer_err:
            rejected.append(_reject(proposal, "initial_validation", transfer_err, transfer_err, tick, rejected))
            continue

        trade_err = validate_people_trade(proposal, entities)
        if trade_err:
            rejected.append(_reject(proposal, "initial_validation", trade_err, trade_err, tick, rejected))
            continue

        aid_err = validate_people_aid(proposal, entities)
        if aid_err:
            rejected.append(_reject(proposal, "initial_validation", aid_err, aid_err, tick, rejected))
            continue

        living_action_err = validate_living_action_proposal(proposal, entities)
        if living_action_err:
            rejected.append(_reject(
                proposal, "initial_validation", living_action_err,
                living_action_err, tick, rejected,
            ))
            continue

        social_action_err = validate_social_action_proposal(proposal, entities)
        if social_action_err:
            rejected.append(_reject(
                proposal, "initial_validation", social_action_err,
                social_action_err, tick, rejected,
            ))
            continue

        association_err = validate_association_proposal(proposal, entities)
        if association_err:
            rejected.append(_reject(
                proposal, "initial_validation", association_err,
                association_err, tick, rejected,
            ))
            continue

        group_state_err = validate_group_state_proposal(proposal, entities)
        if group_state_err:
            rejected.append(_reject(
                proposal, "initial_validation", group_state_err,
                group_state_err, tick, rejected,
            ))
            continue

        collective_err = validate_group_collective_proposal(proposal, entities)
        if collective_err:
            rejected.append(_reject(
                proposal, "initial_validation", collective_err,
                collective_err, tick, rejected,
            ))
            continue

        group_goal_err = validate_group_goal_proposal(proposal, entities)
        if group_goal_err:
            rejected.append(_reject(
                proposal, "initial_validation", group_goal_err,
                group_goal_err, tick, rejected,
            ))
            continue

        group_norm_err = validate_group_norm_proposal(proposal, entities)
        if group_norm_err:
            rejected.append(_reject(
                proposal, "initial_validation", group_norm_err,
                group_norm_err, tick, rejected,
            ))
            continue

        group_carriage_err = validate_group_carriage_proposal(proposal, entities)
        if group_carriage_err:
            rejected.append(_reject(
                proposal, "initial_validation", group_carriage_err,
                group_carriage_err, tick, rejected,
            ))
            continue

        if not proposal.get("is_exogenous"):
            causal_parents = proposal.get("causal_parent_event_ids") or []
            if not causal_parents:
                rejected.append(_reject(
                    proposal, "initial_validation", "causality.missing_parent",
                    "non-exogenous proposal without causal parent", tick, rejected,
                ))
                continue
            if valid_causal_parent_event_ids is not None:
                invalid = sorted(
                    set(causal_parents) - set(valid_causal_parent_event_ids)
                )
                if invalid:
                    rejected.append(_reject(
                        proposal, "initial_validation", "causality.invalid_parent",
                        f"causal parent not present in accepted stream or validated anchor: {invalid}",
                        tick, rejected,
                    ))
                    continue

        precond_err = evaluate_preconditions(proposal.get("preconditions", []), entities)
        if precond_err:
            reason_code = "conflict.resource_contention" if "claimed_tick" in precond_err else "precondition.failed"
            rejected.append(_reject(proposal, "commit_revalidation", reason_code, precond_err, tick, rejected))
            continue

        event_id = f"evt-{tick}-{order_index}-{proposal['content_hash'][:8]}"
        mutation = proposal["mutation"]
        mutation.setdefault("entity_updates", {}).setdefault(proposal["entity_id"], {})
        mutation["entity_updates"][proposal["entity_id"]]["last_event_id"] = event_id
        _stamp_new_entity_provenance(mutation, event_id)
        _stamp_food_interaction_provenance(proposal, mutation, event_id)
        _stamp_living_agent_provenance(proposal, mutation, event_id)
        _stamp_living_action_provenance(proposal, mutation, event_id)
        stamp_association_provenance(proposal, mutation, event_id)
        stamp_group_state_provenance(proposal, mutation, event_id)
        stamp_collective_action_provenance(proposal, mutation, event_id)
        stamp_group_goal_provenance(proposal, mutation, event_id)
        stamp_group_norm_provenance(proposal, mutation, event_id)
        stamp_group_carriage_provenance(proposal, mutation, event_id)

        apply_mutation(entities, mutation)
        if entity_json_cache is None:
            post_hash = canonical_hash(snapshot_for_hash(entities, tick, lineage_key))
        else:
            invalidate_entity_json_cache(entity_json_cache, mutation)
            spliced_json = spliced_snapshot_json(entities, tick, lineage_key, entity_json_cache)
            post_hash = hash_canonical_json_string(spliced_json)
            if debug_assert_fragment_cache:
                direct_hash = canonical_hash(snapshot_for_hash(entities, tick, lineage_key))
                if post_hash != direct_hash:
                    raise AssertionError(
                        "CORE-PERF-01 Slice B: fragment-cache splice diverged from "
                        f"direct canonical_json at tick {tick}, order_index {order_index}: "
                        f"{post_hash} != {direct_hash}"
                    )

        accepted_events.append({
            "id": event_id,
            "run_id": run_id,
            "frame_id": frame_id,
            "event_family": proposal["proposal_family"],
            "event_type": proposal["proposal_type"],
            "simulation_time": tick,
            "order_index": order_index,
            "causal_parent_event_ids": proposal.get("causal_parent_event_ids", []),
            "is_exogenous": proposal.get("is_exogenous", False),
            "entity_id": proposal["entity_id"],
            "touched_scope": proposal.get("touched_scope", []),
            "mutation": mutation,
            "post_state_hash": post_hash,
            "source_proposal_id": proposal["proposal_id"],
            "proposer_engine_id": proposal["proposer_engine_id"],
            "explanation": proposal.get("explanation", ""),
        })
        if proposal.get("transfer"):
            accepted_events[-1]["transfer"] = proposal["transfer"]
        if proposal.get("trade"):
            accepted_events[-1]["trade"] = proposal["trade"]
        if proposal.get("interaction"):
            accepted_events[-1]["interaction"] = proposal["interaction"]
        if proposal.get("living_action"):
            accepted_events[-1]["living_action"] = proposal["living_action"]
        if proposal.get("social_action"):
            social_action = proposal["social_action"]
            commitment = social_action.get("commitment")
            if isinstance(commitment, dict):
                if commitment.get("created_event_id") is None:
                    commitment["created_event_id"] = event_id
                commitment["last_event_id"] = event_id
            accepted_events[-1]["social_action"] = social_action
        if proposal.get("association_update"):
            accepted_events[-1]["association_update"] = proposal["association_update"]
        if proposal.get("group_state_update"):
            accepted_events[-1]["group_state_update"] = proposal["group_state_update"]
        if proposal.get("collective_action"):
            accepted_events[-1]["collective_action"] = proposal["collective_action"]
        if proposal.get("group_goal_update"):
            accepted_events[-1]["group_goal_update"] = proposal["group_goal_update"]
        if proposal.get("group_norm_update"):
            accepted_events[-1]["group_norm_update"] = proposal["group_norm_update"]
        order_index += 1

    return accepted_events, rejected, order_index
