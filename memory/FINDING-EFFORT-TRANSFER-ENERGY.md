# FINDING — the `+40 / −20` effort-transfer energy pair (`cooperate`, `help`)

**Status: OPEN — needs a ruling, not a fix. Raised 2026-07-26.**
Moved out of `memory/REGISTRY-COMPONENT-OWNERSHIP.md`, where it was carried as
finding **F11** and was misclassified twice. Registry cross-reference kept.

**Not a numbered family.** Deliberately named `FINDING-…` rather than opening a
`BEHAVIOUR-…-001` series: `CLAUDE.md` forbids inventing taxonomy categories
unilaterally. Fold it into a family if you want one.

---

## What this is

```python
# living_agent_social.py:435-437   (cooperate)
updates[target_id]["energy"] = min(1000, int(target.get("energy", 0)) + 40)
updates[actor_id]["energy"]  = max(0,    int(actor.get("energy", 0))  - 20)

# living_agent_actions.py:502-504  (help) -- IDENTICAL pair, plus +50 health
"energy": min(1000, int(target.get("energy", 0)) + 40),
actor_update["energy"] = max(0, int(actor.get("energy", 0)) - 20)
```

One actor spends 20 energy; one target gains 40. Both ends clamp.

## Two misclassifications, both corrected here

**1. It is not an ownership or lost-update finding.** It entered the registry
as F11 because the ownership tests found `living_agent_social` writing `energy`
cross-entity, which no inventory pass had recorded. That *writer* fact is real
and stays in the registry. But a single `cooperate` proposal writing both
energies is **one event touching two entities** — not two events touching one,
which is the collision shape. Measured: `living_settlement` 320 has 37
cooperates and **0** same-tick energy collisions. No CAS fixes anything here,
and it does not belong in the CORE-INTEGRITY family.

**2. It is not a conservation defect either** — and this corrects the framing
the reclassification was requested under, plus my own earlier "+740 units of
invented energy". **Energy is a non-conserved quantity by design:**

- `rest` mints 80 energy from nothing every time (`living_agent_actions.py:435`,
  `min(1000, energy + 80)`). Nothing offsets it.
- The engine *does* have conservation validators — `living_action.nonconserving_
  transfer` (`living_agent_actions.py:643-647`) and `social_action.
  nonconserving_exchange` (`living_agent_social.py:596`) — and both are scoped
  to **resource** transfers (food/wood). Energy is deliberately outside them.

So "cooperate does not conserve energy" describes the engine working as
designed, not a defect. Asking what `cooperate` "is supposed to conserve" has
a defensible answer: nothing — same as `rest`.

## The measured numbers, which are the actual finding

The nominal arithmetic is `+40 − 20 = +20` net per cooperate. **Clamping makes
the realized effect diverge from that, and invert its sign.** Replaying the
accepted-event stream in canonical commit order and summing real per-event
deltas on `cooperate` events only, on the frozen `living_settlement` 320
baseline at its confirming hash
`897f3f7f48e8bc292068d1a5a017236a293808901e3ce7736ccfb8a03903c5ab`:

```
cooperate events             : 37
unclamped ceiling (+20 each) : +740        <- NOT a measurement
ACTUAL net energy delta      : -420
  target writes clamped by min(1000, ...) : 29 of 37
  actor  writes clamped by max(0, ...)    :  0 of 37
```

Agents sit near full energy, so **29 of 37** target gains evaporate at the
ceiling while every actor cost lands in full. In this baseline `cooperate` is
net energy-**destroying**, by −420.

**It replicates on the other frozen baseline** (`collective_groups` 1,000, hash
`43893bdde4ce4b93c6076650326861b66ff8bd6343a7568653d122917db1638a`), so this is
not a `living_settlement` quirk:

| Baseline | cooperates | nominal | **actual** | target clamped | actor clamped |
|---|---|---|---|---|---|
| `living_settlement` 320 | 37 | +740 | **−420** | 29 (78%) | 0 |
| `collective_groups` 1,000 | 232 | +4,640 | **−1,650** | 170 (73%) | 0 |

Three things the pair shows that one baseline could not:

- **The sign inverts in both**, at a near-identical clamp rate (78% / 73%).
- **`max(0, …)` never fires — 0 of 269 actor writes across both runs.** The
  floor clamp is effectively dead in practice; `min(1000, …)` is the only one
  that is load-bearing. Any ruling should treat the two clamps differently.
- **Per-event magnitude differs** (−11.35 vs −7.11), which is direct evidence
  for the state-dependent gradient in §"What is actually open" — the effect
  tracks how full the targets happen to be, rather than being a fixed penalty.

*Any earlier "+740 units of invented energy" figure — including in
`REGISTRY-COMPONENT-OWNERSHIP.md` before 2026-07-26 — was an unclamped ceiling
mistaken for a measurement. Wrong in magnitude and in sign. The same applies to
`+4,640` for `collective_groups`; both ceilings are shown above only to
contrast them against the measured values.*

## What is actually open

1. **The realized effect is state-dependent and unexamined.** The same action
   creates energy when the target is depleted and destroys it when the target
   is near full. Whether that gradient is intended — cooperation helps most
   those who need it, costs the group when it doesn't — or is an accident of
   two clamps, is unrecorded either way.
2. **The constants have no evidence record.** `+40`, `−20`, `+50`, `+80` are
   inline literals with no named constant and no comment. `CLAUDE.md`:
   "Constants live beside the code with a one-line comment naming the evidence
   that set them." Compare `core/constants.py:25`, `SLEEP_ENERGY_TARGET = 950`,
   which does carry its rationale. **This is the one concrete, actionable gap.**
3. **The pair is duplicated, not shared.** `cooperate` and `help` both hardcode
   `+40 / −20` independently. Changing one silently diverges them.

## Disposition

**Needs a ruling from Ryan**, not a code fix:

- If the gradient is intended → name the constants, record the evidence beside
  them, and this closes.
- If it is not → it is a behaviour change, and it is **re-baseline-class**:
  37 cooperates are baked into the frozen `living_settlement` 320 hash and 232
  into `collective_groups`, so altering the arithmetic moves both. That needs
  an authorised re-baseline STOP.

**Out of scope where it was raised.** Not fixed in the ownership audit; no code
touched. Cross-referenced from `REGISTRY-COMPONENT-OWNERSHIP.md`, whose Table 1
`energy` row retains the ownership half (the undeclared cross-entity writer).
