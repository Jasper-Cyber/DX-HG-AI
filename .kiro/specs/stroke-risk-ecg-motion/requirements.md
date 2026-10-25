# Requirements Document

## Introduction

This feature extends the HeartGuardian AI prototype into an experimental early-warning system for atrial-fibrillation-related (AF-related) stroke-risk signals. It fuses a single-lead ECG rhythm model with wearable motion analysis. ECG does not detect stroke. ECG detects AF-like rhythm patterns, and AF is a major stroke-risk factor (about 5x). The feature is therefore framed as "AF-related stroke-risk signals with motion corroboration". All user-facing output is non-diagnostic and labeled experimental. The system uses the phrase "possible acute event signs" and never "stroke detected".

The feature adds:

- Real public ECG and motion data (PhysioNet CinC 2017, MIT-BIH AFDB, MIT-BIH NSTDB, UCI HAR, UCI HAPT), processed reproducibly with full provenance.
- An ML rhythm model (classical HRV baseline plus a small CNN-LSTM), evaluated with explicit overfitting controls and external validation.
- A motion model used as a guardrail: ECG during heavy motion is treated as unreliable, and escalation requires corroborating motion (collapse or prolonged inactivity).
- A human-in-the-loop warning lifecycle: countdown, "I'm OK, cancel warning", "Get help", and automatic simulated escalation.
- Data-grounded demo personas (Healthy, Stroke-event, False-alarm) alongside existing scenarios A/B/C.
- `/stroke/*` API endpoints, mobile UI (warning card, history timeline, warning detail), docs, and a teammate demo DB snapshot.

All work is additive. Existing scenarios A/B/C, the existing detectors in `backend/app/analysis_config.py`, the existing emergency flow, and the teammate's redesigned mobile screens and components keep working unchanged.

Requirement groups:

- Requirements 1–5: Data acquisition and provenance
- Requirements 6–10: ML modeling and evaluation
- Requirements 11–13: Motion and fusion guardrail
- Requirements 14–17: Warning lifecycle and human-in-the-loop
- Requirements 18–22: Demo personas and realism validation
- Requirement 23: Explainer placeholder
- Requirement 24: API
- Requirements 25–29: Mobile UI
- Requirements 30–32: Teammate DB snapshot and docs
- Requirements 33–35: Resource constraints, verification, and git delivery

### Decisions and Assumptions

The user pre-approved all phases. The following decisions were made without further questions and are encoded in the requirements below.

- D1 CinC 2017 publishes no patient IDs. Each record is treated as one patient for grouped splitting. This assumption is stated in the Model_Card.
- D2 One modeling row = one CinC 2017 record = the first full 10 s Window of that record. Records shorter than 10 s and records labeled "Other" or "Noisy" are excluded before seeded sampling. This yields exactly 1000 rows (700 Normal / 300 AF).
- D3 CinC 2017 records outside the 1000-record cohort form a Demo_Pool used only by personas. This keeps demo windows out of train, validation, and test.
- D4 AFDB is used only for external validation and the Stroke-event persona. AFDB data is never used for training. Lead 1 is used, resampled from 250 Hz to 125 Hz.
- D5 MIT-BIH Noise Stress Test Database (NSTDB) records `em` and `ma` are added as the real motion-artifact noise source. This dataset was not in the original list. Neither CinC 2017 nor AFDB supplies labeled motion-artifact noise, and NSTDB is a few MB. If the NSTDB download fails, the fallback is an artifact derived from the real IMU acceleration magnitude, and the fallback is recorded in provenance.
- D6 UCI HAR and UCI HAPT contain no jogging class. The False-alarm persona uses real UCI HAPT walking-upstairs and walking-downstairs windows, labeled "vigorous movement (stair walking)". Continuous 10 s motion windows and postural transitions are cut from UCI HAPT RawData (50 Hz, waist-worn smartphone). UCI HAR's subject-labeled inertial windows serve as an additional motion-model evaluation set. Both datasets come from the same 30 volunteers, so each subject is assigned to the same partition in both.
- D7 ECG and motion come from different people and datasets. Pairing them into one timeline is a demo and evaluation construction, and is documented as a limitation.
- D8 Default fusion parameters (all in Stroke_Config):
  - K = 3 of N = 5 reliable windows
  - countdown 30 s, aligned with Apple Fall Detection, valid range 10–120 s
  - prolonged inactivity ≥ 60 s
  - Watch/motion coincidence interval 5 min
  - threshold nudge step 0.01 per cancel from the 3rd cumulative cancel, capped at +0.05 total
- D9 Status semantics:
  - `confirmed`: the user tapped "Get help".
  - `escalated`: the countdown expired with no response. Escalated events store an escalation channel, either `simulated_dispatch` or `in_app_only`.
- D10 Automatic simulated dispatch is a deliberate, scoped exception to the existing explicit-confirmation rule (heartguardian-ai Req 11.5). The exception applies only to the `simulated` channel and only while `emergency_enabled` is on. Real dispatch keeps the existing gate.
- D11 Persona IDs are `healthy`, `stroke_event`, and `false_alarm`. The UI shows the Stroke-event persona as "Possible acute event (demo)" to keep wording non-diagnostic.
- D12 Each existing 5 s Monitoring_Tick processes 3 consecutive 10 s Windows by default (30 s of signal per tick). The mapping between the hourly measurement timeline and the 10 s Window stream is left to the design.
- D13 Countdown expiry is checked on every Monitoring_Tick loop iteration, whether the simulator is running or paused.
- D14 One extra read-only endpoint, `GET /stroke/timeline`, is added for the History AF-probability chart.
- D15 The deployed rhythm model is the model with higher validation AUPRC. If torch fails, the scikit-learn Classical_Model is deployed. The backend runtime uses ONNX Runtime and never imports torch.
- D16 Simulator reset clears the personal threshold offset so that demo runs stay repeatable. The reset is logged.
- D17 `/stroke/*` endpoints carry no authentication, matching the existing local-only prototype. This is flagged in the README as unsuitable for non-local deployment.
- D18 Paths:
  - `backend/data/raw/` (gitignored)
  - `backend/data/processed/`
  - `backend/data/README.md`
  - `backend/ml/` (offline scripts)
  - `backend/models/` (ONNX + metadata)
  - `docs/MODEL_CARD.md`
  - `docs/EVALUATION.md` and `docs/figures/`
  - `docs/PRIOR_ART.md`
  - `backend/requirements-ml.txt` (offline-only dependencies)
- D19 The "Processed locally" badge means processing happens on the device or the user's local HeartGuardian backend, with no third-party cloud. The badge's accessible description says exactly this.

### Known Limitations (carried into docs)

