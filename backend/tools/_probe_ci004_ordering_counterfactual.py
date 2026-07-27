"""CORE-INTEGRITY-004: counterfactual comparison of proposal ordering keys.

QUESTION
--------
Can deterministic commit ordering use a CONTENT-INDEPENDENT final tie-break, so
that adding or changing non-ordering proposal content (a precondition, receipt
metadata, a mutation detail) does not reorder otherwise-equivalent proposals?

CURRENT KEY (core/commit_pipeline.py:108-109)
    order_key(p) = (requested_time,
                    PHASE_RANK[phase],          # environment=0, agent=1
                    engine_priority (default 100),
                    content_hash)               # <-- CONTENT-DERIVED TIE-BREAK

`content_hash` = canonical_hash(core_fields) and core_fields INCLUDES
`preconditions`, `mutation`, `living_action`, `social_action` (`:75-95`). So any
content edit reshuffles otherwise-equivalent proposals.

CANDIDATE KEY (Design A/B hybrid, following the repo's OWN genesis precedent at
core/kernel.py:83, which already made genesis ordering positional via
engine_priority):
    candidate(p) = (requested_time,
                    PHASE_RANK[phase],
                    engine_priority,
                    proposer_engine_id,         # stable: domain identity
                    entity_id,                  # stable: actor identity
                    proposal_type,              # stable: action family
                    ordinal)                    # deterministic emission index
                                                # within (engine, entity, type)

Every component is fixed BEFORE the mutation/preconditions are built, so adding a
precondition cannot change it.

READ-ONLY. Wraps `run_commit_frame` to observe the proposal list pre-sort, then
delegates to the original untouched. Production ordering is NOT changed.

Usage:
  python -m tools._probe_ci004_ordering_counterfactual <out.json> [ticks] [scenario] [seed] [--with-energy-precondition]
"""
from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import core.commit_pipeline as cp
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario


SEED = "living-agents-stage6"
DEFAULT_SCENARIO = "living_settlement"
DEFAULT_TICKS = 320


def _sorted_counter(c) -> dict:
    return {str(k): int(c[k]) for k in sorted(c, key=str)}


def _candidate_key(p: dict, ordinal: int):
    return (
        p["requested_time"],
        cp.PHASE_RANK.get(p["phase"], 99),
        p.get("engine_priority", 100),
        str(p.get("proposer_engine_id") or ""),
        str(p.get("entity_id") or ""),
        str(p.get("proposal_type") or ""),
        ordinal,
    )


