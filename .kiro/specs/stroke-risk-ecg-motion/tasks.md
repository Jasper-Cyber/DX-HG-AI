# Implementation Plan: One-Hour MVP — Stroke Risk ECG + Motion

## Overview

Implement a truthful, runnable Python MVP in **55 estimated minutes** on a small Windows laptop. The required queue contains exactly three sequential, non-optional leaf tasks: data foundation (18 minutes), model/motion/fusion/CLI (22 minutes), and tests/docs/validation/local commit (15 minutes). Use real public data only for anything labeled real; if acquisition cannot reach 1000 ECG rows within the time box, keep the largest stratified real subset and report its exact counts without fabrication.

The MVP excludes production integration. CNN-LSTM, ONNX, `/stroke/*`, mobile UI, persistent warning/database integration, the demo DB snapshot, and local/on-device LLM work are deferred as optional follow-ups and must not execute during the one-hour queue.

## Tasks

- [x] 1. Establish the branch, environment, baseline, and compact real-data foundation
  - [x] 1.1 Build the isolated ECG data pipeline and provenance artifacts (estimated: 18 minutes; cumulative: 18 minutes)
    - Start a wall-clock run log immediately. Switch to or create local branch `feat/stroke-ecg-motion` from the current starting commit; make local commits only and never push.
    - Preserve the two personal steering ignores by adding `.kiro/steering/response-style.md` and `.kiro/steering/python-environment.md` to `.git/info/exclude` if absent, then remove only those exact local lines from `.gitignore`. Add an ignore rule for the MVP raw-download directory; do not alter unrelated ignore entries.
    - Use `C:\Users\RAFF\Applications\miniconda3\Scripts\conda.exe` and, only if needed for command discovery, prepend `C:\Users\RAFF\Applications\miniconda3\condabin` to `PATH`. Verify with `conda run --no-capture-output -n hack1 python -c "import sys; print(sys.executable)"`; stop the entire execution and report the error if `hack1` is unavailable. Never fall back to another interpreter.
    - Record a targeted pre-change backend baseline, including command, elapsed time, pass/fail counts, and failing test names, using `conda run --no-capture-output -n hack1 python -m pytest ...` against relevant existing smoke tests. Do not fix unrelated baseline failures and do not start a server or watcher.
    - Create a clearly isolated Python package under `backend/ml_mvp/` with deterministic configuration, stdlib download/cache helpers, ECG loading/preprocessing, cohort selection, record-level splitting, canonical JSON writing, hashing, and a runnable pipeline entry point.
    - Acquire PhysioNet CinC 2017 labels and signals into a gitignored raw cache. Prefer stdlib downloads and already-installed scipy/scikit-learn. Install into `hack1` only when essential, using an exact version and recording the pin; do not install globally or create an environment.
    - With a fixed seed, exclude unusable labels and records, apply an approximately 0.5–40 Hz zero-phase bandpass, resample to 125 Hz, and retain one first valid 10-second/1250-sample window per record. Target exactly 700 Normal and 300 AF rows. If the source or download deadline prevents this, stop acquisition expansion at the task deadline, retain the largest stratified real subset, and record exact counts and the reason; never pad, duplicate, synthesize, or relabel rows to meet the target.
    - Split by record into deterministic, stratified 70/15/15 train/validation/test partitions with no overlap. Write compact processed artifacts only when comfortably below normal Git size limits.
    - Write `backend/data/README.md` and canonical manifests containing source and citation/license URLs, source version/access date, file hashes, achieved class and split counts, split record IDs, preprocessing parameters, `isSynthetic: false`, excluded-record counts, and limitations. Explicitly state that CinC 2017 detects rhythm labels rather than stroke and has no published patient IDs, so record-level grouping is an MVP assumption.
    - Add a fast pipeline self-check that fails on non-finite/wrong-length windows, duplicate split IDs, incorrect achieved counts versus the manifest, hash mismatches, or any row labeled real without source provenance. Run it with `conda run --no-capture-output -n hack1 python -m ml_mvp.<entrypoint> --check` from `backend` and record the result in the run log.
    - Checkpoint: ensure the environment, baseline, data self-check, manifests, and time log are complete before proceeding; ask the user only if execution is blocked.
    - _Requirements: 1.1, 1.3, 1.5, 1.6, 2.1–2.5, 3.1–3.3, 4.1, 4.3, 4.5, 5.1–5.4, 33.1, 33.4, 34.1, 34.6, 35.1, 35.3, 35.4_

