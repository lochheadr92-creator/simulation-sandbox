# Stage 8B Leg 1 — close-out claims (post-review, corrected)

Authority for shipping wording. Supersedes unqualified phrasing in
`leg1_claims_bare.md` for close-out and the capability contract.
Bare claims remain the historical blind-pass artifact (including the F1 wording trap).

Scope: Leg 1 change set through Contract Amendment 2, after adversarial review
2026-07-24 (findings F1–F3, P1-01…P1-08).

1. **Single mutation authority.** `group_carriage` is proposal-only. Only Core
   commits its proposals; accepted `group_carry_norm` events write only the
   `group-carriage-000` registry entity. No other entity is mutated by this
   domain's proposals, and rejected proposals mutate nothing.

2. **Registry schema.** The registry is `group-carriage-registry-v1`
   (`group-carriage-000`), created lazily on first formation:
   `revision`, `carriers` keyed `{norm_id}:{person_id}`,
   **`backfilled_norm_ids` (bounded; one-time backfill tracking)**,
   `processed_transmission_keys` (bounded), `created_tick`,
   `last_updated_tick`. One carrier record per (norm_id, person_id) pair.
   After Amendment 1 (F2c), carrier record bodies do **not** restate
   `carrier_id` / `norm_id` / `person_id` (recoverable from the key).

3. **Formation backfill.** When a `group_form_norm` "formed" transition commits
   at tick T, the carriage domain (at T+1, or the first later tick an active
   goal is visible) writes one carrier record per supporter of the **active
   maintain_shared_shelter goal visible in the lagged frame**
   (`group-goal-000` `supporter_ids` for that group), with
   `source = "formation_backfill"`, `learned_from = None`,
   `via_event_id` = the formation event's id,
   **`learned_tick` = the carriage advance/commit tick** (not the formation
   tick). Supporters only — non-supporting members are excluded.
   **Lag assumption (P1-03 ACCEPT):** backfill is not a formation-time
   snapshot; it trusts that adoption cadence ≫ one-tick lag so the visible
   active goal still matches the formation-triggering supporter set. Once
   written, `backfilled_norm_ids` seals the set (no re-sync on later re-adoption).

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
   canonical-byte equality. Forged `learned_from`, `via_event_id`, `source`,
   restated key ids (`carrier_id`/`norm_id`/`person_id` in the record body),
   or pending staging keys are rejected. The forbidden fields
   `{inventory, authority, obedience, orders, law, command, punishment}`
   never appear in carriage records.

8. **Write-once records (Amendment 2).** Committed carrier records are
   write-once and carry no post-commit staging residue: `pending_event_tick`
   and `pending_transition` are absent from every committed record, and the
   validator rejects a record carrying either key. No schema-version bump was
   needed (v1 finalized before first commit).

9. **Eligibility vs acquisition (F1).**
   - **Eligibility** (the read-only nudge) is carriage-only and fully
     membership-independent: `_apply_group_norm_influence` consults the
     carriage registry and nothing else, so a carrier who has left the group
     is still nudged and a current member who never earned carriage is not.
   - **Acquisition** by transmission additionally requires co-membership:
     `derive_group_carriage_changes` selects learners from
     `member_ids - carriers`. A non-member cannot learn.
   Cross-group transmission is an 8D non-goal on this leg.

10. **Influence guard unchanged.** The survival-dominance guard, read-only
    nudge, `NORM_REPAIR_INCREMENT` magnitude, and "never creates a candidate a
    member lacks" rule are byte-for-byte 8A behaviour. This leg changes who is
    eligible, never what the nudge does.
    **Organic influence firings are not measured in the v3 evidence packet**
    (P1-05); harness JSON has no influence counter. Prior Stage 8A work
    recorded disjoint repair/norm windows as the organic-firing blocker;
    that scenario dynamics limit is unchanged by Leg 1 and remains Tier B
    Deferred where stated.

11. **Determinism.** With `group_carriage` enabled: `collective_groups`
    1000×2 repeat matches and replay matches final entities. Keyed RNG only;
    no wall-clock; no iteration-order dependence.
    Evidence: `harness_collective_groups_1000_v3.json`
    (`final_state_hash = b5abbfffa9e0b5b5b52da912c757b75231afb8b752658a1a76e9d91d7472368c`).

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
    `person-004` learns the live `shelter_upkeep_norm` (id
    `group-norm-5ae28cfdb0f88c3addd5`) from `person-000`
    (qualifying action accepted tick 698, carriage committed tick 699,
    `via_event_id` = `evt-698-13861-115d344e`). `accepted_by_type.group_carry_norm = 4`.
    Mechanism correctness is proven by the synthetic-fixture tests, not by this
    run; this run proves the real pipeline exercises the machinery.

15. **Coupling classification (state authority, not behavioural isolation).**
    Enabling `group_carriage` can shift unrelated same-priority tie-breaks
    downstream (architecture-wide same-priority commit coupling, also exhibited
    under 8A alone). The contract's containment claim is **state authority**
    (carriage writes only `group-carriage-000`), not behavioural isolation of
    unrelated domains.
    **P1-06:** the discriminating A/B/C probe is **not re-proven by a persisted
    artifact in `memory/evidence/stage-8b-leg1/`**; treat the architecture-wide
    classification as a design statement, not as packet-verified measurement.

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
