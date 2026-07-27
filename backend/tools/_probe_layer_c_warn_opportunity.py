"""Layer C Social Density Leg 2 -- Session 2: `warn` stage A/B instrument.

Plan: memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md, Phase 1,
Session 2 ("A/B probes ONLY for the never-generated subset").
Definition under test, ratified for criticism before this was built:
memory/evidence/layer-c-social-density-leg1/leg2_session2_warn_opportunity_definition.md

SCOPE: `warn` only. Session 1 resolved the other seven target actions to a
measured monotone counter; `warn` was the sole INSUFFICIENT EVIDENCE verdict --
its self-cap is 2, the scout spent 1, so the gate was open for 100% of 24,000
alive-person-ticks and it still never regenerated after tick 1.

WHAT IS MEASURED
----------------
Stage A, per the ratified definition -- a tick is a `warn` semantic opportunity
iff the scout, alive and due, observes BOTH an animal and another person under
perceive_living's P1..P5. The role gate and the self-cap are deliberately NOT
part of stage A, so a consumed counter cannot masquerade as an absent
opportunity.

Stage B, ALL conjuncts independently -- never first-false-only:
`role_ok`, `animal_observed`, `person_observed`, `counter_open`, plus the full
2x2 co-occurrence of the two perception conjuncts so "animal but no person" is
distinguishable from "person but no animal" and from "neither".

Attribution context per decision, all read from the frame the gate read:
effective_radius, the four radius_penalty components, night, scout health and
energy, and the Manhattan distance to the nearest animal and nearest person.
This lets a failure be attributed to DISTANCE versus DEGRADATION rather than
merely observed.

NEUTRALITY -- approach (a) with (c) as cross-check
---------------------------------------------------
(a) This probe DOES monkeypatch `build_settlement_candidates`, restoring it in a
    `finally`. That is deliberate and was authorised: it reads the exact `delta`
    object the gate reads, so a wrong reimplementation of P1..P5 cannot
    masquerade as a finding about the world. The wrapper calls the original
    first, observes, and mutates nothing.

    PROOF OBLIGATION: Session 1's UNPATCHED 3,000-tick run on this seed,
    scenario and horizon produced
    fb032eaf6fa5041cea73e6172943ce31203809c1c3dab90b893aba8025597d7a
    (memory/evidence/.../leg2_session1_funnel_collective_groups_3000.json).
    This probe re-derives its own final_state_hash and compares. Byte equality
    proves the patch inert over exactly the measured window. A mismatch is a
    STOP: the tracer becomes the work item.

(c) CROSS-CHECK, free and inside the same run: `diagnostics[actor]["perception"]`
    is written by the domain from the same `delta` the patch intercepts, and is
    available WITHOUT the patch. Every decision asserts the patch-captured
    observation count and attention profile equal the domain's own record. A
    disagreement means the patch did not read what the gate read.

P3 / P4 are established rather than asserted: the terrain grid is scanned once
for any OPAQUE_TERRAIN tile (if none exists, line-of-sight provably cannot
block), and the per-decision entity-observation count is compared against the
frame's declared entity budget.

Usage:
  python -m tools._probe_layer_c_warn_opportunity <out.json> [ticks] [seed]
"""
from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import domains.living_settlement_domain as living_domain
from core.constants import ENGINE_VERSION, SCHEMA_VERSION, VISION_RADIUS, is_night
from core.geometry import manhattan
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from domains.living_agent_cognition import OPAQUE_TERRAIN
from scenarios import get_scenario


SEED = "living-agents-stage6"
SCENARIO = "collective_groups"
DEFAULT_TICKS = 3_000
CHECKPOINT_EVERY = 250
WINDOW = 1_000
EXAMPLE_LIMIT = 32
TARGET_ROLE = "scout"
TARGET_ACTION = "warn"
TARGET_GOAL = "WARN_DANGER"
WARN_SELF_CAP = 2

# Session 1, unpatched, same seed / scenario / horizon. The patch must reproduce
# this exactly at tick 3000.
SESSION1_UNPATCHED_HASH_3000 = (
    "fb032eaf6fa5041cea73e6172943ce31203809c1c3dab90b893aba8025597d7a"
)


def _sorted_counter(counter) -> dict:
    return {str(key): int(counter[key]) for key in sorted(counter, key=str)}


