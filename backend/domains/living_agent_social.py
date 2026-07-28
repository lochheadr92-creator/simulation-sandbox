"""Capability Stage 6D deterministic social actions and consequences."""
from __future__ import annotations

import copy

from core.constants import (
    EFFORT_TRANSFER_ACTOR_ENERGY_COST,
    EFFORT_TRANSFER_TARGET_ENERGY_GAIN,
)
from core.hashing import canonical_hash
from core.mutations import MERGE_WRAPPER_KEY
from domains.living_agent_actions import living_action_metadata, social_signal_spec
from domains.living_agent_cognition import merge_knowledge_claim
from domains.living_agent_contracts import (
    ACTION_SCHEMA_VERSION,
    COMMITMENT_SCHEMA_VERSION,
    LIMITS,
    RELATIONSHIP_SCHEMA_VERSION,
    SOCIAL_ACTION_TYPES,
    compat_action,
    compat_living_agent_state,
)
from domains.perception import _compat_knowledge


SOCIAL_ACTION_VERSION = "social-action-v1"
SOCIAL_EXCHANGE_VERSION = "social-exchange-v1"


RELATIONSHIP_DIMENSIONS = (
    "familiarity", "trust", "affection", "fear", "respect", "resentment",
    "obligation", "perceived_reliability",
)

RELATIONSHIP_DELTAS = {
    "request_help": {"familiarity": 20, "obligation": 20},
    "offer_help": {"familiarity": 20, "trust": 20, "affection": 15, "perceived_reliability": 10},
    "cooperate": {"trust": 60, "affection": 30, "respect": 40, "perceived_reliability": 50},
    "help": {"trust": 80, "affection": 50, "respect": 45, "obligation": 60, "perceived_reliability": 60},
    "refuse": {"trust": -50, "resentment": 60, "perceived_reliability": -20},
    "warn": {"trust": 40, "respect": 20, "perceived_reliability": 20},
    "share_information": {"familiarity": 20, "trust": 10},
    "give": {"trust": 70, "affection": 40, "respect": 25, "obligation": 45},
    "trade": {"trust": 30, "respect": 20, "perceived_reliability": 30},
    "threaten": {"trust": -100, "fear": 180, "respect": -20, "resentment": 120},
    "apologise": {"trust": 30, "affection": 20, "resentment": -80, "fear": -20},
    "promise": {"trust": 15, "obligation": 50, "perceived_reliability": 10},
    "repay": {"trust": 90, "respect": 60, "obligation": -80, "resentment": -30, "perceived_reliability": 90},
    "confront": {"trust": -30, "fear": 50, "respect": 10, "resentment": 70},
    "compete": {"respect": 20, "resentment": 40},
    "reconcile": {"trust": 80, "affection": 60, "fear": -40, "resentment": -120},
    "take": {"trust": -100, "fear": 30, "resentment": 140, "perceived_reliability": -80},
    "broken_promise": {"trust": -140, "respect": -50, "resentment": 130, "perceived_reliability": -180},
    "contradiction": {"trust": -80, "respect": -20, "resentment": 60, "perceived_reliability": -120},
}


def _clamp(value: int, *, familiarity=False) -> int:
    if familiarity:
        return max(0, min(1000, int(value)))
    return max(-1000, min(1000, int(value)))


def empty_relationship(subject_id: str, tick: int) -> dict:
    return {
        "schema_version": RELATIONSHIP_SCHEMA_VERSION,
        "subject_id": subject_id,
        **{dimension: 0 for dimension in RELATIONSHIP_DIMENSIONS},
        "last_changed_tick": int(tick),
        "last_cause": None,
        "causal_event_ids": [],
        "applied_event_ids": [],
        "pending_event_tick": None,
        "perceived_intention": None,
    }


