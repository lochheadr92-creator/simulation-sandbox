# Stage 8B Leg 1 — §3 adversarial review, reviewer brief (paste-ready)

Purpose: everything the protocol requires is assembled here so the review can run in one sitting. Nothing in this brief substitutes for the protocol — `memory/ADVERSARIAL-REVIEW-PROTOCOL.md` is the authority; this is the packing list and the paste-ready prompt.

## 1. Review inputs (protocol §1 — all four required)

- **Confirmed contract + decision log:** `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md` (repo working tree)
- **Full branch diff:** `scratchpad/leg1_change_set.diff` — `git diff 3506bd2b <branch tip> -- backend/domains backend/core backend/tests backend/scenarios CLAUDE.md`
- **Persisted evidence files:** `memory/evidence/stage-8b-leg1/harness_living_settlement_320_v3.json`, `harness_collective_groups_1000_v3.json`, `probe_8b_registry_bytes_post_a2.json`, `pytest_full_suite_post_a2.log`
- **Draft close-out claims (bare list):** `scratchpad/leg1_claims_bare.md` (17 claims)

## 2. Evidence → claim map

| Evidence file | Substantiates claims |
|---|---|
| `harness_living_settlement_320_v3.json` | 12 (frozen-hash safety) |
| `harness_collective_groups_1000_v3.json` | 11 (determinism), 14 (organic integration) |
| `probe_8b_registry_bytes_post_a2.json` | 13 (bounded state / headroom) |
| `pytest_full_suite_post_a2.log` | 6 (idempotence), 7 (validation/forgery rejection), 8 (write-once), plus the 23 tests in `test_stage8b_leg1_norm_transmission.py` |
| Diff + code reading only (no separate evidence file) | 1–5, 9, 10, 15, 16, 17 — structural/behavioral claims; check against the named functions directly (`derive_group_carriage_changes`, `_apply_group_norm_influence`, `commit_pipeline.py`) |

## 3. Procedure (protocol §2 — verbatim structure, not paraphrased)

**Pass 1 — blind.** Reviewer receives only the four inputs in §1. No builder narrative, no self-assessment, no seeded findings. Attempt to falsify each of the 17 claims. Requirement (protocol §2): the pass must produce at least one independent finding, **or** state explicitly, per claim, that no independent flaw was found — silence is not acceptable, and an entirely-builder-seeded outcome is insufficient.

**Pass 2 — builder-seeded, after pass 1 completes.** Submit the three findings in §4 below, tagged builder-seeded. Reviewer confirms or disputes each stated disposition. The implementing side may also rebut any pass-1 finding; reviewer holds or withdraws.

**Independence (protocol §3).** Reviewer model must differ from the implementing model; at least one non-Anthropic model must participate (zen MCP/OpenRouter, or Codex CLI). Record which model(s) actually ran — that's part of the report, not optional.

**Findings ledger (protocol §4).** Every finding — pass 1's and the three seeded ones — gets exactly one disposition: FIX / ACCEPT / DISPUTE. DISPUTE escalates to the user at the close-out STOP. Nothing is dropped silently.

**Scope cap (protocol §5).** This leg's diff and this leg's judgment calls only. No re-auditing Stage 8A or earlier. A suspected prior-stage issue is filed as a DISPUTE for the user, not an expanded review.

## 4. Known findings — pre-tagged builder-seeded, for pass 2

- **F1 — claim-9 wording (eligibility vs acquisition).** Ruled 2026-07-21: FIX wording, ACCEPT behaviour. The code is already correct and unchanged by this finding — only a claim statement is corrected (see `post_review_edits.md` for the exact ready-to-paste replacement text). Not yet applied to any shipped close-out text.
- **F2 / F2c — registry byte headroom.** Ruled + fixed twice: Amendment 1 slimmed the record (`carrier_id`/`norm_id`/`person_id` removed as key-recoverable duplicates), Amendment 2 removed post-commit staging residue (`pending_event_tick`/`pending_transition`). Final gate-measured state (2026-07-23, cloud): 17,126 B vs 24,576 B target → **30.31% headroom**, clears invariant-4's ≥20% bar. Disposition: FIX, applied and gate-verified.
- **F3 — tracking eviction order.** Ruled + fixed: `backfilled_norm_ids` pruning changed from lexicographic truncation to "retain the intersection with norms still present upstream," closing a latent (unreached-at-7-norms) defect where an active norm could be evicted and wrongly re-backfilled. Regression test `test_backfilled_tracking_never_evicts_a_norm_still_in_the_registry` added. Disposition: FIX, applied.

## 5. Hard-rail mechanical pre-check — already run (cloud, 2026-07-23)

Per `CLAUDE.md` / `.claude/agents/hard-rail-reviewer.md`, this mechanical grep-only pass runs before every adversarial review. Result, scope `3506bd2b..a2-gate -- backend/domains backend/core backend/tests backend/scenarios CLAUDE.md`:

```
HARD-RAIL SCAN — 3506bd2b..a2-gate -- backend/domains backend/core backend/tests backend/scenarios CLAUDE.md
backend/tests/test_stage7b_group_state.py:598 — Rule 2 (Frozen hash: touches test_stage7b_group_state.py) — matched text: `"group_norm", "group_carriage",`
backend/tests/test_stage8a_group_norm.py:44 — Rule 2 (Frozen hash: touches test_stage8a_group_norm.py) — matched text: `from domains.group_carriage_contracts import (`
backend/scenarios/collective_groups.py:76 — Rule 3 (Schema/cap/priority locks) — LIKELY, looks like an additive stage-label bump, not a structural schema/cap edit — matched text: `-"capability_stage": "8A",` / `+"capability_stage": "8B",`
backend/domains/group_carriage_contracts.py:74 — Rule 6 (New stores/cap raises/authority grants: new persistent store) — matched text: `GROUP_CARRIAGE_REGISTRY_ID = "group-carriage-000"`
```

Orienting note only, not a clearance — disposition of these 4 hits belongs to the reviewer/user per the spec ("flagging is not blocking, the human decides"): the new registry is this leg's stated purpose; the stage-label bump is cosmetic scenario metadata; the two frozen-file touches are additive (an import and a list entry), consistent with the frozen `living_settlement` hash already coming back byte-identical in the gate re-run. None of the four look like undeclared scope reach on their face — but that judgment is the reviewer's to make, not this scan's.

## 6. Paste-ready prompt

```
Run a Stage-End Adversarial Review (per memory/ADVERSARIAL-REVIEW-PROTOCOL.md) on
Stage 8B Leg 1 of simulation-sandbox.

Pass 1 (blind — do this first, alone): you are given four inputs only —
(1) the confirmed contract & decision log at
    memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md,
(2) the full branch diff at scratchpad/leg1_change_set.diff,
(3) the persisted evidence files under memory/evidence/stage-8b-leg1/, and
(4) the bare close-out claims at scratchpad/leg1_claims_bare.md.
Attempt to falsify each of the 17 claims. You do not have any builder narrative
or self-assessment yet — do not ask for one. For each claim, give either a
specific finding (what's false and why, citing the diff/evidence) or state
"no independent flaw found." At least one claim must get an independent
finding, or you must say explicitly, per claim, that none was found — silence
on this is insufficient per protocol §2.

Pass 2 (builder-seeded — only after pass 1 is complete): I'm now submitting 3
known findings the builder already identified, tagged builder-seeded:

F1 — claim-9 wording (eligibility vs acquisition). Ruled: FIX wording, ACCEPT
behaviour. Code unchanged/correct; only a claim statement needs correcting.
F2/F2c — registry byte headroom. Ruled + fixed twice; final measured state
17,126 B vs 24,576 B target = 30.31% headroom (invariant-4 ≥20% cleared).
Disposition: FIX, applied and gate-verified.
F3 — tracking eviction order (lexicographic vs active-recency). Ruled + fixed
via prune-to-known-norm-ids; regression test added. Disposition: FIX, applied.

For each, confirm or dispute the stated disposition. Also, for each pass-1
finding, I may rebut — you then hold or withdraw.

Scope cap (§5): this leg's diff and this leg's judgment calls only — do not
re-audit Stage 8A or earlier; file any suspected prior-stage issue as a
DISPUTE for the user instead.

Report: which model(s) you are (record independence level per §3), then a
findings ledger — every finding (yours + the 3 seeded) with exactly one
disposition: FIX / ACCEPT / DISPUTE.
```

## 7. After the review

The ledger's DISPUTE items (if any) escalate to the user at the close-out STOP — they are not resolved unilaterally. Once dispositions are settled, the roadmap's remaining sequence is: commit series (code + evidence files; delete dead `backend/tools/_probe_8b_coupling_discriminator.py`; apply the F1 wording fix — see `post_review_edits.md`) → close-out STOP → Stage 8C opens.

## 8. Review completed (2026-07-24)

- **Report + full claim attack:** `scratchpad/leg1_adversarial_review_report.md`
- **Durable findings ledger:** `memory/evidence/stage-8b-leg1/adversarial_review_ledger.md`
- **Reviewer:** Grok (xAI); Codex companion blocked on usage limit. Independence level recorded in the report.
- **Builder F1–F3:** all confirmed.
- **Independent findings:** P1-01, P1-02, P1-03, P1-04(=F1), P1-05, P1-06, P1-07, P1-08 (+ hard-rail ACCEPT).
- **Mandatory DISPUTE:** none. **Optional DISPUTE:** elevate P1-03 if formation-exact supporter freeze is required.

## 9. Review FIX items applied (2026-07-24)

| Item | Where applied |
|---|---|
| F1 + P1-01/02/05/06 claim wording | `scratchpad/leg1_claims_closeout.md` |
| F1 ruling + Amendment-2 verified addendum + lag assumption (P1-03) | `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md` |
| P1-07 protocol restore | `memory/ADVERSARIAL-REVIEW-PROTOCOL.md` |
| P1-07 contract restore | `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md` |
| Ledger statuses → Applied/Closed | `memory/evidence/stage-8b-leg1/adversarial_review_ledger.md` |
| Bare claims | left as historical trap; banner points to close-out claims |

**Remaining for user STOP (not auto-done):** commit series for code + evidence + docs; delete dead coupling probe tool if present; open 8C only after explicit confirmation.
