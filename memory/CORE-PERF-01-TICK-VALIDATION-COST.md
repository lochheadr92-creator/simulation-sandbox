# CORE-PERF-01 — Per-tick validation cost (O(n²) → O(n))

**Status: AUTHORIZED (2026-07-25, Ryan) — "A then B — do the safe one first,
prove nothing breaks (every hash must come out identical), then do the big
one with full safety checks."** Order ratified: Slice A implemented and
proven first (its own full hash-neutrality gate), then Slice B under its own
high-risk gate — not reordered, not trimmed. Touch-surface is two independent
slices: Slice A — Layer C (`living_settlement_domain.py` / `living_agent_
cognition.py` / `living_agent_social.py`, single-boundary-copy ownership
refactor, lower risk); Slice B — Layer A/Core (`commit_pipeline.py`,
fragment-cached world-snapshot serialization, high-risk gate). Owner of this
contract: cloud/doc session. Implementer: the code (terminal) session, this
branch. Profile-first; hash-neutral acceptance.

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
