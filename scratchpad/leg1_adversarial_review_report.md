# Stage 8B Leg 1 — adversarial review report & findings ledger

**Date:** 2026-07-24  
**Scope:** Stage 8B Leg 1 review packet (`scratchpad/reviewer_brief.md` packing list)  
**Protocol authority cited by packet:** `memory/ADVERSARIAL-REVIEW-PROTOCOL.md` (restored 2026-07-24 as review FIX P1-07; pass structure originally followed from the brief’s §2–§5 restatement)  
**Independence (protocol §3):** Reviewer = **Grok (xAI, non-Anthropic)**. Codex companion adversarial-review was attempted first and **failed on OpenAI usage limit** (retry window Jul 29 2026). This review is therefore **cross-model automated**, run in the same workspace that holds the builder packet, **not** a human-driven third-party audit and **not** Codex. Honest independence level: better than pure self-review; weaker than an independent agent process with no packet-builder co-presence.

**Inputs used**

| Required (brief §1) | Status in tree |
|---|---|
| `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md` | Present (restored 2026-07-24 as review FIX P1-07) |
| `scratchpad/leg1_change_set.diff` | Present (10 files; contracts/domain/tests + wiring) |
| `memory/evidence/stage-8b-leg1/*` v3 | Present (harness ×2, probe bytes, pytest log) |
| `scratchpad/leg1_claims_bare.md` | Present (17 claims) |
| Builder-seeded F1–F3 (pass 2) | Present in `reviewer_brief.md` §4 / `post_review_edits.md` |

---

## Pass 1 — blind claim attack (independent findings only)

For each of the 17 bare claims: either an independent finding, or an explicit “no independent flaw found.”

### Claim 1 — single mutation authority
**No independent flaw found** against the diff. `build_group_carriage_proposal` mutates only `group-carriage-000`; validator enforces scope; domain is proposal-only.

### Claim 2 — registry schema
**FINDING P1-01 (schema claim incomplete).**  
Claim lists `revision`, `carriers`, `processed_transmission_keys`, `created_tick`, `last_updated_tick` only. The implemented registry also has first-class **`backfilled_norm_ids`** (bounded, pruned, load-bearing for one-time backfill / F3). That omission is a false schema statement, not a cosmetic omission.  
**Disposition: FIX** (claim / close-out text; code OK).

### Claim 3 — formation backfill
**FINDING P1-02 (`learned_tick` is not the formation tick).**  
Bare claim: `learned_tick` = the **formation** tick.  
Code (`_carrier_record` / `advance_group_carriage_registry`): `learned_tick = int(tick)` of the **carriage advance/commit tick**.  
Evidence: transmission `via_event_id=evt-698-…`, `learned_tick=699`; backfills with formation events at 777 → `learned_tick=778`. Tests assert `learned_tick == 20` when advanced at tick 20.  
Behaviour matches the T / T+1 lag model; the **claim is false**.  
**Disposition: FIX** (wording: learned_tick = carriage-commit tick / first observation tick).

**FINDING P1-03 (supporter set is current-goal, not formation-frozen).**  
Backfill reads `_group_active_goal(...).supporter_ids` at the **first successful backfill tick**, not a formation-time snapshot. Code comments rely on “adoption cadence ≫ one-tick lag.” If the active goal is missing and backfill retries later, or supporters change before first success, carriage can be granted to a non-formation set — then permanently sealed by `backfilled_norm_ids`. Tests cover “no re-sync after already backfilled,” not “wrong set at first write.”  
Bare claim’s “supporters of the **triggering** goal” overstates fidelity.  
**Disposition: ACCEPT** behaviour for this leg **only if** close-out explicitly records the lag assumption; otherwise **FIX** (pin formation-time supporters, or reword claim to “supporters of the active goal visible at first successful backfill”). Escalates to user if they want formation-exact semantics.

### Claim 4 — transmission trigger
**No independent flaw found** on the stated mechanism. `TRANSMISSION_COUNT=1`, `TRANSMISSION_QUALIFYING_EVENT_TYPES=("social_request_help",)`, non-carrier → carrier, membership-gated learners. Teaching path correctly absent.

### Claim 5 — visibility and lag
**No independent flaw found** relative to prior-frame domain semantics and engine_priority=86 comments. Organic evidence matches T+1 commit for the transmission event.

