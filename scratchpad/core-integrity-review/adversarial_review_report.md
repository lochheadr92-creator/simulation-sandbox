# CORE-INTEGRITY-001 — Independent Adversarial Review Report (Grok)

**Date:** 2026-07-25 · **Reviewer:** Grok (xAI) — non-Anthropic; did not author finding or probes.
**Transcription note:** this file was transcribed into the repo by the Cowork session from Grok's chat output pasted by Ryan; some table cells in the paste were width-truncated and have been reconstructed conservatively. If Grok's raw export is saved, that copy supersedes this one.
**Scope:** read-only independent adversarial review of `scratchpad/core-integrity-review/` packet only — no engine change, no commit, no overlap with Upkeep close-out.

## Independence record (confirmed)

| Role | Model / path |
|---|---|
| Finding author | Anthropic Claude (Stage 8C Phase 1, 2026-07-22) |
| Disposition | Ryan: findings ACCEPTED, remediation DEFERRED (2026-07-24) |
| Reviewer | Grok (xAI) — non-Anthropic; did not author finding or probes |
| Caveat | Same human owns both sessions. Reviewer did not re-execute probes; verdicts rest on committed/packet JSONs. Re-runs demanded where authenticity or fidelity is load-bearing. |

---

## Pass 1 — blind attack on the ten claims (labels VERIFIED / LIKELY / GAP; never upgraded)

**Claim 1 (shallow LWW `dict.update`; silent discard; only opt-in eq): no independent flaw in the core mechanism claim.** Evidence: `mutations.py:20-23` shallow top-level key replace, no conflict check, no error; `commit_pipeline.py:441-445` revalidates preconditions then `apply_mutation` at `:462`; preconditions opt-in (empty list passes). Does not support the absolute "only guard": domain-specific validators can reject before apply, but none is a generic same-field multi-writer conflict detector. Mechanism VERIFIED from packet source. → **IND-C1-NOTE** (wording nit).

**Claim 2 (sub-test 2b proves F1 by execution): no independent flaw for the synthetic pipeline proof.** `probe_8c_pipeline_write.json` subtest2b: accepted: 2, rejected: [], beneficiary_still_has_SYN_COMMIT_after_frame: false. Does not support that production aid used this exact shape. Synthetic F1 VERIFIED if JSON authentic. → **IND-JSON** (re-run demand: `python -m tools._probe_8c_pipeline_write` and `_probe_core_integrity_death_scope`, diff vs packet/evidence copies).

**Claim 3 (touched_scope existence-only; F2 proven twice): no independent flaw.** `check_scope_exists` (`commit_pipeline.py:107-112`) tests existence only; `apply_mutation` iterates all keys unfiltered; both probe entries confirm persistence of out-of-scope writes. Narrow contracts (e.g. food transfer `:145-146`) exist but are not generic `entity_updates ⊆ touched_scope`. F2 VERIFIED on generic path (subject to IND-JSON).

**Claim 4 (real exploiter `living_settlement_domain.py:734` explains 17/17): FINDING — not independently checkable from packet.** The packet contains the mechanism (2b) but not `living_settlement_domain.py`, `living_agent_actions.py`, or the 17/17 measurement artifact. Production causal attribution remains LIKELY at best until artifacts land. → **IND-C4**: DISPUTE the VERIFIED production-explanation step; demand (1) domain source slice around `:528`/`:734`, (2) physical-action precondition builder cites, (3) original 17/17 measurement artifact.

**Claim 5 (death path F1-exposed; corrupted death; order-flip; un-kill permitted): no independent flaw for structural exposure under synthetic shapes.** D2 alive:false + health:500; D3 order-flip; D4 pipeline_permits_unkill. Probes hand-mirror domain shapes ("constructed to match, cited, not imported") — shape fidelity LIKELY, not VERIFIED. → **IND-FIDELITY**: re-probe with real domain builders or documented field-by-field equality check vs `lifecycle_domain.py:151-172` and HELP path; no promotion to "production death corruption observed."

**Claim 6 (corruptible not maskable; zero-deaths = hunger recovery): FINDING — maskability negation and zero-deaths explanation outside packet proof.** D2's alive:false persistence is structural VERIFIED; "no domain writes alive:True" is a grep assertion not in packet (GAP); hunger-recovery explanation stays LIKELY. → **IND-C6**: ACCEPT structural half; keep historical explanation non-load-bearing.

