# Capability Stage 8B, Leg 1 — Norm Transmission (individual carriage)

Status: **CONFIRMED with riders (2026-07-20). See "Confirmation and decision log" below
for the exact ruling. Phase D (implementation) is authorised.**

## Disclosure — prior exposure (read before anything else)

Before this contract existed, an untracked, unreferenced 442-line module
(`backend/domains/group_carriage_contracts.py`) was found sitting in the working
tree with no confirmed contract. Per the session's remediation directive it has
been moved out of the repository to
`...\scratchpad\archive_8b_pre-contract\group_carriage_contracts.py.pre-contract-archive`
and was **not** read again, and its contents were **not** used as a source while
drafting this contract's mechanism, schema, or constants. However, honesty requires
recording that **its first 40 lines (module docstring only, no implementation code)
were read once during the initial repo-status triage, before the quarantine
instruction existed.** That docstring described: formation backfill from Stage 7D
`supporter_ids`, a `TRANSMISSION_COUNT`-th-interaction trigger riding the accepted-
action seam (`entity["action"]`/`accepted_event_id`), and `engine_priority = 86`.
Several conclusions below (carriage-only backfill from `supporter_ids`, the
accepted-action seam, priority 86) **independently converge with that docstring**.
Every one of them is re-derived and re-verified below from primary sources — the
probe evidence (this leg's own measurements) and direct greps of
`association_contracts.py`, `group_goal_contracts.py`, and the existing
`engine_priority` ladder, cited by file:line, not from memory of the archived
file. The convergence is unsurprising (it is the same evidence, the same
established commit-ordering pattern, and the same architecture), but it is not
"blind." **If you want a genuinely blind second derivation, say so and this
contract will be redone by a fresh reviewer who never saw the archive.**

## Probe evidence (Phase 1 — persisted, cited by filename)

Seed `living-agents-stage6`, scenario `collective_groups`, read-only, real
committed pipeline. All figures below are VERIFIED, pasted from the persisted
files — not from memory.

- `memory/evidence/stage-8b-leg1/probe_8b_leg1_1000.json` (1,000 ticks)
- `memory/evidence/stage-8b-leg1/probe_8b_carriage_350.json`,
  `probe_8b_carriage_800.json`, `probe_8b_carriage_1000.json` (same script, three
  tick horizons — the 350-tick pass undershot the actual norm-formation ticks
  (683–778), so it was extended twice to the standard 1,000-tick horizon before
  any contract text was written, per invariant 12)

### 1. Overlap probe (mandatory input; reconfirms 8A gate-5's root cause)

REPAIR_SHELTER-candidate windows: `[{1-12},{71},{156},{161-162},{236}]` (17
ticks total, last at 236). Active-norm window: `[{683-1000}]` (318 ticks, single
contiguous window). **Intersection: 0.** Gap: 447 ticks. Identical at both
pre-scoring and post-scoring granularity (no truncation artifact hiding a
near-miss). This is the same disjoint-window cause recorded in 8A gate-5, now
independently reconfirmed for Leg 1's purposes — it governs Tier B of this leg's
organic gate below.

### 2. Membership turnover — zero (matches the protocol's own stop clause)

0 joins, 0 leaves across all 7 tracked norm-holding groups over 1,000 ticks.
**All 7 groups have identical membership: all 8 persons (person-000..007), the
entire population.** This is not "turnover is low" — there is no membership
turnover mechanism firing at all in this scenario, and there is no population
outside any group to begin with. This is a scenario property (closed 8-person
population, 0 lifecycle events — see item 4), not a defect, and it directly
shapes the eligibility-fork decision below: a membership-based fork would have
**zero** organically-producible non-members to transmit to, ever. A
carriage-based fork does not have this problem (see item 5).

### 3. Interactions across the *membership* boundary — zero (expected, not informative)

0, for the reason in item 2 (no non-members exist). This measurement, as
originally specified, answers the wrong question for a carriage-based fork; item
5 below (added for this leg) answers the right one.

### 4. Lifecycle — zero

0 births, 0 deaths across 1,000 ticks. Generational transfer stays **Deferred —
demography-blocked (Stage 11)**, per the continuation prompt's Assumption 7.

### 5. Norm timeline

7 norms form: `group-77ec2beb76de22397715` at tick 683; the other 6 at ticks
777–778 (three at 777, three at 778). Every formation has full 8-member
membership (all of person-000..007). All 7 norms remain `active` through tick
1000 (none reach `decay_deadline_tick = last_adoption_tick + 300 ≈ 1077–1078` —
**no norm expires inside the standard 1,000-tick horizon**, which matters for the
"carriage outlives the norm" acceptance item below: it cannot be measured
organically here either, only via a focused test).

### 6. Carriage/supporter evidence — the central, load-bearing measurement

**22 adoptions observed across all 7 groups, spanning ticks 282–777. Every
single one of the 22 has the identical ratio 7/8, with `person-004` as the sole
non-supporter, zero exceptions.**

**Count reconciliation (added at confirmation, 2026-07-20):** the true count is
22, not 7×3=21. Source, verified against the raw per-row probe data: **one**
group (`group-77ec2beb76de22397715`) adopts **four** times (ticks 282, 376,
682, 776); the other **six** groups adopt exactly **three** times each (ticks
~377/683/777) — `4 + (3×6) = 22`. The norm-formation timeline (item 5, above)
confirms this group forms its norm only **once**, at tick 683 (after its 3rd
adoption, per `NORM_FORMATION_COUNT = 3`); its 4th adoption (tick 776) is a
post-formation re-adoption that refreshes the norm's decay deadline, not a
second formation — consistent with 8A's documented refresh mechanism
(`CAPABILITY-STAGE-8A-EMERGENT-NORMS.md`, "on formation and on each subsequent
counted adoption... `decay_deadline_tick` extended"). This is not a new
asymmetry: it independently **reproduces** 8A's own previously-published
per-group adoption distribution `[4, 3, 3, 3, 3, 3, 3]` at ticks "282 / 376 /
682 / 776" for the top group and "~377 / ~683 / ~777" for the rest
(`CAPABILITY-STAGE-8A-EMERGENT-NORMS.md:165-167`) — the same seed, same
scenario, measured independently by a different probe script two legs apart,
landing on the identical tick sequence. Cross-validation, not coincidence.

Every one of the 22 adoptions was cross-checked against
`want_holders_min=0`/`want_holders_max=7` (of 8 persons) — `person-004`
structurally never holds the `improve_shelter` want that drives support, at any
sampled tick. This is a stable, organic, non-seeded property of that one
person, not an artifact of sampling.

**Carrier/non-carrier interaction evidence** (this is new measurement work added
for this leg, cross-referencing the carriage probe's `social_events` array
against the leg1 probe's formation timeline by hand — the probe script itself
does not compute this): every occurrence of `person-004` (the only
organically-producible non-carrier under a carriage-only fork, in all 7 groups)
in the full 1,000-tick `social_events` array (7 occurrences total):

| tick | etype | actor | target | relative to first formation (683) |
|---|---|---|---|---|
| 8 | social_lie | person-005 | person-004 | pre-formation |
| 11 | social_threaten | person-004 | person-000 | pre-formation |
| 13 | social_apologise | person-005 | person-004 | pre-formation |
| 15 | social_reconcile | person-005 | person-004 | pre-formation |
| 296 | social_request_help | person-004 | person-000 | pre-formation |
| 299 | social_request_help | person-004 | person-000 | pre-formation |
| **699** | **social_request_help** | **person-004** | **person-000** | **post-formation** |

**Exactly one** of these seven crosses a carrier/non-carrier boundary
*after* a norm exists to carry: tick 699, `person-004` (non-carrier) as actor,
`person-000` (carrier of `shelter_upkeep_norm` on `group-77ec2beb76de22397715`
since tick 683) as target, event type `social_request_help`. No further
`person-004` event occurs between tick 700 and tick 1000. **This is the entire
organic evidence base for transmission in this scenario: one event, one
direction, one event type, one norm out of seven.** This shapes every decision
in the next section, and it is thin — flagged explicitly, not smoothed over.

## Contract decisions (recommendation + evidence each — confirm or overturn at the STOP)

### Decision 1 — the eligibility fork: **carriage-only** (confirms the continuation prompt's default)

After this leg, exactly one source of truth grants the norm nudge: carriage, not
current membership. Formation deterministically backfills carriage to the
supporters recorded on the goal that triggered formation (`supporter_ids`, read
from the committed `group-goal-000` registry — confirmed field, see
`group_goal_contracts.py:713`, `"supporter_ids": list(goal.get("supporter_ids")
or [])` on every committed goal record). Members present at formation who did
**not** support are **not** backfilled — they are the organically-produced
non-carriers (item 6: unanimously `person-004`, in every one of 7 groups).
Post-formation joiners are not automatically carriers; they must learn via
transmission (item 2 below).

**Evidence for carriage over membership:** item 2 shows a membership-based fork
has zero organically-producible non-members — the entire population belongs to
every group, permanently. A carriage-based fork has exactly one
organically-producible non-carrier, in every group, unanimously. Carriage is the
only fork with anything to transmit to in this scenario.

**Consequence, stated explicitly (per the continuation prompt's requirement):**
this changes 8A's late-joiner semantics from *implicit coverage* (any current
member is nudged) to *must-learn* (only carriers are nudged; a post-formation
member is not automatically covered). **This semantic change is real and
correct in principle but is organically untestable in the current scenario** —
item 2's own measurement (0 joins in 1,000 ticks) means there is no
post-formation joiner to exercise it on. It will be proven only by a focused
test (a synthetic post-formation joiner, mirroring how 8A itself proved
transmission-to-a-later-joiner in its focused suite before the organic scenario
existed to test it). Flagged as a known gap, not hidden.

### Decision 2 — one transmission mechanism: **imitation (observer/non-carrier-initiated)**, not teaching

**Evidence:** across the entire 1,000-tick horizon, zero carrier-initiated
actions are ever directed at `person-004` after any norm forms. The one
qualifying post-formation event (tick 699) is `person-004` (non-carrier) as
**actor**, `person-000` (carrier) as **target** — non-carrier-initiated. Teaching
(carrier-initiated, directed at a non-carrier) has **zero** organic evidence in
this scenario and is a named non-goal for this leg, per the continuation
prompt's "the other is a named non-goal" instruction. This is not a preference —
it is what the measurement shows and the alternative shows nothing.

### Decision 3 — deterministic trigger: **`TRANSMISSION_COUNT = 1`** (the first qualifying interaction)

**Evidence:** exactly one qualifying carrier/non-carrier interaction exists in
the entire standard 1,000-tick horizon. Any `TRANSMISSION_COUNT ≥ 2` is
**measured, not assumed, to be unreachable** in this scenario — there is no
second event to count. `TRANSMISSION_COUNT = 1` is therefore not a threshold
chosen for convenience; it is the only value at which the mechanism can fire
organically at all, and it is also the honest floor (no lower value exists).

**Named tension, flagged rather than hidden:** 8A's norm-formation mechanism
specifically required *repetition* (`NORM_FORMATION_COUNT = 3`) to model
culture as something that crystallises from recurrence, not a single event.
`TRANSMISSION_COUNT = 1` is philosophically inconsistent with that — "taught on
the very first qualifying contact" is a weaker model of learning than 8A's model
of norm formation. This is scenario-forced, not a considered pedagogical choice,
and it means the acceptance gate's organic proof rests on exactly one measured
event with zero margin: if that one tick-699 event had not fired (e.g. a
one-tick perturbation from any upstream change), Leg 1's organic transmission
gate would be exactly as Deferred as 8A's gate-5. **This is the single biggest
risk in this contract** and is why it is presented at a STOP rather than
implemented straight through.

### Decision 4 — qualifying event type: **`social_request_help` only**

The one demonstrated crossing rides `social_request_help`. Per the "ride one
[event type] that demonstrably fires" instruction (not "any 6C/6D type"), the
trigger is scoped narrowly to this one type — not generalised to `social_*`
broadly, since no other type was ever observed crossing the carrier boundary
post-formation. Widening the type set would be inventing untested behaviour.

**Rider (confirmed 2026-07-20):** the whitelist is implemented as a **data
constant**, `TRANSMISSION_QUALIFYING_EVENT_TYPES = ("social_request_help",)`,
in `group_carriage_contracts.py`'s constants block (alongside
`TRANSMISSION_COUNT`), and the trigger checks membership in that tuple — never
a hardcoded `if etype == "social_request_help"` structural assumption in the
domain logic. Widening the set later (should future probe evidence justify it)
is a one-line constants change plus a contract-amendment note in this doc's
decision log — never a rewrite of the trigger-detection code path.

### Decision 5 — registry: **new `group-carriage-registry-v1`**, not an extension of `group-norm-registry-v1`

**Justification:** carriage records are keyed by **person**, not group — a
structurally different entity axis from `group-norm-registry-v1`'s group-keyed
norm records. Carriage must persist independently of the norm's own lifecycle
(a carrier keeps what they learned even if the norm later decays/expires — no
contract specifies forgetting; see Decision 6). Folding a person-keyed,
independently-lifecycled fact into a group-keyed registry would either violate
8A's frozen schema (touching the Do-Not-Touch list) or require carriage records
to inherit norm compaction/eviction semantics that don't fit their lifecycle.
A new registry is the only option that doesn't touch 8A.

**Size math (LIKELY, not yet measured — no run has exercised this registry):**
existing caps establish the ceiling: `norms` cap = 16
(`group_norm_contracts.py:60`), `members_per_candidate` cap = 8
(`association_contracts.py:78`). A carrier record is bounded by (norm × person)
pairs, so the worst-case ceiling is `16 × 8 = 128`. Observed need in this
scenario: 7 groups × 7 backfilled carriers + up to 1 transmitted carrier = 50
records — `(128-50)/128 = 61%` headroom against a cap of 128, comfortably above
the 20% floor, using the same ceiling-vs.-cap-vs.-observed-need method 8A used
(norms cap 16 vs. 7 observed, 77% headroom on that registry's own byte budget).
**This must be re-measured against actual serialized bytes at Phase D verify,
same as 8A's own capacity numbers were measured only after implementation** —
this section is a pre-implementation projection, labelled as such.

### Decision 6 — decay interaction: carriage is independent of norm decay

A carrier's record has no expiry of its own — it persists once written,
regardless of what later happens to the norm it names (active, weakening, or
expired). This is deliberate: "culture outlives its originators" (this leg's
stated goal) requires carriage to survive at least as long as the norm, and no
contract in this leg specifies a forgetting mechanic (matching the continuation
prompt's explicit note). **This cannot be measured organically** — item 5 shows
no norm reaches its decay deadline inside the 1,000-tick horizon — so it is
proven only by a focused test that advances a norm past expiry and asserts the
carrier record is untouched.

## Mechanism

### Formation backfill

At norm-formation time (the tick the `group_norm` domain commits a
`group_form_norm` "formed" transition), the carriage domain reads the
triggering goal's `supporter_ids` from the (lagged, see Commit ordering)
`group-goal-000` registry and writes one `carrier_record` per supporter, scoped
to that norm, with `source = "formation_backfill"`, `learned_from = None`,
`via_event_id` = the `group_form_norm` event's id, `learned_tick` = the
formation tick.

### Transmission

Each tick, for every active carrier↔norm pair and every living non-carrier
person who is a **current member of that norm's group**, the carriage domain
checks whether that person's own entity `action` field (the existing accepted-
action seam — independently confirmed at `association_contracts.py:212-213`:
`action = entity.get("action"); action.get("accepted_event_id")` — already used
by 7A for identical purposes, not invented here) shows a *committed, this-tick*
`social_request_help` action whose `target_id` is a current carrier of that
norm. On the 1st such qualifying occurrence (`TRANSMISSION_COUNT = 1`, per
Decision 3) for a given (norm, non-carrier) pair, a `carrier_record` is written
for the non-carrier with `source = "transmission"`, `learned_from` = the
carrier's id, `via_event_id` = the qualifying action's `accepted_event_id`,
`learned_tick` = the current tick. Idempotent: a `processed_transmission_keys`
set (mirroring `group_norm`'s `processed_norm_keys` pattern) prevents
re-triggering on the same qualifying event.

### Influence (unchanged guard, new eligibility source)

`_apply_group_norm_influence` (or its Leg-1 successor) changes its eligibility
check from "is `entity_id` a current member of the norm's group" (8A) to "does
`entity_id` hold a `carrier_record` for this norm" (Leg 1). The survival-
dominance guard, the read-only nudge, the `NORM_REPAIR_INCREMENT` magnitude, and
the "never creates a candidate a member lacks" rule are **unchanged from 8A** —
this leg changes *who is eligible*, never *what the nudge does*.

## Commit ordering

`group_carriage` runs at **`engine_priority = 86`** — one below `group_norm`
(87), independently derived from the established, mechanically-repeated pattern
at each existing layer (association 90 → group_state 89 → group_goal 88 →
group_norm 87, each new consumer sitting exactly one below what it reads;
confirmed via direct grep of each domain file's own `engine_priority` line, not
from the archived module). It pins `group-goal-000` (88) and `group-norm-000`
(87) — both **higher** priority numbers, both therefore evaluated *after*
`group_carriage` in the same tick's commit cascade, so `group_carriage` sees
their state as of the end of the *previous* tick (the same one-tick-lag
discipline as 8A: a norm formed at tick T is backfilled at T+1; a goal's
`supporter_ids` update at T is visible to carriage at T+1). It also reads each
person entity's `action` field — `living_agent_social`/`living_agent_actions`
commit at **priority 10** (confirmed:
`living_agent_social.py:521`, `living_agent_actions.py:541`), well *below* 86,
so those commits happen *earlier* in the same tick's cascade and
`group_carriage` sees **this tick's** just-committed social actions with **no
lag** — this is why the transmission trigger can fire same-tick rather than
one-tick-delayed. Both lags (and the one no-lag case) are documented, not
incidental.

## Validation (re-derivation + byte-equality, mirroring 8A)

`validate_group_carriage_proposal` re-derives the full backfill+transmission set
from the current canonical frame (committed `group-norm-000`, `group-goal-000`,
and person `action` fields) and requires exact byte-equality with the proposal's
metadata — rejecting forged `carrier_id`, `learned_from`, `via_event_id`,
`learned_tick`, or `source`. Forbidden fields (`inventory, authority, obedience,
orders, law, command, punishment`) absent from every carrier record (tested).
One carrier record per (norm_id, person_id) pair, idempotent by
`processed_transmission_keys`.

## Proposed contracts

| Item | Value |
|---|---|
| Proposal type | `group_carry_norm` (formation-backfill batch + transmission events in one registry update) |
| Proposal family | `group_carriage` |
| Carrier schema | `group-carriage-v1` |
| Domain | `group_carriage` (proposal-only; `engine_priority = 86`, before `group_norm` 87) |
| Registry | new `group-carriage-registry-v1` (`group-carriage-000`), created lazily on first formation |
| Influence | eligibility source changed from membership to carriage in `_apply_group_norm_influence`; guard/magnitude unchanged |
| Scenario | reuse `collective_groups` (+ `group_carriage` domain), no new seeding |

## Constants (each justified from the probe evidence above)

| Constant | Value | Justification |
|---|---|---|
| `TRANSMISSION_COUNT` | **1** | Exactly one qualifying carrier/non-carrier interaction exists in the standard 1,000-tick horizon (Decision 3); the only reachable value, measured not assumed. |
| `TRANSMISSION_QUALIFYING_EVENT_TYPES` | **`("social_request_help",)`** — a data constant (tuple), not a structural code assumption | The only event type ever observed crossing the carrier/non-carrier boundary post-formation (Decision 4); extension is a constants change, per the confirmed rider. |
| Transmission direction | **non-carrier-initiated (imitation)** | Zero carrier-initiated events toward the non-carrier were observed post-formation; the one qualifying event is non-carrier-initiated (Decision 2). |
| `carriers` registry cap | **128** | `norms` cap (16) × `members_per_candidate` cap (8); observed need 50, 61% headroom. |
| `processed_transmission_keys` cap | **96** | Mirrors `group_norm`'s `processed_norm_keys` cap exactly (same idempotence-guard role, same order of magnitude). |
| `engine_priority` | **86** | One below `group_norm` (87), continuing the established ladder; documented one-tick lag on `group-goal-000`/`group-norm-000`, no lag on person `action` reads (priority 10). |
| registry `payload_target_bytes` / `proposal_bytes` | **24 KiB / 32 KiB** | Mirrors `group_norm`'s own budget (comparable record complexity and count order of magnitude); to be re-measured against actual bytes at Phase D verify. |

## Registry schema (`group-carriage-registry-v1`)

```
{ "type": "group_carriage_registry", "schema_version": "group-carriage-registry-v1",
  "revision": int,
  "carriers": { "{norm_id}:{person_id}": carrier_record },
  "processed_transmission_keys": [bounded to 96],
  "created_tick": int, "last_updated_tick": int }
```
`carrier_record`: `schema_version, carrier_id, norm_id, group_id, person_id,
source ("formation_backfill"|"transmission"), learned_from (person_id|None),
via_event_id, learned_tick, revision, created_event_id, last_event_id`.

## Explicit non-goals (this leg)

Teaching (carrier-initiated transmission) — zero organic evidence, named
non-goal per Decision 2. Forgetting / carriage expiry — no contract specifies
it (Decision 6). Generational transfer — Deferred, demography-blocked (item 4).
Multiple transmission mechanisms. Multiple norm types (8C). Values, taboos,
myths, rituals. Cross-group diffusion (8D). Any economy, institution, voting,
or player-facing surface. Widening the qualifying-event-type set beyond
`social_request_help` (Decision 4) — that would be inventing untested behaviour.

## Acceptance gate (two tiers — stated up front, per invariant 12, not discovered at verify)

**Tier A — reachable, evidenced, required:**

1. Focused `group_carriage` tests: formation-backfill correctness (7/8
   supporters become carriers per group, `person-004` excluded, for all 7
   groups); eligibility-source exclusivity (carriage, never membership, tested
   both ways); transmission fires at exactly `TRANSMISSION_COUNT = 1` (not
   before — there is no "before" to test against since N=1, but test that a
   non-qualifying event type or wrong-direction event does *not* trigger);
   provenance correctness (`learned_from`/`via_event_id`/`learned_tick` exact);
   decay-independence (carrier survives a synthetic norm expiry — focused only,
   per item 5); forged-field rejection (re-derivation + byte-equality);
   duplicate-key idempotence; capacity bound; replay + resume reconstruction.
   **Required (confirmed rider, 2026-07-20): a deterministic synthetic-fixture
   test** that constructs a carrier and a non-carrier directly (not via the
   organic scenario), injects one qualifying `social_request_help` interaction
   between them, and asserts the transmission machinery (trigger detection,
   `carrier_record` write, provenance, idempotence) fires correctly —
   independent of whether the organic tick-699 event exists at all. This is
   the actual proof of mechanism correctness; item 5's organic run below is
   rescoped to test **scenario integration only** (does the real pipeline
   reach and exercise this machinery), not mechanism correctness in isolation.
2. **Integrated full-kernel test:** `group_carriage` enabled in the real commit
   pipeline, backfill and transmission proven end-to-end **through same-frame
   upstream (7A/7B/7D/8A) revision churn**.
3. **Regression:** full backend suite stays green per the reporting rule.
4. **Determinism:** `collective_groups` repeat + replay + resume match with
   `group_carriage` enabled.
5. **Organic proof — scenario integration only** (mechanism correctness is
   proven by item 1's synthetic fixture, per the confirmed rider): the unseeded
   1,000-tick `collective_groups` run backfills carriage for all 7 formations
   (49 records, `person-004` excluded from all 7 — already measured, Decision
   1) **and** shows **exactly the one** measured transmission event (tick 699,
   `person-004` learns `shelter_upkeep_norm` on `group-77ec2beb76de22397715`
   from `person-000`) fire through the real pipeline, with 0 deaths, survival
   dominant. This item confirms the real commit pipeline *reaches* the
   machinery under organic conditions; it is not the correctness proof.
6. **Registry size measurement (confirmed rider, 2026-07-20):** the first
   Phase D run that exercises `group-carriage-registry-v1` (integrated test or
   the organic run, whichever first writes carrier records) records the
   measured peak serialized size and record count in the verification report,
   against the 128-record / 24 KiB projection in Decision 5 — same
   measure-against-cap discipline 8A used, not skipped because the estimate
   looks reasonable on paper.
7. **Frozen-hash safety:** `living_settlement` 320-tick hash unchanged
   (`84d3ad52…c32d2` — `group_carriage` absent/inert there, same guard as every
   prior culture domain). New `collective_groups` hashes recorded (this domain
   WILL change them — a new domain enters the pipeline).
8. **Adversarial review before promoting status** (Codex or equivalent,
   independence level recorded honestly) against the branch diff.

**Tier B — Deferred up front, scenario-dynamics-blocked, full required record (taxonomy: `CAPABILITY_ROADMAP.md` § Deferral taxonomy):**

- **(a) Blocking measurement.** "Verifiably influenced on the new carrier"
  (the acceptance item's own phrase, continuation prompt line 121) requires a
  `REPAIR_SHELTER` candidate to exist for `person-004` at or after tick 699 (the
  only transmission event). The overlap probe (item 1, this doc) measures
  `REPAIR_SHELTER` candidates existing **only** on ticks 1–236, all of them
  *before* any norm exists (first formation at 683) and therefore before
  transmission is even possible. No tick from 699 through 1000 has a
  `REPAIR_SHELTER` candidate for anyone. This is identically the disjoint-window
  cause recorded in 8A's gate-5 — not a new defect, the same one, one hop
  further down the causal chain.
- **(b) Unblock condition — RULED (2026-07-20): purpose-built scenario.** The
  standing-scenario decision the continuation prompt flagged at the Leg 1 Phase
  1 STOP (line 104) is resolved as follows, superseding the three-option
  presentation above (kept for the record of what was considered):
  - **Extend-horizon: rejected.** 764 post-window ticks (237–1000, past the
    last `REPAIR_SHELTER` candidate at 236) show **zero** recurrence at the
    standard 1,000-tick horizon — the overlap probe (item 1) already measured
    this; more ticks of the same dynamics would not produce a different
    result.
  - **Authorised dynamics change: rejected.** An era-level re-baseline (the
    frozen `living_settlement` hash, and every downstream hash built on it)
    is a disproportionate cost for a leg-level gate, and it would split
    verification onto two incomparable baselines going forward.
  - **Purpose-built scenario: RULED.** A new scenario, built as the **first
    contract-gated work item after Leg 1 closes**, scoped to exactly two named
    outcomes: (1) retire 8A's gate-5 and this leg's Tier B in **one
    consolidated verification pass** (both are the identical disjoint-window
    cause; one fix answers both), and (2) provide organic-gate substrate for
    remaining legs (8C, 8D). One scenario, these two named gates, no general
    framework beyond what those two require.
  - **Consequence for this leg:** Phase D proceeds **now**, under the existing
    Tier B deferral — implementation does not block on the scenario work.
    Leg 2's (8C's) contract is written against the new scenario once it
    exists; **no third scenario-dynamics-blocked deferral accrues** past this
    point — if 8C's own organic gate would otherwise need one, that is a
    signal the new scenario's scope was wrong, not a reason to defer again.
- **(c) No threshold was lowered.** `TRANSMISSION_COUNT = 1` is the measured
  floor (Decision 3), not a lowering to manufacture a firing — the opposite
  direction of adjustment would be needed to reach Tier B and none was made.
- **Also Deferred (Tier B, separate item):** the late-joiner-must-learn
  semantic change (Decision 1's consequence) is organically untestable — 0
  membership joins occur in 1,000 ticks (item 2). Proven by focused test only,
  named explicitly rather than silently substituted for organic proof.

## Risks (stated plainly)

1. **Single point of failure.** The entire Tier A organic proof rests on one
   measured event (tick 699). This contract does not — and structurally cannot
   — provide a distribution or margin around `TRANSMISSION_COUNT`. If this is
   judged too thin to build on, the correct move is to resolve the standing
   scenario decision (Tier B's unblock condition) before implementing, not to
   implement against a single data point and hope.
2. **Prior exposure**, disclosed above — a partial, non-implementation read of
   the archived module happened before quarantine was ordered, and several
   conclusions here converge with it. Flagged for your judgment, not hidden.
3. **Registry size projection is unmeasured** (Decision 5) — real bytes come
   only from Phase D implementation and running the harness; the 128 cap and
   24 KiB target are principled but not yet verified.
4. **Hash consequence.** Enabling `group_carriage` will change `collective_groups`
   hashes (new domain, new registry, new one-tick-lag reads) — expected, to be
   recorded fresh at Phase D verify, not treated as a regression.
5. **Philosophical inconsistency**, named in Decision 3: `TRANSMISSION_COUNT=1`
   models transmission as instantaneous while 8A modelled norm formation as
   requiring repetition. This is scenario-forced, not a considered choice.

## Confirmation and decision log

**2026-07-20 — CONFIRMED with riders.** All five contract decisions (eligibility
fork carriage-only, mechanism imitation-only, `TRANSMISSION_COUNT = 1`, event
type `social_request_help` only, new registry separate from 8A's) confirmed as
recommended. Riders applied and folded into the relevant sections above:

- Rider (a): the event-type whitelist is a data constant
  (`TRANSMISSION_QUALIFYING_EVENT_TYPES`), not a structural code assumption —
  see Decision 4 and the Constants table.
- Rider (b): a deterministic synthetic-fixture test is required in Tier A,
  independent of the organic tick-699 event; the organic-proof gate item is
  rescoped to integration-only — see Tier A items 1 and 5.
- Rider (c): the first Phase D run to exercise the carriage registry must
  record measured size against the 128-record / 24 KiB projection in the
  verification report — see Tier A item 6.
- Adoption count reconciled: true count is 22 (4 + 3×6, not 7×3), sourced and
  cross-validated against 8A's own published distribution — see the probe
  evidence section, item 6.
- Standing scenario decision RULED: purpose-built scenario, scoped to retiring
  8A gate-5 and this leg's Tier B together plus providing organic-gate
  substrate for remaining legs; built as the first contract-gated item after
  this leg closes; Phase D does not block on it — see Tier B, item (b).
- Docstring-exposure disclosure (top of this doc) is accepted **permanently** —
  it stays in this document; it is not to be trimmed in a later edit.
  **Phase D's post-implementation archive diff (step 13 of the original
  five-phase directive) must explicitly call out any divergence in the three
  areas where this contract's independent derivation converged with the
  archived module's docstring: carriage-only formation backfill, the
  `entity["action"]`/`accepted_event_id` seam, and `engine_priority = 86`.**
  Convergence in the diff is expected and not itself a finding; the report
  must say so explicitly rather than passing over those three areas silently.
- Phase D authorised: fresh implementation from this confirmed contract,
  test-first, no archive consultation during implementation; the archive is a
  post-hoc diff cross-check only, after Tier A's own acceptance criteria pass;
  the contract — never the archive — resolves any divergence found. STOP at
  Leg 1 close-out with the standard report.

## What this contract does NOT authorise

Any deviation from the confirmed decisions and riders above without a new,
recorded confirmation. Any consultation of the archived module during
implementation (post-hoc diff only, per the log above). Any scenario-dynamics
work beyond this leg's scope — that is explicitly parked as the first
contract-gated item after this leg closes, not folded into Phase D.
