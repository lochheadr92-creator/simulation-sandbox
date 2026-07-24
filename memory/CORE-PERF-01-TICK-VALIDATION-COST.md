# CORE-PERF-01 — Per-tick validation cost (O(n²) → O(n))

**Status: PROPOSED — QUEUED behind the Upkeep leg. Not authorized, not started.**
Layer A (Kernel). Owner of this contract: cloud/doc session. Implementer when
authorized: the code (terminal) session. Profile-first; hash-neutral acceptance.

## Classification (why an infra leg is allowed here)

This leg changes **no player-visible behaviour** — its acceptance bar is that every
canonical hash is byte-identical before and after. Per the delivery lifecycle it is
therefore **approved infrastructure**, justified because it unblocks the visible
legs above it: every behaviour/culture/economy gate needs deterministic runs, and
at the current cost a 1,000-tick run is multi-hour. Fixing it makes verification of
those visible slices tractable. It is not a standalone feature and never claims one.

## Problem (measured evidence)

Per-tick cost rises across a run — **~0.6 s/tick early → ~1.05 s/tick by tick 80,
still climbing** (terminal timing diagnostic, living_settlement, capture on). Cost
model from the Stage-8C pre-registration: `T(n) ≈ 0.296·n + 0.000894·n²` — the
quadratic term dominates at long horizon, so 1,000-tick × multi-run gates run into
hours. This is a **pre-existing** engine cost, unrelated to any culture/behaviour leg.

## Root-cause hypothesis (confirm before touching code)

The set of acceptable causal-parent event IDs (`valid_parent_ids` or equivalent in
`backend/core/commit_pipeline.py :: run_commit_frame`) grows linearly with the run
and is rebuilt / re-scanned per frame → linear work × linear ticks = **O(n²)**.
Hypothesis only — Stage 1 confirms it.

## Lifecycle

### Stage 1 — Discovery (read-only, no code)
Profile a short run and confirm the hotspot; measure the max causal-parent age.
```
PYTHONPATH=. python -m cProfile -o /tmp/prof.out tools/living_agent_harness.py \
  --scenario collective_groups --ticks 200 --repeat 1
PYTHONPATH=. python -c "import pstats; pstats.Stats('/tmp/prof.out').sort_stats('cumulative').print_stats(25)"
```
- Confirm the dominant cost is causal-parent validation (not per-tick canonical
  rehash, entity deep-copy, or event-log re-serialization — if it's one of those,
  re-scope to that hotspot instead).
- Measure the **maximum age** (in ticks/events) of any real causal parent across a
  ≥300-tick run. This bounds any horizon in Tier 2.

### Stage 2 — Mechanism (implement the smallest fix the profile justifies)
- **Tier 1 — incremental set (hash-neutral, try first).** If the valid-parent set is
  rebuilt from full history each frame, maintain it **incrementally**: carry it on
  run/pipeline state, add each newly accepted event ID on commit, never rebuild.
  Membership is already O(1); the per-frame rebuild disappears → O(n²) → O(n). No
  accept/reject decision changes.
- **Tier 2 — bounded horizon (only if Tier 1 is insufficient).** Evict parent IDs
  older than horizon `K`, with `K` set safely above the Stage-1 measured max parent
  age. Because no legitimate parent is ever evicted, output is unchanged. Ties into
  the existing "recent replay horizon" invariant.

## Ownership / ordering (change surface)
Touch **only** the parent-set construction in `run_commit_frame`. No new canonical
fields, no schema change, no ordering/priority/hash-logic change, nothing else in
the pipeline. Update the Domain Ordering / Component Ownership registry rows only if
the change alters a documented invariant (it should not).

## Acceptance gate (the bar for this leg)
Pure speed-up, proven. All must hold:
1. **Hash-neutral — byte-identical before vs after:**
   - frozen `living_settlement` 320-tick hash `897f3f7f…3c5ab` unchanged
     (re-baselined 2026-07-25 at the Layer C Variety Leg 1 close-out from the
     prior frozen value `84d3ad52…c32d2` — see
     `memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md` §6 item 3; this leg
     must preserve the *new* value, not the retired one);
   - `collective_groups` `accepted_event_sequence_hash` + `final_state_hash`
     unchanged; repeat + replay + resume equality preserved.
   *(Any hash movement ⇒ the change altered behaviour ⇒ back it out; it is no longer
   perf-only.)*
2. **Measured speed-up:** per-tick cost is ~flat, not rising; report before/after
   ms-per-tick and total time for a fixed-horizon run (e.g. 250 and 500 ticks).
3. **Full regression suite green** (per the suite-status phrasing rule).

## Non-goals
No behaviour change; no schema/field change; no generic performance framework; no
chasing other perf suspects unless Stage 1 surfaces them; not folded into any
behaviour/culture leg. This is the *only* Core-adjacent change in its commit.

## Risks / rollback
This is Core/kernel — it governs determinism and replay, the most protected code in
the project. The entire safety argument is "the hashes do not move," proven by the
gate above. Roll back on any hash movement. If Tier 2 is used, choose `K`
conservatively (measured max age × a safety multiple).

## Queue / dependencies
Queued **after the Upkeep leg closes**. Independent of it. Recommended to land
**before** the next long-horizon gate or any Layer-F (economy) work, since those
need tractable long runs. FRONTIER "queued next" pointer added at the Upkeep
close-out (2026-07-25, `FRONTIER.md`) — no mid-leg FRONTIER edit was needed.
