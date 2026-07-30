"""Chunked culture-census runner (CULTURE_PASS.md).

Runs the shared 500-tick culture census (`tools/culture_census.py`) in
time-bounded chunks, pickling engine state between invocations, so long
horizons fit inside per-command time limits. State is (entities, order_index,
next_tick, counters); DeterministicRNG streams embed the tick, so chunk
boundaries are transparent to the run.

    py -3.12 -m tools._probe_culture_census --seed culture-tier-b --ticks 500 \
        --chunk 60 --state ../test_reports/culture_census_state.pkl \
        --report ../test_reports/culture_census_500.json

Repeat the same command until it prints "complete": true. Redirect output to
a file for long chunks (house rule).
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

from tools.culture_census import census_ticks, finalize, new_census_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="culture-tier-b")
    parser.add_argument("--ticks", type=int, default=500)
    parser.add_argument("--chunk", type=int, default=60)
    parser.add_argument("--state", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    state_path = Path(args.state)
    if state_path.exists():
        with state_path.open("rb") as fh:
            state = pickle.load(fh)
    else:
        state = new_census_state(args.seed)

    upto = min(state["next_tick"] - 1 + args.chunk, args.ticks)
    census_ticks(state, upto)
    complete = state["next_tick"] > args.ticks

    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("wb") as fh:
        pickle.dump(state, fh)

    summary = {
        "seed": args.seed,
        "ticks_run": state["next_tick"] - 1,
        "target_ticks": args.ticks,
        "complete": complete,
        "trade_events": state["counters"]["trade_events"],
        "aid_events": state["counters"]["aid_events"],
        "offer_ticks": state["counters"]["offer_ticks"],
        "memory_hit_ticks": state["counters"]["memory_hit_ticks"],
        "gate_blocked": state["counters"]["gate_blocked"],
    }
    if complete:
        report = finalize(state)
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))
        summary["report"] = str(report_path)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
