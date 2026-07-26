"""F8 diagnostic: WHY does `group_collective` never propose?

Distinguishes the two candidate causes recorded in
memory/REGISTRY-COMPONENT-OWNERSHIP.md:

  (1) the registries never materialise, so select_due_ids
      (group_collective_domain.py:24-27) returns [] and the domain never
      activates at all; versus
  (2) the registries exist and the domain activates, but eligibility never
      coincides -- no two members simultaneously adjacent to the shared
      storage while carrying a resource.

Read-only. Runs the recorded harness invocation, then walks the eligibility
chain on the FINAL committed state in the same order the domain does, reporting
the first gate that fails. Probes observe; they never seed behaviour.

Usage: PYTHONPATH=. python -m tools._probe_f8_collective_preconditions <out.json> [ticks]
"""
from __future__ import annotations

import json
import sys

from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_state_contracts import GROUP_STATE_REGISTRY_ID
from domains.group_collective_contracts import (
    _recognised_groups,
    _shared_storage_facts,
    derive_coordinated_deposits,
    eligible_participants,
)
from tools.living_agent_harness import run_living_agent_harness

SEED = "living-agents-stage6"
SCENARIO = "collective_groups"


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "probe_f8.json"
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    result = run_living_agent_harness(SEED, ticks=ticks, scenario_id=SCENARIO,
                                      capture_events=True, run_id="probe-f8")
    entities = result["entities"]
    summary = result["summary"]

    assoc = entities.get(ASSOCIATION_REGISTRY_ID)
    gstate = entities.get(GROUP_STATE_REGISTRY_ID)

    # --- GATE 1: does the domain ever activate? -----------------------------
    gate1 = {
        "association_registry_present": assoc is not None,
        "group_state_registry_present": gstate is not None,
        "select_due_ids_would_return": (
            [GROUP_STATE_REGISTRY_ID] if (assoc is not None and gstate is not None) else []
        ),
    }

    # First tick each registry appears, reconstructed from the event stream.
    first_seen = {}
    for ev in sorted(result["accepted_events"],
                     key=lambda e: (int(e.get("simulation_time", 0) or 0),
                                    int(e.get("order_index", -1) or -1))):
        for eid in ((ev.get("mutation") or {}).get("entity_updates") or {}):
            if eid in (ASSOCIATION_REGISTRY_ID, GROUP_STATE_REGISTRY_ID):
                first_seen.setdefault(eid, int(ev.get("simulation_time", 0) or 0))
        for eid in ((ev.get("mutation") or {}).get("new_entities") or {}):
            if eid in (ASSOCIATION_REGISTRY_ID, GROUP_STATE_REGISTRY_ID):
                first_seen.setdefault(eid, int(ev.get("simulation_time", 0) or 0))
    gate1["first_tick_seen"] = first_seen

    # --- GATE 2: is any group RECOGNISED? -----------------------------------
    candidates = (assoc or {}).get("group_candidates") or {}
    states = {}
    for cand in candidates.values():
        states[cand.get("recognition_state")] = states.get(cand.get("recognition_state"), 0) + 1
    recognised = _recognised_groups(assoc or {})
    gate2 = {
        "group_candidates_total": len(candidates),
        "recognition_state_distribution": states,
        "recognised_group_count": len(recognised),
        "recognised_group_ids": sorted(recognised)[:10],
    }

    # --- GATE 3: does a recognised group hold a shared_storage fact? --------
    gate3 = {"groups_with_shared_storage_fact": {}, "all_fact_categories": {}}
    for gid, group in ((gstate or {}).get("groups") or {}).items():
        for fact in (group.get("facts") or {}).values():
            cat = fact.get("category")
            gate3["all_fact_categories"][cat] = gate3["all_fact_categories"].get(cat, 0) + 1
    for gid in recognised:
        facts = _shared_storage_facts(gstate or {}, gid)
        if facts:
            gate3["groups_with_shared_storage_fact"][gid] = [f.get("target_id") for f in facts]

    # --- GATE 4: are >=2 members eligible on the final state? ---------------
    gate4 = {}
    for gid, cand in sorted(recognised.items()):
        members = sorted(cand.get("member_ids") or [])
        for facts in (_shared_storage_facts(gstate or {}, gid),):
            for fact in facts:
                sid = fact.get("target_id")
                rows = eligible_participants(entities, members, sid)
                gate4[f"{gid}|{sid}"] = {
                    "members": len(members),
                    "eligible": len(rows),
                    "eligible_ids": [r["person_id"] for r in rows],
                }

    # --- GATE 5: would a deposit be derived right now? ----------------------
    derived = derive_coordinated_deposits(entities, ticks)

    # First gate that fails, in the domain's own order.
    if not (gate1["association_registry_present"] and gate1["group_state_registry_present"]):
        blocked_at = "GATE1_domain_never_activates_registries_missing"
    elif gate2["recognised_group_count"] == 0:
        blocked_at = "GATE2_no_group_ever_recognised"
    elif not gate3["groups_with_shared_storage_fact"]:
        blocked_at = "GATE3_no_shared_storage_fact"
    elif not any(v["eligible"] >= 2 for v in gate4.values()):
        blocked_at = "GATE4_fewer_than_two_eligible_participants"
    elif not derived:
        blocked_at = "GATE5_derive_returned_nothing"
    else:
        blocked_at = "NONE_would_propose_on_final_state"

    payload = {
        "seed": SEED, "scenario": SCENARIO, "ticks": ticks,
        "final_state_hash": result["final_state_hash"],
        "collective_accepted": summary.get("stage7c", {}).get("accepted_count"),
        "collective_rejected": summary.get("stage7c", {}).get("rejected_count"),
        "BLOCKED_AT": blocked_at,
        "gate1_domain_activation": gate1,
        "gate2_recognition": gate2,
        "gate3_shared_storage_fact": gate3,
        "gate4_eligibility": gate4,
        "gate5_derived_deposits": len(derived),
        "max_state_counts": {
            k: summary.get("max_state_counts", {}).get(k)
            for k in ("association_records", "group_candidates", "dissolved_groups",
                      "shared_group_states", "shared_group_facts",
                      "collective_processed_keys", "collective_storage_content_units")
        },
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
