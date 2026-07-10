"""Domain Engine Contract (Specification #28, right-sized for the MVP kernel).

A DomainEngine is a deterministic proposal generator. It receives a
read-only ActivationFrame and returns a DomainOutput (proposals +
diagnostics). It never mutates state, never touches storage, never calls
an LLM, and never reads the wall clock. All randomness comes from
`frame.rng` (Core-issued deterministic named streams).
"""


class ActivationFrame:
    def __init__(self, run_id, simulation_time, engine_version, phase, entities, terrain, due_entity_ids, rng):
        self.run_id = run_id
        self.simulation_time = simulation_time
        self.engine_version = engine_version
        self.phase = phase
        self.entities = entities
        self.terrain = terrain
        self.due_entity_ids = due_entity_ids
        self.rng = rng


class DomainOutput:
    def __init__(self, proposals=None, diagnostics=None, activation_requests=None):
        self.proposals = proposals or []
        self.diagnostics = diagnostics or {}
        self.activation_requests = activation_requests or []


class DomainEngine:
    engine_id = "base"
    engine_version = "0.0.0"
    engine_priority = 100
    phase = "agent"

    def activate(self, frame: ActivationFrame) -> DomainOutput:
        raise NotImplementedError
