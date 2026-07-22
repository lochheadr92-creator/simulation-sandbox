> **SUPERSEDED 2026-07-22.** This directive is historical. Its Phase 0 was
> executed as commit 3c6a8a1b. Its fast-lane methodology (defer adversarial
> review / contract doc / byte-headroom) is overridden by Invariant 12 v2,
> ratified as commit 002a18a4. Its food-sharing candidate was empirically
> refuted: people_domain is disabled in collective_groups, so food events
> and interaction-memory facts are 0. Do not execute. Retained for the
> 3c6a8a1b provenance trail only.

# TASK: Stage 8C Leg 1 — a second, run-grounded norm type with relationship-based social consequence (fast-lane capability block)

Status: PROPOSED prompt (2026-07-21). Fast-lane block: build the next in-bounds culture capability on a committed 8B floor; keep the load-bearing invariants; defer heavy ceremony (adversarial review, byte-headroom, full contract doc) to a later batch. Hand to Claude Code.

## Context
Deterministic, replayable simulation kernel (backend/, Python). Core owns truth; domains are proposal-only. Branch capability/stage-8-culture. Stage 8B Leg 1 (individual norm carriage/transmission) is implemented but UNCOMMITTED, with two deferred, non-floor blockers (invariant-4 headroom miss ~0.27pp; adversarial review not yet run). Before writing code, do the CLAUDE.md session-start (git log --oneline -10, git status) and read: CLAUDE.md, memory/STAGE-8-CONTINUATION-PROMPT.md, memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md, memory/CAPABILITY-STAGE-8A-EMERGENT-NORMS.md. Restate your position in one paragraph, then act.

## Phase 0 — establish the 8B floor FIRST (before any 8C code)
- Confirm determinism on the current tree: `python -m tools.living_agent_harness --scenario collective_groups --ticks 1000 --repeat 2 --seed living-agents-stage6` -> repeat_matches AND replay_matches true, 0 deaths. And `--scenario living_settlement --ticks 320 --repeat 2` -> hash == 84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2, byte-identical.
- If BOTH pass: commit the 8B Leg 1 work as ONE WIP checkpoint - message: `wip(stage-8b): Leg 1 norm transmission - determinism-green floor; DEFERRED: invariant-4 headroom 19.73% vs 20%, adversarial review`. This is a deliberate, authorized relaxation of "no commit past an open finding," for velocity; the deferrals are recorded in the commit body, not hidden.
- If EITHER fails (red repeat/replay, or a moved frozen hash): STOP. A red floor is the one bug that cannot be deferred - do not commit, do not build on it, report the divergence.

