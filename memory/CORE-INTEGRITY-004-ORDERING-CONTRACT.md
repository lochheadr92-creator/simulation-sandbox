# CORE-INTEGRITY-004 — proposal commit ordering is content-independent

**Status: IMPLEMENTED (branch `core-integrity-004`, not merged).** Trajectory
hashes move by design; **nothing re-baselined here**. The migration/re-baseline
decision is separate.

## Why content-derived data must not order proposals

`order_key` previously ended in `content_hash`, which `normalize_proposal`
computes over `core_fields` — including `preconditions` and `mutation`.
`PHASE_RANK` has two ranks and `engine_priority` is domain-level, so nearly every
agent proposal tied on the first three components and **content decided
behavioural commit order**.

Measured at 320 ticks: **5,804 / 6,291 proposals (92.3%)** in `living_settlement`
and **6,258 / 7,205 (86.9%)** in `collective_groups` sat inside tie groups
resolved only by `content_hash` — 82 of those groups were size 8, i.e. all eight
people every tick.

Proven at tick 1: adding a **semantically inactive** precondition — one pinning a
value already true, which cannot fail — completely permuted the frame's commit
order *before any guard was evaluated*:

| | first six proposals, tick 1, `living_settlement` |
|---|---|
| plain | `person-007, 005, 004, 006, 003, 000` |
| + inactive precondition | `person-001, 006, 007, 000, 004, 005` |

Every downstream difference — actions, deaths, hashes — followed from that
reorder, not from the precondition doing anything. This made *any* content edit a
silent, chaotic behaviour change, and made A/B experiments on proposal content
unfalsifiable. It is what forced the OQ-1 energy containment experiment to
`INSUFFICIENT / INCORRECT`.

## The ordering contract

```
order_key(p) = (requested_time,
                phase_rank,            # PHASE_RANK: environment=0, agent=1
                engine_priority,
                proposer_engine_id,
                entity_id,
                proposal_type,
                tuple(sorted(touched_scope)))
```

Every component is fixed by the proposal's **semantic origin** — who acts, in
what way, upon what — before its mutation or preconditions are constructed.

No component may derive from: preconditions, mutations, receipt or diagnostic
metadata, dictionary serialisation, `content_hash`, runtime object identity,
unordered set/dict iteration, randomness, or the proposal's position in the
submitted list. The last of these preserves the doctrine recorded at
`normalize_proposal`: *shuffling submission order never changes final commit
order.*

**No ordinal component exists.** One was investigated and rejected: it would have
derived from incoming list position, disguising submission order as semantic
identity.

## `touched_scope` as the 7th component

Required because one actor can legitimately emit several proposals of the same
type in one frame. Food-interaction contention has `person-b` emit two
`fulfil_food_interaction` proposals distinguished only by what they fulfil:
`['fi-66c1…', 'person-a', 'person-b']` versus
`['fi-00f0…', 'person-b', 'person-c']`.

`touched_scope` is declared by the proposer, validated by `check_scope_exists`,
and already canonically sorted for `core_fields`. It is semantic scope, not
payload — adding a precondition, adding receipt metadata, reordering mutation
keys, or changing mutation values all leave it unchanged.

## Duplicate rule — fail closed

`assert_unique_order_keys` runs **before** the sort, so an ambiguous order can
never be committed.

- **Same key, same `content_hash`** → the *same proposal*. Relative order is
  unobservable; `sorted` is stable and keeps them adjacent. The engine's existing
  dedupe behaviour applies. Not an error.
- **Same key, different content** → genuinely ambiguous. Raises
  `AmbiguousProposalOrderError` naming the key and the competing `proposal_id` /
  `proposal_family`. Deterministic identifiers only — no object reprs, and **no
  fallback to content-derived ordering**, which is the defect this prevents from
  returning silently.

`content_hash` is consulted only to answer *"is this the same proposal?"* — a
duplicate-content diagnostic. It never orders different proposals.

## `content_hash` is now identity and audit only

Retained unchanged for `proposal_id` (`prop-{time}-{hash[:12]}`), `event_id`
(`evt-{tick}-{order}-{hash[:8]}`), audit and integrity evidence. It still changes
whenever proposal content changes; it simply no longer decides behaviour.

## Migration consequence

Commit order changes at **tick 1**, so every scenario trajectory hash moves,
including the frozen `living_settlement` 320-tick hash
`9c1b9b8ba28a6fa830ff141d1eea7a8755d7c13a5a62dfc94ba93a15946e55d4` →
`5b4eff56da1d5ddd583c4ff2efeff5a5a377413cb8e71dc80f541439f9bb8373`
(`collective_groups` @320: `74f050fea2be79d0b609dc67ce3f32d5abd884f0b1f0921d49a80d2de64369b5`).

This is the correction landing, not a regression: the old trajectory was an
artefact of content-ordered commits. **Expected hashes are deliberately NOT
updated on this branch.**

## Acceptance evidence

Plain versus inactive-precondition arms, under the new ordering:

| scenario @320 | plain | + inactive precondition |
|---|---|---|
| `living_settlement` | `5b4eff56da1d5ddd…` | **identical** |
| `collective_groups` | `74f050fea2be79d0…` | **identical** |

Adding a precondition that cannot fire now changes nothing — not proposal order,
event order, trajectory, or final hash.
