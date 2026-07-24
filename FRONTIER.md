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

Active leg: CORE-PERF-01 (memory/CORE-PERF-01-TICK-VALIDATION-COST.md) —
      Stage 1 Discovery complete (2026-07-25, read-only, no code changed).
      Original hypothesis (causal-parent-set rebuild in Core's
      commit_pipeline.py) FALSIFIED by profiling: run_commit_frame is only
      ~17% of profiled runtime. Actual dominant cost (~75%) is copy.deepcopy,
      reached through living_settlement_domain.py's per-agent activate() call
      graph -- living_agent_cognition.py / living_agent_social.py functions
      each doing a wholesale copy.deepcopy(state) of the full per-agent
      canonical state. This moves the touch-surface from Layer A (Core) to
      Layer C (domain code) -- a different risk profile requiring
      re-authorization before any Stage 2 code. STOP delivered with findings
      and options; awaiting direction. No active Layer C *behaviour* leg is
      open (this is infra, not a behaviour leg).

Blocked / parked:
  - Aid Exchange ............... DEFERRED — needs Layer F-A (material surplus)
  - Remaining Layer-E culture .. waits on C + D organic density
```
