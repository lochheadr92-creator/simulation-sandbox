# CULTURE PASS — ADVERSARIAL REVIEW (2026-07-30)

Reviewer: Claude (Cairn), read-only adversarial review leg. No code modified; this file is the only write.
Tree under review: worktree `C:/dev/simulation-sandbox/simulation-sandbox`, branch `frontend/window-3d`,
HEAD `0f6cbde2`, plus uncommitted changes (15 modified tracked files, ~952 insertions; untracked
culture / surplus / emotion / layer-C files). Nothing staged. Review findings are pinned to this
exact tree state; they may not transfer to a modified tree.

## Verdict (verification-gate classification)

- Culture-layer mechanics: **COMPONENT_VERIFIED** — Tier A greens and two-run self-equality are
  consistent with the code as read.
- Handoff tree-state claim and the "legacy byte-identical by construction" claim: **FAILED as stated.**
- Promotion: **BLOCKED.** Do not run the five pending verifications on this tree until S1 is
  dispositioned; the results would be uninterpretable.

## Findings (severity-ordered)

### S1 — BLOCKER: undisclosed emotion layer in the tree; legacy byte-identity broken by construction

Claimed: "the tree is exactly the surplus-pass state plus additive culture files/edits";
"every legacy scenario is byte-identical by construction."

Observed:
- `backend/domains/emotion_domain.py` + `emotion_contracts.py` — untracked, declared nowhere.
- `backend/domains/registry.py` registers `EmotionDomain` ungated: `select_due_ids` = every alive
  person with `living_agent`, in every scenario, priority 8 (before living_settlement).
- `backend/domains/living_agent_contracts.py`: `empty_living_agent_state` now mints an `emotions`
  block (`emotion-v1`); `compat_living_agent_state` backfills it onto legacy agents. Every
  living-agent mint or compat write in every scenario now carries new canonical state, regardless
  of the culture layer's `storage_location` gate.
- `backend/domains/living_settlement_domain.py`: `_apply_emotion_gradient` inserted into the
  candidate pipeline; uses float arithmetic (`intensity / 1000`) in a stack whose culture module
  advertises "integer arithmetic only."
- `SURPLUS_PASS.md` line 5 declares "No emotion, social, culture, market" — the tree contradicts
  its own scope document.

Consequence: legacy hashes cannot be byte-identical for any living-agent scenario. The two-run
hash test (`backend/tests/test_culture_pass.py:671`) is self-relative (run A vs run B in the same
tree) and structurally cannot detect this; the frozen-baseline pin (pending item 3) is the only
check that can, and it has not been run. All current local greens were measured on the
contaminated tree — internally consistent, but not attributable to the culture layer alone.

Also undeclared in the handoff: `backend/tests/test_layer_c_*.py`, a 41-line edit to
`backend/tools/_probe_layer_c_singleton_funnel.py`, `HANDOFF.md`, `files.zip`, `inspect_zip.py`,
`.venv/`, `scratch_prof.pstats`; and the work sits on `frontend/window-3d`, not a capability branch.

Fix: quarantine the emotion layer to its own branch/worktree (revert the registry, contracts and
settlement hunks here), or formally declare it in-scope with its own contract. Re-run all
verification after disposition.

### S2 — HIGH: norm-priced trade voided the carry-total invariant (capacity overflow reachable)

`validate_people_trade` (backend/core/commit_pipeline.py) docstring: "equal-quantity exchange...
both parties' carry totals are invariant and no capacity check is needed." The culture pass made
give != receive normal: a greedy-seeded agent's first offer is give 2 / ask 3
(`_seeded_receive_x100`, `select_trade_partner` in `people_culture.py`). The validator accepts any
positive ints — no upper bound on either quantity — so net carry changes per trade and capacity is
re-checked nowhere (not in Core, not in `select_trade_partner`). An agent at `inventory_capacity`
can overflow it through an accepted proposal (e.g. gather_excess fills to capacity, then a
give 2 / receive 3 barter nets +1).

Pattern note: "symmetric swap" and "norm-priced exchange" were collapsed into one contract without
re-deriving the consequence that justified skipping the capacity check.

Fix: bound quantities in `validate_people_trade` (give_qty <= TRADE_QUANTITY + 1,
receive_qty <= TRADE_MIN_SURPLUS - TRADE_MIN_RETAIN), or re-derive post-trade capacity for both
parties; mirror the bound at emission in `select_trade_partner`.

### S3 — HIGH: `validate_people_aid` does not fully re-derive the material flow it claims

The meat leg is derived against live state, but the wood leg is not:
`giver_update.get("inventory")` and the receiver's wood are checked only for internal
carried_resources-mirror consistency — never against live values. An aid proposal can carry
arbitrary wood mutations on either party and pass Core validation.

Context: extra-field openness is inherited (`apply_mutation` applies any field, no whitelist;
`validate_food_transfer` has the same shape). The new regression is aid-specific: it is strictly
weaker than the barter validator on the same mirror while its docstring claims Core re-derives
"giver decrement, receiver increment, receiver capacity, versioned carry mirrors."