def _numeric_summary(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "min": None, "p25": None, "median": None,
                "p75": None, "p90": None, "max": None, "mean": None}
    ordered = sorted(int(value) for value in values)

    def pct(fraction: float) -> int:
        return ordered[round((len(ordered) - 1) * fraction)]

    return {"count": len(ordered), "min": ordered[0], "p25": pct(0.25),
            "median": pct(0.50), "p75": pct(0.75), "p90": pct(0.90),
            "max": ordered[-1], "mean": round(sum(ordered) / len(ordered), 4)}


class WarnOpportunityCensus:
    def __init__(self) -> None:
        self.current_entities: dict = {}
        self.current_tick = 0
        # stage A
        self.scout_decisions = 0
        self.animal_observed = 0
        self.person_observed = 0
        self.semantic_opportunities = 0            # A1 AND A2
        self.cooccurrence = Counter()              # (animal, person) -> n
        # stage B -- every conjunct independently, never first-false
        self.gate = Counter()
        self.gate_failures = Counter()
        self.candidate_returned = 0
        # attribution context
        self.effective_radius_hist = Counter()
        self.radius_penalty_hist = Counter()
        self.penalty_components = defaultdict(Counter)
        self.night_decisions = 0
        self.min_animal_distance: list[int] = []
        self.min_person_distance: list[int] = []
        self.min_animal_distance_when_missed: list[int] = []
        self.min_person_distance_when_missed: list[int] = []
        self.health_values: list[int] = []
        self.energy_values: list[int] = []
        self.warn_count_hist = Counter()
        # P4 budget
        self.entity_observation_counts: list[int] = []
        self.entity_budget_hits = 0
        self.entity_budget_limit: int | None = None
        # (c) cross-check
        self.crosscheck_compared = 0
        self.crosscheck_mismatches = 0
        self.crosscheck_mismatch_examples: list[dict] = []
        self._pending: dict[tuple[int, str], dict] = {}
        # windows
        self.window_opportunities = Counter()
        self.window_scout_decisions = Counter()
        self.window_animal = Counter()
        self.window_person = Counter()
        self.examples: dict[str, list] = defaultdict(list)
        self.opportunity_ticks: list[int] = []

    def _example(self, kind: str, row: dict) -> None:
        if len(self.examples[kind]) < EXAMPLE_LIMIT:
            self.examples[kind].append(copy.deepcopy(row))

    # -- called from inside the patched builder ------------------------
    def observe_candidate_build(self, *, actor_id: str, entity: dict, delta: dict,
                                tick: int, candidates: list[dict]) -> None:
        if str(entity.get("stage6_role") or "") != TARGET_ROLE:
            return
        window = (int(tick) - 1) // WINDOW

        animals = living_domain._observation_map(delta, "animal")
        people = living_domain._observation_map(delta, "person")
        a1 = bool(animals)
        a2 = bool(people)

        attention = delta.get("attention") or {}
        effective_radius = delta.get("effective_radius")
        observations = delta.get("observations") or []
        limits = delta.get("limits") or {}
        entity_obs = [
            row for row in observations
            if row.get("observation_type") in ("person", "animal")
        ]
        entity_limit = limits.get("entities")
        if entity_limit is not None:
            self.entity_budget_limit = int(entity_limit)
            if len(entity_obs) >= int(entity_limit):
                self.entity_budget_hits += 1
        self.entity_observation_counts.append(len(entity_obs))

        warn_count = living_domain._action_count(entity, TARGET_ACTION)
        counter_open = warn_count < WARN_SELF_CAP
        role_ok = True  # filtered above; recorded for completeness
        candidate_returned = any(
            row.get("goal") == TARGET_GOAL for row in candidates
        )

        self.scout_decisions += 1
        self.window_scout_decisions[window] += 1
        self.cooccurrence[f"animal={int(a1)},person={int(a2)}"] += 1
        if a1:
            self.animal_observed += 1
            self.window_animal[window] += 1
        if a2:
            self.person_observed += 1
            self.window_person[window] += 1
        if a1 and a2:
            self.semantic_opportunities += 1
            self.window_opportunities[window] += 1
            if len(self.opportunity_ticks) < 512:
                self.opportunity_ticks.append(int(tick))
        if candidate_returned:
            self.candidate_returned += 1

        # ALL gate conjuncts, independently -- never first-false-only.
        for name, value in (("role_ok", role_ok), ("animal_observed", a1),
                            ("person_observed", a2), ("counter_open", counter_open)):
            if value:
                self.gate[name] += 1
            else:
                self.gate_failures[name] += 1
        if role_ok and a1 and a2 and counter_open:
            self.gate["all_conjuncts_true"] += 1
            if not candidate_returned:
                self.gate["eligible_but_candidate_missing"] += 1

        self.warn_count_hist[warn_count] += 1
        if effective_radius is not None:
            self.effective_radius_hist[int(effective_radius)] += 1
        if attention:
            self.radius_penalty_hist[int(attention.get("radius_penalty", 0))] += 1
            for key in ("fatigue_penalty", "health_penalty",
                        "lighting_penalty", "weather_penalty"):
                self.penalty_components[key][int(attention.get(key, 0))] += 1
        if is_night(int(tick)):
            self.night_decisions += 1
        self.health_values.append(int(entity.get("health", 0) or 0))
        self.energy_values.append(int(entity.get("energy", 0) or 0))

        # Distances from the pinned frame: separates DISTANCE from DEGRADATION.
        pos = entity.get("position") or {}
        d_animal = self._nearest(pos, "animal", exclude=actor_id)
        d_person = self._nearest(pos, "person", exclude=actor_id)
        if d_animal is not None:
            self.min_animal_distance.append(d_animal)
            if not a1:
                self.min_animal_distance_when_missed.append(d_animal)
        if d_person is not None:
            self.min_person_distance.append(d_person)
            if not a2:
                self.min_person_distance_when_missed.append(d_person)

        row = {
            "tick": int(tick), "actor_id": actor_id,
            "animal_observed": a1, "person_observed": a2,
            "counter_open": counter_open, "warn_count": warn_count,
            "candidate_returned": candidate_returned,
            "effective_radius": effective_radius,
            "radius_penalty": attention.get("radius_penalty"),
            "night": is_night(int(tick)),
            "health": entity.get("health"), "energy": entity.get("energy"),
            "nearest_animal_distance": d_animal,
            "nearest_person_distance": d_person,
            "entity_observation_count": len(entity_obs),
        }
        if a1 and a2:
            self._example("semantic_opportunity", row)
        elif a1 and not a2:
            self._example("animal_only", row)
        elif a2 and not a1:
            self._example("person_only", row)
        else:
            self._example("neither", row)

        # (c) cross-check payload, resolved against diagnostics after the tick.
        self._pending[(int(tick), actor_id)] = {
            "observation_count": len(observations),
            "attention": copy.deepcopy(attention),
        }

    def _nearest(self, pos: dict, entity_type: str, *, exclude: str) -> int | None:
        best = None
        for entity_id, entity in self.current_entities.items():
            if entity_id == exclude or entity.get("type") != entity_type:
                continue
            other = entity.get("position")
            if not other:
                continue
            distance = manhattan(pos, other)
            if best is None or distance < best:
                best = distance
        return best

    # -- (c) cross-check, after the tick -------------------------------
    def resolve_crosscheck(self, *, tick: int, diagnostics: dict) -> None:
        for (pending_tick, actor_id), captured in list(self._pending.items()):
            if pending_tick != int(tick):
                continue
            self._pending.pop((pending_tick, actor_id), None)
            row = diagnostics.get(actor_id)
            if not isinstance(row, dict) or "decision_receipt" not in row:
                continue
            domain_view = row.get("perception") or {}
            self.crosscheck_compared += 1
            same_count = int(domain_view.get("count", -1)) == int(captured["observation_count"])
            same_attention = (domain_view.get("attention") or {}) == captured["attention"]
            if not (same_count and same_attention):
                self.crosscheck_mismatches += 1
                if len(self.crosscheck_mismatch_examples) < 8:
                    self.crosscheck_mismatch_examples.append({
                        "tick": int(tick), "actor_id": actor_id,
                        "patch_observation_count": captured["observation_count"],
                        "domain_observation_count": domain_view.get("count"),
                        "attention_equal": same_attention,
                    })
        self._pending = {
            key: value for key, value in self._pending.items() if key[0] >= int(tick)
        }

    def metrics(self) -> dict:
        decisions = max(1, self.scout_decisions)
        return {
            "definition": (
                "A tick is a warn SEMANTIC OPPORTUNITY iff the scout, alive and "
                "due, observes BOTH an animal and another person under "
                "perceive_living P1..P5. Role gate and self-cap are stage B and "
                "are excluded from stage A by design."
            ),
            "scout_decisions": self.scout_decisions,
            "stage_A_semantic_opportunities": self.semantic_opportunities,
            "stage_A_opportunity_rate": round(self.semantic_opportunities / decisions, 6),
            "stage_A_animal_observed": self.animal_observed,
            "stage_A_person_observed": self.person_observed,
            "stage_A_cooccurrence": _sorted_counter(self.cooccurrence),
            "stage_A_opportunity_ticks": self.opportunity_ticks,
            "stage_B_gate_true_counts": _sorted_counter(self.gate),
            "stage_B_gate_failure_counts": _sorted_counter(self.gate_failures),
            "stage_C_candidate_returned": self.candidate_returned,
            "warn_action_count_histogram": _sorted_counter(self.warn_count_hist),
            "effective_radius_histogram": _sorted_counter(self.effective_radius_hist),
            "radius_penalty_histogram": _sorted_counter(self.radius_penalty_hist),
            "radius_penalty_components": {
                key: _sorted_counter(counter)
                for key, counter in sorted(self.penalty_components.items())
            },
            "night_decisions": self.night_decisions,
            "scout_health_distribution": _numeric_summary(self.health_values),
            "scout_energy_distribution": _numeric_summary(self.energy_values),
            "nearest_animal_distance_distribution": _numeric_summary(self.min_animal_distance),
            "nearest_person_distance_distribution": _numeric_summary(self.min_person_distance),
            "nearest_animal_distance_when_not_observed": _numeric_summary(
                self.min_animal_distance_when_missed),
            "nearest_person_distance_when_not_observed": _numeric_summary(
                self.min_person_distance_when_missed),
            "vision_radius_constant": VISION_RADIUS,
            "P4_entity_observation_count_distribution": _numeric_summary(
                self.entity_observation_counts),
            "P4_entity_budget_limit": self.entity_budget_limit,
            "P4_entity_budget_hits": self.entity_budget_hits,
            "crosscheck_c_compared": self.crosscheck_compared,
            "crosscheck_c_mismatches": self.crosscheck_mismatches,
            "crosscheck_c_pass": self.crosscheck_mismatches == 0,
            "crosscheck_c_mismatch_examples": self.crosscheck_mismatch_examples,
            "windows": [
                {
                    "window_index": index,
                    "scout_decisions": int(self.window_scout_decisions[index]),
                    "semantic_opportunities": int(self.window_opportunities[index]),
                    "animal_observed": int(self.window_animal[index]),
                    "person_observed": int(self.window_person[index]),
                }
                for index in sorted(self.window_scout_decisions)
            ],
            "examples": {kind: rows for kind, rows in sorted(self.examples.items())},
        }


