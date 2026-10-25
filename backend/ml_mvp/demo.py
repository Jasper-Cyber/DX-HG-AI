"""Run one deterministic, non-diagnostic ECG + motion CLI persona."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

import numpy as np

from . import config
from .fusion import WindowInput, run_sequence, watch_occurrences
from .io_utils import write_canonical_json
from .modeling import load_model, score_windows
from .motion import motion_features
from .warning import CliWarningMachine

PERSONAS = ("healthy", "possible_acute_event", "false_alarm")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _transitions(states: list[str]) -> list[str]:
    result: list[str] = []
    for state in states:
        if not result or result[-1] != state:
            result.append(state)
    return result


def run_persona(persona_name: str, countdown_seconds: float) -> dict[str, Any]:
    specification = json.loads(config.PERSONA_INPUTS_FILE.read_text(encoding="utf-8"))
    persona = specification["personas"][persona_name]
    threshold = float(specification["decisionThreshold"])
    with np.load(config.COHORT_FILE, allow_pickle=False) as cohort:
        ecg = cohort["ecg_mv"][persona["ecgIndices"]].astype(np.float64)
        records = cohort["record_id"][persona["ecgIndices"]].astype(str)
        labels = cohort["label"][persona["ecgIndices"]].astype(str)
    with np.load(config.MOTION_FILE, allow_pickle=False) as motion_data:
        acceleration = motion_data["acceleration_g"][persona["motionIndices"]].astype(np.float64)
        motion_subjects = motion_data["subject_id"][persona["motionIndices"]].astype(int)
        motion_activities = motion_data["activity"][persona["motionIndices"]].astype(str)

    probabilities = score_windows(load_model(), ecg)
    motion_rows = [motion_features(window) for window in acceleration]
    inputs = [
        WindowInput(index=index, af_probability=probability, motion=motion_row)
        for index, (probability, motion_row) in enumerate(zip(probabilities, motion_rows))
    ]
    _, outputs = run_sequence(inputs, threshold)
    states = [output.state for output in outputs]
    transitions = _transitions(states)
    warning_count = sum(output.warning_trigger for output in outputs)
    downgrades = [output.downgrade_reason for output in outputs if output.downgrade_reason]

    machine = CliWarningMachine(countdown_seconds)
    escalation_message: str | None = None
    for output in outputs:
        if output.warning_trigger:
            machine.raise_warning(float(output.index * config.WINDOW_SECONDS))
    if persona_name == "possible_acute_event":
        if machine.event is None:
            raise AssertionError("possible_acute_event did not create a warning")
        _, escalation_message = machine.expire(machine.event.deadline_seconds + 0.001)

    raised_threshold = min(1.0, threshold + 0.05)
    base_watch_count = watch_occurrences(inputs, threshold)
    raised_watch_count = watch_occurrences(inputs, raised_threshold)
    if raised_watch_count > base_watch_count:
        raise AssertionError("raising the ECG threshold increased Watch occurrences")

    if persona_name == "healthy" and warning_count != 0:
        raise AssertionError("healthy persona raised a Warning")
    if persona_name == "possible_acute_event":
        required = ["normal", "watch", "warning"]
        cursor = 0
        for state in transitions:
            if cursor < len(required) and state == required[cursor]:
                cursor += 1
        if cursor != len(required) or machine.event is None or machine.event.status != "escalated":
            raise AssertionError(f"possible_acute_event outcome mismatch: {transitions}")
        if escalation_message is None or "SIMULATED" not in escalation_message:
            raise AssertionError("automatic CLI escalation was not explicitly simulated-only")
    if persona_name == "false_alarm":
        if warning_count != 0 or "motion_artifact_excluded" not in downgrades:
            raise AssertionError("false_alarm did not demonstrate a no-warning motion-artifact downgrade")

    result = {
        "persona": persona_name,
        "experimentalNonDiagnostic": True,
        "wording": "Possible acute event signs are an experimental fusion output; ECG detects AF-like rhythm patterns, not stroke.",
        "dataDisclosure": "ECG and motion are real public-data windows from different people and datasets; no paired actual stroke-onset dataset is used.",
        "ecg": {
            "dataset": "PhysioNet CinC 2017",
            "recordIds": records.tolist(),
            "rhythmLabels": labels.tolist(),
            "probabilities": [None if value is None else round(float(value), 6) for value in probabilities],
        },
        "motion": {
            "dataset": "UCI HAPT",
            "subjectIds": motion_subjects.tolist(),
            "activities": motion_activities.tolist(),
            "artifactWindows": int(sum(row.artifact for row in motion_rows)),
        },
        "fusion": {
            "states": states,
            "stateTransitions": transitions,
            "warningCount": warning_count,
            "guardrailDowngradeCount": len(downgrades),
            "guardrailDowngradeReasons": sorted(set(downgrades)),
            "threshold": threshold,
            "watchWindowsAtThreshold": base_watch_count,
            "raisedThreshold": raised_threshold,
            "watchWindowsAtRaisedThreshold": raised_watch_count,
            "thresholdMonotonic": True,
        },
        "warningLifecycle": {
            "status": machine.event.status if machine.event else "none",
            "countdownSeconds": countdown_seconds if machine.event else None,
            "productionAnalogueSeconds": config.PRODUCTION_COUNTDOWN_ANALOGUE_SECONDS,
            "escalationChannel": machine.event.escalation_channel if machine.event else None,
            "message": escalation_message,
            "networkOrNotificationAction": False,
        },
    }
    return result


def _record_result(result: dict[str, Any], command: str) -> None:
    log = json.loads(config.MVP_RUN_LOG_FILE.read_text(encoding="utf-8"))
    log.setdefault("personaRuns", {})[result["persona"]] = {
        "command": command,
        "result": "passed",
        "completedAtUtc": _utc_now(),
        "terminalState": result["fusion"]["stateTransitions"][-1],
        "warningStatus": result["warningLifecycle"]["status"],
        "warningCount": result["fusion"]["warningCount"],
        "guardrailDowngradeCount": result["fusion"]["guardrailDowngradeCount"],
        "simulatedOnly": not result["warningLifecycle"]["networkOrNotificationAction"],
    }
    if set(log["personaRuns"]) == set(PERSONAS):
        completed = datetime.now(timezone.utc)
        started = datetime.fromisoformat(log["startedAtUtc"].replace("Z", "+00:00"))
        task_elapsed = round((completed - started).total_seconds(), 3)
        build_elapsed = float(log.get("buildElapsedSeconds", log.get("elapsedSeconds", 0.0)))
        log["status"] = "completed" if task_elapsed <= float(log["taskLimitSeconds"]) else "deadline_exceeded"
        log["completedAtUtc"] = completed.isoformat().replace("+00:00", "Z")
        log["buildElapsedSeconds"] = build_elapsed
        log["elapsedSeconds"] = task_elapsed
        log["overallCumulativeSeconds"] = round(float(log["priorTaskElapsedSeconds"]) + task_elapsed, 3)
    write_canonical_json(config.MVP_RUN_LOG_FILE, log)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persona", required=True, choices=PERSONAS)
    parser.add_argument("--countdown-seconds", type=float, default=config.DEMO_COUNTDOWN_SECONDS)
    args = parser.parse_args(argv)
    command = (
        "conda run --no-capture-output -n hack1 python -m ml_mvp.demo "
        f"--persona {args.persona} --countdown-seconds {args.countdown_seconds:g}"
    )
    try:
        result = run_persona(args.persona, args.countdown_seconds)
        _record_result(result, command)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
