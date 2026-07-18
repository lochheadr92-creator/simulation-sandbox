"""Capability Stage 8A emergent-norm focused + integrated tests."""
from __future__ import annotations

import copy

from core.commit_pipeline import run_commit_frame
from core.mutations import apply_mutation
from domains.base import DomainOutput
from domains.association_contracts import (
    ASSOCIATION_REGISTRY_ID,
    ASSOCIATION_REGISTRY_VERSION,
    GROUP_CANDIDATE_VERSION,
)
from domains.group_goal_contracts import (
    GROUP_GOAL_REGISTRY_ID,
    GROUP_GOAL_REGISTRY_VERSION,
    GROUP_GOAL_VERSION,
    GOAL_TYPE,
    group_goal_id,
)
from domains.group_norm_contracts import (
    GROUP_NORM_REGISTRY_ID,
    GROUP_NORM_REGISTRY_VERSION,
    GROUP_NORM_VERSION,
    NORM_TYPE,
    NORM_FORMATION_COUNT,
    NORM_DECAY_TICKS,
    NORM_WEAKENING_STRENGTH,
    PROPOSAL_TYPE,
    LIMITS,
    advance_group_norm_registry,
    build_group_norm_proposal,
    derive_group_norm_changes,
    empty_group_norm_registry,
    group_norm_id,
    norm_display_status,
    norm_strength,
    validate_group_norm_proposal,
)
from domains.living_settlement_domain import (
    NORM_REPAIR_INCREMENT,
    _apply_group_norm_influence,
)

LINEAGE = "stage8a-lineage"
RUN = "stage8a-run"
GID = "grp-1"
SHELTER = "shelter-1"


# --- fixtures -----------------------------------------------------------------

def _person(pid, *, alive=True, want=False):
    living = {"wants": {}}
    if want:
        living["wants"]["want-1"] = {"want_type": "improve_shelter", "status": "active"}
    return {
        "type": "person", "alive": alive, "living_agent": living,
        "position": {"x": 0, "y": 0}, "last_event_id": "evt-0-" + pid,
    }


def _shelter(condition=300):
    return {
        "type": "shelter", "access": "shared", "condition": int(condition),
        "position": {"x": 0, "y": 0}, "last_event_id": "evt-0-shelter",
    }


def _assoc(members=("p-a", "p-b"), *, group_id=GID, rev=1, recognised=True):
    cand = {
        "schema_version": GROUP_CANDIDATE_VERSION,
        "recognition_state": "recognised" if recognised else "dissolved",
        "ever_recognised": True,
        "member_ids": sorted(members), "group_type": "household",
        "recognised_tick": 1, "recognition_event_id": "evt-0-recog",
    }
    return {
        "schema_version": ASSOCIATION_REGISTRY_VERSION, "revision": rev,
        "last_event_id": "evt-0-assoc",
        "group_candidates": {group_id: cand},
    }


def _goal_registry(*, key="k1", target=SHELTER, group_id=GID, rev=1,
                   status="active", last_updated=1):
    goal_id = group_goal_id(group_id, GOAL_TYPE, target)
    return {
        "type": "group_goal_registry",
        "schema_version": GROUP_GOAL_REGISTRY_VERSION,
        "revision": rev, "last_event_id": "evt-0-goal",
        "goals": {goal_id: {
            "schema_version": GROUP_GOAL_VERSION, "goal_id": goal_id,
            "group_id": group_id, "goal_type": GOAL_TYPE, "target_id": target,
            "status": status, "adopted_via_key": key,
            "last_updated_tick": last_updated,
        }},
        "processed_goal_keys": [key],
    }


def _entities(*, members=("p-a", "p-b"), key="k1", target=SHELTER, recognised=True):
    ents = {m: _person(m) for m in members}
    ents[SHELTER] = _shelter()
    ents[ASSOCIATION_REGISTRY_ID] = _assoc(members, recognised=recognised)
    ents[GROUP_GOAL_REGISTRY_ID] = _goal_registry(key=key, target=target)
    return ents


