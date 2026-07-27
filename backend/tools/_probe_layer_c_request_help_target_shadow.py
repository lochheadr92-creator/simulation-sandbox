"""Layer C Social Density Leg 2 — R1 target-rule shadow (N derivation).

Executes step 2c of the pre-registration committed at `a1a0ea68`
(`memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md`, §Phase 2
"SELECTED CANDIDATE"). The rule under test was pre-registered BEFORE this file
existed and is NOT re-chosen here.

PRE-REGISTERED RULE — R1
------------------------
"nearest visible person, tie-break lowest id":

    argmin over observed persons of (observation["distance"], observed_subject_id)

`distance` is already computed by `perceive_living`
(`living_agent_cognition.py:240`); this probe reads it and invents nothing.
`perceive_living` never includes the observer in its own observations
(`:183-184`), so self-selection is impossible by construction.

WHAT THIS PROBE DOES
--------------------
SHADOW ONLY. At every decision where `REQUEST_HELP` was ACTUALLY generated, it
additionally computes which person R1 *would* have selected, logs it, and
**never uses it**. The real candidate list is returned untouched, so the run is
the unmodified baseline trajectory.

NEUTRALITY — VERIFIED, NOT ASSUMED
----------------------------------
The probe re-derives its own `final_state_hash` and compares against the
committed unmodified Phase 3 runs at the same seed/scenario/horizon:

    seed living-agents-stage6      @1200 -> 4efe6c5080704633fd5806e70ee9560b79a7294664caca0d5228cd3e108d2a21
    seed living-agents-stage6-alt  @1200 -> 8d900c97dbf349ed0ff583003963d4c9367bb836f43a31d91bb1bc33014669ca

Byte equality proves the shadow inert over exactly the measured window. A
mismatch is a STOP.

N DERIVATION (pre-registered method, number NOT chosen here)
-----------------------------------------------------------
Per 1,000-tick window, count distinct shadow-selected persons.
  N                     := MINIMUM of that count across all windows and BOTH seeds
  concentration ceiling := MAXIMUM shadow top-person share across windows/seeds
  FAIL                  := any window with distinct shadow-selected persons <= 3

The cross-seed MIN/MAX are computed by the caller after both runs; this module
emits the per-window inputs and its own single-run summary.

Usage:
  python -m tools._probe_layer_c_request_help_target_shadow <out.json> [ticks] [seed]
"""
from __future__ import annotations

import copy
import json
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
from scenarios import get_scenario


SEED = "living-agents-stage6"
SCENARIO = "collective_groups"
DEFAULT_TICKS = 1_200
WINDOW = 1_000
CHECKPOINT_EVERY = 250
EXAMPLE_LIMIT = 32
REQUEST_GOAL = "REQUEST_HELP"

# Committed unmodified Phase 3 runs, same scenario/horizon.
BASELINE_HASHES_1200 = {
    "living-agents-stage6": "4efe6c5080704633fd5806e70ee9560b79a7294664caca0d5228cd3e108d2a21",
    "living-agents-stage6-alt": "8d900c97dbf349ed0ff583003963d4c9367bb836f43a31d91bb1bc33014669ca",
}


def _sorted_counter(counter) -> dict:
    return {str(k): int(counter[k]) for k in sorted(counter, key=str)}


def _numeric_summary(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None, "mean": None}
    o = sorted(int(v) for v in values)
    return {
        "count": len(o), "min": o[0], "median": o[round((len(o) - 1) * 0.5)],
        "max": o[-1], "mean": round(sum(o) / len(o), 4),
    }


def _r1_select(people: dict) -> tuple[str | None, int | None, list[str]]:
    """Pre-registered R1: argmin (distance, subject_id).

    Returns (selected_id, min_distance, nearest_cohort_ids). The COHORT is
    returned, not merely its size: the cohort-min vs global-min decomposition
    needs membership, and an earlier revision recorded only the count.
    """
    if not people:
        return None, None, []
    best_distance = min(
        int(obs.get("distance", 10 ** 9)) for obs in people.values()
    )
    cohort = sorted(
        str(pid) for pid, obs in people.items()
        if int(obs.get("distance", 10 ** 9)) == best_distance
    )
    # R1's tie-break is lowest id WITHIN the nearest cohort.
    return cohort[0], best_distance, cohort


