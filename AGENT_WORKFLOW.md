# AGENT_WORKFLOW.md — how a capability leg is executed

Operational process only. This file is deliberately kept out of the strategic docs:

- **Rules & invariants** (hard rails, forbidden fields, determinism, reporting labels, proportionality): `CLAUDE.md` — always in force. This file never restates them; it points to them.
- **What & why** (capability definitions, status, acceptance criteria, deferral register): `memory/CAPABILITY_ROADMAP.md`.
- **Long-range** (Stage 9–15 charters, pre-flight friction): `memory/MACRO-ROADMAP.md`.
- **The current leg's contract**: `memory/CAPABILITY-STAGE-<N>-<NAME>.md` — the durable per-leg state between sessions.

Superseded by this file: the per-leg execution prompts (`STAGE-8-MASTER-PROMPT.md`, `STAGE-8-CONTINUATION-PROMPT.md`, `STAGE-8B-PROMPT.md`, `STAGE-8B-TO-9-PROMPT.md`) each re-encoded this same process. The process is here once; the stage-specific direction lives in each leg's contract doc.

## Session start (every session, before acting)

1. `git log --oneline -10` and `git status`.
2. Read `THE-SPINE.md` + `FRONTIER.md` + `CLAUDE.md`, and the active leg's contract.
3. Restate your position in one paragraph (branch, what's committed, what's uncommitted, the one open blocker). Then act.

## The leg loop (gate-and-stop)

One leg per session (minimum: one phase per session for large legs). No leg starts until the previous leg's STOP is answered with explicit user approval.

1. **Probe** — read-only measurement of the committed runs (`backend/tools/_probe_*.py`, seed `living-agents-stage6`). No constant enters a contract without a pasted distribution behind it. Organic reachability is probed *before* the contract is written for extensions of existing organic behaviour; genuinely new decision logic instead carries a post-build acceptance gate, pre-registered in the contract (CLAUDE.md invariant 12 v2).
2. **Contract** — write the leg's doc in `memory/` (goal, organic-reachability evidence, agency model, mechanism, commit-order analysis, validation, constants table with evidence, registry schema, non-goals, acceptance gate, risks). Status PROPOSED. Contract phases run in **plan mode**: produce the doc, present it, **STOP** for user confirmation before implementing.
3. **Implement** — contract-conformant, proposal-only, through the existing registered-validator seam.
4. **Verify** — the full gate (template below).
5. **Adversarial review** — an independent agent (non-Anthropic model; e.g. via the Codex/Zen flow), reviewing the branch diff against a bare-claims list, blind first pass then builder-seeded. Never self-review; record the independence level honestly. Findings fixed ⇒ **re-run the full gate** (fixes invalidate prior run evidence) ⇒ then commit.
6. **Document + commit + STOP** — the leg's contract status, the roadmap frontier pointer, and the behaviour ship in the **same commit series**. Close-out report: STATUS / CHANGES / RISKS / NEXT STEP. Then end the turn and wait for an explicit "proceed"; the next leg starts in a fresh session.

If context runs low mid-phase, write a "Session handoff" note into the leg contract (done / in-flight / next command), commit nothing extra, and tell the user to start a fresh session — the doc is the memory, not the context window.

## Gate template (every leg)

- Focused tests: forged-field rejection by re-derivation + byte-equality; duplicate idempotence; capacity bound; replay + resume reconstruction.
- The **integrated full-kernel test through same-frame upstream revision churn** in the real commit pipeline (the class of defect focused tests miss).
- An end-to-end causal-chain proof from committed records.
- Organic proof measured on an unseeded 1,000-tick run, 0 deaths — or the deferral classification recorded up front (CLAUDE.md deferral taxonomy).
- Full regression green (report honestly per CLAUDE.md phrasing — never bare "passes cleanly").
- Determinism: repeat + replay + resume equality on the touched scenario.
- Frozen `living_settlement` 320-tick hash byte-identical (moving it needs an authorised re-baseline STOP).
- New scenario hashes recorded in the leg contract + the roadmap changelog.
- New registry peak capacity measured with ≥20% headroom vs its payload target.

## Runs and tests

- Full suite: `python -m pytest` from `backend/`. Harness: `backend/tools/living_agent_harness.py`, seed `living-agents-stage6`, recorded invocations only — if you can't locate one, STOP and ask.
- Long runs: redirect output to a file; read back only the summary block (repeat/replay matches, hashes, accepted-by-type, deaths). Never dump full run logs into context.
- Delegate probe runs and log-summary extraction to subagents to keep the main context lean. The adversarial review stays an independent agent — never you reviewing your own diff.
- Windows shell: quote paths; prefer `python -m pytest` from `backend/`; avoid POSIX-only assumptions unless the shell is git-bash. Scratch output under ignored paths or OS temp, never committed.

## Commit discipline

- House style: `feat(stage-8b): …`, `fix(8c): …`, `docs: …`. One leg, one purpose; reviewable, reversible, explainable.
- Nothing committed past a failing gate, an open review finding, or an unresolved STOP.
- Doc updates ship with the behaviour they describe, in the same commit series.
- No destructive git ever: no reset/checkout/clean/stash-drop on the working tree, no force-push, no history rewrite, no branch deletion.

## Documentation load

Maintain only: the frontier (`FRONTIER.md`); the active leg's contract; source-of-truth updates when behaviour actually changes; one compact close-out per leg. No new planning, readiness-audit, taxonomy, adoption-report, reconciliation, or duplicated continuation-prompt docs unless the user explicitly requests them. Constants live beside the code with a one-line comment naming the evidence that set them.
