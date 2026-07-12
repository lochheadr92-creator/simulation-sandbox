"""Deterministic canonical weather transitions for the Stage 6 scenario."""
from domains.base import DomainEngine, DomainOutput
from domains.living_agent_contracts import default_affordances


WEATHER_CYCLE = (
    {"condition": "clear", "exposure": 0, "visibility_penalty": 0, "temperature": 650, "rain": 0},
    {"condition": "rain", "exposure": 180, "visibility_penalty": 1, "temperature": 520, "rain": 500},
    {"condition": "storm", "exposure": 420, "visibility_penalty": 2, "temperature": 430, "rain": 900},
    {"condition": "cold_clear", "exposure": 220, "visibility_penalty": 0, "temperature": 330, "rain": 0},
)
WEATHER_INTERVAL = 20


class WeatherDomain(DomainEngine):
    engine_id = "weather"
    engine_version = "1.0.0"
    engine_priority = -2
    phase = "environment"

    def select_due_ids(self, entities: dict, tick: int) -> list:
        if tick % WEATHER_INTERVAL != 0:
            return []
        return [
            entity_id for entity_id, entity in sorted(entities.items())
            if entity.get("type") == "weather"
        ]

    def activate(self, frame):
        proposals = []
        diagnostics = {}
        tick = frame.simulation_time
        for entity_id in sorted(frame.due_entity_ids):
            weather = frame.entities.get(entity_id)
            if not weather:
                continue
            cycle_index = (tick // WEATHER_INTERVAL) % len(WEATHER_CYCLE)
            next_state = dict(WEATHER_CYCLE[cycle_index])
            next_state.update({
                "cycle_index": cycle_index,
                "last_transition_tick": tick,
                "forecast": WEATHER_CYCLE[(cycle_index + 1) % len(WEATHER_CYCLE)]["condition"],
            })
            mutation = {"entity_updates": {entity_id: next_state}, "new_entities": {}}
            touched = [entity_id]
            if next_state["condition"] == "storm":
                signal_id = f"signal-weather-{tick}"
                signal = {
                    "type": "signal", "schema_version": "physical-signal-v1",
                    "position": dict(weather.get("position") or {"x": 5, "y": 5}),
                    "signal_kind": "warning", "strength": 900,
                    "source_entity_id": entity_id, "source_action_id": None,
                    "source_event_id": None,
                    "message": {"environmental_threat": "storm"},
                    "truth_status": "physical_evidence", "propagation_depth": 0,
                    "created_tick": tick, "expires_tick": tick + 4,
                }
                signal["affordances"] = default_affordances(signal)
                mutation["new_entities"][signal_id] = signal
                touched.append(signal_id)
            proposals.append({
                "proposal_family": "weather_process",
                "proposal_type": "weather_transition",
                "proposer_engine_id": self.engine_id,
                "proposer_engine_version": self.engine_version,
                "entity_id": entity_id,
                "causal_parent_event_ids": [weather["last_event_id"]] if weather.get("last_event_id") else [],
                "is_exogenous": not weather.get("last_event_id"),
                "requested_time": tick,
                "phase": self.phase,
                "engine_priority": self.engine_priority,
                "touched_scope": touched,
                "preconditions": [
                    {"entity_id": entity_id, "field": "cycle_index", "op": "eq", "value": weather.get("cycle_index", 0)},
                ],
                "mutation": mutation,
                "explanation": f"weather changed to {next_state['condition']}; forecast {next_state['forecast']}",
            })
            diagnostics[entity_id] = {"selected_goal": "WEATHER_TRANSITION", **next_state}
        return DomainOutput(proposals=proposals, diagnostics=diagnostics)
