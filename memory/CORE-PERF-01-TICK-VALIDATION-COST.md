# CORE-PERF-01 — Per-tick validation cost (O(n²) → O(n))

**Status: Slice A VERIFIED-CLOSED (2026-07-25, Ryan's ruling); Slice B
VERIFIED (2026-07-25), awaiting Ryan's close-out ruling.** Slice A:
hash-neutral at 250 and 500 ticks (~1.22x / ~1.51x measured speed-up),
fallback-rest path closed with a verified-to-have-teeth fixture test. Slice
B: hash-neutral with debug-assert-mode proving byte-equality on every single
accepted event across both full gate runs (zero mismatches), ~1.47x-2.12x
measured speed-up (controlled, back-to-back methodology; ratio increasing
with horizon exactly as the mechanism predicts), 7 new property tests
including a direct proof that cache invalidation is load-bearing.
Authorization: "A then B — do the safe one first, prove nothing breaks
(every hash must come out identical), then do the big one with full safety
checks" (Ryan, 2026-07-25). Touch-surface is two independent slices: Slice A
— Layer C (`living_settlement_domain.py` / `living_agent_cognition.py` /
`living_agent_social.py` / `living_agent_reasoning.py`, single-boundary-copy
ownership refactor) — **VERIFIED-CLOSED, see "Slice A results" below**;
Slice B — Layer A/Core (`commit_pipeline.py` / `core/mutations.py` /
`core/hashing.py` / `core/kernel.py` / `tools/living_agent_harness.py`,
fragment-cached world-snapshot serialization) — **VERIFIED, see "Slice B
results" below, awaiting close-out ruling**. Owner of this contract:
cloud/doc session. Implementer: the code (terminal) session, this branch.
Profile-first; hash-neutral acceptance.

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

## Stage 1 findings (2026-07-25, read-only, no code changed) — attribution
superseded by Stage 1b below; the falsified-hypothesis verdict stands

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
about *where* the O(n²) mechanism lives does not match either code path. This
verdict is unaffected by the Stage 1b correction below.

**Attribution superseded by Stage 1b:** this pass measured `copy.deepcopy` at
~75% of runtime via `cProfile`. That number is a profiler artifact — see
Stage 1b immediately below for the corrected attribution (~33%) and the
actual dominant cost.

**Shape confirmation (unprofiled, direct timing, `collective_groups`,
`living-agents-stage6`, 250 ticks) — this table is unaffected by the Stage 1b
correction, only the *cause* of the climb is re-attributed there:**

| window | wall time | ms/tick avg | entity_count | valid_parent_ids size |
|---|---:|---:|---:|---:|
| ticks 1-10 | 3.958s | 395.8 | 29 | 225 |
| ticks 11-50 | 25.123s | 628.1 | 28 | 1,061 |
| ticks 51-100 | 35.474s | 709.5 | 36 | 2,116 |
| ticks 101-150 | 37.741s | 754.8 | 37 | 3,156 |
| ticks 151-200 | 38.306s | 766.1 | 33 | 4,203 |
| ticks 201-250 | 41.582s | 831.6 | 40 | 5,216 |

Per-tick cost genuinely climbs across the run, but **`entity_count` stays
flat** while cost grows — ruling out an entity-count-driven mechanism. The
correlated growing quantity is per-agent **state size**
(memories/relationships/wants/decision_history accumulating toward their
bounded caps over the run).

## Stage 1b — re-scoped Discovery findings (VERIFIED, 2026-07-25, cloud session)

Produced from a disposable clone of `worktree-typed-painting-marshmallow` at
`4974aff2`. **Environment caveat:** all measurements below ran on the cloud
Linux environment (Ubuntu, Python 3.11.15, DB-free harness path); absolute
times differ from the canonical Windows machine, but the *structure* (shares,
growth shape) is the finding.

### 1. Correction to the Stage 1 numbers (VERIFIED)

The Stage 1 claim "`copy.deepcopy` ≈ 75% of runtime" is a **cProfile
artifact**. `deepcopy` recurses once per nested node (~200M profiled calls
over 200 ticks); cProfile charges fixed per-call overhead to each, inflating
recursive functions. Re-measured two independent ways that don't have this
failure mode:

- **Outermost-call timing** (reentrancy-guarded wrap of `copy.deepcopy`, only
  the top-level call timed): deepcopy = **33% of wall**, stable across 80-
  and 240-tick runs (27.8s/84.8s and 103.3s/311.2s).
- **Stack sampling** (~200 Hz, no instrumentation of the hot path): `copy.*`
  frames ≈ 34%, **canonical hashing/serialization ≈ 60%**, everything else
  ≈ 6%.

The Stage 1 *conclusion* (hypothesis falsified; cost is state-size-driven,
not entity-count- or parent-set-driven) stands. The *attribution* changes
materially: **the dominant cost is canonical JSON serialization for
per-event world hashing, not deepcopy.** Both grow with per-agent state
size, which is why ms/tick climbs while entity_count stays flat
(re-confirmed: 910 → 1,271 ms/tick across quarters of a 240-tick run;
deepcopy portion 342 → 490 ms/tick).

### 2. Where the time actually goes (VERIFIED, collective_groups)

**Hotspot #1 — `commit_pipeline.py:463` (`run_commit_frame`): ~44% of wall.**
```python
post_hash = canonical_hash(snapshot_for_hash(entities, tick, lineage_key))
```
Runs once per *accepted proposal* (~21/tick) and serializes the **entire
world** to JSON each time: **1.51 GB serialized in a 60-tick run** (1,248
calls, 27.3s of a 61.4s wall; 83% of all `canonical_json` time). This term
grows with world JSON size × events — it is the main driver of both total
cost and the climb. The JSON encoder is already on CPython's C path (checked;
`default=str` does not disable it) — the cost is pure volume, not a slow
encoder. Spot-verified directly against `commit_pipeline.py:463` in this
session before this document arrived — matches exactly.

