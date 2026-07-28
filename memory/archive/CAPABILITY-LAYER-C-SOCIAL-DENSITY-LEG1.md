# Layer C, Social Density Leg 1 — Shared-Storage Intent

**Status: CONFIRMED 2026-07-27 — IMPLEMENTING (Tier A complete; frozen-hash
ruling RATIFIED 2026-07-28; organic gate, second seed and disabled control NOT
yet done).**

The threshold-only mechanism in §6 was confirmed by the user with the §9
store-provenance amendment. Implemented so far:

- `backend/core/constants.py` — new `STORE_SURPLUS_MIN_FOOD = 2` with the
  measured citation.
- `backend/domains/living_settlement_domain.py` — the inline
  `resources.get("food", 0) >= 3` at the STORE_SURPLUS gate now reads the
  constant. Import added. Nothing else changed.
- `backend/tests/test_layer_c_social_density.py` — new, 21 tests, all passing;
  covers the §9 Tier A items including commit-through-pipeline, the keep-one
  guarantee, survival dominance (C-6) and repeat determinism.

**Frozen-hash ruling: RATIFIED 2026-07-28, explicitly accepted by the user.**
`living_settlement@320` moved `9c1b9b8b…46e55d4` → `4240d6a0…305de1bb`. The
STOP write-up — causal diff (single divergence at index 284, frame-14, the
authorised STORE_SURPLUS firing), census delta, all four pre-registered bands
passing, and the adversarial review — is
`memory/evidence/frozen-hash/2d68ac16-LIVING-SETTLEMENT-320-RATIFICATION.md`.
The suite now pins that baseline literally
(`backend/tests/test_frozen_baseline_hashes.py`), so §291's requirement is met
by an executable check rather than by documentation alone.

**Still outstanding, and gated:** the organic 5,000-tick `collective_groups`
gate, the second-seed `living-agents-stage6-alt` repeat, and the paired
threshold-3 disabled control. `collective_groups`' own post-`2d68ac16` hash
status is UNKNOWN — not measured. Any FURTHER moved baseline hash remains
UNAUTHORISED until a STOP presents the exact causal diff. Repeat/replay
equality alone is still NOT evidence that a baseline held.

Frontier: `FRONTIER.md` — Layer C (Individual Agency), Social Density Leg 1.

## 1. Goal

Make the existing `STORE_SURPLUS` intent organically reachable in
`collective_groups` so at least two distinct agents can use shared storage and
produce the existing `shared_storage` association evidence, without creating
resources, weakening survival dominance, widening Stage 7/8 schemas, or
changing the Stage 7C collective mechanism.

Impossible today:

> Agents see shared storage, but never carry the three food units required to
> generate `STORE_SURPLUS`. No store candidate exists, so scoring, planning,
> execution, association evidence, and collective storage never get a turn.

This is an extension of an existing organic decision/action path. Invariant
12(v2) therefore requires committed-baseline measurement before the contract;
that measurement is complete below.

## 2. Provenance and evidence

- Checkout: `C:\dev\simulation-sandbox\simulation-sandbox`
- Branch: `capability/stage-8c-phase1-aid-exchange`
- Probe-start HEAD: `180c43f4640e06aa1f9a891397e46126c6a0f575`
- Scenario: `collective_groups`
- Seed: `living-agents-stage6`
- Control horizon: one continuous 5,000-tick run, sampled cumulatively at
  1,000 / 3,000 / 5,000 as required by `FRONTIER.md`
- Probe: `backend/tools/_probe_layer_c_social_density.py`
- Control evidence:
  `memory/evidence/layer-c-social-density-leg1/baseline_collective_groups_5000.json`
- Threshold-2 read-only shadow evidence:
  `memory/evidence/layer-c-social-density-leg1/shadow_food_threshold_2_collective_groups_40.json`
- Matching 40-tick no-shadow control:
  `memory/evidence/layer-c-social-density-leg1/control_collective_groups_40.json`

The probe executes the real kernel and tallies live decision diagnostics,
accepted events, and rejected proposals without retaining the accepted-event
stream. It replays each accepted mutation immediately and reports exact replay
equality at every checkpoint. The shadow candidate is scored for comparison
only; it is never inserted into a domain output or committed.

## 3. Organic-reachability result