**Claim 7 (person entity is exposed surface; field map; Category-2 safe): FINDING — only two fields proven in-packet.** living_agent (2b) and health (D2) VERIFIED synthetically; the rest of the §6 table and Category-2 validator restrictions are not packet-auditable (contracts files absent). → **IND-C7**: ACCEPT person-entity as primary surface; DISPUTE full table / Category-2 absolutes as independently verified by this review.

**Claim 8 (deterministic order ⇒ any F1 repair necessarily moves frozen baselines): FINDING — determinism half solid; "necessarily" too strong.** order_key + sort + content-only hash + DET probe: deterministic collision survival VERIFIED. But hash moves iff a repair changes committed state for that scenario: scope-only enforcement may be hash-stable on clean scenarios; eq additions can move hashes merely via content_hash/order changes; deep-merge only moves where clobbering currently occurs. → **IND-C8**: replace "any F1 repair necessarily moves…" with "repairs that alter accepted collision outcomes or ordering-relevant proposal content will move affected freezes; scope-only fixes may not." ACCEPT re-baseline gate whenever measured post-repair hash ≠ frozen.

**Claim 9 (culture inv. 11 = test mandate; coverage gap not violation; no no-lost-update canon): no independent flaw on the culture-11 reading.** Matches standing CLAUDE.md list. SOT §19 not in packet → "no canon forbids silent overwrite" stays LIKELY. → **IND-C9**: attach SOT §19 excerpt for formal VERIFIED.

**Claim 10 (standing mitigation policy is sufficient containment): FINDING — necessary but NOT sufficient. Live residual risk.** Ten concrete failure shapes:

| ID | Failure shape |
|---|---|
| P10-1 | Eq race freezes the second legitimate writer (aid delivery then settlement eq-fail → agency starved for the frame; no merge/partial-eq/priority defined) |
| P10-2 | Two "single-owner" legs each also write the same person field "for convenience" — single-owner registries don't prevent multi-owner person fields |
| P10-3 | Registry-truth vs person dual-read split-brain: delivery recorded in registry while UI/probes read living_agent.commitments → false "loss" metrics and bad gates |
| P10-4 | Eq on the wrong grain (eq on alive while colliding on health/energy/plan; death path has no health eq) |
| P10-5 | Whole-blob eq + partial semantic intent: nested-only update replaces entire living_agent from snapshot; "field-level" ambiguous (top-level key vs nested path) |
| P10-6 | Churn-test mandate is unenforced shape — culture-11 already failed once; no required scenario matrix (non-actor beneficiary, death+HELP, out-of-scope write) |
| P10-7 | F2 omitted: policy doesn't require entity_updates ⊆ touched_scope — future leg can write undeclared persons while "following" the rules |
| P10-8 | Adding eq preconditions changes content_hash → can reorder same-frame commits and change which writer wins across leg versions |
| P10-9 | Eq protects only listed fields: a writer can eq-guard living_agent and still LWW-clobber unguarded knowledge/action/position in the same mutation |
| P10-10 | Category-2 multi-write GAP unclosed: apply_mutation is entity-agnostic; two engines writing one registry id in one frame LWW equally |

Label: policy LIKELY reduces silent person-field loss when correctly applied; NOT VERIFIED as sufficient. Residual risk VERIFIED as structural (P10-1, P10-5, P10-7 especially). → **IND-C10**: DISPUTE "sufficient"; ACCEPT "necessary interim discipline with explicit residual risk register (P10-*)."

---

## Findings ledger (proposed dispositions — rulings are Ryan's)

