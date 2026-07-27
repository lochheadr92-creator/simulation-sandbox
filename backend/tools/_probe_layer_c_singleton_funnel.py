"""Layer C Social Density Leg 2 -- Session 1 receipts-only C-H funnel census.

Plan: memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md,
Phase 1, "Session 1 -- receipts-only funnel".

WHAT THIS PROBE IS
------------------
It answers the RECURRENCE question for the singleton action family (warn,
share_information, lie, promise, apologise, reconcile, threaten -- plus trade,
measured but flagged, see TRADE_NOTE) by deriving funnel stages C..H from
records the engine already produces:

  * ``diagnostics[actor]["candidates"]``      -- the post-scoring, post-influence
                                                 candidate list
  * ``diagnostics[actor]["decision_receipt"]``-- every candidate with its full
                                                 score components, every
                                                 rejected alternative with
                                                 ``lost_by``, and the tie-break
                                                 rank key
  * ``accepted`` / ``rejected``               -- the committed event stream and
                                                 the commit-pipeline refusals

NEUTRALITY BY CONSTRUCTION
--------------------------
This probe patches NOTHING.  Leg 1's probe monkeypatched
``build_settlement_candidates`` to observe pre-scoring eligibility; that is the
stage A/B surface and it is deliberately NOT built here (it is Session 2 work,
conditional on this run's classification).  Every value read below is already
computed and already returned by ``run_tick`` -- ``diagnostics`` in particular
is discarded by ``tools/living_agent_harness.py`` today.  Reading a returned
value cannot change the computation that produced it.  Nothing this module
receives is ever mutated: examples are deep-copied before they are retained.

WHAT IT CANNOT SEE (stated up front, not discovered later)
----------------------------------------------------------
``build_settlement_candidates`` returns ``candidates[:16]`` in APPEND order
before scoring.  Candidates dropped by that slice never reach a receipt, so
stage C ("generated") is not independently observable from receipts and the
conservation identity ``generated = rejected_before_scoring + scored`` cannot be
closed in Session 1.  It is BOUNDED instead: a decision whose scored list holds
fewer than ``candidate_goals_per_decision`` entries provably lost nothing to
truncation.  ``candidate_cap_saturated_decisions`` counts the remainder exactly,
and ``at_risk_decisions`` per action counts saturated decisions where that
action's candidate is absent -- the only decisions where truncation could have
hidden it.  ``score_goal_candidates`` re-slices to the same cap after sorting,
but its input is already capped, so that second slice is a proven no-op.

Usage:
  python -m tools._probe_layer_c_singleton_funnel <out.json> [ticks] [seed]
"""
from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash, canonical_json
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_goal_contracts import GROUP_GOAL_REGISTRY_ID
from domains.group_norm_contracts import GROUP_NORM_REGISTRY_ID
from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_ID,
    LIMITS as GROUP_STATE_LIMITS,
    group_state_capacity_diagnostics,
)
from domains.living_agent_contracts import LIMITS as LIVING_LIMITS
from scenarios import get_scenario


SEED = "living-agents-stage6"
SCENARIO = "collective_groups"
DEFAULT_TICKS = 3_000
WINDOW = 1_000
EXAMPLE_LIMIT = 24
NEIGHBOURHOOD_LIMIT = 32
NEIGHBOURHOOD_SPAN = 3

# TRADE_NOTE: the canonical plan excludes `trade` from the singleton family
# ("food-coupled, Stage 9 F-A") and lists it under Out of scope.  The session
# prompt named it among the target actions.  Measuring it is free -- it is one
# more key in the same pass -- so it is measured and reported, and flagged in
# the payload so it cannot silently drive a contract.
TARGET_ACTIONS = (
    "warn", "share_information", "lie", "promise",
    "apologise", "reconcile", "threaten", "trade",
)
PLAN_SCOPED_TARGETS = frozenset(TARGET_ACTIONS) - {"trade"}
REFERENCE_ACTIONS = ("cooperate", "repay", "request_help")
TRACKED_ACTIONS = TARGET_ACTIONS + REFERENCE_ACTIONS

# Self-limiting guards read straight out of the committed candidate builder.
# These are recorded as canonical-state OBSERVATIONS, not as stage-B gate
# instrumentation -- `living_action_counts` is ordinary committed entity state.
SELF_CAP = {
    "warn": 2, "lie": 1, "apologise": 1, "reconcile": 1,
    "share_information": 1, "trade": 1, "threaten": 1, "promise": 1,
}