- No public dataset records an actual stroke onset with paired wearable ECG and motion.
- ECG and motion windows come from different people (see D7).
- UCI HAPT and UCI HAR motion comes from a waist-worn smartphone with lab-scripted activities, not a wrist wearable in daily life.
- The UCI HAPT stand-to-lie transition is a controlled lie-down, not a real fall.
- CinC 2017 device and demographic details are limited, so subgroup bias cannot be measured.
- NeuroKit2 `ecg_simulate` does not model AF morphology (absent P waves, fibrillatory waves). Synthetic AF-like windows only mimic RR irregularity.

## Glossary

- **AF (Atrial Fibrillation)**: An irregular heart rhythm and a major stroke-risk factor. The system detects AF-like rhythm patterns, not stroke.
- **ECG (Electrocardiogram)**: A recording of the heart's electrical activity. Single-lead ECG in this feature.
- **IMU (Inertial Measurement Unit)**: An accelerometer plus gyroscope producing motion signals.
- **RR_Interval**: The time between consecutive R-peaks in an ECG, in milliseconds.
- **HRV (Heart Rate Variability)**: Variation in RR_Intervals, summarized as RMSSD, SDNN, and pNN50.
- **RR_Irregularity**: A scalar index of RR_Interval irregularity (defined in the design) used as a classical AF feature.
- **TSTR (Train on Synthetic, Test on Real)**: A realism check that trains a model on synthetic data and evaluates the model on real data.
- **Provenance**: Origin metadata attached to every Window: dataset, record or subject ID, sample offset, original sampling rate, license, and whether the Window is real or synthetic.
- **Persona**: A deterministic, data-grounded demo scenario (Healthy, Stroke-event, False-alarm) built from real Windows plus fitted synthetic filler.
- **Window**: A 10 s segment. For ECG, 1250 samples at 125 Hz. For motion, 500 samples per axis at 50 Hz.
- **Reliable_Window**: An ECG Window whose paired motion Window has no motion-artifact flag.
- **AF_Probability**: The rhythm model's output in [0, 1] for one ECG Window. This is a model output, not a clinically validated risk score.
- **Personal_Threshold**: The base decision threshold from the Model_Artifact plus the user's false-alarm offset (0 to +0.05).
- **Watch**: The fusion state entered when AF_Probability exceeds the Personal_Threshold in at least K of the last N Reliable_Windows.
- **Corroborating_Motion_Signal**: A sudden-collapse signal or a prolonged-inactivity signal from the Motion_Model.
- **Warning**: The fusion state entered when Watch and a Corroborating_Motion_Signal occur within the coincidence interval.
- **Countdown**: The configurable wall-clock period after a Warning during which the user can cancel or ask for help.
- **Episode**: A 10-minute (60-Window) evaluation sequence built from held-out real ECG and motion Windows for fusion evaluation.
- **False_Alarms_Per_Day**: The number of alerts in Episodes without AF, divided by the total hours of those Episodes, times 24.
- **CinC_2017**: The PhysioNet/Computing in Cardiology Challenge 2017 single-lead ECG dataset (Normal, AF, Other, Noisy).
- **AFDB**: The MIT-BIH Atrial Fibrillation Database, containing long continuous recordings with annotated rhythm changes.
- **NSTDB**: The MIT-BIH Noise Stress Test Database, containing real electrode-motion (`em`) and muscle/motion-artifact (`ma`) noise records.
- **UCI_HAR**: The UCI Human Activity Recognition Using Smartphones dataset, containing activity-labeled inertial signals with subject IDs.
- **UCI_HAPT**: The UCI Smartphone-Based Recognition of Human Activities and Postural Transitions dataset, containing continuous raw IMU data with activity and transition labels.
- **Demo_Pool**: CinC_2017 records outside the 1000-record modeling cohort, reserved for personas.
- **Data_Pipeline**: The offline scripts that acquire, select, preprocess, window, split, and document datasets.
- **Raw_Cache**: The gitignored directory for raw downloads.
- **Processed_Store**: The committed directory for processed datasets and manifests.
- **Data_README**: The data documentation file covering sources, licenses, citations, and limitations.
- **Classical_Model**: An R-peak and HRV feature extractor feeding logistic regression and gradient boosting classifiers.
- **CNN_LSTM_Model**: A small convolutional plus LSTM network operating on raw ECG Windows.
- **Training_Runner**: The offline script that trains models under resource limits and exports artifacts.
- **Evaluation_Harness**: The offline script that computes metrics, plots, and overfitting checks and writes the evaluation report.
- **Model_Artifact**: The deployed model exported as ONNX plus a metadata JSON.
- **Model_Card**: The document describing intended use, data, evaluation, limitations, and bias of the Model_Artifact.
- **Inference_Service**: The backend runtime component that scores Windows with the Model_Artifact via ONNX Runtime.
- **Motion_Model**: The component that computes motion features and outputs activity state, motion-artifact flag, and Corroborating_Motion_Signals.
- **Fusion_Engine**: The backend component that combines AF_Probability, reliability, and motion signals into the fusion states Normal, Data_Quality, Watch, and Warning.
- **Stroke_Config**: The single transparent configuration module `backend/app/stroke_config.py`.
- **Fusion_Evaluator**: The offline script that compares ECG-only and ECG+motion configurations over Episodes.
- **Warning_Service**: The backend component that manages warning events, the Countdown, cancel/confirm, escalation, feedback labels, and threshold nudges.
- **Emergency_Service**: The existing `EmergencyService` (evaluate, dispatch, history).
- **Monitoring_Tick**: The existing 5 s background loop in `backend/app/services/monitoring.py`.
- **Persona_Simulator**: The simulator extension that plays Persona scripts through the Monitoring_Tick.
- **Realism_Validator**: The offline script that compares synthetic and real data distributions and runs TSTR.
- **Explainer_Adapter**: The interface that turns fusion states and warning events into human-readable explanations.
- **Template_Explainer**: The active Explainer_Adapter implementation, based on template text.
- **Local_LLM_Explainer**: The disabled, interface-only Explainer_Adapter stub for a future local LLM.
- **Stroke_API**: The FastAPI router serving `/stroke/*` endpoints.
- **Mobile_App**: The Expo React Native client in `mobile/`.
- **StrokeWarningCard**: The mobile card that shows Watch and Warning states, the Countdown, and the action buttons.
- **History_Screen**: The existing mobile History tab, extended with the AF-probability timeline and the warning-event list.
- **Warning_Detail_Screen**: The mobile screen showing one warning event's ECG strip, motion trace, explanation, and Provenance.
- **Scenario_Picker**: The teammate's existing mobile scenario selection component.
- **Privacy_Badge**: The mobile badge stating that data is processed locally.
- **DB_Bootstrap**: The existing `init_db` function in `backend/app/db/connection.py`.
- **Demo_Seed_DB**: The committed snapshot `backend/data/demo_seed.db`.
- **Project_Docs**: README.md, TEAM.md, docs/DEMO.md, docs/PRIOR_ART.md, docs/MODEL_CARD.md, docs/EVALUATION.md, and the Data_README.
- **Verification_Run**: Execution of pytest, Jest, and `tsc --noEmit`, compared against a recorded baseline.
- **Repository**: The local git repository of the project.

