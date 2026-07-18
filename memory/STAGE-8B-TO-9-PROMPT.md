> **SUPERSEDED** — this prompt is superseded by `memory/STAGE-8-CONTINUATION-PROMPT.md`, which governs the 8B→9 arc. Kept for historical reference only; do not follow it directly.

# TASK: Deliver the remainder of Capability Stage 8 (Culture) — Legs 8B → 8C → 8D → close-out — hard stop at the Stage 9 boundary

Mode: greenfield-addition legs inside the live deterministic kernel, executed **gate-and-stop** — one leg at a time; each leg ends in a full acceptance gate, an adversarial review, and a STOP for explicit user confirmation before the next begins. This prompt **assumes Stage 8A (Emergent Norms) is implemented, verified, and committed**; the preflight verifies that assumption before anything else. You never run ahead, and you never cross into Stage 9.

## Running this under Claude Code (operating rules for THIS harness)

- **This file lives in the repo** at `memory/STAGE-8B-TO-9-PROMPT.md`. It is the standing instruction set for the whole 8B→9 arc; the per-leg contract docs in `memory/` are the durable state between sessions. Kick off each leg with: `Read memory/STAGE-8B-TO-9-PROMPT.md and the current leg's contract doc, then continue from the recorded position.`
- **One leg per session (minimum: one phase per session for big legs).** Do not try to carry 8B→8D in a single context window. At the start of EVERY session, re-orient before acting: `git log --oneline -10`, `git status`, read this file, read the active leg's contract doc, and restate your position in one paragraph. The repo docs are your memory; your context window is not.
- **Track phases with the todo list.** Create todos per phase (probe / contract / implement / verify / review / close) at leg start; one in-progress at a time; never mark the verify todo complete on partial evidence.
- **Use plan mode for contract phases.** Phase "Contract" is design, not code — enter plan mode, produce the contract doc, present it, and end the turn. Implementation starts only in a later turn, after the user's confirmation.
- **STOP means end your turn.** A STOP is a message to the user containing the close-out report and an explicit question — then you stop generating. Never treat auto-accept-edits mode, a permissive settings file, or user silence as permission to cross a STOP. If you notice you are about to continue past one "because the next step is obvious", that is the defect — end the turn.
- **Long runs go to files, not context.** The 1,000-tick harness runs take minutes and print plenty. Run them via Bash with output redirected to a file (run in background where sensible), then read back only the summary block (repeat/replay matches, hashes, accepted-by-type, deaths). Paste those lines into the report — never dump full run logs into context.
- **Delegate to subagents to keep the main context lean:** probes (Phase 1) and the adversarial-review retrieval (the established Codex companion flow) are subagent work; the main session consumes their summarised results. The adversarial review itself must remain an independent agent, not you reviewing your own diff.
- **Windows shell caveats:** this repo lives on Windows; quote paths, prefer `python -m pytest` from `backend/`, and avoid commands that assume a POSIX-only environment unless the session shell is git-bash. Temp/scratch output belongs under the repo's ignored paths or the OS temp dir, never committed.
- **If context is running low mid-phase**, write the current position into the leg's contract doc (a "Session handoff" note: done / in-flight / next command), commit nothing extra, and tell the user to start a fresh session — the next session resumes from the doc, not from a compacted summary.

## Context

Repo: `simulation-sandbox`, branch `capability/stage-8-culture` (renamed from `capability/stage-6-living-agents` at the Stage 8 Leg 0 boundary, 2026-07-18). Delivered so far: Stages 6–7D committed and verified; Stage 8A shipped ONE group-scoped `shelter_upkeep_norm` — formed from repeated 7D goal adoptions, decision-affecting via a survival-guarded read-only nudge, transmitted **group-membership-implicitly** (a member is covered because the association registry currently lists them; no transfer is ever a caused event).

Your job: the rest of the core culture loop — transmission becomes individual and observable (8B), norms become plural with social consequence (8C), cultures diverge, diffuse, and conflict between groups (8D) — then an honest close-out audit of the roadmap's Stage 8 list, stopping dead at Stage 9 (Economy).

## Authority and reading order (binding — read before writing any code)

1. `memory/SOURCE-OF-TRUTH-v2.md` — architecture authority.
2. `memory/CAPABILITY_ROADMAP.md` — Stage 8 goal list, global completion rules 1–10, frontier.
3. `memory/CAPABILITY-STAGE-8A-EMERGENT-NORMS.md` — the delivered 8A contract, verified results, recorded hashes, constants. 8B+ builds on it and must not silently change it.
4. `memory/STAGE-8-MASTER-PROMPT.md` — the original Stage 8 protocol this prompt continues (its invariants apply verbatim).
5. `memory/CAPABILITY-STAGE-7D-GROUP-GOALS-LEADERSHIP.md` + `memory/STAGE-6-LIVENESS-PASS.md` — the defect history you must not repeat: same-frame ordering (`stale_membership`), forged-field acceptance, focused-tests-bypassing-the-real-pipeline, overstated verification.
6. `memory/ROADMAP-RECONCILIATION-2026-07-14.md` — the doc-drift failure mode; one frontier pointer, always.

