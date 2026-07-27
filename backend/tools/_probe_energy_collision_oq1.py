"""OQ-1: attribute the same-tick, same-person `energy` collisions.

Open question, recorded in memory/REGISTRY-COMPONENT-OWNERSHIP.md (the `energy`
row) with its earlier F11 attribution WITHDRAWN:

    "MEDIUM (was LOW; that rating assumed one-per-scenario SELF-writes, which the
     cross-entity social writer breaks. Held at MEDIUM pending OQ-1 -- 64
     unattributed same-tick `energy` collisions in `collective_groups`, 0 in
     `living_settlement`. Drop to LOW if OQ-1 resolves to something benign)"

Declared writers of `energy`: `people_domain.py:375`;
`living_settlement_domain.py:712,715`; `living_agent_actions.py:435,503,505`;
`living_agent_social.py:436-437` (CROSS-ENTITY -- actor AND target);
`interventions.py:25`.

WHAT THIS ANSWERS
-----------------
A "collision" is two or more accepted events in ONE frame writing the same
person's `energy`. The benign/malign question is whether the second write is a
LOST UPDATE -- i.e. whether the later writer's value was computed from a base
that already included the earlier write, or whether it silently discarded it.

For each collision this records: the writers in commit order, their action types
and event families, each written value, the entity's pre-frame value, and whether
the final committed value equals the value a correct sequential application would
produce. That last test is what separates "benign layering" from "lost update".

The scenario asymmetry (collective_groups vs living_settlement) is itself the
control and is reproduced here rather than assumed.

READ-ONLY. Patches nothing, changes no production behaviour.

Usage:
  python -m tools._probe_energy_collision_oq1 <out.json> [ticks] [scenario] [seed]
"""
from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario


SEED = "living-agents-stage6"
DEFAULT_SCENARIO = "collective_groups"
DEFAULT_TICKS = 1_000
EXAMPLE_LIMIT = 40


def _sorted_counter(counter) -> dict:
    return {str(k): int(counter[k]) for k in sorted(counter, key=str)}


def _energy_writes(event: dict) -> dict:
    """{entity_id: written_energy} for every energy write in this event."""
    out = {}
    updates = ((event.get("mutation") or {}).get("entity_updates") or {})
    for eid, row in updates.items():
        if isinstance(row, dict) and "energy" in row:
            out[str(eid)] = row["energy"]
    return out


