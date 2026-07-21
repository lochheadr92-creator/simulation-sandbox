"""Narrow falsifying diagnostic: is cross-domain outcome coupling pre-existing?

Question: enabling `group_carriage` (8B Leg 1) shifted an UNRELATED pair of
persons' social_request_help from tick 699 to 698. Did the PREVIOUS stage's
domain addition (`group_norm`, 8A) do the same thing when it was added?

Design (narrowest form, per CLAUDE.md "narrowest falsifying diagnostic first"):
two configs run in LOCKSTEP in one process, compared tick-by-tick, terminating
at the FIRST divergence rather than running a full horizon.

  A = 7D baseline   (no group_norm, no group_carriage)
  B = A + group_norm (the 8A state)

Critical control: the added domain's OWN event type is EXCLUDED from the
comparison signature. Otherwise the comparison trivially "diverges" the moment
the new domain commits its own first event, which proves nothing. We compare
only the events of the domains that were already there - so a divergence means
group_norm changed some OTHER domain's behaviour, which is exactly the
phenomenon under investigation.

Read-only. Usage: python -m tools._probe_8b_coupling_narrow [max_ticks]
"""
from __future__ import annotations

import json
import sys
import time

from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario

SEED = "living-agents-stage6"

# The added domain's own proposal type - excluded from the comparison so we
# measure only whether PRE-EXISTING domains' behaviour shifted.
GROUP_NORM_EVENT_TYPES = {"group_form_norm"}
GROUP_CARRIAGE_EVENT_TYPES = {"group_carry_norm"}


def _signature(accepted, exclude):
    """Per-tick behavioural fingerprint of the domains common to both configs."""
    return sorted(
        (e.get("event_type"), e.get("entity_id"))
        for e in accepted
        if e.get("event_type") not in exclude
    )


def _social(accepted):
    out = []
    for e in accepted:
        etype = e.get("event_type") or ""
        if not etype.startswith("social_"):
            continue
        meta = e.get("social_action") or {}
        out.append({
            "event_type": etype,
            "actor": meta.get("actor_id") or e.get("entity_id"),
            "target": meta.get("target_id"),
        })
    return out


def _new_run(domains):
    scenario = get_scenario("collective_groups")
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    return {
        "domains": list(domains),
        "entities": entities,
        "terrain": world["terrain"],
        "order_index": order_index,
        "rng": DeterministicRNG(SEED),
        "valid_parents": {e["id"] for e in genesis},
        "lineage_key": lineage_key,
        "social": [],
    }


def _step(run, tick):
    accepted, _rej, run["order_index"], _diag = run_tick(
        "probe", run["entities"], run["terrain"], tick, run["rng"], run["order_index"],
        run["lineage_key"], run["domains"],
        valid_causal_parent_event_ids=run["valid_parents"],
    )
    for e in accepted:
        run["valid_parents"].add(e["id"])
    run["social"].extend({**s, "tick": tick} for s in _social(accepted))
    return accepted


def probe(max_ticks=720):
    base = [d for d in get_scenario("collective_groups").enabled_domains
            if d not in ("group_norm", "group_carriage")]
    config_a = list(base)                      # 7D baseline
    config_b = list(base) + ["group_norm"]     # 8A

    run_a = _new_run(config_a)
    run_b = _new_run(config_b)

    exclude = GROUP_NORM_EVENT_TYPES | GROUP_CARRIAGE_EVENT_TYPES

    first_divergent_tick = None
    divergence_detail = None
    first_norm_event_tick = None

    for tick in range(1, max_ticks + 1):
        acc_a = _step(run_a, tick)
        acc_b = _step(run_b, tick)

        if first_norm_event_tick is None and any(
            e.get("event_type") in GROUP_NORM_EVENT_TYPES for e in acc_b
        ):
            first_norm_event_tick = tick

        sig_a = _signature(acc_a, exclude)
        sig_b = _signature(acc_b, exclude)
        if sig_a != sig_b and first_divergent_tick is None:
            first_divergent_tick = tick
            only_a = [x for x in sig_a if x not in sig_b]
            only_b = [x for x in sig_b if x not in sig_a]
            divergence_detail = {
                "tick": tick,
                "config_a_event_count_excl_new_domain": len(sig_a),
                "config_b_event_count_excl_new_domain": len(sig_b),
                "present_only_in_A": only_a,
                "present_only_in_B": only_b,
            }
            break  # early termination: the question is answered

    # Social-triple comparison over the ticks actually run.
    def triples(run):
        return {(s["event_type"], s["actor"], s["target"], s["tick"]) for s in run["social"]}

    tri_a, tri_b = triples(run_a), triples(run_b)
    same_triple_diff_tick = []
    by_key_a = {(t[0], t[1], t[2]): t[3] for t in tri_a}
    by_key_b = {(t[0], t[1], t[2]): t[3] for t in tri_b}
    for key, tick_a in sorted(by_key_a.items()):
        tick_b = by_key_b.get(key)
        if tick_b is not None and tick_b != tick_a:
            same_triple_diff_tick.append({
                "event_type": key[0], "actor": key[1], "target": key[2],
                "tick_in_A_7D_baseline": tick_a, "tick_in_B_8A": tick_b,
            })

    print(json.dumps({
        "question": "Did adding group_norm (8A) shift UNRELATED domains' behaviour, as adding group_carriage (8B Leg 1) was measured to do?",
        "ticks_run": min(first_divergent_tick or max_ticks, max_ticks),
        "max_ticks_configured": max_ticks,
        "config_a_7D_baseline": config_a,
        "config_b_8A": config_b,
        "comparison_excludes_event_types": sorted(exclude),
        "first_tick_group_norm_committed_its_own_event": first_norm_event_tick,
        "ANSWER_first_divergent_tick_excluding_new_domains_own_events": first_divergent_tick,
        "divergence_detail": divergence_detail,
        "social_events_A_count": len(run_a["social"]),
        "social_events_B_count": len(run_b["social"]),
        "same_actor_target_type_at_different_tick": same_triple_diff_tick,
    }, indent=2, default=str))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 720
    t0 = time.time()
    probe(tk)
    print(json.dumps({"wall_clock_seconds": round(time.time() - t0, 2)}), file=sys.stderr)
