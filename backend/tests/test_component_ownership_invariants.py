"""Component-ownership invariants -- closes registry finding F10.

`memory/REGISTRY-COMPONENT-OWNERSHIP.md` F10: "No ownership test exists,
anywhere. Nothing in `backend/tests/` asserts that a component has exactly one
writing module, or exercises a same-tick two-writer case. The three nearest
tests ... all prove the *rejection* path works **where a CAS already exists** --
which is precisely why the unguarded fields (F1, F2, F3) were never caught."

F1-F4 are deliberately NOT fixed here: they write person or storage entities and
fall under the CORE-INTEGRITY-001 interim containment discipline, so remediation
belongs to the core-integrity stage, not a feature leg. That constraint dictates
the design. These are **characterization tests**: they assert the unguarded set
is EXACTLY the set the registry records, so

  * a NEW unguarded multi-writer field fails (regression caught), and
  * silently CLOSING a known gap ALSO fails, forcing fix and registry to land
    together.

Tier A throughout -- real builders, real commit frames, no harness run, no
simulation behaviour changed. Hash-neutral by construction: tests only.

Every registry claim asserted here is re-derived from code at run time, never
transcribed as a literal expected value, except the registry tables themselves
(which are the thing under test).
"""
from __future__ import annotations

import copy

from core.commit_pipeline import run_commit_frame
from domains.association_contracts import (
    build_association_proposal,
    make_association_evidence,
)
from domains.base import DomainOutput
from domains.group_state_contracts import (
    GROUP_STATE_REGISTRY_ID,
    build_group_state_proposal,
)
from domains.group_collective_contracts import build_group_collective_proposals
from domains.living_agent_actions import build_physical_action_proposal
from domains.living_agent_social import build_social_action_proposal

LINEAGE = "ownership-invariant-lineage"
RUN = "ownership-invariant-run"


# --------------------------------------------------------------------------
# Registry transcription -- the thing under test.
# Keep in lockstep with memory/REGISTRY-COMPONENT-OWNERSHIP.md Table 1.
# --------------------------------------------------------------------------

# Ownership is per DOMAIN, not per proposal builder: Table 1 names
# `living_settlement_domain` as the owner, and both living_agent_actions and
# living_agent_social are that domain's builders. Collapsing them here is what
# makes "exactly one writing module" a meaningful assertion.
ENGINE_FAMILY = {
    "living_actions": "living_settlement",
    "living_social": "living_settlement",
    "group_collective": "group_collective",
}

# Canonical component -> domain families the registry records as writing it. A
# family observed writing a field not listed here is an unregistered writer:
# either a real ownership violation or a stale registry.
REGISTERED_WRITERS: dict[str, set[str]] = {
    "action": {"living_settlement", "group_collective"},
    "living_agent": {"living_settlement"},
    "carried_resources": {"living_settlement", "group_collective"},
    "inventory": {"living_settlement", "group_collective"},
    "food_inventory": {"living_settlement", "group_collective"},
    "contents": {"living_settlement", "group_collective"},
    "condition": {"living_settlement"},
    "plan": {"living_settlement"},
    "current_goal": {"living_settlement"},
    "hunger": {"living_settlement"},
    "thirst": {"living_settlement"},
    "energy": {"living_settlement"},
    "health": {"living_settlement"},
    "position": {"living_settlement"},
    "durability": {"living_settlement"},
    "open": {"living_settlement"},
    "last_collective_action_key": {"group_collective"},
    "last_collective_action_tick": {"group_collective"},
    "collective_processed_keys": {"group_collective"},
}

# The gaps the registry records as OPEN, keyed (family, field). Deferred to the
# core-integrity stage; see the module docstring. When one is fixed, delete its
# entry here in the SAME commit -- the test fails until you do.
KNOWN_UNGUARDED: set[tuple[str, str]] = {
    # F2 -- gap is real at the precondition layer, but NOT exploitable: the
    # domain validator re-derives expected contents from live state and
    # rejects on mismatch (group_collective_contracts.py:515-521). Refuted as
    # a lost update; pinned as a precondition gap. See the dedicated test.
    ("group_collective", "contents"),
    # F3 -- gap is real AND exploitable. Nothing re-derives or guards `action`,
    # so a resource-free action (rest) is silently overwritten. CONFIRMED.
    ("group_collective", "action"),
    # Legacy scalar mirrors of carried_resources. Unguarded in their own right,
    # but the collective CASes `carried_resources` itself, and the validator
    # re-derives both mirrors (group_collective_contracts.py:505-508), so a
    # divergent write cannot commit. Compensated, not exploitable.
    ("group_collective", "inventory"),
    ("group_collective", "food_inventory"),
}

