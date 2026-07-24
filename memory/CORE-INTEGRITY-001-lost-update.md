# CORE-INTEGRITY-001 — Silent same-frame lost update

**Status: DISPOSITIONED (2026-07-24) — findings ACCEPTED as recorded; remediation
DEFERRED.** User ruling at the post-8B-close-out STOP: F1/F2/F3 stand as verified
findings; no remediation inside any culture leg (per §7, repairing F1 changes
which writes survive → moves the frozen `living_settlement` 320 hash and the
`collective_groups` baseline, so repair requires its own separately authorized
core-integrity stage with an explicit re-baseline). Until then, the interim
containment discipline applies — **reclassified 2026-07-25 (review finding
IND-C10, ruling by Ryan): this is necessary interim discipline, NOT sufficient
containment; residual risk register P10-1..10 in
`scratchpad/core-integrity-review/adversarial_review_report.md`:**

1. New state lives in single-owner Category-2 registries (§6: not the exposed
   surface).
2. Any person-entity write a leg proposes must carry field-level eq guards —
   eq on EVERY top-level key the mutation writes, not merely some eq
   (P10-4/P10-9) — plus integrated churn-test coverage for the same-frame
   overwrite class (§9).
3. Every leg's churn matrix must include at minimum: a non-actor
   `living_agent` overwrite, a death+HELP `health` collision, and an
   out-of-scope write attempt (P10-6).
4. Legs must keep `entity_updates` ⊆ `touched_scope` as a leg-level rule even
   though the pipeline does not enforce it (F2, P10-7).
5. No two legs/domains may write the same person field (dual-write ban,
   P10-2).
6. "Field-level" means top-level entity key; a writer with nested-path partial
   intent must eq-guard the whole key and handle merge explicitly (P10-5).
7. Per F3, directives must qualify invariant numbers with a namespace
   (C-N culture list vs SOT-19.N).

**Independent adversarial review: RAN 2026-07-25 (reviewer: Grok/xAI,
cross-vendor; independence accepted).** Report + findings ledger + Ryan's
rulings: `scratchpad/core-integrity-review/adversarial_review_report.md`.
Probe re-runs 2026-07-25 semantically identical to committed evidence
(IND-JSON closed); packet copies identical to `memory/evidence/stage-8c-leg1/`
(IND-PATH closed). The stage7a/7b concurrency intermittency is scoped OUT of
this finding → `memory/CORE-INTEGRITY-002-CONCURRENCY-CAS.md`.

Original status (historical): PROPOSED — findings only. No remediation proposed;
repair is separately authorized after disposition. Sealed Stage 6 / core / frozen
hashes.

- **Date:** 2026-07-22 · **Branch:** `capability/stage-8c-phase1-aid-exchange`
  · **Base SHA:** `002a18a4`.
- **Discovered during:** Stage 8C Phase 1 aid-exchange measurement (the
  beneficiary-non-delivery of request_help commitments, 17/17).
- **Evidence artifacts (committed under `memory/evidence/stage-8c-leg1/`):**
  `probe_8c_pipeline_write.json` (F1, F2), `probe_core_integrity_death_scope.json`
  (death path, F2, determinism); probes `backend/tools/_probe_8c_pipeline_write.py`,
  `backend/tools/_probe_core_integrity_death_scope.py`.
- **Method:** synthetic proposals handed to the public commit entry
  `run_commit_frame`; NO engine/domain/kernel/core file modified, no monkey-patch,
  no domain engine invoked. Verdicts are execution evidence, not code readings.
- **Labels:** VERIFIED (executed/committed), LIKELY (supported, not directly
  measured), GAP (named, unfilled).

---

## 1. Summary and classification

The commit pipeline provides **no structural protection against same-frame lost
updates**. When two accepted proposals in one frame write the **same top-level
field of the same entity**, `apply_mutation` performs a shallow, last-writer-wins
`dict.update` — the earlier write is **silently discarded, no error raised**. The
only guard is a per-proposal `eq` precondition, which is opt-in; an unguarded
writer bypasses it. Three findings:

