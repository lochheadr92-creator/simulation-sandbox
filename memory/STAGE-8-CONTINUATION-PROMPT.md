# TASK: Deliver the remainder of Capability Stage 8 (Culture) — Leg 0 (post-8A amendments) → 8B → 8C → 8D → close-out — hard stop at the Stage 9 boundary

Mode: greenfield-addition legs inside the live deterministic kernel, executed **gate-and-stop** — one leg at a time; each leg ends in a full acceptance gate, an adversarial review, and a STOP for explicit user confirmation before the next begins. This prompt supersedes `memory/STAGE-8B-TO-9-PROMPT.md` where they differ; the master protocol in `memory/STAGE-8-MASTER-PROMPT.md` (invariants, hard stops, verification discipline) applies verbatim except where this prompt updates it with post-8A facts. You never run ahead, and you never cross into Stage 9.

## Running this under Claude Code (operating rules for THIS harness)

- **This file lives in the repo** at `memory/STAGE-8-CONTINUATION-PROMPT.md`. It is the standing instruction set for the 8B→9 arc; per-leg contract docs in `memory/` are the durable state between sessions. Kick off each session with: `Read memory/STAGE-8-CONTINUATION-PROMPT.md and the current leg's contract doc, then continue from the recorded position.`
- **One leg per session** (minimum: one phase per session for big legs). At the start of EVERY session, re-orient before acting: `git log --oneline -10`, `git status`, read this file, read the active leg's doc, restate your position in one paragraph. The repo docs are your memory; your context window is not.
- **Track phases with the todo list** (probe / contract / implement / verify / review / close). One in-progress at a time; never mark the verify todo complete on partial evidence.
- **Use plan mode for contract phases.** A contract phase is design, not code — enter plan mode, produce the contract doc, present it, end the turn. Implementation starts only after the user's confirmation in a later turn.
- **STOP means end your turn.** A STOP is a message containing the close-out report and an explicit question — then you stop generating. Auto-accept-edits mode, permissive settings, and user silence are never permission to cross a STOP. If you notice you are about to continue "because the next step is obvious", that is the defect — end the turn.
- **Long runs go to files, not context.** Run harness invocations via Bash with output redirected to a file (background where sensible), then read back only the summary block (repeat/replay matches, hashes, accepted-by-type, deaths). Never dump full run logs into context.
- **Delegate to subagents:** probes and the adversarial-review retrieval (the established Codex companion flow) are subagent work; the main session consumes summarised results. The adversarial review itself must remain an independent agent — never you reviewing your own diff.
- **Windows shell caveats:** quote paths, prefer `python -m pytest` from `backend/`, avoid POSIX-only assumptions unless the session shell is git-bash. Scratch output goes under ignored paths or the OS temp dir, never committed.
- **If context runs low mid-phase**, write a "Session handoff" note into the active leg's doc (done / in-flight / next command), commit nothing extra, and tell the user to start a fresh session.

## Context — what is true NOW (baseline as of the 8A close-out, 2026-07-18)

Repo: `simulation-sandbox`, branch `capability/stage-6-living-agents` (renamed to `capability/stage-8-culture` in Leg 0 item 4 below). Stages 6–7D committed and verified. Stage 8A committed as:

- `9cff3f62` `feat(stage-8a)` — 11 files: `group_norm_contracts.py`, `group_norm_domain.py`, registry/scenario/pipeline/harness wiring, the influence hook (post-scoring), `test_stage8a_group_norm.py`, two evidence probes. One existing test modified and flagged (`test_stage7b_group_state.py` enabled-domains assertion).
- `e7e87832` `docs(stage-8a)` — 8A contract promoted to VERIFIED with gate-5 Deferred; hashes recorded; 9 closed adversarial findings; pre-existing-findings section; roadmap frontier pointer → 8B.
- Both commits sit cleanly on `f6850d0b`; revertable in isolation.

**8A verified facts your work builds on (do not re-litigate; do re-verify in preflight):**