## Requirements

### Requirement 1: Data — Dataset Acquisition and Storage

**User Story:** As a data scientist, I want real public ECG and motion datasets acquired reproducibly, so that the model is trained and validated on real signals instead of only synthetic data.

#### Acceptance Criteria

1. THE Data_Pipeline SHALL acquire the CinC_2017 training set, UCI_HAR, UCI_HAPT, the AFDB record slices listed in a committed slice manifest, and the NSTDB `em` and `ma` records from their public sources.
2. WHEN the Data_Pipeline acquires AFDB data, THE Data_Pipeline SHALL read only the sample ranges listed in the slice manifest.
3. THE Data_Pipeline SHALL write raw downloads to the Raw_Cache and processed outputs to the Processed_Store.
4. IF a PhysioNet download fails or exceeds the timeout in Stroke_Config, THEN THE Data_Pipeline SHALL retry from the configured zip mirror and record the source used in the data manifest.
5. IF a required raw file is missing after acquisition, THEN THE Data_Pipeline SHALL stop with an error naming the missing file and its dataset.
6. WHEN the Data_Pipeline is re-run with the same seed and the same raw inputs, THE Data_Pipeline SHALL produce Processed_Store files with identical content hashes.

### Requirement 2: Data — Modeling Cohort Selection (70/30)

**User Story:** As a data scientist, I want about 1000 real rows at 70% normal and 30% AF, so that the dataset matches the mentor's guidance and has a realistic class imbalance.

#### Acceptance Criteria

1. THE Data_Pipeline SHALL exclude from the selection pool the CinC_2017 records shorter than 10 s and the records labeled Other or Noisy.
2. THE Data_Pipeline SHALL select exactly 700 Normal and 300 AF CinC_2017 records from the selection pool, using the fixed seed in Stroke_Config.
3. THE Data_Pipeline SHALL produce one modeling row per selected record, taken from the first full 10 s Window of the record.
4. THE Data_Pipeline SHALL assign a seeded sample of CinC_2017 records outside the 1000-record cohort to the Demo_Pool.
5. THE Data_Pipeline SHALL record the selected record IDs, Demo_Pool record IDs, and class counts in the data manifest.

### Requirement 3: Data — Signal Preprocessing and Windowing

**User Story:** As a data scientist, I want consistent preprocessing across all ECG and motion sources, so that models see comparable inputs regardless of dataset.

#### Acceptance Criteria

1. THE Data_Pipeline SHALL apply a zero-phase bandpass filter with cutoffs of 0.5 Hz and 40 Hz to every ECG signal.
2. THE Data_Pipeline SHALL resample every ECG signal to 125 Hz.
3. THE Data_Pipeline SHALL segment ECG signals into non-overlapping 10 s Windows of exactly 1250 finite samples.
4. THE Data_Pipeline SHALL cut 10 s motion Windows (500 samples per axis at 50 Hz) from the continuous raw UCI_HAPT accelerometer and gyroscope streams.
5. WHEN the Data_Pipeline cuts a motion Window, THE Data_Pipeline SHALL label the motion Window with the activity or transition label that covers the majority of the Window's samples.
6. WHEN the Data_Pipeline processes AFDB slices, THE Data_Pipeline SHALL label each AFDB Window as AF or non-AF from the AFDB rhythm annotations and record each annotated AF onset offset.

### Requirement 4: Data — Patient-Disjoint Splits

**User Story:** As a data scientist, I want splits by record and subject, so that no patient appears in more than one split and metrics are not inflated by leakage.

#### Acceptance Criteria

1. THE Data_Pipeline SHALL split the 1000-record cohort into train, validation, and test partitions of 70%, 15%, and 15%, stratified by label, with the record as the grouping unit.
2. THE Data_Pipeline SHALL split UCI_HAR and UCI_HAPT by subject ID and assign each subject to the same partition in both datasets.
3. THE Data_Pipeline SHALL produce pairwise-disjoint sets of record IDs and subject IDs across all partitions, the AFDB external set, and the Demo_Pool.
4. THE Training_Runner SHALL use grouped, stratified 5-fold cross-validation inside the train partition for model selection and hyperparameter tuning.
5. THE Data_Pipeline SHALL store the partition assignment of every record and subject in a committed split manifest.

### Requirement 5: Data — Provenance and Data Documentation

**User Story:** As a judge or teammate, I want every data point traceable to its source, so that the demo's claims about real data can be verified.

#### Acceptance Criteria

1. THE Data_Pipeline SHALL attach Provenance to every processed Window.
2. THE Data_Pipeline SHALL write a data manifest listing each processed file with row count, class counts, total download size, and content hash.
3. THE Data_README SHALL list, for each dataset, the source URL, the license as stated on the source page, the required citation, the version, the download size, and the preprocessing steps.
4. THE Data_README SHALL state each item in the Known Limitations section of this document.
5. THE Data_README SHALL document the NSTDB addition and the IMU-derived artifact fallback described in D5.

### Requirement 6: ML — Classical HRV Baseline

**User Story:** As a data scientist, I want an interpretable feature-based baseline, so that the deep model's gains can be judged against a transparent reference.

#### Acceptance Criteria

1. THE Classical_Model SHALL detect R-peaks in each ECG Window and compute RMSSD, SDNN, pNN50, mean heart rate, and RR_Irregularity.
2. THE Training_Runner SHALL train a logistic regression classifier and a gradient boosting classifier on the Classical_Model features.
3. THE Training_Runner SHALL fit feature scaling and any imputation on the train partition only.
4. IF fewer than 3 R-peaks are detected in an ECG Window, THEN THE Classical_Model SHALL mark the Window's features invalid and classify the Window as a data-quality case instead of producing an AF_Probability.

### Requirement 7: ML — Small CNN-LSTM on Raw ECG

**User Story:** As a data scientist, I want a compact deep model with standard regularization, so that the model can learn morphology beyond RR features without overfitting.

#### Acceptance Criteria

1. THE CNN_LSTM_Model SHALL accept one 1250-sample ECG Window and output an AF_Probability in the range [0, 1].
2. THE CNN_LSTM_Model SHALL have at most 200,000 trainable parameters.
3. THE Training_Runner SHALL apply amplitude scaling, baseline wander, Gaussian noise, and time-shift augmentation to train-partition Windows only.
4. THE Training_Runner SHALL train the CNN_LSTM_Model with dropout, weight decay, and class weights inversely proportional to class frequency.
5. THE Training_Runner SHALL stop training at the epoch cap in Stroke_Config, or earlier when validation loss has not improved for the configured early-stopping patience.
6. THE Training_Runner SHALL restore the weights from the epoch with the lowest validation loss before export.