## Preflight — verify the "8A is done" assumption (gap-stop if false)

1. `git log` shows the 8A leg committed, substance separated from any formatting/churn commits; working tree clean or fully attributable.
2. The 8A doc status is promoted past PROPOSED with verified results and **recorded `collective_groups` hashes** — capture them as this prompt's baseline.
3. Full backend suite green (note the count). Frozen `living_settlement` 320-tick hash matches what the docs record as current (`84d3ad52…c32d2` unless a later authorised re-baseline superseded it).
4. The 8A adversarial-review findings are closed — fixed or explicitly waived in the doc, none open.

Any check fails → STOP and report. Finishing 8A is the 8A leg's prompt, not this one.

## Operating protocol — every leg, same shape

1. **Probe** — read-only measurement of the committed runs (pattern: `backend/tools/_probe_*.py`, seed `living-agents-stage6`, 1,000-tick `collective_groups`). No constant enters a contract without a pasted distribution behind it.
2. **Contract** — write the leg's doc in `memory/` (mirror the 8A structure: goal, organic-reachability evidence, agency model, mechanism, commit-order analysis, validation, contracts table, justified constants table, registry schema, non-goals, acceptance gate, risks). Status PROPOSED. **STOP for user confirmation before implementing.**
3. **Implement** — contract-conformant, proposal-only, through existing seams.
4. **Verify** — the leg's full gate (template below plus the contract's own items).
5. **Adversarial review** — independent agent (Codex or equivalent) against the branch diff. Findings fixed ⇒ **re-run the full gate** (fixes invalidate prior run evidence) ⇒ then commit.
6. **Document + commit + STOP** — leg doc status, roadmap frontier pointer, and behaviour ship in the same commit series. Close-out report: STATUS (VERIFIED / LIKELY / UNKNOWN per claim — never promote), CHANGES, RISKS, NEXT STEP. Then end the turn and wait for an explicit "proceed" — the next leg starts in a fresh session per the Claude Code rules above.

Gate template (every leg): focused tests incl. forged-field rejection by re-derivation + byte-equality, duplicate idempotence, capacity bound, replay + resume reconstruction; the **mandatory integrated full-kernel test through same-frame upstream revision churn** in the real commit pipeline; an end-to-end causal-chain proof from committed records; organic proof measured on an unseeded 1,000-tick run with 0 deaths; full regression green; determinism repeat + replay + resume; frozen `living_settlement` hash byte-identical; new `collective_groups` hashes recorded in the leg doc; registry peak capacity measured with ≥20% headroom.

## Leg 1 — Stage 8B: Norm Transmission (individual carriage, one taught/imitated pathway)

Goal: **who carries the norm becomes canonical state; how they came to carry it becomes a caused, committed event chain** (learned from whom, via which interaction, at which tick). Culture must be shown to outlive its originators — a norm persisting through membership turnover via individual carriers, not a membership lookup.

Probes (paste all): membership turnover of norm-holding groups after formation (joins/leaves, ticks — if ~0, STOP with evidence and options rather than seeding behaviour); which 6C/6D interaction event types organically fire between carriers and non-carriers (the transmission trigger must ride one that demonstrably does); lifecycle births/deaths in horizon (zero births ⇒ generational transfer recorded **Deferred — demography-blocked, Stage 11**, with the probe as evidence); the 8A norm timeline (formation ticks, decay events, membership at formation) that transmission constants must fit inside.

Contract decisions to resolve, with recommendation + evidence:

