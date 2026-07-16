"""Integrated Capability Stage 6 living-agent domain.

This domain is enabled only by the Living Agents Camp scenario.  Candidate
generation reads the actor's pressure state, owned knowledge, commitments, and
this tick's bounded observations.  Canonical execution reuses the generic
Stage 6 physical/social proposal builders and Core validation path.
"""
from __future__ import annotations

import copy

from core.navigation import ARRIVAL_ADJACENT, find_path
from domains.base import DomainEngine, DomainOutput
from domains.living_agent_actions import build_physical_action_proposal
from domains.living_agent_cognition import (
    derive_internal_pressures,
    merge_meaningful_memories,
    merge_observations_into_knowledge,
    perceive_living,
    refresh_wants,
)
from domains.living_agent_contracts import LIMITS, compat_living_agent_state, compat_plan
from domains.living_agent_reasoning import (
    build_decision_receipt,
    form_structured_plan,
    record_decision,
    score_goal_candidates,
    select_goal,
)
from domains.living_agent_social import (
    advance_commitment_deadlines,
    apply_observed_social_information,
    build_social_action_proposal,
)
from domains.perception import _compat_knowledge, empty_knowledge, merge_knowledge
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_goal_contracts import (
    GROUP_GOAL_REGISTRY_ID,
    GROUP_GOAL_REGISTRY_VERSION,
    GOAL_TYPE as GROUP_GOAL_TYPE,
    _holds_improve_shelter_want,
    _recognised_groups,
)


SOCIAL_DIRECT_ACTIONS = frozenset({
    "request_help", "offer_help", "cooperate", "refuse", "warn",
    "share_information", "conceal_information", "lie", "give", "trade",
    "threaten", "apologise", "promise", "repay", "confront", "compete",
    "reconcile",
})
SURVIVAL_GOALS = frozenset({"DRINK_WATER", "EAT_CARRIED", "RETRIEVE_FOOD", "GATHER_FOOD", "REQUEST_HELP", "REST"})


def _observation_map(delta: dict, observation_type: str) -> dict:
    return {
        item["observed_subject_id"]: item
        for item in delta.get("observations") or []
        if item.get("observation_type") == observation_type
    }


def _pos(observation: dict | None):
    if not observation:
        return None
    properties = observation.get("properties") or {}
    return copy.deepcopy(properties.get("position"))


def _action_count(entity: dict, action_type: str) -> int:
    return int((entity.get("living_action_counts") or {}).get(action_type, 0))


def _known_false_storage_claim(knowledge: dict, storage_id: str) -> bool:
    for fact in (knowledge.get("facts") or {}).values():
        if fact.get("subject") != storage_id or fact.get("fact_type") != "storage":
            continue
        props = fact.get("properties") or {}
        if props.get("access") == "public" and (props.get("visible_contents") or {}).get("food", 0) > 0:
            return True
    return False


def _candidate(goal, action_type, score, *, target_id=None, target_pos=None, **extra):
    return {
        "goal": goal,
        "direct_action_type": action_type,
        "score": int(score),
        "availability": 1,
        "risk": int(extra.pop("risk", 0)),
        "travel_cost": int(extra.pop("travel_cost", 0)),
        "target_entity_id": target_id,
        "target_pos": copy.deepcopy(target_pos),
        **extra,
    }


GROUP_GOAL_REPAIR_INCREMENT = 250  # bounded, member-grounded Stage 7D upkeep nudge


