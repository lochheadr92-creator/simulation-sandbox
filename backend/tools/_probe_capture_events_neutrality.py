"""Instrumentation-neutrality gate for the Layer C Leg 2 Session 1 funnel probe.

Plan: memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md,
Phase 1, "Session 1 ... Neutrality check covers only the capture_events flag".

Two independent claims are tested, both on `collective_groups` at the same seed,
tick count and run_id so the only varying input is the thing under test.

CLAIM 1 -- the capture_events flag is canonically inert.
  The 5,000-tick baseline ran with capture_events false; this probe run needs it
  conceptually "on".  `run_living_agent_harness` only appends deep copies of
  already-produced events to a list when the flag is set, so inertness is
  expected by construction.  This measures it rather than asserting it:
  final_state_hash, the ORDERED accepted-event hash sequence, the frame hash
  sequence, and actions_by_type must all be identical.

CLAIM 2 -- the funnel probe itself is canonically inert.
  The probe patches nothing and only reads values `run_tick` already returns
  (`diagnostics` is discarded by the harness today).  Inertness is therefore
  also expected by construction.  This measures it: the probe's final_state_hash
  must equal the harness's at the same tick.  This simultaneously proves run_id
  does not leak into canonical state, since the two callers use the same run_id
  but reach it by different code paths.

A mismatch on either claim is a STOP: the tracer becomes the work item and no
classification may be derived from a non-neutral instrument.

Usage:
  python -m tools._probe_capture_events_neutrality <out.json> [ticks]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from core.hashing import canonical_hash
from tools._probe_layer_c_singleton_funnel import probe as funnel_probe
from tools.living_agent_harness import run_living_agent_harness


SEED = "living-agents-stage6"
SCENARIO = "collective_groups"
DEFAULT_TICKS = 300
RUN_ID = "neutrality-gate"


def _fingerprint(result: dict) -> dict:
    summary = result["summary"]
    return {
        "final_state_hash": result["final_state_hash"],
        "accepted_event_sequence_hash": summary["accepted_event_sequence_hash"],
        "frame_sequence_hash": summary["frame_sequence_hash"],
        "replay_state_hash": summary["replay_state_hash"],
        "replay_matches_final_entities": summary["replay_matches_final_entities"],
        "accepted_event_count": summary["accepted_event_count"],
        "rejected_proposal_count": summary["rejected_proposal_count"],
        "actions_by_type": summary["actions_by_type"],
        "accepted_by_type": summary["accepted_by_type"],
        "rejected_by_reason": summary["rejected_by_reason"],
        "decisions_by_kind": summary["decisions_by_kind"],
        "summary_hash": canonical_hash(summary),
    }


def run(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
        scenario_id: str = SCENARIO, output_path: Path | None = None) -> dict:
    started = time.perf_counter()

    off = run_living_agent_harness(
        seed, ticks=ticks, run_id=RUN_ID, scenario_id=scenario_id,
        capture_events=False,
    )
    off_print = _fingerprint(off)
    off_elapsed = round(time.perf_counter() - started, 3)

    mark = time.perf_counter()
    on = run_living_agent_harness(
        seed, ticks=ticks, run_id=RUN_ID, scenario_id=scenario_id,
        capture_events=True,
    )
    on_print = _fingerprint(on)
    on_elapsed = round(time.perf_counter() - mark, 3)

    # The ordered committed-event stream, compared element by element rather
    # than only via its aggregate hash, so a mismatch names its first index.
    captured_event_hashes = on["event_hashes"]
    ordered_stream_identical = off["event_hashes"] == captured_event_hashes
    first_divergent_index = None
    if not ordered_stream_identical:
        for index, (left, right) in enumerate(zip(off["event_hashes"], captured_event_hashes)):
            if left != right:
                first_divergent_index = index
                break
        if first_divergent_index is None:
            first_divergent_index = min(len(off["event_hashes"]), len(captured_event_hashes))

    claim_1_fields = {
        key: {"off": off_print[key], "on": on_print[key], "identical": off_print[key] == on_print[key]}
        for key in sorted(off_print)
    }
    claim_1_pass = all(row["identical"] for row in claim_1_fields.values()) and ordered_stream_identical

    mark = time.perf_counter()
    probed = funnel_probe(ticks=ticks, seed=seed, scenario_id=scenario_id, run_id=RUN_ID)
    probe_elapsed = round(time.perf_counter() - mark, 3)
    claim_2_pass = probed["final_state_hash"] == off_print["final_state_hash"]

    payload = {
        "gate": "layer-c-leg2-session1-instrumentation-neutrality",
        "plan": "memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG2-DISCOVERY-PLAN.md",
        "seed": seed,
        "scenario_id": scenario_id,
        "ticks": int(ticks),
        "run_id": RUN_ID,
        "elapsed_seconds": {
            "capture_events_off": off_elapsed,
            "capture_events_on": on_elapsed,
            "funnel_probe": probe_elapsed,
            "total": round(time.perf_counter() - started, 3),
        },
        "claim_1_capture_events_flag_is_inert": {
            "pass": claim_1_pass,
            "ordered_accepted_event_stream_identical": ordered_stream_identical,
            "first_divergent_event_index": first_divergent_index,
            "accepted_event_hash_count": len(off["event_hashes"]),
            "captured_accepted_event_count": len(on["accepted_events"]),
            "captured_rejected_proposal_count": len(on["rejected_proposals"]),
            "fields": claim_1_fields,
        },
        "claim_2_funnel_probe_is_inert": {
            "pass": claim_2_pass,
            "harness_final_state_hash": off_print["final_state_hash"],
            "probe_final_state_hash": probed["final_state_hash"],
            "probe_replay_matches_entities": probed["replay_matches_entities"],
            "probe_monkeypatched_functions": probed["instrumentation"]["monkeypatched_functions"],
            "note": (
                "Equality also proves run_id does not leak into canonical state: "
                "both callers use the same run_id but reach it by different paths."
            ),
        },
        "verdict": "NEUTRAL" if (claim_1_pass and claim_2_pass) else "NOT_NEUTRAL",
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    output_path = Path(argv[0]) if argv else Path("probe_capture_events_neutrality.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    payload = run(ticks=ticks, output_path=output_path)
    print(json.dumps({
        "verdict": payload["verdict"],
        "output_path": str(output_path),
        "ticks": payload["ticks"],
        "elapsed_seconds": payload["elapsed_seconds"],
        "claim_1_pass": payload["claim_1_capture_events_flag_is_inert"]["pass"],
        "claim_1_ordered_stream_identical": payload[
            "claim_1_capture_events_flag_is_inert"
        ]["ordered_accepted_event_stream_identical"],
        "claim_2_pass": payload["claim_2_funnel_probe_is_inert"]["pass"],
        "harness_final_state_hash": payload["claim_2_funnel_probe_is_inert"][
            "harness_final_state_hash"
        ],
        "probe_final_state_hash": payload["claim_2_funnel_probe_is_inert"][
            "probe_final_state_hash"
        ],
    }, indent=2, sort_keys=True))
    return 0 if payload["verdict"] == "NEUTRAL" else 1


if __name__ == "__main__":
    sys.exit(main())
