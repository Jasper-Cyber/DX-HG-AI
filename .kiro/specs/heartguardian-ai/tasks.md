# Implementation Plan — HeartGuardian AI

Each phase leaves the app runnable. Check off tasks as they are completed.

## Phase 0 — Project scaffolding

- [x] 1. Initialize repository structure — _Owner: Jasper-Cyber_
  - Create `backend/` (FastAPI) and `mobile/` (Expo) folders and root `README.md`.
  - Add root `.gitignore` (Python, Node, Expo, SQLite db files, `.env`).
  - _Requirements: 7, 8_

- [x] 2. Scaffold FastAPI backend skeleton — _Owner: Jasper-Cyber_
  - Create `backend/pyproject.toml` (fastapi, uvicorn, sqlalchemy, numpy, pandas, scikit-learn, pytest, httpx).
  - Add `backend/app/main.py` with `/health` and CORS for the Expo dev client.
  - _Requirements: 7.1, 7.5_

- [x] 3. Scaffold Expo mobile app skeleton — _Owner: Helenawai_
  - Create Expo + TypeScript + Expo Router app in `mobile/` with tab layout and placeholder screens.
  - Add `theme.ts` dark-blue token set and a `SimulatedDataRibbon` placeholder.
  - _Requirements: 1.7, 8.5_

## Phase 1 — Data layer & SQLite

- [x] 4. Implement SQLite schema and repository layer — _Owner: Jasper-Cyber_
  - Create schema/migrations for `users`, `measurements`, `baselines`, `anomaly_findings`, `alerts`, `sim_state`.
  - Implement repository functions (insert/query readings, upsert baseline, store findings/alerts, read/update sim_state).
  - _Requirements: 7.2, 7.3, 2.9_

- [x] 5. Seed synthetic sample history — _Owner: Jasper-Cyber_
  - Add a `seed_data.py` script that generates a labeled synthetic dataset for demos.
  - _Requirements: 5.4, 8.4_

## Phase 2 — Simulator

- [x] 6. Implement SimulatorService with seedable RNG — _Owner: Raffy_
  - Scenario A (Normal), B (Gradual Deviation), C (Rhythm Irregularity) generators; occasional missing/low-quality samples.
  - Start / Pause / Reset / Scenario-select operations persisted to `sim_state`.
  - _Requirements: 2.1–2.9_

- [x] 7. Implement SensorAdapter interface + SimulatedSensorAdapter — _Owner: Raffy_
  - Define `SensorAdapter` protocol; implement `SimulatedSensorAdapter`.
  - Add interface-only `AppleHealthAdapter`, `HealthConnectAdapter`, `BluetoothSensorAdapter` stubs.
  - _Requirements: 6.1–6.4_

- [x] 8. Wire simulator + scenario endpoints — _Owner: Jasper-Cyber_
  - `GET/POST /scenario`, `POST /simulator/{start|pause|reset}`, `GET /measurements`.
  - Start now generates a batch via SimulatorService; reset clears readings + cursor. All tested.
  - _Requirements: 2.6, 7.1, 7.4_

## Phase 3 — Analysis engine

- [x] 9. Implement baseline + rolling statistics — _Owner: Raffy_
  - `compute_baseline`, `rolling_stats`; persist baselines.
  - _Requirements: 3.1, 3.2_

- [x] 10. Implement anomaly detectors — _Owner: Raffy_
  - persistent_shift, combination (HR↑ & HRV↓), rhythm_irregularity, data_quality.
  - Thresholds centralized in `analysis_config.py`; reproducible outputs.
  - _Requirements: 3.3–3.8_

- [x] 11. Expose analysis endpoints — _Owner: Jasper-Cyber_
  - `POST /analysis/run`, `GET /trends?range=daily|weekly|monthly`.
  - _Requirements: 7.1, 5.1, 5.2, 5.3_

## Phase 4 — Alerts

- [x] 12. Implement AlertService — _Owner: Raffy_
  - Map findings → `normal | trend_review | attention`; build explanation + next steps.
  - Always attach emergency guidance and experimental label; expose `GET /insights`.
  - _Requirements: 4.1–4.5_

## Phase 5 — Mobile UI

- [ ] 13. API client + React Query hooks — _Owner: Helenawai_
  - Typed `api/client.ts`, `api/types.ts`; hooks with polling while simulator runs.
  - _Requirements: 7.5, 1.1_

- [ ] 14. Dashboard screen — _Owner: Helenawai_
  - Metric cards (HR, HRV, SpO2, rhythm), activity/sleep, monitoring status, wearable badge, mini trends.
  - Always-visible simulated-data ribbon; explicit no-data state.
  - _Requirements: 1.1–1.7_

- [ ] 15. Insights/Alerts screen — _Owner: Helenawai_
  - State banner, explanation, next steps, emergency guidance card, experimental label.
  - _Requirements: 4.1–4.5_