def _step(ents, tick, key):
    """Simulate one tick: set the group's active goal key, derive + advance the
    norm registry, install it. Mirrors the domain's per-tick operation."""
    goal = list(ents[GROUP_GOAL_REGISTRY_ID]["goals"].values())[0]
    goal["adopted_via_key"] = key
    goal["last_updated_tick"] = tick
    changes = derive_group_norm_changes(ents, tick)
    existing = ents.get(GROUP_NORM_REGISTRY_ID)
    registry, _transitions = advance_group_norm_registry(existing, changes, tick)
    ents[GROUP_NORM_REGISTRY_ID] = registry
    return changes, registry


def _commit(entities, proposals, tick, order=0):
    return run_commit_frame(
        entities, [DomainOutput(proposals=list(proposals))],
        tick, LINEAGE, RUN, order, "frame-" + str(tick),
    )


def _norm_id():
    return group_norm_id(GID, NORM_TYPE)


def _form_norm(ents, start_tick=10, step=1):
    """Drive exactly NORM_FORMATION_COUNT distinct adoptions and return the tick
    the norm formed on (the final step). Constant-agnostic."""
    formed_tick = start_tick
    for i in range(NORM_FORMATION_COUNT):
        formed_tick = start_tick + i * step
        _step(ents, formed_tick, f"k{i + 1}")
    return formed_tick


# --- formation counting -------------------------------------------------------

def test_forms_norm_at_formation_count_not_before():
    ents = _entities()
    # Distinct adoption instances (unique keys), one per tick. No norm until the
    # count reaches NORM_FORMATION_COUNT.
    for i in range(NORM_FORMATION_COUNT - 1):
        _step(ents, 10 + i * 10, f"k{i + 1}")
        reg = ents[GROUP_NORM_REGISTRY_ID]
        assert reg["group_progress"][GID]["adoption_count"] == i + 1
        assert not reg["norms"]  # still below threshold
    formed_tick = 10 + (NORM_FORMATION_COUNT - 1) * 10
    _step(ents, formed_tick, f"k{NORM_FORMATION_COUNT}")
    reg = ents[GROUP_NORM_REGISTRY_ID]
    assert reg["group_progress"][GID]["adoption_count"] == NORM_FORMATION_COUNT
    norm = reg["norms"][_norm_id()]
    assert norm["status"] == "active"
    assert norm["norm_type"] == NORM_TYPE
    assert norm["target_id"] == SHELTER
    assert norm["formation_count"] == NORM_FORMATION_COUNT
    assert norm["decay_deadline_tick"] == formed_tick + NORM_DECAY_TICKS


def test_same_key_does_not_recount():
    ents = _entities()
    _step(ents, 10, "k1")
    _step(ents, 11, "k1")  # same key -> no new adoption
    _step(ents, 12, "k1")
    reg = ents[GROUP_NORM_REGISTRY_ID]
    assert reg["group_progress"][GID]["adoption_count"] == 1
    assert not reg["norms"]


def test_one_norm_per_group_refresh_not_reform():
    ents = _entities()
    for i, key in enumerate(["k1", "k2", "k3", "k4", "k5"]):
        _step(ents, 10 + i * 10, key)
    reg = ents[GROUP_NORM_REGISTRY_ID]
    norms_for_group = [n for n in reg["norms"].values() if n["group_id"] == GID]
    assert len(norms_for_group) == 1  # exactly one norm, refreshed by later adoptions
    norm = reg["norms"][_norm_id()]
    # The 5th adoption at tick 50 refreshed the deadline.
    assert norm["last_adoption_tick"] == 50
    assert norm["decay_deadline_tick"] == 50 + NORM_DECAY_TICKS


# --- decay / expiry -----------------------------------------------------------

