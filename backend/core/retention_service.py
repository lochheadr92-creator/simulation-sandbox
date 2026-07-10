"""Retention policy (Phase 4A).

Bounded history policy, kept honest about what it actually does:

- Recent horizon (last RECENT_HORIZON_TICKS ticks): raw accepted events,
  rejected proposals (with full proposal_snapshot/scoring evidence), and
  commit_frames are all retained, giving full detailed causal inspection.
- Older horizon: accepted_events and commit_frames are NEVER pruned (they
  are required for replay/determinism verification forever - deleting them
  would break the Replay Doctrine). Only `rejected_proposals` older than
  the recent horizon are pruned, because they are NOT required for replay
  (replay_service.py never reads rejected_proposals) and the spec
  explicitly says not to retain every rejected proposal forever.

Deliberately NOT built in this phase (explicitly deferred, not stubbed):
checkpoints, branch/fork-from-snapshot, and any compressed/archival
storage tier for accepted events. The existing full accepted-event history
plus the current per-run entities snapshot is what makes save/load/continue
work today - no new mechanism was needed for that.
"""
from core.db import db
from core.constants import RECENT_HORIZON_TICKS


async def prune_old_rejections(run_id: str, current_tick: int) -> int:
    cutoff = current_tick - RECENT_HORIZON_TICKS
    if cutoff <= 0:
        return 0
    result = await db.rejected_proposals.delete_many({"run_id": run_id, "simulation_time": {"$lt": cutoff}})
    return result.deleted_count
