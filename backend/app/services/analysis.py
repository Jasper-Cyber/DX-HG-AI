"""Analysis engine: per-metric baselines and rolling statistics (Task 9).

PURPOSE
-------
This module turns the simulator's raw time-series (persisted via the repository)
into the two foundational analytical primitives the rest of the engine builds on
(Requirement 3.1, 3.2):

1. ``compute_baseline`` — learns a per-metric personal reference (mean, std,
   sample_count) from historical readings and persists it.
2. ``rolling_stats`` — summarizes the most recent window of a metric into a
   rolling mean, rolling std, a trend measure, and a standardized deviation from
   the baseline.

Task 10 (anomaly detectors) and Task 11 (analysis endpoints) consume the typed
results defined here (``Baseline`` from the DB models, and ``RollingStats``
below). The detectors are intentionally NOT implemented here yet.

TRANSPARENCY & REPRODUCIBILITY
------------------------------
Every threshold/window this module uses comes from ``app.analysis_config`` — the
single source of configuration (Req 3.6). The math is pure NumPy/Pandas with no
randomness, so for a fixed input dataset and fixed config the outputs are
bit-for-bit reproducible across runs (Req 3.7).

DATA QUALITY
------------
Missing/low-quality samples (``value is None`` OR ``quality != 'ok'``) are
excluded before any statistic is computed, so a sensor gap is never mistaken for
a physiological change (this supports Req 3.4; the explicit "it's a data-quality
issue, not a trend" classification is Task 10's job).

RHYTHM NOTE
-----------
``rhythm`` is a 0.0/1.0 irregular-rhythm flag, not a continuous physiological
value. Its mean is therefore the *rate* of irregular readings in the window and
its std behaves like a Bernoulli std. The same arithmetic is applied uniformly to
every metric (no special-casing) — this is well-defined for a 0/1 series and the
"mean = irregularity rate" reading is the sensible interpretation. The only guard
that matters for rhythm is the divide-by-zero protection when a baseline is a
constant flag (handled via ``MIN_STD_FOR_DEVIATION``).

KNOWN LIMITATIONS
-----------------
- The baseline is a simple global mean/std over a trailing window; it does not
  model time-of-day or circadian structure.
- The trend is a least-squares slope over sample index, not over real elapsed
  time, so irregular sampling intervals are treated as evenly spaced. For the
  demo's roughly-hourly ticks this is a close approximation.
- Standard deviation uses the SAMPLE convention (ddof=1); see ``compute_baseline``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from ..analysis_config import (
    BASELINE_WINDOW,
    COMBINATION_BAND_ATTENTION,
    COMBINATION_BAND_REVIEW,
    COMBINATION_HR_UP_DEVIATION,
    COMBINATION_HRV_DOWN_DEVIATION,
    DATA_QUALITY_MISSING_FRACTION,
    DATA_QUALITY_WINDOW,
    GUARDRAIL_CONTAMINATION,
    GUARDRAIL_FEATURE_METRICS,
    GUARDRAIL_MIN_SAMPLES,
    GUARDRAIL_N_ESTIMATORS,
    GUARDRAIL_RECENT_WINDOW,
    GUARDRAIL_RESIDUAL_Z,
    MIN_STD_FOR_DEVIATION,
    MIN_VALID_FRACTION_FOR_TREND,
    PERSISTENT_SHIFT_BAND_ATTENTION,
    PERSISTENT_SHIFT_BAND_REVIEW,
    PERSISTENT_SHIFT_MIN_DEVIATION,
    PERSISTENT_SHIFT_WINDOW,
    RANDOM_STATE,
    RHYTHM_BAND_ATTENTION,
    RHYTHM_BAND_REVIEW,
    RHYTHM_IRREGULARITY_RATE,
    RHYTHM_IRREGULARITY_WINDOW,
    ROLLING_WINDOW,
)
from ..db import repository as repo
from ..db.connection import DEMO_USER_ID, utc_now_iso
from ..db.models import AnomalyFinding, Baseline, Measurement, MetricType

# Physiological metrics that get a learned baseline + the shift/combination
# detectors. rhythm/activity/sleep are handled by their own detectors or are
# contextual, so they are not in this list.
_BASELINE_METRICS: tuple[MetricType, ...] = ("hr", "hrv", "spo2")

# Public alias of the numeric metrics the engine baselines/trends.
# BUGFIX (maiabrunne): ``routers/analysis.py`` (Task 11) imports ``NUMERIC_METRICS``
# for /trends iteration + metric validation, but this module only defined the
# private ``_BASELINE_METRICS``. Parallel PRs merged with mismatched names and broke
# the import of ``app.main``. Expose the public name without changing any logic.
NUMERIC_METRICS: tuple[MetricType, ...] = _BASELINE_METRICS

# Severity bands ordered weakest -> strongest; used by the guardrail downgrade.
_SEVERITY_ORDER: tuple[str, ...] = ("info", "review", "attention")


# --------------------------------------------------------------------------- #
# Typed result for rolling_stats (consumed by Task 10 / Task 11)
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class RollingStats:
    """Structured rolling-statistics result for a single metric window.

    Attributes:
        metric_type:   which metric these stats describe.
        window:        number of samples actually used (<= configured window).
        mean:          arithmetic mean of the window's valid values.
        std:           sample standard deviation (ddof=1) of the window; 0.0 when
                       fewer than 2 samples (std is undefined for n<2).
        trend:         least-squares slope of value vs. sample index over the
                       window (units: metric-units per sample step). Positive =>
                       rising, negative => falling. 0.0 when fewer than 2 samples.
        deviation:     standardized deviation of the window mean from the baseline:
                       ``(mean - baseline.mean) / baseline.std``. None when no
                       baseline exists; 0.0 when the baseline std is effectively
                       zero (guarded by MIN_STD_FOR_DEVIATION) to avoid blow-up.
        sample_count:  same as ``window`` (explicit name for downstream clarity).
    """

    metric_type: str
    window: int
    mean: float
    std: float
    trend: float
    deviation: Optional[float]
    sample_count: int


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _valid_values(measurements: list[Measurement]) -> list[float]:
    """Extract usable numeric values, dropping missing/low-quality samples.

    A sample is excluded when its value is None OR its quality is not 'ok'. This
    is the single place that defines "valid sample" for the analysis engine so
    baselines and rolling stats stay consistent with each other.
    """
    return [
        float(m.value)
        for m in measurements
        if m.value is not None and m.quality == "ok"
    ]


def _slope(values: list[float]) -> float:
    """Least-squares slope of ``values`` against their 0-based sample index.

    Defined as the trend measure: fit ``y = a*x + b`` with x = 0,1,2,... and
    return ``a``. Reproducible and dependency-light (numpy.polyfit). Returns 0.0
    for fewer than 2 points, where a slope is undefined.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    # polyfit degree 1 -> [slope, intercept]; take the slope.
    slope = np.polyfit(x, np.asarray(values, dtype=float), 1)[0]
    return float(slope)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def compute_baseline(
    metric_type: MetricType,
    *,
    user_id: int = DEMO_USER_ID,
    window: int = BASELINE_WINDOW,
) -> Baseline:
    """Compute, persist, and return the personal baseline for one metric.

    HOW IT IS COMPUTED
    ------------------
    1. Pull the metric's historical readings (timestamp-ascending) via
       ``repository.query_measurements``.
    2. Drop missing/low-quality samples (see ``_valid_values``).
    3. Keep the most recent ``window`` valid samples (the trailing baseline
       window). With fewer than ``window`` samples, all of them are used.
    4. ``mean`` = arithmetic mean; ``std`` = SAMPLE standard deviation with
       ``ddof=1`` (divides by n-1). The sample convention is used consistently
       across the engine; for n < 2 the std is undefined and stored as 0.0.
    5. ``sample_count`` = number of valid samples used.
    6. Persist via ``repository.upsert_baseline`` (one row per user+metric) and
       return the ``Baseline``.

    THIN DATA (Req 3.4 support)
    ---------------------------
    If there are zero valid samples, a zeroed baseline (mean=0, std=0,
    sample_count=0) is still persisted and returned so the pipeline never
    crashes on empty/low-quality data. When ``sample_count`` is below
    ``analysis_config.MIN_BASELINE_SAMPLES`` the baseline is low-confidence; the
    count is carried through so Task 10 can flag it rather than trust it. The
    behavior is fully deterministic either way.
    """
    measurements = repo.query_measurements(metric_type=metric_type, user_id=user_id)
    values = _valid_values(measurements)

    # Keep only the most recent ``window`` valid samples (ASC order => tail).
    if window is not None and window > 0:
        values = values[-window:]

    sample_count = len(values)
    if sample_count == 0:
        mean = 0.0
        std = 0.0
    else:
        arr = np.asarray(values, dtype=float)
        mean = float(arr.mean())
        # Sample std (ddof=1). numpy returns nan for n==1 with ddof=1; normalize
        # that undefined case to 0.0 so the stored baseline is always finite.
        std = float(arr.std(ddof=1)) if sample_count >= 2 else 0.0

    baseline = Baseline(
        metric_type=metric_type,
        mean=mean,
        std=std,
        sample_count=sample_count,
        computed_at=utc_now_iso(),
        user_id=user_id,
    )
    repo.upsert_baseline(baseline)
    return baseline


