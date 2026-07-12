"""PeopleDomain (Phase 2 + 5A5 cognitive grounding).

Per-tick cognitive chain (same activation, proposal-only):
  1. Observation frame is version-pinned by Core (entities_view deepcopy).
  2. Bounded perceive() — integer Manhattan vision; sorted entity IDs.
  3. merge_knowledge — material changes only (no silent full-world copy).
  4. Needs evaluation + score_candidates from knowledge / this-tick detections.
  5. form_plan / start_step / execute_action_tick.
  6. Single proposal; knowledge field omitted when unchanged (bounded growth).
  7. Core commit pipeline remains authoritative.

Omniscient target scans are not used for planning. Hunting uses known/perceived
animals only. Exploration uses passable unknown 4-neighbours only.
"""
from domains.base import DomainEngine, DomainOutput
from domains.perception import perceive, merge_knowledge, empty_knowledge, _compat_knowledge
from domains.people_utility import score_candidates
from domains.people_planning import (
    idle_action, empty_plan, check_critical_interrupt, form_plan, start_step,
    execute_action_tick, context_from_action,
)
from domains.food_interaction_proposals import (
    propose_protocol_steps_for_person,
    propose_stranded_accepted_invalidations,
)


class PeopleDomain(DomainEngine):
    engine_id = "people"
    engine_version = "2.1.0"
    engine_priority = 10
    phase = "agent"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        return [eid for eid, e in entities.items() if e["type"] == "person" and e.get("alive", True)]

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        night = getattr(frame, "night", False)
        terrain = frame.terrain

        tick = frame.simulation_time

        # Stable activation order
        for eid in sorted(frame.due_entity_ids):
            e = frame.entities.get(eid)
            if not e or e["type"] != "person" or not e.get("alive", True):
                continue

            pos = e["position"]
            rng = frame.rng.stream(f"people.{eid}.decision.{tick}")

            existing_knowledge = _compat_knowledge(e.get("knowledge") or empty_knowledge())
            # Perception from pinned frame only (frame.entities is the observation view).
            delta = perceive(pos, frame.entities, terrain, tick, observer_id=eid)
            knowledge, knowledge_changed, learned = merge_knowledge(
                existing_knowledge, delta, observer_id=eid,
            )

            action = dict(e.get("action") or idle_action())
            plan = dict(e.get("plan") or empty_plan())
            paused = e.get("paused")

            candidates, context = score_candidates(
                e, knowledge, pos, tick, night, action, terrain,
                entities=frame.entities, perception_delta=delta,
            )
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
                decision_note = ""  # continue; nothing new decided this tick

            elif paused and not critical_available:
                action = dict(paused["action"])
                action["status"] = "travelling" if action["type"] == "travel" else "performing"
                plan = dict(paused["plan"])
                paused = None
                selected_goal = plan.get("goal")
                decision_note = f"resumed {action['type']} after prior interruption cleared"

            else:
                best = max(candidates, key=lambda c: c["score"])
                ranked = sorted(candidates, key=lambda c: (-c["score"], c["goal"]))
                runner = next((c for c in ranked if c["goal"] != best["goal"]), None)
                plan = form_plan(best["goal"], e, context, tick)
                action = start_step(plan["steps"][0], e, eid, context, terrain, tick, pos)
                selected_goal = best["goal"]
                candidates_out = candidates
                if runner:
                    decision_note = (
                        f"selected {best['goal']} (score={best['score']}, travel={best.get('travel_cost')}) "
                        f"over {runner['goal']} (score={runner['score']}, travel={runner.get('travel_cost')})"
                    )
                else:
                    decision_note = f"selected {best['goal']} (score={best['score']})"
                if best["goal"] == "EXPLORE" and best.get("urgent_without_known_solution"):
                    decision_note += "; explore: urgent need without known solution"

            result = execute_action_tick(e, eid, action, frame.entities, terrain, tick, night, rng)
            action = result["action"]
            tree_delta = action.pop("_tree_delta", None)
            carcass_delta = action.pop("_carcass_delta", None)
            animal_delta = action.pop("_animal_delta", None)
            food_transfer = action.pop("_food_transfer", None)
            step_note = result["explanation"]
            explanation = f"{decision_note} -> {step_note}" if decision_note else step_note
            if knowledge_changed and learned:
                explanation = f"learned {len(learned)} fact(s); {explanation}"

            if result["advance_plan"]:
                plan["step_index"] = plan.get("step_index", 0) + 1
                if action["status"] != "failed" and plan["step_index"] < len(plan.get("steps", [])):
                    next_step = plan["steps"][plan["step_index"]]
                    context = context_from_action(action, result["pos"])
                    action = start_step(next_step, e, eid, context, terrain, tick, result["pos"])
                else:
                    plan["status"] = "completed" if action["status"] != "failed" else "abandoned"

            proposal = self._build_proposal(
                e, eid, action, plan, paused, knowledge, knowledge_changed, result,
                tree_delta, carcass_delta, animal_delta, food_transfer, tick, explanation,
            )
            proposals.append(proposal)
            # Phase 5B3: protocol proposals ride as additional domain proposals.
            # Action proposal stays first so existing tests reading proposals[0]
            # remain stable; Core orders by content_hash, not list position.
            # Evaluate against the pinned frame so protocol decisions do not
            # observe uncommitted same-tick mutations from this activation.
            view_entities = dict(frame.entities)
            if knowledge_changed:
                # Protocol create uses initiator knowledge; surface this tick's
                # merged knowledge only for the acting person in a shallow copy.
                view_entities[eid] = dict(e)
                view_entities[eid]["knowledge"] = knowledge
            proposals.extend(propose_protocol_steps_for_person(view_entities, eid, tick))
            diagnostics[eid] = {
                "candidates": candidates_out,
                "selected_goal": selected_goal,
                "explanation": explanation,
                "rng_stream": f"people.{eid}.decision.{tick}",
                "night": night,
                "perception": {
                    "radius": delta.get("radius"),
                    "rule_version": delta.get("perception_rule_version"),
                    "detection_count": len(delta.get("detections") or []),
                    "detections": (delta.get("detections") or [])[:12],
                    "knowledge_changed": knowledge_changed,
                    "learned": learned[:12],
                },
                "planning": {
                    "selected_goal": selected_goal,
                    "target_from_knowledge": bool(
                        context.get("water_target") or context.get("food_target_id")
                        or context.get("animal_target_id") or context.get("frontier_target")
                    ),
                    "explore_neighbour_only": True,
                },
            }

        # Global stranded-accepted maintenance once per activation on the pinned
        # observation frame (next boundary after same-tick contention/fulfil).
        # Duplicate invalidates with per-person steps reject safely as terminal.
        proposals.extend(propose_stranded_accepted_invalidations(frame.entities, tick))

        return DomainOutput(proposals=proposals, diagnostics=diagnostics)

    def _build_proposal(self, e, eid, action, plan, paused, knowledge, knowledge_changed,
                        result, tree_delta, carcass_delta, animal_delta, food_transfer, tick, explanation):
        entity_updates = {
            eid: {
                "position": result["pos"],
                "hunger": result["hunger"],
                "thirst": result["thirst"],
                "energy": result["energy"],
                "inventory": result["inventory"],
                "food_inventory": result["food_inventory"],
                "has_shelter": result["has_shelter"],
                "action": action,
                "plan": plan,
                "paused": paused,
                "current_goal": plan.get("goal"),
            }
        }
        # Bounded growth: rewrite knowledge only on material perception change
        # (accepted event still carries the action; knowledge rides along when new).
        if knowledge_changed:
            entity_updates[eid]["knowledge"] = knowledge

        touched_scope = list(result["touched_scope"])
        preconditions = list(result["preconditions"])
        preconditions.append({"entity_id": eid, "field": "alive", "op": "eq", "value": True})
        # Every people action writes this field.  Revalidation prevents a
        # later single-person proposal from overwriting an accepted transfer.
        preconditions.append({"entity_id": eid, "field": "food_inventory", "op": "eq", "value": e.get("food_inventory", 0)})
        new_entities = dict(result["new_entities"])

        if food_transfer:
            receiver_id = food_transfer["receiver_id"]
            entity_updates[receiver_id] = {
                "food_inventory": food_transfer["receiver_food_inventory"] + food_transfer["quantity"],
            }
            if receiver_id not in touched_scope:
                touched_scope.append(receiver_id)

        for delta in (tree_delta, carcass_delta):
            if delta:
                entity_updates[delta["id"]] = {
                    "resource": delta["resource"], "claimed_tick": delta["claimed_tick"],
                }
                if delta["id"] not in touched_scope:
                    touched_scope.append(delta["id"])

        if animal_delta:
            animal_id = animal_delta.pop("id")
            entity_updates[animal_id] = animal_delta
            if animal_id not in touched_scope:
                touched_scope.append(animal_id)

        proposal = {
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
        if food_transfer:
            proposal["transfer"] = {
                key: food_transfer[key]
                for key in ("contract_version", "giver_id", "receiver_id", "field", "quantity")
            }
        return proposal