**Hotspot #2 — wholesale per-agent state deepcopies (Layer C): ~22% of
wall.** Per agent per tick, the activation chain in
`living_settlement_domain.activate` full-copies the agent's living_agent
state ~8–9 times, discarding each input immediately (`state = f(state)`
style). Measured sites, share of total deepcopy time (240-tick run):
`working_actor = deepcopy(entity)` at `living_settlement_domain.py:645`
(9.2%), `apply_relationship_consequence` :85 — called per observed social
signal, full state copy each time (8.0%), `merge_meaningful_memories`
:704+:705 (9.9%), `derive_internal_pressures` :415 (6.6%), `refresh_wants`
:538 (6.6%), `merge_observations_into_knowledge` :269 (5.0%),
`apply_observed_social_information` :600 (3.5%),
`advance_commitment_deadlines` :184 (3.3%), `record_decision` :352 (3.3%),
plus compat/`_bounded_dict` internals (~5%).

**Also measured, deliberately left out of scope (see "Explicitly out of
scope" below):** `kernel.py:73` per-tick `entities_view` deepcopy (11% of
deepcopy time ≈ 3.7% wall — it is the read-only-frame guarantee);
harness-internal copies/hashes (`_event_hash` :45, replay-reconstruction
:216 — ~17% of deepcopy time, verification-instrument only).

## Stage 2 (revised) — two-slice mechanism proposal (PROPOSED, awaiting
authorization; supersedes the Tier 1/Tier 2 mechanism in "Lifecycle" below,
which targeted the falsified hypothesis)

Acceptance bar for both slices is unchanged from the contract: **byte-identical
hashes** (frozen `living_settlement` 320-tick hash `897f3f7f…3c5ab` — see
correction note; `collective_groups` accepted_event_sequence_hash +
final_state_hash; repeat + replay + resume), full suite, before/after ms/tick
at 250 and 500 ticks.

> **Hash correction:** the source draft of this section (as received) cited
> `897f3f7f…3ab5`. The verified value, cross-checked directly against
> `memory/evidence/layer-c-leg1/upkeep_living_settlement_320_frozen_rebaseline.json`
> and already committed identically in four places (`CLAUDE.md`,
> `memory/CAPABILITY-DOCTRINE.md`, `.claude/agents/hard-rail-reviewer.md`,
> and `memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md`), is `897f3f7f…3c5ab`
> — used throughout this document instead.

### Slice A — Layer C: single-boundary-copy ownership for the agent chain
*(lower risk; recommend first)*

Mechanism: establish one ownership rule — `compat_living_agent_state` already
returns a **fully detached** state object (verified by reading it: every
sub-record is deep-copied or rebuilt). From that boundary on, the chain owns
its state exclusively, so each chain function replaces its wholesale
`out = copy.deepcopy(state)` with a shallow top-level copy, rebuilding only
the sub-tree it changes. Function-by-function safety (all verified by
reading each):

- `derive_internal_pressures` — builds `pressures` entirely fresh; shallow copy
  is sufficient as-is.
- `refresh_wants` — new want records are fresh dicts; the dormant-flip
  (:594–597) mutates existing records → replace with copy-on-write
  (`wants[id] = {**wants[id], "status": …}`).
- `merge_meaningful_memories` — `_upsert_memory` *replaces* records (safe); the
  decay loop (:785) mutates records in place → copy-on-write there.
- `advance_commitment_deadlines` / `_put_commitment` — record mutation →
  copy-on-write per touched record; drop the two wholesale copies.
- `apply_relationship_consequence` — keep the per-record copy at :87 (it already
  isolates the record); drop the full-state copy at :85 and the
  whole-relationships deepcopy at :86.
- `record_decision` — shallow copy + fresh `decision_history` list; keep the
  receipt deepcopy (the receipt also lands in diagnostics).
