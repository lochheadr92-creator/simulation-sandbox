# TASK: Deliver Capability Stage 8 (Culture) — core culture loop, Legs 8A → 8D, hard stop at the Stage 9 boundary

Mode: greenfield-addition legs inside a live deterministic kernel, executed **gate-and-stop** — one leg at a time, each ending in a full acceptance gate, an adversarial review, and a STOP for explicit user confirmation before the next leg begins. You never run ahead.

## Context

Repo: `simulation-sandbox` (backend Python kernel + domains + scenarios; branch then named `capability/stage-6-living-agents`, HEAD `f6850d0b` "Stage 6 Liveness Pass" at the time this doc was written; the branch was renamed to `capability/stage-8-culture` at the Stage 8 Leg 0 boundary, 2026-07-18, same history). The Core owns truth; domains are proposal-only observers. Stages 6, 7A, 7B, 7B.1, 7C (mechanism-verified, organic gate Stage-9-blocked), and 7D (verified via the Liveness Pass) are committed. Stage 8A (Emergent Norms) is spec'd and **partially implemented in the uncommitted working tree** — see "Current state". Your job is Stage 8: prove culture as emergent, decision-affecting canonical state, through the core culture loop, and stop dead at the Stage 9 (Economy) boundary.

## Authority and reading order (binding docs — read before writing any code)

1. `memory/SOURCE-OF-TRUTH-v2.md` — architecture authority (truth model, proposals, provenance, hashing, projections).
2. `memory/CAPABILITY_ROADMAP.md` — Stage 8 goal list, global completion rules, dependency chain, frontier.
3. `memory/CAPABILITY-STAGE-8A-EMERGENT-NORMS.md` — **the binding 8A contract** (constants, counting semantics, commit ordering, acceptance gate). If code and this contract diverge, the contract wins; if you believe the contract is wrong, STOP and report — do not silently deviate.
4. `memory/CAPABILITY-STAGE-7D-GROUP-GOALS-LEADERSHIP.md` + `memory/STAGE-6-LIVENESS-PASS.md` — the defect history your work must not repeat (ordering defect, forged-field acceptance, focused-tests-bypassing-the-pipeline, overstated verification).
5. `memory/ROADMAP-RECONCILIATION-2026-07-14.md` — the doc-drift failure mode; you will not recreate it.

## Current state (VERIFIED 2026-07-17) — you start in a DIRTY working tree

- Untracked: `backend/domains/group_norm_contracts.py` (771 lines), `backend/domains/group_norm_domain.py` (54), `backend/tests/test_stage8a_group_norm.py` (504), probe tools `backend/tools/_probe_norm_influence.py`, `_probe_repair_timing.py`, and the 8A spec doc itself.
- Modified (uncommitted): 44 backend files, +4,398/−4,316 lines. `living_settlement_domain.py` carries ~51 net new lines (the 8A influence hook); many other files show near-equal add/remove counts consistent with formatting or line-ending churn, **not yet attributed**.
- Nothing 8A-related is committed. The 8A spec status is "PROPOSED (2026-07-17)". This prompt constitutes the user's confirmation to implement it as written (Assumption 1).

This working tree is in-flight work. **Never** `git reset --hard`, `git checkout --`, `git clean`, stash-drop, or otherwise discard it. Reconciling it is Leg 0.

## Operating protocol — gate-and-stop

Every leg follows the same shape. No leg starts until the previous leg's STOP is answered with explicit user approval.

1. **Spec** — the leg's contract doc exists in `memory/` with status PROPOSED, every constant justified by measured evidence (probes on committed runs, like 8A's adoption probe), non-goals explicit. For 8A this doc already exists. For 8B–8D **you write it first**, then STOP for user confirmation of the contract before implementing.
2. **Implement** — contract-conformant, proposal-only, inside the existing seams.
3. **Verify** — the leg's full acceptance gate: focused tests, the mandatory integrated full-kernel test through same-frame upstream revision churn, regression suites green, determinism (repeat + replay + resume), organic proof measured on an unseeded run, frozen-hash safety.
4. **Adversarial review** — a second, independent agent (Codex or equivalent) reviews the branch diff against the contract before any status is promoted. Review findings are fixed and re-verified before proceeding.
5. **Document + commit** — update the leg's stage doc (status, verified results, recorded hashes) and the roadmap frontier pointer **in the same commit series** as the behaviour. Three docs saying three different "nexts" is a named historical defect (reconciliation C2); do not recreate it.
6. **STOP** — output a close-out report (format below) and wait for explicit "proceed to <next leg>".

Close-out report format (required at every STOP):
- STATUS — VERIFIED / LIKELY / UNKNOWN per claim; never promote LIKELY to VERIFIED
- CHANGES — what changed, commits
- RISKS — assumptions, unverified items, rollback path
- NEXT STEP — the recommended next leg and any open decision

