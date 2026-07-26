# Current Frontier

**The only file that declares the current task.** (History is archived in
`CAPABILITY_ROADMAP.md` — not authoritative for current state; full detail for
each closed leg lives in its own contract doc; this file owns "what now" and
stays lean by design — see `AGENT_WORKFLOW.md`'s documentation-load rule.)

```
Layer:          C — Individual Agency (behaviour) + A — Kernel (infra, one-off)
Capability:     Behaviour Enrichment  (variety → social density → individuality → memory)

Active leg:     Layer C — SOCIAL DENSITY.  Status: NOT STARTED.
                Activated 2026-07-26 on the CORE-INTEGRITY-002 close-out.
                Needs its own probe + contract phase (Invariant 12 v2) before
                ANY implementation. This is a new leg-loop start.

                Carried forward, open and unstarted:
                  - F8 storage trace: WHY agents never store. Measured: one
                    storage action in 1,000 organic ticks of collective_groups
                    (a `retrieve`), zero `store` actions ever. This is the
                    first thing social density has to move.
                  - OQ-1: 64 same-tick same-person `energy` collisions in
                    collective_groups, 0 in living_settlement. Cause UNKNOWN;
                    the F11 attribution was withdrawn. See
                    memory/REGISTRY-COMPONENT-OWNERSHIP.md.
                  - Rulings queued for Ryan: the effort-transfer gradient
                    (memory/FINDING-EFFORT-TRANSFER-ENERGY.md) and F8 A/B/C.
                  - DEBT, load-bearing before Stage 11 touches population
                    counts: per-parameter-PER-ENTITY RNG keying. Authorised;
                    only per-parameter is implemented in world/generator.py.
                    With per-parameter streams, adding a person still shifts
                    every LATER person's draws.
                  - CORE-INTEGRITY-004: single-run A/B action-count deltas are
                    untrustworthy at tens-of-percent scale. Social density's
                    first act -- the 5,000-tick baseline control sampled at
                    1,000 / 3,000 / 5,000 -- is now DOUBLY motivated: it is
                    both the organic-reachability baseline and the only way to
                    separate signal from ordering noise. Single-horizon A/B
                    readings are suspect.

Closed leg:     Variety Leg 1 — Upkeep drive
Status:         VERIFIED — CLOSED (2026-07-25). Full detail, gate results,
                adversarial review (Grok/xAI), and findings ledger:
                memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md.
Headline:       Agents rest less, tend worn structures on their own initiative.
                Rest fraction falls (living_settlement 73.3%->32.1% seed1;
                collective_groups 89.5%->40.9% / 88.9%->47.2% alt seed); action
                mix broadens (Shannon entropy 0.75->2.31 / 1.52->2.46 bits).
                Frozen living_settlement hash moved (re-baseline authorised):
                84d3ad52...c32d2 -> 897f3f7f...3c5ab.

Closed leg:     CORE-PERF-01 — per-tick validation cost (O(n^2) -> O(n))
Status:         VERIFIED — CLOSED (2026-07-25). Layer A infra, hash-neutral,
                queued behind the Upkeep leg per its own doc. Full detail,
                mechanism, and gate results: memory/CORE-PERF-01-TICK-
                VALIDATION-COST.md.
Headline:       Two slices, both hash-neutral (frozen living_settlement +
                collective_groups hashes byte-identical throughout, proven
                with debug-assert-mode on every accepted event for Slice B).
                Slice A (Layer C copy-ownership refactor): ~1.22x-1.51x.
                Slice B (Core fragment-cached hashing): ~1.47x-2.12x,
                increasing with horizon. Full suite green throughout, no
                executed failure at any step.
Deferred follow-ups (not blocking, not started): thread the Slice B cache
                into core/run_service.py / core/replay_service.py; a fixture
                test for merge_observations_into_knowledge / merge_knowledge_
                claim's deepcopy sites (same safe pattern as Slice A, never
                explicitly cleared).

Next (per THE-SPINE.md's stated order, not yet started): Layer C — social
                density, the next item after variety in the behaviour-
                enrichment sequence (variety -> social density ->
                individuality -> memory). Needs its own probe + contract
                phase (Invariant 12(v2)) before any implementation — this is
                a new leg-loop start, not a continuation of either closed leg
                above.

Blocked / parked:
  - Aid Exchange ............... DEFERRED — needs Layer F-A (material surplus)
  - Remaining Layer-E culture .. waits on C + D organic density
```
