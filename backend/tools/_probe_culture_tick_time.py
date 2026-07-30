"""Tick-time regression probe — collective_groups benchmark (CULTURE_PASS.md).

Mirrors the Surplus Pass guardrail: 500 ticks of `collective_groups` (seed
living-agents-stage6), wall-clock per tick averaged over the run. The culture
layer never activates in this scenario (no surplus-enabled persons), so any
movement here is import/validator overhead only. Gate: <= 400 ms/tick average
(surplus pass measured 367.6 ms/tick final, limit 1200).

    py -3.12 -m tools._probe_culture_tick_time --ticks 500 \
        --report ../test_reports/culture_tick_time.json

Redirect output to a file for the full run (house rule).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import scenarios  # noqa: F401  (registration side effects)
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from scenarios.registry import get_scenario


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="collective_groups")
    parser.add_argument("--seed", default="living-agents-stage6")
    parser.add_argument("--ticks", type=int, default=500)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    scenario = get_scenario(args.scenario)
    lineage_key = f"{args.seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, _genesis, _genesis_rejected, order_index = build_genesis(
        args.seed, scenario, lineage_key)
    rng = DeterministicRNG(args.seed)
    # Caller-owned fragment cache, matching how the harness (and therefore
    # the 367.6 ms/tick surplus-pass baseline) drives the kernel.
    entity_json_cache: dict = {}

    started = time.perf_counter()
    for tick in range(1, args.ticks + 1):
        _accepted, _rejected, order_index, _diagnostics = run_tick(
            "culture-tick-time", entities, world["terrain"], tick, rng,
            order_index, lineage_key, scenario.enabled_domains,
            entity_json_cache=entity_json_cache,
        )
    wall = time.perf_counter() - started

    summary = {
        "scenario": args.scenario,
        "seed": args.seed,
        "ticks": args.ticks,
        "wall_clock_seconds": round(wall, 2),
        "ms_per_tick_avg": round(wall * 1000 / args.ticks, 1),
        "gate_ms_per_tick": 400,
        "within_gate": (wall * 1000 / args.ticks) <= 400,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