- **F1 — Silent lost update.** A validated write persists at commit and is
  overwritten by a later same-frame write to the same field. [VERIFIED]
- **F2 — `touched_scope` is not enforced.** A proposal can write an entity it did
  **not** declare in `touched_scope`; the write is accepted and persists. Every
  domain-scope declaration in canon is therefore unverified. [VERIFIED]
- **F3 — Canon invariant-number collision.** "Invariant N" is ambiguous: two
  independent numbered lists exist in canon. [VERIFIED]

Classification of the originating aid case: **(b) lost update** — ruling out
(a) discard and (c) aid-specific (see §3).

---

## 2. Mechanism (with citations)

- **Core apply path — `core/mutations.py:14-25` `apply_mutation`:**
  ```
  for eid in sorted(entity_updates):
      if eid in entities:
          entities[eid].update(updates)     # line 23 — shallow, per top-level key
  ```
  A shallow `dict.update`: it replaces whole top-level keys, does not merge nested
  sub-dicts, applies **every** `entity_updates` key that exists (no `touched_scope`
  filter), and raises nothing on a conflicting overwrite. "Only this module mutates
  `entities`" (`core/commit_pipeline.py:7`); it is called at
  `commit_pipeline.py:462` after per-proposal precondition revalidation.
- **`living_agent` is one top-level key.** A commitment lives at
  `entity["living_agent"]["commitments"][...]`; overwriting `entity["living_agent"]`
  wholesale drops it.
- **Real exploiter — `living_settlement_domain.py:734`:**
  `actor_update["living_agent"] = resulting_state`, where `resulting_state` derives
  from `state` = the actor's `living_agent` taken from the **frame snapshot**
  (`:528`). This runs for **every** settlement proposal. Non-social (physical)
  actions carry **no `living_agent` eq precondition** (build_physical_action_proposal
  guards `alive`/resources/condition — `living_agent_actions.py:293-294,321,344,469`
  — never `living_agent`; `_replace_living_preconditions` at `:666/488-491` only
  substitutes *existing* `living_agent` preconditions). So a person that is
  delivered an aid commitment and then acts later in the same frame overwrites its
  own `living_agent`, dropping the commitment.

---

## 3. Pipeline probe evidence — F1 (`probe_8c_pipeline_write.json`)

| Sub-test | Result | Establishes |
|---|---|---|
| 1 — non-actor write, in `touched_scope` | `nonactor_field_persisted: true` | non-actor writes ARE applied → **(a) refuted** |
| 3 — write to entity NOT in `touched_scope` | `out_of_scope_field_persisted: true` | no scope gate → **(a) refuted again**; F2 |
| 2a — lone delivery of a commitment to a non-actor beneficiary | `beneficiary_has_SYN_COMMIT: true` | the delivery write itself is applied |
| 2b — + a later UNGUARDED same-frame write to the same `living_agent` | both accepted, **0 rejected**, `beneficiary_still_has_SYN_COMMIT_after_frame: false` | **(b) lost update — silent overwrite, no error** |

**(c) ruled out:** the behaviour reproduces on arbitrary synthetic entities via the
generic apply path; it is not aid-specific. **VERDICT (from the probe):**
`"(b) lost update: validated write persists at commit, overwritten by a later
same-frame write to the same field"`.

---

## 4. `touched_scope` enforcement — F2

`check_scope_exists` (`commit_pipeline.py:107`) verifies that declared
`touched_scope` entities **exist**; nothing constrains `entity_updates` **keys** to
`touched_scope`, and `apply_mutation` (`mutations.py:20-23`) iterates all keys.

- `probe_8c_pipeline_write.json` subtest 3: proposal with `touched_scope=["person-007"]`
  and an `entity_updates` write to `person-002` → **accepted, persisted**.
- `probe_core_integrity_death_scope.json` `F2_out_of_scope_write`:
  `declared_touched_scope: ["person-007"]`, `wrote_undeclared_entity_person_002: true`.
  [VERIFIED, both]

Consequence: a proposal's declared scope is not a containment boundary. Any domain
can write any existing entity's fields regardless of its declared scope. This is a
**containment finding independent of F1** and is escalated as its own item.

