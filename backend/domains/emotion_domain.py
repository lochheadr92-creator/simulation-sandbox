"""Emotion Domain — standalone hybrid A+C architecture.

Emotions are stored in `living_agent.emotions` (gradient modulation for
living_settlement) and extreme states generate interruptive action proposals
(FLEE, CONFRONT, CELEBRATE, MOURN) that compete in the commit pipeline.

Priority 8: runs before living_settlement (10) so emotion state updates are
committed and visible when living_settlement reads them.
"""
from __future__ import annotations

import copy

from domains.base import DomainEngine, DomainOutput
from domains.emotion_contracts import (
    ACTION_BASE_SCORES,
    ACTION_THRESHOLDS,
    EMOTION_KINDS,
    _bounded,
    _compat_emotions,
    derive_emotion_deltas,
    empty_emotions,
)


class EmotionDomain(DomainEngine):
    engine_id = "emotion"
    engine_version = "1.0.0"
    engine_priority = 8  # before living_settlement (10)
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        return [
            entity_id for entity_id, entity in sorted(entities.items())
            if entity.get("type") == "person" and entity.get("alive", True)
            and entity.get("living_agent")
        ]

    def activate(self, frame) -> DomainOutput:
        proposals = []
        diagnostics = {}
        tick = frame.simulation_time
        night = getattr(frame, "night", False)

        for entity_id in sorted(frame.due_entity_ids):
            entity = frame.entities.get(entity_id)
            if not entity or not entity.get("alive", True):
                continue

            state = entity.get("living_agent") or {}
            existing = _compat_emotions(state.get("emotions"))
            deltas = derive_emotion_deltas(state, entity, tick)

            # Build new emotion state
            new_emotions = dict(existing)
            for kind in EMOTION_KINDS:
                new_emotions[kind] = _bounded(new_emotions.get(kind, 0) + deltas[kind])

            # Recompute derived fields
            values = {k: new_emotions[k] for k in EMOTION_KINDS}
            dominant = max(values, key=values.get)
            new_emotions["dominant_emotion"] = dominant if values[dominant] > 0 else None
            new_emotions["arousal"] = _bounded(max(values.values()))
            positive = values.get("joy", 0) + values.get("calm", 0) + values.get("surprise", 0) // 2
            negative = values.get("fear", 0) + values.get("anger", 0) + values.get("sadness", 0) + values.get("disgust", 0)
            new_emotions["valence"] = max(-1000, min(1000, positive - negative))

            # Mutation: update emotions in living_agent state
            mutation = {
                "entity_updates": {
                    entity_id: {
                        "living_agent": {
                            **state,
                            "emotions": new_emotions,
                        },
                    },
                },
            }

            # Action proposals for extreme emotional states (C-path)
            action_proposals = self._build_action_proposals(
                entity_id, entity, state, new_emotions, tick, night,
            )

            # State-update proposal (always emitted — A-path)
            proposals.append({
                "proposal_family": "emotion",
                "proposal_type": "emotion_update",
                "proposer_engine_id": self.engine_id,
                "proposer_engine_version": self.engine_version,
                "entity_id": entity_id,
                "causal_parent_event_ids": [],
                "is_exogenous": False,
                "requested_time": tick,
                "phase": self.phase,
                "engine_priority": self.engine_priority,
                "touched_scope": [entity_id],
                "preconditions": [],
                "mutation": mutation,
                "explanation": (
                    f"emotion update: dominant={new_emotions['dominant_emotion']} "
                    f"fear={new_emotions['fear']} joy={new_emotions['joy']} "
                    f"anger={new_emotions['anger']} sadness={new_emotions['sadness']}"
                ),
            })

            proposals.extend(action_proposals)

            diagnostics[entity_id] = {
                "emotions": new_emotions,
                "deltas": deltas,
                "action_proposals_generated": len(action_proposals),
            }

        return DomainOutput(proposals=proposals, diagnostics=diagnostics)

    def _build_action_proposals(self, entity_id: str, entity: dict, state: dict,
                                emotions: dict, tick: int, night: bool) -> list:
        """Generate interruptive action proposals for extreme emotions."""
        proposals = []
        position = copy.deepcopy(entity.get("position"))
        people = {
            eid: e for eid, e in sorted(entity.get("_observed_people", {}).items())
        } if isinstance(entity.get("_observed_people"), dict) else {}

        # FLEE: extreme fear + any visible danger
        if emotions.get("fear", 0) >= ACTION_THRESHOLDS["fear"]:
            # Find the direction away from nearest perceived danger
            danger_obs = entity.get("_nearest_danger_position")
            flee_pos = self._flee_target(position, danger_obs)
            if flee_pos:
                proposals.append(self._action_proposal(
                    entity_id, tick, "FLEE", "flee", ACTION_BASE_SCORES["FLEE"],
                    target_pos=flee_pos,
                    explanation=f"fear={emotions['fear']} exceeds threshold {ACTION_THRESHOLDS['fear']}; fleeing",
                ))

        # CONFRONT: extreme anger + someone to confront
        if emotions.get("anger", 0) >= ACTION_THRESHOLDS["anger"] and people:
            target_id = sorted(people)[0]
            proposals.append(self._action_proposal(
                entity_id, tick, "CONFRONT", "confront", ACTION_BASE_SCORES["CONFRONT"],
                target_id=target_id,
                explanation=f"anger={emotions['anger']} exceeds threshold {ACTION_THRESHOLDS['anger']}; confronting {target_id}",
            ))

        # CELEBRATE: extreme joy + people nearby
        if emotions.get("joy", 0) >= ACTION_THRESHOLDS["joy"] and people:
            target_id = sorted(people)[0]
            proposals.append(self._action_proposal(
                entity_id, tick, "CELEBRATE", "celebrate", ACTION_BASE_SCORES["CELEBRATE"],
                target_id=target_id,
                explanation=f"joy={emotions['joy']} exceeds threshold {ACTION_THRESHOLDS['joy']}; celebrating with {target_id}",
            ))

        # MOURN: extreme sadness + alone
        if emotions.get("sadness", 0) >= ACTION_THRESHOLDS["sadness"] and not people:
            proposals.append(self._action_proposal(
                entity_id, tick, "MOURN", "mourn", ACTION_BASE_SCORES["MOURN"],
                explanation=f"sadness={emotions['sadness']} exceeds threshold {ACTION_THRESHOLDS['sadness']}; mourning alone",
            ))

        return proposals

    def _action_proposal(self, entity_id: str, tick: int, goal: str, action_type: str,
                         score: int, *, target_id: str | None = None,
                         target_pos: dict | None = None, explanation: str = "") -> dict:
        return {
            "proposal_family": "emotion",
            "proposal_type": "emotional_action",
            "proposer_engine_id": self.engine_id,
            "proposer_engine_version": self.engine_version,
            "entity_id": entity_id,
            "causal_parent_event_ids": [],
            "is_exogenous": False,
            "requested_time": tick,
            "phase": self.phase,
            "engine_priority": self.engine_priority - 1,  # action proposals win over state updates
            "touched_scope": [entity_id, target_id] if target_id else [entity_id],
            "preconditions": [],
            "mutation": {
                "entity_updates": {
                    entity_id: {
                        "action": {
                            "type": action_type,
                            "target_entity_id": target_id,
                            "target_pos": copy.deepcopy(target_pos),
                            "emotional": True,
                            "score": score,
                        },
                    },
                },
            },
            "explanation": explanation,
        }

    @staticmethod
    def _flee_target(position: dict | None, danger_pos: dict | None) -> dict | None:
        """Return a position one step away from danger. If no danger known, move north."""
        if not position:
            return None
        px = position.get("x", 0)
        py = position.get("y", 0)
        if danger_pos:
            dx = px - danger_pos.get("x", px)
            dy = py - danger_pos.get("y", py)
            # Move one step in the direction away from danger
            step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            return {"x": px + step_x, "y": py + step_y}
        return {"x": px, "y": py - 1}  # Default flee: north
