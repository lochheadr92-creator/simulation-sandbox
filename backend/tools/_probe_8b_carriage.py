"""Stage 8B design evidence: is `supporter_ids` a STRICT subset of `member_ids`?

Decides the formation-backfill rule. If adoption supporters == all group members
at every adoption, then backfilling supporters yields zero non-carriers and
organic transmission has no target. If supporters are a strict subset, the
non-supporters are organically-produced non-carriers and transmission has
somewhere to go -- with no seeding.

Also records which persons participate in social_* events, so the transmission
trigger can be grounded on an event type that demonstrably fires between a
would-be carrier and a would-be non-carrier.

Read-only. Usage: python -m tools._probe_8b_carriage [ticks]
"""
from __future__ import annotations

import json
import sys
import time

from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario
from domains.association_contracts import ASSOCIATION_REGISTRY_ID
from domains.group_goal_contracts import (
    GROUP_GOAL_REGISTRY_ID,
    _holds_improve_shelter_want,
)

SEED = "living-agents-stage6"


def probe(ticks=350):
    scenario = get_scenario("collective_groups")
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    adoption_samples = []      # per observed adoption: members vs supporters
    seen_goal_keys = set()
    want_holder_counts = {}    # tick -> count of persons holding improve_shelter want
    social_events = []         # {tick, etype, actor, target}
    ratio_histogram = {}       # "supporters/members" -> count

    for tick in range(1, ticks + 1):
        accepted, _rej, order_index, _diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        for e in accepted:
            valid_parent_ids.add(e["id"])
            etype = e.get("event_type")
            if etype and etype.startswith("social_"):
                meta = e.get("social_action") or {}
                social_events.append({
                    "tick": tick, "etype": etype,
                    "actor": e.get("entity_id"), "target": meta.get("target_id"),
                })

        # Adoption supporters vs recognised-group members (post-commit).
        assoc = entities.get(ASSOCIATION_REGISTRY_ID) or {}
        cands = assoc.get("group_candidates") or {}
        goal_reg = entities.get(GROUP_GOAL_REGISTRY_ID) or {}
        for goal in (goal_reg.get("goals") or {}).values():
            key = goal.get("goal_key") or goal.get("adopted_via_key")
            if not key or key in seen_goal_keys:
                continue
            seen_goal_keys.add(key)
            gid = goal.get("group_id")
            members = sorted((cands.get(gid) or {}).get("member_ids") or [])
            supporters = sorted(goal.get("supporter_ids") or [])
            ratio = f"{len(supporters)}/{len(members)}"
            ratio_histogram[ratio] = ratio_histogram.get(ratio, 0) + 1
            if len(adoption_samples) < 40:
                adoption_samples.append({
                    "tick": tick, "group": gid,
                    "members": len(members), "supporters": len(supporters),
                    "non_supporters": sorted(set(members) - set(supporters)),
                    "strict_subset": set(supporters) < set(members),
                })

        # How many persons hold the want at all (the carrier-eligible pool).
        holders = 0
        for _eid, ent in entities.items():
            if not isinstance(ent, dict) or ent.get("type") != "person":
                continue
            if _holds_improve_shelter_want(ent):
                holders += 1
        want_holder_counts[tick] = holders

    persons = sorted(eid for eid, e in entities.items()
                     if isinstance(e, dict) and e.get("type") == "person")
    holder_series = [want_holder_counts[t] for t in sorted(want_holder_counts)]
    print(json.dumps({
        "ticks": ticks,
        "person_count": len(persons),
        "adoptions_observed": len(seen_goal_keys),
        "supporters_over_members_histogram": ratio_histogram,
        "any_strict_subset": any(s["strict_subset"] for s in adoption_samples),
        "adoption_samples": adoption_samples,
        "want_holders_min": min(holder_series) if holder_series else None,
        "want_holders_max": max(holder_series) if holder_series else None,
        "want_holders_sample_every_25": {
            str(t): want_holder_counts[t] for t in sorted(want_holder_counts) if t % 25 == 0
        },
        "social_event_count": len(social_events),
        "social_events": social_events[:60],
    }, indent=2, default=str))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 350
    t0 = time.time()
    probe(tk)
    print(json.dumps({"wall_clock_seconds": round(time.time() - t0, 2)}), file=sys.stderr)
