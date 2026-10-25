"""Pure ECG-motion fusion with no I/O, network, or wall-clock dependency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from . import config
from .motion import MotionFeatures, MotionTrackerState, track_motion


@dataclass(frozen=True)
class FusionState:
    recent_reliability: tuple[bool, ...] = ()
    reliable_probabilities: tuple[tuple[int, float], ...] = ()
    motion: MotionTrackerState = MotionTrackerState()
    last_watch_seconds: float | None = None
    last_corroboration_seconds: float | None = None
    last_corroboration: str | None = None
    warning_active: bool = False


@dataclass(frozen=True)
class WindowInput:
    index: int
    af_probability: float | None
    motion: MotionFeatures


@dataclass(frozen=True)
class FusionOutput:
    index: int
    state: str
    reliable: bool
    af_probability: float | None
    watch: bool
    watch_count: int
    corroboration: str | None
    warning_trigger: bool
    downgrade_reason: str | None


def step(
    state: FusionState,
    window: WindowInput,
    threshold: float,
    *,
    k: int = config.FUSION_K,
    n: int = config.FUSION_N,
) -> tuple[FusionState, FusionOutput]:
    if not (0.0 <= threshold <= 1.0):
        raise ValueError("threshold must be within [0, 1]")
    if not (1 <= k <= n):
        raise ValueError("fusion requires 1 <= k <= n")

    signal_time = float(window.index * config.WINDOW_SECONDS)
    reliable = not window.motion.artifact and window.af_probability is not None
    recent = (state.recent_reliability + (reliable,))[-n:]
    probabilities = state.reliable_probabilities
    if reliable:
        probabilities = probabilities + ((window.index, float(window.af_probability)),)
    probabilities = probabilities[-n:]
    watch_count = sum(probability > threshold for _, probability in probabilities)
    watch = watch_count >= k

    motion_state, corroboration = track_motion(state.motion, window.motion, signal_time)
    last_watch = signal_time if watch else state.last_watch_seconds
    last_corroboration = signal_time if corroboration is not None else state.last_corroboration_seconds
    last_corroboration_kind = corroboration or state.last_corroboration
    warning = (
        watch
        and last_corroboration is not None
        and signal_time - last_corroboration <= config.FUSION_COINCIDENCE_SECONDS
    ) or (
        corroboration is not None
        and last_watch is not None
        and signal_time - last_watch <= config.FUSION_COINCIDENCE_SECONDS
    )
    warning_trigger = bool(warning and not state.warning_active)

    data_quality = bool(recent) and sum(not item for item in recent) > config.FUSION_DATA_QUALITY_FRACTION * len(recent)
    if warning:
        display_state = "warning"
    elif watch:
        display_state = "watch"
    elif data_quality:
        display_state = "data_quality"
    else:
        display_state = "normal"

    if window.motion.artifact:
        downgrade = "motion_artifact_excluded"
    elif window.af_probability is None:
        downgrade = "invalid_ecg_features"
    elif watch:
        downgrade = "watch_without_corroborating_motion" if not warning else None
    else:
        downgrade = None

    new_state = FusionState(
        recent_reliability=recent,
        reliable_probabilities=probabilities,
        motion=motion_state,
        last_watch_seconds=last_watch,
        last_corroboration_seconds=last_corroboration,
        last_corroboration=last_corroboration_kind,
        warning_active=bool(warning),
    )
    return new_state, FusionOutput(
        index=window.index,
        state=display_state,
        reliable=reliable,
        af_probability=window.af_probability,
        watch=watch,
        watch_count=watch_count,
        corroboration=corroboration,
        warning_trigger=warning_trigger,
        downgrade_reason=downgrade,
    )


def run_sequence(
    windows: Iterable[WindowInput], threshold: float, state: FusionState = FusionState()
) -> tuple[FusionState, list[FusionOutput]]:
    outputs: list[FusionOutput] = []
    for window in windows:
        state, output = step(state, window, threshold)
        outputs.append(output)
    return state, outputs


def watch_occurrences(windows: Iterable[WindowInput], threshold: float) -> int:
    """Count Watch-condition windows; raising threshold cannot increase this count."""
    _, outputs = run_sequence(windows, threshold)
    return sum(output.watch for output in outputs)
