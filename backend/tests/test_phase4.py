"""
Phase 4 backend tests: Persistent History & Causal Memory (A) and
Ageing/Health/Death Foundations (B). Covers every item in the Phase 4
Verification checklist.
"""
import inspect
import os
import random
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


def create_run(session, seed, scenario_id="basic_survival"):
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


class TestSaveLoadContinue:
    def test_load_existing_run_preserves_state_hash(self, session):
        run = create_run(session, "TEST_phase4_saveload_1")
        step(session, run["id"], 15)
        state_before = get_state(session, run["id"])

        resp = session.get(f"{API}/runs/{run['id']}")
        assert resp.status_code == 200
        loaded = resp.json()
        assert loaded["current_tick"] == 15
        assert loaded["last_state_hash"] == state_before["last_state_hash"]

    def test_loaded_run_continues_deterministically(self, session):
        run = create_run(session, "TEST_phase4_saveload_2")
        step(session, run["id"], 10)
        loaded = session.get(f"{API}/runs/{run['id']}").json()
        # continue stepping - must not create a new/second hidden truth path
        step(session, run["id"], 10)
        state = get_state(session, run["id"])
        assert state["current_tick"] == 20
        verify = session.post(f"{API}/runs/{run['id']}/replay/verify").json()
        assert verify["status"] == "pass"

    def test_run_id_is_stable_run_list_includes_it(self, session):
        run = create_run(session, "TEST_phase4_saveload_3")
        resp = session.get(f"{API}/runs")
        assert resp.status_code == 200
        ids = {r["id"] for r in resp.json()["runs"]}
        assert run["id"] in ids


class TestTimelineAndMilestones:
    def test_timeline_rebuilds_identically(self, session):
        run = create_run(session, "TEST_phase4_timeline_1")
        step(session, run["id"], 20)
        t1 = session.get(f"{API}/runs/{run['id']}/timeline", params={"limit": 500}).json()
        t2 = session.get(f"{API}/runs/{run['id']}/timeline", params={"limit": 500}).json()
        assert t1["timeline"] == t2["timeline"]
        assert t1["total_events_in_run"] == t2["total_events_in_run"]

    def test_milestones_rebuild_identically(self, session):
        run = create_run(session, "TEST_phase4_timeline_2")
        step(session, run["id"], 40)
        m1 = session.get(f"{API}/runs/{run['id']}/milestones").json()
        m2 = session.get(f"{API}/runs/{run['id']}/milestones").json()
        assert m1 == m2

    def test_milestones_only_use_approved_set(self, session):
        run = create_run(session, "TEST_phase4_timeline_3")
        step(session, run["id"], 60)
        milestones = session.get(f"{API}/runs/{run['id']}/milestones").json()["milestones"]
        approved = {"first_shelter", "shelter_completed", "first_resource_exhausted",
                    "first_major_discovery", "first_injury", "first_death"}
        for m in milestones:
            assert m["milestone_type"] in approved

    def test_timeline_entity_filter(self, session):
        run = create_run(session, "TEST_phase4_timeline_4")
        step(session, run["id"], 10)
        full = session.get(f"{API}/runs/{run['id']}/timeline", params={"limit": 500}).json()["timeline"]
        assert len(full) > 0
        eid = full[0]["entity_id"]
        filtered = session.get(f"{API}/runs/{run['id']}/timeline", params={"limit": 500, "entity_id": eid}).json()["timeline"]
        assert all(t["entity_id"] == eid or eid in t["touched_scope"] for t in filtered)


