"""Tests for the care-network data layer (Task 18)."""
import importlib

import pytest


@pytest.fixture()
def care(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "care.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import care_repository as care_mod

    importlib.reload(care_mod)
    from app.db import seed_providers as seed_mod

    importlib.reload(seed_mod)

    conn_mod.init_db()
    return care_mod, seed_mod


def test_settings_defaults_opt_in_off(care):
    care_mod, _ = care
    s = care_mod.get_settings()
    assert s.warnings_enabled is True
    assert s.suggestions_enabled is False  # opt-in off by default
    assert s.emergency_enabled is False    # opt-in off by default
    assert s.disclaimer_ack_at is None


def test_update_settings_toggles(care):
    care_mod, _ = care
    s = care_mod.update_settings(suggestions_enabled=True, emergency_enabled=True)
    assert s.suggestions_enabled is True
    assert s.emergency_enabled is True
    # Unspecified flag preserved.
    assert s.warnings_enabled is True


def test_acknowledge_disclaimer_sets_timestamp(care):
    care_mod, _ = care
    assert care_mod.get_settings().disclaimer_ack_at is None
    s = care_mod.acknowledge_disclaimer()
    assert s.disclaimer_ack_at is not None


def test_seed_providers_idempotent(care):
    care_mod, seed_mod = care
    n1 = seed_mod.seed_providers()
    assert n1 == 8  # matches the seed list
    n2 = seed_mod.seed_providers()  # second call is a no-op
    assert n2 == 0
    assert care_mod.count_providers() == 8


def test_seed_has_cardiac_capable_hospital(care):
    care_mod, seed_mod = care
    seed_mod.seed_providers()
    hospitals = care_mod.list_providers(kind="hospital")
    assert any(h.can_handle_cardiac_emergency for h in hospitals)


def test_care_profile_upsert_with_contacts(care):
    care_mod, _ = care
    from app.db.care_models import CareProfile, EmergencyContact

    assert care_mod.get_care_profile() is None

    profile = CareProfile(
        full_name="Demo User",
        phone="+1-555-9000",
        default_lat=40.71,
        default_lon=-74.00,
        emergency_contacts=[
            EmergencyContact(name="Pat", phone="+1-555-9001", relationship="spouse", priority=1),
            EmergencyContact(name="Sam", phone="+1-555-9002", relationship="sibling", priority=2),
        ],
    )
    saved = care_mod.upsert_care_profile(profile)
    assert saved.full_name == "Demo User"
    assert len(saved.emergency_contacts) == 2
    assert saved.emergency_contacts[0].name == "Pat"  # ordered by priority


def test_care_profile_upsert_replaces_contacts(care):
    care_mod, _ = care
    from app.db.care_models import CareProfile, EmergencyContact

    care_mod.upsert_care_profile(
        CareProfile(full_name="A", emergency_contacts=[EmergencyContact(name="X", phone="1")])
    )
    saved = care_mod.upsert_care_profile(
        CareProfile(full_name="B", emergency_contacts=[EmergencyContact(name="Y", phone="2")])
    )
    assert saved.full_name == "B"
    assert len(saved.emergency_contacts) == 1
    assert saved.emergency_contacts[0].name == "Y"


def test_dispatch_event_insert_and_list(care):
    care_mod, _ = care
    from app.db.care_models import DispatchEvent

    care_mod.insert_dispatch_event(
        DispatchEvent(
            routing_reason="nearest_capable_hospital",
            channel="simulated",
            status="sent",
            payload='{"demo": true}',
        )
    )
    events = care_mod.list_dispatch_events()
    assert len(events) == 1
    assert events[0].channel == "simulated"
    assert events[0].status == "sent"
