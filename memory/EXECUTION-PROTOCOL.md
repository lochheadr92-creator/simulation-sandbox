# Execution Protocol — capability-stage delivery (stage-agnostic)

**Version: 1.2 (2026-07-22) · Status: PROPOSED — uncommitted draft, user review pending**

Scope: binding process for every capability-stage leg from **Stage 9 onward**.
Stage 8 remains governed by `STAGE-8-CONTINUATION-PROMPT.md` (in flight; a leg
finishes under the rules it started with — no mid-arc re-basing).

## Position in the document hierarchy (reference, never mirror)

- `SOURCE-OF-TRUTH-v2.md` — architecture authority.
- `CAPABILITY_ROADMAP.md` — capability sequencing, stage status, **the single
  frontier pointer**, the deferral + test-flake taxonomies. Referenced here,
  never mirrored.
- `ROADMAP.md` — technical-phase authority.
- `CLAUDE.md` — harness standing rules (session start, STOP discipline,
  reporting labels + suite-status phrasing, proportionality doctrine,
  model/cost, environment). Referenced here, never mirrored.
- **This protocol** — the leg process: lifecycle, gate template, review
  policy, generic invariants, deferral mechanics, commit discipline.
- Stage master prompts — **stage-specific deltas only**: the stage boundary,
  scope decisions, leg carve, stage constants and authorities. Each pins a
  protocol version (e.g. `Protocol: EXECUTION-PROTOCOL v1.0`) and may
  override a clause only by naming it explicitly.

Conflict rule: architecture → SOT-v2; sequencing/status → CAPABILITY_ROADMAP;
process → this protocol unless the pinned stage prompt explicitly overrides;
harness conduct → CLAUDE.md.

## Leg lifecycle (gate-and-stop; one leg per session minimum granularity)

1. **Probe** — read-only measurement of committed runs. No constant enters a
   contract without a pasted distribution. Organic reachability is probed
   BEFORE the contract is written: every organic gate item cites probe
   evidence that its conditions can co-occur in the standing scenario, or
   carries its taxonomy classification up front. *(v1.2)* Where a leg
   introduces decision logic that cannot exist before implementation,
   reachability is instead deferred to a post-build acceptance gate per
   invariant 12(b): the contract states this classification up front,
   pre-registers the acceptance gates, and the probe phase still measures
   every constant it can from committed runs.
2. **Contract** — the leg doc in `memory/`, mirroring the established
   structure (goal, organic-reachability evidence, agency model, mechanism,
   commit-order analysis, validation, contracts table, justified constants
   table, registry schema, non-goals, acceptance gate, risks). Status
   PROPOSED. Plan mode — design, not code. **STOP for user confirmation.**
3. **Implement** — contract-conformant, proposal-only, through existing seams.
4. **Verify** — the gate template below plus the contract's own items.
   Evidence pasted, never claimed.
5. **Adversarial review** — independent agent, separate process; independence
   level recorded honestly (cross-model automated review is never described
   as a human audit). Findings fixed ⇒ **full gate re-run** (fixes invalidate
   prior run evidence) ⇒ then commit.
6. **Document + commit + STOP** — leg doc status, roadmap frontier pointer,
   and behaviour in one commit series. Close-out report (STATUS with
   evidence labels / CHANGES / RISKS / NEXT STEP); end the turn; explicit
   "proceed" required; next leg starts in a fresh session.

## Gate template (every leg; stage prompts may add items, never subtract)

- Focused tests: forged-field rejection via full re-derivation +
  byte-equality; duplicate idempotence; capacity bound; replay + resume
  reconstruction.
- The **integrated full-kernel test through same-frame upstream revision
  churn** in the real commit pipeline (mandatory; focused-only verification
  is a named historical defect).
- An end-to-end causal-chain proof from committed records.
- Organic proof on an unseeded run, 0 deaths, on the standing scenario
  decision's vehicle; counts measured and pasted.
- **Stability** *(v1.1)*: the organic proof demonstrates recurrence or
  persistence over the horizon per a contract-defined stability measure
  (recurrence count, persistence window, or steady-state property) — not a
  single occurrence. A phenomenon that is honestly one-shot is declared so
  in the contract, with rationale.
- **Robustness** *(v1.1)*: the organic phenomenon fires under ≥2 distinct
  seeds (the recorded seed plus ≥1 alternate). Orthogonal to determinism:
  repeat + replay + resume equality still holds per seed, unchanged.
  Alternate-seed hashes are recorded separately; frozen baselines bind only
  their recorded seed; other gate items bind on the recorded seed unless the
  contract explicitly extends them.
- Full regression, reported per the suite-status phrasing rule (CLAUDE.md).
- Determinism: repeat + replay + resume equality on every touched scenario.
- Every frozen baseline hash byte-identical (pasted from run output); new
  scenario hashes recorded in the leg doc.
- Registry peak capacity measured, ≥20% headroom stated.

## Generic invariants (stage-neutral master set)

Stage prompts instantiate these for their domain; `CLAUDE.md` carries the
active stage's instantiation and is re-instantiated from this set at each new
stage's kickoff. This wording is the forward authority for new stages.

1. Core alone validates and writes truth; every stage domain is proposal-only
   over pinned frames; rejected proposals mutate nothing.
2. Determinism end-to-end: keyed RNG only; no wall-clock, no iteration-order
   dependence, no probability rolls as behaviour — counted, deterministic
   conditions.
3. Every transition provenance-stamped and event-caused; every canonical
   fact's chain inspectable from committed records.
