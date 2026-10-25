"""Focused unit and property-style tests for the isolated ECG-motion MVP."""

from __future__ import annotations

import numpy as np
import pytest

from ml_mvp import config
from ml_mvp.demo import run_persona
from ml_mvp.fusion import FusionState, WindowInput, run_sequence, watch_occurrences
from ml_mvp.motion import MotionFeatures, motion_features
from ml_mvp.signal_features import detect_r_peaks, hrv_features
from ml_mvp.warning import CliWarningMachine


def _motion(*, state: str = "static", artifact: bool = False, energy: float = 0.0) -> MotionFeatures:
    return MotionFeatures(
        magnitude_mean_g=1.0,
        magnitude_variance_g2=config.MOTION_ARTIFACT_MAG_VAR_G2 + 0.01 if artifact else 0.0,
        energy_g2=energy,
        posture_angle_deg=75.0 if state == "lying" else 0.0,
        jerk_rms_g_per_s=config.MOTION_ARTIFACT_JERK_RMS_GPS + 0.01 if artifact else 0.0,
        peak_g=1.0,
        activity_state=state,
        artifact=artifact,
    )


def _pulse_train(rr_samples: int, polarity: float) -> tuple[np.ndarray, np.ndarray]:
    peaks = np.arange(rr_samples // 2, config.WINDOW_SAMPLES, rr_samples, dtype=np.int32)
    signal = np.zeros(config.WINDOW_SAMPLES, dtype=np.float64)
    kernel = polarity * np.asarray([0.2, 0.7, 1.0, 0.7, 0.2])
    for peak in peaks:
        if 2 <= peak < signal.size - 2:
            signal[peak - 2 : peak + 3] += kernel
    return signal, peaks


@pytest.mark.parametrize(("rr_samples", "polarity"), [(75, 1.0), (100, -1.0), (125, 1.0)])
def test_ecg_features_are_deterministic_and_follow_hrv_formulas(rr_samples: int, polarity: float) -> None:
    """Property 8: deterministic peaks and HRV formulas hold across pulse rates.

    **Validates: Requirements 6.1, 6.4**
    """
    signal, expected_peaks = _pulse_train(rr_samples, polarity)
    first_peaks = detect_r_peaks(signal)
    second_peaks = detect_r_peaks(signal.copy())
    first = hrv_features(signal)
    second = hrv_features(signal.copy())

    assert np.array_equal(first_peaks, second_peaks)
    assert first == second
    assert first is not None
    assert len(first_peaks) == len(expected_peaks)
    assert np.max(np.abs(first_peaks - expected_peaks)) <= 5

    rr = np.diff(first_peaks) * 1000.0 / config.TARGET_FS_HZ
    differences = np.diff(rr)
    assert first.rmssd_ms == pytest.approx(np.sqrt(np.mean(differences**2)))
    assert first.sdnn_ms == pytest.approx(np.std(rr, ddof=1))
    assert first.pnn50_pct == pytest.approx(100.0 * np.mean(np.abs(differences) > 50.0))
    assert first.mean_hr_bpm == pytest.approx(60000.0 / np.mean(rr))
    assert first.rr_irregularity == pytest.approx(np.median(np.abs(differences)) / np.median(rr))


@pytest.mark.parametrize(
    "invalid_window",
    [
        np.zeros(config.WINDOW_SAMPLES),
        np.full(config.WINDOW_SAMPLES, np.nan),
        np.pad(np.asarray([1.0, 0.0, 1.0]), (0, config.WINDOW_SAMPLES - 3)),
    ],
    ids=["flat", "non-finite", "fewer-than-three-pulses"],
)
def test_invalid_ecg_windows_return_no_features(invalid_window: np.ndarray) -> None:
    """Property 8: invalid windows become data-quality cases, not probabilities.

    **Validates: Requirement 6.4**
    """
    assert hrv_features(invalid_window) is None


@pytest.mark.parametrize(
    ("angle_deg", "amplitude_g", "frequency_hz"),
    [(0.0, 0.0, 0.5), (30.0, 0.2, 1.0), (75.0, 0.4, 2.0)],
)
def test_motion_features_follow_transparent_rule_ladder(
    angle_deg: float, amplitude_g: float, frequency_hz: float
) -> None:
    """Property 14: motion features and state classification follow configured rules.

    **Validates: Requirements 11.1, 11.2, 11.3**
    """
    time_s = np.arange(config.MOTION_WINDOW_SAMPLES) / config.MOTION_FS_HZ
    angle_rad = np.deg2rad(angle_deg)
    acceleration = np.column_stack(
        (
            np.full(time_s.size, np.cos(angle_rad)),
            np.full(time_s.size, np.sin(angle_rad)),
            amplitude_g * np.sin(2.0 * np.pi * frequency_hz * time_s),
        )
    )
    features = motion_features(acceleration)
    expected_energy = amplitude_g**2 / 6.0
    if expected_energy > config.MOTION_DYNAMIC_ENERGY_G2:
        expected_state = "dynamic"
    elif angle_deg > config.MOTION_LYING_ANGLE_DEG:
        expected_state = "lying"
    else:
        expected_state = "static"

    assert features.posture_angle_deg == pytest.approx(angle_deg, abs=2.0)
    assert features.energy_g2 == pytest.approx(expected_energy, rel=0.05, abs=1e-12)
    assert features.activity_state == expected_state
    assert features.activity_state in {"dynamic", "static", "lying"}
    assert features.artifact is (
        features.magnitude_variance_g2 > config.MOTION_ARTIFACT_MAG_VAR_G2
        or features.jerk_rms_g_per_s > config.MOTION_ARTIFACT_JERK_RMS_GPS
    )


def test_motion_artifact_is_excluded_from_fusion_watch_count() -> None:
    """Property 17: artifact-paired ECG is unreliable and excluded from K-of-N.

    **Validates: Requirements 12.3, 12.4, 21.2**
    """
    windows = [WindowInput(0, 0.99, _motion(artifact=True))]
    windows.extend(WindowInput(index, 0.99, _motion()) for index in range(1, 4))
    _, outputs = run_sequence(windows, threshold=0.5)

    assert outputs[0].reliable is False
    assert outputs[0].watch_count == 0
    assert outputs[0].downgrade_reason == "motion_artifact_excluded"
    assert [output.watch for output in outputs] == [False, False, False, True]
    assert all(not output.warning_trigger for output in outputs)


def test_fusion_is_deterministic_and_chunk_invariant() -> None:
    """Property 18: replay and chunked execution produce identical pure outputs.

    **Validates: Requirement 12.9**
    """
    probabilities = [0.1, 0.9, None, 0.8, 0.95, 0.2, 0.99]
    windows = [
        WindowInput(index, probability, _motion(artifact=index == 2))
        for index, probability in enumerate(probabilities)
    ]
    final_a, outputs_a = run_sequence(windows, threshold=0.7)
    final_b, outputs_b = run_sequence(windows, threshold=0.7)
    chunk_state, first_chunk = run_sequence(windows[:3], threshold=0.7, state=FusionState())
    chunk_state, second_chunk = run_sequence(windows[3:], threshold=0.7, state=chunk_state)

    assert final_a == final_b == chunk_state
    assert outputs_a == outputs_b == first_chunk + second_chunk


@pytest.mark.parametrize(
    ("probabilities", "low", "high"),
    [
        ([0.1, 0.2, 0.3, 0.4, 0.5], 0.2, 0.4),
        ([0.9, 0.8, 0.7, 0.6, 0.5], 0.4, 0.75),
        ([0.51, None, 0.52, 0.49, 0.9, 0.1], 0.5, 0.8),
    ],
)
def test_raising_threshold_never_increases_watch_occurrences(
    probabilities: list[float | None], low: float, high: float
) -> None:
    """Property 19: Watch occurrences are monotone under a raised threshold.

    **Validates: Requirement 12.10**
    """
    windows = [
        WindowInput(index, probability, _motion())
        for index, probability in enumerate(probabilities)
    ]
    assert watch_occurrences(windows, high) <= watch_occurrences(windows, low)


@pytest.mark.parametrize("repeat_count", [1, 2, 5, 20])
def test_cancel_is_idempotent_for_any_repeat_count(repeat_count: int) -> None:
    """Property 25: repeated CLI cancellation preserves the first terminal event.

    **Validates: Requirement 15.2**
    """
    machine = CliWarningMachine(countdown_seconds=0.2)
    machine.raise_warning(now_seconds=1.0)
    first_event, changed = machine.cancel(now_seconds=1.1)
    assert changed is True

    for index in range(repeat_count):
        repeated_event, repeated_changed = machine.cancel(now_seconds=2.0 + index)
        assert repeated_changed is False
        assert repeated_event == first_event
    assert machine.simulated_escalations == 0


@pytest.mark.parametrize("persona", ["healthy", "possible_acute_event", "false_alarm"])
def test_personas_have_expected_outcomes_and_are_deterministic(persona: str) -> None:
    """Property 28: fresh real-data persona replays have deterministic outcomes.

    **Validates: Requirements 18.4, 18.5, 19.2, 20.3**
    """
    first = run_persona(persona, countdown_seconds=0.2)
    second = run_persona(persona, countdown_seconds=0.2)
    assert first == second
    assert first["experimentalNonDiagnostic"] is True
    assert first["warningLifecycle"]["networkOrNotificationAction"] is False
    assert "different people and datasets" in first["dataDisclosure"]

    if persona == "healthy":
        assert first["fusion"]["warningCount"] == 0
        assert first["warningLifecycle"]["status"] == "none"
    elif persona == "possible_acute_event":
        transitions = first["fusion"]["stateTransitions"]
        assert all(state in transitions for state in ("normal", "watch", "warning"))
        assert first["warningLifecycle"]["status"] == "escalated"
        assert first["warningLifecycle"]["escalationChannel"] == "simulated_cli_only"
        assert "SIMULATED escalation" in first["warningLifecycle"]["message"]
    else:
        assert first["fusion"]["warningCount"] == 0
        assert first["fusion"]["guardrailDowngradeCount"] >= 1
        assert "motion_artifact_excluded" in first["fusion"]["guardrailDowngradeReasons"]
