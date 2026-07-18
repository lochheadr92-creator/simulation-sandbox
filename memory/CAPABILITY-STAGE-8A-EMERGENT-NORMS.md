# Capability Stage 8A — Emergent Norms (smallest culture proof)

Status: **VERIFIED (mechanism), IMPLEMENTED & COMMITTED (2026-07-18). Gate-5
(organic influence firing): DEFERRED — organic-firing unobserved (scenario horizon
does not exercise the repair seam; evidence below). Stage 8A = partially complete
(core loop / mechanism-verified), NOT "complete".** Path A ratified.

This contract mirrors the 7B/7C/7D registry + validator + provenance + diagnostics
structure exactly and folds in the corrected-7D implementation lessons.

## Close-out (VERIFIED 2026-07-18)

**Verified results** (seed `living-agents-stage6`, all fixes in tree; actual run
output, not from memory):

- **Tests:** full backend suite **338 passed** (+4 pre-existing collection errors
  in `test_phase2/3/4` + `test_simulation_sandbox`, unrelated — they import a
  Docker-only `/app/frontend/.env`); Stage 8A focused **32 passed**; Stage 6+7A–7D
  focused all green.
- **Frozen-hash safety:** `living_settlement --ticks 320 --repeat 2` →
  `final_state_hash = 84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`
  **byte-identical** to the frozen baseline; `repeat_matches` + `replay_matches` = true.
  (`group_norm` is absent there and the influence hooks are inert without their
  registries, so Stage 6 is untouched.)
- **Determinism + organic proof:** `collective_groups --ticks 1000 --repeat 2` →
  `repeat_matches` + `replay_matches` = true; **0 deaths**; **7 `shelter_upkeep_norm`
  norms form organically** (all 7 recognised groups; first at tick 683), all active
  at end; `group_form_norm` accepted = 7. New `collective_groups` hashes:
  `final_state_hash = 659a27f3ec6a9cbaeb90206cf1198a1fa8e23abde00afa10978bc39e63920342`,
  `group_norm_summary_hash = 3f2e5b9ea7c0dba2acc6a3223b02a1f9656f9aba860f951fe11afae195a4aff2`.
- **Registry capacity:** peak serialized `group-norm-000` = **5,643 bytes** vs the
  24,576-byte payload target (**77% headroom**, ≥20% required) and 32,768-byte
  proposal cap; peak `group_progress` = 7 of 32; peak norms = 7 of 16.
- **Forbidden fields** (`inventory, authority, obedience, orders, law, command,
  punishment`) absent from every norm record (validator-enforced, tested).

**Gate-5 — DEFERRED (organic influence firing unobserved).** Over the 1,000-tick
run the norm influence fired **0 times**; so did the 7D goal influence (identical
cause). Tick evidence: shelter-`REPAIR_SHELTER` candidates exist on only **17 ticks,
all within ticks 1–236** (agents repair the initially-damaged shelter early, then
build private shelters and never repair the shared shelter again — the documented
Liveness self-solving dynamic). Norms cannot form until **tick 377+** (they require
≥2, here 3, distinct 7D adoptions, which require the shelter to *re-degrade* first —
adoptions begin at tick 282). The repair window (≤236) and the norm-active window
(≥377) are **disjoint**, so the read-only nudge has no already-existing
`REPAIR_SHELTER` candidate to boost. This is a scenario-horizon limitation, not a
mechanism defect: the influence firing IS proven through the real commit pipeline by
the integrated tests (a norm-holding member with a present repair candidate is
boosted, and it transmits to a want-less later joiner). Per the ratified Path A,
Stage 8A ships mechanism-verified with organic firing Deferred; NOT reframed and NO
threshold lowered to manufacture a firing (the `NORM_FORMATION_COUNT = 2` fallback
was measured too — it also yields **0** organic firings, first norm at tick 377,
because the disjoint-window cause is threshold-independent; so 3 is retained on its
recurrence merits). Evidence tooling: `backend/tools/_probe_norm_influence.py`
(firing + capacity), `_probe_repair_timing.py` (repair-vs-norm windows).

