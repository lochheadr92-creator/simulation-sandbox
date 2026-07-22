"""Stage 8C Phase 1 response-side probe (the single authorized run).

Read-only, observation-only. Runs the committed `collective_groups` tick loop
(seed living-agents-stage6) exactly once via the same build_genesis/run_tick
primitives as tools/living_agent_harness.py and the existing _probe_8c_*.py.
It makes NO assignment to any imported module, NO monkey-patch, NO rule/hook
registration, and modifies NO engine/domain/kernel file. Every value it keeps
is extracted as a scalar/plain copy off the live objects immediately after
run_tick, so nothing it holds can feed back into the simulation.

Purpose: close the CANNOT-yield set {1,3,4,6} from the Phase 0.6 Step 1
analysis in one run, and capture the Leg B pre-change baseline at the same
length.

  #1 per-agent hunger + position (Q2 uniqueness): does a second agent cross
     hunger>=600 and simply never propose REQUEST_HELP (geometry/priority),
     or is only person-007 ever eligible?
  #3 RESPOND_HELP firing: accepted + rejected, paired to the originating
     REQUEST_HELP with tick delta.
  #4 recipient-side pending-commitment presence at T+1, measured directly;
     distinguishes never-delivered from delivered-then-evicted (the 12-cap
     confounder, commitments_per_entity=12, living_agent_contracts.py:86).
  #6 cooperate-source separation via the winning candidate's current_goal.

Field paths verified against source (not guessed):
  hunger = entity["living_agent"]["pressures"]["hunger"]["severity"]
           (living_settlement_domain.py:245,284)
  role   = entity["stage6_role"]                (living_settlement_domain.py:243)
  commit = entity["living_agent"]["commitments"] (living_agent_social.py:170-180)
  goal   = accepted_event["mutation"]["entity_updates"][actor]["current_goal"]
           (commit_pipeline.py:465-477 ; living_agent_social.py:304)
  reject = rejected["proposal_snapshot"] (full proposal) (commit_pipeline.py:312)

Durability (MANDATORY): the result object is written to the output JSON after
every checkpoint and again in a finally block on cap-hit / exception, so a
truncated run still yields usable evidence (the prior 1000-tick attempt
produced a 0-byte file). Records ticks_run, target_ticks_at_stop, truncated,
stopped_reason, wall_clock_seconds.

Raw social-event goals are stored verbatim and classified in a pure
post-processing pass (build_result); a single deterministic run cannot be
re-run to reclassify, so no live filter is trusted with an assumed goal string.

Usage: python -m tools._probe_8c_response_side <target_ticks> <output_json_abspath>
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter

from core.kernel import build_genesis, run_tick
from core.rng import DeterministicRNG
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from scenarios import get_scenario

SEED = "living-agents-stage6"
SCENARIO_ID = "collective_groups"
CHECKPOINT_EVERY = 10
HUNGER_THRESHOLD = 600     # OBSERVED legacy REQUEST_HELP trigger (living_settlement_domain.py:292); not imposed by this probe
MAX_WALL_SECONDS = 600.0   # 10-minute hard cap; diagnostic-only, not a scenario/engine constant
EPISODE_GAP = 8            # request-episode break = due_tick horizon tick+8 (living_settlement_domain.py:322)
RESPOND_GOAL = "RESPOND_HELP"
REQUEST_GOAL = "REQUEST_HELP"


def _hunger(entity):
    pressures = ((entity or {}).get("living_agent") or {}).get("pressures") or {}
    return int((pressures.get("hunger") or {}).get("severity", 0))


def _commitments(entity):
    return dict(((entity or {}).get("living_agent") or {}).get("commitments") or {})


def _alive_people(entities):
    return {eid: e for eid, e in entities.items()
            if isinstance(e, dict) and e.get("type") == "person" and e.get("alive", True)}


def _goal_of(container_entity_id, container):
    """current_goal from a proposal or accepted-event mutation.entity_updates[actor]."""
    upd = ((container.get("mutation") or {}).get("entity_updates") or {}).get(container_entity_id) or {}
    return upd.get("current_goal")


def probe(target_ticks, out_path):
    scenario = get_scenario(SCENARIO_ID)
    lineage_key = f"{SEED}|{SCHEMA_VERSION}|{ENGINE_VERSION}"
    world, entities, genesis, _rej, order_index = build_genesis(SEED, scenario, lineage_key)
    valid_parent_ids = {e["id"] for e in genesis}
    rng = DeterministicRNG(SEED)

    accepted_by_type = Counter()
    social_goal_distribution = Counter()   # "event_type|goal" for every social_* event (safety net)
    request_events = []                    # accepted REQUEST_HELP
    request_rejected = []                  # rejected REQUEST_HELP proposals
    response_events = []                   # accepted social_cooperate + social_refuse (raw, with goal)
    response_rejected = []                 # rejected proposals whose goal == RESPOND_HELP
    delivery_records = {}                  # commitment_id -> delivery/eviction record (#4)

    person_ids = sorted(_alive_people(entities))
    max_hunger = {pid: _hunger(entities[pid]) for pid in person_ids}
    first_cross_600 = {}                   # pid -> first tick hunger>=600
    ever_requested = set()                 # pids that proposed REQUEST_HELP (accepted or rejected)
    hunger_position_samples = []           # per checkpoint

    state = {"ticks_run": 0, "truncated": False, "stopped_reason": None}
    t0 = time.time()
    last_checkpoint = t0

    def build_result():
        respond_help = [r for r in response_events if r["goal"] == RESPOND_GOAL]
        # pair each RESPOND_HELP to the originating REQUEST_HELP (creator==respond.target, beneficiary==respond.actor)
        req_by_pair = {}
        for rq in request_events:
            req_by_pair.setdefault((rq["actor_id"], rq["target_id"]), []).append(rq)
        paired = []
        for rh in respond_help:
            # responder actor answered a request whose creator is rh.target and beneficiary is rh.actor
            candidates = sorted(req_by_pair.get((rh["target_id"], rh["actor_id"]), []),
                                key=lambda rq: rq["tick"])
            prior = [rq for rq in candidates if rq["tick"] <= rh["tick"]]
            src = prior[-1] if prior else None
            paired.append({
                "respond_tick": rh["tick"], "responder_id": rh["actor_id"],
                "requester_id": rh["target_id"], "respond_event_type": rh["event_type"],
                "linked_request_tick": src["tick"] if src else None,
                "linked_request_event_id": src["event_id"] if src else None,
                "tick_delta": (rh["tick"] - src["tick"]) if src else None,
                "request_event_in_causal_parents": bool(
                    src and src["event_id"] in (rh.get("causal_parent_event_ids") or [])),
            })
        req_ticks = sorted({r["tick"] for r in request_events})
        episodes = []
        for tk in req_ticks:
            if episodes and tk - episodes[-1]["end"] <= EPISODE_GAP:
                episodes[-1]["end"] = tk
                episodes[-1]["count"] += 1
            else:
                episodes.append({"start": tk, "end": tk, "count": 1})
        req_pairs = sorted({(r["actor_id"], r["target_id"]) for r in request_events if r["target_id"]})
        resp_pairs = sorted({(r["actor_id"], r["target_id"]) for r in respond_help if r["target_id"]})
        hungry_ever = {pid for pid in person_ids if max_hunger.get(pid, 0) >= HUNGER_THRESHOLD}
        cooperate_goals = Counter(r["goal"] for r in response_events if r["event_type"] == "social_cooperate")
        return {
            "scenario": SCENARIO_ID, "seed": SEED,
            "target_ticks_at_stop": target_ticks,
            "ticks_run": state["ticks_run"],
            "truncated": state["truncated"],
            "stopped_reason": state["stopped_reason"],
            "wall_clock_seconds": round(time.time() - t0, 2),
            "hunger_threshold_observed": HUNGER_THRESHOLD,
            # ---- #3 RESPOND_HELP firing ----
            "respond_help_accepted_count": len(respond_help),
            "respond_help_rejected_count": len(response_rejected),
            "respond_help_rejected_reason_codes": dict(Counter(r["reason_code"] for r in response_rejected)),
            "respond_help_request_pairing": paired,
            "respond_help_events": respond_help,
            "respond_help_rejected": response_rejected,
            # ---- #6 cooperate-source separation ----
            "social_cooperate_by_source_goal": dict(cooperate_goals),
            "social_response_events_all": response_events,
            "social_goal_distribution_raw": dict(social_goal_distribution),
            # ---- #1 per-agent need / geometry ----
            "person_ids": person_ids,
            "max_hunger_per_agent": dict(sorted(max_hunger.items())),
            "first_tick_crossed_600": dict(sorted(first_cross_600.items())),
            "agents_that_ever_requested": sorted(ever_requested),
            "agents_hungry_ge600_ever": sorted(hungry_ever),
            "agents_hungry_ge600_but_never_requested": sorted(hungry_ever - ever_requested),
            "hunger_position_checkpoint_samples": hunger_position_samples,
            # ---- #4 delivery / eviction ----
            "delivery_records": delivery_records,
            "requests_never_delivered_to_beneficiary": [c for c, d in delivery_records.items() if not d["present_at_T1"]],
            "requests_delivered_then_evicted": [c for c, d in delivery_records.items()
                                                if d["present_at_T1"] and d.get("present_at_final") is False],
            "requests_delivered_and_retained": [c for c, d in delivery_records.items()
                                                if d["present_at_T1"] and d.get("present_at_final") is True],
            # ---- Leg B baseline ----
            "accepted_by_type_full": dict(sorted(accepted_by_type.items())),
            "request_help_accepted_count": len(request_events),
            "request_help_rejected_count": len(request_rejected),
            "request_help_rejected_reason_codes": dict(Counter(r["reason_code"] for r in request_rejected)),
            "request_dyads_ordered": [list(p) for p in req_pairs],
            "respond_dyads_ordered": [list(p) for p in resp_pairs],
            "request_episodes": episodes,
            "request_events": request_events,
            "survival": {"alive_persons": len(_alive_people(entities))},
        }

    def flush():
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(build_result(), fh, indent=2, default=str)
        except Exception as exc:   # a flush failure must never mask evidence
            print(json.dumps({"flush_error": str(exc)}), file=sys.stderr, flush=True)

    try:
        for tick in range(1, target_ticks + 1):
            accepted, rejected, order_index, diag = run_tick(
                "probe", entities, world["terrain"], tick, rng, order_index,
                lineage_key, scenario.enabled_domains,
                valid_causal_parent_event_ids=valid_parent_ids,
            )
            state["ticks_run"] = tick

            for pid in person_ids:
                h = _hunger(entities.get(pid))
                if h > max_hunger.get(pid, 0):
                    max_hunger[pid] = h
                if h >= HUNGER_THRESHOLD and pid not in first_cross_600:
                    first_cross_600[pid] = tick

            for r in rejected:
                snap = r.get("proposal_snapshot") or {}
                ptype = snap.get("proposal_type")
                goal = _goal_of(snap.get("entity_id"), snap)
                sa = snap.get("social_action") or {}
                if ptype == "social_request_help" or goal == REQUEST_GOAL:
                    request_rejected.append({"tick": tick, "actor_id": r.get("entity_id"),
                        "target_id": sa.get("target_id"), "reason_code": r.get("reason_code"),
                        "reason_detail": r.get("reason_detail"), "goal": goal})
                    ever_requested.add(r.get("entity_id"))
                elif goal == RESPOND_GOAL:
                    response_rejected.append({"tick": tick, "actor_id": r.get("entity_id"),
                        "target_id": sa.get("target_id"), "reason_code": r.get("reason_code"),
                        "reason_detail": r.get("reason_detail")})

            for e in accepted:
                valid_parent_ids.add(e["id"])
                etype = e.get("event_type")
                accepted_by_type[etype] += 1
                if not (isinstance(etype, str) and etype.startswith("social_")):
                    continue
                actor = e.get("entity_id")
                goal = _goal_of(actor, e)
                sa = e.get("social_action") or {}
                target = sa.get("target_id")
                social_goal_distribution[f"{etype}|{goal}"] += 1

                if etype == "social_request_help" or goal == REQUEST_GOAL:
                    commitment = sa.get("commitment") or {}
                    cid = commitment.get("commitment_id")
                    request_events.append({"tick": tick, "event_id": e["id"], "actor_id": actor,
                        "target_id": target, "commitment_id": cid,
                        "created_tick": commitment.get("created_tick"),
                        "due_tick": commitment.get("due_tick"),
                        "causal_parent_event_ids": e.get("causal_parent_event_ids", [])})
                    ever_requested.add(actor)
                    if cid and target:   # #4 : beneficiary presence in the post-tick-T (== T+1 frozen) state
                        bene = _commitments(entities.get(target))
                        present = cid in bene
                        delivery_records[cid] = {"commitment_id": cid, "created_tick": tick,
                            "creator_id": actor, "beneficiary_id": target,
                            "present_at_T1": present,
                            "status_at_T1": (bene.get(cid) or {}).get("status") if present else None,
                            "present_at_final": None}

                if etype in ("social_cooperate", "social_refuse"):
                    response_events.append({"tick": tick, "event_id": e["id"], "actor_id": actor,
                        "target_id": target, "event_type": etype, "goal": goal,
                        "causal_parent_event_ids": e.get("causal_parent_event_ids", [])})

            if tick % CHECKPOINT_EVERY == 0 or tick == target_ticks:
                sample = {"tick": tick, "agents": {}}
                for pid in person_ids:
                    ent = entities.get(pid) or {}
                    sample["agents"][pid] = {"hunger": _hunger(ent),
                        "position": ent.get("position"), "role": ent.get("stage6_role"),
                        "carried_food": (ent.get("carried_resources") or {}).get("food", 0),
                        "alive": ent.get("alive", True)}
                hunger_position_samples.append(sample)
                now = time.time()
                print(json.dumps({"checkpoint_tick": tick, "cumulative_seconds": round(now - t0, 2),
                    "window_seconds": round(now - last_checkpoint, 2),
                    "request_accepted": len(request_events), "respond_accepted":
                        sum(1 for r in response_events if r["goal"] == RESPOND_GOAL),
                    "valid_parent_ids": len(valid_parent_ids)}), file=sys.stderr, flush=True)
                last_checkpoint = now
                flush()

            if len(_alive_people(entities)) < 2:
                state["stopped_reason"] = "population_cannot_produce_pairs"
                break
            if (time.time() - t0) >= MAX_WALL_SECONDS:
                state["truncated"] = True
                state["stopped_reason"] = "wall_time_cap"
                break
        else:
            state["stopped_reason"] = "reached_target_ticks"
    except Exception as exc:
        state["stopped_reason"] = f"exception:{type(exc).__name__}:{exc}"
        print(json.dumps({"probe_exception": state["stopped_reason"],
                          "ticks_run": state["ticks_run"]}), file=sys.stderr, flush=True)
    finally:
        for cid, d in delivery_records.items():
            d["present_at_final"] = cid in _commitments(entities.get(d["beneficiary_id"]))
        flush()

    return build_result()


if __name__ == "__main__":
    tk = int(sys.argv[1]) if len(sys.argv) > 1 else 308
    out = sys.argv[2] if len(sys.argv) > 2 else "probe_8c_response_side.json"
    result = probe(tk, out)
    print(json.dumps({"done": True, "ticks_run": result["ticks_run"],
        "truncated": result["truncated"], "stopped_reason": result["stopped_reason"],
        "wall_clock_seconds": result["wall_clock_seconds"],
        "respond_help_accepted": result["respond_help_accepted_count"],
        "respond_help_rejected": result["respond_help_rejected_count"],
        "request_help_accepted": result["request_help_accepted_count"],
        "cooperate_by_source": result["social_cooperate_by_source_goal"],
        "agents_hungry_ge600_but_never_requested": result["agents_hungry_ge600_but_never_requested"]},
        default=str), file=sys.stderr, flush=True)
