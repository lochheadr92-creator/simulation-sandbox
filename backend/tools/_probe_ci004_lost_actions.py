"""Why do `share_information` and `threaten` stop firing under CI-004 ordering?

Both are one-shot, counter-gated actions that fired once in the baseline and
zero times under the new ordering at 320 / 600 / 1,000 ticks. Five other
one-shot actions are unaffected, so the cause must lie in the conjuncts unique
to these two.

    share_information (VERIFY_INFORMATION, living_settlement_domain.py:435)
        role == "steward"
        AND visible_person_ids
        AND "storage-private" in storages        <-- unique: observed OBJECT
        AND _action_count("share_information") < 1

    threaten (THREATEN, :459)
        role == "hoarder"
        AND visible_person_ids
        AND tick >= 8                            <-- unique: tick floor
        AND _action_count("threaten") < 1

This records EVERY conjunct independently, per tick, for the two eligible
actors -- never first-false-only -- so the failing conjunct is identified rather
than inferred.

READ-ONLY. Wraps `build_settlement_candidates`, calls the original first,
observes, and returns it untouched (the shadow pattern already proven inert).

Usage:
  python -m tools._probe_ci004_lost_actions <out.json> [ticks] [scenario] [seed]
"""
from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path

import domains.living_settlement_domain as living
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario


SEED = "living-agents-stage6"
DEFAULT_SCENARIO = "living_settlement"
DEFAULT_TICKS = 400

WATCH = {
    "steward": ("share_information", "VERIFY_INFORMATION"),
    "hoarder": ("threaten", "THREATEN"),
}


def _c(counter) -> dict:
    return {str(k): int(counter[k]) for k in sorted(counter, key=str)}


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = DEFAULT_SCENARIO, output_path: Path | None = None) -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _r, order_index = build_genesis(seed, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(seed)
    cache: dict = {}
    started = time.perf_counter()

    gates = {role: Counter() for role in WATCH}
    decisions = Counter()
    first_all_true = {}
    candidate_seen = Counter()
    storage_ids_seen: set[str] = set()
    examples: dict[str, list] = {role: [] for role in WATCH}

    original = living.build_settlement_candidates

    def observed(entity_id, entity, state, knowledge, delta, tick):
        candidates = original(entity_id, entity, state, knowledge, delta, tick)
        role = str(entity.get("stage6_role") or "")
        if role in WATCH:
            action, goal = WATCH[role]
            people = living._observation_map(delta, "person")
            storages = living._observation_map(delta, "storage")
            storage_ids_seen.update(str(s) for s in storages)
            conj = {
                "role_ok": True,
                "person_visible": bool(people),
                "counter_open": living._action_count(entity, action) < 1,
            }
            if role == "steward":
                conj["storage_private_observed"] = "storage-private" in storages
            else:
                conj["tick_ge_8"] = int(tick) >= 8
            decisions[role] += 1
            for name, ok in conj.items():
                gates[role]["PASS:" + name if ok else "FAIL:" + name] += 1
            if all(conj.values()):
                gates[role]["ALL_TRUE"] += 1
                first_all_true.setdefault(role, int(tick))
            if any(c.get("goal") == goal for c in candidates):
                candidate_seen[role] += 1
            if len(examples[role]) < 8 and all(conj.values()):
                examples[role].append({"tick": int(tick), **conj,
                                       "visible_storages": sorted(storages)})
        return candidates

    living.build_settlement_candidates = observed
    try:
        for tick in range(1, ticks + 1):
            accepted, _rej, order_index, _d = run_tick(
                "probe-ci004-lost", entities, world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
                valid_causal_parent_event_ids=valid_parent_ids,
                entity_json_cache=cache)
            for event in accepted:
                valid_parent_ids.add(event["id"])
    finally:
        living.build_settlement_candidates = original

    payload = {
        "status": "complete", "probe": "ci004-lost-actions",
        "seed": seed, "scenario_id": scenario_id, "ticks": int(ticks),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, ticks, lineage_key)),
        "decisions_per_role": _c(decisions),
        "gates": {role: _c(g) for role, g in gates.items()},
        "first_tick_all_conjuncts_true": first_all_true,
        "candidate_generated": _c(candidate_seen),
        "all_storage_ids_ever_observed": sorted(storage_ids_seen),
        "examples": examples,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[0]) if argv else Path("ci004_lost.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    scenario = argv[2] if len(argv) > 2 else DEFAULT_SCENARIO
    seed = argv[3] if len(argv) > 3 else SEED
    r = probe(ticks=ticks, seed=seed, scenario_id=scenario, output_path=out)
    print(json.dumps({k: v for k, v in r.items() if k != "examples"},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
