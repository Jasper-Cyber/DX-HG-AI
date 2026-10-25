"""Build task 2.1 model, real-motion fixture, and deterministic persona inputs."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable

from . import config
from .io_utils import write_canonical_json
from .modeling import train_and_evaluate
from .motion_data import build_motion_subset
from .personas import build_persona_inputs
from .warning import CliWarningMachine

TASK_LIMIT_SECONDS = 22 * 60


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stage(log: dict[str, Any], name: str, task_start: float, action: Callable[[], Any]) -> Any:
    started = time.perf_counter()
    result = action()
    elapsed = time.perf_counter() - started
    log["stages"].append({"name": name, "result": "passed", "elapsedSeconds": round(elapsed, 3)})
    log["elapsedSeconds"] = round(time.perf_counter() - task_start, 3)
    write_canonical_json(config.MVP_RUN_LOG_FILE, log)
    if log["elapsedSeconds"] >= TASK_LIMIT_SECONDS:
        raise TimeoutError(f"task 2.1 checkpoint exceeded after {name}")
    return result


def _warning_self_check() -> dict[str, Any]:
    machine = CliWarningMachine(0.1)
    machine.raise_warning(0.0)
    first, first_changed = machine.cancel(0.01)
    second, second_changed = machine.cancel(0.02)
    if first != second or not first_changed or second_changed:
        raise AssertionError("warning cancel is not idempotent")
    return {"cancelIdempotent": True, "automaticAction": "simulated_cli_only"}


def build() -> dict[str, Any]:
    task_start = time.perf_counter()
    log: dict[str, Any] = {
        "schema": "ml_mvp_task_2_1_run_log/v1",
        "task": "2.1 Build and exercise the complete non-production MVP demo path",
        "status": "building",
        "startedAtUtc": _utc_now(),
        "taskLimitSeconds": TASK_LIMIT_SECONDS,
        "priorTaskElapsedSeconds": 593.857,
        "command": "conda run --no-capture-output -n hack1 python -m ml_mvp.build_mvp",
        "stages": [],
        "personaRuns": {},
        "blockers": [],
    }
    write_canonical_json(config.MVP_RUN_LOG_FILE, log)
    try:
        metrics = _stage(log, "train_select_evaluate", task_start, train_and_evaluate)
        motion = _stage(log, "acquire_extract_real_motion", task_start, build_motion_subset)
        personas = _stage(log, "build_persona_inputs", task_start, build_persona_inputs)
        warning_check = _stage(log, "warning_state_machine_self_check", task_start, _warning_self_check)
        log.update(
            {
                "status": "ready_for_cli_exercise",
                "completedBuildAtUtc": _utc_now(),
                "elapsedSeconds": round(time.perf_counter() - task_start, 3),
                "selectedModel": metrics["selection"]["selectedModel"],
                "testMetrics": metrics["evaluation"]["test"],
                "motionRows": motion["extraction"]["boundedRows"],
                "personaIds": sorted(personas["personas"]),
                "warningSelfCheck": warning_check,
                "documentationInputs": [
                    str(config.MVP_METRICS_FILE.relative_to(config.BACKEND_DIR)),
                    str(config.MOTION_MANIFEST_FILE.relative_to(config.BACKEND_DIR)),
                    str(config.PERSONA_INPUTS_FILE.relative_to(config.BACKEND_DIR)),
                    str(config.MVP_RUN_LOG_FILE.relative_to(config.BACKEND_DIR)),
                ],
            }
        )
        write_canonical_json(config.MVP_RUN_LOG_FILE, log)
        return log
    except Exception as exc:
        log.update(
            {
                "status": "blocked",
                "elapsedSeconds": round(time.perf_counter() - task_start, 3),
                "blockers": [f"{type(exc).__name__}: {exc}"],
            }
        )
        write_canonical_json(config.MVP_RUN_LOG_FILE, log)
        raise


def main() -> int:
    try:
        result = build()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
