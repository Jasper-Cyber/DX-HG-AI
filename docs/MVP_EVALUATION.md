# One-Hour MVP Evaluation — ECG + Motion Fusion

## Scope and claim boundary

This is an experimental, non-diagnostic fusion demonstration. The ECG model detects AF-like rhythm patterns, not stroke. It is not a medical device and is not clinically validated. The paired timeline combines ECG and motion windows from different people and datasets; no public paired wearable dataset with actual stroke onset was used.

## Data evidence

| Item | Actual result |
|---|---:|
| CinC 2017 rows | 1,000 real records |
| Rhythm classes | 700 Normal / 300 AF |
| Train split | 700 (490 Normal / 210 AF) |
| Validation split | 150 (105 Normal / 45 AF) |
| Test split | 150 (105 Normal / 45 AF) |
| Feature-valid rows | 951 |
| Feature-invalid/data-quality rows | 49 |
| Valid train / validation / test | 665 / 144 / 142 |
| UCI HAPT motion fixture | 8 real 10-second windows |

The CinC cohort uses one first valid 10-second, 1,250-sample window per record after an order-4 zero-phase 0.5–40 Hz bandpass and resampling from 300 Hz to 125 Hz. Splits are deterministic, stratified, and record-disjoint. CinC 2017 publishes no patient IDs, so treating each record as one patient/group is only an MVP assumption.

The motion fixture contains one bounded real UCI HAPT window for each selected activity/transition: walking, walking upstairs, walking downstairs, sitting, standing, lying, sit-to-lie, and stand-to-lie. It comes from subject 1, experiment 1, sampled at 50 Hz by a waist-worn smartphone in scripted laboratory activities. Controlled lie-down transitions are not falls or stroke events. Exact offsets, derived features, archive hash, source URL, and CC BY 4.0 license are recorded in `backend/data/processed/motion_manifest.json`.

## Model selection and threshold

Both candidates were trained on the train split only. The deployed model was selected solely by validation AUPRC.

| Candidate | Validation AUPRC | Validation AUROC |
|---|---:|---:|
| Logistic regression | 0.835252 | 0.948413 |
| Gradient boosting | **0.896718** | **0.952381** |

- Selected model: gradient boosting, version `mvp-v1-gradient_boosting-5c71fa63-s42`.
- Decision threshold: `0.761676078`, selected from validation only as the highest midpoint reaching at least 0.90 sensitivity.
- Validation sensitivity at that threshold: 0.904762; no sensitivity shortfall was recorded.
- The held-out test partition was evaluated once for this model version at `2026-10-25T10:27:54.587122Z`.

## Actual metrics

| Split | AUROC | AUPRC | F1 | Sensitivity | Specificity | Confusion matrix (TN, FP, FN, TP) |
|---|---:|---:|---:|---:|---:|---|
| Train | 0.980413 | 0.962524 | 0.889447 | 0.855072 | 0.969432 | 444, 14, 30, 177 |
| Validation | 0.952381 | 0.896718 | 0.873563 | 0.904762 | 0.931373 | 95, 7, 4, 38 |
| Held-out test | 0.939239 | 0.858808 | 0.734177 | 0.659091 | 0.938776 | 92, 6, 15, 29 |

Interpretation: held-out test sensitivity is materially lower than validation sensitivity, so the validation-selected operating point does not transfer perfectly. These compact results support only a runnable software experiment, not medical effectiveness.

## Overfitting and leakage checks

- Perfect validation/test metric flag: `false`; no metric was exactly 1.0.
- Train-minus-validation AUROC: `0.028032`; the configured >0.10 generalization-gap flag is `false`.
- Shuffled-train-label validation AUROC: `0.580065`, inside the configured [0.40, 0.60] sanity range; `leakageSuspect` is `false`.
- Overall `overfitSuspect`: `false`.

These flags did not trigger, but they do not prove absence of leakage, generalization, calibration, subgroup, or clinical-validity problems.

## Motion, fusion, and persona evidence