def test_norm_weakens_then_expires_on_no_readoption():
    ents = _entities()
    formed_tick = _form_norm(ents, start_tick=10)
    norm = ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]
    assert norm_display_status(norm, formed_tick) == "active"
    # Half-way through decay -> weakening band.
    mid = formed_tick + NORM_DECAY_TICKS // 2 + 1
    assert norm_display_status(norm, mid) == "weakening"
    assert 0 < norm_strength(norm, mid) < NORM_WEAKENING_STRENGTH
    # Past the deadline with no re-adoption -> a derive proposes expiry.
    expire_tick = formed_tick + NORM_DECAY_TICKS
    # No active goal key change; make the goal expired so no new adoption counts.
    ents[GROUP_GOAL_REGISTRY_ID]["goals"][group_goal_id(GID, GOAL_TYPE, SHELTER)]["status"] = "expired"
    changes = derive_group_norm_changes(ents, expire_tick)
    assert _norm_id() in changes["expiries"]
    registry, _ = advance_group_norm_registry(ents[GROUP_NORM_REGISTRY_ID], changes, expire_tick)
    assert registry["norms"][_norm_id()]["status"] == "expired"


def test_norm_expires_on_group_dissolution():
    ents = _entities()
    _form_norm(ents, start_tick=10)
    assert ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]["status"] == "active"
    # Group dissolves (no longer recognised) -> immediate expiry even before decay.
    ents[ASSOCIATION_REGISTRY_ID] = _assoc(("p-a", "p-b"), recognised=False, rev=2)
    changes = derive_group_norm_changes(ents, 20)
    assert _norm_id() in changes["expiries"]
    registry, _ = advance_group_norm_registry(ents[GROUP_NORM_REGISTRY_ID], changes, 20)
    assert registry["norms"][_norm_id()]["status"] == "expired"


def test_readoption_refreshes_decay_deadline():
    ents = _entities()
    _form_norm(ents, start_tick=10)
    old_deadline = ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]["decay_deadline_tick"]
    # A later re-adoption well before the deadline refreshes it.
    _step(ents, 100, "k4")
    norm = ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]
    assert norm["status"] == "active"
    assert norm["decay_deadline_tick"] == 100 + NORM_DECAY_TICKS > old_deadline


def test_refresh_repoints_target_on_different_shelter():
    # Adversarial-review regression: a re-adoption targeting a DIFFERENT shared
    # shelter must re-point the norm, not leave the influence boosting the old one.
    ents = _entities()
    _form_norm(ents, start_tick=10)
    assert ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]["target_id"] == SHELTER
    ents[GROUP_GOAL_REGISTRY_ID] = _goal_registry(key="k-shelter2", target="shelter-2")
    changes = derive_group_norm_changes(ents, 100)
    assert any(r["group_id"] == GID and r["target_id"] == "shelter-2"
               for r in changes["refreshes"])
    reg, _ = advance_group_norm_registry(ents[GROUP_NORM_REGISTRY_ID], changes, 100)
    assert reg["norms"][_norm_id()]["status"] == "active"
    assert reg["norms"][_norm_id()]["target_id"] == "shelter-2"


def test_validate_rejects_forged_active_norm_count():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    proposal = build_group_norm_proposal(ents, 120)
    proposal["group_norm_update"]["active_norm_count"] = 999
    assert validate_group_norm_proposal(proposal, ents) is not None


def test_validate_rejects_type_variant_scalar_forgery():
    # Adversarial-review regression: True == 1 in Python but canonical JSON differs
    # ('true' vs '1'). Byte-exact validation must reject a bool-for-int forgery even
    # though int() coercion elsewhere would accept it.
    from core.hashing import canonical_json
    ents = _entities(key="k1")
    proposal = build_group_norm_proposal(ents, 10)
    reg = proposal["mutation"]["new_entities"][GROUP_NORM_REGISTRY_ID]
    reg["revision"] = True  # forged: was int 1
    proposal["group_norm_update"]["payload_bytes"] = len(canonical_json(reg).encode("utf-8"))
    assert validate_group_norm_proposal(proposal, ents) is not None