def _sorted_counter(counter) -> dict:
    return {str(key): int(counter[key]) for key in sorted(counter, key=str)}


def _numeric_summary(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "min": None, "p25": None, "median": None,
                "p75": None, "p90": None, "max": None, "mean": None}
    ordered = sorted(int(value) for value in values)

    def percentile(fraction: float) -> int:
        return ordered[round((len(ordered) - 1) * fraction)]

    return {
        "count": len(ordered), "min": ordered[0], "p25": percentile(0.25),
        "median": percentile(0.50), "p75": percentile(0.75),
        "p90": percentile(0.90), "max": ordered[-1],
        "mean": round(sum(ordered) / len(ordered), 4),
    }


def _event_action(event: dict) -> str | None:
    return (event.get("living_action") or {}).get("action_type")


def _event_goal_id(event: dict) -> str | None:
    return (event.get("living_action") or {}).get("causal_goal_id")


def _actor_update(event: dict, actor_id: str) -> dict:
    return ((event.get("mutation") or {}).get("entity_updates") or {}).get(actor_id, {}) or {}


def _event_targets(event: dict, actor_id: str) -> list[str]:
    action = _actor_update(event, actor_id).get("action") or {}
    return [str(value) for value in (action.get("target_entity_ids") or []) if value]


def _candidate_action(candidate: dict) -> str | None:
    action = candidate.get("direct_action_type")
    return str(action) if action else None


class ActionFunnel:
    """Stage C..H tallies for one action type."""

    def __init__(self, action_type: str) -> None:
        self.action_type = action_type
        # C/D -- receipts observe one set; see module docstring.
        self.scored_decisions = 0
        self.scored_decision_actors: set[str] = set()
        self.at_risk_decisions = 0          # cap-saturated AND action absent
        # E
        self.won = 0
        self.lost = 0
        self.lost_by_values: list[int] = []
        self.winners_when_present = Counter()
        self.score_values: list[int] = []
        # F / G
        self.committed = 0
        self.preempted_travel = 0
        self.invalidated_plan_failed = 0
        self.invalidated_builder_error = 0
        self.commit_rejected = 0
        self.other_commit_action = Counter()
        self.no_commit_record = 0
        self.rejection_reasons = Counter()
        self.builder_failure_reasons = Counter()
        # G cross-check (bypass detector) and H
        self.raw_committed_events = 0
        self.committed_ticks: list[int] = []
        self.committed_actors = Counter()
        self.committed_pairs = Counter()

    def conservation(self) -> dict:
        scored_lhs = self.scored_decisions
        scored_rhs = self.lost + self.won
        won_rhs = (
            self.preempted_travel + self.invalidated_plan_failed
            + self.invalidated_builder_error + self.commit_rejected
            + self.committed + sum(self.other_commit_action.values())
            + self.no_commit_record
        )
        return {
            "scored_equals_lost_plus_won": {
                "lhs_scored": scored_lhs, "rhs_lost_plus_won": scored_rhs,
                "balanced": scored_lhs == scored_rhs,
            },
            "won_equals_outcomes": {
                "lhs_won": self.won, "rhs_outcomes": won_rhs,
                "balanced": self.won == won_rhs,
                "note": (
                    "outcomes = preempted_travel + invalidated_plan_failed + "
                    "invalidated_builder_error + commit_rejected + committed + "
                    "other_commit_action + no_commit_record. The plan's 3-term "
                    "form omits commit_rejected/other/no_record; they are kept "
                    "explicit so a non-zero value cannot hide inside 'invalidated'."
                ),
            },
            "committed_equals_raw_event_count": {
                "lhs_resolved_from_decisions": self.committed,
                "rhs_raw_committed_events": self.raw_committed_events,
                "balanced": self.committed == self.raw_committed_events,
                "note": (
                    "BYPASS DETECTOR. A surplus on the right means an action "
                    "reached the committed stream without passing the observed "
                    "decision path -- the plan's 'any bypass is a finding'."
                ),
            },
        }

    def metrics(self) -> dict:
        return {
            "action_type": self.action_type,
            "stage_C_D_scored_decisions": self.scored_decisions,
            "stage_C_D_distinct_actors": len(self.scored_decision_actors),
            "stage_C_truncation_at_risk_decisions": self.at_risk_decisions,
            "stage_E_won": self.won,
            "stage_E_lost": self.lost,
            "stage_F_preempted_travel": self.preempted_travel,
            "stage_F_invalidated_plan_failed": self.invalidated_plan_failed,
            "stage_F_invalidated_builder_error": self.invalidated_builder_error,
            "stage_F_commit_rejected": self.commit_rejected,
            "stage_F_other_commit_action": _sorted_counter(self.other_commit_action),
            "stage_F_no_commit_record": self.no_commit_record,
            "stage_G_committed": self.committed,
            "stage_H_committed_events_in_stream": self.raw_committed_events,
            "committed_ticks": self.committed_ticks[:64],
            "committed_distinct_actors": len(self.committed_actors),
            "committed_by_actor": _sorted_counter(self.committed_actors),
            "committed_distinct_pairs": len(self.committed_pairs),
            "committed_top_pair_count": (
                max(self.committed_pairs.values()) if self.committed_pairs else 0
            ),
            "candidate_score_distribution": _numeric_summary(self.score_values),
            "lost_by_distribution": _numeric_summary(self.lost_by_values),
            "winners_when_candidate_present": _sorted_counter(self.winners_when_present),
            "commit_rejection_reasons": _sorted_counter(self.rejection_reasons),
            "builder_failure_reasons": _sorted_counter(self.builder_failure_reasons),
            "conservation": self.conservation(),
        }