# Guards that DO exist and must not silently disappear (regression lock),
# keyed (proposer_engine_id, field) -- builder-level, since that is where a
# precondition is actually emitted.
REQUIRED_GUARDS: set[tuple[str, str]] = {
    ("living_actions", "contents"),            # store/retrieve CAS the storage
    ("living_actions", "carried_resources"),   # every resource producer CASes
    ("living_actions", "condition"),           # repair/tend strict equality CAS
    ("living_social", "living_agent"),         # actor AND target CAS'd
    ("group_collective", "carried_resources"),
}


# --------------------------------------------------------------------------
# Fixtures -- minimal, self-contained. Mirrors the 7C bootstrap shape.
# --------------------------------------------------------------------------


def _person(entity_id: str, x: int, y: int, *, food: int = 0, wood: int = 0) -> dict:
    return {
        "type": "person",
        "alive": True,
        "position": {"x": x, "y": y},
        "health": 900,
        "energy": 800,
        "hunger": 500,
        "thirst": 400,
        "food_inventory": food,
        "inventory": wood,
        "carried_resources": {"wood": wood, "food": food},
        "inventory_capacity": 30,
        "carried_item_ids": [],
        "last_event_id": f"evt-genesis-{entity_id}",
        "action": {"type": "idle", "status": "completed", "started_tick": 0},
    }


def _base_entities() -> dict:
    """Both members within manhattan range 1 of the shared storage (7C rule)."""
    return {
        "person-a": _person("person-a", 1, 0, food=2, wood=1),
        "person-b": _person("person-b", 0, 1, food=1, wood=2),
        # Storage-adjacent but NOT a group member: lets a store collide with a
        # collective deposit on the same storage without disturbing the
        # collective's participant eligibility.
        "person-c": _person("person-c", 0, 0, food=3, wood=0),
        "shelter-camp": {
            "type": "shelter", "position": {"x": 0, "y": 0}, "access": "shared",
            "condition": 900, "max_condition": 1000, "last_event_id": "evt-0-shelter",
        },
        "storage-camp": {
            "type": "storage", "position": {"x": 0, "y": 0}, "access": "shared",
            "contents": {"food": 1, "wood": 0}, "capacity": 40, "open": True,
            "last_event_id": "evt-0-storage",
        },
    }


def _commit(entities, proposals, tick, order=0):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))], tick, LINEAGE, RUN,
        order, f"frame-{tick}",
    )


def _evidence(tick: int, category: str, target_id: str) -> dict:
    pair = ("person-a", "person-b")
    return make_association_evidence(
        list(pair), category, tick,
        [f"evt-{pair[0]}-{tick}", f"evt-{pair[1]}-{tick}", f"evt-0-{target_id}"],
        condition_ids=[target_id],
    )


def _recognised_with_shared_storage():
    """Recognise a group via shared_shelter, then land a shared_storage fact."""
    entities = _base_entities()
    order = 0
    for tick in range(1, 4):
        proposal = build_association_proposal(
            entities, tick, observations=[_evidence(tick, "shared_shelter", "shelter-camp")],
        )
        assert proposal is not None
        _accepted, rejected, order = _commit(entities, [proposal], tick, order)
        assert not rejected
    proposal = build_association_proposal(
        entities, 4, observations=[_evidence(4, "shared_storage", "storage-camp")],
    )
    assert proposal is not None
    _accepted, rejected, order = _commit(entities, [proposal], 4, order)
    assert not rejected

    gs = build_group_state_proposal(entities, 4)
    assert gs is not None
    _accepted, rejected, order = _commit(entities, [gs], 4, order)
    assert not rejected
    assert GROUP_STATE_REGISTRY_ID in entities
    return entities, order


def _collective_proposal(entities, tick):
    proposals = build_group_collective_proposals(entities, tick)
    assert proposals, "fixture failed to produce a collective deposit proposal"
    return proposals[0]


