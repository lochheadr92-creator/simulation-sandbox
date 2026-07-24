# CORE-INTEGRITY-001 — Independent Adversarial Review Brief (Grok)

**Protocol:** `memory/ADVERSARIAL-REVIEW-PROTOCOL.md` (blind pass first, then seeded; every finding → FIX / ACCEPT / DISPUTE; no silent drops).
**Date:** 2026-07-25
**Packet:** `scratchpad/core-integrity-review/` (7 files + this brief)
**Runs in parallel with** the Layer C Upkeep close-out (separate worktree, separate files — zero overlap). Nothing in this review touches, blocks, or is blocked by that work.

---

## Independence record (fill in / confirm at review time)

| Role | Model / path |
|---|---|
| Finding author | Anthropic Claude (Stage 8C Phase 1 session, 2026-07-22; probes + doc) |
| Disposition | Ryan, post-8B-close-out STOP (2026-07-24): findings ACCEPTED, remediation DEFERRED |
| Reviewer | Grok (xAI) — non-Anthropic, did not author the finding or the probes |
| Caveat | Same human owns both sessions. Reviewer cannot execute code; probe verdicts rest on the committed JSONs. **The reviewer may demand a probe re-run (by Ryan, locally) as a finding rather than accepting the JSONs.** |

---

## What this review is

CORE-INTEGRITY-001 is a **dispositioned engine finding**: the commit pipeline permits silent same-frame lost updates on person entities, `touched_scope` is not enforced, and canon has a duplicate invariant numbering. Remediation is deferred to its own future core-integrity stage because any repair moves the frozen baselines. The finding has execution evidence but has **never had independent review**. This review does two things:

- **Pass 1 (blind):** attack the ten claims below using only the packet files. Try to refute each. Default skeptical.
- **Pass 2 (forward):** produce the attack plan for the unresolved GAPs and the requirements sheet a future remediation stage must satisfy.

Read-only. Nothing gets committed. No remediation is designed into the engine by this review. Output is a findings ledger + attack plan for Ryan, who rules on every disposition.

## Inputs (the packet, all in `scratchpad/core-integrity-review/`)

1. `CORE-INTEGRITY-001-lost-update.md` — the finding under review (read LAST section §11 carefully — the GAPs are pass-2 raw material).
2. `mutations.py` — the entire apply path (small; the shallow `dict.update` is the core mechanism claim).
3. `commit_pipeline.py` — ordering (`order_key`), revalidation, `check_scope_exists`, the `apply_mutation` call site.
4. `_probe_8c_pipeline_write.py` + `probe_8c_pipeline_write.json` — F1/F2 probe and its committed output.
5. `_probe_core_integrity_death_scope.py` + `probe_core_integrity_death_scope.json` — death-path probe and output.

## Bare claims for the blind pass (attack each; verdict + evidence per claim)

1. `apply_mutation` performs a shallow last-writer-wins `dict.update`; a validated earlier same-frame write to the same top-level field is silently discarded, no error raised; the only guard is an opt-in per-proposal `eq` precondition. (F1)
2. Probe sub-test 2b proves F1 by execution: two accepted proposals, 0 rejected, beneficiary's delivered commitment absent after the frame.
3. `touched_scope` is existence-checked but never enforced against `entity_updates` keys: a proposal can write an entity it did not declare, and the write persists. Proven by two independent probe sub-tests. (F2)
4. The real exploiter is `living_settlement_domain.py:734`: every settlement proposal overwrites the actor's whole `living_agent` from the frame snapshot, and non-social physical actions carry no `living_agent` eq guard — this mechanism explains the observed 17/17 aid-commitment loss as a lost update, ruling out discard and aid-specific causes.
5. The death path is F1-exposed: death + later same-frame `health` write yields alive=False with health=500 (corrupted death); the outcome flips with commit order; the pipeline structurally permits un-kill (alive=True after death).
6. Real deaths are corruptible but NOT maskable: no domain writes `alive: True` on an existing person, so F1 cannot suppress a death, and the historical zero-deaths observation is adequately explained by benign hunger recovery (health never reaches 0, no death proposal generated).
7. The exposed surface is the person entity; the field-collision map identifies `living_agent` (exercised), `health` (proven), and `energy`/`current_goal`/`action`/`position`/`knowledge`/`plan` (structural) as unguarded multi-writer fields; Category-2 singleton registries are single-owner and not exposed.
8. Frame ordering is deterministic (`order_key` = requested_time, phase rank, engine priority, content hash), therefore which write survives each collision is baked into every frozen baseline — any F1 repair necessarily moves the frozen `living_settlement` 320 hash and the `collective_groups` baseline, so remediation requires its own authorized re-baseline stage.
9. Culture invariant 11 is a test-shipping mandate, not a no-lost-update guarantee; the finding is a coverage gap (the shipped churn test never exercises a same-frame non-actor `living_agent`/`health` overwrite), not a literal invariant violation. No canon invariant anywhere forbids the silent overwrite. (F3 adjacent)
10. The standing mitigation policy for culture legs — new state in single-owner Category-2 registries; any person-entity write must carry field-level eq guards plus integrated churn-test coverage for the same-frame overwrite class — is sufficient containment while remediation is deferred.

