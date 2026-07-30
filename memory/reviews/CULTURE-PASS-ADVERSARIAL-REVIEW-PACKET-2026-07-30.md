# Culture Pass — Adversarial Review Packet

**Date** 2026-07-30 · **Subject** the uncommitted culture layer (norms, aid,
collective memory, gate-keeping) on top of the uncommitted Surplus Pass
**Author** the implementing agent (Kimi), disclosed — this is an implementer's
self-review packet built for *independent* verification, not an independent
review. Every claim is labeled VERIFIED / LIKELY / UNKNOWN and every
verification step is reproducible from the commands in §7. Treat anything
labeled LIKELY/UNKNOWN as unproven.
**Template** superpowers `requesting-code-review` / `code-reviewer.md`, adapted
to this repo's reporting rules. House precedent honoured: the last adversarial
review lived outside the repo and cost a full re-derivation round — this one
lives in `memory/reviews/`.

---

## 1. Review surface

HEAD `0f6cbde2` on branch `frontend/window-3d`. Everything reviewed is
**uncommitted working-tree content** (house rule: review first, commit never
without it). Two passes share the tree; this packet reviews the culture layer
only, but flags where it touches Surplus Pass lines.

```bash
git status --short
git diff backend/core/constants.py backend/core/commit_pipeline.py \
         backend/domains/people_culture.py backend/domains/people_utility.py \
         backend/domains/people_planning.py backend/domains/people_domain.py \
         backend/domains/living_agent_actions.py
```

Culture-owned files: `backend/domains/people_culture.py` (new),
`backend/tools/culture_census.py` (new), `backend/tools/_probe_culture_census.py`,
`backend/tools/_probe_culture_tick_time.py`, `backend/tests/test_culture_pass.py`,
`backend/tests/test_culture_pass_invariants.py`, `CULTURE_PASS.md`.
Culture edits inside shared files: constants banner
(`core/constants.py`, "Culture Pass" section), Core validator
`validate_people_aid` + dispatch (`core/commit_pipeline.py`), OFFER_TRADE
candidate rewrite (`people_utility.score_candidates`), OFFER_TRADE step terms
+ aid path + `context_from_action` copies (`people_planning.py`), culture
update/proposal-write/CAS-pin/diagnostics (`people_domain.py`), trade-signal
terms (`living_agent_actions.evidence_signal_for_action`).

## 2. Requirements → implementation

