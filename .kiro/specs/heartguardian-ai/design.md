# Design Document — HeartGuardian AI

## Overview

HeartGuardian AI is a two-tier prototype: an Expo/React Native (TypeScript) mobile client and
a FastAPI (Python) backend backed by SQLite. The backend owns the simulator, the analysis
engine, and persistence. The client renders a dark-blue healthcare dashboard, trend charts,
and explainable alerts. Everything runs locally; all data is synthetic and labeled experimental.

It also includes a **care-network module**: the user saves a care profile (their contacts and a
preferred doctor), the app suggests nearby providers when a warning appears, and a safety-gated
emergency-response flow can notify a provider with the patient's location and key context.

Design principles:
- **Transparency over black-box scoring.** Thresholds live in one config; findings carry their supporting values.
- **Separation of concerns.** Simulation, analysis, and persistence are independent, testable modules.
- **Pluggable sensors.** A `SensorAdapter` interface isolates data source from the rest of the system.
- **Safety-first UI.** Emergency guidance and "experimental, not medical advice" labels are always present.
- **User in control.** Warnings, provider suggestions, and emergency dispatch are optional and opt-in;
  the app works fully with them off, and the user decides whether to enable each one.
- **Human-in-the-loop emergencies.** Dispatch is simulated by default and never happens without explicit
  user confirmation; a real channel additionally requires opt-in configuration. Routing rules are transparent and configurable.
- **Pluggable notifications.** A `NotifierAdapter` interface isolates the dispatch channel; the MVP ships a
  `SimulatedNotifier` so the flow is fully demonstrable without contacting real recipients.
- **Experimental, not liable.** A plain-language disclaimer (first-launch acknowledgement + always
  accessible) states the app is not reliable, not responsible for false alarms, and that acting on
  warnings is solely the user's decision. It is a product notice, not legal advice.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Mobile Client (Expo / RN / TS)          │
│                                                          │
│  Expo Router screens                                     │
│   ├─ Dashboard   ├─ Insights/Alerts  ├─ History          │
│   └─ Simulator controls   └─ Profile/Settings            │
│                                                          │
│  State: React Query (server cache) + Zustand (UI state)  │
│  Charts: react-native-gifted-charts / Skia               │
│  API client: typed fetch wrapper (generated from OpenAPI)│
└───────────────────────────┬──────────────────────────────┘
                            │ HTTP (JSON, localhost / LAN)
┌───────────────────────────▼──────────────────────────────┐
│                   FastAPI Backend (Python)                │
│                                                          │
│  Routers:  /measurements  /trends  /analysis             │
│            /insights      /scenario                       │
│            /care/profile  /providers  /emergency          │
│                                                          │
│  Services:                                               │
│   ├─ SimulatorService  (scenarios A/B/C, seedable)        │
│   ├─ SensorAdapter      (SimulatedSensorAdapter)          │
│   ├─ AnalysisEngine     (baseline, rolling stats, finds)  │
│   ├─ AlertService       (findings → states + guidance)    │
│   ├─ ProviderService    (directory + distance ranking)    │
│   ├─ EmergencyService   (routing rules + payload build)   │
│   └─ NotifierAdapter     (SimulatedNotifier; future SMS)  │
│                                                          │
│  Repository layer (SQLAlchemy Core / sqlite3)             │
└───────────────────────────┬──────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  SQLite (file) │
                    └────────────────┘
```

### Why these technology choices
- **Expo Router**: file-based navigation, required by the brief, fast to scaffold.
- **React Query + Zustand**: React Query caches server data and handles polling for live simulator
  updates; Zustand holds light UI state (selected range, scenario toggle) without boilerplate.
- **react-native-gifted-charts**: pure RN charts (line/area/bar) that render the trend cards in the
  mockups without native build friction; works in Expo Go.
- **FastAPI**: async, typed, auto OpenAPI — the client's API types are generated from it.
- **SQLite**: embedded, zero-config, file-based; ideal for a reproducible single-user demo. See
  "Database Design" for the rationale and scale-up path.

---

## Database Design

### Choice: SQLite (with a documented scale-up path to TimescaleDB/Postgres)

SQLite is selected because the MVP is single-user, local-first, and demo-oriented. It needs no
server process, ships with Python, and stores everything in one portable file — which directly
serves "store data locally when practical" and "reproducible demo." Physiological data is
naturally relational time-series, and SQLite with proper indexes handles the demo's volume
(thousands of rows) comfortably. If the system ever needed many concurrent users or
high-frequency streaming, the migration target is **TimescaleDB** (a Postgres time-series
extension); the repository layer abstracts SQL access so that swap stays localized.

### Schema

```sql
-- One synthetic user for the MVP (no real PII).
CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    display_name  TEXT NOT NULL DEFAULT 'Demo User',
    created_at    TEXT NOT NULL            -- ISO-8601 UTC
);

