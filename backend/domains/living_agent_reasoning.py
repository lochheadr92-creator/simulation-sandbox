"""Capability Stage 6B deterministic goal reasoning and bounded planning.

No free-form reasoning is stored.  Every selected goal is backed by integer
score components, declared evidence references, and a stable tie-break rule.
"""
from __future__ import annotations

import copy

from core.hashing import canonical_hash
from domains.living_agent_contracts import (
    DECISION_RECEIPT_VERSION,
    LIMITS,
    compat_plan,
)


GOAL_PRESSURES = {
    "SEEK_WATER": ("thirst", "safety"),
    "SEEK_FOOD": ("hunger", "safety"),
    "SLEEP": ("fatigue", "comfort", "exposure"),
    "BUILD_SHELTER": ("exposure", "comfort", "safety"),
    "GATHER_SURPLUS": ("safety",),
    "HUNT": ("hunger", "curiosity"),
    "GIVE_FOOD": ("belonging", "attachment", "perceived_obligation"),
    "EXPLORE": ("curiosity",),
    "WANDER": ("curiosity", "comfort"),
    "STORE_SURPLUS": ("safety", "hunger"),
    "REPAIR_SHELTER": ("comfort", "exposure", "safety"),
    "HELP_PERSON": ("attachment", "belonging", "perceived_obligation"),
    "WARN_PERSON": ("attachment", "perceived_obligation"),
    "VERIFY_INFORMATION": ("curiosity", "fear"),
    "REQUEST_HELP": ("hunger", "thirst", "safety"),
    "RESPOND_HELP": ("belonging", "attachment", "perceived_obligation"),
    "PROMISE_HELP": ("attachment", "perceived_obligation"),
    "REPAY_DEBT": ("perceived_obligation", "belonging"),
    "WARN_DANGER": ("fear", "attachment", "perceived_obligation"),
    "SHARE_RUMOUR": ("curiosity", "belonging"),
    "APOLOGISE": ("belonging", "perceived_obligation"),
    "RECONCILE": ("belonging", "attachment"),
    "THREATEN": ("fear", "safety"),
    "TAKE_FOOD": ("hunger", "safety"),
    "RETRIEVE_FOOD": ("hunger",),
    "GATHER_FOOD": ("hunger",),
    "TEND_STRUCTURE": ("upkeep",),  # Layer C Variety Leg 1: memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md
}

WANT_GOALS = {
    "improve_shelter": ("BUILD_SHELTER", "REPAIR_SHELTER"),
    "store_surplus_food": ("STORE_SURPLUS", "GATHER_SURPLUS"),
    "explore_unknown_area": ("EXPLORE",),
    "gain_safety": ("BUILD_SHELTER", "SLEEP"),
    "stay_near_family": ("HELP_PERSON", "WARN_PERSON"),
    "avoid_person": ("SEEK_WATER", "SEEK_FOOD", "SLEEP"),
    "repay_obligation": ("GIVE_FOOD", "HELP_PERSON"),
}

SURVIVAL_GOALS = frozenset({"SEEK_WATER", "SEEK_FOOD", "SLEEP", "BUILD_SHELTER"})
SOCIAL_GOALS = frozenset({"GIVE_FOOD", "HELP_PERSON", "WARN_PERSON"})


def _integer(value, scale=10) -> int:
    try:
        return int(round(float(value) * scale))
    except (TypeError, ValueError):
        return 0


def _confidence_for_candidate(candidate: dict, knowledge: dict) -> tuple[int, list[str]]:
    subjects = {
        candidate.get("recipient_id"),
        candidate.get("target_entity_id"),
        candidate.get("target_id"),
    } - {None}
    target_pos = candidate.get("target_pos")
    refs = []
    values = []
    for fact_id, fact in sorted((knowledge.get("facts") or {}).items()):
        matches_subject = fact.get("subject") in subjects
        location = fact.get("location") or (fact.get("properties") or {}).get("position")
        matches_position = bool(
            target_pos and location
            and location.get("x") == target_pos.get("x")
            and location.get("y") == target_pos.get("y")
        )
        if not (matches_subject or matches_position):
            continue
        refs.append(fact_id)
        values.append(int(fact.get("confidence", 500)))
        if len(refs) >= 6:
            break
    if not values:
        # Local/default actions have moderate certainty; unavailable targets
        # remain explicitly uncertain through their availability component.
        return (650 if candidate.get("availability", 0) > 0 else 250), []
    return sum(values) // len(values), refs