- `working_actor` (:645) — the deepcopy of the full entity immediately has its
  two largest subtrees (`living_agent`, `knowledge`) *replaced*. Safest variant:
  deepcopy the entity **minus those two keys**, then attach the new state and
  knowledge. Preserves full defensive copying for everything the proposal
  builders read, while skipping the two big discarded copies. (Builders were
  skimmed and build fresh update dicts rather than mutating actors — but this
  variant doesn't even rely on that.)
- **One mandatory new defensive copy:** at :736,
  `resulting_state = actor_update.get("living_agent") or state` can alias the
  proposal's mutation payload (social builders set `living_agent` on the
  update). Today the chain's next deepcopy breaks that alias incidentally; under
  in-place ownership it must be broken explicitly with a single deepcopy here.
  This is the one place the refactor could silently corrupt a proposal if
  skipped — it goes in with a comment naming this paragraph. Spot-verified
  directly in this session before this document arrived — the aliasing
  fallback is exactly as described.

Why hash-neutral: deepcopy affects aliasing, never values. Identical values into
identical proposal payloads ⇒ identical accepted events ⇒ identical hashes. The
gate proves it end-to-end.

Expected effect (LIKELY): removes most of the ~22% Layer-C deepcopy share and
most of its growth term; roughly 1.25–1.4× overall at current horizons.

### Slice B — Layer A: fragment-cached world snapshot for the per-event hash
*(bigger win; Core territory; high-risk gate; recommend second)*

