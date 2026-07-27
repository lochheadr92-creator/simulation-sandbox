"""Group-formation convergence check for Layer C Leg 2 (R1).

Decides one question and nothing else: does R1's measured reduction in Stage 7A
recognised groups CONVERGE toward baseline by the 3,000-tick acceptance horizon,
or is it a standing capability cost?

At 300 ticks, `collective_groups` recognised groups measured HEAD -> R1:
  living-agents-stage6       11 -> 7
  living-agents-stage6-alt   13 -> 8

Read-only. Patches nothing, mutates nothing, and only snapshots registry counts
at each 1,000-tick window boundary. Run the SAME script in a HEAD worktree and in
the modified tree; the only difference between arms is the domain code.

Usage:
  python -m tools._probe_group_formation_convergence <out.json> [ticks] [seed]
"""
from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import snapshot_for_hash
from core.rng import DeterministicRNG
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_state_contracts import GROUP_STATE_REGISTRY_ID
from scenarios import get_scenario


SEED = "living-agents-stage6"
SCENARIO = "collective_groups"
DEFAULT_TICKS = 3_000
WINDOW = 1_000


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = SCENARIO, output_path: Path | None = None) -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(seed, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(seed)
    cache: dict = {}
    accepted_by_type = Counter()
    actions_by_type = Counter()
    windows: list[dict] = []
    prev = {"ugss": 0, "cooperate": 0, "request_help": 0}
    started = time.perf_counter()

    for tick in range(1, ticks + 1):
        accepted, _rejected, order_index, _diag = run_tick(
            "probe-group-convergence", entities, world["terrain"], tick, rng,
            order_index, lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
            entity_json_cache=cache,
        )
        for event in accepted:
            valid_parent_ids.add(event["id"])
            accepted_by_type[str(event.get("event_type"))] += 1
            action = (event.get("living_action") or {}).get("action_type")
            if action:
                actions_by_type[action] += 1

        if tick % WINDOW == 0 or tick == ticks:
            association = entities.get(ASSOCIATION_REGISTRY_ID) or {}
            candidates = association.get("group_candidates") or {}
            group_state = entities.get(GROUP_STATE_REGISTRY_ID) or {}
            people = [e for e in entities.values() if e.get("type") == "person"]
            ugss = int(accepted_by_type.get("update_group_shared_state", 0))
            coop = int(actions_by_type.get("cooperate", 0))
            req = int(actions_by_type.get("request_help", 0))
            windows.append({
                "window_end_tick": int(tick),
                "recognised_groups": sum(
                    1 for g in candidates.values()
                    if g.get("recognition_state") == "recognised"),
                "group_candidates": len(candidates),
                "shared_group_states": len(group_state.get("groups") or {}),
                "update_group_shared_state_cumulative": ugss,
                "update_group_shared_state_in_window": ugss - prev["ugss"],
                "cooperate_cumulative": coop,
                "cooperate_in_window": coop - prev["cooperate"],
                "request_help_cumulative": req,
                "request_help_in_window": req - prev["request_help"],
                "alive_people": sum(1 for p in people if p.get("alive", True)),
                "elapsed_seconds": round(time.perf_counter() - started, 1),
            })
            prev = {"ugss": ugss, "cooperate": coop, "request_help": req}
            if output_path is not None:
                _write(output_path, _payload(seed, scenario_id, ticks, windows,
                                             entities, lineage_key, tick, "in_progress"))

    payload = _payload(seed, scenario_id, ticks, windows, entities, lineage_key,
                       ticks, "complete")
    if output_path is not None:
        _write(output_path, payload)
    return payload


def _payload(seed, scenario_id, ticks, windows, entities, lineage_key, tick, status) -> dict:
    return {
        "status": status,
        "probe": "layer-c-leg2-group-formation-convergence",
        "seed": seed, "scenario_id": scenario_id, "ticks": int(ticks),
        "schema_version": SCHEMA_VERSION, "engine_version": ENGINE_VERSION,
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, tick, lineage_key)),
        "windows": copy.deepcopy(windows),
    }


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[0]) if argv else Path("group_formation_convergence.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    seed = argv[2] if len(argv) > 2 else SEED
    result = probe(ticks=ticks, seed=seed, output_path=out)
    print(json.dumps({
        "seed": seed, "ticks": ticks, "status": result["status"],
        "final_state_hash": result["final_state_hash"],
        "windows": result["windows"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
