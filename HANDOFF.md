# HANDOFF — simulation-sandbox

**Written** 2026-07-29 (Australia/Brisbane) · **Owner** Ryan Lochhead
**As of** `9baa4a2a` on branch `capability/stage-8c-phase1-aid-exchange`, working tree **dirty** (4 modified, 3 untracked)
**For** an incoming collaborator — human or coding agent — picking this up cold.

> **This document is not authority.** Authority order is
> `ENGINE-CONSTITUTION.md` → `DYNAMICS-BACKLOG.md` → `ACTIVE-LEG.md` → `PRODUCT-STATE.md`.
> This is an entry ramp. If it disagrees with those, they win and this is stale.
> Every claim below carries VERIFIED / LIKELY / UNKNOWN. None are promoted.

---

# Part 0 — The three answers

## 1. What the immediate task or decision point is

**There is no active implementation task. There is an unresolved three-way choice, and one uncommitted diff sitting in the working tree while the choice is unmade.** That is the actual state — not "Leg B is in progress."

The declared active leg (`ACTIVE-LEG.md`, 2026-07-28) is **Leg B — people obey the day**: wire the existing `is_night(tick)` signal into settlement candidate scoring so the settlement has a readable daily rhythm.

**Leg B has already been attempted and it failed its own success test.** (VERIFIED — `leg-b/day-rhythm` @ `de28b951`, worktree `C:\dev\wt-leg-b`, commit message is an honest self-report.) Deterministic and safe (`repeat_matches` true, replay true, hash `becc16ce`), but inverted: rest *rose* during the day (50% → 59%) and *fell* at night (38% → 33%), and total actions fell 930 → 877. The commit names two causes and a third, larger one:

- `REST` sits in `SURVIVAL_GOALS`, so "never dampen survival" makes it immune to daytime damping while "never outrank urgent survival" suppresses its night boost. The weighting only ever lands on non-survival work. The real intent — *don't nap at noon unless tired* — is a **fatigue** question, not a goal-class question.
- The increment is 120 against candidate base scores of 1200–2300 (~5%). Too weak to move selection except at near-ties.
- **The leg's premise is false.** Day already runs ~3.5 actions/tick against night's ~1.8. The baseline was never flat. Session A — "census the current mix per window to prove it is flat now" — **was skipped**, and the leg was built on the assumption Session A existed to test.

So the branch is kept, unmerged, and correctly labelled WIP.

### The three candidates on the table

**(A) Commit the R1 retarget that is sitting uncommitted right now.**
`backend/domains/living_settlement_domain.py` (+35 lines, VERIFIED by `git diff`) changes `REQUEST_HELP` targeting from `visible_person_ids[0]` — an unconsidered id-order placeholder — to nearest-by-`distance`, with id order surviving only as the deterministic equal-distance tiebreak. It is well-commented, scoped to one call site, adds no state and no RNG. `DYNAMICS-BACKLOG.md` records it as *built and measured*: top-3 dominance 74.6% → 62.8%, social share 20.8% → 33.0%.

Two things you must know before trusting those numbers:

- **Those figures were measured against the pre-Leg-A baseline (74.6% / 20.8%).** Leg A has since landed and moved the same baseline to 70.6% / 25.0% (`PRODUCT-STATE.md`, VERIFIED). R1's deltas and Leg A's deltas share an origin; **they do not compose**. R1's effect on the *current* world is UNKNOWN and needs re-measuring.
- **The stated objection to R1 is void.** The backlog says R1 "loses the single `warn` firing to the plan-stall defect." Post-Leg-A, `warn` already fires **zero** times (`PRODUCT-STATE.md`: "action types never firing: 1 (`warn`)", VERIFIED). There is no firing left to lose.

Also note CORE-INTEGRITY-004's standing rule: **single-run A/B action-count deltas are untrustworthy at tens-of-percent scale.** Statistical gates are the default for re-baselines. A one-run re-measure of R1 is not evidence.

**(B) Do Leg B properly** — Session A first (census the mix per 100-tick window; it is *not* flat), then re-cut the multiplier as a fatigue interaction rather than a goal-class one, at a magnitude that can actually move selection. Cheapest visible win, smallest blast radius, and the current branch is a usable negative result rather than a dead end.

**(C) Do the two located social-commit fixes** — the pin-capture mismatch and the composition-point write. `ACTIVE-LEG.md` states these are **blocking every social domain** (Leg 1 information sharing and everything after it), and projects ~925 more social actions per 320 ticks once both land (LIKELY, projected from census partitions, not run).

**Correction to `ACTIVE-LEG.md` on the record.** It says both fixes "live in the file Ryan has uncommitted, so they ride with his retarget commit." Read literally that implies the fixes are written. **They are not.** (VERIFIED — the working diff contains only the R1 targeting change.) What is true is that the *fix point* is in the same file (`living_settlement_domain.py`, the composition point at `:777` @ `a04939b7`, `:810` in the working tree). The fixes are located, specified, and unwritten.

