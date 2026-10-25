"""Train, select, evaluate, and persist the lightweight classical MVP model."""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import config
from .io_utils import sha256_file, write_canonical_json
from .signal_features import FEATURE_ORDER, feature_matrix, hrv_features


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _candidate_models() -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        C=1.0,
                        class_weight="balanced",
                        max_iter=2000,
                        random_state=config.SEED,
                    ),
                ),
            ]
        ),
        "gradient_boosting": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    GradientBoostingClassifier(
                        n_estimators=120,
                        learning_rate=0.05,
                        max_depth=2,
                        subsample=0.8,
                        random_state=config.SEED,
                    ),
                ),
            ]
        ),
    }


def _fit(model: Pipeline, name: str, features: np.ndarray, labels: np.ndarray) -> Pipeline:
    if name == "gradient_boosting":
        counts = np.bincount(labels, minlength=2)
        weights = np.asarray([len(labels) / (2.0 * counts[label]) for label in labels], dtype=np.float64)
        return model.fit(features, labels, classifier__sample_weight=weights)
    return model.fit(features, labels)


def _safe_auc(labels: np.ndarray, probabilities: np.ndarray) -> float:
    return float(roc_auc_score(labels, probabilities)) if len(np.unique(labels)) == 2 else float("nan")


def select_threshold(labels: np.ndarray, probabilities: np.ndarray) -> tuple[float, float, bool]:
    unique = np.unique(np.asarray(probabilities, dtype=np.float64))
    candidates = [0.0, 1.0]
    candidates.extend(float((left + right) / 2.0) for left, right in zip(unique[:-1], unique[1:]))
    scored = []
    for threshold in sorted(set(candidates)):
        sensitivity = float(recall_score(labels, probabilities > threshold, zero_division=0))
        scored.append((threshold, sensitivity))
    qualifying = [item for item in scored if item[1] >= config.MODEL_TARGET_SENSITIVITY]
    if qualifying:
        threshold, sensitivity = max(qualifying, key=lambda item: item[0])
        return float(threshold), float(sensitivity), False
    threshold, sensitivity = max(scored, key=lambda item: (item[1], item[0]))
    return float(threshold), float(sensitivity), True