### Claim 6 — idempotence
**No independent flaw found** at organic scale. Residual note (not a separate finding): `processed_transmission_keys` is FIFO-truncated (`processed[-96:]`) while carriers are not pruned; re-derive can re-emit a transmission that advance then no-ops because the carrier already exists. Harmless while carriers remain.

### Claim 7 — validation / forgery rejection
**No independent flaw found** on the main path: marker gate, scope gate, canonical-byte re-derive of `changes` + advanced registry, forbidden fields, F2c key-id restatement reject, pending-* reject.  
Note: bare claim still lists forged `carrier_id` as a first-class field attack; after F2c that field is forbidden if present. Wording should track the slimmed schema (see F2 / claim 2).

### Claim 8 — write-once / no pending residual
**No independent flaw found.** Tests + stamp path match Amendment 2.

### Claim 9 — eligibility (bare wording)
**FINDING P1-04 (eligibility vs acquisition conflation) — matches builder F1.**  
Bare claim: “Carriage is the sole gate on this leg’s **influence and acquisition** path.”  
Code: influence (`_apply_group_norm_influence`) is carriage-only; **acquisition/transmission** additionally requires co-membership (`member_ids - carriers`).  
**Disposition: FIX** wording, **ACCEPT** behaviour (builder F1 ruling stands).

### Claim 10 — influence guard unchanged + zero organic firings
**FINDING P1-05 (zero-firing half of claim is unsubstantiated).**  
Guard / magnitude / “never creates candidate” look structural in the living_settlement hunk (membership → carriage swap only).  
But “The influence hook fired zero times in the standard 1,000-tick organic run” has **no measurement** in the four evidence files (no influence counter, no probe field). Harness JSON does not report it.  
**Disposition: FIX** — drop or instrument; do not ship as verified without evidence.

### Claim 11 — determinism
**No independent flaw found.** `harness_collective_groups_1000_v3.json`: `repeat_matches=true`, `replay_matches_final_entities=true`, `final_state_hash=b5abbfffa9e0b5b5b52da912c757b75231afb8b752658a1a76e9d91d7472368c`.

### Claim 12 — frozen-hash safety
**No independent flaw found.** `harness_living_settlement_320_v3.json`: `final_state_hash=84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2` (byte-identical to baseline cited in the claim).

### Claim 13 — bounded state
**No independent flaw found.** Probe: 50 carriers, 1 processed key, `total_serialized_bytes=17126` vs `payload_target_bytes=24576` → 30.31% headroom.

### Claim 14 — organic integration
**No independent flaw found** on the countable facts: 49 backfill + 1 transmission; person-004 never in backfill set; transmission from person-000 with `via_event_id=evt-698-13861-115d344e`, `learned_tick=699`; `accepted_by_type.group_carry_norm=4`; 7 active norms; 8A `group_norm_summary_hash` unchanged.  
Soft note: probe does not label the transmitted norm as `shelter_upkeep_norm` by type string (id only); type is implied by scenario/domain constants, not re-proven in the probe file.

### Claim 15 — coupling classification
**FINDING P1-06 (coupling claim not backed by packet evidence).**  
Brief maps claims 1–5, 9, 10, 15, 16, 17 to “diff + code reading only,” and cites a discriminating A/B/C probe in the claim text, but **no coupling-probe artifact** is in `memory/evidence/stage-8b-leg1/`. Only `__pycache__` remnants of `_probe_8b_coupling_*` appear elsewhere. Cross-priority behavioural non-isolation is plausible and architecture-wide, but the packet does not let a reviewer verify the A/B/C result.  
**Disposition: FIX** — attach the probe JSON to evidence, or reword claim 15 to “not proven in this packet; architecture-wide assumption.”

### Claim 16 — Core touch wiring-only
**No independent flaw found.** `commit_pipeline.py` hunk: import + validate dispatch + stamp; no ordering/hash/CAS/tx changes.

### Claim 17 — deferrals / thresholds
**No independent flaw found** in the packet’s own terms (Tier B deferred; `TRANSMISSION_COUNT=1` as measured floor). Cannot re-audit deferred organic windows without longer runs — out of evidence.

