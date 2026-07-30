"""Culture Pass — shared 500-tick culture-emergence census (CULTURE_PASS.md).

One source of truth for the Tier B census, importable by both the pytest
invariant module (single-process run) and the chunked probe runner
(`tools/_probe_culture_census.py`, for machines where 500 ticks exceeds one
invocation). Counts emergent counters only and discards per-tick state, so
memory stays flat over the horizon — same discipline as the Surplus Pass
Tier B census.

Resumable: `new_census_state()` -> `census_ticks(state, upto_tick)` advances
the shared state; pickle between chunks carries (entities, order_index,
next_tick, counters). DeterministicRNG streams embed the tick, so a fresh
stream set per chunk reproduces the identical run.
"""
from __future__ import annotations

import scenarios  # noqa: F401  (registration side effects)
from core.constants import (
    AID_CONTRACT_VERSION,
    ENGINE_VERSION,
    SCHEMA_VERSION,
    TRADE_CONTRACT_VERSION,
)
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from scenarios.registry import get_scenario

SCENARIO_ID = "surplus_forage"
NUM_PEOPLE = 20


def new_census_state(seed: str) -> dict:
    scenario = get_scenario(SCENARIO_ID)
    lineage_key = f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, _genesis, _genesis_rejected, order_index = build_genesis(
        seed, scenario, lineage_key)
    return {
        "seed": seed,
        "scenario": scenario,
        "lineage_key": lineage_key,
        "terrain": world["terrain"],
        "entities": entities,
        "order_index": order_index,
        "next_tick": 1,
        "counters": {
            "trade_events": 0,
            "aid_events": 0,
            "trade_participants": [],      # (tick, giver_id, receiver_id) barter only
            "aid_receivers": [],           # (tick, receiver_id)
            "offer_ticks": 0,              # person-ticks with an OFFER_TRADE candidate available
            "memory_hit_ticks": 0,         # of those, selected via collective memory
            "gate_blocked": 0,             # aid-eligible subjects excluded by the gate
            "ever_stored_by_tick": {},     # eid -> first tick stored total > 0
            "norm_history": [],            # (tick, {eid: {pair: (give, receive)}}) sampled
        },
    }


def _norm_terms(entity):
    culture = entity.get("culture_state") or {}
    terms = {}
    for pair, norm in (culture.get("norms") or {}).items():
        terms[pair] = (
            (norm.get("expected_give_x100", 0) + 50) // 100,
            (norm.get("expected_receive_x100", 0) + 50) // 100,
        )
    return terms


def census_ticks(state: dict, upto_tick: int) -> dict:
    """Advance the census through `upto_tick` (inclusive)."""
    scenario = state["scenario"]
    rng = DeterministicRNG(state["seed"])
    counters = state["counters"]
    entities = state["entities"]
    order_index = state["order_index"]
    # Caller-owned fragment cache (CORE-PERF-01 Slice B): the same
    # optimization the harness and every long probe use; hash values are
    # identical, only the per-event serialization cost changes.
    entity_json_cache: dict = state.setdefault("entity_json_cache", {})

    for tick in range(state["next_tick"], upto_tick + 1):
        accepted, _rejected, order_index, diagnostics = run_tick(
            "culture-census", entities, state["terrain"], tick, rng,
            order_index, state["lineage_key"], scenario.enabled_domains,
            entity_json_cache=entity_json_cache,
        )
        for event in accepted:
            if event["event_type"] != "offer_trade":
                continue
            trade = event.get("trade") or {}
            version = trade.get("contract_version")
            if version == TRADE_CONTRACT_VERSION:
                counters["trade_events"] += 1
                counters["trade_participants"].append(
                    (tick, trade.get("giver_id"), trade.get("receiver_id")))
            elif version == AID_CONTRACT_VERSION:
                counters["aid_events"] += 1
                counters["aid_receivers"].append((tick, trade.get("receiver_id")))
        for eid, entity in entities.items():
            if entity.get("type") != "person" or not entity.get("alive", True):
                continue
            stored = entity.get("stored_resources") or {}
            if stored.get("wood", 0) + stored.get("food", 0) > 0 \
                    and eid not in counters["ever_stored_by_tick"]:
                counters["ever_stored_by_tick"][eid] = tick
            culture_diag = (diagnostics.get(eid) or {}).get("culture") or {}
            if culture_diag.get("offer_available"):
                counters["offer_ticks"] += 1
                if culture_diag.get("memory_hit"):
                    counters["memory_hit_ticks"] += 1
            counters["gate_blocked"] += int(culture_diag.get("gate_blocked") or 0)
        if tick % 100 == 0:
            counters["norm_history"].append((
                tick,
                {
                    eid: _norm_terms(entity)
                    for eid, entity in entities.items()
                    if entity.get("type") == "person" and entity.get("alive", True)
                },
            ))
    state["next_tick"] = upto_tick + 1
    state["order_index"] = order_index
    return state