def classification_metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, Any]:
    predicted = probabilities > threshold
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return {
        "auroc": round(_safe_auc(labels, probabilities), 6),
        "auprc": round(float(average_precision_score(labels, probabilities)), 6),
        "f1": round(float(f1_score(labels, predicted, zero_division=0)), 6),
        "sensitivity": round(float(sensitivity), 6),
        "specificity": round(float(specificity), 6),
        "confusionMatrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def load_model(path: Path = config.MVP_MODEL_FILE) -> dict[str, Any]:
    with path.open("rb") as handle:
        artifact = pickle.load(handle)
    if tuple(artifact["featureOrder"]) != FEATURE_ORDER:
        raise ValueError("model feature order does not match runtime extractor")
    return artifact


def score_windows(artifact: dict[str, Any], windows: np.ndarray) -> list[float | None]:
    result: list[float | None] = []
    model = artifact["estimator"]
    for window in windows:
        features = hrv_features(window)
        if features is None:
            result.append(None)
        else:
            probability = float(model.predict_proba(features.as_vector()[None, :])[0, 1])
            result.append(float(np.clip(probability, 0.0, 1.0)))
    return result


def train_and_evaluate() -> dict[str, Any]:
    with np.load(config.COHORT_FILE, allow_pickle=False) as cohort:
        windows = cohort["ecg_mv"].astype(np.float64)
        labels_text = cohort["label"].astype(str)
        partitions = cohort["partition"].astype(str)
        record_ids = cohort["record_id"].astype(str)

    compact_features, valid = feature_matrix(windows)
    features = np.full((len(windows), len(FEATURE_ORDER)), np.nan, dtype=np.float64)
    features[valid] = compact_features
    labels = (labels_text == "A").astype(np.int8)
    masks = {name: (partitions == name) & valid for name in ("train", "validation", "test")}
    for name, mask in masks.items():
        if mask.sum() == 0 or len(np.unique(labels[mask])) != 2:
            raise RuntimeError(f"{name} has insufficient valid ECG features for binary evaluation")

    fitted: dict[str, Pipeline] = {}
    candidate_metrics: dict[str, dict[str, float]] = {}
    for name, candidate in _candidate_models().items():
        model = _fit(candidate, name, features[masks["train"]], labels[masks["train"]])
        fitted[name] = model
        validation_probabilities = model.predict_proba(features[masks["validation"]])[:, 1]
        candidate_metrics[name] = {
            "validationAuprc": round(float(average_precision_score(labels[masks["validation"]], validation_probabilities)), 6),
            "validationAuroc": round(_safe_auc(labels[masks["validation"]], validation_probabilities), 6),
        }

    selected_name = max(
        candidate_metrics,
        key=lambda name: (candidate_metrics[name]["validationAuprc"], name == "logistic_regression"),
    )
    selected = fitted[selected_name]
    probabilities = {
        name: selected.predict_proba(features[mask])[:, 1]
        for name, mask in masks.items()
    }
    threshold, threshold_sensitivity, threshold_shortfall = select_threshold(
        labels[masks["validation"]], probabilities["validation"]
    )
    split_metrics = {
        name: classification_metrics(labels[masks[name]], probabilities[name], threshold)
        for name in ("train", "validation", "test")
    }

    shuffled_labels = labels[masks["train"]].copy()
    np.random.default_rng(config.SEED).shuffle(shuffled_labels)
    shuffled_model = _fit(clone(_candidate_models()[selected_name]), selected_name, features[masks["train"]], shuffled_labels)
    shuffled_probabilities = shuffled_model.predict_proba(features[masks["validation"]])[:, 1]
    shuffle_validation_auroc = round(_safe_auc(labels[masks["validation"]], shuffled_probabilities), 6)

    perfect_metrics = [
        f"{split_name}.{metric_name}"
        for split_name in ("validation", "test")
        for metric_name, value in split_metrics[split_name].items()
        if metric_name != "confusionMatrix" and value == 1.0
    ]
    generalization_gap_value = split_metrics["train"]["auroc"] - split_metrics["validation"]["auroc"]
    flags = {
        "overfitSuspect": bool(perfect_metrics),
        "perfectMetrics": perfect_metrics,
        "generalizationGap": bool(generalization_gap_value > 0.10),
        "generalizationGapValue": round(float(generalization_gap_value), 6),
        "leakageSuspect": not (0.40 <= shuffle_validation_auroc <= 0.60),
    }

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = {
        "schema": "ml_mvp_model_pickle/v1",
        "modelType": selected_name,
        "featureOrder": FEATURE_ORDER,
        "estimator": selected,
    }
    with config.MVP_MODEL_FILE.open("wb") as handle:
        pickle.dump(artifact, handle, protocol=5)

    data_manifest_hash = sha256_file(config.PROCESSED_DIR / "data_manifest.json")
    version = f"mvp-v1-{selected_name}-{data_manifest_hash[:8]}-s{config.SEED}"
    metrics = {
        "schema": "ml_mvp_metrics/v1",
        "modelVersion": version,
        "isMedicalValidation": False,
        "taskScope": "non-production AF-like rhythm and motion fusion experiment",
        "data": {
            "rows": int(len(windows)),
            "classCounts": {"N": int(np.sum(labels == 0)), "A": int(np.sum(labels == 1))},
            "validFeatureRows": int(valid.sum()),
            "invalidFeatureRows": int((~valid).sum()),
            "validBySplit": {name: int(mask.sum()) for name, mask in masks.items()},
        },
        "selection": {
            "criterion": "highest validation AUPRC",
            "candidates": candidate_metrics,
            "selectedModel": selected_name,
        },
        "threshold": {
            "value": round(threshold, 9),
            "selectedFrom": "validation only",
            "rule": "highest midpoint threshold with sensitivity >= 0.90",
            "validationSensitivity": round(threshold_sensitivity, 6),
            "sensitivityShortfall": threshold_shortfall,
        },
        "evaluation": {
            **split_metrics,
            "testEvaluatedOnceAtUtc": _utc_now(),
        },
        "shuffleCheck": {
            "seed": config.SEED,
            "selectedModelRetrainedOnShuffledTrainLabels": True,
            "validationAuroc": shuffle_validation_auroc,
            "expectedRange": [0.40, 0.60],
        },
        "flags": flags,
        "limitations": [
            "CinC 2017 rhythm labels are not stroke outcomes.",
            "Results are experimental and are not clinical or medical validation.",
            "Invalid ECG windows are data-quality cases and receive no probability.",
        ],
    }
    write_canonical_json(config.MVP_METRICS_FILE, metrics)
    metadata = {
        "schema": "ml_mvp_model/v1",
        "modelVersion": version,
        "modelType": selected_name,
        "artifact": config.MVP_MODEL_FILE.name,
        "artifactSha256": sha256_file(config.MVP_MODEL_FILE),
        "input": {"kind": "hrv_features", "featureOrder": list(FEATURE_ORDER), "ecgFsHz": 125, "windowSamples": 1250},
        "decisionThreshold": round(threshold, 9),
        "seed": config.SEED,
        "dataManifestSha256": data_manifest_hash,
        "selectionRationale": "Selected by validation AUPRC; threshold selected on validation only; test evaluated once.",
        "metricsFile": config.MVP_METRICS_FILE.name,
        "overfittingFlags": flags,
        "testRecordIds": record_ids[partitions == "test"].tolist(),
        "experimentalNonDiagnostic": True,
    }
    write_canonical_json(config.MVP_MODEL_META_FILE, metadata)
    return metrics
