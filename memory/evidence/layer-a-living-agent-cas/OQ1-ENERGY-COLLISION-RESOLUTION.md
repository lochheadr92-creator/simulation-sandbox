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

---

# REMEDIATION DECISION PACKAGE (CORE-INTEGRITY-001 class)

Nothing implemented. No behaviour changed, no simulation run beyond committed
evidence. THE-SPINE §8 defers this remediation pending a dedicated stage at a
STOP; that stage is not open.

## Option (a) — energy precondition on physical action proposals

**Files.** `backend/domains/living_agent_actions.py` preconditions list (`:300`),
or equivalently the universal energy write in
`backend/domains/living_settlement_domain.py:712-715`. The latter covers strictly
more: the `-5` per-action cost is applied on the shared path after *either*
builder, so it lands on social proposals too.

**Blast radius — far beyond those lines (VERIFIED).** A precondition is part of
`core_fields`, so it changes `content_hash`; `content_hash` is the final
tie-break in `order_key` (`commit_pipeline.py:108-109`). Measured: 92.3% of
`living_settlement` proposals and 86.9% of `collective_groups` proposals sit in
tie groups resolved only by `content_hash`. Adding a **semantically inactive**
precondition — one pinning a value already true, which cannot fail — permuted
tick 1 entirely. So this option reorders the world before its own guard ever
evaluates.

**Frozen hashes: MOVES (VERIFIED).** Measured directly: `living_settlement` @320
went `9c1b9b8b…46e55d4` → `9b118c8cc602c490d8afac09327d3440c5fa4930527b46c9aded4f66ee8f2727`
with 17 energy rejections in that window. Every scenario trajectory hash moves.

**Effect on the ~60% CAS refusal rate: RISES (VERIFIED).** It adds a new refusal
class rather than relieving the existing one. Measured 44 `energy_eq_failed`
rejections in `collective_groups` @1,000 and 18 in `living_settlement` @1,000, on
top of the existing `living_agent_eq_failed` volume.

**Player sees:** nothing new — help still fails to land, it just fails visibly in
the inspector's rejection panel instead of silently.

**Regression risk.** Core rejects at *proposal* granularity — there is no
field-level partial commit — so a failed energy precondition drops the whole
physical proposal, taking its position, hunger, gathered resources, tending and
rest recovery with it. Measured cost: 44 dropped proposals, and `collective_groups`
ended 7 alive against baseline 8. That death was **not attributable** to the
guard versus the ordering perturbation, which is why this option was verified
`INSUFFICIENT / INCORRECT` rather than accepted.

**Extend-only: yes** — no sealed scorer or mutation path is edited.

## Option (b) — compositional (delta) energy write

**Files.** `backend/core/mutations.py:24` (`apply_mutation` is a pure
`entities[eid].update(updates)` — there is **no additive or merge semantics
anywhere in the repository**, VERIFIED), plus all five absolute energy writers:
`living_agent_actions.py:441,509,511`, `living_agent_social.py:440,441`,
`living_settlement_domain.py:712`.

**Blast radius — larger than it looks, and structurally blocked (VERIFIED).**
`actor_after`, carrying the absolute post-write energy, is read back at
`living_settlement_domain.py:786-789` by `derive_internal_pressures`, which
computes `fatigue = 1000 - energy` (`living_agent_cognition.py:470`) and
`comfort` (`:487`) into `living_agent.pressures` **inside the same proposal**.
Under delta semantics the domain cannot know the composed energy at build time,
so the pressures it writes would be derived from a prediction the composition may
contradict — and `fatigue >= 650` gates REST generation next tick. Fixing that
means relocating pressure derivation into Core, post-composition: a Layer C
cognitive derivation moving into Core, inverting "Core owns truth; domains are
proposal-only".

**Frozen hashes: MOVES.** All of them (LIKELY — not measured; nothing was built).

**Effect on the ~60% CAS refusal rate: FLAT (LIKELY).** It fixes the *unprotected*
write path; it does not touch the whole-blob `living_agent` CAS, where 79–83% of
refusals are genuine same-sub-key contention that must keep failing closed.

**Player sees:** helping someone actually raises their energy, instead of the
benefit vanishing whenever the recipient acts in the same instant.

**Regression risk.** Clamp semantics change: today each writer clamps its own
absolute value; composed deltas must clamp once, which alters behaviour at 0 and
1000. Verified by focused tests on composition, single-clamp at both bounds,
commutativity, and replay equality.

**Extend-only: NO.** It edits `apply_mutation` — the module whose docstring says
"Only this module mutates `entities`" — and needs a mutation-schema version bump.

## Option (c) — record and defer

**Files.** None. **Frozen hashes:** unmoved. **CAS refusal rate:** flat.
**Player sees:** helping continues to do nothing roughly 97 times per 1,000 ticks
in `collective_groups`. **Regression risk:** none introduced; the existing defect
persists and any future work raising social-action volume inherits it.
**Extend-only:** trivially.

## Option (d) — sequence CORE-INTEGRITY-004 first (added)

Make commit ordering content-independent before attempting (a) or (b).

**Files.** `backend/core/commit_pipeline.py` only — `order_key` and a
fail-closed duplicate rail.

**Basis (VERIFIED).** Built and tested on branch `core-integrity-004`: focused
tests 20/20, full suite 452 passed / 4 skipped / 3 failed, contention and
determinism guardians green, and the acceptance proof exact — an inactive
precondition produced *byte-identical* hashes
(`living_settlement` `5b4eff56da1d5ddd…`, `collective_groups` `74f050fea2be79d0…`).

**Frozen hashes: MOVES** — `9c1b9b8b…46e55d4` → `5b4eff56da1d5ddd…`, first
divergence tick 1.

**Effect on the CAS refusal rate: RISES, sharply and informatively (VERIFIED).**
Under corrected ordering `THREATEN` and `VERIFY_INFORMATION` win arbitration 191
and 171 times per 200 ticks and commit **zero** times, refused 318× on
`living_agent_eq_failed`. Content-ordering had been incidentally scheduling those
two actions into the one slot where the blob was still clean.

**Player sees:** nothing directly; two social behaviours stop occurring until the
CAS question is answered.

**Regression risk.** Two capability fixtures fail
(`test_integrated_camp_…_replays`, `test_warn_danger_commits_…`) asserting
capability *presence*, not trajectory — class 1 invariants, so CI-004 cannot
migrate alone.

**Extend-only: yes** for the ordering key; no domain change.

## Recommendation

**(c) record and defer, with (d) sequenced as the prerequisite when the stage
opens.** Rationale: (a) is measured and rejected — it raises refusals, drops
whole proposals, and its own guard perturbs ordering before firing. (b) is
arithmetically correct but structurally blocked by the pressure read-back and is
not extend-only. Neither can be *evaluated* while `content_hash` orders commits,
because any content edit reorders the world from tick 1 — that is what made (a)'s
survival delta unattributable.

**Strongest argument against this recommendation:** deferring leaves a confirmed,
player-visible correctness defect in place — help silently doing nothing ~97
times per 1,000 ticks — and (d) makes the situation *worse before better*, since
corrected ordering exposes the CAS wall and stops two social behaviours entirely.
A reviewer could reasonably argue that (b), despite its cost, is the only option
that ever makes cooperation work, and that sequencing behind two Core stages
risks indefinite deferral of a defect that is already understood.
