"""Single, transparent configuration for the HeartGuardian AI analysis engine.

PURPOSE
-------
This module is the ONE place where every demonstration threshold, window length,
and tuning constant used by the analysis engine lives (Requirement 3.6). Nothing
in ``services/analysis.py`` (baseline + rolling stats, Task 9) or in the upcoming
anomaly detectors (Task 10) should hard-code a numeric threshold: it should read
it from here. Centralizing the config is what makes the engine's behavior
transparent and auditable, and — together with fixed input data — reproducible
(Requirement 3.7): the same data plus the same constants here always yields the
same baselines, rolling statistics, and findings.

WHY A MODULE OF CONSTANTS
-------------------------
These are plain module-level constants plus a frozen dataclass holding the
rolling-window sizes. Plain constants keep the "single source of truth" trivially
greppable and importable; the frozen dataclass groups the per-use-case window
sizes and prevents accidental mutation at runtime (so a run can't silently
change its own config midway and break reproducibility).

Each value documents its purpose inline. Values are chosen for a demo whose
simulator (Task 6) emits roughly hourly ticks spanning a few weeks; they are not
clinical parameters.
"""
from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Baseline configuration (Req 3.1)
# --------------------------------------------------------------------------- #

# How many of the most-recent valid (quality == 'ok', non-null) samples define a
# metric's personal baseline. The baseline is the trailing reference the engine
# compares current behavior against; a few weeks of hourly ticks lands in the low
# thousands of samples, so this cap keeps the baseline "recent" while still
# averaging out short-term noise. A smaller/larger window can be passed per-call,
# but this is the default used everywhere unless overridden.
BASELINE_WINDOW: int = 2000

# Minimum number of valid samples required for a baseline to be considered
# statistically meaningful. Below this the baseline is still computed (so the
# pipeline never crashes on thin data) but is flagged as low-confidence via its
# ``sample_count`` — downstream detectors (Task 10) can choose to treat a
# low-sample baseline as a data-quality issue rather than a physiological trend
# (Req 3.4). Chosen so that at least a couple of days of hourly ticks exist.
MIN_BASELINE_SAMPLES: int = 48

# --------------------------------------------------------------------------- #
# Rolling-statistics configuration (Req 3.2)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RollingWindows:
    """Rolling-window sizes (in number of samples) for rolling statistics.

    Frozen so the configuration cannot be mutated at runtime, protecting
    reproducibility. ``default`` is used by ``rolling_stats`` when no explicit
    window is given; ``short`` and ``long`` are provided for Task 10's detectors
    that compare a fast-moving window against a slower one.
    """

    # Default rolling window: the number of trailing samples summarized into the
    # current rolling mean/std/trend. ~24 hourly ticks ≈ one day of context.
    default: int = 24
    # Short window for fast-reacting comparisons (about half a day).
    short: int = 12
    # Long window for slow/sustained-change comparisons (about three days).
    long: int = 72


ROLLING_WINDOWS: RollingWindows = RollingWindows()

# Convenience alias for the common case (single source for "the rolling window").
ROLLING_WINDOW: int = ROLLING_WINDOWS.default

# Smallest divisor allowed when standardizing a deviation by the baseline std.
# If a baseline's std is at or below this (e.g. a perfectly flat metric, or the
# 0/1 rhythm flag that happened to be constant), we treat the deviation as
# undefined and return 0.0 rather than dividing by ~zero and producing an
# explosive/NaN value. Keeps deviations finite and reproducible.
MIN_STD_FOR_DEVIATION: float = 1e-9

# --------------------------------------------------------------------------- #
# Reproducibility (Req 3.7) — shared seed
# --------------------------------------------------------------------------- #

# Fixed seed for any stochastic component in the analysis engine. Baseline and
# rolling-stats math (Task 9) are fully deterministic and do not use it, but the
# scikit-learn-based anomaly detector added in Task 10 (e.g. IsolationForest) is
# seeded with this so its output is reproducible for a fixed input + config. It
# is defined here now so the single config location truly owns every tuning knob.
RANDOM_STATE: int = 42

