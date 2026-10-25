# Requirements Document — HeartGuardian AI

## Introduction

HeartGuardian AI is a cross-platform mobile application prototype that demonstrates how
wearable physiological data can be continuously analyzed to identify personalized health
trends and provide explainable, non-diagnostic alerts. It is a **hackathon prototype**, not
a clinically validated medical device. All physiological data in the MVP is **synthetic**
and must be clearly labeled as experimental.

The system is composed of:
- An Expo / React Native (TypeScript) mobile client with a dark-blue healthcare UI.
- A FastAPI (Python) backend exposing measurement, trend, analysis, insight, and scenario endpoints.
- A SQLite datastore for synthetic time-series measurements, baselines, anomalies, and alerts.
- A physiological data simulator with three selectable scenarios.
- A transparent, configurable anomaly-detection engine built on NumPy / Pandas / Scikit-learn.
- A care-network module: user-managed contacts and preferred doctor, a nearby provider directory,
  and a safety-gated emergency-response flow that can notify providers with location and key context.

### Non-Goals
- No hardware manufacturing.
- No clinically validated disease prediction or diagnosis.
- No collection or transmission of real patient data.
- No arbitrary numeric score presented as a validated cardiovascular risk.
- No unattended, fully automatic outreach to real emergency services based on experimental readings.
  In the MVP, real outbound contact is simulated by default and any real dispatch requires explicit
  user confirmation and opt-in configuration (see Requirements 10 and 11).

---

## Glossary

- **Reading / Measurement**: A single timestamped physiological sample (HR, HRV, SpO2, etc.).
- **Baseline**: A per-metric personal reference learned from historical readings.
- **Deviation**: How far a current rolling statistic sits from the baseline.
- **Anomaly finding**: A structured record describing a detected deviation or unusual signal combination.
- **Alert**: A user-facing message derived from findings, with explanation and next steps.
- **Scenario**: A simulator mode (Normal, Gradual Deviation, Rhythm Irregularity).
- **Care profile**: User-saved personal contact info, emergency contacts, and a preferred doctor.
- **Provider**: A doctor or hospital record with location and contact details (seeded demo directory).
- **Care network / directory**: The set of providers the app can suggest or contact.
- **Emergency event**: A system-detected `attention`-level situation that may trigger the response flow.
- **Dispatch**: The act of notifying a provider/contact with the patient's key info and location.
- **Simulated dispatch**: A dispatch recorded/displayed in-app rather than sent to a real recipient
  (the MVP default).

---

## Requirements

### Requirement 1 — Mobile Dashboard

**User Story:** As a user, I want a modern dashboard that shows my current cardiovascular
metrics and trends at a glance, so that I can understand my status quickly.

#### Acceptance Criteria
1. WHEN the dashboard loads THEN the system SHALL display current heart rate (bpm),
   heart rate variability (ms), blood oxygen saturation (%), and a simulated heart rhythm status.
2. WHEN the dashboard loads THEN the system SHALL display daily activity and sleep indicators.
3. WHEN the dashboard loads THEN the system SHALL display historical trend charts for each primary metric.
4. WHEN the dashboard loads THEN the system SHALL display a personalized monitoring status and the wearable connection status.
5. WHERE any value originates from the simulator THE system SHALL visibly label it as simulated/experimental data.
6. WHEN metric data is unavailable THEN the system SHALL show an explicit "no data / low quality" state rather than a misleading value.
7. THE dashboard SHALL use a dark-blue healthcare theme with accessible color contrast (WCAG AA for text) and clear typography.

### Requirement 2 — Wearable Data Simulator

**User Story:** As a demonstrator, I want to generate realistic synthetic physiological data
under different scenarios, so that I can show the app's behavior without real hardware.