def _proposal_corpus():
    """Real proposals from real builders. (label, proposal) pairs."""
    corpus = []

    entities = _base_entities()
    corpus.append(("store", build_physical_action_proposal(
        entities, actor_id="person-a", action_type="store", tick=1,
        target_id="storage-camp", resource_kind="food", quantity=1,
    )))
    corpus.append(("rest", build_physical_action_proposal(
        entities, actor_id="person-a", action_type="rest", tick=1,
    )))
    corpus.append(("tend", build_physical_action_proposal(
        entities, actor_id="person-a", action_type="tend", tick=1,
        target_id="shelter-camp",
    )))
    # person-a (1,0) and person-c (0,0) are adjacent; person-b (0,1) is not.
    corpus.append(("cooperate", build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-c",
    )))

    collective_entities, _order = _recognised_with_shared_storage()
    corpus.append(("collective_deposit", _collective_proposal(collective_entities, 5)))
    return corpus


def _written_fields(proposal) -> set[str]:
    fields = set()
    updates = (proposal.get("mutation") or {}).get("entity_updates") or {}
    for update in updates.values():
        if isinstance(update, dict):
            fields.update(update)
    return fields


def _guarded_fields(proposal) -> set[str]:
    return {p["field"] for p in proposal.get("preconditions") or []}


# --------------------------------------------------------------------------
# 1. Ownership: no unregistered writer of a canonical component.
# --------------------------------------------------------------------------


def test_no_unregistered_writer_of_a_canonical_component():
    """A new engine writing a registered component fails until the registry
    records it. This is the 'exactly one writing module' invariant, stated
    honestly: single-owner fields have one entry, legitimately shared ones
    list every owner explicitly."""
    unregistered = set()
    for _label, proposal in _proposal_corpus():
        family = ENGINE_FAMILY[proposal["proposer_engine_id"]]
        for field in _written_fields(proposal):
            if field in REGISTERED_WRITERS and family not in REGISTERED_WRITERS[field]:
                unregistered.add((family, field))

    assert not unregistered, (
        "unregistered writer(s) of a canonical component: "
        f"{sorted(unregistered)}. Either an ownership violation, or "
        "memory/REGISTRY-COMPONENT-OWNERSHIP.md Table 1 is stale."
    )


def test_single_owner_fields_have_exactly_one_writing_domain():
    """Fields the registry marks single-owner must not gain a second domain."""
    observed: dict[str, set[str]] = {}
    for _label, proposal in _proposal_corpus():
        family = ENGINE_FAMILY[proposal["proposer_engine_id"]]
        for field in _written_fields(proposal):
            observed.setdefault(field, set()).add(family)

    violations = {
        field: sorted(families)
        for field, families in observed.items()
        if field in REGISTERED_WRITERS
        and len(REGISTERED_WRITERS[field]) == 1
        and len(families) > 1
    }
    assert not violations, f"single-owner field(s) gained a second domain: {violations}"


# --------------------------------------------------------------------------
# 2. Guards: every multi-writer field needs a CAS. The known gaps are pinned.
# --------------------------------------------------------------------------


def test_multi_writer_field_precondition_gaps_match_the_registry():
    """THE F10 TEST. Every multi-writer field a proposal writes should carry a
    precondition on that same field; without one, core/mutations.py:24 lets a
    later same-tick writer silently revert it.

    The rule is directional, because a lost update is: only a writer that can
    commit AFTER another writer of the same field needs the CAS. Guarding the
    earlier writer protects nothing. "After" is `engine_priority` -- lower
    commits first (commit_pipeline.py:108).

    The currently-open gaps are pinned in KNOWN_UNGUARDED. A new gap fails
    here; so does closing a known gap without deleting its entry."""
    # field -> [(priority, family, guards_this_field)]
    per_field: dict[str, list[tuple[int, str, bool]]] = {}
    for _label, proposal in _proposal_corpus():
        family = ENGINE_FAMILY[proposal["proposer_engine_id"]]
        priority = int(proposal["engine_priority"])
        guarded = _guarded_fields(proposal)
        for field in _written_fields(proposal):
            per_field.setdefault(field, []).append(
                (priority, family, field in guarded)
            )

    gaps = set()
    for field, rows in per_field.items():
        if len({family for _p, family, _g in rows}) < 2:
            continue  # single-domain field: no cross-owner lost update possible
        earliest = min(priority for priority, _f, _g in rows)
        for priority, family, guarded in rows:
            if priority > earliest and not guarded:
                gaps.add((family, field))

    new_gaps = gaps - KNOWN_UNGUARDED
    closed_gaps = KNOWN_UNGUARDED - gaps

    assert not new_gaps, (
        f"NEW unguarded multi-writer field(s): {sorted(new_gaps)}. A same-tick "
        "second writer will silently revert these. Add the CAS, or register "
        "the gap deliberately."
    )
    assert not closed_gaps, (
        f"known gap(s) now guarded: {sorted(closed_gaps)}. Good -- delete them "
        "from KNOWN_UNGUARDED and update memory/REGISTRY-COMPONENT-OWNERSHIP.md "
        "in this same commit."
    )


