"""Stage 8B Leg 1 Phase 1 evidence tooling: five read-only measurement probes.

Extends the pattern from _probe_norm_influence.py / _probe_repair_timing.py.
Runs the real committed collective_groups tick loop (seed living-agents-stage6)
and records, in one pass:

  1. Full active-norm tick set (group-norm-000) and full REPAIR_SHELTER
     candidate-present tick set -> overlap/distance measurement.
  2. Membership join/leave events (association_domain member_ids changes) for
     the group(s) that hold shelter_upkeep_norm, post-formation.
  3. living_agent_social interaction event types firing between a
     norm-holding-group member (post formation) and a non-member.
  4. Lifecycle births (none exist as a mechanic - counted anyway) and deaths.
  5. Full norm timeline: formations/refreshes/expiries with group membership
     snapshot at each formation tick.

Usage: python -m tools._probe_8b_leg1 [ticks]
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict

import domains.living_settlement_domain as lsd
from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario
from domains.group_norm_contracts import GROUP_NORM_REGISTRY_ID
from domains.association_contracts import ASSOCIATION_REGISTRY_ID

SEED = "living-agents-stage6"

_repair_cand_ticks = set()
_orig_norm_influence = lsd._apply_group_norm_influence

# --- Task 1 additions: pre-scoring capture + REPAIR_SHELTER gate decomposition ---
# The original capture point wraps _apply_group_norm_influence, which sees
# candidates only AFTER build_settlement_candidates truncates to
# LIMITS.candidate_goals_per_decision and AFTER score_goal_candidates re-sorts
# by goal_id and truncates again. A REPAIR_SHELTER candidate dropped by either
# truncation would be invisible there. We therefore ALSO capture pre-scoring,
# pre-truncation, by wrapping build_settlement_candidates, and record which of
# the four AND-gates at living_settlement_domain.py:351-364 is unsatisfied.
_repair_cand_ticks_prescore = set()
_orig_build_candidates = lsd.build_settlement_candidates

# tick -> {gate_name: count_of_builders_failing_only_that_gate}
_gate_fail_by_tick = {}
_gate_state_samples = []  # bounded per-builder gate snapshots


def _wrapped_build_candidates(entity_id, entity, state, knowledge, delta, tick):
    cands = _orig_build_candidates(entity_id, entity, state, knowledge, delta, tick)
    if any(c.get("goal") == "REPAIR_SHELTER" for c in cands):
        _repair_cand_ticks_prescore.add(int(tick))
    # Decompose the gate for builders only (the sole role that can propose repair).
    if entity.get("stage6_role") == "builder":
        resources = entity.get("carried_resources") or {}
        tools = lsd._observation_map(delta, "tool")
        shelters = lsd._observation_map(delta, "shelter")
        damaged = [
            sid for sid, obs in sorted(shelters.items())
            if int((obs.get("properties") or {}).get("condition", 1000)) < 750
        ]
        hammer = next((tid for tid, obs in sorted(tools.items())
                       if (obs.get("properties") or {}).get("tool_kind") == "hammer"), None)
        gates = {
            "damaged_shelter_visible": bool(damaged),
            "wood_gt_0": int(resources.get("wood", 0) or 0) > 0,
            "hammer_visible": hammer is not None,
        }
        failed = [name for name, ok in gates.items() if not ok]
        bucket = _gate_fail_by_tick.setdefault(int(tick), {})
        for name in failed:
            bucket[name] = bucket.get(name, 0) + 1
        if not failed:
            bucket["all_satisfied"] = bucket.get("all_satisfied", 0) + 1
        if len(_gate_state_samples) < 400:
            _gate_state_samples.append({
                "tick": int(tick), "entity": entity_id,
                "wood": int(resources.get("wood", 0) or 0),
                "shelters_visible": len(shelters),
                "damaged_visible": len(damaged),
                "hammer": hammer is not None,
                "failed_gates": failed,
            })
    return cands


def _windows(tick_set):
    """Contiguous runs of qualifying ticks. Two windows are separate only when
    at least one intervening tick does not qualify."""
    out = []
    for t in sorted(tick_set):
        if out and t == out[-1][1] + 1:
            out[-1][1] = t
        else:
            out.append([t, t])
    return [{"start": a, "end": b, "length": b - a + 1} for a, b in out]


def _wrapped_norm_influence(candidates, entity_id, entities, tick):
    if any(c.get("goal") == "REPAIR_SHELTER" for c in candidates):
        _repair_cand_ticks.add(int(tick))
    return _orig_norm_influence(candidates, entity_id, entities, tick)


def probe(ticks=1000):
    lsd._apply_group_norm_influence = _wrapped_norm_influence
    lsd.build_settlement_candidates = _wrapped_build_candidates
    scenario = get_scenario("collective_groups")
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    # --- item 5: norm timeline ---
    formations = []   # {tick, norm_id, group_id, members}
    transitions_log = []  # {tick, norm_id, group_id, kind}

    # --- item 1: active-norm tick set ---
    active_norm_ticks = set()

    # --- item 2: membership turnover of norm-holding group(s) ---
    # norm_group_ids populated as formations occur; track member_ids snapshot
    # each tick per tracked group to detect join/leave (diff-based, since no
    # explicit per-member join/leave event type exists at the association
    # layer - see association_contracts.py membership_changed transitions).
    tracked_group_ids = set()
    last_members_by_group = {}
    join_events = []   # {tick, group_id, agent_id}
    leave_events = []  # {tick, group_id, agent_id}
    membership_changed_transitions = []  # {tick, group_id, kind: 'membership_changed', removed}

    # --- item 3: interaction events between norm-group members and non-members ---
    # entity_id -> tick at which they became eligible (post formation, member of
    # a group holding a live norm). Simple approach: at every tick after first
    # formation, track current member set of norm-holding groups; count
    # social_* events per action_type where actor/target membership differs.
    interaction_counts = defaultdict(int)
    interaction_examples = defaultdict(list)
    accepted_by_type = {}

    # --- item 4: lifecycle births/deaths ---
    births = 0
    deaths = 0
    birth_event_types_seen = set()

    # --- Task 1: per-tick shelter/structure condition trajectory + repair events ---
    shelter_condition_by_tick = {}   # tick -> {entity_id: condition}
    repair_events = []               # {tick, actor, target, wood_after}
    wear_events = 0

    for tick in range(1, ticks + 1):
        accepted, rejected, order_index, diag = run_tick(
            "probe", entities, world["terrain"], tick, rng, order_index,
            lineage_key, scenario.enabled_domains,
            valid_causal_parent_event_ids=valid_parent_ids,
        )

        # Determine current norm-group member sets from THIS tick's committed
        # state (post-commit) for use in interaction attribution this tick.
        assoc = entities.get(ASSOCIATION_REGISTRY_ID) or {}
        candidates_reg = assoc.get("group_candidates") or {}
        current_members_by_group = {
            gid: set(cand.get("member_ids") or [])
            for gid, cand in candidates_reg.items()
            if gid in tracked_group_ids
        }
        all_norm_members = set()
        for gid in tracked_group_ids:
            all_norm_members |= current_members_by_group.get(gid, set())

        for e in accepted:
            valid_parent_ids.add(e["id"])
            etype = e.get("event_type")
            accepted_by_type[etype] = accepted_by_type.get(etype, 0) + 1

            # Task 1: repair / wear accounting straight off committed events.
            # Event types confirmed from the measured accepted-by-type distribution
            # of the 1,000-tick run: "structure_wear" (ecology) and "living_repair"
            # (settlement agent action).
            if etype == "structure_wear":
                wear_events += 1
            if etype == "living_repair":
                repair_events.append({
                    "tick": tick, "actor": e.get("entity_id"), "event_type": etype,
                })

            if etype == "death":
                deaths += 1
            if etype and "birth" in etype:
                births += 1
                birth_event_types_seen.add(etype)

            if etype == "group_form_norm":
                meta = e.get("group_norm_update") or {}
                for t in meta.get("transitions") or []:
                    kind = t.get("kind")
                    norm_id = t.get("norm_id")
                    group_id = t.get("group_id")
                    transitions_log.append({
                        "tick": tick, "norm_id": norm_id, "group_id": group_id, "kind": kind,
                    })
                    if kind == "formed":
                        tracked_group_ids.add(group_id)
                        cand = candidates_reg.get(group_id) or {}
                        members_now = sorted(cand.get("member_ids") or [])
                        formations.append({
                            "tick": tick, "norm_id": norm_id, "group_id": group_id,
                            "member_count": len(members_now), "members": members_now,
                        })

            if etype == "group_recognise" or (e.get("group_state_update") is not None) or True:
                pass  # membership diff handled below via registry snapshot, not per-event

            if etype and etype.startswith("social_"):
                actor_id = e.get("entity_id")
                social_meta = e.get("social_action") or {}
                target_id = social_meta.get("target_id")
                if all_norm_members and actor_id and target_id:
                    actor_member = actor_id in all_norm_members
                    target_member = target_id in all_norm_members
                    if actor_member != target_member:
                        interaction_counts[etype] += 1
                        if len(interaction_examples[etype]) < 3:
                            interaction_examples[etype].append(
                                {"tick": tick, "actor": actor_id, "target": target_id,
                                 "actor_member": actor_member, "target_member": target_member})

        # membership diff (post-commit state, AFTER this tick's events applied)
        assoc_after = entities.get(ASSOCIATION_REGISTRY_ID) or {}
        candidates_after = assoc_after.get("group_candidates") or {}
        for gid in tracked_group_ids:
            cand = candidates_after.get(gid) or {}
            members_now = set(cand.get("member_ids") or [])
            prior = last_members_by_group.get(gid)
            if prior is not None:
                joined = members_now - prior
                left = prior - members_now
                for agent_id in sorted(joined):
                    join_events.append({"tick": tick, "group_id": gid, "agent_id": agent_id})
                for agent_id in sorted(left):
                    leave_events.append({"tick": tick, "group_id": gid, "agent_id": agent_id})
            last_members_by_group[gid] = members_now

        # Task 1: per-tick shelter/structure condition + builder wood (post-commit).
        shelter_condition_by_tick[tick] = {
            eid: int(e.get("condition", 0) or 0)
            for eid, e in sorted(entities.items())
            if isinstance(e, dict) and e.get("type") in ("shelter", "structure")
        }

        # active-norm tick set (post-commit registry state)
        reg = entities.get(GROUP_NORM_REGISTRY_ID) or {}
        norms = reg.get("norms") or {}
        if any(n.get("status") == "active" for n in norms.values()):
            active_norm_ticks.add(tick)

    active_sorted = sorted(active_norm_ticks)
    repair_sorted = sorted(_repair_cand_ticks)
    intersection = active_norm_ticks & _repair_cand_ticks

    # --- Task 1 derived reporting ---
    pre_windows = _windows(_repair_cand_ticks_prescore)
    post_windows = _windows(_repair_cand_ticks)
    norm_windows = _windows(active_norm_ticks)
    pre_inter = _repair_cand_ticks_prescore & active_norm_ticks

    last_cand = max(_repair_cand_ticks_prescore) if _repair_cand_ticks_prescore else None
    first_norm = min(active_norm_ticks) if active_norm_ticks else None
    gap = (first_norm - last_cand) if (last_cand is not None and first_norm is not None) else None

    # Condition trajectory: sample every 25 ticks plus every tick in the 20 ticks
    # around the final candidate tick (where the gate closes).
    sample_ticks = set(range(1, ticks + 1, 25)) | {ticks}
    if last_cand:
        sample_ticks |= set(range(max(1, last_cand - 10), min(ticks, last_cand + 10) + 1))
    condition_trajectory = {
        str(t): shelter_condition_by_tick.get(t, {}) for t in sorted(sample_ticks)
    }

    # Which gate closed, at and after the final candidate tick.
    gate_after_last = {}
    if last_cand:
        for t in range(last_cand, ticks + 1):
            for name, n in (_gate_fail_by_tick.get(t) or {}).items():
                gate_after_last[name] = gate_after_last.get(name, 0) + n
    gate_totals = {}
    for _t, bucket in _gate_fail_by_tick.items():
        for name, n in bucket.items():
            gate_totals[name] = gate_totals.get(name, 0) + n

    alive = sum(1 for e in entities.values()
                if isinstance(e, dict) and e.get("type") == "person" and e.get("alive", True))

    result = {
        "ticks": ticks,
        "task1_diagnosis": {
            "prescore_candidate_windows": pre_windows,
            "postscore_candidate_windows": post_windows,
            "active_norm_windows": norm_windows,
            "prescore_vs_norm_intersection_size": len(pre_inter),
            "postscore_vs_norm_intersection_size": len(intersection),
            "truncation_undercount_ticks": len(_repair_cand_ticks_prescore - _repair_cand_ticks),
            "final_candidate_tick": last_cand,
            "first_active_norm_tick": first_norm,
            "gap_final_candidate_to_first_norm": gap,
            "gate_failure_totals_all_ticks": gate_totals,
            "gate_failure_totals_from_final_candidate_tick_onward": gate_after_last,
            "gate_state_samples_first_400": _gate_state_samples[:400],
            "shelter_condition_trajectory": condition_trajectory,
            "repair_events": repair_events,
            "structure_wear_events": wear_events,
            "accepted_by_type": dict(sorted(accepted_by_type.items())),
            "survival": {"alive_persons_final": alive, "deaths": deaths},
        },
        "item1_overlap": {
            "active_norm_tick_count": len(active_sorted),
            "active_norm_tick_min": active_sorted[0] if active_sorted else None,
            "active_norm_tick_max": active_sorted[-1] if active_sorted else None,
            "repair_candidate_tick_count": len(repair_sorted),
            "repair_candidate_tick_min": repair_sorted[0] if repair_sorted else None,
            "repair_candidate_tick_max": repair_sorted[-1] if repair_sorted else None,
            "intersection_size": len(intersection),
            "intersection_ticks_sample": sorted(intersection)[:20],
        },
        "item2_membership_turnover": {
            "tracked_group_ids": sorted(tracked_group_ids),
            "join_event_count": len(join_events),
            "leave_event_count": len(leave_events),
            "join_events": join_events,
            "leave_events": leave_events,
        },
        "item3_interactions": {
            "counts_by_event_type": dict(sorted(interaction_counts.items())),
            "examples_by_event_type": {k: v for k, v in interaction_examples.items()},
        },
        "item4_lifecycle": {
            "births": births,
            "birth_event_types_seen": sorted(birth_event_types_seen),
            "deaths": deaths,
        },
        "item5_timeline": {
            "formations": formations,
            "all_transitions": transitions_log,
        },
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    t0 = time.time()
    probe(tk)
    elapsed = time.time() - t0
    print(json.dumps({"wall_clock_seconds": round(elapsed, 2)}), file=sys.stderr)
