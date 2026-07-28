# simulation-sandbox — standing rules

Deterministic simulation kernel. Core owns truth; domains propose.
**The work is simulation dynamics — making the world do things worth watching.**
Architecture work is maintenance-only: it happens when it blocks behaviour,
safety or performance.

**Domain delivery is the default activity. Maintenance is the exception.**

**Authority, in order:**

1. `ENGINE-CONSTITUTION.md` — the eight properties that must hold. Rarely changes.
2. `DYNAMICS-BACKLOG.md` — the operating model, the maintenance freeze, the domain queue.
3. `ACTIVE-LEG.md` — the one domain being delivered right now. Read this before acting.
4. `PRODUCT-STATE.md` — what the world measurably does today.

## Maintenance freeze

Maintenance is permitted **only** when: the active domain cannot activate; it
produces incorrect authoritative state; replay breaks; data corrupts or grows
uncontrolled; or a bug stops the user observing the behaviour. Never because
code could be cleaner, abstractions improved, diagnostics broadened, docs
expanded, or a future subsystem might need it. Budget: 70% domain, 20%
integration and visualisation, 10% maintenance.

No architectural audits during a leg. No refactor unless it removes a blocker
hit twice. No new diagnostic framework unless existing tools can't explain the
failed chain. No speculative support for future domains. One new subsystem per
leg, maximum. Every session either moves the active causal chain forward or
explicitly closes a blocker.

## A domain is done when

Reachable · Deterministic · Consequential · Integrated · Visible · Bounded.
`PASS WITH LIMITATIONS` is a valid completion — name the limitation instead of
widening the contract.

Everything under `memory/archive/` is history. Never take the current task from
it. `memory/evidence/` is data, still citable.

## Session start

`git log --oneline -10`, `git status`, read `ACTIVE-LEG.md` and the docs above,
restate your position in one paragraph, then act.

## How a change is judged — the five checks

1. **Visible** — a player sees the difference in the world, inspector, or event history.
2. **Consequential** — it changes later decisions or state.
3. **Recurrent** — across time, multiple actors. One firing is not a behaviour.
4. **Diverse** — it doesn't just replace `rest` with a new dominant loop.
5. **Deterministic** — same version, seed, inputs reproduce exactly.

No event-count bands. No pre-registration for tuning. Change the dial, watch
the world, keep or revert.

## Hashes

`backend/tests/test_frozen_baseline_hashes.py` proves the engine is
deterministic for an unchanged version, seed and scenario. It is not a
behavioural gate. When an intended change moves it, update the pinned constants
**in the same commit** and say what moved them in the commit message.

## Hard rails (explicit confirmation required)

- Destructive git: reset/checkout/clean/stash-drop on the working tree,
  force-push, history rewrite, branch deletion.
- Committing secrets — never, with or without confirmation.
- Anything that breaks one of the eight constitutional properties.

## Reporting

- Label every claim VERIFIED / LIKELY / UNKNOWN. Never promote one to another.
- Suite status is never unqualified "green" while exclusions exist.
- Hash strings pasted from run output, never from memory.
- Close-out: STATUS / CHANGES / RISKS / NEXT STEP. Keep it short.

## Proportionality

- Cheapest decisive observation first. Name the single observation that would
  settle the question, run it, escalate only if it comes back ambiguous.
- Verification effort is bounded by the cost of the failure it prevents.
  Reversible local work earns one cheap check.
- If the verification plan is longer than the diff, cut the plan.
- Narrowest falsifying diagnostic before any full harness re-run.
- Report the single highest-severity flaw or "no blocking flaw". Don't
  enumerate. "Good enough, ship" is a valid verdict.

## Runs and tests

- Suite: `python -m pytest` from `backend/`.
- Harness: `py -3.12 -m tools.living_agent_harness --scenario living_settlement
  --ticks 320 --seed living-agents-stage6` from `backend/`.
- Long runs: redirect to a file, read back the summary (a PreToolUse hook
  enforces this — don't fight it).
- UI: backend `uvicorn server:app --port 8000` from `backend/`, frontend
  `npm start` in `frontend/` (port 3010).
- Worktrees only when parallel work genuinely needs isolation. Default to
  working in the main checkout.

## Environment

Windows; quote paths; git-bash available at
`C:\Program Files\Git\bin\bash.exe`.

## On ambiguity

Name the gap. No invented data, constants or fields. If docs, code and tests
disagree, say so, show evidence, recommend one option. Silence is not approval.
