"""Acceptance-gate probe for Layer C Variety Leg 1 (Upkeep drive).

See scratchpad/UPKEEP-GATE-REVISED.md (authored 2026-07-24) for the gate this
implements: H=250 organic runs, no event capture. Runs a live per-tick loop
directly against core.kernel (like tools/_probe_repair_timing.py) instead of
tools.living_agent_harness's capture_events=True path -- this keeps memory and
per-run cost flat regardless of tick count, since accepted events are
inspected and tallied tick-by-tick and never accumulated into a list.

Read-only: builds genesis and steps the deterministic kernel; does not
mutate any source file. Reports rest fraction, N distinct actors and M
distinct shelters for the `tend` action, `repair` non-collapse, deaths, and
the final canonical hash (for the frozen living_settlement 320-tick
re-baseline). Determinism (repeat/replay/resume) is checked separately via
`python -m tools.living_agent_harness --repeat 2 [--resume-at N]`, which
already implements that comparison and defaults to capture_events=False.

Usage: python -m tools._probe_layer_c_upkeep_gate <scenario_id> <ticks> [seed]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario


def probe(scenario_id: str, ticks: int, seed: str = "living-agents-stage6") -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(seed, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(seed)

    actions_by_type = Counter()
    tend_actors = set()
    tend_targets = set()
    repair_targets = set()
    goals_by_actor = defaultdict(set)

    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        for e in accepted:
            valid_parent_ids.add(e["id"])
            la = e.get("living_action") or {}
            action_type = la.get("action_type")
            if action_type:
                actions_by_type[action_type] += 1
            if action_type in ("tend", "repair"):
                actor_id = e.get("entity_id")
                updates = (e.get("mutation") or {}).get("entity_updates", {})
                targets = {tid for tid in updates if tid != actor_id}
                if action_type == "tend":
                    tend_actors.add(actor_id)
                    tend_targets |= targets
                else:
                    repair_targets |= targets
        for actor_id, row in diag.items():
            if isinstance(row, dict) and row.get("selected_goal"):
                goals_by_actor[actor_id].add(row["selected_goal"])

    total_actions = sum(actions_by_type.values())
    rest_count = actions_by_type.get("rest", 0)
    tend_count = actions_by_type.get("tend", 0)
    repair_count = actions_by_type.get("repair", 0)
    deaths = sum(
        1 for e in entities.values()
        if e.get("type") == "person" and not e.get("alive", True)
    )
    alive_count = sum(1 for e in entities.values() if e.get("type") == "person" and e.get("alive", True))

    return {
        "scenario_id": scenario_id,
        "ticks": ticks,
        "seed": seed,
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, ticks, lineage_key)),
        "actions_by_type": dict(sorted(actions_by_type.items())),
        "total_actions": total_actions,
        "rest_count": rest_count,
        "rest_fraction": (rest_count / total_actions) if total_actions else None,
        "tend_count": tend_count,
        "tend_fraction": (tend_count / total_actions) if total_actions else None,
        "repair_count": repair_count,
        "repair_fraction": (repair_count / total_actions) if total_actions else None,
        "n_distinct_tend_actors": len(tend_actors),
        "m_distinct_tend_shelters": len(tend_targets),
        "m_distinct_repair_shelters": len(repair_targets),
        "deaths": deaths,
        "alive_count": alive_count,
        "distinct_action_type_count": len(actions_by_type),
        "goals_fired": sorted({g for goals in goals_by_actor.values() for g in goals}),
    }


def main() -> int:
    scenario_id = sys.argv[1]
    ticks = int(sys.argv[2])
    seed = sys.argv[3] if len(sys.argv) > 3 else "living-agents-stage6"
    result = probe(scenario_id, ticks, seed)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
