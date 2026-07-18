# Roadmap Reconciliation Record — 2026-07-14

Audit of the three planning sources against actual code and git state, on
branch `capability/stage-6-living-agents` (simulation-sandbox main working copy).
This is a **reconciliation record only**. It does not override ROADMAP.md,
CAPABILITY_ROADMAP.md, the Domain Plan, or Source of Truth v2. It names drift and
recommends resolutions; applying them requires your approval.

**Revised 2026-07-14 (post-commit `ca2419e0`).** Since the first pass, commit
`ca2419e0 "feat: Stage 7B.1 capacity hardening and Stage 7C collective deposit"`
(Ryan, Tue Jul 14 22:28) committed the previously-untracked 7B.1 and 7C work.
The VCS-provenance finding (old C5) is resolved; the documentation conflicts are
not.

Evidence labels: VERIFIED (confirmed by file/git/command), LIKELY (supported, not
proven), UNKNOWN (unverified).

---

## 1. Canonical current state (what actually exists)

HEAD: `ca2419e0 feat: Stage 7B.1 capacity hardening and Stage 7C collective deposit`.

| Layer | Claimed status | Evidence found | Reconciled status |
|---|---|---|---|
| Capability Stage 6 — Living Agents | Implemented and verified (2026-07-13) | Committed; 320-tick determinism gate recorded | VERIFIED committed |
| Stage 7A — Emergent groups | Implemented, acceptance-verified | `association_*` tracked; commit `97b0fe53` | VERIFIED committed |
| Stage 7B — Shared group state | Implemented, acceptance-verified | `group_state_*` tracked; commit `701c6115` | VERIFIED committed |
| Stage 7B.1 — Capacity hardening | Implemented, acceptance-verified | Now committed in `ca2419e0` (assoc/group_state compaction + `hashing.py`/`commit_pipeline.py`) | VERIFIED committed |
| Stage 7C — Group collective action | Implemented (focused-verified kernel baseline) | `group_collective_*` + `test_stage7c_*` now tracked in `ca2419e0` (15 tests / 65 combined) | VERIFIED committed; **verification pending** (focused-only) |

**What changed since the first pass:** the frontier is now durable in git — 6,
7A, 7B, 7B.1, 7C all committed. The earlier risk (7C existing only as untracked
files) is gone. Two caveats remain:

- **One commit, many purposes.** `ca2419e0` bundles 7B.1 + 7C + capability-doc
  edits + this reconciliation record in a single commit. Against your
  one-commit-one-problem norm it is not cleanly reviewable/revertible, but it is
  committed — a hygiene note, not a risk.
- **Known limitation (from the commit message itself):** "Organic long-run
  `shared_storage` reachability remains a known limitation" — i.e. 7C's
  `coordinated_storage_deposit` is proven in the focused scenario but may not
  arise organically in long runs, because the Stage 7B `shared_storage` facts it
  consumes are not reliably produced by the natural simulation. This is a real
  gap in the 7C causal loop and feeds C4 below.

---

## 2. Conflicts across sources (named)

Committing the code did **not** touch the stale pointers or the authority split.
All four documentation conflicts below remain live at HEAD.

### C1 — Two numbering systems have diverged past their own dependency rules *(structural, high impact — UNCHANGED)*
- `ROADMAP.md` (declared **execution authority** by DOMAIN_MAPPING) still says
  **"Phase 5B6 is the next active phase"** (lines 128, 174, 256, 765) and
  **"does not authorise Capability Stage 7"** (line 775). Phase 6 groups are
  still marked "deferred."
- Reality: **Stage 7A/7B/7B.1/7C group work is committed.** The execution-authority
  doc now directly contradicts committed code.
- Root cause unchanged: nothing bridges Capability-Stage numbers to Phase numbers.

### C2 — Stale "immediate next" pointers *(low effort, now definitively wrong — UNCHANGED)*
- `CAPABILITY_ROADMAP.md` footer ("# Immediate next capability") still reads
  "With Capability Stage 7B verified, the next … is Capability Stage 7C." 7C is
  now committed — this pointer is objectively stale.
- `ROADMAP.md`: "Phase 5B6 is the next active phase."
- `DOMAIN_MAPPING.md` footer: "last aligned to Phase 5B5 / Capability Stage 6."
- Three docs, three different "nexts," none of which is the true frontier
  (7C done, verification pending).

### C3 — Stage 7C has two names *(naming collision — UNCHANGED)*
- Body + standalone doc: **"Group Behaviour and Collective Action."**
- Footer of CAPABILITY_ROADMAP: **"Narrow Shared-Fact Consumer Contract."**
- Code domain is `group_collective` → the body name is the accurate one.

### C4 — 7C verification status is overstated against the doc's own gate *(correctness — UNCHANGED, reinforced)*
- 7C is committed but only *focused-verified* (15 / 65 tests). It meets **none**
  of CAPABILITY_ROADMAP's Global completion rules requiring persistence+replay
  survival for `group_collective`, frontend-projection safety, explicit perf
  limits under integrated load, and matching docs.