- [ ] 16. History screen — _Owner: Helenawai_
  - Daily/weekly/monthly toggle, baseline overlay, anomaly markers, past alerts, empty states.
  - _Requirements: 5.1–5.5_

- [ ] 17. Simulator screen — _Owner: Helenawai_
  - Scenario picker (A/B/C) + Start/Pause/Reset wired to backend.
  - _Requirements: 2.6_

## Phase 6 — Care network & emergency response

- [x] 18. Care profile + contacts + settings data layer (backend) — _Owner: maiabrunne_
  - Add `user_settings`, `care_profiles`, `emergency_contacts`, `providers`, `dispatch_events` tables + repository functions.
  - Seed a synthetic provider directory (doctors + hospitals with lat/lon + capability flags).
  - Feature flags default: suggestions OFF, emergency OFF; expose `GET/PUT /settings`.
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.10, 11.1_

- [x] 19. ProviderService + endpoints — _Owner: maiabrunne_
  - Haversine distance; non-emergency ranking by distance; emergency ranking by capability then distance; preferred-doctor flag.
  - `GET/PUT /care/profile`, `GET /providers?lat&lon&emergency`.
  - _Requirements: 10.4, 10.5, 10.6, 10.7_

- [x] 20. EmergencyService + NotifierAdapter + endpoints — _Owner: maiabrunne_
  - Respect `emergency_enabled` flag (off => no dispatch path). Routing rule (preferred-reachable vs nearest-capable) in `emergency_config.py`; payload assembly; `SimulatedNotifier`.
  - Future interface-only `SmsNotifierAdapter`/`VoiceCallNotifierAdapter` stubs.
  - `POST /emergency/evaluate`, `POST /emergency/dispatch` (simulated default, requires confirm; real gated by opt-in flag), `GET /emergency/history`.
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.6, 11.7, 11.9, 11.10_

- [x] 21. Disclaimer + settings (backend + shared) — _Owner: maiabrunne_
  - `POST /settings/disclaimer-ack`; disclaimer copy as a shared constant; concise experimental notice string.
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.6, 12.7_

- [ ] 22. Care profile + settings screen (mobile) — _Owner: Helenawai_
  - Personal + optional emergency contacts forms, optional preferred-doctor picker, default location; `useCareProfile`.
  - Feature toggles for warnings / suggestions / emergency (suggestions + emergency default OFF); `useSettings`.
  - _Requirements: 10.1, 10.2, 11.1_

- [ ] 23. Disclaimer screen (mobile) — _Owner: Helenawai_
  - First-launch `DisclaimerModal` with one-time acknowledgement; accessible from Settings; `ExperimentalNotice` on alert/dispatch surfaces.
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 24. Nearby provider suggestions (mobile) — _Owner: maiabrunne_
  - When suggestions enabled, on `trend_review`/`attention` show `NearbyProvidersSheet` with ranked `ProviderSuggestionCard`s + distances; manual open allowed when disabled.
  - Location via `expo-location` with approximate-location fallback indicator.
  - _Requirements: 10.5, 10.6, 10.7, 10.8, 10.9_

- [x] 25. Emergency response flow (mobile) — _Owner: maiabrunne_
  - Only when enabled: emergency route with routing decision, recipient, payload preview, confirm-with-countdown + Cancel, simulated/real badge.
  - Always show static emergency-services guidance alongside dispatch; dispatch history list.
  - _Requirements: 11.2, 11.4, 11.5, 11.6, 11.7, 11.8_

## Phase 7 — Tests & docs

- [x] 26. Python tests (pytest) — _Owner: Raffy_
  - Simulator determinism, baseline math, each detector, missing-data, alert mapping, scenario transitions, API routes.
  - Provider distance ranking + emergency-capability ordering; emergency routing rule; payload assembly;
    feature flags respected (suggestions/emergency off => no flow); simulated dispatch records an event and sends nothing;
    dispatch requires confirmation; real dispatch blocked without opt-in flag; routing determinism.
  - _Requirements: 9.1, 9.2_

- [ ] 27. TypeScript tests (Jest + RN Testing Library) — _Owner: Helenawai_
  - Formatting utils, API parsing, rendering of labels/emergency guidance, chart transforms.
  - Care-profile form validation; provider-suggestion list sorting/rendering; emergency confirm dialog (countdown + Cancel);
    disclaimer acknowledgement gating; feature-toggle behavior.
  - _Requirements: 9.1, 9.2_

- [x] 28. README, demo script, screenshots — _Owner: Jasper-Cyber (all contribute)_
  - Install/config/run for backend and mobile; demo walkthrough; screenshot references.
  - Document the optional care-profile setup, provider suggestions on a warning, the (simulated-by-default,
    opt-in) emergency flow, and the experimental disclaimer; include how to safely enable a real notifier channel.
  - Verify demo runs with no real sensors or paid APIs.
  - _Requirements: 9.3, 9.4, 9.5_
```
