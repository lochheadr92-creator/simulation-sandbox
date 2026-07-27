"""Layer C Social Density Leg 1 organic-reachability census.

Runs the committed ``collective_groups`` scenario without persistence and
measures the STORE_SURPLUS path at the three pre-registered horizons:
1,000, 3,000, and 5,000 ticks.  The probe observes the real candidate builder,
per-tick decision diagnostics, accepted events, and rejected proposals.  It
does not seed behaviour or change canonical state.

The final entity projection retains only a bounded, compact decision history.
This probe therefore tallies full decision receipts while each tick is live and
keeps aggregates plus bounded examples.  Accepted events are replayed as they
arrive but are not accumulated, keeping memory use flat across the long run.

Usage:
  python -m tools._probe_layer_c_social_density <out.json> [ticks] [shadow_food_threshold]
"""
from __future__ import annotations

import copy
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import domains.living_settlement_domain as living_domain
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_goal_contracts import GROUP_GOAL_REGISTRY_ID
from domains.group_norm_contracts import GROUP_NORM_REGISTRY_ID
from domains.group_state_contracts import GROUP_STATE_REGISTRY_ID
from scenarios import get_scenario


SEED = "living-agents-stage6"
SCENARIO = "collective_groups"
DEFAULT_TICKS = 5_000
DEFAULT_CHECKPOINTS = (1_000, 3_000, 5_000)
STORE_GOAL = "STORE_SURPLUS"
STORAGE_ACTIONS = frozenset({"store", "retrieve", "access"})
EXAMPLE_LIMIT = 24


def _sorted_counter(counter: Counter) -> dict:
    return {str(key): counter[key] for key in sorted(counter, key=str)}


def _numeric_summary(values: list[int]) -> dict:
    """Return a compact deterministic distribution summary."""
    if not values:
        return {"count": 0, "min": None, "p25": None, "median": None,
                "p75": None, "p90": None, "max": None, "mean": None}
    ordered = sorted(int(value) for value in values)

    def percentile(fraction: float) -> int:
        index = round((len(ordered) - 1) * fraction)
        return ordered[index]

    return {
        "count": len(ordered),
        "min": ordered[0],
        "p25": percentile(0.25),
        "median": percentile(0.50),
        "p75": percentile(0.75),
        "p90": percentile(0.90),
        "max": ordered[-1],
        "mean": round(sum(ordered) / len(ordered), 3),
    }


def _shannon_entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    return round(-sum(
        (count / total) * math.log2(count / total)
        for count in counter.values() if count > 0
    ), 6)


def _event_action(event: dict) -> str | None:
    return (event.get("living_action") or {}).get("action_type")


def _event_goal_id(event: dict) -> str | None:
    return (event.get("living_action") or {}).get("causal_goal_id")


def _proposal_goal_id(rejection: dict) -> str | None:
    proposal = rejection.get("proposal_snapshot") or {}
    return (proposal.get("living_action") or {}).get("causal_goal_id")