- One group-scoped `shelter_upkeep_norm` (`group-norm-v1`), formed at `NORM_FORMATION_COUNT = 3` distinct 7D adoptions counted by `adopted_via_key` change, domain at `engine_priority = 87` (before 88/89/90), registry `group-norm-registry-v1` cap 16 norms / 32 progress, decay 1000-linear to `last_adoption_tick + 300`, weakening < 500, influence +150 on an already-existing `REPAIR_SHELTER` candidate, survival dominance absolute, transmission group-membership-implicit.
- Frozen `living_settlement` 320-tick hash byte-identical: `84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`.
- `collective_groups` 1000×2, seed `living-agents-stage6`: final_state_hash `659a27f3…920342`, group_norm_summary `3f2e5b9e…`, repeat + replay True, 0 deaths, **7 norms form organically**.
- Registry peak 5,643 B vs 24,576 target (77% headroom); progress 7/32, norms 7/16.
- Test suite: **338 executed passed; 4 known docker-path collection failures excluded from execution; no executed test failed.** (Reporting rule below.)

**8A gate-5 (organic influence firing): Deferred — scenario-dynamics-blocked.** Measured 0 firings over 1,000 ticks. REPAIR_SHELTER candidates exist only ticks 1–236; earliest norm formation is 377+ (re-degradation required first). The windows are disjoint **by scenario construction, not by threshold** (count=2 also measured 0). 7D's goal influence is identically inert (`goal_influence_firings = 0`) — a pre-existing scenario property. Consequence: **in the current organic run, culture is decision-inert.** Norms form, decay, and are stored — none ever changes a decision. This is a scenario property, not an 8A implementation defect, but it is the central structural risk to every remaining leg, because every remaining gate demands organic decision-affecting behaviour in this same scenario.

**Known deferred/unresolved (not yours to fix unless directed):** three architecture-wide malicious-proposal surfaces (trusted `requested_time`, marker-gating, structural-vs-byte equality on 7A–7D validators) documented for a separate authorised hardening pass — none reachable by the honest kernel; a reverted defensive overlay guard in `group_goal_contracts.py` (7A–7D byte-untouched guardrail upheld); tracked `node_modules` (removal is its own commit, only on user direction); `DOMAIN_MAPPING.md` uncommitted.

## Authority and reading order (binding — read before writing any code)

1. `memory/SOURCE-OF-TRUTH-v2.md` — architecture authority.
2. `memory/CAPABILITY_ROADMAP.md` — Stage 8 goal list, global completion rules 1–10, frontier, deferral taxonomy (extended in Leg 0).
3. `memory/CAPABILITY-STAGE-8A-EMERGENT-NORMS.md` — the delivered 8A contract, verified results, recorded hashes, constants, gate-5 deferral. 8B+ builds on it and must not silently change it.
4. `memory/STAGE-8-MASTER-PROMPT.md` — original Stage 8 protocol; its invariants apply verbatim.
5. `memory/CAPABILITY-STAGE-7D-GROUP-GOALS-LEADERSHIP.md` + `memory/STAGE-6-LIVENESS-PASS.md` — the defect history: same-frame ordering (`stale_membership`), forged-field acceptance, focused-tests-bypassing-the-pipeline, overstated verification.
6. `memory/ROADMAP-RECONCILIATION-2026-07-14.md` — doc-drift failure mode; one frontier pointer, always.

## Deferral taxonomy (authoritative; defined once, reused every leg)

Every deferred gate item is classified as exactly one of:

- **Deferred — Stage-9-blocked**: honestly requires surplus/economy mechanics. Record the concrete Stage 9 dependency (7C-style).
- **Deferred — content stage**: myths, rituals, symbolic objects, naming conventions, generational myths — per the user's core-culture-loop scope decision.
- **Deferred — scenario-dynamics-blocked** *(new; formalised in Leg 0)*: the mechanism is implemented and mechanism-verified, but the scenario's dynamics never produce the conditions the organic gate measures. Required record: (a) the blocking measurement (the probe/tick evidence proving the conditions cannot co-occur), (b) the concrete unblock condition — an alternative/extended scenario permitting co-occurrence, or an authorised dynamics change with its re-baseline consequence named, (c) the statement that no threshold was lowered.
- **Deferred — demography-blocked (Stage 11)**: requires lifecycle events (births/deaths) the horizon does not produce; probe evidence attached.

A deferral without its required record is an open gate, not a closed one. Never invent a fifth category ad hoc; if none fits, STOP and propose one to the user.

## Preflight — verify the baseline (gap-stop if false)

