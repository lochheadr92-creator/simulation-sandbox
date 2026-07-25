"""Pure simulation kernel: genesis + one deterministic tick. No DB access here
so this module can be unit-tested and replay-verified in isolation.

Phase 3: this kernel is scenario-agnostic. It never imports a concrete
domain engine and never branches on a scenario id - it only iterates
whichever `enabled_domains` list the caller supplies (sourced from a
Scenario, see scenarios/) and looks each one up in the generic domain
registry. This is what proves the Core supports arbitrary scenarios/domain
combinations without Core code changes."""
import copy

from core.constants import ENGINE_VERSION, is_night
from domains.base import ActivationFrame, DomainOutput
from domains.registry import DOMAIN_REGISTRY
from core.commit_pipeline import run_commit_frame
from world.generator import generate_world


def _frame(run_id, tick, entities_view, terrain, due_ids, rng, phase, night):
    f = ActivationFrame(run_id, tick, ENGINE_VERSION, phase, entities_view, terrain, due_ids, rng)
    f.night = night
    return f


def build_genesis(seed: str, scenario, lineage_key: str):
    """Creates the initial world and commits it as genesis accepted events (tick 0)."""
    world = generate_world(seed, scenario)
    entities = {}
    proposals = []
    counters = {}

    for spec in world["genesis_specs"]:
        spec = dict(spec)
        explicit_id = spec.pop("id", None)
        t = spec["type"]
        counters.setdefault(t, 0)
        eid = explicit_id or f"{t}-{counters[t]:03d}"
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


def run_tick(run_id: str, entities: dict, terrain: list, tick: int, rng, order_index_start: int,
             lineage_key: str, enabled_domains: list,
             valid_causal_parent_event_ids: set | None = None,
             entity_json_cache: dict | None = None,
             debug_assert_fragment_cache: bool = False):
    """Runs exactly one deterministic commit frame at `tick`. Mutates `entities` in place.

    `enabled_domains` is a generic list of domain_id strings (from the
    active Scenario) - the kernel has zero knowledge of what any of them
    mean; it only calls the Domain Engine Contract methods on whatever is
    registered under those ids.

    `entity_json_cache` / `debug_assert_fragment_cache`: passthrough to
    `run_commit_frame` (CORE-PERF-01 Slice B). `None` preserves prior
    behaviour exactly.
    """
    night = is_night(tick)
    entities_view = copy.deepcopy(entities)

    outputs = []
    for domain_id in enabled_domains:
        domain = DOMAIN_REGISTRY[domain_id]
        due_ids = domain.select_due_ids(entities_view, tick)
        frame = _frame(run_id, tick, entities_view, terrain, due_ids, rng, domain.phase, night)
        outputs.append(domain.activate(frame))

    frame_id = f"frame-{tick}"
    accepted, rejected, next_order = run_commit_frame(
        entities, outputs, tick, lineage_key, run_id, order_index_start, frame_id,
        valid_causal_parent_event_ids=valid_causal_parent_event_ids,
        entity_json_cache=entity_json_cache,
        debug_assert_fragment_cache=debug_assert_fragment_cache,
    )

    diagnostics = {}
    for out in outputs:
        diagnostics.update(out.diagnostics)
    return accepted, rejected, next_order, diagnostics