def _terrain_opacity_check(terrain: list) -> dict:
    """Establish P3's status as fact rather than asserting it."""
    kinds = Counter()
    for row in terrain:
        for tile in row:
            kinds[str(tile)] += 1
    opaque = {kind: count for kind, count in kinds.items() if kind in OPAQUE_TERRAIN}
    return {
        "terrain_tile_kinds": _sorted_counter(kinds),
        "opaque_terrain_kinds": OPAQUE_TERRAIN and sorted(OPAQUE_TERRAIN),
        "opaque_tiles_present": opaque,
        "P3_line_of_sight_can_block": bool(opaque),
        "note": (
            "Scanned once from the generated world. With no opaque tile present, "
            "_has_line_of_sight provably cannot reject any pair, so P3 is vacuous "
            "in this scenario -- established, not assumed."
        ),
    }


def _write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = SCENARIO, output_path: Path | None = None,
          run_id: str = "probe-layer-c-warn-opportunity") -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, genesis_rejected, order_index = build_genesis(
        seed, scenario, lineage_key)
    valid_parent_ids = {event["id"] for event in genesis}
    replayed: dict = {}
    for event in genesis:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    rng = DeterministicRNG(seed)
    entity_json_cache: dict = {}
    census = WarnOpportunityCensus()
    checkpoints: dict[str, dict] = {}
    started = time.perf_counter()

    payload = {
        "status": "in_progress",
        "probe": "layer-c-social-density-leg2-session2-warn-opportunity",
        "plan": "memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md",
        "definition_doc": (
            "memory/evidence/layer-c-social-density-leg1/"
            "leg2_session2_warn_opportunity_definition.md"),
        "seed": seed, "scenario_id": scenario_id, "ticks": int(ticks),
        "run_id": run_id, "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION, "lineage_key": lineage_key,
        "instrumentation": {
            "approach": "(a) monkeypatch build_settlement_candidates, with (c) diagnostics cross-check",
            "monkeypatched_functions": ["domains.living_settlement_domain.build_settlement_candidates"],
            "authorised": True,
            "neutrality_proof": (
                "final_state_hash at tick 3000 must equal the Session 1 UNPATCHED "
                "run's hash on the same seed/scenario/horizon."),
        },
        "terrain_opacity": _terrain_opacity_check(world["terrain"]),
        "genesis_rejection_count": len(genesis_rejected),
        "checkpoints": checkpoints,
    }

    original_builder = living_domain.build_settlement_candidates

    def observed_builder(entity_id, entity, state, knowledge, delta, tick):
        candidates = original_builder(entity_id, entity, state, knowledge, delta, tick)
        census.observe_candidate_build(
            actor_id=entity_id, entity=entity, delta=delta, tick=tick,
            candidates=candidates)
        return candidates

    living_domain.build_settlement_candidates = observed_builder
    try:
        for tick in range(1, ticks + 1):
            census.current_entities = entities
            census.current_tick = tick
            accepted, rejected, order_index, diagnostics = run_tick(
                run_id, entities, world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
                valid_causal_parent_event_ids=valid_parent_ids,
                entity_json_cache=entity_json_cache)
            for event in accepted:
                valid_parent_ids.add(event["id"])
                apply_mutation(replayed, copy.deepcopy(event["mutation"]))
            census.resolve_crosscheck(tick=tick, diagnostics=diagnostics)

            if tick % CHECKPOINT_EVERY == 0 or tick == ticks:
                checkpoints[str(tick)] = {
                    "tick": int(tick),
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                    "final_state_hash": canonical_hash(
                        snapshot_for_hash(entities, tick, lineage_key)),
                    "replay_matches_entities": replayed == entities,
                }
                payload["last_completed_checkpoint"] = int(tick)
                payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
                payload["census"] = census.metrics()
                if output_path is not None:
                    _write_payload(output_path, payload)
    finally:
        living_domain.build_settlement_candidates = original_builder

    final_hash = checkpoints[str(ticks)]["final_state_hash"]
    neutral = None
    if int(ticks) == 3000 and seed == SEED and scenario_id == SCENARIO:
        neutral = final_hash == SESSION1_UNPATCHED_HASH_3000
    payload["status"] = "complete"
    payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    payload["final_state_hash"] = final_hash
    payload["replay_matches_entities"] = replayed == entities
    payload["census"] = census.metrics()
    payload["neutrality"] = {
        "session1_unpatched_hash_3000": SESSION1_UNPATCHED_HASH_3000,
        "this_run_final_state_hash": final_hash,
        "comparable": neutral is not None,
        "patch_is_inert": neutral,
        "crosscheck_c_pass": payload["census"]["crosscheck_c_pass"],
        "verdict": (
            "NEUTRAL" if (neutral and payload["census"]["crosscheck_c_pass"])
            else ("NOT_COMPARABLE" if neutral is None else "NOT_NEUTRAL")),
    }
    if output_path is not None:
        _write_payload(output_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    output_path = Path(argv[0]) if argv else Path("probe_layer_c_warn_opportunity.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    seed = argv[2] if len(argv) > 2 else SEED
    result = probe(ticks=ticks, seed=seed, output_path=output_path)
    c = result["census"]
    print(json.dumps({
        "status": result["status"],
        "output_path": str(output_path),
        "ticks": ticks,
        "elapsed_seconds": result["elapsed_seconds"],
        "neutrality": result["neutrality"],
        "replay_matches_entities": result["replay_matches_entities"],
        "P3_line_of_sight_can_block": result["terrain_opacity"]["P3_line_of_sight_can_block"],
        "scout_decisions": c["scout_decisions"],
        "stage_A_semantic_opportunities": c["stage_A_semantic_opportunities"],
        "stage_A_cooccurrence": c["stage_A_cooccurrence"],
        "stage_B_gate_failure_counts": c["stage_B_gate_failure_counts"],
        "stage_C_candidate_returned": c["stage_C_candidate_returned"],
        "effective_radius_histogram": c["effective_radius_histogram"],
        "nearest_animal_distance_distribution": c["nearest_animal_distance_distribution"],
        "nearest_person_distance_distribution": c["nearest_person_distance_distribution"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
