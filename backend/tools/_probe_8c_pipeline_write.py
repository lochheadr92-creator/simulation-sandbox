"""Stage 8C — pipeline two-entity write probe (core-integrity escalation).

Tests the commit pipeline DIRECTLY, by EXECUTION, not by reading domain code.
It constructs synthetic proposals (plain dicts, the same shape domains emit)
and hands them to `run_commit_frame`, then reports what persists in `entities`
for actor vs non-actor updates, and whether a second same-frame write to the
same top-level field silently overwrites the first.

Read-only w.r.t. engine source: NO engine/domain/kernel/core file modified,
NO monkey-patch, NO domain engine invoked. It imports only the public commit
entry (`run_commit_frame`), `build_genesis`, and `DomainOutput`.

Goal — distinguish, with execution evidence:
  (a) the pipeline silently discards writes to entities outside the proposer's
      touched scope (a GENERAL discard);
  (b) a write persists at commit and is overwritten later in the same frame by
      another write to the same field (a LOST UPDATE);
  (c) something else.

Usage: python -m tools._probe_8c_pipeline_write <output_json_abspath>
"""
from __future__ import annotations

import copy
import json
import sys

from core.kernel import build_genesis
from core.commit_pipeline import run_commit_frame
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from domains.base import DomainOutput
from scenarios import get_scenario

SEED = "living-agents-stage6"
SCENARIO_ID = "collective_groups"


def _fresh():
    scenario = get_scenario(SCENARIO_ID)
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    _world, entities, _genesis, _rej, _order = build_genesis(SEED, scenario, lineage_key)
    return entities, lineage_key


def _prop(entity_id, touched, entity_updates, *, priority, preconditions=None):
    """A minimal proposal with NO domain payload, so every domain validator
    early-returns None (off-type) and only generic scope/precondition/causality
    checks apply. is_exogenous=True skips the causal-parent requirement."""
    return {
        "proposal_family": "syn", "proposal_type": "syn_test",
        "proposer_engine_id": "syn", "proposer_engine_version": "1.0.0",
        "entity_id": entity_id, "requested_time": 1, "phase": "agent",
        "engine_priority": priority, "is_exogenous": True,
        "causal_parent_event_ids": [],
        "touched_scope": touched, "preconditions": preconditions or [],
        "mutation": {"entity_updates": entity_updates, "new_entities": {}},
    }


def _run(entities, proposals, lineage_key):
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=proposals)], 1, lineage_key, "syn", 0, "frame-syn",
    )
    return accepted, rejected


def _syn_commit():
    return {"commitment_id": "SYN-COMMIT", "commitment_kind": "request_help",
            "creator_id": "person-007", "beneficiary_id": "person-001",
            "status": "pending", "last_changed_tick": 1}


def _has_syn(entity):
    la = (entity or {}).get("living_agent") or {}
    return "SYN-COMMIT" in (la.get("commitments") or {})


