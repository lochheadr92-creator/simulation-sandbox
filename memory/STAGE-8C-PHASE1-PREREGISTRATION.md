# Stage 8C Phase 1 — Aid-Exchange Pre-registration

**Status: PROPOSED — not ratified. Ratification is the user's act.**
Leg A remains unauthorized. This document pre-registers (per Invariant 12(b)/(c))
the organic-reachability acceptance gates, run length, and threshold-provenance
rules for a future aid-exchange norm. It is measurement + planning only; it is
**not** the Leg A contract and contains no production-code design.

---

## 1. Status and provenance

- **Date:** 2026-07-22.
- **Branch:** `capability/stage-8c-phase1-aid-exchange`.
- **Base SHA:** `002a18a4` (Invariant 12 v2 ratified).
- **Commits on top of base (this phase):**
  - `0469d8c0` `chore(stage-8c): commit Phase 0.5 probe scripts and evidence`
  - `cc0fbe96` `docs(roadmap): pre-flight dependency friction, stages 9-15`
  - `e5816714` `docs(stage-8c): mark STAGE-8C-LEG1-PROMPT.md superseded`
  - `e6337920` `chore(stage-8c): response-side probe script and 308-tick evidence`
  - (this doc) `docs(stage-8c): Phase 1 pre-registration proposal v2`
- **Committed evidence base:** `memory/evidence/stage-8c-leg1/`
  - `probe_8c_social_request_help_run.json` (150 ticks — the Phase 0.5 request-side run)
  - `probe_8c_food_sharing_50_diag.json` (50-tick wiring diagnostic)
  - `probe_8c_food_sharing_1000.json` (0-byte; the failed 1000-tick attempt, retained)
  - `probe_8c_response_side_308.json` (**Phase B**, 308 ticks — the single authorized run)
- **Authority:** STAGE-8-CONTINUATION-PROMPT.md → CLAUDE.md invariants (incl. 12 v2)
  → EXECUTION-PROTOCOL.md v1.2 → AGENT_WORKFLOW.md. Only ratified text governs.
- **Evidence labels used throughout:** VERIFIED (committed measurement/code),
  LIKELY (supported but not directly measured), GAP (named, unfilled — never a
  guessed number).

---

## 2. Pre-flight findings A–D (read-only, from committed code)

- **A. Event rendering — GENERIC, no whitelist.** `/runs/{id}/events`
  (`backend/api/routes.py:193-196`) returns all accepted events by `order_index`;
  the causal-chain walker (`routes.py:225-253`) carries `event_type` with no
  allowlist. A new aid event needs no registration to be observable. (Any
  frontend display switch is non-canonical projection.) [VERIFIED]
- **B. Death — observable from the frozen `entities_view`.**
  `lifecycle_domain._death_proposal` commits `alive=False`,
  `current_goal="DEAD"`, `health=0`, `death_cause`, `death_tick`, and
  `action.type="death"` onto the person entity (gated by an `alive==eq==True`
  precondition; fires once). [VERIFIED]
- **C. Accept/refuse disposition — the static `role` field.**
  `living_settlement_domain.py:334`:
  `action_type = "refuse" if role == "skeptic" else "cooperate"`. Roles are
  scenario genesis (`scenarios/living_settlement.py:33-48`; person-006 is the
  sole `skeptic`, person-001 a `caretaker`). **No dynamic trust signal is usable
  in `collective_groups`:** `reciprocity_trust` consumes `interaction_memory`,
  written only by `people_domain`, which is **disabled** here (food-diag
  `wiring_trace.people_domain_in_enabled_domains=false`, 0 facts). [VERIFIED]
- **D. Association registry capacity — two-tier byte budget + count caps.**
  `AssociationLimits` (`association_contracts.py:69-87`): soft
  `payload_target_bytes=98 304` (deterministic compaction via
  `_fit_registry_payload`), hard `proposal_bytes=131 072` (validator
  `association.payload_limit`; `metadata.payload_bytes` must exactly equal the
  recomputed byte length). Count caps: `records=48`, `candidates=24`,
  `processed_evidence_ids=96`, `detailed_evidence_per_record=8`,
  `provenance_refs=16`; scalar `PAIR_STRENGTH_MAX=CATEGORY_SCORE_MAX=100`.
  Byte-primary and exact-byte-accounted — not a flat record count. [VERIFIED]