def apply_relationship_consequence(
    state: dict,
    *,
    owner_id: str,
    subject_id: str,
    action_type: str,
    tick: int,
    confidence: int,
    direct_involvement: bool,
    source_event_id: str | None,
) -> tuple[dict, dict, bool]:
    """Apply one believed/perceived event, idempotent by accepted event id."""
    # CORE-PERF-01 Slice A: shallow copies for `out`/`relationships` -- the
    # only per-key write is `relationships[subject_id] = relation` (a whole-
    # record replacement) below, and `relation` itself stays an independently
    # owned deep copy (kept as-is) before any in-place mutation of it.
    out = dict(state)
    relationships = dict(out.get("relationships") or {})
    relation = copy.deepcopy(relationships.get(subject_id) or empty_relationship(subject_id, tick))
    if relation.get("schema_version") != RELATIONSHIP_SCHEMA_VERSION:
        raise ValueError(f"unsupported relationship schema: {relation.get('schema_version')}")
    if source_event_id and source_event_id in (relation.get("applied_event_ids") or []):
        return out, relation, False

    perceived_type = "share_information" if action_type == "lie" else action_type
    deltas = RELATIONSHIP_DELTAS.get(perceived_type, {"familiarity": 10})
    confidence = max(0, min(1000, int(confidence)))
    involvement_weight = 1000 if direct_involvement else 600
    for dimension in RELATIONSHIP_DIMENSIONS:
        raw_delta = int(deltas.get(dimension, 0))
        if dimension == "familiarity":
            raw_delta += 10  # every causally available interaction increases familiarity
        scaled = raw_delta * confidence * involvement_weight // 1_000_000
        relation[dimension] = _clamp(
            int(relation.get(dimension, 0)) + scaled,
            familiarity=dimension == "familiarity",
        )
    relation["last_changed_tick"] = int(tick)
    relation["last_cause"] = perceived_type
    relation["perceived_intention"] = {
        "kind": perceived_type,
        "basis": "direct_action" if direct_involvement else "observed_or_reported_action",
        "confidence": confidence,
    }
    applied = list(relation.get("applied_event_ids") or [])
    causal = list(relation.get("causal_event_ids") or [])
    if source_event_id:
        if source_event_id not in applied:
            applied.append(source_event_id)
        if source_event_id not in causal:
            causal.append(source_event_id)
        relation["pending_event_tick"] = None
    else:
        relation["pending_event_tick"] = int(tick)
    relation["applied_event_ids"] = applied[-16:]
    relation["causal_event_ids"] = causal[-16:]
    relationships[subject_id] = relation
    if len(relationships) > LIMITS.relationship_records:
        ranked = sorted(
            relationships.items(),
            key=lambda pair: (int(pair[1].get("last_changed_tick", 0)), pair[0]),
            reverse=True,
        )[:LIMITS.relationship_records]
        relationships = {key: value for key, value in sorted(ranked)}
    out["relationships"] = relationships
    return out, copy.deepcopy(relation), True


def _commitment_id(creator_id: str, beneficiary_id: str, kind: str, obligation: str, tick: int) -> str:
    return "commitment-" + canonical_hash([
        COMMITMENT_SCHEMA_VERSION, creator_id, beneficiary_id, kind, obligation, tick,
    ])[:16]


def make_commitment(
    *, creator_id: str, beneficiary_id: str, kind: str, obligation: str,
    tick: int, due_tick: int | None, status: str,
) -> dict:
    commitment_id = _commitment_id(creator_id, beneficiary_id, kind, obligation, tick)
    return {
        "schema_version": COMMITMENT_SCHEMA_VERSION,
        "commitment_id": commitment_id,
        "commitment_kind": kind,
        "creator_id": creator_id,
        "beneficiary_id": beneficiary_id,
        "obligation": obligation,
        "creation_cause": kind,
        "created_tick": int(tick),
        "due_tick": int(due_tick) if due_tick is not None else None,
        "status": status,
        "completed_tick": None,
        "failed_tick": None,
        "cancelled_tick": None,
        "dispute_reason": None,
        "created_event_id": None,
        "last_event_id": None,
        "last_changed_tick": int(tick),
        "reliability_effect": 0,
    }


