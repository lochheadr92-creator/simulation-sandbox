# CAPABILITY-DOCTRINE.md — Execution Doctrine

Defines how future work is selected and executed.

It claims no authority over simulation behaviour:

- `SOURCE-OF-TRUTH-v2` remains the architecture authority.
- Delivered stage and contract documents remain the binding record of implemented behaviour.
- The committed simulation record outranks every document, including this one.

Where stage prompts or roadmaps conflict with this doctrine, this doctrine governs what is built next and nothing else.

Historical design documents are retired individually through the Retirement Rule. They are never declared obsolete in bulk.

## Non-Negotiable Floor — The Product

- Deterministic repeat, replay and resume.
- Proposal-only domain authority. Core alone writes truth.
- Survival pressure dominates every influence.
- Forbidden fields in culture records: inventory, authority, obedience, orders, law, command, punishment.
- No destructive git operations.

## Baselines — Two Classes

### Regression baselines

- `living_settlement`: `48dfec22…1b1e3b` (re-baselined 2026-07-27, authorised at
  stage 1 of the age-realism re-baseline leg — genesis RNG sub-streams + spawn
  index; gate and attribution in
  `memory/evidence/genesis-rng/SHARED-SPAWN-STREAM-2026-07-26.md`. Prior
  baselines `897f3f7f…3c5ab` (2026-07-25, Layer C Variety Leg 1) and
  `84d3ad52…c32d2`)
- `collective_groups`: `659a27f3…920342` — **STALE AS OF 2026-07-27, VALUE NOT
  YET RE-MEASURED.** The genesis sub-stream + spawn-index change is global to
  world generation and no scenario overrides `person_age_range`, so this hash
  has necessarily moved too. It was NOT re-baselined in stage 1: its recorded
  invocation is 1,000 ticks, no bands were pre-registered for it, and the leg
  prompt authorised the `living_settlement` re-baseline only. Measured and
  recorded at the leg close-out, and only with explicit authorisation at that
  STOP. **Do not treat the value above as a passing gate in the meantime.**

Regression baselines never change without explicit user authorisation at a STOP.

### Scenario baselines

The active culture scenario and successor scenarios may be re-baselined whenever the scenario intentionally changes.

Every scenario re-baseline must:

- reverify repeat, replay and resume;
- record the new hash;
- update every affected assertion;
- land in the same commit as the intentional scenario change.

## Cadence

One capability → one implementation → one verification → one coherent commit series → one STOP.

Never batch separate capabilities.

The next checkpoint begins only after the user gives approval.

## Selection — Pressure Decides

At every STOP, identify the currently measured pressures:

- What is impossible in the world today?
- Why is it impossible?
- What committed-run evidence proves that limitation?

An unmeasured world reports no pressure.

Widening measurement through a read-only probe is therefore a valid capability when the missing measurement prevents a sound decision.

Present two to four candidate capabilities ranked by Capability Score.

### Numerator

Every claim must cite committed-run evidence. No evidence means no credit.

Count:

- named pressure relieved;
- existing domains connected, minimum two;
- new emergent interactions made possible.

### Denominator

Count in concrete units:

- files touched;
- net new constants;
- new registries;
- new schemas;
- new configuration surface.

New registries and schemas have a target of zero.

Roadmap position scores zero.

Recorded deferrals are pre-registered pressures. A deferred gate becomes eligible when its recorded pressure condition is measurably present. No stage number is required.

Pressure ranks. The user rules.

## Existing-First Rule

If the behaviour can emerge by extending an existing subsystem, extend it.

If an existing subsystem blocks worthwhile behaviour, improving that subsystem is the capability.

Only create a new subsystem when the target behaviour is impossible through an existing subsystem.

Use the smallest new subsystem capable of producing the behaviour.

Never invent two subsystems in one checkpoint.

## Verification

The standing verification gate is fixed-cost and is never scored against a capability:

- focused tests;
- forged-field rejection wherever records change;
- deterministic repeat, replay and resume;
- regression baselines byte-identical;
- scenario baseline recorded;
- target behaviour demonstrated on an organic run using a fixed declared scenario seed, without directly seeding the target behaviour.

The behaviour proof must be traceable through committed events and answer:

**What can happen today that was impossible yesterday?**

Independent adversarial review occurs at the user's call for each checkpoint.

## Complexity Ledger

Every checkpoint report records:

- net new constants;
- net new registries;
- net new schemas;
- net new configuration surface;
- files touched;
- mechanisms removed;
- constants removed;
- abstractions simplified;
- documents retired or merged.

Deletions and simplifications are credited.

Complexity should remain flat or fall relative to each observable behaviour gained.

## Retirement Rule

Every checkpoint must evaluate whether the delivered capability made an existing mechanism, constant, abstraction or document unnecessary.

Where something has become unnecessary:

- remove it;
- merge it;
- simplify it;
- or record why it must remain.

Behavioural removals pass the same verification gate as additions.

Complexity should not only grow slower than capability. It should occasionally shrink.

This doctrine is itself subject to retirement.

## Stop Immediately If

Stop if:

- a new architectural framework would be required;
- more than one subsystem must be invented at once;
- new verification machinery would exceed the implementation being verified;
- the target behaviour cannot be demonstrated;
- deterministic guarantees would be weakened.

The existing fixed verification gate does not count as new verification machinery.

## Checkpoint Report

At every STOP, report:

1. Capability delivered and the impossible-yesterday trace.
2. Pressures now measured: what remains impossible and why.
3. Two to four ranked next candidates with evidence-based scores.
4. Complexity ledger, including credited retirements.
5. Verification results and hashes.

Then STOP.
