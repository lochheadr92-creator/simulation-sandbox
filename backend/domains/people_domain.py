"""PeopleDomain (Phase 2): multi-stage actions, short plans, knowledge-driven
utility, deterministic interruption/resume. Still proposal-only, still reads
only Core-issued named RNG streams, still never mutates or touches storage.

Phase 4B note: this domain no longer proposes person death itself - that is
now owned entirely by LifecycleDomain (see domains/lifecycle_domain.py),
which runs earlier in the same tick (environment phase) so a person's death
always commits before their own action proposal is evaluated. This domain
only guards against acting AFTER death by adding an `alive == True`
precondition to every action proposal (see _build_proposal below) - Core's
existing sequential commit-time revalidation is what makes a same-tick
death correctly cancel that tick's action, with zero Core changes.

Per-tick flow for each living person:
  1. perceive() + merge into persistent `knowledge` (canonical, discovered-only)
  2. decide WHICH action should be active this tick:
       a. a critical need (>= CRITICAL_THRESHOLD) interrupts an unrelated
          in-progress interruptible action -> pause it, plan the critical goal
       b. otherwise keep continuing an in-progress action as-is
       c. otherwise resume a previously paused action if one exists
       d. otherwise score fresh candidates (people_utility.score_candidates)
          and form a new short plan (people_planning.form_plan)
  3. always progress the (possibly just-decided) action by exactly one tick
     (people_planning.execute_action_tick) - this is what makes actions
     multi-frame and each step individually observable
  4. if the step finished, advance the plan to its next step (or complete it)
"""
from domains.base import DomainEngine, DomainOutput
from domains.perception import perceive, merge_knowledge, empty_knowledge
from domains.people_utility import score_candidates
from domains.people_planning import (
    idle_action, empty_plan, check_critical_interrupt, form_plan, start_step,
    execute_action_tick, context_from_action,
)


