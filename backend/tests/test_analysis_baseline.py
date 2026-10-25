"""Tests for the analysis engine's baseline + rolling statistics (Task 9).

Covers Requirements 3.1 and 3.2:
  - baseline mean/std/sample_count match hand-computed values on a small fixed
    dataset inserted directly via the repository (exact arithmetic, no simulator);
  - missing/low-quality samples are excluded from the baseline;
  - the baseline persists and is retrievable via get_baseline;
  - rolling_stats mean/std/trend/deviation are correct on a fixed dataset and
    reproducible across repeated calls;
  - divide-by-zero and empty-data edge cases are handled without crashing.

Uses the same isolated-temp-DB pattern as the other backend tests: point
HEARTGUARDIAN_DB at a temp file, then importlib.reload the modules so they pick
up the env var before the analysis service touches the DB.
"""
import importlib
import math

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Fresh temp DB wired to reloaded connection + repository + analysis modules."""
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "analysis.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import analysis as analysis_mod

    importlib.reload(analysis_mod)

    conn_mod.init_db()
    return analysis_mod, repo_mod


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _ts(i: int) -> str:
    """Deterministic ascending ISO timestamps (one per minute)."""
    return f"2026-01-01T00:{i:02d}:00+00:00"


def _seed(repo, metric, specs):
    """Insert measurements from (value, quality) specs in ascending time order.

    A value of None is stored as-is (used for 'missing' samples).
    """
    from app.db.models import Measurement

    rows = [
        Measurement(timestamp=_ts(i), metric_type=metric, value=v, quality=q)
        for i, (v, q) in enumerate(specs)
    ]
    repo.insert_measurements(rows)


# --------------------------------------------------------------------------- #
# compute_baseline — exact arithmetic (Req 3.1)
# --------------------------------------------------------------------------- #

def test_baseline_matches_hand_computed_mean_std_count(env):
    analysis, repo = env
    # Fixed dataset: values 10,20,30,40,50 (all ok).
    _seed(repo, "hr", [(10.0, "ok"), (20.0, "ok"), (30.0, "ok"), (40.0, "ok"), (50.0, "ok")])

    b = analysis.compute_baseline("hr")

    # Mean = 30. Sample std (ddof=1) of {10,20,30,40,50}:
    # variance = (400+100+0+100+400)/(5-1) = 1000/4 = 250 -> std = sqrt(250).
    assert b.sample_count == 5
    assert b.mean == pytest.approx(30.0)
    assert b.std == pytest.approx(math.sqrt(250.0))


def test_baseline_excludes_missing_and_low_quality_samples(env):
    analysis, repo = env
    # Only the three 'ok' values (10, 30, 50) should count; the low and missing
    # samples (including a stray non-null low value) must be dropped.
    _seed(
        repo,
        "hr",
        [
            (10.0, "ok"),
            (999.0, "low"),      # excluded: low quality
            (30.0, "ok"),
            (None, "missing"),   # excluded: missing / null
            (50.0, "ok"),
        ],
    )

    b = analysis.compute_baseline("hr")

    # Mean of {10,30,50} = 30; variance = (400+0+400)/2 = 400 -> std = 20.
    assert b.sample_count == 3
    assert b.mean == pytest.approx(30.0)
    assert b.std == pytest.approx(20.0)


def test_baseline_persists_and_is_retrievable(env):
    analysis, repo = env
    _seed(repo, "spo2", [(97.0, "ok"), (98.0, "ok"), (99.0, "ok")])

    computed = analysis.compute_baseline("spo2")
    stored = repo.get_baseline("spo2")

    assert stored is not None
    assert stored.metric_type == "spo2"
    assert stored.mean == pytest.approx(computed.mean)
    assert stored.std == pytest.approx(computed.std)
    assert stored.sample_count == computed.sample_count


def test_baseline_single_sample_has_zero_std(env):
    analysis, repo = env
    _seed(repo, "hr", [(72.0, "ok")])

    b = analysis.compute_baseline("hr")

    assert b.sample_count == 1
    assert b.mean == pytest.approx(72.0)
    assert b.std == 0.0  # sample std undefined for n=1 -> normalized to 0.0


def test_baseline_empty_data_does_not_crash(env):
    analysis, repo = env
    # No measurements inserted at all.
    b = analysis.compute_baseline("hrv")

    assert b.sample_count == 0
    assert b.mean == 0.0
    assert b.std == 0.0
    # And it is still persisted.
    assert repo.get_baseline("hrv") is not None


# --------------------------------------------------------------------------- #
# rolling_stats — mean / std / trend / deviation (Req 3.2)
# --------------------------------------------------------------------------- #

def test_rolling_stats_mean_std_trend_on_fixed_dataset(env):
    analysis, repo = env
    # Strictly increasing by 10 -> slope should be exactly 10 per sample step.
    _seed(repo, "hr", [(10.0, "ok"), (20.0, "ok"), (30.0, "ok"), (40.0, "ok"), (50.0, "ok")])

    rs = analysis.rolling_stats("hr", window=10)

    assert rs.sample_count == 5
    assert rs.mean == pytest.approx(30.0)
    assert rs.std == pytest.approx(math.sqrt(250.0))  # sample std, matches baseline
    assert rs.trend == pytest.approx(10.0)            # least-squares slope


def test_rolling_stats_window_limits_to_recent_samples(env):
    analysis, repo = env
    # 6 samples; a window of 3 should summarize only the last three (40,50,60).
    _seed(
        repo,
        "hr",
        [(10.0, "ok"), (20.0, "ok"), (30.0, "ok"), (40.0, "ok"), (50.0, "ok"), (60.0, "ok")],
    )

    rs = analysis.rolling_stats("hr", window=3)

    assert rs.sample_count == 3
    assert rs.mean == pytest.approx(50.0)  # mean of 40,50,60
    assert rs.trend == pytest.approx(10.0)


def test_rolling_stats_excludes_missing_and_low_quality(env):
    analysis, repo = env
    _seed(
        repo,
        "hr",
        [(10.0, "ok"), (None, "missing"), (20.0, "ok"), (999.0, "low"), (30.0, "ok")],
    )

    rs = analysis.rolling_stats("hr", window=10)

    assert rs.sample_count == 3
    assert rs.mean == pytest.approx(20.0)  # mean of 10,20,30


def test_rolling_stats_deviation_against_baseline(env):
    analysis, repo = env
    # Baseline from a known dataset: mean=30, std=20 (from {10,30,50}).
    _seed(repo, "hr", [(10.0, "ok"), (30.0, "ok"), (50.0, "ok")])
    analysis.compute_baseline("hr")

    # Now the current window mean is 70; deviation = (70-30)/20 = 2.0.
    repo.clear_measurements()
    _seed(repo, "hr", [(60.0, "ok"), (70.0, "ok"), (80.0, "ok")])

    rs = analysis.rolling_stats("hr", window=10)

    assert rs.mean == pytest.approx(70.0)
    assert rs.deviation == pytest.approx(2.0)


def test_rolling_stats_deviation_none_without_baseline(env):
    analysis, repo = env
    _seed(repo, "hr", [(60.0, "ok"), (70.0, "ok")])

    rs = analysis.rolling_stats("hr", window=10)

    assert rs.deviation is None  # no baseline stored yet


def test_rolling_stats_is_reproducible_across_calls(env):
    analysis, repo = env
    _seed(repo, "hr", [(11.0, "ok"), (13.0, "ok"), (12.0, "ok"), (15.0, "ok"), (14.0, "ok")])
    analysis.compute_baseline("hr")

    first = analysis.rolling_stats("hr", window=10)
    second = analysis.rolling_stats("hr", window=10)

    assert first == second  # dataclass equality: identical mean/std/trend/deviation


# --------------------------------------------------------------------------- #
# Edge cases: divide-by-zero and empty data (Req 3.2 robustness)
# --------------------------------------------------------------------------- #

def test_rolling_stats_zero_std_baseline_yields_zero_deviation(env):
    analysis, repo = env
    # A constant metric (e.g. a flat rhythm flag) => baseline std == 0.
    _seed(repo, "rhythm", [(0.0, "ok"), (0.0, "ok"), (0.0, "ok")])
    b = analysis.compute_baseline("rhythm")
    assert b.std == 0.0

    # Current window differs, but deviation must be guarded to 0.0 (no inf/nan).
    repo.clear_measurements()
    _seed(repo, "rhythm", [(1.0, "ok"), (1.0, "ok")])

    rs = analysis.rolling_stats("rhythm", window=10)

    assert rs.deviation == 0.0
    assert not math.isinf(rs.deviation) and not math.isnan(rs.deviation)


def test_rolling_stats_empty_data_does_not_crash(env):
    analysis, repo = env
    rs = analysis.rolling_stats("spo2", window=10)

    assert rs.sample_count == 0
    assert rs.mean == 0.0
    assert rs.std == 0.0
    assert rs.trend == 0.0
    assert rs.deviation is None  # no baseline, no data


def test_rhythm_baseline_is_rate_of_irregular_flags(env):
    analysis, repo = env
    # rhythm is a 0/1 flag: mean == fraction of irregular readings.
    _seed(
        repo,
        "rhythm",
        [(0.0, "ok"), (1.0, "ok"), (0.0, "ok"), (1.0, "ok")],
    )

    b = analysis.compute_baseline("rhythm")

    assert b.sample_count == 4
    assert b.mean == pytest.approx(0.5)  # 2 of 4 irregular
