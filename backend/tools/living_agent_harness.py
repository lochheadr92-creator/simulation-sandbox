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
from core.hashing import canonical_hash, canonical_json
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    LIMITS as ASSOCIATION_LIMITS,
    association_capacity_diagnostics,
    association_current_truth_summary,
)
from core.rng import DeterministicRNG
from scenarios import get_scenario
from domains.group_goal_contracts import GROUP_GOAL_REGISTRY_ID
from domains.group_norm_contracts import GROUP_NORM_REGISTRY_ID
from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_ID,
    LIMITS as GROUP_STATE_LIMITS,
    group_state_capacity_diagnostics,
    group_state_current_truth_summary,
)
from domains.group_collective_contracts import (
    LIMITS as GROUP_COLLECTIVE_LIMITS,
    PROPOSAL_TYPE as GROUP_COLLECTIVE_PROPOSAL_TYPE,
)


def _lineage_key(seed: str) -> str:
    return f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"


def _event_hash(event: dict) -> str:
    canonical = copy.deepcopy(event)
    canonical.pop("run_id", None)
    return canonical_hash(canonical)


def _counter_dict(counter: Counter) -> dict:
    return {key: int(counter[key]) for key in sorted(counter)}


def _headroom_percent(used_bytes: int, cap_bytes: int) -> float:
    return round(max(0, cap_bytes - used_bytes) * 100.0 / cap_bytes, 3)