class WindowStats:
    """Per-1,000-tick population, participation and cap context."""

    def __init__(self, index: int) -> None:
        self.index = index
        self.first_tick: int | None = None
        self.last_tick: int | None = None
        self.alive_person_ticks = 0
        self.person_ticks = 0
        self.alive_counts: list[int] = []
        self.committed = Counter()
        self.actors: dict[str, set[str]] = defaultdict(set)
        self.pairs: dict[str, Counter] = defaultdict(Counter)
        self.recognised_groups_last = 0
        self.shared_group_states_last = 0
        self.active_group_goals_last = 0
        self.active_group_norms_last = 0
        self.group_state_bytes_peak = 0
        self.group_state_bytes_peak_tick: int | None = None
        self.group_state_peak_composition: dict = {}
        self.ticks_over_payload_target = 0
        self.rejections = Counter()

    def metrics(self) -> dict:
        rows = {}
        for action in TRACKED_ACTIONS:
            count = int(self.committed[action])
            pairs = self.pairs[action]
            top_pair = max(pairs.values()) if pairs else 0
            rows[action] = {
                "committed_count": count,
                "per_alive_person_tick_rate": (
                    round(count / self.alive_person_ticks, 8)
                    if self.alive_person_ticks else None
                ),
                "unique_actors": len(self.actors[action]),
                "unique_actor_target_pairs": len(pairs),
                "top_pair_count": top_pair,
                "top_pair_share": (
                    round(top_pair / count, 4) if count else None
                ),
                "top_pair": (
                    max(sorted(pairs), key=lambda key: (pairs[key], key)) if pairs else None
                ),
            }
        return {
            "window_index": self.index,
            "tick_range": [self.first_tick, self.last_tick],
            "alive_person_ticks": self.alive_person_ticks,
            "person_ticks": self.person_ticks,
            "alive_population_min": min(self.alive_counts) if self.alive_counts else None,
            "alive_population_max": max(self.alive_counts) if self.alive_counts else None,
            "alive_population_last": self.alive_counts[-1] if self.alive_counts else None,
            "recognised_group_count_last": self.recognised_groups_last,
            "shared_group_state_count_last": self.shared_group_states_last,
            "active_group_goal_count_last": self.active_group_goals_last,
            "active_group_norm_count_last": self.active_group_norms_last,
            "group_state_payload_peak_bytes": self.group_state_bytes_peak,
            "group_state_payload_peak_tick": self.group_state_bytes_peak_tick,
            "group_state_hard_cap_bytes": GROUP_STATE_LIMITS.proposal_bytes,
            "group_state_operational_target_bytes": GROUP_STATE_LIMITS.payload_target_bytes,
            "group_state_ticks_over_operational_target": self.ticks_over_payload_target,
            "group_state_peak_headroom_percent": (
                round(
                    max(0, GROUP_STATE_LIMITS.proposal_bytes - self.group_state_bytes_peak)
                    * 100.0 / GROUP_STATE_LIMITS.proposal_bytes, 3,
                ) if self.group_state_bytes_peak else None
            ),
            "group_state_peak_composition": self.group_state_peak_composition,
            "rejections_by_reason": _sorted_counter(self.rejections),
            "actions": rows,
        }


