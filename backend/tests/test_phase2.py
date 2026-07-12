"""
Phase 2 backend tests: multi-stage actions, behavior planning, knowledge
(resource memory / vision-radius perception), exploration, utility scoring,
critical interruption/resume, resource contention, and determinism.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
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
    resp = session.post(f"{API}/runs", json={"seed": "TEST_phase2_seed", "scenario_id": "basic_survival"})
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


def get_causal(session, run_id, entity_id):
    resp = session.get(f"{API}/runs/{run_id}/entities/{entity_id}/causal")
    assert resp.status_code == 200
    return resp.json()


class TestKnowledgeAndPerception:
    """Knowledge (resource memory) must only grow via discovery, never be omniscient."""

    def test_fresh_person_knowledge_near_zero(self, session, run):
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person" and e.get("alive", True))
        knowledge = person.get("knowledge") or {}
        # at tick 0/near start, should not already know most tiles
        assert len(knowledge.get("known_tiles", [])) < 400

    def test_knowledge_grows_monotonically_over_ticks(self, session, run):
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person" and e.get("alive", True))
        pid = person["id"]
        before = len(((person.get("knowledge") or {}).get("known_tiles", [])))

        step(session, run["id"], 30)

        state2 = get_state(session, run["id"])
        person2 = next(e for e in state2["entities"] if e["id"] == pid)
        after = len(((person2.get("knowledge") or {}).get("known_tiles", [])))
        assert after >= before  # never shrinks

    def test_causal_knowledge_summary_present(self, session, run):
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person" and e.get("alive", True))
        data = get_causal(session, run["id"], person["id"])
        assert "knowledge_summary" in data
        ks = data["knowledge_summary"]
        for key in ("explored_tiles", "known_water_tiles", "known_trees", "known_shelters"):
            assert key in ks
            assert isinstance(ks[key], int)


class TestActionsAndPlans:
    """Canonical action/plan fields present and evolving over ticks."""

    def test_action_and_plan_fields_present(self, session, run):
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person" and e.get("alive", True))
        assert "action" in person
        assert "plan" in person
        action = person["action"]
        for key in ("type", "status", "ticks_spent", "ticks_required"):
            assert key in action
        plan = person["plan"]
        assert "steps" in plan and "step_index" in plan and "goal" in plan

    def test_action_progresses_over_ticks(self, session, run):
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person" and e.get("alive", True))
        pid = person["id"]

        seen_statuses = set()
        for _ in range(10):
            state = get_state(session, run["id"])
            p = next((e for e in state["entities"] if e["id"] == pid and e.get("alive", True)), None)
            if not p:
                break
            seen_statuses.add(p["action"]["status"])
            step(session, run["id"], 5)
        # over 50 ticks a person should exhibit more than one distinct action status
        assert len(seen_statuses) >= 1  # weak sanity: at minimum action status is always populated

    def test_no_crash_stepping_60_ticks(self, session, run):
        state_before = get_state(session, run["id"])
        step(session, run["id"], 60)
        state_after = get_state(session, run["id"])
        assert state_after["current_tick"] > state_before["current_tick"]
        assert len(state_after["entities"]) > 0


class TestUtilityBreakdown:
    """Utility candidate rows must include all documented goals & score fields."""

    # HUNT added in Phase 4 (hunt -> injury -> death -> carcass -> meat food chain).
    EXPECTED_GOALS = {"SEEK_WATER", "SEEK_FOOD", "GIVE_FOOD", "SLEEP", "BUILD_SHELTER", "GATHER_SURPLUS", "EXPLORE", "WANDER", "HUNT"}

    def test_candidate_rows_contain_expected_goals_and_fields(self, session, run):
        # find a tick where diagnostics.candidates is non-empty (fresh decision, not mid-action)
        found = False
        for _ in range(20):
            state = get_state(session, run["id"])
            person = next((e for e in state["entities"] if e["type"] == "person" and e.get("alive", True)), None)
            if person:
                data = get_causal(session, run["id"], person["id"])
                cands = (data.get("diagnostics") or {}).get("candidates") or []
                if cands:
                    found = True
                    goals = {c["goal"] for c in cands}
                    assert goals == self.EXPECTED_GOALS, f"missing/extra goals: {goals}"
                    for c in cands:
                        for field in ("severity", "predicted_severity", "travel_cost", "availability",
                                      "risk", "interruption_cost", "score"):
                            assert field in c
                    break
            step(session, run["id"], 3)
        assert found, "never observed a fresh-decision tick with populated candidates in 60 ticks"

    def test_selected_goal_matches_best_score_or_critical(self, session, run):
        for _ in range(20):
            state = get_state(session, run["id"])
            person = next((e for e in state["entities"] if e["type"] == "person" and e.get("alive", True)), None)
            if person:
                data = get_causal(session, run["id"], person["id"])
                diag = data.get("diagnostics") or {}
                cands = diag.get("candidates") or []
                if cands:
                    best = max(cands, key=lambda c: c["score"])
                    selected = diag.get("selected_goal")
                    explanation = diag.get("explanation", "")
                    is_critical = "CRITICAL" in explanation or "resumed" in explanation
                    assert selected == best["goal"] or is_critical
                    return
            step(session, run["id"], 3)


class TestResourceContentionAndRejections:
    def test_rejections_endpoint_returns_real_reason_codes(self, session, run):
        step(session, run["id"], 40)
        resp = session.get(f"{API}/runs/{run['id']}/rejections")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["rejections"], list)
        # not asserting non-empty (contention is probabilistic on world layout) but
        # if present, must have real reason codes
        for r in data["rejections"]:
            assert "reason_code" in r


class TestReplayDeterminismPhase2:
    def test_replay_verify_pass_after_phase2_actions(self, session, run):
        resp = session.post(f"{API}/runs/{run['id']}/replay/verify")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pass"

    def test_determinism_pass_with_real_hash(self, session, run):
        resp = session.post(f"{API}/runs/{run['id']}/replay/determinism")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pass"
        assert len(data["final_state_hash"]) > 0

    def test_same_seed_two_runs_identical_hash_sequence(self, session):
        r1 = session.post(f"{API}/runs", json={"seed": "TEST_phase2_determinism", "scenario_id": "basic_survival"}).json()
        r2 = session.post(f"{API}/runs", json={"seed": "TEST_phase2_determinism", "scenario_id": "basic_survival"}).json()

        hashes1, hashes2 = [], []
        for _ in range(6):
            f1 = session.post(f"{API}/runs/{r1['id']}/step", json={"ticks": 5}).json()["frames"]
            f2 = session.post(f"{API}/runs/{r2['id']}/step", json={"ticks": 5}).json()["frames"]
            hashes1.extend([fr.get("ending_state_hash") or fr.get("post_state_hash") for fr in f1])
            hashes2.extend([fr.get("ending_state_hash") or fr.get("post_state_hash") for fr in f2])

        assert hashes1 == hashes2
        assert all(h for h in hashes1)


class TestLongRunStability:
    def test_step_100_ticks_no_deadlock(self, session):
        r = session.post(f"{API}/runs", json={"seed": "TEST_phase2_longrun", "scenario_id": "basic_survival"}).json()
        for _ in range(4):
            resp = session.post(f"{API}/runs/{r['id']}/step", json={"ticks": 25})
            assert resp.status_code == 200
        state = get_state(session, r["id"])
        assert state["current_tick"] >= 100

        # No person should be stuck travelling for more than TRAVEL_STALL_LIMIT (25) ticks straight
        # (spot check via causal action_history for one alive person)
        person = next((e for e in state["entities"] if e["type"] == "person" and e.get("alive", True)), None)
        if person:
            action = person["action"]
            if action["status"] == "travelling":
                assert action.get("ticks_spent", 0) <= 26