**Adversarial review — cross-model, automated (independence caveat, recorded).**
Two adversarial reviews were run by **Codex (OpenAI GPT-5)** as a separate CLI
subprocess, reviewing the Claude-authored diff; they were **orchestrated by the
implementing agent (Claude)** — dispatched, retrieved, and acted on by the same
agent that wrote the code — and were **not human-driven and not a fully independent
third-party audit**. It is genuine *cross-model* review (reviewer model ≠ implementer
model) and it surfaced **9 real defects** that were fixed and re-verified, so it was
materially more than self-review; but it is not an independent human audit and is
recorded as such (the master-prompt reviewer-independence flag).

**All 9 review findings — closed:**
1. Commit ordering / `stale_membership` — priority 87 commits before goal(88)/state(89)/assoc(90); integrated churn tests pass. ✅
2. `entity_updates` overlay hole (norm validator) — registry rejected if in both `new_entities` and `entity_updates`. ✅ (test)
3. Survival guard defeated by the scorer — both influence hooks moved **post-scoring**; compare/boost final `score_total`; stack cannot flip an urgent survival. ✅ (test)
4. Form-then-expire clobber at exact decay deadline — re-adoption refreshes any active norm (excluded from expiry), never form-then-expire. ✅ (test)
5. Compaction false-refresh — `_compact_registry` never evicts an active-norm group's progress (norms cap 16 ≤ tracked 32 guarantees fit). ✅
6. Stale-target refresh — refresh re-points the norm to the current 7D target. ✅ (test)
7. Unrederived `active_norm_count` — validator now re-derives and checks it. ✅ (test)
8. Marker-gated bypass (norm registry) — a marker-less write to `group-norm-000` is rejected. ✅ (test)
9. Byte-equality not truly enforced (Python `==` accepts `True`==`1`) — the **8A**
   validator now byte-compares canonical JSON and advances the *trusted* re-derived
   changes; `True`/`1` forgery rejected. ✅ (test).

Low-severity: the `refreshes` docstring/annotation drift (list-of-str → list-of-dict)
was corrected. Modified existing test (per contract-driven behaviour change):
`tests/test_stage7b_group_state.py` — its pinned `collective_groups.enabled_domains`
assertion now includes `"group_norm"`.

### Pre-existing findings NOT fixed here (out of Stage 8A scope — recommend a separate, user-authorised hardening pass)

The reviews noted that the **Stage 7A–7D validators share a malicious-proposal
threat surface** that predates 8A and is architecture-wide. These were deliberately
**NOT** touched, to honour the "do not touch 7A–7D; extend via new registries and
hooks only" guardrail (`STAGE-8-MASTER-PROMPT.md`). No honest domain triggers any of
them; 8A's own validator is hardened against all of them. Recorded for a future pass:

- **7D `entity_updates` overlay hole** — `validate_group_goal_proposal` does not
  reject the goal registry appearing in both `new_entities` and `entity_updates`. A
  defensive guard was drafted during review and then **reverted** to keep the 7D file
  byte-identical to HEAD; the hole is left recorded rather than patched inside an 8A
  commit. 8A reads the goal registry as canonical, so a future hardening pass should
  close it (and the byte-equality point below) across all group validators.
- **Structural vs. canonical-byte equality** — the 7D (and other group) validators
  use Python `==` for registry re-derivation, which accepts type-variant scalars
  (`True`==`1`). 8A's validator was upgraded to canonical-byte equality; 7A–7D were
  left unchanged.
- **Trusted `requested_time`** — `run_commit_frame` does not bind a proposal's
  `requested_time` to the actual commit tick; every group validator re-derives at the
  proposal-supplied time. Architecture-wide; a commit-pipeline-level check would be
  the fix.
- **Marker-gated validation** — a proposal that writes a registry *without* its
  domain marker bypasses that domain's validator. 8A now rejects marker-less writes to
  its own registry; the same pattern remains open for the other registries.

All four require touching Core/7A–7D and are outside the 8A boundary. They are the
malicious-hand-crafted-proposal threat model, not reachable by the honest kernel.

## Goal

Prove that repeated group behaviour crystallises into ONE bounded, canonical
**norm** that then influences member decisions and is inherited by later group
members — culture as *emergent state that affects behaviour*, never generated
descriptive text. This is the smallest honest step from "groups pursue a shared
goal" (7D) toward "groups carry shared norms." Exactly one norm type, one
decision-affecting nudge, nothing else.

