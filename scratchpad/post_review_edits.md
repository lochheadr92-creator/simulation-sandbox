# Stage 8B Leg 1 — post-review text — APPLIED 2026-07-24

Both edits below were drafted from already-ruled decisions and already-verified
gate numbers. They have now been applied as follows:

| Edit | Applied to |
|---|---|
| Edit 1 — F1 claim-9 wording | `scratchpad/leg1_claims_closeout.md` claim 9; `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md` § F1 ruling |
| Edit 2 — Amendment 2 verified addendum | `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md` § Contract amendment 2 |

Additional review FIX items applied in the same pass:

- P1-01 schema claim (`backfilled_norm_ids`) — close-out claims + contract schema
- P1-02 `learned_tick` wording — close-out claims + contract mechanism
- P1-03 lag assumption documented (ACCEPT)
- P1-05 influence-firing claim qualified / not over-claimed
- P1-06 coupling claim weakened without probe artifact
- P1-07 contract + `memory/ADVERSARIAL-REVIEW-PROTOCOL.md` restored

Bare claims file left intentionally unfixed (historical blind-pass trap) with a
pointer banner to the close-out claims.

---

## Edit 1 — F1 corrected claim-9 wording (source text)

> - **Eligibility** (the read-only nudge) is carriage-only and fully membership-independent: `_apply_group_norm_influence` consults the carriage registry and nothing else, so a carrier who has left the group is still nudged and a current member who never earned carriage is not.
> - **Acquisition** by transmission additionally requires co-membership: `derive_group_carriage_changes` selects learners from `member_ids - carriers`. A non-member cannot learn.

## Edit 2 — Amendment 2 close-out addendum (source text)

> ### Post-amendment-2 gate re-run (2026-07-23) — VERIFIED, closes this amendment
>
> Cloud re-run (Ubuntu 24.04 / Python 3.11.15 / Mongo 8.0.4 single-node replica set); all figures from the v3 evidence files, not memory.
>
> - **Frozen-hash safety — PASS, byte-identical.** …
> - **Determinism + organic — PASS.** …
> - **Suite — 369 executed passed; 4 named Docker-environment skips; 1 in-context intermittent** …
> - **Registry byte re-measure — closes the amendment.** 17,126 B vs `payload_target_bytes` 24,576 B → **30.31% headroom** …
> - Evidence: `memory/evidence/stage-8b-leg1/…`