1. **The eligibility fork (central).** After 8B, exactly ONE source of truth grants the norm nudge — membership or carriage, never both. Default recommendation to argue: **carriage-only**, with formation deterministically backfilling carriage for members present at formation tick, and post-formation coverage acquired only through transmission events. This changes 8A's late-joiner semantics (implicit coverage → must learn); say so explicitly, record the expected `collective_groups` hash change, justify it as the honest model. If evidence favours the other resolution, argue that — but one owner, stated in the doc.
2. **One transmission mechanism, not two.** Teaching (carrier-initiated) or imitation (observer-initiated) — probe-decided; the other is a named non-goal for a later leg. Same smallest-honest-step discipline as 8A's one norm type.
3. **Deterministic trigger, no probabilities.** Transmission commits on a counted condition (e.g. Nth qualifying carrier↔non-carrier interaction, N from the probe distribution). Never "chance to learn".
4. **Where carriage lives**: schema-versioned extension of `group-norm-registry-v1` or a new bounded registry — justified by size math. Every carriage record carries provenance: `learned_from`, `via_event_id`, `learned_tick` (or `backfilled_at_formation`).
5. **Commit-order analysis**: which upstream registries the evaluation pins (association / group_state / group_goal / group_norm / interaction seams) and the engine_priority that commits before all of them (the 87-before-88/89/90 discipline, extended); every one-tick lag documented.
6. **Decay interaction**: carriage may outlive the group norm (that IS culture outliving its originators), but its influence guard, decay, and expiry are explicit, bounded, Core-committed.

Leg-specific gate items: transmission fires at exactly N (not before); eligibility-source exclusivity tested both ways; backfill correctness; causal-chain proof norm → carrier → interaction → transmission event → new carrier → influence firing on the new carrier; ≥1 organic transmission in the unseeded run with a post-formation joiner (or surviving carrier, per the decided fork) verifiably influenced. The influence hook keeps 8A's exact survival-dominance guard; `living_settlement` stays inert.

## Leg 2 — Stage 8C: Norm plurality and social enforcement

Goal: more than one norm type exists, and violating a norm has social consequence — through relationships, never authority.

- Second norm type(s) must be grounded in behaviour the committed runs already show recurring — probe first (candidates: food-sharing via the food-interaction and reciprocity/trust seams). Do not invent a norm type no run exhibits.
- Values/taboos enter only as bounded, decision-affecting norm classes (a taboo suppresses an existing candidate under the same survival-dominance guard; a value is a persistent preference weight) — never free text, never a new authority path.
- **Enforcement means relationships, not punishment**: a member's norm-violating act may deterministically affect trust/reciprocity (existing 6D consequence seams) of members who observed it. It never means punishment records, orders, obedience, exclusion authority, or physical consequence — the forbidden-fields list is absolute.
- Contract must define violation detection purely from committed events (what counts as a violating act, who counts as an observer), norm-class schema versioning, and per-class caps.
- Non-goals: cross-group dynamics, ownership/resource-sharing rules (Stage 9), institutions (Stage 10), myths/rituals.

## Leg 3 — Stage 8D: Divergence, diffusion, conflict, and norm change after events

Goal: culture varies between groups, moves between groups only through contact, and responds to history.

- **Divergence**: different groups verifiably hold different norm sets/strengths from their own histories (8C plurality makes it structurally possible; the gate measures it organically).
- **Diffusion**: a norm type spreading between groups only through observable cross-group member contact (the 8B transmission mechanism crossing a group boundary), as caused events — never ambient copying.
- **Cultural conflict**: the roadmap's "same act interpreted differently by different cultures", scoped to **non-economic** rule differences (e.g. differing shelter-upkeep obligations) — ownership/obligation/resource-sharing interpretations are Stage-9 material. Interpretation differences change consequences (8C relationship effects), not text.
- **Norm change after major events**: a committed world event (e.g. weather disaster from the existing weather domain) may deterministically accelerate decay or reset formation counting — same registry transitions, Core-committed.
- Non-goals: warfare, diplomacy, migration mechanics, religion, institutions, anything requiring surplus.

## Close-out — the Stage 8 audit (before any "Stage 8 complete" claim)

1. Walk the roadmap's full Stage 8 item list. Classify every item with evidence: **Implemented** (verifying test/run named), **Deferred — Stage-9-blocked** (concrete dependency, 7C-style), or **Deferred — content stage** (myths, rituals, symbolic objects, naming conventions, generational myths — per the user's core-culture-loop scope decision). No item silently dropped.
2. Verify the roadmap's global completion rules 1–10 per delivered leg. Stage 8 is recorded **partially complete (core loop delivered)** unless every item is honestly Implemented — never mark the stage complete because the core loop exists.
3. Update `CAPABILITY_ROADMAP.md` (Stage 8 section + frontier pointer to the Stage 9 decision) and every stage doc status in one commit series. One frontier, stated once.
4. Final close-out report; STOP. No Stage 9 design work.

## Hard stop — the Stage 9 boundary (never cross, even when a gate asks nicely)

Out of bounds in every leg: production, gathering-surplus, storage economy, ownership records, trade/exchange, currency; any attempt to unblock 7C's organic-emergence gate (it waits on Stage 9 surplus by ratified decision); institutions, governance, law, voting (Stage 10); ecology/demography expansion (Stage 11); player-facing surfaces (14/15); LLM-generated content as canonical state anywhere. If an honest gate turns out to require any of these, the correct output is a **Deferred — Stage-9-blocked** record with evidence — never a shim, stub economy, or "temporary" mechanic.