## Why this behaviour, and why it is organically reachable (VERIFIED probe)

Stage 7D's `maintain_shared_shelter` goal is adopted organically in the 1,000-tick
`collective_groups` run. A per-group adoption probe (seed `living-agents-stage6`,
committed pipeline, 2026-07-17) measured:

- **22 adoption records across 7 distinct recognised groups**; per-group counts
  `[4, 3, 3, 3, 3, 3, 3]` — every recognised group re-adopts the shelter goal **≥3
  times**, one reaches 4.
- Adoptions recur in **waves ~306 ticks apart** (the weather/shelter-degradation
  cycle): the top group at ticks 282 / 376 / 682 / 776; the others at ~377 / ~683
  / ~777. So the 3rd adoption for a group lands ~tick 682–777, spanning **≥2
  distinct degradation cycles** — genuine recurrence, not one burst.

A norm that crystallises from *repeated adoption of that goal by the same group* is
therefore reachable in natural runs today, on the same organically-firing link 7D
proved. (7C stayed Stage-9-blocked because it needs surplus; 8A, like 7D, grounds
on `shared_shelter`, which fires now.)

## Chosen behaviour — `shelter_upkeep_norm` (`group-norm-v1`)

When a recognised Stage 7A group has adopted the Stage 7D `maintain_shared_shelter`
goal at least `NORM_FORMATION_COUNT` (=3) **distinct times** (counted by unique
adoption instance — see "Counting" below), a single canonical `shelter_upkeep_norm`
forms for that group, naming the group and the shelter the repeated goals targeted.
The norm:

- **affects decisions (read-only, member-grounded, transmission-inclusive):** a
  small bounded priority increment (`NORM_REPAIR_INCREMENT` = 150) to the
  `REPAIR_SHELTER` candidate — *for its norm shelter* — of **any current living
  member** of the norm-holding group, whether or not that member individually holds
  the `improve_shelter` want. It never creates a candidate a member lacks and never
  overrides an urgent survival decision (mirror the corrected 7D influence guard).
- **is transmitted:** the norm is group-scoped, so a member who joins the group
  after formation is covered without re-earning it — the seed of knowledge
  transmission. (No per-individual teaching yet — that is Stage 8B.)
- **decays / expires:** deterministically weakens then expires if the group stops
  adopting the goal for `NORM_DECAY_TICKS` (=300), or immediately if the group
  dissolves (no longer recognised).

## Agency model (no hidden group mind) — MUST hold

1. Proposal-only `group_norm` domain; **Core alone** validates and writes the
   registry. The domain evaluates a pinned frame and proposes at most one
   registry update per tick.
2. The norm forms only from **accepted-event history** (repeated 7D adoptions
   already committed by Core) — never from generated text, never invented.
3. Member-grounded: the norm cannot make a member do what they are incapable of
   (the `REPAIR_SHELTER` candidate must already exist) or override survival; it
   only nudges an already-available repair choice.
4. Bounded, versioned registry `group-norm-registry-v1`; provenance-stamped;
   deterministic; replayable. No new authority path. No caps raised on 7A–7D.

The group never scores privately, never owns a planner, never mutates member or
world state, and never commands. Transmission is *implicit via current membership*
only — no member is auto-included in any behaviour; a joined member is merely
*eligible* for the read-only nudge when they already have a repair option.

## How the norm forms — counting semantics (RESOLVED)

"Repeated adoption" counts **distinct adoption instances (re-adoptions)** of the
`maintain_shared_shelter` goal by the same group — NOT distinct shelters. Rationale
and mechanism:

- The 7D `goal_id = hash(group_id, goal_type, target_id)` is **stable** across
  re-adoptions of the same shelter; the 7D `adopted_via_key` (a.k.a. `goal_key`)
  includes `tick` and is therefore **unique per adoption instance**. Counting
  `goal_id`s would collapse all re-adoptions to 1 (there are only 1–2 shelters);
  counting adoption instances captures the *repetition* that is the whole point.
- The `group_norm` domain reads the Stage 7D `group-goal-000` registry each tick
  and, per group, tracks the last counted `adopted_via_key`. When the group's
  active goal shows an `adopted_via_key` different from the last counted one, that
  is exactly one new adoption instance → increment the group's `adoption_count`.
  Because keys embed `tick` (monotonic) and adoption is ≤1 per group per tick, an
  O(1) `last_counted_key` per group is sufficient and exact (no key set needed).