def _put_commitment(state: dict, commitment: dict) -> dict:
    # CORE-PERF-01 Slice A: shallow copies -- the only write is a whole-record
    # replacement below.
    out = dict(state)
    commitments = dict(out.get("commitments") or {})
    commitments[commitment["commitment_id"]] = copy.deepcopy(commitment)
    ranked = sorted(
        commitments.items(),
        key=lambda pair: (int(pair[1].get("last_changed_tick", 0)), pair[0]),
        reverse=True,
    )[:LIMITS.commitments_per_entity]
    out["commitments"] = {key: value for key, value in sorted(ranked)}
    return out


def advance_commitment_deadlines(state: dict, *, owner_id: str, tick: int) -> tuple[dict, list[dict]]:
    # CORE-PERF-01 Slice A: shallow copies -- the broken-commitment update
    # below (was in-place mutation) uses copy-on-write so no shared record
    # from `state` is ever mutated in place.
    out = dict(state)
    consequences = []
    commitments = dict(out.get("commitments") or {})
    for commitment_id, commitment in sorted(commitments.items()):
        due_tick = commitment.get("due_tick")
        if commitment.get("status") != "active" or due_tick is None or int(tick) <= int(due_tick):
            continue
        commitment = {
            **commitment,
            "status": "broken",
            "failed_tick": int(tick),
            "last_changed_tick": int(tick),
            "last_event_id": None,
            "reliability_effect": -180,
        }
        commitments[commitment_id] = commitment
        consequences.append({
            "kind": "broken_promise",
            "commitment_id": commitment_id,
            "beneficiary_id": commitment.get("beneficiary_id"),
        })
        if commitment.get("beneficiary_id") and commitment.get("beneficiary_id") != owner_id:
            out, _relation, _ = apply_relationship_consequence(
                out, owner_id=owner_id, subject_id=commitment["beneficiary_id"],
                action_type="broken_promise", tick=tick, confidence=1000,
                direct_involvement=True, source_event_id=None,
            )
    out["commitments"] = commitments
    return out, consequences


def _witness_ids(entities: dict, actor_id: str, target_id: str | None) -> list[str]:
    actor = entities[actor_id]
    out = []
    for entity_id in sorted(entities):
        if entity_id in (actor_id, target_id):
            continue
        entity = entities[entity_id]
        if entity.get("type") != "person" or not entity.get("alive", True) or not entity.get("position"):
            continue
        distance = abs(actor["position"]["x"] - entity["position"]["x"]) + abs(actor["position"]["y"] - entity["position"]["y"])
        if distance <= 3:
            out.append(entity_id)
    return out[:LIMITS.witnesses_processed_per_event]


def _sync_resources(update: dict, resources: dict) -> None:
    update["carried_resources"] = copy.deepcopy(resources)
    update["inventory"] = int(resources.get("wood", 0))
    update["food_inventory"] = int(resources.get("food", 0))


def _living_agent_write_diff(before: dict, after: dict) -> dict:
    """The sub-records of a living_agent blob that `after` actually changed,
    as an opt-in merge spec ({MERGE_WRAPPER_KEY: {...}} in the update).

    The social builder only ever modifies a PARTICIPANT'S blob at
    relationships[subject_id] (apply_relationship_consequence's own
    CORE-PERF-01 comment: the only per-key write is a whole-record
    replacement) and commitments[commitment_id] (_put_commitment, same
    shape). Writing just the changed records -- instead of the whole blob
    from a frame-start base -- is what lets two agents act on the same
    person in one frame: disjoint counterpart keys compose instead of
    colliding. Records are never mutated in place under the copy-on-write
    regime, so a shallow snapshot of the before sub-dicts is a sound diff
    base. Note a merge cannot express eviction: if either sub-dict sits at
    its LIMITS cap, an evicted record lingers until the owner's next compat
    pass re-truncates (bounded, self-healing).
    """
    spec = {}
    for sub_key in ("relationships", "commitments"):
        before_records = before.get(sub_key) or {}
        after_records = after.get(sub_key) or {}
        changed = {
            key: after_records[key]
            for key in sorted(after_records)
            if before_records.get(key) != after_records[key]
        }
        if changed:
            spec[sub_key] = changed
    return spec


