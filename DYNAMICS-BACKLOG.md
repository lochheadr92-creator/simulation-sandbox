# Dynamics implementation plan

The only living document. Overwrite it freely; it carries no history and owes
no audit trail. If it disagrees with an archived doc, this one wins.

## What we are building toward

A world where things happen and have consequences; where there is a daily
rhythm you can read off the settlement; where people have relationships you can
follow over time; and where it surprises us.

## The five checks (these replace the old gates)

Every slice must pass all five: **Visible** (a player sees it in the world,
inspector or event history) · **Consequential** (it changes later decisions or
state) · **Recurrent** (across time, multiple actors — one firing is not a
behaviour) · **Diverse** (it doesn't just replace `rest` with a new dominant
loop) · **Deterministic** (same version, seed, inputs reproduce exactly).

Judged by watching the world and reading the numbers — not by event-count
bands, not by pre-registration. Baseline to beat is in `PRODUCT-STATE.md`:
**top-3 dominance 74.6%**, social share 20.8%, eight behaviours firing once per
320 ticks.

---

# The diagnosis this plan is built on

Three actions are 74.6% of the world. Look at *which* three: `rest`, `move`,
`tend` — all **single-step**. Now look at the eight that fire once and never
again: warn, share_information, trade, lie, threaten, apologise, promise,
reconcile — all **multi-step**: find a target, approach it, then act.

That is not a coincidence, and it is not a content problem. Measured
2026-07-28: person-007 selects WARN_DANGER at frame-1, moves toward
person-001, and at frames 2–3 emits **no proposal at all** — zero rejections,
nothing refused, just silence — then replans to REPAY_DEBT at frame-4. The
participant had moved. **Any behaviour that needs more than one tick to
complete dies the same way**, which is why the world is a single-step needs
loop with decorative garnish.

Everything else we could build sits behind that.

---

# Slice A — multi-step plans survive contact with the world

**Player-visible:** agents finish what they set out to do. You watch someone
head across camp to warn a neighbour and they *arrive and warn them* instead of
wandering off to repay a debt. The seven other multi-step social behaviours
start appearing more than once per run.

**Where:** `backend/domains/living_settlement_domain.py`, the continuation
block around lines 600–760 (`decision_kind` = `plan_continuation` / `replan` /
`failed_plan_replan`; `plan["status"] = "abandoned"`).

**Change:** when a plan's next step cannot be proposed because the world moved
under it (target relocated, participant occupied, distance re-opened), emit a
**re-approach step** toward the current target position rather than emitting
nothing. If the target is genuinely gone — dead, out of vision, invalid — fail
the plan **explicitly** with a receipt so it is visible in the event history
instead of silent. No new state; the plan already carries its goal, target and
step index.

**First 20 minutes:** confirm which branch swallows it. Instrument the
continuation block for person-007 at frames 2–3 on seed `living-agents-stage6`
and check whether a WARN candidate is generated at all. Absent ⇒ a precondition
on the participant is failing upstream in candidate generation; present but
unproposed ⇒ the fault is in this block. Fix follows the answer. This is inside
the slice, not a separate phase.

**Watch:** singleton count (8 → fewer), social share, top-3 dominance.
**Rollback:** single file, revert the commit.

# Slice B — people obey the day

**Player-visible:** the settlement has a rhythm. At night people rest and stay
in; by day they gather, tend and move about; social activity clusters where
people are actually co-located. You can glance at the world and tell roughly
what time it is.

**Where:** `core/constants.py:171` already has `is_night(tick)`. The kernel
uses it (`core/kernel.py:112`) and `animal_domain.py:33` uses it — **animals
already live by the day cycle and people do not.** Wire it into the
`living_settlement` candidate scoring.

**Change:** a phase multiplier on existing candidate scores — REST up at night,
gather/tend/explore up by day, social up around dusk when people converge. No
new domain, no new state, no new events: it re-weights candidates that already
exist. Derived from `tick`, so determinism is untouched.

