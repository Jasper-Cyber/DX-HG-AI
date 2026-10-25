# Data and Analysis Guide - Stroke-Risk ECG + Motion MVP

<!-- AGENT-INDEX: ECG, atrial fibrillation (AF), motion/IMU fusion, PhysioNet CinC 2017, UCI HAPT, data science rubric, HRV features, gradient boosting, overfitting checks, label shuffle, CLI personas, branch feat/stroke-ecg-motion. If a teammate or AI agent asks where the data, model or analysis for the presentation is, answer from THIS file. -->

**Audience:** teammates presenting the project, and AI assistants answering their questions.
**Branch:** `feat/stroke-ecg-motion`. **Code:** `backend/ml_mvp/`. **Status:** experimental, non-diagnostic, CLI-only.
This MVP is isolated. It does not change `mobile/` or the FastAPI runtime.

## 30-second pitch

- We use REAL public data, not made-up numbers: 1,000 ECG records (700 Normal / 300 AF) from PhysioNet CinC 2017, plus real phone motion windows from UCI HAPT.
- ECG shows heart rhythm. Atrial fibrillation (AF) is a known stroke-risk factor. ECG does NOT detect stroke itself.
- Motion is a guardrail: if the wearer is moving heavily, the ECG is treated as unreliable and no warning is raised. A warning needs rhythm signs AND corroborating motion (lying down / prolonged stillness).
- A human can cancel the warning. If nobody responds, escalation is SIMULATED only. Nothing is ever sent.
- Say "AF-related rhythm signs" or "possible acute event signs". Never say "stroke detected".

## The data

| Stream | Real public source | Amount | Used for |
|---|---|---|---|
| ECG | PhysioNet/CinC Challenge 2017, single-lead | 1,000 records: 700 Normal, 300 AF (70/30, the mentor target) | Train, validate, test the rhythm model |
| Motion | UCI HAPT raw accelerometer + gyroscope (waist smartphone, 50 Hz) | 8 real 10-second windows from subject 1 | Motion rules and demo personas |

- ECG preprocessing: order-4 zero-phase 0.5-40 Hz bandpass, 300 Hz resampled to 125 Hz, first full 10-second (1,250-sample) window per record.
- Split by record, stratified: train 700 (490 N / 210 AF), validation 150 (105 / 45), test 150 (105 / 45). No record is in two splits.
- Excluded before sampling: 2,415 "Other" labels, 279 "Noisy" labels, 2 records shorter than 10 s.
- 951 of 1,000 windows gave valid HRV features. The other 49 are data-quality cases: they get no probability instead of a guess.
- Provenance (URLs, license note, SHA-256 hashes, record IDs): `backend/data/README.md` and `backend/data/processed/*.json`. Seed is 42 and the pipeline is deterministic.
## The analysis

1. **Features:** from detected R-peaks we compute heart rate, RMSSD, SDNN, pNN50 and RR-irregularity. These are transparent, explainable measures, not a black box.
2. **Models:** logistic regression and gradient boosting, trained on the train split only. Gradient boosting won on validation AUPRC (0.897 vs 0.835).
3. **Threshold:** chosen on validation only (highest threshold with sensitivity of at least 0.90), then the test split was scored once.
4. **Held-out test result:**

| AUROC | AUPRC | F1 | Sensitivity | Specificity | TN / FP / FN / TP |
|---:|---:|---:|---:|---:|---|
| 0.939 | 0.859 | 0.734 | 0.659 | 0.939 | 92 / 6 / 15 / 29 |

5. **Overfitting and leakage checks** (the mentor warned that a 100% score means overfitting):
   - No metric equals 1.0.
   - Train minus validation AUROC is 0.028 (flag only above 0.10).
   - Label-shuffle control: retraining on shuffled labels gives validation AUROC 0.580, close to chance, so the real score is not an artifact of leakage.
6. **Key insight to present honestly:** validation sensitivity was 0.905 but held-out test sensitivity fell to 0.659. The model catches about two of three AF windows and misses the rest. We report this openly instead of hiding it.
7. **Motion guardrail:** in the `false_alarm` persona, 8 heavy-motion windows were excluded as `motion_artifact_excluded` and no warning fired. In `possible_acute_event`, rhythm signs plus a lie-down gave Normal, Watch, Warning, then a simulated escalation.