def build_social_action_proposal(
    entities: dict,
    *,
    actor_id: str,
    action_type: str,
    tick: int,
    target_id: str | None = None,
    plan: dict | None = None,
    message: dict | None = None,
    obligation: str | None = None,
    due_tick: int | None = None,
    resource_kind: str = "food",
    quantity: int = 1,
    propagation_depth: int = 0,
) -> dict:
    if action_type not in SOCIAL_ACTION_TYPES:
        raise ValueError(f"unsupported social action: {action_type}")
    actor = entities.get(actor_id)
    target = entities.get(target_id) if target_id else None
    if not actor or actor.get("type") != "person" or not actor.get("alive", True):
        raise ValueError("social actor must be a living person")
    if action_type != "conceal_information":
        if not target or target.get("type") != "person" or not target.get("alive", True):
            raise ValueError("social action requires a living target")
        distance = abs(actor["position"]["x"] - target["position"]["x"]) + abs(actor["position"]["y"] - target["position"]["y"])
        if distance > 1:
            raise ValueError("social target must be adjacent")

    plan = copy.deepcopy(plan or {})
    plan.setdefault("plan_id", "plan-" + canonical_hash([actor_id, tick, action_type, target_id])[:16])
    plan.setdefault("goal_id", "goal-" + canonical_hash([actor_id, tick, action_type])[:16])
    plan.setdefault("goal", action_type.upper())
    plan.setdefault("step_index", 0)
    actor_state = compat_living_agent_state(actor.get("living_agent"), actor_id, tick)
    target_state = compat_living_agent_state(target.get("living_agent"), target_id, tick) if target else None
    target_blob_before = {
        "relationships": dict(target_state.get("relationships") or {}),
        "commitments": dict(target_state.get("commitments") or {}),
    } if target else {}
    perceived_type = "share_information" if action_type == "lie" else action_type
    if target:
        actor_state, _actor_relation, _ = apply_relationship_consequence(
            actor_state, owner_id=actor_id, subject_id=target_id,
            action_type=perceived_type, tick=tick, confidence=1000,
            direct_involvement=True, source_event_id=None,
        )
        target_state, _target_relation, _ = apply_relationship_consequence(
            target_state, owner_id=target_id, subject_id=actor_id,
            action_type=perceived_type, tick=tick, confidence=1000,
            direct_involvement=True, source_event_id=None,
        )

    action = compat_action(
        {
            "type": action_type,
            "status": "completed",
            "current_stage": "completed",
            "target_entity_id": target_id,
            "target_entity_ids": [target_id] if target_id else [],
            "participants": [target_id] if target_id else [],
            "target_pos": copy.deepcopy((target or actor).get("position")),
            "ticks_spent": 1,
            "ticks_required": 1,
            "started_tick": int(tick),
            "interruptible": True,
            "progress": 1000,
            "physical_effects": ["social_signal", "relationship_change"],
        },
        actor_id=actor_id,
        tick=tick,
        plan=plan,
    )
    updates = {
        actor_id: {
            "action": action,
            "plan": plan,
            "current_goal": plan.get("goal"),
            "living_agent": actor_state,
        }
    }
    touched = [actor_id]
    # Pin only what the action actually depends on: both participants alive,
    # plus exactly the two relationship records it modifies (the counterpart
    # record on each side, path-scoped -- never the whole blob). The old
    # whole-blob living_agent eq pin was a false positive by construction --
    # two agents acting on the same person wrote provably disjoint sub-keys
    # yet one was always discarded (88.8% of baseline rejections over 320
    # ticks: precondition.failed / living_agent_eq_failed). Disjoint
    # concurrent writes now merge instead of colliding; a genuine reciprocal
    # pair (both actions writing the same two records) fails honestly with
    # the record path named. The dotted field also keeps these conditions
    # invisible to the settlement domain's vestigial whole-blob precondition
    # rewriter, which matches field == "living_agent" exactly.
    preconditions = [
        {"entity_id": actor_id, "field": "alive", "op": "eq", "value": True},
    ]
    if target:
        updates[target_id] = {}
        touched.append(target_id)
        actor_record = ((actor.get("living_agent") or {}).get("relationships") or {}).get(target_id)
        target_record = ((target.get("living_agent") or {}).get("relationships") or {}).get(actor_id)
        preconditions.extend([
            {"entity_id": target_id, "field": "alive", "op": "eq", "value": True},
            {"entity_id": actor_id, "field": f"living_agent.relationships.{target_id}",
             "op": "eq", "value": actor_record},
            {"entity_id": target_id, "field": f"living_agent.relationships.{actor_id}",
             "op": "eq", "value": target_record},
        ])

    commitment = None
    if target and action_type in ("request_help", "offer_help", "promise"):
        status = "active" if action_type == "promise" else "pending"
        commitment = make_commitment(
            creator_id=actor_id,
            beneficiary_id=target_id,
            kind=action_type,
            obligation=obligation or action_type.replace("_", " "),
            tick=tick,
            due_tick=due_tick,
            status=status,
        )
        actor_state = _put_commitment(actor_state, commitment)
        target_state = _put_commitment(target_state, commitment)
        updates[actor_id]["living_agent"] = actor_state
    elif target and action_type in ("cooperate", "give"):
        debt = make_commitment(
            creator_id=target_id,
            beneficiary_id=actor_id,
            kind="debt",
            obligation=f"repay {action_type}",
            tick=tick,
            due_tick=due_tick,
            status="active",
        )
        actor_state = _put_commitment(actor_state, debt)
        target_state = _put_commitment(target_state, debt)
        updates[actor_id]["living_agent"] = actor_state
        commitment = debt
    elif target and action_type == "repay":
        matches = [
            item for item in (actor_state.get("commitments") or {}).values()
            if item.get("creator_id") == actor_id
            and item.get("beneficiary_id") == target_id
            and item.get("status") in ("active", "overdue", "disputed", "broken")
        ]
        if not matches:
            raise ValueError("no repayable commitment")
        commitment = copy.deepcopy(sorted(matches, key=lambda item: item["commitment_id"])[0])
        commitment["status"] = "completed"
        commitment["completed_tick"] = int(tick)
        commitment["last_changed_tick"] = int(tick)
        commitment["last_event_id"] = None
        commitment["reliability_effect"] = 90
        actor_state = _put_commitment(actor_state, commitment)
        target_state = _put_commitment(target_state, commitment)
        updates[actor_id]["living_agent"] = actor_state

    social_exchange = None
    if target and action_type == "give":
        actor_resources = copy.deepcopy(actor.get("carried_resources") or {})
        target_resources = copy.deepcopy(target.get("carried_resources") or {})
        if actor_resources.get(resource_kind, 0) < quantity:
            raise ValueError("insufficient gift resource")
        actor_after = copy.deepcopy(actor_resources)
        target_after = copy.deepcopy(target_resources)
        actor_after[resource_kind] -= quantity
        target_after[resource_kind] = target_after.get(resource_kind, 0) + quantity
        _sync_resources(updates[actor_id], actor_after)
        _sync_resources(updates[target_id], target_after)
        social_exchange = {
            "schema_version": SOCIAL_EXCHANGE_VERSION,
            "kind": "give", "resource_kind": resource_kind, "quantity": int(quantity),
            "actor_before": actor_resources, "target_before": target_resources,
            "actor_after": actor_after, "target_after": target_after,
        }
        preconditions.extend([
            {"entity_id": actor_id, "field": "carried_resources", "op": "eq", "value": actor_resources},
            {"entity_id": target_id, "field": "carried_resources", "op": "eq", "value": target_resources},
        ])
    elif target and action_type == "trade":
        terms = (message or {}).get("trade") or {}
        offer_kind = terms.get("offer_kind", resource_kind)
        request_kind = terms.get("request_kind", "wood" if offer_kind != "wood" else "food")
        trade_quantity = max(1, int(terms.get("quantity", quantity)))
        actor_resources = copy.deepcopy(actor.get("carried_resources") or {})
        target_resources = copy.deepcopy(target.get("carried_resources") or {})
        if actor_resources.get(offer_kind, 0) < trade_quantity or target_resources.get(request_kind, 0) < trade_quantity:
            raise ValueError("trade resources unavailable")
        actor_after = copy.deepcopy(actor_resources)
        target_after = copy.deepcopy(target_resources)
        actor_after[offer_kind] -= trade_quantity
        target_after[offer_kind] = target_after.get(offer_kind, 0) + trade_quantity
        target_after[request_kind] -= trade_quantity
        actor_after[request_kind] = actor_after.get(request_kind, 0) + trade_quantity
        _sync_resources(updates[actor_id], actor_after)
        _sync_resources(updates[target_id], target_after)
        social_exchange = {
            "schema_version": SOCIAL_EXCHANGE_VERSION,
            "kind": "trade", "offer_kind": offer_kind, "request_kind": request_kind,
            "quantity": trade_quantity, "actor_before": actor_resources,
            "target_before": target_resources, "actor_after": actor_after,
            "target_after": target_after,
        }
        preconditions.extend([
            {"entity_id": actor_id, "field": "carried_resources", "op": "eq", "value": actor_resources},
            {"entity_id": target_id, "field": "carried_resources", "op": "eq", "value": target_resources},
        ])
    elif target and action_type == "cooperate":
        updates[target_id]["energy"] = min(1000, int(target.get("energy", 0)) + EFFORT_TRANSFER_TARGET_ENERGY_GAIN)
        updates[actor_id]["energy"] = max(0, int(actor.get("energy", 0)) - EFFORT_TRANSFER_ACTOR_ENERGY_COST)

    claim = copy.deepcopy((message or {}).get("claim"))
    if target and action_type in ("warn", "share_information", "lie") and claim:
        prior_target_knowledge = _compat_knowledge(target.get("knowledge"))
        target_knowledge, learned_claim = merge_knowledge_claim(
            prior_target_knowledge,
            observer_id=target_id,
            subject_id=claim["subject_id"],
            fact_type=claim["fact_type"],
            properties=claim.get("properties") or {},
            tick=tick,
            provenance_kind="reported",
            confidence=int(claim.get("confidence", 650)),
            source_entity_id=actor_id,
            source_event_id=None,
            # The recipient cannot know a statement is deceptive merely
            # because canonical action truth says it was a lie.
            deceptive=False,
        )
        updates[target_id]["knowledge"] = target_knowledge
        claim["fact_id"] = learned_claim["fact_id"]
        contradicted_sources = {
            (prior_target_knowledge.get("facts") or {}).get(fact_id, {}).get("source_entity_id")
            for fact_id in learned_claim.get("contradicts") or []
        } - {None, actor_id}
        for contradicted_source in sorted(contradicted_sources):
            target_state, _relation, _ = apply_relationship_consequence(
                target_state,
                owner_id=target_id,
                subject_id=contradicted_source,
                action_type="contradiction",
                tick=tick,
                confidence=int(claim.get("confidence", 650)),
                direct_involvement=False,
                source_event_id=None,
            )
    if target:
        participant_write = _living_agent_write_diff(target_blob_before, target_state)
        if participant_write:
            updates[target_id]["living_agent"] = {MERGE_WRAPPER_KEY: participant_write}

    perceived_action_type = "share_information" if action_type == "lie" else action_type
    signal_message = {
        "action_type": perceived_action_type,
        "actor_id": actor_id,
        "target_id": target_id,
        "claim": claim,
        "commitment_id": (commitment or {}).get("commitment_id"),
    }
    new_entities = {}
    witnesses = _witness_ids(entities, actor_id, target_id)
    if action_type != "conceal_information":
        signal_id, signal = social_signal_spec(
            actor_id=actor_id,
            action_id=action["action_id"],
            action_type=action_type,
            tick=tick,
            position=actor["position"],
            message=signal_message,
            recipient_ids=[target_id] if target_id else [],
            witness_ids=witnesses,
            truth_status="deceptive" if action_type == "lie" else "asserted",
            propagation_depth=propagation_depth,
        )
        new_entities[signal_id] = signal
        touched.append(signal_id)
    else:
        action["physical_effects"] = ["concealment_record", "internal_memory_change"]
        updates[actor_id]["action"] = action

    living_meta = living_action_metadata(action, plan)
    living_meta["physical_effects"] = list(action.get("physical_effects") or [])
    social_meta = {
        "schema_version": SOCIAL_ACTION_VERSION,
        "action_type": action_type,
        "actor_id": actor_id,
        "target_id": target_id,
        "information_route": "concealed" if action_type == "conceal_information" else "direct_interaction",
        "recipient_ids": [target_id] if target_id else [],
        "witness_ids": witnesses,
        "propagation_depth": min(int(propagation_depth), LIMITS.information_propagation_depth),
        "truth_status": "deceptive" if action_type == "lie" else "asserted",
        "commitment": copy.deepcopy(commitment),
        "claim": claim,
        "social_exchange": social_exchange,
    }
    parent_ids = sorted({
        event_id for event_id in (actor.get("last_event_id"), (target or {}).get("last_event_id")) if event_id
    })
    return {
        "proposal_family": "living_agent_social",
        "proposal_type": f"social_{action_type}",
        "proposer_engine_id": "living_social",
        "proposer_engine_version": "1.0.0",
        "entity_id": actor_id,
        "causal_parent_event_ids": parent_ids,
        "is_exogenous": not bool(parent_ids),
        "requested_time": int(tick),
        "phase": "agent",
        "engine_priority": 10,
        "touched_scope": sorted(set(touched)),
        "preconditions": preconditions,
        "mutation": {"entity_updates": updates, "new_entities": new_entities},
        "living_action": living_meta,
        "social_action": social_meta,
        "explanation": f"{actor_id} performs {action_type} toward {target_id}",
    }