#### Acceptance Criteria
1. THE simulator SHALL produce timestamped readings for HR, HRV, SpO2, rhythm flag, activity, and sleep.
2. THE simulator SHALL provide three scenarios: Normal (A), Gradual Deviation (B), and Rhythm Irregularity (C).
3. WHEN Scenario A is active THEN measurements SHALL fluctuate within a simulated personal baseline.
4. WHEN Scenario B is active THEN resting HR SHALL trend upward, HRV SHALL trend downward, and sleep duration SHALL decline over simulated weeks.
5. WHEN Scenario C is active THEN the simulator SHALL inject a synthetic irregular-rhythm pattern.
6. THE simulator SHALL expose Start, Pause, Reset, and Scenario Selection controls via the API and UI.
7. WHEN Reset is invoked THEN the simulator SHALL clear generated session data and return to the selected scenario's start state.
8. THE simulator SHALL use a seedable random generator so runs are reproducible.
9. ALL simulated measurements SHALL be stored and labeled as synthetic.

### Requirement 3 — Personalized AI Analysis

**User Story:** As a user, I want the app to learn what is normal for me and flag meaningful
changes, so that alerts are personalized rather than generic.

#### Acceptance Criteria
1. THE analysis engine SHALL compute a per-metric baseline from historical measurements.
2. THE engine SHALL compute rolling statistics (mean, std, trend) and deviations from baseline.
3. THE engine SHALL detect persistent changes (sustained over a configurable window) and unusual combinations of signals.
4. WHEN data is missing or low quality THEN the engine SHALL classify it as a data-quality issue rather than a physiological trend.
5. THE engine SHALL output structured anomaly findings (metric, type, window, severity-band, supporting values).
6. THE engine SHALL use transparent, configurable demonstration thresholds stored in a single config location.
7. THE engine SHALL produce reproducible results for a fixed input dataset and config.
8. THE engine SHALL NOT present any numeric score as a clinically validated cardiovascular risk.

### Requirement 4 — AI Insights and Alerts

**User Story:** As a user, I want clear, explainable alerts and emergency guidance, so that I
know what the data means and what to do next.

#### Acceptance Criteria
1. THE system SHALL support three interface states: Normal monitoring, Trend review recommended, and Potentially concerning measurement requiring further assessment.
2. WHEN an alert is shown THEN it SHALL explain the supporting data and indicate appropriate next steps.
3. THE system SHALL always display symptom-based emergency guidance instructing users to contact emergency services for possible heart attack or stroke symptoms, regardless of wearable readings.
4. THE system SHALL NOT claim to diagnose arrhythmia, heart attack, or stroke.
5. EVERY alert SHALL carry an "experimental / not medical advice" label.

### Requirement 5 — Historical Data and Visualization

**User Story:** As a user, I want to review my history across time ranges, so that I can see
how my metrics and baselines evolve.

#### Acceptance Criteria
1. THE system SHALL let users view daily, weekly, and monthly trends.
2. THE system SHALL display individual physiological baselines alongside trends.
3. THE system SHALL display detected anomalies and historical alerts.
4. THE system SHALL ship with sample historical data for demonstrations.
5. WHEN a time range has no data THEN the system SHALL display an explicit empty state.

### Requirement 6 — Device Integration Architecture

**User Story:** As a developer, I want a pluggable sensor interface, so that future adapters
can be added without rewriting the app.

#### Acceptance Criteria
1. THE system SHALL define a SensorAdapter interface.
2. THE system SHALL implement SimulatedSensorAdapter.
3. THE system SHALL define (interface-only, future) AppleHealthAdapter, HealthConnectAdapter, and BluetoothSensorAdapter.
4. THE MVP SHALL function fully without real wearable hardware.

### Requirement 7 — Backend and Data Storage

**User Story:** As the mobile client, I need backend endpoints and persistent storage, so
that data and analysis are served consistently.

#### Acceptance Criteria
1. THE backend SHALL expose endpoints to read measurements, retrieve historical trends, run anomaly analysis, retrieve insights, and select simulation scenarios.
2. THE backend SHALL persist synthetic data in SQLite.
3. THE backend SHALL NOT store real patient information.
4. THE backend SHALL return explicit error responses for invalid scenario or range requests.
5. THE backend SHALL expose an OpenAPI schema (FastAPI default) for the client.