### Requirement 8: ML — Threshold Selection and Evaluation Metrics

**User Story:** As a judge, I want thresholds chosen on validation and a single honest test evaluation, so that reported performance reflects unseen data.

#### Acceptance Criteria

1. THE Evaluation_Harness SHALL select each model's decision threshold on the validation partition as the highest threshold that achieves sensitivity of at least 0.90.
2. IF no threshold achieves validation sensitivity of at least 0.90, THEN THE Evaluation_Harness SHALL select the threshold with maximum validation sensitivity and record the shortfall in the evaluation report.
3. THE Evaluation_Harness SHALL evaluate the test partition once per final model version with the validation-selected threshold, and SHALL record the test-run timestamp in the metrics JSON.
4. IF a test evaluation already exists for a model version, THEN THE Evaluation_Harness SHALL refuse a repeat test evaluation unless an explicit override flag is passed, and SHALL log every override in the evaluation report.
5. THE Evaluation_Harness SHALL report AUROC, AUPRC, F1, sensitivity, specificity, and the confusion matrix for cross-validation, validation, test, and AFDB external validation.
6. THE Evaluation_Harness SHALL report a reliability diagram, the Brier score, and learning curves at train fractions 0.10, 0.25, 0.50, 0.75, and 1.00.
7. THE Evaluation_Harness SHALL report 95% bootstrap confidence intervals for test AUROC, sensitivity, and specificity.
8. THE Evaluation_Harness SHALL select the deployed model as the model with the higher validation AUPRC and record the selection rationale in the evaluation report.

### Requirement 9: ML — Overfitting and Leakage Controls

**User Story:** As a mentor, I want explicit overfitting checks, so that a perfect score is treated as a red flag instead of a success.

#### Acceptance Criteria

1. IF any validation, test, or external metric equals 1.0, THEN THE Evaluation_Harness SHALL set an `overfit_suspect` flag in the metrics JSON and print a warning at the top of the evaluation report.
2. THE Evaluation_Harness SHALL run a label-shuffle check that retrains each model on permuted train labels and reports the resulting validation AUROC.
3. IF the label-shuffle validation AUROC falls outside the range [0.40, 0.60], THEN THE Evaluation_Harness SHALL set a `leakage_suspect` flag and print a warning in the evaluation report.
4. IF train AUROC exceeds validation AUROC by more than 0.10, THEN THE Evaluation_Harness SHALL set a `generalization_gap` flag in the metrics JSON.
5. THE Evaluation_Harness SHALL evaluate the deployed model on AFDB Windows as an external validation set and report the external metrics next to the test metrics.
6. THE Evaluation_Harness SHALL add NSTDB motion-artifact noise to test Windows at SNR levels of 24, 12, 6, and 0 dB and report AUROC, sensitivity, and specificity per level.
7. IF the split manifest shows any record or subject ID in more than one of train, validation, test, AFDB external, or Demo_Pool, THEN THE Training_Runner SHALL stop before training with an error listing the overlapping IDs.

### Requirement 10: ML — Model Export, Runtime Inference, and Model Card

**User Story:** As a backend developer, I want a portable model artifact with documented limits, so that the backend can score windows on a laptop CPU without the training stack.

#### Acceptance Criteria

1. THE Training_Runner SHALL export the deployed model as an ONNX file plus a metadata JSON. The metadata SHALL contain model version, model type, input specification (125 Hz, 1250 samples), decision threshold, seed, data manifest hash, metrics summary, and overfitting flags.
2. WHEN the Training_Runner exports a model, THE Training_Runner SHALL verify on 100 test Windows that ONNX outputs differ from native framework outputs by at most 1e-4.
3. THE Inference_Service SHALL score ECG Windows with ONNX Runtime on CPU, without importing torch.
4. IF the Model_Artifact is missing or fails to load, THEN THE Inference_Service SHALL report the stroke feature as unavailable through the Stroke_API while existing monitoring and alerts continue to run.
5. THE Model_Card SHALL cover intended use, out-of-scope use, training data, evaluation results, overfitting checks, limitations, and bias considerations (recording device, unknown demographics, lab-scripted motion).
6. THE Model_Card SHALL state that the model detects AF-like rhythm patterns, is not a medical device, and does not detect stroke.

### Requirement 11: Motion — Motion Model

**User Story:** As a user, I want the app to understand my movement, so that noisy ECG during exercise is discounted and a collapse or prolonged stillness is noticed.

#### Acceptance Criteria

1. THE Motion_Model SHALL compute acceleration magnitude, signal energy, posture angle relative to gravity, and jerk for each motion Window.
2. THE Motion_Model SHALL classify each motion Window into exactly one activity state: dynamic, static, or lying.
3. WHEN a motion Window's acceleration-magnitude variance or jerk exceeds the motion-artifact thresholds in Stroke_Config, THE Motion_Model SHALL set the motion-artifact flag on that motion Window.
4. WHEN a transition to the lying state is followed by lying or static Windows with energy below the inactivity threshold for at least the prolonged-inactivity duration in Stroke_Config, THE Motion_Model SHALL emit a prolonged-inactivity signal.
5. WHEN a peak acceleration magnitude above the impact threshold in Stroke_Config is followed, within the configured gap, by a lying or static Window, THE Motion_Model SHALL emit a sudden-collapse signal.
6. THE Evaluation_Harness SHALL report per-class precision, recall, and F1 of the Motion_Model activity state on held-out UCI_HAPT and UCI_HAR subjects.

### Requirement 12: Fusion — ECG and Motion Guardrail

**User Story:** As a user, I want rhythm alerts gated by motion context, so that I get fewer false alarms during activity and escalation only when motion corroborates a possible acute event.

#### Acceptance Criteria

1. THE Stroke_Config SHALL hold every fusion, motion, countdown, threshold-nudge, and persona-timing parameter, each with an inline comment explaining its purpose.
2. IF a Stroke_Config parameter is outside the valid range documented in Stroke_Config, THEN THE Stroke_Config SHALL raise an error at backend startup naming the parameter.
3. WHILE the paired motion Window has the motion-artifact flag set, THE Fusion_Engine SHALL mark the ECG Window as unreliable and exclude the ECG Window from the Watch count.
4. WHEN AF_Probability exceeds the Personal_Threshold in at least K of the last N Reliable_Windows, THE Fusion_Engine SHALL enter the Watch state.
5. WHILE the Fusion_Engine is in the Watch state without a Corroborating_Motion_Signal, THE Fusion_Engine SHALL report Watch as a non-urgent rhythm-review state without a Countdown.
6. WHEN the Watch state and a Corroborating_Motion_Signal occur within the coincidence interval in Stroke_Config, THE Fusion_Engine SHALL raise a Warning.
7. IF more than half of the last N ECG Windows are unreliable or lack valid features, THEN THE Fusion_Engine SHALL report the Data_Quality state.
8. THE Fusion_Engine SHALL persist, for every processed Window, the AF_Probability, reliability flag, activity state, motion flags, fusion state, guardrail-downgrade reason, and Provenance.
9. THE Fusion_Engine SHALL produce identical fusion states for identical Window sequences under an identical Stroke_Config.
10. WHEN the Personal_Threshold is raised for a fixed Window sequence, THE Fusion_Engine SHALL produce a number of Watch-state Windows that is unchanged or lower.