### Packet integrity (not a numbered bare claim)
**FINDING P1-07 (required contract + protocol docs missing).**  
Brief §1 requires the confirmed contract at `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md` and cites `memory/ADVERSARIAL-REVIEW-PROTOCOL.md`. Both are **absent** from this working tree. Review proceeded on diff + claims + evidence + builder brief only. Decision-log / acceptance-gate text could not be checked for consistency with code.  
**Disposition: FIX** before close-out STOP (restore contract + protocol into the packet tree, or explicitly re-scope the review inputs).

**FINDING P1-08 (full suite not green in persisted log).**  
`pytest_full_suite_post_a2.log`: **1 failed**, 369 passed, 4 skipped — failure is `test_concurrent_stage7b_steps_do_not_duplicate_shared_state_or_head` (registry missing after step). Builder notes treat this as intermittent / CORE-INTEGRITY-001, unrelated to Amendment 2. Evidence file itself still records a failure.  
**Disposition: ACCEPT** for Leg 1 scope if close-out keeps the failure classified out-of-leg with the roadmap tracking note; do not claim “full suite green” without the intermittent caveat.

---

## Pass 2 — builder-seeded findings

| ID | Builder statement | Reviewer ruling |
|---|---|---|
| **F1** | Claim-9 wording (eligibility vs acquisition). FIX wording, ACCEPT behaviour. | **Confirm.** Independent pass reproduced as **P1-04**. Ready-to-paste text in `post_review_edits.md` Edit 1 is correct. |
| **F2 / F2c** | Registry byte headroom; slim keys + drop pending; 17,126 B / 30.31% headroom. FIX applied & gate-verified. | **Confirm.** Probe + Amendment-2 validator gates match. Residual claim-schema wording still lists pre-slim fields (P1-01 / claim 7 wording). |
| **F3** | Tracking eviction: prune to known norm ids; regression test. FIX applied. | **Confirm.** `advance_group_carriage_registry` + `test_backfilled_tracking_never_evicts_a_norm_still_in_the_registry` match the stated defect and fix. |

No builder-seeded disposition is disputed.

---

## Hard-rail mechanical hits (brief §5)

| Hit | Reviewer disposition |
|---|---|
| `test_stage7b_group_state.py` frozen-file touch | **ACCEPT** — additive list entry for new domain label; consistent with frozen living_settlement hash still matching. |
| `test_stage8a_group_norm.py` import | **ACCEPT** — additive import for interaction tests / fixtures. |
| `collective_groups.py` capability_stage 8A→8B | **ACCEPT** — scenario metadata stage-label bump. |
| New store `group-carriage-000` | **ACCEPT** — this leg’s stated purpose; not undeclared scope. |

---

## Findings ledger (protocol §4 — complete)

Every finding has exactly one disposition: **FIX** / **ACCEPT** / **DISPUTE**.

| ID | Source | Summary | Disposition | Close-out action |
|---|---|---|---|---|
| F1 | Builder + P1-04 | Claim 9 conflates eligibility and acquisition | **FIX** wording / **ACCEPT** code | Apply `post_review_edits.md` Edit 1 to any close-out claims restatement |
| F2/F2c | Builder | Registry headroom after slim + no pending | **FIX** (already applied) | Keep Amendment-2 verified block; optional contract addendum Edit 2 |
| F3 | Builder | `backfilled_norm_ids` eviction order | **FIX** (already applied) | Keep regression test |
| P1-01 | Pass 1 | Claim 2 omits `backfilled_norm_ids` | **FIX** | Correct schema claim in close-out |
| P1-02 | Pass 1 | Claim 3 `learned_tick` ≠ formation tick | **FIX** | Word as carriage-commit / advance tick; do not say formation tick |
| P1-03 | Pass 1 | Backfill supporters = current active goal, not formation snapshot | **ACCEPT*** | Document lag assumption in close-out; *user may upgrade to FIX if formation-exact is required → then DISPUTE at STOP |
| P1-05 | Pass 1 | Claim 10 zero influence firings unmeasured | **FIX** | Evidence or drop the sentence |
| P1-06 | Pass 1 | Claim 15 coupling probe not in evidence packet | **FIX** | Persist A/B/C probe output or weaken claim |
| P1-07 | Pass 1 | Contract + protocol files missing from tree | **FIX** | Restore docs before promoting VERIFIED |
| P1-08 | Pass 1 | Pytest log shows 1 failed + 369 passed | **ACCEPT** | Keep intermittent / CORE-INTEGRITY-001 caveat; never claim clean suite without it |
| HR-1..4 | Hard-rail | Four mechanical hits | **ACCEPT** | No further action |

