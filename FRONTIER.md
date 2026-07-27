# Current Frontier

**The only file that declares the current task.** (History is archived in
`CAPABILITY_ROADMAP.md` — not authoritative for current state; full detail for
each closed leg lives in its own contract doc; this file owns "what now" and
stays lean by design — see `AGENT_WORKFLOW.md`'s documentation-load rule.)

```
Layer:          C — Individual Agency (behaviour) + A — Kernel (infra, one-off)
Capability:     Behaviour Enrichment  (variety → social density → individuality → memory)

Active leg:     Layer C — SOCIAL DENSITY, Leg 1: Shared-Storage Intent.
Status:         CONFIRMED 2026-07-27 — IMPLEMENTING. Tier A complete and green
                (21/21, backend/tests/test_layer_c_social_density.py). The
                threshold-only mechanism is in: STORE_SURPLUS_MIN_FOOD = 2
                replaces the inline food >= 3 gate. Contract:
                memory/CAPABILITY-LAYER-C-SOCIAL-DENSITY-LEG1.md.

                NOT yet done, and gated: the organic 5,000-tick
                collective_groups gate, the living-agents-stage6-alt second
                seed, the paired threshold-3 disabled control, and the
                frozen-hash ruling. The pytest suite pins repeat/replay
                equality only — never a literal frozen hash — so a green suite
                is NOT evidence a baseline held. Any moved hash stays
                UNAUTHORISED until a STOP presents the exact causal diff.

                Pre-registered 5,000-tick control complete (collective_groups,
                seed living-agents-stage6, checkpoints 1,000/3,000/5,000):
                shared storage was visible on 33,683 / 37,521 decisions, but
                carried food never exceeded 2. Therefore food >=3 fired zero
                times, STORE_SURPLUS was never generated, and the full run had
                one retrieve / zero stores. Replay exact; deaths 0/0/2 at the
                three checkpoints; group goals and norms zero throughout.
                Evidence: memory/evidence/layer-c-social-density-leg1/.

                Read-only threshold-2 shadow: 56 joint opportunities, existing
                unchanged score would win 31 across 2 distinct actors; actual
                candidate lists peak at 5 vs cap 16. Shadow/no-shadow 40-tick
                hashes are byte-identical. Proposed mechanism: eligibility
                threshold only (named constant 2); score/order/executor remain
                unchanged. STOP before implementation.

                Carried-forward context and remaining open items:
                  - F8 storage trace: CAUSE NOW VERIFIED. The 5,000-tick census
                    locates the earliest dead seam at STORE_SURPLUS's food >=3
                    eligibility gate, not perception, scoring, execution, or
                    the four-tick evidence window. Contract above proposes the
                    smallest causal move; implementation is not authorised.
                  - OQ-1: 64 same-tick same-person `energy` collisions in
                    collective_groups, 0 in living_settlement. Cause UNKNOWN;
                    the F11 attribution was withdrawn. See
                    memory/REGISTRY-COMPONENT-OWNERSHIP.md.
                  - Deferred future rulings: the effort-transfer gradient
                    (memory/FINDING-EFFORT-TRANSFER-ENERGY.md) and the
                    GOAL-SCORING smell, same class, for a future scoring-
                    contract leg: REPAY_DEBT scores 27477
                    against WARN_DANGER's 23435, so repaying a debt outranks
                    warning a neighbour about a predator, and it preempts an
                    in-progress warn plan. VERIFIED by decision receipts
                    (living_settlement, seed stage6-integrated, tick 3).
                    PRE-EXISTING -- not introduced by the genesis re-stream.
                    Deliberately NOT acted on and NOT asserted as correct
                    anywhere; the C-6 fixture pins survival dominance only.
                    Evidence: the deferral row for `warn` organic firing in
                    memory/CAPABILITY_ROADMAP.md.
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

Current gate:   Layer C — Social Density Leg 1 ORGANIC gate + frozen-hash
                ruling. Contract confirmed and Tier A is green; the next phase
                runs the 5,000-tick collective_groups census (checkpoints
                1,000/3,000/5,000), the second seed, and the paired
                threshold-3 disabled control, then STOPs with the exact causal
                diff for every moved hash. Recorded harness invocations:
                memory/evidence/genesis-rng/SHARED-SPAWN-STREAM-2026-07-26.md
                lines 442 and 468.

                Pre-registered at the amendment: threshold 2 can only fire on
                the genesis food endowment (the food-2 bucket is frozen at 64
                across all three checkpoints — no agent ever holds two units
                again after tick 1,000). Passing the organic gate therefore
                does NOT unblock Stage 7C; that stays DEFERRED pending an
                explicit user ruling. See the contract's §9 amendment.

Blocked / parked:
  - Aid Exchange ............... DEFERRED — needs Layer F-A (material surplus)
  - Remaining Layer-E culture .. waits on C + D organic density
```
