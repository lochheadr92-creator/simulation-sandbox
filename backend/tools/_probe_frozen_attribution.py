"""Frozen-baseline attribution probe (Culture Pass, Cairn S1).

The frozen living_settlement@320 pin moved on the culture-pass tree. The
owner's instruction: attribute any movement "culture layer additive vs
people-stack emotion leg". This probe decomposes the movement:

  variant "all"      — current tree, all enabled domains (should reproduce
                       the moved hash the pin test measured);
  variant "no_emotion" — same tree with the emotion domain filtered out of
                       enabled_domains (its marginal contribution).

The contracts/settlement hunks of the emotion leg (emotions block minted in
living_agent state, `_apply_emotion_gradient` in settlement scoring) are not
reverted here, so "no_emotion" is NOT expected to restore the ratified
baseline; the gap to ratified is the state/schema half of the emotion leg.
The culture layer is statically absent from this scenario either way (no
`people` domain, no `storage_location` persons, aid validator early-returns,
signal terms scoped to offer_trade).

    py -3.12 -m tools._probe_frozen_attribution --ticks 320 \
        --report ../test_reports/frozen_attribution.json
"""
from __future__ import annotations

import argparse
import json
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

RATIFIED = "e80743460e46be4cf73086854988baa9aa92de27cbff9b5e777430497a0317b2"
SEED = "living-agents-stage6"
SCENARIO_ID = "living_settlement"


def _run(domains: list[str], ticks: int) -> dict:
    scenario = get_scenario(SCENARIO_ID)
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, _genesis, _genesis_rejected, order_index = build_genesis(
        SEED, scenario, lineage_key)
    rng = DeterministicRNG(SEED)
    entity_json_cache: dict = {}
    accepted_count = 0
    emotion_events = 0
    for tick in range(1, ticks + 1):
        accepted, _rejected, order_index, _diagnostics = run_tick(
            "frozen-attribution", entities, world["terrain"], tick, rng,
            order_index, lineage_key, domains,
            entity_json_cache=entity_json_cache,
        )
        accepted_count += len(accepted)
        emotion_events += sum(
            1 for event in accepted
            if event.get("proposer_engine_id") == "emotion"
            or str(event.get("event_type", "")).startswith("emotion")
        )
    return {
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, ticks, lineage_key)),
        "accepted_event_count": accepted_count,
        "emotion_events": emotion_events,
        "matches_ratified": canonical_hash(snapshot_for_hash(entities, ticks, lineage_key)) == RATIFIED,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=320)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    scenario = get_scenario(SCENARIO_ID)
    all_domains = list(scenario.enabled_domains)
    no_emotion = [d for d in all_domains if d != "emotion"]

    report = {
        "scenario": SCENARIO_ID,
        "seed": SEED,
        "ticks": args.ticks,
        "ratified_baseline": RATIFIED,
        "all_domains": _run(all_domains, args.ticks),
        "no_emotion_domain": _run(no_emotion, args.ticks),
        "domains_all": all_domains,
        "domains_no_emotion": no_emotion,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