### Requirement 13: Fusion — ECG-Only versus ECG+Motion Evaluation

**User Story:** As a judge, I want a quantitative comparison of ECG-only and ECG+motion alerting, so that the value of the motion guardrail is shown with evidence.

#### Acceptance Criteria

1. THE Fusion_Evaluator SHALL build 200 Episodes with the fixed seed. Episodes SHALL use only test-partition CinC_2017 Windows, AFDB Windows, NSTDB noise, and held-out-subject UCI_HAPT motion Windows.
2. THE Fusion_Evaluator SHALL compose the Episodes as:
   - 40 AF-onset Episodes with collapse or prolonged inactivity
   - 40 AF-onset Episodes with ordinary activity
   - 60 normal-rhythm Episodes at rest
   - 60 normal-rhythm Episodes during vigorous motion with motion-artifact-corrupted ECG
3. THE Fusion_Evaluator SHALL compute False_Alarms_Per_Day, Episode-level sensitivity, and median time-to-alert from AF onset, for both the ECG-only configuration (K-of-N on all Windows, no motion input) and the ECG+motion configuration (Fusion_Engine).
4. THE Fusion_Evaluator SHALL report Watch-level and Warning-level results in separate tables, and label the Warning-level comparison as dependent on how the Episodes were constructed.
5. THE Fusion_Evaluator SHALL report 95% bootstrap confidence intervals over Episodes for every compared metric.
6. THE Fusion_Evaluator SHALL write the comparison tables and a time-to-alert plot to the evaluation report.

### Requirement 14: Warning — Warning Event Creation and Persistence

**User Story:** As a user, I want every warning recorded with its evidence, so that I and a clinician can review what triggered the warning.

#### Acceptance Criteria

1. WHEN the Fusion_Engine raises a Warning, THE Warning_Service SHALL create a warning event with status `active`, a Countdown deadline equal to the creation time plus the configured countdown duration, an explanation from the Explainer_Adapter, and the Provenance of the triggering Windows.
2. THE Warning_Service SHALL store with each warning event the ECG snippet and motion snippet covering the configured context duration before the trigger (default 30 s).
3. WHILE a warning event is `active`, THE Warning_Service SHALL attach later Warning triggers to the existing active warning event instead of creating a new warning event.
4. WHILE `warnings_enabled` is off in user settings, THE Warning_Service SHALL record fusion states for each Window and create no warning events.
5. THE Warning_Service SHALL restrict warning event status values to `active`, `cancelled_by_user`, `confirmed`, and `escalated`.
6. WHEN a warning event changes status, THE Warning_Service SHALL append the old status, new status, actor (`user` or `system`), and timestamp to the event's status history.
7. WHEN DB_Bootstrap runs, THE Warning_Service SHALL create the stroke tables (`ml_windows`, `warning_events`, `warning_feedback`, `threshold_adjustments`) idempotently, leaving existing tables and rows unchanged.

### Requirement 15: Warning — Cancel and Get Help

**User Story:** As a user, I want to cancel a false warning or ask for help, so that I stay in control of what happens next.

#### Acceptance Criteria

1. WHEN the user cancels an `active` warning event, THE Warning_Service SHALL set the status to `cancelled_by_user`, record the cancel time, and stop the Countdown.
2. WHEN the user cancels a warning event that is already `cancelled_by_user`, THE Warning_Service SHALL return the existing event unchanged and record no additional false-alarm label.
3. IF the user cancels a warning event with status `escalated` or `confirmed`, THEN THE Warning_Service SHALL reject the request with HTTP 409 and leave the event unchanged.
4. WHEN the user confirms an `active` warning event ("Get help"), THE Warning_Service SHALL set the status to `confirmed` and return the warning summary needed to open the existing emergency flow.
5. WHEN the user confirms a warning event that is already `confirmed`, THE Warning_Service SHALL return the existing event unchanged.
6. IF the user confirms a warning event with status `cancelled_by_user` or `escalated`, THEN THE Warning_Service SHALL reject the request with HTTP 409 and leave the event unchanged.
7. IF a cancel or confirm request arrives after the Countdown deadline but before an escalation has been committed, THEN THE Warning_Service SHALL apply the user's request.

### Requirement 16: Warning — Countdown Expiry and Automatic Simulated Escalation

**User Story:** As a user who may be unable to respond, I want the app to escalate automatically, so that help is requested in a simulated way when I do not answer.

#### Acceptance Criteria

1. THE Warning_Service SHALL check Countdown expiry on every Monitoring_Tick loop iteration, whether the simulator is running or paused.
2. WHEN an `active` warning event's Countdown deadline passes with no user response while `emergency_enabled` is on, THE Warning_Service SHALL set the status to `escalated` with escalation channel `simulated_dispatch`. Within one Monitoring_Tick interval after the deadline, THE Warning_Service SHALL create a dispatch through the Emergency_Service on the `simulated` channel.
3. THE Warning_Service SHALL use the `simulated` channel for every automatic dispatch, regardless of the `REAL_DISPATCH_ENABLED` setting.
4. THE Warning_Service SHALL link each automatic dispatch to the warning event and record the trigger `auto_escalation_no_response` with the routing reason.
5. WHEN an `active` warning event's Countdown deadline passes with no user response while `emergency_enabled` is off, THE Warning_Service SHALL set the status to `escalated` with escalation channel `in_app_only` and create no dispatch event.
6. IF the Emergency_Service raises EmergencyNotAvailable during automatic escalation, THEN THE Warning_Service SHALL set the escalation channel to `in_app_only` and store the failure reason on the warning event.
7. THE Warning_Service SHALL build the automatic dispatch finding summary from the Explainer_Adapter output using the phrase "possible acute event signs".
8. THE Warning_Service SHALL leave the existing real-dispatch gate (explicit confirmation plus `REAL_DISPATCH_ENABLED`) unchanged.

### Requirement 17: Warning — False-Alarm Feedback and Personal Threshold Nudge

**User Story:** As a user who cancels false alarms, I want the app to learn from my feedback within safe bounds, so that repeated false alarms decrease without hiding real signals.

#### Acceptance Criteria

