# Layer C Variety Leg 1 (Upkeep) — adversarial review findings ledger

**Recorded:** 2026-07-25
**Fixes applied:** 2026-07-25
**Full report:** `scratchpad/upkeep_adversarial_review_ledger.md`
**Reviewer brief:** `scratchpad/upkeep_reviewer_brief.md`
**Contract:** `memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md` (§10 close-out)
**Protocol:** `memory/ADVERSARIAL-REVIEW-PROTOCOL.md`
**Reviewer:** Grok 4.5 (xAI) — cross-vendor, independent of the Anthropic
implementer session. Codex path unavailable (usage quota exhausted to
2026-07-29); brief authorised Grok as substitute. Same human (Ryan) owns both
the implementer and reviewer sessions — no second independent re-run of the
organic gate or full suite by the reviewer; suite counts were builder-asserted
at review time (see F-05 below).

## Ledger

| ID | Source | Summary | Disposition | Status |
|---|---|---|---|---|
| S1 | builder-seeded | Candidate-order starvation under the 16-item append-order cap; `TEND_STRUCTURE` generated last, before the `EXPLORE`/`REST` fallbacks | **FIX** | Applied pre-review, confirmed by reviewer |
| S2 | builder-seeded | `TEND_STRUCTURE_BASE_SCORE` 400 (above `EXPLORE`) caused an absorbing tending loop that starved exploration; rebalanced to 120 (between `REST` and `EXPLORE`) | **FIX** | Applied pre-review, confirmed by reviewer |
| F-04 | builder-seeded + independent | `assert summary["false_belief_count"] >= 0"` in `test_stage6e_living_settlement.py` is vacuous (always true) — no longer a regression net for false-belief detection | **FIX** | Applied — new dedicated test `test_false_belief_detection_flags_a_known_deceptive_report` added; demonstrated to fail under an induced regression and pass restored |
| F-05 | independent | Claim of "338 passed / 4 skipped / 0 failed" was not backed by a saved suite log in the evidence package; not independently re-run by the reviewer | **FIX** | Applied — full suite re-run at close-out, log saved: `memory/evidence/layer-c-leg1/full_suite_closeout.txt` (339 executed passed, 4 known skips excluded, 5 known `MONGO_URL`-env collection errors excluded, 0 executed failed) |
| F-03 | independent | "Upkeep fires organically ... both scenarios, both seeds" overstated coverage — `living_settlement` evidence exists for seed1 only | **FIX** (wording) | Applied — corrected in the contract's session-handoff summary and in `FRONTIER.md`; the individual per-scenario gate items in the contract §6 were already correctly single-seed-scoped |
| F-06 | independent | Re-baseline causal diff (contract §6 item 3) listed rest/tend/repair counts only and omitted the largest non-tend shift (`move` 62→304) and the social-action shifts | **FIX** (wording) | Applied — contract §6 item 3 now carries the full 7-action delta table (rest, tend, repair, move, request_help, cooperate, repay), sourced directly from the pre- and post-leg 320-tick evidence files |
| F-01 | independent (Focus A) | Variety claim should cite the full action-type distribution / entropy, not rest% alone; mix genuinely broadened (not rest replaced by a single new chore) but residual rest+tend still 54-67% combined | **ACCEPT** (wording) | Applied — contract §6 items 2/3 and `FRONTIER.md` now cite Shannon entropy (0.75→2.31 bits `collective_groups`; 1.52→2.46 bits `living_settlement`) alongside the distribution table |
| F-02 | independent (Focus B) | `repair` count drop (9→4) attributed to a proactive-tending/band interaction is mechanism-plausible but not trajectory-proven in the evidence (no condition-over-time dump) | **ACCEPT** | No code or wording change required — mechanism argument and nonzero residual repair count stand as originally written |

## Re-baseline

Authorised by Ryan (2026-07-25), conditional on the F-06 causal-diff write-up
being complete. Applied: frozen `living_settlement` 320-tick hash moves
`84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2` →
`897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab`.

## Rulings (Ryan, 2026-07-25)

Recorded verbatim in `scratchpad/upkeep_adversarial_review_ledger.md`:

1. F-04/S3: FIX — restore a real net (a dedicated false-belief test or a
   non-vacuous integrated pin); the vacuous `>= 0` form does not ship.
2. F-05: suite log required — one full-suite run with the log saved under
   `memory/evidence/layer-c-leg1/` before close-out; builder assertion alone
   not accepted.
3. Re-baseline: authorised, conditional on the F-06-complete causal write-up.
4. F-01, F-02 dispositions stand as ACCEPT; F-03, F-06 wording fixes stand as
   FIX for the close-out author.
