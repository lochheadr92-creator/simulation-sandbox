# Operating model — Domain Delivery Legs

Adopted 2026-07-28. Replaces the capability-stage ladder and the
investigate → harden → document → find-another-concern loop.

**Domain delivery is the default activity. Maintenance is the exception.**

## The loop

    choose behaviour → prove it can occur → implement thin version →
    expose it visually → test combined behaviour → ship domain → move on

A domain is only worth implementing when it completes this chain:

    world condition → agent opportunity → decision → action →
    state change → memory/social consequence → visible evidence

Anything that does not complete that chain is infrastructure, not a delivered
domain.

## Maintenance freeze (in force)

Maintenance is permitted **only** when one of these is true:

1. The current domain cannot activate.
2. The current domain produces incorrect authoritative state.
3. Deterministic replay breaks.
4. Data corruption or uncontrolled growth occurs.
5. A bug prevents the user from observing the behaviour.

Maintenance is **not** permitted because code could be cleaner, abstractions
could be improved, diagnostics could be broader, an edge case exists outside
the current scenario, documentation could be fuller, or another subsystem might
eventually need restructuring.

**Budget: 70% domain implementation · 20% integration and visualisation ·
10% maintenance.** If maintenance exceeds roughly one session during a leg,
stop and reassess whether the domain is too coupled or the architecture is
fighting us.

## Anti-maintenance rules

1. No broad architectural audits during an active leg.
2. No refactor unless it removes a blocker encountered at least twice.
3. No new diagnostic framework unless current tools cannot explain the failed
   chain.
4. No documentation expansion before behaviour works.
5. No speculative support for future domains.
6. No domain is complete without a visible consequence.
7. No more than one new subsystem per leg.
8. Every session must either move the active causal chain forward or explicitly
   close a blocker.

## Domain-done gate — six conditions

**Reachable** (occurs organically in a normal scenario) · **Deterministic**
(same seed and inputs, same authoritative results) · **Consequential** (changes
a later decision or meaningful state) · **Integrated** (works beside existing
domains without disabling them) · **Visible** (a normal observer can see and
understand it) · **Bounded** (memory, events and state growth controlled).

Perfection is not required. `PASS WITH LIMITATIONS` is a healthy completion —
state the limitation instead of expanding the contract until every future case
is covered.

## Session cadence

| session | output |
|---|---|
| A — definition and activation | causal chain defined, scenario built, prerequisites proven to occur, blockers identified |
| B — thin implementation | opportunity, decision, event, authoritative consequence committed |
| C — integration | memory/relationship effect wired; later behaviour demonstrably changes; determinism and fork tests |
| D — presentation | animation or indicator, plain-language event, causal explanation, tested in the normal UI |
| E — hardening and freeze | boundedness, regression tests, known limitations, commit, mark complete |

Some domains take more than five sessions. The structure exists to stop
investigation swallowing the leg.

---

# Domain backlog

Ranked by visible life added, not architectural sequence.

## Tier 1 — existing-domain completion (do these now)

Existing memory, witness, trust, group and resource machinery can support all
of these.

1. **Information sharing** ← ACTIVE, see `ACTIVE-LEG.md`
2. Social approach and conversation
3. Helping and refusal
4. Relationship adjustment
5. Group cooperation
6. Shared shelter maintenance
7. Resource conflict

## Tier 2 — settlement dynamics (after Tier 1 is visibly working)

Task specialisation · leadership influence · informal rules · reputation ·
exclusion and reconciliation · communal resource ownership.

Two candidates already scoped and cheap, to slot in here:

- **Day rhythm.** `is_night(tick)` exists at `core/constants.py:171`; the
  kernel and `animal_domain.py:33` use it, people do not. Wiring it into
  settlement candidate scoring gives the settlement a readable daily shape.
- **Threat aftermath.** `animal_domain.py` already ships bounded post-threat
  persistence (`FLEE_PERSIST_TICKS`); people have no equivalent.

## Tier 3 — not yet

Trade economies · politics · law · religion · warfare · generational
inheritance · language evolution · advanced culture. These multiply integration
complexity before the basic social loop is alive.

---

## Containment passes

Maintenance is batched, not continuous. After every two or three completed
domains, run one pass: remove duplicated logic, address repeated performance
problems, simplify interfaces that multiple domains have exercised, improve
shared diagnostics, update architecture docs, delete dead experiments.

Refactoring an interface before several domains have used it is guessing.

## Carried debts — do not touch unless they block the active leg

- A multi-step plan whose participant moves emits no proposal for two ticks and
  is then replanned away (measured 2026-07-28, person-007, frames 2–3, zero
  rejections). This is the likeliest blocker for any domain requiring approach
  before action — fix it **inside** the leg it blocks, under freeze rule 1.
- Group-contract identity is content-dependent, so `collective_groups` has no
  stable A/B surface.
- Per-parameter-per-entity RNG keying is owed before anything touches
  population counts.
- `collective_groups`' 1,000-tick hash unmeasured since `2d68ac16`.
- The R1 retarget is built and measured (top-3 dominance 74.6% → 62.8%, social
  share 20.8% → 33.0%) but uncommitted; it loses the single `warn` firing to
  the plan-stall defect above.
