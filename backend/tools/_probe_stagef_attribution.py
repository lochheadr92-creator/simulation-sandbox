"""Phase 1: attribute every selected-but-uncommitted THREATEN / VERIFY_INFORMATION.

Under CI-004 ordering both actions are generated ~390x and WIN arbitration
(THREATEN 191, VERIFY_INFORMATION 171 in 200 ticks) yet never commit. This
records the direct failure reason rather than inferring it from zero commits.

`living_settlement_domain.activate` catches `ValueError` from the proposal
builder, sets `plan["failure_reason"] = str(exc)` and falls back to `rest`.
That failure_reason is read straight out of the committed event's mutation.

Classes: non_adjacent_target | other_build_validation | cas_rejection |
         replaced_after_selection | domain_fallback | unknown

READ-ONLY. Consumes run_tick's returned diagnostics/accepted/rejected.

Usage:
  python -m tools._probe_stagef_attribution <out.json> [ticks] [scenario] [seed]
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.geometry import manhattan
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario

SEED = "living-agents-stage6"
WATCH = {"THREATEN": "threaten", "VERIFY_INFORMATION": "share_information"}


def _c(c):
    return {str(k): int(c[k]) for k in sorted(c, key=str)}


def probe(*, ticks=200, seed=SEED, scenario_id="living_settlement", output_path=None):
    sc = get_scenario(scenario_id)
    lk = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _r, oi = build_genesis(seed, sc, lk)
    vp = {e["id"] for e in genesis}
    rng = DeterministicRNG(seed)
    cache: dict = {}
    started = time.perf_counter()

    selected = Counter()
    committed = Counter()
    classes = {g: Counter() for g in WATCH}
    reasons = {g: Counter() for g in WATCH}
    distances = {g: Counter() for g in WATCH}
    adjacency = {g: Counter() for g in WATCH}
    counter_vals = {g: Counter() for g in WATCH}
    records: list[dict] = []

    for tick in range(1, ticks + 1):
        acc, rej, oi, diag = run_tick("probe-stagef", entities, world["terrain"], tick,
                                      rng, oi, lk, sc.enabled_domains,
                                      valid_causal_parent_event_ids=vp,
                                      entity_json_cache=cache)
        for ev in acc:
            vp.add(ev["id"])
        by_actor = {}
        for ev in acc:
            aid = str(ev.get("entity_id") or "")
            if aid:
                by_actor.setdefault(aid, ev)
        rejected_actors = {str(r.get("entity_id") or "") for r in rej}

        for aid, row in sorted(diag.items()):
            if "decision_receipt" not in row:
                continue
            goal = str(row.get("selected_goal") or "")
            if goal not in WATCH:
                continue
            action = WATCH[goal]
            selected[goal] += 1
            cand = next((c for c in (row.get("candidates") or [])
                         if c.get("goal") == goal), {}) or {}
            target = cand.get("target_entity_id")
            actor_ent = entities.get(aid) or {}
            tgt_ent = entities.get(str(target)) or {}
            apos, tpos = actor_ent.get("position"), tgt_ent.get("position")
            dist = manhattan(apos, tpos) if apos and tpos else None
            adjacent = dist is not None and dist <= 1
            distances[goal][str(dist)] += 1
            adjacency[goal]["adjacent" if adjacent else "not_adjacent"] += 1
            counter_vals[goal][str(int((actor_ent.get("living_action_counts") or {}).get(action, 0)))] += 1

            ev = by_actor.get(aid)
            committed_action = (ev.get("living_action") or {}).get("action_type") if ev else None
            plan = (((ev or {}).get("mutation") or {}).get("entity_updates") or {}).get(aid, {}).get("plan") or {}
            fr = plan.get("failure_reason")

            if committed_action == action:
                committed[goal] += 1
                klass = "committed"
            elif fr:
                reasons[goal][str(fr)] += 1
                klass = ("non_adjacent_target" if "adjacent" in str(fr).lower()
                         else "other_build_validation")
            elif aid in rejected_actors:
                klass = "cas_rejection"
            elif committed_action in ("rest", "move"):
                klass = "domain_fallback"
            elif ev is None:
                klass = "replaced_after_selection"
            else:
                klass = "unknown"
            if klass != "committed":
                classes[goal][klass] += 1
            if len(records) < 40:
                records.append({
                    "tick": tick, "actor": aid, "goal": goal, "target": target,
                    "actor_pos": apos, "target_pos": tpos, "distance": dist,
                    "adjacent": adjacent, "committed_action": committed_action,
                    "failure_reason": fr, "class": klass,
                    "visible_people": sorted(
                        o["observed_subject_id"] for o in (row.get("perception") or {}).get("_", [])
                    ) if False else None,
                })

    payload = {
        "status": "complete", "probe": "stagef-attribution",
        "seed": seed, "scenario_id": scenario_id, "ticks": ticks,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, ticks, lk)),
        "selected": _c(selected), "committed": _c(committed),
        "classes": {g: _c(c) for g, c in classes.items()},
        "failure_reasons": {g: _c(c) for g, c in reasons.items()},
        "target_distance": {g: _c(c) for g, c in distances.items()},
        "adjacency": {g: _c(c) for g, c in adjacency.items()},
        "action_counter_at_decision": {g: _c(c) for g, c in counter_vals.items()},
        "unattributed": sum(c.get("unknown", 0) for c in classes.values()),
        "records": records,
    }
    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                                     encoding="utf-8")
    return payload


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[0]) if argv else Path("stagef.json")
    ticks = int(argv[1]) if len(argv) > 1 else 200
    scen = argv[2] if len(argv) > 2 else "living_settlement"
    seed = argv[3] if len(argv) > 3 else SEED
    r = probe(ticks=ticks, seed=seed, scenario_id=scen, output_path=out)
    print(json.dumps({k: v for k, v in r.items() if k != "records"},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
