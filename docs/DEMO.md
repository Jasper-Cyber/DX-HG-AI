# HeartGuardian AI — Demonstration Script

HeartGuardian contains two distinct demonstrations: the existing mobile simulator uses synthetic physiological values, while the isolated ECG + motion CLI uses selected real public-data windows. Both are experimental, non-diagnostic prototypes and neither is a medical device.

## One-hour ECG + motion MVP

Run from `backend/` on Windows. These commands use the required `hack1` Conda environment and do not start a server or watcher.

```powershell
conda run --no-capture-output -n hack1 python -m ml_mvp.pipeline --check
conda run --no-capture-output -n hack1 python -m ml_mvp.demo --persona healthy --countdown-seconds 0.2
conda run --no-capture-output -n hack1 python -m ml_mvp.demo --persona possible_acute_event --countdown-seconds 0.2
conda run --no-capture-output -n hack1 python -m ml_mvp.demo --persona false_alarm --countdown-seconds 0.2
```

Optional artifact rebuild, using the already acquired/processed real data:

```powershell
conda run --no-capture-output -n hack1 python -m ml_mvp.build_mvp
```

### Expected CLI outcomes

| Persona | Expected state path and evidence |
|---|---|
| `healthy` | Ends `normal`; zero Warnings; no countdown or escalation. |
| `possible_acute_event` | Includes Normal → Watch → Warning; 0.2-second demo countdown ends as `escalated`; output explicitly says `SIMULATED escalation` and `networkOrNotificationAction: false`. |
| `false_alarm` | Heavy-motion windows produce `motion_artifact_excluded`; zero Warnings; current fixture ends `data_quality`. |

Narration cues:

- ECG windows are real held-out PhysioNet CinC 2017 records; motion windows are a bounded real UCI HAPT fixture.
- The two streams come from different people and datasets. They are paired only to exercise fusion, and no paired actual stroke-onset dataset is used.
- ECG detects AF-like rhythm patterns, not stroke. Say “possible acute event signs” or “AF-related rhythm signs,” never “stroke detected.”
- The 0.2-second countdown makes the CLI quick. The documented production analogue is 30 seconds.
- Expiry changes only process-local state and prints a simulated-only message. It sends no dispatch, HTTP request, notification, or other warning-triggered network action.

### Backup-video checklist

- Record at 1080p or the highest stable available resolution with the terminal text readable.
- Segment 1: pipeline `--check`, showing 1,000 rows and the 700/300 real rhythm cohort.
- Segment 2: `healthy`, pausing on `warningCount: 0`.
- Segment 3: `possible_acute_event`, showing Normal → Watch → Warning and the simulated-only escalation message.
- Segment 4: `false_alarm`, showing `motion_artifact_excluded` and no Warning.
- Narrate the different-person/dataset pairing, non-diagnostic boundary, short countdown, and no-real-dispatch limitation.
- If a live run fails, play the unedited segment and show `backend/data/processed/task_2_1_run_log.json` plus `docs/MVP_EVALUATION.md`; do not substitute fabricated output.

## Existing mobile simulator setup

The mobile app remains the original synthetic-data prototype; this MVP did not edit teammate-owned mobile UI.

```powershell
# Terminal 1 — backend
cd backend
conda run --no-capture-output -n hack1 python seed_data.py --scenario B --reset
conda run --no-capture-output -n hack1 python -m uvicorn app.main:app --port 8000

# Terminal 2 — mobile
cd mobile
npm install
npm start
```

Verify the backend at <http://localhost:8000/health>. Stop the backend and Expo process when the mobile walkthrough is complete.

## Existing mobile walkthrough (~3 minutes)

| # | Step | What to point out |
|---|---|---|
| 1 | Open **Dashboard** | “SIMULATED DATA” ribbon; HR/HRV/SpO₂/rhythm cards; activity, sleep, and monitoring status. |
| 2 | **Disclaimer** | Experimental and non-diagnostic; acknowledge it and note it remains available in Settings. |
| 3 | **Simulator → A** → Start | Metrics remain near baseline; Insights shows Normal monitoring. |
| 4 | **Simulator → B** → Reset, Start | HR drifts up and HRV down; Insights rises to Trend review/Attention with supporting evidence. |
| 5 | **Simulator → C** → Reset, Start | Rhythm irregularity is flagged for review, never diagnosed. |
| 6 | **History** | Daily/weekly/monthly toggles, baseline overlay, and anomaly markers. |
| 7 | Optional care/emergency flow | Any dispatch is simulated-by-default and user-controlled in the existing app. |
| 8 | Reset to **A** | Leave the simulator in a clean state. |

## Focused verification

```powershell
cd backend
conda run --no-capture-output -n hack1 python -m pytest -q tests/test_ml_mvp_data.py tests/test_ml_mvp_logic.py
conda run --no-capture-output -n hack1 python -m pytest -q tests/test_health.py tests/test_sensor_adapters.py tests/test_db_repository.py
```

## MVP limitations

- Experimental and non-diagnostic; not a medical device or clinical validation.
- CinC 2017 labels rhythm, not stroke; no paired actual stroke-onset data is used.
- ECG and motion are paired from different people/datasets.
- Motion is a bounded waist-worn-phone laboratory fixture, not wrist/free-living evidence.
- CinC 2017 lacks published patient IDs; record-as-patient is an MVP assumption.
- Persona rows are selected and cycled for deterministic outcomes.
- No real dispatch, `/stroke/*` API, persistent warning DB, mobile warning UI, CNN-LSTM, ONNX runtime, demo DB snapshot, or LLM explainer is included.
