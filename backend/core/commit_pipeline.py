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
from core.hashing import canonical_hash
from core.mutations import apply_mutation, snapshot_for_hash
from core.constants import CRITICAL_THRESHOLD, FOOD_TRANSFER_QUANTITY, FOOD_TRANSFER_SURPLUS
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


def evaluate_preconditions(preconditions: list, entities: dict):
    for cond in preconditions:
        eid = cond["entity_id"]
        entity = entities.get(eid)
        if entity is None:
            return f"entity_missing:{eid}"
        value = entity.get(cond["field"])
        if not OPS[cond["op"]](value, cond["value"]):
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


def _reject(proposal: dict, stage: str, reason_code: str, detail: str, tick: int) -> dict:
    return {
        "id": f"rej-{tick}-{proposal['content_hash'][:10]}-{proposal['entity_id']}",
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
                      valid_causal_parent_event_ids: set | None = None):
    """Runs one deterministic commit frame. Mutates `entities` in place.

    Returns (accepted_events, rejected_proposals, next_order_index).
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
            rejected.append(_reject(proposal, "initial_validation", "precondition.entity_missing", scope_err, tick))
            continue

        interaction_err = validate_food_interaction(proposal, entities, tick)
        if interaction_err:
            rejected.append(_reject(proposal, "initial_validation", interaction_err, interaction_err, tick))
            continue

        transfer_err = validate_food_transfer(proposal, entities)
        if transfer_err:
            rejected.append(_reject(proposal, "initial_validation", transfer_err, transfer_err, tick))
            continue

        living_action_err = validate_living_action_proposal(proposal, entities)
        if living_action_err:
            rejected.append(_reject(
                proposal, "initial_validation", living_action_err,
                living_action_err, tick,
            ))
            continue

        social_action_err = validate_social_action_proposal(proposal, entities)
        if social_action_err:
            rejected.append(_reject(
                proposal, "initial_validation", social_action_err,
                social_action_err, tick,
            ))
            continue

        association_err = validate_association_proposal(proposal, entities)
        if association_err:
            rejected.append(_reject(
                proposal, "initial_validation", association_err,
                association_err, tick,
            ))
            continue

        if not proposal.get("is_exogenous"):
            causal_parents = proposal.get("causal_parent_event_ids") or []
            if not causal_parents:
                rejected.append(_reject(
                    proposal, "initial_validation", "causality.missing_parent",
                    "non-exogenous proposal without causal parent", tick,
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
                        tick,
                    ))
                    continue

        precond_err = evaluate_preconditions(proposal.get("preconditions", []), entities)
        if precond_err:
            reason_code = "conflict.resource_contention" if "claimed_tick" in precond_err else "precondition.failed"
            rejected.append(_reject(proposal, "commit_revalidation", reason_code, precond_err, tick))
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

        apply_mutation(entities, mutation)
        post_hash = canonical_hash(snapshot_for_hash(entities, tick, lineage_key))

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
        order_index += 1

    return accepted_events, rejected, order_index