---

## 3. Step 1 — per-quantity yield (from the 150-tick committed run, pre-Phase-B)

| # | Quantity | Committed data yields it? | Basis |
|---|---|---|---|
| 1 | per-tick `hunger≥600` eligibility count (all agents) | CANNOT (pre-B) | per-agent hunger unrecorded; only a person-007 lower bound |
| 2 | visible-person co-occurrence at eligibility | CAN (partial) | `nearby_context` on 8 accepted requests: 6 non-participants within range ≤4 |
| 3 | REQUEST_HELP / RESPOND_HELP pairing + timing | CANNOT (pre-B) | RESPOND_HELP not instrumented in the 150-tick probe |
| 4 | recipient-side pending-commitment presence at T+1 | CANNOT directly (pre-B) | only final-state recorded |
| 5 | distinct dyads over time | CAN | =1 at t150; reversed pair false; spread gate false |
| 6 | cooperate-source separation (request-linked vs debt) | CANNOT (pre-B) | `social_cooperate` unattributed at 50t |

The CANNOT-yield set **{1, 3, 4, 6}** justified the single Phase B run (§5), which
resolved all four.

---

## 4. Q1, Q2, Q3 (with citations)

**Q1 — the 12 rejections (150-tick run; scaled and reconfirmed at 308 in §5).**
11×`precondition.failed`/detail `living_agent_eq_failed` + 1×`social_action.not_adjacent`.
`living_agent_eq_failed` is constructed by `evaluate_preconditions` as
`f"{field}_{op}_failed"` (`commit_pipeline.py:115-123`; reason_code set at
`:443`) when the **two-party** `living_agent eq` precondition (actor **and**
target; `living_agent_social.py:311,318`) fails commit-time revalidation against
the plan-time snapshot stamped by `_replace_living_preconditions`
(`living_settlement_domain.py:488-491`). **Verdict: dominated by actor/target
same-frame `living_agent` staleness revalidation** — not target unavailability
(the lone `not_adjacent`) and not already-open-request suppression, which is
**structurally absent** (`REQUEST_HELP` has no pending gate; `outstanding_pending`
climbs 0→7 unimpeded, `living_settlement_domain.py:292-323`). [VERIFIED]

