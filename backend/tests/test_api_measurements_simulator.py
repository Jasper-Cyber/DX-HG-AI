"""API tests for /measurements and scenario/simulator endpoints (Task 8)."""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """App wired to a fresh temp DB."""
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "api.db"))

    # Reload DB modules so they read the env var, then reload the app + routers.
    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.routers import measurements as m_mod

    importlib.reload(m_mod)
    from app.routers import simulator as s_mod

    importlib.reload(s_mod)
    from app import main as main_mod

    importlib.reload(main_mod)

    conn_mod.init_db()
    return TestClient(main_mod.app), repo_mod


def test_measurements_empty(client):
    c, _ = client
    resp = c.get("/measurements")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["isExperimental"] is True
    assert body["items"] == []


def test_measurements_returns_inserted(client):
    c, repo = client
    from app.db.models import Measurement

    repo.insert_measurement(Measurement(timestamp="2026-01-01T00:00:00+00:00", metric_type="hr", value=72.0))
    resp = c.get("/measurements", params={"metric": "hr"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["metricType"] == "hr"
    assert body["items"][0]["isSynthetic"] is True


def test_measurements_unknown_metric_422(client):
    c, _ = client
    resp = c.get("/measurements", params={"metric": "bogus"})
    assert resp.status_code == 422


def test_scenario_get_and_set(client):
    c, _ = client
    assert c.get("/scenario").json()["scenario"] == "A"

    resp = c.post("/scenario", json={"scenario": "C"})
    assert resp.status_code == 200
    assert resp.json()["scenario"] == "C"


def test_scenario_invalid_422(client):
    c, _ = client
    resp = c.post("/scenario", json={"scenario": "Z"})
    assert resp.status_code == 422


def test_simulator_start_pause_reset(client):
    c, repo = client

    # Start now generates a batch of synthetic readings via the SimulatorService seam.
    assert c.post("/simulator/start").json()["status"] == "running"
    assert repo.count_measurements() > 0
    assert c.post("/simulator/pause").json()["status"] == "paused"

    # Reset clears ALL generated readings.
    state = c.post("/simulator/reset").json()
    assert state["status"] == "paused"
    assert state["cursorTs"] is None
    assert repo.count_measurements() == 0


def test_simulator_invalid_action_422(client):
    c, _ = client
    assert c.post("/simulator/explode").status_code == 422


def test_resume_and_tick_append_without_duplicates(client):
    c, repo = client
    from app.services.monitoring import tick

    initial = c.post('/simulator/start').json()
    first_count = repo.count_measurements()
    assert initial['cursorTs'] == repo.get_sim_state().cursor_ts
    # Repeated Start while running must be idempotent.
    c.post('/simulator/start')
    assert repo.count_measurements() == first_count
    tick()
    assert repo.count_measurements() == first_count + 6
    c.post('/simulator/pause')
    tick()
    assert repo.count_measurements() == first_count + 6
    resumed = c.post('/simulator/start').json()
    assert resumed['cursorTs'] > initial['cursorTs']
    rows = repo.query_measurements()
    assert len(rows) == first_count + 12
    assert len({(r.timestamp, r.metric_type) for r in rows}) == len(rows)
    assert c.get('/insights/history').json()


def test_analysis_replaces_stale_findings_and_reset_preserves_history(client):
    c, repo = client
    from app.db.models import AnomalyFinding

    repo.insert_finding(AnomalyFinding(
        metric_type='hr', finding_type='persistent_shift', severity_band='attention',
        window_start='2026-01-01', window_end='2026-01-02', deviation=4,
        supporting='{}',
    ))
    assert c.get('/insights', params={'persist': True}).json()['state'] == 'attention'
    assert c.post('/analysis/run').json()['alertState'] == 'normal'
    assert repo.list_findings() == []
    c.post('/simulator/start')
    count = len(c.get('/insights/history').json())
    c.post('/simulator/reset')
    assert c.get('/insights').json()['state'] == 'normal'
    assert repo.list_findings() == []
    assert repo.count_measurements() == 0
    history = c.get('/insights/history').json()
    assert len(history) == count + 1
    assert any(a['state'] == 'attention' for a in history)
    assert all(a['id'] and a['createdAt'] for a in history)
    assert len(c.get('/insights/history', params={'limit': 1}).json()) == 1
    assert c.get('/insights/history', params={'limit': 0}).status_code == 422


def test_scenario_change_refreshes_readings_analysis_and_trends(client, monkeypatch):
    c, repo = client
    from app.services.simulator import SimulatorService

    # A controlled irregular sequence exercises the warning path without
    # depending on whether a random burst lands in the trailing detector window.
    monkeypatch.setattr(SimulatorService, '_rhythm_flag',
                        lambda self, scenario, offset, rng: float(scenario == 'C'))
    c.post('/simulator/start')
    c.post('/scenario', json={'scenario': 'C'})
    assert all(r.scenario == 'C' for r in repo.query_measurements())
    assert repo.list_findings(), 'Scenario C should be analyzed without a manual API call'
    before = len(repo.list_findings())
    c.post('/analysis/run')
    assert len(repo.list_findings()) == before, 'Reanalysis must not accumulate findings'
    c.post('/simulator/reset')
    assert all(not s['points'] and s['baselineMean'] is None
               for s in c.get('/trends').json()['series'])
    assert c.get('/insights').json()['findings'] == []


def test_background_worker_advances_and_stops(client, monkeypatch):
    import asyncio
    from app.services import monitoring

    c, repo = client
    c.post('/simulator/start')
    count = repo.count_measurements()
    monkeypatch.setattr(monitoring, 'INTERVAL_SECONDS', 0.01)
    original_tick = monitoring.tick

    async def exercise():
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()

        def one_tick():
            original_tick()
            loop.call_soon_threadsafe(stop.set)

        monkeypatch.setattr(monitoring, 'tick', one_tick)
        await asyncio.wait_for(monitoring.run(stop), timeout=10)

    asyncio.run(exercise())
    assert repo.count_measurements() == count + 6