def rolling_stats(
    metric_type: MetricType,
    *,
    user_id: int = DEMO_USER_ID,
    window: int = ROLLING_WINDOW,
) -> RollingStats:
    """Compute rolling mean/std/trend and deviation-from-baseline for one metric.

    HOW IT IS COMPUTED
    ------------------
    1. Pull the metric's readings (ASC) and drop missing/low-quality samples.
    2. Take the most recent ``window`` valid samples into a pandas Series.
    3. ``mean`` = Series.mean(); ``std`` = Series.std() (pandas default ddof=1,
       i.e. the sample std — consistent with ``compute_baseline``); 0.0 when
       fewer than 2 samples.
    4. ``trend`` = least-squares slope of value vs. sample index over the window
       (see ``_slope``): positive = rising, negative = falling, in metric-units
       per sample step. 0.0 for fewer than 2 samples.
    5. ``deviation`` = standardized distance of the window mean from the stored
       baseline: ``(mean - baseline.mean) / baseline.std``. If no baseline exists
       the deviation is None. If the baseline std is <= MIN_STD_FOR_DEVIATION the
       deviation is 0.0 (divide-by-zero guard) rather than inf/nan.

    EDGE CASES
    ----------
    - No valid samples -> mean/std/trend = 0.0, sample_count = 0, deviation
      computed against the baseline mean if a baseline exists (0 - mean)/std, else
      None. Never raises.
    - Fully reproducible for fixed input + config: no randomness is involved.
    """
    measurements = repo.query_measurements(metric_type=metric_type, user_id=user_id)
    values = _valid_values(measurements)
    if window is not None and window > 0:
        values = values[-window:]

    series = pd.Series(values, dtype="float64")
    sample_count = int(series.size)

    if sample_count == 0:
        mean = 0.0
        std = 0.0
        trend = 0.0
    else:
        mean = float(series.mean())
        # pandas Series.std defaults to ddof=1; nan for a single element -> 0.0.
        std = float(series.std()) if sample_count >= 2 else 0.0
        trend = _slope(values)

    deviation = _standardized_deviation(metric_type, mean, user_id=user_id)

    return RollingStats(
        metric_type=metric_type,
        window=sample_count,
        mean=mean,
        std=std,
        trend=trend,
        deviation=deviation,
        sample_count=sample_count,
    )