def test_validate_rejects_markerless_norm_registry_write():
    # Adversarial-review regression: a proposal writing the norm registry WITHOUT
    # the group_norm_update marker must not bypass validation.
    ents = _entities(key="k1")
    proposal = build_group_norm_proposal(ents, 10)
    del proposal["group_norm_update"]
    assert validate_group_norm_proposal(proposal, ents) is not None
    # A proposal that does not touch the norm registry still passes untouched.
    assert validate_group_norm_proposal(
        {"mutation": {"entity_updates": {"p-a": {}}}}, ents) is None


def test_exact_deadline_readoption_refreshes_not_clobbers():
    # Adversarial-review regression: at the EXACT decay deadline a re-adoption must
    # REFRESH the norm, never form-then-expire it (same norm_id) in one advance.
    ents = _entities()
    _form_norm(ents, start_tick=10)
    deadline = ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]["decay_deadline_tick"]
    _step(ents, deadline, "k-readopt")  # re-adopt exactly at the deadline
    norm = ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]
    assert norm["status"] == "active", "exact-deadline re-adoption clobbered to expired"
    assert norm["decay_deadline_tick"] == deadline + NORM_DECAY_TICKS


# --- influence hook (transmission-inclusive, member-grounded, survival-first) --

def _norm_registry(*, group_id=GID, target=SHELTER, tick=10, status="active",
                   deadline=None, rev=3):
    reg = empty_group_norm_registry(0)
    reg["revision"] = rev
    nid = group_norm_id(group_id, NORM_TYPE)
    reg["norms"][nid] = {
        "schema_version": GROUP_NORM_VERSION, "norm_id": nid,
        "group_id": group_id, "norm_type": NORM_TYPE, "target_id": target,
        "status": status, "formation_count": 3, "formed_tick": tick,
        "created_tick": tick, "last_updated_tick": tick, "last_adoption_tick": tick,
        "decay_deadline_tick": (tick + NORM_DECAY_TICKS) if deadline is None else deadline,
        "formed_via_key": "k3", "created_event_id": "evt", "last_event_id": "evt",
        "revision": 1,
    }
    return reg


def _influence_entities(*, members=("p-a", "p-b"), norm_status="active",
                        recognised=True, schema=GROUP_NORM_REGISTRY_VERSION,
                        deadline=None):
    ents = {m: _person(m, want=False) for m in members}  # NOTE: no improve_shelter want
    ents[ASSOCIATION_REGISTRY_ID] = _assoc(members, recognised=recognised)
    reg = _norm_registry(status=norm_status, deadline=deadline)
    reg["schema_version"] = schema
    ents[GROUP_NORM_REGISTRY_ID] = reg
    return ents


def _repair_cand(target=SHELTER, score=100):
    return {"goal": "REPAIR_SHELTER", "direct_action_type": "repair",
            "score": score, "target_entity_id": target}


def _survival_cand(goal="DRINK_WATER", score=100):
    return {"goal": goal, "direct_action_type": "drink", "score": score}


def test_influence_boosts_repair_for_current_member_without_want():
    # Transmission: a member holding NO improve_shelter want is still nudged.
    ents = _influence_entities()
    cands = [_repair_cand(score=100)]
    out = _apply_group_norm_influence(cands, "p-a", ents, 20)
    assert out[0]["score"] == 100 + NORM_REPAIR_INCREMENT


def test_influence_transmits_to_later_joiner():
    # p-c joins the group after the norm formed; it inherits the nudge.
    ents = _influence_entities(members=("p-a", "p-b"))
    ents["p-c"] = _person("p-c", want=False)
    ents[ASSOCIATION_REGISTRY_ID] = _assoc(("p-a", "p-b", "p-c"))
    cands = [_repair_cand(score=100)]
    out = _apply_group_norm_influence(cands, "p-c", ents, 20)
    assert out[0]["score"] == 100 + NORM_REPAIR_INCREMENT


def test_influence_skips_non_member():
    ents = _influence_entities()
    ents["p-z"] = _person("p-z", want=False)
    cands = [_repair_cand(score=100)]
    out = _apply_group_norm_influence(cands, "p-z", ents, 20)
    assert out[0]["score"] == 100  # unchanged


