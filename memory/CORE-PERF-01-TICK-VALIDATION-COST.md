# CORE-PERF-01 — Per-tick validation cost (O(n²) → O(n))

**Status: DISCOVERY — Stage 1 complete (2026-07-25); original root-cause
hypothesis FALSIFIED by profiling. Touch-surface must be re-scoped from Core
(`commit_pipeline.py`) to domain code (`living_agent_cognition.py` /
`living_agent_social.py`) before this contract can be authorized. See "Stage 1
findings" below. Not yet re-authorized, not started.**
Layer A (Kernel) as originally scoped — actual hotspot is Layer C domain code
(see findings). Owner of this contract: cloud/doc session. Implementer when
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

## Root-cause hypothesis (confirm before touching code) — FALSIFIED, see below

The set of acceptable causal-parent event IDs (`valid_parent_ids` or equivalent in
`backend/core/commit_pipeline.py :: run_commit_frame`) grows linearly with the run
and is rebuilt / re-scanned per frame → linear work × linear ticks = **O(n²)**.
Hypothesis only — Stage 1 confirms it.

## Stage 1 findings (2026-07-25, read-only, no code changed)

**Method:** `cProfile` over a 200-tick `collective_groups` harness run (`python
-m cProfile -m tools.living_agent_harness --scenario collective_groups --ticks
200 --repeat 1`), plus a separate unprofiled timing pass (windowed ms/tick over
250 ticks) to confirm the growth *shape* independent of profiler overhead.