-- Normalized time-series of readings. metric_type keys the physiological signal.
CREATE TABLE measurements (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    timestamp     TEXT NOT NULL,           -- ISO-8601 UTC
    metric_type   TEXT NOT NULL,           -- 'hr' | 'hrv' | 'spo2' | 'rhythm' | 'activity' | 'sleep'
    value         REAL,                    -- NULL => missing/low-quality sample
    quality       TEXT NOT NULL DEFAULT 'ok', -- 'ok' | 'low' | 'missing'
    is_synthetic  INTEGER NOT NULL DEFAULT 1, -- always 1 in MVP
    scenario      TEXT NOT NULL            -- 'A' | 'B' | 'C'
);
CREATE INDEX idx_meas_user_metric_ts ON measurements(user_id, metric_type, timestamp);
CREATE INDEX idx_meas_ts            ON measurements(timestamp);

-- Learned per-metric baseline (recomputed by the analysis engine).
CREATE TABLE baselines (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    metric_type   TEXT NOT NULL,
    mean          REAL NOT NULL,
    std           REAL NOT NULL,
    sample_count  INTEGER NOT NULL,
    computed_at   TEXT NOT NULL,
    UNIQUE(user_id, metric_type)
);

-- Structured anomaly findings produced by the engine.
CREATE TABLE anomaly_findings (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    metric_type   TEXT NOT NULL,
    finding_type  TEXT NOT NULL,           -- 'persistent_shift' | 'combination' | 'rhythm_irregularity' | 'data_quality'
    severity_band TEXT NOT NULL,           -- 'info' | 'review' | 'attention'
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    deviation     REAL,                    -- standardized deviation from baseline
    supporting    TEXT NOT NULL,           -- JSON: raw supporting values
    created_at    TEXT NOT NULL
);
CREATE INDEX idx_find_user_ts ON anomaly_findings(user_id, created_at);

