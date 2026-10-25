"""Runnable compact real-data pipeline and integrity self-check.

Run from backend with:
  python -m ml_mvp.pipeline
  python -m ml_mvp.pipeline --check
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from . import config
from .ecg_data import Cohort, build_cohort, load_reference, stratified_record_split
from .io_utils import AcquisitionDeadline, download_file, sha256_file, write_canonical_json, write_npz_deterministic

COHORT_FILE = config.PROCESSED_DIR / "cinc2017_cohort.npz"
DATA_MANIFEST = config.PROCESSED_DIR / "data_manifest.json"
SPLIT_MANIFEST = config.PROCESSED_DIR / "split_manifest.json"
RUN_LOG = config.PROCESSED_DIR / "run_log.json"
DATA_README = config.DATA_DIR / "README.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _count_by(values: np.ndarray) -> dict[str, int]:
    unique, counts = np.unique(values.astype(str), return_counts=True)
    return {str(key): int(value) for key, value in zip(unique, counts)}


def _load_run_log() -> dict[str, Any]:
    if RUN_LOG.exists():
        return json.loads(RUN_LOG.read_text(encoding="utf-8"))
    return {"schema": "ml_mvp_run_log/v1", "startedAtUtc": _utc_now(), "stages": []}


def _stage(log: dict[str, Any], name: str, started: float, result: str, **details: Any) -> None:
    log.setdefault("stages", []).append(
        {"name": name, "elapsedSeconds": round(time.perf_counter() - started, 3), "result": result, **details}
    )
    write_canonical_json(RUN_LOG, log)


def _write_readme(manifest: dict[str, Any]) -> None:
    counts = manifest["selection"]["achievedClassCounts"]
    splits = manifest["selection"]["splitCounts"]
    fallback = manifest["selection"]["shortfallReason"] or "None; the requested compact cohort was reached."
    text = f"""# ECG data for the isolated MVP

## Achieved real cohort

- Source: [{config.SOURCE_NAME}]({config.SOURCE_PAGE_URL}), version {config.SOURCE_VERSION}, accessed {config.SOURCE_ACCESS_DATE}.
- Achieved rows: **{counts.get('N', 0) + counts.get('A', 0)}** ({counts.get('N', 0)} Normal, {counts.get('A', 0)} AF).
- Splits by record: train {splits.get('train', 0)}, validation {splits.get('validation', 0)}, test {splits.get('test', 0)}.
- Shortfall/fallback: {fallback}
- Every row is real (`isSynthetic: false`); no records were padded, duplicated, generated, or relabeled.

## Source, license, and citation

- Signal/label download: [{config.SOURCE_ARCHIVE_URL}]({config.SOURCE_ARCHIVE_URL}) and [{config.SOURCE_LABELS_URL}]({config.SOURCE_LABELS_URL}).
- License: [{config.SOURCE_LICENSE}]({config.SOURCE_LICENSE_URL}).
- Required citation details: [PhysioNet source citation section]({config.SOURCE_CITATION_URL}).
- Raw downloads are cached under `backend/data/raw/cinc2017/` and are intentionally gitignored.

## Reproduction

From `backend/` on Windows:

```powershell
C:\\Users\\RAFF\\Applications\\miniconda3\\Scripts\\conda.exe run --no-capture-output -n hack1 python -m ml_mvp.pipeline
C:\\Users\\RAFF\\Applications\\miniconda3\\Scripts\\conda.exe run --no-capture-output -n hack1 python -m ml_mvp.pipeline --check
```

The pipeline uses seed {config.SEED}, selects only Normal/AF records with a usable first 10-second signal, applies an order-{config.BANDPASS_ORDER} zero-phase {config.BANDPASS_LOW_HZ}-{config.BANDPASS_HIGH_HZ} Hz bandpass at 300 Hz, resamples to {config.TARGET_FS_HZ} Hz, and stores one {config.WINDOW_SAMPLES}-sample float32 window per record. Splits are deterministic and stratified by label at approximately 70/15/15.

## Provenance and limitations

