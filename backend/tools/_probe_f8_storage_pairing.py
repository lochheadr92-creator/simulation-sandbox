"""F8 gate-3 cause: WHY is no `shared_storage` association evidence ever derived?

Distinguishes three candidates recorded in memory/REGISTRY-COMPONENT-OWNERSHIP.md:

  (a) the evidence rule counts food stores only, so wood stores never qualify;
  (b) the rule is resource-agnostic, but no two agents ever hold a storage
      action on the SAME storage with started_tick within 4 of each other;
  (c) only one distinct agent ever performs a storage action at all.

(a) is answerable by code-read alone -- association_contracts.py:303-316 tests
`left_action["type"] in {"store","retrieve","access"}` and never inspects the
resource. This probe settles (b) vs (c) by MEASUREMENT.

It replicates the rule exactly rather than approximating it: the association
domain reads each person's CURRENT committed action (`_accepted_action`, i.e.
`action.accepted_event_id` present) and compares pairs at each tick. So this
replays the accepted-event stream in canonical commit order, maintains each
person's current action, and evaluates the real predicate every tick.

Read-only. Usage:
  PYTHONPATH=. python -m tools._probe_f8_storage_pairing <out.json> [ticks]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations

from tools.living_agent_harness import run_living_agent_harness

SEED = "living-agents-stage6"
SCENARIO = "collective_groups"
STORAGE_ACTIONS = {"store", "retrieve", "access"}


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "probe_f8_pairing.json"
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    result = run_living_agent_harness(SEED, ticks=ticks, scenario_id=SCENARIO,
                                      capture_events=True, run_id="probe-f8-pair")
    entities = result["entities"]
    events = sorted(result["accepted_events"],
                    key=lambda e: (int(e.get("simulation_time", 0) or 0),
                                   int(e.get("order_index", -1) or -1)))

    def is_shared_storage(eid):
        e = entities.get(eid) or {}
        return (e.get("type") in ("storage", "container")
                and e.get("access") in ("shared", "public"))

    storage_events = []          # every committed storage action
    current: dict[str, dict] = {}  # person -> current committed action
    pair_hits = []               # ticks where the real predicate fires
    closest_gap = None           # smallest |tick delta| between two storers on one storage

    last_tick = -1
    for ev in events:
        tick = int(ev.get("simulation_time", 0) or 0)

        if tick != last_tick and last_tick >= 0:
            _evaluate(current, is_shared_storage, last_tick, pair_hits)
        last_tick = tick

        for eid, upd in ((ev.get("mutation") or {}).get("entity_updates") or {}).items():
            if not isinstance(upd, dict) or "action" not in upd:
                continue
            act = upd["action"]
            if not isinstance(act, dict):
                continue
            person = entities.get(eid) or {}
            if person.get("type") != "person":
                continue
            # Mirror _accepted_action: only committed actions count.
            merged = dict(act)
            merged.setdefault("accepted_event_id", ev.get("id"))
            current[eid] = merged
            if act.get("type") in STORAGE_ACTIONS:
                la = ev.get("living_action") or {}
                rt = la.get("resource_transfer") or {}
                storage_events.append({
                    "tick": tick, "person_id": eid, "type": act.get("type"),
                    "targets": list(act.get("target_entity_ids") or []),
                    "resource_kind": rt.get("resource_kind"),
                    "quantity": rt.get("quantity"),
                    "started_tick": act.get("started_tick"),
                })
    if last_tick >= 0:
        _evaluate(current, is_shared_storage, last_tick, pair_hits)

    storers = sorted({s["person_id"] for s in storage_events})
    by_storage: dict[str, list] = {}
    for s in storage_events:
        for t in s["targets"]:
            if is_shared_storage(t):
                by_storage.setdefault(t, []).append(s)

    # Smallest started_tick gap between two DIFFERENT agents on one shared storage.
    for sid, rows in by_storage.items():
        for a, b in combinations(rows, 2):
            if a["person_id"] == b["person_id"]:
                continue
            gap = abs(int(a["started_tick"] or a["tick"]) - int(b["started_tick"] or b["tick"]))
            if closest_gap is None or gap < closest_gap[0]:
                closest_gap = (gap, sid, a["person_id"], a["tick"], b["person_id"], b["tick"])

    if not storage_events:
        verdict = "NO_STORAGE_ACTIONS_AT_ALL"
    elif len(storers) < 2:
        verdict = "C_ONLY_ONE_DISTINCT_STORER"
    elif not any(len({r["person_id"] for r in rows}) >= 2 for rows in by_storage.values()):
        verdict = "C_VARIANT_NO_SHARED_STORAGE_HAD_TWO_DISTINCT_STORERS"
    elif not pair_hits:
        verdict = "B_TWO_STORERS_BUT_NEVER_WITHIN_4_TICKS"
    else:
        verdict = "PREDICATE_FIRED_evidence_should_exist"

    payload = {
        "seed": SEED, "scenario": SCENARIO, "ticks": ticks,
        "final_state_hash": result["final_state_hash"],
        "VERDICT": verdict,
        "resource_kind_filter_in_rule": False,
        "resource_kind_note": "association_contracts.py:303-316 tests action TYPE only; never inspects resource kind -- candidate (a) refuted by code-read",
        "storage_action_count": len(storage_events),
        "distinct_storers": storers,
        "distinct_storer_count": len(storers),
        "actions_by_type": dict(Counter(s["type"] for s in storage_events)),
        "actions_by_resource_kind": dict(Counter(str(s["resource_kind"]) for s in storage_events)),
        "shared_storages_touched": {
            sid: {
                "action_count": len(rows),
                "distinct_storers": sorted({r["person_id"] for r in rows}),
                "ticks": sorted(r["tick"] for r in rows)[:40],
            } for sid, rows in sorted(by_storage.items())
        },
        "closest_cross_agent_gap": (
            {"gap_ticks": closest_gap[0], "storage": closest_gap[1],
             "person_a": closest_gap[2], "tick_a": closest_gap[3],
             "person_b": closest_gap[4], "tick_b": closest_gap[5]}
            if closest_gap else None
        ),
        "predicate_fired_ticks": pair_hits[:40],
        "first_20_storage_actions": storage_events[:20],
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(json.dumps({k: v for k, v in payload.items()
                      if k not in ("first_20_storage_actions",)}, indent=2, default=str))


def _evaluate(current, is_shared_storage, tick, pair_hits):
    """The real predicate from association_contracts.py:303-316."""
    ids = sorted(current)
    for left_id, right_id in combinations(ids, 2):
        la, ra = current[left_id], current[right_id]
        if la.get("type") not in STORAGE_ACTIONS or ra.get("type") not in STORAGE_ACTIONS:
            continue
        lt = int(la.get("started_tick", -1) or -1)
        rt = int(ra.get("started_tick", -1) or -1)
        shared = sorted(set(la.get("target_entity_ids") or [])
                        & set(ra.get("target_entity_ids") or []))
        if abs(lt - rt) <= 4 and shared and is_shared_storage(shared[0]):
            pair_hits.append({"tick": tick, "pair": [left_id, right_id],
                              "storage": shared[0], "started_ticks": [lt, rt]})


if __name__ == "__main__":
    main()
