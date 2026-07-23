# Stage 8B Leg 1 — adversarial review findings ledger

**Recorded:** 2026-07-24  
**Fixes applied:** 2026-07-24  
**Full report:** `scratchpad/leg1_adversarial_review_report.md`  
**Close-out claims:** `scratchpad/leg1_claims_closeout.md`  
**Contract:** `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md`  
**Protocol:** `memory/ADVERSARIAL-REVIEW-PROTOCOL.md`  
**Reviewer:** Grok (xAI) — cross-model automated; Codex unavailable (usage limit).

## Ledger

| ID | Source | Summary | Disposition | Status |
|---|---|---|---|---|
| F1 | Builder + P1-04 | Claim 9 conflates eligibility and acquisition | **FIX** wording / **ACCEPT** code | **Applied** — close-out claims + contract F1 section |
| F2/F2c | Builder | Registry headroom after slim + no pending (17,126 B, 30.31%) | **FIX** (code already) | **Closed** — Amendment-2 gate block in contract |
| F3 | Builder | `backfilled_norm_ids` eviction order | **FIX** (code already) | **Closed** — regression test in suite |
| P1-01 | Pass 1 | Claim 2 omits `backfilled_norm_ids` | **FIX** | **Applied** — close-out claims + contract schema |
| P1-02 | Pass 1 | Claim 3 `learned_tick` ≠ formation tick | **FIX** | **Applied** — close-out claims + contract mechanism |
| P1-03 | Pass 1 | Backfill supporters = current active goal, not formation snapshot | **ACCEPT** | **Documented** — lag assumption in contract |
| P1-05 | Pass 1 | Claim 10 zero influence firings unmeasured | **FIX** | **Applied** — claim 10 no longer over-claims measurement |
| P1-06 | Pass 1 | Claim 15 coupling probe not in evidence packet | **FIX** | **Applied** — claim 15 design-statement only |
| P1-07 | Pass 1 | Contract + protocol files missing from tree | **FIX** | **Applied** — both files restored under `memory/` |
| P1-08 | Pass 1 | Pytest log: 1 failed + 369 passed (intermittent concurrency) | **ACCEPT** | **Documented** — CORE-INTEGRITY-001 caveat |
| HR-1..4 | Hard-rail | Four mechanical hits | **ACCEPT** | **Closed** — no further action |

**Mandatory DISPUTE:** none.  
**Optional DISPUTE (open for user STOP):** elevate P1-03 if formation-time-exact supporters are required.

## Evidence cited

- `harness_living_settlement_320_v3.json` — frozen hash `84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`
- `harness_collective_groups_1000_v3.json` — hash `b5abbfffa9e0b5b5b52da912c757b75231afb8b752658a1a76e9d91d7472368c`; repeat/replay true; `group_carry_norm=4`
- `probe_8b_registry_bytes_post_a2.json` — 50 carriers (49 backfill + 1 tx), 17,126 B
- `pytest_full_suite_post_a2.log` — 369 passed, 4 skipped, 1 failed (concurrency canary)

## Verdict (post-fix)

Doc/claim FIX rows are applied. Code FIX rows (F2/F3) were already in the Leg 1
change set. Remaining gate for the human: close-out STOP + commit series.
Do not open Stage 8C until that STOP.