## Do NOT touch

- The frozen `living_settlement` 320-tick hash. Any mechanic that would change it requires explicit re-baseline authorisation from the user at a STOP — assume no.
- Stage 7A–7D and 8A registry schemas, caps, priorities, and constants — extend via new registries, schema-version bumps, and new hooks only; any 8A semantic change (e.g. the eligibility fork) happens only through a confirmed contract that records it.
- Core authority surfaces (commit pipeline ordering semantics, validation authority, hashing, RNG keying, fork/replay/resume) beyond registering new domains/validators through existing seams.
- Projection/frontend truth-mutation paths; existing test assertions except where a confirmed contract changes behaviour (list every such test in the leg report).
- The working tree, destructively: no reset/checkout/clean/stash-drop, no force-push, no history rewrite, no branch deletion, ever.

## Invariants (all legs — from SOURCE-OF-TRUTH-v2, the roadmap, and the 7D/8A lessons)

1. Core alone validates and writes truth; culture domains are proposal-only over pinned frames; rejected proposals mutate nothing.
2. Determinism end-to-end: repeat + replay + resume; keyed RNG only; no wall-clock, no iteration-order dependence, no probabilities-as-culture.
3. Every transition is provenance-stamped and event-caused; any cultural fact's chain (formation → carriage → influence → consequence → decay) is inspectable from committed records.
4. Bounded state: hard caps, ≥20% measured peak headroom, deterministic compaction; never raise a prior stage's cap.
5. Commit-order discipline: pin upstreams ⇒ commit before them; every deliberate one-tick lag written down.
6. Influence is read-only, member/carrier-grounded, boosts or suppresses only already-existing candidates, and **never** outranks an urgent survival decision.
7. Forbidden fields in every culture record: `inventory, authority, obedience, orders, law, command, punishment`.
8. No hidden group mind; carriers, observers, and coordinators are records, not commanders.
9. Culture affects decisions and consequences as canonical state — never generated descriptive text.
10. Validators re-derive and require exact equality; a test proves forged fields are rejected, per leg.
11. Focused tests are never sufficient: every leg carries the integrated full-kernel churn test — the class of defect 7D's focused tests missed.

## Verification — run these and paste actual output (never claim without evidence)

- `python -m pytest` — full backend suite plus the leg's focused files, using the repo's established invocation.
- The scenario harness (`backend/tools/living_agent_harness.py`) with the exact recorded invocations and seed (`living-agents-stage6`): the `living_settlement --ticks 320 --repeat 2` and `collective_groups --ticks 1000 --repeat 2` equivalents — output redirected to a file, with only the summary block read back: `repeat_matches`, `replay_matches`, `final_state_hash`, accepted-by-type counts, death counts. If you cannot locate the exact invocation, STOP and ask; do not invent flags.
- A probe script per constant, with the measured distribution pasted into the contract.
- Hash strings from run output, never from memory.

## On missing data or ambiguity

STOP. Report the gap. No invented data, constants, fields, or flags; no new store, cap raise, or authority grant to route around a gap; no threshold lowered to make a gate pass without measured evidence and a recorded decision. If docs, code, or tests disagree: name the conflict, show evidence, present options, recommend one, wait. Silence is never approval.

## Commit discipline

One leg, one purpose; house style (`feat(stage-8b): …`, `fix(8c): …`, `docs: …`); reviewable, reversible, explainable. Nothing committed past a failing gate, an open review finding, or an unresolved STOP. Doc updates ship with the behaviour they describe.

## Assumptions made (veto any that are wrong)

1. 8A closed clean — the preflight verifies rather than trusts, and stops if it didn't.
2. Same branch as 8A unless the 8A close-out renamed it; a truthfully-named `capability/stage-8-culture` branch may be cut at your direction.
3. Gate-and-stop remains in force for every leg boundary and every contract confirmation (your ratified execution model).
4. Core-culture-loop scope: myths, rituals, symbolic objects, naming conventions expected **Deferred — content stage** at close-out; taboo/value *mechanics* in 8C are in scope.
5. One transmission mechanism in 8B; carriage-only eligibility with formation backfill is the recommended fork resolution — the contract may overturn either with evidence at its STOP.
6. Generational transfer ships only if probes show in-horizon births; otherwise Deferred — demography-blocked (Stage 11).
7. The adversarial reviewer is Codex or an equivalent independent agent, per established practice.
8. The 8B → 8C → 8D carve is accepted as the leg structure; each leg's contract still gets its own confirmation STOP.
