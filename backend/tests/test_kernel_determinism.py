import ast
import copy
import sys
from pathlib import Path
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from scenarios import get_scenario


def _lineage_key(seed: str) -> str:
    return f"{seed}|{SCHEMA_VERSION}|{ENGINE_VERSION}"


def _canonical_event_hash(event: dict) -> str:
    event = dict(event)
    event.pop("run_id", None)
    return canonical_hash(event)


def _run_trace(seed: str, ticks: int, run_id: str, reverse_entity_order: bool = False) -> dict:
    scenario = get_scenario("basic_survival")
    lineage_key = _lineage_key(seed)
    world, entities, genesis_events, _, order_index = build_genesis(seed, scenario, lineage_key)
    if reverse_entity_order:
        entities = dict(reversed(list(entities.items())))

    events_by_tick = {0: list(genesis_events)}
    frame_hashes = [genesis_events[-1]["post_state_hash"]]
    rng = DeterministicRNG(seed)

    for tick in range(1, ticks + 1):
        accepted, _, order_index, _ = run_tick(
            run_id,
            entities,
            world["terrain"],
            tick,
            rng,
            order_index,
            lineage_key,
            scenario.enabled_domains,
        )
        events_by_tick[tick] = accepted
        frame_hashes.append(
            accepted[-1]["post_state_hash"] if accepted else frame_hashes[-1]
        )

    return {
        "entities": copy.deepcopy(entities),
        "events_by_tick": events_by_tick,
        "event_hashes": [
            _canonical_event_hash(event)
            for tick in range(ticks + 1)
            for event in events_by_tick[tick]
        ],
        "frame_hashes": frame_hashes,
        "lineage_key": lineage_key,
    }


class TestKernelReplayDeterminism(unittest.TestCase):
    def test_same_seed_reproduces_canonical_event_trace_and_hashes(self):
        first = _run_trace("kernel-replay-baseline", ticks=30, run_id="run-a")
        second = _run_trace("kernel-replay-baseline", ticks=30, run_id="run-b")

        self.assertEqual(first["event_hashes"], second["event_hashes"])
        self.assertEqual(first["frame_hashes"], second["frame_hashes"])
        self.assertEqual(first["entities"], second["entities"])

    def test_accepted_event_mutations_rebuild_each_frame_hash(self):
        trace = _run_trace("kernel-replay-rebuild", ticks=30, run_id="run-replay")
        rebuilt_entities = {}

        for tick, expected_hash in enumerate(trace["frame_hashes"]):
            for event in trace["events_by_tick"][tick]:
                apply_mutation(rebuilt_entities, event["mutation"])
            rebuilt_hash = canonical_hash(
                snapshot_for_hash(rebuilt_entities, tick, trace["lineage_key"])
            )
            self.assertEqual(rebuilt_hash, expected_hash)

        self.assertEqual(rebuilt_entities, trace["entities"])

    def test_reversed_loaded_entity_order_preserves_trace(self):
        standard = _run_trace("kernel-order-baseline", ticks=30, run_id="run-order")
        reversed_order = _run_trace(
            "kernel-order-baseline",
            ticks=30,
            run_id="run-order",
            reverse_entity_order=True,
        )

        self.assertEqual(standard["event_hashes"], reversed_order["event_hashes"])
        self.assertEqual(standard["frame_hashes"], reversed_order["frame_hashes"])
        self.assertEqual(standard["entities"], reversed_order["entities"])


class TestDomainDeterministicBoundary(unittest.TestCase):
    def test_domains_do_not_import_wall_clock_rng_or_storage_modules(self):
        forbidden_modules = {"datetime", "motor", "os", "pymongo", "random", "time", "uuid"}
        forbidden_from_modules = {"core.db"}

        for source_path in sorted((BACKEND_ROOT / "domains").glob("*.py")):
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
            imported_modules = set()
            imported_from_modules = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_modules.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_from_modules.add(node.module)

            self.assertFalse(
                forbidden_modules & imported_modules,
                f"{source_path.name} imports a forbidden nondeterministic module",
            )
            self.assertFalse(
                forbidden_from_modules & imported_from_modules,
                f"{source_path.name} imports Core storage directly",
            )