def _standardized_deviation(
    metric_type: MetricType,
    rolling_mean: float,
    *,
    user_id: int,
) -> Optional[float]:
    """(rolling_mean - baseline.mean) / baseline.std, guarding divide-by-zero.

    Returns None when no baseline is stored for the metric. Returns 0.0 when the
    baseline std is effectively zero (<= MIN_STD_FOR_DEVIATION) so a flat baseline
    (e.g. a constant rhythm flag) never produces an infinite/NaN deviation.
    """
    baseline = repo.get_baseline(metric_type, user_id=user_id)
    if baseline is None:
        return None
    if abs(baseline.std) <= MIN_STD_FOR_DEVIATION:
        return 0.0
    return float((rolling_mean - baseline.mean) / baseline.std)


# =========================================================================== #
# Task 10 — anomaly detectors, cross-signal guardrail, and entry points
# =========================================================================== #
#
# Everything below extends the Task 9 primitives (compute_baseline, rolling_stats)
# into the four anomaly detectors required by Req 3.3–3.5, the scikit-learn
# cross-signal guardrail that reduces single-sensor-artifact false positives, and
# the two entry points Task 11 (Jasper) will wire to HTTP routes.
#
# TRANSPARENCY / REPRODUCIBILITY (Req 3.6/3.7): every numeric threshold comes from
# ``app.analysis_config``. The only stochastic component — IsolationForest — is
# seeded from ``analysis_config.RANDOM_STATE`` and refit fresh each run, so for a
# fixed input dataset and config the findings (including downgrade decisions) are
# identical across runs. ``_window_bounds`` derives window_start/window_end from
# the actual data (not wall-clock) so a given dataset always yields the same ISO
# window stamps.
#
# NOT A CLINICAL SCORE (Req 3.8): every ``deviation`` and every value inside a
# finding's ``supporting`` JSON is a DESCRIPTIVE statistic only. Nothing here is,
# or should be presented as, a validated clinical risk.


# --------------------------------------------------------------------------- #
# Shared helpers for the detectors
# --------------------------------------------------------------------------- #

def _recent(measurements: list[Measurement], window: int) -> list[Measurement]:
    """Return the most-recent ``window`` measurements (ASC input -> ASC tail)."""
    if window is not None and window > 0:
        return measurements[-window:]
    return list(measurements)


def _window_bounds(measurements: list[Measurement]) -> tuple[str, str]:
    """ISO (start, end) timestamps spanning ``measurements``.

    Derived from the data itself so the window stamps are reproducible for a
    fixed dataset. Falls back to ``utc_now_iso()`` for both ends when the list is
    empty (so a finding always has well-formed, non-null bounds).
    """
    if not measurements:
        now = utc_now_iso()
        return now, now
    return measurements[0].timestamp, measurements[-1].timestamp


def _valid_fraction(measurements: list[Measurement]) -> float:
    """Fraction of ``measurements`` that are valid (value present, quality 'ok').

    Returns 0.0 for an empty list. This is the mirror of the missing/low fraction
    and is what the physiological detectors gate on (Req 3.4).
    """
    if not measurements:
        return 0.0
    valid = sum(1 for m in measurements if m.value is not None and m.quality == "ok")
    return valid / len(measurements)


def _window_has_enough_quality(measurements: list[Measurement]) -> bool:
    """True when a physiological detector is allowed to fire on this window.

    Enforces Req 3.4 structurally: if the valid-sample fraction is below
    ``MIN_VALID_FRACTION_FOR_TREND`` the window is too gappy to trust as a trend,
    so persistent_shift / combination / rhythm must stay silent and only the
    data_quality detector may speak about it.
    """
    return _valid_fraction(measurements) >= MIN_VALID_FRACTION_FOR_TREND


def _band_from_magnitude(magnitude: float, review_cut: float, attention_cut: float) -> str:
    """Map a non-negative magnitude to a severity band via configurable cuts.

    >= attention_cut -> 'attention'; >= review_cut -> 'review'; otherwise 'info'.
    The cut-points live in analysis_config so the escalation ladder is auditable.
    """
    if magnitude >= attention_cut:
        return "attention"
    if magnitude >= review_cut:
        return "review"
    return "info"


