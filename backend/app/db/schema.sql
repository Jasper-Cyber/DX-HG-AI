-- HeartGuardian AI — SQLite schema (Task 4 + Task 18).
--
-- All data is synthetic and labeled experimental. No real PII is stored.
-- Timestamps are ISO-8601 UTC strings. JSON payloads are stored as TEXT.
--
-- Core tables (Task 4, Jasper-Cyber): users, measurements, baselines,
--   anomaly_findings, alerts, sim_state.
-- Care-network tables (Task 18, maiabrunne): user_settings, care_profiles,
--   emergency_contacts, providers, dispatch_events.
-- The full schema lives here so the database is internally consistent; each
-- owner implements the repository functions for their own tables.

PRAGMA foreign_keys = ON;

-- One synthetic user for the MVP (no real PII).
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    display_name  TEXT NOT NULL DEFAULT 'Demo User',
    created_at    TEXT NOT NULL            -- ISO-8601 UTC
);

-- Normalized time-series of readings. metric_type keys the physiological signal.
CREATE TABLE IF NOT EXISTS measurements (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    timestamp     TEXT NOT NULL,           -- ISO-8601 UTC
    metric_type   TEXT NOT NULL,           -- 'hr' | 'hrv' | 'spo2' | 'rhythm' | 'activity' | 'sleep'
    value         REAL,                    -- NULL => missing/low-quality sample
    quality       TEXT NOT NULL DEFAULT 'ok', -- 'ok' | 'low' | 'missing'
    is_synthetic  INTEGER NOT NULL DEFAULT 1, -- always 1 in MVP
    scenario      TEXT NOT NULL            -- 'A' | 'B' | 'C'
);
CREATE INDEX IF NOT EXISTS idx_meas_user_metric_ts ON measurements(user_id, metric_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_meas_ts             ON measurements(timestamp);

-- Learned per-metric baseline (recomputed by the analysis engine).
CREATE TABLE IF NOT EXISTS baselines (
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
CREATE TABLE IF NOT EXISTS anomaly_findings (
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
CREATE INDEX IF NOT EXISTS idx_find_user_ts ON anomaly_findings(user_id, created_at);

-- User-facing alerts derived from findings.
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    state           TEXT NOT NULL,         -- 'normal' | 'trend_review' | 'attention'
    title           TEXT NOT NULL,
    explanation     TEXT NOT NULL,         -- human-readable supporting-data summary
    next_steps      TEXT NOT NULL,
    finding_ids     TEXT NOT NULL,         -- JSON array of anomaly_findings.id
    is_experimental INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL
);

-- Simulator session state (single row updated in place).
CREATE TABLE IF NOT EXISTS sim_state (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    scenario      TEXT NOT NULL DEFAULT 'A',
    status        TEXT NOT NULL DEFAULT 'paused', -- 'running' | 'paused'
    seed          INTEGER NOT NULL DEFAULT 42,
    cursor_ts     TEXT,                    -- next timestamp to generate
    updated_at    TEXT NOT NULL
);

-- =====================================================================
-- Care-network tables (Task 18 — maiabrunne). Defined here for a coherent
-- schema; repository functions for these live in a care-network module.
-- =====================================================================

-- Provider directory: doctors and hospitals (seeded synthetic data in MVP).
CREATE TABLE IF NOT EXISTS providers (
    id             INTEGER PRIMARY KEY,
    kind           TEXT NOT NULL,          -- 'doctor' | 'hospital'
    name           TEXT NOT NULL,
    specialty      TEXT,                   -- e.g. 'cardiology', 'emergency'
    can_handle_cardiac_emergency INTEGER NOT NULL DEFAULT 0,
    phone          TEXT,
    address        TEXT,
    lat            REAL NOT NULL,
    lon            REAL NOT NULL,
    is_synthetic   INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_providers_kind ON providers(kind);

-- Per-user settings & feature flags; makes warning/emergency features user-controlled.
CREATE TABLE IF NOT EXISTS user_settings (
    user_id              INTEGER PRIMARY KEY REFERENCES users(id),
    warnings_enabled     INTEGER NOT NULL DEFAULT 1,
    suggestions_enabled  INTEGER NOT NULL DEFAULT 0,
    emergency_enabled    INTEGER NOT NULL DEFAULT 0,
    disclaimer_ack_at    TEXT,
    updated_at           TEXT NOT NULL
);

-- Care profile: the user's own contact info and default/approx location.
CREATE TABLE IF NOT EXISTS care_profiles (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    full_name      TEXT,
    phone          TEXT,
    default_lat    REAL,
    default_lon    REAL,
    preferred_provider_id INTEGER REFERENCES providers(id),
    updated_at     TEXT NOT NULL,
    UNIQUE(user_id)
);

-- Emergency contacts linked to a user.
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    name           TEXT NOT NULL,
    relationship   TEXT,
    phone          TEXT NOT NULL,
    priority       INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_contacts_user ON emergency_contacts(user_id, priority);

-- Dispatch history: every emergency routing decision + payload (simulated or real).
CREATE TABLE IF NOT EXISTS dispatch_events (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    alert_id       INTEGER REFERENCES alerts(id),
    recipient_provider_id INTEGER REFERENCES providers(id),
    routing_reason TEXT NOT NULL,
    channel        TEXT NOT NULL,          -- 'simulated' | 'real'
    status         TEXT NOT NULL,          -- 'pending_confirm' | 'cancelled' | 'sent' | 'failed'
    payload        TEXT NOT NULL,          -- JSON
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dispatch_user_ts ON dispatch_events(user_id, created_at);