def main():
    results = {}

    # ---- SUB-TEST 1 : non-actor entity_update, IN touched_scope. Tests (a). ----
    entities, lk = _fresh()
    p = _prop("person-007", ["person-007", "person-001"],
              {"person-007": {"syn_actor": "A"}, "person-001": {"syn_nonactor": "B"}},
              priority=10)
    acc, rej = _run(entities, [p], lk)
    results["subtest1_nonactor_in_scope"] = {
        "accepted": len(acc), "rejected_reason_codes": [r["reason_code"] for r in rej],
        "actor_field_persisted": entities["person-007"].get("syn_actor") == "A",
        "nonactor_field_persisted": entities["person-001"].get("syn_nonactor") == "B",
    }

    # ---- SUB-TEST 2a : single proposal delivers a commitment to a non-actor beneficiary. ----
    entities, lk = _fresh()
    la0 = copy.deepcopy(entities["person-001"].get("living_agent"))
    la_with = copy.deepcopy(la0) if isinstance(la0, dict) else {}
    la_with["commitments"] = dict((la_with.get("commitments") or {}))
    la_with["commitments"]["SYN-COMMIT"] = _syn_commit()
    p_aid = _prop("person-007", ["person-007", "person-001"],
                  {"person-007": {"syn_marker": "aid"}, "person-001": {"living_agent": la_with}},
                  priority=10,
                  preconditions=[{"entity_id": "person-001", "field": "living_agent", "op": "eq", "value": la0}])
    acc, rej = _run(entities, [p_aid], lk)
    results["subtest2a_delivery_alone"] = {
        "accepted": len(acc), "rejected_reason_codes": [r["reason_code"] for r in rej],
        "beneficiary_has_SYN_COMMIT": _has_syn(entities["person-001"]),
    }

    # ---- SUB-TEST 2b : same delivery + a LATER same-frame write to person-001.living_agent
    #                    (no living_agent guard). Tests (b) lost update. ----
    entities, lk = _fresh()
    la0 = copy.deepcopy(entities["person-001"].get("living_agent"))
    la_with = copy.deepcopy(la0) if isinstance(la0, dict) else {}
    la_with["commitments"] = dict((la_with.get("commitments") or {}))
    la_with["commitments"]["SYN-COMMIT"] = _syn_commit()
    la_stale = copy.deepcopy(la0)   # a rebuild from the frame snapshot, WITHOUT SYN-COMMIT
    p_aid = _prop("person-007", ["person-007", "person-001"],
                  {"person-007": {"syn_marker": "aid"}, "person-001": {"living_agent": la_with}},
                  priority=10,
                  preconditions=[{"entity_id": "person-001", "field": "living_agent", "op": "eq", "value": la0}])
    p_over = _prop("person-001", ["person-001"],
                   {"person-001": {"living_agent": la_stale}},
                   priority=20, preconditions=[])   # commits AFTER p_aid; NO living_agent guard
    acc, rej = _run(entities, [p_aid, p_over], lk)
    results["subtest2b_same_frame_overwrite"] = {
        "accepted": len(acc),
        "rejected": [(r["entity_id"], r["reason_code"]) for r in rej],
        "aid_accepted": any(e.get("entity_id") == "person-007" for e in acc),
        "overwrite_accepted": any(e.get("entity_id") == "person-001" for e in acc),
        "beneficiary_still_has_SYN_COMMIT_after_frame": _has_syn(entities["person-001"]),
    }

    # ---- SUB-TEST 3 : entity_update OUTSIDE touched_scope. Characterises (a). ----
    entities, lk = _fresh()
    p3 = _prop("person-007", ["person-007"],   # person-002 NOT in touched_scope
               {"person-007": {"syn_x": 1}, "person-002": {"syn_outside": 1}},
               priority=10)
    acc, rej = _run(entities, [p3], lk)
    results["subtest3_out_of_scope_write"] = {
        "accepted": len(acc), "rejected_reason_codes": [r["reason_code"] for r in rej],
        "out_of_scope_field_persisted": entities["person-002"].get("syn_outside") == 1,
    }

    # ---- classification ----
    s1 = results["subtest1_nonactor_in_scope"]
    s2a = results["subtest2a_delivery_alone"]
    s2b = results["subtest2b_same_frame_overwrite"]
    verdict = "undetermined"
    if s1["accepted"] and not s1["nonactor_field_persisted"]:
        verdict = "(a) pipeline discards non-actor writes"
    elif (s1["nonactor_field_persisted"] and s2a["beneficiary_has_SYN_COMMIT"]
          and s2b["aid_accepted"] and s2b["overwrite_accepted"]
          and not s2b["beneficiary_still_has_SYN_COMMIT_after_frame"]):
        verdict = "(b) lost update: validated write persists at commit, overwritten by a later same-frame write to the same field"
    results["VERDICT"] = verdict

    out = sys.argv[1] if len(sys.argv) > 1 else "probe_8c_pipeline_write.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
