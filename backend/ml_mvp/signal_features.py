"""Deterministic ECG R-peak detection and interpretable HRV features."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config

FEATURE_ORDER = ("rmssd_ms", "sdnn_ms", "pnn50_pct", "mean_hr_bpm", "rr_irregularity")


@dataclass(frozen=True)
class HrvFeatures:
    rmssd_ms: float
    sdnn_ms: float
    pnn50_pct: float
    mean_hr_bpm: float
    rr_irregularity: float
    n_beats: int
    rr_ms: tuple[float, ...]

    def as_vector(self) -> np.ndarray:
        return np.asarray([getattr(self, name) for name in FEATURE_ORDER], dtype=np.float64)


def window_quality_ok(window: np.ndarray) -> bool:
    signal = np.asarray(window, dtype=np.float64).reshape(-1)
    return signal.size == config.WINDOW_SAMPLES and np.isfinite(signal).all() and float(np.std(signal)) > 1e-3


def detect_r_peaks(window: np.ndarray, fs: int = config.TARGET_FS_HZ) -> np.ndarray:
    signal = np.asarray(window, dtype=np.float64).reshape(-1)
    if not window_quality_ok(signal):
        return np.empty(0, dtype=np.int32)

    centered = signal - np.median(signal)
    energy = np.gradient(centered) ** 2
    width = max(3, int(round(0.15 * fs)))
    integrated = np.convolve(energy, np.ones(width, dtype=np.float64) / width, mode="same")
    threshold = 0.25 * float(np.percentile(integrated, 99))
    active = integrated > threshold
    edges = np.diff(np.pad(active.astype(np.int8), (1, 1)))
    starts = np.flatnonzero(edges == 1)
    stops = np.flatnonzero(edges == -1)
    extension = max(1, int(round(0.05 * fs)))
    candidates: list[int] = []
    for start, stop in zip(starts, stops):
        lo = max(0, int(start) - extension)
        hi = min(signal.size, int(stop) + extension)
        if hi > lo:
            candidates.append(lo + int(np.argmax(np.abs(centered[lo:hi]))))

    refractory = max(1, int(round(0.25 * fs)))
    kept: list[int] = []
    for candidate in sorted(set(candidates)):
        if not kept or candidate - kept[-1] >= refractory:
            kept.append(candidate)
        elif abs(centered[candidate]) > abs(centered[kept[-1]]):
            kept[-1] = candidate
    return np.asarray(kept, dtype=np.int32)


def rr_intervals_ms(peaks: np.ndarray, fs: int = config.TARGET_FS_HZ) -> np.ndarray:
    rr = np.diff(np.asarray(peaks, dtype=np.float64)) * 1000.0 / fs
    return rr[(rr >= config.RR_MIN_MS) & (rr <= config.RR_MAX_MS)]


def hrv_features(window: np.ndarray, fs: int = config.TARGET_FS_HZ) -> HrvFeatures | None:
    peaks = detect_r_peaks(window, fs)
    if peaks.size < config.MIN_R_PEAKS:
        return None
    rr = rr_intervals_ms(peaks, fs)
    if rr.size < 2:
        return None
    differences = np.diff(rr)
    if differences.size == 0 or float(np.median(rr)) <= 0:
        return None
    return HrvFeatures(
        rmssd_ms=float(np.sqrt(np.mean(differences**2))),
        sdnn_ms=float(np.std(rr, ddof=1)),
        pnn50_pct=float(100.0 * np.mean(np.abs(differences) > 50.0)),
        mean_hr_bpm=float(60000.0 / np.mean(rr)),
        rr_irregularity=float(np.median(np.abs(differences)) / np.median(rr)),
        n_beats=int(peaks.size),
        rr_ms=tuple(float(value) for value in rr),
    )


def feature_matrix(windows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return finite feature rows and a validity mask without inventing values."""
    rows: list[np.ndarray] = []
    valid = np.zeros(len(windows), dtype=np.bool_)
    for index, window in enumerate(windows):
        features = hrv_features(window)
        if features is not None:
            valid[index] = True
            rows.append(features.as_vector())
    matrix = np.stack(rows) if rows else np.empty((0, len(FEATURE_ORDER)), dtype=np.float64)
    return matrix, valid