| ID | Source | Finding | Proposed disposition |
|---|---|---|---|
| IND-JSON | independent | Probe JSONs not re-executed by reviewer; authenticity assumed | ACCEPT pending Ryan re-run; FIX only if diverge |
| IND-C4 | independent | Production 17/17 + settlement:734 not in packet → cannot VERIFY production attribution | DISPUTE VERIFIED production causal claim until artifacts land |
| IND-FIDELITY | independent | Death/HELP shapes cited-not-imported | ACCEPT structural; no promotion to observed production corruption |
| IND-C6 | independent | alive-True grep + hunger zero-deaths out of packet | ACCEPT structural half; historical link non-load-bearing |
| IND-C7 | independent | Full field map + Category-2 not packet-auditable | ACCEPT person surface; DISPUTE full table as independently verified |
| IND-C8 | independent | "Any F1 repair necessarily moves freezes" overstrong | DISPUTE universal necessity; ACCEPT re-baseline gate when hash moves |
| IND-C9 | independent | SOT §19 not in packet for full F3 dual-list VERIFIED | ACCEPT culture-11 + F3 class; attach SOT excerpt |
| IND-C10 | independent | Mitigation policy not sufficient; residual scenarios P10-1…10 | DISPUTE sufficiency; revise standing policy |
| IND-C1-NOTE | independent | "Only guard is eq" ignores domain validators (non-conflict) | ACCEPT as wording nit |
| IND-PATH | independent | Finding cites memory/evidence/stage-8c-leg1/; review packet is scratchpad/core-integrity-review/ | ACCEPT if identical; demand path reconciliation |
| F1 | seeded | Silent same-frame lost update via shallow update | ACCEPT (mechanism VERIFIED in packet) |
| F2 | seeded | touched_scope not enforced on update keys | ACCEPT (VERIFIED in packet) |
| F3 | seeded | Invariant-number collision | ACCEPT as doc defect (SOT attach for full VERIFIED) |
| SEC-CAS | seeded-adjacent | test_concurrent_stage7a/7b intermittency | ACCEPT classification: out of CORE-INTEGRITY-001 scope — own ID (e.g. CORE-INTEGRITY-002-CONCURRENCY-CAS) |

No silent drops.

---

## Pass 2 — forward deliverables

### A. GAP attack plan (ranked by risk-per-cost)

