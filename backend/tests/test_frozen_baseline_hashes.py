"""Executable pin for the protected living_settlement baseline.

The frozen hash was previously enforced by documentation only (FRONTIER.md and
the evidence records), which is how commit 2d68ac16 moved it silently: the suite
pins repeat/replay equality, and equality still holds on a moved trajectory.
This test compares against literal baseline values instead.

Runtime: ~2 minutes (320 ticks). That cost is the point -- it is the only check
in the suite that compares against a literal baseline rather than against
itself.

WHEN THIS TEST FAILS, DO NOT UPDATE THE CONSTANTS TO GO GREEN. A moved baseline
is a STOP: produce the exact causal diff (first divergent accepted event,
per-type census delta, pre-registered bands), get the new baseline ratified, and
only then update the constants in the same commit as the ratification evidence.

Read the failure before assuming a state change:
  - final_state_hash only .............. tick-320 world state moved
  - sequence hash only ................. events/frames reordered, same end state
                                         (CORE-INTEGRITY-004 content-ordering
                                         drift -- still a STOP, still unratified)
  - rejected_proposal_count only ....... validation changed what gets rejected;
                                         canonical state is unaffected
  - accepted_event_count only .......... may be a representation-only refactor
                                         (event split/merge) rather than a
                                         behaviour change -- check before
                                         treating it as a moved baseline

What this pin does NOT cover, and what still needs judgement elsewhere:
divergence that reconverges before tick 320; any scenario other than
living_settlement; any horizon other than 320; any seed other than
living-agents-stage6; and world health generally -- the pre-registered bands
(deaths, rest fraction, action entropy) are checked at ratification time, by
hand, not here. A deterministic but unhealthy world passes this test.

Failure modes catalogued by the 2026-07-28 adversarial review; see
memory/evidence/frozen-hash/.
"""
from tools.living_agent_harness import run_living_agent_harness

# Ratified 2026-07-28 (commit 2d68ac16, STORE_SURPLUS_MIN_FOOD 3 -> 2).
# Supersedes 9c1b9b8ba28a6fa830ff141d1eea7a8755d7c13a5a62dfc94ba93a15946e55d4.
# Evidence: memory/evidence/frozen-hash/2d68ac16-LIVING-SETTLEMENT-320-RATIFICATION.md
#
# Moved 2026-07-28 by Active Leg A (social commit-survival fix): the narrowed
# participant write plus record-scoped pins let disjoint concurrent social
# actions commit (accepted 4868 -> 5088) and replaced the whole-blob
# living_agent_eq_failed false positive (1263 -> 0) with honest, path-named
# same-record rejections (living_agent.relationships.*_eq_failed, 1155).
# Evidence: memory/evidence/frozen-hash/leg-a-2026-07-28-baseline-census.json
# and leg-a-2026-07-28-postfix-pins-census.json (320-tick census, clean
# leg-a-verify worktree, replay equality holds).
FROZEN_LIVING_SETTLEMENT_320 = (
    "e80743460e46be4cf73086854988baa9aa92de27cbff9b5e777430497a0317b2"
)
FROZEN_ACCEPTED_EVENT_SEQUENCE = (
    "6e16a535bbc0b3dfa5d2e82553dddfb6adfe61762a8ec65bfa8f58b79f463a38"
)
FROZEN_FRAME_SEQUENCE = (
    "be4cb25f9d659afd70b8b2a03465b2f45b121d8136f464336eaa651b02c75ee0"
)
FROZEN_ACCEPTED_EVENT_COUNT = 5088
FROZEN_REJECTED_PROPOSAL_COUNT = 1320


def test_living_settlement_320_matches_the_ratified_frozen_baseline():
    result = run_living_agent_harness(
        "living-agents-stage6",
        ticks=320,
        run_id="frozen-baseline-pin",
        scenario_id="living_settlement",
    )
    summary = result["summary"]

    assert result["final_state_hash"] == FROZEN_LIVING_SETTLEMENT_320, (
        "living_settlement@320 final_state_hash moved. This is a STOP, not a "
        "constant to edit -- see this module's docstring."
    )
    assert summary["accepted_event_sequence_hash"] == (
        FROZEN_ACCEPTED_EVENT_SEQUENCE
    ), (
        "Accepted events were reordered or their content changed while the "
        "final state held. Ordering is part of the baseline -- STOP."
    )
    assert summary["frame_sequence_hash"] == FROZEN_FRAME_SEQUENCE
    assert summary["accepted_event_count"] == FROZEN_ACCEPTED_EVENT_COUNT
    assert summary["rejected_proposal_count"] == FROZEN_REJECTED_PROPOSAL_COUNT
    assert summary["replay_matches_final_entities"] is True