## Leg 0 — Reconcile the in-flight working tree (do this FIRST, before any new code)

1. Attribute the diff: separate 8A substance (group_norm files, influence hook, scenario/pipeline wiring) from the unattributed ±4.3k-line churn across 44 files. Determine whether the churn is formatting/line-endings (byte-level inspection of a sample, e.g. `git diff backend/core/rng.py`) or behavioural. If any churned file cannot be confidently attributed, STOP and report before committing anything.
2. Audit the existing 8A implementation against the 8A contract clause by clause (priority 87, counting by `adopted_via_key`, constants 3/300/500/150/16/32, validator re-derivation + byte-equality, forbidden-fields check, decay formula). Produce a conformance list: implemented-conformant / implemented-divergent / missing.
3. Run the full backend suite and the 8A focused tests as they stand; report actual results.
4. STOP with the Leg 0 report. Do not commit in Leg 0. The plan for finishing 8A (Leg 1) is confirmed at this STOP, including how the churn will be committed (separately from 8A substance, or reverted file-by-file if pure noise — user decides).

## Leg 1 — Stage 8A: Emergent Norms (contract exists; finish, verify, close)

Deliver `memory/CAPABILITY-STAGE-8A-EMERGENT-NORMS.md` exactly as written. Summary of the binding contract (the doc controls where this summary is lossy):

- One norm type `shelter_upkeep_norm` (`group-norm-v1`), formed when a group's Stage 7D `maintain_shared_shelter` adoptions reach `NORM_FORMATION_COUNT = 3` distinct adoption instances, counted by change of `adopted_via_key` per group (O(1) `last_counted_key`).
- Proposal-only `group_norm` domain at `engine_priority = 87` (commits **before** group_goal 88 / group_state 89 / association 90); pins upstream revisions; documented one-tick lag. This ordering is the 7D `stale_membership` lesson — do not "fix" it.
- New bounded registry `group-norm-registry-v1` (`group-norm-000`), lazily created, cap 16 norms / 32 progress entries, one active norm per group, payload targets 24/32 KiB.
- Influence: `_apply_group_norm_influence` in `living_settlement_domain.py`, read-only, +`NORM_REPAIR_INCREMENT = 150` to an **already-existing** `REPAIR_SHELTER` candidate for the norm shelter, any current living member (no want required — that is the transmission seed), survival dominance absolute, inert when no registry exists.
- Decay: strength 1000, linear to expiry at `last_adoption_tick + 300`; weakening below 500; dissolve-expiry on group derecognition; expiry is a Core-committed transition.
- Validator: full re-derivation of (formations, decays, expiries) + exact structural equality; forged `norm_id`/`strength`/`formation_count`/`target_id`/`group_id`/`decay_deadline_tick` rejected; forbidden fields `{inventory, authority, obedience, orders, law, command, punishment}` absent.

Acceptance gate = the 7 items in the contract, verbatim, including: the integrated full-kernel test that drives a frame with association(90)+group_state(89)+group_goal(88) revision bumps plus the group_norm(87) proposal through the **real commit pipeline**; ≥1 organic norm with measured influence firing over an unseeded 1,000-tick `collective_groups` run, 0 deaths; `living_settlement` 320-tick hash unchanged (`84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`); new `collective_groups` hashes recorded; adversarial review before promoting status. The documented fallback `NORM_FORMATION_COUNT = 2` may be taken **only** on measured evidence of sparse organic firing, recorded in the doc, and reported at the STOP.

## Leg 2 — Stage 8B: Transmission (teaching, imitation, generational carry)

Direction, not contract — the contract is written in Leg 2 step 1 from measured probes of the committed 8A run, as `memory/CAPABILITY-STAGE-8B-<NAME>.md`, and confirmed at a STOP before implementation.

- Goal: norm carriage becomes **per-individual and observable**. 8A transmission is group-membership-implicit; 8B introduces individual adoption records and transmission *events* — a member teaches/a member imitates — using the existing Stage 6C canonical-action and 6D social-interaction seams, so knowledge transfer is a caused, inspectable event chain, not a membership lookup.
- Culture must outlive its originators: demonstrate a norm persisting through membership turnover via individual carriers (the probe must measure actual turnover in the 1,000-tick run to ground constants).
- Generational transfer: include **only if** probes show lifecycle mechanics (births/deaths in `lifecycle_domain`) actually occur in the scenario horizon; otherwise record it Deferred (demography-blocked, Stage 11) with the probe as evidence. Evidence decides, not ambition.
- Non-goals: multiple norm types, values/taboos, enforcement, cross-group anything, myths/rituals, economy.

## Leg 3 — Stage 8C: Norm plurality and social enforcement