def _finding(
    *,
    metric_type: str,
    finding_type: str,
    severity_band: str,
    measurements: list[Measurement],
    supporting: dict,
    deviation: Optional[float],
    user_id: int,
) -> AnomalyFinding:
    """Build an AnomalyFinding with JSON-encoded supporting values.

    ``supporting`` is serialized with ``sort_keys=True`` so the stored JSON text
    is byte-identical across runs for the same values (reproducibility, Req 3.7).
    """
    start, end = _window_bounds(measurements)
    return AnomalyFinding(
        metric_type=metric_type,  # type: ignore[arg-type]
        finding_type=finding_type,  # type: ignore[arg-type]
        severity_band=severity_band,  # type: ignore[arg-type]
        window_start=start,
        window_end=end,
        supporting=json.dumps(supporting, sort_keys=True),
        deviation=deviation,
        user_id=user_id,
    )


# --------------------------------------------------------------------------- #
# Detector 1 — persistent_shift (Req 3.3)
# --------------------------------------------------------------------------- #

def detect_persistent_shift(
    metric_type: MetricType,
    *,
    user_id: int = DEMO_USER_ID,
) -> Optional[AnomalyFinding]:
    """Detect a sustained deviation of one metric from its personal baseline.

    PURPOSE
        Catch a change that PERSISTS over a window (e.g. resting HR creeping up
        for days), as opposed to a momentary spike. This is the single-metric
        half of the Scenario-B signature (Req 3.3).

    EXACT RULE (auditable)
        1. Load the metric's readings; take the trailing
           ``PERSISTENT_SHIFT_WINDOW`` samples as the sustained window.
        2. If that window is too gappy (valid fraction <
           ``MIN_VALID_FRACTION_FOR_TREND``) do NOT fire — a data gap is not a
           trend (Req 3.4). Return None.
        3. Compute the window's standardized deviation from baseline
           ``(window_mean - baseline.mean) / baseline.std``.
        4. FIRE when ``abs(deviation) >= PERSISTENT_SHIFT_MIN_DEVIATION``.
        5. severity_band is scaled by ``abs(deviation)`` via the configurable
           ``PERSISTENT_SHIFT_BAND_REVIEW`` / ``_ATTENTION`` cut-points.

    REQUIREMENT: 3.3 (persistent change), 3.5 (structured finding), 3.6 (config),
    3.8 (deviation is descriptive, not a clinical risk).

    LIMITATIONS
        - Uses a single sustained window vs. the stored baseline; it does not
          require the deviation to be present in every sub-window, only that the
          window as a whole has shifted. A slow ramp that only crosses threshold
          at the very end can still fire — acceptable for the demo's sensitivity.
        - Needs a baseline with non-trivial std; a flat baseline yields deviation
          0.0 (guarded) and therefore never fires.
    """
    measurements = repo.query_measurements(metric_type=metric_type, user_id=user_id)
    window = _recent(measurements, PERSISTENT_SHIFT_WINDOW)
    if not _window_has_enough_quality(window):
        return None

    values = _valid_values(window)
    if not values:
        return None
    window_mean = float(np.mean(values))
    deviation = _standardized_deviation(metric_type, window_mean, user_id=user_id)
    if deviation is None:
        return None

    magnitude = abs(deviation)
    if magnitude < PERSISTENT_SHIFT_MIN_DEVIATION:
        return None

    band = _band_from_magnitude(
        magnitude, PERSISTENT_SHIFT_BAND_REVIEW, PERSISTENT_SHIFT_BAND_ATTENTION
    )
    baseline = repo.get_baseline(metric_type, user_id=user_id)
    supporting = {
        "detector": "persistent_shift",
        "baseline_mean": baseline.mean if baseline else None,
        "baseline_std": baseline.std if baseline else None,
        "window_mean": window_mean,
        "window_samples": len(values),
        "standardized_deviation": deviation,
        "threshold": PERSISTENT_SHIFT_MIN_DEVIATION,
        "direction": "up" if deviation > 0 else "down",
        "note": "descriptive statistic, not a clinical risk score",
    }
    return _finding(
        metric_type=metric_type,
        finding_type="persistent_shift",
        severity_band=band,
        measurements=window,
        supporting=supporting,
        deviation=deviation,
        user_id=user_id,
    )


# --------------------------------------------------------------------------- #
# Detector 2 — combination: HR up AND HRV down together (Req 3.3)
# --------------------------------------------------------------------------- #

