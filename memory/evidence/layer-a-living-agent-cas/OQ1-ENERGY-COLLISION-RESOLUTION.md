# OQ-1 — same-tick `energy` collisions: RESOLVED, and NOT benign

**Verdict: CONFIRMED LOST UPDATE.** `REGISTRY-COMPONENT-OWNERSHIP.md` holds
`energy` at MEDIUM *"pending OQ-1 … Drop to LOW if OQ-1 resolves to something
benign."* **It does not resolve benign. The rating must NOT drop to LOW.**

Read-only attribution, clean detached worktree from `521ecccf`. No production
behaviour changed, nothing patched.

## Result

| arm | ticks | energy-writing events | **collisions** |
|---|---|---|---|
| `collective_groups` | 1,000 | 7,137 | **97** |
| `living_settlement` (control) | 1,000 | 2,644 | **0** |
| `living_settlement` (control) | 320 | 1,511 | **0** |

The control detects thousands of energy writes and finds zero collisions, so the
zero is a measured absence, not a probe that cannot see them. Replay exact on
every run; the 320-tick control reproduced the frozen hash
`9c1b9b8ba28a6fa830ff141d1eea7a8755d7c13a5a62dfc94ba93a15946e55d4`.

## Every collision has one identical shape (97/97)

| property | value |
|---|---|
| writers per collision | **2**, in all 97 |
| self vs cross | **`mixed_self_and_cross`**, in all 97 |
| cross writer | **`social_cooperate`**, in all 97 |
| self writer | the recipient's own physical action — `move` 43, `rest` 27, `tend` 19, `consume` 6, `drink` 1, `gather` 1 |
| outcome | **`final_equals_last_writer`, in all 97** |

## The defect, worked

Tick 4, `person-007`, frame-start energy **565**:

1. `person-001`'s `cooperate` (`evt-4-82`) writes `person-007.energy = 605` — the
   **+40 help benefit**.
2. `person-007`'s own `rest` (`evt-4-83`) writes `640` — that is `565 + 75`,
   computed from the **frame-start** base, not from 605.
3. Final: **640**. Correct composition would be 680. **The help is silently
   discarded.**

Tick 69, `person-007`, frame-start **970**: `cooperate` writes 1000 (+30);
the recipient's own `move` writes 965 (`970 − 5`); final **965** — help lost.

`final_minus_pre_frame_energy` confirms the pattern at scale: **−5 occurs 70 of
97 times** — the bare action cost, with the cooperate benefit entirely absent.

## Mechanism (VERIFIED — this is documented finding F4)

`REGISTRY-COMPONENT-OWNERSHIP.md` F4 already records the asymmetry:
`build_social_action_proposal` CASes the blob
(`living_agent_social.py:324,331`), while `build_physical_action_proposal`
**CASes neither** — `living_agent_actions.py:294-296` pins only `alive`.

So the recipient's own physical action carries no precondition capable of
detecting that its `energy` base changed mid-frame. It commits second and
overwrites `energy` with a value derived from the stale frame-start snapshot.
This is a genuine lost update, not last-write-wins over equivalent values:
`all_writers_wrote_same_value` occurred **once** in 97 collisions.

## Player-visible consequence

Helping another agent frequently does nothing. In `collective_groups`, 97 times
per 1,000 ticks a `cooperate` transfers energy that is then erased in the same
frame by the recipient's own action. The cooperation event is committed and
replay-visible — the benefit is not.

This compounds the Layer A picture: the CAS attribution
(`ATTRIBUTION-REPORT.md`) found ~80% of social-action refusals are *legitimate*
contention that correctly fails closed. Here the opposite failure appears — a
write that is **not** protected at all, and silently loses.

## Two things NOT established

- **Why the asymmetry.** The scenario difference is reproduced at matched
  horizons but its cause is **UNKNOWN**. `collective_groups` differs from
  `living_settlement` by the five group domains and by packed genesis positions.
  A plausible candidate is that `social_cooperate` and a recipient action rarely
  co-occur in a frame in `living_settlement`, but that was not measured and is
  **not claimed**.
### The 64 vs 97 discrepancy — original basis PROVEN, and it is not a scope difference

The registry's original basis **is** recoverable and is method-identical to this
run. `REGISTRY-COMPONENT-OWNERSHIP.md` "Open questions" records: *"The
multi-writer census measured **64** same-tick / same-person / same-field `energy`
collisions in **1,000 ticks of `collective_groups`** … reproduced identically
across two independent probe runs."* Same scenario, same horizon, same
same-tick/same-person/same-field basis as the 97 measured here.

**So the two figures are not differently scoped — they measure different
worlds.** OQ-1 was opened **2026-07-26**. Two authorised re-baselines landed
**2026-07-27**, both after that measurement and both of which moved the canonical
trajectory:

- `ce49d762` — *fix(genesis): keyed RNG sub-streams + spawn index — authorised
  re-baseline*
- `180c43f4` — *feat(lifecycle): rebaseline realistic founder ages*

CLAUDE.md records the resulting frozen-hash move `48dfec22…1b1e3b` (stage 1,
genesis RNG isolation) → `9c1b9b8b…46e55d4` (stage 2, realistic founder ages).

**Disposition: 64 is superseded by 97.** The method is unchanged; the world it
was measured on no longer exists. The two numbers must not be equated, and the
difference is not evidence of measurement error in either. Under
CORE-INTEGRITY-004 — commit order is content-derived, so any perturbation
propagates chaotically — a changed collision count across a re-baseline is the
expected consequence, not an anomaly.

## Registry action required (not performed here)

The `energy` row should be updated: OQ-1 is resolved, the rating must stay at or
above MEDIUM, and the resolution is a confirmed lost update via F4's unprotected
physical-action path. **Not edited** — `REGISTRY-COMPONENT-OWNERSHIP.md`
currently carries uncommitted Leg 1 and Leg 2 content and cannot be staged
without including unrelated work. Requires `git add -p`.

## Remediation — NOT attempted

The obvious fix (give `build_physical_action_proposal` a CAS on the fields it
writes) changes accept/reject outcomes and would move frozen hashes. That is a
hard rail requiring explicit authorisation and is out of scope here.
