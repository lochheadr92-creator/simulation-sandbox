"""Deterministic long-run harness for Capability Stage 6 living agents.

The harness uses the same pure kernel and accepted-event mutation path as a
persisted run.  It deliberately avoids database access so repeatability,
bounded state, and the integrated camp scenario can be exercised in CI.
"""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter, defaultdict

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario


def _lineage_key(seed: str) -> str:
    return f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"


def _event_hash(event: dict) -> str:
    canonical = copy.deepcopy(event)
    canonical.pop("run_id", None)
    return canonical_hash(canonical)


def _counter_dict(counter: Counter) -> dict:
    return {key: int(counter[key]) for key in sorted(counter)}


def run_living_agent_harness(
    seed: str = "living-agents-stage6",
    *,
    ticks: int = 320,
    run_id: str = "living-agent-harness",
    reverse_entity_order: bool = False,
    capture_events: bool = False,
) -> dict:
    """Run the canonical Stage 6 scenario and return trace evidence.

    ``run_id`` is intentionally excluded from canonical trace hashes so two
    independent runs with the same seed can be compared directly.
    """
    if ticks < 0:
        raise ValueError("ticks must be non-negative")

    scenario = get_scenario("living_settlement")
    lineage_key = _lineage_key(seed)
    world, entities, genesis, genesis_rejected, order_index = build_genesis(
        seed, scenario, lineage_key,
    )
    if reverse_entity_order:
        entities = dict(reversed(list(entities.items())))

    initial_entities = copy.deepcopy(entities)
    accepted_events = list(genesis) if capture_events else []
    rejected_proposals = list(genesis_rejected) if capture_events else []
    accepted_event_count = len(genesis)
    rejected_proposal_count = len(genesis_rejected)
    valid_parent_ids = {event["id"] for event in genesis}
    event_hashes = [_event_hash(event) for event in genesis]
    frame_hashes = [
        genesis[-1]["post_state_hash"]
        if genesis else canonical_hash(snapshot_for_hash(entities, 0, lineage_key))
    ]
    accepted_by_type = Counter(event["event_type"] for event in genesis)
    rejected_by_reason = Counter(row["reason_code"] for row in genesis_rejected)
    actions_by_type = Counter()
    goals_by_actor: dict[str, set[str]] = defaultdict(set)
    decisions_by_kind = Counter()
    plan_failure_reasons = Counter()
    weather_conditions = []
    max_state_counts = {
        "knowledge_facts": 0,
        "memories": 0,
        "relationships": 0,
        "commitments": 0,
        "decision_history": 0,
        "causal_links": 0,
    }

    rng = DeterministicRNG(seed)
    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, diagnostics = run_tick(
            run_id,
            entities,
            world["terrain"],
            tick,
            rng,
            order_index,
            lineage_key,
            scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        accepted_event_count += len(accepted)
        rejected_proposal_count += len(rejected)
        if capture_events:
            accepted_events.extend(copy.deepcopy(accepted))
            rejected_proposals.extend(copy.deepcopy(rejected))
        for event in accepted:
            valid_parent_ids.add(event["id"])
            event_hashes.append(_event_hash(event))
            accepted_by_type[event["event_type"]] += 1
            living_action = event.get("living_action") or {}
            if living_action.get("action_type"):
                actions_by_type[living_action["action_type"]] += 1
            if event.get("event_type") == "weather_transition":
                weather_update = (event.get("mutation") or {}).get("entity_updates", {}).get("weather-000", {})
                weather_conditions.append(weather_update.get("condition"))
            actor_update = (event.get("mutation") or {}).get("entity_updates", {}).get(event.get("entity_id"), {})
            failure_reason = (actor_update.get("plan") or {}).get("failure_reason")
            if failure_reason:
                plan_failure_reasons[failure_reason] += 1
        for rejection in rejected:
            rejected_by_reason[rejection["reason_code"]] += 1
        if accepted:
            frame_hashes.append(accepted[-1]["post_state_hash"])
        else:
            frame_hashes.append(frame_hashes[-1])

        for actor_id, row in sorted(diagnostics.items()):
            if not actor_id.startswith("person-") or not isinstance(row, dict):
                continue
            if row.get("selected_goal"):
                goals_by_actor[actor_id].add(row["selected_goal"])
            if row.get("decision_kind"):
                decisions_by_kind[row["decision_kind"]] += 1

        for entity in entities.values():
            if entity.get("type") != "person":
                continue
            living = entity.get("living_agent") or {}
            knowledge = entity.get("knowledge") or {}
            counts = {
                "knowledge_facts": len(knowledge.get("facts") or {}),
                "memories": len(living.get("memories") or {}),
                "relationships": len(living.get("relationships") or {}),
                "commitments": len(living.get("commitments") or {}),
                "decision_history": len(living.get("decision_history") or []),
                "causal_links": len(living.get("causal_links") or []),
            }
            for key, count in counts.items():
                max_state_counts[key] = max(max_state_counts[key], count)

    final_people = {
        entity_id: entity for entity_id, entity in sorted(entities.items())
        if entity.get("type") == "person"
    }
    final_relationships = sum(
        len((person.get("living_agent") or {}).get("relationships") or {})
        for person in final_people.values()
    )
    final_commitments = Counter(
        commitment.get("status", "unknown")
        for person in final_people.values()
        for commitment in ((person.get("living_agent") or {}).get("commitments") or {}).values()
    )
    knowledge_provenance = Counter(
        fact.get("provenance_kind", "legacy")
        for person in final_people.values()
        for fact in (person.get("knowledge") or {}).get("facts", {}).values()
    )
    deceptive_claims = sum(
        1
        for person in final_people.values()
        for fact in (person.get("knowledge") or {}).get("facts", {}).values()
        if fact.get("deceptive_source_claim")
    )
    reported_claims = [
        fact
        for person in final_people.values()
        for fact in (person.get("knowledge") or {}).get("facts", {}).values()
        if fact.get("provenance_kind") in ("reported", "inferred", "rumoured")
    ]
    false_beliefs = 0
    for fact in reported_claims:
        canonical_subject = entities.get(fact.get("subject")) or {}
        claimed = fact.get("properties") or {}
        comparable = {
            key: canonical_subject.get(key)
            for key in claimed
            if key in canonical_subject
        }
        if comparable and any(claimed.get(key) != value for key, value in comparable.items()):
            false_beliefs += 1
    contradicted_claims = sum(
        1
        for person in final_people.values()
        for fact in (person.get("knowledge") or {}).get("facts", {}).values()
        if fact.get("status") == "contradicted" or int(fact.get("contradiction_count", 0)) > 0
    )
    initial_resource_total = sum(
        int(entity.get("quantity", entity.get("resource", 0)))
        for entity in initial_entities.values()
        if entity.get("type") in ("resource", "tree")
    )
    final_resource_total = sum(
        int(entity.get("quantity", entity.get("resource", 0)))
        for entity in entities.values()
        if entity.get("type") in ("resource", "tree")
    )

    return {
        "seed": seed,
        "ticks": ticks,
        "lineage_key": lineage_key,
        "initial_entities": initial_entities,
        "entities": copy.deepcopy(entities),
        "accepted_events": accepted_events,
        "rejected_proposals": rejected_proposals,
        "event_hashes": event_hashes,
        "frame_hashes": frame_hashes,
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, ticks, lineage_key)),
        "summary": {
            "accepted_event_count": accepted_event_count,
            "rejected_proposal_count": rejected_proposal_count,
            "accepted_by_type": _counter_dict(accepted_by_type),
            "rejected_by_reason": _counter_dict(rejected_by_reason),
            "actions_by_type": _counter_dict(actions_by_type),
            "goals_by_actor": {
                actor_id: sorted(goals) for actor_id, goals in sorted(goals_by_actor.items())
            },
            "decisions_by_kind": _counter_dict(decisions_by_kind),
            "plan_failure_reasons": _counter_dict(plan_failure_reasons),
            "weather_conditions": weather_conditions,
            "final_relationship_count": final_relationships,
            "commitment_statuses": _counter_dict(final_commitments),
            "knowledge_provenance": _counter_dict(knowledge_provenance),
            "reported_claim_count": len(reported_claims),
            "false_belief_count": false_beliefs,
            # Must remain zero: actors receive a claim, not hidden narrator truth.
            "deceptive_claim_count": deceptive_claims,
            "contradicted_claim_count": contradicted_claims,
            "resource_depletion": initial_resource_total - final_resource_total,
            "max_state_counts": max_state_counts,
        },
    }


def _public_report(result: dict) -> dict:
    return {
        "seed": result["seed"],
        "ticks": result["ticks"],
        "final_state_hash": result["final_state_hash"],
        **result["summary"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default="living-agents-stage6")
    parser.add_argument("--ticks", type=int, default=320)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args(argv)
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    baseline = run_living_agent_harness(
        args.seed, ticks=args.ticks, run_id="living-agent-harness-1",
    )
    repeat_matches = True
    for index in range(2, args.repeat + 1):
        repeated = run_living_agent_harness(
            args.seed, ticks=args.ticks, run_id=f"living-agent-harness-{index}",
        )
        repeat_matches = repeat_matches and all((
            baseline["event_hashes"] == repeated["event_hashes"],
            baseline["frame_hashes"] == repeated["frame_hashes"],
            baseline["final_state_hash"] == repeated["final_state_hash"],
            baseline["entities"] == repeated["entities"],
            baseline["summary"] == repeated["summary"],
        ))
    report = _public_report(baseline)
    report["repeat_count"] = args.repeat
    report["repeat_matches"] = repeat_matches
    print(json.dumps(report, sort_keys=True, indent=2))
    if not repeat_matches:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
