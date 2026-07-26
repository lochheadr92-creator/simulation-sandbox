# THE SPINE — Simulation Sandbox

**Status: PROPOSED (2026-07-24).** Owner: Ryan Lochhead.
**Read this first.** It is the one-page map of the project: the layer stack, what
is actually weak right now, the rules every layer obeys, and the single current
front. It is a *navigation* document — it does not redefine truth or architecture.
Operational rules live in `ARCHITECTURE-SPINE.md`; canonical-truth doctrine lives
in the Source of Truth. When documents conflict, the higher authority wins (see
`ARCHITECTURE-SPINE.md` §Authority).

---

## 1. What this is

Simulation Sandbox is a **deterministic living-world simulation engine**. It
produces autonomous worlds where entities persist, actions arise from simulated
state, every lasting change is causally traceable, agents act only on their own
perception and memory, and replay reproduces canonical state exactly. Players
observe, and later influence, without bypassing Core. Generated prose may
*present* the world; it is never canonical truth.

### Authority, archive & vision (kills the two-authorities failure mode)

- **THE-SPINE + `FRONTIER.md` are the single strategic authority** for the
  project's current state and next work. Nothing else declares the frontier.
- **`CAPABILITY_ROADMAP.md` / `ROADMAP.md` are historical archive** — closed-leg
  records, old hashes and test counts, for forensic reference only. They do **not**
  declare current state. (Physical move to `docs/archive/` is a later
  documentation-migration step; until then they carry a demotion header pointing
  here.)
- **The Domain Plan (`/Domain Plan.txt`) remains the long-range vision/catalogue**
  for unbuilt layers (F–I and beyond). THE-SPINE is the *executable build-order*
  derived from it; where they differ on what may be built **now**, the SPINE wins.
  The old `DOMAIN_MAPPING.md` bridge is superseded by the A–I stack + registries →
  archive. *(Later task: reconcile the A–I stack against the Domain Plan catalogue
  so no envisioned domain is orphaned.)*

## 2. The layer stack (A–I)

The world is built bottom-up. A layer should not be built until the one beneath
it is real.

```
I  Player Product        (cross-cutting — see Rail D, not a final layer)
H  Demography & History
G  Institutions
F  Economy   ── F-A material surplus · F-B economic coordination
E  Collective Behaviour  (groups, norms, culture)
D  Interaction           (communication, transfer, help/harm, relationships)
C  Individual Agency     (perception, memory, needs/drives, planning, action)
B  Physical World        (time, space, weather, resources, lifecycle, structures)
A  Kernel                (determinism, validation, commit, replay)
```

## 3. Where the project actually stands (dual-axis status)

Two separate questions, not one: is the *mechanism* built, and does the behaviour
*happen organically often enough to shape the world*? Plus its delivery status.

| Layer | Mechanism | Organic life | Delivery | Evidence |
|---|---|---|---|---|
| A Kernel | SOLID | — | VERIFIED | regression suite passes; frozen hashes verified |
| B Physical World | SOLID | — | VERIFIED | harness runs |
| **C Individual Agency** | **survival SOLID · non-survival drives THIN** (one drive, Upkeep, added 2026-07-25) | **THIN** (rest 32.1%, was ~90%; action entropy 2.31 bits, was 0.75) | **PARTIAL** — Variety Leg 1 closed; social density, individuality, memory not started | `memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md` §6; `BEHAVIOUR-BASELINE-001` |
| D Interaction | SOLID | THIN (rich actions fire ~once/1000 ticks) | VERIFIED-mech | `BEHAVIOUR-BASELINE-001` |
| E Collective Behaviour | SOLID | THIN ("machinery, not felt culture") | VERIFIED-mech; deposit DEFERRED *(arch. 7C)* | Layer-E close-outs *(arch. 8A/8B)* |
| F Economy | ABSENT | ABSENT | PARKED | — |
| G Institutions | ABSENT | ABSENT | PARKED | — |
| H Demography & History | ABSENT | ABSENT | PARKED | — |
| I Player Product | projections exist (event log, inspector, causal chain) | — | ONGOING (Rail D) | — |