1. WHEN a warning event first changes to `cancelled_by_user`, THE Warning_Service SHALL store a false-alarm label linked to the warning event and the warning event's triggering Windows.
2. WHEN a new false-alarm label brings the user's cumulative false-alarm label count to 3 or more, THE Warning_Service SHALL increase the Personal_Threshold offset by the configured step (default 0.01).
3. THE Warning_Service SHALL cap the cumulative Personal_Threshold offset at +0.05.
4. THE Warning_Service SHALL keep the Personal_Threshold within [base threshold, base threshold + 0.05] and non-decreasing between resets, for every sequence of cancels.
5. WHEN the Personal_Threshold offset changes, THE Warning_Service SHALL log the old value, new value, triggering warning event ID, and timestamp.
6. WHEN the simulator is reset, THE Warning_Service SHALL reset the Personal_Threshold offset to 0 and log the reset.

### Requirement 18: Personas — Persona Scenario Framework

**User Story:** As a demonstrator, I want data-grounded personas next to the existing scenarios, so that the demo shows real signals end to end with repeatable outcomes.

#### Acceptance Criteria

1. THE Persona_Simulator SHALL offer the Personas `healthy`, `stroke_event`, and `false_alarm` alongside scenarios A, B, and C through the existing scenario endpoint.
2. WHEN a Persona is selected, THE Persona_Simulator SHALL reset the run and start the Persona script from the first Window, consistent with existing scenario switching.
3. WHILE a Persona is running, THE Persona_Simulator SHALL process the next configured number of consecutive Windows (default 3) on each Monitoring_Tick.
4. THE Persona_Simulator SHALL produce identical Window sequences, AF_Probabilities, fusion states, and warning event outcomes (excluding wall-clock timestamps) for repeated runs with the same seed and Stroke_Config.
5. THE Persona_Simulator SHALL draw real ECG Windows only from the Demo_Pool and AFDB, and real motion Windows only from held-out UCI_HAPT subjects.
6. THE Persona_Simulator SHALL derive hourly `hr` and `hrv` measurements from real ECG Windows and set `is_synthetic` to 0 on those rows. Measurement rows without a real source SHALL keep `is_synthetic` set to 1.
7. WHEN scenario A, B, or C is selected, THE Persona_Simulator SHALL keep the existing generation behavior and outputs of that scenario unchanged.

### Requirement 19: Personas — Healthy Persona

**User Story:** As a demonstrator, I want a healthy persona built from real data, so that the demo shows the system staying quiet for normal life.

#### Acceptance Criteria

1. THE Persona_Simulator SHALL build the Healthy Persona from Demo_Pool Normal CinC_2017 Windows paired with real UCI_HAPT walking, sitting, and lying motion Windows.
2. WHEN the Healthy Persona script runs to completion under the default Stroke_Config, THE Fusion_Engine SHALL raise zero Warnings.

### Requirement 20: Personas — Stroke-Event Persona

**User Story:** As a demonstrator, I want a persona with a real AF onset followed by lying still, so that the full warning, countdown, and automatic simulated dispatch flow can be shown honestly.

#### Acceptance Criteria

1. THE Persona_Simulator SHALL build the Stroke-event Persona from one AFDB recording slice containing an annotated AF onset preceded by at least 2 minutes of non-AF rhythm from the same person.
2. THE Persona_Simulator SHALL pair the post-onset ECG Windows with a real UCI_HAPT stand-to-lie transition Window, followed by real lying motion Windows with energy below the inactivity threshold.
3. WHEN the Stroke-event Persona runs under the default Stroke_Config with no user response while `emergency_enabled` is on, THE Warning_Service SHALL progress the warning event through the Normal, Watch, Warning, and `escalated` (`simulated_dispatch`) stages in that order.
4. WHEN the Stroke-event Persona runs under the default Stroke_Config, THE Fusion_Engine SHALL raise the Warning within 120 s of wall-clock time after Persona start.
5. THE Persona_Simulator SHALL attach to the Stroke-event Persona's motion Windows a note stating that the motion is a controlled lie-down from a lab dataset and not a real fall or stroke.

### Requirement 21: Personas — False-Alarm Persona

**User Story:** As a demonstrator, I want a persona where vigorous movement makes the ECG look irregular, so that the demo shows both the motion guardrail and the user cancel and feedback loop.

#### Acceptance Criteria

1. THE Persona_Simulator SHALL build the first False-alarm segment from Demo_Pool Normal CinC_2017 Windows corrupted with NSTDB motion-artifact noise and paired with real UCI_HAPT stair-walking motion Windows.
2. WHEN the first False-alarm segment runs, THE Fusion_Engine SHALL mark the corrupted ECG Windows unreliable, raise zero Warnings, and record a guardrail-downgrade reason for each downgraded Window.
3. WHEN the first False-alarm segment is replayed through the ECG-only configuration, THE Fusion_Evaluator SHALL report at least one alert, demonstrating the guardrail's effect.
4. THE Persona_Simulator SHALL build the second False-alarm segment from Demo_Pool Normal CinC_2017 Windows with low-level NSTDB noise below the motion-artifact threshold, followed by a real UCI_HAPT lie-down-and-rest sequence, so that a Warning is raised.
5. WHEN the user taps "I'm OK, cancel warning" during the second False-alarm segment, THE Warning_Service SHALL cancel the warning event and store a false-alarm label.

### Requirement 22: Personas — Synthetic Gap-Filling and Realism Validation

**User Story:** As a judge, I want synthetic data used only to fill gaps and validated against real data, so that the demo's realism claims are supported.

#### Acceptance Criteria

1. THE Persona_Simulator SHALL generate long-timeline filler ECG with NeuroKit2 `ecg_simulate`, using heart-rate mean and standard deviation fitted from RR statistics of train-partition real records.
2. THE Persona_Simulator SHALL label every filler Window with Provenance dataset `synthetic:neurokit2` and the fitted parameters.
3. THE Realism_Validator SHALL run two-sample Kolmogorov–Smirnov tests between real test-partition Windows and synthetic Windows for heart rate, RMSSD, and RR_Irregularity, and report each statistic, p-value, and an overlay plot.
4. IF a Kolmogorov–Smirnov p-value is below 0.05, THEN THE Realism_Validator SHALL label that metric "distribution differs" in the realism section of the evaluation report.
5. THE Realism_Validator SHALL run TSTR by training the Classical_Model on synthetic Normal and RR-irregular AF-like Windows, testing on the real test partition, and reporting AUROC next to the train-on-real AUROC.
6. IF any Persona Window's Provenance record ID appears in the train, validation, or test partition, THEN THE Realism_Validator SHALL fail with an error listing the overlapping IDs.

### Requirement 23: Explainer — ExplainerAdapter Placeholder

**User Story:** As a developer, I want an explainer interface with a disabled local-LLM stub, so that a privacy-preserving on-device LLM can be added later without rewriting the warning flow.

