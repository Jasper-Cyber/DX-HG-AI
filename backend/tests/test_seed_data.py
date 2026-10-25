"""Test the synthetic seed-data script (Task 5)."""
import importlib

import pytest


@pytest.fixture()
def seed_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "seed.db"))

    # Reload the modules the script imports so they bind to the temp DB.
    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.db import care_repository as care_mod

    importlib.reload(care_mod)
    from app.db import seed_providers as sp_mod

    importlib.reload(sp_mod)
    from app.services import simulator as sim_mod

    importlib.reload(sim_mod)
    from app.services import analysis as an_mod

    importlib.reload(an_mod)
    from app.services import alerts as al_mod

    importlib.reload(al_mod)

    import seed_data

    importlib.reload(seed_data)
    return seed_data, repo_mod, care_mod


def test_seed_populates_everything(seed_mod):
    seed, repo, care = seed_mod
    summary = seed.seed(scenario="B", steps=200, seed_value=42, do_reset=True)

    assert summary["scenario"] == "B"
    assert summary["readings"] > 0
    assert repo.count_measurements() == summary["readings"]
    # Providers seeded.
    assert care.count_providers() == 8
    # Baseline + findings + alert produced.
    assert repo.get_baseline("hr") is not None
    assert repo.latest_alert() is not None
    # Care profile with a contact.
    profile = care.get_care_profile()
    assert profile is not None
    assert profile.default_lat is not None
    assert len(profile.emergency_contacts) == 1


def test_seed_is_reproducible(seed_mod):
    seed, repo, _ = seed_mod
    # Two runs without do_reset (which would remove the open DB file on Windows);
    # seed() already clears measurements each run, so same seed => identical data.
    s1 = seed.seed(scenario="B", steps=150, seed_value=7, do_reset=False)
    readings1 = [(m.metric_type, m.value) for m in repo.query_measurements()]
    s2 = seed.seed(scenario="B", steps=150, seed_value=7, do_reset=False)
    readings2 = [(m.metric_type, m.value) for m in repo.query_measurements()]
    assert s1["readings"] == s2["readings"]
    assert readings1 == readings2  # same seed => identical data


def test_seed_scenario_a_is_normal(seed_mod):
    seed, repo, _ = seed_mod
    summary = seed.seed(scenario="A", steps=200, seed_value=3, do_reset=True)
    assert summary["alert_state"] == "normal"
