# HeartGuardian AI

An AI-assisted cardiovascular monitoring and early-warning **prototype**. HeartGuardian AI
demonstrates how wearable physiological data can be continuously analyzed to surface
personalized health trends and explainable, non-diagnostic alerts.

> ⚠️ **Experimental prototype — not a medical device.**
> All physiological data is **synthetic** and labeled experimental. The app does not diagnose
> conditions, makes no guarantee of accuracy, reliability, or timeliness, and is **not responsible
> for false alarms or missed events**. Any decision to act on a warning — including whether to
> enable warnings, contact anyone, or trigger a dispatch — is solely the user's decision. For real
> medical needs, contact a qualified professional or your local emergency services. This notice is
> a product disclaimer, not legal advice.

---

## What it does

- **Dashboard** of current cardiovascular metrics (heart rate, HRV, SpO₂, rhythm) with activity,
  sleep, monitoring status, wearable connection, and trend charts.
- **Wearable data simulator** with three scenarios: **A** Normal, **B** Gradual Deviation,
  **C** Rhythm Irregularity — Start / Pause / Reset controls, seedable for reproducibility.
- **Personalized analysis**: learns a per-metric baseline, computes rolling statistics, and runs
  transparent anomaly detectors (persistent shift, HR↑&HRV↓ combination, rhythm irregularity,
  data-quality). All thresholds are in one config file; no "risk score" is presented as validated.
- **Explainable alerts** in three states (Normal / Trend review / Attention), each with supporting
  data, next steps, always-visible emergency guidance, and an experimental label.
- **Optional, user-controlled care network**: save contacts + a preferred doctor, see nearby
  providers on a warning, and an **opt-in, simulated-by-default** emergency dispatch flow.
- **Experimental disclaimer** acknowledged on first launch and always accessible from Settings.

Everything runs locally with no real sensors and no paid APIs.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Mobile | React Native + Expo + TypeScript + Expo Router |
| State/data | React Query + Zustand |
| Charts | react-native-gifted-charts |
| Backend | Python + FastAPI (Uvicorn) |
| Database | SQLite (local, synthetic data only) |
| Analytics | NumPy, Pandas, scikit-learn |
| Tests | pytest (backend), Jest + RN Testing Library (mobile) |

## Repository layout

```
backend/                         FastAPI service
  app/
    main.py                      app entry + router registration
    db/                          schema.sql, connection, repositories, seeds
    services/                    simulator, analysis, alerts, provider, emergency
    adapters/                    sensor + notifier adapters (simulated + future stubs)
    analysis_config.py           all anomaly-detection thresholds (transparent)
    emergency_config.py          routing / dispatch config
  tests/                         pytest suite
  seed_data.py                   generate a labeled synthetic demo dataset
mobile/                          Expo React Native app
  app/                           Expo Router screens (tabs + disclaimer + emergency)
  components/                    MetricCard, TrendChart, alert/emergency UI, etc.
  api/                           typed client, types, React Query hooks
  utils/ · __tests__/            formatting/validation helpers + Jest tests
.kiro/specs/heartguardian-ai/    requirements.md · design.md · tasks.md
TEAM.md                          team roles, work allocation, git workflow
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11–3.13 |
| Node.js | 20 LTS or newer |
| Expo Go app (phone) or a simulator | latest |

## Run the backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash); use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

# (optional but recommended for the demo) seed a labeled synthetic history:
python seed_data.py --scenario B --reset

uvicorn app.main:app --reload --port 8000
```

- Health check: <http://localhost:8000/health>
- Interactive API docs: <http://localhost:8000/docs>
- Run backend tests: `pytest` (from `backend/`)

## Run the mobile app

In a second terminal:

```bash
cd mobile
npm install
npm start          # scan the QR with Expo Go, or press w for web, a/i for emulators
```

The app opens to a dark-blue dashboard with a persistent "SIMULATED DATA" ribbon.
Run mobile tests with `npm test`.

Starting a fresh simulator run creates three weeks of hourly synthetic history and
analyzes it immediately. While running, the backend appends one simulated hour every
five seconds and refreshes analysis; mobile readings, trends, insights, and alert
history poll for updates. Pause freezes generation; Start resumes at the saved cursor.
Reset clears readings and current analysis but preserves saved alert history. Selecting
a different scenario starts a fresh dataset (and continues running if already active).
The accelerated demo uses a deterministic January 1, 2026 starting point.
Run one Uvicorn worker for this local demo: its scheduler and control lock are in-process.

