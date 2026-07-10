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
                      run_id: str, order_index_start: int, frame_id: str):
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

        if not proposal.get("is_exogenous") and not proposal.get("causal_parent_event_ids"):
            rejected.append(_reject(proposal, "initial_validation", "causality.missing_parent",
                                     "non-exogenous proposal without causal parent", tick))
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
        order_index += 1

    return accepted_events, rejected, order_index