**Q2 — `distinct_requesters == 1` (150-tick) — RESOLVED by Phase B as a
right-censoring artifact.** The candidate rule is **not** a singleton:
`REQUEST_HELP` (`living_settlement_domain.py:292-323`) is a per-agent candidate
(`hunger≥600` ∧ a visible person), the lowest-priority food option (1200+hunger
vs EAT_CARRIED 1850+, RETRIEVE 1700+, GATHER 1500+). Phase B (§5) shows **6 of 8
agents propose REQUEST_HELP across 5 accepted dyads and 2 episodes**, and **all 8
cross hunger≥600**. So the single-requester picture was the 150-tick window
catching only episode 1 (ticks 43–59, all person-007). Only person-000 and
person-006 are hungry-but-never-request; **LIKELY** because higher-priority food
candidates win for them (person-000 carries food early and becomes the episode-2
hub target; person-006 starts hungriest at 850 but is well-positioned to
gather) — the exact per-tick candidate-set reason is a residual (§13), not rule
gating. [VERIFIED that it is not rule gating / not a single-requester property;
LIKELY for the two non-requesters' cause]

**Q3 — `commitments_with_any_status_change == 0`: ONE defect, confirmed.**
request_help commitments are born `"pending"` (`living_agent_social.py:323`), but
every lifecycle path excludes pending: the deadline sweep
`advance_commitment_deadlines` breaks only `"active"` (`:189`); the
obligation/repay loop acts only on `{active,overdue,disputed}`
(`living_agent_cognition.py:528,417`); completion matches only
`{active,overdue,disputed,broken}` (`living_agent_social.py:357`). No transition
leaves `"pending"` → immortal-pending. **Not a second defect.** [VERIFIED]
> Correction carried forward: my Step 1 explained the beneficiary's missing
> commitment as 12-cap eviction (`commitments_per_entity=12`,
> `living_agent_contracts.py:86`). Phase B §5 refutes this by direct T+1
> measurement — see the delivery finding.

---

## 5. Phase B run results (the single authorized run) — resolves {1, 3, 4, 6}

**Run meta [VERIFIED]:** `probe_8c_response_side_308.json`; scenario
`collective_groups`, seed `living-agents-stage6`; **ticks_run 308**,
target_ticks_at_stop 308, **truncated false**, stopped_reason
`reached_target_ticks`, **wall_clock 140.44s**, alive 8, **0 deaths**.
Determinism note: keyed RNG, fixed scenario/ticks; the only time-dependent fields
are wall-clock diagnostics.

**#3 RESPOND_HELP firing [VERIFIED, and decisive]:** `respond_help_accepted = 0`,
`respond_help_rejected = 0`. RESPOND_HELP was **never even proposed** over 308
ticks — zero, not a collection gap.

**#4 recipient-side delivery [VERIFIED — corrects the Step 1 inference]:**
`requests_never_delivered_to_beneficiary = 17` (all), `delivered_then_evicted =
0`, `delivered_and_retained = 0`. `present_at_T1 = false` for **all 17** accepted
requests (e.g. `commitment-c15028f399747da5`, creator person-007 → beneficiary
person-001, created tick 43: present_at_T1 false, present_at_final false). The
beneficiary **never** holds the commitment — not delivered-then-evicted. This is
the mechanical cause of `#3 = 0`: RESPOND_HELP's precondition is the **responder
holding a pending request_help where `beneficiary_id == self`**
(`living_settlement_domain.py:330-333`); if the beneficiary never holds it, the
candidate is never generated.
> Code-vs-evidence: the accepted proposal's mutation **does** include the target
> `living_agent` with the commitment (`living_agent_social.py:333-336`, returned
> at `:524`) and the validator **permits** it (`:557-561`). So the commitment is
> *proposed for delivery* yet does **not persist** to the beneficiary's committed
> state — a same-frame overwrite, not a builder omission. The exact overwrite
> point is a named mechanism-gap (§13); pinning it needs domain instrumentation,
> which is out of bounds this phase.

**#1 need/geometry [VERIFIED]:** all 8 agents cross hunger≥600
(`first_tick_crossed_600`: person-006 t1, person-000 t13, person-005 t35,
person-001 t36, person-007 t41, person-003 t42, person-002 t44, person-004 t44;
`max_hunger` 620–906). **6 of 8 propose REQUEST_HELP** (person-001/002/003/004/
005/007); **person-000 and person-006 never do** despite crossing 600.

**#6 cooperate-source [VERIFIED]:** exactly **1** `social_cooperate` in the run —
tick 1, person-001 → person-007, goal **`HELP_PERSON`** (caretaker aiding the
injured scout), **not request-linked**. `0` `social_refuse`. Raw goal map:
`social_request_help|REQUEST_HELP:17`, `social_cooperate|HELP_PERSON:1`, plus one
each of repay|REPAY_DEBT, share_information|VERIFY_INFORMATION, trade|TRADE_RESOURCES,
promise|PROMISE_HELP, lie|SHARE_RUMOUR, threaten|THREATEN, apologise|APOLOGISE,
reconcile|RECONCILE.

**Net picture:** the legacy "aid exchange" is really **aid REQUEST generation
only** — a rich, organic, multi-agent, multi-dyad, recurring request substrate
with **no functioning response, delivery, or closure**.

---

## 6. Gate set (post FIX 1–3)

> These are the **organic-reachability acceptance gates** for the aid-exchange
> norm under Invariant 12(b) (a *new-decision-logic* post-build gate). The
> standard leg gate template (determinism; frozen `living_settlement` 320 hash;
> full regression; the integrated same-frame churn test; end-to-end causal-chain
> proof; ≥20% registry headroom; multi-seed robustness) applies **additionally**
> at Leg A implementation and is **not** part of this organic pre-registration.

- **G1 — Existence.** ≥1 organically *completed* aid exchange (request accepted →
  response accepted → the aid commitment reaches a terminal non-pending status)
  in the standing-scenario post-build run. **Provenance:** committed evidence =
  **0** completions (`respond_help_accepted=0`, 17/17 commitments immortal-pending
  and undelivered). ≥1 is the minimal falsifiable demonstration that the new
  machinery does what the legacy path cannot. A run of 0 completed exchanges
  fails G1 → rollback.
- **G2 — Norm formation.** The aid norm forms after **N** completed exchanges.
  **N is a DECLARED GAP.** N is set **once**, from the probe-build's *measured*
  completed-exchange distribution, with the derivation shown at calibration time.
  Per FIX 3, **no prior constant may be cited as an anchor, starting point, or
  tie-breaker**; the single Invariant-12(b) calibration allowance is spent on a
  measurement, not on confirming a pre-seeded number.
- **G3 — Episodic recurrence / stability.** ≥**K** completed-exchange *episodes*
  over the horizon (episode = a request→response→completion cycle bounded by the
  `due_tick = tick+8` window, `living_settlement_domain.py:322`). **K is a
  DECLARED GAP**, calibration-derived from the probe-build. **Provenance for the
  episodic form:** the committed request substrate is itself episodic — 2
  episodes at ticks 43–59 and 287–299 (§5) — so recurrence, not a single shot,
  is the honest stability shape (EXECUTION-PROTOCOL v1.1 declared-measure option).

**Enumerability (FIX 1):** the organic acceptance-gate set is **exactly
{G1, G2, G3}** — complete and enumerable, no gaps. There is no canonical "G3" in
STAGE-8-CONTINUATION-PROMPT.md or the 8A/8B gate sets to reinstate (those list
unnumbered gate *items*); the earlier v1 numbering (G1, G2, G4) is renumbered
contiguously here, and the former "G4" (≥2 dyads) is removed as a gate (FIX 2,
see §12).

---

## 7. Run length and cost model (arithmetic shown)

**Cost model** fitted to the 150-tick committed stderr checkpoints:
`T(n) ≈ 0.296·n + 0.000894·n²` seconds (fit points n=50→17.0s, n=100→38.5s
[meas 39.4], n=150→64.5s; quadratic because `valid_parent_ids` grows ~linearly,
so per-tick revalidation of the parent set is O(n²)).

**Chosen Phase B length: 308 ticks.** Rationale (stated before launch): the
pre-registered minimum and the derived complete-window minimum; projected
`T(308) ≈ 176s` gives a 3.4× margin under the 600s cap; all four CANNOT-yield
gaps resolve within 308 (both request episodes fall at ≤299).

**Actual vs projected [VERIFIED]:** 140.44s actual vs 176s projected — the model
**overestimates** (conservative). The response-side probe is faster than the
150-tick probe because it extracts scalars instead of deep-copying `entities`
every tick; window cost at tick 308 was 4.16s/10t vs the prior probe's 5.47s/10t
at tick 150. **Right-censoring:** none — the 308 run reached both request
episodes and stopped at `reached_target_ticks`, not a cap.

**Recommended length for any future post-build acceptance run:** 308–500 ticks,
10-minute wall cap, 10-tick checkpoints, incremental disk flush + finally-block
partial flush (the pattern this probe used; the prior 1000-tick attempt produced
a 0-byte file). Model bound `T(500) ≈ 372s`; the faster response-side probe will
run under that. 1000 ticks (`T(1000) ≈ 1190s`, at the 20-min edge) is not
recommended un-segmented.

---

## 8. Threshold provenance (gaps named as gaps)

| Threshold | Provenance | Status |
|---|---|---|
| Legacy REQUEST_HELP trigger `hunger≥600` | `living_settlement_domain.py:292` | CITED (sealed; must not be altered) |
| Social-action adjacency ≤1 | `living_agent_social.py:554-556` | CITED |
| Visibility range ≤4 | probe `VISIBLE_RANGE=4` ~ `living_agent_reasoning` | CITED |
| Enforcement relationship deltas | `RELATIONSHIP_DELTAS` `living_agent_social.py:30-33` (request_help {familiarity:20,obligation:20}; cooperate {trust:60,affection:30,respect:40,perceived_reliability:50}) | CITED (existing constants the consequence would ride) |
| New aid **arousal threshold** | — | **GAP** (undefined; a new parallel constant, never a Stage-6 edit) |
| Norm-formation count **N** (G2) | probe-build measured distribution | **GAP** (FIX 3: no prior-constant anchor) |
| Episode count **K** (G3) | probe-build measured distribution | **GAP** |
| Leg B interference tolerance | Phase B baseline (§10) now exists | partially fillable (§10); exact tolerance a Leg-B decision |

No threshold in this document is filled with a guessed number; every unmeasured
one is a named GAP.

---

## 9. Episodic stability measure (declared)

Request generation is **non-stationary and clustered**: Phase B shows 2 discrete
episodes (ticks 43–59, count 8; ticks 287–299, count 9) separated by ~228 idle
ticks. The stability measure is therefore **episodic, not steady-state**
(EXECUTION-PROTOCOL v1.1 declared-measure option): stability = **≥K
completed-exchange episodes** (G3), an episode being a request→response→completion
cycle bounded by the `due_tick = tick+8` window (`living_settlement_domain.py:322`).
The episode *definition* cites committed mechanics and the observed 2-episode
request structure; **K itself is a GAP** (calibration-derived, §6/§8).

---

## 10. Interference stance (with the Phase B baseline)

**Relation to the legacy family.** The new aid-exchange arousal threshold is
**distinct from and must not lower** the sealed legacy `hunger≥600`
(`living_settlement_domain.py:292`); it rides a **parallel** registry/hook, never
a re-priority of REQUEST_HELP (1200+hunger) or the (inert) RESPOND_HELP (3100).
Survival dominance (Invariant 6) is absolute: aid influence never outranks an
urgent survival decision.

**Leg B pre-change baseline at 308 ticks [VERIFIED] — fills the previously
declared tolerance GAP:**
- REQUEST_HELP: **17 accepted, 47 rejected** (46 `precondition.failed` /
  `living_agent_eq_failed`, 1 `social_action.not_adjacent`).
- RESPOND_HELP: **0 accepted, 0 rejected**.
- Accepted request dyads (5): person-001→000, 002→000, 004→000, 005→000, 007→001.
- Request episodes (2): [43–59], [287–299].
- Norm machinery active: `group_form_norm=1`, `group_adopt_collective_goal=2`.
- Survival: 8 alive, 0 deaths.
- Selected `accepted_by_type` rows: living_rest 2150, lifecycle_tick 2464,
  graze 289, update_association_registry 308, update_group_shared_state 299,
  structure_wear 122, living_move 91, living_consume 49, living_gather 41,
  living_drink 38, expire_signal 171, weather_transition 15, rest 14,
  living_repair 9, flee 5, social_request_help 17, social_cooperate 1.

**Acceptable redistribution for the Leg B interference run:** any that (a) keeps
the frozen `living_settlement` 320 hash byte-identical; (b) preserves
`collective_groups` determinism (repeat+replay+resume) and 0 deaths / 8 alive;
(c) does not reduce or reorder legacy survival candidates; and (d) holds the
above legacy counts (notably 17 REQUEST_HELP accepts and the 2-episode structure)
within a tolerance **pre-registered in the Leg B contract** against this baseline.
**Unacceptable:** any reordering that suppresses a survival candidate or moves a
frozen hash. The exact tolerance number remains a Leg-B-contract decision, but it
now has a committed 308-tick baseline (previously a GAP).

---

## 11. Reachability position (RESPONSE line updated to the measured result)

On committed evidence, in the standing scenario `collective_groups`:

- **REQUEST side — organic and rich.** 6 of 8 agents propose REQUEST_HELP; 5
  accepted dyads; 2 recurring episodes; all 8 cross hunger≥600. [VERIFIED, 308-tick]
  *(Corrects the Step 1 "single dyad / spread absent" — that was 150-tick
  right-censoring.)*
- **RESPONSE side — structurally inert.** RESPOND_HELP is **never proposed**
  (0 accepted, 0 rejected) because the request_help commitment is **never
  delivered to the beneficiary's committed state** (17/17, present_at_T1 false).
  [VERIFIED — was [LIKELY-live / UNKNOWN-firing] in v1; now measured inert.]
- **CLOSURE side — broken and sealed.** 0 completions; immortal-pending (§4 Q3);
  repairing it edits sealed Stage-6 behaviour and moves frozen hashes → out of
  bounds. [VERIFIED]
- **SPREAD — present.** 5 dyads across 2 episodes. [VERIFIED — corrects v1's
  "absent".]

**Position:** the aid-exchange norm requires decision logic that **cannot exist
before implementation** — a *working* delivery→response→completion handshake and
a formation trigger — none of which occurs organically today (0 responses, 0
completions), while the *request substrate it would ride is real, broad, and
recurring*. This is squarely **Invariant 12(b)**: reachability is a **post-build
acceptance gate** (§6), not a pre-build organic-extension probe. What changes it:
the parallel new family must supply its own delivery of "who was asked" (it
cannot rely on the legacy commitment reaching the beneficiary — §5/§13) plus a
response and a completion transition; the post-build run then tests G1–G3, with
rollback on failure after at most one calibration.

---

## 12. Known scenario limitations (FIX 2 — corrected for the Phase B evidence)

> **FIX 2 ruling applied:** the ≥2-dyad criterion is **not a gate**. Under
> Invariant 12(b) a gate exists so it can fail and trigger rollback; a criterion
> pre-classified as unreachable cannot fail, so it does not belong in the gate
> set. It is recorded here as an observation instead.

**Conflict flagged (must-report):** FIX 2's *stated premise* — "committed
evidence shows a single dyad, the blocker is scenario geometry, and the
standing-scenario decision is formally reopened" — was written on the 150-tick
data and is **falsified by the Phase B run the same directive authorized.**
Corrected facts:
- **Spread is present, not absent:** Phase B shows **5 accepted dyads across 2
  episodes with 6 distinct requesters** (§5). The ≥2-dyad criterion is
  organically **met** in `collective_groups` over 308 ticks. Per the FIX 2
  ruling this remains an **observation, not a gate pass**.
- **The blocker is not scenario geometry.** The dyad-scarcity blocker does not
  exist. The real limitation is that the **response/delivery/closure path is
  broken-and-sealed** (RESPOND_HELP inert via non-delivery; immortal-pending
  closure) — an implementation / sealed-legacy-defect matter, addressed by the
  new family under 12(b), **not** a scenario-geometry matter.
- **The standing-scenario decision does not need reopening on spread grounds.**
  `collective_groups` demonstrably produces multi-agent, multi-dyad, recurring
  requests; it is an adequate vehicle for the request substrate. Whether to
  reopen it for any other reason remains the user's standing call, but no dyad
  scarcity forces it.

I did not write the superseded "single dyad" claim into this document; the
divergence from FIX 2's premise is surfaced at the STOP for ratification.

---

## 13. UNRESOLVED

- **Beneficiary non-delivery mechanism (named mechanism-gap).** The accepted
  request proposal's mutation includes the target `living_agent` with the
  commitment (`living_agent_social.py:333-336,524`) and the validator permits it
  (`:557-561`), yet 17/17 never persist to the beneficiary (present_at_T1 false).
  The exact same-frame overwrite point is not resolvable by reading; pinning it
  needs domain instrumentation, which is **out of bounds** this phase. Recorded,
  not fixed. Design implication: the new family must own "who was asked" as its
  own canonical state.
- **Why person-000 and person-006 never request despite hunger≥600 (residual).**
  LIKELY higher-priority food candidates win for them (position/provisioning);
  the exact per-tick candidate-set reason is unmeasured (per-tick candidate sets
  were not recorded). Not rule gating (§4 Q2). Not gate-critical.
- **G2 `N` and G3 `K` — GAPS by design.** Set once at the probe-build's
  calibration from measured completed-exchange distributions (§6, FIX 3). Not to
  be pre-filled.
- **Leg B interference tolerance number.** Baseline now exists (§10); the
  tolerance value is a Leg-B-contract decision, not set here.

---

*End of pre-registration proposal (PROPOSED). No production code, no Leg A
contract, no ratification is implied by this document.*
