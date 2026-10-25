"""Tests for SimulatorService (Task 6).

Covers the Requirement 2 behaviors: six-metric generation, the three scenarios,
reproducibility (same seed + scenario => identical sequences), Scenario B's
directional trends, Scenario C's irregular-rhythm injection, Reset clearing
session data, and occasional missing/low-quality samples.

Uses the same isolated-temp-DB pattern as test_api_measurements_simulator.py:
point HEARTGUARDIAN_DB at a temp file, then importlib.reload the DB modules so
they pick up the env var before the service touches them.
"""
import importlib

import pytest


@pytest.fixture()
def sim_env(tmp_path, monkeypatch):
    """Fresh temp DB wired to reloaded repository + service modules."""
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "sim.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import simulator as sim_mod

    importlib.reload(sim_mod)

    conn_mod.init_db()
    return sim_mod, repo_mod


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _run(repo, sim_mod, scenario="A", seed=42, days_back=21):
    """Set scenario + seed, backfill a history window, run start(), return rows.

    Seeds cursor_ts ``days_back`` days in the past so a single synchronous start()
    generates a multi-week batch up to now. This is the realistic resume/backfill
    path (a fresh cursor_ts=None start with no elapsed time generates nothing).
    """
    from datetime import datetime, timedelta, timezone

    start_cursor = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    repo.update_sim_state(scenario=scenario, seed=seed, cursor_ts=start_cursor)
    sim = sim_mod.SimulatorService()
    sim.start()
    return repo.query_measurements()


def _series(rows, metric):
    """Ordered (timestamp, value) pairs for a metric, skipping missing samples."""
    return [(r.timestamp, r.value) for r in rows if r.metric_type == metric and r.value is not None]


# --------------------------------------------------------------------------- #
# Generation basics (Req 2.1, 2.9)
# --------------------------------------------------------------------------- #

def test_start_generates_all_metrics_tagged_synthetic(sim_env):
    sim_mod, repo = sim_env
    rows = _run(repo, sim_mod, scenario="A")

    assert len(rows) > 0
    metrics = {r.metric_type for r in rows}
    assert metrics == {"hr", "hrv", "spo2", "rhythm", "activity", "sleep", "vo2max"}
    assert all(r.is_synthetic for r in rows)
    assert all(r.scenario == "A" for r in rows)


def test_start_advances_cursor_and_sets_running(sim_env):
    sim_mod, repo = sim_env
    from datetime import datetime, timedelta, timezone

    # Seed cursor into the past so this start() has ticks to generate and advances.
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    repo.update_sim_state(scenario="A", seed=42, cursor_ts=past)
    sim = sim_mod.SimulatorService()
    state = sim.start()

    assert state.status == "running"
    assert state.cursor_ts is not None


def test_fresh_start_with_no_elapsed_time_generates_nothing(sim_env):
    sim_mod, repo = sim_env
    # Fresh session (cursor_ts NULL): a start() at "now" has no completed tick to
    # backfill, so it generates nothing and leaves the cursor clean.
    sim = sim_mod.SimulatorService()
    state = sim.start()

    assert state.status == "running"
    assert state.cursor_ts is None
    assert repo.count_measurements() == 0


def test_pause_marks_paused_and_generates_nothing(sim_env):
    sim_mod, repo = sim_env
    _run(repo, sim_mod, scenario="A")
    before = repo.count_measurements()

    sim = sim_mod.SimulatorService()
    state = sim.pause()

    assert state.status == "paused"
    assert repo.count_measurements() == before


# --------------------------------------------------------------------------- #
# Reproducibility (Req 2.8)
# --------------------------------------------------------------------------- #

def test_same_seed_and_scenario_yield_identical_sequences(sim_env):
    sim_mod, repo = sim_env

    # Pin cursor_ts to a FIXED instant so both runs cover identical ticks; this
    # isolates reproducibility from wall-clock movement between the two runs.
    fixed_cursor = "2026-01-01T00:00:00+00:00"

    def run_once():
        repo.update_sim_state(scenario="A", seed=123, cursor_ts=fixed_cursor)
        sim_mod.SimulatorService().start()
        return [
            (r.timestamp, r.metric_type, r.value, r.quality)
            for r in repo.query_measurements()
        ]

    seq1 = run_once()
    sim_mod.SimulatorService().reset()
    seq2 = run_once()

    assert seq1 == seq2
    assert len(seq1) > 0


def test_different_seed_changes_sequence(sim_env):
    sim_mod, repo = sim_env

    rows1 = _run(repo, sim_mod, scenario="A", seed=1)
    hr1 = _series(rows1, "hr")

    sim_mod.SimulatorService().reset()
    rows2 = _run(repo, sim_mod, scenario="A", seed=999)
    hr2 = _series(rows2, "hr")

    assert hr1 != hr2


# --------------------------------------------------------------------------- #
# Scenario B — Gradual Deviation (Req 2.4)
# --------------------------------------------------------------------------- #

