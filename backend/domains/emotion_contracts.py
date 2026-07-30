"""Emotion Domain contracts — Schema A+C hybrid.

Emotions are stored inside `living_agent.emotions` (gradient modulation)
and the Emotion domain also emits action proposals for extreme states
(interruptive actions: FLEE, CONFRONT, CELEBRATE, MOURN).
"""
from __future__ import annotations

from core.hashing import canonical_hash


EMOTION_SCHEMA_VERSION = "emotion-v1"

# Canonical emotion dimensions — all bounded 0..1000
EMOTION_KINDS = (
    "joy",
    "fear",
    "anger",
    "sadness",
    "disgust",
    "surprise",
    "calm",
)

# Thresholds for interruptive action proposals
ACTION_THRESHOLDS = {
    "fear": 700,   # → FLEE when danger visible
    "anger": 700,  # → CONFRONT when target present
    "joy": 700,    # → CELEBRATE when people nearby
    "sadness": 750,  # → MOURN when alone
}

# Base scores for emotional action proposals (must compete with survival)
ACTION_BASE_SCORES = {
    "FLEE": 2400,
    "CONFRONT": 2200,
    "CELEBRATE": 1800,
    "MOURN": 1600,
}

# Gradient increments applied by living_settlement scorer
GRADIENT_INCREMENTS = {
    "fear": {
        "REST": 30,
        "WANDER": -10,
        "EXPLORE": -20,
        "REQUEST_HELP": 25,
    },
    "anger": {
        "CONFRONT": 40,
        "COOPERATE": -20,
        "REST": -15,
    },
    "joy": {
        "COOPERATE": 20,
        "SHARE_INFORMATION": 15,
        "TRADE_RESOURCES": 10,
    },
    "sadness": {
        "REST": 20,
        "WANDER": -10,
        "COOPERATE": -15,
    },
}


def empty_emotions() -> dict:
    return {
        "schema_version": EMOTION_SCHEMA_VERSION,
        **{kind: 0 for kind in EMOTION_KINDS},
        "dominant_emotion": None,
        "arousal": 0,
        "valence": 0,
    }


def _bounded(value: int, low: int = 0, high: int = 1000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = low
    return max(low, min(high, parsed))


def _compat_emotions(existing: dict | None) -> dict:
    base = empty_emotions()
    if not isinstance(existing, dict):
        return base
    if existing.get("schema_version") not in (None, EMOTION_SCHEMA_VERSION):
        # Unknown version — discard and return empty
        return base
    for kind in EMOTION_KINDS:
        if kind in existing:
            base[kind] = _bounded(existing[kind])
    # Computed fields
    values = {k: base[k] for k in EMOTION_KINDS}
    if values:
        dominant = max(values, key=values.get)
        base["dominant_emotion"] = dominant if values[dominant] > 0 else None
        base["arousal"] = _bounded(max(values.values()))
        # Valence: positive (joy, calm, surprise) minus negative (fear, anger, sadness, disgust)
        positive = values.get("joy", 0) + values.get("calm", 0) + values.get("surprise", 0) // 2
        negative = values.get("fear", 0) + values.get("anger", 0) + values.get("sadness", 0) + values.get("disgust", 0)
        base["valence"] = max(-1000, min(1000, positive - negative))
    return base


def derive_emotion_deltas(state: dict, entity: dict, tick: int) -> dict:
    """Compute proposed emotion changes from current state.

    Reads pressures, relationships, memories, recent actions.
    Returns a dict of {emotion_kind: delta_int} bounded per-tick.
    """
    deltas = {kind: 0 for kind in EMOTION_KINDS}
    pressures = state.get("pressures") or {}
    relationships = state.get("relationships") or {}
    memories = state.get("memories") or {}
    history = state.get("decision_history") or []

    # Fear from safety pressure and danger memories
    safety = int((pressures.get("safety") or {}).get("severity", 0))
    fear_pressure = (safety - 300) // 4
    deltas["fear"] += max(0, fear_pressure)

    threat_memories = [
        m for m in memories.values()
        if m.get("meaningful_kind") == "threat_observed"
        and tick - int(m.get("tick", tick)) <= 8
    ]
    deltas["fear"] += len(threat_memories) * 40

    # Anger from resentment in relationships
    resentment = sum(
        int(r.get("resentment", 0)) for r in relationships.values()
    )
    deltas["anger"] += resentment // 20

    # Joy from positive relationships and recent cooperation
    affection = sum(
        int(r.get("affection", 0)) for r in relationships.values()
    )
    deltas["joy"] += affection // 25

    recent_cooperate = sum(
        1 for h in history[-3:]
        if (h.get("selected") or {}).get("direct_action_type") == "cooperate"
    )
    deltas["joy"] += recent_cooperate * 30

    # Sadness from failed plans and losses
    failed = sum(
        1 for h in history[-5:]
        if h.get("decision_kind") == "failed_plan_replan"
    )
    deltas["sadness"] += failed * 50

    # Calm inverse to overall arousal
    arousal = deltas["fear"] + deltas["anger"] + deltas["surprise"]
    deltas["calm"] = max(-60, -arousal // 3)

    # Decay all emotions toward baseline (0) — passive cooling
    existing = _compat_emotions((state.get("emotions") or {}))
    for kind in EMOTION_KINDS:
        current = existing.get(kind, 0)
        if kind != "calm":
            decay = -max(2, current // 20)  # 5% decay, minimum 2
            deltas[kind] += decay

    # Bound per-tick deltas so emotions don't jump wildly
    for kind in EMOTION_KINDS:
        deltas[kind] = max(-80, min(80, deltas[kind]))

    return deltas