def run_living_agent_harness(
    seed: str = "living-agents-stage6",
    *,
    ticks: int = 320,
    run_id: str = "living-agent-harness",
    reverse_entity_order: bool = False,
    capture_events: bool = False,
    scenario_id: str = "living_settlement",
    resume_at_tick: int | None = None,
    debug_assert_fragment_cache: bool = False,
) -> dict:
    """Run a living-agent scenario and return deterministic trace evidence.

    ``run_id`` is intentionally excluded from canonical trace hashes so two
    independent runs with the same seed can be compared directly.

    CORE-PERF-01 Slice B: an entity-JSON fragment cache (see
    ``core.mutations.spliced_snapshot_json``) is always used for the per-
    event canonical hash -- it is a derived, non-canonical performance aid
    that is verified byte-identical to the un-cached computation by
    construction. ``debug_assert_fragment_cache=True`` additionally proves
    that byte-identity on every single accepted event of this run (used for
    the gate, not normal use -- it defeats the optimization's purpose by
    doing both computations).
    """
    if ticks < 0:
        raise ValueError("ticks must be non-negative")
    if resume_at_tick is not None and not 1 <= resume_at_tick <= ticks:
        raise ValueError("resume_at_tick must be within the simulated tick range")

    scenario = get_scenario(scenario_id)
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
    entity_json_cache: dict = {}
    event_hashes = [_event_hash(event) for event in genesis]
    frame_hashes = [
        genesis[-1]["post_state_hash"]
        if genesis else canonical_hash(snapshot_for_hash(entities, 0, lineage_key))
    ]
    accepted_by_type = Counter(event["event_type"] for event in genesis)
    rejected_by_reason = Counter(row["reason_code"] for row in genesis_rejected)
    capacity_rejections = Counter()
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
        "association_records": 0,
        "group_candidates": 0,
        "dissolved_groups": 0,
        "association_registry_bytes": 0,
        "shared_group_states": 0,
        "shared_group_facts": 0,
        "group_state_processed_proposals": 0,
        "group_state_registry_bytes": 0,
        "collective_processed_keys": 0,
        "collective_storage_content_units": 0,
    }
    capacity_peaks = {
        "association": {"bytes": 0, "tick": None, "composition": {}},
        "group_state": {"bytes": 0, "tick": None, "composition": {}},
        "collective": {
            "processed_keys": 0,
            "tick": None,
            "cap": GROUP_COLLECTIVE_LIMITS.processed_keys,
        },
    }
    stage7c = {
        "first_accepted_tick": None,
        "first_rejected_tick": None,
        "accepted_count": 0,
        "rejected_count": 0,
        "accepted_participant_orders": [],
        "rejected_by_reason": Counter(),
        "final_storage_contents": {},
        "final_storage_processed_keys": 0,
    }
    truth_changes_after_320 = {
        "association": 0,
        "group_state": 0,
        "combined": 0,
        "first_tick": None,
        "last_tick": None,
    }
    truth_hash_at_tick_320 = None
    previous_association_truth_hash = canonical_hash(association_current_truth_summary({}))
    previous_group_state_truth_hash = canonical_hash(group_state_current_truth_summary({}))
    previous_combined_truth_hash = canonical_hash([
        previous_association_truth_hash, previous_group_state_truth_hash,
    ])
    replayed_entities = {}
    for event in genesis:
        apply_mutation(replayed_entities, copy.deepcopy(event["mutation"]))

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
            entity_json_cache=entity_json_cache,
            debug_assert_fragment_cache=debug_assert_fragment_cache,
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
            # Stage 7C non-authoritative metrics only
            if event.get("event_type") == GROUP_COLLECTIVE_PROPOSAL_TYPE:
                stage7c["accepted_count"] += 1
                if stage7c["first_accepted_tick"] is None:
                    stage7c["first_accepted_tick"] = int(tick)
                collective = event.get("collective_action") or {}
                stage7c["accepted_participant_orders"].append({
                    "tick": int(tick),
                    "group_id": collective.get("group_id"),
                    "initiator_id": collective.get("initiator_id"),
                    "participant_ids": list(collective.get("participant_ids") or []),
                    "action_key": collective.get("action_key"),
                })
        for rejection in rejected:
            rejected_by_reason[rejection["reason_code"]] += 1
            if rejection["reason_code"] in (
                "association.payload_limit", "group_state.payload_limit",
            ):
                capacity_rejections[rejection["reason_code"]] += 1
            if str(rejection["reason_code"]).startswith("group_collective."):
                stage7c["rejected_count"] += 1
                stage7c["rejected_by_reason"][rejection["reason_code"]] += 1
                if stage7c["first_rejected_tick"] is None:
                    stage7c["first_rejected_tick"] = int(tick)
        for event in accepted:
            apply_mutation(replayed_entities, copy.deepcopy(event["mutation"]))
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

        association_registry = entities.get(ASSOCIATION_REGISTRY_ID) or {}
        max_state_counts["association_records"] = max(
            max_state_counts["association_records"],
            len(association_registry.get("association_records") or {}),
        )
        max_state_counts["group_candidates"] = max(
            max_state_counts["group_candidates"],
            len(association_registry.get("group_candidates") or {}),
        )
        max_state_counts["dissolved_groups"] = max(
            max_state_counts["dissolved_groups"],
            len(association_registry.get("dissolved_history") or []),
        )
        max_state_counts["association_registry_bytes"] = max(
            max_state_counts["association_registry_bytes"],
            len(canonical_json(association_registry).encode("utf-8")) if association_registry else 0,
        )
        if association_registry:
            association_composition = association_capacity_diagnostics(association_registry)
            association_bytes = association_composition["total_serialized_bytes"]
            if association_bytes > capacity_peaks["association"]["bytes"]:
                capacity_peaks["association"] = {
                    "bytes": association_bytes,
                    "tick": int(tick),
                    "composition": association_composition,
                }
        group_state_registry = entities.get(GROUP_STATE_REGISTRY_ID) or {}
        group_states = group_state_registry.get("groups") or {}
        group_facts = sum(
            len(group.get("facts") or {})
            for group in group_states.values()
        )
        max_state_counts["shared_group_states"] = max(
            max_state_counts["shared_group_states"], len(group_states),
        )
        max_state_counts["shared_group_facts"] = max(
            max_state_counts["shared_group_facts"], group_facts,
        )
        max_state_counts["group_state_processed_proposals"] = max(
            max_state_counts["group_state_processed_proposals"],
            len(group_state_registry.get("processed_proposal_keys") or []),
        )
        max_state_counts["group_state_registry_bytes"] = max(
            max_state_counts["group_state_registry_bytes"],
            len(canonical_json(group_state_registry).encode("utf-8")) if group_state_registry else 0,
        )
        if group_state_registry:
            group_state_composition = group_state_capacity_diagnostics(group_state_registry)
            group_state_bytes = group_state_composition["total_serialized_bytes"]
            if group_state_bytes > capacity_peaks["group_state"]["bytes"]:
                capacity_peaks["group_state"] = {
                    "bytes": group_state_bytes,
                    "tick": int(tick),
                    "composition": group_state_composition,
                }

        # Stage 7C: track bounded processed-key growth on storage entities
        collective_key_total = 0
        max_keys_on_one_storage = 0
        storage_units = 0
        for entity in entities.values():
            if entity.get("type") not in ("storage", "container"):
                continue
            keys = entity.get("collective_processed_keys") or []
            key_count = len(keys)
            collective_key_total += key_count
            max_keys_on_one_storage = max(max_keys_on_one_storage, key_count)
            contents = entity.get("contents") or {}
            storage_units += sum(
                int(value) for value in contents.values() if isinstance(value, (int, float))
            )
        max_state_counts["collective_processed_keys"] = max(
            max_state_counts["collective_processed_keys"], collective_key_total,
        )
        max_state_counts["collective_storage_content_units"] = max(
            max_state_counts["collective_storage_content_units"], storage_units,
        )
        if max_keys_on_one_storage > capacity_peaks["collective"]["processed_keys"]:
            capacity_peaks["collective"] = {
                "processed_keys": max_keys_on_one_storage,
                "tick": int(tick),
                "cap": GROUP_COLLECTIVE_LIMITS.processed_keys,
            }

        association_truth_hash = canonical_hash(
            association_current_truth_summary(association_registry)
        )
        group_state_truth_hash = canonical_hash(
            group_state_current_truth_summary(group_state_registry)
        )
        combined_truth_hash = canonical_hash([
            association_truth_hash, group_state_truth_hash,
        ])
        if tick == 320:
            truth_hash_at_tick_320 = combined_truth_hash
        if tick > 320:
            if association_truth_hash != previous_association_truth_hash:
                truth_changes_after_320["association"] += 1
            if group_state_truth_hash != previous_group_state_truth_hash:
                truth_changes_after_320["group_state"] += 1
            if combined_truth_hash != previous_combined_truth_hash:
                truth_changes_after_320["combined"] += 1
                truth_changes_after_320["first_tick"] = (
                    truth_changes_after_320["first_tick"] or int(tick)
                )
                truth_changes_after_320["last_tick"] = int(tick)
        previous_association_truth_hash = association_truth_hash
        previous_group_state_truth_hash = group_state_truth_hash
        previous_combined_truth_hash = combined_truth_hash

        if resume_at_tick is not None and tick == resume_at_tick:
            entities = copy.deepcopy(entities)
            valid_parent_ids = set(valid_parent_ids)
            rng = DeterministicRNG(seed)

    final_people = {
        entity_id: entity for entity_id, entity in sorted(entities.items())
        if entity.get("type") == "person"
    }
    final_relationships = sum(
        len((person.get("living_agent") or {}).get("relationships") or {})
        for person in final_people.values()
    )
    final_association_registry = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    final_group_state_registry = entities.get(GROUP_STATE_REGISTRY_ID) or {}
    final_group_goal_registry = entities.get(GROUP_GOAL_REGISTRY_ID) or {}
    _final_group_goals = final_group_goal_registry.get("goals") or {}
    final_group_goal_count = len(_final_group_goals)
    final_active_group_goal_count = sum(
        1 for _g in _final_group_goals.values() if _g.get("status") == "active"
    )
    final_group_norm_registry = entities.get(GROUP_NORM_REGISTRY_ID) or {}
    _final_group_norms = final_group_norm_registry.get("norms") or {}
    final_group_norm_count = len(_final_group_norms)
    final_active_group_norm_count = sum(
        1 for _n in _final_group_norms.values() if _n.get("status") == "active"
    )
    final_groups = final_association_registry.get("group_candidates") or {}
    final_shared_groups = final_group_state_registry.get("groups") or {}
    final_shared_facts = sum(
        len(group.get("facts") or {})
        for group in final_shared_groups.values()
    )
    final_association_composition = (
        association_capacity_diagnostics(final_association_registry)
        if final_association_registry else {}
    )
    final_group_state_composition = (
        group_state_capacity_diagnostics(final_group_state_registry)
        if final_group_state_registry else {}
    )
    retained_history_composition = {
        "association_recent_evidence_rows": sum(
            len(record.get("recent_evidence") or [])
            for record in (final_association_registry.get("association_records") or {}).values()
        ),
        "association_dissolved_history_rows": len(
            final_association_registry.get("dissolved_history") or []
        ),
        "association_processed_evidence_ids": len(
            final_association_registry.get("processed_evidence_ids") or []
        ),
        "group_support_history_rows": sum(
            len(fact.get("support_history") or [])
            for group in final_shared_groups.values()
            for fact in (group.get("facts") or {}).values()
        ),
        "group_proposal_summary_rows": sum(
            len(group.get("latest_collective_proposals") or [])
            for group in final_shared_groups.values()
        ),
        "group_processed_proposal_keys": len(
            final_group_state_registry.get("processed_proposal_keys") or []
        ),
    }
    replay_matches = replayed_entities == entities
    replay_state_hash = canonical_hash(snapshot_for_hash(
        replayed_entities, ticks, lineage_key,
    ))
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
    final_storage_contents = {}
    final_storage_processed_keys = 0
    for entity_id, entity in sorted(entities.items()):
        if entity.get("type") not in ("storage", "container"):
            continue
        final_storage_contents[entity_id] = dict(entity.get("contents") or {})
        final_storage_processed_keys += len(entity.get("collective_processed_keys") or [])
    stage7c["final_storage_contents"] = final_storage_contents
    stage7c["final_storage_processed_keys"] = final_storage_processed_keys
    stage7c["rejected_by_reason"] = _counter_dict(stage7c["rejected_by_reason"])
    # Bound retained participant-order samples for report size
    stage7c["accepted_participant_orders"] = stage7c["accepted_participant_orders"][:32]

    return {
        "seed": seed,
        "scenario_id": scenario_id,
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
            "capacity_rejection_reasons": _counter_dict(capacity_rejections),
            "actions_by_type": _counter_dict(actions_by_type),
            "goals_by_actor": {
                actor_id: sorted(goals) for actor_id, goals in sorted(goals_by_actor.items())
            },
            "decisions_by_kind": _counter_dict(decisions_by_kind),
            "plan_failure_reasons": _counter_dict(plan_failure_reasons),
            "weather_conditions": weather_conditions,
            "final_relationship_count": final_relationships,
            "final_association_record_count": len(
                final_association_registry.get("association_records") or {}
            ),
            "final_group_candidate_count": len(final_groups),
            "final_recognised_group_count": sum(
                1 for candidate in final_groups.values()
                if candidate.get("recognition_state") == "recognised"
            ),
            "final_weakening_group_count": sum(
                1 for candidate in final_groups.values()
                if candidate.get("recognition_state") == "weakening"
            ),
            "association_summary_hash": canonical_hash(final_association_registry),
            "final_shared_group_state_count": len(final_shared_groups),
            "final_shared_group_fact_count": final_shared_facts,
            "group_state_summary_hash": canonical_hash(final_group_state_registry),
            "final_group_goal_count": final_group_goal_count,
            "final_active_group_goal_count": final_active_group_goal_count,
            "group_goal_summary_hash": canonical_hash(final_group_goal_registry),
            "final_group_norm_count": final_group_norm_count,
            "final_active_group_norm_count": final_active_group_norm_count,
            "group_norm_summary_hash": canonical_hash(final_group_norm_registry),
            "accepted_event_sequence_hash": canonical_hash(event_hashes),
            "frame_sequence_hash": canonical_hash(frame_hashes),
            "replay_state_hash": replay_state_hash,
            "replay_matches_final_entities": replay_matches,
            "final_current_truth_hash": previous_combined_truth_hash,
            "current_truth_hash_at_tick_320": truth_hash_at_tick_320,
            "useful_truth_changes_after_tick_320": truth_changes_after_320,
            "useful_state_changed_after_tick_320": (
                truth_changes_after_320["combined"] > 0
            ),
            "capacity": {
                "association": {
                    "hard_cap_bytes": ASSOCIATION_LIMITS.proposal_bytes,
                    "operational_target_bytes": ASSOCIATION_LIMITS.payload_target_bytes,
                    "peak_bytes": capacity_peaks["association"]["bytes"],
                    "peak_tick": capacity_peaks["association"]["tick"],
                    "peak_headroom_percent": _headroom_percent(
                        capacity_peaks["association"]["bytes"],
                        ASSOCIATION_LIMITS.proposal_bytes,
                    ),
                    "peak_composition": capacity_peaks["association"]["composition"],
                    "final_composition": final_association_composition,
                },
                "group_state": {
                    "hard_cap_bytes": GROUP_STATE_LIMITS.proposal_bytes,
                    "operational_target_bytes": GROUP_STATE_LIMITS.payload_target_bytes,
                    "peak_bytes": capacity_peaks["group_state"]["bytes"],
                    "peak_tick": capacity_peaks["group_state"]["tick"],
                    "peak_headroom_percent": _headroom_percent(
                        capacity_peaks["group_state"]["bytes"],
                        GROUP_STATE_LIMITS.proposal_bytes,
                    ),
                    "peak_composition": capacity_peaks["group_state"]["composition"],
                    "final_composition": final_group_state_composition,
                },
            },
            "retained_history_composition": retained_history_composition,
            "commitment_statuses": _counter_dict(final_commitments),
            "knowledge_provenance": _counter_dict(knowledge_provenance),
            "reported_claim_count": len(reported_claims),
            "false_belief_count": false_beliefs,
            # Must remain zero: actors receive a claim, not hidden narrator truth.
            "deceptive_claim_count": deceptive_claims,
            "contradicted_claim_count": contradicted_claims,
            "resource_depletion": initial_resource_total - final_resource_total,
            "max_state_counts": max_state_counts,
            "stage7c": stage7c,
            "capacity_collective": {
                "processed_keys_peak": capacity_peaks["collective"]["processed_keys"],
                "processed_keys_peak_tick": capacity_peaks["collective"]["tick"],
                "processed_keys_cap": capacity_peaks["collective"]["cap"],
                "processed_keys_headroom_percent": _headroom_percent(
                    capacity_peaks["collective"]["processed_keys"],
                    max(1, capacity_peaks["collective"]["cap"]),
                ),
            },
            "group_collective_domain_enabled": "group_collective" in scenario.enabled_domains,
        },
    }


