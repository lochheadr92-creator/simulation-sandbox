"""
Backend tests for Simulation Sandbox kernel API.
Covers: run creation, state, step, causal inspection, events, rejections,
interventions (boost_need/spawn_tree/kill_entity), replay verify, determinism verify.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fallback read from frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.strip().split("=", 1)[1]
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def run(session):
    resp = session.post(f"{API}/runs", json={"seed": "TEST_seed_pytest", "scenario_id": "basic_survival"})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    return data


class TestScenarios:
    def test_get_scenarios(self, session):
        resp = session.get(f"{API}/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["scenarios"], list)
        assert any(s["id"] == "basic_survival" for s in data["scenarios"])


class TestRunLifecycle:
    def test_create_run(self, run):
        assert run["seed"] == "TEST_seed_pytest"
        assert run["scenario_id"] == "basic_survival"
        assert run["current_tick"] == 0

    def test_get_run(self, session, run):
        resp = session.get(f"{API}/runs/{run['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == run["id"]
        assert "terrain" not in data  # excluded

    def test_get_state_genesis(self, session, run):
        resp = session.get(f"{API}/runs/{run['id']}/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_tick"] == 0
        assert len(data["entities"]) > 0
        assert "terrain" in data
        assert data["time_phase"] in ("dawn", "day", "dusk", "night")

    def test_get_state_not_found(self, session):
        resp = session.get(f"{API}/runs/nonexistent-run-id/state")
        assert resp.status_code == 404

    def test_step_run(self, session, run):
        resp = session.post(f"{API}/runs/{run['id']}/step", json={"ticks": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["frames"]) == 1

        state = session.get(f"{API}/runs/{run['id']}/state").json()
        assert state["current_tick"] == 1

    def test_step_run_not_found(self, session):
        resp = session.post(f"{API}/runs/does-not-exist/step", json={"ticks": 1})
        assert resp.status_code == 404

    def test_step_multi_tick_then_advance_to_30(self, session, run):
        # advance to at least 30 ticks total for later determinism test
        state = session.get(f"{API}/runs/{run['id']}/state").json()
        remaining = 30 - state["current_tick"]
        while remaining > 0:
            batch = min(remaining, 25)
            resp = session.post(f"{API}/runs/{run['id']}/step", json={"ticks": batch})
            assert resp.status_code == 200
            remaining -= batch
        state = session.get(f"{API}/runs/{run['id']}/state").json()
        assert state["current_tick"] >= 30

    def test_pause_run(self, session, run):
        resp = session.post(f"{API}/runs/{run['id']}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"


class TestEventsAndRejections:
    def test_get_events(self, session, run):
        resp = session.get(f"{API}/runs/{run['id']}/events")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["events"], list)
        if data["events"]:
            ev = data["events"][0]
            assert "id" in ev and "event_type" in ev and "simulation_time" in ev

    def test_get_rejections(self, session, run):
        resp = session.get(f"{API}/runs/{run['id']}/rejections")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["rejections"], list)


class TestCausalInspection:
    def test_get_causal_valid_entity(self, session, run):
        state = session.get(f"{API}/runs/{run['id']}/state").json()
        person = next((e for e in state["entities"] if e["type"] == "person"), None)
        assert person is not None
        resp = session.get(f"{API}/runs/{run['id']}/entities/{person['id']}/causal")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity"]["id"] == person["id"]
        assert "causal_chain" in data
        assert "recent_accepted_events" in data
        assert "recent_rejected_proposals" in data
        # diagnostics should show real candidate scoring if present
        if data["diagnostics"]:
            assert "candidates" in data["diagnostics"]

    def test_get_causal_entity_not_found(self, session, run):
        resp = session.get(f"{API}/runs/{run['id']}/entities/nonexistent-entity/causal")
        assert resp.status_code == 404

    def test_get_causal_run_not_found(self, session):
        resp = session.get(f"{API}/runs/bad-run-id/entities/e1/causal")
        assert resp.status_code == 404


class TestInterventions:
    def test_boost_need_intervention(self, session, run):
        state = session.get(f"{API}/runs/{run['id']}/state").json()
        person = next((e for e in state["entities"] if e["type"] == "person" and e.get("alive", True)), None)
        assert person is not None
        before_hunger = person["hunger"]
        resp = session.post(f"{API}/runs/{run['id']}/interventions", json={
            "type": "boost_need", "payload": {"entity_id": person["id"], "field": "hunger", "delta": 300}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["accepted"]) >= 1
        assert data["accepted"][0]["event_type"] is not None

        state2 = session.get(f"{API}/runs/{run['id']}/state").json()
        person2 = next(e for e in state2["entities"] if e["id"] == person["id"])
        assert person2["hunger"] != before_hunger

    def test_spawn_tree_intervention(self, session, run):
        state = session.get(f"{API}/runs/{run['id']}/state").json()
        tree_count_before = sum(1 for e in state["entities"] if e["type"] == "tree")
        resp = session.post(f"{API}/runs/{run['id']}/interventions", json={
            "type": "spawn_tree", "payload": {"x": 3, "y": 3, "resource": 60}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["accepted"]) >= 1

        state2 = session.get(f"{API}/runs/{run['id']}/state").json()
        tree_count_after = sum(1 for e in state2["entities"] if e["type"] == "tree")
        assert tree_count_after == tree_count_before + 1

    def test_kill_entity_intervention(self, session, run):
        state = session.get(f"{API}/runs/{run['id']}/state").json()
        animal = next((e for e in state["entities"] if e["type"] == "animal" and e.get("alive", True)), None)
        assert animal is not None
        resp = session.post(f"{API}/runs/{run['id']}/interventions", json={
            "type": "kill_entity", "payload": {"entity_id": animal["id"]}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["accepted"]) >= 1

        state2 = session.get(f"{API}/runs/{run['id']}/state").json()
        animal2 = next(e for e in state2["entities"] if e["id"] == animal["id"])
        assert animal2["alive"] is False

    def test_invalid_intervention_type(self, session, run):
        resp = session.post(f"{API}/runs/{run['id']}/interventions", json={
            "type": "not_a_real_type", "payload": {}
        })
        assert resp.status_code == 400


class TestReplayAndDeterminism:
    def test_verify_replay(self, session, run):
        # advance a few more ticks after interventions
        session.post(f"{API}/runs/{run['id']}/step", json={"ticks": 5})
        resp = session.post(f"{API}/runs/{run['id']}/replay/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pass"

    def test_verify_determinism(self, session, run):
        resp = session.post(f"{API}/runs/{run['id']}/replay/determinism")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pass"
        assert "final_state_hash" in data

    def test_replay_run_not_found(self, session):
        resp = session.post(f"{API}/runs/bad-id/replay/verify")
        assert resp.status_code == 404

    def test_determinism_run_not_found(self, session):
        resp = session.post(f"{API}/runs/bad-id/replay/determinism")
        assert resp.status_code == 404