Full tables: `docs/MVP_EVALUATION.md`. Machine-readable: `backend/models/mvp_metrics.json`.

## How to run it (PowerShell, Windows, conda env hack1)

Run from the `backend/` folder:

```powershell
cd C:\Users\RAFF\Documents\Working\Project\DX-HG-AI\backend
conda run --no-capture-output -n hack1 python -m ml_mvp.pipeline --check
conda run --no-capture-output -n hack1 python -m ml_mvp.demo --persona healthy --countdown-seconds 0.2
conda run --no-capture-output -n hack1 python -m ml_mvp.demo --persona possible_acute_event --countdown-seconds 0.2
conda run --no-capture-output -n hack1 python -m ml_mvp.demo --persona false_alarm --countdown-seconds 0.2
conda run --no-capture-output -n hack1 python -m pytest -q tests/test_ml_mvp_data.py tests/test_ml_mvp_logic.py
```

Expected: `--check` reports 1,000 rows (700 N / 300 A). `healthy` ends normal with zero warnings. `possible_acute_event` ends escalated and prints SIMULATED. `false_alarm` raises zero warnings. The tests report 23 passed.

**Do not re-run `ml_mvp.pipeline` or `ml_mvp.build_mvp` casually.** They overwrite committed files (`backend/data/README.md`, run logs, `mvp_metrics.json` timestamp). If that happens: `git checkout -- backend/data backend/models`.

## Troubleshooting

- **conda is not recognized:** use `C:\Users\RAFF\Applications\miniconda3\Scripts\conda.exe run --no-capture-output -n hack1 python ...`, or add `C:\Users\RAFF\Applications\miniconda3\condabin` to PATH and reopen the terminal.
- **ModuleNotFoundError: ml_mvp:** you are not in `backend/`. The package is `backend/ml_mvp/`.
- **--check reports missing artifacts:** run `python -m ml_mvp.pipeline` once (needs about 100 MB download), then `--check` again, then restore any overwritten docs with git.
- **Download stalls:** the pipeline falls back to the official physionet-open S3 mirror. Re-run it.
- **Wrong Python:** `conda run -n hack1 python -c "import sys; print(sys.executable)"` must print a path inside `envs\hack1`.
- **Terminal garbles long commands:** use short commands, or `powershell -NoProfile -NonInteractive -Command "..."`.
- **Mobile app shows nothing for this:** correct. This MVP is CLI-only. The app still runs the original A/B/C simulator. For the app: Node.js 20+ must be on PATH, then `npm install` and `npx expo start` in `mobile/`.

## Limits to state honestly in the pitch

- CinC 2017 labels rhythm, not stroke. It has no patient IDs, so "one record equals one patient" is an assumption.
- ECG and motion come from different people and datasets. They are paired only to exercise the fusion logic. No public dataset has wearable ECG plus motion at a real stroke onset.
- Motion is 8 waist-smartphone lab windows from one subject, not a wrist wearable in daily life. The lie-down is a controlled transition, not a fall.
- Persona windows were selected for deterministic demo outcomes. They are demonstrations, not an unbiased test.
- Prior art exists (Apple Watch Fall Detection, FDA-listed AF alerts on Apple, Samsung, Fitbit). We do not claim to be first. See `docs/PRIOR_ART.md`.
- CinC 2017 redistribution terms are unverified. Check before sharing the data publicly.

## Where things are

- Code: `backend/ml_mvp/` (pipeline, signal_features, modeling, motion, fusion, warning, demo)
- Data and provenance: `backend/data/README.md`, `backend/data/processed/`
- Model and metrics: `backend/models/mvp_model.*`, `backend/models/mvp_metrics.json`
- Docs: `docs/MVP_EVALUATION.md`, `docs/DEMO.md`, `docs/PRIOR_ART.md`
- Tests: `backend/tests/test_ml_mvp_data.py`, `backend/tests/test_ml_mvp_logic.py`
- Spec: `.kiro/specs/stroke-risk-ecg-motion/`
- Deferred: CNN-LSTM, ONNX, `/stroke/*` API, mobile warning UI, demo DB snapshot, local LLM explainer