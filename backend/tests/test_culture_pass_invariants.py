"""Culture Pass — Tier B: culture-emergence invariants (CULTURE_PASS.md).

Invariant tests over one shared 500-tick census of `surplus_forage`
(20 agents, seed culture-tier-b), using the shared census driver in
`tools/culture_census.py` (the same code the chunked probe runner uses, so
CI and chunked local verification measure identically). These assert emergent
thresholds only — never a frozen hash — so intentional retunes update
thresholds, not baselines.

Thresholds are calibrated to seed `culture-tier-b` on `surplus_forage`
(invariants of the scenario, not universal constants) — same discipline as
the Surplus Pass Tier B module.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from tools.culture_census import NUM_PEOPLE, census_ticks, finalize, new_census_state

SEED = "culture-tier-b"
TICKS = 500


@pytest.fixture(scope="module")
def census():
    """One shared 500-tick run. Returns emergent counters only."""
    state = new_census_state(SEED)
    census_ticks(state, TICKS)
    return finalize(state)


def test_barter_still_fires(census):
    """Culture must not kill the surplus economy it hooks into."""
    assert census["trade_events"] >= 2, (
        f"only {census['trade_events']} barter events in {TICKS} ticks"
    )


def test_aid_events_occur(census):
    """Aid fires organically: a satiated stocked agent gifts a hungry
    gate-passing ally at least twice in 500 ticks."""
    assert census["aid_events"] >= 2, (
        f"only {census['aid_events']} aid events in {TICKS} ticks"
    )


def test_norm_convergence(census):
    """Norms converge: on at least one resource pair held by >=2 living
    agents, >=50% of holders agree on the modal (give, receive) terms."""
    convergence = census["norm_convergence"]
    assert convergence, "no shared norms emerged at all"
    best = max(entry["agreement"] for entry in convergence.values())
    assert best >= 0.5, f"no pair reached 50% term agreement: {convergence}"


def test_memory_query_hit_rate(census):
    """Collective memory is decision-affecting: of OFFER_TRADE candidate
    activations, >=20% select a partner the agent remembers."""
    assert census["offer_ticks"] > 0, "no trade/aid candidates were ever available"
    assert census["memory_hit_rate"] >= 0.2, (
        f"memory hit rate {census['memory_hit_rate']} over {census['offer_ticks']} offer ticks"
    )


def test_gate_enforcement(census):
    """Gate-keeping is real and exact: the gate excludes at least one
    aid-eligible non-trader during the run, and no aid event ever lands on a
    receiver with no earlier barter participation (verified from the event
    stream, not from diagnostics)."""
    assert census["gate_blocked"] >= 1, "the gate never excluded anyone"
    assert census["aid_to_non_traders"] == [], (
        f"aid reached non-traders: {census['aid_to_non_traders']}"
    )


def test_accumulation_curve_not_collapsed_by_aid(census):
    """The aid probe: >=20% of agents still accumulate stored surplus by tick
    500 (Surplus Pass Tier B parity), so gifting is not draining the loop."""
    assert census["person_count"] == NUM_PEOPLE
    assert census["stored_surplus_agents_by_500"] >= max(1, NUM_PEOPLE // 5), (
        f"only {census['stored_surplus_agents_by_500']}/{NUM_PEOPLE} agents stored "
        f"surplus by tick 500"
    )
