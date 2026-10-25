"""Tests for ProviderService ranking + /providers and /care/profile (Task 19)."""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "prov.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import care_repository as care_mod

    importlib.reload(care_mod)
    from app.db import seed_providers as seed_mod

    importlib.reload(seed_mod)
    from app.services import provider as svc_mod

    importlib.reload(svc_mod)
    from app.routers import providers as prov_router

    importlib.reload(prov_router)
    from app import main as main_mod

    importlib.reload(main_mod)

    conn_mod.init_db()
    seed_mod.seed_providers()
    return TestClient(main_mod.app), care_mod, svc_mod, seed_mod


def test_haversine_zero_distance(ctx):
    _, _, svc_mod, _ = ctx
    assert svc_mod.haversine_km(40.0, -74.0, 40.0, -74.0) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance(ctx):
    _, _, svc_mod, _ = ctx
    # ~1 degree of latitude ≈ 111 km.
    d = svc_mod.haversine_km(40.0, -74.0, 41.0, -74.0)
    assert d == pytest.approx(111.19, abs=1.0)


def test_suggest_non_emergency_sorted_by_distance(ctx):
    _, _, svc_mod, seed_mod = ctx
    svc = svc_mod.ProviderService()
    results = svc.suggest(seed_mod.DEMO_CENTER_LAT, seed_mod.DEMO_CENTER_LON, emergency=False)
    distances = [r.distance_km for r in results]
    assert distances == sorted(distances)  # ascending by distance


def test_suggest_emergency_prioritizes_cardiac_capable(ctx):
    _, _, svc_mod, seed_mod = ctx
    svc = svc_mod.ProviderService()
    results = svc.suggest(seed_mod.DEMO_CENTER_LAT, seed_mod.DEMO_CENTER_LON, emergency=True)
    # The first result must be cardiac-capable.
    assert results[0].provider.can_handle_cardiac_emergency is True
    # All cardiac-capable providers come before any non-capable one.
    seen_non_capable = False
    for r in results:
        if not r.provider.can_handle_cardiac_emergency:
            seen_non_capable = True
        elif seen_non_capable:
            pytest.fail("a cardiac-capable provider appeared after a non-capable one")


def test_suggest_flags_preferred(ctx):
    _, care_mod, svc_mod, seed_mod = ctx
    doctors = care_mod.list_providers(kind="doctor")
    pref = doctors[0]
    svc = svc_mod.ProviderService()
    results = svc.suggest(
        seed_mod.DEMO_CENTER_LAT, seed_mod.DEMO_CENTER_LON, preferred_id=pref.id
    )
    flagged = [r for r in results if r.is_preferred]
    assert len(flagged) == 1
    assert flagged[0].provider.id == pref.id


def test_providers_endpoint_with_coords(ctx):
    client, _, _, seed_mod = ctx
    resp = client.get(
        "/providers",
        params={"lat": seed_mod.DEMO_CENTER_LAT, "lon": seed_mod.DEMO_CENTER_LON},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 8
    assert body["isExperimental"] is True
    # sorted ascending
    dists = [i["distanceKm"] for i in body["items"]]
    assert dists == sorted(dists)


def test_providers_endpoint_falls_back_to_profile_location(ctx):
    client, _, _, seed_mod = ctx
    # No lat/lon given, but a default location is set on the profile.
    client.put(
        "/care/profile",
        json={"defaultLat": seed_mod.DEMO_CENTER_LAT, "defaultLon": seed_mod.DEMO_CENTER_LON},
    )
    resp = client.get("/providers")
    assert resp.status_code == 200
    assert resp.json()["count"] == 8


def test_providers_endpoint_no_location_422(ctx):
    client, _, _, _ = ctx
    resp = client.get("/providers")  # no coords, no profile default
    assert resp.status_code == 422


def test_care_profile_roundtrip(ctx):
    client, _, _, _ = ctx
    assert client.get("/care/profile").json() is None

    resp = client.put(
        "/care/profile",
        json={
            "fullName": "Demo User",
            "phone": "+1-555-9000",
            "emergencyContacts": [
                {"name": "Pat", "phone": "+1-555-9001", "relationship": "spouse", "priority": 1}
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["fullName"] == "Demo User"
    assert len(body["emergencyContacts"]) == 1
    assert body["emergencyContacts"][0]["name"] == "Pat"