def detect_combination(*, user_id: int = DEMO_USER_ID) -> Optional[AnomalyFinding]:
    """Detect the HR-up-AND-HRV-down co-movement (the Scenario-B signature).

    PURPOSE
        Some changes are only meaningful as a COMBINATION. Rising heart rate
        together with falling heart-rate variability is a classic stress/strain
        signature that is more notable than either metric alone (Req 3.3).

    EXACT RULE (auditable)
        1. Build rolling stats for HR and HRV over the long sustained window.
        2. If EITHER metric's window is too gappy, do not fire (Req 3.4).
        3. FIRE only when BOTH hold at once:
             HR deviation  >= +COMBINATION_HR_UP_DEVIATION   (HR up), AND
             HRV deviation <= -COMBINATION_HRV_DOWN_DEVIATION (HRV down).
        4. severity_band is scaled by the WEAKER leg (min of the two magnitudes)
           so one strong + one barely-past leg cannot over-escalate, via the
           configurable COMBINATION_BAND_* cut-points.
        5. Emit a SINGLE finding (metric_type 'hr' as the anchor) referencing both
           metrics in ``supporting``.

    REQUIREMENT: 3.3 (unusual combination), 3.5, 3.6, 3.8.

    LIMITATIONS
        - Requires both baselines to exist with non-trivial std.
        - Directional and symmetric only for the HR-up/HRV-down pattern; the
          reverse (HR down / HRV up) is intentionally not flagged.
    """
    hr = repo.query_measurements(metric_type="hr", user_id=user_id)
    hrv = repo.query_measurements(metric_type="hrv", user_id=user_id)
    hr_win = _recent(hr, PERSISTENT_SHIFT_WINDOW)
    hrv_win = _recent(hrv, PERSISTENT_SHIFT_WINDOW)
    if not _window_has_enough_quality(hr_win) or not _window_has_enough_quality(hrv_win):
        return None

    hr_vals = _valid_values(hr_win)
    hrv_vals = _valid_values(hrv_win)
    if not hr_vals or not hrv_vals:
        return None

    hr_dev = _standardized_deviation("hr", float(np.mean(hr_vals)), user_id=user_id)
    hrv_dev = _standardized_deviation("hrv", float(np.mean(hrv_vals)), user_id=user_id)
    if hr_dev is None or hrv_dev is None:
        return None

    hr_up = hr_dev >= COMBINATION_HR_UP_DEVIATION
    hrv_down = hrv_dev <= -COMBINATION_HRV_DOWN_DEVIATION
    if not (hr_up and hrv_down):
        return None

    weakest = min(abs(hr_dev), abs(hrv_dev))
    band = _band_from_magnitude(weakest, COMBINATION_BAND_REVIEW, COMBINATION_BAND_ATTENTION)
    supporting = {
        "detector": "combination",
        "metrics": ["hr", "hrv"],
        "hr_deviation": hr_dev,
        "hrv_deviation": hrv_dev,
        "hr_up_threshold": COMBINATION_HR_UP_DEVIATION,
        "hrv_down_threshold": -COMBINATION_HRV_DOWN_DEVIATION,
        "gating_magnitude": weakest,
        "note": "HR up AND HRV down co-movement; descriptive, not a clinical risk score",
    }
    # Use the union span of both windows for the finding bounds.
    span = sorted(hr_win + hrv_win, key=lambda m: m.timestamp)
    return _finding(
        metric_type="hr",
        finding_type="combination",
        severity_band=band,
        measurements=span,
        supporting=supporting,
        deviation=hr_dev,
        user_id=user_id,
    )


# --------------------------------------------------------------------------- #
# Detector 3 — rhythm_irregularity (Req 3.3 / 3.5)
# --------------------------------------------------------------------------- #

def detect_rhythm_irregularity(*, user_id: int = DEMO_USER_ID) -> Optional[AnomalyFinding]:
    """Detect an elevated rate of irregular-rhythm flags (Scenario-C signature).

    PURPOSE
        rhythm is a 0/1 flag where 1 == a reading was tagged irregular. A short
        burst is noise; a sustained elevated RATE over the recent window is the
        Scenario-C signature worth surfacing (Req 3.3/3.5).

    EXACT RULE (auditable)
        1. Take the trailing ``RHYTHM_IRREGULARITY_WINDOW`` rhythm readings.
        2. If the window is too gappy, do not fire (Req 3.4).
        3. irregular_rate = mean of the valid 0/1 values (= fraction flagged).
        4. FIRE when ``irregular_rate >= RHYTHM_IRREGULARITY_RATE``.
        5. severity_band scaled by the rate via RHYTHM_BAND_* cut-points.

    REQUIREMENT: 3.3, 3.5, 3.6, 3.8.

    LIMITATIONS
        - Treats every flagged tick equally; it does not model clustering or
          burst duration, only the overall rate in the window.
    """
    rhythm = repo.query_measurements(metric_type="rhythm", user_id=user_id)
    window = _recent(rhythm, RHYTHM_IRREGULARITY_WINDOW)
    if not _window_has_enough_quality(window):
        return None

    values = _valid_values(window)
    if not values:
        return None
    irregular_rate = float(np.mean(values))
    if irregular_rate < RHYTHM_IRREGULARITY_RATE:
        return None

    band = _band_from_magnitude(irregular_rate, RHYTHM_BAND_REVIEW, RHYTHM_BAND_ATTENTION)
    supporting = {
        "detector": "rhythm_irregularity",
        "irregular_rate": irregular_rate,
        "irregular_count": int(sum(1 for v in values if v >= 0.5)),
        "window_samples": len(values),
        "threshold": RHYTHM_IRREGULARITY_RATE,
        "note": "rate of irregular-rhythm flags; descriptive, not a diagnosis of arrhythmia",
    }
    return _finding(
        metric_type="rhythm",
        finding_type="rhythm_irregularity",
        severity_band=band,
        measurements=window,
        supporting=supporting,
        deviation=None,
        user_id=user_id,
    )


# --------------------------------------------------------------------------- #
# Detector 4 — data_quality (Req 3.4)
# --------------------------------------------------------------------------- #

