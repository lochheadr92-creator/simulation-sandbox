"""Stage 8B Leg 1 evidence tooling: final-state inspection of the
group-carriage registry (`group-carriage-000`) after a standard 1,000-tick
collective_groups run.

Read-only. Runs the real committed pipeline exactly like _probe_8b_carriage.py
and _probe_8b_leg1.py, then reads the registry's post-loop committed state and
reports carrier counts by source, the full carrier list, the registry's own
measured byte-size diagnostics, and the configured capacity limits for direct
comparison. Also cross-checks whether "person-004" appears as a carrier.

Usage: python -m tools._probe_8b_carriage_registry_state [ticks]
"""
from __future__ import annotations

import json
import sys
import time

from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario
from domains.group_carriage_contracts import (
    GROUP_CARRIAGE_REGISTRY_ID,
    LIMITS,
    group_carriage_capacity_diagnostics,
    split_carrier_key,
)

SEED = "living-agents-stage6"


def probe(ticks=1000):
    scenario = get_scenario("collective_groups")
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    for tick in range(1, ticks + 1):
        accepted, _rej, order_index, _diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        for e in accepted:
            valid_parent_ids.add(e["id"])

    registry = entities.get(GROUP_CARRIAGE_REGISTRY_ID) or {}
    carriers = registry.get("carriers") or {}

    backfill_count = sum(1 for r in carriers.values() if r.get("source") == "formation_backfill")
    transmission_count = sum(1 for r in carriers.values() if r.get("source") == "transmission")

    carrier_records = []
    for key, rec in sorted(carriers.items()):
        # F2c (byte slimming): carrier_id/norm_id/person_id are no longer
        # stored in the record body; they are recoverable from the registry
        # key via split_carrier_key. Probe fixed to read ids from the key.
        norm_id, person_id = split_carrier_key(key)
        carrier_records.append({
            "carrier_key": key,
            "carrier_id": key,
            "norm_id": norm_id,
            "group_id": rec.get("group_id"),
            "person_id": person_id,
            "source": rec.get("source"),
            "learned_from": rec.get("learned_from"),
            "via_event_id": rec.get("via_event_id"),
            "learned_tick": rec.get("learned_tick"),
        })

    person_004_records = [r for r in carrier_records if r["person_id"] == "person-004"]

    diagnostics = group_carriage_capacity_diagnostics(registry)

    result = {
        "ticks": ticks,
        "registry_found": bool(registry),
        "carrier_count": len(carriers),
        "backfill_count": backfill_count,
        "transmission_count": transmission_count,
        "backfilled_norm_ids": registry.get("backfilled_norm_ids") or [],
        "processed_transmission_keys": registry.get("processed_transmission_keys") or [],
        "carrier_records": carrier_records,
        "registry_revision": registry.get("revision"),
        "capacity_diagnostics": diagnostics,
        "limits": {
            "carriers": LIMITS.carriers,
            "payload_target_bytes": LIMITS.payload_target_bytes,
            "proposal_bytes": LIMITS.proposal_bytes,
        },
        "person_004_present": bool(person_004_records),
        "person_004_records": person_004_records,
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    t0 = time.time()
    probe(tk)
    elapsed = time.time() - t0
    print(json.dumps({"wall_clock_seconds": round(elapsed, 2)}), file=sys.stderr)