### Requirement 8 — Privacy and Safety

**User Story:** As a user, I want my data handled safely and outputs clearly labeled, so that
I am not misled about the prototype's capabilities.

#### Acceptance Criteria
1. THE system SHALL store data locally when practical.
2. THE system SHALL NOT contain hardcoded credentials.
3. THE mobile application SHALL NOT embed API keys.
4. THE system SHALL use synthetic data for demonstration.
5. THE system SHALL label all medical outputs as experimental.
6. THE system SHALL NOT send real health data to third-party LLM services without consent and safeguards.
7. THE system SHALL make clear that alerts do not replace medical evaluation.

### Requirement 9 — Testing and Documentation

**User Story:** As a maintainer, I want automated tests and clear docs, so that the demo is
reproducible and the code is trustworthy.

#### Acceptance Criteria
1. THE project SHALL include tests for simulator behavior, baseline calculations, anomaly detection, missing-data handling, alert generation, API responses, scenario transitions, provider suggestion/distance logic, and the emergency-response routing and dispatch flow.
2. THE project SHALL include TypeScript tests for client logic and Python tests for backend/analytics.
3. THE project SHALL include a README with installation, configuration, and run instructions.
4. THE project SHALL include a short demonstration script and screenshot references.
5. WHEN the documented steps are followed THEN the demo SHALL run without real sensors or paid APIs.

### Requirement 10 — Care Profile and Provider Suggestions (User-Controlled, Optional)

**User Story:** As a user, I want to optionally save my contact details and a preferred doctor, and
optionally see suitable hospitals or doctors near me when a warning sign appears, so that I stay in
full control of if and how the app involves my contacts.

#### Acceptance Criteria
1. THE care profile and provider-suggestion features SHALL be entirely optional; the app SHALL function fully with them disabled or empty, and the user SHALL decide whether to enable and populate them.
2. THE system SHALL let the user create and edit a care profile containing their own contact
   details (name, phone), zero or more emergency contacts (name, relationship, phone), and an optional preferred doctor.
3. THE system SHALL persist the care profile locally and SHALL NOT transmit it to third parties except as part of a user-initiated, explicit emergency dispatch (Requirement 11).
4. THE system SHALL maintain a provider directory of doctors and hospitals, each with name, type, specialty, location (lat/lon), and contact details; the MVP SHALL ship a seeded synthetic directory.
5. WHEN provider suggestions are enabled AND an alert reaches the `trend_review` or `attention` state THEN the system SHALL offer suggested providers near the user's current location, ordered by suitability (distance and, for emergencies, life-saving capability).
6. WHEN provider suggestions are disabled THEN the system SHALL NOT surface the suggestion sheet automatically, though the user MAY still open it manually.
7. THE system SHALL compute distance between the user's current location and each provider and SHALL display it in the suggestion list.
8. WHEN the user's location is unavailable or location permission is denied THEN the system SHALL fall back to a configured/default location and clearly indicate that an approximate location is in use.
9. THE provider suggestion list SHALL distinguish the user's preferred doctor from directory results.
10. ALL provider data in the MVP SHALL be labeled synthetic/for-demonstration.

### Requirement 11 — Emergency Response and Dispatch (User-Controlled, Opt-In)

**User Story:** As a user, I want to decide whether the app may contact my preferred doctor or a
nearby capable hospital on my behalf — sharing my key information and current location — so that any
outreach happens only because I chose to enable and confirm it.

#### Acceptance Criteria
1. THE emergency-response flow SHALL be opt-in and disabled by default; it SHALL run ONLY when the user has explicitly enabled it. WHEN disabled, the system SHALL show warnings and static guidance but SHALL NOT initiate any dispatch.
2. WHEN the feature is enabled AND an emergency event is detected (an `attention`-level situation meeting the configured emergency criteria) THEN the system SHALL offer to start the emergency-response flow, with the user making the final decision to proceed.
3. THE emergency-response flow SHALL select a recipient using transparent, configurable rules:
   it SHALL prefer the user's preferred doctor WHEN that doctor is within a configurable reachable
   distance/time; OTHERWISE it SHALL select the nearest hospital capable of handling the emergency.