class SocialDensityCensus:
    """Cumulative, non-canonical measurements for one probe run."""

    def __init__(self, *, shadow_food_threshold: int | None = None) -> None:
        self.shadow_food_threshold = shadow_food_threshold
        self.shadow_candidates: dict[tuple[int, str], dict] = {}
        self.shadow_opportunities_by_actor = Counter()
        self.shadow_wins_by_actor = Counter()
        self.shadow_actual_winners = Counter()
        self.shadow_score_values: list[int] = []
        self.shadow_actual_candidate_counts: list[int] = []
        self.shadow_actual_minus_store_margins: list[int] = []
        self.gates = Counter()
        self.gates_by_actor: dict[str, Counter] = defaultdict(Counter)
        self.food_histogram = Counter()
        self.visible_storage_histogram = Counter()
        self.visible_shared_storage_ids: set[str] = set()
        self.base_store_candidate_actors: set[str] = set()
        self.postscore_store_candidate_actors: set[str] = set()
        self.selected_store_actors: set[str] = set()
        self.storage_action_actors: set[str] = set()
        self.store_action_actors: set[str] = set()
        self.storage_targets: set[str] = set()
        self.shared_storage_fact_group_ids: set[str] = set()
        self.shared_storage_fact_targets: set[str] = set()
        self.shared_storage_fact_ticks = 0
        self.first_shared_storage_fact_tick: int | None = None
        self.candidate_score_values: list[int] = []
        self.lost_by_values: list[int] = []
        self.winners_when_store_present = Counter()
        self.selected_store_commit_actions = Counter()
        self.selected_store_final_actions = Counter()
        self.selected_store_rejections = Counter()
        self.selected_store_plan_statuses = Counter()
        self.actions_by_type = Counter()
        self.storage_actions_by_type = Counter()
        self.storage_actions_by_resource = Counter()
        self.accepted_by_type = Counter()
        self.rejected_by_reason = Counter()
        self.person_ticks = 0
        self.alive_person_ticks = 0
        self.accepted_event_count = 0
        self.rejected_proposal_count = 0
        self.examples: dict[str, list] = defaultdict(list)

    def _example(self, kind: str, row: dict) -> None:
        if len(self.examples[kind]) < EXAMPLE_LIMIT:
            self.examples[kind].append(row)

    def observe_candidate_build(
        self,
        *,
        actor_id: str,
        entity: dict,
        delta: dict,
        tick: int,
        candidates: list[dict],
        state: dict | None = None,
        knowledge: dict | None = None,
    ) -> None:
        storages = living_domain._observation_map(delta, "storage")
        shared = [
            storage_id
            for storage_id, observation in sorted(storages.items())
            if (observation.get("properties") or {}).get("access")
            in ("public", "shared")
        ]
        food = int((entity.get("carried_resources") or {}).get("food", 0) or 0)
        food_eligible = food >= 3
        storage_visible = bool(shared)
        joint_eligible = storage_visible and food_eligible
        candidate_returned = any(row.get("goal") == STORE_GOAL for row in candidates)

        self.gates["decision_opportunities"] += 1
        self.gates_by_actor[actor_id]["decision_opportunities"] += 1
        self.food_histogram[food] += 1
        self.visible_storage_histogram[len(shared)] += 1
        self.visible_shared_storage_ids.update(shared)
        for name, value in (
            ("shared_storage_visible", storage_visible),
            ("food_ge_3", food_eligible),
            ("joint_eligible", joint_eligible),
            ("base_store_candidate_returned", candidate_returned),
        ):
            if value:
                self.gates[name] += 1
                self.gates_by_actor[actor_id][name] += 1
        if joint_eligible and not candidate_returned:
            self.gates["eligible_but_base_candidate_missing"] += 1
        if candidate_returned:
            self.base_store_candidate_actors.add(actor_id)
        if (
            self.shadow_food_threshold is not None
            and shared
            and food >= self.shadow_food_threshold
            and not candidate_returned
        ):
            storage_id = shared[0]
            observation = storages[storage_id]
            base = living_domain._candidate(
                STORE_GOAL,
                "store",
                1350,
                target_id=storage_id,
                target_pos=living_domain._pos(observation),
                resource_kind="food",
            )
            scored = living_domain.score_goal_candidates(
                [base],
                actor_id=actor_id,
                state=state or {},
                knowledge=knowledge or {},
                tick=tick,
            )[0]
            self.shadow_candidates[(int(tick), actor_id)] = scored
            self.shadow_opportunities_by_actor[actor_id] += 1
            self.shadow_score_values.append(int(scored.get("score_total", 0) or 0))
        if joint_eligible or candidate_returned:
            self._example("eligibility", {
                "tick": int(tick),
                "actor_id": actor_id,
                "food": food,
                "visible_shared_storage_ids": shared,
                "candidate_returned": candidate_returned,
            })

    def observe_tick(
        self,
        *,
        tick: int,
        entities: dict,
        accepted: list[dict],
        rejected: list[dict],
        diagnostics: dict,
    ) -> None:
        people = [entity for entity in entities.values() if entity.get("type") == "person"]
        self.person_ticks += len(people)
        self.alive_person_ticks += sum(1 for entity in people if entity.get("alive", True))
        self.accepted_event_count += len(accepted)
        self.rejected_proposal_count += len(rejected)

        shared_fact_present = False
        group_state = entities.get(GROUP_STATE_REGISTRY_ID) or {}
        for group_id, group in (group_state.get("groups") or {}).items():
            for fact in (group.get("facts") or {}).values():
                if fact.get("category") != "shared_storage":
                    continue
                shared_fact_present = True
                self.shared_storage_fact_group_ids.add(str(group_id))
                if fact.get("target_id"):
                    self.shared_storage_fact_targets.add(str(fact["target_id"]))
        if shared_fact_present:
            self.shared_storage_fact_ticks += 1
            if self.first_shared_storage_fact_tick is None:
                self.first_shared_storage_fact_tick = int(tick)

        accepted_by_actor_goal: dict[tuple[str, str], list[dict]] = defaultdict(list)
        rejected_by_actor_goal: dict[tuple[str, str], list[dict]] = defaultdict(list)

        for event in accepted:
            self.accepted_by_type[str(event.get("event_type"))] += 1
            action_type = _event_action(event)
            if action_type:
                self.actions_by_type[action_type] += 1
            goal_id = _event_goal_id(event)
            actor_id = event.get("entity_id")
            if actor_id and goal_id:
                accepted_by_actor_goal[(actor_id, goal_id)].append(event)
            if action_type in STORAGE_ACTIONS:
                self._observe_storage_event(tick, event, action_type)

        for rejection in rejected:
            reason = str(rejection.get("reason_code"))
            self.rejected_by_reason[reason] += 1
            goal_id = _proposal_goal_id(rejection)
            actor_id = rejection.get("entity_id")
            if actor_id and goal_id:
                rejected_by_actor_goal[(actor_id, goal_id)].append(rejection)

        for actor_id, row in sorted(diagnostics.items()):
            if not actor_id.startswith("person-") or not isinstance(row, dict):
                continue
            candidates = list(row.get("candidates") or [])
            shadow_candidate = self.shadow_candidates.pop((int(tick), actor_id), None)
            if shadow_candidate is not None:
                shadow_winner = living_domain.select_goal([*candidates, shadow_candidate])
                actual_winner = str(row.get("selected_goal") or "UNKNOWN")
                actual_score = int(
                    ((row.get("decision_receipt") or {}).get("selected_score", 0)) or 0
                )
                shadow_score = int(shadow_candidate.get("score_total", 0) or 0)
                self.shadow_actual_winners[actual_winner] += 1
                self.shadow_actual_candidate_counts.append(len(candidates))
                self.shadow_actual_minus_store_margins.append(actual_score - shadow_score)
                shadow_would_win = shadow_winner.get("goal") == STORE_GOAL
                if shadow_would_win:
                    self.shadow_wins_by_actor[actor_id] += 1
                self._example("shadow_store_candidate", {
                    "tick": int(tick),
                    "actor_id": actor_id,
                    "actual_winner": actual_winner,
                    "actual_score": actual_score,
                    "shadow_store_score": shadow_score,
                    "shadow_would_win": shadow_would_win,
                })
            store_candidate = next(
                (candidate for candidate in candidates if candidate.get("goal") == STORE_GOAL),
                None,
            )
            if store_candidate is None:
                continue

            self.gates["postscore_store_candidate_present"] += 1
            self.postscore_store_candidate_actors.add(actor_id)
            score = int(store_candidate.get("score_total", store_candidate.get("score", 0)) or 0)
            self.candidate_score_values.append(score)
            winner = str(row.get("selected_goal") or "UNKNOWN")
            self.winners_when_store_present[winner] += 1

            receipt = row.get("decision_receipt") or {}
            selected_goal_id = receipt.get("selected_goal_id") or row.get("goal_id")
            if winner != STORE_GOAL:
                alternative = next(
                    (item for item in (receipt.get("rejected_alternatives") or [])
                     if item.get("goal") == STORE_GOAL),
                    None,
                )
                selected_score = int(receipt.get("selected_score", 0) or 0)
                lost_by = int((alternative or {}).get("lost_by", selected_score - score) or 0)
                self.lost_by_values.append(lost_by)
                self._example("candidate_losses", {
                    "tick": int(tick), "actor_id": actor_id,
                    "winner": winner, "winner_score": selected_score,
                    "store_score": score, "lost_by": lost_by,
                })
                continue

            self.gates["store_selected"] += 1
            self.selected_store_actors.add(actor_id)
            accepted_rows = accepted_by_actor_goal.get((actor_id, selected_goal_id), [])
            rejected_rows = rejected_by_actor_goal.get((actor_id, selected_goal_id), [])
            if accepted_rows:
                for event in accepted_rows:
                    action_type = _event_action(event) or "unknown"
                    self.selected_store_commit_actions[action_type] += 1
                    actor_update = (
                        ((event.get("mutation") or {}).get("entity_updates") or {})
                        .get(actor_id, {})
                    )
                    plan = actor_update.get("plan") or {}
                    self.selected_store_plan_statuses[str(plan.get("status") or "unknown")] += 1
                self.gates["selected_store_proposal_accepted"] += 1
            elif rejected_rows:
                self.gates["selected_store_proposal_rejected"] += 1
                for rejection in rejected_rows:
                    self.selected_store_rejections[str(rejection.get("reason_code"))] += 1
            else:
                self.gates["selected_store_without_commit_record"] += 1

            final_action = ((entities.get(actor_id) or {}).get("action") or {}).get("type")
            self.selected_store_final_actions[str(final_action or "none")] += 1
            self._example("selected_store_paths", {
                "tick": int(tick), "actor_id": actor_id,
                "selected_goal_id": selected_goal_id,
                "accepted_action_types": [
                    _event_action(event) for event in accepted_rows
                ],
                "rejection_reasons": [
                    rejection.get("reason_code") for rejection in rejected_rows
                ],
                "final_action_type": final_action,
            })

        for key in [key for key in self.shadow_candidates if key[0] <= int(tick)]:
            self.shadow_candidates.pop(key, None)

    def _observe_storage_event(self, tick: int, event: dict, action_type: str) -> None:
        actor_id = str(event.get("entity_id"))
        actor_update = (
            ((event.get("mutation") or {}).get("entity_updates") or {})
            .get(actor_id, {})
        )
        action = actor_update.get("action") or {}
        targets = list(action.get("target_entity_ids") or [])
        transfer = (event.get("living_action") or {}).get("resource_transfer") or {}
        resource_kind = str(transfer.get("resource_kind") or "none")

        self.storage_actions_by_type[action_type] += 1
        self.storage_actions_by_resource[resource_kind] += 1
        self.storage_action_actors.add(actor_id)
        self.storage_targets.update(targets)
        if action_type == "store":
            self.store_action_actors.add(actor_id)
        self._example("storage_actions", {
            "tick": int(tick), "actor_id": actor_id, "action_type": action_type,
            "targets": targets, "resource_kind": resource_kind,
            "quantity": transfer.get("quantity"),
        })

    def classify(self) -> str:
        if self.storage_actions_by_type["store"]:
            return "STORE_ORGANICALLY_REACHABLE"
        if self.gates["store_selected"]:
            if self.gates["selected_store_proposal_rejected"]:
                return "C_STORE_SELECTED_BUT_PROPOSAL_REJECTED"
            if self.selected_store_commit_actions["move"]:
                return "C_STORE_SELECTED_BUT_ONLY_MOVE_COMMITS"
            return "C_STORE_SELECTED_BUT_NO_STORE_COMMITS"
        if self.gates["postscore_store_candidate_present"]:
            return "B_STORE_CANDIDATE_ALWAYS_LOSES"
        if self.gates["base_store_candidate_returned"]:
            return "A_BASE_CANDIDATE_DROPPED_BEFORE_SELECTION"
        if self.gates["joint_eligible"]:
            return "A_ELIGIBLE_BUT_BASE_CANDIDATE_MISSING"
        if self.gates["shared_storage_visible"] == 0:
            return "A_NO_SHARED_STORAGE_VISIBLE"
        if self.gates["food_ge_3"] == 0:
            return "A_FOOD_NEVER_REACHES_3"
        return "A_STORAGE_VISIBILITY_AND_FOOD_NEVER_COINCIDE"

    def metrics(self) -> dict:
        metrics = {
            "causal_classification": self.classify(),
            "person_ticks": self.person_ticks,
            "alive_person_ticks": self.alive_person_ticks,
            "candidate_gate_counts": _sorted_counter(self.gates),
            "candidate_gate_counts_by_actor": {
                actor_id: _sorted_counter(counter)
                for actor_id, counter in sorted(self.gates_by_actor.items())
            },
            "carried_food_histogram_at_decision": _sorted_counter(self.food_histogram),
            "visible_shared_storage_count_histogram": _sorted_counter(
                self.visible_storage_histogram
            ),
            "visible_shared_storage_ids": sorted(self.visible_shared_storage_ids),
            "base_store_candidate_actor_count": len(self.base_store_candidate_actors),
            "postscore_store_candidate_actor_count": len(
                self.postscore_store_candidate_actors
            ),
            "selected_store_actor_count": len(self.selected_store_actors),
            "store_candidate_score_distribution": _numeric_summary(
                self.candidate_score_values
            ),
            "store_candidate_lost_by_distribution": _numeric_summary(
                self.lost_by_values
            ),
            "winners_when_store_candidate_present": _sorted_counter(
                self.winners_when_store_present
            ),
            "selected_store_committed_actions": _sorted_counter(
                self.selected_store_commit_actions
            ),
            "selected_store_final_actions": _sorted_counter(
                self.selected_store_final_actions
            ),
            "selected_store_rejections": _sorted_counter(
                self.selected_store_rejections
            ),
            "selected_store_plan_statuses": _sorted_counter(
                self.selected_store_plan_statuses
            ),
            "accepted_event_count": self.accepted_event_count,
            "rejected_proposal_count": self.rejected_proposal_count,
            "accepted_by_type": _sorted_counter(self.accepted_by_type),
            "rejected_by_reason": _sorted_counter(self.rejected_by_reason),
            "actions_by_type": _sorted_counter(self.actions_by_type),
            "action_type_count": len(self.actions_by_type),
            "action_entropy_bits": _shannon_entropy(self.actions_by_type),
            "storage_actions_by_type": _sorted_counter(self.storage_actions_by_type),
            "storage_actions_by_resource": _sorted_counter(
                self.storage_actions_by_resource
            ),
            "storage_action_actor_count": len(self.storage_action_actors),
            "store_action_actor_count": len(self.store_action_actors),
            "storage_targets": sorted(self.storage_targets),
            "shared_storage_fact_ever_formed": bool(
                self.shared_storage_fact_group_ids
            ),
            "first_shared_storage_fact_tick": self.first_shared_storage_fact_tick,
            "ticks_with_shared_storage_fact": self.shared_storage_fact_ticks,
            "shared_storage_fact_group_ids": sorted(
                self.shared_storage_fact_group_ids
            ),
            "shared_storage_fact_targets": sorted(self.shared_storage_fact_targets),
            "examples": {
                kind: rows for kind, rows in sorted(self.examples.items())
            },
        }
        if self.shadow_food_threshold is not None:
            metrics["shadow_store_candidate"] = {
                "food_threshold": self.shadow_food_threshold,
                "joint_opportunity_count": sum(
                    self.shadow_opportunities_by_actor.values()
                ),
                "opportunities_by_actor": _sorted_counter(
                    self.shadow_opportunities_by_actor
                ),
                "would_win_count": sum(self.shadow_wins_by_actor.values()),
                "would_win_by_actor": _sorted_counter(self.shadow_wins_by_actor),
                "distinct_would_win_actor_count": len(self.shadow_wins_by_actor),
                "actual_winners": _sorted_counter(self.shadow_actual_winners),
                "shadow_score_distribution": _numeric_summary(
                    self.shadow_score_values
                ),
                "actual_candidate_count_distribution": _numeric_summary(
                    self.shadow_actual_candidate_counts
                ),
                "actual_minus_shadow_score_distribution": _numeric_summary(
                    self.shadow_actual_minus_store_margins
                ),
            }
        return metrics


