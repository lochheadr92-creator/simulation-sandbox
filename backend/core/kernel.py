"""Pure simulation kernel: genesis + one deterministic tick. No DB access here
so this module can be unit-tested and replay-verified in isolation."""
import copy

from core.constants import REGROWTH_INTERVAL, ENGINE_VERSION, is_night
from domains.base import ActivationFrame, DomainOutput
from domains.people_domain import PeopleDomain
from domains.animal_domain import AnimalDomain
from domains.ecology_domain import EcologyDomain
from core.commit_pipeline import run_commit_frame
from world.generator import generate_world

ECOLOGY = EcologyDomain()
PEOPLE = PeopleDomain()
ANIMAL = AnimalDomain()


def _frame(run_id, tick, entities_view, terrain, due_ids, rng, phase, night):
    f = ActivationFrame(run_id, tick, ENGINE_VERSION, phase, entities_view, terrain, due_ids, rng)
    f.night = night
    return f


def build_genesis(seed: str, scenario_id: str, lineage_key: str):
    """Creates the initial world and commits it as genesis accepted events (tick 0)."""
    world = generate_world(seed, scenario_id)
    entities = {}
    proposals = []
    counters = {"tree": 0, "person": 0, "animal": 0}

    for spec in world["genesis_specs"]:
        t = spec["type"]
        eid = f"{t}-{counters[t]:03d}"
        counters[t] += 1
        proposals.append({
            "proposal_family": "genesis",
            "proposal_type": "spawn_entity",
            "proposer_engine_id": "world_generator",
            "proposer_engine_version": ENGINE_VERSION,
            "entity_id": eid,
            "causal_parent_event_ids": [],
            "is_exogenous": True,
            "requested_time": 0,
            "phase": "environment",
            "engine_priority": -1,
            "touched_scope": [eid],
            "preconditions": [],
            "mutation": {"entity_updates": {}, "new_entities": {eid: dict(spec)}},
            "explanation": f"genesis spawn of {t} at {spec['position']}",
        })

    accepted, rejected, next_order = run_commit_frame(
        entities, [DomainOutput(proposals=proposals)], 0, lineage_key, "genesis", 0, "frame-genesis",
    )
    return world, entities, accepted, rejected, next_order


def run_tick(run_id: str, entities: dict, terrain: list, tick: int, rng, order_index_start: int, lineage_key: str):
    """Runs exactly one deterministic commit frame at `tick`. Mutates `entities` in place."""
    night = is_night(tick)

    due_trees = [eid for eid, e in entities.items() if e["type"] == "tree" and tick % REGROWTH_INTERVAL == 0]
    people_ids = [eid for eid, e in entities.items() if e["type"] == "person" and e.get("alive", True)]
    animal_ids = [eid for eid, e in entities.items() if e["type"] == "animal" and e.get("alive", True)]

    entities_view = copy.deepcopy(entities)

    eco_out = ECOLOGY.activate(_frame(run_id, tick, entities_view, terrain, due_trees, rng, "environment", night))
    people_out = PEOPLE.activate(_frame(run_id, tick, entities_view, terrain, people_ids, rng, "agent", night))
    animal_out = ANIMAL.activate(_frame(run_id, tick, entities_view, terrain, animal_ids, rng, "agent", night))

    frame_id = f"frame-{tick}"
    accepted, rejected, next_order = run_commit_frame(
        entities, [eco_out, people_out, animal_out], tick, lineage_key, run_id, order_index_start, frame_id,
    )

    diagnostics = {}
    diagnostics.update(eco_out.diagnostics)
    diagnostics.update(people_out.diagnostics)
    diagnostics.update(animal_out.diagnostics)
    return accepted, rejected, next_order, diagnostics
