"""Stage 8C Leg 1 diagnostic: does accepted `social_request_help` behaviour in
`collective_groups` show genuine population spread, and what does existing
code actually prove about third-party observation of it?

Read-only, diagnostic-only. Does NOT modify commitment lifecycle, norm
formation, carriage, consequences, or kernel/commit_pipeline behaviour. Runs
the real committed `collective_groups` tick loop (seed living-agents-stage6)
through the same build_genesis/run_tick primitives as
tools/living_agent_harness.py and the existing _probe_8c_food_sharing.py,
bounded to <=250 ticks with a hard wall-time cap.

Witness-evidence caveat (do not weaken when reading results): association's
own domain has a documented one-tick lag (CLAUDE.md invariant 5) - it reads
entities_view frozen at the START of tick T+1, which is exactly the REAL
`entities` state as committed at the END of tick T (before any T+1 proposal
runs). commit_pipeline.py stamps `action["accepted_event_id"]` onto the
actor's own entity generically at commit time (any proposal type, not just
social), so a tick-T request_help action only becomes visible to
_accepted_action() starting at that T+1 snapshot - never within tick T
itself, since every domain in a tick reads one shared pre-commit
entities_view (core/kernel.py). This probe reproduces that exact timing: for
each tick-T accepted event it calls derive_association_evidence() on the
real, already-mutated `entities` object taken immediately after run_tick(T)
returns, with tick argument T+1 - i.e. the byte-identical snapshot+tick pair
association's own domain would use the next time it activates. This is
strictly backward-looking (T+1 evidence describes T's committed state, never
a later tick's), so it cannot leak later co-presence into an earlier event. But
derive_association_evidence's own contract only ever produces
ASSOCIATION/PROXIMITY facts (distance<=1 at the same tick, categorised
"proximity"/"dependency"/etc.) - it does not model perception, attention, or
belief update, and this evidence is never merged into any third party's own
knowledge in this scenario (people_domain, the sole consumer of
interaction_memory, is disabled - see probe_8c_food_sharing's wiring_trace).
Every third-party record this probe reports is therefore labelled
"proximity/association evidence", never "witnessed" or "observed". The
requester and target are never counted in this third-party set.

Usage: python -m tools._probe_8c_social_request_help
"""
from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter

from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario

from domains.association_contracts import derive_association_evidence, _position_distance

SEED = "living-agents-stage6"
SCENARIO_ID = "collective_groups"
CHECKPOINT_EVERY = 10
INITIAL_TICKS = 150
MAX_TICKS = 250
MIN_ACCEPTED_FOR_EARLY_STOP = 3
MAX_WALL_SECONDS = 480.0  # hard safety cap; diagnostic-only, not a scenario/engine constant
VISIBLE_RANGE = 4  # descriptive only - matches living_agent_reasoning.py's target-visibility threshold


def _alive_people(entities: dict) -> dict:
    return {
        eid: e for eid, e in entities.items()
        if isinstance(e, dict) and e.get("type") == "person" and e.get("alive", True)
    }


def _commitments_of(entity: dict) -> dict:
    la = (entity or {}).get("living_agent") or {}
    return dict(la.get("commitments") or {})


