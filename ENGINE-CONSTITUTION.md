# Engine constitution

The properties that make this engine worth having. They are not process — they
are what the code guarantees. Changing any of them is a deliberate act with the
owner's agreement, not a side effect of a feature.

Adopted 2026-07-28, replacing the staged capability roadmap and its gates.

## The eight

1. **Core owns canonical truth.** Nothing else writes state.
2. **Domains propose; Core validates and commits.** Proposal-only, always.
3. **Same version, seed and inputs replay identically.**
4. **Deterministic ordering and RNG.** No wall-clock, no iteration-order
   dependence, no probabilities standing in for behaviour.
5. **Accepted events retain causality and attribution.** Every change is
   traceable to what caused it and who did it.
6. **State remains bounded.** Hard caps, measured headroom.
7. **Validators re-derive rather than trust domain output.**
8. **No LLM-generated canonical truth.**

These are the competitive advantage. On 2026-07-28 a `social_warn` regression
was isolated to *person-007, frame-2, no proposal emitted, replanned to
REPAY_DEBT at frame-4* in about six minutes. Almost no simulation project can
do that. It is possible only because of 3, 4 and 5.

## What freezes, and what doesn't

- **Exact hashes freeze only for an unchanged version, seed and scenario.** A
  hash is a reproducibility check, not a behavioural gate. `backend/tests/
  test_frozen_baseline_hashes.py` exists to prove the engine is deterministic,
  not to stop the world from changing.
- **A hash that moves because behaviour intentionally changed is expected.**
  Update the pin in the same commit as the change and say what moved it in the
  commit message. No ratification ceremony.
- **±3% event-count bands do not apply to intended behaviour changes.**
  Retired. They were built to catch regressions in a mature system and were
  blocking the changes that make the world alive.
- **Tuning changes are not pre-registered.** Change the dial, watch the world,
  keep or revert.

## Architecture work is maintenance-only

Kernel, ordering, storage and performance work happens when it **blocks
behaviour, safety or performance** — not on its own schedule, not as the main
event. If an architecture task can't name the behaviour it unblocks, it waits.

## Behavioural invariants that survive the roadmap

Three rules from the retired culture protocol that are about the world, not the
process, and still hold:

- Influence boosts or suppresses existing candidates only. It never outranks
  urgent survival, and it never invents a candidate.
- No hidden group mind. Groups act through members, with carriers and
  provenance.
- Social and cultural state is canonical, decision-affecting state — never
  generated text.

## Still true, still enforced

- Destructive git operations need explicit confirmation.
- Secrets are never committed.
- If docs, code and tests disagree, name the conflict rather than picking a
  side silently.
- Claims are labelled VERIFIED / LIKELY / UNKNOWN, and never promoted.