---

## 5. Death-path exposure (`probe_core_integrity_death_scope.json`)

Death (`lifecycle_domain.py:151-172`) writes `alive`, `current_goal`, `health`, …
as top-level fields, guarded only by `{alive eq True}` (`:164`). `HELP_PERSON`
(`living_agent_actions.py:484-486`) writes a target's `health`/`energy`, guarded by
adjacency only — **no `health`-eq precondition, no commit-time alive re-check**.

| Sub-test | Result | Meaning |
|---|---|---|
| D1 death alone | `alive:false, current_goal:DEAD, health:0` | death applies fully in isolation [baseline] |
| D2 death → health | both accepted; `alive:false, health:500`; `corrupted_death…: true` | **a person can end alive=False with NON-ZERO health** |
| D3 health → death | both accepted; `alive:false, health:0` | consistent — **outcome is ordering-dependent** |
| D4 death → `alive:True` | `alive:true, current_goal:DEAD, health:0`; `pipeline_permits_unkill: true` | pipeline **structurally permits un-kill** (partial/Frankenstein state) |

**Is the death path exposed to F1? YES** — D2 produces a corrupted death
(alive=False + health=500), and the outcome flips with commit order (D3).

**Is that sufficient to explain zero-deaths-under-starvation? NO — not even
necessary.** F1 corrupts a death's *fields*; it does not *prevent* the death
(alive stays False in D2). Masking a death requires flipping `alive` back to True
(D4 shows the pipeline permits it), but **no domain writes `alive:True` on an
existing person** — grep finds `alive:True` only in `new_entities` (shelter,
`people_planning.py:515`) and perception records (`perception.py:142,225`); the
only person writer of `alive` is death itself (`lifecycle_domain.py:166`, →False).
So real deaths are corruptible but not maskable. The observed zero-deaths (308-tick
run; a prior 169-tick diagnostic) is fully consistent with the **benign**
explanation: agents recover hunger (308-run hunger peaks 620–906 then falls to
246–564 by tick 308), so health (`lifecycle_domain.py:99` fires death only at
`health <= 0`) never reaches 0 and **no death proposal is generated**.

**I do NOT claim F1 explains the historical zero-deaths bug** — there is no
evidence linking a corrupted-death to an absent-death. [VERIFIED exposure; benign
explanation LIKELY; historical-link NOT established]

---

## 6. Field-collision map (person entity, grep-enumerated)

Per top-level person field: the domains that write it, whether the write carries an
`eq` precondition **on that field**, and whether an unguarded same-writer overlap
exists (the exposure). Writes are grep-cited; whether a given overlap is *exercised*
in a real frame is separate (only `living_agent` is confirmed exercised — §3, aid
17/17).

| Field | Writers (file:line) | Guarded on the field? | Exposed |
|---|---|---|---|
| `living_agent` | living_settlement_domain.py:734 (actor, every proposal); living_agent_social.py:335/336/350/370/461 (actor+target); people_domain.py:389 (disabled here) | settlement:734 **NO** (non-social); social **YES** (two-party living_agent eq, social.py:316-319) | **YES** — confirmed exercised (aid) |
| `health` | lifecycle_domain.py:140 (tick), :166 (death); living_agent_actions.py:485 (HELP target) | lifecycle guards `{alive eq}` not `health`; HELP guards adjacency only | **YES** — proven (D2) |
| `energy` | living_settlement_domain.py:678 (actor); living_agent_social.py:423 (cooperate target); living_agent_actions.py:486 (HELP target), :488 (actor) | none guard `energy` | **YES** (structural) |
| `current_goal` | living_settlement_domain.py:304/734-path (actor); lifecycle_domain.py:166 (death); animal_domain.py:105/146; people_domain.py:388 (disabled) | settlement **NO**; death guards `{alive eq}` | **YES** (structural) |
| `action` | living_settlement (actor); lifecycle_domain.py:168 (death); animal_domain.py:105/147 | none guard `action` | **YES** (structural) |
| `position` | living_settlement (move, actor); living_agent_actions.py:361 (pickup target) | none guard `position` | **YES** (structural) |
| `knowledge` | living_settlement_domain.py:680 (actor); living_agent_social.py:444 (lie target) | none guard `knowledge` | **YES** (structural) |
| `hunger`/`thirst` | living_settlement_domain.py:678 (actor); living_agent_actions.py:421 (eat, actor, guards `carried_resources`); people_domain (disabled); animal (animal entity) | none guard `hunger`/`thirst` | LOWER — mostly single-writer per person/frame |
| `plan` | living_settlement_domain.py:694 (actor); lifecycle_domain.py:170 (death) | none guard `plan` | **YES** (structural) |
| `injury` | lifecycle_domain.py:140/166 | `{alive eq}` | single-writer (lifecycle) |
| `alive` | lifecycle_domain.py:166 (person, →False only) | `{alive eq}` | **NO real overwrite** — no domain writes person `alive:True` |

