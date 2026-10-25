"""Tests for EmergencyService + /emergency endpoints (Task 20)."""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "emg.db"))
    monkeypatch.delenv("HG_REAL_DISPATCH_ENABLED", raising=False)
    monkeypatch.setenv("HG_MAX_REACHABLE_KM", "15")

    from app import emergency_config as cfg_mod

    importlib.reload(cfg_mod)
    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import care_repository as care_mod

    importlib.reload(care_mod)
    from app.db import seed_providers as seed_mod

    importlib.reload(seed_mod)
    from app.services import provider as prov_mod

    importlib.reload(prov_mod)
    from app.adapters import notifier as notif_mod

    importlib.reload(notif_mod)
    from app.services import emergency as emg_mod

    importlib.reload(emg_mod)
    from app.routers import emergency as emg_router

    importlib.reload(emg_router)
    from app import main as main_mod

    importlib.reload(main_mod)

    conn_mod.init_db()
    seed_mod.seed_providers()
    return {
        "client": TestClient(main_mod.app),
        "care": care_mod,
        "seed": seed_mod,
        "emg": emg_mod,
        "cfg": cfg_mod,
    }


def _enable_emergency(care_mod):
    care_mod.update_settings(emergency_enabled=True)


def test_evaluate_returns_none_when_disabled(ctx):
    svc = ctx["emg"].EmergencyService()
    decision = svc.evaluate(lat=ctx["seed"].DEMO_CENTER_LAT, lon=ctx["seed"].DEMO_CENTER_LON)
    assert decision is None  # opt-in off by default


def test_evaluate_routes_to_nearest_capable_hospital(ctx):
    _enable_emergency(ctx["care"])
    svc = ctx["emg"].EmergencyService()
    decision = svc.evaluate(lat=ctx["seed"].DEMO_CENTER_LAT, lon=ctx["seed"].DEMO_CENTER_LON)
    assert decision is not None
    assert decision.routing_reason == "nearest_capable_hospital"
    assert decision.recipient.can_handle_cardiac_emergency is True


def test_evaluate_prefers_reachable_preferred_doctor(ctx):
    care_mod, seed = ctx["care"], ctx["seed"]
    _enable_emergency(care_mod)
    # Set preferred doctor to a nearby doctor (within MAX_REACHABLE_KM).
    doctors = care_mod.list_providers(kind="doctor")
    nearest_doc = min(
        doctors,
        key=lambda d: ctx["emg"].haversine_km(seed.DEMO_CENTER_LAT, seed.DEMO_CENTER_LON, d.lat, d.lon),
    )
    from app.db.care_models import CareProfile

    care_mod.upsert_care_profile(
        CareProfile(preferred_provider_id=nearest_doc.id, default_lat=seed.DEMO_CENTER_LAT, default_lon=seed.DEMO_CENTER_LON)
    )
    svc = ctx["emg"].EmergencyService()
    decision = svc.evaluate(lat=seed.DEMO_CENTER_LAT, lon=seed.DEMO_CENTER_LON)
    assert decision.routing_reason == "preferred_doctor_reachable"
    assert decision.recipient.id == nearest_doc.id


def test_payload_contains_contacts_and_location(ctx):
    care_mod, seed = ctx["care"], ctx["seed"]
    _enable_emergency(care_mod)
    from app.db.care_models import CareProfile, EmergencyContact

    care_mod.upsert_care_profile(
        CareProfile(
            full_name="Demo User",
            phone="+1-555-9000",
            emergency_contacts=[EmergencyContact(name="Pat", phone="+1-555-9001", priority=1)],
        )
    )
    svc = ctx["emg"].EmergencyService()
    decision = svc.evaluate(lat=seed.DEMO_CENTER_LAT, lon=seed.DEMO_CENTER_LON, finding_summary="elevated resting HR trend")
    payload = decision.payload
    assert payload["patient"]["name"] == "Demo User"
    assert payload["emergencyContacts"][0]["name"] == "Pat"
    assert payload["findingSummary"] == "elevated resting HR trend"
    assert payload["isExperimental"] is True


def test_dispatch_requires_confirmation(ctx):
    _enable_emergency(ctx["care"])
    svc = ctx["emg"].EmergencyService()
    decision = svc.evaluate(lat=ctx["seed"].DEMO_CENTER_LAT, lon=ctx["seed"].DEMO_CENTER_LON)
    with pytest.raises(ctx["emg"].EmergencyNotAvailable):
        svc.dispatch(decision, confirmed=False)


def test_simulated_dispatch_records_and_sends_nothing(ctx):
    care_mod = ctx["care"]
    _enable_emergency(care_mod)
    svc = ctx["emg"].EmergencyService()
    decision = svc.evaluate(lat=ctx["seed"].DEMO_CENTER_LAT, lon=ctx["seed"].DEMO_CENTER_LON)
    event = svc.dispatch(decision, channel="simulated", confirmed=True)
    assert event.channel == "simulated"
    assert event.status == "sent"
    assert len(care_mod.list_dispatch_events()) == 1  # recorded


def test_real_dispatch_blocked_without_optin(ctx):
    _enable_emergency(ctx["care"])
    svc = ctx["emg"].EmergencyService()
    decision = svc.evaluate(lat=ctx["seed"].DEMO_CENTER_LAT, lon=ctx["seed"].DEMO_CENTER_LON)
    with pytest.raises(ctx["emg"].RealDispatchNotAllowed):
        svc.dispatch(decision, channel="real", confirmed=True)


def test_routing_is_deterministic(ctx):
    _enable_emergency(ctx["care"])
    svc = ctx["emg"].EmergencyService()
    d1 = svc.evaluate(lat=ctx["seed"].DEMO_CENTER_LAT, lon=ctx["seed"].DEMO_CENTER_LON)
    d2 = svc.evaluate(lat=ctx["seed"].DEMO_CENTER_LAT, lon=ctx["seed"].DEMO_CENTER_LON)
    assert d1.recipient.id == d2.recipient.id
    assert d1.routing_reason == d2.routing_reason


# ------------------------- API endpoint tests ------------------------- #

def test_evaluate_endpoint_disabled(ctx):
    client = ctx["client"]
    resp = client.post("/emergency/evaluate", json={"lat": ctx["seed"].DEMO_CENTER_LAT, "lon": ctx["seed"].DEMO_CENTER_LON})
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert "emergency" in body["emergencyGuidance"].lower()


def test_dispatch_endpoint_simulated(ctx):
    client, care_mod, seed = ctx["client"], ctx["care"], ctx["seed"]
    _enable_emergency(care_mod)
    resp = client.post(
        "/emergency/dispatch",
        json={"lat": seed.DEMO_CENTER_LAT, "lon": seed.DEMO_CENTER_LON, "confirmed": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["channel"] == "simulated"
    assert body["status"] == "sent"

    hist = client.get("/emergency/history").json()
    assert len(hist) == 1


def test_dispatch_endpoint_real_forbidden(ctx):
    client, care_mod, seed = ctx["client"], ctx["care"], ctx["seed"]
    _enable_emergency(care_mod)
    resp = client.post(
        "/emergency/dispatch",
        json={"lat": seed.DEMO_CENTER_LAT, "lon": seed.DEMO_CENTER_LON, "confirmed": True, "channel": "real"},
    )
    assert resp.status_code == 403