- Reinforced by the commit's own "organic reachability" caveat: the cause→effect
  chain isn't demonstrably closed under natural runs.
- Correct label: **"Implemented — verification pending."**

### (Resolved 2026-07-18) C6 — Branch name understates scope
- Was: branch still `capability/stage-6-living-agents`; HEAD now carries 6, 7A,
  7B, 7B.1, 7C. **Now renamed to `capability/stage-8-culture` at the Stage 8
  Leg 0 boundary** (`memory/STAGE-8-CONTINUATION-PROMPT.md` item 4) — same
  branch, same commit history, no rewrite. Closed.

### (Resolved) C5 — VCS provenance
- Was: 7C untracked, 7B.1 uncommitted. **Now committed in `ca2419e0`.** Closed.

---

## 3. Recommended resolutions

R1 (commit the frontier) is now **done** — superseded by `ca2419e0`. Remaining,
by leverage:

**R2 — Add the missing Capability-Stage ↔ Technical-Phase bridge.**
The drift persists because nothing maps Stage 6/7 onto Phase 5x/6. Add a short
table to DOMAIN_MAPPING.md declaring that Capability Stage 6–7 subsume the
social/group loop ROADMAP framed as Phase 5B–6, and that ROADMAP's "Phase 6
groups deferred / Stage 6 does not authorise Stage 7" statements are
**superseded**. Make CAPABILITY_ROADMAP authoritative for capability sequencing
and ROADMAP authoritative for Core/persistence/replay mechanics; state that in
both headers.

**R3 — Collapse the three stale "next" pointers (C1, C2) into one shared frontier
line:** "Frontier = Stage 7C committed, verification pending; next authorised
work = close 7C's hard gate (incl. organic `shared_storage` reachability), then
Stage 8." Canonical copy in CAPABILITY_ROADMAP; ROADMAP/DOMAIN_MAPPING reference
it. Update ROADMAP lines 128/174/256/765/775 so they stop asserting 5B6-next and
Stage-7-unauthorised.

**R4 — Pick one 7C name (C3):** "Group Behaviour and Collective Action" (matches
code + standalone doc). Delete "Narrow Shared-Fact Consumer Contract" from the
footer.

**R5 — Downgrade 7C to "Implemented — verification pending" (C4)** everywhere,
and list the open gates explicitly: `group_collective` persistence/replay,
frontend-projection safety, integrated 6→7C regression, and the organic
`shared_storage` reachability limitation from the commit message.

**R6 — Retag the branch** (e.g. `capability/stage-7-groups`) to reflect true
scope. Low priority.

---

## 4. Reconciled forward sequence

1. **Doc reconciliation (R2–R5)** — now the highest-leverage work, since the code
   is committed but the docs still misstate the frontier and authority.
2. **Stage 7C hardening — RESOLVED 2026-07-14.** A 1,000-tick `collective_groups`
   run confirmed `group_collective` persistence/replay, integrated 6→7A→7B→7C
   determinism, and projection safety (all green). The organic-reachability gate
   was investigated and **deferred as Stage 9-blocked**: a measured 1,000-tick
   run fired 0 collective proposals because agents have no surplus to store
   (`store ≈ 0`), so `shared_storage` facts never form — reliable surplus is a
   Stage 9 Economy capability, downstream of 7C. A Stage 6 planner nudge to force
   it was tested and rejected (no effect; moved the frozen Stage 6 hash). 7C is
   now **mechanism-verified; organic emergence deferred** and off the critical
   path. See `CAPABILITY-STAGE-7C-GROUP-COLLECTIVE.md`.
3. **Clear the 5A2 infrastructure gate** — live transaction-capable Mongo
   (replica set). Several Phase 5 items and, by inheritance, the Stage 7
   persistence claims remain "verification pending" until this is exercised.
4. **Decide the true next capability** (open — see §5).

**Recommendation:** do **not** start Stage 8 (Culture) next. Reconcile the docs,
close 7C's organic-reachability gap, and clear 5A2 first. Every Stage 7 "verified"
claim still sits on top of an unexercised live-transaction path and a collective
loop that only fires in a hand-built scenario. Retire hidden risk before adding a
new domain.

---

## 5. Decision (ratified 2026-07-14): depth over breadth

The next-stage fork is **resolved: depth.** After 7C (now mechanism-verified),
the next capability is **Stage 7D — finish the group loop (leadership, collective
goals)**, not Stage 8 (Culture) breadth. Rationale: Stage 8 culture rests on
persistent group identity and collective decision-making that the Stage 7 loop
only partially delivers; deepening 7 before widening into 8 keeps the capability
chain honest. Stage 8 is deferred until the group loop is complete. The 5A2
live-transaction infrastructure gate remains a parallel technical task.

Guardrail (unchanged): Stage 7D must not introduce a hidden group mind —
leadership and collective goals remain proposal-only, Core-authored, and
member-grounded; no obedience, warfare, diplomacy, politics, religion, or player
control until separately contracted.