- [x] 2. Implement the lightweight model, real-motion rules, pure fusion, and CLI personas
  - [x] 2.1 Build and exercise the complete non-production MVP demo path (estimated: 22 minutes; cumulative: 40 minutes)
    - Add shared deterministic ECG feature extraction under `backend/ml_mvp/`: R-peak detection, heart rate, RMSSD, SDNN, pNN50, and normalized RR irregularity. Mark invalid windows as data-quality cases instead of inventing probabilities.
    - Train logistic regression and gradient boosting on the train split only; select the deployed MVP model by validation AUPRC. Select any classification threshold from validation data only, then perform one held-out test evaluation and persist AUROC, AUPRC, F1, sensitivity, specificity, and confusion matrix in canonical metrics JSON.
    - Add overfitting controls: flag any perfect validation/test metric, flag train AUROC minus validation AUROC above 0.10, and retrain on deterministically shuffled train labels to report validation AUROC as a leakage sanity check. Do not describe strong results as medical validation.
    - Acquire a bounded real UCI HAPT raw accelerometer/gyroscope subset; use UCI HAR only when it is materially faster. If a full archive threatens the task or overall deadline, use a small directly downloadable slice or a compact fixture derived from the real dataset and document its exact source, extraction method, subject/activity IDs, hash, and limitations. Never call generated or random motion data real.
    - Compute acceleration magnitude, energy, posture angle, and jerk, then implement deterministic rule-based `dynamic`/`static`/`lying`, motion-artifact, lie-down, and prolonged-inactivity signals. Keep thresholds transparent in the MVP configuration.
    - Implement pure fusion state transitions: high ECG probability in K of the last N reliable windows produces Watch; heavy motion makes paired ECG unreliable and records a downgrade; Watch plus lie-down/prolonged inactivity produces Warning. Ensure increasing the ECG threshold cannot increase Watch occurrences for a fixed sequence.
    - Implement a process-local warning/countdown state machine for the CLI only. Use a short configurable demo countdown while documenting the 30-second production analogue. Expiry may print/record only `SIMULATED escalation`; it must perform no dispatch, HTTP request, notification, or other warning-triggered network action. Repeated cancel must be idempotent; implement the bounded cancel/nudge rule only if time remains after the runnable paths work.
    - Build three deterministic CLI personas from selected real ECG and motion windows: `healthy` ends without Warning; `possible_acute_event` progresses Normal → Watch → Warning → countdown → automatic simulated escalation; `false_alarm` demonstrates motion-artifact downgrade or Warning → user cancel. Use non-diagnostic wording and disclose in CLI output that ECG and motion come from different people/datasets and that no paired actual stroke-onset dataset is used.
    - Write canonical evaluation outputs and `docs/MVP_EVALUATION.md` inputs. Generate lightweight plots only if the required model, fusion, all personas, and metrics JSON are already complete and the elapsed budget permits it.
    - Exercise all three paths from `backend` with `conda run --no-capture-output -n hack1 python -m ml_mvp.<demo_module> --persona <name> ...`; assert/inspect the expected terminal state, no-warning result, downgrade/cancel result, and explicit simulated-only message. Record commands and outcomes without running a server.
    - Checkpoint: ensure the model artifact, real-motion provenance, pure fusion, canonical metrics, and all three runnable CLI outcomes are complete before proceeding; ask the user only if execution is blocked.
    - _Requirements: 6.1–6.4, 8.1–8.5, 8.8, 9.1–9.4, 11.1–11.5, 12.3–12.10, 14.5, 15.1–15.3, 16.2–16.5, 18.4–18.5, 19.2, 20.3, 21.2, 21.5, 23.4_

- [ ] 3. Add focused tests and truthful docs, enforce the time box, validate, and commit locally
  - [-] 3.1 Test, document, clean, and commit the MVP without exceeding 60 minutes (estimated: 15 minutes; cumulative: 55 minutes)
    - Add focused pytest coverage following existing `backend/tests/` conventions. Keep tests offline and deterministic, use temporary paths, and cover: achieved cohort counts plus exact split disjointness; deterministic ECG features and fusion; motion-artifact exclusion; threshold monotonicity; cancel idempotency and the cancel/nudge cap only if nudge exists; and expected outcomes for all three personas.
    - Encode the scoped universal checks as parameterized/property-style tests tied to design Properties 2, 5, 6, 8, 14, 17, 18, 19, 25, 26 (only if nudge exists), and 28. Do not add a new test dependency unless it is essential and there is sufficient time; if Hypothesis is already available, bound its examples for fast execution.
    - Complete `docs/MVP_EVALUATION.md` from actual artifacts: exact achieved sample size/classes/splits, model-selection result, held-out metrics, confusion matrix, shuffle result, overfit/generalization flags with interpretation, motion sample provenance, elapsed stages, and failed/skipped items. Truthfully distinguish completed evidence from planned full-feature work.
    - Minimally update `README.md` and `docs/DEMO.md` with exact conda commands, the three CLI demos and expected output, real-data provenance, short countdown versus production analogue, and limitations: experimental/non-diagnostic; ECG detects AF-like rhythm rather than stroke; ECG and motion are paired from different people/datasets; no actual paired stroke-onset data; bounded motion sample; record-as-patient assumption; and no real dispatch.
    - Add paraphrased prior-art references and access dates for Apple Watch Fall Detection and the FDA smartwatch cardiovascular-notification page named in the requirements. Describe the MVP as a fusion experiment without novelty, medical-device, diagnosis, or clinical-validation claims.
    - Add explicit roadmap entries for the full data/evaluation pipeline, CNN-LSTM, ONNX runtime, `/stroke/*`, persistent warning/database integration, full mobile UI, demo DB snapshot, and disabled local/on-device LLM explainer. State that teammate mobile UI was not edited in this MVP.
    - Run the targeted MVP suite with `conda run --no-capture-output -n hack1 python -m pytest -q <MVP test files>` and relevant existing backend smoke tests with the same command prefix. Record command, elapsed time, pass/fail counts, failing names, and differences from baseline; do not fix unrelated pre-existing failures.
    - Enforce the hard deadline: reserve this validation/documentation task by stopping extra downloads, larger cohort expansion, optional plots, and metric embellishment first as elapsed work approaches 60 minutes. Preserve, in priority order, a runnable tested CLI, real-data provenance, canonical metrics, focused tests, and truthful docs. Do not start work on any optional deferred task.
    - Confirm no server, watcher, downloader, or other process started by the work remains running. Remove caches and partial downloads from the staging set; verify raw data, `.kiro/steering/*`, mutable live DBs, `.env`/secrets, and caches are ignored or unstaged.
    - Review `git status` and file sizes, stage only explicit MVP feature paths plus the intentional `.gitignore` cleanup, and create a local commit with concise message `feat: add one-hour stroke risk MVP`. Never push. If tests fail only as recorded pre-existing failures, document them; if an MVP test fails, fix it within the remaining budget or do not claim completion/commit a knowingly broken MVP.
    - Final checkpoint: ensure all targeted tests pass, required artifacts are truthful, no process remains, and the local branch/commit constraints hold; ask the user if questions arise.
    - _Requirements: 5.3–5.5, 8.3–8.7, 9.1–9.4, 10.5–10.6, 23.5, 31.1–31.3, 32.1–32.4, 33.6, 34.2–34.6, 35.2–35.5_

