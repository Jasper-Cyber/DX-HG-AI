"""CinC 2017 loading, preprocessing, cohort selection, and record splitting."""

from __future__ import annotations

import csv
import io
import random
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, resample_poly, sosfiltfilt

from . import config


@dataclass(frozen=True)
class Cohort:
    record_ids: tuple[str, ...]
    labels: tuple[str, ...]
    windows_mv: np.ndarray
    excluded: dict[str, int]
    deadline_reached: bool


def load_reference(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row[0].strip(): row[1].strip() for row in csv.reader(handle) if len(row) >= 2}


def preprocess_ecg(raw_adc: np.ndarray, gain_adc_per_mv: float) -> np.ndarray | None:
    signal = np.asarray(raw_adc, dtype=np.float64).reshape(-1)
    if signal.size < config.ORIGINAL_FS_HZ * config.WINDOW_SECONDS or not np.isfinite(signal).all():
        return None
    if not np.isfinite(gain_adc_per_mv) or gain_adc_per_mv <= 0:
        return None
    signal_mv = signal / gain_adc_per_mv
    sos = butter(
        config.BANDPASS_ORDER,
        [config.BANDPASS_LOW_HZ, config.BANDPASS_HIGH_HZ],
        btype="bandpass",
        fs=config.ORIGINAL_FS_HZ,
        output="sos",
    )
    filtered = sosfiltfilt(sos, signal_mv)
    resampled = resample_poly(filtered, config.TARGET_FS_HZ, config.ORIGINAL_FS_HZ)
    if resampled.size < config.WINDOW_SAMPLES:
        return None
    window = np.asarray(resampled[: config.WINDOW_SAMPLES], dtype=np.float32)
    return window if np.isfinite(window).all() else None


def _member_map(archive: zipfile.ZipFile) -> dict[str, str]:
    return {Path(name).name: name for name in archive.namelist() if not name.endswith("/")}


def _gain_from_header(header: str) -> float:
    lines = [line for line in header.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("missing signal specification in header")
    for token in lines[1].split():
        if "/mV" in token:
            value = token.split("/", 1)[0].split("(", 1)[0]
            return float(value)
    raise ValueError("header does not declare ADC gain in units per mV")


def _load_record(archive: zipfile.ZipFile, members: dict[str, str], record_id: str) -> tuple[np.ndarray, float]:
    mat_name = members[f"{record_id}.mat"]
    header_name = members[f"{record_id}.hea"]
    matrix = loadmat(io.BytesIO(archive.read(mat_name)))
    raw = np.asarray(matrix["val"]).reshape(-1)
    header = archive.read(header_name).decode("ascii", errors="replace")
    return raw, _gain_from_header(header)


def build_cohort(reference: dict[str, str], archive_path: Path, deadline: float) -> Cohort:
    candidates = {
        "N": sorted(record for record, label in reference.items() if label == "N"),
        "A": sorted(record for record, label in reference.items() if label == "A"),
    }
    for offset, label in enumerate(("N", "A")):
        random.Random(config.SEED + offset).shuffle(candidates[label])

    targets = {"N": config.TARGET_NORMAL, "A": config.TARGET_AF}
    positions = {"N": 0, "A": 0}
    accepted: dict[str, list[tuple[str, np.ndarray]]] = {"N": [], "A": []}
    excluded = {
        "otherLabel": sum(label == "O" for label in reference.values()),
        "noisyLabel": sum(label == "~" for label in reference.values()),
        "shorterThan10Seconds": 0,
        "missingArchiveMember": 0,
        "unusableSignalOrHeader": 0,
    }
    deadline_reached = False

    with zipfile.ZipFile(archive_path) as archive:
        members = _member_map(archive)
        while any(len(accepted[label]) < targets[label] for label in targets):
            if time.monotonic() >= deadline:
                deadline_reached = True
                break
            available = [
                label
                for label in ("N", "A")
                if len(accepted[label]) < targets[label] and positions[label] < len(candidates[label])
            ]
            if not available:
                break
            label = min(available, key=lambda item: (len(accepted[item]) / targets[item], item != "N"))
            record_id = candidates[label][positions[label]]
            positions[label] += 1
            if f"{record_id}.mat" not in members or f"{record_id}.hea" not in members:
                excluded["missingArchiveMember"] += 1
                continue
            try:
                raw, gain = _load_record(archive, members, record_id)
                if raw.size < config.ORIGINAL_FS_HZ * config.WINDOW_SECONDS:
                    excluded["shorterThan10Seconds"] += 1
                    continue
                window = preprocess_ecg(raw, gain)
            except (KeyError, OSError, ValueError):
                excluded["unusableSignalOrHeader"] += 1
                continue
            if window is None:
                excluded["unusableSignalOrHeader"] += 1
                continue
            accepted[label].append((record_id, window))

    rows = accepted["N"] + accepted["A"]
    rows.sort(key=lambda item: item[0])
    labels_by_id = {record_id: label for label, records in accepted.items() for record_id, _ in records}
    windows = np.stack([window for _, window in rows]) if rows else np.empty((0, config.WINDOW_SAMPLES), dtype=np.float32)
    return Cohort(
        record_ids=tuple(record_id for record_id, _ in rows),
        labels=tuple(labels_by_id[record_id] for record_id, _ in rows),
        windows_mv=windows,
        excluded=excluded,
        deadline_reached=deadline_reached,
    )


def _partition_sizes(count: int) -> dict[str, int]:
    names = tuple(config.SPLIT_FRACTIONS)
    exact = {name: count * config.SPLIT_FRACTIONS[name] for name in names}
    sizes = {name: int(exact[name]) for name in names}
    remaining = count - sum(sizes.values())
    order = sorted(names, key=lambda name: (-(exact[name] - sizes[name]), names.index(name)))
    for name in order[:remaining]:
        sizes[name] += 1
    return sizes


def stratified_record_split(record_ids: tuple[str, ...], labels: tuple[str, ...]) -> dict[str, list[str]]:
    result = {name: [] for name in config.SPLIT_FRACTIONS}
    for offset, label in enumerate(("N", "A")):
        records = sorted(record for record, record_label in zip(record_ids, labels) if record_label == label)
        random.Random(config.SEED + 100 + offset).shuffle(records)
        sizes = _partition_sizes(len(records))
        cursor = 0
        for partition in config.SPLIT_FRACTIONS:
            end = cursor + sizes[partition]
            result[partition].extend(records[cursor:end])
            cursor = end
    for records in result.values():
        records.sort()
    return result