## Build (on the committed 8B floor)
- PROBE FIRST (evidence before code - invariant 12): write a read-only probe (backend/tools/_probe_*.py pattern) measuring whether a candidate second behaviour - food-sharing via the existing 5B food-interaction + reciprocity/trust (5B5) seams - recurs organically in the committed collective_groups 1000-tick run, often enough to ground a norm (mirror how 8A's shelter-adoption probe grounded NORM_FORMATION_COUNT). Paste the distribution.
- ONLY if the probe shows it recurs: add ONE second norm type (e.g. food_sharing_norm) as a NEW schema-versioned registry OR a schema-version-bumped extension - NEVER by editing 8A/8B constants, caps, or priorities in place. It forms from repeated organic instances, decays, and expires by the same Core-committed transition pattern as 8A.
- Add ONE enforcement consequence: a committed norm-violating act deterministically adjusts the trust/reciprocity relationship (existing 6D consequence seam) of members who OBSERVED it (observer set derived purely from committed events). Read-only influence + relationship effect only.

## Do NOT build yet
- A third+ norm type; taboo/value norm classes; cross-group diffusion/divergence (that is 8D); myths/rituals/symbolic content.
- Any punishment record, order, obedience, exclusion authority, or physical consequence - enforcement is relationship effects ONLY.

## Do NOT touch / do NOT wire in
- The Stage 9 boundary: production, surplus, storage economy, ownership, trade, currency. If 8C appears to need any of it, STOP and record a Deferred - Stage-9-blocked note; never a stub economy.
- Frozen living_settlement 320-tick hash (84d3ad52...c32d2) - must stay byte-identical.
- Stage 7A-8B schemas, caps, priorities (90/89/88/87), or constants - extend via NEW registries, schema-version bumps, and new hooks only.
- Core authority surfaces: commit-pipeline ordering, validation authority, hashing, RNG keying, fork/replay/resume - register the new validator/domain through the SAME registered-validator seam 7A-8B use; add no new ordering/hashing semantics.
- Frontend/projection truth-mutation paths; existing test assertions except where this block's behaviour requires it (list every one you change).

## Invariants to preserve
- Determinism end-to-end: repeat + replay + resume equality on collective_groups with 8C on; keyed RNG only; no wall-clock, no iteration-order dependence, no probability-as-culture.
- Proposal-only: the new domain proposes over a pinned frame; Core alone writes truth; rejected proposals mutate nothing.
- Bounded state: new registry has a hard cap with >=20% measured peak headroom and deterministic compaction; provenance-stamped, event-caused transitions; validator re-derives and requires exact canonical-byte equality, with a forged-field-rejection test.
- Forbidden fields in every culture record: inventory, authority, obedience, orders, law, command, punishment.
- Influence is read-only, member/carrier-grounded, boosts/suppresses only already-existing candidates, and NEVER outranks an urgent survival decision (reuse the 8A survival-dominance guard).
- Same-frame commit-order: if the new domain pins upstream registries, it commits before them or documents the one-tick lag.

## Fast-lane deferrals (explicitly OUT of scope this block - batch later, note in commit body)
- Adversarial (cross-model) review. Byte-headroom optimization beyond meeting the cap. A full per-leg contract doc. The 8B invariant-4 slimming (Amendment 2).

## Acceptance criteria
- Second norm type forms organically >=1 time in an unseeded collective_groups 1000-tick run, 0 deaths (probe output pasted).
- A committed norm-violation event deterministically changes a named member's trust/reciprocity value, traceable end-to-end from committed records (cause chain pasted).
- Determinism: repeat_matches + replay_matches true on collective_groups 1000x2 with 8C on; resume equality where persistence/ordering is touched.
- Frozen living_settlement 320 hash byte-identical (paste it). New collective_groups hash recorded.
- Full backend suite: state counts honestly - "N passed; M known <reason> skipped; no executed test failed."
- New registry peak bytes measured with >=20% headroom vs its payload target.

## Verification, run these and paste the actual output
- `cd backend && python -m pytest`  (N passed / M skipped; name the skips)
- `python -m tools.living_agent_harness --scenario collective_groups --ticks 1000 --repeat 2 --seed living-agents-stage6`  (repeat/replay matches, final_state_hash, accepted-by-type incl. deaths, new norm/enforcement counts)
- `python -m tools.living_agent_harness --scenario living_settlement --ticks 320 --repeat 2`  (frozen hash byte-check)
- `python -m tools._probe_<yourprobe> 1000`  (food-sharing recurrence distribution + the violation->relationship cause chain)
- Redirect long runs to a file; read back only the summary block.

## On missing data or ambiguity
STOP. Report the gap. If the food-sharing probe does NOT show the behaviour recurring, do not invent a norm type no run exhibits - report it and propose the next-best run-grounded candidate. Do not fabricate data, stand up a new store to route around a gap, grant authority, or lower a threshold without measured evidence and a recorded decision. Silence is never approval.

## Commit discipline
- Two commits max: (1) the Phase-0 8B WIP floor; (2) the 8C block as one logical change (status/doc update in the same series). No unrelated edits, no drive-by refactors, no line-ending churn.
- Do not commit on a red repeat/replay or a moved frozen hash.
- No destructive git (reset/checkout/clean/stash-drop, force-push, history rewrite, branch deletion), ever.

## Assumptions made (veto any that are wrong)
- Target is Stage 8C Leg 1 (in-bounds next culture leg), NOT a Stage-9 economy domain (that crosses a documented hard rail and needs explicit go-ahead).
- Fast-lane authorized: WIP-commit the 8B floor past its two non-floor blockers, provided determinism is green.
- Second-norm candidate is food-sharing (reciprocity/trust seam); the probe may redirect it.
- collective_groups stays the working culture scenario; the purpose-built culture scenario (gate-5 retirement) is a separate later item.
