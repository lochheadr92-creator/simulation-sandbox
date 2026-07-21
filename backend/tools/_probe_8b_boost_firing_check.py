"""Stage 8B Leg 1 decisive diagnostic: does `_apply_group_norm_influence`'s
REPAIR_SHELTER boost (`_boost_score`, living_settlement_domain.py:235) ever
actually fire (change a candidate's decisive score) across a real 1000-tick
collective_groups run with the CURRENT scenario config (group_carriage
enabled, as committed in the working tree)?

Read-only: wraps `_apply_group_norm_influence` exactly in the style of
tools/_probe_8b_leg1.py's `_wrapped_norm_influence`, but instead of merely
recording which ticks carry a REPAIR_SHELTER candidate, it snapshots each
REPAIR_SHELTER candidate's decisive score (`_effective_score`: score_total if
present, else score) BEFORE calling the original function and compares it to
the same candidate object's score AFTER. `_boost_score` mutates candidate
dicts in place and `_apply_group_norm_influence` returns the same list
object, so a before/after diff by object identity is bit-exact.

Does not modify living_settlement_domain.py, group_carriage_contracts.py, or
scenarios/collective_groups.py. Observation only.

Usage: python -m tools._probe_8b_boost_firing_check [ticks]
"""
from __future__ import annotations

import json
import sys
import time

import domains.living_settlement_domain as lsd
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario

SEED = "living-agents-stage6"

_orig_norm_influence = lsd._apply_group_norm_influence
_effective_score = lsd._effective_score

firings = []          # {tick, entity_id, target_entity_id, score_before, score_after}
_current_tick = None  # set by the tick loop, read by the wrapper


def _wrapped_norm_influence(candidates, entity_id, entities, tick):
    before = {}
    for c in candidates:
        if c.get("goal") == "REPAIR_SHELTER":
            before[id(c)] = (c.get("target_entity_id"), _effective_score(c))
    result = _orig_norm_influence(candidates, entity_id, entities, tick)
    for c in result:
        if c.get("goal") != "REPAIR_SHELTER":
            continue
        key = id(c)
        if key not in before:
            continue  # candidate object added by the call itself (never happens; influence never creates)
        target_before, score_before = before[key]
        score_after = _effective_score(c)
        if score_after != score_before:
            firings.append({
                "tick": int(tick),
                "entity_id": entity_id,
                "target_entity_id": c.get("target_entity_id", target_before),
                "score_before": score_before,
                "score_after": score_after,
            })
    return result


def probe(ticks=1000):
    lsd._apply_group_norm_influence = _wrapped_norm_influence
    scenario = get_scenario("collective_groups")
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        for e in accepted:
            valid_parent_ids.add(e["id"])

    firing_ticks = sorted({f["tick"] for f in firings})
    distinct_entities = sorted({f["entity_id"] for f in firings})
    distinct_targets = sorted({f["target_entity_id"] for f in firings})

    result = {
        "ticks": ticks,
        "enabled_domains": list(scenario.enabled_domains),
        "boost_firing_check": {
            "firing_count": len(firings),
            "firing_tick_count": len(firing_ticks),
            "firing_ticks": firing_ticks,
            "distinct_entities_boosted": len(distinct_entities),
            "distinct_entities": distinct_entities,
            "distinct_targets": len(distinct_targets),
            "distinct_target_entities": distinct_targets,
            "firings": firings,
        },
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    t0 = time.time()
    probe(tk)
    elapsed = time.time() - t0
    print(json.dumps({"wall_clock_seconds": round(elapsed, 2)}), file=sys.stderr)