- When a group's `adoption_count` first reaches `NORM_FORMATION_COUNT`, the norm
  forms (once — one norm per group, idempotent by norm key).

## How the norm affects decisions without commanding

A live `shelter_upkeep_norm` is consumed by Stage 6 **only as read-only context**,
in a new `_apply_group_norm_influence` hook that runs at the same settlement
decision call site as the 7D hook, immediately after it:

1. **Inert without registry:** if no `group-norm-registry-v1` exists (e.g.
   `living_settlement`), return candidates unchanged — preserves the frozen Stage 6
   hash (same guard as the 7D influence hook).
2. Collect norm shelters: for each `active`/`weakening` (non-expired) norm whose
   `group_id` is a currently recognised group that **currently** contains
   `entity_id` as a member, add the norm's `target_id`. (Current membership is read
   from the association registry — this is where transmission to later joiners
   happens; there is deliberately NO `improve_shelter`-want requirement here.)
3. **Survival dominance:** for each `REPAIR_SHELTER` candidate targeting a norm
   shelter, if any survival-goal candidate already scores ≥ the repair candidate's
   base score, **skip** (never override an urgent survival decision); otherwise add
   `NORM_REPAIR_INCREMENT`. Survival scores are read from the unmodified survival
   candidates, so stacking with the 7D nudge cannot defeat the urgent-survival
   guarantee.

This is the crucial contrast with 7D: the 7D nudge required the member to hold the
`improve_shelter` want (personal, acute). The norm nudge applies to *any current
member* — that is culture carrying behaviour beyond the individual who originated
it. It remains member-grounded because it only boosts an *already-available*
`REPAIR_SHELTER` candidate.

## How the norm is transmitted (RESOLVED: group-membership-implicit)

Transmission scope is **group-membership-implicit** (no per-member record). The
norm lives in the registry keyed by `group_id`; influence eligibility is decided by
*current* association-registry membership at decision time. A member recognised
into the group after the norm formed is therefore covered automatically, and a
member who leaves stops being nudged. Per-individual teaching, imitation, and
generational transfer are explicitly deferred to Stage 8B.

## How the norm decays / expires (deterministic)

- On formation and on each subsequent counted adoption: `strength = 1000`,
  `last_adoption_tick = tick`, `decay_deadline_tick = tick + NORM_DECAY_TICKS`.
- Each evaluation tick with no new adoption: `strength =
  max(0, 1000 * (decay_deadline_tick - tick) // NORM_DECAY_TICKS)`; `status` is
  `active` while `strength >= NORM_WEAKENING_STRENGTH` (=500), `weakening` while
  `0 < strength < NORM_WEAKENING_STRENGTH`, and it **expires** (`status="expired"`)
  at `tick >= decay_deadline_tick` OR immediately if the group is no longer
  recognised (dissolved). Expiry is a Core-committed transition (like 7D goal
  expiry), not a silent drop.
- `NORM_DECAY_TICKS = 300` ≈ one observed degradation cycle, so a norm survives the
  normal re-adoption cadence but fades if the group genuinely stops re-affirming it.
  The goal TTL is 48, so a norm outlives ~6 goal lifetimes — correctly modelling
  culture as more persistent than any single goal.

## Commit ordering (THE critical 7D lesson — applied)

`group_norm` reads the Stage 7D `group-goal-000` registry. Commit order is by
`engine_priority` ascending (lower commits first): association **90**, group_state
**89**, group_goal **88**. The 7D `stale_membership` defect was caused by a domain
pinning an upstream registry's `revision` and committing *after* that upstream
churned it the same tick.

**Resolution:** `group_norm` runs at **`engine_priority = 87`** (`phase="agent"`),
committing **before** group_goal (88), group_state (89), and association (90). It
derives from the frozen pre-tick frame and pins the `revision` of association,
group_state, AND group_goal in its preconditions; because it commits first, those
pinned revisions still match at commit-time revalidation. The cost is a **documented
one-tick lag**: at tick T the domain sees group_goal's registry as of end-of-tick
T−1, so it counts each adoption exactly one tick after group_goal commits it. This
is deterministic and harmless over 1,000 ticks. (Same discipline as 7D committing
before 7A/7B; one level deeper.)

