"""Bounded, read-only projection of canonical living-agent state.

This module formats one actor's owned state for inspection.  It never reads
other entities to adjudicate beliefs, so reported or contradicted knowledge is
shown as uncertain without leaking canonical world truth back to the actor.
"""
from __future__ import annotations

import copy

from domains.living_agent_contracts import LIMITS, compat_living_agent_state


LIVING_AGENT_PROJECTION_VERSION = "living-agent-projection-v1"
MAX_NEEDS = 16
MAX_WANTS = 12
MAX_BELIEFS = 20
MAX_MEMORIES = 12
MAX_RELATIONSHIPS = 12
MAX_COMMITMENTS = 12
MAX_CAUSAL_LINKS = 16
MAX_CANDIDATES = 8


def _recent(values, *, tick_key: str, limit: int) -> list[dict]:
    return [
        copy.deepcopy(value)
        for value in sorted(
            values,
            key=lambda value: (int(value.get(tick_key, 0)), str(value.get("id", ""))),
            reverse=True,
        )[:limit]
    ]


def _needs(state: dict) -> list[dict]:
    rows = []
    for kind, pressure in sorted((state.get("pressures") or {}).items()):
        rows.append({
            "kind": kind,
            "severity": int(pressure.get("severity", 0)),
            "predicted_severity": int(pressure.get("predicted_severity", 0)),
            "urgency": int(pressure.get("urgency", 0)),
            "source": pressure.get("source"),
        })
    return sorted(rows, key=lambda row: (-row["urgency"], -row["severity"], row["kind"]))[:MAX_NEEDS]


def _wants(state: dict) -> list[dict]:
    rows = [
        {
            "want_id": want.get("want_id"),
            "want_type": want.get("want_type"),
            "desired_outcome": want.get("desired_outcome"),
            "target_id": want.get("target_id"),
            "status": want.get("status"),
            "strength": int(want.get("strength", 0)),
            "source_pressures": list(want.get("source_pressures") or []),
            "blocked_reason": want.get("blocked_reason"),
        }
        for want in (state.get("wants") or {}).values()
    ]
    return sorted(rows, key=lambda row: (row["status"] != "active", -row["strength"], row["want_id"] or ""))[:MAX_WANTS]


def _beliefs(entity: dict, tick: int) -> tuple[list[dict], dict]:
    facts = list(((entity.get("knowledge") or {}).get("facts") or {}).values())
    rows = []
    provenance_counts = {}
    for fact in facts:
        provenance = fact.get("provenance_kind", "legacy")
        provenance_counts[provenance] = provenance_counts.get(provenance, 0) + 1
        stale_after = fact.get("stale_after_tick")
        stale = stale_after is not None and int(tick) > int(stale_after)
        status = fact.get("status", "unclassified")
        may_be_wrong = (
            provenance in ("reported", "rumoured", "inferred")
            or status in ("unconfirmed", "contradicted")
            or stale
        )
        rows.append({
            "fact_id": fact.get("fact_id"),
            "subject_id": fact.get("subject"),
            "fact_type": fact.get("fact_type"),
            "properties": copy.deepcopy(fact.get("properties") or {}),
            "confidence": int(fact.get("confidence", 0)),
            "provenance_kind": provenance,
            "status": status,
            "may_be_wrong": may_be_wrong,
            "stale": stale,
            "source_entity_id": fact.get("source_entity_id"),
            "source_event_id": fact.get("source_event_id"),
            "last_confirmed_tick": fact.get("last_confirmed_tick"),
            "contradiction_count": int(fact.get("contradiction_count", 0)),
        })
    rows.sort(key=lambda row: (
        not row["may_be_wrong"],
        -int(row["last_confirmed_tick"] or 0),
        row["fact_id"] or "",
    ))
    return rows[:MAX_BELIEFS], {
        "fact_count": len(facts),
        "provenance_counts": {key: provenance_counts[key] for key in sorted(provenance_counts)},
        "displayed": min(len(facts), MAX_BELIEFS),
        "truncated": len(facts) > MAX_BELIEFS,
    }


def _trying(entity: dict, state: dict) -> dict:
    action = copy.deepcopy(entity.get("action") or {})
    plan = copy.deepcopy(entity.get("plan") or {})
    paused = copy.deepcopy(entity.get("paused_living_plan") or entity.get("paused"))
    return {
        "current_goal": entity.get("current_goal") or plan.get("goal"),
        "plan": {
            "plan_id": plan.get("plan_id"),
            "goal": plan.get("goal"),
            "goal_id": plan.get("goal_id"),
            "status": plan.get("status"),
            "steps": list(plan.get("steps") or [])[:LIMITS.planning_depth],
            "step_index": int(plan.get("step_index", 0)),
            "failure_reason": plan.get("failure_reason"),
            "replan_of": plan.get("replan_of"),
        },
        "action": {
            "action_id": action.get("action_id"),
            "type": action.get("type"),
            "status": action.get("status"),
            "target_entity_id": action.get("target_entity_id"),
            "target_pos": copy.deepcopy(action.get("target_pos")),
            "progress": action.get("progress"),
            "physical_effects": list(action.get("physical_effects") or []),
            "accepted_event_id": action.get("accepted_event_id"),
        },
        "interruption": {
            "interrupted_plan_id": action.get("interrupted_plan_id"),
            "reason": action.get("interruption_reason"),
            "paused_plan": paused,
        },
        "failed_goal_counts": copy.deepcopy(entity.get("living_failed_goal_counts") or {}),
    }