def detect_data_quality(
    metric_type: MetricType,
    *,
    user_id: int = DEMO_USER_ID,
) -> Optional[AnomalyFinding]:
    """Classify a gappy recent window as a DATA-QUALITY issue, not a trend.

    PURPOSE
        Req 3.4: when too much of the recent window is missing/low-quality, the
        engine must say "this is a sensor/data problem" instead of silently
        letting a gap masquerade as a physiological change. This detector emits
        that explicit classification; the physiological detectors separately
        refuse to fire on the same gappy window (see ``_window_has_enough_quality``).

    EXACT RULE (auditable)
        1. Take the trailing ``DATA_QUALITY_WINDOW`` readings (ALL of them,
           regardless of quality).
        2. missing_fraction = (#missing or low) / (#readings in window).
        3. FIRE when ``missing_fraction >= DATA_QUALITY_MISSING_FRACTION``.
        4. severity_band is fixed at 'info' — a data-quality gap is informational,
           never an escalating physiological alarm.

    REQUIREMENT: 3.4, 3.5, 3.6.

    LIMITATIONS
        - Operates per metric; it does not correlate gaps across metrics.
        - A window with zero readings does not fire (nothing to measure).
    """
    measurements = repo.query_measurements(metric_type=metric_type, user_id=user_id)
    window = _recent(measurements, DATA_QUALITY_WINDOW)
    if not window:
        return None

    missing = sum(1 for m in window if m.value is None or m.quality != "ok")
    missing_fraction = missing / len(window)
    if missing_fraction < DATA_QUALITY_MISSING_FRACTION:
        return None

    supporting = {
        "detector": "data_quality",
        "missing_fraction": missing_fraction,
        "missing_count": missing,
        "window_samples": len(window),
        "threshold": DATA_QUALITY_MISSING_FRACTION,
        "note": "data-quality issue (sensor gap / low quality), NOT a physiological trend",
    }
    return _finding(
        metric_type=metric_type,
        finding_type="data_quality",
        severity_band="info",
        measurements=window,
        supporting=supporting,
        deviation=None,
        user_id=user_id,
    )


# --------------------------------------------------------------------------- #
# scikit-learn cross-signal guardrail (IsolationForest)
# --------------------------------------------------------------------------- #

def _build_feature_matrix(
    *, user_id: int
) -> tuple[Optional[np.ndarray], list[str]]:
    """Align GUARDRAIL_FEATURE_METRICS by timestamp into a dense feature matrix.

    Each row is one timestamp at which ALL configured feature metrics have a
    valid (non-null, quality 'ok') reading; any timestamp missing any metric is
    dropped. Columns follow ``GUARDRAIL_FEATURE_METRICS`` order.

    EXTENSION POINT: add a new signal by appending its metric_type to
    ``analysis_config.GUARDRAIL_FEATURE_METRICS`` — this builder, the fit, and the
    scoring all read that list, so accelerometer/composite features slot in with
    no other code change.

    Returns ``(matrix, sorted_timestamps)``; matrix is None when there are zero
    aligned rows.
    """
    per_metric: dict[str, dict[str, float]] = {}
    for metric in GUARDRAIL_FEATURE_METRICS:
        rows = repo.query_measurements(metric_type=metric, user_id=user_id)
        per_metric[metric] = {
            m.timestamp: float(m.value)
            for m in rows
            if m.value is not None and m.quality == "ok"
        }

    # Timestamps where every configured metric has a valid reading.
    common = set.intersection(*(set(v.keys()) for v in per_metric.values())) if per_metric else set()
    timestamps = sorted(common)
    if not timestamps:
        return None, []

    matrix = np.array(
        [[per_metric[metric][ts] for metric in GUARDRAIL_FEATURE_METRICS] for ts in timestamps],
        dtype=float,
    )
    return matrix, timestamps


def _guardrail_recent_is_outlier(*, user_id: int) -> Optional[bool]:
    """Decide whether the recent window is a *single-sensor artifact* (True).

    RATIONALE (false-positive reduction): see analysis_config's guardrail section.
    The decision must separate a SINGLE-SENSOR DRIFT (one metric moves while its
    correlated partners stay put — an artifact) from a COHERENT whole-body event
    (all metrics move together — a real signal). A plain multivariate outlier test
    cannot do this: any strong excursion (coherent or not) lands outside the
    baseline cloud and looks anomalous. So the guardrail keys off the CORRELATION
    RESIDUAL instead of absolute level.

    METHOD (fast, deterministic, config-driven)
        1. Compute PARTNER RESIDUALS: for each feature metric, the residual is
           ``actual - predicted`` where ``predicted`` is a least-squares linear
           estimate of that metric from its PARTNER metrics, learned on the
           baseline portion only. On the baseline these residuals are small; a
           metric moving while its partners stay put yields a large residual.
        2. Standardize the recent window's residuals by the baseline residual std
           (per metric) to get a z-score, and FLAG the window a single-sensor
           artifact when any metric's residual z-score >= ``GUARDRAIL_RESIDUAL_Z``.
        3. (Corroboration) A fresh IsolationForest is also fit on the baseline
           residuals with ``random_state=RANDOM_STATE`` so we exercise the agreed
           scikit-learn guardrail path and keep an ML extension point; its vote is
           OR-ed with the residual-z rule. The residual-z rule is the transparent,
           reproducible primary discriminator (the forest alone cannot separate a
           coherent strong event from a drift — both look far from baseline).

    Because a coherent event preserves the partner relationships, its residuals
    stay small (not flagged); a single-sensor drift breaks them (flagged).

    FIT vs. SCORE SPLIT: coefficients, residual std, and the forest are all fit on
    the baseline portion (all aligned rows except the most-recent
    ``GUARDRAIL_RECENT_WINDOW``); the recent window is scored against them.

    DETERMINISM (Req 3.7): the residual regression and z-scores are pure NumPy
    (no randomness); the forest is seeded. Two runs over the same data return the
    same decision.

    TOO-FEW-SAMPLES: if fewer than ``GUARDRAIL_MIN_SAMPLES`` baseline rows exist,
    SKIP cleanly and return None ("guardrail did not run" — no downgrade, no crash).
    """
    matrix, _ = _build_feature_matrix(user_id=user_id)
    if matrix is None:
        return None

    recent = matrix[-GUARDRAIL_RECENT_WINDOW:]
    train = matrix[:-GUARDRAIL_RECENT_WINDOW]
    if recent.shape[0] == 0 or train.shape[0] < GUARDRAIL_MIN_SAMPLES:
        return None

    train_resid = _partner_residuals(train, train)
    recent_resid = _partner_residuals(recent, train)
    if train_resid is None or recent_resid is None:
        return None

    # Primary, transparent discriminator: residual z-score vs baseline residual std.
    resid_std = train_resid.std(axis=0, ddof=1)
    resid_std[resid_std < MIN_STD_FOR_DEVIATION] = MIN_STD_FOR_DEVIATION
    recent_z = np.abs(recent_resid) / resid_std
    residual_flag = bool(np.any(recent_z >= GUARDRAIL_RESIDUAL_Z))

    # Corroborating scikit-learn path (agreed design + ML extension point). Its
    # vote only strengthens the decision; it never vetoes the residual rule.
    forest_flag = False
    try:
        from sklearn.ensemble import IsolationForest

        forest = IsolationForest(
            n_estimators=GUARDRAIL_N_ESTIMATORS,
            contamination=GUARDRAIL_CONTAMINATION,
            random_state=RANDOM_STATE,
        )
        forest.fit(train_resid)
        forest_flag = bool(np.any(forest.predict(recent_resid) == -1))
    except Exception:  # pragma: no cover - environment without sklearn
        forest_flag = False

    return residual_flag or forest_flag