| Sprint requirement | Implementation | Status |
|---|---|---|
| Norms: (resource_type, expected_give, expected_receive) from trade outcomes | `culture_state.norms[pair]`, generosity-seeded x100 fixed point, integer EMA toward accepted terms (own + witnessed) | VERIFIED by Tier A fixtures |
| Agents with surplus bias toward norm-compliant offers | Offered quantities come from the norm tuple, clamped validator-safe; partner ranking prefers remembered counterparties | VERIFIED by Tier A fixtures (`test_norm_terms_ride_the_offer`) |
| Aid: surplus above SURPLUS_KEEP_FOOD, aid_eligible on kin/ally, bypasses trade validation, decrements surplus | `offer_trade` + `people-aid-v1` contract; `validate_people_aid` (12 reason codes); ally = support_score ≥ 20 OR remembered counterparty; giver food −2, keeps ≥ 4 | VERIFIED by Tier A fixtures |
| Aid must not collapse accumulation — census probe | `stored_surplus_agents_by_500 ≥ 4` (Tier B parity) in the culture census | UNKNOWN — census pending |
| Collective memory: who/what/rate/tick, queried before offers, decays with half-life | `culture_state.memory` (own via committed action's `accepted_event_id`; witness via term-carrying trade signals); `CULTURE_MEMORY_HALF_LIFE_TICKS = 100`, evict at weight 0, cap 16 | VERIFIED by Tier A fixtures; organic hit-rate UNKNOWN — census pending |
| Gate-keeping: gate_status on collective action proposals, keyed to trade history | `gate_status` from non-decayed **barter** entries; enforced on aid (the pass's only collective benefit) | VERIFIED by Tier A fixtures; organic enforcement UNKNOWN — census pending |
| No new proposal types (rehash constraint) | Aid rides `offer_trade`; zero new `proposal_type` strings (grep-verified) | VERIFIED |
| Tier A fixtures through Core pipeline | 20 tests in `test_culture_pass.py` | VERIFIED green (pre-fix run; re-run pending, see F1) |
| 500-tick culture census | Driver + chunked probe + invariant module written | UNKNOWN — not yet run |
| ≤ 400 ms/tick on collective_groups | `tools/_probe_culture_tick_time.py` written | UNKNOWN — not yet run |
| Replay hash equality two-run test | `test_two_identical_runs_hash_match_with_culture_active` | VERIFIED green (285.2s) |
| Frozen baselines: movement attribution | living_settlement has no `people` domain; persons there have no `storage_location` → byte-identical by construction | LIKELY; pin test not yet re-run |
| Defect watchlist: compat_action wraps, field copies, grep-isolation | 3/3 `start_step` sites wrapped; OFFER_TRADE fields copied through `context_from_action`; AID_/CULTURE_ imports confined to culture files + Core validator | VERIFIED by grep |

### Declared deviations (interpretations, not silent choices)

1. **No kin exists** in the people stack → ally ties = reciprocity-trust
   support + remembered counterparties.
2. **No groups exist** in `surplus_forage` → collective memory is per-person,
   shared by witnessing term-carrying signals.
3. **Gate target**: `group_collective` has no trade history (would be dead
   machinery — the documented Layer-E trap) → gate enforced on aid.
4. **Rejections are canonically invisible to actors** → norms learn from
   accepted outcomes only; rejection-rate reduction is an external
   (census-side) metric.

## 3. Findings

### Critical (must fix)

None found.

### Important (should fix)

**F1 — Norm double-count on re-observation.** *Found by this review; fixed
before publication of this packet.* `record_trade_outcome`
(`people_culture.py`) applied the norm EMA and incremented `accepts`/
`witnessed` **outside** the new-entry guard, so re-detecting the same trade
(own action record surviving a rejected follow-up proposal; a witness signal
living its 4-tick lifetime across activations) counted one trade up to 4
times — corrupting norm statistics and forcing redundant `culture_state`
rewrites. Deterministic, so no hash breakage, but wrong. **Fix:** norm update
moved inside the new-entry guard; regression tests
`test_repeated_detection_does_not_double_count` and
`test_persistent_signal_recorded_once_across_activations` added.
**Verification debt:** the full Tier A suite has not been re-run since the
fix (command approvals expired); the two new tests target exactly the changed
guard, and the remaining 18 fixtures do not discriminate old/new behaviour.
Suite re-run is the first command in §7. Status: fix written, suite
confirmation UNKNOWN.

**F2 — Tier B thresholds are asserted, not measured.** `aid_events ≥ 2`,
`memory_hit_rate ≥ 0.2`, `convergence ≥ 0.5`, `gate_blocked ≥ 1` in
`test_culture_pass_invariants.py` are design targets awaiting the 500-tick
census. If the census shows aid events at 0–1, the honest outcomes are
recalibrate (documented, seed-calibrated like Surplus Tier B) or retune aid
severity/eligibility — **not** silent threshold edits. The single observation
that settles this: `aid_events` in `test_reports/culture_census_500.json`.

**F3 — Three exit criteria unverified.** Census, benchmark, frozen-baseline
pin have not run locally (Bash approvals expired mid-session). The packet's
VERIFIED claims cover determinism and contracts only (Tier A + two-run).
Emergence, performance, and baseline-still-frozen are UNKNOWN until §7 runs.

### Minor (nice to have)

- **M1** Unused imports `TRADE_MIN_SURPLUS`/`TRADE_RANGE` lingered in
  `people_utility.py` after `eligible_trade_partner` was superseded. Fixed;
  grep-verified.
- **M2** No duplicate-aid CAS test. The pattern class is covered by Surplus's
  `test_duplicate_trade_is_deterministic_and_replay_safe` (same pins, same
  mechanics). Cheap to add if the reviewer wants symmetry.
- **M3** Census state pickles the `Scenario` object; re-fetching from the
  registry on resume would be cleaner. Works as-is (plain dataclass).
- **M4** Aid-giver satiation (hunger ≤ 400) is domain-side only; Core
  validates the receiver's need and the material flow, not the giver's mood.
  Deliberate boundary (Core validates transfer, not relationship) — named
  here so it isn't mistaken for an omission.

## 4. The repo's own rake — answered for this pass

The recorded failure mode is two questions treated as one. Applied here:

- **Mechanism exists vs behaviour occurs** — deliberately NOT fused: every
  emergence claim is gated on the pending census (F2/F3), and this packet
  asserts no emergent behaviour.
- **Gate vs behaviour upstream of the gate** — aid frequency depends on the
  whole chain (surplus ≥ 6 meat + satiation + ally + gate + range); the
  census measures each counter separately (`offer_ticks`, `aid_events`,
  `gate_blocked`) so a zero can be localized.
- **Measured delta vs real effect** — local two-run times (274.5s vs 285.2s
  per 80 ticks) are single-machine, single-run numbers; per CORE-INTEGRITY-004
  they are labelled machine-local, not a performance claim.
- **Assumed vs established baseline** — Surplus Tier A was re-run on this
  tree before culture landed (green), not assumed green from SURPLUS_PASS.md.
- **Commit message vs instrument** — no commit exists; this packet's claims
  are keyed to test names and log files, not prose memory.

## 5. Strengths

- Aid genuinely rides the existing proposal set: zero new `proposal_type`
  strings, barter validator untouched on the barter path (dispatch is a
  two-line defer), and the aid contract is validated with the same
  re-derivation rigour as `validate_people_trade` (12 reason codes, mutation
  math, CAS subset, position pin checked apart for dict values).
- Culture state discipline matches the house's hardest-won lessons: single
  writer, whole-map CAS mirroring `stored_resources`, write-on-change only,
  deep-copied compat (no aliasing into the pinned frame — the exact class
  that made CORE-INTEGRITY-003), bounded caps on every substructure.
- Witness propagation uses canonical signals with provenance — no group mind,
  no event-stream access, no projection-as-truth. Terms in signals are scoped
  to `offer_trade` only; every other family's payload is byte-identical.
- The gate is externally falsifiable: `aid_to_non_traders` is computed from
  the accepted-event stream, not from diagnostics the implementation could
  game.

## 6. Assessment

**Ready to merge: No — with fixes pending verification.**

**Reasoning:** Contracts and determinism are verified (Tier A 18 + 2
regression fixtures, two-run hash equality, surplus suite unaffected);
emergence, performance, and baseline-still-frozen are not (F2/F3). The
double-count find (F1) shows the review was load-bearing. Commit only after
§7 completes and `CULTURE_PASS.md`'s measured-emergence section is filled
from actual run output.

## 6b. Disposition of the Cairn findings (2026-07-30)

An external read-only adversarial review (`CULTURE_PASS_ADVERSARIAL_REVIEW.md`)
landed after this packet. Each finding was verified against the code before
action; none required pushback on technical grounds.

| Finding | Verification result | Disposition |
|---|---|---|
| S1 emotion layer in tree, byte-identity claim false | CONFIRMED. `emotion_domain.py`/`emotion_contracts.py` untracked, `EmotionDomain` registered ungated at priority 8, `emotions` block minted in `empty_living_agent_state` and backfilled by compat — every living-agent scenario's canonical state differs from HEAD regardless of the culture gate. My "byte-identical by construction" claim was false for the tree as a whole (it remains true for the culture layer's own gating — Cairn confirmed "the culture layer's own gating is airtight"). The owner anticipated this leg ("document attribution: culture additive vs people-stack emotion leg"). | OWNER DECISION (quarantine vs declare) — not mine to revert another leg's work. Frozen-baseline run moved to front of queue as the cheapest falsifier; movement will be attributed culture-vs-emotion as the owner instructed. Reporting corrected in CULTURE_PASS.md. |
| S2 capacity overflow via norm-priced terms | CONFIRMED reachable (give 2/receive 3 at full carry nets +1; no re-check anywhere). | FIXED: `trade.capacity_exceeded` re-derived for both parties in `validate_people_trade`; emission clamps in `select_trade_partner` (each leg bounded by the opposite party's room). Tier A regression test. |
| S3 aid wood legs not re-derived | CONFIRMED — strictly weaker than the barter validator beside it. | FIXED: all four legs checked against live state in `validate_people_aid`. Tier A regression test (`test_aid_arbitrary_wood_mutation_rejects`). |
| S4 memory cap pre-insert; silent cap eviction | CONFIRMED both halves (17 reachable; `changed` under-reported). | FIXED: eviction after insertion; cap deletions fold into `changed`. Tier A committed-cap test. |
| S5 receiver retain violated at receive_qty 3 | CONFIRMED (4-holder drops to 1 < TRADE_MIN_RETAIN). | FIXED: retain pin required by Core + emitted by the domain + emission clamp (`partner_stock − TRADE_MIN_RETAIN`). Two Tier A tests (required-set + pin bites + emission clamps). Surplus `_trade_proposal` helper updated to the new standard pin set. |
| S6 set-precedence in refresh_aid_eligible | CONFIRMED latent (benign today: interaction facts never record subject == observer by construction). | FIXED: union parenthesized. |
| S7 doc drift (severity comment, floating baseline) | CONFIRMED; the "up to 330" figure is only reachable at generosity 100 (trait seeds are 25–75; 317 typical max) — moot either way since aid never competes with barter for the slot. | FIXED: comment rewritten (slot semantics, not magnitude). Floating-baseline point stands and is owner-facing (surplus-first commit is their call under the no-commit rule). |

Post-fix verification status: fast Tier A re-run across both suites is the
next queued command (approvals pending); the two-run hash test will be re-run
after it, since trade-precondition content changed for barter proposals.

The reviewer's recommended sequence is adopted with one deviation: step 4
(commit surplus first) is surfaced to the owner rather than executed — the
standing instruction to this session is "do not commit; review first."

## 7. Independent verification (in order)

From `backend/` with the repo-root venv; long runs redirect to
`test_reports/` per house rule:

```bash
# 1. Tier A incl. F1 regression tests (fast)
../.venv/Scripts/python.exe -m pytest tests/test_surplus_pass.py tests/test_culture_pass.py -q -k "not two_identical"

# 2. Two-run hash equality (2 × ~4.5 min)
../.venv/Scripts/python.exe -m pytest tests/test_culture_pass.py -q -k two_identical > ../test_reports/tier_a_culture_tworun.log 2>&1

# 3. 500-tick culture census (repeat until "complete": true; ~9 chunks)
../.venv/Scripts/python.exe -m tools._probe_culture_census --seed culture-tier-b \
  --ticks 500 --chunk 60 --state ../test_reports/culture_census_state.pkl \
  --report ../test_reports/culture_census_500.json > ../test_reports/culture_census_chunk.log 2>&1

# 4. Tier B invariants (single-process; calibrate thresholds from step 3 first if needed)
../.venv/Scripts/python.exe -m pytest tests/test_culture_pass_invariants.py -q > ../test_reports/tier_b_culture.log 2>&1

# 5. Tick-time benchmark (~3 min; gate ≤ 400 ms/tick)
../.venv/Scripts/python.exe -m tools._probe_culture_tick_time --ticks 500 \
  --report ../test_reports/culture_tick_time.json > ../test_reports/culture_tick_time.log 2>&1

# 6. Frozen baseline pin (~2–4 min; must not move)
../.venv/Scripts/python.exe -m pytest tests/test_frozen_baseline_hashes.py -q > ../test_reports/frozen_baseline_culture.log 2>&1
```

Evidence so far: `test_reports/tier_a_surplus_tworun.log` (1 passed,
274.54s), `test_reports/tier_a_culture_tworun.log` (1 passed, 285.21s), fast
fixtures 41 passed 2 deselected (0.58s, post-S2–S6-fix), plus:

- **Frozen-baseline pin FAILED as Cairn's S1 predicted** (101.53s,
  `test_reports/frozen_baseline_culture.log`): living_settlement@320 moved to
  `5ffaf4ba7bb669ea09bfe13c1537cae1bc1d37c4be6eaceb38358c8603858c76`, accepted
  5,774 vs ratified 5,088. Attribution completed
  (`test_reports/frozen_attribution.json` + static decomposition, recorded in
  `CULTURE_PASS.md` §Frozen-baseline attribution): **the emotion leg's
  contracts hunk is the mover** (canonical `emotion-v1` block on every
  living_agent → CI-004 chaotic ordering, +686 events; emotion domain fires
  zero events, the gradient is inert at 0 < 100); **culture contributes zero**
  (statically absent from the scenario; both probe variants byte-identical);
  surplus contributes zero; R1 is not in this tree. The re-baseline/quarantine
  STOP is the owner's call.
- Post-fix two-run re-verification: the continuous pytest exceeds the local
  per-command budget (killed at 300s), so it runs chunked via
  `tools/_probe_tworun.py` (same traces, fragment cache, resumable; both runs
  share chunk boundaries, making it an exact A/B determinism check). PENDING.
