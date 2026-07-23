# Stage 8B Leg 1 — bare claims for blind adversarial review

> **Historical blind-pass artifact.** Do not use for shipping wording.
> Authoritative close-out claims (post-review fixes applied 2026-07-24):
> `scratchpad/leg1_claims_closeout.md` and
> `memory/CAPABILITY-STAGE-8B-LEG1-NORM-TRANSMISSION.md`.
> Unqualified claim 9 and other wording traps below are intentional for the
> blind first pass; they are superseded by the close-out claims.

Scope: the Leg 1 change set (`leg1_change_set.diff` — everything from commit
`3506bd2b` to the branch tip, i.e. through Contract Amendment 2). Attempt to
REFUTE each claim against the diff and the code. No builder context beyond
this list is provided in the first pass, by design.

1. **Single mutation authority.** `group_carriage` is proposal-only. Only Core
   commits its proposals; accepted `group_carry_norm` events write only the
   `group-carriage-000` registry entity. No other entity is mutated by this
   domain's proposals, and rejected proposals mutate nothing.

2. **Registry schema.** The registry is `group-carriage-registry-v1`
   (`group-carriage-000`), created lazily on first formation:
   `revision`, `carriers` keyed `{norm_id}:{person_id}`,
   `processed_transmission_keys` (bounded), `created_tick`,
   `last_updated_tick`. One carrier record per (norm_id, person_id) pair.

3. **Formation backfill.** When a `group_form_norm` "formed" transition commits
   at tick T, the carriage domain (at T+1) writes one carrier record per
   supporter of the triggering goal (from the lagged `group-goal-000`
   `supporter_ids`), with `source = "formation_backfill"`,
   `learned_from = None`, `via_event_id` = the formation event's id,
   `learned_tick` = the formation tick. Supporters only — non-supporting
   members are excluded.

4. **Transmission trigger.** Exactly one transmission mechanism exists:
   imitation, non-carrier-initiated. The trigger is the first
   (`TRANSMISSION_COUNT = 1`) committed `social_request_help` action by a
   living non-carrier who is a current member of the norm's group, targeting a
   current carrier of that norm. Qualifying event types are a data constant
   (`TRANSMISSION_QUALIFYING_EVENT_TYPES = ("social_request_help",)`), not a
   structural assumption. No chance-to-learn exists anywhere.

5. **Visibility and lag.** Every domain, regardless of `engine_priority`,
   builds proposals from one frame frozen at end of tick T−1. `engine_priority`
   (86 for carriage, one below `group_norm` 87) affects only apply order within
   the commit pass. A qualifying action accepted at tick T produces the
   transmission carrier record at tick T+1, never same-tick, never backdated.

6. **Idempotence.** `processed_transmission_keys` prevents re-triggering on the
   same qualifying event. Replaying or resuming reconstructs identical registry
   state.

7. **Validation and forgery rejection.** Core's validator re-derives the full
   expected backfill + transmission set from committed state and requires exact
   canonical-byte equality. Forged `carrier_id`, `learned_from`,
   `via_event_id`, `learned_tick`, or `source` are rejected. The forbidden
   fields `{inventory, authority, obedience, orders, law, command, punishment}`
   never appear in carriage records.

8. **Write-once records (Amendment 2).** Committed carrier records are
   write-once and carry no post-commit staging residue: `pending_event_tick`
   and `pending_transition` are absent from every committed record, and the
   validator rejects a record carrying either key. No schema-version bump was
   needed (v1 finalized before first commit).

9. **Eligibility.** Eligibility for the norm-influence nudge is carriage-only:
   a person receives the nudge iff they hold a carrier record for that norm.
   Membership no longer grants eligibility. Carriage is the sole gate on this
   leg's influence and acquisition path.

10. **Influence guard unchanged.** The survival-dominance guard, read-only
    nudge, `NORM_REPAIR_INCREMENT` magnitude, and "never creates a candidate a
    member lacks" rule are byte-for-byte 8A behaviour. This leg changes who is
    eligible, never what the nudge does. The influence hook fired zero times in
    the standard 1,000-tick organic run.

11. **Determinism.** With `group_carriage` enabled: `collective_groups`
    1000×2 repeat matches and replay matches final entities. Keyed RNG only;
    no wall-clock; no iteration-order dependence.

12. **Frozen-hash safety.** `living_settlement` 320-tick
    `final_state_hash = 84d3ad52773d95877a2de3a178a205cf96f1637c76dcf561c702fa24788c32d2`,
    byte-identical to the recorded baseline — `group_carriage` is inert there.

13. **Bounded state.** `carriers` cap 128 (50 used); `processed_transmission_keys`
    cap 96 (1 used); registry serialized size 17,126 B against
    `payload_target_bytes` 24,576 B → 30.31% headroom (invariant-4 ≥20%
    satisfied post-Amendment-2); hard `proposal_bytes` cap 32,768 B respected.

14. **Organic integration.** The unseeded 1,000-tick `collective_groups` run
    reaches the machinery: 49 backfill records across all 7 formations
    (`person-004` excluded from all 7), plus exactly one transmission —
    `person-004` learns `shelter_upkeep_norm` from `person-000`
    (qualifying action accepted tick 698, carriage committed tick 699,
    `via_event_id` = `evt-698-13861-115d344e`). `accepted_by_type.group_carry_norm = 4`.
    Mechanism correctness is proven by the synthetic-fixture tests, not by this
    run; this run proves the real pipeline exercises the machinery.

15. **Coupling classification.** Enabling `group_carriage` shifts unrelated
    same-priority tie-breaks downstream (first divergence tick 698). The
    discriminating A/B/C probe verified this coupling is pre-existing and
    architecture-wide (8A alone exhibits it), not introduced by this leg. The
    contract's containment claim is state authority, not behavioural isolation.

16. **Core touch is wiring-only.** The only Core change
    (`core/commit_pipeline.py`, +13 lines) follows the established per-domain
    seam exactly: import, `validate_group_carriage_proposal` dispatch in
    initial validation, `stamp_group_carriage_provenance` in the stamp chain.
    The validator returns no error for non-carriage proposals. No ordering,
    hashing, CAS, or transaction logic is touched.

17. **Deferrals stand, thresholds unlowered.** Tier B items (influence
    verifiably felt by the new carrier — organically unreachable, disjoint
    windows; late-joiner-must-learn — no joins in horizon) remain Deferred
    with recorded evidence. `TRANSMISSION_COUNT = 1` is the measured floor,
    not a lowering to force a firing.