def _partner_residuals(
    rows: np.ndarray, baseline: np.ndarray
) -> Optional[np.ndarray]:
    """Residual of each metric vs. a linear prediction from its partner metrics.

    For every feature column ``j``, fit (on ``baseline``) an ordinary
    least-squares model ``metric_j ~ [all other metrics, 1]`` and return, for
    ``rows``, the residual ``actual_j - predicted_j`` in each column. The partner
    relationships are what the guardrail cares about: a metric that drifts on its
    own (partners unchanged) yields a large residual, whereas a coherent move that
    keeps the partner relationship intact yields a small one.

    Deterministic (pure least squares, no randomness). Returns None if there are
    too few baseline rows or fewer than two feature columns to regress against.
    """
    n_cols = baseline.shape[1]
    if n_cols < 2 or baseline.shape[0] < n_cols + 1:
        return None

    out = np.empty((rows.shape[0], n_cols), dtype=float)
    for j in range(n_cols):
        others = [c for c in range(n_cols) if c != j]
        # Design matrix of partners + intercept, fit on the baseline.
        x_base = np.hstack([baseline[:, others], np.ones((baseline.shape[0], 1))])
        coef, *_ = np.linalg.lstsq(x_base, baseline[:, j], rcond=None)
        x_rows = np.hstack([rows[:, others], np.ones((rows.shape[0], 1))])
        predicted = x_rows @ coef
        out[:, j] = rows[:, j] - predicted
    return out


def _downgrade_band(band: str) -> str:
    """Lower a severity band by one step (attention->review->info; info stays)."""
    idx = _SEVERITY_ORDER.index(band)
    return _SEVERITY_ORDER[max(0, idx - 1)]


def _apply_guardrail(
    findings: list[AnomalyFinding], *, user_id: int
) -> list[AnomalyFinding]:
    """Apply the cross-signal guardrail to a list of physiological findings.

    DECISION: when the recent window is a multivariate outlier (one metric moving
    while correlated partners did not — a likely single-sensor artifact) we
    DOWNGRADE each persistent_shift / combination finding by one severity band and
    EMIT one explanatory data_quality finding. We DOWNGRADE RATHER THAN SUPPRESS
    so a human can review and cancel the decision (Req 3.4/3.5/3.8); nothing is
    hidden silently.

    Returns the (possibly modified) list with any guardrail data_quality finding
    appended. If the guardrail did not run (too few samples / no sklearn) or the
    recent window is NOT an outlier, the list is returned unchanged.
    """
    physiological = [f for f in findings if f.finding_type in ("persistent_shift", "combination")]
    if not physiological:
        return findings

    is_outlier = _guardrail_recent_is_outlier(user_id=user_id)
    if is_outlier is None or not is_outlier:
        # Guardrail skipped (too few samples) or recent window is coherent ->
        # leave genuine multi-signal events un-downgraded.
        return findings

    downgraded_info = []
    for f in physiological:
        before = f.severity_band
        f.severity_band = _downgrade_band(before)  # type: ignore[assignment]
        downgraded_info.append(
            {"finding_type": f.finding_type, "metric": f.metric_type, "from": before, "to": f.severity_band}
        )

    # Emit ONE explanatory data_quality finding describing the sensor inconsistency.
    _, timestamps = _build_feature_matrix(user_id=user_id)
    start = timestamps[0] if timestamps else utc_now_iso()
    end = timestamps[-1] if timestamps else utc_now_iso()
    supporting = {
        "detector": "guardrail",
        "reason": "cross-signal inconsistency: recent window is a multivariate outlier "
        "consistent with a single-sensor artifact (one metric moved while correlated "
        "partners did not)",
        "feature_metrics": list(GUARDRAIL_FEATURE_METRICS),
        "downgrades": downgraded_info,
        "action": "downgraded coinciding physiological finding(s) by one band; NOT suppressed, "
        "open for human review/cancellation",
        "note": "descriptive guardrail decision, not a clinical risk score",
    }
    guardrail_finding = AnomalyFinding(
        metric_type="hr",
        finding_type="data_quality",
        severity_band="info",
        window_start=start,
        window_end=end,
        supporting=json.dumps(supporting, sort_keys=True),
        deviation=None,
        user_id=user_id,
    )
    return findings + [guardrail_finding]