def _world_checkpoint(entities: dict) -> dict:
    association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
    groups = association.get("group_candidates") or {}
    group_state = entities.get(GROUP_STATE_REGISTRY_ID) or {}
    shared_groups = group_state.get("groups") or {}
    group_goals = (entities.get(GROUP_GOAL_REGISTRY_ID) or {}).get("goals") or {}
    group_norms = (entities.get(GROUP_NORM_REGISTRY_ID) or {}).get("norms") or {}

    fact_categories = Counter()
    for group in shared_groups.values():
        for fact in (group.get("facts") or {}).values():
            fact_categories[str(fact.get("category"))] += 1

    storages = {
        entity_id: {
            "access": entity.get("access"),
            "contents": dict(entity.get("contents") or {}),
            "collective_processed_key_count": len(
                entity.get("collective_processed_keys") or []
            ),
        }
        for entity_id, entity in sorted(entities.items())
        if entity.get("type") in ("storage", "container")
    }
    people = [entity for entity in entities.values() if entity.get("type") == "person"]
    return {
        "person_count": len(people),
        "alive_person_count": sum(1 for person in people if person.get("alive", True)),
        "death_count": sum(1 for person in people if not person.get("alive", True)),
        "recognised_group_count": sum(
            1 for group in groups.values()
            if group.get("recognition_state") == "recognised"
        ),
        "shared_group_state_count": len(shared_groups),
        "shared_group_fact_categories": _sorted_counter(fact_categories),
        "group_goal_count": len(group_goals),
        "active_group_goal_count": sum(
            1 for goal in group_goals.values() if goal.get("status") == "active"
        ),
        "group_norm_count": len(group_norms),
        "active_group_norm_count": sum(
            1 for norm in group_norms.values() if norm.get("status") == "active"
        ),
        "storages": storages,
    }