> **Networking:** the app calls the backend at `http://localhost:8000`. On a physical phone, set
> the API base URL to your computer's LAN IP (see `mobile/api/`), since `localhost` on the phone
> refers to the phone itself.

---

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/measurements` | Ranged/latest synthetic readings |
| GET/POST | `/scenario` | Get or set the simulator scenario (A/B/C) |
| POST | `/simulator/{start\|pause\|reset}` | Control the simulator (start generates data) |
| POST | `/analysis/run` | Recompute baselines + findings, refresh the alert |
| GET | `/trends?range=daily\|weekly\|monthly` | Aggregated trend series + baseline |
| GET | `/insights` | Current alert state and supporting findings |
| GET | `/insights/history?limit=100` | Saved alert snapshots, newest first |
| GET/PUT | `/settings` | Feature flags (warnings / suggestions / emergency) |
| POST | `/settings/disclaimer-ack` | Record disclaimer acknowledgement |
| GET/PUT | `/care/profile` | Care profile + emergency contacts |
| GET | `/providers?lat&lon&emergency` | Nearby provider suggestions (ranked) |
| POST | `/emergency/evaluate` | Routing decision + payload preview (opt-in) |
| POST | `/emergency/dispatch` | Dispatch (simulated default; real gated + confirmed) |
| GET | `/emergency/history` | Past dispatch events |

---

## Demo script (~3 minutes)

A suggested walkthrough for a live demo. Seed data first with
`python seed_data.py --scenario B --reset`, then start the backend and app.

1. **Dashboard (Normal).** Open the app. Point out the "SIMULATED DATA" ribbon and the current
   HR / HRV / SpO₂ / rhythm cards, activity & sleep, and the monitoring status. Emphasize that all
   values are synthetic.
2. **First-launch disclaimer.** Show the experimental disclaimer and acknowledge it; note it stays
   available from Settings.
3. **Simulator → Scenario A (Normal).** Start the simulator. Metrics fluctuate within baseline;
   the Insights screen shows **Normal monitoring**.
4. **Switch to Scenario B (Gradual Deviation).** Reset, pick B, Start. Over the simulated weeks,
   resting HR drifts up and HRV down. Open **Insights** — the state rises to **Trend review** (or
   **Attention**), with a plain-language explanation of the supporting data and next steps.
5. **Scenario C (Rhythm Irregularity).** Reset, pick C, Start. Show the rhythm-irregularity finding
   surfaced for review — framed as "flag for review," never a diagnosis.
6. **History.** Toggle daily / weekly / monthly trends; show the baseline overlay and anomaly markers.
7. **Care network (optional, opt-in).** In Settings, enable provider suggestions, set a default
   location + preferred doctor. On a warning, open the nearby-providers sheet (ranked by distance).
8. **Emergency flow (opt-in, simulated).** Enable emergency response. Trigger the flow: show the
   routing decision (preferred doctor if reachable, else nearest capable hospital), the payload
   preview (contacts + location + non-diagnostic summary), the confirm-with-countdown, and that the
   dispatch is **simulated** (recorded in history, nothing sent externally). Point out the always-on
   guidance to contact real emergency services.

Reset to Scenario A to leave a clean state.

## Screenshots

Place demo screenshots in `docs/screenshots/` and reference them here, e.g.:

- `docs/screenshots/dashboard.png` — dashboard with metric cards and trends
- `docs/screenshots/insights-attention.png` — Attention-state alert with explanation
- `docs/screenshots/simulator.png` — scenario picker + controls
- `docs/screenshots/emergency.png` — simulated emergency dispatch preview

---

## Safety & privacy

- No credentials or API keys in the client; the backend reads config from env / local files.
- All data is synthetic; the local SQLite file holds no real patient information.
- Warnings, provider suggestions, and emergency dispatch are **optional and user-controlled**;
  suggestions and emergency default **off**.
- Emergency dispatch is **simulated by default** and never sends anything without explicit
  confirmation. A real channel requires an opt-in config flag and a working notifier adapter.
- All medical-adjacent output is labeled experimental and does not replace professional evaluation.

## Development

Built with Amazon Kiro using spec-driven development. The requirements, design, and task plan live
in `.kiro/specs/heartguardian-ai/`. See `TEAM.md` for ownership and the branch-per-task workflow.