Category-2 (singleton registries: association, group_state/collective/goal/norm/
carriage) each write only their own `*_REGISTRY_ID` and their validators restrict
`entity_updates` to that id (group_state_contracts.py:693, group_norm:604,
group_goal:515, group_carriage:618), so registries are single-owner and not the
exposed cross-writer surface. The exposed surface is the **person entity**.

---

## 7. Frame-ordering determinism and the frozen-hash consequence

Proposal application order across a frame is **deterministic**:
`ordered = sorted(all_proposals, key=order_key)` (`commit_pipeline.py:335`), with
`order_key = (requested_time, PHASE_RANK[phase], engine_priority, content_hash)`
(`:103-104`); `content_hash` is a pure function of proposal content
(`normalize_proposal`, `:65-96`). `apply_mutation` also sorts keys
(`mutations.py:16,20,24`). The probe confirms by execution:
`DET_frame_ordering_determinism.identical: true` (D2 run twice → identical final
state). [VERIFIED]

**Consequence, stated plainly:** because the ordering — and therefore *which* write
survives each collision — is deterministic, the lost-update outcomes are baked into
the committed state and its hashes. **All frozen baselines and green determinism
results encode this defect.** *(Wording corrected 2026-07-25 per review finding
IND-C8 — the original "necessarily move the frozen hashes" was an overclaim.)*
Repairs that alter which writes survive currently exercised collisions (e.g.
merging sub-dicts, rejecting conflicting writes) — or that change
ordering-relevant proposal content, since preconditions feed `content_hash`
and thus commit order — **will move the affected frozen baselines** (the
`living_settlement` 320 hash and/or the `collective_groups` baseline).
Scope-only fixes (e.g. enforcing `touched_scope` on scenarios that never emit
out-of-scope keys) **may be hash-stable**. Whether a given repair moves a
baseline is an empirical question: prototype the fix on a throwaway branch and
re-hash the frozen scenarios. Remediation therefore requires a **measured-hash
gate** — an authorized re-baseline wherever post-repair hash ≠ frozen — and
cannot be done inside a culture leg.

---

## 8. Canon invariant-number collision — F3

Two independent numbered invariant lists exist in canon; a bare "invariant N"
resolves to different content depending on the document.

- **Culture-invariant list (12 items)** — agrees across three docs:
  `CLAUDE.md:46-57` ("Invariants (verbatim from the master protocol)"),
  `STAGE-8-CONTINUATION-PROMPT.md:164-177`, `EXECUTION-PROTOCOL.md:87-130` (generic
  form). Minor wording differences, same meaning per number.
- **`SOURCE-OF-TRUTH-v2.md:566-584` §19 (17-item "No X" safety list)** — a
  different list entirely.

Collision table (representative; the divergence is systematic for every N in 1–12):

