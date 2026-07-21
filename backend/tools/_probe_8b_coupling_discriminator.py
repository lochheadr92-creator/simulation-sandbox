"""Stage 8B Leg 1 discriminator: is the cross-domain outcome coupling that
shifted an unrelated `social_request_help` interaction from tick 699 to 698
when `group_carriage` was added a pre-existing, architecture-wide property of
the commit pipeline (adding ANY proposal-generating domain does it), or is it
specific to `group_carriage`?

Runs the SAME 1000-tick `collective_groups` simulation three times, once per
domain-set config, with fresh `build_genesis` + fresh `DeterministicRNG` each
time (no state carried between configs):

  Config A (7D baseline): scenario domains minus group_norm, group_carriage.
  Config B (8A):           Config A + group_norm.
  Config C (8B Leg 1):      Config B + group_carriage (== full scenario list).

For each config records every accepted `social_*` event (tick, event_type,
actor, target) and per-tick accepted-event counts for all 1000 ticks, then
diffs A vs B, B vs C, A vs C.

Read-only. Usage: python -m tools._probe_8b_coupling_discriminator [ticks]
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

EXPECTED_A = [
    "weather", "ecology", "lifecycle", "living_settlement", "animal",
    "association", "group_state", "group_collective", "group_goal",
]
EXPECTED_B = EXPECTED_A + ["group_norm"]
EXPECTED_C = EXPECTED_B + ["group_carriage"]


def _derive_configs():
    scenario = get_scenario("collective_groups")
    full = list(scenario.enabled_domains)
    config_c = full
    config_b = [d for d in full if d != "group_carriage"]
    config_a = [d for d in config_b if d != "group_norm"]
    assert config_a == EXPECTED_A, (config_a, EXPECTED_A)
    assert config_b == EXPECTED_B, (config_b, EXPECTED_B)
    assert config_c == EXPECTED_C, (config_c, EXPECTED_C)
    return scenario, {"A": config_a, "B": config_b, "C": config_c}


def _run_config(scenario, domains, ticks):
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    social_events = []
    per_tick_counts = {}
    per_tick_types = {}  # tick -> sorted list of event_type strings (internal, used only for diffing)

    for tick in range(1, ticks + 1):
        accepted, _rej, order_index, _diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        types_this_tick = []
        for e in accepted:
            valid_parent_ids.add(e["id"])
            etype = e.get("event_type")
            types_this_tick.append(etype)
            if etype and etype.startswith("social_"):
                meta = e.get("social_action") or {}
                social_events.append({
                    "tick": tick,
                    "event_type": etype,
                    "actor": e.get("entity_id"),
                    "target": meta.get("target_id"),
                })
        per_tick_counts[tick] = len(accepted)
        per_tick_types[tick] = sorted(types_this_tick)

    return {
        "domains": domains,
        "social_events": social_events,
        "per_tick_counts": per_tick_counts,
        "per_tick_types": per_tick_types,
    }


def _diff(name_x, name_y, run_x, run_y, ticks):
    counts_x = run_x["per_tick_counts"]
    counts_y = run_y["per_tick_counts"]
    types_x = run_x["per_tick_types"]
    types_y = run_y["per_tick_types"]

    first_divergent_tick = None
    per_tick_signature_diff = {}
    for t in range(1, ticks + 1):
        if counts_x[t] != counts_y[t] or types_x[t] != types_y[t]:
            if first_divergent_tick is None:
                first_divergent_tick = t
            per_tick_signature_diff[str(t)] = {
                name_x: {"count": counts_x[t], "types": types_x[t]},
                name_y: {"count": counts_y[t], "types": types_y[t]},
            }

    social_x = run_x["social_events"]
    social_y = run_y["social_events"]
    social_events_identical = social_x == social_y

    diff_detail = []
    same_triple_diff_tick = []
    if not social_events_identical:
        set_x = {(e["tick"], e["event_type"], e["actor"], e["target"]) for e in social_x}
        set_y = {(e["tick"], e["event_type"], e["actor"], e["target"]) for e in social_y}
        only_x = sorted(set_x - set_y)
        only_y = sorted(set_y - set_x)
        for tup in only_x:
            diff_detail.append({"side": name_x + "_only", "tick": tup[0], "event_type": tup[1], "actor": tup[2], "target": tup[3]})
        for tup in only_y:
            diff_detail.append({"side": name_y + "_only", "tick": tup[0], "event_type": tup[1], "actor": tup[2], "target": tup[3]})

        # same (actor, target, event_type) triple occurring at a different tick
        triples_x = {}
        for e in social_x:
            triples_x.setdefault((e["event_type"], e["actor"], e["target"]), []).append(e["tick"])
        triples_y = {}
        for e in social_y:
            triples_y.setdefault((e["event_type"], e["actor"], e["target"]), []).append(e["tick"])
        common_triples = set(triples_x) & set(triples_y)
        for triple in sorted(common_triples):
            ticks_x = sorted(triples_x[triple])
            ticks_y = sorted(triples_y[triple])
            if ticks_x != ticks_y:
                same_triple_diff_tick.append({
                    "event_type": triple[0], "actor": triple[1], "target": triple[2],
                    name_x + "_ticks": ticks_x, name_y + "_ticks": ticks_y,
                })

    return {
        "first_divergent_tick": first_divergent_tick,
        "social_events_identical": social_events_identical,
        "social_event_count": {name_x: len(social_x), name_y: len(social_y)},
        "differing_social_events": diff_detail,
        "same_triple_different_tick": same_triple_diff_tick,
        "per_tick_signature_diff_sample": dict(list(per_tick_signature_diff.items())[:50]),
        "per_tick_signature_diff_count": len(per_tick_signature_diff),
    }


def probe(ticks=1000):
    scenario, configs = _derive_configs()

    runs = {}
    for name in ("A", "B", "C"):
        t0 = time.time()
        runs[name] = _run_config(scenario, configs[name], ticks)
        runs[name]["wall_clock_seconds"] = round(time.time() - t0, 2)

    a_vs_b = _diff("A", "B", runs["A"], runs["B"], ticks)
    b_vs_c = _diff("B", "C", runs["B"], runs["C"], ticks)
    a_vs_c = _diff("A", "C", runs["A"], runs["C"], ticks)

    result = {
        "ticks": ticks,
        "seed": SEED,
        "configs": {name: configs[name] for name in ("A", "B", "C")},
        "expected_configs": {"A": EXPECTED_A, "B": EXPECTED_B, "C": EXPECTED_C},
        "per_config": {
            name: {
                "domains": runs[name]["domains"],
                "social_event_count": len(runs[name]["social_events"]),
                "social_events": runs[name]["social_events"],
                "per_tick_counts": {str(t): runs[name]["per_tick_counts"][t] for t in range(1, ticks + 1)},
                "wall_clock_seconds": runs[name]["wall_clock_seconds"],
            }
            for name in ("A", "B", "C")
        },
        "final_state_hash": (
            "SKIPPED - core/hashing.py:state_content_hash requires a "
            "world_context_hash argument scoped to the fork-comparison "
            "contract; computing one outside that contract would be "
            "inventing a measurement, not reading one. Not reported."
        ),
        "a_vs_b": a_vs_b,
        "b_vs_c": b_vs_c,
        "a_vs_c": a_vs_c,
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    t0 = time.time()
    probe(tk)
    elapsed = time.time() - t0
    print(json.dumps({"wall_clock_seconds": round(elapsed, 2)}), file=sys.stderr)