# --------------------------------------------------------------------------- #
# Entry points for Task 11 (Jasper)
# --------------------------------------------------------------------------- #

# TASK 11 (Jasper): POST /analysis/run should call run_analysis().
def run_analysis(*, user_id: int = DEMO_USER_ID) -> list[AnomalyFinding]:
    """Refresh baselines, run all detectors, apply the guardrail, persist, return.

    PIPELINE (all deterministic for a fixed dataset + config, Req 3.7)
        1. Recompute each physiological baseline (hr/hrv/spo2) so detectors
           compare against an up-to-date reference.
        2. Run the four detectors:
             - data_quality for every metric (hr/hrv/spo2/rhythm);
             - persistent_shift for hr/hrv/spo2;
             - combination (hr+hrv);
             - rhythm_irregularity.
           Gappy windows only yield data_quality findings — the physiological
           detectors refuse to fire there (Req 3.4).
        3. Apply the IsolationForest cross-signal guardrail: downgrade coinciding
           persistent_shift/combination findings and append an explanatory
           data_quality finding (never silent suppression).
        4. Persist every finding via ``repository.insert_finding`` and return the
           in-memory list (with DB ids populated).

    REQUIREMENT: 3.3–3.8. Returns descriptive findings only; no clinical score.
    """
    for metric in _BASELINE_METRICS:
        compute_baseline(metric, user_id=user_id)

    findings: list[AnomalyFinding] = []

    # data_quality first — it also governs whether the others may fire.
    for metric in ("hr", "hrv", "spo2", "rhythm"):
        dq = detect_data_quality(metric, user_id=user_id)  # type: ignore[arg-type]
        if dq is not None:
            findings.append(dq)

    for metric in _BASELINE_METRICS:
        ps = detect_persistent_shift(metric, user_id=user_id)
        if ps is not None:
            findings.append(ps)

    combo = detect_combination(user_id=user_id)
    if combo is not None:
        findings.append(combo)

    rhythm = detect_rhythm_irregularity(user_id=user_id)
    if rhythm is not None:
        findings.append(rhythm)

    # Cross-signal guardrail (may downgrade + append a data_quality finding).
    findings = _apply_guardrail(findings, user_id=user_id)

    # Persist everything; populate ids on the in-memory objects.
    for f in findings:
        f.id = repo.insert_finding(f)

    return findings


# TASK 11 (Jasper): GET /trends should call get_trends().
def get_trends(range: str, *, user_id: int = DEMO_USER_ID) -> dict:
    """Aggregate measurements into daily/weekly/monthly buckets per metric.

    PURPOSE
        Back the GET /trends endpoint (Task 11, Req 5.1–5.3): resample the raw
        per-tick readings into coarse buckets the mobile history screen charts.

    RANGE
        One of {"daily", "weekly", "monthly"}. Any other value raises ``ValueError``
        (Jasper's route maps that to a 422). Resample rules (pandas offset
        aliases): daily -> 'D', weekly -> 'W', monthly -> 'MS' (month start).

    OUTPUT SHAPE
        ``{"range": <range>, "metrics": { <metric>: [ {"bucket": ISO,
        "mean": float|None, "count": int}, ... ] } }``. Only valid (non-null,
        quality 'ok') readings contribute to ``mean``/``count``; a bucket with no
        valid readings reports ``mean: None, count: 0``. Buckets are ascending.
        A metric with no data yields an empty list.

    REQUIREMENT: 5.1–5.3 (daily/weekly/monthly trends); 7.4 (invalid range error).
    """
    freq_map = {"daily": "D", "weekly": "W", "monthly": "MS"}
    if range not in freq_map:
        raise ValueError(
            f"invalid range '{range}'; expected one of {sorted(freq_map)}"
        )
    freq = freq_map[range]

    metrics_out: dict[str, list[dict]] = {}
    for metric in ("hr", "hrv", "spo2", "rhythm", "activity", "sleep"):
        rows = repo.query_measurements(metric_type=metric, user_id=user_id)
        valid = [m for m in rows if m.value is not None and m.quality == "ok"]
        if not valid:
            metrics_out[metric] = []
            continue

        frame = pd.DataFrame(
            {
                "timestamp": pd.to_datetime([m.timestamp for m in valid], utc=True),
                "value": [float(m.value) for m in valid],
            }
        ).set_index("timestamp")

        grouped = frame["value"].resample(freq)
        agg = grouped.agg(["mean", "count"])
        buckets = []
        for bucket_ts, row in agg.iterrows():
            count = int(row["count"])
            buckets.append(
                {
                    "bucket": bucket_ts.isoformat(),
                    "mean": float(row["mean"]) if count > 0 else None,
                    "count": count,
                }
            )
        metrics_out[metric] = buckets

    return {"range": range, "metrics": metrics_out}