- `healthy`: terminal state `normal`; no Warning and no escalation.
- `possible_acute_event`: ordered Normal → Watch → Warning path; one warning; the 0.2-second CLI countdown expired to `SIMULATED escalation` through `simulated_cli_only` and performed no dispatch, HTTP request, notification, or other warning-triggered network action.
- `false_alarm`: eight motion-artifact downgrades; no Warning; terminal display state `data_quality`.
- Raising the ECG threshold by 0.05 did not increase Watch occurrences in any persona.
- Persona ECG rows are selected real held-out CinC 2017 records. Motion rows are selected real UCI HAPT windows. Reusing/cycling selected rows creates a deterministic demo timeline, not new observations.
- The CLI countdown is intentionally 0.2 seconds for demonstration; the documented production analogue is 30 seconds.

## Verification and elapsed evidence

| Stage | Command/result | Elapsed |
|---|---|---:|
| Task 1.1 data foundation | Completed; pipeline determinism and self-check passed | 593.857 s |
| Task 2.1 model/motion/fusion/personas | Completed; all three CLI paths passed | 132.586 s |
| Task 3.1 focused suite | `python -m pytest -q tests/test_ml_mvp_data.py tests/test_ml_mvp_logic.py`; 23 passed | 2.99 s |
| Task 3.1 backend smoke | `python -m pytest -q tests/test_health.py tests/test_sensor_adapters.py tests/test_db_repository.py`; 23 passed, 2 dependency deprecation warnings | 4.19 s |

Every Python command was executed through `conda run --no-capture-output -n hack1`. Task 3.1 took 177.075 seconds through final pre-commit validation/documentation; recorded cumulative work for tasks 1.1–3.1 was 903.518 seconds (15 minutes 3.518 seconds), below the 60-minute hard limit. Exact command and hygiene evidence is recorded in `backend/data/processed/task_3_1_run_log.json`.

Baseline comparison: the same backend smoke selection passed 23 tests before the MVP in 4.155 seconds and passed 23 tests after it in 4.19 seconds. No new failure or changed pass count was observed. Mobile Jest and TypeScript checks were not rerun because this one-hour MVP intentionally made no mobile changes.

## Completed versus deferred

Completed: compact real CinC cohort, deterministic splits/provenance, transparent HRV features, logistic-regression/gradient-boosting selection, held-out metrics, shuffled-label sanity check, bounded real HAPT motion fixture, pure fusion rules, process-local CLI warning lifecycle, three deterministic personas, focused tests, and documentation.

Deferred roadmap (not implemented by this MVP):

1. Full data/evaluation pipeline with AFDB, NSTDB, UCI HAR/full HAPT, external validation, robustness, calibration, confidence intervals, and subgroup analysis.
2. Small CNN-LSTM training and ONNX export/runtime parity.
3. `/stroke/*` APIs plus persistent warning/database and monitoring integration.
4. Full mobile warning, history, evidence, provenance, accessibility, and persona UI.
5. Synthetic-only demo DB snapshot/bootstrap.
6. Disabled interface placeholder for a future local/on-device LLM explainer; no model weights or explainer runtime.

The teammate-owned mobile UI was not edited.

## Limitations and skipped items

- AF-like rhythm is a stroke-risk factor signal, not stroke detection.
- There is no paired actual stroke-onset ECG/motion dataset in this MVP.
- ECG and motion are paired from different people and datasets.
- Motion evidence is only eight waist-phone laboratory windows from one subject; it is not wrist-wearable or free-living validation.
- CinC records have no published patient IDs; record-level grouping may not guarantee patient independence.
- Persona records were selected for deterministic outcomes and are demonstrations, not an unbiased evaluation set.
- Invalid ECG windows receive no probability and become data-quality cases.
- No real dispatch exists; escalation is text/state only.
- No optional plots, larger downloads, threshold-nudge feature, CNN-LSTM, ONNX, API, database integration, mobile UI, or LLM work was performed.
