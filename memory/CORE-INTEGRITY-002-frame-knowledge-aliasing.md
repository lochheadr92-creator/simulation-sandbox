# CORE-INTEGRITY-002 — Pinned-frame knowledge-fact aliasing (silent in-place write)

**Status: PROPOSED — findings only, remediation DEFERRED.** A fix exists (fully
implemented and test-verified in isolation) but is withheld from commit because
landing it moves both protected hashes named in `CAPABILITY_ROADMAP.md`
("Protected baselines"): the frozen `living_settlement` 320-tick hash and the
`collective_groups` scenario baseline. Per the hard rail in `CLAUDE.md`
("Change the frozen `living_settlement` 320-tick hash ... re-baseline requires
explicit authorisation"), remediation needs its own separately authorized
core-integrity stage with an explicit re-baseline decision — same disposition
path as `CORE-INTEGRITY-001-lost-update.md`.

- **Date:** 2026-07-25 · **Branch:** `worktree-typed-painting-marshmallow`
  (capability/stage-8c-phase1-aid-exchange context) · **Base SHA:** `5267217b`.
- **Discovered during:** implementing and hash-verifying a proposed fix for an
  external adversarial review finding (three integrity repairs; the review
  document itself was not locatable in this repo — findings were independently
  confirmed against the code before acting).
- **Evidence artifacts:** none committed under `memory/evidence/` (session
  scratch only, per "scratch output... never committed"). Reproduction is
  cheap and described below — a probe can be built from it if this is picked
  up.
- **Method:** ran the standing frozen-hash harness invocations
  (`tools.living_agent_harness --scenario living_settlement --ticks 320
  --repeat 2`, and `--scenario collective_groups --ticks 250/1000 --repeat 2`)
  once on the clean committed tree and once with a candidate fix applied;
  isolated the cause via `git stash push`/`pop` (no checkout/reset/clean) to
  a single file; diffed the full canonical entity snapshot
  (`canonical_json(snapshot_for_hash(entities, ticks, lineage_key))`) between
  the two runs. Execution evidence, not a code reading.
- **Labels:** VERIFIED (executed/measured), LIKELY (supported, not directly
  traced to certainty).

---

## 1. Summary and classification

`domains/perception.py`'s `_compat_knowledge()` shallow-copies the outer
`facts` dict (`out["facts"] = dict(existing[key])`) but not each individual
fact record. `existing` is frequently a live reference into the pinned,
per-tick read-only observation frame (`frame.entities[entity_id]["knowledge"]`
via `entity.get("knowledge")` in `living_settlement_domain.py`'s `activate()`).
`merge_knowledge()`'s field-level in-place updates (e.g. the tree/person/
shelter re-observation path, `facts[fid]["last_confirmed_tick"] = tick`) then
mutate that shared fact-record object — writing into what Rail A requires to
stay read-only for the whole tick.

This was believed unreachable in any shipped scenario (no other domain reads
another entity's `knowledge.facts` back out of `frame.entities`). That belief
is **refuted**: deep-copying each fact record (the direct fix) measurably
changes the canonical simulation trajectory in **both** flagship frozen-hash
scenarios.

- **F1 — Aliased fact-record mutation reaches both flagship scenarios.**
  [VERIFIED] `living_settlement --ticks 320 --repeat 2` `final_state_hash`
  moves from `897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab`
  (clean tree, `repeat_matches: true`) to
  `edcd75fcc4a53cc332bbbf59d0b572354727cc1fdf1554c50489a5b49287c249`
  (fix applied, `repeat_matches: true`) — a deterministic behaviour change,
  not run-to-run noise. `collective_groups --ticks 250 --repeat 2`
  `final_state_hash` moves from `91a9b7d1da3cfa6188169e924a3496d1d5d7e9fe870267dcf2715218735e8b98`
  to `33eafd399880012b0ad2111a1b90980efcadab4af2e52776fe1f0dd96e5230d8`.
- **F2 — The corruption is substantive, not cosmetic.** [VERIFIED] Diffing the
  full `living_settlement` entity snapshot: entity index 2's own `action`,
  `position`, `hunger` (776→688), and `energy` (80→0) diverge starting around
  tick 296–314 and cascade from there. Its own `knowledge.facts` about several
  other people/shelters shift from staggered confidence/timestamps
  (confidence 700–880, `last_confirmed_tick`=314) to a uniform reset
  (confidence 470, `last_confirmed_tick`=296, `stale_after_tick`=316) — the
  signature of an aliased object being touched by more than the entity that
  owns it.
- **F3 — Precise trigger mechanism.** [LIKELY, not traced to certainty] Most
  plausibly a same-tick self-read: `entity.get("knowledge")` for entity X
  returns a live reference into the pinned frame's own copy of X's knowledge;
  `merge_knowledge()`'s in-place writes (pre-fix) mutate that pinned-frame
  object; something later in the *same tick* re-reads it, producing an
  order-dependent divergence. Not traced further — the STOP condition was
  already unambiguous without full root-cause tracing (proportionality: the
  cheapest decisive observation, not exhaustive tracing, once a hash-moving
  behaviour change is confirmed).

## 2. The withheld fix

`_compat_knowledge()`: deep-copy each fact record instead of shallow-copying
only the outer `facts` dict —
`out["facts"] = {fid: copy.deepcopy(fact) for fid, fact in out["facts"].items()}`.
Verified hash-neutral in isolation is **false** — see F1. The fix itself is
correct in what it closes (object identity), but closing it changes behaviour
that the current frozen baselines encode as canonical, because the aliasing
bug was already live and had already been shaping those baselines' state
trajectories.

## 3. Remediation options (undecided — for the eventual authorized stage)

- **A. Re-baseline.** Accept the new hash values as correct (the aliasing bug
  the fix closes was real) and land the fix. Requires the explicit
  re-baseline authorisation the hard rail names.
- **B. Loud guard instead of silent fix.** Detect the aliasing condition and
  raise a named exception rather than silently correcting it — closer to the
  original ask that motivated this fix. Caveat: since the condition is
  reached in both flagship scenarios *today*, a guard that raises would make
  the standing frozen-hash harness runs throw instead of complete — a
  behaviour change to the verification workflow itself, needing its own
  sign-off.
- **C. Leave as-is, tracked.** No code change; this record is the tracking
  artifact. (Current disposition, pending a future authorized session.)

## 4. Consequence in the meantime

Same posture as `CORE-INTEGRITY-001-lost-update.md`: any leg touching
`living_settlement_domain.py`'s knowledge-merge path, or any leg reasoning
about per-entity knowledge-fact freshness/confidence, should be aware that a
pinned-frame read-only guarantee is not currently held for
`knowledge.facts` records reached via `_compat_knowledge()`. Do not build new
cross-entity knowledge-reading logic without first checking whether it can
observe this aliasing.