- [ ] 4. Deferred optional full-feature follow-ups — do not execute in the one-hour MVP queue
  - [ ]* 4.1 Expand the offline data and evaluation pipeline to the full design
    - Acquire/process complete scoped CinC 2017, AFDB slices, NSTDB, UCI HAPT, and UCI HAR inputs; add deterministic processed packs, external validation, SNR robustness, bootstrap intervals, learning curves, calibration, fusion episodes, realism/TSTR checks, and generated reports.
    - Add the full property and integration test coverage mapped by the design.
    - _Requirements: 1–5, 8.5–8.7, 9.5–9.7, 11.6, 13.1–13.6, 22.1–22.6_

  - [ ]* 4.2 Implement the CNN-LSTM training and ONNX deployment path
    - Add bounded CPU-only CNN-LSTM training, augmentation, regularization, early stopping, model selection, ONNX export/parity checks, runtime inference, metadata, fallback behavior, and Model Card updates.
    - Add model/export/runtime tests without changing the MVP evidence retroactively.
    - _Requirements: 7.1–7.6, 8.8, 10.1–10.6, 33.1–33.5_

  - [ ]* 4.3 Implement persistent warning storage, backend runtime wiring, and `/stroke/*` APIs
    - Add the stroke schema/repository, persistent state machine, countdown integration with monitoring, simulated escalation linkage, feedback/threshold adjustments, persona runtime, typed FastAPI endpoints, and compatibility tests.
    - Keep existing monitoring, alerts, emergency behavior, and A/B/C scenarios compatible.
    - _Requirements: 12.1–12.2, 14.1–17.6, 18.1–18.7, 23.1–24.9_

  - [ ]* 4.4 Implement the full Expo mobile experience
    - Add typed clients/hooks, warning card, countdown/actions, escalation banner, AF timeline, warning list/detail, evidence charts, provenance, persona picker, privacy badge, accessibility behavior, and web-compatible tests.
    - Preserve teammate screens/components and make all edits additive.
    - _Requirements: 25.1–29.5_

  - [ ]* 4.5 Build the full demo snapshot and local/on-device explainer placeholder
    - Create and validate the synthetic-only personal-data demo DB snapshot, bootstrap behavior, template explainer, disabled local/on-device LLM adapter, full demo documentation, and delivery checks.
    - Do not download LLM weights or enable real dispatch.
    - _Requirements: 23.1–23.5, 30.1–30.5, 31.4–31.5, 35.4–35.5_

## Notes

- Required execution is limited to leaf tasks `1.1`, `2.1`, and `3.1`, in order; their combined estimate is **55 minutes**.
- Tasks marked with `*` are optional deferred full-feature work and must not be implemented by the one-hour MVP queue.
- Python implementation uses the Windows Conda environment `hack1`; every Python/test invocation must use the exact command prefixes stated above.
- The source-availability fallback changes only achieved sample size, never data truthfulness: no fabricated row may be labeled real.
- No mobile UI, production API, persistent demo DB, CNN-LSTM, ONNX, real dispatch, or LLM implementation belongs in the required MVP.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["3.1"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["4.2"] },
    { "id": 5, "tasks": ["4.3"] },
    { "id": 6, "tasks": ["4.4", "4.5"] }
  ]
}
```
