# Capability Stage 8C, Leg A — Aid Exchange (delivery, response, completion)

**Status: PROPOSED — awaiting user confirmation (with riders) before any
implementation.** Drafted 2026-07-24 under the authority granted by the ratified
Phase 1 pre-registration (`STAGE-8C-PHASE1-PREREGISTRATION.md`, RATIFIED
2026-07-24). No production code exists for this leg.

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

*End of Leg A contract proposal (PROPOSED). Confirmation with riders is the
user's act; implementation starts only after that confirmation, phase-gated per
EXECUTION-PROTOCOL.*