def test_existing_cas_guards_are_not_silently_removed():
    """Regression lock: the guards that DO exist keep existing."""
    present = set()
    for _label, proposal in _proposal_corpus():
        engine = proposal["proposer_engine_id"]
        for field in _written_fields(proposal) & _guarded_fields(proposal):
            present.add((engine, field))

    missing = REQUIRED_GUARDS - present
    assert not missing, f"CAS guard(s) disappeared: {sorted(missing)}"


def test_physical_action_lacks_the_living_agent_cas_that_social_carries():
    """F4, pinned. build_social_action_proposal CASes living_agent on actor and
    target; build_physical_action_proposal CASes neither, while the settlement
    domain attaches living_agent to every proposal including physical ones. The
    guard is therefore one-directional. Deferred with F1-F3; pinned so the
    asymmetry cannot widen or vanish unnoticed."""
    entities = _base_entities()
    physical = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="rest", tick=1,
    )
    social = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-c",
    )
    assert "living_agent" not in _guarded_fields(physical), (
        "physical actions now CAS living_agent -- F4 is fixed; update the "
        "registry and delete this test."
    )
    social_guarded = [
        p for p in social["preconditions"] if p["field"] == "living_agent"
    ]
    assert {p["entity_id"] for p in social_guarded} == {"person-a", "person-c"}


def test_social_actions_write_energy_cross_entity():
    """Registry omission found by this file, not by the inventory pass.

    `living_agent_social.py:436-437` writes `energy` on BOTH the actor and the
    TARGET. Table 1's `energy` row lists people_domain.py:375,
    living_settlement_domain.py:712,715, living_agent_actions.py:435,503,505
    and interventions.py:25 -- it does not list living_agent_social at all, and
    does not record that this writer is cross-entity.

    Same domain family as the other living-agent writers, so it is not an
    ownership violation; it is an incomplete registry row. `energy` is rated
    LOW there partly on the assumption that its writers are one-per-scenario
    self-writes. A cross-entity write is a different shape and should be
    re-rated deliberately rather than by omission. Pinned so the row gets
    corrected."""
    entities = _base_entities()
    social = build_social_action_proposal(
        entities, actor_id="person-a", action_type="cooperate", tick=1,
        target_id="person-c",
    )
    updates = social["mutation"]["entity_updates"]
    assert "energy" in updates["person-a"]
    assert "energy" in updates["person-c"], (
        "cooperate no longer writes the target's energy -- re-check Table 1's "
        "`energy` row before deleting this test"
    )


# --------------------------------------------------------------------------
# 3. The same-tick two-writer cases the registry says do not exist.
# --------------------------------------------------------------------------


def test_same_tick_storage_contents_collision_rejects_the_collective_deposit():
    """F2 REFUTED. This is the case the registry records as untested ("no test
    mixes a living `store` with a collective deposit in one tick"), and running
    it overturns the finding.

    The registry predicted a silent lost update: group_collective carries no
    `contents` precondition, so its whole-dict write (built from the pinned
    pre-tick frame) should revert the agent's prio-10 deposit. It does not.
    `validate_group_collective_proposal` re-derives the expected contents from
    LIVE storage state at commit revalidation
    (group_collective_contracts.py:515-521) and rejects on any mismatch. The
    agent's deposit survives; the collective proposal is rejected and retries.

    That defence is functionally a CAS on `contents`, just implemented as a
    domain re-derivation rather than a precondition -- which is exactly why a
    preconditions-only code read missed it. The precondition gap is real; the
    lost update is not.

    Pinned so the compensating defence cannot be removed unnoticed."""
    entities, order = _recognised_with_shared_storage()
    pre_tick = copy.deepcopy(entities["storage-camp"]["contents"])

    # person-c is storage-adjacent but NOT a group member, so their deposit
    # cannot disturb the collective's participant eligibility. That isolates
    # the raw `contents` collision from the eligibility re-derivation which
    # independently defends the same-person case (pinned in the test below).
    store = build_physical_action_proposal(
        entities, actor_id="person-c", action_type="store", tick=5,
        target_id="storage-camp", resource_kind="food", quantity=1,
    )
    collective = _collective_proposal(entities, 5)
    assert "person-c" not in collective["mutation"]["entity_updates"], (
        "fixture assumes person-c is not a collective participant"
    )
    assert store["engine_priority"] < collective["engine_priority"], (
        "fixture assumes the agent store commits before the collective deposit"
    )
    assert "contents" not in {
        p["field"] for p in collective["preconditions"]
        if p["entity_id"] == "storage-camp"
    }, "collective deposit now CASes storage contents -- F2 is fixed; invert this test"

    accepted, rejected, _order = _commit(entities, [store, collective], 5, order)

    # The agent's store commits; the collective deposit is rejected, not lost.
    assert len(accepted) == 1
    assert [(r["entity_id"], r["reason_code"]) for r in rejected] == [
        ("person-a", "group_collective.invalid_mutation")
    ], (
        "the contents re-derivation defence "
        "(group_collective_contracts.py:515-521) no longer rejects a "
        "concurrent storage write -- F2's lost update may now be reachable"
    )

    # The agent's deposit survives intact: pre-tick + 1, nothing reverted.
    final = entities["storage-camp"]["contents"]
    assert final["food"] == pre_tick["food"] + 1, (
        f"agent deposit did not survive: pre={pre_tick['food']}, "
        f"final={final['food']}"
    )