| N | Culture list (CLAUDE.md:46-57 et al.) | SOURCE-OF-TRUTH-v2.md §19 (:568-584) | Agree? |
|---|---|---|---|
| 1 | Core alone writes truth; domains proposal-only | :568 One mutation authority: only Core-accepted events mutate canonical state | THEME-ALIGNED, different text |
| 2 | Determinism (repeat/replay/resume; keyed RNG) | :569 No accepted event lacks deterministic identity | DIFFERENT |
| 3 | Every transition provenance-stamped, event-caused | :570 No accepted event lacks deterministic order | DIFFERENT |
| 4 | Bounded state; ≥20% headroom; never raise a cap | :571 No state-changing import without accepted events | DIFFERENT |
| 6 | Influence read-only, never outranks survival | :573 No external influence affects truth unless normalized/recorded/validated/accepted/replayed | DIFFERENT |
| 7 | Forbidden fields: inventory, authority, … punishment | :574 No domain engine writes canonical storage | DIFFERENT |
| **11** | **integrated full-kernel same-frame churn test** (CLAUDE.md:57; STAGE-8-CONTINUATION:176) | **:578 No receipt replaces accepted events inside the recent replay horizon** | **DIFFERENT** |
| 12 | Organic reachability (v2) | :579 No checkpoint valid without source ranges + hashes | DIFFERENT |

The SOT §19 list continues 13–17 (projection/administrative rules) with no
culture-list counterpart. **Any directive citing a bare invariant number is
ambiguous** between the two families; this is the concrete harm F3 flags (it already
occurred with "invariant 11", §9). Note: **none** of the SOT §19 invariants forbids
the lost update either — §19.1 (Core authority) and §19.3 (deterministic order) both
hold; there is no canon invariant asserting "no accepted write is silently
overwritten by another accepted write in the same frame."

---

## 9. Invariant 11 analysis (as reported at the finding)

Verbatim, with the multiple canonical numberings:
- **CLAUDE.md:57** — "11. Every leg carries the integrated full-kernel same-frame
  churn test."
- **STAGE-8-CONTINUATION-PROMPT.md:176** — "11. Focused tests are never sufficient:
  every leg carries the integrated full-kernel churn test — the class of defect 7D's
  focused tests missed." (`:43` names the defect family: "same-frame ordering
  (`stale_membership`)".)
- **SOURCE-OF-TRUTH-v2.md:578** — a *different* invariant 11: "No receipt replaces
  accepted events inside the recent replay horizon" — **not violated**, unrelated.

The culture invariant 11 is a **test-shipping mandate**, not a substantive
no-lost-update guarantee — it is **silent** on whether lost updates are permitted.
The measured behaviour is **exactly the defect class** that its churn test exists to
catch. So this is **not a literal violation** of invariant 11's text; it is a
**coverage gap** — the shipped churn test does not exercise a same-frame non-actor
`living_agent` (or `health`) overwrite. (This reading was accepted as correct at the
finding.)

---

## 10. What this does NOT establish

- **Not** that F1 explains the historical zero-deaths-under-starvation bug — no
  evidence links a corrupted death to an absent death; the benign hunger-recovery
  explanation is supported (§5).
- **Not** that every field-collision in §6 is *exercised* in a real run — only
  `living_agent` is confirmed exercised (aid 17/17); the rest are structural
  exposure (multiple unguarded writers exist), pending a run-trace.
- **Not** that the death path is ever *reached* in the standing scenario — no death
  proposal was observed (health never hit 0); death is reachable only in principle
  (`lifecycle_domain.py:99-100`).
- **Not** whether the behaviour is intended or a defect at the design level — canon
  is silent (§8); reported as a defect-class exposure.
- **No remediation is proposed or designed** — out of scope by instruction.

---

## 11. UNRESOLVED

- The exact per-frame commit order for the 17 real aid cases (which writer wins) is
  inferred from the mechanism + measured 17/17 loss, not per-frame traced. GAP.
- Which of the §6 structural collisions actually fire in production runs (needs an
  instrumented run-trace, which would require domain instrumentation — **not done**,
  out of bounds). GAP.
- Whether any Category-2 registry is ever multi-written within a single frame
  (single-owner by validator, but not exhaustively proven across all frames). GAP.
- Remediation and its re-baseline consequence (§7) — separately authorized after
  disposition. GAP.

---

*End of CORE-INTEGRITY-001 (PROPOSED). Findings only; no remediation, no engine
change, no Leg A / Phase 1 continuation is implied by this document.*
