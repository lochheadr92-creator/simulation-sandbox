"""
Phase 3 backend tests: architectural proof that the Core kernel is
scenario/domain-agnostic. Verifies both scenarios (Wilderness Survival,
Desert Oasis) run on the exact same Core, both replay correctly, both
pass deterministic verification, and no scenario-specific logic leaked
into the Core.
"""
import inspect
import pytest
import requests

from tests.helpers.env import SKIP_REASON, resolve_backend_base_url

# NOTE: no module-level pytestmark here - TestCoreDomainAgnosticism is pure
# static analysis and must run with no server; HTTP classes are marked
# `integration` individually.

# Resolved lazily by the _backend_api fixture - never at module import time.
BASE_URL = None
API = None

SCENARIO_IDS = ["basic_survival", "desert_oasis"]


@pytest.fixture(scope="module")
def _backend_api():
    global BASE_URL, API
    base = resolve_backend_base_url()
    if not base:
        pytest.skip(SKIP_REASON)
    BASE_URL, API = base, f"{base}/api"


@pytest.fixture(scope="module")
def session(_backend_api):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def create_run(session, seed, scenario_id):
    resp = session.post(f"{API}/runs", json={"seed": seed, "scenario_id": scenario_id})
    assert resp.status_code == 200
    return resp.json()


def step(session, run_id, ticks):
    resp = session.post(f"{API}/runs/{run_id}/step", json={"ticks": ticks})
    assert resp.status_code == 200
    return resp.json()


def get_state(session, run_id):
    resp = session.get(f"{API}/runs/{run_id}/state")
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.integration
class TestScenarioRegistry:
    def test_both_scenarios_listed(self, session):
        resp = session.get(f"{API}/scenarios")
        assert resp.status_code == 200
        ids = {s["id"] for s in resp.json()["scenarios"]}
        assert set(SCENARIO_IDS) <= ids

    def test_unknown_scenario_id_rejected(self, session):
        resp = session.post(f"{API}/runs", json={"seed": "x", "scenario_id": "not_a_real_scenario"})
        assert resp.status_code == 400

    def test_desert_oasis_has_no_animal_domain_enabled(self, session):
        resp = session.get(f"{API}/scenarios")
        scenarios = {s["id"]: s for s in resp.json()["scenarios"]}
        assert "animal" not in scenarios["desert_oasis"]["enabled_domains"]
        assert "animal" in scenarios["basic_survival"]["enabled_domains"]


@pytest.mark.integration
class TestBothScenariosRunOnSameCore:
    @pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
    def test_create_and_step_no_crash(self, session, scenario_id):
        run = create_run(session, f"TEST_phase3_{scenario_id}", scenario_id)
        step(session, run["id"], 20)
        state = get_state(session, run["id"])
        assert state["current_tick"] == 20
        assert state["scenario_id"] == scenario_id
        assert len(state["entities"]) > 0

    def test_desert_oasis_spawns_no_animal_entities(self, session):
        run = create_run(session, "TEST_phase3_no_animals", "desert_oasis")
        state = get_state(session, run["id"])
        assert not any(e["type"] == "animal" for e in state["entities"])
        assert any(e["type"] == "person" for e in state["entities"])

    def test_desert_oasis_ground_terrain_is_sand(self, session):
        run = create_run(session, "TEST_phase3_terrain", "desert_oasis")
        state = get_state(session, run["id"])
        flat = [t for row in state["terrain"] for t in row]
        assert "sand" in flat
        assert "grass" not in flat

    def test_wilderness_survival_ground_terrain_is_grass(self, session):
        run = create_run(session, "TEST_phase3_terrain2", "basic_survival")
        state = get_state(session, run["id"])
        flat = [t for row in state["terrain"] for t in row]
        assert "grass" in flat
        assert "sand" not in flat


@pytest.mark.integration
class TestReplayAndDeterminismBothScenarios:
    @pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
    def test_replay_verify_pass(self, session, scenario_id):
        run = create_run(session, f"TEST_phase3_replay_{scenario_id}", scenario_id)
        step(session, run["id"], 25)
        resp = session.post(f"{API}/runs/{run['id']}/replay/verify")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pass"

    @pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
    def test_determinism_verify_pass(self, session, scenario_id):
        run = create_run(session, f"TEST_phase3_determinism_{scenario_id}", scenario_id)
        step(session, run["id"], 25)
        resp = session.post(f"{API}/runs/{run['id']}/replay/determinism")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pass"
        assert len(data["final_state_hash"]) > 0

    @pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
    def test_same_seed_two_runs_identical_hash_sequence(self, session, scenario_id):
        seed = f"TEST_phase3_dual_{scenario_id}"
        r1 = create_run(session, seed, scenario_id)
        r2 = create_run(session, seed, scenario_id)
        hashes1, hashes2 = [], []
        for _ in range(4):
            f1 = step(session, r1["id"], 5)["frames"]
            f2 = step(session, r2["id"], 5)["frames"]
            hashes1.extend([f["ending_state_hash"] for f in f1])
            hashes2.extend([f["ending_state_hash"] for f in f2])
        assert hashes1 == hashes2
        assert all(hashes1)


class TestCoreDomainAgnosticism:
    """Static-code proof (Verification Doctrine #32 style): the Core kernel
    must never reference a concrete entity type or scenario id literal -
    it only iterates a generic `enabled_domains` list supplied by the
    caller and looks each id up in the domain registry."""

    def test_kernel_has_no_hardcoded_entity_type_literals(self):
        from core import kernel
        source = inspect.getsource(kernel)
        for literal in ('"person"', '"animal"', '"tree"', "'person'", "'animal'", "'tree'"):
            assert literal not in source, f"kernel.py must not hardcode entity type {literal}"

    def test_kernel_has_no_hardcoded_scenario_id_literals(self):
        from core import kernel
        source = inspect.getsource(kernel)
        for scenario_id in SCENARIO_IDS:
            assert scenario_id not in source, f"kernel.py must not hardcode scenario id {scenario_id}"

    def test_kernel_does_not_import_concrete_domain_classes(self):
        from core import kernel
        source = inspect.getsource(kernel)
        for concrete in ("PeopleDomain", "AnimalDomain", "EcologyDomain"):
            assert concrete not in source, f"kernel.py must not import concrete domain class {concrete}"

    def test_kernel_run_tick_accepts_generic_enabled_domains_param(self):
        from core.kernel import run_tick
        params = list(inspect.signature(run_tick).parameters)
        assert "enabled_domains" in params

    def test_commit_pipeline_hashing_mutations_rng_untouched_by_scenarios(self):
        """These Core modules must never import the scenarios package -
        proves scenario data cannot leak into the deterministic commit/
        hashing layer."""
        import core.commit_pipeline as cp
        import core.hashing as hashing
        import core.mutations as mutations
        import core.rng as rng
        for mod in (cp, hashing, mutations, rng):
            source = inspect.getsource(mod)
            assert "scenarios" not in source
            assert "scenario_id" not in source