def validate_social_action_proposal(proposal: dict, entities: dict) -> str | None:
    meta = proposal.get("social_action")
    if meta is None:
        return None
    if not isinstance(meta, dict) or meta.get("schema_version") != SOCIAL_ACTION_VERSION:
        return "social_action.invalid_version"
    action_type = meta.get("action_type")
    if action_type not in SOCIAL_ACTION_TYPES:
        return "social_action.invalid_type"
    actor_id = meta.get("actor_id")
    target_id = meta.get("target_id")
    if actor_id != proposal.get("entity_id"):
        return "social_action.invalid_actor"
    if len(meta.get("recipient_ids") or []) > LIMITS.social_propagation_recipients:
        return "social_action.recipient_limit"
    if len(meta.get("witness_ids") or []) > LIMITS.witnesses_processed_per_event:
        return "social_action.witness_limit"
    if int(meta.get("propagation_depth", 0)) > LIMITS.information_propagation_depth:
        return "social_action.propagation_depth"
    if action_type != "conceal_information":
        actor, target = entities.get(actor_id), entities.get(target_id)
        if not actor or not target or actor.get("type") != target.get("type") or actor.get("type") != "person":
            return "social_action.invalid_participant"
        distance = abs(actor["position"]["x"] - target["position"]["x"]) + abs(actor["position"]["y"] - target["position"]["y"])
        if distance > 1:
            return "social_action.not_adjacent"
    updates = (proposal.get("mutation") or {}).get("entity_updates") or {}
    allowed_people = {actor_id, target_id} - {None}
    for entity_id, update in updates.items():
        if "living_agent" in update and entity_id not in allowed_people:
            return "social_action.uncausal_relationship_update"
    if action_type == "lie" and target_id:
        target_knowledge = (updates.get(target_id) or {}).get("knowledge") or {}
        if any(fact.get("deceptive_source_claim") for fact in (target_knowledge.get("facts") or {}).values()):
            return "social_action.deception_leak"
    commitment = meta.get("commitment")
    if commitment:
        if commitment.get("schema_version") != COMMITMENT_SCHEMA_VERSION:
            return "social_action.invalid_commitment"
        if commitment.get("creator_id") not in allowed_people or commitment.get("beneficiary_id") not in allowed_people:
            return "social_action.invalid_commitment_participant"
    exchange = meta.get("social_exchange")
    if exchange:
        if exchange.get("schema_version") != SOCIAL_EXCHANGE_VERSION:
            return "social_action.invalid_exchange"
        actor_before = exchange.get("actor_before") or {}
        target_before = exchange.get("target_before") or {}
        actor_after = exchange.get("actor_after") or {}
        target_after = exchange.get("target_after") or {}
        all_kinds = set(actor_before) | set(target_before) | set(actor_after) | set(target_after)
        for kind in all_kinds:
            if actor_before.get(kind, 0) + target_before.get(kind, 0) != actor_after.get(kind, 0) + target_after.get(kind, 0):
                return "social_action.nonconserving_exchange"
        if (updates.get(actor_id) or {}).get("carried_resources") != actor_after:
            return "social_action.exchange_mutation_mismatch"
        if (updates.get(target_id) or {}).get("carried_resources") != target_after:
            return "social_action.exchange_mutation_mismatch"
    return None