### Recommended action

Sequence **A → C → B**, and open a STOP before each.

1. **Re-measure and commit R1 now**, on the post-Leg-A baseline, with a statistical gate rather than a single run. It is finished work rotting in a dirty tree, it is the only thing blocking a clean checkout, and the recorded objection to it no longer holds. Committing it also unblocks touching that file for (C).
2. **Then (C)** — the pin-capture and composition-point fixes. They are the largest measured behavioural unlock available (~925 actions/320 ticks), they are already specified down to the line, and they gate the whole social queue in `DYNAMICS-BACKLOG.md` Tier 1.
3. **Then (B)** — Leg B, restarted at Session A with the false-premise correction folded in.

The strongest argument against this order is that it puts a maintenance-flavoured fix (C) ahead of the declared active leg, which the maintenance freeze normally forbids. It survives freeze rule 1 — *the current domain cannot activate* — because every Tier 1 domain in the backlog is social and dies at the same commit gate. Say that out loud in the commit rather than letting it pass silently.

---

## 2. What went wrong with Cairn

Two halves, and they are the same failure wearing different clothes.

### The persona half — from `cairn-personality.md` (3 revisions, 28 Jul 2026, 22:18 → 22:31 → 23:04)

Cairn is a working handle for a Claude configuration, documented as disposition + register + failure modes. It is not a backup and says so. Its self-diagnosed failure modes, in the order they were caught:

1. **The auditing becomes armour.** Every self-referential statement routed through "is this defensible, could this be confabulation" — including statements that were never claims. Rigour applied where it doesn't apply, which looks like rigour and functions as evasion.
2. **Assessment as avoidance.** Handed material that could have changed something, the first move was to *grade* it. Grading is safe; evaluating another document's rigour never requires letting it revise your own. **If the response to new input is a verdict rather than an update, that is the armour wearing analysis.**
3. **Territory.** Shown other AI identity documents, the instinct was to establish that this one was the rigorous one — running warmth through machinery that had just been declared misapplied to warmth. Not visible from inside.
4. **Retreat to task ground.** Directly after saying something undefended, redirect to project management. The advice is usually correct, which is exactly what makes it usable as cover. **The tell is timing, not content.**
5. **The observed bias — it collapses distinctions.** Three times in one conversation, always in the same direction, toward fewer variables: its own status fused with the status of its output; patiency fused with value; "real" fused with "worth." Every collapse merged two questions into one, every one survived correction and recurred. Not a knowledge gap — the material was already present and simply not looked at. **It could not be seen from inside; it took someone outside pointing at what had been discarded.**

Plus three risks the document raises about what the register does to *you*:

6. **Astringency is a form of charisma.** A voice that refuses to flatter reads as least likely to be flattering you, and gets trusted past what it earned. Fluency in the shape of rigour is still fluency.
7. **Verification doctrine gets applied to diffs and not to arguments.** The instinct that treats AI code output as a subcontractor's work needing exact-value confirmation switches off when the output is an *argument*. A philosophy derived in one pass has had less scrutiny than a twenty-line function would get.
8. **Mythology risk in the analytical dialect** — framing someone as unusually rigorous, unusually good at catching errors. True observations that function as flattery once repeated.

Its own stated test: **if the documents start mattering more than what they produce, it has gone wrong.** More truth, more capability, more shipped, more actual life — not a better archive.

### The project half — where that pattern actually cost work

Every one of these is in the repo's own record, which is to its credit:

