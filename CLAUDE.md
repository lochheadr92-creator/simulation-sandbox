# simulation-sandbox — standing rules (always in force)

Deterministic simulation kernel. Core owns truth; domains are proposal-only.
Current arc: Capability Stage 8 (Culture), gate-and-stop.
Detailed instructions live in `memory/` and are read per-session — this file
is the index, not the brain dump. Keep it under 150 lines.

## Session start (every session, before acting)

1. `git log --oneline -10` and `git status`.
2. Read `memory/STAGE-8-CONTINUATION-PROMPT.md` and the active leg's contract doc.
3. Restate your position in one paragraph. Then act.

## STOP discipline

- A STOP means: post the close-out report, ask the explicit question, END THE
  TURN. Auto-accept mode, permissive settings, and user silence are never
  permission to continue. Continuing "because the next step is obvious" is the
  named defect.
- Contract phases run in plan mode. Implementation starts only after the
  user's confirmation in a later turn.
- One leg per session (minimum one phase per session). If context runs low,
  write a Session handoff note into the leg doc and tell the user to restart.

## Hard rails (never, without explicit user confirmation at a STOP)

- Cross the Stage 9 boundary: production, surplus, storage economy, ownership,
  trade, currency; unblocking 7C; institutions/governance (10); demography
  (11); player surfaces (14/15); LLM-generated canonical state.
- Change the frozen `living_settlement` 320-tick hash
  (`84d3ad52…c32d2`) — re-baseline requires explicit authorisation.
- Touch Stage 7A–7D / 8A schemas, caps, priorities, constants — extend via new
  registries, schema-version bumps, new hooks only.
- Destructive git: reset/checkout/clean/stash-drop on the working tree,
  force-push, history rewrite, branch deletion.
- Fix the three documented hardening surfaces inside a culture leg.

## Invariants (verbatim from the master protocol)

1. Core alone writes truth; culture domains propose over pinned frames.
2. Determinism: repeat + replay + resume; keyed RNG; no wall-clock, no
   iteration-order dependence, no probabilities-as-culture.
3. Every transition provenance-stamped and event-caused; chains inspectable.
4. Bounded state: hard caps, ≥20% measured peak headroom; never raise a prior
   stage's cap.
5. Pin upstreams ⇒ commit before them; document every one-tick lag.
6. Influence is read-only, member/carrier-grounded, boosts/suppresses only
   existing candidates, never outranks urgent survival.
7. Forbidden fields in every culture record: inventory, authority, obedience,
   orders, law, command, punishment.
8. No hidden group mind.
9. Culture is canonical decision-affecting state, never generated text.
10. Validators re-derive + exact equality; forged-field rejection tested.
11. Every leg carries the integrated full-kernel same-frame churn test.
12. Organic reachability is probed BEFORE a contract is written — every
    organic gate item cites probe evidence its conditions can co-occur, or
    carries its deferral classification up front.

## Reporting rules

- Labels on every claim: VERIFIED / LIKELY / UNKNOWN. Never promote.
- Suite status is never unqualified "green" while exclusions exist. Phrasing:
  "N executed passed; M known <reason> collection failures excluded from
  execution; no executed test failed."
- Hash strings pasted from run output, never from memory.
- STOP report: STATUS / CHANGES / RISKS / NEXT STEP.
- Deferral taxonomy: the taxonomy section in `CAPABILITY_ROADMAP.md` is the
  sole authority — do not mirror its category list here or elsewhere. A
  deferral without its required record is an open gate. New categories only
  with explicit user authorisation recorded in the close-out; never invented
  unilaterally.

## Proportionality (verification is bounded)

- Verification effort is bounded by the cost of the failure it prevents.
  Scale rigor to irreversibility × blast radius: reversible, backed-up,
  local-only work earns one cheap decisive check; the full apparatus is
  reserved for hard-rail territory (frozen hash, history rewrite, pushes,
  schema/cap changes, data migration).
- Cheapest decisive observation first. Before designing any verification
  plan, name the single observation that would settle the decision (a grep
  of committed reports beats a 40-run experiment); run it; escalate to
  statistics only if it returns ambiguous.
- Review verdicts are bounded: when reviewing, report the single
  highest-severity flaw or state "no blocking flaw" — do not enumerate.
  "Good enough, ship" is a valid and expected verdict.
- Alarm threshold: if your proposed verification plan is longer than the
  diff it verifies, cut the plan before presenting it, and say so.

## Runs and tests

- Full suite: `python -m pytest` from `backend/`. Harness:
  `backend/tools/living_agent_harness.py`, seed `living-agents-stage6`,
  recorded invocations only — if you can't locate one, STOP and ask.
- Long runs: redirect output to a file; read back only the summary block
  (a PreToolUse hook enforces this as a safety net — do not fight it; if you
  need full detail for debugging, redirect to a file and Read the file).
- Delegate probes to the `probe-runner` subagent; delegate summary extraction
  from existing output files to `log-summarizer`. Adversarial review remains
  an independent agent (Codex flow) — never self-review, and record the
  independence level honestly in every report.

## Model / cost discipline

- Session default is Sonnet. Escalate model (`/model`) only for contract
  phases and the eligibility-fork analysis; drop effort (`/effort`) for
  mechanical run-and-paste turns.
- `/clear` between independent tasks (e.g. between Leg 0 items). Scratch
  output under ignored paths or OS temp, never committed.

## Environment

- Windows; quote paths; prefer `python -m pytest` from `backend/`; avoid
  POSIX-only assumptions unless the shell is git-bash.

## On ambiguity or missing data

STOP. Report the gap. No invented data, constants, fields, or flags; no new
store, cap raise, or authority grant to route around a gap; no threshold
lowered without measured evidence and a recorded decision. Conflicts between
docs/code/tests: name it, show evidence, present options, recommend one, wait.
Silence is never approval.