## Validation (re-derivation + byte-equality — applied)

Core's `validate_group_norm_proposal` mirrors the corrected 7D validator: it
re-derives the full `(formations, decays, expiries)` set from the current canonical
frame and requires **exact structural equality** with the proposal's metadata —
rejecting forged `norm_id`, `strength`, `formation_count`, `target_id`, `group_id`,
or `decay_deadline_tick`. Defence-in-depth per-norm invariants:
`norm_type == "shelter_upkeep_norm"`; `norm_id == group_norm_id(group_id,
norm_type)`; `formation_count >= NORM_FORMATION_COUNT` at formation;
`decay_deadline_tick == last_adoption_tick + NORM_DECAY_TICKS`; forbidden fields
`{inventory, authority, obedience, orders, law, command, punishment}` absent from
every norm; **one active norm per group**; registry byte-equal to
`advance_group_norm_registry(...)` recomputed from the frame; capacity ≤ cap.

## Proposed contracts

| Item | Value |
|---|---|
| Proposal type | `group_form_norm` (also carries decays/expiries in one registry update) |
| Proposal family | `group_norm` |
| Norm schema | `group-norm-v1` |
| Domain | `group_norm` (proposal-only; `engine_priority = 87`, before `group_goal` 88) |
| Registry | new `group-norm-registry-v1` (`group-norm-000`), created lazily on first formation |
| Influence | `_apply_group_norm_influence` + `NORM_REPAIR_INCREMENT` in `living_settlement_domain.py` |
| Scenario | reuse `collective_groups` (+ `group_norm` domain), no new seeding |

## Constants (determinism-visible — each justified)

| Constant | Value | Justification |
|---|---|---|
| `NORM_FORMATION_COUNT` | **3** | All 7 recognised groups re-adopt ≥3× over 1,000 ticks (max 4); 3 spans ≥2 degradation cycles (genuine recurrence, not a blip); below the empirical ceiling of 4 so formation is robust, not fragile. 5+ would form **zero** norms. |
| `NORM_DECAY_TICKS` | **300** | ≈ one observed ~306-tick degradation cycle: survives the normal re-adoption cadence, fades if the group stops re-affirming; norm outlives ~6 goal-TTLs (48). |
| `NORM_WEAKENING_STRENGTH` | **500** | Half-strength boundary between `active` and `weakening`; purely a reported status band, no behavioural cliff. |
| max norms per group | **1** | One canonical norm per group (analogous to 7D one-goal-per-group). |
| `norms` registry cap | **16** | Mirrors 7D `goals=16`; ≥7 groups → ≥55% headroom. |
| tracked `group_progress` entries | **32** | Bounded per-group adoption tally; ≥7 groups → ample headroom; compacted by recency if exceeded. |
| `NORM_REPAIR_INCREMENT` | **150** | Strictly below the 7D goal nudge (250): a norm is a diffuse cultural nudge, weaker than an acute active goal; large enough to observe, always survival-suppressed. |
| registry `payload_target_bytes` / `proposal_bytes` | **24 KiB / 32 KiB** | Mirror 7D; target < 32 KiB with ≥20% headroom. |
| `engine_priority` | **87** | Commit before group_goal (88) to avoid same-frame `stale_membership`; one-tick lag documented. |

## Registry schema (`group-norm-registry-v1`)

```
{ "type": "group_norm_registry", "schema_version": "group-norm-registry-v1",
  "revision": int, "norms": { norm_id: norm_record },
  "group_progress": { group_id: {"adoption_count": int,
                                 "last_counted_key": str|None,
                                 "last_adoption_tick": int} },
  "processed_norm_keys": [bounded], "created_tick": int, "last_updated_tick": int }
```
`norm_record`: `schema_version, norm_id, group_id, norm_type="shelter_upkeep_norm",
target_id, status, strength, formation_count, formed_tick, last_adoption_tick,
decay_deadline_tick, formed_via_key, created_event_id, last_event_id, revision,
pending_event_tick, pending_transition`.

## Explicit non-goals (Stage 8B+, NOT built now)

