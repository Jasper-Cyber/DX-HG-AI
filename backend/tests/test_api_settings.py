"""API tests for /settings endpoints (Task 18)."""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "settings.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import care_repository as care_mod

    importlib.reload(care_mod)
    from app.routers import settings as set_mod

    importlib.reload(set_mod)
    from app import main as main_mod

    importlib.reload(main_mod)

    conn_mod.init_db()
    return TestClient(main_mod.app)


def test_get_settings_defaults(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["warningsEnabled"] is True
    assert body["suggestionsEnabled"] is False
    assert body["emergencyEnabled"] is False
    assert body["disclaimerAckAt"] is None


def test_put_settings_opt_in(client):
    resp = client.put("/settings", json={"suggestionsEnabled": True, "emergencyEnabled": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["suggestionsEnabled"] is True
    assert body["emergencyEnabled"] is True


def test_disclaimer_ack(client):
    assert client.get("/settings").json()["disclaimerAckAt"] is None
    resp = client.post("/settings/disclaimer-ack")
    assert resp.status_code == 200
    assert resp.json()["disclaimerAckAt"] is not None