Contract written from evidence, confirmed at a STOP, then implemented.

- Goal: more than one norm type may exist, and norm violation has social consequence. Candidate second norm types must be grounded in behaviours the committed runs already show recurring (probe first — e.g. food-sharing via the 5B3/5B5 food-interaction and reciprocity/trust seams); do not invent a norm type no run exhibits.
- Values/taboos enter only as bounded, decision-affecting norm classes (a taboo is a suppressing nudge with the same survival-dominance guard; a value is a persistent preference weight) — never free text, never a new authority path.
- Enforcement means: a member's norm-violating act may deterministically affect *relationships* (trust/reciprocity via existing 6D consequence seams) of members who observed it. It never means punishment records, orders, obedience, exclusion authority, or physical consequence — the forbidden-fields list is unchanged and absolute.
- Non-goals: cross-group dynamics, ownership/resource-sharing rules (Stage 9), institutions (Stage 10).

## Leg 4 — Stage 8D: Divergence, diffusion, conflict, and norm change

Contract written from evidence, confirmed at a STOP, then implemented.

- Divergence: different groups verifiably hold different norm sets/strengths from their own histories (8C plurality makes this structurally possible; the gate measures it happening organically).
- Diffusion: a norm type spreading between groups only through observable cross-group member contact (6D interactions), as caused events — never ambient copying.
- Cultural conflict: the roadmap's "same act interpreted differently by different cultures" — scoped to **non-economic** rule differences (e.g. differing shelter-upkeep obligations), because ownership/obligation/resource-sharing interpretations are Stage-9 material. Interpretation differences must change consequences (relationship effects per 8C), not text.
- Norm change after major events: a committed world event (e.g. weather disaster from the existing weather domain) may deterministically accelerate decay or reset formation counting — through the same registry transitions, Core-committed.
- Non-goals: warfare, diplomacy, migration mechanics, religion, institutions, anything requiring surplus.

## Stage 8 close-out audit (final leg; before any "Stage 8 complete" claim)

1. Walk the roadmap's full Stage 8 item list. Classify every item: **Implemented** (with the verifying test/run), **Deferred — Stage-9-blocked** (with the concrete dependency, 7C-style), or **Deferred — content stage** (myths, rituals, symbolic objects, naming conventions, generational myths — per the user's core-culture-loop scope decision). No item silently dropped.
2. Verify the roadmap's global completion rules 1–10 per delivered leg; Stage 8 is recorded **partially complete (core loop delivered)** unless every item is honestly Implemented — do not mark the stage complete because the core loop exists.
3. Update `CAPABILITY_ROADMAP.md` (Stage 8 section + frontier pointer to the Stage 9 decision) and every stage doc status in one commit series. One frontier, stated once.
4. Final close-out report; STOP. Do not begin any Stage 9 design work.

## Hard stop — the Stage 9 boundary (never cross, even when asked nicely by a gate)

Out of bounds in every leg: production, gathering-surplus, storage-economy, ownership records, trade/exchange, currency; any attempt to unblock 7C's organic-emergence gate (it waits on Stage 9 surplus by ratified decision); institutions, governance, law, voting, courts (Stage 10); ecology/demography expansion (Stage 11); player-facing surfaces (14/15); LLM-generated content as canonical state anywhere. If an honest Stage 8 gate turns out to require any of these, the correct output is a **Deferred — Stage-9-blocked** record with evidence, exactly as 7C did — never a shim, stub economy, or "temporary" mechanic.

## Do NOT touch / do NOT wire in

- The frozen `living_settlement` 320-tick hash (`84d3ad52…c32d2`). Any leg whose mechanics would change it (a Stage 6 dynamics change, Liveness-style) requires an explicit re-baseline authorisation from the user at a STOP — assume no.
- Stage 7A/7B/7C/7D registry schemas, caps, and priorities (90/89/88). Extend via new registries and new hooks only.
- Core authority surfaces: commit pipeline ordering semantics, validation authority, hashing, RNG keying, fork/replay/resume machinery — beyond registering new domains/validators through the existing seams.
- Frontend/projection code paths that could mutate truth (projections stay read-only); no frontend redesign.
- Existing test assertions, except where a confirmed leg contract explicitly changes behaviour — list every such test in the leg report.
- The uncommitted working tree, destructively (no reset/checkout/clean/stash-drop; nothing force-pushed; no history rewrite; no branch deletion).

## Invariants to preserve (all legs — sourced from SOURCE-OF-TRUTH-v2, the roadmap, and the 7D/8A lessons)

