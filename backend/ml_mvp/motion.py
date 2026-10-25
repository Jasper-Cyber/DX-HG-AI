"""Transparent, deterministic motion features and corroboration rules."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config


@dataclass(frozen=True)
class MotionFeatures:
    magnitude_mean_g: float
    magnitude_variance_g2: float
    energy_g2: float
    posture_angle_deg: float
    jerk_rms_g_per_s: float
    peak_g: float
    activity_state: str
    artifact: bool


@dataclass(frozen=True)
class MotionTrackerState:
    previous_state: str | None = None
    inactivity_bout: bool = False
    inactive_seconds: float = 0.0
    last_impact_seconds: float | None = None


def motion_features(acceleration_g: np.ndarray, fs: int = config.MOTION_FS_HZ) -> MotionFeatures:
    acceleration = np.asarray(acceleration_g, dtype=np.float64)
    if acceleration.ndim != 2 or acceleration.shape[1] != 3 or acceleration.shape[0] < 2:
        raise ValueError("motion window must have shape (samples, 3)")
    if not np.isfinite(acceleration).all():
        raise ValueError("motion window contains non-finite values")

    magnitude = np.linalg.norm(acceleration, axis=1)
    mean_vector = np.mean(acceleration, axis=0)
    gravity_norm = float(np.linalg.norm(mean_vector))
    vertical = abs(float(mean_vector[config.MOTION_VERTICAL_AXIS]))
    cosine = np.clip(vertical / gravity_norm, 0.0, 1.0) if gravity_norm > 1e-9 else 0.0
    posture = float(np.degrees(np.arccos(cosine)))
    energy = float(np.mean(np.var(acceleration, axis=0)))
    magnitude_variance = float(np.var(magnitude))
    jerk = float(np.sqrt(np.mean((np.diff(magnitude) * fs) ** 2)))

    if energy > config.MOTION_DYNAMIC_ENERGY_G2:
        state = "dynamic"
    elif posture > config.MOTION_LYING_ANGLE_DEG:
        state = "lying"
    else:
        state = "static"
    artifact = (
        magnitude_variance > config.MOTION_ARTIFACT_MAG_VAR_G2
        or jerk > config.MOTION_ARTIFACT_JERK_RMS_GPS
    )
    return MotionFeatures(
        magnitude_mean_g=float(np.mean(magnitude)),
        magnitude_variance_g2=magnitude_variance,
        energy_g2=energy,
        posture_angle_deg=posture,
        jerk_rms_g_per_s=jerk,
        peak_g=float(np.max(magnitude)),
        activity_state=state,
        artifact=bool(artifact),
    )


def track_motion(
    state: MotionTrackerState,
    features: MotionFeatures,
    signal_time_seconds: float,
) -> tuple[MotionTrackerState, str | None]:
    entered_lying = state.previous_state != "lying" and features.activity_state == "lying"
    bout = state.inactivity_bout or entered_lying
    inactive = state.inactive_seconds
    if bout:
        qualifying = (
            features.activity_state in {"lying", "static"}
            and features.energy_g2 < config.MOTION_INACTIVITY_ENERGY_G2
            and not features.artifact
        )
        if qualifying:
            inactive += config.WINDOW_SECONDS
        else:
            bout = False
            inactive = 0.0

    last_impact = state.last_impact_seconds
    corroboration: str | None = None
    if features.peak_g > config.MOTION_IMPACT_PEAK_G:
        last_impact = signal_time_seconds
    elif (
        last_impact is not None
        and 0.0 < signal_time_seconds - last_impact <= config.MOTION_COLLAPSE_GAP_SECONDS
        and features.activity_state in {"lying", "static"}
    ):
        corroboration = "collapse"
        last_impact = None
    if corroboration is None and bout and inactive >= config.PROLONGED_INACTIVITY_SECONDS:
        corroboration = "prolonged_inactivity"

    return (
        MotionTrackerState(
            previous_state=features.activity_state,
            inactivity_bout=bout,
            inactive_seconds=inactive,
            last_impact_seconds=last_impact,
        ),
        corroboration,
    )