Status words are fixed: **mechanism** ∈ {ABSENT, THIN, SOLID}; **delivery** ∈
{DISCOVERY, CONTRACT, AUTHORIZED, IMPLEMENTING, VERIFYING, VERIFIED, PARTIAL,
DEFERRED, REJECTED, SUPERSEDED}. No other wording for status.

## 4. Why work is being re-sequenced

Two things were built out of order and both stalled:

1. **Culture (E) outran individual behaviour (C).** Norms and transmission were
   layered on a world where agents **rested ~90% of the time** and every rich action
   fired ~once per 1,000 ticks [`BEHAVIOUR-BASELINE-001`]. Culture can't feel alive
   on an idle world — hence "machinery, not felt culture." *(Historical: the rest
   half was addressed by Variety Leg 1 — see §3. The rich-action half was not;
   social density is the next Layer C item.)*
2. **Aid (E) outran the economy (F).** Giving needs a surplus; nobody has one under
   survival pressure. 7C (group deposit) was recorded as dying the same way, and
   **for 7C that diagnosis is falsified** (2026-07-26, VERIFIED — see §8). Not
   because surplus exists, but because the chain dies four steps earlier: agents
   perform **one** storage action in 1,000 ticks and **zero** `store` actions,
   so no `shared_storage` fact is ever derived and the deposit is never even
   considered. Surplus is neither confirmed nor refuted as a blocker; it never
   gets to be the question. *(An intermediate note that day blamed
   `STORE_SURPLUS`'s `food >= 3` gate for stores failing to pair — void: stores
   do not fail to pair, they do not happen.)* 8C Leg A's surplus diagnosis is
   separate either way — it has its own 17/17 evidence and needs its own check.

The correction is just to respect the stack: **fill C now** (ordinary life), before
more E; keep aid parked until **F-A** (material surplus) exists. Same order Maslow
and Dwarf Fortress both use — daily needs and behaviour precede social esteem and
culture. We learned it the hard way; it is written down now.

## 5. Current frontier

Owned by `FRONTIER.md` (the only file that declares the current task). Summary:

> **Layer C — Individual Agency: behaviour enrichment.** Order: variety → social
> density → individuality → memory. **Active leg: NONE** — both most-recent legs
> closed 2026-07-25. Variety Leg 1 (Upkeep drive) VERIFIED–CLOSED: agents rest
> less and tend worn structures on their own initiative (rest 73.3%→32.1%
> `living_settlement`; 89.5%→40.9% / 88.9%→47.2% `collective_groups`; entropy
> 0.75→2.31 / 1.52→2.46 bits; frozen hash re-baselined `84d3ad52…c32d2` →
> `897f3f7f…3c5ab` with authorisation). CORE-PERF-01 (Layer A infra)
> VERIFIED–CLOSED, hash-neutral, ~1.2–2.1×. **Next, not started:** Layer C social
> density — needs its own probe + contract phase (C-12 v2) before any
> implementation.

## 6. The five rails (every layer obeys these)

- **Rail A — Canonical truth.** Every lasting change travels
  `observe → propose → order → validate → commit → event → state → projection`.
  No layer bypasses Core. (Full path: `ARCHITECTURE-SPINE.md`.)
- **Rail B — Ownership & ordering.** Every canonical component has exactly one
  owner; every cross-owner write has an explicit contract; every ordering
  dependency is centrally registered and **tested as a relationship, not a literal
  priority number**.
- **Rail C — Organic reachability.** A mechanism is not "alive" because a test can
  fire it. Each layer measures frequency, actor spread, scenario spread, repeated
  episodes, and downstream consequence.
- **Rail D — Player visibility.** Every accepted leg must be observable in at least
  one of: world view, inspector, event log, causal-chain viewer, replay timeline.
- **Rail E — Evidence.** Every SOLID/THIN/PARKED claim links to a deterministic run,
  tests, hashes, close-out evidence, and (if deferred) a re-entry condition.

## 7. Protective registries (the three that prevent our real bugs)

Built from a read-only code inventory, risk-first (see `ARCHITECTURE-SPINE.md`).
Indexes, not essays. Each stamped "as of `<commit>`".

- **Component Ownership Registry** — who owns/writes each canonical field. Direct
  control against the lost-update class (CORE-INTEGRITY-001).
- **Domain Ordering Registry** — phase/priority/reads/writes/before/after + the
  *reason* each ordering protects. Tests assert the relationship, not the number.
