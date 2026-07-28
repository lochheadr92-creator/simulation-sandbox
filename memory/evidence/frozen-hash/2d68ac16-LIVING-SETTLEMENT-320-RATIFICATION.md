# living_settlement@320 frozen-hash move at `2d68ac16` — causal diff and ratification

**Ruling: RATIFIED. Accepted by Ryan (owner) 2026-07-28.**
New protected baseline: `4240d6a088514c1c84367b03beac4712e4d33009b28f0f22748cbdac305de1bb`
Supersedes: `9c1b9b8ba28a6fa830ff141d1eea7a8755d7c13a5a62dfc94ba93a15946e55d4`

This is the STOP write-up FRONTIER's re-entry condition requires. Adversarially
reviewed by Kimi Code on 2026-07-28 (verdict RETURN; every load-bearing
measurement reproduced independently — see §7).

## 1. Measurement

From `backend/` in each worktree:

```
py -3.12 -m tools.living_agent_harness --scenario living_settlement --ticks 320 --seed living-agents-stage6
```

| arm | commit | accepted events | `final_state_hash` |
|---|---|---:|---|
| A | `882cdbc1` (parent) | 4,947 | `9c1b9b8b…46e55d4` — reproduces the old frozen hash |
| B | `1c14371a` (contains `2d68ac16`) | 4,868 | `4240d6a0…305de1bb` — moved |

Arm A reproducing the recorded hash exactly is the instrument check: same
machine, same interpreter, same session. `git diff 882cdbc1..1c14371a` is seven
files containing exactly two functional lines — `constants.py`
`STORE_SURPLUS_MIN_FOOD = 2` and the comparison RHS in
`living_settlement_domain.py`. No `.pyc`, fixture, or data files in range;
nothing docs-side is read at runtime. The delta is attributable to `2d68ac16`
alone.

## 2. Causal diff — one event

Accepted streams captured with `capture_events=True` and compared
element-by-element. **Identical for indices 0–283.** First divergence at index
284, `frame-14`:

| arm | event | actor | explanation |
|---|---|---|---|
| A | `evt-14-284-b8266ef3` `living_retrieve` | person-000 | `plan_continuation: selected RETRIEVE_FOOD` |
| B | `evt-14-284-7c5c128c` `living_store` | person-001 | `new_goal: selected STORE_SURPLUS -> store` |

Reachability is causal, not reordering: person-001's prior store (`evt-13-269`,
food 3→2) is byte-identical in both streams, so at frame-14 person-001 holds
exactly `food: 2` — ineligible at threshold 3, eligible at 2. Arm A's event id
and its goal id (`goal-ab100da754c155f2`) appear nowhere in arm B's stream.

Consistent with the §9 pre-registration: the firing is on the genesis food
endowment, before any agent re-accumulates two units.

Downstream is a genuinely different trajectory — 79 fewer accepted events across
12 types, chaotically amplified from the single fork — **not** a permutation.
Calling it "004 ordering drift" understates it.

## 3. Census delta (B − A)

`living_store` 1→2 (**the causal event**), `living_retrieve` 2→3,
`social_cooperate` 38→55, `social_repay` 35→44, `social_request_help` 135→130,
`living_tend` 215→187, `expire_signal` 707→681, `living_rest` 445→419,
`living_move` 261→243, `living_drink` 20→18, `living_consume` 17→16,
`living_gather` 10→9. No type present in one arm only. Deaths 0 in both. All
eight singleton social actions still fire exactly once each.

## 4. Pre-registered bands — all four PASS

| quantity | band | arm A | arm B |
|---|---|---:|---:|
| accepted events | 4,849 ±3% = 4,704–4,994 | 4,947 | **4,868** |
| deaths | ≤ 1 | 0 | **0** |
| rest fraction | 0.25–0.45 | 0.373636 | **0.368190** (419/1,138) |
| action entropy | ≥ 1.8 bits | 2.485325 | **2.559783 bits** |

Rest fraction and entropy are recomputed offline from `summary.actions_by_type`;
the construction reproduces arm A's recorded `0.373636` and `2.485325` exactly.
Verdict is anchor-invariant (passes against 4,849 and against 4,947).

## 5. Determinism — what is and is not proven

VERIFIED: `repeat_matches: true` (2 runs), `replay_state_hash ==
final_state_hash`, `replay_matches_final_entities: true`.

NOT proven, recorded to prevent over-reading:

- `resume_matches` is **assigned, not measured** — `living_agent_harness.py:659`
  sets it to `repeat_matches` whenever `--resume-at` is passed.
- The "resume" path (`harness:369-372`) is an in-process `copy.deepcopy` plus
  `DeterministicRNG(seed)` re-instantiation. No serialisation, write, or reload
  occurs. Equality proves runtime RNG streams are tick-keyed; it says nothing
  about save/load resumability.
- `replay_state_hash` applies the same `apply_mutation` to the same accepted
  mutations as the forward path, so it is implied by
  `replay_matches_final_entities` plus canonical hashing — not an independent
  signal.

## 6. Not claimed

`social_cooperate` +17 (38→55, +45%) is **not** claimable as a density gain.
CORE-INTEGRITY-004's own paired same-seed experiment moved `social_request_help`
+44% and `social_repay` −39% with zero behavioural change, so social-type
ordering noise reaches ≥44% and this delta sits exactly at it.

The one distributional datum that does point somewhere, recorded without a
claim attached: action entropy moved **+0.0745 bits**, against 004's
**−0.0043 bit** entropy-noise datum — roughly 17×. n=1 each side. Worth a
controlled test, not a result.

## 7. Adversarial review (Kimi Code, 2026-07-28) — verdict RETURN

Independently reproduced: arm A's hash, the two-line functional diff, the
index-284 divergence (by a stronger method — per-event canonical hashes with
`run_id` stripped, agreeing with the original comparison), all four bands, the
determinism values, and the isolation of the second move (§8). Findings
accepted and actioned here: the missing in-repo evidence file (this document),
the stale doctrine in FRONTIER/the leg contract (updated at this commit), the
overstated determinism signals (§5), and the pin's ordering-only blind spot
(closed — see below).

Pin strengthened in the same change set: `test_frozen_baseline_hashes.py` now
also asserts `accepted_event_sequence_hash`, `frame_sequence_hash`, and
`rejected_proposal_count`, closing the ordering-only and rejected-path holes.
Remaining known holes, recorded not fixed: divergence that reconverges before
tick 320; any other scenario, horizon, or seed; and world health generally —
the bands above are checked by hand at ratification time, not by the test.

## 8. Related finding — a second, unratified move is in flight

The uncommitted Leg-2 R1 `REQUEST_HELP` nearest-target retarget (+35/−1 in
`backend/domains/living_settlement_domain.py`) moves the baseline again to
`a2ec907a35ac1e1926cca20ad693169b15bca6d8e05f19d78a0a3ed2c2466a4f` with 5,224
accepted events. Isolated bit-for-bit: `HEAD` plus only that file reproduces it
exactly; the other dirty files contribute zero; stale bytecode, `.env`,
interpreter and untracked test collection are all eliminated. It also takes
`warn` to 0 — the same failure recorded in the 2026-07-27 handoff. That change
needs its own causal diff before it is committed.