def _memory_evidence(goal: str, state: dict, tick: int) -> tuple[int, list[str]]:
    score = 0
    refs = []
    for memory_id, memory in sorted((state.get("memories") or {}).items()):
        kind = memory.get("memory_kind")
        age = max(0, int(tick) - int(memory.get("last_recalled_tick", 0)))
        recency = max(0, 100 - age * 3)
        influence = int(memory.get("significance", 0)) * recency // 100
        applies = False
        if goal in ("SEEK_WATER", "SEEK_FOOD", "GATHER_SURPLUS") and kind == "resource_discovered":
            score += influence // 8
            applies = True
        elif goal in ("SLEEP", "BUILD_SHELTER") and kind == "threat_observed":
            score += influence // 6
            applies = True
        elif goal in ("EXPLORE", "HUNT") and kind == "failed_action":
            score -= influence // 7
            applies = True
        elif goal == "GIVE_FOOD" and kind in ("social_information", "successful_action"):
            score += influence // 10
            applies = True
        elif kind == "interruption":
            score -= influence // 12
            applies = True
        if applies:
            refs.append(memory_id)
        if len(refs) >= 6:
            break
    return score, refs


def _want_evidence(goal: str, state: dict) -> tuple[int, list[str]]:
    score = 0
    refs = []
    for want_id, want in sorted((state.get("wants") or {}).items()):
        if want.get("status") != "active":
            continue
        if goal not in WANT_GOALS.get(want.get("want_type"), ()):
            continue
        score += int(want.get("strength", 0)) // 3
        refs.append(want_id)
    return score, refs[:6]


def _relationship_evidence(goal: str, candidate: dict, state: dict) -> tuple[int, list[str]]:
    if goal not in SOCIAL_GOALS:
        return 0, []
    subject_id = candidate.get("recipient_id") or candidate.get("target_entity_id")
    relation = (state.get("relationships") or {}).get(subject_id)
    if not relation:
        return 0, []
    score = (
        int(relation.get("trust", 0))
        + int(relation.get("affection", 0))
        + int(relation.get("obligation", 0))
        - int(relation.get("fear", 0))
        - int(relation.get("resentment", 0))
    ) // 5
    return score, [subject_id]


