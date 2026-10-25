"""Tests for the Task 10 anomaly detectors, guardrail, and entry points.

Covers Requirements 3.3–3.8 (and the Task 11-facing get_trends shape, Req 5.1–5.3):
  - each detector FIRES on a crafted positive fixture and STAYS SILENT on a clean
    negative fixture;
  - the data_quality path fires on a high-missing window AND the physiological
    detectors do NOT emit a spurious trend on that gappy data (Req 3.4);
  - run_analysis outputs are reproducible across repeated calls (Req 3.7);
  - the IsolationForest cross-signal guardrail DOWNGRADES a crafted single-sensor
    drift (one metric drifts while correlated partners stay flat) and emits a
    data_quality finding, while a coherent multi-signal Scenario-B-like event is
    left un-downgraded;
  - the guardrail decision is deterministic under the fixed RANDOM_STATE (two
    runs => identical downgrade decisions);
  - the guardrail skips cleanly when there are too few aligned samples;
  - get_trends returns the expected aggregation shape and raises ValueError on a
    bad range.

Uses the same isolated-temp-DB pattern as the other backend tests: point
HEARTGUARDIAN_DB at a temp file, then importlib.reload the modules so they pick
up the env var before the analysis service touches the DB. Fixtures are inserted
directly via the repository for threshold-exact control (never via the simulator).
"""
import importlib
import json

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Fresh temp DB wired to reloaded connection + repository + analysis + config."""
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "detectors.db"))

    from app import analysis_config as cfg_mod

    importlib.reload(cfg_mod)
    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import analysis as analysis_mod

    importlib.reload(analysis_mod)

    conn_mod.init_db()
    return analysis_mod, repo_mod, cfg_mod


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _ts(i: int) -> str:
    """Deterministic ascending ISO timestamps (one per hour from a fixed start)."""
    day = 1 + (i // 24)
    hour = i % 24
    return f"2026-01-{day:02d}T{hour:02d}:00:00+00:00"


def _seed(repo, metric, specs, *, start=0):
    """Insert (value, quality) specs for one metric in ascending hourly order."""
    from app.db.models import Measurement

    rows = [
        Measurement(timestamp=_ts(start + i), metric_type=metric, value=v, quality=q)
        for i, (v, q) in enumerate(specs)
    ]
    repo.insert_measurements(rows)


def _ok(values):
    return [(float(v), "ok") for v in values]


def _supporting(finding):
    return json.loads(finding.supporting)


def _by_type(findings):
    out = {}
    for f in findings:
        out.setdefault(f.finding_type, []).append(f)
    return out


# --------------------------------------------------------------------------- #
# Detector 1 — persistent_shift (Req 3.3)
# --------------------------------------------------------------------------- #

def test_persistent_shift_fires_on_sustained_deviation(env):
    analysis, repo, cfg = env
    # Baseline ~60 with real spread so std is non-trivial.
    _seed(repo, "hr", _ok([58, 60, 62, 59, 61, 60, 62, 58, 61, 59] * 4))
    analysis.compute_baseline("hr")
    base = repo.get_baseline("hr")

    # Sustained window shifted well above baseline (>= 1.5 std).
    repo.clear_measurements()
    shifted = base.mean + cfg.PERSISTENT_SHIFT_MIN_DEVIATION * base.std + 5 * base.std
    _seed(repo, "hr", _ok([shifted] * cfg.PERSISTENT_SHIFT_WINDOW))
    # Re-point baseline to the original (compute_baseline overwrote? no — we did
    # not recompute). Re-upsert original baseline so deviation is vs. the normal ref.
    from app.db.models import Baseline

    repo.upsert_baseline(
        Baseline(metric_type="hr", mean=base.mean, std=base.std,
                 sample_count=base.sample_count, computed_at=base.computed_at)
    )

    f = analysis.detect_persistent_shift("hr")
    assert f is not None
    assert f.finding_type == "persistent_shift"
    assert abs(f.deviation) >= cfg.PERSISTENT_SHIFT_MIN_DEVIATION
    assert f.severity_band in ("info", "review", "attention")
    assert _supporting(f)["direction"] == "up"


def test_persistent_shift_silent_on_clean_data(env):
    analysis, repo, cfg = env
    _seed(repo, "hr", _ok([58, 60, 62, 59, 61, 60, 62, 58, 61, 59] * 4))
    analysis.compute_baseline("hr")
    base = repo.get_baseline("hr")

    repo.clear_measurements()
    # Current window sits right on the baseline mean -> no shift.
    _seed(repo, "hr", _ok([base.mean] * cfg.PERSISTENT_SHIFT_WINDOW))
    from app.db.models import Baseline

    repo.upsert_baseline(
        Baseline(metric_type="hr", mean=base.mean, std=base.std,
                 sample_count=base.sample_count, computed_at=base.computed_at)
    )

    assert analysis.detect_persistent_shift("hr") is None


# --------------------------------------------------------------------------- #
# Detector 2 — combination (Req 3.3)
# --------------------------------------------------------------------------- #

def test_combination_fires_when_hr_up_and_hrv_down(env):
    analysis, repo, cfg = env
    # Baselines with spread.
    _seed(repo, "hr", _ok([58, 60, 62, 59, 61] * 8))
    _seed(repo, "hrv", _ok([48, 50, 52, 49, 51] * 8))
    analysis.compute_baseline("hr")
    analysis.compute_baseline("hrv")
    hr_b = repo.get_baseline("hr")
    hrv_b = repo.get_baseline("hrv")

    repo.clear_measurements()
    hr_now = hr_b.mean + 2.0 * hr_b.std      # HR up
    hrv_now = hrv_b.mean - 2.0 * hrv_b.std   # HRV down
    _seed(repo, "hr", _ok([hr_now] * cfg.PERSISTENT_SHIFT_WINDOW))
    _seed(repo, "hrv", _ok([hrv_now] * cfg.PERSISTENT_SHIFT_WINDOW), start=cfg.PERSISTENT_SHIFT_WINDOW)
    from app.db.models import Baseline

    repo.upsert_baseline(Baseline(metric_type="hr", mean=hr_b.mean, std=hr_b.std,
                                  sample_count=hr_b.sample_count, computed_at=hr_b.computed_at))
    repo.upsert_baseline(Baseline(metric_type="hrv", mean=hrv_b.mean, std=hrv_b.std,
                                  sample_count=hrv_b.sample_count, computed_at=hrv_b.computed_at))

    f = analysis.detect_combination()
    assert f is not None
    assert f.finding_type == "combination"
    sup = _supporting(f)
    assert sup["hr_deviation"] >= cfg.COMBINATION_HR_UP_DEVIATION
    assert sup["hrv_deviation"] <= -cfg.COMBINATION_HRV_DOWN_DEVIATION


def test_combination_silent_when_only_hr_up(env):
    analysis, repo, cfg = env
    _seed(repo, "hr", _ok([58, 60, 62, 59, 61] * 8))
    _seed(repo, "hrv", _ok([48, 50, 52, 49, 51] * 8))
    analysis.compute_baseline("hr")
    analysis.compute_baseline("hrv")
    hr_b = repo.get_baseline("hr")
    hrv_b = repo.get_baseline("hrv")

    repo.clear_measurements()
    _seed(repo, "hr", _ok([hr_b.mean + 2.0 * hr_b.std] * cfg.PERSISTENT_SHIFT_WINDOW))
    _seed(repo, "hrv", _ok([hrv_b.mean] * cfg.PERSISTENT_SHIFT_WINDOW),
          start=cfg.PERSISTENT_SHIFT_WINDOW)  # HRV flat, not down
    from app.db.models import Baseline

    repo.upsert_baseline(Baseline(metric_type="hr", mean=hr_b.mean, std=hr_b.std,
                                  sample_count=hr_b.sample_count, computed_at=hr_b.computed_at))
    repo.upsert_baseline(Baseline(metric_type="hrv", mean=hrv_b.mean, std=hrv_b.std,
                                  sample_count=hrv_b.sample_count, computed_at=hrv_b.computed_at))

    assert analysis.detect_combination() is None


# --------------------------------------------------------------------------- #
# Detector 3 — rhythm_irregularity (Req 3.3/3.5)
# --------------------------------------------------------------------------- #

def test_rhythm_irregularity_fires_on_elevated_rate(env):
    analysis, repo, cfg = env
    w = cfg.RHYTHM_IRREGULARITY_WINDOW
    irregular = int(round(0.6 * w))  # 60% flagged, above the 0.30 threshold
    specs = _ok([1.0] * irregular + [0.0] * (w - irregular))
    _seed(repo, "rhythm", specs)

    f = analysis.detect_rhythm_irregularity()
    assert f is not None
    assert f.finding_type == "rhythm_irregularity"
    assert _supporting(f)["irregular_rate"] >= cfg.RHYTHM_IRREGULARITY_RATE


def test_rhythm_irregularity_silent_on_mostly_regular(env):
    analysis, repo, cfg = env
    w = cfg.RHYTHM_IRREGULARITY_WINDOW
    irregular = int(round(0.1 * w))  # 10% flagged, below threshold
    specs = _ok([1.0] * irregular + [0.0] * (w - irregular))
    _seed(repo, "rhythm", specs)

    assert analysis.detect_rhythm_irregularity() is None


# --------------------------------------------------------------------------- #
# Detector 4 — data_quality (Req 3.4)
# --------------------------------------------------------------------------- #

def test_data_quality_fires_and_physiological_stays_silent_on_gappy_window(env):
    analysis, repo, cfg = env
    # First establish a normal baseline for hr.
    _seed(repo, "hr", _ok([58, 60, 62, 59, 61] * 8))
    analysis.compute_baseline("hr")
    base = repo.get_baseline("hr")

    repo.clear_measurements()
    # Craft a gappy window: >= 40% missing/low. Of the few valid samples, push
    # them far from baseline so a naive detector WOULD have called it a shift.
    w = cfg.DATA_QUALITY_WINDOW
    n_missing = int(round(0.7 * w))
    specs = [(None, "missing")] * n_missing + _ok([base.mean + 10 * base.std] * (w - n_missing))
    _seed(repo, "hr", specs)
    from app.db.models import Baseline

    repo.upsert_baseline(Baseline(metric_type="hr", mean=base.mean, std=base.std,
                                  sample_count=base.sample_count, computed_at=base.computed_at))

    dq = analysis.detect_data_quality("hr")
    assert dq is not None
    assert dq.finding_type == "data_quality"
    assert dq.severity_band == "info"
    assert _supporting(dq)["missing_fraction"] >= cfg.DATA_QUALITY_MISSING_FRACTION

    # Physiological detector must NOT read the gap as a trend (Req 3.4).
    assert analysis.detect_persistent_shift("hr") is None


def test_data_quality_silent_on_clean_window(env):
    analysis, repo, cfg = env
    _seed(repo, "spo2", _ok([97, 98, 99, 97, 98] * 10))
    assert analysis.detect_data_quality("spo2") is None


# --------------------------------------------------------------------------- #
# run_analysis — reproducibility (Req 3.7)
# --------------------------------------------------------------------------- #

def _seed_scenario_b(repo, cfg, *, coherent_partners: bool):
    """Seed a baseline-window of data then a Scenario-B-like HR up / HRV down event.

    When coherent_partners is True, spo2 and activity move TOGETHER with the HR/HRV
    event (a believable whole-body change). When False, only HR drifts while HRV,
    spo2 and activity stay flat (a single-sensor artifact the guardrail should
    catch).
    """
    import numpy as np

    rng = np.random.default_rng(0)
    n = max(cfg.GUARDRAIL_MIN_SAMPLES + 40, cfg.BASELINE_WINDOW // 20)

    # Correlated baseline block: hr and activity rise together, hrv falls when hr
    # rises, spo2 mildly anti-correlated — so the forest learns the joint shape.
    drive = rng.normal(0, 1, n)
    hr = 60 + 3 * drive + rng.normal(0, 0.3, n)
    hrv = 50 - 3 * drive + rng.normal(0, 0.3, n)
    spo2 = 98 - 0.2 * drive + rng.normal(0, 0.1, n)
    activity = 40 + 5 * drive + rng.normal(0, 0.5, n)

    _seed(repo, "hr", _ok(hr))
    _seed(repo, "hrv", _ok(hrv), start=0)
    _seed(repo, "spo2", _ok(spo2), start=0)
    _seed(repo, "activity", _ok(activity), start=0)


# --------------------------------------------------------------------------- #

def test_run_analysis_is_reproducible(env):
    analysis, repo, cfg = env
    _seed(repo, "hr", _ok([58, 60, 62, 59, 61] * 20))
    _seed(repo, "hrv", _ok([48, 50, 52, 49, 51] * 20))
    _seed(repo, "spo2", _ok([97, 98, 99, 97, 98] * 20))
    _seed(repo, "rhythm", _ok([0.0] * 100))

    first = analysis.run_analysis()
    # Clear previously-persisted findings so we compare the computed set, not the
    # accumulated DB rows.
    second = analysis.run_analysis()

    def sig(fs):
        return sorted(
            (f.finding_type, f.metric_type, f.severity_band,
             round(f.deviation, 9) if f.deviation is not None else None)
            for f in fs
        )

    assert sig(first) == sig(second)


# --------------------------------------------------------------------------- #
# Cross-signal guardrail (IsolationForest)
# --------------------------------------------------------------------------- #

def test_guardrail_downgrades_single_sensor_drift_and_emits_data_quality(env):
    analysis, repo, cfg = env
    import numpy as np

    rng = np.random.default_rng(1)
    # A large clean baseline so recomputing the baseline over the full series is
    # not polluted by the appended drift block (keeps the persistent_shift
    # deviation large and the test robust).
    n = 400

    # Coherent correlated baseline: hr & activity up together, hrv down with hr.
    drive = rng.normal(0, 1, n)
    hr = list(60 + 3 * drive)
    hrv = list(50 - 3 * drive)
    spo2 = list(98 - 0.2 * drive)
    activity = list(40 + 5 * drive)

    # Append a SINGLE-SENSOR drift sustained over the whole persistent-shift
    # window: HR sits well above baseline while hrv/spo2/activity stay at their
    # calm baseline means (partners did NOT move). The sustained HR elevation
    # fires persistent_shift, and because HR broke the learned partner
    # relationship the recent residual is large -> the guardrail flags a
    # single-sensor artifact and downgrades. Jitter so the rows are distinct.
    drift_len = cfg.PERSISTENT_SHIFT_WINDOW
    drift_jit = rng.normal(0, 0.3, (drift_len, 4))
    hr += list(90.0 + drift_jit[:, 0])     # ~10 baseline-std above mean, sustained
    hrv += list(50.0 + drift_jit[:, 1])    # partner flat
    spo2 += list(98.0 + drift_jit[:, 2])   # partner flat
    activity += list(40.0 + drift_jit[:, 3])  # partner flat

    _seed(repo, "hr", _ok(hr))
    _seed(repo, "hrv", _ok(hrv), start=0)
    _seed(repo, "spo2", _ok(spo2), start=0)
    _seed(repo, "activity", _ok(activity), start=0)

    findings = analysis.run_analysis()
    by_type = _by_type(findings)
    # Sanity: the single-metric HR shift must have fired a physiological finding
    # for the guardrail to have something to downgrade.
    assert by_type.get("persistent_shift"), "fixture should trigger a persistent_shift on hr"

    # A persistent_shift on hr should exist but have been downgraded, and a
    # guardrail data_quality finding should be present explaining it.
    dq = [f for f in by_type.get("data_quality", []) if _supporting(f).get("detector") == "guardrail"]
    assert dq, "guardrail should emit an explanatory data_quality finding"
    downgrades = _supporting(dq[0])["downgrades"]
    assert downgrades, "guardrail should record at least one downgrade"
    # The downgrade must be a strict lowering (not a no-op).
    order = ["info", "review", "attention"]
    for d in downgrades:
        assert order.index(d["to"]) < order.index(d["from"])


def test_guardrail_leaves_coherent_event_undowngraded(env):
    analysis, repo, cfg = env
    import numpy as np

    rng = np.random.default_rng(2)
    n = cfg.GUARDRAIL_MIN_SAMPLES + 60

    drive = rng.normal(0, 1, n)
    hr = list(60 + 3 * drive)
    hrv = list(50 - 3 * drive)
    spo2 = list(98 - 0.2 * drive)
    activity = list(40 + 5 * drive)

    # Append a COHERENT whole-body event: HR up WHILE hrv down WHILE activity up
    # and spo2 nudges — consistent with the learned correlation, so NOT an outlier.
    ev = cfg.GUARDRAIL_RECENT_WINDOW
    hr += [78.0] * ev
    hrv += [32.0] * ev
    spo2 += [96.8] * ev
    activity += [70.0] * ev

    _seed(repo, "hr", _ok(hr))
    _seed(repo, "hrv", _ok(hrv), start=0)
    _seed(repo, "spo2", _ok(spo2), start=0)
    _seed(repo, "activity", _ok(activity), start=0)

    findings = analysis.run_analysis()
    guardrail_dq = [
        f for f in findings
        if f.finding_type == "data_quality" and _supporting(f).get("detector") == "guardrail"
    ]
    assert not guardrail_dq, "a coherent multi-signal event must not be downgraded"


def test_guardrail_decision_is_deterministic(env):
    analysis, repo, cfg = env
    import numpy as np

    rng = np.random.default_rng(3)
    n = cfg.GUARDRAIL_MIN_SAMPLES + 60
    drive = rng.normal(0, 1, n)
    L = cfg.GUARDRAIL_RECENT_WINDOW
    jit = rng.normal(0, 0.2, (L, 4))
    hr = list(60 + 3 * drive) + list(120.0 + jit[:, 0])
    hrv = list(50 - 3 * drive) + list(50.0 + jit[:, 1])
    spo2 = list(98 - 0.2 * drive) + list(98.0 + jit[:, 2])
    activity = list(40 + 5 * drive) + list(40.0 + jit[:, 3])
    _seed(repo, "hr", _ok(hr))
    _seed(repo, "hrv", _ok(hrv), start=0)
    _seed(repo, "spo2", _ok(spo2), start=0)
    _seed(repo, "activity", _ok(activity), start=0)

    first = analysis._guardrail_recent_is_outlier(user_id=1)
    second = analysis._guardrail_recent_is_outlier(user_id=1)
    assert first == second
    assert first is True  # the crafted single-sensor drift is an outlier


def test_guardrail_skips_cleanly_when_too_few_samples(env):
    analysis, repo, cfg = env
    # Far fewer than GUARDRAIL_MIN_SAMPLES aligned rows.
    few = max(1, cfg.GUARDRAIL_MIN_SAMPLES // 5)
    _seed(repo, "hr", _ok(range(60, 60 + few)))
    _seed(repo, "hrv", _ok(range(50, 50 + few)), start=0)
    _seed(repo, "spo2", _ok([98] * few), start=0)
    _seed(repo, "activity", _ok([40] * few), start=0)

    # Should return None (skipped), never raise.
    assert analysis._guardrail_recent_is_outlier(user_id=1) is None


# --------------------------------------------------------------------------- #
# get_trends (Req 5.1–5.3 shape; invalid range -> ValueError)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("rng_name", ["daily", "weekly", "monthly"])
def test_get_trends_shape(env, rng_name):
    analysis, repo, cfg = env
    _seed(repo, "hr", _ok([60, 61, 62, 63, 64, 65] * 8))

    out = analysis.get_trends(rng_name)
    assert out["range"] == rng_name
    assert "hr" in out["metrics"]
    buckets = out["metrics"]["hr"]
    assert len(buckets) >= 1
    for b in buckets:
        assert set(b.keys()) == {"bucket", "mean", "count"}
        if b["count"] > 0:
            assert isinstance(b["mean"], float)
    # A metric with no data yields an empty list.
    assert out["metrics"]["sleep"] == []


def test_get_trends_rejects_bad_range(env):
    analysis, repo, cfg = env
    with pytest.raises(ValueError):
        analysis.get_trends("hourly")
