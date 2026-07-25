"""CORE-PERF-01 Slice A -- fallback-rest path fixture (Ryan's close-out ruling).

memory/CORE-PERF-01-TICK-VALIDATION-COST.md: Slice A's copy-ownership
refactor touches LivingSettlementDomain.activate()'s exception-handler
fallback path (build_physical_action_proposal raises ValueError -> a second,
"rest" attempt is built reusing the same working_entities/working_actor).
That path has zero organic occurrence across every gate run in this leg's
evidence (both scenarios, every tested horizon, the standard seed) -- forced
deterministically here instead of relying on an organic occurrence, per
Ryan's ruling: "That path is Slice-A-touched code with zero organic
coverage; the fixture closes it permanently."
"""
import copy

from core.commit_pipeline import run_commit_frame
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.kernel import build_genesis
from core.rng import DeterministicRNG
from domains import living_settlement_domain
from domains.base import ActivationFrame, DomainOutput
from domains.living_settlement_domain import LivingSettlementDomain
from scenarios import get_scenario


FORCED_FAILURE_MESSAGE = "forced failure for CORE-PERF-01 fixture test"

# Captured once, at import time, before any test can monkeypatch the module
# attribute -- a test that calls _activate_with_forced_first_failure more
# than once must not re-read living_settlement_domain.build_physical_action_
# proposal as "the real builder" the second time, since by then it is
# already patched from the first call and the two closures would chain into
# each other instead of behaving as two independent interceptions.
_REAL_BUILD_PHYSICAL_ACTION_PROPOSAL = living_settlement_domain.build_physical_action_proposal


def _genesis_frame(seed="living-agents-stage6", scenario_id="living_settlement", tick=1):
    scenario = get_scenario(scenario_id)
    lineage = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rejected, _order = build_genesis(seed, scenario, lineage)
    domain = LivingSettlementDomain()
    due = domain.select_due_ids(entities, tick)
    frame = ActivationFrame(
        "fallback-fixture", tick, ENGINE_VERSION, "agent", entities,
        world["terrain"], due, DeterministicRNG(seed),
    )
    return domain, frame, entities


def _activate_with_forced_first_failure(domain, frame, monkeypatch):
    """Monkeypatches build_physical_action_proposal so the first call raises
    ValueError (forcing the except-handler fallback path) and every
    subsequent call behaves normally. Returns (output, calls), where `calls`
    records the exact `plan` object passed to each call in order.
    """
    calls = []

    def intercepted(*args, **kwargs):
        calls.append(kwargs.get("plan"))
        if len(calls) == 1:
            raise ValueError(FORCED_FAILURE_MESSAGE)
        return _REAL_BUILD_PHYSICAL_ACTION_PROPOSAL(*args, **kwargs)

    monkeypatch.setattr(living_settlement_domain, "build_physical_action_proposal", intercepted)
    output = domain.activate(frame)
    return output, calls


def _fallback_proposal(output):
    # Not matched on `proposal["explanation"]`: that field gets unconditionally
    # overwritten later in activate() (the post-try/except "decision_kind:
    # selected X -> Y" line) regardless of which branch built the proposal, so
    # the except-handler's "deterministic fallback rest" string never survives
    # to the returned proposal -- pre-existing behaviour, not a Slice A change.
    # `plan["failure_reason"]` is set ONLY by the except handler (the sibling
    # "no route found" fallback also lands on decision_kind=="failed_plan_
    # replan" but never sets failure_reason), so it's the unambiguous signal.
    matches = [
        proposal for proposal in output.proposals
        for update in proposal["mutation"]["entity_updates"].values()
        if (update.get("plan") or {}).get("failure_reason") == FORCED_FAILURE_MESSAGE
    ]
    assert len(matches) == 1, "expected exactly one forced fallback-rest proposal"
    return matches[0]


def test_forced_build_failure_produces_a_well_formed_fallback_rest_proposal(monkeypatch):
    domain, frame, entities = _genesis_frame()
    output, calls = _activate_with_forced_first_failure(domain, frame, monkeypatch)

    assert len(calls) >= 2, "expected the failed attempt and the fallback attempt"
    proposal = _fallback_proposal(output)

    assert proposal["living_action"]["action_type"] == "rest"
    actor_id = proposal["mutation"]["entity_updates"]
    (actor_id,) = actor_id.keys()
    actor_update = proposal["mutation"]["entity_updates"][actor_id]
    assert actor_update["plan"]["status"] == "abandoned"
    assert actor_update["plan"]["failure_reason"] == FORCED_FAILURE_MESSAGE

    # Well-formed per the real acceptance path, not just by inspection: the
    # commit pipeline must accept it like any other proposal.
    accepted, rejected, _order = run_commit_frame(
        entities, [DomainOutput(proposals=[proposal])], 1, "lineage", "run", 0, "frame-1",
    )
    assert accepted and not rejected


def test_forced_build_failure_fallback_plan_is_not_aliased_to_the_failed_plan(monkeypatch):
    """The exception handler does `fallback_plan = copy.deepcopy(plan)` before
    mutating it -- verify directly that the plan object used to build the
    failed (first) attempt and the plan object used to build the succeeding
    fallback (second) attempt are independent objects, and that mutating one
    after the fact never affects the other. This is exactly the class of bug
    Slice A's copy-ownership refactor risks (memory/CORE-PERF-01-TICK-
    VALIDATION-COST.md, "the living_settlement_domain.py:736 alias class")."""
    domain, frame, entities = _genesis_frame()
    _output, calls = _activate_with_forced_first_failure(domain, frame, monkeypatch)

    failed_attempt_plan, fallback_attempt_plan = calls[0], calls[1]
    assert failed_attempt_plan is not fallback_attempt_plan

    before_failed = copy.deepcopy(failed_attempt_plan)
    before_fallback = copy.deepcopy(fallback_attempt_plan)

    fallback_attempt_plan["poisoned"] = "mutated after the fact"
    assert failed_attempt_plan == before_failed, (
        "mutating the fallback attempt's plan corrupted the failed attempt's plan -- aliasing bug"
    )

    failed_attempt_plan["poisoned"] = "mutated after the fact, the other way"
    assert fallback_attempt_plan != before_fallback or "poisoned" in fallback_attempt_plan, (
        "fallback plan was already mutated above; this just re-confirms independence"
    )
    del fallback_attempt_plan["poisoned"]
    assert fallback_attempt_plan == before_fallback, (
        "mutating the failed attempt's plan corrupted the fallback attempt's plan -- aliasing bug"
    )


def test_forced_build_failure_fallback_rest_is_deterministic(monkeypatch):
    """Two independent genesis builds, each forced to fail on the same first
    build_physical_action_proposal call, must produce byte-identical
    fallback proposals -- if Slice A's shallow-copy-plus-copy-on-write
    refactor left any hidden aliasing that depends on incidental object
    identity or mutation order, this is exactly the kind of thing that would
    make two otherwise-identical runs diverge."""
    domain1, frame1, entities1 = _genesis_frame()
    output1, calls1 = _activate_with_forced_first_failure(domain1, frame1, monkeypatch)
    proposal1 = _fallback_proposal(output1)

    domain2, frame2, entities2 = _genesis_frame()
    output2, calls2 = _activate_with_forced_first_failure(domain2, frame2, monkeypatch)
    proposal2 = _fallback_proposal(output2)

    assert len(calls1) == len(calls2)
    assert proposal1 == proposal2