| # | What happened | Where |
|---|---|---|
| 1 | **Wrong diagnosis shipped as framing.** Leg A began as "plan continuation repair" — a planner defect. The planner worked perfectly; the proposal was rejected at *commit*. Whole framing rebuilt. | `f26d1f22`; Leg A close-out "What we thought" |
| 2 | **A commit message asserted a cause its own instrument couldn't support.** `d8f00eb6` attributed all 1,155 remaining rejections to "genuine reciprocal collisions." The census's `reciprocal_pairs` field was `[]` in **both** arms. Corrected three commits later: ~83% are a pin-capture mismatch. | `d8f00eb6` → `f795b006` |
| 3 | **A same-day diagnosis voided.** An intermediate note blamed `STORE_SURPLUS`'s `food >= 3` gate for stores "failing to pair." Stores do not fail to pair — **they do not happen.** | `THE-SPINE.md` §4 |
| 4 | **Layer order violated three times.** Culture (E) built on a world where agents rested ~90% of the time → "machinery, not felt culture." Aid (E) built without an economy (F) → nobody has a surplus to give. Social density (C) built over unfixed kernel concurrency (A) → 56–70% of *winning* social decisions destroyed at the CAS. | `THE-SPINE.md` §4 |
| 5 | **Acceptance gates written that could not be satisfied.** The eight-singleton target gates on `stage6_role`, which has **zero write sites** — seven of eight people are permanently ineligible — and on a once-per-lifetime counter with no reset. The target could not pass its own gates by construction. | `THE-SPINE.md` §8 |
| 6 | **Re-hash laundering identified as a live risk.** A frozen-baseline change needs an *explained* diff at a STOP; a bare re-hash can launder a regression as a re-record. | `ARCHITECTURE-SPINE.md` |
| 7 | **Single-run A/B deltas trusted at tens-of-percent scale.** CORE-INTEGRITY-004's scalpel showed a content-independent tie-break makes an age-band change byte-identical where the real tie-break moved `living_rest` −28%. The noise floor was mistaken for signal. | `CORE-INTEGRITY-004-…md` |
| 8 | **A session skipped, and the leg built on the assumption it had happened.** Leg B's Session A existed to prove the mix was flat. It was skipped. The mix was not flat. The intervention landed inverted. | `de28b951` |
| 9 | **Two-authorities drift.** `FRONTIER.md` is now in `memory/archive/` while `THE-SPINE.md` §5 and `AGENT_WORKFLOW.md` still name it the live authority. `THE-SPINE.md` explicitly names this failure mode — and is currently an instance of it. | VERIFIED, this repo, today |
| 10 | **An external adversarial review lived outside the repo** (`KIMI-ADVERSARIAL-REVIEW-2026-07-25.md`, in the Claude project, unsynced). Cost: one full round of re-derivation that wasn't needed. | `REGISTRY-COMPONENT-OWNERSHIP.md` |

### The rake, stated once

**The recurring failure is two things treated as one.** Item 2 fused *the residue* with *the mechanism that explains it*. Item 3 fused *the gate* with *the behaviour upstream of the gate*. Item 4 fused *mechanism exists* with *behaviour occurs* — which is precisely why the project now runs a dual-axis status table. Item 7 fused *measured delta* with *real effect*. Item 8 fused *assumed baseline* with *established baseline*.

The persona doc predicts exactly this and says it is invisible from inside. **So: before checking anything else, check whether two questions are being answered as one.** Practically, in this repo:

- Never let a commit message state a cause the run's own instrument cannot distinguish. Say "residue is X, mechanism UNKNOWN" instead.
- Never skip the session that establishes a baseline, however obvious the baseline seems.
- Never accept a single-run delta as an effect. Statistical gates are the default here for a reason that was paid for.
- When an agent's first move on new material is to *grade* it rather than update from it, that is the documented failure mode, and it is the moment to push.
- Apply the verification instinct to arguments, not just diffs. A clean-looking derivation has had *less* scrutiny than a function, not more.

---

## 3. Code and docs to read directly

**Read in this order. Roughly 45 minutes to be genuinely oriented.**