class TargetShadowCensus:
    def __init__(self) -> None:
        self.request_decisions = 0
        self.actual_by_person = Counter()
        self.shadow_by_person = Counter()
        self.divergent = 0
        self.tie_decisions = 0
        self.actual_distance: list[int] = []
        self.shadow_distance: list[int] = []
        self.visible_count: list[int] = []
        self.window_actual: dict[int, Counter] = defaultdict(Counter)
        self.window_shadow: dict[int, Counter] = defaultdict(Counter)
        self.examples: list[dict] = []
        # --- cohort-min vs global-min decomposition ---
        # How much of R1's widening is DISTANCE, and how much is still the
        # lowest-id tie-break operating inside the nearest cohort?
        self.cohort_size_hist = Counter()
        self.decomp = Counter()
        self.cohort_union_persons: set[str] = set()
        self.window_cohort_union: dict[int, set[str]] = defaultdict(set)
        self.cohort_member_appearances = Counter()

    def observe(self, *, actor_id: str, delta: dict, tick: int, candidates: list) -> None:
        request = next(
            (c for c in candidates if c.get("goal") == REQUEST_GOAL), None,
        )
        if request is None:
            return
        people = living_domain._observation_map(delta, "person")
        actual_id = request.get("target_entity_id")
        if not actual_id:
            return
        shadow_id, shadow_distance, cohort = _r1_select(people)
        if shadow_id is None:
            return
        ties = len(cohort)

        actual_obs = people.get(str(actual_id)) or {}
        actual_distance = int(actual_obs.get("distance", -1))
        window = (int(tick) - 1) // WINDOW

        # DECOMPOSITION. `global_min_id` is the baseline rule's pick (lowest id
        # over ALL visible); `shadow_id` is the lowest id within the NEAREST
        # cohort. Comparing them separates distance-driven change from
        # tie-break-driven change.
        global_min_id = min(str(pid) for pid in people)
        global_min_in_cohort = global_min_id in cohort
        self.cohort_size_hist[ties] += 1
        self.cohort_union_persons.update(cohort)
        self.window_cohort_union[window].update(cohort)
        for member in cohort:
            self.cohort_member_appearances[member] += 1
        if ties == 1:
            bucket = ("unique_nearest_same_as_global_min" if shadow_id == global_min_id
                      else "unique_nearest_differs_from_global_min")
        elif global_min_in_cohort:
            # The distance filter kept the baseline target, and the lowest-id
            # tie-break then re-selected it: R1 reproduces baseline here.
            bucket = "tied_global_min_in_cohort_tiebreak_reproduces_baseline"
        else:
            bucket = "tied_global_min_excluded_distance_did_the_work"
        self.decomp[bucket] += 1

        self.request_decisions += 1
        self.actual_by_person[str(actual_id)] += 1
        self.shadow_by_person[shadow_id] += 1
        self.window_actual[window][str(actual_id)] += 1
        self.window_shadow[window][shadow_id] += 1
        self.visible_count.append(len(people))
        if actual_distance >= 0:
            self.actual_distance.append(actual_distance)
        self.shadow_distance.append(int(shadow_distance))
        if ties > 1:
            self.tie_decisions += 1
        if shadow_id != str(actual_id):
            self.divergent += 1
            if len(self.examples) < EXAMPLE_LIMIT:
                self.examples.append({
                    "tick": int(tick), "requester": actor_id,
                    "actual_target": str(actual_id), "actual_distance": actual_distance,
                    "shadow_target": shadow_id, "shadow_distance": int(shadow_distance),
                    "visible_person_count": len(people), "tie_count": ties,
                    "nearest_cohort": list(cohort),
                    "global_min_id": global_min_id,
                    "global_min_in_cohort": global_min_in_cohort,
                })

    @staticmethod
    def _window_row(index: int, counter: Counter) -> dict:
        total = sum(counter.values())
        top = max(counter.values()) if counter else 0
        return {
            "window_index": index,
            "selections": total,
            "distinct_persons": len(counter),
            "by_person": _sorted_counter(counter),
            "top_person": (
                max(sorted(counter), key=lambda k: (counter[k], k)) if counter else None
            ),
            "top_person_count": top,
            "top_person_share": round(top / total, 4) if total else None,
        }

    def metrics(self) -> dict:
        windows = sorted(set(self.window_actual) | set(self.window_shadow))
        actual_rows = [self._window_row(i, self.window_actual[i]) for i in windows]
        shadow_rows = [self._window_row(i, self.window_shadow[i]) for i in windows]
        shadow_distincts = [r["distinct_persons"] for r in shadow_rows]
        shadow_shares = [r["top_person_share"] for r in shadow_rows if r["top_person_share"] is not None]
        return {
            "pre_registered_rule": "R1 = argmin(observation.distance, observed_subject_id)",
            "request_help_decisions_with_target": self.request_decisions,
            "actual_by_person": _sorted_counter(self.actual_by_person),
            "shadow_by_person": _sorted_counter(self.shadow_by_person),
            "actual_distinct_persons": len(self.actual_by_person),
            "shadow_distinct_persons": len(self.shadow_by_person),
            "divergent_decisions": self.divergent,
            "divergence_rate": (
                round(self.divergent / self.request_decisions, 4)
                if self.request_decisions else None
            ),
            "tie_decisions": self.tie_decisions,
            "visible_person_count_distribution": _numeric_summary(self.visible_count),
            "actual_target_distance_distribution": _numeric_summary(self.actual_distance),
            "shadow_target_distance_distribution": _numeric_summary(self.shadow_distance),
            "windows_actual": actual_rows,
            "windows_shadow": shadow_rows,
            "run_shadow_min_distinct_per_window": min(shadow_distincts) if shadow_distincts else None,
            "run_shadow_max_top_person_share": max(shadow_shares) if shadow_shares else None,
            "run_fail_any_window_le_3": (
                any(d <= 3 for d in shadow_distincts) if shadow_distincts else None
            ),
            # --- cohort-min vs global-min decomposition ---
            "cohort_size_histogram": _sorted_counter(self.cohort_size_hist),
            "decomposition": _sorted_counter(self.decomp),
            "decomposition_note": (
                "unique_nearest_* = cohort of 1, so DISTANCE alone decided and the "
                "tie-break was inert. tied_global_min_in_cohort_... = the distance "
                "filter kept the baseline target and the lowest-id tie-break "
                "re-selected it, so R1 REPRODUCES baseline on those decisions. "
                "tied_global_min_excluded_... = distance removed the baseline target "
                "and the tie-break only resolved a residual set."
            ),
            "cohort_union_distinct_persons": len(self.cohort_union_persons),
            "cohort_union_persons": sorted(self.cohort_union_persons),
            "cohort_member_appearances": _sorted_counter(self.cohort_member_appearances),
            "tiebreak_headroom": {
                "reached_by_R1_lowest_id_tiebreak": len(self.shadow_by_person),
                "reachable_by_any_tiebreak_within_cohorts": len(self.cohort_union_persons),
                "note": (
                    "The gap bounds what a state-derived tie-break (a separately "
                    "pre-registered R2) could buy WITHOUT changing the distance "
                    "filter. Zero gap means the tie-break is not costing reach."
                ),
            },
            "windows_cohort_union_distinct": [
                {"window_index": i, "distinct_persons": len(self.window_cohort_union[i])}
                for i in sorted(self.window_cohort_union)
            ],
            "divergence_examples": self.examples,
        }


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = SCENARIO, output_path: Path | None = None,
          run_id: str = "probe-layer-c-request-help-target-shadow") -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(seed, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    replayed: dict = {}
    for event in genesis:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    rng = DeterministicRNG(seed)
    entity_json_cache: dict = {}
    census = TargetShadowCensus()
    checkpoints: dict[str, dict] = {}
    started = time.perf_counter()

    payload = {
        "status": "in_progress",
        "probe": "layer-c-social-density-leg2-request-help-target-shadow",
        "pre_registration_commit": "a1a0ea68",
        "plan": "memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md",
        "seed": seed, "scenario_id": scenario_id, "ticks": int(ticks), "run_id": run_id,
        "schema_version": SCHEMA_VERSION, "engine_version": ENGINE_VERSION,
        "instrumentation": {
            "monkeypatched_functions": [
                "domains.living_settlement_domain.build_settlement_candidates",
            ],
            "shadow_only": True,
            "note": (
                "The real candidate list is returned untouched; the shadow "
                "selection is computed, logged, and never used."
            ),
        },
        "checkpoints": checkpoints,
    }

    original_builder = living_domain.build_settlement_candidates

    def observed_builder(entity_id, entity, state, knowledge, delta, tick):
        candidates = original_builder(entity_id, entity, state, knowledge, delta, tick)
        census.observe(actor_id=entity_id, delta=delta, tick=tick, candidates=candidates)
        return candidates

    living_domain.build_settlement_candidates = observed_builder
    try:
        for tick in range(1, ticks + 1):
            accepted, _rejected, order_index, _diag = run_tick(
                run_id, entities, world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
                valid_causal_parent_event_ids=valid_parent_ids,
                entity_json_cache=entity_json_cache,
            )
            for event in accepted:
                valid_parent_ids.add(event["id"])
                apply_mutation(replayed, copy.deepcopy(event["mutation"]))
            if tick % CHECKPOINT_EVERY == 0 or tick == ticks:
                checkpoints[str(tick)] = {
                    "tick": int(tick),
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                    "final_state_hash": canonical_hash(
                        snapshot_for_hash(entities, tick, lineage_key)),
                    "replay_matches_entities": replayed == entities,
                }
                payload["last_completed_checkpoint"] = int(tick)
                payload["census"] = census.metrics()
                if output_path is not None:
                    _write(output_path, payload)
    finally:
        living_domain.build_settlement_candidates = original_builder

    final_hash = checkpoints[str(ticks)]["final_state_hash"]
    expected = BASELINE_HASHES_1200.get(seed) if int(ticks) == 1200 else None
    payload["status"] = "complete"
    payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    payload["final_state_hash"] = final_hash
    payload["replay_matches_entities"] = replayed == entities
    payload["census"] = census.metrics()
    payload["neutrality"] = {
        "committed_baseline_hash": expected,
        "this_run_final_state_hash": final_hash,
        "comparable": expected is not None,
        "shadow_is_inert": (final_hash == expected) if expected else None,
        "verdict": (
            "NEUTRAL" if expected and final_hash == expected
            else ("NOT_COMPARABLE" if not expected else "NOT_NEUTRAL")
        ),
    }
    if output_path is not None:
        _write(output_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[0]) if argv else Path("probe_request_help_target_shadow.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    seed = argv[2] if len(argv) > 2 else SEED
    result = probe(ticks=ticks, seed=seed, output_path=out)
    c = result["census"]
    print(json.dumps({
        "status": result["status"], "seed": seed, "ticks": ticks,
        "elapsed_seconds": result["elapsed_seconds"],
        "neutrality": result["neutrality"],
        "replay_matches_entities": result["replay_matches_entities"],
        "request_help_decisions_with_target": c["request_help_decisions_with_target"],
        "actual_distinct_persons": c["actual_distinct_persons"],
        "shadow_distinct_persons": c["shadow_distinct_persons"],
        "actual_by_person": c["actual_by_person"],
        "shadow_by_person": c["shadow_by_person"],
        "divergence_rate": c["divergence_rate"],
        "tie_decisions": c["tie_decisions"],
        "cohort_size_histogram": c["cohort_size_histogram"],
        "decomposition": c["decomposition"],
        "tiebreak_headroom": c["tiebreak_headroom"],
        "cohort_union_distinct_persons": c["cohort_union_distinct_persons"],
        "run_shadow_min_distinct_per_window": c["run_shadow_min_distinct_per_window"],
        "run_shadow_max_top_person_share": c["run_shadow_max_top_person_share"],
        "run_fail_any_window_le_3": c["run_fail_any_window_le_3"],
        "windows_shadow": c["windows_shadow"],
        "windows_actual": c["windows_actual"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