- **Event Family Registry** — producer, validator, mutations, causal parents,
  lifecycle, projection, replay handler per event family.

## 8. Deferrals & re-entry conditions

| Item | Delivery | Blocker | Re-entry condition | Preserved |
|---|---|---|---|---|
| Aid Exchange *(arch. 8C Leg A)* | DEFERRED | needs **Layer F-A material surplus** (not full economy) | a committed run shows reliable transferable surplus | `lega_v2_full.patch`: priority-5 window, keep-one guard, RESPOND_AID 3334 |
| Layer-E collective deposit / group storage *(arch. 7C)* | DEFERRED | **agents never perform storage actions at all** (VERIFIED 2026-07-26) | Registries form, all 12 groups are recognised, the domain activates — it stops at gate 3, zero `shared_storage` facts ever. Cause measured, not inferred: the 1,000-tick run contains **one** storage action in total (a `retrieve` of 1 food, `person-006`, tick 7) and **zero `store` actions**. `storage-camp`'s `{food: 0, wood: 12}` is genesis seeding (`{food: 1, wood: 12}`) minus that one retrieve — nothing was ever deposited. The 4-tick pairing rule (`association_contracts.py:303-316`) is resource-agnostic and never becomes the binding constraint. **Re-entry condition: ≥2 distinct agents perform storage actions on a shared storage organically.** *(Supersedes the "surplus falsified" framing in §4 and the earlier `food >= 3` attribution — why agents never store is a separate, unverified question.)* | mechanism on branch; probes `_probe_f8_collective_preconditions.py`, `_probe_f8_storage_pairing.py` |
| CORE-INTEGRITY-001 remediation | DEFERRED | authorized re-baseline (moves frozen hashes) | dedicated core-integrity stage at a STOP | finding + probes on branch |
| CORE-INTEGRITY-003 remediation *(frame-knowledge aliasing)* | DEFERRED | authorized re-baseline (moves frozen `living_settlement` + `collective_groups` hashes) | dedicated core-integrity stage at a STOP | finding + withheld fix described in `memory/CORE-INTEGRITY-003-frame-knowledge-aliasing.md` |
| Remaining Layer-E culture (plurality, enforcement, diffusion) *(arch. 8C–8D)* | not started | behaviour + social density (Layers C, D) | C and D organically thicken | — |

## 9. Coherence test (the project is coherent when a newcomer can answer these from the docs, not from chat history)

1. What is the product? 2. What owns canonical truth? 3. Exact runtime path of a
world transition? 4. Which component does each domain own? 5. Which domains may
write each entity? 6. Why do domains run in their current order? 7. Which event
families exist? 8. Which scenario enables each capability? 9. What can the player
currently see? 10. Which capabilities are verified / partial / deferred / rejected?
11. What is the current frontier? 12. Which evidence proves the current baseline?
13. What exact condition reopens each deferred item? 14. What must pass before a
capability is accepted?

If any answer needs a past conversation or an agent's memory, the spine is
incomplete.

## 10. Prior art — *design reference, not project authority*

Comparable living-world sims that solved these problems (full write-up:
`docs/research/LIVING-WORLD-PRIOR-ART.md`). They inform patterns and risks; they do
**not** set our schemas, constants, ordering, or acceptance gates.

- **Dwarf Fortress needs system** — 27 non-survival needs; unmet needs damage
  "focus"; needs weighted by personality. Directly cures our idle-agent problem;
  the personality weighting *is* our individuality layer.
- **The Sims / needs-based AI (Zubek)** — needs decay; the *world advertises*
  actions with rewards; agents choose by urgency. The "advertisement" pattern is
  our north star for modular drives (not built in Leg 1).
- **RimWorld** — legible traits (individuality) + decaying thoughts (memory/mood).
- **Talk of the Town** — characters observe, tell, misremember, lie; knowledge
  mutates as it spreads. Our D/memory frontier.
- **Utility AI (Dave Mark) / BDI** — confirm our scoring + the belief/desire/
  intention framing (Beliefs = knowledge/memory, Desires = drives, Intentions =
  plans/commitments).

---

*Process: cloud session owns this spine, the frontier, the registries, and
contracts; the terminal session implements. One leg at a time: contract →
implement → gate → STOP.*
