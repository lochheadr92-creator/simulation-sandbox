# Phase 5A4a — Transactional Tick Persistence

## Transaction contents (frame-critical)

Inside one Mongo multi-document transaction:

1. `accepted_events` insert for the frame
2. `rejected_proposals` insert for the frame
3. changed `entities` projections only (replace/delete)
4. `commit_frames` insert (includes `frame_identity_hash`)
5. `kernel_runs` CAS update on application field `id` + `head_revision`

## Excluded writes (safe outside the transaction)

| Write | Why safe outside |
|---|---|
| `activation_diagnostics` | Derived presentation; rebuildable; not world truth |
| `prune_old_rejections` | Retention policy; not required for frame validity |
| Timeline / milestones | Derived projections over accepted events |

Failure to write excluded records does **not** roll back or invalidate canonical world truth.

## CAS / head_revision

- New runs and fork children initialize `head_revision: 0`.
- Legacy runs without the field: after integrity check passes, set to `0` once.
- CAS filter: `{id, head_revision, maintenance_mode $ne true, quarantined $ne true, current_tick, next_order_index}`.
- On match: set tick/hash/order; `$inc head_revision`.
- Zero matches → `CONCURRENT_MODIFICATION` (HTTP 409); never retry the same precomputed frame.

## Retry policy

| Class | Policy |
|---|---|
| CAS mismatch | Abort; no retry; 409 |
| TransientTransactionError | Retry same precomputed frame ≤3 attempts / 15s deadline; revalidate head each time |
| UnknownTransactionCommitResult | Resolve via frame identity; never blind replay |
| Capacity / permanent DB | Fail closed before or without retry |

## Recovery

`python -m tools.rebuild_run --run-id <ID>`

- Requires paused/quarantined (or `--force` with reason + CONFIRM / `SIM_SANDBOX_FORCE_RECOVERY=1`)
- Acquires maintenance via CAS (advances `head_revision`)
- Rebuilds entities from `accepted_events`, verifies ending hash, swaps projections
- Failure leaves run quarantined; writes immutable `recovery_records`

## Authority boundaries

Unchanged: accepted events are world truth; entities/commit_frames/kernel_runs are operational projections and head metadata. FrameCommit-as-sole-authority is Phase 5A4b.