| Tick | Decision opportunities | Shared storage visible | Carried food `0 / 1 / 2` | Food `>=3` | `STORE_SURPLUS` candidates | Storage actions | Goals / norms | Deaths | Entropy (bits) | State hash |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| 1,000 | 8,000 | 7,110 | 7,394 / 542 / 64 | **0** | **0** | retrieve 1, store 0 | 0 / 0 | 0 | 2.350245 | `03312018977e518227652d4929afb643bdc6db3fc99f7a7a5ee4e055754488a6` |
| 3,000 | 24,000 | 21,207 | 22,714 / 1,222 / 64 | **0** | **0** | retrieve 1, store 0 | 0 / 0 | 0 | 2.322166 | `fb032eaf6fa5041cea73e6172943ce31203809c1c3dab90b893aba8025597d7a` |
| 5,000 | 37,521 | 33,683 | 35,878 / 1,579 / 64 | **0** | **0** | retrieve 1, store 0 | 0 / 0 | 2 | 2.352938 | `9177ad0c4c4db74fbbc4489367876d3de674448a877a8ad372981cea021ad5e8` |

All three checkpoints report `replay_matches_entities: true`. The lower
decision count at 5,000 is real: two agents die between ticks 3,000 and 5,000.
Therefore zero deaths is not a valid 5,000-tick control expectation.

Additional facts:

- `food == 2` occurs 64 times by tick 1,000 and never again. Food never reaches
  3 in the entire 5,000-tick trajectory.
- Shared storage is visible on 89.8% of decision opportunities at tick 5,000
  (`33,683 / 37,521`). Perception is not the binding gate.
- `storage-camp` remains `{food: 0, wood: 12}` after its one genesis food unit
  is retrieved. No resource is deposited and no collective processed key lands.
- Recognised groups exist (17 at tick 5,000) and shared facts exist, but all
  retained facts are `shared_shelter`; no `shared_storage` fact forms.
- Group goals and group norms remain zero at all checkpoints. This predates
  the current leg and is recorded as a secondary trajectory observation, not
  a Stage 8 repair target.
- `cooperate` is materially active (1,377 actions by tick 5,000), so the
  deferred delivered-energy gradient remains a real lower-ranked Layer C
  pressure. It is not causal to the missing store candidate.

### Causal classification

**A — prerequisite reachability: VERIFIED.** `food >= 3` is the earliest
failing seam. Because no candidate is generated, the control run contains no
evidence for either B (candidate loses scoring) or C (selected candidate fails
to execute). Those downstream hypotheses are not blamed.

## 4. Threshold-2 shadow result

The current scenario intentionally starts two storage-adjacent people with two
food units each. A read-only shadow candidate using the existing score and the
existing target/action metadata measured the full early food-2 window:

| Measurement | Result |
|---|---:|
| storage-visible, food `>=2` opportunities | 56 |
| actors with opportunities | 2 (`person-000`: 17, `person-001`: 39) |
| shadow candidate would win | 31 |
| distinct would-win actors | 2 (`person-000`: 12, `person-001`: 19) |
| shadow score range / median | 13,816–14,080 / 13,872 |
| actual candidate-list size range / max | 1–5 / 5 (cap is 16) |

The other 25 decisions retain their actual winner under the normal tie-break;
these include active survival and social-help decisions. A score increase is
therefore neither necessary nor supported. Adding the existing storage
candidate would leave at least ten slots below the candidate cap throughout
the measured window.

The 40-tick shadow and no-shadow controls have the identical final hash
`95ce1ac893bcf8ff66fcdf0567ed4f0d6c6f9a5595df199c2fb72de37c0b3fab`
and both replay exactly. The observer is behaviour-neutral.

Historical caution remains valid: an older 40-tick `emergent_groups`
experiment combined threshold 2 with a score increase to 1,650 and produced no
organic gain. That different scenario/build is not current causal evidence,
but it is why this contract changes one variable only and retains an explicit
rollback gate.

## 5. Candidate ranking (Capability Doctrine)

| Rank | Candidate | Measured pressure / connections / emergence | Concrete cost | Ruling |
|---:|---|---|---|---|
| 1 | **Make existing shared-storage intent reserve-aware** | Relieves the verified F8 storage dead path; connects living decision → physical action → association → shared group state; can unlock repeated storage and the existing collective path | 2 production files, 1 named constant, 0 registries, 0 schemas, 0 config | **PROPOSED** |
| 2 | Charge cooperation only for energy actually delivered | Relieves the measured clamp-loss gradient; `cooperate` fires 1,377 times at 5,000 ticks | separate re-baseline-class social-action semantics change; does not unblock storage | Defer to its own leg |
| 3 | General goal-precedence/scoring contract | Addresses the verified `REPAY_DEBT > WARN_DANGER` smell and other competition policy | wider multi-goal policy surface, new doctrine/fixtures, high trajectory sensitivity | Defer; separate contract |
| 4 | Accept or retire organically dead Stage 7C | Documentation or destructive removal only; delivers no new world capability | concedes or removes a tested mechanism before the measured lower seam is tried | Reject for this leg |