#### Acceptance Criteria

1. THE Explainer_Adapter SHALL define one interface that returns explanation text for a fusion state or warning event.
2. THE Template_Explainer SHALL be the active Explainer_Adapter implementation. THE Template_Explainer SHALL build explanations from template text plus the triggering values (K-of-N count, AF_Probability range, reliability, and motion signal).
3. THE Local_LLM_Explainer SHALL report `is_available` as False and raise NotImplementedError with the message "future adapter — not implemented in MVP", following the pattern of `backend/app/adapters/sensor_stubs.py`.
4. THE Template_Explainer SHALL phrase every explanation with "possible acute event signs" or "AF-related rhythm signs", include an experimental label, and exclude the phrase "stroke detected" and diagnostic statements.
5. THE Project_Docs SHALL include a roadmap note describing a future on-device or local LLM explainer for privacy. No LLM weights are downloaded in this feature.

### Requirement 24: API — Stroke Endpoints

**User Story:** As the mobile client, I want `/stroke/*` endpoints, so that the app can show status, history, and details and send user decisions.

#### Acceptance Criteria

1. WHEN the client requests `GET /stroke/status`, THE Stroke_API SHALL return:
   - fusion state, latest AF_Probability, and reliability
   - the active warning event ID, Countdown deadline, and seconds remaining
   - base threshold, threshold offset, and cumulative cancel count
   - model version and feature availability
   - `processedLocally` and `isExperimental`
2. WHEN the client requests `GET /stroke/warnings`, THE Stroke_API SHALL return warning events newest first, with a `limit` parameter (default 50, maximum 200).
3. WHEN the client requests `GET /stroke/warnings/{id}`, THE Stroke_API SHALL return the warning event's ECG snippet, motion snippet, explanation, Provenance, status history, escalation channel, and linked dispatch event ID.
4. WHEN the client sends `POST /stroke/warnings/{id}/cancel` or `POST /stroke/warnings/{id}/confirm`, THE Stroke_API SHALL apply the Warning_Service rules in Requirement 15 and return the resulting warning event.
5. WHEN the client requests `GET /stroke/model`, THE Stroke_API SHALL return the Model_Artifact metadata, metrics summary, overfitting flags, and Model_Card summary.
6. WHEN the client requests `GET /stroke/timeline` with a time range, THE Stroke_API SHALL return per-Window AF_Probability, reliability, spike markers for Windows above the Personal_Threshold, and warning event markers.
7. IF a requested warning event ID does not exist, THEN THE Stroke_API SHALL return HTTP 404.
8. THE Stroke_API SHALL use camelCase JSON field names and set `isExperimental` to true in every response.
9. THE Stroke_API SHALL be registered in `backend/app/main.py` by one additive line, with all existing routes keeping their paths and response shapes.

### Requirement 25: Mobile — API Types and Hooks

**User Story:** As a mobile developer, I want typed client functions and hooks for `/stroke/*`, so that screens consume the API consistently with existing patterns.

#### Acceptance Criteria

1. THE Mobile_App SHALL define TypeScript types for every Stroke_API response in `mobile/api/types.ts`, and client functions and hooks in `mobile/api/client.ts` and `mobile/api/hooks.ts`, following the existing patterns.
2. WHILE a warning event is `active`, THE Mobile_App SHALL refresh stroke status at an interval of at most 2 s.
3. THE Mobile_App SHALL compute the displayed Countdown from the server-provided deadline.

### Requirement 26: Mobile — StrokeWarningCard

**User Story:** As a user, I want a clear warning card with a countdown and two large buttons, so that I can respond quickly and accessibly.

#### Acceptance Criteria

1. WHILE a warning event is `active`, THE StrokeWarningCard SHALL appear on the Dashboard and Insights screens with the remaining Countdown seconds, an "I'm OK, cancel warning" button, and a "Get help" button.
2. WHEN the user taps "I'm OK, cancel warning", THE StrokeWarningCard SHALL send the cancel request and display a confirmation that the warning was recorded as a false alarm.
3. WHEN the user taps "Get help", THE StrokeWarningCard SHALL send the confirm request and open the existing emergency screen.
4. THE StrokeWarningCard SHALL give each button an accessibility role, an accessibility label, and a tap target of at least 48 × 48 dp, and SHALL announce Countdown updates through a polite live region.
5. WHILE the fusion state is Watch, THE StrokeWarningCard SHALL show a non-urgent "AF-related rhythm signs, review" message without a Countdown.
6. WHEN a warning event is escalated with channel `in_app_only`, THE Mobile_App SHALL show a full-width alert banner at the top of the Dashboard containing the existing emergency guidance text, and keep the banner visible until the user taps "Acknowledge".
7. WHEN a warning event is escalated with channel `simulated_dispatch`, THE StrokeWarningCard SHALL state that a simulated dispatch was recorded and that nothing was sent to real services.
8. THE StrokeWarningCard SHALL display an experimental, non-diagnostic label and label AF_Probability as a model output, not a clinically validated score.

### Requirement 27: Mobile — History Timeline and Warning List

**User Story:** As a user, I want to see warning spikes over time, so that I can review patterns and past decisions.

#### Acceptance Criteria

1. THE History_Screen SHALL display an AF_Probability timeline with a Personal_Threshold line, spike markers for Windows above the Personal_Threshold, and warning event markers.
2. THE History_Screen SHALL display a warning event list with status chips for `active`, `cancelled_by_user`, `confirmed`, and `escalated`. Each chip SHALL use both color and a text label.
3. WHEN the user taps a warning event in the list, THE Mobile_App SHALL open the Warning_Detail_Screen for that event.
4. IF the selected range has no Windows or no warning events, THEN THE History_Screen SHALL display an explicit empty state.

### Requirement 28: Mobile — Warning Detail Screen

**User Story:** As a user or judge, I want to see the raw evidence behind a warning, so that I can check what the system saw and where the data came from.

#### Acceptance Criteria

1. THE Warning_Detail_Screen SHALL display the ECG strip, the acceleration-magnitude motion trace, the explanation, the status history, and each Window's Provenance (dataset, record or subject ID, offset).
2. THE Warning_Detail_Screen SHALL label each synthetic filler Window as synthetic.
3. WHERE a warning event comes from the Stroke-event Persona, THE Warning_Detail_Screen SHALL display the controlled lie-down note from Requirement 20.
4. THE Warning_Detail_Screen SHALL provide text alternatives summarizing the ECG strip and the motion trace for screen readers.

### Requirement 29: Mobile — Persona Picker, Privacy Badge, and Compatibility

**User Story:** As a demonstrator, I want personas selectable in the existing picker and the teammate's UI preserved, so that the demo works on Expo web without regressions.

#### Acceptance Criteria

