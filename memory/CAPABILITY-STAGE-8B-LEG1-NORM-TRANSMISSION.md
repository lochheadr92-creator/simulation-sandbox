# Capability Stage 8B, Leg 1 — Norm Transmission (individual carriage)

Status: **PROPOSED — reopened (2026-07-20).** The five contract decisions,
their riders, and the standing-scenario ruling recorded in "Confirmation and
decision log" below were confirmed and remain confirmed — they are not in
question. What is open: a classification judgment call raised by a Phase D
verification finding (see "Phase D verification finding" below) — enabling
`group_carriage` measurably shifts an unrelated pair of persons' interaction
by one tick, through a mechanism unrelated to this leg's own sanctioned
influence hook. Two readings are presented with a recommendation; **this is a
STOP, not a closed finding — implementation code exists in the working tree,
untouched since being written, but Phase D's remaining steps (adversarial
review, commit, close-out) are paused until this is ruled on.**

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
by 7A for identical purposes, not invented here), **as visible in the frame
frozen at the end of the previous tick** (see Commit ordering — no domain sees
same-tick data, regardless of priority), shows a committed
`social_request_help` action whose `target_id` is a current carrier of that
norm. On the 1st such qualifying occurrence (`TRANSMISSION_COUNT = 1`, per
Decision 3) for a given (norm, non-carrier) pair, a `carrier_record` is written
for the non-carrier with `source = "transmission"`, `learned_from` = the
carrier's id, `via_event_id` = the qualifying action's `accepted_event_id`,
`learned_tick` = the current (carriage-domain-evaluation) tick — one tick after
the qualifying action's own accepted tick, per the corrected Commit ordering
section. Idempotent: a `processed_transmission_keys` set (mirroring
`group_norm`'s `processed_norm_keys` pattern) prevents re-triggering on the
same qualifying event.

### Influence (unchanged guard, new eligibility source)

`_apply_group_norm_influence` (or its Leg-1 successor) changes its eligibility
check from "is `entity_id` a current member of the norm's group" (8A) to "does
`entity_id` hold a `carrier_record` for this norm" (Leg 1). The survival-
dominance guard, the read-only nudge, the `NORM_REPAIR_INCREMENT` magnitude, and
the "never creates a candidate a member lacks" rule are **unchanged from 8A** —
this leg changes *who is eligible*, never *what the nudge does*.

## Commit ordering

**Correction made during Phase D prep (2026-07-20), before any code was
written** — the paragraph below replaces an incorrect claim in the originally
confirmed contract. The original text asserted `group_carriage` would see
*this-tick's* social actions with "no lag" because `living_agent_social` commits
at a lower `engine_priority` (10) than `group_carriage`'s proposed 86. That
claim was **wrong**, caught by reading `core/kernel.py` and
`core/commit_pipeline.py` directly rather than trusting the pattern-extrapolation
that produced it. It does not change any of the five confirmed decisions,
`TRANSMISSION_COUNT`, the event type, or the mechanism — it corrects a
commit-tick arithmetic detail and a mischaracterisation of what `engine_priority`
governs. Recorded here rather than silently fixed, per the same disclosure
standard as the rest of this document.

**What `engine_priority` actually governs (verified,
`core/kernel.py:72-91` + `core/commit_pipeline.py:317-331`):** every domain's
`activate()` call for tick T reads from **one single `entities_view`**, deep-copied
**once** at the start of `run_tick`, from `entities` as they stood at the end of
tick T−1 (`kernel.py:73`: `entities_view = copy.deepcopy(entities)`, before the
per-domain loop; no domain ever sees another domain's proposal-in-progress this
same tick — proposals are collected from ALL domains first, then passed as a
single batch to `run_commit_frame`). **`engine_priority` has no effect on what
data a domain can read.** It only determines the order proposals are
*validated and applied* within `run_commit_frame`'s single pass
(`order_key = (requested_time, phase_rank, engine_priority, content_hash)`,
ascending — confirmed `commit_pipeline.py:99-100,331,337`), where each
proposal's preconditions are checked against `entities` as **progressively
mutated by earlier-in-this-pass commits** (`commit_pipeline.py:9-15`, its own
docstring: "commits proposals ONE AT A TIME... re-validates preconditions
against the progressively-mutated state before each commit"). Committing at a
lower priority number means your pinned-revision precondition is checked
*before* a higher-priority-number proposal has had a chance to bump that
revision this tick — avoiding a same-tick stale-precondition rejection. It says
nothing about visibility during proposal-*building*, which is always frozen at
end-of-T−1 for every domain, without exception.

**Corrected statement:** `group_carriage` runs at **`engine_priority = 86`** —
one below `group_norm` (87), independently derived from the established,
mechanically-repeated pattern at each existing layer (association 90 →
group_state 89 → group_goal 88 → group_norm 87, each new consumer sitting
exactly one below what it reads; confirmed via direct grep of each domain
file's own `engine_priority` line). Being one below `group_norm` means its
proposal's pinned `group-goal-000` (88) and `group-norm-000` (87) revisions are
revalidated *before* those two domains' own proposals get a chance to bump them
this tick — avoiding a same-tick stale-precondition rejection, the same
discipline 8A applied one layer up. **But data visibility has nothing to do
with priority: `group_carriage` sees `group-goal-000`, `group-norm-000`, AND
every person's `action` field — all of it — as of the end of the *previous*
tick, universally, for every registry it reads, with no exception for
`living_agent_social`'s low priority number.** A norm formed at tick T is
backfilled at T+1 (unchanged from the original claim). A qualifying
`social_request_help` action **accepted** at tick T is **detected and turned
into a transmission proposal at tick T+1**, not tick T (corrected — the
original claimed same-tick detection). This does not change `TRANSMISSION_COUNT`
or which event qualifies; it changes only the tick at which the resulting
`carrier_record` is stamped, consistent with 8A's own convention of never
backdating a commit to the tick that caused it (norm formation itself is
stamped at the domain's own evaluation tick, one after the causing adoption,
not backdated to the adoption's tick).

**Consequence for the measured evidence:** the Phase 1 probe (run before
`group_carriage` existed) recorded the one qualifying event as an accepted
event at tick 699, predicting (at contract-confirmation time) that
`group_carriage`, once implemented and enabled, would detect it and commit
the resulting transmission `carrier_record` one tick later, at tick 700.
**Superseded by direct Phase D measurement** (see "Phase D verification
finding" below, added after implementation): enabling `group_carriage`
itself shifts the underlying action's own accepted tick from 699 to **698**
(a real, investigated, non-blocking trajectory shift — not a bug in this
one-tick-lag reasoning, which is confirmed correct and is exactly why the
carriage domain's own commit lands at **699**, one tick after the action's
*actual* accepted tick of 698, not the Phase-1-probed tick of 699). Every
other reference to "tick 699" elsewhere in this document that describes the
*Phase 1 probe's own recorded evidence* (an immutable record of what that
specific, pre-implementation run measured) is left as-is for historical
accuracy; only forward-looking predictions of the carriage domain's *own*
behavior are corrected against the actual Phase D measurement.

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
5. **Organic proof — scenario integration only, VERIFIED (2026-07-20)**
   (mechanism correctness is proven by item 1's synthetic fixture, per the
   confirmed rider): the unseeded 1,000-tick `collective_groups` run,
   measured directly (`memory/evidence/stage-8b-leg1/probe_8b_carriage_registry_state_1000.json`),
   backfills carriage for all 7 formations — **49 records measured**,
   `person-004` excluded from all 7, exactly as predicted — **and** fires
   **exactly the one** predicted transmission event: `person-004` learns
   `shelter_upkeep_norm` on `group-77ec2beb76de22397715` from `person-000`,
   `carrier_count = 50` total. The qualifying `social_request_help` action is
   accepted at tick **698** (not 699 as predicted pre-implementation — see
   "Phase D verification finding" below for the investigated reason), and
   `group_carriage` commits the resulting `carrier_record` at tick **699**
   (`via_event_id: "evt-698-13861-115d344e"`, `learned_tick: 699`) — one tick
   after the action's actual accepted tick, exactly per the one-tick-lag
   design. `accepted_by_type.group_carry_norm = 4` in the full harness run
   (3 backfill-batch ticks + 1 transmission tick), 0 deaths, survival
   dominant (repeat_matches/replay_matches both true). This item confirms
   the real commit pipeline *reaches* the machinery under organic
   conditions; it is not the correctness proof (item 1 is).
6. **Registry size measurement — VERIFIED (2026-07-20):**
   `group_carriage_capacity_diagnostics` measured on the final committed
   registry: `total_serialized_bytes = 26,076` against the 128-record cap
   (50 used, 61% headroom, comfortably clear) and the 24,576-byte
   `payload_target_bytes` **soft target** (exceeded by ~1,500 bytes / +6%)
   and the 32,768-byte hard `proposal_bytes` cap (79.6% of cap, well clear).
   Recorded honestly: the soft target was undershot in the pre-implementation
   projection (Decision 5's math used norm/member-count ceilings, not actual
   serialized bytes); the hard cap — the one that actually bounds state —
   is comfortably respected. Not silently rounded up after the fact; the
   projection is left as originally written above and this is noted as a
   measured correction, same discipline as 8A's own capacity numbers being
   measured only after implementation.
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
  tick the one transmission event actually commits, VERIFIED — see the
  Organic proof item above and "Phase D verification finding" below). The
  overlap probe (item 1, this doc) measures `REPAIR_SHELTER` candidates
  existing **only** on ticks 1–236, all of them *before* any norm exists
  (first formation at 683) and therefore before transmission is even
  possible — independently reconfirmed under the actual `group_carriage`-
  enabled configuration by the zero-firings boost-check below. No tick from 699 through 1000 has a
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

## Phase D verification finding — STOP: does enabling group_carriage cross a containment line? (open, 2026-07-20)

Found during Phase D verify, presented as its own STOP rather than folded
into the acceptance-gate items above as settled. The mechanism below is
plausible and sourced; **its classification is a judgment call, not a
fact**, and it is left open for your ruling rather than decided here.

The Tier A organic-proof evidence above cites `via_event_id:
"evt-698-13861-115d344e"`, `learned_tick: 699` for `person-004`'s transmission
— **the underlying qualifying `social_request_help` action was accepted at
tick 698**, not tick 699 as the Phase 1 probe (run before `group_carriage`
existed) recorded for the same nominal interaction. Investigated rather than
assumed to be a probe artifact:

- **VERIFIED (direct instrumented re-run, both configurations):** enabling
  `group_carriage` in `collective_groups`'s `enabled_domains` measurably
  changes the tick-by-tick trajectory starting at tick 698 (first divergence;
  accepted-event counts differ tick-by-tick from 698 through at least 702).
  Ticks 690–697 are byte-identical between configurations. The person-004→
  person-000 `social_request_help` interaction that grounds this leg's one
  measured transmission event happens at tick 699 *without* `group_carriage`
  enabled and at tick 698 *with* it enabled — same actors, same action, one
  tick earlier once the domain is live.
- **RULED OUT: the boost pathway.** The obvious suspect — this leg's own
  `_apply_group_norm_influence` eligibility change (Decision 1) causing
  carriers to get boosted, which changes their decisions, which cascades —
  was directly instrumented against the real 1,000-tick pipeline (wrapping
  the function, comparing every candidate list before/after). **Zero firings
  across the entire run.** This reconfirms rather than contradicts the
  standing overlap-probe fact (REPAIR_SHELTER candidates: ticks 1–236 only;
  carriers: tick 684+; disjoint) — now independently verified under the
  actual `group_carriage`-enabled configuration, not just the earlier
  Phase 1 probe's un-enabled one. **This leg's own sanctioned influence
  mechanism contributes zero behavioural difference; it is not the cause.**
- **RULED OUT: RNG order-dependence.** Read `core/rng.py` directly:
  `DeterministicRNG.stream(name)` is keyed purely by `sha256(run_seed +
  "::" + name)`, independent of call order or how many streams exist —
  by design (the module's own docstring: "determinism does not depend on
  call order, only on (run seed, name)"). Confirmed, not assumed.
- **LIKELY mechanism (identified by source read; not independently
  re-instrumented — see "What is NOT yet verified" below).**
  `run_commit_frame` (`core/commit_pipeline.py`) assigns a strictly
  increasing `order_index` to every accepted event this tick, carried
  forward as the next tick's starting `order_index`
  (`core/kernel.py:83-86`). `event_id` embeds it
  (`evt-{tick}-{order_index}-{hash}`), and that string becomes an entity's
  `last_event_id`. A person's next proposal typically cites their own
  `last_event_id` in `causal_parent_event_ids` — one of the fields hashed
  into `content_hash` (`core/commit_pipeline.py`'s `normalize_proposal`,
  confirmed `seq`/`order_index` are explicitly excluded from that hash, but
  `causal_parent_event_ids` is not). `content_hash` is the final tie-breaker
  in `order_key` for same-`(requested_time, phase, engine_priority)`
  proposals. `group_carriage` contributing extra proposals from tick 684
  onward shifts `order_index` for everything after it in the same and every
  subsequent tick, which shifts `last_event_id` strings, which shifts
  `content_hash` for entities that cite them, which can flip a same-priority
  tie-break — the mechanism `commit_pipeline.py`'s own docstring names for
  resource contention ("the first proposal in order wins").

### What is NOT yet verified (stated so the classification below is not read as resting on more than it does)

- The mechanism above is a **source-read hypothesis**, not an instrumented
  measurement. What is measured is the *effect* (trajectory diverges at 698)
  and two *exclusions* (boost pathway: zero firings; RNG: keyed by
  `(seed, name)` only). The specific `order_index → last_event_id →
  content_hash → tie-break` chain has **not** been traced end-to-end on the
  actual diverging proposals — no probe has yet shown the two competing
  same-priority proposals at tick 698 and their `content_hash` values with
  vs without `group_carriage`. Until that is done, the causal chain is
  LIKELY, not VERIFIED.
- Whether the divergence is **bounded** (a one-tick reordering that
  re-converges) or **unbounded** (a persistent trajectory fork that grows)
  is **UNKNOWN**. The measured window is ticks 690–702; divergence appears
  at 698 and is still present at 702. Nothing has measured whether the two
  trajectories re-converge, stay slightly offset, or diverge further over
  the remaining ~300 ticks. The final-state hashes differ, but that is
  equally consistent with both readings.
- Whether any **other** domain pair exhibits this coupling (i.e. whether
  this is genuinely general to the pipeline, or specific to what
  `group_carriage` does) is **UNKNOWN** — not tested.

### The classification question (open — this is what needs your ruling)

The facts above are not in dispute. What they *mean* is, and the two
readings carry different consequences:

**Reading (a) — same category as prior accepted hash changes.** Every prior
stage (7A, 7D, 8A) changed `collective_groups` hashes when its domain was
added, and each was accepted as the ordinary cost of a new domain entering
the pipeline. On this reading, what happened here is the same thing: a new
domain writes its own new registry, that state hashes differently, event
ids shift downstream, and a same-priority tie-break resolves differently.
Determinism is intact (`repeat_matches` and `replay_matches_final_entities`
both `true`); the frozen `living_settlement` hash is byte-identical
(`group_carriage` inert there); nothing about `group_carriage`'s own
proposal-only, carriage-scoped behaviour is violated. This contract already
anticipated a hash change in its "Hash consequence" risk. Under (a), the
correct action is to record the new hashes and proceed.

**Reading (b) — a new category: cross-domain outcome coupling through the
shared ordering/hashing substrate.** Prior stages' accepted hash changes
were, as far as this leg's evidence goes, *that domain's own new state
hashing differently*. What is measured here is different in kind: enabling
`group_carriage` changed **which tick two unrelated persons interacted** —
`person-004` and `person-000`, in a `living_agent_social` interaction that
`group_carriage` neither proposes, validates, reads as input, nor influences
(its one sanctioned influence path fired **zero** times all run — measured,
not assumed). That is one domain shifting a *different* domain's outcome
through a substrate neither of them declares as a dependency. Under (b),
the leg's "proposal-only, carriage-scoped, reads-only-its-own-upstreams"
containment story is materially weaker than the contract asserts: the
containment is real at the level of *state authority* (Core still writes
truth; `group_carriage` still writes only its own registry) but not at the
level of *behavioural outcome*, and the contract does not currently
distinguish those two claims. It also has a compounding implication —
if adding any domain can silently reshuffle other domains' event timing,
then every future leg's organic evidence is measured against a substrate
that the next leg will perturb, which is a verification-methodology
problem, not just a hashing detail.

**Which I think is more accurate: (b), with a qualification.**

My reasoning, and the honest limits of it:

1. The distinguishing question is not "did hashes change" (both readings
   predict that) but "did a domain change another domain's *behaviour*."
   Here it demonstrably did — the interaction moved from tick 699 to 698.
   That is an outcome change, not a representation change, and reading (a)
   does not account for it.
2. The most obvious innocent explanation was tested and **failed**: this
   leg's own sanctioned influence hook fired zero times across the entire
   1,000-tick run. So the coupling did not travel by any declared,
   contract-visible path. Coupling that travels by an undeclared path is
   precisely the class of thing a containment scope is supposed to exclude.
3. Against my own conclusion: I have **not** verified that prior stages
   (7A, 7D, 8A) did *not* do exactly this same thing when they were added.
   If they did — and the source-read mechanism suggests any proposal-adding
   domain would — then (b) describes a **pre-existing, architecture-wide
   property that Leg 1 merely made visible**, not something Leg 1
   introduced. That distinction matters enormously for what the right
   response is, and I did not test it. It is the single cheapest
   observation that would most change this recommendation: re-run an
   earlier stage's addition (e.g. `group_norm` on/off against the 7D
   baseline) and check whether unrelated interaction ticks moved then too.
4. Even under (b), I do not think this blocks *the mechanism* Leg 1 built:
   backfill, transmission, carriage-only eligibility, and the survival
   guard are all independently proven by the synthetic-fixture and
   integrated tests, which do not depend on the organic trajectory at all.
   What (b) puts in question is narrower: the contract's containment
   language, and the durability of organic evidence measured on a
   substrate that later legs will perturb.

**Recommended ruling options** (yours to pick; I am not choosing):
(i) rule (a), record hashes, proceed; (ii) rule (b) and accept it as
pre-existing/architecture-wide, with the contract's containment language
narrowed to "state authority, not behavioural isolation" and the
methodology consequence recorded for later legs; (iii) rule (b) but
require the cheap discriminating probe in point 3 *first*, so the ruling
is made knowing whether prior stages did the same; (iv) treat it as a
hardening-surface item for the separate authorised pass, alongside the
three already parked there.

### RULING (2026-07-20): option (iii)

**(b) is the working classification, but final contract language waits on
the discriminating probe.** The probe was specified and run immediately
after this ruling: `collective_groups`, 1,000 ticks, three domain configs
run from identical genesis with `enabled_domains` as the only variable —
**A** = the 7D baseline (no `group_norm`, no `group_carriage`), **B** = A +
`group_norm` (the 8A state), **C** = B + `group_carriage` (this leg). It
compares, for each pair, the first divergent tick and whether the full
`social_*` interaction list is byte-identical — specifically flagging any
case where the *same* `(actor, target, event_type)` triple occurs at a
*different* tick, which is the exact signature of the phenomenon.

The A-vs-B result decides how (b) gets written up:

- **If A→B also shifts unrelated interaction ticks:** the coupling is a
  **pre-existing, architecture-wide property** of the commit pipeline that
  Stage 8A already exhibited and that Leg 1 merely made visible. (b) is
  still the correct classification of *what the phenomenon is*, but Leg 1
  did not introduce it, and the correct response is to narrow this
  contract's containment language to "state authority, not behavioural
  isolation", record the verification-methodology consequence for later
  legs, and route the substrate issue to the parked hardening pass rather
  than to this leg.
- **If A→B does NOT shift them (only B→C does):** `group_carriage` is doing
  something the prior domain did not, the "general pipeline property"
  defence fails, and the finding is Leg-1-specific — which would warrant
  understanding the actual mechanism before this leg is committed at all,
  not just narrower language.

Neither branch is pre-written into the contract body; the result is
recorded here when it lands, and any change to the contract's containment
claims is made under it.

#### Probe result (2026-07-20) — VERIFIED: the first branch. Coupling is pre-existing.

**Method note (standing-rule correction, recorded because the first attempt
was wrong).** The probe was initially specified as three full 1,000-tick
runs — which is precisely the opening move `CLAUDE.md` § Proportionality
now forbids ("a full harness re-run is the escalation after an inconclusive
narrow check, never the opening move"). That run was killed and replaced
with a narrow diagnostic: **two configs in lockstep in one process,
terminating at the first divergence**, with the added domain's *own* event
types excluded from the comparison signature (without that exclusion the
comparison trivially "diverges" the moment the new domain commits its first
event, which proves nothing about other domains). It answered in **286
ticks** instead of 3,000. Evidence:
`memory/evidence/stage-8b-leg1/probe_8b_coupling_narrow.json`;
script `backend/tools/_probe_8b_coupling_narrow.py`.

**Result — A vs B (7D baseline vs 7D + `group_norm`, i.e. Stage 8A's own
addition):**

- `group_norm` first commits its own event at tick **283**.
- Excluding `group_norm`'s own events entirely, the two configs' accepted
  events **diverge at tick 286** — three ticks after the new domain began
  proposing.
- The divergence is a `living_agent_social` event: `social_request_help` by
  `person-005` is present in the 7D baseline and absent in the 8A config at
  that tick (A has 19 unrelated-domain events, B has 18).

**Conclusion: Stage 8A's own addition already changed unrelated domains'
behaviour, by the same class of effect and on the same event family
(`living_agent_social`) as the Leg 1 finding.** The phenomenon is a
**pre-existing, architecture-wide property of the commit pipeline**, not
something `group_carriage` introduced. Reading (b) remains the correct
*description* of what the phenomenon is — one domain does shift another
domain's outcome through the shared ordering/hashing substrate, and that is
not the same thing as "a domain's own new state hashing differently" — but
Leg 1 is not its origin, and the "general pipeline property" account is now
measured rather than asserted.

**Honest limit of this result:** the probe terminates at the first
divergence, so it establishes that `person-005`'s interaction *differs at
tick 286*. It does **not** establish whether that event is permanently
suppressed or merely displaced to a later tick — the run stopped before it
could tell. That distinction does not affect the classification (either way
an unrelated domain's behaviour changed), but it is unmeasured and is not
claimed. Equally unmeasured: whether 7A's and 7D's additions did the same
(only 8A's was tested), and whether these divergences are bounded or grow
over a full horizon.

**Consequences taken under this result** (each applied in this document):

1. **Containment language narrowed.** This contract's claims are now
   scoped to **state authority, not behavioural isolation** — see the
   amended Agency/containment wording in "Mechanism" and the Constants
   table's `engine_priority` row. `group_carriage` is proposal-only, writes
   only its own registry, and Core alone commits truth: those claims stand
   and are tested. It is **not** claimed that enabling it leaves other
   domains' tick-by-tick behaviour untouched — that claim would be false,
   and would have been equally false for 8A.
2. **Verification-methodology consequence recorded for later legs.** Any
   leg's organic evidence is measured on a substrate that the *next* leg's
   domain addition can perturb. Organic tick-level facts are therefore
   valid for the configuration they were measured under, and must be
   re-measured (not carried forward) once a new domain is enabled. This is
   why Tier A (deterministic fixture/injection) proof is the primary
   correctness evidence for this leg and Tier B organic evidence is
   explicitly secondary — a split that the confirmed rider (b) already
   required for other reasons and that this result independently justifies.
3. **Substrate issue routed to the parked hardening pass**, alongside the
   three already-documented surfaces — *not* fixed inside this culture leg
   (`CLAUDE.md` hard rail: "Fix the three documented hardening surfaces
   inside a culture leg" is forbidden; this is the same class). The open
   question for that pass: whether `content_hash` should be computed over
   a parent-independent identity so that same-priority tie-breaks are
   stable under unrelated domain additions.

Evidence: `memory/evidence/stage-8b-leg1/probe_8b_tick_discrepancy_investigation.json`,
`probe_8b_boost_firing_check_1000.json`.

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
   recorded fresh at Phase D verify. **Amended 2026-07-20:** this risk as
   originally written anticipated only a *hash* change. Phase D measured
   something the original wording does not cover — a change to an unrelated
   pair of persons' *interaction tick*. Whether that is the same risk or a
   different one is the open classification question in the "Phase D
   verification finding" STOP above; this item no longer asserts "not a
   regression", pending that ruling.
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

## Post-implementation archive diff (step 13 of the session directive, 2026-07-20)

Performed only after Tier A acceptance criteria passed, per the directive.
The archive was **not** consulted during implementation. The contract, not
the archive, resolves every divergence — and in each substantive divergence
below the contract's probe-derived choice differs from the archive's.

**The three converged areas the confirmed rider requires be called out
explicitly** (convergence here is expected and is not itself a finding):

1. **Carriage-only formation backfill from 7D `supporter_ids`** — converged.
   Archive derives via `_forming_supporters`; this implementation via
   `_group_active_goal` + `supporter_ids`. Same source of truth, same
   supporters-only rule, different helper decomposition.
2. **The `entity["action"]` / `accepted_event_id` seam** — converged. Both
   define `_accepted_action` mirroring `association_contracts.py`.
   **Divergence within the converged area:** the archive resolves the
   counterparty through `_action_target_person` (a copy of 7A's helper,
   scanning `participants` + `target_entity_ids` + `target_entity_id`);
   this implementation reads `action.get("target_entity_id")` only. Mine is
   **narrower** — it would miss a qualifying interaction expressed only via
   `participants`. Not a defect against the contract (Decision 4 scopes the
   trigger tightly and the measured organic event carries
   `target_entity_id`), but it is a real behavioural difference and is
   recorded rather than glossed.
3. **`engine_priority = 86`** — converged exactly.

**Substantive divergences (contract prevails; each traced to probe evidence
the archive did not have):**

| Aspect | Archive | This implementation | Basis |
|---|---|---|---|
| Transmission direction | **Teaching** — `if actor_id not in holders: continue`, i.e. the actor must already carry, target is the learner | **Imitation** — non-carrier initiates toward a carrier | Decision 2: zero organic carrier-initiated crossings post-formation; the one measured event is non-carrier-initiated |
| `TRANSMISSION_COUNT` | **2** | **1** | Decision 3: exactly one qualifying interaction exists in the horizon; N=2 is measurably unreachable |
| Qualifying types | 7 bare action types (`help, offer_help, cooperate, request_help, promise, repay, give`) | 1 event type, `("social_request_help",)`, as a data constant | Decision 4: only type ever measured crossing the boundary |
| Pair counters | `interaction_pairs` cap 256, per-(teacher, learner, norm) counting | none — unnecessary at N=1, documented with the condition for reintroducing them | falls out of N=1 |
| Compaction | `_compact_registry` present (carriage evictable) | absent — carriage never evicted | Decision 6: no forgetting mechanic is specified |
| Core validation path | **absent** — no proposal builder, no validator, no provenance stamper (442 lines, ending at diagnostics) | `build_group_carriage_proposal`, `validate_group_carriage_proposal` (re-derive + canonical-byte equality + forged-field rejection), `stamp_group_carriage_provenance` | invariant 10; the archive could not have been committed through Core at all |

**Consequence worth stating plainly (LIKELY, reasoned from measured data —
the archive was not executed):** under the archive's model the organic run
would have produced **zero** transmissions. Its teaching direction requires
the actor to be a carrier; the single measured post-formation crossing has
`person-004` — the sole non-carrier — as actor, so it would not qualify.
`TRANSMISSION_COUNT = 2` would then require a second such event, which the
horizon does not contain. The contract-first path produced the one value of
N and the one direction under which this leg's organic gate is reachable at
all. Recorded as vindication of the process, not of the author.

## Contract amendment 1 (2026-07-21) — F1 wording, F2c record slimming, F3 tracking-eviction fix

User-ruled 2026-07-21. **The five confirmed decisions, their riders, and the
standing-scenario ruling are untouched by this amendment** — carriage-only
eligibility, imitation-only, `TRANSMISSION_COUNT = 1`,
`social_request_help` only, and a separate registry all stand exactly as
confirmed. What changes is one claim's wording and two implementation
defects found after implementation.

### F1 — claim wording (eligibility vs acquisition). Ruling: FIX wording, ACCEPT behaviour.

The close-out claim "carriage is independent of current membership" is true
of **eligibility** and false of **acquisition**, and the unqualified form is
therefore wrong. Corrected statement, which is what the code does and what
the Mechanism section already described:

- **Eligibility** (the read-only nudge) is carriage-only and fully
  membership-independent: `_apply_group_norm_influence` consults the
  carriage registry and nothing else, so a carrier who has left the group is
  still nudged and a current member who never earned carriage is not.
- **Acquisition** by transmission additionally requires co-membership:
  `derive_group_carriage_changes` selects learners from
  `member_ids - carriers`. A non-member cannot learn.

The behaviour is unchanged and is correct for this leg — cross-group
transmission is 8D's diffusion goal and an explicit non-goal here. Only the
claim is corrected.

### F2c — record slimming. Ruling: option (c), remove duplicated fields.

Rejected: raising this registry's own `payload_target_bytes` (option a) or
re-designating the hard cap as invariant-4's denominator (option b). Both
resolve a measurement failure by moving the threshold. Option (c) removes
genuine redundancy instead.

Removed from every `carrier_record` body: `carrier_id`, `norm_id`,
`person_id`. All three are recoverable from the registry key that indexes
the record (`split_carrier_key`, exact because neither id contains `":"`).
Before the change each record stored the two longest strings in the schema
three times over — once in the key, once as `carrier_id`, once as the field
itself.

**Rider satisfied — provenance completeness preserved, stored once each:**
`via_event_id` (the causal event), `created_event_id` / `last_event_id`
(the commit event), `learned_from`, `learned_tick`, `source`, `group_id`
all remain. Every record is still traceable to the event that caused it.
The validator now **rejects** any record that re-states a key-held id, so
the slimming cannot be silently undone by a later writer or a forged
proposal (`test_validator_rejects_record_that_restates_key_ids`).

Measured bytes, before and after, per the rider:

| | bytes | vs `payload_target_bytes` 24,576 | vs `proposal_bytes` 32,768 |
|---|---|---|---|
| before | 26,076 | **−6.10%** (over by 1,500) | +20.42% |
| after | **19,726** (saved 6,350) | **+19.73%** | +39.80% |

**Outcome: the ruled fix is a large improvement but does NOT clear
invariant 4. It falls short by 0.27 percentage points** — 19.73% measured
against the ≥20% requirement. Reaching exactly 20% needs the registry at
≤ 19,660 bytes, i.e. **66 more bytes** across 50 records (1.32 bytes per
record). Recorded as a failure rather than rounded up or re-based onto the
`proposal_bytes` denominator, which is the manoeuvre option (b) was
rejected for. Escalated to the user rather than resolved unilaterally: the
ruling enumerated three specific fields to remove, all three were removed,
and removing a fourth is a further schema decision, not an implementation
detail of the existing ruling.

Record content preserved exactly as required by the rider — carrier_count
50 (49 backfill + 1 transmission), and `person-004` still traceable end to
end: `source: transmission`, `learned_from: person-000`,
`via_event_id: evt-698-13861-115d344e`, `learned_tick: 699`.
Evidence: `probe_8b_carriage_registry_state_1000_v2.json`.

**Ruling recorded on the classification itself:** this was an
**invariant-4 headroom question**, not an estimate miss. 8A measured its own
≥20% headroom against `payload_target_bytes` (5,643 / 24,576 → 77.0%),
which establishes that denominator in this codebase; against it, Leg 1 had
negative headroom and failed invariant 4 outright.

### F3 — tracking eviction. Ruling: fix now.

`backfilled_norm_ids` was truncated by `sorted(set(...))[-16:]` —
**lexicographic** — while `group_norm` compacts its own norms by
**(active, recency)**. The orderings disagree, so an **active** norm could
be evicted from the tracking set while still present in `norms`; the next
derive would then re-backfill it against the **current** goal's
`supporter_ids`, granting carriage to people who were not supporters at
formation and breaking the one-time-backfill guarantee (claim 4).
Unreachable at this scenario's 7 norms; latent at the 16 cap and reachable
once 8C/8D raise norm counts.

Fixed by **pruning to norms still present upstream** rather than truncating
by id order: `advance_group_carriage_registry` now takes `known_norm_ids`
(every norm_id in the Stage 8A registry, any status) and retains exactly the
intersection. An active norm can therefore never be evicted while it remains
in `norms`, and the set is bounded by the norm registry's own cap instead of
a second independent one — so the two caps can no longer drift apart. A norm
absent from `norms` needs no entry, because `derive_group_carriage_changes`
only iterates `norms` and cannot re-backfill it.

Added to the acceptance criteria (Tier A, cap boundary), per the ruling:
`test_backfilled_tracking_never_evicts_a_norm_still_in_the_registry`
injects more distinct norms than the cap and asserts every norm still
upstream is still tracked — a genuine regression test, which the previous
lexicographic code fails. Paired with
`test_backfilled_tracking_prunes_norms_no_longer_upstream` to hold the
bound.

### Post-amendment gate re-run (2026-07-21) — VERIFIED, supersedes all prior run evidence

All figures pasted from the v2 evidence files, not from memory. The pre-fix
evidence files remain on disk for comparison but are **superseded**.

- **Frozen-hash safety — PASS, byte-identical.**
  `living_settlement --ticks 320 --repeat 2` →
  `final_state_hash = 84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`,
  `repeat_matches` + `replay_matches_final_entities` true. The schema change
  did not perturb the frozen scenario (`group_carriage` inert there).
  Evidence: `harness_living_settlement_320_v2.json`.
- **Determinism + organic — PASS.**
  `collective_groups --ticks 1000 --repeat 2` → `repeat_matches` +
  `replay_matches_final_entities` true; `final_active_group_norm_count = 7`;
  `accepted_by_type.group_carry_norm = 4` (unchanged by the fixes).
  New `final_state_hash = 4d1d396a1da33c57c7540d5d75b4da17d631e217af9d49bbaf746475a3c2ed32`
  (changed, as expected — the carriage schema changed).
  `group_norm_summary_hash = 7487bbbcbc62d6fc6988c6ab12989facba692b72bec93198c01b8edcf2f06ae1`
  — **unchanged from the pre-fix run**, confirming the Stage 8A registry is
  genuinely untouched by this leg's schema change rather than merely
  asserted to be. Evidence: `harness_collective_groups_1000_v2.json`.
- **Suite — 368 executed passed; 4 named Docker-environment skips; no
  executed test failed.** Includes the new F3 boundary test. One earlier run
  hit `test_concurrency.py::test_concurrent_stage7a_steps_do_not_duplicate_groups_or_head`,
  the intermittent CAS-revision flake already documented in
  `CAPABILITY_ROADMAP.md` § Test-suite flake taxonomy; it passed on isolated
  re-run and did not recur on the confirming full run.
- **Measurement-tool change, recorded:**
  `backend/tools/_probe_8b_carriage_registry_state.py` was patched alongside
  the schema — it read `carrier_id`/`norm_id`/`person_id` from record bodies,
  which F2c removed, and now derives them from the registry key via
  `split_carrier_key`. `group_id`, `source`, `learned_from`, `via_event_id`
  and `learned_tick` are still body-stored and still read from the body. No
  other read referenced a removed field, so no silent-null path could distort
  the counts. No domain, core, or test file was touched by the patch.

### Sequencing under this amendment

One amendment (this section) → both fixes implemented → full gate re-run
replacing the superseded evidence files → adversarial review (deferred until
after the re-run, per ruling 1) → commit series → close-out STOP.

## Contract amendment 2 (2026-07-21) — invariant-4 headroom resolution

**Trigger.** The post-amendment-1 gate re-run measured `group-carriage-registry-v1`
peak at 19,726 B against `payload_target_bytes` = 24,576 B → 19.73% headroom, short
of invariant 4's ≥20% by 0.27 pp (66 B across 50 records; ~1.32 B/record). Amendment
1's F2c ruling explicitly escalated any further field removal as "a schema decision,
not an implementation detail of the existing ruling."

**Ruling — option A.** Remove the post-commit staging keys `pending_event_tick` and
`pending_transition` from committed carriage records. The record builder
(`group_carriage_contracts.py:334-358`) writes these as staging inputs to the
stamper; they survive commit as `null` keys — pure post-commit residue.

**Why A, not B/C/D.**
- Carriage records are write-once (never updated after creation), so — unlike 8A
  norms, which re-use `pending_*` on refresh/expiry — these keys can never be read or
  re-used post-commit. Removing them takes non-canonical residue out of canonical
  state: a correctness improvement, not a headroom manoeuvre. The divergence from
  8A's idiom is justified solely by the write-once property.
- (B) drop per-record `schema_version` and (C) collapse `created_event_id` /
  `last_event_id` each also clear the bar, but each deletes a field redundant today
  yet semantically real: (B) forecloses cheap per-record migration to a future
  carriage schema; (C) removes the create-vs-last-touch seam an updatable-carriage
  leg would need. A removes the one field with no future canonical role.
- (D) accept 19.73% is rejected: it leaves a hard-rail invariant knowingly violated.
  Re-basing headroom onto the looser `proposal_bytes` (32,768) denominator was
  already rejected; accepting a miss is the same threshold-relaxation from the other
  side.

**No version bump.** `group-carriage-registry-v1` / `group-carriage-v1` are unshipped
(the leg is uncommitted), so this finalizes the v1 record shape before first commit
rather than migrating v1→v2. No schema-version increment; the first committed shape
is the amended one.

**Estimated effect (binding number is the gate re-measure).** ~2,600 B saved
(~52 B/record × 50) → ~17,126 B → ~30.3% headroom. String-arithmetic estimates only;
the condition that closes this amendment is the re-measured post-commit registry byte
count, not these figures.

**Implementation mandate.**
1. The carriage stamper drops `pending_event_tick` / `pending_transition` from the
   record after stamping. Change isolated to the carriage path — the 8A norm stamper
   is untouched (it keeps `pending_*` for refresh/expiry).
2. The validator's expected-record re-derivation must omit the same keys, or
   post-commit byte-equality fails on every carriage record.
3. A new validator test locks it both ways: a committed record carrying either key is
   rejected, and the honest stamped record omits both — mirroring
   `test_validator_rejects_record_that_restates_key_ids` from F2c.
4. Grep-confirm that no consumer reads `pending_event_tick` / `pending_transition`
   off a committed carriage record (projection, inspector, downstream domain) before
   deletion.

**Gate consequence (revises the sequencing above).** This is a schema change and
invalidates prior run evidence. Close-out requires a full gate re-run superseding the
post-amendment-1 evidence files — suite, `living_settlement` 320×2 (frozen hash
`84d3ad52…c32d2` re-confirmed byte-identical), `collective_groups` 1000×2 (new
registry hash recorded), and the registry byte re-measure whose ≥20% result closes
this amendment. Per protocol §3 this re-run precedes the adversarial review, so the
reviewer sees the shipping numbers — Amendment 2's implement → re-gate step runs
before the review named in "Sequencing under this amendment," not after.

## Session handoff (2026-07-21) — resume here

**Position.** Phase D implementation is complete and passing. The leg is
blocked at one thing only: the protocol §3 adversarial review has never
run. Everything else is done.

**Committed** (branch `capability/stage-8-culture`, pushed through
`8883b715`; later commits local):
`3506bd2b` cache untrack · `798bb0e` hard-rail-reviewer agent ·
`24c27435` contract PROPOSED + Phase 1 evidence · `cc4dcedf` contract
CONFIRMED + riders + adoption-count reconciliation · `0f638818`
commit-ordering correction · `cb91d804` doctrine (CLAUDE.md +
ADVERSARIAL-REVIEW-PROTOCOL.md).

**Uncommitted in the working tree** (deliberately — commit discipline
forbids committing past an open review finding):
- `backend/domains/group_carriage_contracts.py`, `group_carriage_domain.py` (new)
- `backend/tests/test_stage8b_leg1_norm_transmission.py` (new, 23 tests)
- modified: `core/commit_pipeline.py`, `domains/registry.py`,
  `domains/living_settlement_domain.py`, `scenarios/collective_groups.py`,
  `tests/test_stage7b_group_state.py`, `tests/test_stage8a_group_norm.py`
- this contract doc's Phase D sections · `memory/evidence/stage-8b-leg1/*`
- `backend/tools/_probe_8b_*.py` (probe scripts; `_probe_8b_coupling_discriminator.py`
  is DEAD — written for the killed 3×1000-tick approach, never run, delete
  before commit)

**Verified state.** Suite: 364 executed passed; 4 named Docker-environment
skips; no executed test failed. Frozen `living_settlement` hash
byte-identical. `collective_groups` repeat+replay true, 0 deaths, 49
backfill + 1 transmission carriers, `group_carry_norm` = 4.

**The one blocker.** Protocol §3 requires a non-Anthropic reviewer. Codex
CLI is installed but its nested reviewer subprocess fails with "No local
provider is running". The Zen MCP server was misconfigured — the upstream
project renamed its executable from `zen-mcp-server` to `pal-mcp-server`,
so the configured command could never launch. **Fixed and verified
connected 2026-07-21** (`claude mcp list` → `zen: ✔ Connected`, OpenRouter,
27 models). MCP tools load at session start, so `mcp__zen__*` is unavailable
in the session that fixed it.

**Next action, in a fresh session:** run the blind first pass via
`mcp__zen__codereview` (or `challenge`/`consensus`) against the bare claims
at `<scratchpad>/leg1_claims_bare.md`, per the AMENDED §2 — **claims only,
no builder seeds in the first pass**. Then submit the three findings below
as builder-seeded, tagged, and collect dispositions.

**Open findings carried in** (full detail in the close-out report):
- **F1** claim-9 wording: eligibility is carriage-only, but *acquisition*
  via transmission requires co-membership (`derive_group_carriage_changes`
  gates learners on `member_ids`). Disposition: FIX wording, ACCEPT
  behaviour. Not yet applied.
- **F2** DISPUTE — registry 26,076 B vs `payload_target_bytes` 24,576
  (**−6.10% headroom**) vs `proposal_bytes` 32,768 (**+20.42%**). 8A's
  precedent measures invariant-4 headroom against the *target*, under which
  this fails. Recommended resolution (c): slim the record — `carrier_id`
  duplicates the dict key, so `norm_id`/`person_id` are each stored twice
  per record. Needs contract amendment + gate re-run.
- **F3** DISPUTE — `backfilled_norm_ids` truncates lexicographically
  (`sorted(set(...))[-16:]`) while `group_norm` compacts by
  (active, recency); an **active** norm can therefore be evicted from the
  backfilled set and re-backfilled against the *current* supporter set,
  breaking one-time backfill. Unreachable at 7 norms, latent at the 16 cap.

## What this contract does NOT authorise

Any deviation from the confirmed decisions and riders above without a new,
recorded confirmation. Any consultation of the archived module during
implementation (post-hoc diff only, per the log above). Any scenario-dynamics
work beyond this leg's scope — that is explicitly parked as the first
contract-gated item after this leg closes, not folded into Phase D.
