"""Executable pin for the protected living_settlement baseline hash.

The frozen hash was previously enforced by documentation only (FRONTIER.md and
the evidence records), which is how commit 2d68ac16 moved it silently: the suite
pins repeat/replay equality, and equality still holds on a moved trajectory.
This test makes an unratified move fail at commit time instead.

Runtime: ~2 minutes (320 ticks). That cost is the point -- it is the only check
that compares against a literal baseline rather than against itself.

WHEN THIS TEST FAILS, DO NOT UPDATE THE CONSTANT TO GO GREEN. A moved hash is a
STOP: produce the exact causal diff for the move (first divergent accepted
event, per-type census delta, pre-registered bands), get the new baseline
ratified, and only then update FROZEN_LIVING_SETTLEMENT_320 in the same commit
as the ratification evidence.
"""
from tools.living_agent_harness import run_living_agent_harness

# Ratified 2026-07-28 (commit 2d68ac16, STORE_SURPLUS_MIN_FOOD 3 -> 2).
# Supersedes 9c1b9b8ba28a6fa830ff141d1eea7a8755d7c13a5a62dfc94ba93a15946e55d4.
FROZEN_LIVING_SETTLEMENT_320 = (
    "4240d6a088514c1c84367b03beac4712e4d33009b28f0f22748cbdac305de1bb"
)
FROZEN_ACCEPTED_EVENT_COUNT = 4868


def test_living_settlement_320_matches_the_ratified_frozen_hash():
    result = run_living_agent_harness(
        "living-agents-stage6",
        ticks=320,
        run_id="frozen-baseline-pin",
        scenario_id="living_settlement",
    )

    assert result["final_state_hash"] == FROZEN_LIVING_SETTLEMENT_320, (
        "living_settlement@320 final_state_hash moved. This is a STOP, not a "
        "constant to edit -- see this module's docstring."
    )
    summary = result["summary"]
    assert summary["accepted_event_count"] == FROZEN_ACCEPTED_EVENT_COUNT
    assert summary["replay_state_hash"] == FROZEN_LIVING_SETTLEMENT_320
    assert summary["replay_matches_final_entities"] is True