class OrderingCensus:
    def __init__(self) -> None:
        self.frames = 0
        self.proposals = 0
        self.tie_groups = 0            # groups sharing (time, phase, priority)
        self.proposals_in_ties = 0
        self.reordered_proposals = 0
        self.frames_with_reorder = 0
        self.first_divergence_tick = None
        self.first_divergence_detail = None
        self.duplicate_candidate_keys = 0
        self.duplicate_examples: list[dict] = []
        self.ambiguous = 0
        self.candidate_key_shape = Counter()
        self.tie_group_sizes = Counter()
        self.examples: list[dict] = []

    def observe(self, tick: int, proposals: list[dict]) -> None:
        self.frames += 1
        self.proposals += len(proposals)

        # Deterministic emission ordinal within (engine, entity, type).
        counters: dict[tuple, int] = defaultdict(int)
        annotated = []
        for p in proposals:
            group = (str(p.get("proposer_engine_id") or ""),
                     str(p.get("entity_id") or ""),
                     str(p.get("proposal_type") or ""))
            ordinal = counters[group]
            counters[group] += 1
            annotated.append((p, _candidate_key(p, ordinal)))

        # Duplicate candidate keys => ambiguity the design must resolve.
        seen: dict[tuple, dict] = {}
        for p, key in annotated:
            if key in seen:
                self.duplicate_candidate_keys += 1
                if len(self.duplicate_examples) < 12:
                    self.duplicate_examples.append({
                        "tick": int(tick), "key": [str(x) for x in key],
                        "first_proposal_type": seen[key].get("proposal_type"),
                        "second_proposal_type": p.get("proposal_type"),
                    })
            else:
                seen[key] = p

        # Tie groups under the CURRENT key, before the content_hash tie-break.
        groups: dict[tuple, list] = defaultdict(list)
        for p, key in annotated:
            groups[(p["requested_time"], cp.PHASE_RANK.get(p["phase"], 99),
                    p.get("engine_priority", 100))].append((p, key))
        for g, members in groups.items():
            if len(members) > 1:
                self.tie_groups += 1
                self.proposals_in_ties += len(members)
                self.tie_group_sizes[len(members)] += 1

        current = [p["content_hash"] for p, _ in
                   sorted(annotated, key=lambda item: cp.order_key(item[0]))]
        candidate = [p["content_hash"] for p, _ in
                     sorted(annotated, key=lambda item: item[1])]

        if current != candidate:
            self.frames_with_reorder += 1
            diff = sum(1 for a, b in zip(current, candidate) if a != b)
            self.reordered_proposals += diff
            if self.first_divergence_tick is None:
                self.first_divergence_tick = int(tick)
                cur_order = sorted(annotated, key=lambda item: cp.order_key(item[0]))
                cand_order = sorted(annotated, key=lambda item: item[1])
                self.first_divergence_detail = {
                    "tick": int(tick),
                    "proposal_count": len(annotated),
                    "current_order": [{
                        "entity_id": p.get("entity_id"),
                        "proposal_type": p.get("proposal_type"),
                        "engine": p.get("proposer_engine_id"),
                        "order_key": [str(x) for x in cp.order_key(p)],
                    } for p, _ in cur_order[:10]],
                    "candidate_order": [{
                        "entity_id": p.get("entity_id"),
                        "proposal_type": p.get("proposal_type"),
                        "engine": p.get("proposer_engine_id"),
                        "candidate_key": [str(x) for x in k],
                    } for p, k in cand_order[:10]],
                }
        if len(self.examples) < 3:
            self.examples.append({
                "tick": int(tick), "proposals": len(annotated),
                "tie_groups": sum(1 for m in groups.values() if len(m) > 1),
            })

    def metrics(self) -> dict:
        return {
            "frames": self.frames,
            "proposals_total": self.proposals,
            "tie_groups_before_final_tiebreak": self.tie_groups,
            "proposals_inside_tie_groups": self.proposals_in_ties,
            "tie_group_size_histogram": _sorted_counter(self.tie_group_sizes),
            "frames_where_candidate_reorders": self.frames_with_reorder,
            "proposals_whose_position_differs": self.reordered_proposals,
            "first_divergence_tick": self.first_divergence_tick,
            "first_divergence_detail": self.first_divergence_detail,
            "duplicate_candidate_keys": self.duplicate_candidate_keys,
            "duplicate_examples": self.duplicate_examples,
            "examples": self.examples,
        }


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = DEFAULT_SCENARIO, output_path: Path | None = None,
          with_energy_precondition: bool = False) -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(seed, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(seed)
    cache: dict = {}
    census = OrderingCensus()
    started = time.perf_counter()

    original_run_commit_frame = cp.run_commit_frame
    original_normalize = cp.normalize_proposal

    def observing_frame(entities_arg, domain_outputs, tick, *args, **kwargs):
        flat = []
        seq = 0
        for output in domain_outputs:
            for p in output.proposals:
                q = dict(p)
                if with_energy_precondition and q.get("entity_id", "").startswith("person-"):
                    # Semantically INACTIVE probe precondition: pins the value
                    # already true at frame start, so it can never fail here.
                    live = (entities_arg.get(q["entity_id"]) or {}).get("energy")
                    q = dict(q)
                    q["preconditions"] = list(q.get("preconditions") or []) + [
                        {"entity_id": q["entity_id"], "field": "energy",
                         "op": "eq", "value": live},
                    ]
                flat.append(original_normalize(q, seq))
                seq += 1
        census.observe(tick, flat)
        return original_run_commit_frame(entities_arg, domain_outputs, tick, *args, **kwargs)

    cp.run_commit_frame = observing_frame
    try:
        import core.kernel as kernel
        kernel.run_commit_frame = observing_frame
        for tick in range(1, ticks + 1):
            accepted, _rejected, order_index, _diag = run_tick(
                "probe-ci004", entities, world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
                valid_causal_parent_event_ids=valid_parent_ids,
                entity_json_cache=cache,
            )
            for event in accepted:
                valid_parent_ids.add(event["id"])
    finally:
        cp.run_commit_frame = original_run_commit_frame
        import core.kernel as kernel
        kernel.run_commit_frame = original_run_commit_frame

    payload = {
        "status": "complete",
        "probe": "ci004-ordering-counterfactual",
        "seed": seed, "scenario_id": scenario_id, "ticks": int(ticks),
        "with_energy_precondition": bool(with_energy_precondition),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, ticks, lineage_key)),
        "current_key": "(requested_time, phase_rank, engine_priority, content_hash)",
        "candidate_key": "(requested_time, phase_rank, engine_priority, proposer_engine_id, entity_id, proposal_type, ordinal)",
        "census": census.metrics(),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    with_pre = "--with-energy-precondition" in argv
    argv = [a for a in argv if not a.startswith("--")]
    out = Path(argv[0]) if argv else Path("ci004_ordering.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    scenario = argv[2] if len(argv) > 2 else DEFAULT_SCENARIO
    seed = argv[3] if len(argv) > 3 else SEED
    r = probe(ticks=ticks, seed=seed, scenario_id=scenario, output_path=out,
              with_energy_precondition=with_pre)
    c = r["census"]
    print(json.dumps({
        "scenario": scenario, "ticks": ticks,
        "with_energy_precondition": r["with_energy_precondition"],
        "final_state_hash": r["final_state_hash"],
        "proposals_total": c["proposals_total"],
        "tie_groups_before_final_tiebreak": c["tie_groups_before_final_tiebreak"],
        "proposals_inside_tie_groups": c["proposals_inside_tie_groups"],
        "tie_group_size_histogram": c["tie_group_size_histogram"],
        "frames_where_candidate_reorders": c["frames_where_candidate_reorders"],
        "proposals_whose_position_differs": c["proposals_whose_position_differs"],
        "first_divergence_tick": c["first_divergence_tick"],
        "duplicate_candidate_keys": c["duplicate_candidate_keys"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