# =========================================================================== #
# Task 10 — anomaly-detector thresholds (Req 3.3–3.8)
# =========================================================================== #
#
# Everything below is the single source of truth for the four anomaly detectors
# and the scikit-learn cross-signal guardrail added in Task 10. Nothing in
# ``services/analysis.py`` should hard-code any of these numbers — it reads them
# from here so the engine stays transparent/auditable (Req 3.6) and, together
# with a fixed input dataset and the fixed RANDOM_STATE above, reproducible
# (Req 3.7). None of these are clinical parameters; they are demo tuning knobs
# chosen for the simulator's roughly-hourly ticks.

# --------------------------------------------------------------------------- #
# persistent_shift detector (Req 3.3)
# --------------------------------------------------------------------------- #

# A sustained deviation fires only when the |standardized deviation| of the
# sustained (long) window's mean from the baseline meets or exceeds this many
# baseline standard deviations. Expressed in units of baseline std so it is
# scale-free across metrics. 1.5σ is a deliberately sensitive demo threshold.
PERSISTENT_SHIFT_MIN_DEVIATION: float = 1.5

# The sustained window (in samples) over which the shift must hold. We summarize
# the trailing ``ROLLING_WINDOWS.long`` samples and require the shift to be
# present in that whole window, so a single-tick spike does not fire the
# detector — the change has to persist. Pulled from the shared long window so
# "sustained" means the same thing everywhere.
PERSISTENT_SHIFT_WINDOW: int = ROLLING_WINDOWS.long

# Severity bands are scaled by the magnitude of the |deviation| (in baseline
# std). At/above REVIEW but below ATTENTION -> 'review'; at/above ATTENTION ->
# 'attention'; at/above the fire threshold but below REVIEW -> 'info'. Keeping
# the band cut-points here (not in code) makes the escalation auditable.
PERSISTENT_SHIFT_BAND_REVIEW: float = 2.0
PERSISTENT_SHIFT_BAND_ATTENTION: float = 3.0

# --------------------------------------------------------------------------- #
# combination detector — HR up AND HRV down together (Scenario B signature, Req 3.3)
# --------------------------------------------------------------------------- #

# The combination finding fires ONLY when BOTH metrics move beyond threshold in
# the correct directions at once: HR's standardized deviation is at/above
# +HR_UP and HRV's is at/below -HRV_DOWN. Requiring both guards against a single
# metric drifting on its own (that is persistent_shift's job, not combination's).
# Thresholds are in baseline-std units, like persistent_shift.
COMBINATION_HR_UP_DEVIATION: float = 1.0
COMBINATION_HRV_DOWN_DEVIATION: float = 1.0

# Severity for the combination finding, scaled by the smaller of the two
# magnitudes (the weakest leg gates the combined severity so one strong + one
# barely-past-threshold leg does not over-escalate). Cut-points in baseline std.
COMBINATION_BAND_REVIEW: float = 1.5
COMBINATION_BAND_ATTENTION: float = 2.5

# --------------------------------------------------------------------------- #
# rhythm_irregularity detector (Req 3.3 / 3.5 — Scenario C signature)
# --------------------------------------------------------------------------- #

# rhythm is a 0/1 irregular-rhythm flag. We look at the recent window and fire
# when the *rate* of irregular flags (mean of the 0/1 series) meets or exceeds
# this fraction. 0.30 => at least ~30% of recent readings flagged irregular.
RHYTHM_IRREGULARITY_RATE: float = 0.30

# The recent window (in samples) the irregular-rate is measured over. Uses the
# shared default rolling window (~one day of hourly ticks).
RHYTHM_IRREGULARITY_WINDOW: int = ROLLING_WINDOWS.default

# Severity bands for rhythm, scaled by the irregular-rate itself (a fraction in
# [0,1]). At/above REVIEW -> 'review'; at/above ATTENTION -> 'attention';
# at/above the fire rate but below REVIEW -> 'info'.
RHYTHM_BAND_REVIEW: float = 0.50
RHYTHM_BAND_ATTENTION: float = 0.75

# --------------------------------------------------------------------------- #
# data_quality detector (Req 3.4)
# --------------------------------------------------------------------------- #

