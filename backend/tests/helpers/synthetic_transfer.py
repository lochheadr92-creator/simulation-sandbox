"""Kernel-only synthetic resource-transfer proposals for persistence stress tests.

These helpers construct ordinary production-shaped proposals that flow through
the real commit pipeline. They do NOT register a production domain handler and
do NOT implement GIVE_FOOD gameplay logic.
"""
from domains.base import DomainOutput


def make_transfer_proposal(
    *,
    source_id: str,
    dest_id: str,
    amount: int,
    tick: int,
    field: str = "resource",
    phase: str = "agent",
    engine_priority: int = 10,
    causal_parent_event_ids: list | None = None,
    proposer_engine_id: str = "test.synthetic_transfer",
    is_exogenous: bool = True,
) -> dict:
    """Build one two-entity transfer proposal with commit-time preconditions."""
    return {
        "proposal_family": "test_transfer",
        "proposal_type": "resource_transfer",
        "proposer_engine_id": proposer_engine_id,
        "proposer_engine_version": "0.0.0-test",
        "entity_id": source_id,
        "causal_parent_event_ids": list(causal_parent_event_ids or []),
        "is_exogenous": is_exogenous,
        "requested_time": tick,
        "phase": phase,
        "engine_priority": engine_priority,
        "touched_scope": sorted([source_id, dest_id]),
        "preconditions": [
            {"entity_id": source_id, "field": field, "op": "gte", "value": amount},
            {"entity_id": dest_id, "field": field, "op": "gte", "value": 0},
        ],
        "mutation": {
            "entity_updates": {
                source_id: {field: None},  # filled by apply helper below
                dest_id: {field: None},
            },
            "new_entities": {},
        },
        "explanation": f"transfer {amount} {field} {source_id}->{dest_id}",
        # Absolute post-mutation values are not known without reading state;
        # callers should use make_transfer_proposals_from_state or patch deltas
        # via absolute targets in stress fixtures.
        "_transfer": {
            "source_id": source_id,
            "dest_id": dest_id,
            "amount": amount,
            "field": field,
        },
    }


def materialize_transfer_mutation(proposal: dict, entities: dict) -> dict:
    """Convert relative transfer metadata into absolute field updates.

    Call this immediately before run_commit_frame so preconditions see current
    balances and mutation writes absolute post-state values (commit pipeline
    uses assignment, not relative deltas).
    """
    p = dict(proposal)
    meta = p.pop("_transfer")
    field = meta["field"]
    src, dst, amount = meta["source_id"], meta["dest_id"], meta["amount"]
    src_bal = entities[src][field]
    dst_bal = entities[dst][field]
    p["mutation"] = {
        "entity_updates": {
            src: {field: src_bal - amount},
            dst: {field: dst_bal + amount},
        },
        "new_entities": {},
    }
    p["preconditions"] = [
        {"entity_id": src, "field": field, "op": "gte", "value": amount},
        {"entity_id": dst, "field": field, "op": "gte", "value": 0},
    ]
    return p


def overlapping_transfer_batch(entities: dict, tick: int, rounds: int = 20) -> list:
    """100 overlapping A/B/C transfers for stress tests (6 pairs * rounds, default 20*5=100).

    Default: 20 rounds of the 5 distinct directed edges among {A,B,C} that
    keep multi-way contention (actually 6 edges * ~16-17 = 100).
    """
    pairs = [
        ("A", "B"), ("A", "C"),
        ("B", "A"), ("B", "C"),
        ("C", "A"), ("C", "B"),
    ]
    proposals = []
    amount = 1
    n = 0
    while n < 100:
        for src, dst in pairs:
            if n >= 100:
                break
            raw = make_transfer_proposal(
                source_id=src, dest_id=dst, amount=amount, tick=tick,
                engine_priority=10 + (n % 3),
            )
            # materialize against the *initial* snapshot; commit-time
            # revalidation + sequential apply resolves contention.
            # Absolute values from initial state would go stale — use relative
            # materialization against entities as they stand only for the first
            # proposal. For batch stress we set mutations as relative via a
            # deferred materialization pattern: store amount and resolve in
            # ordered commit by using preconditions only and computing from
            # live state in a thin DomainOutput factory.
            proposals.append(raw)
            n += 1
    return proposals


def domain_output_from_transfers(raw_proposals: list, entities: dict) -> DomainOutput:
    """Materialize absolute mutations from current entities for each proposal.

    Note: for multi-proposal frames, sequential materialization against the
    pre-frame snapshot is intentional — the commit pipeline revalidates
    preconditions against progressive state, so stale absolute mutations that
    would go negative fail on precondition.gte at commit time when earlier
    winners already spent the resource. We materialize from the *current*
    progressive view only inside a custom loop used by tests.
    """
    # Leave _transfer markers; tests that call run_commit_frame should first
    # expand via progressive_materialize.
    return DomainOutput(proposals=list(raw_proposals))


def _intent_order_key(p: dict):
    """Stable order from transfer intent (not absolute post-mutation balances)."""
    from core.commit_pipeline import PHASE_RANK
    meta = p.get("_transfer") or {}
    return (
        p["requested_time"],
        PHASE_RANK.get(p["phase"], 99),
        p.get("engine_priority", 100),
        meta.get("source_id", p.get("entity_id", "")),
        meta.get("dest_id", ""),
        meta.get("amount", 0),
        p.get("explanation", ""),
    )


def progressive_commit(entities: dict, raw_proposals: list, tick: int, lineage_key: str,
                       run_id: str, order_index_start: int, frame_id: str):
    """Apply overlapping transfers through the real commit pipeline.

    Each proposal is ordered by stable transfer intent, then materialized against
    progressive live state so preconditions reject exhausted sources and absolute
    field assignments stay resource-conserving.
    """
    from core.commit_pipeline import normalize_proposal, run_commit_frame
    from domains.base import DomainOutput

    ordered = sorted((dict(p) for p in raw_proposals), key=_intent_order_key)

    all_accepted = []
    all_rejected = []
    order_index = order_index_start
    for prop in ordered:
        live = materialize_transfer_mutation(prop, entities)
        live = normalize_proposal(live, 0)
        accepted, rejected, order_index = run_commit_frame(
            entities, [DomainOutput(proposals=[live])], tick, lineage_key,
            run_id, order_index, frame_id,
        )
        all_accepted.extend(accepted)
        all_rejected.extend(rejected)
    return all_accepted, all_rejected, order_index