def test_influence_only_boosts_the_norm_shelter():
    ents = _influence_entities()
    cands = [_repair_cand(target="other-shelter", score=100)]
    out = _apply_group_norm_influence(cands, "p-a", ents, 20)
    assert out[0]["score"] == 100  # different target, no boost


def test_influence_never_overrides_urgent_survival():
    ents = _influence_entities()
    cands = [_repair_cand(score=100), _survival_cand(score=100)]  # survival >= base
    out = _apply_group_norm_influence(cands, "p-a", ents, 20)
    repair = next(c for c in out if c["goal"] == "REPAIR_SHELTER")
    assert repair["score"] == 100  # suppressed by urgent survival


def test_influence_inert_without_registry():
    ents = _influence_entities(schema="wrong-version")
    cands = [_repair_cand(score=100)]
    out = _apply_group_norm_influence(cands, "p-a", ents, 20)
    assert out[0]["score"] == 100


def test_influence_survival_guard_uses_final_score_total():
    # Adversarial-review regression: the hook runs AFTER scoring, so a survival
    # goal whose urgency lives in score_total (low raw score) must still suppress
    # the nudge. The OLD pre-scoring guard (comparing raw score) would wrongly boost.
    ents = _influence_entities()
    repair = {"goal": "REPAIR_SHELTER", "direct_action_type": "repair",
              "score": 100, "score_total": 100, "target_entity_id": SHELTER}
    urgent_food = {"goal": "DRINK_WATER", "direct_action_type": "drink",
                   "score": 10, "score_total": 200}  # urgency in score_total
    out = _apply_group_norm_influence([repair, urgent_food], "p-a", ents, 20)
    r = next(c for c in out if c["goal"] == "REPAIR_SHELTER")
    assert r["score_total"] == 100 and r["score"] == 100  # suppressed


def test_influence_boosts_score_total_when_survival_low():
    ents = _influence_entities()
    repair = {"goal": "REPAIR_SHELTER", "direct_action_type": "repair",
              "score": 100, "score_total": 100, "target_entity_id": SHELTER}
    weak_food = {"goal": "DRINK_WATER", "direct_action_type": "drink",
                 "score": 10, "score_total": 20}
    out = _apply_group_norm_influence([repair, weak_food], "p-a", ents, 20)
    r = next(c for c in out if c["goal"] == "REPAIR_SHELTER")
    assert r["score_total"] == 100 + NORM_REPAIR_INCREMENT  # ranking field boosted
    assert r["score"] == 100 + NORM_REPAIR_INCREMENT


def test_influence_skips_expired_or_past_deadline_norm():
    # committed-expired norm
    ents = _influence_entities(norm_status="expired")
    out = _apply_group_norm_influence([_repair_cand(score=100)], "p-a", ents, 20)
    assert out[0]["score"] == 100
    # active record but past its decay deadline (expiry not yet committed)
    ents2 = _influence_entities(deadline=15)
    out2 = _apply_group_norm_influence([_repair_cand(score=100)], "p-a", ents2, 50)
    assert out2[0]["score"] == 100


# --- build / validate / forged-field rejection --------------------------------

def _progress_registry(count=2, key="k2", tick=100):
    reg = empty_group_norm_registry(0)
    reg["revision"] = 4
    reg["group_progress"] = {GID: {
        "adoption_count": count, "last_counted_key": key, "last_adoption_tick": tick,
    }}
    return reg


def test_build_and_validate_ok():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()  # count 2 -> 3rd forms
    proposal = build_group_norm_proposal(ents, 120)
    assert proposal is not None
    assert proposal["proposal_type"] == PROPOSAL_TYPE
    assert proposal["engine_priority"] == 87
    assert validate_group_norm_proposal(proposal, ents) is None


