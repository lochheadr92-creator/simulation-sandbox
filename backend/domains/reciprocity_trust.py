"""Phase 5B5 — Derived reciprocity and trust (reciprocity-trust-v1).

Rebuildable, observer-relative projection from interaction-memory-v1 facts only.
Not a mutable canonical relationship field. Integer arithmetic only.
"""
from __future__ import annotations

from domains.interaction_memory import (
    INTERACTION_MEMORY_VERSION,
    KIND_HELPED,
    KIND_OFFERED,
    KIND_REFUSED,
    KIND_REQUESTED,
    KIND_WITNESSED,
    list_interaction_facts,
)

RECIPROCITY_TRUST_VERSION = "reciprocity-trust-v1"

# Integer weights (per fact before recency scaling). Scores clamped to [0, 100].
WEIGHT_HELPED_SUPPORT = 40
WEIGHT_WITNESSED_SUPPORT = 15
WEIGHT_REFUSED_CAUTION = 40
WEIGHT_REQUESTED_CONFIDENCE = 5
WEIGHT_OFFERED_CONFIDENCE = 5

# Recency: weight = max(0, 100 - age_ticks * DECAY_PER_TICK)
DECAY_PER_TICK = 2
RECENCY_FULL = 100
SCORE_MAX = 100
SCORE_MIN = 0

# Narrow behavioural influence thresholds (inspectable)
CAUTION_AUTO_REFUSE_THRESHOLD = 50  # auto-accept blocked when caution >= this
# Support used only for stable recipient ranking among equal survival eligibility.


def _recency_weight(accepted_event_tick: int, current_tick: int) -> int:
    age = max(0, int(current_tick) - int(accepted_event_tick))
    return max(0, RECENCY_FULL - age * DECAY_PER_TICK)


def _scaled(base: int, recency: int) -> int:
    return (int(base) * int(recency)) // RECENCY_FULL


def _clamp(v: int) -> int:
    return max(SCORE_MIN, min(SCORE_MAX, int(v)))


def derive_subject_view(
    knowledge: dict,
    *,
    observer_id: str,
    subject_id: str,
    current_tick: int,
) -> dict:
    """Observer-relative derived view of one subject. Pure; no mutation."""
    facts = [
        f for f in list_interaction_facts(knowledge)
        if f.get("observer_id") == observer_id and f.get("subject_id") == subject_id
    ]
    # Stable order for accumulation (not dependent on dict insertion)
    facts = sorted(
        facts,
        key=lambda f: (
            int(f.get("accepted_event_tick", 0)),
            f.get("kind", ""),
            f.get("fact_id", ""),
        ),
    )

    support = 0
    caution = 0
    confidence = 0
    helped_count = 0
    refused_count = 0
    witnessed_count = 0
    request_count = 0
    offer_count = 0
    contributions = []

    for fact in facts:
        kind = fact.get("kind")
        recency = _recency_weight(fact.get("accepted_event_tick", 0), current_tick)
        if recency <= 0:
            continue
        if kind == KIND_HELPED:
            delta = _scaled(WEIGHT_HELPED_SUPPORT, recency)
            support += delta
            confidence += delta
            helped_count += 1
            contributions.append({"kind": kind, "delta_support": delta, "fact_id": fact["fact_id"]})
        elif kind == KIND_WITNESSED:
            delta = _scaled(WEIGHT_WITNESSED_SUPPORT, recency)
            support += delta
            confidence += max(1, delta // 2)
            witnessed_count += 1
            contributions.append({"kind": kind, "delta_support": delta, "fact_id": fact["fact_id"]})
        elif kind == KIND_REFUSED:
            delta = _scaled(WEIGHT_REFUSED_CAUTION, recency)
            caution += delta
            confidence += delta
            refused_count += 1
            contributions.append({"kind": kind, "delta_caution": delta, "fact_id": fact["fact_id"]})
        elif kind == KIND_REQUESTED:
            delta = _scaled(WEIGHT_REQUESTED_CONFIDENCE, recency)
            confidence += delta
            request_count += 1
            contributions.append({"kind": kind, "delta_confidence": delta, "fact_id": fact["fact_id"]})
        elif kind == KIND_OFFERED:
            delta = _scaled(WEIGHT_OFFERED_CONFIDENCE, recency)
            confidence += delta
            offer_count += 1
            contributions.append({"kind": kind, "delta_confidence": delta, "fact_id": fact["fact_id"]})

    # Reciprocity tendency: net of support vs caution (signed then mapped note)
    # Keep as separate bounded components + net integer in [-100, 100]
    net = _clamp(support) - _clamp(caution)
    net = max(-SCORE_MAX, min(SCORE_MAX, net))

    return {
        "version": RECIPROCITY_TRUST_VERSION,
        "source_memory_version": INTERACTION_MEMORY_VERSION,
        "observer_id": observer_id,
        "subject_id": subject_id,
        "current_tick": int(current_tick),
        "support_score": _clamp(support),
        "caution_score": _clamp(caution),
        "confidence_score": _clamp(confidence),
        "reciprocity_net": net,
        "fact_counts": {
            "helped": helped_count,
            "refused": refused_count,
            "witnessed_assistance": witnessed_count,
            "requested": request_count,
            "offered": offer_count,
        },
        "contributions": contributions[:16],
        "derived": True,
        "canonical": False,
    }


def list_subject_views(knowledge: dict, *, observer_id: str, current_tick: int) -> list[dict]:
    subjects = sorted({
        f.get("subject_id")
        for f in list_interaction_facts(knowledge)
        if f.get("observer_id") == observer_id and f.get("subject_id")
    })
    return [
        derive_subject_view(
            knowledge, observer_id=observer_id, subject_id=sid, current_tick=current_tick,
        )
        for sid in subjects
    ]


def support_score_for(knowledge: dict, observer_id: str, subject_id: str, current_tick: int) -> int:
    return derive_subject_view(
        knowledge, observer_id=observer_id, subject_id=subject_id, current_tick=current_tick,
    )["support_score"]


def caution_score_for(knowledge: dict, observer_id: str, subject_id: str, current_tick: int) -> int:
    return derive_subject_view(
        knowledge, observer_id=observer_id, subject_id=subject_id, current_tick=current_tick,
    )["caution_score"]


def should_auto_accept_with_caution(
    knowledge: dict, observer_id: str, subject_id: str, current_tick: int,
) -> bool:
    """False when derived caution against subject blocks auto-accept."""
    return caution_score_for(knowledge, observer_id, subject_id, current_tick) < CAUTION_AUTO_REFUSE_THRESHOLD