def _apply_group_goal_influence(candidates, entity_id, entities, tick):
    """Stage 7D read-only influence: raise REPAIR_SHELTER priority for a member
    who CURRENTLY supports an active, unexpired shared-shelter upkeep goal.

    Inert when no valid group-goal registry exists (e.g. the living_settlement
    scenario), preserving the frozen Stage 6 determinism hash.  Guards
    (member grounding, current membership, schema, TTL) ensure the nudge only
    reaches a member who still holds an active improve_shelter want and is still
    in the recognised group; it never creates a goal a member lacks, never
    survives goal expiry, and never overrides an urgent survival candidate."""
    registry = entities.get(GROUP_GOAL_REGISTRY_ID)
    if not isinstance(registry, dict) or registry.get("schema_version") != GROUP_GOAL_REGISTRY_VERSION:
        return candidates
    # Member grounding: only a member who currently holds an active
    # improve_shelter want is influenced (a stale/dormant supporter is not).
    if not _holds_improve_shelter_want(entities.get(entity_id)):
        return candidates
    association = entities.get(ASSOCIATION_REGISTRY_ID)
    recognised = _recognised_groups(association) if isinstance(association, dict) else {}
    targets = set()
    for goal in (registry.get("goals") or {}).values():
        if goal.get("status") != "active" or goal.get("goal_type") != GROUP_GOAL_TYPE:
            continue
        if int(tick) >= int(goal.get("ttl_tick", tick)):
            continue  # unexpired goals only
        if entity_id not in (goal.get("supporter_ids") or []):
            continue
        group = recognised.get(goal.get("group_id")) or {}
        if entity_id not in (group.get("member_ids") or []):
            continue  # current recognised-group membership only
        if goal.get("target_id"):
            targets.add(goal["target_id"])
    if not targets:
        return candidates
    # Survival dominance: the nudge is a strictly lower tier than survival.
    # Never lift a repair candidate to/above an urgent survival candidate (one
    # whose base score already meets or exceeds this repair candidate's base).
    survival_scores = [
        int(c.get("score", 0)) for c in candidates if c.get("goal") in SURVIVAL_GOALS
    ]
    for cand in candidates:
        if cand.get("goal") == "REPAIR_SHELTER" and cand.get("target_entity_id") in targets:
            base = int(cand.get("score", 0))
            if any(s >= base for s in survival_scores):
                continue  # urgent survival present; suppress the group nudge
            cand["score"] = base + GROUP_GOAL_REPAIR_INCREMENT
    return candidates