def test_scenario_b_hr_up_hrv_down_sleep_down(sim_env):
    sim_mod, repo = sim_env
    rows = _run(repo, sim_mod, scenario="B", seed=7)

    hr = [v for _, v in _series(rows, "hr")]
    hrv = [v for _, v in _series(rows, "hrv")]
    sleep = [v for _, v in _series(rows, "sleep")]

    # Compare the mean of the first quarter to the last quarter to smooth noise.
    def _trend(values):
        q = max(1, len(values) // 4)
        return sum(values[-q:]) / q - sum(values[:q]) / q

    assert _trend(hr) > 0, "resting HR should trend upward in Scenario B"
    assert _trend(hrv) < 0, "HRV should trend downward in Scenario B"
    assert _trend(sleep) < 0, "sleep should decline in Scenario B"


def test_scenario_a_hr_is_flat_relative_to_b(sim_env):
    sim_mod, repo = sim_env

    rows_a = _run(repo, sim_mod, scenario="A", seed=5)
    hr_a = [v for _, v in _series(rows_a, "hr")]

    sim_mod.SimulatorService().reset()
    rows_b = _run(repo, sim_mod, scenario="B", seed=5)
    hr_b = [v for _, v in _series(rows_b, "hr")]

    def _trend(values):
        q = max(1, len(values) // 4)
        return sum(values[-q:]) / q - sum(values[:q]) / q

    # Scenario A has no drift; its HR trend should be far smaller than B's.
    assert _trend(hr_b) > _trend(hr_a)


# --------------------------------------------------------------------------- #
# Scenario C — Rhythm Irregularity (Req 2.5)
# --------------------------------------------------------------------------- #

def test_scenario_c_injects_more_irregular_rhythm_than_a(sim_env):
    sim_mod, repo = sim_env

    rows_a = _run(repo, sim_mod, scenario="A", seed=3)
    irregular_a = sum(1 for _, v in _series(rows_a, "rhythm") if v == 1.0)
    total_a = len(_series(rows_a, "rhythm"))

    sim_mod.SimulatorService().reset()
    rows_c = _run(repo, sim_mod, scenario="C", seed=3)
    irregular_c = sum(1 for _, v in _series(rows_c, "rhythm") if v == 1.0)
    total_c = len(_series(rows_c, "rhythm"))

    rate_a = irregular_a / total_a if total_a else 0
    rate_c = irregular_c / total_c if total_c else 0

    assert irregular_c > 0, "Scenario C must inject irregular-rhythm flags"
    assert rate_c > rate_a, "Scenario C should be markedly more irregular than A"


# --------------------------------------------------------------------------- #
# Reset (Req 2.7)
# --------------------------------------------------------------------------- #

def test_reset_clears_readings_and_resets_state(sim_env):
    sim_mod, repo = sim_env
    _run(repo, sim_mod, scenario="C", seed=42)
    assert repo.count_measurements() > 0

    state = sim_mod.SimulatorService().reset()

    assert repo.count_measurements() == 0
    assert state.status == "paused"
    assert state.cursor_ts is None
    # Scenario selection is preserved across reset.
    assert state.scenario == "C"


# --------------------------------------------------------------------------- #
# Data quality (missing / low) — Req 3.4 feed, Req 1.6
# --------------------------------------------------------------------------- #

def test_missing_and_low_quality_samples_appear(sim_env):
    sim_mod, repo = sim_env
    # Generate across all scenarios' worth of ticks; the batch spans ~3 weeks of
    # hourly ticks so the small degradation rates should produce several of each.
    rows = _run(repo, sim_mod, scenario="A", seed=42)

    qualities = {r.quality for r in rows}
    assert "missing" in qualities, "expected some missing-quality samples"
    assert "low" in qualities, "expected some low-quality samples"

    # Missing samples must carry a null value; ok/low must carry a value.
    for r in rows:
        if r.quality == "missing":
            assert r.value is None
        else:
            assert r.value is not None


def test_advance_is_identical_across_chunks(sim_env):
    sim_mod, repo = sim_env
    sim = sim_mod.SimulatorService()
    sim.select_scenario('B')
    expected = sim.generate(steps=48, persist=False)
    sim.advance(24)
    cursor = repo.get_sim_state().cursor_ts
    sim.advance(24)
    actual = repo.query_measurements()
    key = lambda r: (r.timestamp, r.metric_type)
    values = lambda rows: [(r.timestamp, r.metric_type, r.value, r.quality)
                           for r in sorted(rows, key=key)]
    assert values(actual) == values(expected)
    assert repo.get_sim_state().cursor_ts > cursor


def test_vo2_is_daily_synthetic_and_backfill_is_idempotent(sim_env):
    sim_mod, repo = sim_env
    from app.db.models import Measurement

    sim = sim_mod.SimulatorService()
    generated = sim.generate(steps=48, persist=False)
    expected_vo2 = [r for r in generated if r.metric_type == 'vo2max']
    assert len(expected_vo2) == 2
    assert all(r.is_synthetic and 'T00:00:00' in r.timestamp for r in expected_vo2)
    assert all(r.value is None or 15 <= r.value <= 80 for r in expected_vo2)
    # Reproduce a database created before VO2 support, including alternate ISO notation.
    old = [r for r in generated if r.metric_type != 'vo2max']
    for row in old:
        row.timestamp = row.timestamp.replace('+00:00', 'Z')
    repo.insert_measurements(old)
    repo.insert_measurement(Measurement(timestamp='2026-01-03T00:00:00Z', metric_type='hr', value=60, is_synthetic=False))
    assert sim.backfill_vo2() == 2
    assert sim.backfill_vo2() == 0
    actual = repo.query_measurements(metric_type='vo2max')
    assert [(r.timestamp, r.value, r.quality) for r in actual] == [(r.timestamp, r.value, r.quality) for r in expected_vo2]
    assert repo.count_measurements() == len(old) + 3