Roadmap position contributes no score. Candidate 1 ranks first because it
relieves the active measured pressure through existing subsystems with no new
registry, schema, event family, or configuration surface.

## 6. Proposed mechanism — threshold only

If this contract is confirmed:

1. Add one named constant, `STORE_SURPLUS_MIN_FOOD = 2`, beside the other
   living-agent behavioural constants in `backend/core/constants.py`, with a
   one-line citation to this probe distribution.
2. Replace only the inline `resources.get("food", 0) >= 3` eligibility check in
   `build_settlement_candidates` with that constant.
3. Keep all of the following byte-for-byte unchanged:
   - goal/action names: `STORE_SURPLUS` / `store`;
   - base score: `1350`;
   - candidate insertion order and deterministic tie-break;
   - storage target selection;
   - transfer quantity: one food unit;
   - planner, movement, executor, validators, preconditions, conservation;
   - association evidence window and `shared_storage` rule;
   - Stage 7C collective derivation;
   - group goal/norm influence;
   - scenario genesis.

At proposal time, an eligible actor has at least two food units. An accepted
one-unit store therefore leaves at least one unit; contention still fails
closed through the existing resource preconditions. This does not create
material surplus or satisfy Layer F-A by assertion. It only lets agents place
an already-owned unit into existing shared storage when the unchanged scoring
system selects that intent.

No score calibration is authorised by this contract. If the threshold-only
build does not pass the organic gate, roll it back and STOP for a new contract
rather than raising the score or widening scope.

## 7. Ownership and ordering

| Surface | Existing owner/path | Change | Risk control |
|---|---|---|---|
| Candidate eligibility | `living_settlement_domain` reads pinned perception and carried resources | one threshold constant | exact boundary fixtures; no canonical write |
| Person food / storage contents | existing physical-action proposal, Core validator and commit pipeline | none | conservation, access, capacity and stale-precondition tests remain authoritative |
| Current action / decision receipt | existing living-agent reasoning/action path | none | accepted causal-chain proof |
| `shared_storage` association evidence | existing association domain reads committed current actions | none | organic downstream assertion, no direct seeding |
| Shared group state / collective deposit | existing Stage 7B/7C domains | none | record outcomes; no schema/cap changes |

No phase, priority, writer, event family, registry, schema version, payload cap,
or replay handler changes. Candidate lists were at most five entries in every
shadow opportunity; adding one remains below the cap of 16, but a focused test
will still protect later critical candidates from accidental truncation.

## 8. Implementation boundary

Expected production/test files only:

- `backend/core/constants.py`
- `backend/domains/living_settlement_domain.py`
- `backend/tests/test_layer_c_social_density.py` (new focused tests)

Probe/evidence/status documentation may be updated in the same eventual commit
series. No dependency, UI, scenario, API, persistence, Stage 7/8 schema,
economy, lifecycle, RNG, time, or CORE-INTEGRITY-004 work belongs in this leg.

## 9. Pre-registered acceptance gate

### Tier A — deterministic mechanism

1. Shared storage visible + food 1: no `STORE_SURPLUS` candidate.
2. Shared storage visible + food 2: exactly one existing candidate; food 3
   remains eligible.
3. Private/invisible storage: no candidate at either inventory level.
4. With idle competitors, unchanged scoring can select `STORE_SURPLUS`; an
   active survival candidate still wins.
5. Candidate activation does not truncate `WARN_DANGER` or other later
   required vocabulary; the cap stays unchanged.
6. Accepted store transfers exactly one unit, conserves total food, and leaves
   the actor with at least one unit in the boundary fixture.
7. Same-frame resource contention rejects without partial mutation; replay of
   an accepted store is byte-exact.

### Organic behaviour

Run `collective_groups`, seed `living-agents-stage6`, for 5,000 ticks with the
same 1,000 / 3,000 / 5,000 checkpoints and the same census:

- at least two distinct actors commit `store` to shared `storage-camp`;
- at least one `shared_storage` association fact forms organically;
- every accepted transfer conserves resources and has an inspectable causal
  chain from decision receipt through accepted event and storage mutation;
- zero deaths at 1,000 and 3,000, and no more than the control's two deaths at
  5,000;
- replay equality at every checkpoint;
- group-goal, norm, Stage 7C, action-distribution, entropy, and storage-content
  outcomes are reported, but no single-run percentage delta is used as proof.

#### Amendment (confirmed with the contract, 2026-07-27): store provenance

