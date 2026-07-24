# Capability Stage 8C, Leg A — Aid Exchange (delivery, response, completion)

**Status: DEFERRED — Stage-9-blocked (ruled at STOP, 2026-07-24).** Two
implementation attempts ran the pre-registered post-build gate (Invariant
12(b), culture list); both failed G1 and were rolled back per the ratified
rule — attempt 1 on the observation-window recording defect (fixed by
amendment A1), attempt 2 on measured scarcity: no agent holds carried food ≥ 2
at request time, so the A2-guarded RESPOND_AID candidate can never fire, and
no calibration threads the ≥1-death / ≥2-starves pincer (see the attempt-2
record below). **No Leg A code is committed; the branch carries docs and
evidence only.** Concrete Stage 9 dependency: a reliable food surplus so a
responder can afford the minimum give (carried food ≥ 2 at request time) —
the same wall as Stage 7C. Register rows: `CAPABILITY_ROADMAP.md` §Global
deferral register; `MACRO-ROADMAP.md` §Deferral ledger. What Stage 9 revives:
the full v2 build (A1 priority-5 relocation with the recording fix proven,
A2 keep-one guard, A3 constant 3334, 4 wiring points, 33 tests, both probes),
committed as [`memory/evidence/stage-8c-lega/lega_v2_full.patch`](evidence/stage-8c-lega/lega_v2_full.patch)
(the cloud finding note's content is captured in the attempt-2 record below).

Original status (historical): CONFIRMED (2026-07-24) — user approval;
implementation authorized, phase-gated per EXECUTION-PROTOCOL. Riders
resolved at confirmation: **D3**
`respond_aid` candidate priority = **3100 by citation** of the legacy
RESPOND_HELP constant (sealed provenance, not a new number); **D6** registry
`engine_priority` = **85** (next culture-ladder slot). All other decisions
confirmed as proposed. The D5 ordering analysis remains a blocking
implementation-time task, and N/K remain calibration GAPs — confirmation does
not fill them.

Drafted 2026-07-24 under the authority granted by the ratified Phase 1
pre-registration (`STAGE-8C-PHASE1-PREREGISTRATION.md`, RATIFIED 2026-07-24).
No production code exists for this leg at confirmation.

- **Branch:** `capability/stage-8c-phase1-aid-exchange` (rebased onto 8B Leg 1
  close-out `1c78b9df`; base tip at drafting `8b0d23b2`).
- **Evidence base (all committed):** the 308-tick Phase B run
  (`memory/evidence/stage-8c-leg1/probe_8c_response_side_308.json`), the 150-tick
  request-side run, CORE-INTEGRITY-001 (`CORE-INTEGRITY-001-lost-update.md`,
  DISPOSITIONED 2026-07-24: accepted-as-recorded, remediation deferred), and the
  8B Leg 1 close-out corpus.
- **Authority:** STAGE-8-CONTINUATION-PROMPT.md → CLAUDE.md invariants (culture
  list; per CI-001 F3, every invariant citation below names its list) →
  EXECUTION-PROTOCOL.md → the ratified pre-registration.
- **Labels:** VERIFIED / LIKELY / GAP as elsewhere. No GAP is filled with a
  guessed number.

---

## 1. Player-visible outcome (the point of the leg)

Today the event log shows people asking for help — 17 accepted requests over 308
ticks, across 5 dyads and 2 recurring episodes — and **nobody ever answers**:
zero responses, zero completions, every request an immortal dangling promise
[VERIFIED, Phase B]. After this leg, the player watching the standard
`collective_groups` run sees, in the event log and the causal-chain walker, at
least one full arc: *person X asks for help → person Y responds → the aid is
delivered → the exchange closes* — and, after enough completed exchanges, an
aid norm forming in the inspector. Pre-flight finding A (event rendering is
generic, no whitelist) guarantees the new events are observable with zero
frontend work [VERIFIED].

User story: *as a player, I can watch a hungry villager ask for food and watch
another villager actually help them — and see the exchange complete — without
inspecting internal state.*

## 2. Why this shape (constraints inherited from evidence)

- The legacy response path is **broken and sealed**: RESPOND_HELP never fires
  because request commitments never persist to the person being asked (17/17
  `present_at_T1=false`) — a CORE-INTEGRITY-001 F1 same-frame lost update on the
  person entity. Repairing that is remediation (deferred, re-baseline-gated).
  Therefore the new family **owns "who was asked" as its own canonical state**
  and never relies on person-held commitments for its lifecycle. [VERIFIED basis]
- Singleton Category-2 registries are single-owner by validator and are **not**
  the F1-exposed surface (CI-001 §6). The exposed surface is the person entity —
  so registry state is safe; any person write this leg proposes is the one place
  F1 discipline applies (D5).
- The request substrate is organic and rich (6/8 requesters, 5 dyads, 2
  episodes) — the leg **rides it, never edits it**. `hunger≥600`, REQUEST_HELP
  priority 1200+hunger, and the inert RESPOND_HELP (3100) are sealed constants
  [CITED, pre-reg §8].

## 3. Decisions for confirmation (D1–D8)

**D1 — Family shape.** New proposal-only domain `aid_exchange` with one
singleton registry `aid-exchange-000` (`aid-exchange-registry-v1`), created
lazily. Schema (v1): `revision`; `open_requests` keyed by `request_id`
(`requester_id`, `responder_id`, `opened_tick`, `due_tick`, `source_event_id`);
`completions` (bounded ledger: `request_id` → `response_event_id`,
`completed_tick`, `delivered` flag); `processed_request_event_ids` (bounded,
FIFO); `completed_exchange_count` (the G2 counter); `aid_norm` (absent until
formed; then `formed_tick`, `formation_count`); `created_tick`,
`last_updated_tick`. Validator restricts `entity_updates` to the registry id for
all lifecycle writes (Category-2 single-owner pattern, per group_carriage
`:618`-style scope gate), with the single D5 exception. Forbidden fields
(culture list): never in any record.

**D2 — Trigger source.** The domain observes **accepted legacy
`social_request_help` events from the prior frame** (T/T+1 lag, standard
prior-frame semantics) and opens a registry request per event, idempotent via
`processed_request_event_ids`. No new arousal threshold is needed on the request
side — the measured organic driver is the sealed legacy trigger. The pre-reg §8
"aid arousal threshold" GAP therefore attaches to the **influence** hook, which
is **out of Leg A scope** (D8) — the GAP survives, unfilled, to that later leg.
`due_tick = opened_tick + 8`, provenance: the legacy commitment window
(`living_settlement_domain.py:322`) [CITED]. Expiry is a registry-local
transition (`expired`), never a person write and never a sanction (forbidden
fields).

**D3 — Response candidate.** An **additive** candidate `respond_aid` in the
living-settlement candidate set, generated for a person who is the
`responder_id` of an open, unexpired registry request (prior-frame read),
adjacency-gated like all social actions (≤1) [CITED]. This is the 8B-precedented
seam: a guarded additive edit to `living_settlement_domain.py` (as the 8A→8B
membership→carriage influence swap was), **not** an edit to the sealed
RESPOND_HELP, which remains inert and untouched. Candidate priority: **GAP at
drafting** — proposed to cite the legacy RESPOND_HELP constant 3100 as
provenance (an existing sealed constant, not a new number), placing response
above routine actions but below urgent survival; survival dominance (culture
invariant 6) is absolute and unmodified. Rider requested: confirm 3100-by-citation
or direct a measured derivation.

**D4 — Completion and norm formation.** When a `respond_aid` action commits, the
domain (next frame) marks the request completed, increments
`completed_exchange_count`, and — after **N** completions (G2; N is a GAP filled
once at calibration, FIX 3 no-anchor rule) — writes the `aid_norm` record **in
its own registry**. It does not touch `group_norm` (extend-only seal; aid is
settlement-scoped co-location behaviour, not group-membership behaviour).

**D5 — Material delivery (the one person-write, and the F1 discipline).** A
completed exchange must be *felt*, not just recorded — the 8B lesson ("machinery
in the pipeline, not felt culture") and Gameplay-First both demand it. On
completion the domain proposes one material-transfer mutation: responder
`carried_resources` decremented, requester hunger relieved (exact fields and
magnitudes to be fixed at implementation from the committed eat-action
constants, cited not invented). Precedent: Stage 7C proposes direct person/
storage mutations without owning a registry. F1 discipline (per the CI-001
disposition): the write carries **field-level eq preconditions** on every
written field plus two-party `alive` guards, so a stale same-frame collision
**rejects cleanly and retries next frame** rather than silently losing either
write; and the leg's integrated churn test (culture invariant 11 — the test-
shipping mandate) must include the same-frame case: material transfer + the
target's own actor-update in one frame, asserting the deterministic outcome.
**Ordering analysis is a blocking implementation-time task:** CI-001 §6 shows
the actor update writes `hunger`/`living_agent` unguarded every proposal, and
commit order is `(requested_time, phase, engine_priority, content_hash)` — the
transfer's `engine_priority` must be chosen **after reading living_settlement's
actual priority** so the transfer applies on the surviving side of any
collision, verified by the churn test, never assumed. This is exactly the 7D
ordering-defect class; it gets a named test, not an assumption.

**D6 — Engine priority (registry lifecycle).** The `aid_exchange` registry
domain takes the next culture-ladder slot **85** (below group_carriage 86),
consistent with the later-stage-commits-earlier rule for registry writes. The
D5 transfer proposal's priority is decided separately per the ordering analysis
above. Rider requested: confirm 85.

**D7 — Bounded state (culture invariant 4).** Caps set at implementation from
measured peaks with derivation shown: open requests peaked at 7 outstanding
(150t) and 17 total accepted (308t) [VERIFIED], so caps of the form
`open_requests ≤ 4× measured peak`, `processed_request_event_ids` FIFO 96 (the
existing family constant, cited), `completions` ledger bounded with
prune-to-terminal discipline (the F3-eviction lesson from 8B: never evict a
record still load-bearing). Byte budget: `payload_target_bytes` sized at
implementation with the invariant-4 **≥20% headroom** bar measured by probe,
8B-style. Exact numbers land in the implementation phase with their derivations;
none are invented here.

**D8 — Non-goals (Leg A).** No influence hook (no nudge-to-respond; that is the
later leg carrying the arousal-threshold GAP). No edits to sealed legacy:
`hunger≥600`, REQUEST_HELP, RESPOND_HELP, commitment lifecycle all untouched. No
CORE-INTEGRITY-001 remediation. No cross-scenario work (`living_settlement`
stays inert for this domain — frozen 320-tick hash must remain byte-identical).
No forgetting/expiry-punishment semantics (forbidden fields). No generational /
teaching pathway (8D).

## 4. Acceptance gates

Standard leg template [binding]: determinism (`collective_groups` repeat +
replay + resume); frozen `living_settlement` 320 hash byte-identical; full
regression suite; the integrated same-frame churn test **including the D5
collision case**; end-to-end causal-chain proof (request event → response event
→ completion → norm formation traversable in `/runs/{id}/events` and the chain
walker); registry ≥20% headroom by probe; multi-seed robustness.

Ratified organic gates (pre-reg §6, post-build, one calibration allowance,
rollback on failure):
- **G1** ≥1 organically completed exchange (request accepted → response accepted
  → terminal non-pending status) in the standing-scenario post-build run.
- **G2** aid norm forms after N completed exchanges — N set once from the
  probe-build's measured completed-exchange distribution, derivation shown, no
  prior-constant anchor.
- **G3** ≥K completed-exchange episodes over the horizon — K calibration-derived
  the same way; episode bounded by the due-window definition (pre-reg §9).

Interference: the post-build run must hold the ratified 308-tick baseline shape
(pre-reg §10) — 17 REQUEST_HELP accepts and the 2-episode structure within the
tolerance that the Leg B contract will pre-register; unconditionally: no frozen
hash movement, no survival-candidate suppression or reordering, 8 alive / 0
deaths preserved.

Run plan: 308–500 ticks, 10-minute wall cap, 10-tick checkpoints, incremental
flush (the Phase B pattern; the cost model `T(n) ≈ 0.296n + 0.000894n²` bounds
T(500) ≈ 372s, and the response-side probe ran 20% under model) [CITED].

## 5. UNRESOLVED at drafting (named, not guessed)

- N (G2) and K (G3) — GAPs by design until calibration.
- `respond_aid` candidate priority — D3 rider (3100-by-citation vs measured).
- Transfer-side engine priority — blocked on the implementation-time ordering
  analysis (D5); a named churn-test case, not an assumption.
- Exact cap and byte-budget numbers — implementation-time, derivation-shown (D7).
- The influence-leg arousal threshold — inherited GAP, out of scope here.

---

---

## Implementation attempt 1 (2026-07-24) — gate FAILED; disposition at STOP

Cloud clone build (Ubuntu/Py3.11/Mongo 8.0.4 rs0), never applied to canonical
mainline; full patch preserved (delivered 2026-07-24, `lega_implementation.patch`,
1,769 lines). All figures VERIFIED from pasted run output.

**Built per contract:** `aid_exchange_contracts.py` (684 lines) +
`aid_exchange_domain.py` + 30 focused tests + the four wiring points +
the D3 additive candidate. Focused tests 30/30; full suite **400 passed /
4 skipped / 0 failed** (Mongo parity, concurrency clean); frozen
`living_settlement` 320 hash **byte-identical** (`84d3ad52…c32d2`) with all
new code present; `collective_groups` determinism repeat+replay TRUE
(1000-tick hash with aid enabled: `79ba1f94…0f56` — never a baseline).

**Calibration (the single 12(b) allowance) — SPENT, user-authorized at a STOP:**
RESPOND_AID priority 3100 → **3334** = 3100 (rider D3 citation) + 233 (max
measured RESPOND_HELP score advantage; 350-tick diagnostic probe
`_probe_8c_lega_completion_diag`: 23/23 shadowed decisions, gap 74–233) + 1.
Reading conflict recorded: pre-reg §6 wording can be read as reserving the
allowance for the G2-N measurement; ruled at the STOP that N/K-filling is
pre-registered GAP-filling, the allowance is the one post-failure adjustment.

**Calibration effect — VERIFIED organic:** RESPOND_AID selected (ticks 45–46);
**1 accepted `social_give`** (tick 46, person-001 → person-007, inside the
44–52 due window). The full request → respond → deliver arc fired for the
first time.

**Gate result (probe `_probe_8c_lega_gate_metrics`, 1000 ticks):**
- **G1 FAIL — completed_exchange_count = 0.** The physically delivered give was
  never recorded: completion detection reads the responder's committed
  `action` at T+1, but the priority-85 validator re-derives against mid-frame
  mutated entities (CI-001 §7 seam, inherited from the carriage template), and
  the responder's next action overwrites the give first →
  `aid_exchange.metadata_mismatch` ×13. One-frame detection window, lost every
  time; requests then expire (5 opened / 5 expired / 0 completed). Same seam
  undercounts opens (5 vs 44 accepted requests).
- **Interference FAIL — 1 death.** person-007 dies tick 153; counterfactual
  run without aid_exchange: 0 deaths (VERIFIED, not root-caused). Material
  aid redistributes food under scarcity; the giver's loss propagates. The
  unconditional 0-deaths constraint is in structural tension with material
  aid — a design finding, not a tuning miss.
- **Invariant-4 PASS:** peak registry 1,730 B vs 24,576 B target →
  **92.96% headroom**.
- G3: 0 completion episodes (distribution empty). N and K remain GAPs —
  never derived, since no completion distribution exists.

**Prescribed disposition (ratified pre-reg + spent-calibration rider):**
G1 failure after the calibration ⇒ **rollback of the capability from
mainline**. Mainline was never touched — rollback = do not apply the patch;
this record and the preserved patch + probes are the attempt's evidence.

**Redesign findings for any Leg A v2 (contract-amendment territory, not
calibration):** (1) completion detection must not depend on the volatile
accepted-action field surviving into mid-frame validation — the recording
evidence needs a durable carrier (this is CORE-INTEGRITY-001-adjacent seam
behaviour, shipped identically in group_carriage, where it merely rate-limits
rare transmissions rather than zeroing the gate); (2) a giver-protection
guard (e.g. give only when carried food ≥ 2) with measured provenance is the
candidate answer to the aid-caused death; (3) the pre-reg's "RESPOND_HELP
structurally inert" finding is ordering-contingent and falsified once a new
domain shifts collision winners — delivery sometimes persists and RESPOND_HELP
fires (it shadowed RESPOND_AID at equal priority pre-calibration).

**RULED at the STOP (2026-07-24): ROLLBACK + RECORD.** The user upheld the
ratified rule. Attempt 1 is closed: mainline untouched, patch + probe evidence
preserved, this record is the durable memory. Leg A returns to design; any v2
proceeds only as a ratified contract amendment carrying the two findings
(durable completion evidence; giver-protection guard). The Stage 8C frontier
is unchanged — next 8C action is the v2 amendment, at the user's initiative.

*End of attempt-1 record.*

---

## Contract amendment 1 — Leg A v2 (2026-07-24)

**Status: RATIFIED (2026-07-24) — user approval ("as proposed"). Ratified in
full (A1–A5), including the A4 ruling: v2 is granted its own single
evidence-based calibration allowance under Invariant 12(b) [culture list];
attempt-1's spent allowance carries no debt forward.** Drafted at the user's
"next leg" direction after the attempt-1 rollback. Amends the CONFIRMED
contract; everything not amended here stands as confirmed. Implementation of v2
is authorized, phase-gated per EXECUTION-PROTOCOL; no production code exists at
ratification.

**A1 — Observation-window relocation (supersedes rider D6; the durable-evidence
fix).** `aid_exchange` moves from `engine_priority = 85` to **`engine_priority
= 5`, phase "agent"**. Grounds, from committed code read this session:
`run_commit_frame` is a **single sorted validate-and-apply pass** (one
`for proposal in ordered:` loop; order `(requested_time, PHASE_RANK,
engine_priority, content_hash)`), and validators re-derive against
progressively-mutated entities (CORE-INTEGRITY-001 §7). At 85, every
person-action evidence field is overwritten by living_settlement (priority 10)
before the aid validator runs — the attempt-1 gate-killer (`metadata_mismatch`
×13; opens undercounted 5 of 44). At 5, the aid proposal validates after the
environment phase (ecology 0, lifecycle 1) but **before any agent-phase person
writer** (living 10, animal 20), so the validation state for `action` fields is
identical to the frozen frame the domain derived from — byte-exact
re-derivation becomes structurally guaranteed, not collision-lucky. Residual,
documented: a same-frame death (environment phase, writes `action`) can void
one detection deterministically — clean reject, no retry, acceptable. Slot 5 is
unoccupied; implementation ships a test asserting the ordering property
(aid validates before any person-action mutation in-frame). The culture-ladder
rationale that placed 85 (pin-upstream-registries) does not apply: this
domain's upstream evidence is person actions, not later-priority registries.
Note for the record: `group_carriage` (86) shares this seam for its
transmission trigger and survives only when the actor's same-frame proposal
happens to reject — sealed, out of scope here, flagged for a future
core-integrity follow-up.

**A2 — Giver-protection guard (the death fix).** The RESPOND_AID candidate
requires **carried food ≥ 2** (gives 1, always keeps ≥ 1). Provenance: the
attempt-1 measured aid-caused death (tick 153; counterfactually absent without
aid — VERIFIED), plus the structural finding that material aid moves survival
risk onto the giver. The threshold is the minimal keep-one rule, not a tuned
number. The v2 gate re-verifies the unconditional 0-deaths constraint on the
full 1000-tick run.

**A3 — Constants carried forward as ratified.** RESPOND_AID priority **3334**
enters v2 as a contract constant with its attempt-1 derivation (3100 rider
citation + 233 max measured shadow gap + 1) — recorded evidence, not a
fresh-calibration spend.

**A4 — Fresh calibration allowance — RULED: GRANTED (2026-07-24).** v2 is a new
pre-registered build under invariant 12(b) [culture list] with its **own single
evidence-based calibration allowance**; attempt-1's spent allowance does not
carry debt forward. The user upheld this reading ("as proposed") at
ratification; the alternative (zero allowance → straight to rollback on any gate
failure) was declined.

**A5 — Gates unchanged, evidence reset.** G1/G2/G3 exactly as ratified; N and
K remain calibration GAPs; interference baseline and the 0-deaths constraint
unchanged; every standard-template item re-runs fresh on the v2 tree (all
attempt-1 run evidence is void for v2 purposes). Non-goals (D8) unchanged.

*End of amendment 1 (RATIFIED 2026-07-24).*

---

## Implementation attempt 2 — v2 (2026-07-24) — G1 FAILED; DEFERRED at STOP

Built per the ratified amendment 1 (A1 `engine_priority = 5` phase "agent",
A2 carried-food ≥ 2 keep-one guard, A3 RESPOND_AID 3334, A5 fresh gate) by a
parallel cloud session; delivered as a 4-patch series — committed as evidence
at [`memory/evidence/stage-8c-lega/lega_v2_full.patch`](evidence/stage-8c-lega/lega_v2_full.patch)
(patch 1/4 docs, 2/4 v1 implementation, 3/4 spent calibration, 4/4 the A1+A2
v2 amendments) — with the finding note (`scratchpad/LEGA_V2_CLOUD_FINDING.md`,
canonical machine; content captured in this record). Reproduced on the canonical machine
2026-07-24 by applying the backend patches to the working tree at `12b034a8`
(never committed), running the gate, then reverse-applying — tracked diff
empty afterwards. Deterministic kernel: canonical reproduction matched the
cloud run number-for-number (headroom to two decimals).

**What the build proved (VERIFIED, canonical run output):**

- **A1 fixed the attempt-1 recording defect.** Request opens 20/20 detected
  (attempt 1: 5 of 44); completion recording survives same-frame overwrite in
  the churn fixture. The observation-window relocation is sound and is the
  design to revive at Stage 9.
- **Focused tests 33/33 pass** (incl. the A1 ordering-property test and the
  A2 keep-one boundary pair: absent at food=1, present at food=2).
- Frozen `living_settlement` 320 hash byte-identical; `collective_groups`
  repeat+replay true; registry headroom **75.64%** (peak 5,986 B) —
  invariant-4 (culture list) PASS. [cloud-verified; headroom reproduced
  canonically]
- **A2 held the unconditional constraint: 0 deaths, 8 alive** (attempt 1's
  aid-caused death does not recur).

**Gate result (canonical, 1000 ticks, wall 922.32s):**

```
G1 FAIL — final_completed_exchange_count = 0
requests: 20 opened → 20 expired → 0 completed
respond_aid_selections = 0; social_give_accepted = 0
episode_count = 0  (G3 empty; N and K underivable — no completion distribution)
deaths 0 / alive 8; headroom 75.64%
```

**Root cause (VERIFIED, diag probe in the patch):** the only agent ever asked
(person-001, responder to every person-007 request) holds **exactly carried
food = 1** for the entire request window — adjacent, requester visible, itself
unpressured. A2 requires ≥ 2. person-000 holds 0. The two food=2 genesis
endowments are consumed before requests begin (~tick 44). No agent reaches
food ≥ 2 at request time.

**Why the A4 calibration allowance was not spent:** there is no legal target.
Threshold food ≥ 1 re-creates the attempt-1 aid-caused death (measured);
food ≥ 2 never fires (measured); the give amount is already the minimum (1);
N/K cannot be derived from an empty distribution. Lowering thresholds to
manufacture a firing is forbidden (protocol §On missing data). The allowance
lapses unspent with the deferral.

**RULED at the STOP (2026-07-24): DEFERRED — Stage-9-blocked.** Rollback per
the ratified rule: canonical mainline never carried the code; the working-tree
application was reverse-applied (tracked diff empty). Evidence preserved:
patch + finding note (scratchpad, canonical machine), canonical gate/test
outputs pasted here. Revival at Stage 9 re-enters at the v2 design — the
mechanism is fully proven except for an economy in which anyone can afford
to give.

*End of attempt-2 record. End of Leg A (deferred).*