def build_settlement_candidates(entity_id: str, entity: dict, state: dict, knowledge: dict,
                                delta: dict, tick: int) -> list[dict]:
    """Generate candidates from observer-owned inputs only."""
    candidates = []
    role = entity.get("stage6_role", "resident")
    resources = entity.get("carried_resources") or {}
    pressures = state.get("pressures") or {}
    people = _observation_map(delta, "person")
    storages = _observation_map(delta, "storage")
    tools = _observation_map(delta, "tool")
    shelters = _observation_map(delta, "shelter")
    water_sources = _observation_map(delta, "water_source")
    resource_nodes = _observation_map(delta, "resource")
    animals = _observation_map(delta, "animal")
    visible_person_ids = sorted(people)

    prior_plan = entity.get("plan") or {}
    paused_plan = entity.get("paused_living_plan")
    max_survival = max(
        int((pressures.get("thirst") or {}).get("severity", 0)),
        int((pressures.get("hunger") or {}).get("severity", 0)),
    )
    if prior_plan.get("status") == "active" and isinstance(prior_plan.get("intent"), dict):
        intent = prior_plan["intent"]
        if max_survival < 850 or intent.get("goal") in SURVIVAL_GOALS:
            candidates.append(_candidate(
                intent["goal"], intent["action_type"], 2300,
                target_id=intent.get("target_id"), target_pos=intent.get("target_pos"),
                message=copy.deepcopy(intent.get("message")), tool_id=intent.get("tool_id"),
                resource_kind=intent.get("resource_kind", "food"),
                allow_unauthorized=bool(intent.get("allow_unauthorized")),
                continuation=True,
            ))
    elif paused_plan and max_survival < 650 and isinstance(paused_plan.get("intent"), dict):
        intent = paused_plan["intent"]
        candidates.append(_candidate(
            intent["goal"], intent["action_type"], 2250,
            target_id=intent.get("target_id"), target_pos=intent.get("target_pos"),
            message=copy.deepcopy(intent.get("message")), tool_id=intent.get("tool_id"),
            resource_kind=intent.get("resource_kind", "food"),
            allow_unauthorized=bool(intent.get("allow_unauthorized")),
            resumption=True,
        ))

    thirst = int((pressures.get("thirst") or {}).get("severity", 0))
    hunger = int((pressures.get("hunger") or {}).get("severity", 0))
    fatigue = int((pressures.get("fatigue") or {}).get("severity", 0))
    if thirst >= 600 and water_sources:
        target_id = sorted(water_sources)[0]
        candidates.append(_candidate(
            "DRINK_WATER", "drink", 1800 + thirst,
            target_id=target_id, target_pos=_pos(water_sources[target_id]),
        ))
    if hunger >= 600:
        if resources.get("food", 0) > 0:
            candidates.append(_candidate("EAT_CARRIED", "consume", 1850 + hunger, resource_kind="food"))
        shared_food = [
            (storage_id, obs) for storage_id, obs in sorted(storages.items())
            if (obs.get("properties") or {}).get("access") in ("public", "shared")
            and ((obs.get("properties") or {}).get("visible_contents") or {}).get("food", 0) > 0
        ]
        if shared_food:
            target_id, obs = shared_food[0]
            candidates.append(_candidate(
                "RETRIEVE_FOOD", "retrieve", 1700 + hunger,
                target_id=target_id, target_pos=_pos(obs), resource_kind="food",
            ))
        food_nodes = [
            (resource_id, obs) for resource_id, obs in sorted(resource_nodes.items())
            if (obs.get("properties") or {}).get("resource_kind") == "food"
            and (obs.get("properties") or {}).get("quantity_band", 0) > 0
        ]
        if food_nodes:
            target_id, obs = food_nodes[0]
            candidates.append(_candidate(
                "GATHER_FOOD", "gather", 1500 + hunger,
                target_id=target_id, target_pos=_pos(obs), resource_kind="food",
            ))
        if visible_person_ids:
            target_id = visible_person_ids[0]
            candidates.append(_candidate(
                "REQUEST_HELP", "request_help", 1200 + hunger,
                target_id=target_id, target_pos=_pos(people[target_id]),
                obligation="help obtain food", due_tick=tick + 8,
            ))
    if fatigue >= 650:
        candidates.append(_candidate("REST", "rest", 1200 + fatigue))

    # Respond to causally received requests before discretionary social acts.
    for commitment in sorted((state.get("commitments") or {}).values(), key=lambda item: item["commitment_id"]):
        counterparty = commitment.get("creator_id")
        if (commitment.get("commitment_kind") == "request_help"
                and commitment.get("beneficiary_id") == entity_id
                and commitment.get("status") == "pending"
                and counterparty in people):
            action_type = "refuse" if role == "skeptic" else "cooperate"
            candidates.append(_candidate(
                "RESPOND_HELP", action_type, 3100,
                target_id=counterparty, target_pos=_pos(people[counterparty]),
            ))
        if (commitment.get("commitment_kind") == "debt"
                and commitment.get("creator_id") == entity_id
                and commitment.get("status") in ("active", "broken")
                and commitment.get("beneficiary_id") in people
                and tick - int(commitment.get("created_tick", tick)) >= 1):
            beneficiary = commitment["beneficiary_id"]
            candidates.append(_candidate(
                "REPAY_DEBT", "repay", 2700,
                target_id=beneficiary, target_pos=_pos(people[beneficiary]),
            ))

    injured_people = [
        (person_id, obs) for person_id, obs in sorted(people.items())
        if (obs.get("properties") or {}).get("appears_injured")
        or (obs.get("properties") or {}).get("apparent_urgent_need") == "critical"
    ]
    if role == "caretaker" and injured_people:
        target_id, obs = injured_people[0]
        if _action_count(entity, "cooperate") < 1:
            candidates.append(_candidate(
                "HELP_PERSON", "cooperate", 2600,
                target_id=target_id, target_pos=_pos(obs),
            ))
        elif _action_count(entity, "promise") < 1:
            candidates.append(_candidate(
                "PROMISE_HELP", "promise", 2100,
                target_id=target_id, target_pos=_pos(obs),
                obligation="bring food and repair shelter", due_tick=tick + 12,
            ))

    if role == "builder":
        damaged = [
            (shelter_id, obs) for shelter_id, obs in sorted(shelters.items())
            if int((obs.get("properties") or {}).get("condition", 1000)) < 750
        ]
        hammer = next((tool_id for tool_id, obs in sorted(tools.items())
                       if (obs.get("properties") or {}).get("tool_kind") == "hammer"), None)
        if damaged and resources.get("wood", 0) > 0 and hammer:
            target_id, obs = damaged[0]
            candidates.append(_candidate(
                "REPAIR_SHELTER", "repair", 2400,
                target_id=target_id, target_pos=_pos(obs), tool_id=hammer,
                resource_kind="wood",
            ))

    shared_storage = next((
        (storage_id, obs) for storage_id, obs in sorted(storages.items())
        if (obs.get("properties") or {}).get("access") in ("public", "shared")
    ), None)
    if shared_storage and resources.get("food", 0) >= 3:
        target_id, obs = shared_storage
        candidates.append(_candidate(
            "STORE_SURPLUS", "store", 1350,
            target_id=target_id, target_pos=_pos(obs), resource_kind="food",
        ))

    if role == "scout" and animals and visible_person_ids and _action_count(entity, "warn") < 2:
        target_id = visible_person_ids[0]
        animal_id = sorted(animals)[0]
        candidates.append(_candidate(
            "WARN_DANGER", "warn", 2300,
            target_id=target_id, target_pos=_pos(people[target_id]),
            message={"claim": {"subject_id": animal_id, "fact_type": "danger",
                                "properties": {"kind": "animal_threat", "position": _pos(animals[animal_id])},
                                "confidence": 900}},
        ))

    if role == "rumourmonger" and visible_person_ids:
        target_id = "person-004" if "person-004" in people else visible_person_ids[0]
        if _action_count(entity, "lie") < 1 and tick >= 5:
            candidates.append(_candidate(
                "SHARE_RUMOUR", "lie", 2050,
                target_id=target_id, target_pos=_pos(people[target_id]),
                message={"claim": {"subject_id": "water-camp", "fact_type": "water_safety",
                                    "properties": {"safe": False}, "confidence": 650}},
            ))
        # The speaker knows their own prior lie even though listeners do not
        # receive the hidden truth marker.  A delayed apology therefore uses
        # actor-owned action history, not omniscient access to others' views.
        if _action_count(entity, "lie") > 0 and tick >= 12 and _action_count(entity, "apologise") < 1:
            candidates.append(_candidate(
                "APOLOGISE", "apologise", 2250,
                target_id=target_id, target_pos=_pos(people[target_id]),
            ))
        elif _action_count(entity, "apologise") > 0 and _action_count(entity, "reconcile") < 1:
            candidates.append(_candidate(
                "RECONCILE", "reconcile", 1900,
                target_id=target_id, target_pos=_pos(people[target_id]),
            ))

    if role == "steward" and visible_person_ids and "storage-private" in storages and _action_count(entity, "share_information") < 1:
        target_id = visible_person_ids[0]
        candidates.append(_candidate(
            "VERIFY_INFORMATION", "share_information", 2000,
            target_id=target_id, target_pos=_pos(people[target_id]),
            message={"claim": {"subject_id": "storage-private", "fact_type": "storage",
                                "properties": copy.deepcopy(storages["storage-private"].get("properties") or {}),
                                "confidence": 950}},
        ))
    if role == "steward" and visible_person_ids and _action_count(entity, "trade") < 1 \
            and resources.get("food", 0) > 0:
        relationship_targets = sorted(
            subject_id
            for subject_id, relation in (state.get("relationships") or {}).items()
            if subject_id in people and relation.get("kinship")
        )
        target_id = relationship_targets[0] if relationship_targets else visible_person_ids[0]
        if target_id:
            candidates.append(_candidate(
                "TRADE_RESOURCES", "trade", 1450,
                target_id=target_id, target_pos=_pos(people[target_id]),
                message={"trade": {"offer_kind": "food", "request_kind": "wood", "quantity": 1}},
            ))

    if role == "hoarder" and visible_person_ids and _action_count(entity, "threaten") < 1 and tick >= 8:
        target_id = visible_person_ids[0]
        candidates.append(_candidate(
            "THREATEN", "threaten", 1750,
            target_id=target_id, target_pos=_pos(people[target_id]), risk=40,
        ))

    prior_false_store_failure = int(
        (entity.get("living_failed_goal_counts") or {}).get("TAKE_FOOD", 0)
    ) > 0
    if role in ("needy", "skeptic") and hunger >= 780 and "storage-private" in storages \
            and _known_false_storage_claim(knowledge, "storage-private") \
            and not prior_false_store_failure:
        candidates.append(_candidate(
            # The actor believes the reported "public/open" claim and plans a
            # normal retrieval. Canonical execution sees private access and
            # fails safely, producing an explicit replan receipt.
            "TAKE_FOOD", "retrieve", 2800,
            target_id="storage-private", target_pos=_pos(storages["storage-private"]),
            resource_kind="food", risk=120,
        ))

    # Deterministic bounded local exploration/fallback.
    unknown = []
    known_tiles = set(knowledge.get("known_tiles") or [])
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        pos = {"x": entity["position"]["x"] + dx, "y": entity["position"]["y"] + dy}
        if f"{pos['x']},{pos['y']}" not in known_tiles:
            unknown.append(pos)
    if unknown:
        candidates.append(_candidate("EXPLORE", "move", 180, target_pos=unknown[0]))
    candidates.append(_candidate("REST", "rest", 60))
    return candidates[:LIMITS.candidate_goals_per_decision]


