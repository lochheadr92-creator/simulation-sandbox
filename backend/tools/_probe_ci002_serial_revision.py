"""CORE-INTEGRITY-002 Objective 1: is "every step advances the association
registry revision" actually an engine guarantee?

`test_concurrency.py:157` asserts
    int(registry["revision"]) == int(registry_before["revision"]) + 1
after two CONCURRENT steps. Before treating a failure there as a race, the
assertion itself has to be validated against serial behaviour.

This runs the equivalent steps SERIALLY -- one `step_run` at a time, no
concurrency anywhere -- against `emergent_groups`, the same scenario 7a uses,
and records per step:

  * simulation tick before / after
  * head revision before / after
  * association-registry revision before / after
  * whether an association proposal was ACCEPTED / REJECTED / ABSENT
  * whether SUBSTANTIVE owned association state changed, i.e. the registry with
    its bookkeeping fields (revision, last_updated_tick, last_event_id)
    stripped -- this separates a revision bump that reflects real change from
    one that is pure bookkeeping

Uses the API path (create_run / step_run) because that is the path 7a drives.
Creates one new run; modifies no existing data.

Run:  python tools/_probe_ci002_serial_revision.py [steps]
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
for _line in (BACKEND / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in _line and not _line.strip().startswith("#"):
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip())

from core import db as core_db  # noqa: E402
from core.hashing import canonical_hash  # noqa: E402
from core.run_service import create_run, get_run, step_run  # noqa: E402
from core.storage.frame_transaction import head_revision_of  # noqa: E402
from domains.association_contracts import ASSOCIATION_REGISTRY_ID  # noqa: E402

SCENARIO = "emergent_groups"
BOOKKEEPING = ("revision", "last_updated_tick", "last_event_id")


def _substantive(registry: dict | None) -> str | None:
    """Canonical hash of the registry with bookkeeping fields stripped."""
    if registry is None:
        return None
    trimmed = {k: v for k, v in registry.items() if k not in BOOKKEEPING}
    return canonical_hash(trimmed)


async def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    await core_db.ensure_indexes()
    db = core_db.db

    run = await create_run(f"ci002-serial-{uuid.uuid4().hex[:8]}", SCENARIO)
    run_id = run["id"]

    async def registry():
        return await db.entities.find_one(
            {"run_id": run_id, "id": ASSOCIATION_REGISTRY_ID}, {"_id": 0})

    rows = []
    for _ in range(steps):
        before_run = await get_run(run_id)
        before_reg = await registry()
        tick_before = before_run["current_tick"]

        await step_run(run_id, 1)

        after_run = await get_run(run_id)
        after_reg = await registry()
        tick_after = after_run["current_tick"]

        # Association proposals resolved in THIS tick.
        accepted = await db.accepted_events.count_documents({
            "run_id": run_id, "simulation_time": tick_after,
            "proposer_engine_id": "association",
        })
        rejected_docs = await db.rejected_proposals.find({
            "run_id": run_id, "simulation_time": tick_after,
        }, {"_id": 0}).to_list(length=200)
        rejected = [
            r for r in rejected_docs
            if ((r.get("proposal_snapshot") or {}).get("proposer_engine_id")
                == "association")
        ]

        if accepted:
            status = "ACCEPTED"
        elif rejected:
            status = "REJECTED"
        else:
            status = "ABSENT"

        rev_before = None if before_reg is None else int(before_reg.get("revision", -1))
        rev_after = None if after_reg is None else int(after_reg.get("revision", -1))
        sub_before, sub_after = _substantive(before_reg), _substantive(after_reg)

        rows.append({
            "tick_before": tick_before, "tick_after": tick_after,
            "head_rev_before": head_revision_of(before_run),
            "head_rev_after": head_revision_of(after_run),
            "assoc_rev_before": rev_before, "assoc_rev_after": rev_after,
            "assoc_rev_delta": (None if rev_before is None or rev_after is None
                                else rev_after - rev_before),
            "association_proposal": status,
            "rejection_reasons": [r.get("reason_code") for r in rejected],
            "substantive_state_changed": (None if sub_before is None
                                          else sub_before != sub_after),
            "records": len((after_reg or {}).get("association_records") or {}),
            "candidates": len((after_reg or {}).get("group_candidates") or {}),
        })

    print(f"scenario: {SCENARIO}   run_id: {run_id}   serial steps: {steps}")
    print(f"{'tick':>9} {'head':>9} {'assocRev':>11} {'d':>3} {'proposal':>9} {'substantive':>12}  rec/cand")
    for r in rows:
        print(f"{r['tick_before']:>4}->{r['tick_after']:<4} "
              f"{str(r['head_rev_before'])+'->'+str(r['head_rev_after']):>9} "
              f"{str(r['assoc_rev_before'])+'->'+str(r['assoc_rev_after']):>11} "
              f"{str(r['assoc_rev_delta']):>3} {r['association_proposal']:>9} "
              f"{str(r['substantive_state_changed']):>12}  "
              f"{r['records']}/{r['candidates']}"
              + (f"  {r['rejection_reasons']}" if r['rejection_reasons'] else ""))

    deltas = [r["assoc_rev_delta"] for r in rows if r["assoc_rev_delta"] is not None]
    noop_but_bumped = [r for r in rows
                       if r["assoc_rev_delta"] == 1 and r["substantive_state_changed"] is False]
    stalled = [r for r in rows if r["assoc_rev_delta"] == 0]
    summary = {
        "scenario": SCENARIO, "run_id": run_id, "serial_steps": steps,
        "assoc_rev_deltas_observed": sorted(set(deltas)),
        "every_serial_step_advanced_revision": bool(deltas) and all(d == 1 for d in deltas),
        "steps_with_delta_0": len(stalled),
        "steps_bumped_with_NO_substantive_change": len(noop_but_bumped),
        "proposal_status_counts": {
            s: sum(1 for r in rows if r["association_proposal"] == s)
            for s in ("ACCEPTED", "REJECTED", "ABSENT")
        },
    }
    print()
    print(json.dumps(summary, indent=2))
    out = BACKEND.parent / "scratchpad" / "ci002_serial_revision.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, default=str),
                   encoding="utf-8")
    print(f"\nwrote {out}")


asyncio.run(main())
