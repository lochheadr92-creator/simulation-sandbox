# Roadmap Reconciliation Record — 2026-07-14

Audit of the three planning sources against actual code and git state, on
branch `capability/stage-6-living-agents` (simulation-sandbox main working copy).
This is a **reconciliation record only**. It does not override ROADMAP.md,
CAPABILITY_ROADMAP.md, the Domain Plan, or Source of Truth v2. It names drift and
recommends resolutions; applying them requires your approval.

Evidence labels: VERIFIED (confirmed by file/git/command), LIKELY (supported, not
proven), UNKNOWN (unverified).

---

## 1. Canonical current state (what actually exists)

| Layer | Claimed status | Evidence found | Reconciled status |
|---|---|---|---|
| Capability Stage 6 — Living Agents | Implemented and verified (2026-07-13) | Committed; 320-tick determinism gate recorded | VERIFIED committed |
| Stage 7A — Emergent groups | Implemented, acceptance-verified | `association_domain.py` / `association_contracts.py` tracked; commit `97b0fe53` | VERIFIED committed |
| Stage 7B — Shared group state | Implemented, acceptance-verified | `group_state_domain.py` / `group_state_contracts.py` tracked; commit `701c6115` | VERIFIED committed |
| Stage 7B.1 — Capacity hardening | Implemented, acceptance-verified | **No matching commit found**; HEAD `c6908f9c` confirmed to contain only persistence-batching files, not 7B.1's association/group_state edits → 7B.1 changes are uncommitted working-tree edits on the tracked 7A/7B files | LIKELY implemented, **uncommitted** |
| Stage 7C — Group collective action | Implemented (focused-verified kernel baseline) | `group_collective_domain.py`, `group_collective_contracts.py`, `test_stage7c_group_collective.py` present on disk but **untracked by git** | VERIFIED code exists, **VERIFIED not committed** |

HEAD commit: `c6908f9c perf: batch entity persistence writes within frame transactions`.

**The headline finding:** the capability docs describe work through Stage 7C as
done, but git tells a narrower story. 6 / 7A / 7B are durable. 7B.1 has no
traceable commit. 7C exists only as untracked working-tree files. Per your Core
Principle (verified progress over apparent progress), 7B.1 and 7C are **apparent,
not verified** at the repository level — one `git clean` or lost worktree erases 7C.

---

## 2. Conflicts across sources (named)

### C1 — Two numbering systems have diverged past their own dependency rules *(structural, high impact)*
- `ROADMAP.md` (declared **execution authority** by DOMAIN_MAPPING) says **Phase 5B6 is the next active phase**, and **Phase 6 — Groups, Settlements, Civilisation is "deferred,"** dependent on completing 5B–5F.
- `CAPABILITY_ROADMAP.md` has already shipped **Stage 7A/7B/7B.1/7C** — group recognition, shared group state, and collective action — i.e. group-scale behaviour that ROADMAP defers to Phase 6.
- The capability chain's own rule ("a later capability must not be treated as complete while the capabilities it depends on remain disconnected") is under strain: group collective action (7C) is built while technical social/resource/conflict phases 5B6, 5C, 5E, 5F remain incomplete.
- Root cause: DOMAIN_MAPPING bridges only **Domain Plan ↔ ROADMAP (Phase numbers)**. There is **no authoritative bridge between Capability Stage numbers and technical Phase numbers**, so the two tracks drift with nothing reconciling them.

### C2 — Stale "immediate next" pointers in all three docs *(low effort, high confusion)*
- `CAPABILITY_ROADMAP.md` footer: "With Stage 7B verified, the next … is Stage 7C" — but 7C is already implemented earlier in the same file.
- `ROADMAP.md`: "Phase 5B6 is the next active phase" and "Capability Stage 6 … does not authorise Capability Stage 7" — yet 7A–7C exist.
- `DOMAIN_MAPPING.md` footer: "last aligned to Phase 5B5 / Capability Stage 6 implementation-complete" — predates 7A–7C entirely.
- Three documents each point at a different "next." A reader cannot tell the true frontier from any single doc.

### C3 — Stage 7C has two different names *(naming collision)*
- Body of CAPABILITY_ROADMAP and the standalone doc: **"Group Behaviour and Collective Action."**
- Footer of CAPABILITY_ROADMAP: **"Narrow Shared-Fact Consumer Contract."**
- Same stage ID, two titles → ambiguity about what 7C actually is.

### C4 — 7C verification status is overstated against the doc's own gate *(correctness)*
- Both docs correctly say 7C is only *focused-verified* (15 tests / 65 combined), with product-facing UI and infra gates open.
- But CAPABILITY_ROADMAP's own **Global completion rules** require persistence+replay survival, frontend-projection safety, explicit performance limits, integrated tests, and matching docs before "complete." 7C meets none of the hard gates.
- Correct label per the doc's vocabulary: **"Implemented — verification pending,"** not a done stage.

