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


# GENESIS SPAWN INDEX.
# Every genesis spawn proposal used to carry the same engine_priority (-1). In
# `order_key` (core/commit_pipeline.py) that means all of
# (requested_time=0, phase="environment", engine_priority) tie, so commit order
# fell through to `content_hash` -- CONTENT decided the order. `order_index` is
# then baked into the event id `evt-{tick}-{order}-{hash8}`, and
# `_stamp_new_entity_provenance` writes that id onto every entity as
# creation_event_id / last_event_id. Net effect: editing one person's age
# relocated an unrelated TREE's provenance ids. Measured: with only
# person_age_range changed, animal-threat moved evt-0-12-3794366e ->
# evt-0-7-3794366e -- identical hash8, different slot.
#
# Giving each spec its position as engine_priority makes genesis order
# POSITIONAL, so an entity whose spec did not change keeps its exact event id.
# Because `order_index` starts at 0 for the genesis frame and every genesis
# proposal is accepted (exogenous, no preconditions, own scope), order_index
# then equals the spec position exactly -- pinned by test.
#
# The base keeps genesis numerically far below every domain priority (lowest is
# weather at -2), so the field's "lower commits first" meaning still reads
# correctly. This cannot reorder genesis against any domain in any case:
# build_genesis constructs the frame's entire proposal list itself, so genesis
# proposals are never in a frame with anything else.
#
# WHAT THIS DOES NOT FIX: an EDITED entity's own spawn id still changes,
# because hash8 is a prefix of its content hash. That channel is
# CORE-INTEGRITY-004's and is remediated in 004's own stage. This also
# stabilises order against CONTENT changes only, not COMPOSITION changes --
# appending a spec is free, inserting one mid-list renumbers everything after.
# See memory/CORE-INTEGRITY-004-COMMIT-ORDER-CONTENT-SENSITIVITY.md.
GENESIS_SPAWN_PRIORITY_BASE = -1_000_000


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

    for spawn_index, spec in enumerate(world["genesis_specs"]):
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
            # Positional, not uniform -- see GENESIS_SPAWN_PRIORITY_BASE above.
            "engine_priority": GENESIS_SPAWN_PRIORITY_BASE + spawn_index,
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