4. THE system SHALL assemble a dispatch payload containing the patient's key contact information,
   current location (coordinates and, when available, a human-readable description), emergency-contact
   details, and a concise, non-diagnostic summary of the triggering findings labeled experimental.
5. BEFORE any outbound contact (simulated or real) THE system SHALL require explicit user confirmation via a clearly
   labeled prompt with a short countdown, and SHALL provide a Cancel control that stops the dispatch; no dispatch SHALL occur without that confirmation.
6. WHERE no real provider channel is configured THE system SHALL perform a SIMULATED dispatch: it SHALL
   record and display the exact recipient, payload, and routing decision in-app WITHOUT contacting a real recipient.
7. THE system SHALL log every dispatch (simulated or real) with timestamp, selected recipient, routing
   reason, and payload summary, and SHALL make this history viewable by the user.
8. THE system SHALL also display static symptom-based emergency guidance instructing the user to contact
   local emergency services directly, independent of any automated dispatch.
9. THE system SHALL NOT perform unattended outreach of any kind; every dispatch SHALL be user-initiated and user-confirmed. The system SHALL NOT claim to diagnose a heart attack, stroke, or arrhythmia.
10. THE routing and selection logic SHALL be deterministic and reproducible for a fixed profile,
    directory, location, and configuration.

### Requirement 12 — Experimental Disclaimer and User Responsibility

**User Story:** As a user, I want the app to be upfront that it is experimental and that acting on
its warnings is my own decision, so that I understand the prototype's limits and my responsibility.

#### Acceptance Criteria
1. THE app SHALL present a clear, plain-language disclaimer on first launch stating that it is an experimental, non-clinical prototype that does not diagnose conditions and does not guarantee accuracy, reliability, or timeliness of its warnings.
2. THE disclaimer SHALL state that warnings may be false alarms or may be missed, and that the application and its authors are not responsible or liable for false alarms, missed events, or any outcome arising from use of the app.
3. THE disclaimer SHALL state that any decision to act on a warning — including whether to enable warnings, contact anyone, or trigger a dispatch — is solely the user's decision and responsibility.
4. THE disclaimer SHALL direct users to contact qualified medical professionals and local emergency services for real medical needs, and SHALL make clear the app does not replace professional medical evaluation.
5. THE user SHALL acknowledge the disclaimer once before using monitoring features, and the disclaimer SHALL remain accessible at any time (e.g., from Settings).
6. A concise experimental-and-not-liable notice SHALL also appear within the alerts/insights and emergency-dispatch surfaces.
7. THE disclaimer is a product notice for this prototype and SHALL NOT be construed as legal advice; wording is plain-language and not a substitute for reviewed legal terms.

---

## Acceptance (Project-Level)
- The mobile application launches successfully.
- Users can switch among all three scenarios.
- Simulated metrics and charts update correctly.
- The anomaly detector produces reproducible results.
- Alerts include understandable explanations.
- The demo works without real sensors or paid APIs.
- Automated tests pass.
- The README explains how to reproduce the demonstration.
- The interface clearly distinguishes simulated data from real medical measurements.
- The care profile, provider suggestions, and emergency response are optional and user-controlled;
  the app works fully with them disabled, and the user decides whether to enable them.
- Users can save a care profile and preferred doctor, and see nearby provider suggestions on a warning.
- The emergency-response flow is opt-in, selects a recipient by transparent rules, assembles the dispatch
  payload, requires user confirmation before any contact, and performs a simulated dispatch by default.
- A plain-language experimental disclaimer makes clear the app is not reliable, not responsible for
  false alarms, and that acting on warnings is solely the user's decision.