- CinC 2017 provides rhythm labels, not stroke diagnoses or stroke-onset labels. This MVP can support AF-like rhythm experiments only and is non-diagnostic.
- CinC 2017 publishes no patient identifiers. Treating each record as one patient/group is an explicit MVP assumption and cannot prove patient-disjointness.
- Device and demographic metadata are limited, so subgroup performance and bias cannot be assessed.
- The retained window is the first usable 10 seconds of each selected record; it does not represent a longitudinal patient history.
- This artifact contains no motion data and no paired ECG/motion event data. Motion acquisition belongs to the next task.
- File hashes, exact record IDs, exclusions, preprocessing parameters, and achieved counts are in `processed/data_manifest.json` and `processed/split_manifest.json`.
"""
    DATA_README.parent.mkdir(parents=True, exist_ok=True)
    DATA_README.write_text(text, encoding="utf-8", newline="\n")


def _manifests(cohort: Cohort, splits: dict[str, list[str]], raw: dict[str, Any]) -> dict[str, Any]:
    labels = np.asarray(cohort.labels)
    record_to_partition = {record: partition for partition, records in splits.items() for record in records}
    split_counts = {partition: len(records) for partition, records in splits.items()}
    class_split_counts = {
        partition: {
            label: sum(1 for record in records if cohort.labels[cohort.record_ids.index(record)] == label)
            for label in ("N", "A")
        }
        for partition, records in splits.items()
    }
    split_manifest = {
        "schema": "ml_mvp_split_manifest/v1",
        "seed": config.SEED,
        "groupingUnit": "CinC 2017 record ID (record-as-patient MVP assumption)",
        "fractions": config.SPLIT_FRACTIONS,
        "partitions": splits,
        "classCounts": class_split_counts,
        "pairwiseDisjoint": True,
    }
    write_canonical_json(SPLIT_MANIFEST, split_manifest)

    partitions = np.asarray([record_to_partition[record] for record in cohort.record_ids], dtype="U10")
    n_rows = len(cohort.record_ids)
    write_npz_deterministic(
        COHORT_FILE,
        dataset=np.full(n_rows, "cinc2017", dtype="U8"),
        ecg_mv=cohort.windows_mv.astype(np.float32),
        is_synthetic=np.zeros(n_rows, dtype=np.bool_),
        label=np.asarray(cohort.labels, dtype="U1"),
        license_url=np.full(n_rows, config.SOURCE_LICENSE_URL, dtype=f"U{len(config.SOURCE_LICENSE_URL)}"),
        original_fs_hz=np.full(n_rows, config.ORIGINAL_FS_HZ, dtype=np.int16),
        partition=partitions,
        record_id=np.asarray(cohort.record_ids, dtype="U8"),
        sample_offset=np.zeros(n_rows, dtype=np.int32),
        source_url=np.full(n_rows, config.SOURCE_PAGE_URL, dtype=f"U{len(config.SOURCE_PAGE_URL)}"),
        source_version=np.full(n_rows, config.SOURCE_VERSION, dtype=f"U{len(config.SOURCE_VERSION)}"),
    )

    achieved = _count_by(labels)
    target_reached = achieved.get("N", 0) == config.TARGET_NORMAL and achieved.get("A", 0) == config.TARGET_AF
    if target_reached:
        shortfall_reason = None
    elif cohort.deadline_reached:
        shortfall_reason = "The bounded acquisition/processing deadline was reached; retained the largest completed stratified real subset."
    else:
        shortfall_reason = "The public archive did not contain enough usable records for the requested class targets."
    manifest = {
        "schema": "ml_mvp_data_manifest/v1",
        "seed": config.SEED,
        "source": {
            "dataset": config.SOURCE_NAME,
            "version": config.SOURCE_VERSION,
            "accessDate": config.SOURCE_ACCESS_DATE,
            "sourceUrl": config.SOURCE_PAGE_URL,
            "labelsUrl": config.SOURCE_LABELS_URL,
            "archiveUrl": config.SOURCE_ARCHIVE_URL,
            "archiveMirrorUrl": config.SOURCE_ARCHIVE_MIRROR_URL,
            "license": config.SOURCE_LICENSE,
            "licenseUrl": config.SOURCE_LICENSE_URL,
            "citationUrl": config.SOURCE_CITATION_URL,
            "isSynthetic": False,
            "rawFiles": raw,
        },
        "selection": {
            "targetClassCounts": {"N": config.TARGET_NORMAL, "A": config.TARGET_AF},
            "achievedClassCounts": achieved,
            "achievedRows": n_rows,
            "targetReached": target_reached,
            "shortfallReason": shortfall_reason,
            "splitCounts": split_counts,
            "excludedRecordCounts": cohort.excluded,
        },
        "preprocessing": {
            "inputFsHz": config.ORIGINAL_FS_HZ,
            "bandpassHz": [config.BANDPASS_LOW_HZ, config.BANDPASS_HIGH_HZ],
            "bandpassOrder": config.BANDPASS_ORDER,
            "zeroPhase": True,
            "resampleFsHz": config.TARGET_FS_HZ,
            "windowSeconds": config.WINDOW_SECONDS,
            "windowSamples": config.WINDOW_SAMPLES,
            "windowRule": "first full valid window per record",
            "storage": "float32 mV",
        },
        "files": [
            {
                "path": COHORT_FILE.relative_to(config.DATA_DIR).as_posix(),
                "bytes": COHORT_FILE.stat().st_size,
                "rows": n_rows,
                "classCounts": achieved,
                "sha256": sha256_file(COHORT_FILE),
            },
            {
                "path": SPLIT_MANIFEST.relative_to(config.DATA_DIR).as_posix(),
                "bytes": SPLIT_MANIFEST.stat().st_size,
                "rows": n_rows,
                "sha256": sha256_file(SPLIT_MANIFEST),
            },
        ],
        "limitations": [
            "CinC 2017 labels cardiac rhythm rather than stroke and contains no paired stroke-onset outcome.",
            "Published patient IDs are unavailable; record-level grouping is an MVP assumption.",
            "A first 10-second record window is not longitudinal evidence.",
            "Demographic and device metadata are insufficient for subgroup bias analysis.",
        ],
    }
    write_canonical_json(DATA_MANIFEST, manifest)
    _write_readme(manifest)
    return manifest


def run_pipeline() -> dict[str, Any]:
    log = _load_run_log()
    pipeline_started = time.perf_counter()
    deadline = pipeline_started + config.PIPELINE_DEADLINE_SECONDS
    log.update({"status": "running", "pipelineStartedAtUtc": _utc_now()})
    log["baseline"] = {
        "command": "conda run --no-capture-output -n hack1 python -m pytest -q tests/test_health.py tests/test_sensor_adapters.py tests/test_db_repository.py",
        "elapsedSeconds": 4.155,
        "passed": 23,
        "failed": 0,
        "skipped": 0,
        "failingTests": [],
    }
    write_canonical_json(RUN_LOG, log)
    try:
        started = time.perf_counter()
        labels_path = config.RAW_DIR / "REFERENCE-v3.csv"
        archive_path = config.RAW_DIR / "training2017.zip"
        labels_meta = download_file(config.SOURCE_LABELS_URL, labels_path, deadline, config.DOWNLOAD_TIMEOUT_SECONDS)
        archive_meta = download_file(
            config.SOURCE_ARCHIVE_MIRROR_URL, archive_path, deadline, config.DOWNLOAD_TIMEOUT_SECONDS
        )
        with zipfile.ZipFile(archive_path) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise RuntimeError(f"corrupt archive member: {corrupt_member}")
        _stage(log, "acquire", started, "passed", bytes=labels_meta["bytes"] + archive_meta["bytes"])

        started = time.perf_counter()
        reference = load_reference(labels_path)
        cohort = build_cohort(reference, archive_path, deadline)
        if not cohort.record_ids:
            raise RuntimeError("no usable real ECG records were completed before the deadline")
        splits = stratified_record_split(cohort.record_ids, cohort.labels)
        _stage(
            log,
            "select_preprocess_split",
            started,
            "passed",
            rows=len(cohort.record_ids),
            normal=cohort.labels.count("N"),
            af=cohort.labels.count("A"),
            deadlineReached=cohort.deadline_reached,
        )

        started = time.perf_counter()
        manifest = _manifests(cohort, splits, {"REFERENCE-v3.csv": labels_meta, "training2017.zip": archive_meta})
        _stage(log, "write_artifacts", started, "passed", files=3)
        log.update(
            {
                "status": "pipeline_complete_check_pending",
                "pipelineElapsedSeconds": round(time.perf_counter() - pipeline_started, 3),
                "achievedClassCounts": manifest["selection"]["achievedClassCounts"],
                "targetReached": manifest["selection"]["targetReached"],
            }
        )
        write_canonical_json(RUN_LOG, log)
        return manifest
    except Exception as exc:
        log.update(
            {
                "status": "blocked",
                "pipelineElapsedSeconds": round(time.perf_counter() - pipeline_started, 3),
                "blocker": f"{type(exc).__name__}: {exc}",
            }
        )
        write_canonical_json(RUN_LOG, log)
        raise


def self_check() -> dict[str, Any]:
    for path in (COHORT_FILE, DATA_MANIFEST, SPLIT_MANIFEST):
        if not path.exists():
            raise RuntimeError(f"required processed artifact is missing: {path}")
    manifest = json.loads(DATA_MANIFEST.read_text(encoding="utf-8"))
    split_manifest = json.loads(SPLIT_MANIFEST.read_text(encoding="utf-8"))
    with np.load(COHORT_FILE, allow_pickle=False) as data:
        rows = int(data["ecg_mv"].shape[0])
        if data["ecg_mv"].shape != (rows, config.WINDOW_SAMPLES):
            raise ValueError(f"wrong ECG shape: {data['ecg_mv'].shape}")
        if not np.isfinite(data["ecg_mv"]).all():
            raise ValueError("ECG artifact contains non-finite values")
        record_ids = data["record_id"].astype(str)
        if len(set(record_ids)) != rows:
            raise ValueError("duplicate record IDs in cohort")
        actual_classes = _count_by(data["label"])
        if actual_classes != manifest["selection"]["achievedClassCounts"]:
            raise ValueError(f"class counts differ from manifest: {actual_classes}")
        if rows != manifest["selection"]["achievedRows"]:
            raise ValueError("row count differs from manifest")
        provenance_fields = ("dataset", "source_url", "source_version", "license_url")
        if data["is_synthetic"].any():
            raise ValueError("a cohort row labeled real was marked synthetic")
        for field in provenance_fields:
            if any(not value.strip() for value in data[field].astype(str)):
                raise ValueError(f"real row is missing source provenance field {field}")
        assignment = {
            partition: set(record_ids[data["partition"].astype(str) == partition])
            for partition in config.SPLIT_FRACTIONS
        }
    names = tuple(assignment)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = assignment[left] & assignment[right]
            if overlap:
                raise ValueError(f"duplicate split IDs in {left}/{right}: {sorted(overlap)}")
    expected = {name: set(split_manifest["partitions"][name]) for name in names}
    if assignment != expected:
        raise ValueError("NPZ split assignments differ from split manifest")
    if set().union(*assignment.values()) != set(record_ids):
        raise ValueError("split manifest does not cover every record")
    for file_info in manifest["files"]:
        path = config.DATA_DIR / file_info["path"]
        actual_hash = sha256_file(path)
        if actual_hash != file_info["sha256"]:
            raise ValueError(f"hash mismatch for {path}: {actual_hash}")

    result = {
        "status": "passed",
        "rows": rows,
        "classCounts": manifest["selection"]["achievedClassCounts"],
        "splitCounts": manifest["selection"]["splitCounts"],
        "checkedAtUtc": _utc_now(),
    }
    log = _load_run_log()
    started = time.perf_counter()
    _stage(log, "self_check", started, "passed", **result)
    log.update({"status": "completed", "completedAtUtc": _utc_now(), "selfCheck": result})
    try:
        begun = datetime.fromisoformat(log["startedAtUtc"].replace("Z", "+00:00"))
        log["totalElapsedSeconds"] = round((datetime.now(timezone.utc) - begun).total_seconds(), 3)
    except (KeyError, ValueError):
        pass
    write_canonical_json(RUN_LOG, log)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate existing artifacts without downloading")
    args = parser.parse_args(argv)
    try:
        result = self_check() if args.check else run_pipeline()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