def score_goal_candidates(
    base_candidates: list[dict],
    *,
    actor_id: str,
    state: dict,
    knowledge: dict,
    tick: int,
) -> list[dict]:
    """Return order-independent, componentized integer goal candidates."""
    scored = []
    pressures = state.get("pressures") or {}
    for candidate in sorted(
        (copy.deepcopy(row) for row in base_candidates),
        key=lambda row: (str(row.get("goal")), canonical_hash(row)),
    ):
        goal = str(candidate.get("goal"))
        pressure_kinds = GOAL_PRESSURES.get(goal, ())
        pressure_value = sum(
            int((pressures.get(kind) or {}).get("urgency", 0))
            for kind in pressure_kinds
        ) // max(1, len(pressure_kinds))
        want_value, want_refs = _want_evidence(goal, state)
        memory_value, memory_refs = _memory_evidence(goal, state, tick)
        relationship_value, relationship_refs = _relationship_evidence(goal, candidate, state)
        confidence, knowledge_refs = _confidence_for_candidate(candidate, knowledge)
        availability = _integer(candidate.get("availability", 0), 100)
        travel_cost = _integer(candidate.get("travel_cost", 0), 10)
        duration_cost = _integer(candidate.get("action_time", 0), 10)
        physical_risk = _integer(candidate.get("risk", 0), 10)
        social_risk = max(0, -relationship_value)
        interruption_cost = _integer(candidate.get("interruption_cost", 0), 10)
        uncertainty_penalty = max(0, 1000 - confidence) // 4
        survival_value = pressure_value // 2 if goal in SURVIVAL_GOALS else 0
        social_value = max(0, relationship_value) if goal in SOCIAL_GOALS else 0
        preference_value = sum(
            int((pressures.get(kind) or {}).get("individual_weight", 100)) - 100
            for kind in pressure_kinds
        )
        obligation_value = int((pressures.get("perceived_obligation") or {}).get("urgency", 0)) \
            if goal in SOCIAL_GOALS else 0
        base_utility = _integer(candidate.get("score", 0), 10)
        components = {
            "base_utility": base_utility,
            "pressure": pressure_value,
            "predicted_danger": max(
                [int((pressures.get(kind) or {}).get("predicted_severity", 0)) for kind in pressure_kinds]
                or [0]
            ) // 4,
            "survival_value": survival_value,
            "social_value": social_value,
            "personal_preference": preference_value,
            "want": want_value,
            "memory": memory_value,
            "relationship": relationship_value,
            "obligation": obligation_value,
            "availability": availability,
            "knowledge_confidence": confidence // 5,
            "travel_cost": -travel_cost,
            "resource_cost": -_integer(candidate.get("resource_cost", 0), 10),
            "duration_cost": -duration_cost,
            "physical_risk": -physical_risk,
            "social_risk": -social_risk,
            "interruption_cost": -interruption_cost,
            "opportunity_cost": -max(0, interruption_cost // 2),
            "uncertainty": -uncertainty_penalty,
            "group_value": 0,
            "cultural_weight": 0,
            "downstream_consequence": int(candidate.get("downstream_value", 0)),
        }
        total = sum(components.values())
        goal_id = "goal-" + canonical_hash([
            actor_id, tick, goal, candidate.get("target_pos"),
            candidate.get("recipient_id"), candidate.get("target_entity_id"),
        ])[:16]
        candidate.update({
            "goal_id": goal_id,
            "score": total,
            "score_total": total,
            "score_components": components,
            "pressure_kinds": list(pressure_kinds),
            "want_refs": want_refs,
            "memory_refs": memory_refs,
            "relationship_refs": relationship_refs,
            "knowledge_refs": knowledge_refs,
            "knowledge_confidence": confidence,
            "assumptions": [
                "target remains available until arrival" if candidate.get("target_pos") else "no remote target assumed",
            ],
            "predicted_risks": {
                "physical": physical_risk,
                "social": social_risk,
                "uncertainty": uncertainty_penalty,
            },
            "success_likelihood": max(0, min(1000, confidence + availability - physical_risk)),
        })
        scored.append(candidate)

    return sorted(scored, key=lambda row: row["goal_id"])[:LIMITS.candidate_goals_per_decision]


def candidate_rank(candidate: dict) -> tuple:
    """Stable winner order independent of input list/map order."""
    return (
        -int(candidate.get("score_total", candidate.get("score", 0))),
        -int(candidate.get("knowledge_confidence", 0)),
        str(candidate.get("goal_id") or candidate.get("goal")),
    )


def select_goal(candidates: list[dict]) -> dict:
    if not candidates:
        raise ValueError("at least one candidate goal is required")
    return copy.deepcopy(sorted(candidates, key=candidate_rank)[0])


def build_decision_receipt(
    *,
    actor_id: str,
    tick: int,
    state: dict,
    knowledge: dict,
    candidates: list[dict],
    selected: dict,
    plan: dict,
    decision_kind: str,
) -> dict:
    ordered = sorted((copy.deepcopy(row) for row in candidates), key=candidate_rank)
    selected_id = selected.get("goal_id")
    receipt_basis = {
        "actor_id": actor_id,
        "tick": int(tick),
        "selected_goal_id": selected_id,
        "candidate_ids": [row.get("goal_id") for row in ordered],
        "candidate_scores": [row.get("score_total") for row in ordered],
        "plan_id": plan.get("plan_id"),
        "decision_kind": decision_kind,
    }
    receipt_id = "decision-" + canonical_hash(receipt_basis)[:16]
    active_wants = [
        copy.deepcopy(want) for want in (state.get("wants") or {}).values()
        if want.get("status") == "active"
    ]
    pressure_rows = [
        {
            "kind": kind,
            "severity": pressure.get("severity"),
            "predicted_severity": pressure.get("predicted_severity"),
            "urgency": pressure.get("urgency"),
            "source": pressure.get("source"),
        }
        for kind, pressure in sorted((state.get("pressures") or {}).items())
    ]
    return {
        "schema_version": DECISION_RECEIPT_VERSION,
        "receipt_id": receipt_id,
        "actor_id": actor_id,
        "tick": int(tick),
        "decision_kind": decision_kind,
        "current_pressures": pressure_rows,
        "active_wants": active_wants[:LIMITS.candidate_goals_per_decision],
        "candidate_goals": ordered,
        "rejected_alternatives": [
            {
                "goal_id": row.get("goal_id"),
                "goal": row.get("goal"),
                "score_total": row.get("score_total"),
                "lost_by": int(selected.get("score_total", 0)) - int(row.get("score_total", 0)),
            }
            for row in ordered if row.get("goal_id") != selected_id
        ],
        "knowledge_used": list(selected.get("knowledge_refs") or []),
        "memory_references": list(selected.get("memory_refs") or []),
        "want_references": list(selected.get("want_refs") or []),
        "relationship_references": list(selected.get("relationship_refs") or []),
        "assumptions": list(selected.get("assumptions") or []),
        "uncertainty": max(0, 1000 - int(selected.get("knowledge_confidence", 0))),
        "predicted_risks": copy.deepcopy(selected.get("predicted_risks") or {}),
        "selected_goal_id": selected_id,
        "selected_goal": selected.get("goal"),
        "selected_score": selected.get("score_total"),
        "plan_id": plan.get("plan_id"),
        "tie_break": {
            "rule": "score_desc_then_knowledge_confidence_desc_then_goal_id_asc",
            "rank_key": list(candidate_rank(selected)),
        },
        "selection_reason": "highest deterministic component score under the documented tie-break",
        "accepted_event_id": None,
        "knowledge_fingerprint": canonical_hash(knowledge or {}),
    }


def record_decision(state: dict, receipt: dict, plan: dict) -> dict:
    # CORE-PERF-01 Slice A: shallow copy -- decision_history/causal_links are
    # append-only list rebuilds below (existing entries never mutated in
    # place); the receipt itself keeps its own defensive deepcopy.
    out = dict(state)
    prior = list(out.get("decision_history") or [])
    prior = [row for row in prior if row.get("receipt_id") != receipt.get("receipt_id")]
    # Canonical history is deliberately compact.  The current receipt retains
    # full candidate scoring for inspection; keeping twelve complete candidate
    # matrices per person made every later state hash increasingly expensive.
    prior.append({
        "schema_version": receipt.get("schema_version"),
        "receipt_id": receipt.get("receipt_id"),
        "actor_id": receipt.get("actor_id"),
        "tick": receipt.get("tick"),
        "decision_kind": receipt.get("decision_kind"),
        "selected_goal_id": receipt.get("selected_goal_id"),
        "selected_goal": receipt.get("selected_goal"),
        "selected_score": receipt.get("selected_score"),
        "plan_id": receipt.get("plan_id"),
        "knowledge_used": list(receipt.get("knowledge_used") or []),
        "memory_references": list(receipt.get("memory_references") or []),
        "want_references": list(receipt.get("want_references") or []),
        "relationship_references": list(receipt.get("relationship_references") or []),
        "uncertainty": receipt.get("uncertainty"),
        "accepted_event_id": receipt.get("accepted_event_id"),
    })
    out["current_decision"] = copy.deepcopy(receipt)
    out["decision_history"] = prior[-LIMITS.decision_receipts_retained:]
    link = {
        "link_type": "decision",
        "tick": receipt.get("tick"),
        "pressure_kinds": list((receipt.get("candidate_goals") or [{}])[0].get("pressure_kinds") or []),
        "want_ids": list(receipt.get("want_references") or []),
        "memory_ids": list(receipt.get("memory_references") or []),
        "selected_goal_id": receipt.get("selected_goal_id"),
        "plan_id": plan.get("plan_id"),
        "accepted_event_id": None,
    }
    links = list(out.get("causal_links") or [])
    links.append(link)
    out["causal_links"] = links[-LIMITS.causal_links_retained:]
    return out


def form_structured_plan(
    legacy_plan: dict,
    *,
    actor_id: str,
    tick: int,
    selected: dict,
    context: dict,
    replan_of: str | None = None,
) -> dict:
    plan = compat_plan(legacy_plan, actor_id=actor_id, tick=tick)
    plan["goal_id"] = selected.get("goal_id")
    plan["replan_of"] = replan_of
    target_id = selected.get("recipient_id") or selected.get("target_entity_id")
    target_pos = selected.get("target_pos")
    for record in plan.get("step_records") or []:
        step = record.get("step_type", "")
        record["target_entity_ids"] = [target_id] if target_id else []
        record["target_location"] = copy.deepcopy(target_pos)
        record["expected_duration"] = int(selected.get("action_time", 1) or 1)
        record["failure_conditions"] = ["target_unavailable", "prerequisite_missing"]
        record["fallback_step"] = "REPLAN" if step != "WANDER_STEP" else None
        if "GATHER" in step or "HUNT" in step or "BUILD" in step:
            record["required_tools"] = list(context.get("required_tools") or [])
        if "BUILD" in step:
            record["required_resources"] = {"wood": 10}
    return plan


def update_plan_progress(plan: dict, action: dict, *, tick: int) -> dict:
    out = copy.deepcopy(plan)
    records = out.get("step_records") or []
    index = int(out.get("step_index", 0))
    if 0 <= index < len(records):
        status = action.get("status")
        records[index]["status"] = {
            "completed": "completed",
            "failed": "failed",
            "paused": "paused",
            "cancelled": "cancelled",
        }.get(status, "active")
        records[index]["last_updated_tick"] = int(tick)
        if status == "failed":
            out["failure_reason"] = action.get("invalidation_reason") or "action_failed"
    out["step_records"] = records
    return out
