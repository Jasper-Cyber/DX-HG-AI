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