# When the fraction of missing/low-quality samples in the recent window meets or
# exceeds this, the window is classified as a DATA-QUALITY issue (a sensor gap),
# NOT a physiological trend. The physiological detectors independently refuse to
# fire on such a window (see ``_window_has_enough_quality``) so a gap can never
# be misread as a trend. 0.40 => 40%+ of the window is missing/low.
DATA_QUALITY_MISSING_FRACTION: float = 0.40

# The recent window (in samples, counting ALL readings regardless of quality)
# over which the missing/low fraction is measured.
DATA_QUALITY_WINDOW: int = ROLLING_WINDOWS.default

# Minimum fraction of VALID samples a physiological detector requires in its
# window before it is willing to fire at all. This is the mirror image of the
# data_quality threshold and is what structurally prevents a gappy window from
# being read as a trend (Req 3.4): if valid-fraction < this, persistent_shift /
# combination / rhythm stay silent and only data_quality may speak.
MIN_VALID_FRACTION_FOR_TREND: float = 0.60

# --------------------------------------------------------------------------- #
# scikit-learn cross-signal guardrail (IsolationForest)
# --------------------------------------------------------------------------- #
#
# RATIONALE: a single physiological sensor can drift or glitch on its own (a loose
# strap, a motion artifact). Treating such a solo drift as a physiological event
# produces false positives. By looking at several metrics TOGETHER we can tell a
# coherent whole-body change (HR up WHILE HRV down WHILE partners move
# consistently — a real Scenario-B-like event) apart from one metric wandering
# while its correlated partners stay flat (a likely sensor artifact).
#
# MECHANISM: each run we fit a fresh IsolationForest on the aligned multi-metric
# matrix over the baseline window (no stored model; fit → score → discard), score
# the current/recent window, and if a physiological finding COINCIDES with the
# current sample being a multivariate outlier, we DOWNGRADE that finding one band
# (attention->review->info) and EMIT a data_quality finding explaining the sensor
# inconsistency. We downgrade rather than suppress so a human can review and undo
# the decision (Req 3.4/3.5/3.8) — nothing is hidden silently.

# The metrics whose aligned per-tick values form the guardrail feature matrix.
# EXTENSION POINT: to add a future signal (e.g. an accelerometer or a composite
# feature), append its metric_type here — the matrix builder, the fit, and the
# scoring all read this list, so no other code needs to change. Keep these as
# continuous-valued metrics (rhythm's 0/1 flag is intentionally excluded).
GUARDRAIL_FEATURE_METRICS: tuple[str, ...] = ("hr", "hrv", "spo2", "activity")

# IsolationForest hyper-parameters. ``random_state`` is taken from the shared
# RANDOM_STATE above so two runs over the same data make IDENTICAL downgrade
# decisions (Req 3.7). ``contamination`` is the expected outlier fraction used to
# place the decision threshold; ``n_estimators`` is the number of trees.
GUARDRAIL_N_ESTIMATORS: int = 200
GUARDRAIL_CONTAMINATION: float = 0.05

# Too-few-samples guard: if the aligned feature matrix has fewer than this many
# complete rows, the guardrail is skipped cleanly (no fit, no downgrade, no
# crash). IsolationForest needs a reasonable sample to place a stable threshold.
GUARDRAIL_MIN_SAMPLES: int = 50

# How many of the most-recent aligned rows count as the "current window" that is
# scored against the fitted forest. A physiological finding is downgraded only if
# any row in this recent window is flagged a cross-signal artifact.
GUARDRAIL_RECENT_WINDOW: int = ROLLING_WINDOWS.short

# Residual-consistency threshold (in baseline-residual std units). This is the
# ACTUAL discriminator the guardrail keys off (see analysis.py): for each feature
# metric we compute the residual of its value vs. a linear prediction from its
# PARTNER metrics, learned on the baseline. A coherent whole-body event preserves
# those partner relationships -> small residual; a single-sensor drift breaks them
# -> large residual. The recent window is flagged a single-sensor artifact when
# any metric's residual z-score meets or exceeds this. A plain multivariate
# outlier test cannot make this coherent-vs-drift distinction (any strong
# excursion looks anomalous), which is why the residual rule exists. 4.0σ is a
# deliberately conservative cut so only clear partner-inconsistencies downgrade.
GUARDRAIL_RESIDUAL_Z: float = 4.0