def _replace_living_preconditions(proposal: dict, canonical_entities: dict) -> None:
    for condition in proposal.get("preconditions") or []:
        if condition.get("field") == "living_agent" and condition.get("entity_id") in canonical_entities:
            condition["value"] = canonical_entities[condition["entity_id"]].get("living_agent")


class LivingSettlementDomain(DomainEngine):
    engine_id = "living_settlement"
    engine_version = "1.0.0"
    engine_priority = 10
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        return [
            entity_id for entity_id, entity in sorted(entities.items())
            if entity.get("type") == "person" and entity.get("alive", True)
            and entity.get("stage6_role")
        ]

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        tick = frame.simulation_time
        night = getattr(frame, "night", False)
        weather = frame.entities.get("weather-000")
        for entity_id in sorted(frame.due_entity_ids):
            entity = frame.entities.get(entity_id)
            if not entity or not entity.get("alive", True):
                continue
            knowledge = _compat_knowledge(entity.get("knowledge") or empty_knowledge())
            delta = perceive_living(
                entity_id, entity, frame.entities, frame.terrain, tick,
                night=night, weather=weather,
            )
            knowledge, changed, learned = merge_knowledge(knowledge, delta, observer_id=entity_id)
            knowledge, obs_changed, obs_learned = merge_observations_into_knowledge(
                knowledge, delta.get("observations") or [],
            )
            changed = changed or obs_changed
            learned = list(learned) + list(obs_learned)
            state = compat_living_agent_state(entity.get("living_agent"), entity_id, tick, frame.rng)
            state, knowledge, social_changes, social_knowledge_changed = apply_observed_social_information(
                state, knowledge, observer_id=entity_id,
                observations=delta.get("observations") or [], tick=tick,
            )
            changed = changed or social_knowledge_changed
            state, commitment_changes = advance_commitment_deadlines(state, owner_id=entity_id, tick=tick)
            state = derive_internal_pressures(
                entity, state, knowledge, delta, tick, night=night, weather=weather,
            )
            state, perceived_memories = merge_meaningful_memories(
                state, actor_id=entity_id, tick=tick,
                observations=delta.get("observations") or [], learned=learned,
            )
            state = refresh_wants(state, entity_id, tick)
            base_candidates = build_settlement_candidates(entity_id, entity, state, knowledge, delta, tick)
            base_candidates = _apply_group_goal_influence(base_candidates, entity_id, frame.entities, tick)
            candidates = score_goal_candidates(
                base_candidates, actor_id=entity_id, state=state,
                knowledge=knowledge, tick=tick,
            )
            selected = select_goal(candidates)
            desired_action = selected["direct_action_type"]
            target_id = selected.get("target_entity_id")
            target_pos = copy.deepcopy(selected.get("target_pos"))
            prior_plan = entity.get("plan") or {}
            decision_kind = "new_goal"
            paused_plan = copy.deepcopy(entity.get("paused_living_plan"))
            if selected.get("continuation"):
                decision_kind = "plan_continuation"
            elif selected.get("resumption"):
                decision_kind = "resumption"
                paused_plan = None
            elif prior_plan.get("status") == "active" and prior_plan.get("goal") != selected.get("goal"):
                decision_kind = "critical_interrupt" if selected.get("goal") in SURVIVAL_GOALS else "replan"
                if decision_kind == "critical_interrupt":
                    paused_plan = copy.deepcopy(prior_plan)

            actual_action = desired_action
            actual_target_id = target_id
            actual_target_pos = target_pos
            steps = [desired_action.upper()]
            plan_status = "active"
            if target_id and target_pos:
                distance = abs(entity["position"]["x"] - target_pos["x"]) + abs(entity["position"]["y"] - target_pos["y"])
                if distance > 1:
                    route = find_path(entity["position"], target_pos, frame.terrain, ARRIVAL_ADJACENT)
                    if route:
                        actual_action = "move"
                        actual_target_id = None
                        actual_target_pos = route[0]
                        steps = ["MOVE_TO_TARGET", desired_action.upper()]
                    else:
                        actual_action = "rest"
                        actual_target_id = None
                        actual_target_pos = None
                        steps = ["REPLAN", "REST"]
                        plan_status = "abandoned"
                        decision_kind = "failed_plan_replan"

            plan_seed = {
                "goal": selected["goal"], "goal_id": selected["goal_id"],
                "steps": steps, "step_index": 0, "status": plan_status,
                "created_tick": tick,
                "replan_of": prior_plan.get("plan_id") if decision_kind in ("replan", "failed_plan_replan") else None,
            }
            if selected.get("continuation") and prior_plan.get("plan_id"):
                plan_seed["plan_id"] = prior_plan["plan_id"]
                plan_seed["created_tick"] = prior_plan.get("created_tick", tick)
            plan = compat_plan(plan_seed, actor_id=entity_id, tick=tick)
            plan = form_structured_plan(
                plan, actor_id=entity_id, tick=tick, selected=selected,
                context={"required_tools": [selected["tool_id"]] if selected.get("tool_id") else []},
                replan_of=plan.get("replan_of"),
            )
            plan["intent"] = {
                "goal": selected["goal"], "action_type": desired_action,
                "target_id": target_id, "target_pos": target_pos,
                "tool_id": selected.get("tool_id"),
                "resource_kind": selected.get("resource_kind", "food"),
                "allow_unauthorized": bool(selected.get("allow_unauthorized")),
                "message": copy.deepcopy(selected.get("message")),
            }

            working_entities = dict(frame.entities)
            working_actor = copy.deepcopy(entity)
            working_actor["living_agent"] = state
            working_actor["knowledge"] = knowledge
            working_entities[entity_id] = working_actor
            failure_reason = None
            try:
                if actual_action in SOCIAL_DIRECT_ACTIONS:
                    proposal = build_social_action_proposal(
                        working_entities,
                        actor_id=entity_id,
                        action_type=actual_action,
                        tick=tick,
                        target_id=actual_target_id,
                        plan=plan,
                        message=selected.get("message"),
                        obligation=selected.get("obligation"),
                        due_tick=selected.get("due_tick"),
                    )
                else:
                    proposal = build_physical_action_proposal(
                        working_entities,
                        actor_id=entity_id,
                        action_type=actual_action,
                        tick=tick,
                        target_id=actual_target_id,
                        target_pos=actual_target_pos,
                        resource_kind=selected.get("resource_kind", "food"),
                        quantity=1,
                        tool_id=selected.get("tool_id"),
                        plan=plan,
                        goal_id=selected.get("goal_id"),
                        allow_unauthorized=bool(selected.get("allow_unauthorized")),
                        message=selected.get("message"),
                    )
            except ValueError as exc:
                failure_reason = str(exc)
                decision_kind = "failed_plan_replan"
                plan["status"] = "abandoned"
                plan["failure_reason"] = str(exc)
                fallback_plan = copy.deepcopy(plan)
                fallback_plan["steps"] = ["REST"]
                fallback_plan["step_records"] = []
                proposal = build_physical_action_proposal(
                    working_entities, actor_id=entity_id, action_type="rest",
                    tick=tick, plan=fallback_plan, goal_id=selected.get("goal_id"),
                )
                proposal["explanation"] = f"plan failed ({exc}); deterministic fallback rest"

            _replace_living_preconditions(proposal, frame.entities)
            proposal["proposer_engine_id"] = self.engine_id
            proposal["proposer_engine_version"] = self.engine_version
            actor_update = proposal["mutation"]["entity_updates"].setdefault(entity_id, {})
            action = actor_update.get("action") or {}
            executed_action = action.get("type", actual_action)
            actor_after = {**entity, **actor_update}
            actor_after["hunger"] = min(1000, int(actor_after.get("hunger", entity.get("hunger", 0))) + 8)
            actor_after["thirst"] = 0 if executed_action == "drink" else min(
                1000, int(actor_after.get("thirst", entity.get("thirst", 0))) + 10,
            )
            actor_after["energy"] = max(0, int(actor_after.get("energy", entity.get("energy", 0))) - 5)
            actor_update.update({
                "hunger": actor_after["hunger"], "thirst": actor_after["thirst"],
                "energy": actor_after["energy"], "knowledge": knowledge,
                "paused_living_plan": paused_plan,
            })
            if decision_kind == "critical_interrupt":
                action["interrupted_plan_id"] = prior_plan.get("plan_id")
                action["interruption_reason"] = "critical_survival_pressure"
            if executed_action == "move":
                plan["status"] = "active"
            elif plan.get("status") != "abandoned":
                plan["status"] = "completed"
                plan["step_index"] = len(plan.get("steps") or [])
                for record in plan.get("step_records") or []:
                    record["status"] = "completed"
                    record["last_updated_tick"] = tick
            actor_update["plan"] = plan
            action_counts = dict(entity.get("living_action_counts") or {})
            action_counts[executed_action] = min(9999, action_counts.get(executed_action, 0) + 1)
            actor_update["living_action_counts"] = {
                key: action_counts[key] for key in sorted(action_counts)[:32]
            }
            if failure_reason:
                failed_counts = dict(entity.get("living_failed_goal_counts") or {})
                failed_counts[selected["goal"]] = min(
                    9999, int(failed_counts.get(selected["goal"], 0)) + 1,
                )
                actor_update["living_failed_goal_counts"] = {
                    key: failed_counts[key] for key in sorted(failed_counts)[:16]
                }

            resulting_state = actor_update.get("living_agent") or state
            resulting_state = derive_internal_pressures(
                actor_after, resulting_state, knowledge, delta, tick,
                night=night, weather=weather,
            )
            resulting_state, action_memories = merge_meaningful_memories(
                resulting_state, actor_id=entity_id, tick=tick,
                action_result={"action": action},
            )
            resulting_state = refresh_wants(resulting_state, entity_id, tick)
            receipt = build_decision_receipt(
                actor_id=entity_id, tick=tick, state=resulting_state,
                knowledge=knowledge, candidates=candidates, selected=selected,
                plan=plan, decision_kind=decision_kind,
            )
            resulting_state = record_decision(resulting_state, receipt, plan)
            links = list(resulting_state.get("causal_links") or [])
            links.append({
                "link_type": "action", "tick": tick,
                "selected_goal_id": selected.get("goal_id"),
                "plan_id": plan.get("plan_id"), "action_id": action.get("action_id"),
                "proposal_id": None, "accepted_event_id": None,
                "consequences": list((proposal.get("living_action") or {}).get("physical_effects") or []),
            })
            resulting_state["causal_links"] = links[-LIMITS.causal_links_retained:]
            actor_update["living_agent"] = resulting_state
            actor_update["action"] = action
            proposal["living_action"] = {
                **proposal["living_action"],
                "plan_id": plan.get("plan_id"),
                "causal_goal_id": selected.get("goal_id"),
            }
            proposal["explanation"] = (
                f"{decision_kind}: selected {selected['goal']} -> {executed_action}; "
                f"effects={proposal['living_action'].get('physical_effects', [])}"
            )
            proposals.append(proposal)
            diagnostics[entity_id] = {
                "selected_goal": selected["goal"], "goal_id": selected.get("goal_id"),
                "plan_id": plan.get("plan_id"), "decision_kind": decision_kind,
                "candidates": candidates, "decision_receipt": receipt,
                "perception": {"version": delta.get("living_perception_version"),
                               "count": len(delta.get("observations") or []),
                               "attention": delta.get("attention")},
                "social_consequences": social_changes[:8],
                "commitment_consequences": commitment_changes[:8],
                "new_memories": (perceived_memories + action_memories)[:8],
                "explanation": proposal["explanation"],
            }
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)
