"""Build deterministic persona input selections from real ECG and motion rows."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from . import config
from .io_utils import write_canonical_json
from .modeling import load_model, score_windows
from .motion import motion_features


def _cycle(values: list[int], count: int) -> list[int]:
    if not values:
        raise RuntimeError("cannot build persona from an empty source pool")
    return [values[index % len(values)] for index in range(count)]


def build_persona_inputs() -> dict[str, Any]:
    metadata = json.loads(config.MVP_MODEL_META_FILE.read_text(encoding="utf-8"))
    threshold = float(metadata["decisionThreshold"])
    artifact = load_model()
    with np.load(config.COHORT_FILE, allow_pickle=False) as cohort:
        windows = cohort["ecg_mv"].astype(np.float64)
        labels = cohort["label"].astype(str)
        partitions = cohort["partition"].astype(str)
        record_ids = cohort["record_id"].astype(str)
    scores = score_windows(artifact, windows)
    valid_indices = [index for index, score in enumerate(scores) if score is not None and partitions[index] == "test"]
    normal = [index for index in valid_indices if labels[index] == "N"]
    af = [index for index in valid_indices if labels[index] == "A"]
    if len(normal) < 5 or len(af) < 5:
        raise RuntimeError("held-out test split lacks enough valid real ECG rows for personas")
    low_normal = sorted(normal, key=lambda index: float(scores[index]))[:5]
    high_normal = sorted(normal, key=lambda index: float(scores[index]), reverse=True)[:5]
    high_af = sorted(af, key=lambda index: float(scores[index]), reverse=True)[:5]

    with np.load(config.MOTION_FILE, allow_pickle=False) as motion_data:
        acceleration = motion_data["acceleration_g"].astype(np.float64)
        motion_rows = [motion_features(window) for window in acceleration]
    static_rows = [index for index, row in enumerate(motion_rows) if row.activity_state == "static" and not row.artifact]
    lying_rows = [
        index
        for index, row in enumerate(motion_rows)
        if row.activity_state == "lying"
        and not row.artifact
        and row.energy_g2 < config.MOTION_INACTIVITY_ENERGY_G2
    ]
    artifact_rows = [index for index, row in enumerate(motion_rows) if row.artifact]
    if not static_rows:
        raise RuntimeError("bounded UCI HAPT fixture has no reliable static motion row")
    if not lying_rows:
        raise RuntimeError("bounded UCI HAPT fixture has no reliable low-energy lying row")
    if not artifact_rows:
        raise RuntimeError("bounded UCI HAPT fixture has no heavy-motion artifact row")

    healthy_ecg = _cycle(low_normal, 12)
    healthy_motion = _cycle(static_rows, 6) + _cycle(lying_rows, 6)
    acute_ecg = _cycle(low_normal, 3) + _cycle(high_af, 11)
    acute_motion = _cycle(static_rows, 8) + _cycle(lying_rows, 6)
    false_ecg = _cycle(high_normal, 8)
    false_motion = _cycle(artifact_rows, 8)

    def persona(ecg_indices: list[int], motion_indices: list[int], expected: dict[str, Any]) -> dict[str, Any]:
        return {
            "ecgIndices": ecg_indices,
            "ecgRecordIds": [str(record_ids[index]) for index in ecg_indices],
            "motionIndices": motion_indices,
            "expected": expected,
        }

    payload = {
        "schema": "ml_mvp_personas/v1",
        "seed": config.SEED,
        "modelVersion": metadata["modelVersion"],
        "decisionThreshold": threshold,
        "sources": {
            "ecg": "Real held-out PhysioNet CinC 2017 records",
            "motion": "Real bounded UCI HAPT accelerometer/gyroscope fixture",
            "pairedFromDifferentPeopleAndDatasets": True,
            "pairedActualStrokeOnsetDatasetUsed": False,
        },
        "selection": {
            "healthy": "Lowest-scored valid held-out Normal ECG rows with reliable static/lying HAPT rows.",
            "possible_acute_event": "Highest-scored valid held-out AF ECG rows after Normal context, paired with static-to-lying HAPT rows. This is not a stroke-onset sequence.",
            "false_alarm": "Highest-scored valid held-out Normal ECG rows paired with HAPT rows that exceed transparent motion-artifact rules.",
            "reuse": "The compact CLI cycles selected real rows to form a deterministic demonstration timeline; it does not create new real observations.",
        },
        "personas": {
            "healthy": persona(healthy_ecg, healthy_motion, {"warningCount": 0}),
            "possible_acute_event": persona(
                acute_ecg,
                acute_motion,
                {"orderedStates": ["normal", "watch", "warning"], "warningStatus": "escalated"},
            ),
            "false_alarm": persona(
                false_ecg,
                false_motion,
                {
                    "warningCount": 0,
                    "minimumDowngrades": 1,
                    "normalRowsAboveThresholdBeforeGuardrail": int(
                        sum(float(scores[index]) > threshold for index in false_ecg)
                    ),
                },
            ),
        },
    }
    write_canonical_json(config.PERSONA_INPUTS_FILE, payload)
    return payload
