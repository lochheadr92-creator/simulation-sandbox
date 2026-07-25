import ast
import copy
import sys
from pathlib import Path
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.commit_pipeline import run_commit_frame
from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.hashing import canonical_hash
from core.kernel import build_genesis, run_tick
from core.mutations import apply_mutation, snapshot_for_hash
from core.rng import DeterministicRNG
from domains.base import DomainOutput
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


class TestRejectionIdCollision(unittest.TestCase):
    """KIMI review, 2026-07-25: _reject's id (commit_pipeline.py) had no
    order_index or sequence component, so two structurally identical
    proposals rejected in the same frame (same tick, content_hash prefix,
    entity_id) collided on id. uq_run_rejection_id (core/db.py) is unique on
    (run_id, id), so before this fix the second insert would fail and a
    retry would reproduce the identical collision, wedging the run
    permanently. Reproduces the collision directly against
    run_commit_frame (no DB needed -- the id collision itself, independent
    of the unique index, is the reproducible part) and proves both
    rejections now land with distinct ids and the run proceeds."""

    @staticmethod
    def _duplicate_missing_causal_parent_proposal():
        return {
            "proposal_family": "test", "proposal_type": "noop",
            "proposer_engine_id": "test", "entity_id": "person-a",
            "causal_parent_event_ids": [], "is_exogenous": False,
            "requested_time": 1, "phase": "agent",
            "touched_scope": ["person-a"], "preconditions": [],
            "mutation": {},
        }

    def test_two_identical_proposals_rejected_in_one_frame_get_distinct_ids(self):
        entities = {"person-a": {"type": "person", "position": {"x": 1, "y": 1}}}
        proposals = [
            self._duplicate_missing_causal_parent_proposal(),
            self._duplicate_missing_causal_parent_proposal(),
        ]

        accepted, rejected, _order = run_commit_frame(
            entities, [DomainOutput(proposals=proposals)],
            1, "lineage-x", "run", 0, "frame-1",
        )

        self.assertFalse(accepted)
        self.assertEqual(len(rejected), 2)
        self.assertEqual(rejected[0]["reason_code"], "causality.missing_parent")
        self.assertEqual(rejected[1]["reason_code"], "causality.missing_parent")

        ids = [row["id"] for row in rejected]
        self.assertEqual(len(set(ids)), 2, "rejection ids collided -- this is the wedge bug")
        # The common, non-colliding case is unchanged: the first rejection
        # keeps its plain id; only the second, colliding one is suffixed.
        self.assertEqual(ids[1], ids[0] + "-2")

        # This is what "the run now proceeds" means concretely: a caller
        # that would insert these into core.db's uq_run_rejection_id unique
        # index (run_id, id) no longer sees a duplicate-key collision on the
        # second row, so the same-tick retry loop that would previously
        # reproduce the identical collision every time never triggers.
        self.assertEqual(len({(row["id"],) for row in rejected}), 2)

    def test_three_identical_proposals_rejected_in_one_frame_all_distinct(self):
        entities = {"person-a": {"type": "person", "position": {"x": 1, "y": 1}}}
        proposals = [self._duplicate_missing_causal_parent_proposal() for _ in range(3)]

        _accepted, rejected, _order = run_commit_frame(
            entities, [DomainOutput(proposals=proposals)],
            1, "lineage-x", "run", 0, "frame-1",
        )

        ids = [row["id"] for row in rejected]
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(ids[2], ids[0] + "-3")

    def test_non_colliding_rejections_keep_their_existing_id_shape(self):
        """Direct proof this fix changes nothing for the common case: a
        single rejection's id is byte-identical to the pre-fix format."""
        entities = {"person-a": {"type": "person", "position": {"x": 1, "y": 1}}}
        proposal = self._duplicate_missing_causal_parent_proposal()

        _accepted, rejected, _order = run_commit_frame(
            entities, [DomainOutput(proposals=[proposal])],
            1, "lineage-x", "run", 0, "frame-1",
        )

        self.assertEqual(len(rejected), 1)
        # Same shape _reject always produced: rej-{tick}-{content_hash[:10]}-{entity_id}
        self.assertRegex(rejected[0]["id"], r"^rej-1-[0-9a-f]{10}-person-a$")