**Claim 10 is the one carrying live risk.** Claims 1–9 are about what happened; claim 10 is the policy every future leg relies on. Attack it hardest: enumerate concrete leg-shapes where the policy fails (e.g. an eq guard that races the same field it guards; two legs each single-owner but writing the same person field; a registry write that references person state read from the snapshot).

## Pass 2 — forward deliverables (after the blind ledger)

**A. GAP attack plan.** For each §11 GAP (per-frame commit order of the 17 aid cases; which §6 collisions fire in production; registry multi-write possibility; remediation/re-baseline), specify: the cheapest decisive observation that closes it, what it must assert, expected cost, and what a bad result would change. Rank by risk-per-cost.

**B. Remediation requirements sheet** (requirements, not design): what a future core-integrity stage must guarantee. Evaluate at minimum: (i) deep-merge of nested sub-dicts, (ii) commit-time conflict rejection on same-field same-frame writes, (iii) mandatory field-level eq guards on every person-entity writer, (iv) enforcing `touched_scope` against `entity_updates` keys. For each: what it fixes, what it breaks, frozen-hash consequence, migration/re-baseline gate contents.

**C. Canon fix for F3:** the smallest change that makes every "invariant N" citation unambiguous.

**Secondary (optional, flag-only):** `test_concurrent_stage7a/7b_steps_do_not_duplicate_*` intermittency is a *separate* suspected CAS/head-revision concurrency concern, historically conflated with this finding. State whether it belongs inside CORE-INTEGRITY-001's scope or needs its own finding ID. Do not investigate beyond classification.

## Ground rules

- Findings ledger format: ID, source (independent / seeded), finding, proposed disposition (FIX / ACCEPT / DISPUTE), owner. Rulings are Ryan's, not yours.
- Label everything VERIFIED / LIKELY / GAP exactly as the finding doc does. Never upgrade a label.
- You cannot execute; if a claim is only checkable by running something, say so and specify the exact command as a demanded artifact.
- Scope: this finding's surfaces only. No re-audit of culture legs, no Upkeep-leg files, no remediation implementation.
- End with a STOP for Ryan listing every decision that is his.

---

## Paste-ready prompt (give Grok this + the 7 packet files)

> You are the independent adversarial reviewer for CORE-INTEGRITY-001, a dispositioned engine-integrity finding in a deterministic replayable simulation engine (Core owns truth; domains are proposal-only). You did not author it. Your review has two passes.
>
> Pass 1 (blind): the brief lists 10 bare claims. Attack each one using only the seven packet files. For each claim: verdict (no independent flaw found / FINDING with ID), the exact evidence line or code line that decides it, and anything the evidence does not actually support. Default skeptical; a claim you cannot check from the packet is itself a finding (demand the missing artifact — you may demand probe re-runs). Attack claim 10 hardest: it is the containment policy every future leg relies on — enumerate concrete scenarios where it fails.
>
> Pass 2 (forward): produce (A) a ranked attack plan closing the finding's §11 GAPs — cheapest decisive observation per GAP, what it asserts, what a bad result changes; (B) a remediation requirements sheet for the deferred core-integrity stage — for each candidate class (deep-merge, commit-time conflict rejection, mandatory eq guards, touched_scope enforcement): what it fixes, what it breaks, frozen-hash consequence, re-baseline gate contents; (C) the smallest canon change resolving the invariant-numbering collision.
>
> Output: a findings ledger (every finding → proposed FIX / ACCEPT / DISPUTE, owner marked), then the pass-2 deliverables, then a STOP listing every decision that belongs to Ryan. You change nothing; you commit nothing; label all claims VERIFIED / LIKELY / GAP honestly and never present LIKELY as VERIFIED.