def _why(state: dict) -> dict | None:
    receipt = state.get("current_decision")
    if not isinstance(receipt, dict):
        return None
    candidates = sorted(
        (copy.deepcopy(row) for row in (receipt.get("candidate_goals") or [])),
        key=lambda row: (-int(row.get("score_total", 0)), str(row.get("goal_id", ""))),
    )[:MAX_CANDIDATES]
    return {
        "receipt_id": receipt.get("receipt_id"),
        "tick": receipt.get("tick"),
        "decision_kind": receipt.get("decision_kind"),
        "selected_goal": receipt.get("selected_goal"),
        "selected_goal_id": receipt.get("selected_goal_id"),
        "selected_score": receipt.get("selected_score"),
        "selection_reason": receipt.get("selection_reason"),
        "uncertainty": receipt.get("uncertainty"),
        "knowledge_used": list(receipt.get("knowledge_used") or []),
        "memory_references": list(receipt.get("memory_references") or []),
        "want_references": list(receipt.get("want_references") or []),
        "relationship_references": list(receipt.get("relationship_references") or []),
        "assumptions": list(receipt.get("assumptions") or []),
        "predicted_risks": copy.deepcopy(receipt.get("predicted_risks") or {}),
        "candidates": candidates,
        "candidate_count": len(receipt.get("candidate_goals") or []),
    }


def _diagnostics(diagnostics: dict | None) -> dict:
    raw = diagnostics or {}
    return {
        "selected_goal": raw.get("selected_goal"),
        "goal_id": raw.get("goal_id"),
        "plan_id": raw.get("plan_id"),
        "decision_kind": raw.get("decision_kind"),
        "explanation": raw.get("explanation"),
        "perception": copy.deepcopy(raw.get("perception") or {}),
        "candidates": copy.deepcopy((raw.get("candidates") or [])[:MAX_CANDIDATES]),
        "social_consequences": copy.deepcopy((raw.get("social_consequences") or [])[:8]),
        "commitment_consequences": copy.deepcopy((raw.get("commitment_consequences") or [])[:8]),
        "new_memories": copy.deepcopy((raw.get("new_memories") or [])[:8]),
    }


def build_living_agent_projection(entity: dict, tick: int, diagnostics: dict | None = None) -> dict:
    if entity.get("type") != "person":
        raise ValueError("living-agent projection requires a person")
    entity_id = entity.get("id")
    state = compat_living_agent_state(entity.get("living_agent"), entity_id, tick)
    beliefs, knowledge_summary = _beliefs(entity, tick)
    memories = _recent(
        list((state.get("memories") or {}).values()),
        tick_key="last_recalled_tick", limit=MAX_MEMORIES,
    )
    relationships = _recent(
        list((state.get("relationships") or {}).values()),
        tick_key="last_changed_tick", limit=MAX_RELATIONSHIPS,
    )
    commitments = _recent(
        list((state.get("commitments") or {}).values()),
        tick_key="last_changed_tick", limit=MAX_COMMITMENTS,
    )
    links = _recent(
        list(state.get("causal_links") or []), tick_key="tick", limit=MAX_CAUSAL_LINKS,
    )
    return {
        "projection_version": LIVING_AGENT_PROJECTION_VERSION,
        "entity_id": entity_id,
        "world_tick": int(tick),
        "role": entity.get("stage6_role"),
        "needs": _needs(state),
        "wants": _wants(state),
        "knowledge": {"summary": knowledge_summary, "beliefs": beliefs},
        "trying": _trying(entity, state),
        "why": _why(state),
        "consequences": {
            "memories": memories,
            "commitments": commitments,
            "causal_links": links,
        },
        "relationships": relationships,
        "diagnostics": _diagnostics(diagnostics),
        "schema_versions": {
            "living_agent": state.get("schema_version"),
            "knowledge": (entity.get("knowledge") or {}).get("schema_version"),
            "action": (entity.get("action") or {}).get("schema_version"),
            "plan": (entity.get("plan") or {}).get("schema_version"),
        },
        "limits": {
            "needs": MAX_NEEDS,
            "wants": MAX_WANTS,
            "beliefs": MAX_BELIEFS,
            "memories": MAX_MEMORIES,
            "relationships": MAX_RELATIONSHIPS,
            "commitments": MAX_COMMITMENTS,
            "causal_links": MAX_CAUSAL_LINKS,
            "candidates": MAX_CANDIDATES,
        },
        "truth_boundary": (
            "Beliefs are actor-owned records. Reported, contradicted, or stale entries may be wrong; "
            "this projection does not compare them with hidden world truth."
        ),
    }