class SingletonFunnelCensus:
    def __init__(self) -> None:
        self.funnels = {action: ActionFunnel(action) for action in TRACKED_ACTIONS}
        self.windows: dict[int, WindowStats] = {}
        self.alive_person_ticks = 0
        self.person_ticks = 0
        self.decisions_observed = 0
        self.decisions_by_kind = Counter()
        self.accepted_event_count = 0
        self.rejected_proposal_count = 0
        self.accepted_by_type = Counter()
        self.rejected_by_reason = Counter()
        self.actions_by_type = Counter()
        self.candidate_count_values: list[int] = []
        self.candidate_cap_saturated_decisions = 0
        self.roles: dict[str, str] = {}
        self.self_cap_closed_alive_person_ticks = Counter()
        self.self_cap_open_alive_person_ticks = Counter()
        self.animal_alive_ticks = 0
        self.animal_last_alive_tick: int | None = None
        self.recent_committed = deque(maxlen=NEIGHBOURHOOD_SPAN)
        self.neighbourhoods: dict[str, list[dict]] = defaultdict(list)
        self.pending_neighbourhoods: list[dict] = []
        self.examples: dict[str, list] = defaultdict(list)

    # -- helpers ---------------------------------------------------------
    def _window(self, tick: int) -> WindowStats:
        index = (int(tick) - 1) // WINDOW
        window = self.windows.get(index)
        if window is None:
            window = WindowStats(index)
            self.windows[index] = window
        if window.first_tick is None:
            window.first_tick = int(tick)
        window.last_tick = int(tick)
        return window

    def _example(self, kind: str, row: dict) -> None:
        if len(self.examples[kind]) < EXAMPLE_LIMIT:
            self.examples[kind].append(copy.deepcopy(row))

    @staticmethod
    def _event_summary(event: dict) -> dict:
        actor_id = str(event.get("entity_id") or "")
        return {
            "tick": int(event.get("simulation_time") or event.get("requested_time") or 0),
            "event_id": event.get("id"),
            "event_type": event.get("event_type"),
            "actor_id": actor_id,
            "action_type": _event_action(event),
            "causal_goal_id": _event_goal_id(event),
            "targets": _event_targets(event, actor_id),
        }

    # -- main per-tick entry point --------------------------------------
    def observe_tick(self, *, tick: int, entities: dict, accepted: list[dict],
                     rejected: list[dict], diagnostics: dict) -> None:
        window = self._window(tick)

        people = {
            entity_id: entity for entity_id, entity in entities.items()
            if entity.get("type") == "person"
        }
        alive_ids = {
            entity_id for entity_id, entity in people.items()
            if entity.get("alive", True)
        }
        self.person_ticks += len(people)
        self.alive_person_ticks += len(alive_ids)
        window.person_ticks += len(people)
        window.alive_person_ticks += len(alive_ids)
        window.alive_counts.append(len(alive_ids))

        for entity_id, entity in people.items():
            role = entity.get("stage6_role")
            if role and entity_id not in self.roles:
                self.roles[entity_id] = str(role)

        # Canonical-state observation of the self-limiting guards. NOT stage-B
        # instrumentation: `living_action_counts` is ordinary committed state.
        for entity_id in sorted(alive_ids):
            counts = people[entity_id].get("living_action_counts") or {}
            for action, cap in SELF_CAP.items():
                if int(counts.get(action, 0) or 0) >= cap:
                    self.self_cap_closed_alive_person_ticks[action] += 1
                else:
                    self.self_cap_open_alive_person_ticks[action] += 1

        animal = entities.get("animal-threat") or {}
        if animal.get("alive", False):
            self.animal_alive_ticks += 1
            self.animal_last_alive_tick = int(tick)

        # --- committed stream -------------------------------------------
        self.accepted_event_count += len(accepted)
        self.rejected_proposal_count += len(rejected)
        accepted_by_actor_goal: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for event in accepted:
            self.accepted_by_type[str(event.get("event_type"))] += 1
            actor_id = str(event.get("entity_id") or "")
            action_type = _event_action(event)
            goal_id = _event_goal_id(event)
            if action_type:
                self.actions_by_type[action_type] += 1
            if actor_id and goal_id:
                accepted_by_actor_goal[(actor_id, goal_id)].append(event)

            summary = self._event_summary(event)
            summary["tick"] = int(tick)
            for pending in self.pending_neighbourhoods:
                if len(pending["next_events"]) < NEIGHBOURHOOD_SPAN:
                    pending["next_events"].append(summary)
            self.pending_neighbourhoods = [
                pending for pending in self.pending_neighbourhoods
                if len(pending["next_events"]) < NEIGHBOURHOOD_SPAN
            ]

            if action_type in self.funnels:
                funnel = self.funnels[action_type]
                funnel.raw_committed_events += 1
                funnel.committed_ticks.append(int(tick))
                funnel.committed_actors[actor_id] += 1
                targets = _event_targets(event, actor_id)
                target = targets[0] if targets else "none"
                funnel.committed_pairs[f"{actor_id}->{target}"] += 1
                window.committed[action_type] += 1
                window.actors[action_type].add(actor_id)
                window.pairs[action_type][f"{actor_id}->{target}"] += 1
            self.recent_committed.append(summary)

        rejected_by_actor_goal: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for rejection in rejected:
            reason = str(rejection.get("reason_code"))
            self.rejected_by_reason[reason] += 1
            window.rejections[reason] += 1
            proposal = rejection.get("proposal_snapshot") or {}
            goal_id = (proposal.get("living_action") or {}).get("causal_goal_id")
            actor_id = rejection.get("entity_id")
            if actor_id and goal_id:
                rejected_by_actor_goal[(str(actor_id), str(goal_id))].append(rejection)

        # --- receipts ----------------------------------------------------
        for actor_id, row in sorted(diagnostics.items()):
            # Select on a POSITIVE marker, not an id prefix. `run_tick` merges
            # every enabled domain's diagnostics into one dict, and
            # `lifecycle_domain.lifecycle_diag_key` emits "person-000::lifecycle"
            # -- which passes a startswith("person-") test and would be counted
            # as a phantom decision with zero candidates, doubling
            # decisions_observed and corrupting the candidate-count
            # distribution and the cap-saturation rate. `decision_receipt` is
            # written only by living_settlement_domain.activate.
            if not isinstance(row, dict) or "decision_receipt" not in row:
                continue
            self._observe_decision(
                tick=tick, actor_id=str(actor_id), row=row,
                accepted_by_actor_goal=accepted_by_actor_goal,
                rejected_by_actor_goal=rejected_by_actor_goal,
                entities=entities,
            )

        # --- registries / cap context ------------------------------------
        association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
        groups = association.get("group_candidates") or {}
        window.recognised_groups_last = sum(
            1 for group in groups.values()
            if group.get("recognition_state") == "recognised"
        )
        group_state_registry = entities.get(GROUP_STATE_REGISTRY_ID) or {}
        window.shared_group_states_last = len(group_state_registry.get("groups") or {})
        if group_state_registry:
            payload_bytes = len(canonical_json(group_state_registry).encode("utf-8"))
            if payload_bytes > window.group_state_bytes_peak:
                window.group_state_bytes_peak = payload_bytes
                window.group_state_bytes_peak_tick = int(tick)
                # Composition only at a new peak -- it re-serialises, and the
                # cheap length above already decides when a peak happened.
                window.group_state_peak_composition = copy.deepcopy(
                    group_state_capacity_diagnostics(group_state_registry)
                )
            if payload_bytes > GROUP_STATE_LIMITS.payload_target_bytes:
                window.ticks_over_payload_target += 1
        goals = (entities.get(GROUP_GOAL_REGISTRY_ID) or {}).get("goals") or {}
        window.active_group_goals_last = sum(
            1 for goal in goals.values() if goal.get("status") == "active"
        )
        norms = (entities.get(GROUP_NORM_REGISTRY_ID) or {}).get("norms") or {}
        window.active_group_norms_last = sum(
            1 for norm in norms.values() if norm.get("status") == "active"
        )

    # -- one actor's decision at one tick -------------------------------
    def _observe_decision(self, *, tick: int, actor_id: str, row: dict,
                          accepted_by_actor_goal: dict, rejected_by_actor_goal: dict,
                          entities: dict) -> None:
        candidates = list(row.get("candidates") or [])
        receipt = row.get("decision_receipt") or {}
        decision_kind = str(row.get("decision_kind") or "unknown")
        self.decisions_observed += 1
        self.decisions_by_kind[decision_kind] += 1
        self.candidate_count_values.append(len(candidates))
        saturated = len(candidates) >= LIVING_LIMITS.candidate_goals_per_decision
        if saturated:
            self.candidate_cap_saturated_decisions += 1

        selected_goal_id = receipt.get("selected_goal_id") or row.get("goal_id")
        selected_goal = str(row.get("selected_goal") or receipt.get("selected_goal") or "")
        selected_score = int(receipt.get("selected_score", 0) or 0)
        ordered = list(receipt.get("candidate_goals") or candidates)
        selected_action = next(
            (
                _candidate_action(candidate) for candidate in ordered
                if candidate.get("goal_id") == selected_goal_id
            ),
            None,
        )
        rejected_alternatives = {
            str(item.get("goal_id")): item
            for item in (receipt.get("rejected_alternatives") or [])
        }

        present_actions = {}
        for candidate in ordered:
            action = _candidate_action(candidate)
            if action in self.funnels:
                present_actions.setdefault(action, candidate)

        for action, funnel in self.funnels.items():
            if action not in present_actions:
                if saturated:
                    funnel.at_risk_decisions += 1
                continue
            candidate = present_actions[action]
            funnel.scored_decisions += 1
            funnel.scored_decision_actors.add(actor_id)
            funnel.score_values.append(
                int(candidate.get("score_total", candidate.get("score", 0)) or 0)
            )
            funnel.winners_when_present[selected_goal or "UNKNOWN"] += 1

            if action != selected_action:
                funnel.lost += 1
                alternative = rejected_alternatives.get(str(candidate.get("goal_id")))
                lost_by = int(
                    (alternative or {}).get(
                        "lost_by",
                        selected_score - int(
                            candidate.get("score_total", candidate.get("score", 0)) or 0
                        ),
                    ) or 0
                )
                funnel.lost_by_values.append(lost_by)
                self._example(f"lost:{action}", {
                    "tick": int(tick), "actor_id": actor_id,
                    "winner_goal": selected_goal, "winner_score": selected_score,
                    "candidate_goal": candidate.get("goal"),
                    "candidate_score": candidate.get("score_total"),
                    "lost_by": lost_by,
                })
                continue

            funnel.won += 1
            self._resolve_won(
                funnel=funnel, action=action, tick=tick, actor_id=actor_id,
                selected_goal_id=str(selected_goal_id or ""), receipt=receipt,
                ordered=ordered, decision_kind=decision_kind,
                accepted_by_actor_goal=accepted_by_actor_goal,
                rejected_by_actor_goal=rejected_by_actor_goal,
                entities=entities,
            )

    def _resolve_won(self, *, funnel: ActionFunnel, action: str, tick: int,
                     actor_id: str, selected_goal_id: str, receipt: dict,
                     ordered: list, decision_kind: str,
                     accepted_by_actor_goal: dict, rejected_by_actor_goal: dict,
                     entities: dict) -> None:
        accepted_rows = accepted_by_actor_goal.get((actor_id, selected_goal_id), [])
        rejected_rows = rejected_by_actor_goal.get((actor_id, selected_goal_id), [])
        outcome = "no_commit_record"
        committed_action = None

        if accepted_rows:
            event = accepted_rows[0]
            committed_action = _event_action(event)
            actor_update = _actor_update(event, actor_id)
            plan = actor_update.get("plan") or {}
            failure_reason = plan.get("failure_reason")
            if committed_action == action:
                funnel.committed += 1
                outcome = "committed"
            elif committed_action == "move":
                funnel.preempted_travel += 1
                outcome = "preempted_travel"
            elif failure_reason:
                funnel.invalidated_builder_error += 1
                funnel.builder_failure_reasons[str(failure_reason)] += 1
                outcome = "invalidated_builder_error"
            elif decision_kind == "failed_plan_replan":
                funnel.invalidated_plan_failed += 1
                outcome = "invalidated_plan_failed"
            else:
                funnel.other_commit_action[str(committed_action)] += 1
                outcome = f"other:{committed_action}"
        elif rejected_rows:
            funnel.commit_rejected += 1
            outcome = "commit_rejected"
            for rejection in rejected_rows:
                funnel.rejection_reasons[str(rejection.get("reason_code"))] += 1
        else:
            funnel.no_commit_record += 1

        self._example(f"won:{action}", {
            "tick": int(tick), "actor_id": actor_id, "outcome": outcome,
            "committed_action": committed_action, "decision_kind": decision_kind,
        })

        if outcome == "committed" and len(self.neighbourhoods[action]) < NEIGHBOURHOOD_LIMIT:
            event = accepted_rows[0]
            targets = _event_targets(event, actor_id)
            record = {
                "action_type": action,
                "tick": int(tick),
                "actor_id": actor_id,
                "actor_role": self.roles.get(actor_id),
                "target_ids": targets,
                "decision_kind": decision_kind,
                "previous_committed_events": [
                    copy.deepcopy(item) for item in list(self.recent_committed)
                ],
                "competing_candidates": [
                    {
                        "goal": item.get("goal"),
                        "action_type": _candidate_action(item),
                        "score_total": item.get("score_total"),
                        "knowledge_confidence": item.get("knowledge_confidence"),
                        "goal_id": item.get("goal_id"),
                    }
                    for item in ordered
                ],
                "arbitration": {
                    "selected_goal_id": receipt.get("selected_goal_id"),
                    "selected_goal": receipt.get("selected_goal"),
                    "selected_score": receipt.get("selected_score"),
                    "tie_break": copy.deepcopy(receipt.get("tie_break") or {}),
                    "rejected_alternatives": copy.deepcopy(
                        receipt.get("rejected_alternatives") or []
                    )[:16],
                },
                "commit_result": {
                    "event_id": event.get("id"),
                    "event_type": event.get("event_type"),
                    "committed_action": _event_action(event),
                },
                "next_events": [],
            }
            self.neighbourhoods[action].append(record)
            self.pending_neighbourhoods.append(record)

    # -- output ----------------------------------------------------------
    def metrics(self) -> dict:
        return {
            "decisions_observed": self.decisions_observed,
            "decisions_by_kind": _sorted_counter(self.decisions_by_kind),
            "person_ticks": self.person_ticks,
            "alive_person_ticks": self.alive_person_ticks,
            "accepted_event_count": self.accepted_event_count,
            "rejected_proposal_count": self.rejected_proposal_count,
            "accepted_by_type": _sorted_counter(self.accepted_by_type),
            "rejected_by_reason": _sorted_counter(self.rejected_by_reason),
            "actions_by_type": _sorted_counter(self.actions_by_type),
            "candidate_count_distribution": _numeric_summary(self.candidate_count_values),
            "candidate_goals_per_decision_cap": LIVING_LIMITS.candidate_goals_per_decision,
            "candidate_cap_saturated_decisions": self.candidate_cap_saturated_decisions,
            "roles": dict(sorted(self.roles.items())),
            "self_cap_closed_alive_person_ticks": _sorted_counter(
                self.self_cap_closed_alive_person_ticks
            ),
            "self_cap_open_alive_person_ticks": _sorted_counter(
                self.self_cap_open_alive_person_ticks
            ),
            "self_cap_values": dict(sorted(SELF_CAP.items())),
            "animal_threat_alive_ticks": self.animal_alive_ticks,
            "animal_threat_last_alive_tick": self.animal_last_alive_tick,
            "target_actions": list(TARGET_ACTIONS),
            "plan_scoped_target_actions": sorted(PLAN_SCOPED_TARGETS),
            "reference_actions": list(REFERENCE_ACTIONS),
            "funnels": {
                action: self.funnels[action].metrics() for action in TRACKED_ACTIONS
            },
            "windows": [
                self.windows[index].metrics() for index in sorted(self.windows)
            ],
            "causal_neighbourhoods": {
                action: rows for action, rows in sorted(self.neighbourhoods.items())
            },
            "examples": {kind: rows for kind, rows in sorted(self.examples.items())},
        }


