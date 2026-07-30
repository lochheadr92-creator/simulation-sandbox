"""Two-run hash-equality probe (chunked, Culture Pass local verification).

Local stand-in for `tests/test_culture_pass.py::test_two_identical_runs_...`
when a continuous 80-tick pair exceeds one command's time budget. Runs the
same two traces (surplus_forage, seed culture-tier-a) with the harness-style
fragment cache for speed, resumable via pickle, and asserts the same contract:
final entities equal, per-tick frame hashes equal, genesis event hashes equal.

    py -3.12 -m tools._probe_tworun --ticks 40 --state ../test_reports/tworun_state.pkl \
        --report ../test_reports/tworun_equality.json

Repeat until "complete": true. Both runs share the chunk boundaries, so the
comparison is an exact determinism check (same version, seed, inputs).
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import scenarios  # noqa: F401  (registration side effects)
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios.registry import get_scenario

SEED = "culture-tier-a"
SCENARIO_ID = "surplus_forage"


def _new_run(run_id: str):
    scenario = get_scenario(SCENARIO_ID)
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _genesis_rejected, order_index = build_genesis(
        SEED, scenario, lineage_key)
    return {
        "run_id": run_id,
        "terrain": world["terrain"],
        "entities": entities,
        "genesis_event_hashes": [canonical_hash(e) for e in genesis],
        "order_index": order_index,
        "next_tick": 1,
        "frame_hashes": [],
        "lineage_key": lineage_key,
        "entity_json_cache": {},
    }


def _advance(run: dict, upto_tick: int) -> None:
    scenario = get_scenario(SCENARIO_ID)
    rng = DeterministicRNG(SEED)
    for tick in range(run["next_tick"], upto_tick + 1):
        _accepted, _rejected, run["order_index"], _diagnostics = run_tick(
            run["run_id"], run["entities"], run["terrain"], tick, rng,
            run["order_index"], run["lineage_key"], scenario.enabled_domains,
            entity_json_cache=run["entity_json_cache"],
        )
        run["frame_hashes"].append(
            canonical_hash(snapshot_for_hash(run["entities"], tick, run["lineage_key"])))
    run["next_tick"] = upto_tick + 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=40)
    parser.add_argument("--chunk", type=int, default=20)
    parser.add_argument("--state", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    state_path = Path(args.state)
    if state_path.exists():
        with state_path.open("rb") as fh:
            state = pickle.load(fh)
    else:
        state = {"runs": [_new_run("culture-run-a"), _new_run("culture-run-b")]}

    total_steps = args.ticks * 2
    done_steps = sum(run["next_tick"] - 1 for run in state["runs"])
    budget = args.chunk
    for run in state["runs"]:
        if budget <= 0:
            break
        remaining = args.ticks - (run["next_tick"] - 1)
        step = min(remaining, budget)
        if step > 0:
            _advance(run, run["next_tick"] - 1 + step)
            budget -= step
    done_steps = sum(run["next_tick"] - 1 for run in state["runs"])

    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("wb") as fh:
        pickle.dump(state, fh)

    complete = done_steps >= total_steps
    summary = {"ticks_per_run": args.ticks, "done_ticks_total": done_steps,
               "complete": complete}
    if complete:
        run_a, run_b = state["runs"]
        summary.update({
            "entities_equal": run_a["entities"] == run_b["entities"],
            "frame_hashes_equal": run_a["frame_hashes"] == run_b["frame_hashes"],
            "genesis_event_hashes_equal": (
                run_a["genesis_event_hashes"] == run_b["genesis_event_hashes"]),
            "final_frame_hash": run_a["frame_hashes"][-1] if run_a["frame_hashes"] else None,
        })
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