Multiple norm types; values, rituals, taboos, myths; per-individual teaching /
imitation; generational transfer; cultural divergence, diffusion, or conflict; norm
enforcement / punishment; norms that command or override survival; any economy,
institution, voting, or player-facing surface. Culture here is ONE emergent,
decision-affecting norm — nothing more.

## Acceptance gate (all required — mirrors the task brief)

1. **Focused `group_norm` tests:** formation threshold (forms at exactly
   `NORM_FORMATION_COUNT`, not before), one-per-group, member-grounded influence
   (skips non-member/dead; never overrides survival; boosts only an existing
   `REPAIR_SHELTER` for the norm shelter), **transmission to a later joiner**,
   decay→weakening→expiry (and dissolve-expiry), forged-field rejection
   (id/strength/count/target/ttl), replay equality, resume reconstruction,
   duplicate-key idempotence, capacity bound.
2. **Integrated full-kernel test:** `group_norm` enabled in the real commit
   pipeline forms ≥1 norm end-to-end **through same-frame upstream (7A/7B/7D)
   revision churn** (the ordering regression 7D's focused tests missed) — build a
   frame with association(90)+group_state(89)+group_goal(88) revision bumps plus the
   group_norm(87) proposal and assert the norm record ends `active`.
3. **Regression:** Stage 6 + 7A/7B/7C/7D suites stay green (currently 136 focused).
4. **Determinism:** two `collective_groups` traces match (repeat + replay + resume)
   with `group_norm` enabled.
5. **Organic proof:** a 1,000-tick unseeded `collective_groups` run forms ≥1
   `shelter_upkeep_norm` and shows the influence firing (measured), with survival
   dominant and 0 deaths.
6. **Frozen-hash safety:** `living_settlement` 320-tick hash unchanged
   (`84d3ad52…c32d2` — `group_norm` absent there, influence inert). Record the new
   `collective_groups` hashes.
7. **Adversarial review before promoting status** (Codex or equivalent) against the
   branch diff — do not mark Stage 8A "verified" until it passes review through the
   real pipeline.

## Open design decisions — RESOLVED

- **`NORM_FORMATION_COUNT` / `NORM_DECAY_TICKS`:** 3 / 300 (justified above from the
  per-group adoption probe).
- **"Repeated adoption" semantics:** distinct adoption instances (re-adoptions),
  deduped by `adopted_via_key` per group — NOT distinct shelters. Drives O(1)
  per-group `last_counted_key` tracking.
- **Transmission scope:** group-membership-implicit (current association membership
  at decision time); no per-member record until Stage 8B.

## Implementation lessons applied (from the 7D adversarial review)

1. Commit ordering chosen deliberately (`priority 87`, before group_goal) with the
   prior-frame / one-tick-lag semantics documented — avoids `stale_membership`.
2. **Integrated full-kernel test is mandatory** (gate item 2) — not focused-only;
   drives the enabled domain through the real pipeline with same-frame churn.
3. Validator rejects forged fields by re-derivation + byte-equality.
4. One norm per group; simultaneous norms capped; never one-per-event.

## Risks / limitations — RESOLVED / RECORDED (2026-07-18)

- **Organic influence-firing — measured 0, RECORDED as Gate-5 Deferred** (see
  Close-out). The pre-implementation hypothesis (members still repairing the
  shared shelter after norm formation) was **disproved by measurement**: repairs
  cease by tick 236, norms form at 377+, the windows are disjoint, so the nudge has
  nothing to boost. The `NORM_FORMATION_COUNT = 2` fallback was measured too and
  also yields 0 firings (threshold-independent cause), so it was NOT taken; 3 is
  retained on recurrence merits. The mechanism is proven via the integrated
  full-kernel tests. Reaching organic firing would require a scenario/liveness
  change to keep the shared shelter under active upkeep in the norm window — out of
  Stage 8A scope, and it would perturb the `collective_groups` trace; deferred by
  ratified decision, not shimmed.
- The 7D goal influence has the identical organic-inertness in this scenario
  (`goal_influence_firings = 0`); this is a pre-existing scenario property, not
  introduced by 8A.
- Enabling `group_norm` perturbs the `collective_groups` trace (new domain,
  one-tick-lag reads) — new hash `659a27f3…920342` recorded; the frozen
  `living_settlement` hash is byte-identical (`84d3ad52…c32d2`, domain absent there).