4. Bounded state: hard caps, ≥20% measured peak headroom, deterministic
   compaction. Never raise a prior stage's cap — capacity growth means a new
   registry or an explicitly ratified cap contract at a STOP.
5. Commit-order discipline: pin upstreams ⇒ commit before them; every
   deliberate one-tick lag documented.
6. Influence is read-only, record-grounded, boosts or suppresses only
   already-existing candidates, and never outranks an urgent survival
   decision.
7. Boundary fields: each stage's contract names the fields its records must
   not contain, inherited forward until a later stage's ratified contract
   relocates a concept into that stage's own registry. Relocation is a
   contract event, never a relaxation. Culture baseline: `inventory,
   authority, obedience, orders, law, command, punishment`.
8. No hidden collective mind: coordinators, carriers, and offices are
   records, not commanders; no auto-inclusion, no private group planner.
9. A capability affects decisions and consequences as canonical state —
   never generated descriptive text; LLM output is never canonical state.
10. Validators re-derive and require exact equality; forged-field rejection
    proven by test, per leg.
11. Focused tests are never sufficient; the integrated churn test always
    ships.
12. Organic reachability, two modes: (a) features extending behaviour the
    simulation already performs organically — probed before the contract is
    written, per the lifecycle; (b) features introducing decision logic that
    cannot exist before implementation — a post-build acceptance gate: a
    bounded probe-build against pre-registered gates (run length, gate
    counts, threshold-provenance rules fixed before the build, never revised
    after a failed run), at most one evidence-based calibration, rollback of
    the capability from mainline on failure, and no dependent work before
    the gate passes. Only the ratified text governs; in-conversation
    reinterpretations carry no authority.

## Deferral mechanics

The taxonomy and its required records live in `CAPABILITY_ROADMAP.md`
§Deferral taxonomy — the sole authority, never mirrored; new categories only
by explicit ratification. Protocol additions:

- A gate that honestly requires out-of-boundary capability yields a
  taxonomy-classified deferral with its full required record — never a shim,
  stub, or "temporary" mechanic.
- Every deferral (new or reclassified) gets a row in `MACRO-ROADMAP.md`
  §Deferral ledger naming its landing stage, in the same commit series as the
  leg doc that records it.
- The Stage-N close-out audit walks the stage's full roadmap item list; every
  item is Implemented (verifying test/run named) or Deferred (exactly one
  category, full record). No silent drops. The stage is recorded partially
  complete unless every item is honestly Implemented.

## Scenario & baseline policy

- **Standing scenario decision**: the user's ratified choice of organic-gate
  vehicle governs all subsequent legs, until a leg's probes show it fails for
  that leg's specific conditions — which reopens the decision at that leg's
  STOP, never unilaterally.
- Frozen baseline hashes change only with explicit re-baseline authorisation
  at a STOP. Each stage close-out records the then-current frozen-hash set; a
  re-baseline names every hash it supersedes.
- **Performance telemetry (from Stage 9 onward)**: every recorded harness run
  logs wall-time and tick-throughput alongside its hashes. Cheap rows now so
  the Stage 12 burn-in wall is measured early, not discovered.

## Git & durability

- Never: `reset --hard` / `checkout --` / `clean` / stash-drop / `rm` on
  untracked work / force-push / history rewrite / branch deletion.
- Substance and churn land separately; one leg, one purpose; house commit
  style; nothing committed past a failing gate, an open review finding, or an
  unresolved STOP; docs ship with the behaviour they describe.
- **Push at every leg close-out, minimum.** Local-only stage work is a named
  durability defect (7C/7D precedent).

## On missing data or ambiguity

STOP; report the gap. No invented data, constants, fields, or flags; no new
store, cap raise, or authority grant to route around a gap; no threshold
lowered without measured evidence and a recorded decision. Conflicts between
docs/code/tests: name it, show evidence, present options, recommend one,
wait. Silence is never approval.

## Change control

This file is semantically versioned with the changelog below. Stage prompts
pin a version; a leg finishes under the version it started with; bumps never
apply retroactively mid-leg. Amendments are `docs:` commits ratified at a
STOP.

## Changelog

- **v1.2 (2026-07-22)** — invariant 12 amended to two-mode form: probe-before-
  contract retained for extensions of existing organic behaviour; a post-build
  acceptance gate (bounded probe-build, pre-registered gates, single
  evidence-based calibration, rollback on failure, no dependent work before
  pass) added for genuinely new decision logic. Lifecycle step 1 gains the
  matching classification carve-out. Motivated by the Stage 8C aid-lifecycle
  finding that reachability of unbuilt decision logic cannot be probed
  read-only; ratified by the user at the Stage 8C Phase 1 STOP.
- **v1.1 (2026-07-19)** — gate-metrics upgrade (readiness-audit workstream 3,
  ratified 2026-07-19): **Stability** and **Robustness (multi-seed)** clauses
  added to the gate template. Additionally directed into the Stage 8B–8D
  contracts by the same ratification — adopted via each contract's own
  acceptance gate, not by re-basing the in-flight Stage 8 prompt.
- **v1.0 (2026-07-19)** — initial factoring from `STAGE-8-MASTER-PROMPT.md`,
  `STAGE-8B-TO-9-PROMPT.md`, `STAGE-8-CONTINUATION-PROMPT.md`, and
  `CLAUDE.md`; generic (stage-neutral) invariant set; deferral-ledger
  linkage; performance-telemetry and push-at-close-out policies added.
