# Current Frontier

**The only file that declares the current task.** (History is archived in
`CAPABILITY_ROADMAP.md` — not authoritative for current state; individual legs in
their contracts; this owns "what now".)

```
Layer:          C — Individual Agency
Capability:     Behaviour Enrichment  (variety → social density → individuality → memory)
Closed leg:     Variety Leg 1 — Upkeep drive
Status:         VERIFIED — CLOSED (2026-07-25). Adversarial review (Grok/xAI,
                cross-vendor) complete; findings ledger + rulings recorded in
                scratchpad/upkeep_adversarial_review_ledger.md; all FIX items
                applied. See memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md §6/§10.
Scenario:       living_settlement (direction + frozen re-baseline, seed1 only) +
                collective_groups (direction + magnitude/organic-reachability
                gate, both seeds)
Owner of docs:  cloud session    ·    Implements: terminal session

Player outcome: agents spend visibly less time resting and maintain worn
                structures on their own initiative.

Primary metric: rest fraction (VERIFIED, H=250, memory/evidence/layer-c-leg1/):
                living_settlement 73.3%->32.1% (seed1 only), collective_groups
                89.5%->40.9% (seed1) / 88.9%->47.2% (alt seed). Action mix
                broadens 17-19 distinct types; Shannon entropy of actions_by_type
                rises 0.75->2.31 bits (collective_groups) / 1.52->2.46 bits
                (living_settlement) — cite entropy, not rest% alone (finding F-01).

Gate shape (magnitude measured, not pre-picked; Invariant 12(b)) — ALL GREEN:
  - rest fraction strictly decreases vs baseline: collective_groups on BOTH seeds;
    living_settlement on its one run (living-agents-stage6, seed1 only) — the
    alt seed was never independently run on living_settlement (finding F-03;
    "both scenarios, both seeds" in the original claim overstated this)
  - Upkeep fires organically by N=8 distinct actors across M=2 structures on
    collective_groups (both seeds) and living_settlement (seed1 only) — same
    coverage shape as above; repair count nonzero, not cannibalised
  - 0 deaths, 8 alive on every run; survival never suppressed
  - determinism holds: repeat + replay + resume equality, both scenarios, H=250,
    primary seed
  - frozen living_settlement hash moved (EXPECTED) 84d3ad52...c32d2 ->
    897f3f7f...3c5ab; full causal diff (all 7 shifted action types, not just
    rest/tend/repair — finding F-06) recorded in the leg doc §6 item 3;
    re-baseline AUTHORISED (Ryan, 2026-07-25) and applied
  - full suite (memory/evidence/layer-c-leg1/full_suite_closeout.txt): 339
    executed passed; 5 known MONGO_URL-env collection failures excluded from
    execution (pre-existing, unrelated to this leg); no executed test failed;
    4 pre-existing skips (Docker live-server env only)
  - dedicated false-belief detection test added (finding F-04), replacing the
    vacuous false_belief_count >= 0 net; demonstrated to fail under an induced
    regression and pass restored

Active leg: CORE-PERF-01 (memory/CORE-PERF-01-TICK-VALIDATION-COST.md) --
      Stage 1 + Stage 1b Discovery complete (2026-07-25, both read-only, no
      code changed). Original hypothesis (causal-parent-set rebuild in Core's
      commit_pipeline.py) FALSIFIED. VERIFIED attribution (outermost-call
      timing + 200 Hz stack sampling, immune to cProfile's recursive-call
      inflation): dominant cost is commit_pipeline.py:463's per-accepted-
      proposal whole-world rehash (~44% of wall on its own, ~60% total for
      canonical hashing/serialization -- Core, Slice B); secondary cost is
      wholesale per-agent copy.deepcopy(state) in the living_settlement_
      domain.py activation chain (~22-33% of wall -- Layer C, Slice A). Full
      two-slice Stage 2 mechanism proposal now folded into the contract doc
      (Slice A: Layer C single-boundary-copy ownership refactor + a
      mandatory alias-break at living_settlement_domain.py:736, lower risk,
      recommended first; Slice B: Core fragment-cached world-snapshot
      serialization, byte-identical hashes via a byte-equality property
      check, high-risk gate, recommended second). AUTHORIZED by Ryan
      (2026-07-25): "A then B". **Slice A VERIFIED-CLOSED (2026-07-25, Ryan's
      ruling):** frozen living_settlement 320-tick hash byte-identical,
      collective_groups H=250 repeat+resume byte-identical, full suite exact
      match (339 passed/4 skipped/5 known errors/0 failed), measured ~1.22x
      speed-up at H=250 (~1.51x at H=500, gap-filled per the verification
      plan) with the ms/tick growth curve essentially flat from ~tick 100
      onward at both horizons (was climbing monotonically the whole run
      before). Three-layer defense recorded in the contract doc: resume
      catches cross-tick aliasing (stress-checked -- 88 social-action hits
      in the post-resume window); the before/after hash comparison against
      the pre-change baseline catches deterministic same-tick corruption
      repeat/replay/resume is structurally blind to; a new Tier-A fixture
      test (backend/tests/test_core_perf01_slice_a.py, 3 tests) closes the
      exception-handler fallback-rest path's zero-organic-coverage gap
      permanently -- verified to have teeth (fails under an induced
      regression in what it covers, restored) and honestly scoped (does not
      catch the separate :736 cross-tick alias class, which is Layer 1's
      job, verified empirically). Evidence: memory/evidence/core-perf-01/.
      **Slice B VERIFIED (2026-07-25), awaiting Ryan's close-out ruling:**
      fragment-cached world-snapshot serialization in core/mutations.py +
      core/hashing.py, threaded through commit_pipeline.py -> kernel.py ->
      the harness (26 existing run_commit_frame callers unaffected -- new
      params default to prior behaviour). Debug-assert-mode proved
      byte-equality on every single accepted event across both full gate
      runs (frozen living_settlement 320-tick, collective_groups H=250
      repeat+resume) -- zero mismatches. Hash-neutral: both runs still land
      on the exact pre-Slice-B hashes with the cache active. 7 new property
      tests (backend/tests/test_core_perf01_slice_b.py), including a direct
      proof that cache invalidation is load-bearing (a stale, un-invalidated
      cache is asserted to actually diverge, not just trusted to). Measured
      speed-up via controlled back-to-back comparison (a first attempt using
      separated-in-time measurements misleadingly showed a slowdown --
      diagnosed as machine noise, not a regression, and documented as a
      methodology lesson): ~1.47x at 100 ticks, ~2.12x at 250 ticks, ratio
      increasing with horizon as the mechanism predicts; ~4.05x on the
      isolated hot call (24.1ms -> 6.0ms, fully warm cache). Full suite: 349
      executed passed (342 + 7 new), 4 known skips excluded, 5 known errors
      excluded, 0 failed. Evidence: memory/evidence/core-perf-01-slice-b/.
      Deliberately did not touch core/run_service.py or core/replay_
      service.py (not exercised by this leg's gate, MONGO_URL-gated in this
      environment) -- same additive pattern available as a follow-up. No
      active Layer C *behaviour* leg is open (this is infra, not a
      behaviour leg).

Blocked / parked:
  - Aid Exchange ............... DEFERRED — needs Layer F-A (material surplus)
  - Remaining Layer-E culture .. waits on C + D organic density
```
