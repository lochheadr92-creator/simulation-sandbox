"""Core-integrity probe: death-path exposure to F1, touched_scope enforcement
(F2), and frame-ordering determinism.

Read-only w.r.t. engine source. Uses ONLY synthetic proposals handed to the
public commit entry `run_commit_frame`. NO engine/domain/kernel/core file
modified, NO monkey-patch, NO domain engine invoked.

Faithful shapes (constructed to match, cited, not imported):
  death proposal   -> lifecycle_domain.py:151-172 (alive=False, current_goal
                      "DEAD", health=0, ...; precondition {alive eq True})
  HELP health write-> living_agent_actions.py:484-486 (target health/energy;
                      adjacency guard only, NO health-eq precondition)

Questions:
  D1  does a death proposal apply fully in isolation? (baseline)
  D2  death then a later same-entity health write -> can it end alive=False
      with NON-ZERO health? (corrupted death)
  D3  the reverse ordering.
  D4  death then a later alive=True write -> does the pipeline permit un-kill?
      (structural; note no real domain writes person alive=True)
  DET run D2 twice -> identical final state? (frame-ordering determinism)
  F2  a write to an entity NOT in touched_scope -> does it persist?

Usage: python -m tools._probe_core_integrity_death_scope <output_json_abspath>
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
    return {
        "proposal_family": "syn", "proposal_type": "syn_test",
        "proposer_engine_id": "syn", "proposer_engine_version": "1.0.0",
        "entity_id": entity_id, "requested_time": 1, "phase": "agent",
        "engine_priority": priority, "is_exogenous": True,
        "causal_parent_event_ids": [],
        "touched_scope": touched, "preconditions": preconditions or [],
        "mutation": {"entity_updates": entity_updates, "new_entities": {}},
    }


def _death_updates():
    # Mirrors lifecycle_domain.py:165-172 (top-level fields).
    return {"alive": False, "current_goal": "DEAD", "health": 0,
            "death_cause": "syn_starvation", "death_tick": 1,
            "action": {"type": "death", "status": "completed"},
            "plan": {"goal": None, "steps": [], "step_index": 0, "status": "abandoned"}}


def _death_prop(eid, priority):
    return _prop(eid, [eid], {eid: _death_updates()}, priority=priority,
                 preconditions=[{"entity_id": eid, "field": "alive", "op": "eq", "value": True}])


def _help_prop(actor, victim, priority):
    # Mirrors living_agent_actions.py:484-486 (target health/energy; adjacency
    # guard only, NO health-eq precondition -> reproduced as no precondition).
    return _prop(actor, [actor, victim], {victim: {"health": 500, "energy": 900}}, priority=priority)


def _run(entities, proposals, lineage_key):
    accepted, rejected, _ = run_commit_frame(
        entities, [DomainOutput(proposals=proposals)], 1, lineage_key, "syn", 0, "frame-syn")
    return accepted, rejected


def _snap(entities, eid):
    e = entities.get(eid) or {}
    return {"alive": e.get("alive"), "current_goal": e.get("current_goal"),
            "health": e.get("health"), "death_cause": e.get("death_cause")}


def main():
    X, Y = "person-007", "person-001"
    results = {}

    # D1 - death alone (baseline)
    entities, lk = _fresh()
    acc, rej = _run(entities, [_death_prop(X, 10)], lk)
    results["D1_death_alone"] = {"accepted": len(acc), "rejected": [r["reason_code"] for r in rej],
                                 "final": _snap(entities, X)}

    # D2 - death (first) then health write (later) -> corrupted death?
    entities, lk = _fresh()
    acc, rej = _run(entities, [_death_prop(X, 10), _help_prop(Y, X, 20)], lk)
    fx = _snap(entities, X)
    results["D2_death_then_health"] = {
        "accepted": len(acc), "rejected": [(r["entity_id"], r["reason_code"]) for r in rej],
        "final": fx,
        "corrupted_death_alive_false_health_nonzero": fx["alive"] is False and (fx["health"] or 0) != 0}

    # D3 - health write (first) then death (later) -> consistent?
    entities, lk = _fresh()
    acc, rej = _run(entities, [_help_prop(Y, X, 10), _death_prop(X, 20)], lk)
    fx = _snap(entities, X)
    results["D3_health_then_death"] = {
        "accepted": len(acc), "rejected": [(r["entity_id"], r["reason_code"]) for r in rej],
        "final": fx, "consistent_death_health_zero": fx["alive"] is False and (fx["health"] or 0) == 0}

    # D4 - death then alive=True write -> does the pipeline permit un-kill?
    entities, lk = _fresh()
    resurrect = _prop(X, [X], {X: {"alive": True}}, priority=20)
    acc, rej = _run(entities, [_death_prop(X, 10), resurrect], lk)
    fx = _snap(entities, X)
    results["D4_death_then_resurrect"] = {
        "accepted": len(acc), "final": fx,
        "pipeline_permits_unkill_alive_true": fx["alive"] is True,
        "note": "structural only; grep shows NO domain writes alive=True on an existing person"}

    # DET - run D2 twice, compare final state (frame-ordering determinism)
    e1, lk1 = _fresh(); _run(e1, [_death_prop(X, 10), _help_prop(Y, X, 20)], lk1)
    e2, lk2 = _fresh(); _run(e2, [_death_prop(X, 10), _help_prop(Y, X, 20)], lk2)
    results["DET_frame_ordering_determinism"] = {
        "run1_final": _snap(e1, X), "run2_final": _snap(e2, X),
        "identical": _snap(e1, X) == _snap(e2, X)}

    # F2 - write to an entity NOT in touched_scope -> persists? (containment gap)
    entities, lk = _fresh()
    p = _prop(X, [X], {X: {"syn_self": 1}, "person-002": {"syn_out_of_scope": 1}}, priority=10)
    acc, rej = _run(entities, [p], lk)
    results["F2_out_of_scope_write"] = {
        "accepted": len(acc), "rejected": [r["reason_code"] for r in rej],
        "declared_touched_scope": [X],
        "wrote_undeclared_entity_person_002": entities["person-002"].get("syn_out_of_scope") == 1}

    out = sys.argv[1] if len(sys.argv) > 1 else "probe_core_integrity_death_scope.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
