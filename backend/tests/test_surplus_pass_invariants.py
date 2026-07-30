"""Surplus Pass — Tier B: organic-behaviour invariants (SURPLUS_PASS.md).

Invariant tests over one shared 1,000-tick census of `surplus_forage`
(20 agents, seed surplus-tier-b). These assert emergent thresholds only —
never a frozen hash — so intentional retunes update thresholds, not baselines.

The module-scoped census runs the raw kernel loop (build_genesis + run_tick),
counts what it needs from each tick's accepted events and live entities, and
discards both, so memory stays flat over the long horizon.
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import scenarios  # noqa: F401  (registration side effects)
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from scenarios.registry import get_scenario

SEED = "surplus-tier-b"
SCENARIO_ID = "surplus_forage"
TICKS = 1000
NUM_PEOPLE = 20


@pytest.fixture(scope="module")
def census():
    """One shared 1,000-tick run. Returns emergent counters only."""
    scenario = get_scenario(SCENARIO_ID)
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, _genesis, _genesis_rejected, order_index = build_genesis(
        SEED, scenario, lineage_key)
    rng = DeterministicRNG(SEED)

    trade_events = 0
    ever_stored_by_tick = {}          # eid -> first tick stored total > 0
    positions = defaultdict(list)     # eid -> [(x, y)] per tick
    for tick in range(1, TICKS + 1):
        accepted, _rejected, order_index, _diagnostics = run_tick(
            "surplus-tier-b-census", entities, world["terrain"], tick, rng,
            order_index, lineage_key, scenario.enabled_domains,
        )
        trade_events += sum(1 for event in accepted if event["event_type"] == "offer_trade")
        for eid, entity in entities.items():
            if entity.get("type") != "person" or not entity.get("alive", True):
                continue
            stored = entity.get("stored_resources") or {}
            if stored.get("wood", 0) + stored.get("food", 0) > 0 and eid not in ever_stored_by_tick:
                ever_stored_by_tick[eid] = tick
            pos = entity["position"]
            positions[eid].append((pos["x"], pos["y"]))

    alive = {
        eid for eid, entity in entities.items()
        if entity.get("type") == "person" and entity.get("alive", True)
    }
    storage_locations = {
        eid: (entity["storage_location"]["x"], entity["storage_location"]["y"])
        for eid, entity in entities.items()
        if entity.get("type") == "person" and entity.get("storage_location")
    }
    return {
        "trade_events": trade_events,
        "ever_stored_by_tick": ever_stored_by_tick,
        "positions": positions,
        "alive": alive,
        "storage_locations": storage_locations,
        "person_count": sum(1 for e in entities.values() if e.get("type") == "person"),
    }


def test_at_least_20pct_agents_accumulate_stored_surplus_500_ticks(census):
    """Spec gate: in a 500-tick run with 20 agents, >=20% of agents
    accumulate non-zero stored surplus at least once."""
    early = [eid for eid, tick in census["ever_stored_by_tick"].items() if tick <= 500]
    assert census["person_count"] == NUM_PEOPLE
    assert len(early) >= max(1, NUM_PEOPLE // 5), (
        f"only {len(early)}/{NUM_PEOPLE} agents stored surplus by tick 500"
    )


def test_at_least_5_trade_events_1000_ticks(census):
    """Spec gate: in a 1000-tick run with 20 agents, >=5 trade events occur."""
    assert census["trade_events"] >= 5, (
        f"only {census['trade_events']} offer_trade events in {TICKS} ticks"
    )


def _median(values):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def test_home_vs_forage_movement_entropy(census):
    """Spec gate: distinct movement patterns (home tile vs foraging area),
    measured by visit-frequency entropy.

    Per agent over its ticks: the home tile must be a genuine attractor
    (visit share far above the ~1/676 uniform-tile baseline), the agent must
    still range over multiple tiles (foraging spread), and the normalized
    Shannon entropy of the visit distribution must sit well below the
    uniform-visit maximum of 1.0 (concentration = home bias).
    """
    home_shares = []
    unique_counts = []
    norm_entropies = []
    for eid, visits in census["positions"].items():
        if len(visits) < 200 or eid not in census["storage_locations"]:
            continue
        counts = Counter(visits)
        total = len(visits)
        unique = len(counts)
        home_share = counts.get(census["storage_locations"][eid], 0) / total
        entropy = -sum((n / total) * math.log(n / total) for n in counts.values())
        norm_entropy = entropy / math.log(unique) if unique > 1 else 0.0
        home_shares.append(home_share)
        unique_counts.append(unique)
        norm_entropies.append(norm_entropy)

    assert len(home_shares) >= 10, f"too few long-lived agents with storage: {len(home_shares)}"
    med_home = _median(home_shares)
    med_unique = _median(unique_counts)
    med_entropy = _median(norm_entropies)
    assert med_home >= 0.03, f"home tile is no attractor: median home share {med_home:.3f}"
    assert med_unique >= 6, f"no foraging spread: median unique tiles {med_unique}"
    assert med_entropy <= 0.93, f"visits ~uniform (no home bias): median norm entropy {med_entropy:.3f}"