def finalize(state: dict) -> dict:
    """Derived census metrics from a completed run."""
    counters = state["counters"]
    entities = state["entities"]
    persons = {
        eid: e for eid, e in entities.items()
        if e.get("type") == "person"
    }
    alive = {eid for eid, e in persons.items() if e.get("alive", True)}

    # Norm convergence at the final snapshot: per pair, the share of agents
    # holding that norm whose rounded terms equal the modal terms.
    final_terms = {
        eid: _norm_terms(e) for eid, e in persons.items() if eid in alive
    }
    convergence = {}
    for pair in sorted({p for terms in final_terms.values() for p in terms}):
        holders = [terms[pair] for terms in final_terms.values() if pair in terms]
        if len(holders) < 2:
            continue
        modal = max(sorted(set(holders)), key=holders.count)
        convergence[pair] = {
            "holders": len(holders),
            "modal_terms": modal,
            "agreement": round(holders.count(modal) / len(holders), 3),
        }

    # Convergence over time: the same agreement metric per 100-tick sample.
    trajectory = []
    for sample_tick, snapshot in counters["norm_history"]:
        window = {}
        for pair in sorted({p for terms in snapshot.values() for p in terms}):
            holders = [terms[pair] for terms in snapshot.values() if pair in terms]
            if len(holders) < 2:
                continue
            modal = max(sorted(set(holders)), key=holders.count)
            window[pair] = {
                "holders": len(holders),
                "agreement": round(holders.count(modal) / len(holders), 3),
            }
        trajectory.append((sample_tick, window))

    # Gate semantics, verified from the event stream: every aid receiver must
    # appear as a barter participant at an earlier tick.
    trader_ticks = {}
    for tick, giver, receiver in counters["trade_participants"]:
        for pid in (giver, receiver):
            if pid not in trader_ticks or tick < trader_ticks[pid]:
                trader_ticks[pid] = tick
    aid_to_non_traders = [
        (tick, rid) for tick, rid in counters["aid_receivers"]
        if rid not in trader_ticks or trader_ticks[rid] >= tick
    ]

    stored_by_500 = [
        eid for eid, tick in counters["ever_stored_by_tick"].items() if tick <= 500
    ]
    stored_totals = {
        eid: dict((persons[eid].get("stored_resources") or {}))
        for eid in stored_by_500
    }
    return {
        "seed": state["seed"],
        "ticks_run": state["next_tick"] - 1,
        "person_count": len(persons),
        "alive_at_end": len(alive),
        "trade_events": counters["trade_events"],
        "aid_events": counters["aid_events"],
        "aid_receivers": counters["aid_receivers"],
        "offer_ticks": counters["offer_ticks"],
        "memory_hit_ticks": counters["memory_hit_ticks"],
        "memory_hit_rate": (
            round(counters["memory_hit_ticks"] / counters["offer_ticks"], 3)
            if counters["offer_ticks"] else 0.0
        ),
        "gate_blocked": counters["gate_blocked"],
        "aid_to_non_traders": aid_to_non_traders,
        "norm_convergence": convergence,
        "norm_convergence_trajectory": trajectory,
        "norm_history_samples": len(counters["norm_history"]),
        "stored_surplus_agents_by_500": len(stored_by_500),
        "stored_totals_at_end": stored_totals,
    }