### C5 — 7C / 7B.1 lack durable VCS evidence *(correctness + risk)*
- VERIFIED: 7C source and tests are untracked. LIKELY: 7B.1 is uncommitted or silently folded into an unrelated `perf:` commit.
- "Acceptance-verified" (7B.1) and "focused-verified" (7C) are asserted, but the artifacts backing those claims are not in git history — so the claims are not reproducible from the repository, violating "no phase marked complete from workflow labels; completion requires reproducible repository commands and recorded results."

### C6 — Branch name understates scope *(minor)*
- Working branch is `capability/stage-6-living-agents`, but it carries 7A, 7B, and (uncommitted) 7C. The name signals Stage 6 only.

---

## 3. Recommended resolutions

Ordered by leverage. Each is reversible; none are applied yet.

**R1 — Commit or quarantine 7C/7B.1 first (do this before anything else).**
Nothing else is trustworthy while the frontier is uncommitted. Options (ToT-lite):
- (a) *Commit 7C as its own "Implemented — verification pending" commit* — recommended: preserves the work, makes the claim reproducible, keeps one-commit-one-purpose.
- (b) Leave untracked and keep building — rejected: one lost worktree deletes verified-claimed work.
- (c) Stash — rejected: hides state, worsens drift.
First confirm whether 7B.1 is inside HEAD `c6908f9c` (`git show c6908f9c --stat`) so its provenance stops being LIKELY.
→ **Recommended action: commit 7C (and split out 7B.1 if it's riding inside the perf commit), labelled "Implemented — verification pending."**

**R2 — Add the missing bridge: one Capability-Stage ↔ Technical-Phase mapping.**
The drift exists because nothing maps Stage 6/7 onto Phase 5x/6. Add a short table to DOMAIN_MAPPING.md (the designated alignment doc) declaring, e.g., "Capability Stage 6–7 subsume the social/group loop that ROADMAP framed as Phase 5B–6; ROADMAP Phase 6 'groups deferred' is **superseded** by the capability track." Pick one as authority for group work and mark the other *derived*.
→ **Recommended action: make CAPABILITY_ROADMAP authoritative for capability sequencing, ROADMAP authoritative for Core/persistence/replay mechanics, and state that explicitly in both headers.**

**R3 — Fix the three stale "next" pointers (C2) to one shared frontier statement:**
"Frontier = Stage 7C implemented, verification pending; next authorised work = 7C hardening to full gate, then Stage 8." Put the canonical version in CAPABILITY_ROADMAP and have ROADMAP/DOMAIN_MAPPING reference it rather than restate it (single source of truth).

**R4 — Pick one name for 7C (C3).** Recommend "Group Behaviour and Collective Action" (matches the standalone doc and the code domain `group_collective`). Delete the "Narrow Shared-Fact Consumer Contract" label from the footer.

**R5 — Downgrade 7C's status label to "Implemented — verification pending" (C4)** everywhere, and list the exact open gates (persistence/replay of `group_collective`, frontend projection safety, explicit perf caps already in the 7C doc, integrated regression).

**R6 — Rename/retag the branch** to reflect true scope (e.g. `capability/stage-7-groups`) or open a fresh `capability/stage-7c-collective` branch off HEAD once 7C is committed. Low priority.

---

## 4. Reconciled forward sequence

Assuming R1–R5 are accepted, the dependency-honest order is:

1. **Commit + provenance** (R1) — make the frontier real in git. *(blocks everything)*
2. **Stage 7C hardening to full gate** — persistence/replay for `group_collective`, integrated 6→7A→7B→7C regression, explicit perf caps confirmed, read-only frontend projection. Only then is 7C "fully verified."
3. **Doc reconciliation** (R2–R5) — bridge table, single frontier pointer, name fix, status downgrade.
4. **Decide the true next capability** — genuinely open; see question below. Candidates:
   - *Stage 8 (Culture/Norms)* — next in the capability chain, but depends on repeated behaviour + group identity that 7C only just seeds.
   - *Deferred technical debt in ROADMAP* — 5A2 live-transaction infra gate (needs replica-set Mongo) still blocks "fully verified" closure on several Phase 5 items; 7B/7C inherit that gate.
   - *Stage 7 consolidation* — leadership/collective-goals were explicitly deferred out of 7C; a 7D could close the group loop before Stage 8.

**Recommendation:** do **not** start Stage 8 next. Close 7C's gate and resolve the 5A2 infrastructure gate first, because every Stage 7 "verified" claim currently sits on top of an unverified live-transaction path. Build order should retire hidden risk before adding a new domain.

---

## 5. Open decision for you

The one genuinely ambiguous fork is **step 4**: after 7C is hardened, go
*breadth* (Stage 8 Culture) or *depth* (finish Stage 7 leadership/collective
goals + clear the 5A2 infra gate)? That's a product-direction call, not a
correctness one — flagged, not assumed.