def test_validate_rejects_forged_norm_id():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    proposal = build_group_norm_proposal(ents, 120)
    reg = proposal["mutation"]["entity_updates"][GROUP_NORM_REGISTRY_ID]
    # Forge a norm id in the resulting registry.
    (nid, norm), = reg["norms"].items()
    norm["norm_id"] = "group-norm-forged00000000000000"
    assert validate_group_norm_proposal(proposal, ents) is not None


def test_validate_rejects_forged_formation_count_in_metadata():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    proposal = build_group_norm_proposal(ents, 120)
    proposal["group_norm_update"]["changes"]["formations"][0]["formation_count"] = 99
    assert validate_group_norm_proposal(proposal, ents) is not None


def test_validate_rejects_forged_decay_deadline():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    proposal = build_group_norm_proposal(ents, 120)
    reg = proposal["mutation"]["entity_updates"][GROUP_NORM_REGISTRY_ID]
    (nid, norm), = reg["norms"].items()
    norm["decay_deadline_tick"] = 999999
    assert validate_group_norm_proposal(proposal, ents) is not None


def test_validate_rejects_out_of_scope_mutation():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    proposal = build_group_norm_proposal(ents, 120)
    proposal["mutation"]["entity_updates"]["p-a"] = {"alive": False}
    assert validate_group_norm_proposal(proposal, ents) is not None


def test_validate_rejects_registry_in_both_new_and_updates():
    # Adversarial-review regression: a forged entity_updates overlay must not ride
    # in behind a validated new_entities payload for the same registry. The first
    # progress update (no existing norm registry) uses the new_entities path.
    ents = _entities(key="k1")  # fresh: no existing norm registry
    proposal = build_group_norm_proposal(ents, 10)
    assert proposal is not None
    assert GROUP_NORM_REGISTRY_ID in proposal["mutation"]["new_entities"]
    forged = copy.deepcopy(proposal["mutation"]["new_entities"][GROUP_NORM_REGISTRY_ID])
    forged["norms"]["group-norm-forged00000000000000"] = {"schema_version": GROUP_NORM_VERSION}
    proposal["mutation"]["entity_updates"][GROUP_NORM_REGISTRY_ID] = forged
    assert validate_group_norm_proposal(proposal, ents) is not None


# --- commit / replay / idempotence / capacity ---------------------------------

def test_commit_creates_registry_and_touches_nothing_else():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    before_person = copy.deepcopy(ents["p-a"])
    before_shelter = copy.deepcopy(ents[SHELTER])
    proposal = build_group_norm_proposal(ents, 120)
    accepted, rejected, _ = _commit(ents, [proposal], 120)
    assert not rejected
    assert len(accepted) == 1
    assert ents["p-a"] == before_person
    assert ents[SHELTER] == before_shelter
    assert ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]["status"] == "active"


def test_replay_equivalence():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    # Formation is an incremental update over the prior registry; replay from that
    # prior state (as genesis replay would, event by event) must reconstruct it.
    prior = copy.deepcopy(ents[GROUP_NORM_REGISTRY_ID])
    proposal = build_group_norm_proposal(ents, 120)
    accepted, rejected, _ = _commit(ents, [proposal], 120)
    assert not rejected
    rebuilt = {GROUP_NORM_REGISTRY_ID: prior}
    for event in accepted:
        apply_mutation(rebuilt, copy.deepcopy(event["mutation"]))
    assert rebuilt[GROUP_NORM_REGISTRY_ID] == ents[GROUP_NORM_REGISTRY_ID]


def test_duplicate_formation_key_idempotent():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    changes = derive_group_norm_changes(ents, 120)
    reg1, _ = advance_group_norm_registry(ents[GROUP_NORM_REGISTRY_ID], changes, 120)
    # Re-applying the same formation (same key) must not create a second norm.
    reg2, _ = advance_group_norm_registry(reg1, changes, 121)
    assert len(reg2["norms"]) == 1


