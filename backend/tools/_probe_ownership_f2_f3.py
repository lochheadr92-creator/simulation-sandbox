"""Ownership-registry probe: do F2 (storage `contents` lost update) and F3
(`group_collective` clobbers person `action`) actually FIRE in an organic run?

Read-only. Modifies no simulation code, no domain, no kernel. Runs the
recorded harness invocation (seed `living-agents-stage6`, scenario
`collective_groups`) with `capture_events=True` and scans the resulting
accepted-event stream post-hoc. Probes observe; they never seed behaviour.

The scan is a pure replay of committed writes in canonical commit order
(`simulation_time`, then `order_index`) -- the same order Core applied them --
so a detected loss is the loss Core actually committed, not a reconstruction.

Questions
  F2  Does any tick commit two writes to the same storage `contents`, and does
      the later write (group_collective, prio 90) drop units the earlier write
      (living_settlement STORE_SURPLUS, prio 10) had just added?
        -> running-state replay: if written[k] < running[k], that many units of
           an already-committed deposit were reverted.
  F3  Does any tick commit two writes to the same person `action`, with
      group_collective overwriting an action living_settlement already
      committed? Registry's named discriminating case: the overwritten action
      is resource-free (rest / drink / move / social), so the collective's
      carried_resources CAS still passes.
        -> also checks whether the overwriting event rewrites `living_agent`.
           If it does not, `current_decision` / `causal_links` survive pointing
           at an action that never happened (the explanation-guarantee hit).
  CENSUS  Same-tick, same-entity, same-top-level-key multi-writer count across
      every field, for later F1/F4 disposition. Free with the same pass.

Both answers double as the gate-tier decision: a CAS whose collision never
fires in a frozen scenario is a hash-neutral repair; one that fires is
re-baseline-class.

Usage: PYTHONPATH=. python -m tools._probe_ownership_f2_f3 <out_json_abspath> [ticks]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

from tools.living_agent_harness import run_living_agent_harness

SEED = "living-agents-stage6"
SCENARIO_ID = "collective_groups"
DEFAULT_TICKS = 1000

# Actions that touch no carried resource -> the collective's carried_resources
# CAS still passes over them. Registry F3 names `rest` as the discriminator.
RESOURCE_FREE_PREFIXES = ("rest", "drink", "move", "social", "talk", "observe", "idle")


def _updates(event):
    return ((event.get("mutation") or {}).get("entity_updates") or {})


def _ordered(events):
    """Canonical commit order. Genesis events carry no order_index."""
    return sorted(events, key=lambda e: (int(e.get("simulation_time", 0) or 0),
                                         int(e.get("order_index", -1) or -1)))


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "probe_ownership_f2_f3.json"
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TICKS

    result = run_living_agent_harness(
        SEED, ticks=ticks, scenario_id=SCENARIO_ID, capture_events=True,
        run_id="probe-ownership-f2-f3",
    )
    events = _ordered(result["accepted_events"])

    # ---- running replay of storage contents (F2) ----------------------------
    running_contents: dict[str, dict] = {}
    f2_hits = []

    # ---- per-tick action writers (F3) --------------------------------------
    action_writes: dict[tuple[int, str], list] = defaultdict(list)

    # ---- census ------------------------------------------------------------
    key_writers: dict[tuple[int, str, str], list] = defaultdict(list)

    for ev in events:
        tick = int(ev.get("simulation_time", 0) or 0)
        engine = ev.get("proposer_engine_id")
        oidx = ev.get("order_index")
        for eid, upd in _updates(ev).items():
            if not isinstance(upd, dict):
                continue
            for key in upd:
                key_writers[(tick, eid, key)].append(engine)

            if "contents" in upd and isinstance(upd["contents"], dict):
                written = {k: int(v or 0) for k, v in upd["contents"].items()
                           if isinstance(v, (int, float))}
                prev = running_contents.get(eid)
                if prev is not None:
                    lost = {k: prev[k] - written.get(k, 0)
                            for k in prev if written.get(k, 0) < prev[k]}
                    if lost:
                        f2_hits.append({
                            "tick": tick, "storage_id": eid,
                            "overwriting_engine": engine, "order_index": oidx,
                            "event_id": ev.get("id"),
                            "contents_before_this_write": dict(prev),
                            "contents_written": dict(written),
                            "units_lost_by_key": lost,
                        })
                running_contents[eid] = written

            if "action" in upd and isinstance(upd["action"], dict):
                action_writes[(tick, eid)].append({
                    "engine": engine, "order_index": oidx,
                    "event_id": ev.get("id"),
                    "action_type": upd["action"].get("type"),
                    "rewrote_living_agent": "living_agent" in upd,
                    "current_decision_action_id": (
                        ((upd.get("living_agent") or {}).get("current_decision") or {})
                        .get("action_id")),
                })

    # ---- F3: same tick, same person, >1 action write ------------------------
    f3_hits = []
    for (tick, pid), writes in sorted(action_writes.items()):
        if len(writes) < 2:
            continue
        writes = sorted(writes, key=lambda w: (w["order_index"] is None, w["order_index"]))
        final = writes[-1]
        if final["engine"] != "group_collective":
            continue
        overwritten = writes[-2]
        atype = (overwritten["action_type"] or "")
        f3_hits.append({
            "tick": tick, "person_id": pid,
            "overwritten_action_type": overwritten["action_type"],
            "overwritten_by_engine": final["engine"],
            "overwritten_was_resource_free": atype.lower().startswith(RESOURCE_FREE_PREFIXES),
            "overwriter_rewrote_living_agent": final["rewrote_living_agent"],
            "stale_current_decision_action_id": overwritten["current_decision_action_id"],
            "writes_in_order": writes,
        })

    # ---- census -------------------------------------------------------------
    multi = {k: v for k, v in key_writers.items() if len(v) > 1}
    census = Counter()
    census_engines = defaultdict(Counter)
    for (tick, eid, key), engines in multi.items():
        census[key] += 1
        census_engines[key][" + ".join(sorted(set(engines)))] += 1

    f3_resource_free = [h for h in f3_hits if h["overwritten_was_resource_free"]]

    summary = {
        "seed": SEED, "scenario_id": SCENARIO_ID, "ticks": ticks,
        "final_state_hash": result["final_state_hash"],
        "accepted_event_count": result["summary"]["accepted_event_count"],
        "collective_accepted_count": result["summary"].get("stage7c", {}).get("accepted_count"),
        # Discriminates "never proposed" from "proposed and always rejected" --
        # decides whether F2/F3 are unreachable because the collision never
        # arises, or because every collective proposal dies first.
        "stage7c_block": result["summary"].get("stage7c"),
        "F2_storage_contents_lost_update": {
            "fired": bool(f2_hits), "occurrences": len(f2_hits),
            "total_units_lost": sum(sum(h["units_lost_by_key"].values()) for h in f2_hits),
            "ticks": sorted({h["tick"] for h in f2_hits})[:40],
        },
        "F3_action_clobber": {
            "fired": bool(f3_hits), "occurrences": len(f3_hits),
            "resource_free_occurrences": len(f3_resource_free),
            "overwritten_action_types": dict(Counter(
                h["overwritten_action_type"] for h in f3_hits)),
            "dangling_decision_receipts": sum(
                1 for h in f3_hits if not h["overwriter_rewrote_living_agent"]),
            "ticks": sorted({h["tick"] for h in f3_hits})[:40],
        },
        "census_multi_writer_same_tick_same_entity_same_key": dict(census.most_common()),
        "census_engine_pairs": {k: dict(v) for k, v in census_engines.items()},
    }

    payload = {
        "summary": summary,
        "F2_hits": f2_hits[:40],
        "F3_hits": f3_hits[:40],
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