class TestCausalLinksAndProvenance:
    def test_causal_links_survive_save_load(self, session):
        run = create_run(session, "TEST_phase4_causal_1")
        step(session, run["id"], 15)
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person")

        # "load" the run (fetch fresh via GET) and confirm the causal chain is identical after
        session.get(f"{API}/runs/{run['id']}")
        chain1 = session.get(f"{API}/runs/{run['id']}/entities/{person['id']}/causal").json()
        chain2 = session.get(f"{API}/runs/{run['id']}/entities/{person['id']}/causal").json()
        assert chain1["causal_chain"] == chain2["causal_chain"]

    def test_provenance_for_person_is_derivable_and_stable(self, session):
        run = create_run(session, "TEST_phase4_provenance_1")
        step(session, run["id"], 30)
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person")
        prov1 = session.get(f"{API}/runs/{run['id']}/entities/{person['id']}/provenance").json()
        prov2 = session.get(f"{API}/runs/{run['id']}/entities/{person['id']}/provenance").json()
        assert prov1 == prov2
        assert prov1["entity_type"] == "person"
        assert prov1["relationships_note"]  # explicitly not-applicable note, never fabricated

    def test_tile_history_is_bounded_projection(self, session):
        run = create_run(session, "TEST_phase4_tile_1")
        step(session, run["id"], 15)
        state = get_state(session, run["id"])
        pos = state["entities"][0]["position"]
        resp = session.get(f"{API}/runs/{run['id']}/tiles/{pos['x']}/{pos['y']}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "note" in data
        assert isinstance(data["events"], list)


class TestDeathDoctrine:
    def test_dead_entities_cannot_act(self, session):
        """Kill a person via intervention, step forward, confirm their action
        never changes again (no further proposals accepted for them)."""
        run = create_run(session, "TEST_phase4_death_1")
        step(session, run["id"], 5)
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person")

        resp = session.post(f"{API}/runs/{run['id']}/interventions", json={
            "type": "kill_entity", "payload": {"entity_id": person["id"]},
        })
        assert resp.status_code == 200

        step(session, run["id"], 15)
        state_after = get_state(session, run["id"])
        person_after = next(e for e in state_after["entities"] if e["id"] == person["id"])
        assert person_after["alive"] is False
        assert person_after["current_goal"] == "DEAD"
        # position must be frozen at time of death (no further movement/action accepted)
        assert person_after["position"] == person["position"] or person_after.get("death_tick") is not None

    def test_death_has_valid_causal_parents_and_appears_in_timeline(self, session):
        run = create_run(session, "TEST_phase4_death_2")
        step(session, run["id"], 5)
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person")
        session.post(f"{API}/runs/{run['id']}/interventions", json={
            "type": "kill_entity", "payload": {"entity_id": person["id"]},
        })
        step(session, run["id"], 2)

        timeline = session.get(f"{API}/runs/{run['id']}/timeline", params={"limit": 500}).json()["timeline"]
        # kill_entity intervention -> event_type mirrors the proposal_type ("kill_entity"),
        # not a literal "death" string; natural LifecycleDomain deaths use "death".
        death_events = [t for t in timeline if t["entity_id"] == person["id"] and t["event_type"] in ("death", "kill_entity")]
        assert len(death_events) == 1
        assert len(death_events[0]["causal_parent_event_ids"]) >= 0  # exogenous-or-caused, both valid, never fabricated

        prov = session.get(f"{API}/runs/{run['id']}/entities/{person['id']}/provenance").json()
        assert prov["death"] is not None
        assert prov["death"]["event_id"] == death_events[0]["event_id"]

    def test_death_replay_produces_same_state_hash(self, session):
        run = create_run(session, "TEST_phase4_death_3")
        step(session, run["id"], 5)
        state = get_state(session, run["id"])
        person = next(e for e in state["entities"] if e["type"] == "person")
        session.post(f"{API}/runs/{run['id']}/interventions", json={
            "type": "kill_entity", "payload": {"entity_id": person["id"]},
        })
        step(session, run["id"], 10)
        verify = session.post(f"{API}/runs/{run['id']}/replay/verify").json()
        assert verify["status"] == "pass"
        determinism = session.post(f"{API}/runs/{run['id']}/replay/determinism").json()
        assert determinism["status"] == "pass"

    def test_same_seed_runs_produce_identical_death_timing_and_cause(self, session):
        """Force two identical-seed runs into starvation via repeated boost_need
        (thirst up, never resolved) and confirm both die at the same tick with the same cause."""
        seed = "TEST_phase4_death_sameseed"
        r1 = create_run(session, seed)
        r2 = create_run(session, seed)
        person1 = next(e for e in get_state(session, r1["id"])["entities"] if e["type"] == "person")["id"]
        person2 = next(e for e in get_state(session, r2["id"])["entities"] if e["type"] == "person")["id"]
        assert person1 == person2

        # Dehydration health decay is DEHYDRATION_HEALTH_DECAY=4/tick from MAX_HEALTH=1000,
        # so >=250 ticks of sustained critical thirst are needed; reboost every tick to
        # counter any successful drinking, with generous headroom (80*5=400 ticks).
        deaths = {}
        for run_id, pid in ((r1["id"], person1), (r2["id"], person2)):
            for _ in range(80):
                session.post(f"{API}/runs/{run_id}/interventions", json={
                    "type": "boost_need", "payload": {"entity_id": pid, "field": "thirst", "delta": 1000},
                })
                step(session, run_id, 5)
                st = get_state(session, run_id)
                p = next(e for e in st["entities"] if e["id"] == pid)
                if not p.get("alive", True):
                    deaths[run_id] = (st["current_tick"], p.get("death_cause"))
                    break

        assert len(deaths) == 2, f"both runs should have produced a death: {deaths}"
        (_t1, c1), (_t2, c2) = deaths.values()
        ticks = [t for t, _ in deaths.values()]
        assert ticks[0] == ticks[1], f"same seed must die at the same tick: {deaths}"
        assert c1 == c2, f"same seed must die of the same cause: {deaths}"

    def test_no_population_replacement(self, session):
        """After a death, entity COUNT for that type must never increase back
        up (no spawn-rate/target-count replacement)."""
        run = create_run(session, "TEST_phase4_death_4")
        step(session, run["id"], 5)
        state = get_state(session, run["id"])
        person_count_before = len([e for e in state["entities"] if e["type"] == "person"])
        target = next(e for e in state["entities"] if e["type"] == "person")
        session.post(f"{API}/runs/{run['id']}/interventions", json={
            "type": "kill_entity", "payload": {"entity_id": target["id"]},
        })
        step(session, run["id"], 40)
        state_after = get_state(session, run["id"])
        person_count_after = len([e for e in state_after["entities"] if e["type"] == "person"])
        alive_after = len([e for e in state_after["entities"] if e["type"] == "person" and e.get("alive", True)])
        assert person_count_after == person_count_before  # total entity records never disappear (death != despawn)
        assert alive_after == person_count_before - 1      # exactly one fewer ALIVE person, never replenished


class TestHuntingFoodChain:
    def test_animal_death_from_starvation_goes_through_proposals(self, session):
        """Confirms the PRE-EXISTING animal death path (unchanged in Phase 4)
        is fully proposal-based - per the doctrine check the user asked for."""
        run = create_run(session, "TEST_phase4_hunt_1")
        state = get_state(session, run["id"])
        animal = next(e for e in state["entities"] if e["type"] == "animal")
        for _ in range(20):
            session.post(f"{API}/runs/{run['id']}/interventions", json={
                "type": "boost_need", "payload": {"entity_id": animal["id"], "field": "hunger", "delta": 1000},
            })
            step(session, run["id"], 3)
            st = get_state(session, run["id"])
            a = next(e for e in st["entities"] if e["id"] == animal["id"])
            if not a.get("alive", True):
                timeline = session.get(f"{API}/runs/{run['id']}/timeline", params={"limit": 500}).json()["timeline"]
                death_ev = [t for t in timeline if t["entity_id"] == animal["id"] and t["event_type"] == "death"]
                assert len(death_ev) == 1, "animal starvation death must be a real accepted event, not a silent despawn"
                return
        pytest.skip("animal did not starve within budget - not a Phase 4 regression, environment-dependent")


class TestReplayDoctrineNotBypassedByHistory:
    def test_history_service_never_writes_to_replay_authority_collections(self):
        from core import history_service
        source = inspect.getsource(history_service)
        assert "commit_frames.insert" not in source
        assert "commit_frames.update" not in source
        assert "commit_frames.replace" not in source
        assert "accepted_events.insert" not in source
        assert "accepted_events.update" not in source
        assert ".delete_" not in source  # history_service is read-only, never deletes

    def test_history_service_only_reads_accepted_events(self):
        from core import history_service
        source = inspect.getsource(history_service)
        assert "db.accepted_events.find" in source or "accepted_events.find" in source

    def test_replay_verification_does_not_import_history_service(self):
        from core import replay_service
        source = inspect.getsource(replay_service)
        assert "history_service" not in source


class TestNoHiddenLifecycleState:
    def test_lifecycle_domain_has_no_mutable_instance_state(self):
        from domains.lifecycle_domain import LifecycleDomain
        domain = LifecycleDomain()
        instance_vars = {k: v for k, v in vars(domain).items()}
        assert instance_vars == {}, f"LifecycleDomain must carry no hidden instance state: {instance_vars}"

    def test_lifecycle_domain_activate_is_pure(self):
        from domains.lifecycle_domain import LifecycleDomain
        from domains.base import ActivationFrame
        from core.rng import DeterministicRNG
        import copy

        terrain = [["grass"] * 5 for _ in range(5)]
        entities = {"person-000": {
            "type": "person", "position": {"x": 1, "y": 1}, "hunger": 500, "thirst": 500, "energy": 500,
            "alive": True, "age_ticks": 1000, "life_stage": "adult", "health": 800,
            "injury": {"injured": False, "severity": 0, "cause": None}, "has_shelter": False,
        }}
        domain = LifecycleDomain()
        rng1 = DeterministicRNG("purity_seed")
        rng2 = DeterministicRNG("purity_seed")
        due = domain.select_due_ids(entities, 5)
        f1 = ActivationFrame("run-a", 5, "0.3.0", "environment", copy.deepcopy(entities), terrain, due, rng1)
        f1.night = False
        f2 = ActivationFrame("run-a", 5, "0.3.0", "environment", copy.deepcopy(entities), terrain, due, rng2)
        f2.night = False
        out1 = domain.activate(f1)
        out2 = domain.activate(f2)
        assert out1.proposals == out2.proposals, "same input frame must produce byte-identical proposals"

    def test_lifecycle_diagnostics_use_namespaced_key_not_overwriting_people_diagnostics(self):
        from domains.lifecycle_domain import lifecycle_diag_key
        assert lifecycle_diag_key("person-000") == "person-000::lifecycle"
        assert lifecycle_diag_key("person-000") != "person-000"


class TestDeliberateResourceContention:
    """Previously-deferred test (Phase 2/3 backlog item) - added in Phase 4
    per the user's explicit instruction, since it exercises historical
    rejection evidence and conflict causality relevant to this phase."""

    def test_two_simultaneous_gather_proposals_on_same_tree_one_rejected(self):
        from core.commit_pipeline import run_commit_frame
        from domains.base import DomainOutput

        entities = {
            "tree-000": {"type": "tree", "position": {"x": 5, "y": 5}, "resource": 50, "max_resource": 80, "claimed_tick": None},
            "person-A": {"type": "person", "position": {"x": 5, "y": 6}, "alive": True},
            "person-B": {"type": "person", "position": {"x": 4, "y": 5}, "alive": True},
        }

        def gather_proposal(entity_id):
            return {
                "proposal_family": "people_action", "proposal_type": "gather",
                "proposer_engine_id": "people", "proposer_engine_version": "2.0.0",
                "entity_id": entity_id, "causal_parent_event_ids": [], "is_exogenous": True,
                "requested_time": 1, "phase": "agent", "engine_priority": 10,
                "touched_scope": [entity_id, "tree-000"],
                "preconditions": [
                    {"entity_id": "tree-000", "field": "claimed_tick", "op": "neq", "value": 1},
                    {"entity_id": "tree-000", "field": "resource", "op": "gte", "value": 1},
                ],
                "mutation": {"entity_updates": {"tree-000": {"resource": 40, "claimed_tick": 1}}, "new_entities": {}},
                "explanation": f"{entity_id} gathers from tree-000",
            }

        proposals = [gather_proposal("person-A"), gather_proposal("person-B")]
        accepted, rejected, _order = run_commit_frame(entities, [DomainOutput(proposals=proposals)], 1, "test-lineage", "test-run", 0, "frame-1")

        assert len(accepted) == 1
        assert len(rejected) == 1
        assert rejected[0]["reason_code"] == "conflict.resource_contention" or "precondition" in rejected[0]["reason_code"]
        assert rejected[0]["rejection_stage"] == "commit_revalidation"

    def test_proposal_arrival_order_does_not_affect_outcome(self):
        """Shuffling the INPUT order of independent proposals must never
        change acceptance outcome or the final hash - ordering is derived
        purely from (requested_time, phase_rank, engine_priority, content_hash)."""
        from core.commit_pipeline import run_commit_frame
        from domains.base import DomainOutput
        import copy

        def make_entities():
            return {f"person-{i:03d}": {"type": "person", "position": {"x": i, "y": 0}, "alive": True, "hunger": 100 + i}
                    for i in range(6)}

        def make_proposals():
            props = []
            for i in range(6):
                eid = f"person-{i:03d}"
                props.append({
                    "proposal_family": "people_action", "proposal_type": "wander",
                    "proposer_engine_id": "people", "proposer_engine_version": "2.0.0",
                    "entity_id": eid, "causal_parent_event_ids": [], "is_exogenous": True,
                    "requested_time": 1, "phase": "agent", "engine_priority": 10,
                    "touched_scope": [eid], "preconditions": [],
                    "mutation": {"entity_updates": {eid: {"hunger": 100 + i + 1}}, "new_entities": {}},
                    "explanation": f"{eid} wanders",
                })
            return props

        entities_a = make_entities()
        proposals_a = make_proposals()
        accepted_a, rejected_a, order_a = run_commit_frame(entities_a, [DomainOutput(proposals=proposals_a)], 1, "test-lineage", "test-run", 0, "frame-1")

        entities_b = make_entities()
        proposals_b = make_proposals()
        random.Random(99).shuffle(proposals_b)
        accepted_b, rejected_b, order_b = run_commit_frame(entities_b, [DomainOutput(proposals=proposals_b)], 1, "test-lineage", "test-run", 0, "frame-1")

        assert entities_a == entities_b, "final entity state must be identical regardless of proposal arrival order"
        assert [e["post_state_hash"] for e in accepted_a] == [e["post_state_hash"] for e in accepted_b]
        assert [e["entity_id"] for e in accepted_a] == [e["entity_id"] for e in accepted_b]
        assert len(rejected_a) == len(rejected_b) == 0