def probe() -> dict:
    scenario = get_scenario(SCENARIO_ID)
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    candidate_requests = []   # every social_request_help proposal, accepted or rejected
    accepted_records = []     # full detail for each accepted social_request_help event

    t0 = time.time()
    last_checkpoint = t0
    truncated = False
    stopped_reason = None
    stopped_at_tick = None
    target_ticks = INITIAL_TICKS

    tick = 0
    while tick < target_ticks:
        tick += 1
        pre_tick_entities = copy.deepcopy(entities)

        accepted, rejected, order_index, diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )

        for r in rejected:
            snap = r.get("proposal_snapshot") or {}
            if snap.get("proposal_type") != "social_request_help":
                continue
            social_meta = snap.get("social_action") or {}
            candidate_requests.append({
                "status": "rejected",
                "tick": tick,
                "proposal_id": snap.get("proposal_id"),
                "actor_id": r.get("entity_id"),
                "target_id": social_meta.get("target_id"),
                "causal_parent_event_ids": snap.get("causal_parent_event_ids", []),
                "reason_code": r.get("reason_code"),
                "reason_detail": r.get("reason_detail"),
            })

        this_tick_request_help = []
        for e in accepted:
            valid_parent_ids.add(e["id"])
            if e.get("event_type") != "social_request_help":
                continue

            actor_id = e.get("entity_id")
            social_meta = e.get("social_action") or {}
            target_id = social_meta.get("target_id")
            commitment = social_meta.get("commitment") or {}

            candidate_requests.append({
                "status": "accepted",
                "tick": tick,
                "event_id": e["id"],
                "actor_id": actor_id,
                "target_id": target_id,
                "causal_parent_event_ids": e.get("causal_parent_event_ids", []),
            })

            # Outstanding pending-request count for this requester, measured from
            # the PRE-tick state (i.e. before this new request is added), so it
            # reflects what already existed, not double-counting the new one.
            prior_actor_commitments = _commitments_of(pre_tick_entities.get(actor_id))
            outstanding_pending = sum(
                1 for c in prior_actor_commitments.values()
                if c.get("creator_id") == actor_id and c.get("commitment_kind") == "request_help"
                and c.get("status") == "pending"
            )

            # Descriptive-only distance/visibility context at the moment of the
            # request (positions the request/target decision was actually made
            # from - not itself an evidence claim).
            people_now = _alive_people(pre_tick_entities)
            nearby_context = []
            for other_id, other_ent in sorted(people_now.items()):
                if other_id in (actor_id, target_id):
                    continue
                dist = _position_distance(
                    (pre_tick_entities.get(actor_id) or {}).get("position"),
                    other_ent.get("position"),
                )
                nearby_context.append({
                    "person_id": other_id,
                    "distance_to_actor": dist,
                    "within_visible_range_le4": dist is not None and dist <= VISIBLE_RANGE,
                })

            this_tick_request_help.append({
                "event_id": e["id"],
                "tick": tick,
                "actor_id": actor_id,
                "target_id": target_id,
                "causal_parent_event_ids": e.get("causal_parent_event_ids", []),
                "commitment_id": commitment.get("commitment_id"),
                "commitment_kind": commitment.get("commitment_kind"),
                "creator_id": commitment.get("creator_id"),
                "beneficiary_id": commitment.get("beneficiary_id"),
                "created_tick": commitment.get("created_tick"),
                "due_tick": commitment.get("due_tick"),
                "status_at_creation": commitment.get("status"),
                "outstanding_pending_requests_by_actor_before_this": outstanding_pending,
                "nearby_context": nearby_context,
            })

        if this_tick_request_help:
            # Association's own domain has a one-tick lag (see module docstring):
            # it would first see this tick's committed actions in the entities_view
            # frozen at the START of tick+1, which is exactly `entities` right now,
            # already mutated by run_commit_frame above. Reproduce that exact
            # snapshot+tick pairing rather than guessing at same-tick visibility.
            post_tick_entities = copy.deepcopy(entities)
            next_tick_evidence = derive_association_evidence(post_tick_entities, tick + 1)
            for rec in this_tick_request_help:
                actor_id, target_id, event_id = rec["actor_id"], rec["target_id"], rec["event_id"]
                third_party_evidence = []
                for item in next_tick_evidence:
                    members = list(item.get("person_ids") or [])
                    if not members or (actor_id not in members and target_id not in members):
                        continue
                    others = [m for m in members if m not in (actor_id, target_id)]
                    if not others:
                        continue  # both slots are the participants themselves, not a third party
                    source_ids = item.get("source_event_ids") or []
                    for other_id in others:
                        third_party_evidence.append({
                            "third_party_id": other_id,
                            "linked_participant": actor_id if actor_id in members else target_id,
                            "category": item.get("category"),
                            "evidence_id": item.get("evidence_id"),
                            "evidence_tick": item.get("tick"),
                            "source_event_ids": source_ids,
                            "cites_this_event": event_id in source_ids,
                        })
                rec["third_party_association_evidence"] = third_party_evidence
                accepted_records.append(rec)

        if tick % CHECKPOINT_EVERY == 0 or tick == target_ticks:
            now = time.time()
            print(
                json.dumps({
                    "checkpoint_tick": tick,
                    "cumulative_seconds": round(now - t0, 2),
                    "window_seconds": round(now - last_checkpoint, 2),
                    "accepted_request_help_so_far": len(accepted_records),
                    "valid_parent_ids": len(valid_parent_ids),
                }),
                file=sys.stderr, flush=True,
            )
            last_checkpoint = now

        alive_count = sum(1 for e in _alive_people(entities).values())
        if alive_count < 2:
            stopped_reason = "population_cannot_produce_pairs"
            stopped_at_tick = tick
            break

        if (time.time() - t0) >= MAX_WALL_SECONDS:
            truncated = True
            stopped_reason = "wall_time_cap"
            stopped_at_tick = tick
            break

        if tick == target_ticks and target_ticks == INITIAL_TICKS and len(accepted_records) < MIN_ACCEPTED_FOR_EARLY_STOP:
            target_ticks = MAX_TICKS  # extend once, continuing the same run - not a restart

    else:
        stopped_reason = stopped_reason or "reached_target_ticks"
        stopped_at_tick = stopped_at_tick or tick

    if stopped_reason is None:
        stopped_reason = "reached_target_ticks"
        stopped_at_tick = tick

    # --- Final-state eviction / later-transition check for every observed commitment ---
    final_commitment_status = []
    for rec in accepted_records:
        cid = rec["commitment_id"]
        actor_final = _commitments_of(entities.get(rec["actor_id"]))
        target_final = _commitments_of(entities.get(rec["target_id"]))
        in_actor = cid in actor_final
        in_target = cid in target_final
        final_status = None
        if in_actor:
            final_status = actor_final[cid].get("status")
        elif in_target:
            final_status = target_final[cid].get("status")
        final_commitment_status.append({
            "commitment_id": cid,
            "present_in_actor_final_state": in_actor,
            "present_in_target_final_state": in_target,
            "evicted_from_both": not in_actor and not in_target,
            "final_status_if_present": final_status,
            "status_changed_from_creation": (
                final_status is not None and final_status != rec["status_at_creation"]
            ),
        })

    # --- Analysis gates ---
    accepted_only = [r for r in candidate_requests if r["status"] == "accepted"]
    distinct_ticks = sorted({r["tick"] for r in accepted_only})
    distinct_requesters = sorted({r["actor_id"] for r in accepted_only})
    distinct_targets = sorted({r["target_id"] for r in accepted_only if r["target_id"]})
    pairs = sorted({(r["actor_id"], r["target_id"]) for r in accepted_only if r["target_id"]})
    distinct_pairs_unordered = sorted({frozenset(p) for p in pairs}, key=lambda s: sorted(s))
    people_in_pairs = sorted({pid for p in pairs for pid in p})

    requester_counts = Counter(r["actor_id"] for r in accepted_only)
    pair_counts = Counter((r["actor_id"], r["target_id"]) for r in accepted_only if r["target_id"])

    reversed_pairs_present = any(
        (b, a) in pair_counts for (a, b) in pair_counts if (a, b) != (b, a)
    )
    non_reversed_relationship_count = len(distinct_pairs_unordered)

    with_independent_witness = sum(
        1 for rec in accepted_records
        if any(ev["cites_this_event"] for ev in rec["third_party_association_evidence"])
    )
    with_proximity_only = sum(
        1 for rec in accepted_records
        if rec["third_party_association_evidence"] and not any(
            ev["cites_this_event"] for ev in rec["third_party_association_evidence"]
        )
    )
    with_no_third_party_evidence = sum(
        1 for rec in accepted_records if not rec["third_party_association_evidence"]
    )

    status_counts = Counter(f["final_status_if_present"] for f in final_commitment_status)
    evicted_count = sum(1 for f in final_commitment_status if f["evicted_from_both"])
    changed_count = sum(1 for f in final_commitment_status if f["status_changed_from_creation"])

    population_spread = (
        len(distinct_ticks) >= 3
        and len(distinct_requesters) >= 2
        and len(distinct_targets) >= 2
        and len(people_in_pairs) >= 3
        and (not requester_counts or max(requester_counts.values()) < len(accepted_only) or len(requester_counts) > 1)
        and non_reversed_relationship_count >= 2
    )

    result = {
        "scenario": SCENARIO_ID,
        "seed": SEED,
        "ticks_run": stopped_at_tick,
        "target_ticks_at_stop": target_ticks,
        "truncated": truncated,
        "stopped_reason": stopped_reason,
        "wall_clock_seconds": round(time.time() - t0, 2),
        "candidate_requests_total": len(candidate_requests),
        "candidate_requests_accepted": len(accepted_only),
        "candidate_requests_rejected": len(candidate_requests) - len(accepted_only),
        "rejected_reason_codes": dict(Counter(
            r["reason_code"] for r in candidate_requests if r["status"] == "rejected"
        )),
        "distinct_accepted_ticks": distinct_ticks,
        "distinct_requesters": distinct_requesters,
        "distinct_targets": distinct_targets,
        "distinct_actor_target_pairs_ordered": [list(p) for p in pairs],
        "distinct_actor_target_relationships_unordered": [sorted(s) for s in distinct_pairs_unordered],
        "total_distinct_people_across_pairs": people_in_pairs,
        "max_events_from_one_requester": max(requester_counts.values()) if requester_counts else 0,
        "max_events_for_one_pair": max(pair_counts.values()) if pair_counts else 0,
        "requester_event_counts": dict(requester_counts),
        "pair_event_counts": {f"{a}->{b}": n for (a, b), n in pair_counts.items()},
        "reversed_pair_present": reversed_pairs_present,
        "events_with_qualified_independent_association_evidence_citing_this_event": with_independent_witness,
        "events_with_proximity_evidence_only_not_citing_this_event": with_proximity_only,
        "events_with_no_third_party_evidence": with_no_third_party_evidence,
        "commitment_final_status_counts": dict(status_counts),
        "commitments_evicted_via_12_cap": evicted_count,
        "commitments_with_any_status_change_since_creation": changed_count,
        "population_spread_gate_result": population_spread,
        "population_spread_gate_criteria": {
            "distinct_ticks_ge_3": len(distinct_ticks) >= 3,
            "distinct_requesters_ge_2": len(distinct_requesters) >= 2,
            "distinct_targets_ge_2": len(distinct_targets) >= 2,
            "distinct_people_ge_3": len(people_in_pairs) >= 3,
            "no_single_requester_responsible_for_all": (
                len(requester_counts) > 1 if requester_counts else False
            ),
            "distinct_non_reversed_relationships_ge_2": non_reversed_relationship_count >= 2,
        },
        "accepted_event_records": accepted_records,
        "final_commitment_status": final_commitment_status,
        "rejected_candidate_records": [r for r in candidate_requests if r["status"] == "rejected"],
    }
    return result


if __name__ == "__main__":
    out = probe()
    print(json.dumps(out, indent=2, default=str))
