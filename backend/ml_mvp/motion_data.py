"""Acquire and extract a small, traceable real UCI HAPT motion fixture."""

from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from . import config
from .io_utils import download_file, sha256_file, write_canonical_json, write_npz_deterministic
from .motion import motion_features

ACTIVITY_NAMES = {
    1: "walking",
    2: "walking_upstairs",
    3: "walking_downstairs",
    4: "sitting",
    5: "standing",
    6: "lying",
    9: "sit_to_lie",
    11: "stand_to_lie",
}


def _member_ending(archive: zipfile.ZipFile, ending: str) -> str:
    normalized = ending.replace("\\", "/").lower()
    matches = [name for name in archive.namelist() if name.replace("\\", "/").lower().endswith(normalized)]
    if not matches:
        raise FileNotFoundError(f"UCI HAPT archive member missing: {ending}")
    return min(matches, key=len)


def _load_text_matrix(archive: zipfile.ZipFile, member: str) -> np.ndarray:
    matrix = np.loadtxt(io.BytesIO(archive.read(member)), dtype=np.float64)
    return np.atleast_2d(matrix)


def build_motion_subset() -> dict[str, Any]:
    deadline = time.monotonic() + 300.0
    raw = download_file(
        config.HAPT_SOURCE_URL,
        config.HAPT_ARCHIVE_FILE,
        deadline,
        config.DOWNLOAD_TIMEOUT_SECONDS,
    )
    if raw["bytes"] > 200 * 1024 * 1024:
        raise RuntimeError("UCI HAPT archive exceeds the bounded 200 MB task limit")

    records: list[dict[str, Any]] = []
    acceleration_rows: list[np.ndarray] = []
    gyroscope_rows: list[np.ndarray] = []
    loaded: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
    with zipfile.ZipFile(config.HAPT_ARCHIVE_FILE) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise RuntimeError(f"corrupt UCI HAPT archive member: {corrupt}")
        labels_member = _member_ending(archive, "RawData/labels.txt")
        labels = _load_text_matrix(archive, labels_member).astype(np.int64)
        for activity_id, activity_name in ACTIVITY_NAMES.items():
            candidates = labels[labels[:, 2] == activity_id]
            if candidates.size == 0:
                continue
            for experiment, subject, _, segment_start, segment_end in candidates:
                key = (int(experiment), int(subject))
                if key not in loaded:
                    stem = f"exp{experiment:02d}_user{subject:02d}.txt"
                    acc_member = _member_ending(archive, f"RawData/acc_{stem}")
                    gyro_member = _member_ending(archive, f"RawData/gyro_{stem}")
                    loaded[key] = (
                        _load_text_matrix(archive, acc_member),
                        _load_text_matrix(archive, gyro_member),
                    )
                acceleration, gyroscope = loaded[key]
                if acceleration.shape[1] != 3 or gyroscope.shape[1] != 3:
                    continue
                segment_lo = max(0, int(segment_start) - 1)
                segment_hi = min(len(acceleration), int(segment_end))
                if activity_id <= 6 and segment_hi - segment_lo >= config.MOTION_WINDOW_SAMPLES:
                    window_start = segment_lo
                else:
                    center = (segment_lo + segment_hi) // 2
                    window_start = max(0, min(center - config.MOTION_WINDOW_SAMPLES // 2, len(acceleration) - config.MOTION_WINDOW_SAMPLES))
                window_end = window_start + config.MOTION_WINDOW_SAMPLES
                if window_start < 0 or window_end > len(acceleration) or window_end > len(gyroscope):
                    continue
                acc_window = np.asarray(acceleration[window_start:window_end], dtype=np.float32)
                gyro_window = np.asarray(gyroscope[window_start:window_end], dtype=np.float32)
                if not np.isfinite(acc_window).all() or not np.isfinite(gyro_window).all():
                    continue
                derived = motion_features(acc_window)
                row_index = len(acceleration_rows)
                acceleration_rows.append(acc_window)
                gyroscope_rows.append(gyro_window)
                records.append(
                    {
                        "row": row_index,
                        "dataset": "uci_hapt",
                        "experimentId": int(experiment),
                        "subjectId": int(subject),
                        "activityId": activity_id,
                        "activity": activity_name,
                        "sourceSegmentStart": int(segment_start),
                        "sourceSegmentEnd": int(segment_end),
                        "sampleOffset": int(window_start),
                        "originalFsHz": config.MOTION_FS_HZ,
                        "windowSamples": config.MOTION_WINDOW_SAMPLES,
                        "isSynthetic": False,
                        "derived": {
                            "activityState": derived.activity_state,
                            "artifact": derived.artifact,
                            "energyG2": round(derived.energy_g2, 8),
                            "postureAngleDeg": round(derived.posture_angle_deg, 6),
                            "jerkRmsGps": round(derived.jerk_rms_g_per_s, 6),
                        },
                    }
                )
                break
            if len(records) >= config.HAPT_MAX_WINDOWS:
                break

    missing = sorted(set(ACTIVITY_NAMES) - {record["activityId"] for record in records})
    if missing:
        raise RuntimeError(f"UCI HAPT subset lacks required activity IDs: {missing}")
    write_npz_deterministic(
        config.MOTION_FILE,
        acceleration_g=np.stack(acceleration_rows).astype(np.float32),
        activity=np.asarray([record["activity"] for record in records], dtype="U20"),
        activity_id=np.asarray([record["activityId"] for record in records], dtype=np.int16),
        experiment_id=np.asarray([record["experimentId"] for record in records], dtype=np.int16),
        gyroscope_rad_s=np.stack(gyroscope_rows).astype(np.float32),
        is_synthetic=np.zeros(len(records), dtype=np.bool_),
        sample_offset=np.asarray([record["sampleOffset"] for record in records], dtype=np.int32),
        subject_id=np.asarray([record["subjectId"] for record in records], dtype=np.int16),
    )
    manifest = {
        "schema": "ml_mvp_motion_manifest/v1",
        "source": {
            "dataset": "UCI Smartphone-Based Recognition of Human Activities and Postural Transitions (HAPT)",
            "sourceUrl": config.HAPT_SOURCE_PAGE_URL,
            "archiveUrl": config.HAPT_SOURCE_URL,
            "version": config.HAPT_VERSION,
            "license": config.HAPT_LICENSE,
            "licenseUrl": config.HAPT_LICENSE_URL,
            "citationUrl": config.HAPT_CITATION_URL,
            "archiveBytes": int(raw["bytes"]),
            "archiveSha256": sha256_file(config.HAPT_ARCHIVE_FILE),
            "isSynthetic": False,
        },
        "extraction": {
            "method": "One first finite 10-second accelerometer/gyroscope window for each required activity; transition windows are centered on the labeled transition.",
            "samplingRateHz": config.MOTION_FS_HZ,
            "windowSamples": config.MOTION_WINDOW_SAMPLES,
            "boundedRows": len(records),
            "activities": sorted({record["activity"] for record in records}),
        },
        "thresholds": {
            "dynamicEnergyG2": config.MOTION_DYNAMIC_ENERGY_G2,
            "lyingAngleDeg": config.MOTION_LYING_ANGLE_DEG,
            "artifactMagnitudeVarianceG2": config.MOTION_ARTIFACT_MAG_VAR_G2,
            "artifactJerkRmsGps": config.MOTION_ARTIFACT_JERK_RMS_GPS,
            "inactivityEnergyG2": config.MOTION_INACTIVITY_ENERGY_G2,
            "impactPeakG": config.MOTION_IMPACT_PEAK_G,
            "prolongedInactivitySeconds": config.PROLONGED_INACTIVITY_SECONDS,
        },
        "rows": records,
        "processedFile": {
            "path": config.MOTION_FILE.relative_to(config.DATA_DIR).as_posix(),
            "bytes": config.MOTION_FILE.stat().st_size,
            "sha256": sha256_file(config.MOTION_FILE),
        },
        "limitations": [
            "This is a small bounded fixture rather than the full UCI HAPT archive.",
            "The source is a waist-worn smartphone in scripted laboratory activities, not a wrist wearable.",
            "Lying transitions are controlled transitions, not falls or stroke events.",
        ],
    }
    write_canonical_json(config.MOTION_MANIFEST_FILE, manifest)
    return manifest