**DISPUTE items for user STOP:** none mandatory.  
**Optional DISPUTE:** if the user requires formation-time-exact supporter freeze, elevate **P1-03** from ACCEPT to FIX and block close-out until designed.

---

## Claim-level outcome summary

| Claim | Outcome |
|---|---|
| 1 | Hold |
| 2 | **Refuted (incomplete)** → P1-01 |
| 3 | **Partially refuted** → P1-02, P1-03 |
| 4–8 | Hold |
| 9 | **Refuted (wording)** → F1 / P1-04 |
| 10 | **Partially unsubstantiated** → P1-05 |
| 11–14 | Hold (evidence-backed) |
| 15 | **Unsubstantiated in packet** → P1-06 |
| 16–17 | Hold |

---

## Design / approach challenges (adversarial, not just defects)

1. **Eligibility flip without dual-path transition.** Moving influence from membership → carriage with “no registry ⇒ no nudge” is honest for `living_settlement`, but any scenario that enables `group_norm` without `group_carriage` silently loses 8A cultural influence. Approach is coherent only if 8B is mandatory wherever 8A is enabled. Confirm in contract (missing here).

2. **Culture outlives originators vs write-once forever.** Carriers never forget and never prune. Cap 128 is “norms×members” headroom for the current scenario, not a long-horizon culture store. Fine for Leg 1 non-goals (no expiry), but the design will need an explicit forgetting / compaction story before multi-horizon 8C/8D, or the registry becomes a permanent membership fossil bed.

3. **Organic proof is thin by design.** One transmission, zero measured influence firings, Tier B deferred. The leg proves *machinery in the pipeline*, not *felt culture*. That is a valid scope cut only if close-out language never upgrades organic integration into “norm transmission works as a cultural system.”

4. **Validator trusts `requested_time`.** Same architecture-wide surface noted in 8A pre-existing findings. Not introduced here; still means transmission liveness (`_norm_is_live`) is attacker-steerable on malicious proposals. Out of leg scope; do not re-open 7A–7D unless user authorises.

---

## Verdict for close-out STOP

- **Code gate figures cited in claims 11–14 and F2 headroom: consistent with v3 evidence.**  
- **Doc/claim FIX items applied 2026-07-24** (close-out claims, contract restore + Amendment-2 addendum, protocol restore, ledger updated). See report § Fixes applied.  
- **Remaining:** user close-out STOP + commit series (code is still the Leg 1 change set, not necessarily committed on this tree). Do not open Stage 8C until STOP.

## Fixes applied (2026-07-24)

| Finding | Resolution artifact |
|---|---|
| F1 / P1-04 | `scratchpad/leg1_claims_closeout.md` §9; contract F1 ruling |
| F2/F2c, F3 | Already in code; Amendment-2 verified block in contract |
| P1-01, P1-02 | Close-out claims 2–3; contract schema + mechanism |
| P1-03 | ACCEPT documented as lag assumption in contract |
| P1-05, P1-06 | Close-out claims 10 + 15 reworded |
| P1-07 | `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md` + `memory/ADVERSARIAL-REVIEW-PROTOCOL.md` |
| P1-08, HR | ACCEPT recorded in contract + ledger |

---

## Artifact index

| Path | Role |
|---|---|
| `scratchpad/reviewer_brief.md` | Packet packing list |
| `scratchpad/leg1_claims_bare.md` | Blind claims (intentionally includes F1 wording trap) |
| `scratchpad/leg1_change_set.diff` | Branch diff under review |
| `scratchpad/post_review_edits.md` | Pre-drafted F1 + Amendment-2 paste text |
| `scratchpad/leg1_adversarial_review_report.md` | **This report / findings ledger** |
| `memory/evidence/stage-8b-leg1/` | Gate evidence (v3) |
| `memory/evidence/stage-8b-leg1/adversarial_review_ledger.md` | Durable copy of the ledger table |