The control measured `carried_food_histogram_at_decision` as `{'0': 7394,
'1': 542, '2': 64}` at 1,000 ticks and `{'0': 35878, '1': 1579, '2': 64}` at
5,000. The `2` bucket is **frozen at 64 across all three checkpoints**: every
food-2 observation in the trajectory occurs before tick 1,000, and food never
reaches 2 again in the following 4,000 ticks. The `1` bucket meanwhile keeps
growing (542 → 1,222 → 1,579), so agents do keep acquiring food — they simply
never hold two units at once again.

Threshold 2 therefore has a **hard behavioural ceiling: it can only fire on the
genesis food endowment, inside the first ~1,000 ticks.** Nothing in the current
world replenishes an actor to two units, which is the Layer F-A material-surplus
gap `THE-SPINE.md` §4 already names. This is a scope fact, not a defect: the
leg's goal is organic *reachability* of an intent measured dead, not sustained
storage traffic.

Two consequences are therefore pre-registered:

1. **The organic gate must report the tick index of every committed `store`,**
   and report separately how many stores were sourced from genesis-endowment
   food versus post-genesis acquisition. A gate that passes purely on
   early-window genesis stores still passes — but it must say so plainly, so
   the result is never read as "storage is now a living behaviour."
2. **Satisfying this gate does NOT by itself satisfy the Stage 7C re-entry
   condition.** `THE-SPINE.md` §8 words that condition as "≥2 distinct agents
   perform storage actions on a shared storage organically", which a one-shot
   genesis-food event would satisfy literally. Unblocking 7C is a hard rail
   (Stage 9 boundary). This contract therefore **defaults closed**: 7C stays
   DEFERRED regardless of this gate's outcome, and whether genesis-endowment
   stores count — or whether the re-entry condition should be tightened to
   require post-genesis food — is an explicit ruling for the user at the gate
   STOP. No implementer may resolve it by reading the condition literally.

For robustness, repeat the categorical reachability gate at 1,000 ticks on
`living-agents-stage6-alt`. Compare it with a threshold-3 disabled control on
the same implementation build. Failure on either seed blocks acceptance.

### Regression and determinism

- focused Layer C tests;
- existing Stage 6C storage and Stage 7C collective suites;
- full executed regression suite, with environment exclusions reported
  separately and honestly;
- `collective_groups` 1,000-tick repeat 2 + replay + resume equality;
- `living_settlement` 320-tick repeat 2 + replay + resume equality;
- exact old/new action-count and causal diff for every regression hash that
  moves.

The current regression tripwires are `03312018…488a6` (`collective_groups`
1,000) and — as of the 2026-07-28 ratification — `4240d6a0…305de1bb`
(`living_settlement` 320, superseding `9c1b9b8b…46e55d4`). This behaviour change
is re-baseline-class. Any moved hash remains **unauthorised** until a later STOP
presents the exact causal diff and the user explicitly accepts it. That ruling
has been given for `living_settlement@320` only
(`memory/evidence/frozen-hash/2d68ac16-LIVING-SETTLEMENT-320-RATIFICATION.md`);
`collective_groups`' 1,000-tick hash has not been re-measured since `2d68ac16`
and its status is UNKNOWN. The build must not be committed as complete before
the remaining gates close.

CORE-INTEGRITY-004 makes single-run A/B action-count magnitudes unreliable.
Acceptance therefore rests on categorical causal events, two fixed seeds,
paired disabled controls, checkpoint health bounds, and exact deterministic
equality—not on claiming that a percentage delta is precise.

## 10. Rollback and risks

- **Threshold 2 may select but not commit.** The organic gate covers movement,
  stale preconditions, final store events, and downstream facts. Failure means
  rollback and re-contract, not score tuning.
- **Candidate starvation.** Shadow lists peak at five versus cap 16; a focused
  required-vocabulary fixture still protects the risk.
- **Survival/resource risk.** Score is unchanged and survival dominance is
  fixture-proven; accepted stores keep one food and conserve totals. The
  long-run death bound prevents laundering starvation into social density.
- **Material-surplus boundary.** No food is created and Layer F-A remains
  deferred. This leg cannot reopen Aid Exchange by documentation claim.
- **Trajectory/hash churn.** Expected and separately gated. No baseline moves
  without explicit user authorisation.
- **Zero goals/norms.** Recorded but not repaired here; widening into Stage 8
  would be a second subsystem and violates the leg boundary.
- **Cooperation gradient and general score policy.** Measured and ranked, but
  deliberately not bundled.

## 11. Contract STOP

**Requested ruling:** confirm or reject the threshold-only mechanism and gate.

Until confirmed, `STORE_SURPLUS_MIN_FOOD` does not exist, the live threshold
remains 3, and no production behaviour is authorised.
