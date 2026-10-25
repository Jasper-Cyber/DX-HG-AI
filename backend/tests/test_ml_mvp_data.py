"""Offline integrity tests for the compact real-data MVP artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BACKEND_DIR / "data" / "processed"


def test_achieved_cohort_has_exact_real_rows_and_first_window_shape() -> None:
    """Property 2: the committed cohort meets its exact scoped invariants.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    manifest = json.loads((PROCESSED_DIR / "data_manifest.json").read_text(encoding="utf-8"))
    with np.load(PROCESSED_DIR / "cinc2017_cohort.npz", allow_pickle=False) as cohort:
        assert cohort["ecg_mv"].shape == (1000, 1250)
        assert np.isfinite(cohort["ecg_mv"]).all()
        assert Counter(cohort["label"].astype(str)) == {"N": 700, "A": 300}
        assert len(set(cohort["record_id"].astype(str))) == 1000
        assert not cohort["is_synthetic"].any()

    assert manifest["selection"]["achievedRows"] == 1000
    assert manifest["selection"]["achievedClassCounts"] == {"A": 300, "N": 700}
    assert manifest["selection"]["targetReached"] is True
    assert manifest["selection"]["shortfallReason"] is None


def test_record_splits_are_exact_complete_stratified_and_pairwise_disjoint() -> None:
    """Properties 5 and 6: every record has one exact split assignment.

    **Validates: Requirements 4.1, 4.3, 9.7**
    """
    split_manifest = json.loads((PROCESSED_DIR / "split_manifest.json").read_text(encoding="utf-8"))
    expected_sizes = {"train": 700, "validation": 150, "test": 150}
    expected_classes = {
        "train": {"A": 210, "N": 490},
        "validation": {"A": 45, "N": 105},
        "test": {"A": 45, "N": 105},
    }
    manifest_sets = {
        name: set(split_manifest["partitions"][name]) for name in expected_sizes
    }

    for name, expected_size in expected_sizes.items():
        assert len(manifest_sets[name]) == expected_size
        assert split_manifest["classCounts"][name] == expected_classes[name]
    assert manifest_sets["train"].isdisjoint(manifest_sets["validation"])
    assert manifest_sets["train"].isdisjoint(manifest_sets["test"])
    assert manifest_sets["validation"].isdisjoint(manifest_sets["test"])

    with np.load(PROCESSED_DIR / "cinc2017_cohort.npz", allow_pickle=False) as cohort:
        record_ids = cohort["record_id"].astype(str)
        labels = cohort["label"].astype(str)
        partitions = cohort["partition"].astype(str)
        for name in expected_sizes:
            selected = partitions == name
            assert set(record_ids[selected]) == manifest_sets[name]
            assert Counter(labels[selected]) == expected_classes[name]
        assert set(record_ids) == set().union(*manifest_sets.values())