def apply_observed_social_information(
    state: dict,
    knowledge: dict,
    *,
    observer_id: str,
    observations: list[dict],
    tick: int,
) -> tuple[dict, dict, list[dict], bool]:
    """Apply only causally perceived signal consequences for this observer."""
    # CORE-PERF-01 Slice A: shallow copy -- out_state is only ever reassigned
    # wholesale via apply_relationship_consequence() below, never mutated
    # in place directly in this function.
    out_state = dict(state)
    out_knowledge = _compat_knowledge(knowledge)
    consequences = []
    knowledge_changed = False
    for observation in sorted(observations or [], key=lambda item: item.get("observation_id", "")):
        if observation.get("observation_type") != "signal":
            continue
        properties = observation.get("properties") or {}
        message = properties.get("message") or {}
        source_event_id = properties.get("source_event_id") or observation.get("source_event_id")
        source_actor_id = message.get("actor_id") or properties.get("source_entity_id")
        perceived_action = message.get("action_type")
        if not source_event_id or not source_actor_id or source_actor_id == observer_id or not perceived_action:
            continue
        direct = message.get("target_id") == observer_id
        out_state, relation, changed = apply_relationship_consequence(
            out_state,
            owner_id=observer_id,
            subject_id=source_actor_id,
            action_type=perceived_action,
            tick=tick,
            confidence=int(observation.get("confidence", 500)),
            direct_involvement=direct,
            source_event_id=source_event_id,
        )
        if changed:
            consequences.append({
                "kind": "relationship_change",
                "subject_id": source_actor_id,
                "source_event_id": source_event_id,
                "direct": direct,
                "relationship": relation,
            })

        claim = message.get("claim")
        if not isinstance(claim, dict):
            continue
        already_applied = any(
            fact.get("source_event_id") == source_event_id
            and fact.get("provenance_kind") in ("reported", "inferred", "rumoured")
            for fact in (out_knowledge.get("facts") or {}).values()
        )
        if already_applied:
            continue
        prior_facts = copy.deepcopy(out_knowledge.get("facts") or {})
        out_knowledge, claim_fact = merge_knowledge_claim(
            out_knowledge,
            observer_id=observer_id,
            subject_id=claim["subject_id"],
            fact_type=claim["fact_type"],
            properties=claim.get("properties") or {},
            tick=tick,
            provenance_kind="reported",
            confidence=min(int(claim.get("confidence", 650)), int(observation.get("confidence", 500))),
            source_entity_id=source_actor_id,
            source_event_id=source_event_id,
            deceptive=False,
        )
        knowledge_changed = True
        consequences.append({
            "kind": "knowledge_report",
            "fact_id": claim_fact["fact_id"],
            "source_event_id": source_event_id,
        })
        contradicted_sources = {
            prior_facts[fact_id].get("source_entity_id")
            for fact_id in claim_fact.get("contradicts") or []
            if fact_id in prior_facts and prior_facts[fact_id].get("source_entity_id")
        }
        for contradicted_source in sorted(contradicted_sources):
            out_state, relation, changed = apply_relationship_consequence(
                out_state,
                owner_id=observer_id,
                subject_id=contradicted_source,
                action_type="contradiction",
                tick=tick,
                confidence=int(observation.get("confidence", 500)),
                direct_involvement=False,
                source_event_id=source_event_id + ":contradiction:" + contradicted_source,
            )
            if changed:
                consequences.append({
                    "kind": "source_contradicted",
                    "subject_id": contradicted_source,
                    "relationship": relation,
                })
    return out_state, out_knowledge, consequences, knowledge_changed