1. **Remediation/re-baseline consequence.** After any candidate fix prototype on a throwaway branch: re-hash frozen scenarios (living_settlement 320 + collective_groups, same commands as at freeze). Asserts: post-fix hash == or ≠ frozen; list which scenarios move. Cost low–medium.
2. **Per-frame commit order of the 17 aid cases.** Offline trace of accepted events for the measurement run: filter frames with an aid-commitment write + later living_agent write on the beneficiary; print order index, proposer engine id, entity id. Asserts, in ≥1 (ideally 17/17) loss frames: aid write accepted earlier; later same-entity living_agent write accepted; final state lacks commitment. Cost low if event log exists.
3. **Which §6 collisions fire in production.** Read-only post-hoc over one frozen 320-tick event stream: group accepted events by (tick, entity_id, top-level entity_updates keys); flag multi-accept key collisions. Counts collisions per field; identifies co-writing engines. Cost medium.
4. **Category-2 registry multi-write.** Same collision script restricted to registry ids. Asserts zero or nonzero same-frame multi-writes to the same registry id+field. Cost low (rides #3).

Risk-per-cost leaders: #2 (closes production attribution cheaply if logs exist) and #1 (gates whether remediation is a hard-rail stage). **Independent note:** Rank-3 may not require domain instrumentation if accepted events already store mutations (they do in pipeline output) — finding §11's "needs instrumentation" may be overstated.

### B. Remediation requirements sheet (requirements, not design)

**(i) Deep-merge of nested sub-dicts.** Fixes nested key clobber where later mutation intends sibling subtrees only. Breaks intentional whole-subtree replace (abandon plan, clear commitments); tombstone/delete semantics must be explicit; replace-vs-merge becomes a per-field contract. Frozen-hash: likely moves wherever nested partial updates currently LWW-clobber. Gate: enumerate merge-vs-replace policy per field; golden runs both scenarios; replay/determinism; explicit hash authorization; prove no silent dual meaning on delete.

**(ii) Commit-time conflict rejection (same field, same entity, same frame).** Fixes silent F1: second writer cannot accept after first touched key; makes contention inspectable. Breaks benign intentional LWW (if any); death+HELP both writing health must reject or be domain-sequenced; event rates/rejection codes change. Frozen-hash: moves wherever second writes currently accept and alter state. Gate: catalog current same-frame multi-writers (from A#3); define winner policy (first-commit-wins + reject reason); freeze new rejection reason codes; full determinism suite; authorize hash.

**(iii) Mandatory field-level eq guards on every person-entity writer.** Fixes stale snapshot overwrites failing closed (aid+settlement class). Breaks: P10-1 freezes; content_hash/order shifts (P10-8); incomplete adoption leaves holes; does not fix F2. Frozen-hash: moves where second writes currently accept without eq; may move solely from precondition content in hashes/order. Gate: inventory all person writers; prove eq on every written key; churn matrix must include non-actor overwrite + death+HELP; measure rejection rates. Not sufficient alone (IND-C10).

**(iv) Enforce touched_scope ⊇ entity_updates keys (+ new_entities/removes policy).** Fixes F2 containment. Breaks any domain currently under-declaring but over-writing (latent bugs become rejections). Frozen-hash: moves only if production frames currently apply out-of-scope keys; may be hash-stable on clean scenarios. Gate: audit declared-vs-written scope across engines; fix under-declarations or accept new rejects; authorize hash only on measured drift.

**Stage-level minimum bar regardless of class mix:** (1) eliminate silent same-frame loss of an accepted write's field values — reject or merge with explicit semantics, inspectable outcome; (2) close F2 or document permanent scope-as-advisory with a new invariant (not silent); (3) ship a mandatory same-frame overwrite churn matrix (non-actor living_agent, health death+HELP, out-of-scope write); (4) re-baseline only with measured hash deltas and user authorization (hard rail); (5) no Category-2 immunity claim without A#4 evidence.

### C. Canon fix for F3 (smallest unambiguous change)

Stop using bare "invariant N" as a cross-doc identifier: namespace the two lists at their headings (culture list → C-1…C-12 / CULTURE-INV-N; SOT §19 → SOT-19.1…SOT-19.17); one cross-link footnote in CLAUDE.md/master protocol and SOT §19 ("numbers are not interchangeable across lists"); do NOT renumber in place (aliases only); optional one-liner in SOURCE-OF-TRUTH noting no invariant forbids same-frame silent field overwrite (see CORE-INTEGRITY-001).

### Secondary — concurrent stage7 intermittency

Classification only: suspected CAS/head-revision concurrent-test issue is not the same defect class as same-frame LWW via apply_mutation. Out of CORE-INTEGRITY-001; assign separate finding ID if still open; do not fold into F1/F2 remediation without shared-root-cause evidence.

---

## STOP — decisions that belong to Ryan

1. Rule every ledger row FIX / ACCEPT / DISPUTE (especially IND-C10, IND-C8, IND-C4).
2. Authorize or refuse probe re-runs (IND-JSON); whether JSON re-match is required before treating F1/F2 as closed evidence.
3. Supply or waive production artifacts for claim 4 (settlement:734 slice + 17/17 measurement).
4. Accept or reject demotion of claim 10 from "sufficient containment" to "partial hedge + residual risk register."
5. Whether standing culture-leg policy must be rewritten now (add F2 discipline, churn matrix shape, dual-write ban, nested-vs-top-level eq grain) before the next culture leg.
6. Whether GAP A#2/#3 may use accepted-event mutation traces instead of domain instrumentation (method ruling).
7. Remediation stage authorization remains deferred; when opened, which of (i)–(iv) are in-scope first.
8. F3 doc edit — authorize C-/SOT- namespacing as a pure-docs change (no hash impact).
9. SEC-CAS — confirm separate finding ID / park / ignore.
10. Independence caveat — accept this Grok pass as meeting the non-Anthropic reviewer requirement, or require a second non-xAI pass.

**STATUS:** Independent adversarial review complete (blind + forward). No code changed; nothing committed.
**RISKS:** Claim 10 overconfidence is the live process risk; F1/F2 mechanism claims stand on packet evidence subject to JSON re-run.
**NEXT STEP:** Ryan's dispositions on the ledger + whether to rewrite interim mitigation policy before any further culture work.

---

## Rulings (Ryan, 2026-07-25 — recorded by Cowork session; settled, do not re-ask)

1. **IND-C10: ACCEPTED — policy demoted and rewrite ordered.** The standing culture-leg containment policy is reclassified "necessary interim discipline with residual risk register (P10-1–10)" and must be rewritten — adding F2 scope discipline (entity_updates ⊆ touched_scope as leg-level rule), a required churn scenario matrix (non-actor living_agent overwrite, death+HELP health collision, out-of-scope write), a person-field dual-write ban across legs, and explicit eq grain (top-level key vs nested path) — **before the next culture leg opens.**
2. **Evidence: FULL PASS ordered.** Re-run both probes locally and diff against committed JSONs (IND-JSON); attach to the evidence pack: living_settlement_domain.py slice around :528/:734 + precondition-builder cites (IND-C4), the original 17/17 measurement artifact (IND-C4), SOT §19 excerpt (IND-C9); reconcile packet vs memory/evidence paths (IND-PATH).
3. **Doc fixes: BOTH.** IND-C8 wording replaces "necessarily moves" in finding §7 with the measured-hash formulation; F3 fixed via C-N / SOT-19.N namespacing, aliases only, no renumbering.
4. **SEC-CAS → CORE-INTEGRITY-002-CONCURRENCY-CAS** as its own finding ID (stub to be created; not folded into F1/F2 remediation). **Independence: this Grok pass ACCEPTED** as satisfying the non-Anthropic reviewer requirement (matches 8B Leg 1 precedent).
5. Remaining STOP items: remediation stage remains DEFERRED (unchanged); GAP-plan method ruling (accepted-event traces vs instrumentation) deferred to whoever executes the GAP plan; IND-C1-NOTE and IND-FIDELITY dispositions stand as proposed (ACCEPT with no promotion of synthetic results to production claims).

---

## Execution record (2026-07-25, Cowork session — all rulings executed; NOTHING COMMITTED)

**IND-JSON — CLOSED (VERIFIED).** Both probes re-run locally (exit 0):
`rerun_probe_8c_pipeline_write.json` and `rerun_probe_core_integrity_death_scope.json` in this folder. Semantic comparison (parsed JSON, depth-20 canonical re-serialize): rerun ≡ `memory/evidence/stage-8c-leg1/` copies for both probes. Same VERDICT string reproduced: "(b) lost update".

**IND-PATH — CLOSED (VERIFIED).** Packet JSON copies ≡ `memory/evidence/stage-8c-leg1/` copies (semantic identity, both files).

**IND-C4 — artifacts attached.** `artifact_002a18a4_living_settlement_domain_480-750.txt` and `artifact_002a18a4_living_agent_actions_280-500.txt` — sliced from the finding's pinned base SHA `002a18a4`, NOT the working tree (line drift exists at current tip: living_agent_actions.py is 641 lines both then and now, exposing a citation error — see correction below). All cited lines verified present at the base SHA: `:488` def `_replace_living_preconditions`, `:528` snapshot read, `:666` call, `:678/:680/:694` actor_update writes, `:734` `actor_update["living_agent"] = resulting_state`. **17/17 measurement artifact identified and attached:** `artifact_17of17_probe_8c_response_side_308.json` (= `memory/evidence/stage-8c-leg1/probe_8c_response_side_308.json`): `request_help_accepted_count: 17`, `requests_never_delivered_to_beneficiary: 17`, delivered_then_evicted/retained: 0/0.

**Citation correction found during artifact pass:** the finding §2 sentence places `_replace_living_preconditions` "at `:666/488-491`" inside a clause about `living_agent_actions.py`; both lines are actually in `living_settlement_domain.py` (verified by `git grep` at `002a18a4`; living_agent_actions.py has only 641 lines). Substance of the claim unaffected; file attribution should be corrected whenever the finding doc is next edited.

**IND-C9 — excerpt attached.** `artifact_SOT_section19_566-595.txt`. Discrepancy surfaced: the finding calls SOT §19 a "17-item" list; the current file continues to at least item 22. Grok's "different list entirely" conclusion unaffected (item 11 = receipt rule, confirmed); the count in the finding is stale or was written against an older SOT revision. Flagged, not silently corrected.

**IND-C8 + IND-C10 — doc edits applied (working tree, uncommitted):** finding §7 rewritten to the measured-hash formulation; finding header policy rewritten to the 7-point interim discipline with P10 register reference; review-status paragraph added to the finding header.

**F3 — applied:** namespacing note (C-N / SOT-19.N, aliases only, no renumber) added at `CLAUDE.md` invariants heading and `SOURCE-OF-TRUTH-v2.md` §19 heading, with the no-invariant-forbids-overwrite pointer.

**SEC-CAS — stub created:** `memory/CORE-INTEGRITY-002-CONCURRENCY-CAS.md`.

**Working tree after execution (branch `capability/stage-8c-phase1-aid-exchange`):** modified `CLAUDE.md`, `memory/CORE-INTEGRITY-001-lost-update.md`, `memory/SOURCE-OF-TRUTH-v2.md`; untracked `memory/CORE-INTEGRITY-002-CONCURRENCY-CAS.md`, `scratchpad/core-integrity-review/`. Upkeep-related untracked files in `scratchpad/` were NOT touched.