1. `git log` shows `9cff3f62` and `e7e87832` on top of `f6850d0b`; working tree clean or fully attributable.
2. 8A doc status VERIFIED with gate-5 recorded Deferred and `collective_groups` hashes present (`659a27f3…920342`).
3. Full backend suite: 338 executed passed (or current higher count), collection exclusions attributed. Frozen `living_settlement` hash matches `84d3ad52…c32d2` (paste from run output, never from memory; if it differs, STOP).
4. 8A adversarial-review findings closed — fixed or explicitly waived in the doc, none open.
5. Roadmap frontier pointer reads 8B and only 8B.

Any check fails → STOP and report. Fixing 8A is not this prompt's job.

## Reporting rules (all legs)

- Evidence labels on every claim: VERIFIED / LIKELY / UNKNOWN; never promote.
- **Suite status is never unqualified "green" while exclusions exist.** The required phrasing: "N executed passed; M known <reason> collection failures excluded from execution; no executed test failed." If the exclusions are ever fixed, say so once and drop the qualifier.
- Hash strings come from run output, pasted, never from memory.
- Close-out report at every STOP: STATUS (per-claim labels) / CHANGES (commits) / RISKS (assumptions, unverified items, rollback path) / NEXT STEP (recommendation + open decisions).

## Leg 0 — Post-8A amendments (docs + hygiene; no new mechanics; do FIRST)

Five items, confirmed by the user at the 8A close-out. Items 1–4 are amendments and answers; item 5 is housekeeping. Commit in house style (`docs:`, `test:`/`chore:`, `chore:`); nothing here touches simulation behaviour or any recorded hash.

1. **Reclassify gate-5 and formalise the taxonomy.** In `CAPABILITY_ROADMAP.md`, add the deferral taxonomy above (four categories, required records). In the 8A doc, reclassify gate-5 as **Deferred — scenario-dynamics-blocked** with its full required record: tick evidence (candidates ticks 1–236; earliest formation 377+; count=2 also 0), unblock condition (a) an alternative or extended scenario permitting REPAIR_SHELTER-candidate and norm-active windows to overlap, or (b) an authorised Stage 6 dynamics change (re-degradation cycles) — which breaks the frozen `living_settlement` hash and requires explicit re-baseline authorisation at a STOP — and the no-threshold-lowered statement.
2. **Attribute the 4 collection errors.** Name the files, state why collection fails, record in the 8A doc as known exclusions using the reporting phrasing above. If fixing collection is trivial (<30 min), fix it instead, in a standalone `test:`/`chore:` commit.
3. **Answer the 7D question — narrowly.** What evidence satisfied 7D's organic acceptance gate, and did it require any influence firing? If the 7D doc remains accurate given `goal_influence_firings = 0`, state so and close the question. If any claim overstates, correct the doc in a `docs:` commit — no code change. Report either way.
4. **Rename the branch** to `capability/stage-8-culture` at current HEAD. No history rewrite; the old name may remain a local pointer if tooling needs it. Update every doc that names the branch (reconciliation C6: no name drift).
5. **STOP** with the Leg 0 report. Do not begin 8B probes until the user confirms.

## Operating protocol — every remaining leg, same shape

