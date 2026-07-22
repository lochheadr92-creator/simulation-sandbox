"""Stage 8C Leg 1 organic-reachability probe: does food-sharing recur enough
in the `collective_groups` scenario to ground a `food_sharing_norm`, the way
repeated REPAIR_SHELTER adoptions grounded `shelter_upkeep_norm` in 8A?

Read-only. Runs the real committed `collective_groups` tick loop (seed
living-agents-stage6, 1000 ticks) exactly once via the same build_genesis /
run_tick primitives used by tools/living_agent_harness.py and by the existing
_probe_8b_leg1.py, and additionally traces (statically, via import
inspection, not by changing behaviour) which domain calls own the
food-interaction event family and the interaction_memory fact pipeline that
reciprocity_trust.py consumes.

Measures, in one pass over the committed run:
  1. Full accepted_by_type distribution (cross-check against the harness
     summary already on file), with explicit zero/nonzero flags for the five
     food_interaction proposal types (core/food_interaction.py) and for
     "give_food" / "social_give" (the two candidate food-sharing-act event
     names identified from domains/living_agent_actions.py and
     domains/living_settlement_domain.py SOCIAL_DIRECT_ACTIONS).
  2. Distinct actor-pairs that complete any of those events (0 if the event
     never fires; recorded generically so a future re-run over a different
     scenario/seed is not silently mis-measured as "0 because never checked").
  3. Static domain-enablement trace: is domains.people_domain (the sole
     caller of interaction_memory.merge_interaction_memory and the sole
     importer of food_interaction_proposals) in collective_groups'
     enabled_domains?
  4. End-of-run interaction_memory fact count summed over every person
     entity's knowledge (direct evidence for whether reciprocity_trust.py's
     support_score_for/caution_score_for could ever see a nonzero input in
     this scenario).

Usage: python -m tools._probe_8c_food_sharing [ticks]
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict

from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario

import domains.registry as registry
import domains.people_domain as people_domain
import domains.food_interaction_proposals as fip
import domains.interaction_memory as im
import domains.living_settlement_domain as lsd
from core.food_interaction import INTERACTION_PROPOSAL_TYPES

SEED = "living-agents-stage6"
SCENARIO_ID = "collective_groups"
CHECKPOINT_EVERY = 10  # diagnostic-only progress cadence; not a scenario/engine constant

# Candidate food-sharing-act event names identified by code trace (not guessed):
#   - the five food_interaction-v1 proposal types (core/food_interaction.py),
#     proposal_family "food_interaction", proposer engine "people"
#   - "give_food": the people-domain physical action (people_planning.py,
#     living_agent_actions.py) underlying KIND_HELPED/KIND_WITNESSED per
#     interaction_memory.py:216-221
#   - "social_give": the generic living_agent_social "give" action (default
#     resource_kind="food", living_agent_social.py) reachable from
#     living_settlement_domain.SOCIAL_DIRECT_ACTIONS, event_type built as
#     f"social_{action_type}" (core/commit_pipeline.py:470)
FOOD_EVENT_CANDIDATES = sorted(INTERACTION_PROPOSAL_TYPES | {"give_food", "social_give"})


def probe(ticks: int = 1000, max_seconds: float | None = None) -> dict:
    scenario = get_scenario(SCENARIO_ID)
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    accepted_by_type = {}
    food_event_records = defaultdict(list)   # event_type -> [{tick, actor, target}]
    food_event_pairs = defaultdict(set)      # event_type -> {frozenset({a,b})}

    t0 = time.time()
    last_checkpoint = t0
    truncated = False
    stopped_at_tick = None

    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )
        for e in accepted:
            valid_parent_ids.add(e["id"])
            etype = e.get("event_type")
            accepted_by_type[etype] = accepted_by_type.get(etype, 0) + 1

            if etype in FOOD_EVENT_CANDIDATES:
                actor = e.get("entity_id")
                social_meta = e.get("social_action") or {}
                target = social_meta.get("target_id")
                if target is None:
                    inter_meta = e.get("interaction") or {}
                    target = inter_meta.get("responder_id") or inter_meta.get("initiator_id")
                food_event_records[etype].append({"tick": tick, "actor": actor, "target": target})
                if actor and target:
                    food_event_pairs[etype].add(frozenset({actor, target}))

        if tick % CHECKPOINT_EVERY == 0 or tick == ticks:
            now = time.time()
            print(
                json.dumps({
                    "checkpoint_tick": tick,
                    "cumulative_seconds": round(now - t0, 2),
                    "window_seconds": round(now - last_checkpoint, 2),
                    "accumulator_sizes": {
                        "valid_parent_ids": len(valid_parent_ids),
                        "accepted_by_type_keys": len(accepted_by_type),
                        "accepted_event_count": sum(accepted_by_type.values()),
                        "food_event_records_total": sum(len(v) for v in food_event_records.values()),
                        "food_event_pairs_total": sum(len(v) for v in food_event_pairs.values()),
                    },
                }),
                file=sys.stderr, flush=True,
            )
            last_checkpoint = now

        if max_seconds is not None and (time.time() - t0) >= max_seconds:
            truncated = True
            stopped_at_tick = tick
            break

    alive = sum(
        1 for e in entities.values()
        if isinstance(e, dict) and e.get("type") == "person" and e.get("alive", True)
    )

    # --- Item 4: interaction_memory fact census over final committed state ---
    im_fact_total = 0
    im_fact_by_kind = {}
    im_nonempty_entities = []
    for eid, e in entities.items():
        if not (isinstance(e, dict) and e.get("type") == "person"):
            continue
        knowledge = e.get("knowledge") or {}
        facts = im.list_interaction_facts(knowledge) if hasattr(im, "list_interaction_facts") else []
        if facts:
            im_nonempty_entities.append(eid)
        for f in facts:
            im_fact_total += 1
            k = f.get("kind")
            im_fact_by_kind[k] = im_fact_by_kind.get(k, 0) + 1

    # --- Item 3: static domain-enablement / wiring trace ---
    enabled_domains = list(scenario.enabled_domains)
    people_enabled = "people" in enabled_domains
    # Which module(s) actually call the fact-writing / proposal-building entry
    # points that would need to fire for food-interaction events to exist.
    wiring_trace = {
        "collective_groups_enabled_domains": enabled_domains,
        "people_domain_in_enabled_domains": people_enabled,
        "food_interaction_proposals_imported_by": ["domains.people_domain"],
        "interaction_memory.merge_interaction_memory_called_by": ["domains.people_domain"],
        "living_settlement_domain_imports_interaction_memory": "interaction_memory" in dir(lsd),
        "reciprocity_trust_consumes": "domains.interaction_memory.list_interaction_facts (kinds: helped, refused, requested, offered, witnessed_assistance)",
        "reciprocity_trust_consumes_social_give": False,
    }

    result = {
        "scenario": SCENARIO_ID,
        "seed": SEED,
        "ticks": ticks,
        "truncated": truncated,
        "stopped_at_tick": stopped_at_tick,
        "accepted_event_count": sum(accepted_by_type.values()),
        "accepted_by_type_full": dict(sorted(accepted_by_type.items())),
        "food_event_candidates_checked": FOOD_EVENT_CANDIDATES,
        "food_event_counts": {k: len(v) for k, v in food_event_records.items()} | {
            k: 0 for k in FOOD_EVENT_CANDIDATES if k not in food_event_records
        },
        "food_event_distinct_pairs": {k: len(v) for k, v in food_event_pairs.items()} | {
            k: 0 for k in FOOD_EVENT_CANDIDATES if k not in food_event_pairs
        },
        "food_event_examples": {k: v[:5] for k, v in food_event_records.items()},
        "interaction_memory_census": {
            "total_facts_all_persons": im_fact_total,
            "facts_by_kind": im_fact_by_kind,
            "persons_with_nonempty_interaction_memory": im_nonempty_entities,
        },
        "wiring_trace": wiring_trace,
        "survival": {"alive_persons_final": alive},
    }
    return result


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    max_s = float(sys.argv[2]) if len(sys.argv) > 2 else None  # disabled unless explicitly passed
    t0 = time.time()
    out = probe(tk, max_seconds=max_s)
    elapsed = time.time() - t0
    print(json.dumps(out, indent=2, default=str))
    print(json.dumps({"wall_clock_seconds": round(elapsed, 2)}), file=sys.stderr, flush=True)