def test_same_person_store_is_defended_by_eligibility_rederivation():
    """Discovered while building the F2 test, and NOT recorded in the registry:
    when the storing agent is itself a collective participant, the store moves
    that participant's carried resources, Core's commit-time revalidation
    re-derives eligibility against the mutated state, the stale `before_value`
    no longer matches, and the whole collective proposal is REJECTED.

    So F2's lost update needs a storer who is *not* a participant. The
    same-person case is defended -- by the validator, not by a CAS. Pinned here
    because that defence is incidental: it rests on the deposit's before_value
    equality, not on any guard over `contents`."""
    entities, order = _recognised_with_shared_storage()
    collective = _collective_proposal(entities, 5)
    participants = [
        eid for eid in collective["mutation"]["entity_updates"]
        if (entities.get(eid) or {}).get("type") == "person"
    ]
    assert participants, "fixture produced no participants"
    storer = sorted(participants)[0]

    store = build_physical_action_proposal(
        entities, actor_id=storer, action_type="store", tick=5,
        target_id="storage-camp", resource_kind="food", quantity=1,
    )
    accepted, rejected, _order = _commit(entities, [store, collective], 5, order)

    assert len(accepted) == 1
    assert [(r["entity_id"], r["reason_code"]) for r in rejected] == [
        (storer, "group_collective.participant_ineligible")
    ], "the eligibility re-derivation no longer defends the same-person case"


def test_same_tick_person_action_collision_overwrites_the_committed_action():
    """F3, exercised end-to-end -- the "discriminating test" the registry names
    as "Not written": a deposit-eligible member whose selected action that tick
    is resource-free (`rest`), so group_collective's carried_resources CAS
    still passes and the freshly-committed action is overwritten anyway.

    CHARACTERIZATION, same contract as the F2 test above."""
    entities, order = _recognised_with_shared_storage()

    rest = build_physical_action_proposal(
        entities, actor_id="person-a", action_type="rest", tick=5,
    )
    collective = _collective_proposal(entities, 5)
    assert "person-a" in collective["mutation"]["entity_updates"], (
        "fixture assumes person-a participates in the deposit"
    )
    assert rest["engine_priority"] < collective["engine_priority"]

    rest_action_type = rest["mutation"]["entity_updates"]["person-a"]["action"]["type"]
    assert rest_action_type == "rest"
    # Resource-free by construction: rest touches no carried resource, so the
    # collective's carried_resources CAS on person-a is unaffected by it.
    assert "carried_resources" not in rest["mutation"]["entity_updates"]["person-a"]

    accepted, rejected, _order = _commit(entities, [rest, collective], 5, order)

    assert len(accepted) == 2 and not rejected, (
        f"both writes must be accepted for the clobber to occur; "
        f"rejected={[(r['entity_id'], r['reason_code']) for r in rejected]}"
    )
    assert "action" not in {
        p["field"] for p in collective["preconditions"] if p["entity_id"] == "person-a"
    }, "collective deposit now CASes person action -- F3 is fixed; invert this test"

    assert entities["person-a"]["action"]["type"] == "group_collective_deposit", (
        "F3 no longer overwrites the committed action -- fixed; invert this test"
    )