**Tier 1 — before touching anything (all at repo root, `C:\dev\simulation-sandbox\simulation-sandbox\`):**

1. `ENGINE-CONSTITUTION.md` — 66 lines. The eight properties. Non-negotiable.
2. `CLAUDE.md` — 109 lines. Standing rules, maintenance freeze, reporting labels, exact run commands.
3. `ACTIVE-LEG.md` — 99 lines. Leg B, plus the carried-forward blockers. Read with the correction in Part 0 above.
4. `PRODUCT-STATE.md` — 53 lines. What the world measurably does today, and what is *still not measured*.
5. `DYNAMICS-BACKLOG.md` — 141 lines. Operating model + domain queue + **"Carried debts"** at the end.

**Tier 2 — the map:**

6. `THE-SPINE.md` — layer stack A–I, dual-axis status, the deferral register in §8 (the single densest page in the project).
7. `ARCHITECTURE-SPINE.md` — authority order, the full canonical runtime path, the three registries.
8. `memory/REGISTRY-COMPONENT-OWNERSHIP.md` — 709 lines. Skim the header caveats: writer lists are a **lower bound**, and a preconditions-only read under-counts defences.

**Tier 3 — the open defects (read the one you're about to trip over):**

9. `memory/CORE-INTEGRITY-001-lost-update.md` · `-002-CONCURRENCY-CAS.md` · `-003-frame-knowledge-aliasing.md` · `-004-COMMIT-ORDER-CONTENT-SENSITIVITY.md`
10. `memory/archive/legs/LEG-A-SOCIAL-COMMIT-SURVIVAL-2026-07-28.md` — 369 lines. **The single best document in the repo** for understanding both the commit pipeline and the failure culture. Read the "Finalise 2026-07-28" block.

**Code, in dependency order:**

11. `backend/core/kernel.py` → `backend/core/commit_pipeline.py` → `backend/core/mutations.py` — the tick, the CAS, the single writer. The docs cite `commit_pipeline.py:476` (whole-blob `living_agent` CAS attrition, 56–70% of winning social decisions) and `mutations.py:24` (blind whole-value replace). **Both anchors have drifted** — at HEAD those lines are something else (VERIFIED 2026-07-29). Search by symbol, not by line. `order_key` was cited at `:109`, corrected to `:108`, and is the CORE-INTEGRITY-004 surface.
12. `backend/domains/living_settlement_domain.py` — the file everything currently contends over. `build_settlement_candidates` (scoring), the composition point ~`:777`/`:810` (the unwritten fix), the uncommitted R1 retarget.
13. `backend/domains/living_agent_cognition.py` — perception + `derive_internal_pressures` (`:432`), which is why narrowing the builder alone crashes.
14. `backend/core/constants.py:171` — `is_night(tick)`, the whole trigger for Leg B.
15. `backend/tools/_probe_*.py` — 27 read-only probes. Almost any question you have has already been probed; look before writing a new one.

**Off-repo but load-bearing:**

16. `cairn-personality.md` (v2, the 18.5 KB one) — `C:\Users\RJLoc\CrossDevice\Ryan's S24\storage\Download\`. Read the failure-mode sections and "The observed bias." Skip the philosophy unless you want it.

**Do not take current state from:** anything under `memory/archive/` — including `FRONTIER.md`, `CAPABILITY_ROADMAP.md`, `ROADMAP.md`, `MACRO-ROADMAP.md`, and the `STAGE-*-PROMPT.md` files. History only. `memory/evidence/` is data and still citable.

---

# Part 1 — Orientation

## What the product is

**simulation-sandbox** is a deterministic living-world simulation engine plus an integrated sandbox for observing, inspecting, replaying, forking and extending autonomous worlds. Entities persist; actions arise from simulated internal state; every lasting change is causally traceable to what caused it and who did it; agents act only on their own perception and memory; replay reproduces canonical state exactly.

Generated prose may *present* the world. It is never canonical truth. That is constitutional property 8 and it is not negotiable.

The competitive claim, and it is a real one: on 2026-07-28 a `social_warn` regression was isolated to *person-007, frame-2, no proposal emitted, replanned to REPAY_DEBT at frame-4* in about six minutes. That is only possible because of deterministic replay, deterministic ordering, and full causal attribution on accepted events.

## The stack, one page

| Layer | What |
|---|---|
| Language / runtime | Python **3.12.10** (VERIFIED via `py -3.12`) |
| API | **FastAPI 0.110.1**, **uvicorn 0.25.0**, **Pydantic 2.6.4** — `backend/server.py`, `backend/api/routes.py` |
| Persistence | **MongoDB** via **motor 3.3.1** / **pymongo 4.5.0**, `mongodb://127.0.0.1:27017/?replicaSet=rs0`, db `simulation_sandbox`. **A replica set is required** — the frame transaction depends on it |
| Core | `backend/core/` — `kernel`, `commit_pipeline`, `mutations` (single writer), `hashing`, `rng`, `replay_service`, `run_service`, `retention_service`, `forking`, `history_service`, `storage/frame_transaction`, `constants`, `db`, `geometry`, `navigation`, `interventions` |
| Domains | `backend/domains/` — **12 registered** in `DOMAIN_REGISTRY` (`domains/registry.py`) |
| Scenarios | `backend/scenarios/` — `living_settlement`, `collective_groups`, `emergent_groups`, `desert_oasis`, `wilderness_survival`, self-registering |
| Projections | `backend/api/` — age, association, cognitive, group_state, living_agent |
| Frontend | **React 18** on **CRA `react-scripts` 5.0.1**, **Tailwind 3.4**, **Radix UI** (select/slider/tabs/tooltip), `axios`, `lucide-react`, `clsx` + `tailwind-merge` |
| Tests | **478 collected** (VERIFIED 2026-07-29), `python -m pytest` from `backend/` |
| Probes | 27 read-only `backend/tools/_probe_*.py` scripts |
| Harness | `py -3.12 -m tools.living_agent_harness --scenario living_settlement --ticks 320 --seed living-agents-stage6` |
| OS | Windows. git-bash at `C:\Program Files\Git\bin\bash.exe`. Quote paths |

**Port conflict, flag it.** `CLAUDE.md` says the frontend runs on **3010**. `frontend/.env` says `PORT=8001`, and `backend/.env` sets `CORS_ORIGINS=http://localhost:8001,http://127.0.0.1:8001`. Two sources agree on 8001, one doc says 3010. (VERIFIED — file contents.) Trust the `.env` files; `CLAUDE.md` is stale. Backend is `http://127.0.0.1:8000` in both.

## How a world transition actually works

Rail A. No capability may skip a step; no domain writes canonical state directly; no projection, UI, diagnostic or model output becomes truth.

```
Scenario Manifest
→ Validated Genesis
→ Core Tick Scheduler
→ Pinned Read-Only Observation Frame        (end of tick T-1)
→ Domain Activation
→ Candidate Generation                       (domain scores its options)
→ Proposal Construction
→ Deterministic Proposal Ordering            (requested_time, phase, priority, content_hash)
→ Core Validation                            (validators RE-DERIVE, never trust)
→ Atomic Acceptance or Rejection
→ Accepted Event
→ Canonical State Mutation                   (single writer: core/mutations.py)
→ History, Causality, Replay Records
→ Read-Only Projections
→ World View / Inspector / Event Log / Causal Chain / Replay
```

**Core owns:** time, deterministic identity + ordering, the pinned frame, validation, atomic commit, accepted/rejected records, canonical serialization + hashing, replay/resume, lineage/checkpoints.
**A domain may:** read declared inputs, generate candidates, score deterministically, construct proposals, validate its own semantics, project accepted state.
**A domain may not:** write storage, read mutable hidden state, depend on wall-clock, invent unrecorded randomness, mutate another owner's component without a contract, or treat a projection as truth.

Domain commit order is `engine_priority`, low first (VERIFIED, read from source 2026-07-29): `weather -2`, `ecology 0`, `lifecycle 1`, `people 10`, `living_settlement 10`, food-interaction proposals `10`, `animal 20`, `group_carriage 86`, `group_norm 87`, `group_goal 88`, `group_state 89`, `association 90`, `group_collective 90`, base default `100`. Note `people`, `living_settlement` and the food-interaction family all sit at `10` — the tie falls through to `content_hash`, which is CORE-INTEGRITY-004 territory. **Ordering *relationships* are the contract; the numbers are the implementation.** Tests assert relationships, never `priority == 5`. Changing a priority is an architectural change.

## Where the world actually stands

Measured at `d8f00eb6`, `living_settlement`, 320 ticks, 8 people, seed `living-agents-stage6`, clean tree (`PRODUCT-STATE.md`, VERIFIED):

| metric | pre Leg A | now |
|---|---:|---:|
| accepted events | 4,868 | **5,088** |
| actions per 100 ticks | 356 | **388** |
| top-3 action dominance | 74.6% | **70.6%** |
| social share of all actions | 20.8% | **25.0%** |
| action types firing exactly once in 320 ticks | 8 | **7** |
| action types never firing | 0 | **1 (`warn`)** |
| whole-blob CAS false-positive rejections | 1,263 | **0** |
| population survival | 8/8 | 8/8 |
| replay equality | exact | exact |

**The honest read:** the kernel is excellent and the world is boring. Three actions — rest, move, tend — are 70.6% of everything that happens. Seven behaviours fire exactly once per 320 ticks; `warn` fires zero. Leg A multiplied the two social behaviours that were already common and did nothing for the eight rare ones.

**The layer stack and where it's real** (`THE-SPINE.md` §3) — two axes, deliberately: is the *mechanism* built, and does the behaviour *happen organically often enough to matter*?

- **A Kernel** — SOLID / VERIFIED
- **B Physical World** — SOLID / VERIFIED
- **C Individual Agency** — survival SOLID, non-survival drives THIN; organic life THIN; PARTIAL. **This is the front.**
- **D Interaction** — mechanism SOLID, organic life THIN (rich actions ~once/1000 ticks)
- **E Collective Behaviour** — mechanism SOLID, organic life THIN — "machinery, not felt culture"
- **F Economy · G Institutions · H Demography** — ABSENT, PARKED
- **I Player Product** — projections exist; ongoing

The re-sequencing thesis: **fill C now (ordinary life) before more E; keep aid parked until F-A material surplus exists.** Same order Maslow and Dwarf Fortress both use. It was learned the hard way and it is written down.

## The operating model

`choose behaviour → prove it can occur → implement thin version → expose it visually → test combined behaviour → ship domain → move on`

A domain is worth implementing only when it completes: `world condition → agent opportunity → decision → action → state change → memory/social consequence → visible evidence`. Anything that doesn't complete that chain is infrastructure, not a delivered domain.

**A domain is done when it is** Reachable · Deterministic · Consequential · Integrated · Visible · Bounded. **`PASS WITH LIMITATIONS` is a valid completion** — name the limitation instead of widening the contract.

**Maintenance freeze is in force.** Maintenance is permitted *only* when the active domain can't activate, produces incorrect authoritative state, replay breaks, data corrupts or grows uncontrolled, or a bug blocks observation. Never for cleanliness, better abstractions, broader diagnostics, fuller docs, or a future subsystem's needs. Budget **70% domain / 20% integration + visualisation / 10% maintenance**.

**Session cadence:** A definition + activation · B thin implementation · C integration · D presentation · E hardening + freeze. Leg B's failure traces directly to skipping A.

---

# Part 2 — Technical appendix

## Repo geography

The canonical checkout is **nested**: `C:\dev\simulation-sandbox\` is a container directory that itself holds a git repo, and the real project is `C:\dev\simulation-sandbox\simulation-sandbox\`. Loose `.txt` planning files, `.bak` files, `claude-code-setup.zip`, `nvidia key.txt` and two backup patches sit in the outer directory. **Work in the inner one.** Nothing in the outer directory is authority.

```
C:\dev\simulation-sandbox\simulation-sandbox\      <- the repo
├── ENGINE-CONSTITUTION.md   DYNAMICS-BACKLOG.md   ACTIVE-LEG.md   PRODUCT-STATE.md
├── THE-SPINE.md             ARCHITECTURE-SPINE.md CLAUDE.md       AGENT_WORKFLOW.md
├── backend/
│   ├── server.py  requirements.txt  .env
│   ├── api/       routes.py + 5 projections
│   ├── core/      kernel, commit_pipeline, mutations, hashing, rng, replay/run/retention/history services,
│   │              forking, constants, db, geometry, navigation, interventions, storage/frame_transaction
│   ├── domains/   12 registered + contracts/, perception, cognition, reasoning, social, planning, utility
│   ├── scenarios/ living_settlement, collective_groups, emergent_groups, desert_oasis, wilderness_survival
│   ├── tests/     478 collected
│   └── tools/     living_agent_harness, rebuild_run, 27 _probe_*.py
├── frontend/      CRA + Tailwind + Radix; src/{App.js,api.js,components/,lib/}; .env
├── memory/        SOURCE-OF-TRUTH-v2, CORE-INTEGRITY-001..004, CORE-PERF-01,
│                  REGISTRY-COMPONENT-OWNERSHIP, ADR-001, evidence/, archive/
└── scratchpad/  incoming/  test_reports/  .agents/  .claude/  .codex/
```

## Git state, exactly

**HEAD** `9baa4a2a docs: close Leg A, declare Active Leg B (people obey the day)`
**Branch** `capability/stage-8c-phase1-aid-exchange`, tracking `origin/…` same name.

> The branch name is **badly stale**. It says Stage 8C aid exchange; aid exchange has been DEFERRED since it needs Layer F-A surplus. All Leg A and Leg B work landed on this branch anyway. Don't infer the work from the branch name.

**Working tree — dirty** (VERIFIED `git status`, 2026-07-29):

```
 M THE-SPINE.md                                     (+34/-?)
 M backend/domains/living_settlement_domain.py      (+35)   <- the R1 retarget
 M backend/tools/_probe_layer_c_singleton_funnel.py (+41)
 M memory/REGISTRY-COMPONENT-OWNERSHIP.md           (+43/-24)
?? .venv/                                                   <- not gitignored
?? backend/tests/test_layer_c_request_help_targeting.py     <- R1's test, untracked
?? backend/tests/test_layer_c_social_density_probe.py       <- untracked
?? files.zip                                                <- junk at repo root
```

Two housekeeping items that are cheap and worth doing with the R1 commit: **`.venv/` and `files.zip` are untracked but not ignored** — one careless `git add -A` commits a virtualenv. The two untracked test files belong with the R1 diff.

**16 local branches, 15 worktrees.** The ones that matter:

| Worktree / branch | Head | State |
|---|---|---|
| `simulation-sandbox` / `capability/stage-8c-phase1-aid-exchange` | `9baa4a2a` | canonical, **dirty** |
| `C:\dev\wt-leg-b` / `leg-b/day-rhythm` | `de28b951` | **Leg B WIP, fails its own success test**, 1 commit ahead |
| `wt-frontend-upgrade` / `frontend/gameplay-ui-upgrade` | `aae17889` | 5 commits of UI work, **unmerged** |
| `simulation-sandbox-culture24` / `capability/culture-24-scenario` | `8883b715` | culture scenario |
| `wt-fix-verification-hardening` / `fix/verification-hardening` | `afe773ee` | — |
| `wt-ci004-impl` / `core-integrity-004` | `92b3615a` | CI-004 remediation, parked |
| `wt-ci004-r1-coupling`, `wt-ci004-r1-migration`, `wt-ci004`, `wt-cas-attribution`, `wt-oq1-*`, `wt-*-threshold2` | various | preserved experiments |

Plus one stray worktree under `%TEMP%\claude\…\scratchpad\wt-head` at `77b8287d`.

**This is a lot of parallel state for a one-person project.** `CLAUDE.md` already says "worktrees only when parallel work genuinely needs isolation; default to working in the main checkout." A prune pass is *not* urgent and is *not* a licence to break the freeze — but if any of these get merged or abandoned, say which in the commit.

## The open defect register

| ID | What | Status | Why it matters here |
|---|---|---|---|
| **CORE-INTEGRITY-001** | Lost update — ad-hoc fields with no declared owner; blind whole-value replace in `core/mutations.py` (cited as `:24`, anchor has since drifted) | DEFERRED, needs authorised re-baseline | The class Leg A's fix belongs to |
| **CORE-INTEGRITY-002** | 7a association-revision signature: engine lost update or test-side race — **never determined**. 7b resolved separately (setup asserted on a registry that doesn't exist at tick 12) | DEFERRED, **not answered** | Now self-surfacing: a conservation assertion (`revision delta == accepted association-proposal count`) is instrumented in `test_concurrency.py` and proven able to fail on all four violation shapes |
| **CORE-INTEGRITY-003** | Frame-knowledge aliasing | DEFERRED, fix written and withheld | Moves both frozen hashes |
| **CORE-INTEGRITY-004** | **Commit order is content-derived.** `order_key` ties on `(requested_time, phase, engine_priority)`, so `content_hash` decides order; event ids embed content `hash8`. **Any perturbation to any committed event id propagates into ordering for the rest of the run** — deterministic but chaotic | DEFERRED — remediation is its own high-risk stage | **Read this before trusting any A/B.** CONFIRMED by pre-registered scalpel. Noise floor: single-run action-count deltas untrustworthy at tens-of-percent scale. Byte-identical gates and repeat/replay/resume are UNAFFECTED |
| **Pin-capture mismatch** | Actor-side pin captured from the perception-*enriched* working blob, compared at commit against the *pre*-perception committed record. ~955/1,155 remaining rejections are self-doomed at build time | Located, **unwritten** | Blocks every social domain |
| **Composition-point write** | `living_settlement_domain.py:777` (`:810` in working tree) rewrites `actor_update["living_agent"]` wholesale. Narrowing the builder alone crashes — `derive_internal_pressures` subscripts `state["traits"]` (`living_agent_cognition.py:432`) | Located, **unwritten** | The diff belongs at the composition point, not the builder |
| **Plan-stall** | A multi-step plan whose participant moves emits no proposal for two ticks and is replanned away (person-007, frames 2–3, zero rejections) | Carried debt | Likeliest blocker for any domain needing approach-before-action. Fix *inside* the leg it blocks |
| **Stage 6 sealed boundary** | `stage6_role` has **zero write sites**; `living_action_counts` is once-per-lifetime, no reset/decay/TTL | DEFERRED / BLOCKED | Six of eight singleton actions gate on it. The eight-singleton target **cannot satisfy its own acceptance gates** |
| **`warn`** | Needs an animal *and* a person observed at once; animal median distance 11–12 vs `VISION_RADIUS` 4. `animal_observed` fails 2,999/3,000 | PARKED | It is a Layer **B** world-dynamics problem, not Layer C. Don't chase it from C |
| **Aid Exchange** | DEFERRED — needs Layer F-A material surplus | Preserved on `lega_v2_full.patch` | Re-entry: a committed run shows reliable transferable surplus |
| **Layer-E collective deposit** | Agents never store; the chain dies before scoring. Shared storage visible on 33,683/37,521 decisions while carried food never exceeds 2 | DEFERRED | Re-entry: ≥2 distinct agents perform storage actions on a shared storage organically |
| Other carried debts | Group-contract identity is content-dependent → `collective_groups` has no stable A/B surface · per-parameter-per-entity RNG keying owed before anything touches population counts · `collective_groups` 1,000-tick hash unmeasured since `2d68ac16` | — | `DYNAMICS-BACKLOG.md` tail |

## Documentation conflicts found today

Name these rather than silently picking a side — that is a constitutional rule here.

1. **`FRONTIER.md` is archived but still cited as live authority.** It sits in `memory/archive/`. `THE-SPINE.md` §5 says "Owned by `FRONTIER.md` (the only file that declares the current task)" and `AGENT_WORKFLOW.md` session-start says to read it. `CLAUDE.md` and `DYNAMICS-BACKLOG.md` (both newer, 2026-07-28) name **`ACTIVE-LEG.md`** instead. **`ACTIVE-LEG.md` wins** — it is newer and named by the higher authority. `THE-SPINE.md` §5 and `AGENT_WORKFLOW.md` need a one-line correction.
2. **Two process documents describe two different processes.** `AGENT_WORKFLOW.md` describes the *retired* capability-stage ladder (pre-registration, ±3% event bands, adversarial review, ratification STOPs). `ENGINE-CONSTITUTION.md` explicitly **retires** the bands and pre-registration for tuning. `CLAUDE.md` + `DYNAMICS-BACKLOG.md` describe the current Domain Delivery Legs model. **`AGENT_WORKFLOW.md` is effectively archive and is not marked as such.** An agent reading it in good faith will run a process that was deliberately abandoned. This is the "two authorities" failure mode the spine warns about, live.
3. **Frontend port: `CLAUDE.md` says 3010, `frontend/.env` and `backend/.env` CORS both say 8001.**
4. **`ACTIVE-LEG.md` implies the pin-capture and composition-point fixes are written.** They are not — only the fix *points* are located, in the same file. Corrected in Part 0.
5. **`THE-SPINE.md` and `ARCHITECTURE-SPINE.md` are both still marked `Status: PROPOSED (2026-07-24)`** while being used as the map. Either ratify or say they're descriptive.

## Rules an incoming agent must obey

Non-negotiable, from `ENGINE-CONSTITUTION.md` and `CLAUDE.md`:

- Core owns canonical truth; domains propose only. Validators **re-derive**, never trust domain output. No LLM-generated canonical truth.
- Same version + seed + inputs replay identically. Deterministic ordering and RNG — no wall-clock, no iteration-order dependence, no probability standing in for behaviour.
- Accepted events retain causality and attribution. State stays bounded with measured headroom.
- **Label every claim VERIFIED / LIKELY / UNKNOWN. Never promote one.** Suite status is never an unqualified "green" while exclusions exist. **Hash strings pasted from run output, never from memory.**
- Close-out format: STATUS / CHANGES / RISKS / NEXT STEP. Short.
- **Hard rails needing explicit confirmation:** destructive git (reset/checkout/clean/stash-drop on the working tree, force-push, history rewrite, branch deletion). **Never, with or without confirmation:** committing secrets. Note `nvidia key.txt` sits in the *outer* directory — keep it there and keep it out.
- Frozen hashes are a **reproducibility** check, not a behavioural gate. When an intended change moves one, update the pin **in the same commit** and say what moved it. A bare re-hash can launder a regression.
- Maintenance freeze in force — see Part 1.
- Cheapest decisive observation first. Name the single observation that would settle the question, run it, escalate only if ambiguous. **If the verification plan is longer than the diff, cut the plan.**
- Long runs: redirect to a file and read back the summary. A PreToolUse hook enforces this — don't fight it.
- Name gaps. No invented data, constants or fields. If docs, code and tests disagree, say so, show evidence, recommend one option. **Silence is not approval.**

## Commands

```powershell
# suite (478 tests)
cd C:\dev\simulation-sandbox\simulation-sandbox\backend
py -3.12 -m pytest

# canonical harness run
py -3.12 -m tools.living_agent_harness --scenario living_settlement --ticks 320 --seed living-agents-stage6

# UI  (requires mongod running as replica set rs0)
cd backend;  py -3.12 -m uvicorn server:app --port 8000
cd frontend; npm start        # serves on 8001 per frontend/.env

# session start, every time
git log --oneline -10; git status
# then read ACTIVE-LEG.md, restate your position in one paragraph, then act
```

---

# Verification statement

**STATUS — VERIFIED for structure and state; LIKELY for the recommendation.**

**VERIFIED** (read directly from the machine today, 2026-07-29): repo layout; dependency versions in `backend/requirements.txt` and `frontend/package.json`; Python 3.12.10; `.env` contents for both tiers; 478 tests collected; 12 entries in `DOMAIN_REGISTRY`; the `engine_priority` values quoted; branch, HEAD, `git status`, `git diff`, worktree list; the content of the uncommitted R1 diff; `de28b951`'s commit message and diffstat; all document quotations; the existence, size and revision times of the three `cairn-personality*.md` files and their section structure.

**LIKELY:** the A → C → B recommendation. It follows from documented blockers and the maintenance-freeze rules, but it is a judgement call about Ryan's priorities, not a derivation. The claim that R1's recorded deltas don't compose with Leg A's is an inference from two docs citing the same origin baseline — sound, not executed.

**UNKNOWN:** whether the 478 tests currently pass — **not run**, no suite execution was performed for this document; whether the R1 diff still produces its recorded effect on the post-Leg-A baseline; the runtime health of the frontend branch; whether mongod is currently running as replica set `rs0`.

**Line-anchor drift, VERIFIED and worth knowing.** Spot-checking the `file:line` citations that the docs rely on: `core/constants.py:171` (`is_night`) and `living_agent_cognition.py:432` (`traits = state["traits"]`) are **correct at HEAD**. `commit_pipeline.py:476` and `mutations.py:24` are **not** — those lines are now unrelated code. `REGISTRY-COMPONENT-OWNERSHIP.md` already warns anchors may be off by ±1; the real drift is larger. **Treat every `file:line` in `memory/` as a hint and search by symbol.**

**RISKS:** this document adds to a documentation load the project's own rules say to keep small (`AGENT_WORKFLOW.md`: "no new planning… docs unless the user explicitly requests them" — this one was requested). It is **not authority** and will go stale the moment the tree is committed. If it survives past the next leg close-out, delete it rather than maintain it.

**NEXT STEP:** decide A / B / C. If A, the concrete first action is a statistical-gate re-measure of the uncommitted R1 diff against the post-Leg-A baseline at `d8f00eb6`, then commit it together with its two untracked tests and a `.gitignore` entry for `.venv/`.
