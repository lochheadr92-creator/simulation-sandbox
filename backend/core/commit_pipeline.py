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
        "requested_time": p["requested_time"],
        "phase": p["phase"],
    }
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
    """Core-owned validation for the narrow Phase 5B transfer contract."""
    if proposal.get("proposal_type") != "give_food":
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

        transfer_err = validate_food_transfer(proposal, entities)
        if transfer_err:
            rejected.append(_reject(proposal, "initial_validation", transfer_err, transfer_err, tick))
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
        order_index += 1

    return accepted_events, rejected, order_index
