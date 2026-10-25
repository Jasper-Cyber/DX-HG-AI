"""Tests for the core DB layer (Task 4).

Each test runs against a fresh temp SQLite file (via HEARTGUARDIAN_DB), so the
suite never touches the real database.
"""
import importlib
import os

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Point the app at a temp DB file and return the repository module."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(db_file))

    # Reload modules so they pick up the env var at import time.
    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)

    conn_mod.init_db()
    return repo_mod


def _measurement(repo, **kw):
    from app.db.models import Measurement

    defaults = dict(timestamp="2026-01-01T00:00:00+00:00", metric_type="hr", value=70.0)
    defaults.update(kw)
    return Measurement(**defaults)


def test_init_creates_demo_user_and_sim_state(db):
    state = db.get_sim_state()
    assert state.scenario == "A"
    assert state.status == "paused"
    assert state.seed == 42


def test_insert_and_query_measurement(db):
    from app.db.models import Measurement

    mid = db.insert_measurement(
        Measurement(timestamp="2026-01-01T00:00:00+00:00", metric_type="hr", value=72.0)
    )
    assert mid > 0
    rows = db.query_measurements(metric_type="hr")
    assert len(rows) == 1
    assert rows[0].value == 72.0
    assert rows[0].is_synthetic is True


def test_bulk_insert_and_count(db):
    from app.db.models import Measurement

    rows = [
        Measurement(timestamp=f"2026-01-01T00:0{i}:00+00:00", metric_type="hr", value=60.0 + i)
        for i in range(5)
    ]
    n = db.insert_measurements(rows)
    assert n == 5
    assert db.count_measurements() == 5


def test_query_time_range_is_inclusive_and_ordered(db):
    from app.db.models import Measurement

    for i in range(5):
        db.insert_measurement(
            Measurement(timestamp=f"2026-01-01T00:0{i}:00+00:00", metric_type="hr", value=float(i))
        )
    rows = db.query_measurements(
        metric_type="hr",
        start="2026-01-01T00:01:00+00:00",
        end="2026-01-01T00:03:00+00:00",
    )
    assert [r.value for r in rows] == [1.0, 2.0, 3.0]  # ordered ascending, inclusive


def test_missing_quality_value_is_null(db):
    from app.db.models import Measurement

    db.insert_measurement(
        Measurement(
            timestamp="2026-01-01T00:00:00+00:00",
            metric_type="spo2",
            value=None,
            quality="missing",
        )
    )
    row = db.latest_measurement("spo2")
    assert row is not None
    assert row.value is None
    assert row.quality == "missing"


def test_clear_measurements(db):
    db.insert_measurement(_measurement(db))
    assert db.count_measurements() == 1
    db.clear_measurements()
    assert db.count_measurements() == 0


def test_upsert_baseline_replaces(db):
    from app.db.models import Baseline

    db.upsert_baseline(Baseline(metric_type="hr", mean=60.0, std=5.0, sample_count=100, computed_at="t1"))
    db.upsert_baseline(Baseline(metric_type="hr", mean=62.0, std=4.0, sample_count=120, computed_at="t2"))
    b = db.get_baseline("hr")
    assert b is not None
    assert b.mean == 62.0 and b.sample_count == 120  # replaced, not duplicated
    assert len(db.list_baselines()) == 1


def test_insert_and_list_findings(db):
    from app.db.models import AnomalyFinding

    db.insert_finding(
        AnomalyFinding(
            metric_type="hr",
            finding_type="persistent_shift",
            severity_band="review",
            window_start="t1",
            window_end="t2",
            supporting="{}",
            deviation=2.5,
        )
    )
    findings = db.list_findings()
    assert len(findings) == 1
    assert findings[0].finding_type == "persistent_shift"


def test_insert_and_latest_alert(db):
    from app.db.models import Alert

    db.insert_alert(
        Alert(
            state="normal",
            title="All clear",
            explanation="Within baseline.",
            next_steps="Keep monitoring.",
            finding_ids="[]",
        )
    )
    a = db.latest_alert()
    assert a is not None
    assert a.state == "normal"
    assert a.is_experimental is True


def test_update_sim_state(db):
    state = db.update_sim_state(scenario="B", status="running")
    assert state.scenario == "B"
    assert state.status == "running"
    # Unspecified fields are preserved.
    assert state.seed == 42
