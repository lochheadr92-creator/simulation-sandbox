"""Regression: replay + determinism verification across event-less frames.

History (2026-07-14 assessment, Task B): `verify_replay` recomputed a
tick-bound snapshot hash for every frame while `step_run` carried the
previous hash forward on ticks that accepted zero events, so any fully
empty frame - reachable after total population death - false-failed replay
verification even though determinism verification passed. The engine fixed
this with hash-policy versioning (`tick-bound-v1` recomputes every frame;
`legacy-carry-v0` carries the prior hash on empty frames), but nothing
pinned the guarantee at the API boundary. This test does: a run stepped
well past total extinction must pass BOTH verifiers, and the stepped window
must actually contain at least one zero-event frame so the regression path
is genuinely exercised.
"""
import pytest
import requests

from tests.helpers.env import SKIP_REASON, resolve_backend_base_url

pytestmark = pytest.mark.integration

# Resolved lazily by the _backend_api fixture - never at module import time.
BASE_URL = None
API = None


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


def test_replay_and_determinism_pass_after_total_extinction(session):
    resp = session.post(f"{API}/runs", json={
        "seed": "TEST_extinction_replay", "scenario_id": "basic_survival",
    })
    assert resp.status_code == 200
    run_id = resp.json()["id"]

    resp = session.post(f"{API}/runs/{run_id}/step", json={"ticks": 3})
    assert resp.status_code == 200

    state = session.get(f"{API}/runs/{run_id}/state").json()
    victims = [e for e in state["entities"]
               if e["type"] in ("person", "animal") and e.get("alive", True)]
    assert victims, "scenario must start with living people/animals"
    for entity in victims:
        resp = session.post(f"{API}/runs/{run_id}/interventions", json={
            "type": "kill_entity", "payload": {"entity_id": entity["id"]},
        })
        assert resp.status_code == 200, f"kill_entity failed for {entity['id']}: {resp.text}"

    state = session.get(f"{API}/runs/{run_id}/state").json()
    assert not any(
        e.get("alive", True) for e in state["entities"]
        if e["type"] in ("person", "animal")
    ), "extinction must be total before stepping"

    # 10 ticks past extinction: ecology regrowth fires at most every 5 ticks,
    # so at least one tick is guaranteed to accept zero events (>=7 needed;
    # 10 gives margin without relying on regrowth cadence details).
    resp = session.post(f"{API}/runs/{run_id}/step", json={"ticks": 10})
    assert resp.status_code == 200
    frames = resp.json()["frames"]
    assert any(frame["accepted_count"] == 0 for frame in frames), (
        "no post-extinction tick accepted zero events - the empty-frame "
        f"regression path was not exercised: {frames}"
    )

    verify = session.post(f"{API}/runs/{run_id}/replay/verify")
    assert verify.status_code == 200
    assert verify.json()["status"] == "pass", verify.json()

    determinism = session.post(f"{API}/runs/{run_id}/replay/determinism")
    assert determinism.status_code == 200
    assert determinism.json()["status"] == "pass", determinism.json()
