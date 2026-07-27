"""Attribute every `energy_eq_failed` rejection produced by the OQ-1 containment.

The question this exists to answer: baseline `living_settlement` recorded ZERO
OQ-1 same-tick energy collisions, yet the containment arm records 18
`energy_eq_failed` rejections. Both cannot be true unless the two counting
bases differ, or the intervening writer is outside the collision probe's
definition, or the precondition is broader than the defect.

For EVERY such rejection this records, without assumption:
  tick, actor, physical action, the pinned frame-start energy, the live energy
  at commit re-validation, every accepted event in that frame that wrote the
  actor's energy (with writer identity, action and value), whether the writer
  was self or cross-entity, and whether the frame would have counted as an
  OQ-1 collision under the ORIGINAL definition (>= 2 ACCEPTED energy writers
  for the same person in one frame).

That last field is the discriminator. The original collision probe counts
ACCEPTED writers only; a rejected second writer is invisible to it by
construction.

READ-ONLY. Patches nothing; consumes run_tick's returned lists.

Usage:
  python -m tools._probe_energy_rejection_attribution <out.json> [ticks] [scenario] [seed]
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
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario


SEED = "living-agents-stage6"
DEFAULT_SCENARIO = "living_settlement"
DEFAULT_TICKS = 1_000


def _sorted_counter(counter) -> dict:
    return {str(k): int(counter[k]) for k in sorted(counter, key=str)}


def _energy_write(event: dict, eid: str):
    row = ((event.get("mutation") or {}).get("entity_updates") or {}).get(eid)
    if isinstance(row, dict) and "energy" in row:
        return row["energy"]
    return None


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
    started = time.perf_counter()

    records: list[dict] = []
    classes = Counter()
    first_death_tick = None
    last_death_tick = None
    prev_alive = None

    for tick in range(1, ticks + 1):
        frame_start = {
            eid: ent.get("energy") for eid, ent in entities.items()
            if ent.get("type") == "person"
        }
        accepted, rejected, order_index, _diag = run_tick(
            "probe-energy-rejection-attr", entities, world["terrain"], tick, rng,
            order_index, lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
            entity_json_cache=cache,
        )
        for event in accepted:
            valid_parent_ids.add(event["id"])
            apply_mutation(replayed, copy.deepcopy(event["mutation"]))

        alive = sum(1 for e in entities.values()
                    if e.get("type") == "person" and e.get("alive", True))
        if prev_alive is not None and alive < prev_alive:
            first_death_tick = first_death_tick if first_death_tick is not None else tick
            last_death_tick = tick
        prev_alive = alive

        for rejection in rejected:
            if str(rejection.get("reason_detail")) != "energy_eq_failed":
                continue
            actor = str(rejection.get("entity_id") or "")
            proposal = rejection.get("proposal_snapshot") or {}
            pinned = next(
                (c.get("value") for c in (proposal.get("preconditions") or [])
                 if c.get("field") == "energy" and c.get("entity_id") == actor),
                None,
            )
            writers = []
            for event in accepted:
                value = _energy_write(event, actor)
                if value is None:
                    continue
                writers.append({
                    "event_id": event.get("id"),
                    "writer_actor": str(event.get("entity_id") or ""),
                    "writer_is_self": str(event.get("entity_id") or "") == actor,
                    "event_type": str(event.get("event_type")),
                    "action_type": (event.get("living_action") or {}).get("action_type"),
                    "value_written": value,
                })
            # ORIGINAL OQ-1 definition: >=2 ACCEPTED energy writers, same person,
            # same frame. A rejected second writer is invisible to it.
            counted_by_original_probe = len(writers) >= 2
            klass = (
                "no_accepted_writer_energy_changed_by_other_path" if not writers else
                ("single_accepted_writer_rejected_one_invisible_to_collision_probe"
                 if len(writers) == 1 else
                 "two_or_more_accepted_writers_would_count_as_collision")
            )
            classes[klass] += 1
            records.append({
                "tick": int(tick), "actor": actor,
                "physical_action": (proposal.get("living_action") or {}).get("action_type"),
                "proposal_type": proposal.get("proposal_type"),
                "frame_start_energy": frame_start.get(actor),
                "pinned_precondition_energy": pinned,
                "live_energy_after_frame": (entities.get(actor) or {}).get("energy"),
                "accepted_energy_writers_in_frame": writers,
                "accepted_writer_count": len(writers),
                "counted_by_original_collision_probe": counted_by_original_probe,
                "classification": klass,
                "cross_entity_writer_present": any(not w["writer_is_self"] for w in writers),
            })

    payload = {
        "status": "complete",
        "probe": "energy-rejection-attribution",
        "seed": seed, "scenario_id": scenario_id, "ticks": int(ticks),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "final_state_hash": canonical_hash(snapshot_for_hash(entities, ticks, lineage_key)),
        "replay_matches_entities": replayed == entities,
        "alive_at_end": sum(1 for e in entities.values()
                            if e.get("type") == "person" and e.get("alive", True)),
        "first_death_tick": first_death_tick,
        "last_death_tick": last_death_tick,
        "energy_eq_failed_total": len(records),
        "fully_attributed": all(r["accepted_writer_count"] >= 1 for r in records),
        "classification_counts": _sorted_counter(classes),
        "records": records,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = Path(argv[0]) if argv else Path("energy_rejection_attribution.json")
    ticks = int(argv[1]) if len(argv) > 1 else DEFAULT_TICKS
    scenario = argv[2] if len(argv) > 2 else DEFAULT_SCENARIO
    seed = argv[3] if len(argv) > 3 else SEED
    r = probe(ticks=ticks, seed=seed, scenario_id=scenario, output_path=out)
    print(json.dumps({k: v for k, v in r.items() if k != "records"},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