def test_capacity_bound_respected():
    reg = empty_group_norm_registry(0)
    changes = {"progress_updates": {}, "formations": [], "refreshes": [], "expiries": []}
    for i in range(LIMITS.norms + 5):
        gid = f"grp-{i:03d}"
        nid = group_norm_id(gid, NORM_TYPE)
        changes["formations"].append({
            "schema_version": GROUP_NORM_VERSION, "norm_id": nid, "group_id": gid,
            "group_type": "household", "norm_type": NORM_TYPE, "target_id": SHELTER,
            "formation_count": 3, "formed_via_key": f"key-{i}", "tick": 10,
            "decay_deadline_tick": 10 + NORM_DECAY_TICKS, "norm_key": f"nk-{i}",
        })
    reg, _ = advance_group_norm_registry(reg, changes, 10)
    assert len(reg["norms"]) <= LIMITS.norms


# --- integrated full-kernel (the gate 7D's focused tests missed) --------------

def _upstream_revision_bump(entities, registry_id, tick, priority):
    rev = int(entities[registry_id]["revision"])
    return {
        "proposal_family": "test_support",
        "proposal_type": "test_upstream_revision_bump",
        "proposer_engine_id": "test", "entity_id": registry_id,
        "causal_parent_event_ids": [], "is_exogenous": True,
        "requested_time": tick, "phase": "agent", "engine_priority": priority,
        "touched_scope": [registry_id],
        "preconditions": [{"entity_id": registry_id, "field": "revision", "op": "eq", "value": rev}],
        "mutation": {"entity_updates": {registry_id: {"revision": rev + 1}}, "new_entities": {}},
        "explanation": "test: upstream registry revision bump in same frame",
    }


def test_norm_formation_survives_same_frame_upstream_churn():
    """The gate the 7D focused tests missed: drive the norm proposal through the
    REAL commit pipeline while association (90) and group_goal (88) churn their
    revisions in the same frame. group_norm (87) commits first, so its pinned
    upstream revisions still match and the norm forms end-to-end."""
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()  # count 2 -> 3rd forms now
    norm_proposal = build_group_norm_proposal(ents, 120)
    assert norm_proposal is not None
    frame = [
        _upstream_revision_bump(ents, ASSOCIATION_REGISTRY_ID, 120, 90),
        _upstream_revision_bump(ents, GROUP_GOAL_REGISTRY_ID, 120, 88),
        norm_proposal,
    ]
    accepted, rejected, _ = _commit(ents, frame, 120)
    norm_rejections = [r for r in rejected if r["entity_id"] == GROUP_NORM_REGISTRY_ID]
    assert not norm_rejections, f"group_norm rejected under churn: {norm_rejections}"
    norm_events = [e for e in accepted if e["event_type"] == PROPOSAL_TYPE]
    assert len(norm_events) == 1
    assert ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]["status"] == "active"


def test_norm_expiry_survives_same_frame_upstream_churn():
    ents = _entities(key="k3")
    ents[GROUP_NORM_REGISTRY_ID] = _progress_registry()
    _commit(ents, [build_group_norm_proposal(ents, 120)], 120)
    assert ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]["status"] == "active"
    # Group dissolves; expiry must survive same-frame upstream churn too.
    ents[ASSOCIATION_REGISTRY_ID]["group_candidates"][GID]["recognition_state"] = "dissolved"
    ents[ASSOCIATION_REGISTRY_ID]["revision"] += 1
    expiry_proposal = build_group_norm_proposal(ents, 121)
    assert expiry_proposal is not None
    frame = [
        _upstream_revision_bump(ents, ASSOCIATION_REGISTRY_ID, 121, 90),
        _upstream_revision_bump(ents, GROUP_GOAL_REGISTRY_ID, 121, 88),
        expiry_proposal,
    ]
    accepted, rejected, _ = _commit(ents, frame, 121)
    norm_rejections = [r for r in rejected if r["entity_id"] == GROUP_NORM_REGISTRY_ID]
    assert not norm_rejections, f"group_norm expiry rejected under churn: {norm_rejections}"
    assert ents[GROUP_NORM_REGISTRY_ID]["norms"][_norm_id()]["status"] == "expired"