class EnergyCollisionCensus:
    def __init__(self) -> None:
        self.frames = 0
        self.energy_write_events = 0
        self.collisions = 0
        self.colliding_person_ticks = 0
        self.writers_per_collision = Counter()
        self.writer_action_pairs = Counter()
        self.writer_event_types = Counter()
        self.self_vs_cross = Counter()
        self.outcome = Counter()
        self.delta_from_last_writer = Counter()
        self.examples: list[dict] = []

    def observe_frame(self, *, tick: int, accepted: list[dict],
                      before: dict, entities: dict) -> None:
        self.frames += 1
        by_entity: dict[str, list[dict]] = defaultdict(list)
        for event in accepted:
            writes = _energy_writes(event)
            if writes:
                self.energy_write_events += 1
            for eid, value in writes.items():
                by_entity[eid].append({
                    "event_id": event.get("id"),
                    "writer_actor": str(event.get("entity_id") or ""),
                    "event_type": str(event.get("event_type")),
                    "action_type": (event.get("living_action") or {}).get("action_type"),
                    "value": value,
                })

        for eid, writers in sorted(by_entity.items()):
            if len(writers) < 2:
                continue
            self.collisions += 1
            self.colliding_person_ticks += 1
            self.writers_per_collision[len(writers)] += 1

            pre = (before.get(eid) or {}).get("energy")
            final = (entities.get(eid) or {}).get("energy")
            last = writers[-1]["value"]

            actions = tuple(str(w["action_type"]) for w in writers)
            self.writer_action_pairs["+".join(actions)] += 1
            for w in writers:
                self.writer_event_types[w["event_type"]] += 1
            roles = {("self" if w["writer_actor"] == eid else "cross") for w in writers}
            self.self_vs_cross[
                "self_only" if roles == {"self"} else
                ("cross_only" if roles == {"cross"} else "mixed_self_and_cross")] += 1

            # Is the final value the LAST writer's value (last-write-wins), and
            # did earlier writers' deltas survive?
            if final == last:
                self.outcome["final_equals_last_writer"] += 1
            else:
                self.outcome["final_differs_from_last_writer"] += 1
            # Did each writer compute from the pre-frame base (=> earlier write
            # discarded) or from a progressively updated base?
            distinct_values = {json.dumps(w["value"], sort_keys=True) for w in writers}
            if len(distinct_values) == 1:
                self.outcome["all_writers_wrote_same_value"] += 1
            self.delta_from_last_writer[str(
                (final - pre) if isinstance(final, int) and isinstance(pre, int) else "n/a"
            )] += 1

            if len(self.examples) < EXAMPLE_LIMIT:
                self.examples.append({
                    "tick": int(tick), "entity_id": eid,
                    "pre_frame_energy": pre, "final_energy": final,
                    "writers": copy.deepcopy(writers),
                    "final_equals_last_writer": final == last,
                    "distinct_written_values": len(distinct_values),
                })

    def metrics(self) -> dict:
        return {
            "frames": self.frames,
            "events_writing_energy": self.energy_write_events,
            "collisions": self.collisions,
            "writers_per_collision": _sorted_counter(self.writers_per_collision),
            "writer_action_combinations": _sorted_counter(self.writer_action_pairs),
            "writer_event_types": _sorted_counter(self.writer_event_types),
            "self_vs_cross_entity": _sorted_counter(self.self_vs_cross),
            "outcome": _sorted_counter(self.outcome),
            "final_minus_pre_frame_energy": _sorted_counter(self.delta_from_last_writer),
            "examples": self.examples,
        }


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def probe(*, ticks: int = DEFAULT_TICKS, seed: str = SEED,
          scenario_id: str = DEFAULT_SCENARIO, output_path: Path | None = None) -> dict:
    scenario = get_scenario(scenario_id)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(seed, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    replayed: dict = {}
    for event in genesis:
        apply_mutation(replayed, copy.deepcopy(event["mutation"]))
    rng = DeterministicRNG(seed)
    cache: dict = {}
    census = EnergyCollisionCensus()
    started = time.perf_counter()

    for tick in range(1, ticks + 1):
        before = {
            eid: {"energy": ent.get("energy")}
            for eid, ent in entities.items() if ent.get("type") == "person"
        }
        accepted, _rejected, order_index, _diag = run_tick(
            "probe-energy-collision-oq1", entities, world["terrain"], tick, rng,
            order_index, lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
            entity_json_cache=cache,
        )
        for event in accepted:
            valid_parent_ids.add(event["id"])
            apply_mutation(replayed, copy.deepcopy(event["mutation"]))
        census.observe_frame(tick=tick, accepted=accepted, before=before,
                             entities=entities)

    payload = {
        "status": "complete",
        "probe": "oq1-energy-collision-attribution",
        "seed": seed, "scenario_id": scenario_id, "ticks": int(ticks),
        "schema_version": SCHEMA_VERSION, "engine_version": ENGINE_VERSION,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, ticks, lineage_key)),
        "replay_matches_entities": replayed == entities,
        "census": census.metrics(),
    }
    if output_path is not None:
        _write(output_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[0]) if argv else Path("energy_collision_oq1.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    scenario = argv[2] if len(argv) > 2 else DEFAULT_SCENARIO
    seed = argv[3] if len(argv) > 3 else SEED
    r = probe(ticks=ticks, seed=seed, scenario_id=scenario, output_path=out)
    c = r["census"]
    print(json.dumps({
        "scenario": scenario, "seed": seed, "ticks": ticks,
        "elapsed_seconds": r["elapsed_seconds"],
        "final_state_hash": r["final_state_hash"],
        "replay_matches_entities": r["replay_matches_entities"],
        "collisions": c["collisions"],
        "events_writing_energy": c["events_writing_energy"],
        "writers_per_collision": c["writers_per_collision"],
        "self_vs_cross_entity": c["self_vs_cross_entity"],
        "writer_action_combinations": c["writer_action_combinations"],
        "outcome": c["outcome"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