def _public_report(result: dict) -> dict:
    return {
        "seed": result["seed"],
        "scenario_id": result["scenario_id"],
        "ticks": result["ticks"],
        "final_state_hash": result["final_state_hash"],
        **result["summary"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default="living-agents-stage6")
    parser.add_argument("--scenario", default="living_settlement")
    parser.add_argument("--ticks", type=int, default=320)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--resume-at", type=int)
    parser.add_argument(
        "--debug-assert-fragment-cache", action="store_true",
        help="CORE-PERF-01 Slice B: verify the fragment-cache splice against "
             "the direct canonical_json computation on every accepted event. "
             "Gate/verification use only -- doubles the hashing cost.",
    )
    args = parser.parse_args(argv)
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    baseline = run_living_agent_harness(
        args.seed, ticks=args.ticks, run_id="living-agent-harness-1",
        scenario_id=args.scenario,
        debug_assert_fragment_cache=args.debug_assert_fragment_cache,
    )
    repeat_matches = True
    for index in range(2, args.repeat + 1):
        repeated = run_living_agent_harness(
            args.seed, ticks=args.ticks, run_id=f"living-agent-harness-{index}",
            scenario_id=args.scenario,
            resume_at_tick=args.resume_at,
            debug_assert_fragment_cache=args.debug_assert_fragment_cache,
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
    report["resumed_repeat_at_tick"] = args.resume_at
    report["resume_matches"] = repeat_matches if args.resume_at is not None else None
    print(json.dumps(report, sort_keys=True, indent=2))
    if not repeat_matches:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