1. **Probe** — read-only measurement of committed runs (`backend/tools/_probe_*.py`, seed `living-agents-stage6`, 1,000-tick `collective_groups` unless a scenario decision changes the vehicle). No constant enters a contract without a pasted distribution behind it.
2. **Contract** — write the leg's doc in `memory/` mirroring the 8A structure (goal, organic-reachability evidence, agency model, mechanism, commit-order analysis, validation, contracts table, justified constants table, registry schema, non-goals, acceptance gate, risks). Status PROPOSED. **STOP for user confirmation before implementing.**
3. **Implement** — contract-conformant, proposal-only, through existing seams.
4. **Verify** — the full gate (template below plus the contract's own items).
5. **Adversarial review** — independent agent (Codex or equivalent, separate process; record the independence level honestly — cross-model automated review is not a human audit and is never described as one) against the branch diff. Findings fixed ⇒ **re-run the full gate** (fixes invalidate prior run evidence) ⇒ then commit.
6. **Document + commit + STOP** — leg doc status, roadmap frontier pointer, and behaviour in the same commit series. Close-out report; end the turn; wait for explicit "proceed". Next leg starts in a fresh session.

**Gate template (every leg):** focused tests incl. forged-field rejection by re-derivation + byte-equality, duplicate idempotence, capacity bound, replay + resume reconstruction; the **mandatory integrated full-kernel test through same-frame upstream revision churn** in the real commit pipeline; an end-to-end causal-chain proof from committed records; organic proof measured on an unseeded run with 0 deaths (scenario per the standing scenario decision); full regression green per the reporting rule; determinism repeat + replay + resume; frozen `living_settlement` hash byte-identical; new scenario hashes recorded in the leg doc; registry peak capacity measured with ≥20% headroom.

## Leg 1 — Stage 8B: Norm Transmission (individual carriage, one taught/imitated pathway)

Goal: **who carries the norm becomes canonical state; how they came to carry it becomes a caused, committed event chain** (learned from whom, via which interaction, at which tick). Culture must be shown to outlive its originators — a norm persisting through membership turnover via individual carriers, not a membership lookup.

### Phase 1 — Probes (STOP after, with results, before any contract text)

Paste measured distributions for all of:

1. **THE OVERLAP PROBE (mandatory; required input to the contract; added by user directive at the 8A close-out).** Can an influence window (surviving REPAIR_SHELTER or any other boostable candidate) and an active-norm window ever overlap in `collective_groups` over the 1,000-tick horizon? If not: what is the minimum change (additional ticks, scenario config) that would produce overlap? Note the prior: 8A's run already implies "no within 1,000 ticks" — if re-degradation ever re-created repair candidates past tick 377, 8A would have recorded firings. Expect to confirm the negative and measure the distance to overlap.
   - If the answer is structurally **no**, this is a **contract-STOP decision for the user, not you**. Present options with measured evidence — (a) extend the horizon (state the tick count at which overlap is projected and its runtime cost), (b) a purpose-built culture scenario (cleaner evidence; avoids overloading `collective_groups` as the universal gate vehicle; state what it must contain), (c) an authorised Stage 6 dynamics change (name the frozen-hash re-baseline consequence) — recommend one, and wait. **Do not pick.** The user's choice becomes the **standing scenario decision** for all remaining legs' organic gates and is recorded in the roadmap.
2. Membership turnover of norm-holding groups after formation (joins/leaves, ticks). If ~0, STOP with evidence and options rather than seeding behaviour.
3. Which 6C/6D interaction event types organically fire between would-be carriers and non-carriers — the transmission trigger must ride one that demonstrably does.
4. Lifecycle births/deaths in horizon. Zero births ⇒ generational transfer recorded **Deferred — demography-blocked (Stage 11)** with the probe as evidence.
5. The committed 8A norm timeline (formation ticks, decay events, membership at formation) that transmission constants must fit inside.

### Phase 2 — Contract decisions to resolve (recommendation + evidence each; STOP for confirmation)

1. **The eligibility fork (central).** After 8B, exactly ONE source of truth grants the norm nudge — membership or carriage, never both. Default recommendation to argue: **carriage-only**, with formation deterministically backfilling carriage for members present at formation tick, and post-formation coverage acquired only through transmission events. This changes 8A's late-joiner semantics (implicit coverage → must learn); say so explicitly, record the expected scenario-hash change, justify it as the honest model. If evidence favours the other resolution, argue that — but one owner, stated in the doc.
2. **One transmission mechanism, not two.** Teaching (carrier-initiated) or imitation (observer-initiated) — probe-decided; the other is a named non-goal.
3. **Deterministic trigger, no probabilities.** Transmission commits on a counted condition (e.g. Nth qualifying carrier↔non-carrier interaction, N from the probe distribution). Never "chance to learn".
4. **Where carriage lives**: schema-versioned extension of `group-norm-registry-v1` or a new bounded registry — justified by size math against the measured 77% headroom. Every carriage record carries provenance: `learned_from`, `via_event_id`, `learned_tick` (or `backfilled_at_formation`).
5. **Commit-order analysis**: which upstream registries the evaluation pins (association / group_state / group_goal / group_norm / interaction seams) and the engine_priority that commits before all of them (the 87-before-88/89/90 discipline, extended); every one-tick lag documented.
6. **Decay interaction**: carriage may outlive the group norm (that IS culture outliving its originators), but its influence guard, decay, and expiry are explicit, bounded, Core-committed.

### 8B leg-specific gate items

Transmission fires at exactly N (not before); eligibility-source exclusivity tested both ways; backfill correctness; causal-chain proof norm → carrier → interaction → transmission event → new carrier → influence firing on the new carrier; ≥1 organic transmission in the unseeded run (per the standing scenario decision) with a post-formation joiner (or surviving carrier, per the decided fork) verifiably influenced. The influence hook keeps 8A's exact survival-dominance guard; `living_settlement` stays inert. If the organic-influence item cannot be met even under the chosen scenario, classify per the taxonomy with the full required record — never lower N.

## Leg 2 — Stage 8C: Norm plurality and social enforcement

Goal: more than one norm type exists, and violating a norm has social consequence — through relationships, never authority.

- **Probe first**: second norm type(s) must be grounded in behaviour the committed runs already show recurring (candidates: food-sharing via the food-interaction and reciprocity/trust seams). Do not invent a norm type no run exhibits. The overlap question applies per norm type: a candidate norm type whose influence window cannot co-occur with its active window in the standing scenario is flagged at the contract STOP, not discovered at verify.
- Values/taboos enter only as bounded, decision-affecting norm classes (a taboo suppresses an existing candidate under the same survival-dominance guard; a value is a persistent preference weight) — never free text, never a new authority path.
- **Enforcement means relationships, not punishment**: a member's norm-violating act may deterministically affect trust/reciprocity (existing 6D consequence seams) of members who observed it. Never punishment records, orders, obedience, exclusion authority, or physical consequence — the forbidden-fields list is absolute.
- Contract defines violation detection purely from committed events (what counts as a violating act, who counts as an observer), norm-class schema versioning, per-class caps.
- Non-goals: cross-group dynamics, ownership/resource-sharing rules (Stage 9), institutions (Stage 10), myths/rituals.

## Leg 3 — Stage 8D: Divergence, diffusion, conflict, and norm change after events

Goal: culture varies between groups, moves between groups only through contact, and responds to history.

- **Divergence**: different groups verifiably hold different norm sets/strengths from their own histories (8C plurality makes it structurally possible; the gate measures it organically).
- **Diffusion**: a norm type spreading between groups only through observable cross-group member contact (the 8B transmission mechanism crossing a group boundary), as caused events — never ambient copying. Probe cross-group contact frequency in the standing scenario before writing the contract; zero contact is a scenario decision, not an implementation problem.
- **Cultural conflict**: "same act interpreted differently by different cultures", scoped to **non-economic** rule differences (e.g. differing shelter-upkeep obligations) — ownership/obligation/resource-sharing interpretations are Stage-9 material. Interpretation differences change consequences (8C relationship effects), not text.
- **Norm change after major events**: a committed world event (e.g. weather disaster from the existing weather domain) may deterministically accelerate decay or reset formation counting — same registry transitions, Core-committed.
- Non-goals: warfare, diplomacy, migration mechanics, religion, institutions, anything requiring surplus.

## Close-out — the Stage 8 audit (before any "Stage 8 complete" claim)

1. Walk the roadmap's full Stage 8 item list. Classify every item with evidence: **Implemented** (verifying test/run named) or Deferred under exactly one taxonomy category with its full required record. No item silently dropped; no ad-hoc categories.
2. Verify the roadmap's global completion rules 1–10 per delivered leg. Stage 8 is recorded **partially complete (core loop delivered)** unless every item is honestly Implemented — never mark the stage complete because the core loop exists.
3. If gate-5-class deferrals (scenario-dynamics-blocked) remain open at close-out, the audit lists each with its unblock condition and states explicitly whether the standing scenario decision resolved it — the forcing-function record the user required.
4. Update `CAPABILITY_ROADMAP.md` (Stage 8 section + frontier pointer to the Stage 9 decision) and every stage doc status in one commit series. One frontier, stated once.
5. Final close-out report; STOP. No Stage 9 design work.

## Hard stop — the Stage 9 boundary (never cross, even when a gate asks nicely)

Out of bounds in every leg: production, gathering-surplus, storage economy, ownership records, trade/exchange, currency; any attempt to unblock 7C's organic-emergence gate (it waits on Stage 9 surplus by ratified decision); institutions, governance, law, voting (Stage 10); ecology/demography expansion (Stage 11); player-facing surfaces (14/15); LLM-generated content as canonical state anywhere. If an honest gate turns out to require any of these, the correct output is a **Deferred — Stage-9-blocked** record with evidence — never a shim, stub economy, or "temporary" mechanic.

## Do NOT touch

- The frozen `living_settlement` 320-tick hash (`84d3ad52…c32d2`). Any mechanic that would change it requires explicit re-baseline authorisation from the user at a STOP — assume no. (The overlap probe's option (c) is the one sanctioned path to *requesting* that authorisation; it is never self-granted.)
- Stage 7A–7D and 8A registry schemas, caps, priorities, and constants — extend via new registries, schema-version bumps, and new hooks only. Any 8A semantic change (the eligibility fork) happens only through a confirmed contract that records it and its expected hash consequence.
- The three documented hardening surfaces — they belong to a separate authorised pass; do not fix them opportunistically inside a culture leg.
- Core authority surfaces (commit pipeline ordering semantics, validation authority, hashing, RNG keying, fork/replay/resume) beyond registering new domains/validators through existing seams.
- Projection/frontend truth-mutation paths; existing test assertions except where a confirmed contract changes behaviour (list every such test in the leg report).
- The working tree, destructively: no reset/checkout/clean/stash-drop, no force-push, no history rewrite, no branch deletion, ever. (The Leg 0 rename is a rename at HEAD, not a deletion-and-recreate.)

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
12. *(new, from the 8A lesson)* **Organic reachability is probed before a contract is written, not discovered at verify.** Every organic gate item in a contract cites the probe evidence that its measured conditions can co-occur in the standing scenario — or carries its taxonomy classification up front.

## Verification — run these and paste actual output (never claim without evidence)

- `python -m pytest` — full backend suite plus the leg's focused files, from the repo's established invocation; report per the suite-status phrasing rule.
- The scenario harness (`backend/tools/living_agent_harness.py`) with the exact recorded invocations and seed (`living-agents-stage6`): the `living_settlement --ticks 320 --repeat 2` and `collective_groups --ticks 1000 --repeat 2` equivalents (plus the standing-scenario invocation once decided) — output redirected to a file, only the summary block read back: `repeat_matches`, `replay_matches`, `final_state_hash`, accepted-by-type counts, death counts. If you cannot locate the exact invocation, STOP and ask; do not invent flags.
- A probe script per constant, with the measured distribution pasted into the contract.
- Hash strings from run output, never from memory.

## On missing data or ambiguity

STOP. Report the gap. No invented data, constants, fields, or flags; no new store, cap raise, or authority grant to route around a gap; no threshold lowered to make a gate pass without measured evidence and a recorded decision. If docs, code, or tests disagree: name the conflict, show evidence, present options, recommend one, wait. Silence is never approval.

## Commit discipline

One leg, one purpose; house style (`feat(stage-8b): …`, `fix(8c): …`, `docs: …`, `chore: …`); reviewable, reversible, explainable. Nothing committed past a failing gate, an open review finding, or an unresolved STOP. Doc updates ship with the behaviour they describe. Leg 0's items are separate small commits, not a bundle.

## Assumptions made (veto any that are wrong)

1. The 8A close-out report is accepted as delivered; the preflight verifies rather than trusts, and stops if the recorded state doesn't match.
2. Leg 0's five items were confirmed by the user at the 8A close-out and need no further confirmation to execute — but Leg 0 still ends in a STOP before 8B probes begin.
3. Gate-and-stop remains in force for every leg boundary and every contract confirmation.
4. The standing scenario decision (overlap probe outcome) is the user's call at the 8B contract STOP; once made, it governs all remaining organic gates without re-deciding per leg — unless a later leg's probes show the chosen scenario fails for that leg's specific conditions, which reopens the decision at that leg's STOP.
5. Core-culture-loop scope: myths, rituals, symbolic objects, naming conventions expected **Deferred — content stage** at close-out; taboo/value *mechanics* in 8C are in scope.
6. One transmission mechanism in 8B; carriage-only eligibility with formation backfill is the recommended fork resolution — the contract may overturn either with evidence at its STOP.
7. Generational transfer ships only if probes show in-horizon births; otherwise **Deferred — demography-blocked (Stage 11)**.
8. The adversarial reviewer is Codex or an equivalent independent agent per established practice, with its independence level recorded honestly in every leg report (cross-model automated ≠ independent audit).
9. The 8B → 8C → 8D carve is accepted as the leg structure; each leg's contract still gets its own confirmation STOP.
10. The hardening pass and `node_modules` removal remain parked until the user schedules them; they are never folded into a culture leg.
