"""Manual projection rebuild under exclusive maintenance (Phase 5A4a).

Usage:
  python -m tools.rebuild_run --run-id <RUN_ID>
  python -m tools.rebuild_run --run-id <RUN_ID> --force --reason "..."

Requires the run to be paused or quarantined (unless --force with safeguards).
Does not auto-repair during normal stepping.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend root is on path when run as module from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from core.db import db, ensure_indexes
from core.run_service import get_run, lineage_key_for_run
from core.storage.frame_transaction import (
    ConcurrentModification,
    RunIntegrityMismatch,
    RunUnderMaintenance,
    acquire_maintenance,
    rebuild_projection_atomically,
    release_maintenance,
    write_recovery_record,
)


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Rebuild entity projections from accepted events")
    p.add_argument("--run-id", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--reason", default=None)
    p.add_argument("--operator", default="cli-operator")
    p.add_argument("--yes", action="store_true",
                   help="Non-interactive; with --force requires SIM_SANDBOX_FORCE_RECOVERY=1")
    return p.parse_args(argv)


async def _run(args) -> int:
    await ensure_indexes()
    run = await get_run(args.run_id)
    if not run:
        print(f"ERROR: run not found: {args.run_id}", file=sys.stderr)
        return 2

    if args.force:
        if not args.reason:
            print("ERROR: --force requires --reason", file=sys.stderr)
            return 2
        if args.yes:
            if os.environ.get("SIM_SANDBOX_FORCE_RECOVERY") != "1":
                print(
                    "ERROR: noninteractive --force requires SIM_SANDBOX_FORCE_RECOVERY=1",
                    file=sys.stderr,
                )
                return 2
        else:
            print("Type CONFIRM to proceed with forced recovery:")
            typed = input().strip()
            if typed != "CONFIRM":
                print("ERROR: confirmation failed", file=sys.stderr)
                return 2
    else:
        if run.get("status") not in ("paused", "quarantined") and not run.get("quarantined"):
            print(
                f"ERROR: run status must be paused/quarantined (got {run.get('status')}); "
                "use --force with safeguards if appropriate",
                file=sys.stderr,
            )
            return 2

    operation_id = f"rebuild-{uuid.uuid4().hex[:12]}"
    recovery_id = f"recovery-{uuid.uuid4().hex[:16]}"
    starting_rev = run.get("head_revision", 0)
    lineage_key = lineage_key_for_run(run)
    latest_frame = await db.commit_frames.find_one(
        {"run_id": args.run_id}, {"_id": 0}, sort=[("tick", -1)],
    )
    if not latest_frame:
        print("ERROR: no commit frame to rebuild against", file=sys.stderr)
        return 2
    expected_hash = latest_frame["ending_state_hash"]
    current_tick = latest_frame["tick"]

    record_base = {
        "recovery_id": recovery_id,
        "run_id": args.run_id,
        "operation": "rebuild_projection",
        "forced": bool(args.force),
        "operator_label": args.operator,
        "operator_reason": args.reason,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "starting_head_revision": starting_rev,
        "source_frame_id": latest_frame.get("id"),
        "source_frame_tick": current_tick,
        "expected_ending_state_hash": expected_hash,
        "maintenance_operation_id": operation_id,
    }

    try:
        await acquire_maintenance(
            args.run_id, operation_id,
            force=bool(args.force),
            reason=args.reason,
            operator=args.operator,
        )
    except (ConcurrentModification, RunUnderMaintenance) as exc:
        await write_recovery_record({
            **record_base,
            "result": "failed",
            "failure_reason": str(exc),
            "rebuilt_ending_state_hash": None,
        })
        print(f"ERROR: could not acquire maintenance: {exc}", file=sys.stderr)
        return 3

    try:
        result = await rebuild_projection_atomically(
            args.run_id, operation_id, lineage_key, expected_hash, current_tick,
        )
        await release_maintenance(args.run_id, operation_id, quarantine=False, status="paused")
        await write_recovery_record({
            **record_base,
            "result": "success",
            "failure_reason": None,
            "rebuilt_ending_state_hash": result["rebuilt_hash"],
            "entity_count": result["entity_count"],
        })
        print(f"OK rebuilt run={args.run_id} tick={current_tick} hash={result['rebuilt_hash']}")
        return 0
    except Exception as exc:
        # Leave quarantined on failure; do not overwrite with unverified rebuild
        try:
            await release_maintenance(args.run_id, operation_id, quarantine=True)
        except Exception as release_exc:
            print(f"WARNING: release failed: {release_exc}", file=sys.stderr)
        await write_recovery_record({
            **record_base,
            "result": "failed",
            "failure_reason": str(exc),
            "rebuilt_ending_state_hash": None,
        })
        print(f"ERROR: rebuild failed; run quarantined: {exc}", file=sys.stderr)
        return 4


def main(argv=None):
    args = _parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