1. Core alone validates and writes truth; every culture domain is proposal-only over a pinned frame; rejected proposals mutate nothing.
2. Determinism end-to-end: repeat + replay + resume equality on every touched scenario; keyed RNG only; no wall-clock, no iteration-order dependence.
3. Every registry transition is provenance-stamped and event-caused; the cause chain of any norm (formation → influence → decay/expiry → consequence) is inspectable.
4. Bounded state: every new registry has a hard cap with ≥20% measured peak headroom; payload targets documented; compaction deterministic.
5. Commit-order discipline: any domain pinning upstream revisions commits **before** those upstreams (priority below theirs) or documents why not; every deliberate one-tick lag is written down.
6. Influence is read-only, member-grounded, boosts only already-existing candidates, and **never** outranks an urgent survival decision — the survival-dominance guard is absolute in every new hook.
7. Forbidden fields in every culture record, all legs: `inventory, authority, obedience, orders, law, command, punishment`.
8. No hidden group mind: no group-owned planner, private scoring, or auto-inclusion; coordinators/carriers are records, not commanders.
9. Culture affects decisions and consequences as canonical state — never generated descriptive text.
10. Validators re-derive and require exact equality; forged fields are rejected by construction, and there is a test proving it, per leg.
11. Focused tests are never the whole story: every leg has the integrated full-kernel test through same-frame upstream churn (the class of defect 7D's 14 focused tests missed).

## Acceptance criteria (global; each leg's contract adds its own gate)

- All focused suites and the full backend suite green at every STOP (Leg 0 baseline: 306 backend / 136 Stage 6+7 focused — report the numbers you actually observe).
- Per leg: integrated full-kernel churn test passes; determinism repeat + replay + resume verified on `collective_groups` with the leg enabled; organic proof measured (counts, ticks, influence firings) on an unseeded run with 0 deaths; frozen `living_settlement` hash byte-identical; new `collective_groups` hashes recorded in the leg doc.
- Registry capacity measured at peak with headroom stated.
- Adversarial review passed before any status promotion; review findings fixed and re-verified.
- Docs match implementation at every commit point (roadmap global rule 10); one frontier pointer.

## Verification — run these and paste the actual output (never claim without evidence)

- `python -m pytest` for the backend suite (full run + the leg's focused files), from the repo's established invocation.
- The scenario harness (`backend/tools/living_agent_harness.py`) with the **exact recorded invocations and seed** (`living-agents-stage6`) used in `STAGE-6-LIVENESS-PASS.md` / the 7D doc: `living_settlement --ticks 320 --repeat 2` and `collective_groups --ticks 1000 --repeat 2` equivalents, pasting `repeat_matches`, `replay_matches`, `final_state_hash`, accepted-by-type counts, and death counts. If you cannot locate the exact harness invocation, STOP and ask — do not invent flags.
- Probe scripts (pattern: `backend/tools/_probe_*.py`) for every constant you set in a new contract — paste the measured distributions that justify the constant.
- Byte-level evidence for hash claims (the hash string itself, from the run output, not from memory).

## On missing data or ambiguity

STOP. Report the gap. Do not invent data, constants, fields, or flags; do not stand up a new store, raise a cap, or grant authority to route around a gap; do not lower a threshold to make a gate pass without measured evidence and a recorded decision. If docs, code, or tests disagree, name the conflict, show the evidence, present options, recommend one, and wait. Silence is never approval.

## Commit discipline

- One leg, one purpose; commits reviewable, reversible, explainable, in the repo's established style (`feat(stage-8a): …`, `fix(8b): …`, `docs: …`).
- The unattributed churn is never bundled with substance — it lands as its own commit (or is reverted) per the Leg 0 decision.
- Never commit past a failing gate, an open review finding, or an unresolved STOP. No force-push, no history rewrite, no branch deletion, ever.
- Doc updates that record a leg's status ship in that leg's commit series, not later.

## Assumptions made (veto any that are wrong)

1. Handing this prompt to the agent **is** the user's confirmation of the 8A contract as written (constants 3 / 300 / 500 / 150, priority 87, fallback rule included). Veto if 8A should change first.
2. **Resolved 2026-07-18:** the branch was renamed in place to `capability/stage-8-culture` at the Stage 8 Leg 0 boundary (reconciliation C6 flagged branch-name drift; no history rewrite, same commits).
3. Core-culture-loop scope: myths, rituals, taboos-as-lore, symbolic objects, and naming conventions are expected **Deferred — content stage** at close-out (taboo/value *mechanics* in 8C are in scope). 
4. Generational transfer belongs to 8B only if probes show in-horizon births; otherwise Deferred to Stage 11 with evidence.
5. The dirty working tree is the user's in-flight 8A work: reconcile and finish it; never discard it.
6. The adversarial reviewer is Codex or an equivalent independent agent, per the established 7D/8A practice.
7. The 8B–8D carve above (transmission → plurality/enforcement → divergence/diffusion/conflict/event-change) is accepted as the leg structure; each leg's *contract* still gets its own confirmation STOP.