def _write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def probe(
    *,
    ticks: int = DEFAULT_TICKS,
    checkpoints: tuple[int, ...] = DEFAULT_CHECKPOINTS,
    output_path: Path | None = None,
    seed: str = SEED,
    scenario_id: str = SCENARIO,
    shadow_food_threshold: int | None = None,
) -> dict:
    checkpoints = tuple(sorted({int(value) for value in checkpoints if 0 < value <= ticks}))
    if ticks not in checkpoints:
        checkpoints = (*checkpoints, ticks)

    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, genesis_rejected, order_index = build_genesis(
        seed, scenario, lineage_key
    )
    valid_parent_ids = {event["id"] for event in genesis}
    replayed_entities: dict = {}
    for event in genesis:
        apply_mutation(replayed_entities, copy.deepcopy(event["mutation"]))
    rng = DeterministicRNG(seed)
    entity_json_cache: dict = {}
    census = SocialDensityCensus(shadow_food_threshold=shadow_food_threshold)
    checkpoint_results: dict[str, dict] = {}
    started = time.perf_counter()

    payload = {
        "status": "in_progress",
        "probe": "layer-c-social-density-leg1-organic-reachability",
        "seed": seed,
        "scenario_id": scenario_id,
        "ticks": int(ticks),
        "checkpoints": list(checkpoints),
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "lineage_key": lineage_key,
        "capture_events": False,
        "shadow_food_threshold": shadow_food_threshold,
        "genesis_rejection_count": len(genesis_rejected),
        "checkpoint_results": checkpoint_results,
    }

    original_builder = living_domain.build_settlement_candidates

    def observed_builder(entity_id, entity, state, knowledge, delta, tick):
        candidates = original_builder(entity_id, entity, state, knowledge, delta, tick)
        census.observe_candidate_build(
            actor_id=entity_id,
            entity=entity,
            delta=delta,
            tick=tick,
            candidates=candidates,
            state=state,
            knowledge=knowledge,
        )
        return candidates

    living_domain.build_settlement_candidates = observed_builder
    try:
        for tick in range(1, ticks + 1):
            accepted, rejected, order_index, diagnostics = run_tick(
                "probe-layer-c-social-density",
                entities,
                world["terrain"],
                tick,
                rng,
                order_index,
                lineage_key,
                scenario.enabled_domains,
                valid_causal_parent_event_ids=valid_parent_ids,
                entity_json_cache=entity_json_cache,
            )
            for event in accepted:
                valid_parent_ids.add(event["id"])
                apply_mutation(replayed_entities, copy.deepcopy(event["mutation"]))
            census.observe_tick(
                tick=tick,
                entities=entities,
                accepted=accepted,
                rejected=rejected,
                diagnostics=diagnostics,
            )

            if tick in checkpoints:
                checkpoint_results[str(tick)] = {
                    "tick": tick,
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                    "final_state_hash": canonical_hash(
                        snapshot_for_hash(entities, tick, lineage_key)
                    ),
                    "replay_matches_entities": replayed_entities == entities,
                    "replay_state_hash": canonical_hash(
                        snapshot_for_hash(replayed_entities, tick, lineage_key)
                    ),
                    "census": census.metrics(),
                    "world": _world_checkpoint(entities),
                }
                payload["last_completed_checkpoint"] = tick
                payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
                if output_path is not None:
                    _write_payload(output_path, payload)
    finally:
        living_domain.build_settlement_candidates = original_builder

    payload["status"] = "complete"
    payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    payload["final_classification"] = census.classify()
    payload["final_state_hash"] = checkpoint_results[str(ticks)]["final_state_hash"]
    payload["replay_matches_entities"] = replayed_entities == entities
    if output_path is not None:
        _write_payload(output_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    output_path = Path(argv[0]) if argv else Path("probe_layer_c_social_density.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    shadow_food_threshold = int(argv[2]) if len(argv) > 2 else None
    checkpoints = tuple(value for value in DEFAULT_CHECKPOINTS if value <= ticks)
    result = probe(
        ticks=ticks,
        checkpoints=checkpoints,
        output_path=output_path,
        shadow_food_threshold=shadow_food_threshold,
    )
    final = result["checkpoint_results"][str(ticks)]
    print(json.dumps({
        "status": result["status"],
        "output_path": str(output_path),
        "ticks": ticks,
        "elapsed_seconds": result["elapsed_seconds"],
        "final_state_hash": result["final_state_hash"],
        "replay_matches_entities": result["replay_matches_entities"],
        "final_classification": result["final_classification"],
        "candidate_gate_counts": final["census"]["candidate_gate_counts"],
        "winners_when_store_candidate_present": final["census"][
            "winners_when_store_candidate_present"
        ],
        "storage_actions_by_type": final["census"]["storage_actions_by_type"],
        "group_goal_count": final["world"]["group_goal_count"],
        "group_norm_count": final["world"]["group_norm_count"],
        "death_count": final["world"]["death_count"],
        "shadow_store_candidate": final["census"].get("shadow_store_candidate"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
