"""Stage 8A evidence tooling: when do shelter repairs happen vs when are norms
active?

Counts committed `repair`/`construct` actions on shelter/structure targets per
100-tick bin, records the ticks any agent repaired a shared shelter, and the norm
formation ticks - to see whether the repeated behaviour has ceased by the time the
norm crystallises (which would explain zero organic influence firings).

Usage: python -m tools._probe_repair_timing [ticks]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario
from domains.group_norm_contracts import GROUP_NORM_REGISTRY_ID

SEED = "living-agents-stage6"


def probe(ticks=1000):
    scenario = get_scenario("collective_groups")
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    repair_bins = defaultdict(int)     # 100-tick bin -> repair action count
    repair_targets = defaultdict(int)  # target shelter id -> repair count
    repair_ticks = []                  # ticks with any shelter repair
    norm_formation_ticks = []
    last_repair_tick = None

    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        for e in accepted:
            valid_parent_ids.add(e["id"])
            la = e.get("living_action") or {}
            action_type = la.get("action_type") or e.get("event_type")
            # committed physical actions carry a living_action with action_type
            if action_type in ("repair",):
                # find the shelter target in the mutation entity_updates
                updates = (e.get("mutation") or {}).get("entity_updates", {})
                for tid, upd in updates.items():
                    if "condition" in upd:
                        repair_bins[tick // 100] += 1
                        repair_targets[tid] += 1
                        repair_ticks.append(tick)
                        last_repair_tick = tick
            if e.get("event_type") == "group_form_norm":
                meta = e.get("group_norm_update") or {}
                for t in meta.get("transitions") or []:
                    if t.get("kind") == "formed":
                        norm_formation_ticks.append(tick)

    print(json.dumps({
        "ticks": ticks,
        "total_shelter_repairs": len(repair_ticks),
        "repairs_by_100tick_bin": {str(k * 100): v for k, v in sorted(repair_bins.items())},
        "repairs_by_target": dict(sorted(repair_targets.items())),
        "first_repair_tick": repair_ticks[0] if repair_ticks else None,
        "last_repair_tick": last_repair_tick,
        "norm_formation_ticks": norm_formation_ticks,
        "repairs_after_first_norm": sum(
            1 for t in repair_ticks if norm_formation_ticks and t >= norm_formation_ticks[0]),
    }, indent=2))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    probe(tk)