def _write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    temporary.replace(path)


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = SCENARIO, output_path: Path | None = None,
          run_id: str = "probe-layer-c-singleton-funnel") -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, genesis_rejected, order_index = build_genesis(
        seed, scenario, lineage_key,
    )
    valid_parent_ids = {event["id"] for event in genesis}
    replayed_entities: dict = {}
    for event in genesis:
        apply_mutation(replayed_entities, copy.deepcopy(event["mutation"]))
    rng = DeterministicRNG(seed)
    entity_json_cache: dict = {}
    census = SingletonFunnelCensus()
    checkpoints: dict[str, dict] = {}
    started = time.perf_counter()

    payload = {
        "status": "in_progress",
        "probe": "layer-c-social-density-leg2-session1-receipts-funnel",
        "plan": "memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md",
        "seed": seed,
        "scenario_id": scenario_id,
        "ticks": int(ticks),
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "lineage_key": lineage_key,
        "instrumentation": {
            "monkeypatched_functions": [],
            "reads_only": [
                "run_tick accepted", "run_tick rejected", "run_tick diagnostics",
                "entities (read-only)",
            ],
            "stage_A_B_probes_built": False,
            "note": (
                "Session 1 is receipts-only. Stage C is not independently "
                "observable (builder truncates to the candidate cap before any "
                "receipt exists); it is bounded by "
                "candidate_cap_saturated_decisions and per-action "
                "stage_C_truncation_at_risk_decisions."
            ),
        },
        "trade_note": (
            "The canonical plan excludes `trade` from the singleton family "
            "(food-coupled, Stage 9 F-A) and lists it Out of scope. It is "
            "measured here because measuring is free, and flagged so it cannot "
            "silently drive a contract."
        ),
        "genesis_rejection_count": len(genesis_rejected),
        "checkpoints": checkpoints,
    }

    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, diagnostics = run_tick(
            run_id, entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
            entity_json_cache=entity_json_cache,
        )
        for event in accepted:
            valid_parent_ids.add(event["id"])
            apply_mutation(replayed_entities, copy.deepcopy(event["mutation"]))
        census.observe_tick(
            tick=tick, entities=entities, accepted=accepted,
            rejected=rejected, diagnostics=diagnostics,
        )
        if tick % WINDOW == 0 or tick == ticks:
            checkpoints[str(tick)] = {
                "tick": int(tick),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "final_state_hash": canonical_hash(
                    snapshot_for_hash(entities, tick, lineage_key)
                ),
                "replay_state_hash": canonical_hash(
                    snapshot_for_hash(replayed_entities, tick, lineage_key)
                ),
                "replay_matches_entities": replayed_entities == entities,
            }
            payload["last_completed_checkpoint"] = int(tick)
            payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            if output_path is not None:
                _write_payload(output_path, payload)

    payload["status"] = "complete"
    payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    payload["final_state_hash"] = checkpoints[str(ticks)]["final_state_hash"]
    payload["replay_matches_entities"] = replayed_entities == entities
    payload["census"] = census.metrics()
    if output_path is not None:
        _write_payload(output_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    output_path = Path(argv[0]) if argv else Path("probe_layer_c_singleton_funnel.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    seed = argv[2] if len(argv) > 2 else SEED
    result = probe(ticks=ticks, seed=seed, output_path=output_path)
    census = result["census"]
    summary = {
        "status": result["status"],
        "output_path": str(output_path),
        "seed": seed,
        "ticks": ticks,
        "elapsed_seconds": result["elapsed_seconds"],
        "final_state_hash": result["final_state_hash"],
        "replay_matches_entities": result["replay_matches_entities"],
        "decisions_observed": census["decisions_observed"],
        "candidate_cap_saturated_decisions": census["candidate_cap_saturated_decisions"],
        "funnel_headline": {
            action: {
                "scored": census["funnels"][action]["stage_C_D_scored_decisions"],
                "won": census["funnels"][action]["stage_E_won"],
                "committed": census["funnels"][action]["stage_G_committed"],
                "events": census["funnels"][action]["stage_H_committed_events_in_stream"],
                "balanced": all(
                    check["balanced"]
                    for check in census["funnels"][action]["conservation"].values()
                ),
            }
            for action in TRACKED_ACTIONS
        },
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
