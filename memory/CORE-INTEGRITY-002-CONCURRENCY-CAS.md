# CORE-INTEGRITY-002 — Suspected CAS/head-revision lost update under concurrent steps (STUB)

**Status: OPEN STUB (2026-07-25) — scoped out of CORE-INTEGRITY-001 by
independent review (Grok/xAI, finding SEC-CAS) and Ryan's ruling. No
investigation performed under this ID yet. This document exists so the
question has one identifiable owner and cannot be silently folded into
F1/F2 remediation without shared-root-cause evidence.**

## What this is

`test_concurrent_stage7a_steps_do_not_duplicate_groups_or_head` and
`test_concurrent_stage7b_steps_do_not_duplicate_shared_state_or_head` fail
intermittently. The seed-dependent setup-miss dimension is explained and
verified test-side (see the flake ledger on the culture branch,
`memory/CAPABILITY_ROADMAP.md`). Whether there is ALSO a genuine
CAS/head-revision lost-update in the engine under concurrent step
execution — separate from that seed dependence — has never been tested.

## Why it is not CORE-INTEGRITY-001

001 is same-frame last-writer-wins field overwrite inside a single
deterministic commit frame (`apply_mutation` shallow `dict.update`).
002 is suspected cross-step concurrency: two concurrent step executions
racing on head-revision/CAS. Different mechanism class, different probe
shape, potentially different remediation. Review ruling (2026-07-25):
do not fold together without evidence of a shared root cause.

## Known prior work

- Canary instrumentation for the CAS/head-revision path was written in a
  2026-07-23 cloud session but never executed (paused mid-launch by user
  redirect; script did not survive the session).
- Isolated re-runs of the intermittent tests pass (e.g. 4/4 on
  2026-07-23), consistent with either explanation.

## Next actions (when opened)

1. Re-derive the canary probe: instrument or observe head-revision CAS
   under deliberately concurrent steps; assert no lost update / no
   duplicate head advance.
2. If a real engine race is found: classify severity, check whether any
   committed run could contain it (determinism claims are per-process;
   concurrency is the API layer), and open a remediation decision.
3. If no race: close 002 as test-isolation-only and record the evidence.

*Stub only. No findings. No remediation implied.*