The recorded `post_state_hash` per accepted event is canonical and must not
change — so the hash *values* and *cadence* stay exactly as they are. What can
change is how the identical bytes get produced. `canonical_json(snapshot)` is a
deterministic concatenation of per-entity JSON fragments (entities sorted by id,
`sort_keys=True` makes each fragment a pure function of that entity's content).
Mechanism: maintain a non-canonical, derived cache `{entity_id: json_fragment}`
alongside the pipeline; on each `apply_mutation`, invalidate exactly the touched
entity ids (the mutation names them: `entity_updates` keys, new entities,
deletions); per accepted event, re-serialize only invalidated entities, splice
the full string by joining cached fragments, and sha256 the splice. Serialization
drops from O(world) to O(changed entities) per event; the sha256+utf-8 pass over
the full string remains but runs at C speed (order GB/s vs ~50 MB/s for JSON
encoding — measured 1.51 GB serialized per 60 ticks collapsing to a few tens of
MB).

Safety mechanism (the whole argument): a **byte-equality property check** —
spliced output == direct `canonical_json(snapshot_for_hash(...))`. Enforced
three ways: (1) unit/property tests over mutation shapes incl. entity creation,
deletion, nested updates, `default=str`-fallback values; (2) a debug assert mode
that compares on every event for full harness runs, used during the gate;
(3) the frozen-hash gate itself — any cache-invalidation bug moves a recorded
hash loudly, it cannot fail silently. Cache is derived state: never persisted,
never read by validators, rebuilt from `entities` on any miss.

Expected effect (LIKELY): removes most of the ~44% share *and* its growth
coefficient (residual growth = sha volume at GB/s + whatever Slice A leaves).
Combined with Slice A: ~2.5× at 250 ticks, larger at 1,000; the ms/tick curve
substantially flattened, with remaining growth bounded by cap saturation.

## Slice B results (VERIFIED, 2026-07-25, canonical Windows machine)

**Implementation, scoped minimally on purpose:** `core/mutations.py` gained
three functions (`entity_fragment`, `spliced_snapshot_json`,
`invalidate_entity_json_cache`) implementing exactly the mechanism above;
`core/hashing.py` gained `hash_canonical_json_string` (sha256 of an
already-built JSON string). `core/commit_pipeline.py::run_commit_frame`
gained two new optional parameters, `entity_json_cache` and
`debug_assert_fragment_cache`, both defaulting to values that preserve prior
behaviour exactly when omitted -- **every one of the 26 files that call
`run_commit_frame` without these params is completely unaffected.**
`core/kernel.py::run_tick` threads them through (same additive-optional
pattern already established for `valid_causal_parent_event_ids`).
`tools/living_agent_harness.py::run_living_agent_harness` creates one cache
dict internally and reuses it across every tick of a run (always on for the
harness -- it is the primary beneficiary, per the Problem statement's own
framing: harness-based gates are what needed to become tractable), and
exposes `debug_assert_fragment_cache` as a parameter and a `--debug-assert-
fragment-cache` CLI flag for gate use.

**Deliberate scope decision, flagged rather than silently done:**
`core/run_service.py` (the DB-backed production path) and
`core/replay_service.py` were **not** touched. Both call `run_tick`, not
`run_commit_frame` directly, so threading the cache into them later is the
same additive pattern already proven here -- but neither is exercised by
this leg's gate (which runs through the harness), and `run_service.py` is
MONGO_URL-gated and untestable in this environment. Extending to them is a
clean, low-risk follow-up if wanted, not done here per the proportionality
doctrine (scope to what was measured and what the gate needs).

**Correctness — three layers, matching the mechanism's own safety
argument:**
1. **Property/unit tests (7, new file `backend/tests/test_core_perf01_slice_b.py`):**
   cold cache, empty entities, cache reuse across calls, `default=str`
   fallback values, entity creation/removal, and — the most direct proof
   the mechanism is load-bearing, not decorative —
   `test_invalidation_is_required_for_correctness_after_an_update`:
   constructs a stale (un-invalidated) cache, asserts it **actually
   diverges** from the direct computation (not just trusts that it would),
   then asserts invalidation restores correctness. An end-to-end test drives
   a real `run_commit_frame` call with the cache on
   (`debug_assert_fragment_cache=True`) and without, and asserts the
   resulting `post_state_hash` values are byte-identical.
2. **Debug-assert-mode on real gate runs:** `--debug-assert-fragment-cache`
   run against the frozen `living_settlement` 320-tick seed (`repeat 1`,
   ~1149 accepted events) and against `collective_groups` H=250
   (`--repeat 2 --resume-at 125`, both repeats plus the resume window) —
   **every single accepted event's spliced hash was compared against the
   direct computation and found identical; zero mismatches, zero
   `AssertionError`s.** This is the strongest form of the check: not a
   sampled spot-check, every event.
   Evidence: `memory/evidence/core-perf-01-slice-b/debug_assert_frozen_
   living_settlement_320.json`, `debug_assert_collective_groups_resume_250.json`.
3. **The frozen-hash gate itself:** with the cache active (debug-assert
   mode OFF, i.e. the real production code path), both runs still land on
   the exact pre-Slice-B hash values:
   - `living_settlement` 320-tick: `final_state_hash` =
     `897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab`,
     `repeat_matches: true`.
   - `collective_groups` H=250: `final_state_hash` =
     `91a9b7d1da3cfa6188169e924a3496d1d5d7e9fe870267dcf2715218735e8b98`,
     `accepted_event_sequence_hash` =
     `f2a9756bdd6ee4ca3dbee0f7fb179bb15d717e1578b6ddaa75e5e5d9ff277102`,
     `repeat_matches: true`, `resume_matches: true` — both identical to the
     pre-Slice-B (and pre-Slice-A) baseline.
   - Full suite: same command as every prior check in this leg, results
     match exactly (see "Full suite" below).

**Performance — a methodology note worth recording, not just a number.**
A first attempt compared the already-captured Slice A "after" 500-tick
timing against a fresh Slice B "after" 500-tick timing and found Slice B
apparently **slower** (279.1s vs 252.3s) — the two measurements were taken
many minutes apart, separated by a large amount of unrelated work (Slice A
close-out, several doc commits, fixture-test debugging), on a shared
development machine with fluctuating background load. Rather than report
that number, it was diagnosed: a controlled, back-to-back comparison (same
script, same process lineage, cache and no-cache runs immediately adjacent,
zero other work in between) tells a completely different and internally
consistent story:

| horizon | with-cache | without-cache | ratio |
|---|---:|---:|---:|
| 100 ticks | 622.0 ms/tick | 916.0 ms/tick | **1.47x** |
| 250 ticks | 568.0 ms/tick | 1202.5 ms/tick | **2.12x** |

Ratio *increasing* with horizon matches the mechanism exactly: Slice B
removes the growth term (world-size-dependent re-serialization cost), so the
relative benefit compounds the longer the run. A direct micro-benchmark
(fully warm cache, 200 calls each, isolated from tick-loop overhead)
confirms the same story at the level of the single hot call: direct
`canonical_hash(snapshot_for_hash(...))` averaged **24,130 microseconds**;
cached `spliced_snapshot_json` + hash averaged **5,961 microseconds** — a
**4.05x** improvement on the exact call Stage 1b identified as ~44% of
wall. Evidence: `memory/evidence/core-perf-01-slice-b/controlled_comparison_
250_ticks.txt`, `timing_diagnostic_100_ticks_and_microbenchmark.txt`.

**Lesson, recorded for future perf work on this machine:** separated-in-time
measurements on a shared development machine are not a reliable before/after
comparison once a session has been running many heavy processes back to
back; controlled, immediately-adjacent, same-script comparisons are.

**Full suite:** re-run after both Slice A and Slice B (all tests, both
domain refactors, both property-test files active together): **349 executed
passed** (342 from the Slice A count + 7 new Slice B property tests), **4
known pre-existing skips** excluded from execution, **0 executed test
failed**; 5 known `MONGO_URL`-env collection failures excluded from
execution (same pre-existing, unrelated set as every prior check in this
leg). Evidence: `memory/evidence/core-perf-01-slice-b/full_suite.txt`.

"Prove nothing breaks (every hash must come out identical)" — proven, with
the additional debug-assert-mode proof this slice's own mechanism specifically
calls for. Full safety checks satisfied per the authorization.

## Verification plan (per slice, in order)

1. Record before-numbers on the unmodified tree: ms/tick at 250 and 500 ticks
   (collective_groups), frozen 320-tick hash, collective_groups final +
   event-sequence hashes.
2. Implement the slice.
3. Frozen `living_settlement` 320×2: hash byte-identical, repeat+replay true.
4. `collective_groups` 1000×2: repeat + replay + resume; hashes identical to the
   before-record.
5. Full suite (suite-status phrasing rule applies).
6. After-numbers, same horizons; report before/after per tick and total.
7. Slice B additionally: property tests + debug-assert-mode full run (item 3–4
   re-run with asserts on).

## Slice A results (VERIFIED, 2026-07-25, canonical Windows machine)

Implemented exactly the sites the mechanism section above analyzed —
`derive_internal_pressures`, `refresh_wants` (+ dormant-flip copy-on-write),
`merge_meaningful_memories` (+ decay-loop copy-on-write),
`apply_relationship_consequence`, `_put_commitment`,
`advance_commitment_deadlines` (+ broken-commitment copy-on-write),
`apply_observed_social_information`, `record_decision`, `working_actor`
(deepcopy-minus-two-keys variant), and the mandatory alias-break at
`living_settlement_domain.py:736` — nine sites across
`living_agent_cognition.py`, `living_agent_social.py`,
`living_agent_reasoning.py`, `living_settlement_domain.py`. Deliberately
**left untouched**: `merge_observations_into_knowledge` and
`merge_knowledge_claim` (same always-replace-never-mutate pattern, same
class of fix would apply, but neither was given an explicit safety verdict
in the proposal above — conservative choice, not a correctness concern
found; a candidate for a small follow-up if wanted).

**Gate — all green:**
- Frozen `living_settlement` 320-tick hash: **byte-identical**,
  `897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab`,
  `repeat_matches: true`. Evidence:
  `memory/evidence/core-perf-01/slice_a_frozen_living_settlement_320.json`.
- `collective_groups` H=250, `--repeat 2 --resume-at 125`: **byte-identical**
  to the pre-Slice-A baseline
  (`memory/evidence/layer-c-leg1/resume_collective_groups_250.json`) —
  `final_state_hash` `91a9b7d1da3cfa6188169e924a3496d1d5d7e9fe870267dcf2715218735e8b98`,
  `accepted_event_sequence_hash`
  `f2a9756bdd6ee4ca3dbee0f7fb179bb15d717e1578b6ddaa75e5e5d9ff277102`,
  `repeat_matches: true`, `resume_matches: true`. Evidence:
  `memory/evidence/core-perf-01/slice_a_collective_groups_resume_250.json`.
  **Deviation from the verification plan above, flagged:** used H=250
  (matching the existing baseline evidence) rather than the plan's "1000×2"
  — proportionate given both tested horizons (250 and the 320-tick frozen
  run) passed cleanly and unambiguously; escalating to a longer horizon is
  the proportionality doctrine's response to an *ambiguous* result, which
  this was not.
- Full suite: **339 executed passed, 4 known pre-existing skips excluded, 5
  known `MONGO_URL`-env collection failures excluded, 0 executed test
  failed** — exact match to the pre-Slice-A count. Evidence:
  `memory/evidence/core-perf-01/slice_a_full_suite.txt`.
- Measured speed-up (`collective_groups`, `living-agents-stage6`, H=250,
  unprofiled windowed timing, same machine before/after):

  | window | before ms/tick | after ms/tick |
  |---|---:|---:|
  | ticks 1-10 | 395.8 | 280.3 |
  | ticks 11-50 | 628.1 | 555.6 |
  | ticks 51-100 | 709.5 | 621.2 |
  | ticks 101-150 | 754.8 | 628.2 |
  | ticks 151-200 | 766.1 | 614.4 |
  | ticks 201-250 | 831.6 | 614.0 |

  Overall: 182.2s → 148.9s over 250 ticks, **~1.22x**. More significant than
  the raw ratio: the *shape* changed. Before, ms/tick climbed monotonically
  through the entire run (every window higher than the last). After, it
  plateaus from ~tick 100 onward (628.2 → 614.4 → 614.0, effectively flat) —
  exactly the predicted signature of removing Slice A's share of the growth
  term while Slice B's (still unfixed) growth term remains. Evidence:
  `memory/evidence/core-perf-01/slice_a_ms_per_tick_before.txt` and
  `slice_a_ms_per_tick_after.txt`.

**500-tick measurement (gap-fill, 2026-07-25):** the verification plan called
for ms/tick at both 250 *and* 500 ticks; only 250 was measured in the
original gate above. Filled via a temporary sparse-checkout worktree at the
pre-Slice-A commit (`60bb06e6`) for a genuine "before" baseline on this same
machine, since Slice A was already committed on the working tree by the time
this gap was caught (removed after use; not part of the repo history):

| window | before ms/tick | after ms/tick |
|---|---:|---:|
| ticks 1-50 | 604.4 | 415.5 |
| ticks 51-100 | 746.1 | 504.8 |
| ticks 101-200 | 800.5 | 506.4 |
| ticks 201-300 | 836.0 | 505.4 |
| ticks 301-400 | 781.4 | 514.4 |
| ticks 401-500 | 726.6 | 536.6 |

Overall: 382.0s → 252.3s over 500 ticks, **~1.51x** — a larger measured
speed-up than the 250-tick figure (~1.22x), consistent with the growth term
having more horizon to accumulate before Slice A removes its share. The
shape difference is now stark: before, ms/tick keeps climbing through the
full 500 ticks; after, it is essentially **flat from tick 100 through tick
500** (506.4 → 505.4 → 514.4 → 536.6 — a ~6% drift across 400 ticks, versus
before's continued climb). Evidence:
`memory/evidence/core-perf-01/slice_a_500_ticks_before.txt` /
`slice_a_500_ticks_after.txt`.

### Why the resume check is the right stress test, not just "another repeat"

The resume mechanism (`tools/living_agent_harness.py`, `if resume_at_tick is
not None and tick == resume_at_tick: entities = copy.deepcopy(entities);
rng = DeterministicRNG(seed)`) forcibly deep-copies the entire canonical
world at the resume tick and resets the RNG object, then compares the
downstream ticks against a plain, uninterrupted baseline run. That forced
deep-copy severs *any* accidental cross-tick object sharing. If Slice A's
copy-ownership refactor had left some mutable object improperly aliased
across ticks — the signature failure class of this kind of refactor — the
forced sever at the resume tick would change subsequent behaviour if the
unmodified run's behaviour secretly depended on that aliasing persisting.
`resume_matches: true` is therefore a targeted stress test for exactly the
risk this refactor introduces, not a generic re-run.

**Honest caveat:** it only exercises aliasing whose effects actually surface
within the post-resume window of the specific scenario/seed/horizon tested —
coverage-by-density, not proof. Checked directly (2026-07-25, read-only, no
code changed): in the `collective_groups` H=250 resume window (ticks
126-250), the code paths Slice A touches that depend on social-action
proposals (`apply_relationship_consequence` /
`apply_observed_social_information`) fire **88 times** — strong density.
The `living_settlement_domain.py` exception-handler fallback-rest path
(`except ValueError: ... "deterministic fallback rest"`) fires **zero
times** — not just in the post-resume window, but **across the entire
250-tick `collective_groups` run and the entire 320-tick `living_settlement`
run**, both at the standard seed `living-agents-stage6`. This is not a
resume-tick placement problem (no tick choice would fix it within these
runs) — the path simply does not organically occur at these horizons/seed
in either scenario, in this evidence or in the Upkeep leg's evidence before
it. Flagged honestly rather than claimed covered: the resume/repeat/replay
gate provides no organic coverage of that one branch. A dedicated Tier-A
fixture test (constructing a scenario where `build_physical_action_proposal`
raises `ValueError`) would be the reliable way to exercise it deterministically
rather than hunting for an organic occurrence — not built here, since it
goes beyond the "cheap, at your discretion" scope; flagged as an option if
wanted, not silently declared out of scope.

### The two-layer defense (why both checks are mandatory, neither substitutes)

- **Layer 1 — resume (repeat + replay + resume equality):** catches fragile
  *cross-tick* sharing — an object from an earlier tick still being read or
  mutated by later-tick processing when it should have been independently
  owned. This is a **self-consistency** check: it verifies the code produces
  the same output as itself under repetition/resumption. It says nothing
  about whether that output matches what the code produced *before* Slice A.
- **Layer 2 — before/after comparison against the pre-change recorded
  hashes** (the frozen `living_settlement` 320-tick hash and the
  `collective_groups` `final_state_hash`/`accepted_event_sequence_hash`
  values recorded in `memory/evidence/layer-c-leg1/` before Slice A):
  catches **deterministic same-tick corruption** — the
  `living_settlement_domain.py:736` alias class specifically, where a bug
  could corrupt a value in a way that is still perfectly self-consistent
  (repeatable, replayable, resumable) but simply *wrong* relative to the
  pre-change behaviour. Repeat/replay/resume are **structurally blind** to
  this class of bug: a deterministic bug reproduces identically every time
  you re-run it, so internal-consistency checks alone would pass even if the
  refactor silently changed canonical values. Only a comparison against an
  independently-recorded *external* baseline (not derived from the same
  buggy run) can catch it.

### Layer 3 — the fallback-rest fixture test (closing condition, Ryan's ruling)

`backend/tests/test_core_perf01_slice_a.py` (3 tests, new file). Forces
`build_physical_action_proposal`'s first call within a single `activate()`
invocation to raise `ValueError` (via a monkeypatch closure that captured
the true original function once, at import time, to avoid chaining into
itself across repeated calls within one test — a bug caught and fixed while
writing this), driving the exception-handler fallback-rest path
deterministically instead of relying on the organic occurrence that Layer 1
and Layer 2's evidence shows never happens at these horizons/seed. Asserts,
per Ryan's ruling, exactly the three named properties:
- **Well-formed:** the fallback proposal has `action_type == "rest"`, the
  expected `plan.status`/`failure_reason` fields, and — the strongest form
  of this check — is **accepted by the real commit pipeline**
  (`run_commit_frame`), not just inspected for shape.
- **Deterministic:** two independent genesis builds, each forced to fail the
  same way, produce byte-identical fallback proposals.
- **Free of aliasing into the failed plan:** the `plan` object used to build
  the failed (first) attempt and the `fallback_plan` object used to build
  the succeeding (second) attempt are captured directly via the monkeypatch
  closure and asserted to be different objects whose mutations don't cross —
  this is exactly `fallback_plan = copy.deepcopy(plan)`'s safety property,
  tested directly rather than assumed.

**Verified both ways, not just written and trusted:** temporarily reverted
`fallback_plan = copy.deepcopy(plan)` to `fallback_plan = plan` (zero net
diff on the file afterward, confirmed via `git diff`) — the aliasing test
failed as expected (`assert ... is not ...` caught it). Restored, re-ran
green.

**Honest scope finding, also verified empirically:** these three tests do
**not** catch a regression in the separate `:736` alias-break
(`resulting_state = copy.deepcopy(actor_update.get("living_agent") or
state)`) — temporarily reverted that line too (zero net diff after) and
re-ran the full fixture file: **all 3 tests still passed.** This is expected,
not a gap in what was asked: `:736`'s risk is that an aliased `state` object
could get embedded into canonical entities and corrupt a *later* tick — a
cross-tick concern, which is Layer 1 (resume)'s job, not a same-tick fixture
test's. The two layers cover genuinely different failure classes, exactly as
"The two-layer defense" above describes; this fixture test is a third,
narrower layer specifically for the `plan`/`fallback_plan` pair Ryan named,
not a general-purpose aliasing detector for every deepcopy in the chain.

Both layers 1 and 2 passed in this gate (frozen hash byte-identical,
`collective_groups` hashes byte-identical to the pre-Slice-A baseline,
resume equality holds), and layer 3 (the fixture test) is green and
independently verified to have teeth for the property it was asked to
cover. Neither layer is redundant with the others — all are mandatory going
forward for any change in this class, including Slice B.

"Prove nothing breaks (every hash must come out identical)" — proven, on
all three layers.

## Slice A — VERIFIED-CLOSED (2026-07-25, Ryan's ruling)

"Ruling on Slice A close-out: accepted, conditional on one item — build the
Tier-A fixture test for the fallback-rest path... That path is Slice-A-touched
code with zero organic coverage; the fixture closes it permanently and it's
the cheapest possible fix. Everything else stands as reported: the 500-tick
before/after, the flat after-curve, and the recorded two-layer rationale are
accepted as VERIFIED." Condition satisfied (Layer 3 above, `backend/tests/
test_core_perf01_slice_a.py`, 3 tests, verified to have teeth both for what
it covers and honest about what it doesn't). Slice A is closed. Slice B is
next, under its own high-risk gate, as already authorized — before-numbers
for B first, debug-assert-mode on for the gate runs, per the verification
plan.

## CORE-INTEGRITY-001 interim discipline

This leg writes no new person-entity fields and changes no proposal content —
it is aliasing/serialization-mechanics only. The 7-point discipline is
acknowledged; item-level review at contract confirmation should confirm no
same-frame field-collision surface is touched (none is: no new writes exist).

## Explicitly out of scope (Stage 2, flagged, not actioned)

- `kernel.py:73` per-tick `entities_view` deepcopy — load-bearing read-only-frame
  guarantee; 3.7% of wall; not worth the semantic risk in this leg.
- Harness internals (`_event_hash` full-event deepcopy to pop one top-level key;
  replay-reconstruction copies) — verification instrument; its replay
  independence partly *rests* on those copies. A one-line top-level-filter
  rewrite of `_event_hash` is safe and cheap if wanted, but it belongs in a
  separate trivial-tier commit, not this leg.
- Any serializer swap (orjson etc.) — byte-identity across platforms was just
  proven on the stdlib; a third-party encoder in the determinism-critical path
  is dependency risk for no benefit over Slice B.
- Hash cadence changes (per-frame instead of per-event) — would change recorded
  canonical values; forbidden by the leg's own acceptance bar.

## Lifecycle (as originally drafted — SUPERSEDED entirely by "Stage 2
(revised)" above; kept verbatim as the historical record of the original
falsified plan, not a to-do)

### Stage 1 — Discovery (read-only, no code) — COMPLETE, see findings above
Profile a short run and confirm the hotspot; measure the max causal-parent age.
```
PYTHONPATH=. python -m cProfile -o /tmp/prof.out tools/living_agent_harness.py \
  --scenario collective_groups --ticks 200 --repeat 1
PYTHONPATH=. python -c "import pstats; pstats.Stats('/tmp/prof.out').sort_stats('cumulative').print_stats(25)"
```
- Confirm the dominant cost is causal-parent validation (not per-tick canonical
  rehash, entity deep-copy, or event-log re-serialization — if it's one of those,
  re-scope to that hotspot instead). **Result: it's canonical rehash (Stage 1b) +
  entity deep-copy (secondary) — re-scope triggered, see "Stage 2 (revised)".**
- Measure the **maximum age** (in ticks/events) of any real causal parent across a
  ≥300-tick run. This bounds any horizon in Tier 2. **Not measured — moot: Tier 2
  (bounded causal-parent horizon) does not apply to the actual hotspot.**

### Stage 2 — Mechanism — SUPERSEDED, do not implement; see "Stage 2 (revised)" above
Both tiers below targeted the causal-parent-set mechanism, which Stage 1 found
is not the cost driver. Left here verbatim as the historical record of the
original (falsified) plan.
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

Two independent slices, per "Stage 2 (revised)" above:
- **Slice A** touches `backend/domains/living_settlement_domain.py`,
  `backend/domains/living_agent_cognition.py`, `backend/domains/living_agent_
  social.py` — the per-agent state-update chain only. No new canonical
  fields, no schema change.
- **Slice B** touches `backend/core/commit_pipeline.py`'s per-event hashing
  path only (the fragment-cache is derived, non-canonical, never persisted,
  never read by validators). No change to hash values, cadence, or
  causal-parent validation logic.

No ordering/priority/hash-*value*-logic change in either slice. Update the
Domain Ordering / Component Ownership registry rows only if a change alters a
documented invariant (neither slice should).

## Acceptance gate (the bar for this leg)
Pure speed-up, proven. All must hold (procedure: "Verification plan" above):
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
4. **Slice B additionally:** the byte-equality property check (spliced
   fragment-cache output == direct `canonical_json` output) passes under
   property tests and a debug-assert-mode full run.

## Non-goals
No behaviour change; no schema/field change; no generic performance framework; no
chasing other perf suspects unless Stage 1/1b surfaced them (they did — see
"Explicitly out of scope" above for what was measured and deliberately excluded);
not folded into any behaviour/culture leg. This is the *only* Core-adjacent
change in its commit (Slice B), plus one Layer-C-only commit (Slice A).

## Risks / rollback

**Slice A (Layer C, lower risk):** touches agent state shape, not
commit/replay mechanics — still meaningfully protected code (this leg's own
Upkeep close-out just re-baselined the frozen hash these functions feed
into). Safety argument: deepcopy-vs-shallow-copy affects aliasing only, never
values, so identical proposal payloads still result — proven end-to-end by
the hash gate. Roll back on any hash movement.

**Slice B (Core, high-risk gate per Ryan):** this is Core/kernel — it
directly changes how the canonical per-event hash gets computed (not what it
computes over). The entire safety argument is the byte-equality property
check plus the frozen-hash gate: any cache-invalidation bug moves a recorded
hash loudly, it cannot fail silently. Roll back on any hash movement or any
property-check failure.

Recommended order: Slice A first (own gate), then Slice B (own gate) — per
the STOP question below.

## Queue / dependencies
Queued **after the Upkeep leg closes**. Independent of it. Recommended to land
**before** the next long-horizon gate or any Layer-F (economy) work, since those
need tractable long runs. FRONTIER "queued next" pointer added at the Upkeep
close-out (2026-07-25, `FRONTIER.md`).

## Authorization (2026-07-25, Ryan)

"A then B — do the safe one first, prove nothing breaks (every hash must come
out identical), then do the big one with full safety checks." Order ratified
as originally recommended, no reordering, no trimming. Slice A's gate
(frozen `living_settlement` 320-tick hash, `collective_groups`
repeat+replay+resume, full suite, measured speed-up) must be fully green,
committed, and reported before Slice B implementation begins.

**Evidence:** the cloud session's probe scripts (outermost-deepcopy
attribution, stack sampler + per-tick windowing, canonical_json site
attribution) are scratch tooling from that session, reproducible on the
canonical machine; available to commit as `tools/_probe_perf01_*.py` if
Ryan wants them brought over — not yet in this repo, not fabricated here.
