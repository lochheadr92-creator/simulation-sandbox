# Layer A — `living_agent` whole-blob CAS refusal: bounded attribution

**Verdict: BRANCH B — PARKED.** Attribution succeeded completely; the dominant
mechanism is **not a defect** and the remediable minority is blocked by a hard
rail. No remediation implemented. No production behaviour changed.

## Isolation (verified before any run)

Clean detached worktree from committed HEAD `521ecccf` at `C:/dev/wt-cas-attribution`.

| check | result |
|---|---|
| `git status --porcelain` | empty |
| `STORE_SURPLUS_MIN_FOOD` occurrences | **0** |
| store eligibility | `resources.get("food", 0) >= 3` |
| `REQUEST_HELP` target | `visible_person_ids[0]` (no R1) |
| R1 sentinel / R1 test file | absent / absent |
| main worktree | **not touched** |

**Positive controls — both passed, proving the arm clean and the probe inert:**

- `collective_groups` seed 1 @1,200 reproduced the committed baseline
  `4efe6c5080704633fd5806e70ee9560b79a7294664caca0d5228cd3e108d2a21`.
- `living_settlement` @320 reproduced the **frozen** hash
  `9c1b9b8ba28a6fa830ff141d1eea7a8755d7c13a5a62dfc94ba93a15946e55d4`
  (CLAUDE.md `9c1b9b8b…46e55d4`).
- `replay_matches_entities: true` on every run.

## Mechanism (VERIFIED)

`_replace_living_preconditions` (`living_settlement_domain.py:516-519`) re-pins
every `living_agent` precondition to the **frame-start** blob.
`build_social_action_proposal` attaches whole-blob `eq` CAS conditions for the
actor **and** the target (`living_agent_social.py:328,335`). `run_commit_frame`
commits one proposal at a time against progressively-mutated state and
re-validates (`commit_pipeline.py:476`). Social actions write the **target's**
blob as well as their own.

So when any earlier-committed event in the same frame writes entity X's
`living_agent`, X's own proposal fails a whole-blob equality check.

**Attribution is 100% on every run — zero unattributed.** Every
`living_agent_eq_failed` rejection maps to exactly one earlier same-frame writer,
and `writers_per_failing_condition` is 1 in every case.

## Results

| measurement | `living_agent_eq_failed` | attributed | genuine same-sub-key conflict | independent sub-keys | recoverable by field-scoped CAS |
|---|---|---|---|---|---|
| `living_settlement` @320 **(frozen)** | 1,181 | 1,181 (100%) | 1,024 (**81.9%**) | 226 (18.1%) | 235 (**19.9%**) |
| `collective_groups` seed 1 @1,200 | 1,389 | 1,389 (100%) | 1,369 (**79.1%**) | 362 (20.9%) | 427 (**30.7%**) |
| `collective_groups` seed 2 @1,200 | 1,466 | 1,466 (100%) | 1,595 (**82.5%**) | 338 (17.5%) | 415 (**28.3%**) |

Three independent measurements across two scenarios agree: **79–83% genuine
conflict, 17–21% independent sub-keys, 20–31% recoverable.**

Seed 1 detail: `living_agent_eq_failed` is 1,389 of 2,382 total rejections
(58.3%); seed 2, 1,466 of 2,598 (56.4%). Pinned entity is **another entity's
blob** in 1,241 of 1,796 failing conditions on seed 1 (69%) and 1,337 of 2,010 on
seed 2 (67%) — the dominant case is *someone else's social action writing my
blob*. Top writers: `request_help` 695, `cooperate` 547, `repay` 408 — the
reference family colliding with itself.

### Granularity matters, and it was measured at both levels

At **top-level key** granularity, 1,731 of 1,796 failing conditions (96%) look
"overlapping". But `relationships` and `commitments` are per-subject / per-id
**maps**, so two writers touching different entries are independent. Measured at
**sub-key** granularity, the independent share is 18–21% — not 4%.

Sub-key conflicts concentrate on specific entries: `relationships:person-000`
(27 in the 120-tick sample) and individual `commitments:commitment-…` ids —
genuine contention over the same relationship edge or the same commitment record,
not coarse-grained comparison.

## Why Branch B

**The 80% test is met — by the *non-remediable* mechanism.** 79–82% of failing
conditions are genuine **same-sub-key write-write conflicts**: two proposals in
one frame both modifying the same `relationships[subject]` entry or the same
`commitments[id]` record. Branch A's own constraint requires the remediation to
*"fail closed on genuinely overlapping writes"* — so those must continue to be
rejected. The CAS is doing its job.

The remediable portion — proposals touching genuinely independent sub-keys — is
**19.9% (frozen scenario) to 30.7% (collective_groups)**. No *remediable*
mechanism reaches 80%.

**And that minority is hard-rail blocked.** 235 of the frozen scenario's own
1,181 rejections are recoverable, so any field-scoped CAS necessarily changes
accept/reject outcomes inside `living_settlement` and moves the frozen 320-tick
hash `9c1b9b8b…46e55d4`. CLAUDE.md rails that: *"Re-baseline requires explicit
authorisation."* This task granted none.

Implementing anyway would mean a ~20% recovery on the frozen scenario, purchased
with a new Core precondition operator and a full-blast-radius hash re-baseline,
against an unauthorised rail. That is not the smallest ownership-correct
remediation; it is a large change with a small measured payoff.

## Corrected framing (this supersedes the earlier characterisation)

The finding recorded in `leg2_session1_funnel_report.md` §7 — that 56–70% of
winning social decisions are refused at the whole-blob CAS — **stands as a
measurement**. What changes is its interpretation: it was described as a
structural *wall* implying a defect. It is mostly **genuine concurrency
contention**. Roughly four fifths of those refusals are two agents legitimately
competing to write the same relationship edge or commitment record in one frame.

Consequence for future social work: raising social-action generation will still
meet this ceiling, and narrowing the CAS would relieve only about a fifth of it.
The ceiling is a property of same-frame contention over shared social state, not
of an over-strict equality check.

## Residual unattributed

**Zero.** Every `living_agent_eq_failed` rejection on every run was attributed to
exactly one earlier same-frame writer.

## Not done, deliberately

No remediation, no new precondition operator, no CAS redesign, no hash
re-baseline, no test or threshold edits, no Stage 7A–7D contact, no changes to
the main worktree, R1, or Leg 1.