class PeopleDomain(DomainEngine):
    engine_id = "people"
    engine_version = "2.0.0"
    engine_priority = 10
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        return [eid for eid, e in entities.items() if e["type"] == "person" and e.get("alive", True)]

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        night = getattr(frame, "night", False)
        terrain = frame.terrain
        height = len(terrain)
        width = len(terrain[0]) if height else 0

        for eid in frame.due_entity_ids:
            e = frame.entities.get(eid)
            if not e or e["type"] != "person" or not e.get("alive", True):
                continue

            tick = frame.simulation_time
            pos = e["position"]
            rng = frame.rng.stream(f"people.{eid}.decision.{tick}")

            existing_knowledge = e.get("knowledge") or empty_knowledge()
            delta = perceive(pos, frame.entities, terrain, tick)
            knowledge, _discovered = merge_knowledge(existing_knowledge, delta)

            action = dict(e.get("action") or idle_action())
            plan = dict(e.get("plan") or empty_plan())
            paused = e.get("paused")

            candidates, context = score_candidates(e, knowledge, pos, tick, night, action, terrain, frame.entities)
            cand_by_goal = {c["goal"]: c for c in candidates}

            critical_goal = check_critical_interrupt(e)
            critical_available = bool(critical_goal) and cand_by_goal.get(critical_goal, {}).get("availability", 0) > 0
            active_now = action.get("status") in ("travelling", "performing")
            already_on_critical = active_now and plan.get("goal") == critical_goal

            candidates_out = []
            selected_goal = plan.get("goal")
            decision_note = ""

            if critical_available and active_now and not already_on_critical and action.get("interruptible", True):
                paused = {"action": {**action, "status": "paused"}, "plan": dict(plan)}
                plan = form_plan(critical_goal, e, context, tick)
                action = start_step(plan["steps"][0], e, eid, context, terrain, tick, pos)
                selected_goal = critical_goal
                candidates_out = candidates
                decision_note = f"CRITICAL: {critical_goal} interrupts in-progress {paused['action']['type']}"

            elif active_now:
                decision_note = ""  # just continue; nothing new decided this tick

            elif paused and not critical_available:
                action = dict(paused["action"])
                action["status"] = "travelling" if action["type"] == "travel" else "performing"
                plan = dict(paused["plan"])
                paused = None
                selected_goal = plan.get("goal")
                decision_note = f"resumed {action['type']} after prior interruption cleared"

            else:
                best = max(candidates, key=lambda c: c["score"])
                plan = form_plan(best["goal"], e, context, tick)
                action = start_step(plan["steps"][0], e, eid, context, terrain, tick, pos)
                selected_goal = best["goal"]
                candidates_out = candidates
                decision_note = f"selected {best['goal']} (score={best['score']})"

            # Always progress the (possibly just-decided) action by one tick.
            result = execute_action_tick(e, eid, action, frame.entities, terrain, tick, night, rng)
            action = result["action"]
            tree_delta = action.pop("_tree_delta", None)
            carcass_delta = action.pop("_carcass_delta", None)
            animal_delta = action.pop("_animal_delta", None)
            step_note = result["explanation"]
            explanation = f"{decision_note} -> {step_note}" if decision_note else step_note

            if result["advance_plan"]:
                plan["step_index"] = plan.get("step_index", 0) + 1
                if action["status"] != "failed" and plan["step_index"] < len(plan.get("steps", [])):
                    next_step = plan["steps"][plan["step_index"]]
                    context = context_from_action(action, result["pos"])
                    action = start_step(next_step, e, eid, context, terrain, tick, result["pos"])
                else:
                    plan["status"] = "completed" if action["status"] != "failed" else "abandoned"

            proposal = self._build_proposal(e, eid, action, plan, paused, knowledge, result,
                                             tree_delta, carcass_delta, animal_delta, tick, explanation)
            proposals.append(proposal)
            diagnostics[eid] = {
                "candidates": candidates_out, "selected_goal": selected_goal, "explanation": explanation,
                "rng_stream": f"people.{eid}.decision.{tick}", "night": night,
            }

        return DomainOutput(proposals=proposals, diagnostics=diagnostics)

    def _build_proposal(self, e, eid, action, plan, paused, knowledge, result,
                         tree_delta, carcass_delta, animal_delta, tick, explanation):
        entity_updates = {eid: {
            "position": result["pos"], "hunger": result["hunger"], "thirst": result["thirst"],
            "energy": result["energy"], "inventory": result["inventory"], "food_inventory": result["food_inventory"],
            "has_shelter": result["has_shelter"], "knowledge": knowledge, "action": action, "plan": plan,
            "paused": paused, "current_goal": plan.get("goal"),
        }}
        touched_scope = list(result["touched_scope"])
        preconditions = list(result["preconditions"])
        preconditions.append({"entity_id": eid, "field": "alive", "op": "eq", "value": True})
        new_entities = dict(result["new_entities"])

        for delta in (tree_delta, carcass_delta):
            if delta:
                entity_updates[delta["id"]] = {"resource": delta["resource"], "claimed_tick": delta["claimed_tick"]}
                if delta["id"] not in touched_scope:
                    touched_scope.append(delta["id"])

        if animal_delta:
            animal_id = animal_delta.pop("id")
            entity_updates[animal_id] = animal_delta
            if animal_id not in touched_scope:
                touched_scope.append(animal_id)

        return {
            "proposal_family": "people_action",
            "proposal_type": result["event_type"],
            "proposer_engine_id": self.engine_id,
            "proposer_engine_version": self.engine_version,
            "entity_id": eid,
            "causal_parent_event_ids": [e["last_event_id"]] if e.get("last_event_id") else [],
            "is_exogenous": not e.get("last_event_id"),
            "requested_time": tick,
            "phase": "agent",
            "engine_priority": self.engine_priority,
            "touched_scope": touched_scope,
            "preconditions": preconditions,
            "mutation": {"entity_updates": entity_updates, "new_entities": new_entities},
            "explanation": explanation,
        }