-- User-facing alerts derived from findings.
CREATE TABLE alerts (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    state         TEXT NOT NULL,           -- 'normal' | 'trend_review' | 'attention'
    title         TEXT NOT NULL,
    explanation   TEXT NOT NULL,           -- human-readable supporting-data summary
    next_steps    TEXT NOT NULL,
    finding_ids   TEXT NOT NULL,           -- JSON array of anomaly_findings.id
    is_experimental INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

-- Simulator session state (single row updated in place).
CREATE TABLE sim_state (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    scenario      TEXT NOT NULL DEFAULT 'A',
    status        TEXT NOT NULL DEFAULT 'paused', -- 'running' | 'paused'
    seed          INTEGER NOT NULL DEFAULT 42,
    cursor_ts     TEXT,                    -- next timestamp to generate
    updated_at    TEXT NOT NULL
);

-- Per-user settings & feature flags; makes warning/emergency features user-controlled (Req 10.1, 11.1, 12.5).
CREATE TABLE user_settings (
    user_id              INTEGER PRIMARY KEY REFERENCES users(id),
    warnings_enabled     INTEGER NOT NULL DEFAULT 1, -- user may turn monitoring warnings off
    suggestions_enabled  INTEGER NOT NULL DEFAULT 0, -- nearby-provider suggestions (opt-in)
    emergency_enabled    INTEGER NOT NULL DEFAULT 0, -- emergency-response flow (opt-in, off by default)
    disclaimer_ack_at    TEXT,                       -- when the experimental disclaimer was acknowledged (Req 12)
    updated_at           TEXT NOT NULL
);

-- Care profile: the user's own contact info and default/approx location (Req 10).
CREATE TABLE care_profiles (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    full_name      TEXT,
    phone          TEXT,
    default_lat    REAL,                   -- fallback location when live GPS is unavailable (Req 10.6)
    default_lon    REAL,
    preferred_provider_id INTEGER REFERENCES providers(id), -- the preferred doctor (Req 10.1/10.7)
    updated_at     TEXT NOT NULL,
    UNIQUE(user_id)
);

-- Emergency contacts linked to a user (Req 10.1).
CREATE TABLE emergency_contacts (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    name           TEXT NOT NULL,
    relationship   TEXT,
    phone          TEXT NOT NULL,
    priority       INTEGER NOT NULL DEFAULT 1, -- 1 = contact first
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_contacts_user ON emergency_contacts(user_id, priority);

-- Provider directory: doctors and hospitals (seeded synthetic data in MVP) (Req 10.3).
CREATE TABLE providers (
    id             INTEGER PRIMARY KEY,
    kind           TEXT NOT NULL,          -- 'doctor' | 'hospital'
    name           TEXT NOT NULL,
    specialty      TEXT,                   -- e.g. 'cardiology', 'emergency'
    can_handle_cardiac_emergency INTEGER NOT NULL DEFAULT 0, -- life-saving capability flag (Req 11.2)
    phone          TEXT,
    address        TEXT,
    lat            REAL NOT NULL,
    lon            REAL NOT NULL,
    is_synthetic   INTEGER NOT NULL DEFAULT 1, -- always 1 in MVP (Req 10.8)
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_providers_kind ON providers(kind);

-- Dispatch history: every emergency routing decision + payload (simulated or real) (Req 11.6).
CREATE TABLE dispatch_events (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    alert_id       INTEGER REFERENCES alerts(id),
    recipient_provider_id INTEGER REFERENCES providers(id),
    routing_reason TEXT NOT NULL,          -- why this recipient was chosen (preferred vs nearest-capable)
    channel        TEXT NOT NULL,          -- 'simulated' | 'real'
    status         TEXT NOT NULL,          -- 'pending_confirm' | 'cancelled' | 'sent' | 'failed'
    payload        TEXT NOT NULL,          -- JSON: assembled dispatch payload (Req 11.3)
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_dispatch_user_ts ON dispatch_events(user_id, created_at);
```

Design notes:
- `value` is nullable and paired with `quality` so missing/low-quality data is first-class and
  distinguishable from a physiological trend (Req 3.4).
- `supporting` and `finding_ids` are JSON text columns — pragmatic for SQLite and enough for the demo.
- `sim_state` is a single-row table (`CHECK id=1`) representing the current simulator session.
- `providers` carries `lat/lon` for distance ranking and a `can_handle_cardiac_emergency` capability
  flag so the router can pick a hospital that can actually help in a cardiac emergency (Req 11.2).
- `dispatch_events` records the recipient, routing reason, channel, and full payload for every dispatch
  so the flow is auditable and the simulated path is fully demonstrable (Req 11.5/11.6).
- `care_profiles` and `emergency_contacts` hold user-entered contact data; it stays in the local SQLite
  file and is only included in a payload during an explicit, confirmed dispatch (Req 10.3).
- `user_settings` makes the warning, suggestion, and emergency features user-controlled: suggestions and
  emergency dispatch default OFF, and `disclaimer_ack_at` records the one-time disclaimer acknowledgement.

---

## Components and Interfaces

### Backend

#### SensorAdapter (Req 6)
```python
class SensorAdapter(Protocol):
    def read_batch(self, start: datetime, end: datetime, step: timedelta) -> list[Reading]: ...
    def capabilities(self) -> set[str]: ...

class SimulatedSensorAdapter:        # implemented
    def __init__(self, simulator: SimulatorService): ...

# Interface-only stubs for the future (raise NotImplementedError):
class AppleHealthAdapter(SensorAdapter): ...
class HealthConnectAdapter(SensorAdapter): ...
class BluetoothSensorAdapter(SensorAdapter): ...
```

#### SimulatorService (Req 2)
- `select_scenario(s)`, `start()`, `pause()`, `reset()`.
- Seedable `numpy.random.default_rng(seed)` for reproducibility.
- Scenario generators:
  - **A Normal**: sample each metric from `N(baseline_mean, baseline_std)`, clipped to physiological ranges.
  - **B Gradual Deviation**: apply a slow linear drift over simulated weeks (HR ↑, HRV ↓, sleep ↓).
  - **C Rhythm Irregularity**: inject intermittent `rhythm=irregular` flags and correlated HR spikes.
- Occasionally emits `quality='missing'` samples to exercise data-quality handling.

#### AnalysisEngine (Req 3)
- `compute_baseline(readings) -> Baseline` (mean/std over a trailing window).
- `rolling_stats(series, window)` via Pandas.
- `detect(findings)` pipeline:
  - **persistent_shift**: rolling mean deviates > `k·std` from baseline for ≥ `W` windows.
  - **combination**: HR up AND HRV down simultaneously beyond thresholds.
  - **rhythm_irregularity**: density of irregular flags exceeds threshold in window.
  - **data_quality**: fraction of missing/low samples exceeds threshold → tag, do not treat as trend.
- All thresholds in `analysis_config.py` (single source), making results transparent and reproducible.
- Returns `AnomalyFinding` objects; never emits a "risk %" as validated.

#### AlertService (Req 4)
- Maps findings → one of three states (`normal`, `trend_review`, `attention`).
- Builds `explanation` from supporting values and `next_steps` text.
- Always attaches static **emergency guidance** and **experimental** label.
- When a state reaches `trend_review`/`attention`, signals the `ProviderService`/`EmergencyService`
  so the client can surface suggestions or the response flow.

#### ProviderService (Req 10)
- `suggest(location, *, emergency: bool, preferred_id) -> list[ProviderSuggestion]`.
- Computes great-circle distance (haversine) from the user's location to each provider.
- Ranking: for non-emergency warnings, order by distance; for emergencies, prioritize providers with
  `can_handle_cardiac_emergency = 1`, then distance. The preferred doctor is flagged in results (Req 10.7).
- Reads from the seeded `providers` directory; all results labeled synthetic (Req 10.8).

#### EmergencyService (Req 11)
- Respects `user_settings`: if `emergency_enabled = 0`, `evaluate` returns `None` and no dispatch path runs (Req 11.1).
- `evaluate(alert) -> EmergencyDecision | None`: returns a decision only when the feature is enabled AND
  for `attention`-level events meeting the configured emergency criteria (thresholds in `emergency_config.py`).
- **Routing rule (transparent, configurable):**
  1. If the user has a preferred doctor AND that doctor is within `MAX_REACHABLE_KM` (config),
     select the preferred doctor; `routing_reason = 'preferred_doctor_reachable'`.
  2. Otherwise select the nearest provider with `can_handle_cardiac_emergency = 1`;
     `routing_reason = 'nearest_capable_hospital'`.
- `build_payload(user, decision)`: assembles patient key contact info, current/approx location,
  emergency-contact details, and a concise **non-diagnostic, experimental** finding summary (Req 11.3).
- `dispatch(decision, channel)`: with `channel='simulated'` (default), records a `dispatch_events` row
  and returns it WITHOUT contacting anyone (Req 11.5). A `channel='real'` dispatch requires an opt-in
  config flag AND a confirmed request from the client; it delegates to the `NotifierAdapter`.
- Deterministic for a fixed profile, directory, location, and config (Req 11.9).

#### NotifierAdapter (Req 11)
```python
class NotifierAdapter(Protocol):
    def send(self, recipient: Provider, payload: dict) -> DispatchResult: ...

class SimulatedNotifier(NotifierAdapter):   # implemented; records/returns, never sends externally
    ...

# Interface-only, future (require opt-in config + consent):
class SmsNotifierAdapter(NotifierAdapter): ...     # e.g. an SMS provider
class VoiceCallNotifierAdapter(NotifierAdapter): ...
```

#### API Endpoints (Req 7, 10, 11)
| Method | Path                         | Purpose                                  |
|--------|------------------------------|------------------------------------------|
| GET    | `/measurements`              | Latest / ranged readings (query: metric, from, to) |
| GET    | `/trends?range=daily|weekly|monthly` | Aggregated trend series + baseline |
| POST   | `/analysis/run`              | Recompute baselines + findings           |
| GET    | `/insights`                  | Current alert state + history            |
| GET/POST | `/scenario`                | Get or set scenario (A/B/C)              |
| POST   | `/simulator/{start|pause|reset}` | Control the simulator                |
| GET/PUT | `/care/profile`             | Get or update the care profile + emergency contacts (Req 10) |
| GET    | `/providers?lat&lon&emergency` | Suggested providers ranked by distance/capability (Req 10) |
| POST   | `/emergency/evaluate`        | Given current alert + location, return the routing decision + payload preview (Req 11) |
| POST   | `/emergency/dispatch`        | Perform dispatch (simulated by default; real requires confirm + opt-in) (Req 11) |
| GET    | `/emergency/history`         | List past dispatch events (Req 11.7)     |
| GET/PUT | `/settings`                 | Feature flags: warnings/suggestions/emergency enabled (Req 10.1, 11.1) |
| POST   | `/settings/disclaimer-ack`   | Record disclaimer acknowledgement (Req 12.5) |
| GET    | `/health`                    | Liveness                                 |

### Frontend

#### Screens (Expo Router)
- `app/(tabs)/index.tsx` — **Dashboard**: metric cards (HR, HRV, SpO2, rhythm), activity/sleep,
  monitoring status, wearable connection badge, mini trend charts. "SIMULATED DATA" ribbon.
- `app/(tabs)/insights.tsx` — **Insights/Alerts**: current state banner, explanation, next steps,
  always-visible emergency guidance card.
- `app/(tabs)/history.tsx` — **History**: daily/weekly/monthly toggle, baseline overlay, anomaly markers, past alerts.
- `app/(tabs)/simulator.tsx` — **Simulator**: scenario picker (A/B/C), Start/Pause/Reset.
- `app/(tabs)/profile.tsx` — **Settings / Care profile**: synthetic profile, personal + emergency
  contacts, preferred doctor picker, default location, data-privacy notes (Req 10.1).
- `app/emergency.tsx` — **Emergency response** (modal/route): routing decision, recipient, payload
  preview, map/location, a **confirm-with-countdown** control and a Cancel button; shows whether the
  dispatch is simulated or real (Req 11.5/11.6). Only reachable when the feature is enabled.
- `app/disclaimer.tsx` — **Experimental disclaimer** (first-launch modal + accessible from Settings):
  plain-language notice that the app is not reliable, not responsible for false alarms, and that acting
  on warnings is the user's decision; requires one-time acknowledgement (Req 12).
- Settings exposes toggles for warnings, provider suggestions, and emergency response (all user-controlled;
  suggestions/emergency default OFF) (Req 10.1, 11.1).

#### Shared UI
- `MetricCard`, `TrendChart`, `AlertBanner`, `EmergencyGuidanceCard`, `SimulatedDataRibbon`, `ScenarioPicker`.
- `ProviderSuggestionCard` (name, type, specialty, distance, "preferred" badge),
  `NearbyProvidersSheet` (shown on a warning), `ContactForm`, `PreferredDoctorPicker`,
  `EmergencyConfirmDialog` (countdown + cancel), `DispatchHistoryList`, `SimulatedDispatchBadge`,
  `DisclaimerModal`, `FeatureToggleRow`, `ExperimentalNotice` (concise not-reliable/not-liable banner).
- Theme tokens in `theme.ts` (dark-blue palette, spacing, typography) with AA-contrast colors.

#### Data layer
- `api/client.ts` typed wrapper; `api/types.ts` generated from OpenAPI.
- React Query hooks: `useMeasurements`, `useTrends`, `useInsights`, `useScenario`, with polling while simulator runs.
- Care-network hooks: `useCareProfile`, `useProviders`, `useEmergencyEvaluation`, `useDispatch`, `useDispatchHistory`.
- Settings/disclaimer hooks: `useSettings` (feature flags), `useDisclaimer` (ack state).
- Location via `expo-location` (with permission handling); falls back to the profile's default
  location and flags it as approximate when live GPS is unavailable (Req 10.6).

---

## Data Models (shared shapes)

```ts
type MetricType = 'hr' | 'hrv' | 'spo2' | 'rhythm' | 'activity' | 'sleep';
type AlertState = 'normal' | 'trend_review' | 'attention';

interface Reading { timestamp: string; metricType: MetricType; value: number | null;
                    quality: 'ok' | 'low' | 'missing'; isSynthetic: true; scenario: 'A'|'B'|'C'; }

interface Alert { state: AlertState; title: string; explanation: string;
                  nextSteps: string; isExperimental: true; emergencyGuidance: string; }

type ProviderKind = 'doctor' | 'hospital';
type DispatchChannel = 'simulated' | 'real';
type RoutingReason = 'preferred_doctor_reachable' | 'nearest_capable_hospital';

interface Provider { id: number; kind: ProviderKind; name: string; specialty?: string;
                     canHandleCardiacEmergency: boolean; phone?: string; address?: string;
                     lat: number; lon: number; isSynthetic: true; }

interface ProviderSuggestion { provider: Provider; distanceKm: number; isPreferred: boolean; }

interface EmergencyContact { name: string; relationship?: string; phone: string; priority: number; }

interface CareProfile { fullName?: string; phone?: string;
                        defaultLat?: number; defaultLon?: number;
                        preferredProviderId?: number; emergencyContacts: EmergencyContact[]; }

interface DispatchPayload { patient: { name?: string; phone?: string };
                            location: { lat: number; lon: number; approximate: boolean; description?: string };
                            emergencyContacts: EmergencyContact[];
                            findingSummary: string;  // non-diagnostic, experimental
                            isExperimental: true; }

interface EmergencyDecision { recipient: Provider; routingReason: RoutingReason;
                              payload: DispatchPayload; channel: DispatchChannel; }
```

---

## Error Handling

- **Backend**: FastAPI exception handlers return structured JSON `{ error, detail }`;
  invalid scenario/range → `422`; missing resource → `404`; simulator misuse → `409`.
- **Analysis**: insufficient data → returns a `data_quality` finding, not an exception.
- **Emergency flow**: no reachable provider → fall back to nearest capable hospital; empty directory →
  `409` with guidance to contact emergency services directly. A real dispatch requested without the
  opt-in config flag → `403`. Location missing → use default/approx location and flag it (Req 10.6).
- **Frontend**: React Query error/loading/empty states; network failure shows a retry card;
  empty ranges show explicit empty states (Req 5.5, 1.6). The emergency dialog always offers Cancel,
  and a failed/declined real dispatch falls back to showing the static emergency guidance.

---

## Testing Strategy (Req 9)

- **Python (pytest)**: simulator determinism per scenario; baseline math; each anomaly detector;
  missing-data classification; alert-state mapping; scenario transitions; API route responses (httpx/TestClient);
  provider distance ranking and emergency-capability ordering; emergency routing rule (preferred-reachable
  vs nearest-capable); payload assembly correctness; simulated dispatch records an event and sends nothing;
  real dispatch is blocked without the opt-in flag; routing determinism for fixed inputs.
- **TypeScript (Jest + RN Testing Library)**: metric/alert formatting utilities, API client parsing,
  component rendering of simulated-data labels and emergency guidance, chart data transforms,
  care-profile form validation, provider-suggestion list rendering/sorting, and the emergency confirm
  dialog (countdown + Cancel stops dispatch).
- **Reproducibility**: fixed seed + fixed config asserts identical findings across runs (Req 3.7).
- **Fixtures**: a seeded synthetic dataset doubles as the demo's sample history.

---

## Safety & Privacy Design (Req 8, 10, 11)
- No credentials or API keys anywhere in the client; backend reads any config from env/local file.
- All outputs labeled experimental; emergency guidance always visible on the Insights screen.
- No third-party LLM calls in the MVP; if added later, gated behind explicit consent.
- Data stays in the local SQLite file; synthetic-only measurements and a synthetic provider directory.
- **Care-network data handling:** the care profile and emergency contacts are user-entered and stored
  locally. They are included in a dispatch payload only during an explicit, user-confirmed dispatch,
  and only the fields needed for that dispatch are sent.
- **User-controlled & opt-in:** warnings, provider suggestions, and emergency dispatch are optional.
  Suggestions and emergency response default OFF and run only when the user enables them; the app is
  fully functional with them disabled. The user decides whether to enable each feature and whether to act.
- **Human-in-the-loop by default:** the MVP performs **simulated** dispatch (recorded/displayed in-app,
  nothing sent externally) and never dispatches without explicit user confirmation. A real channel
  additionally requires an opt-in config flag and a working `NotifierAdapter`. There is no unattended
  outreach of any kind.
- **Experimental disclaimer & user responsibility:** a plain-language disclaimer is acknowledged once on
  first launch and stays accessible from Settings. It states the app is experimental and non-clinical,
  makes no reliability/accuracy/timeliness guarantees, is not responsible for false alarms or missed
  events, and that acting on any warning is solely the user's decision. A concise not-reliable/not-liable
  notice also appears on alert and dispatch surfaces. This is a product notice, not legal advice.
- **Non-diagnostic framing preserved:** dispatch summaries describe observed synthetic signals and are
  labeled experimental; they never assert a heart attack, stroke, or arrhythmia diagnosis.
- **Location handling:** live location is requested with permission via `expo-location`; when
  unavailable the app uses the profile's default location and clearly marks it approximate.