**Hypothesis test result: FALSIFIED.** `run_commit_frame` (where the
hypothesized causal-parent-set rebuild would live) accounts for only **71.8s
cumulative of the 428.9s total profiled run (~17%)**, across 201 calls. No
causal-parent-set-rebuild hotspot appears anywhere near the top of the profile
by either cumulative or self time. Read directly: the harness's own
`valid_parent_ids` is *already* maintained incrementally (`.add()` per accepted
event in `tools/living_agent_harness.py`, not rebuilt), and the production path
(`core/run_service.py::_valid_causal_parent_ids`) computes a set bounded by
**current entity count** (via each entity's `last_event_id`), not by total run
history — so it does not grow with tick count either. The doc's hypothesis
about *where* the O(n²) mechanism lives does not match either code path.

**Actual dominant cost: `copy.deepcopy`, ~75% of total runtime.**
`copy.deepcopy` was called **200,153,735 times** over 200 ticks (~1,000,000
calls/tick), consuming 160.9s self-time / 323.8s cumulative of the 428.9s
total. It is overwhelmingly reached through
`domains/living_settlement_domain.py:534(activate)` (228.8s cumulative / 200
calls) → agent cognition/social update functions, each of which opens with a
wholesale `out = copy.deepcopy(state)` (an immutable-update idiom that copies
the *entire* per-agent canonical state — memories, relationships, wants,
decision_history, commitments, etc.) before making any change:
- `domains/living_agent_cognition.py::derive_internal_pressures` (line 415)
- `domains/living_agent_cognition.py::refresh_wants` (line 538)
- `domains/living_agent_cognition.py::merge_meaningful_memories` (line 704)
- `domains/living_agent_social.py::apply_observed_social_information`,
  `apply_relationship_consequence` (similar pattern, confirmed present in the
  profile's top-cost functions, not yet line-verified)

**Shape confirmation (unprofiled, direct timing, `collective_groups`,
`living-agents-stage6`, 250 ticks):**

| window | wall time | ms/tick avg | entity_count | valid_parent_ids size |
|---|---:|---:|---:|---:|
| ticks 1-10 | 3.958s | 395.8 | 29 | 225 |
| ticks 11-50 | 25.123s | 628.1 | 28 | 1,061 |
| ticks 51-100 | 35.474s | 709.5 | 36 | 2,116 |
| ticks 101-150 | 37.741s | 754.8 | 37 | 3,156 |
| ticks 151-200 | 38.306s | 766.1 | 33 | 4,203 |
| ticks 201-250 | 41.582s | 831.6 | 40 | 5,216 |

Per-tick cost genuinely climbs across the run (confirms the doc's original
"still climbing" observation), but **`entity_count` stays flat** while cost
grows — ruling out an entity-count-driven mechanism (including the
causal-parent-set-by-entity-count path above). The correlated growing
quantity is per-agent **state size** (memories/relationships/wants/
decision_history accumulating toward their bounded caps over the run), which
is exactly what the wholesale `copy.deepcopy(state)` calls above pay for, once
or more per agent per tick, from multiple different functions.

**Conclusion:** the contract's stated touch-surface — "Touch **only** the
parent-set construction in `run_commit_frame`... nothing else in the
pipeline" — does not match the measured hotspot. The real cost lives in
domain code (Layer C: `living_settlement_domain.py` / `living_agent_
cognition.py` / `living_agent_social.py`), not Core's `commit_pipeline.py`.
This is a full re-scope, not a minor correction: different files, different
risk profile (domain code vs. Core/kernel), and the "smallest fix" is not yet
identified (which of the several wholesale-copy call sites contributes most,
and whether a shallow-copy-plus-targeted-mutation refactor is safe and
hash-neutral, both need their own read-only investigation before a Tier 1/
Tier 2 mechanism can be proposed). **STOP — re-scope decision needed before
any Stage 2 code.**

## Lifecycle (as originally drafted — SUPERSEDED by the Stage 1 findings above
for Stage 2 onward; Stage 1 itself is complete and its own text below is now a
historical record of what was run, not a to-do)

### Stage 1 — Discovery (read-only, no code) — COMPLETE, see findings above
Profile a short run and confirm the hotspot; measure the max causal-parent age.
```
PYTHONPATH=. python -m cProfile -o /tmp/prof.out tools/living_agent_harness.py \
  --scenario collective_groups --ticks 200 --repeat 1
PYTHONPATH=. python -c "import pstats; pstats.Stats('/tmp/prof.out').sort_stats('cumulative').print_stats(25)"
```
- Confirm the dominant cost is causal-parent validation (not per-tick canonical
  rehash, entity deep-copy, or event-log re-serialization — if it's one of those,
  re-scope to that hotspot instead). **Result: it's entity deep-copy — re-scope
  triggered, per the findings above.**
- Measure the **maximum age** (in ticks/events) of any real causal parent across a
  ≥300-tick run. This bounds any horizon in Tier 2. **Not measured — moot: Tier 2
  (bounded causal-parent horizon) does not apply to the actual hotspot.**

### Stage 2 — Mechanism — NOT VALID AS WRITTEN, do not implement
Both tiers below targeted the causal-parent-set mechanism, which Stage 1 found
is not the cost driver. Neither applies to the actual hotspot (wholesale
per-agent state deep-copies in domain code) without a fresh design. Left here
verbatim as the historical record of the original (falsified) plan.
- **Tier 1 — incremental set (hash-neutral, try first).** If the valid-parent set is
  rebuilt from full history each frame, maintain it **incrementally**: carry it on
  run/pipeline state, add each newly accepted event ID on commit, never rebuild.
  Membership is already O(1); the per-frame rebuild disappears → O(n²) → O(n). No
  accept/reject decision changes.
- **Tier 2 — bounded horizon (only if Tier 1 is insufficient).** Evict parent IDs
  older than horizon `K`, with `K` set safely above the Stage-1 measured max parent
  age. Because no legitimate parent is ever evicted, output is unchanged. Ties into
  the existing "recent replay horizon" invariant.

## Ownership / ordering (change surface) — NOT VALID AS WRITTEN

Touch **only** the parent-set construction in `run_commit_frame`. No new canonical
fields, no schema change, no ordering/priority/hash-logic change, nothing else in
the pipeline. Update the Domain Ordering / Component Ownership registry rows only if
the change alters a documented invariant (it should not).

**This touch-surface is wrong per the Stage 1 findings** — the measured hotspot
is in `domains/living_settlement_domain.py` / `living_agent_cognition.py` /
`living_agent_social.py` (Layer C domain code), not `commit_pipeline.py`
(Core). A corrected change surface needs its own read-only investigation
(which wholesale-copy call site dominates; whether a shallow-copy + targeted-
mutation refactor is safe and hash-neutral) before this section can be
rewritten and the contract re-authorized.

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
Originally framed as Core/kernel; per the Stage 1 findings the actual
touch-surface is Layer C domain code (`living_settlement_domain.py` /
`living_agent_cognition.py` / `living_agent_social.py`), which governs agent
state shape, not commit/replay mechanics directly — still meaningfully
protected code (this leg's own Upkeep close-out just re-baselined the frozen
hash these functions feed into), just a different risk class than Core. The
entire safety argument is unchanged in kind: "the hashes do not move," proven
by the gate above. Roll back on any hash movement. If Tier 2 (bounded horizon)
ends up relevant to whatever the re-scoped mechanism turns out to be, choose
any such horizon conservatively (measured max age × a safety multiple).

## Queue / dependencies
Queued **after the Upkeep leg closes**. Independent of it. Recommended to land
**before** the next long-horizon gate or any Layer-F (economy) work, since those
need tractable long runs. FRONTIER "queued next" pointer added at the Upkeep
close-out (2026-07-25, `FRONTIER.md`) — no mid-leg FRONTIER edit was needed.