1. THE Scenario_Picker SHALL list scenarios A, B, and C and the three Personas, with the Stroke-event Persona labeled "Possible acute event (demo)".
2. THE Privacy_Badge SHALL display "Processed locally", with an accessible description stating that processing runs on the device or the local HeartGuardian backend with no third-party cloud.
3. THE Mobile_App SHALL build new UI from the existing theme and the AppHeader, Icon, ChartLegend, and HealthTrendDetails components.
4. THE Mobile_App SHALL add any new screen or tab additively, keeping every existing screen, tab, and component rendering.
5. THE Mobile_App SHALL render every new screen and component on Expo web.

### Requirement 30: Teammate DB — Demo Seed Snapshot

**User Story:** As a teammate, I want a committed demo database that appears automatically, so that I can run the demo without regenerating data, while the live DB stays private.

#### Acceptance Criteria

1. THE Repository SHALL keep `backend/heartguardian.db` gitignored and track the Demo_Seed_DB through a gitignore exception.
2. WHEN DB_Bootstrap runs with `HEARTGUARDIAN_DB` unset and no file at the default DB path, THE DB_Bootstrap SHALL copy the Demo_Seed_DB to the default path before applying the schema.
3. WHEN DB_Bootstrap runs with `HEARTGUARDIAN_DB` set, THE DB_Bootstrap SHALL skip the snapshot copy.
4. WHEN DB_Bootstrap runs with an existing live DB, THE DB_Bootstrap SHALL keep existing rows and apply only idempotent, additive schema changes.
5. THE Demo_Seed_DB SHALL contain the current schema, including the stroke tables, and only synthetic personal data (names, phone numbers, contacts).

### Requirement 31: Docs — Project Documentation Updates

**User Story:** As a teammate owning presentation and ethics, I want accurate, reusable docs, so that I can present data provenance, results, and limitations without re-deriving them.

#### Acceptance Criteria

1. THE Project_Docs SHALL update README.md with dataset setup, ML pipeline commands (using `conda run -n hack1`), persona usage, the unauthenticated local-only API note, and accurate data provenance.
2. THE Project_Docs SHALL replace every claim that all data is synthetic with an accurate provenance statement covering real public datasets, real-derived measurements, and synthetic filler.
3. THE Project_Docs SHALL update docs/DEMO.md with a persona demo script (steps, expected on-screen states, timings) and a backup-video checklist (segments to record, resolution, narration cues, fallback if the live demo fails).
4. THE Project_Docs SHALL update TEAM.md with ownership of the new modules and the list of shared files edited additively.
5. THE Model_Card SHALL include a limitations and ethics section reusable by the presentation and ethics teammates.

### Requirement 32: Docs — Prior Art and Demo Talking Points

**User Story:** As a presenter, I want named existing devices cited, so that judges see that fall-based escalation and wearable AF alerts are established and useful, and see what this prototype adds.

#### Acceptance Criteria

1. THE Project_Docs SHALL include docs/PRIOR_ART.md, which summarizes in paraphrase Apple Watch Fall Detection and cites https://support.apple.com/en-us/HT208944. The summary covers hard-fall detection, about one minute of immobility, a 30 s countdown, an automatic emergency call, and messages with location to emergency contacts.
2. THE docs/PRIOR_ART.md file SHALL cite the FDA post-market evaluation of smartwatch cardiovascular notifications (https://www.fda.gov/science-research/advancing-regulatory-science/post-market-evaluation-smartwatch-cardiovascular-notifications), noting that Apple, Samsung, and Fitbit wearables provide AF notifications.
3. THE docs/PRIOR_ART.md file SHALL describe the innovation angle as fusing ECG rhythm and motion into one escalation decision with a cancel and feedback loop, without claiming to be first.
4. THE docs/PRIOR_ART.md file SHALL include demo talking points and an access date for each cited source.

### Requirement 33: Resources — Laptop Resource Limits

**User Story:** As the laptop owner, I want training and setup to stay lightweight and contained, so that other conda projects and the machine stay usable.

#### Acceptance Criteria

1. THE Training_Runner SHALL install packages only into the conda environment `hack1`, with exact pinned versions recorded in `backend/requirements-ml.txt` (offline) and `backend/requirements.txt` (runtime).
2. THE Training_Runner SHALL use the CPU-only torch build, limit torch to 2 threads, and run training at below-normal process priority.
3. THE Training_Runner SHALL enforce the epoch cap and early-stopping patience in Stroke_Config, and log the wall-clock duration of each pipeline stage.
4. THE Data_Pipeline SHALL keep total downloads at or below 500 MB and record the measured total in the data manifest.
5. IF torch installation or CNN_LSTM_Model training fails, THEN THE Training_Runner SHALL deploy the scikit-learn Classical_Model and record the fallback in the Model_Artifact metadata and the Model_Card.
6. WHEN a verification or demo-check step completes, THE Verification_Run SHALL stop every server or watcher process the step started.

### Requirement 34: Verification — Baseline-Compared Test Runs

**User Story:** As a maintainer, I want test results compared with a recorded baseline, so that new failures are caught and pre-existing failures are reported honestly.

#### Acceptance Criteria

1. THE Verification_Run SHALL record pytest, Jest, and `tsc --noEmit` results on the starting commit before any feature change.
2. WHEN feature work is complete, THE Verification_Run SHALL rerun pytest, Jest, and `tsc --noEmit` and report differences from the baseline.
3. IF a failure exists in the baseline, THEN THE Verification_Run SHALL report the failure without modifying other owners' modules to fix the failure.
4. THE Verification_Run SHALL include new backend tests covering K-of-N Watch logic, cancel and confirm idempotency and 409 rules, the threshold-nudge cap, split and Provenance disjointness, explainer wording, and DB_Bootstrap snapshot behavior.
5. THE Verification_Run SHALL run backend tests against temporary databases via `HEARTGUARDIAN_DB`, with no network access and no model training.
6. THE Verification_Run SHALL execute Python commands through `conda run --no-capture-output -n hack1`.

### Requirement 35: Delivery — Git Workflow

**User Story:** As the repository owner, I want the work isolated on a local branch with clean ignore rules, so that I can review everything before sharing.

#### Acceptance Criteria

1. THE Repository SHALL hold the feature work on the local branch `feat/stroke-ecg-motion`, created from the starting commit.
2. THE Repository SHALL receive local commits only, with no push to any remote.
3. THE Repository SHALL move the two personal steering ignore lines (`.kiro/steering/response-style.md`, `.kiro/steering/python-environment.md`) from `.gitignore` to `.git/info/exclude`, keeping both files ignored.
4. THE Repository SHALL stage files by explicit path and exclude the Raw_Cache, the live DB, and secret files from every commit.
5. THE Repository SHALL commit processed datasets and Model_Artifact files, each smaller than 50 MB.
