"""Stage 8B Leg 1 tick-discrepancy investigation (read-only).

Resolves whether the person-004 -> person-000 `social_request_help` event
that the group_carriage carrier record for person-004 cites via
`via_event_id: evt-698-...` actually occurred at tick 698 or tick 699, and
whether enabling `group_carriage` in `collective_groups.enabled_domains`
changes WHEN that event is accepted (as opposed to merely reading it one
tick later, per the domain's documented one-tick lag).

Pure observation: reuses `build_genesis` / `run_tick` exactly as
`_probe_8b_carriage.py` does. No simulation code is modified.

Usage: python -m tools._probe_8b_tick_discrepancy [ticks]
"""
from __future__ import annotations

import json
import sys
import time

from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario

SEED = "living-agents-stage6"
WINDOW_START = 690
WINDOW_END = 702


def probe(ticks=1000):
    scenario = get_scenario("collective_groups")
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    window_events = []          # full raw event dicts (trimmed to requested fields) in [690,702]
    all_social_request_help = []  # every social_request_help event across the whole run (for cross-check)
    accepted_counts_by_tick = {}

    for tick in range(1, ticks + 1):
        accepted, _rej, order_index, _diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        accepted_counts_by_tick[tick] = len(accepted)
        for e in accepted:
            valid_parent_ids.add(e["id"])
            etype = e.get("event_type")
            if etype == "social_request_help":
                meta = e.get("social_action") or {}
                rec = {
                    "id": e.get("id"),
                    "event_type": etype,
                    "entity_id": e.get("entity_id"),
                    "simulation_time": e.get("simulation_time"),
                    "social_action_actor_id": meta.get("actor_id"),
                    "social_action_target_id": meta.get("target_id"),
                    "social_action_action_type": meta.get("action_type"),
                }
                all_social_request_help.append(rec)
            if WINDOW_START <= tick <= WINDOW_END:
                meta = e.get("social_action")
                entry = {
                    "id": e.get("id"),
                    "event_type": etype,
                    "entity_id": e.get("entity_id"),
                    "simulation_time": e.get("simulation_time"),
                }
                if isinstance(meta, dict):
                    entry["social_action"] = {
                        "actor_id": meta.get("actor_id"),
                        "target_id": meta.get("target_id"),
                        "action_type": meta.get("action_type"),
                    }
                window_events.append(entry)

    evt_698_matches = [
        e for e in window_events
        if str(e["id"]).startswith("evt-698-")
        and e["event_type"] == "social_request_help"
        and (e.get("social_action") or {}).get("actor_id") == "person-004"
        and (e.get("social_action") or {}).get("target_id") == "person-000"
    ]
    evt_699_matches = [
        e for e in window_events
        if str(e["id"]).startswith("evt-699-")
        and e["event_type"] == "social_request_help"
        and (e.get("social_action") or {}).get("actor_id") == "person-004"
        and (e.get("social_action") or {}).get("target_id") == "person-000"
    ]
    p004_p000_all = [
        e for e in all_social_request_help
        if e.get("social_action_actor_id") == "person-004"
        and e.get("social_action_target_id") == "person-000"
    ]

    print(json.dumps({
        "ticks": ticks,
        "enabled_domains": list(scenario.enabled_domains),
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "window_events_count": len(window_events),
        "window_events": window_events,
        "evt_698_person004_to_person000_social_request_help": evt_698_matches,
        "evt_699_person004_to_person000_social_request_help": evt_699_matches,
        "all_person004_to_person000_social_request_help_whole_run": p004_p000_all,
        "accepted_counts_690_702": {
            str(t): accepted_counts_by_tick.get(t) for t in range(WINDOW_START, WINDOW_END + 1)
        },
    }, indent=2, default=str))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    t0 = time.time()
    probe(tk)
    print(json.dumps({"wall_clock_seconds": round(time.time() - t0, 2)}), file=sys.stderr)