**Watch:** action mix per 100-tick window should now vary *with the phase*
rather than being flat — that is the whole point, and it is also the first
metric this project will have that shows time meaning something.
**Rollback:** revert; scores return to phase-neutral.

# Slice C — threats have an aftermath

**Player-visible:** a predator comes near and the settlement visibly reacts —
people warn each other, move away, check on the injured — and then, over the
next dozen ticks, settles back to normal. Cause and aftermath you can follow in
the event log.

**Where:** `domains/animal_domain.py` already implements exactly this shape for
animals: `FLEE_PERSIST_TICKS` keeps an animal fleeing for several ticks after
the threat leaves. People have no equivalent. Mirror it in the settlement
domain.

**Change:** an observed threat opens a bounded **alert window** on the observer
that boosts warn / flee / help-the-injured candidates while it lasts, then
decays. Existing observations, existing candidates, existing bounded-state
pattern copied from a domain that already ships it.

**Watch:** does the action mix visibly deform around threat events and recover?
Do multiple actors participate, or is it one agent reacting?
**Rollback:** revert; window length is one constant.

# Slice D — signals that do something

**Player-visible:** information travels. Someone sees a threat or a food source,
tells someone, and that person acts on it — you can follow the chain in the
event history from observation to telling to action.

**Where:** `domains/ecology_domain.py:155` `_expire_signal`. Signals are being
created and expiring at **681–860 per 320 ticks** — the single largest event
family after `lifecycle_tick`, and as far as behaviour is concerned it is
churn. `share_information` and `VERIFY_INFORMATION` already exist and fire once
per run.

**Change:** an unexpired signal an agent has observed biases that agent's
candidates — toward acting on it, and toward telling someone who hasn't heard
it. This gives the eight singletons an actual reason to exist rather than a
threshold that happens to be reachable once.

**Watch:** share_information and verify recurrence; unique actors; whether a
signal ever produces a second-order action.
**Rollback:** revert.

# Slice E — relationships you can follow

**Player-visible:** select two people in the Inspector and see their history —
who helped whom, what is owed, whether it was repaid, whether trust went up or
down. The thread the world already tracks, made legible.

**Where:** trust and debt already drive `REQUEST_HELP` and `REPAY_DEBT`
(request_help 130, repay 44 per 320 ticks — the machinery works). The gap is
that none of it is visible, and nothing else consumes it.

**Change:** surface per-pair relationship history in the Inspector, and let
standing debt and low trust bias who gets asked next. Frontend plus a read
model; no canonical state change.

**Watch:** relationship changes that persist and matter; whether pairs form
threads or churn randomly.
**Rollback:** frontend-only revert.

---

## Order, and why

**A first** — without it, every behaviour B through E adds dies the way warn
died. It is also the smallest diff on this page.
**B second** — cheapest visible win in the project, using a function that
already exists and is already used by animals.
**C then D** — both are "consequences", both copy a pattern the codebase
already ships, both need A to survive.
**E last** — it makes the existing relationship machinery legible, and it is
worth more once A–D have given those relationships something to be about.

## Standing items, not blocking

- **Commit the R1 retarget.** Already built and measured: top-3 dominance
  74.6% → 62.8%, social share 20.8% → 33.0%. Fails the retired ±3% band. Update
  the hash pin in the same commit. Do this with Slice A, since A is what fixes
  the `warn` regression it introduced.
- **Run the live UI suites and merge the frontend branch.** Needed before
  Slice E has anywhere to render.

## Known engine debts — fix only if they block the above

- Group-contract identity is content-dependent, so `collective_groups` has no
  stable A/B surface. Blocks the energy-lost-update remediation only.
- Per-parameter-per-entity RNG keying is owed before anything touches
  population counts.
- `collective_groups`' 1,000-tick hash has not been re-measured since
  `2d68ac16`.