Fix: require `giver_update["inventory"] == live giver inventory` and
`receiver_update["inventory"] == live receiver inventory` in `validate_people_aid`.
### S4 — MEDIUM (recurring class): memory cap enforced pre-insert; committed 17 reachable

`_evict_decayed` (people_culture.py) trims to `CULTURE_MEMORY_MAX_ENTRIES` BEFORE
`record_trade_outcome` inserts the new entry, so committed state can hold 17 entries. Its return
is `bool(dead)` only, so cap-eviction deletions mutate state without setting `changed` — the
"written only on change" signal under-reports. Deterministic re-derivation keeps replay safe, but
the documented committed cap-16 invariant is false, and no test asserts committed cap. This is the
Stage 8B cap-eviction-ordering bug class recurring.

Fix: run eviction after insertion; fold cap deletions into the changed signal; add a
committed-cap Tier A assertion.

### S5 — MEDIUM: receiver retain violated by the design's own offers

Core comment claims retain is implied by `TRADE_MIN_SURPLUS >= quantity + TRADE_MIN_RETAIN`; at
receive_qty 3 that is 4 >= 5 — false. A partner holding exactly 4 accepts a greedy first offer and
drops to 1 < TRADE_MIN_RETAIN. Giver retain is enforced via a required precondition; receiver
retain is enforced nowhere, contradicting TRADE_MIN_RETAIN's definition ("each party keeps at
least this much of what it gives").

Fix: add `(receiver, receive_field, gte, receive_qty + TRADE_MIN_RETAIN)` to domain emission and
the Core required-precondition set, or cap receive_qty per S2.

### S6 — LOW (latent): set-precedence bug in `refresh_aid_eligible`

`{interaction_subjects} | {memory_subjects} - {observer_id, None}` binds as `A | (B - C)`:
self-exclusion never applies to interaction-memory-derived subjects. Benign only while
interaction memory never records `subject_id == observer`. Fix: parenthesize the union.
### S7 — LOW: documentation drift

- Aid severity is `AID_SEVERITY + generosity // 2` (up to 330), falsifying the constants comment
  "below OFFER_TRADE's 320." Moot in-code (aid is only considered when no barter partner exists),
  but the comment misleads.
- "Zero new proposal-type strings" holds only against the uncommitted surplus pass: `offer_trade`
  does not exist at HEAD. The rehash-constraint baseline is an uncommitted tree, i.e. floating.

## Claims verified clean

- 12 aid rejection reason codes — counted exact in `validate_people_aid`.
- Rejection invisibility is structural, not policed: the social signal rides the proposal, so a
  rejected proposal leaves no signal and no memory trace (constitutional property 1 holds).
- Aid excluded from norm updates via the `receive_field is None` guard; `gate_status` requires
  both legs > 0, so gifts never confer trader status.
- Whole-map CAS with deep-copied committed pin; owner single-writer; culture_state written on
  change only; `stored_resources: None` correctly omitted for legacy persons.
- `accepted_event_id` stamped by Core at commit (`commit_pipeline.py:522`), feeding
  `detect_own_trade_outcome`.
- Culture activation gated on `storage_location` in `people_domain.py` — the culture layer's own
  gating is airtight. The legacy break (S1) comes from the emotion layer, not culture.
- `compat_action` wrapping at the plan-step transition confirmed in the diff (1 of the 3 claimed
  call sites falls inside the diff; the other 2 not independently checked).
- AID_/CULTURE_ constant importers (tracked files): commit_pipeline, constants, people_planning,
  people_utility — consistent with the isolation claim given planning/utility host the hooks.
## Recommended sequence

1. Disposition the emotion layer (quarantine or declare). No verification runs before this.
2. Run the frozen-baseline pin FIRST — it is the cheapest falsifier of the byte-identical claim
   and the arbiter of S1's consequence.
3. Fix S2–S5 before Tier B threshold calibration; thresholds calibrated on defective trade/aid
   mechanics would need recalibration after the fixes anyway.
4. Commit the surplus pass as its own leg before culture lands. Every claim baseline in the
   handoff is unfalsifiable while both passes float uncommitted on a frontend branch — the
   durable-truth rule is being violated by proxy.
5. Then: 500-tick census, collective_groups benchmark, chunked-vs-continuous determinism check,
   surplus Tier B re-run.

## Review scope (proportionality record)

Read in full: `people_culture.py` (452 lines), `validate_people_trade` and `validate_people_aid`,
`validate_food_transfer` (inherited-pattern calibration), all diff hunks in people_planning,
people_utility, people_domain, living_agent_actions, living_agent_contracts,
living_agent_reasoning, living_settlement_domain, registry, scenarios/__init__, world/generator,
constants. Targeted greps: `offer_trade` at HEAD (absent), mutation field whitelist (absent),
`accepted_event_id` stamping, AID_/CULTURE_ importers, "emotion" in pass docs, cap/retain/
capacity/hash assertions in culture tests. Not read in full: CULTURE_PASS.md body, full test
bodies, census tooling internals, emotion_domain.py beyond its header and gating.

This review file is itself additive and untracked; expect it in `git status`.
