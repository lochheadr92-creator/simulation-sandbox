"""Stage 8A evidence tooling: influence-firing + registry-capacity probe.

Runs the real committed collective_groups tick loop with the group_norm domain
enabled, wrapping living_settlement_domain._apply_group_norm_influence (and the 7D
goal hook) to count how many times each influence actually boosts a REPAIR_SHELTER
candidate (a real firing) and on how many distinct ticks, plus norm formation
timing, the peak serialized size of the group-norm registry (capacity headroom),
and survival/deaths. Grounds the gate-5 "organic firing Deferred" record and the
registry capacity claim in CAPABILITY-STAGE-8A-EMERGENT-NORMS.md.

Usage: python -m tools._probe_norm_influence [ticks]
"""
from __future__ import annotations

import json
import sys

import domains.living_settlement_domain as lsd
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_json
from scenarios import get_scenario
from domains.group_norm_contracts import GROUP_NORM_REGISTRY_ID, LIMITS

SEED = "living-agents-stage6"

_fire_count = [0]
_fire_ticks = set()
_orig = lsd._apply_group_norm_influence

_goal_fire_count = [0]
_goal_fire_ticks = set()
_orig_goal = lsd._apply_group_goal_influence

# Count how often ANY REPAIR_SHELTER candidate is even present (upper bound on
# what either influence could ever boost).
_repair_cand_ticks = set()


def _wrapped(candidates, entity_id, entities, tick):
    if any(c.get("goal") == "REPAIR_SHELTER" for c in candidates):
        _repair_cand_ticks.add(int(tick))
    before = [int(c.get("score", 0)) for c in candidates]
    out = _orig(candidates, entity_id, entities, tick)
    after = [int(c.get("score", 0)) for c in out]
    if before != after:
        _fire_count[0] += 1
        _fire_ticks.add(int(tick))
    return out


def _wrapped_goal(candidates, entity_id, entities, tick):
    before = [int(c.get("score", 0)) for c in candidates]
    out = _orig_goal(candidates, entity_id, entities, tick)
    after = [int(c.get("score", 0)) for c in out]
    if before != after:
        _goal_fire_count[0] += 1
        _goal_fire_ticks.add(int(tick))
    return out


def probe(ticks=1000):
    lsd._apply_group_norm_influence = _wrapped
    lsd._apply_group_goal_influence = _wrapped_goal
    scenario = get_scenario("collective_groups")
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    formations = []       # (tick, norm_id)
    first_active_tick = None
    max_active = 0
    deaths = 0
    peak_registry_bytes = 0
    peak_progress_entries = 0

    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        for e in accepted:
            valid_parent_ids.add(e["id"])
            if e.get("event_type") == "death":
                deaths += 1
            if e.get("event_type") == "group_form_norm":
                meta = e.get("group_norm_update") or {}
                for t in meta.get("transitions") or []:
                    if t.get("kind") == "formed":
                        formations.append((tick, t.get("norm_id")))
        reg = entities.get(GROUP_NORM_REGISTRY_ID) or {}
        norms = reg.get("norms") or {}
        active = sum(1 for n in norms.values() if n.get("status") == "active")
        if active > 0 and first_active_tick is None:
            first_active_tick = tick
        max_active = max(max_active, active)
        if reg:
            peak_registry_bytes = max(peak_registry_bytes, len(canonical_json(reg).encode("utf-8")))
            peak_progress_entries = max(peak_progress_entries, len(reg.get("group_progress") or {}))

    reg = entities.get(GROUP_NORM_REGISTRY_ID) or {}
    print(json.dumps({
        "ticks": ticks,
        "norm_formations": len(formations),
        "first_formation_tick": formations[0][0] if formations else None,
        "first_active_tick": first_active_tick,
        "max_active_norms_in_a_tick": max_active,
        "final_norm_count": len(reg.get("norms") or {}),
        "final_active_norm_count": sum(
            1 for n in (reg.get("norms") or {}).values() if n.get("status") == "active"),
        "influence_firings_total": _fire_count[0],
        "influence_firing_ticks": len(_fire_ticks),
        "influence_first_firing_tick": min(_fire_ticks) if _fire_ticks else None,
        "influence_last_firing_tick": max(_fire_ticks) if _fire_ticks else None,
        "goal_influence_firings_total": _goal_fire_count[0],
        "goal_influence_firing_ticks": len(_goal_fire_ticks),
        "any_repair_candidate_ticks": len(_repair_cand_ticks),
        "repair_candidate_first_tick": min(_repair_cand_ticks) if _repair_cand_ticks else None,
        "repair_candidate_last_tick": max(_repair_cand_ticks) if _repair_cand_ticks else None,
        "peak_registry_bytes": peak_registry_bytes,
        "payload_target_bytes": LIMITS.payload_target_bytes,
        "proposal_bytes_cap": LIMITS.proposal_bytes,
        "headroom_vs_target_pct": round(100 * (1 - peak_registry_bytes / LIMITS.payload_target_bytes), 1),
        "peak_progress_entries": peak_progress_entries,
        "tracked_groups_cap": LIMITS.tracked_groups,
        "norms_cap": LIMITS.norms,
        "deaths": deaths,
    }, indent=2))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    probe(tk)
