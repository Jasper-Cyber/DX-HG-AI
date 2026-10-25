"""Repository layer for the core tables (Task 4).

Pure data-access functions over SQLite. Services call these; they do not embed
SQL themselves. Each function opens and closes its own connection so callers do
not manage transactions for simple operations.

Scope (Task 4, Jasper-Cyber): measurements, baselines, anomaly_findings, alerts,
sim_state. Care-network repository functions live in a separate module (Task 18).
"""
from __future__ import annotations

import sqlite3
from typing import Iterable, Optional, Sequence

from .connection import DEMO_USER_ID, get_connection, utc_now_iso
from .models import Alert, AnomalyFinding, Baseline, Measurement, SimState

# Sentinel for update_sim_state so callers can explicitly set cursor_ts=None (NULL)
# versus omitting it (leave unchanged).
_UNSET = object()

# --------------------------------------------------------------------------- #
# Measurements
# --------------------------------------------------------------------------- #

def insert_measurement(m: Measurement) -> int:
    """Insert one reading; returns its new id."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO measurements
                (user_id, timestamp, metric_type, value, quality, is_synthetic, scenario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                m.user_id,
                m.timestamp,
                m.metric_type,
                m.value,
                m.quality,
                1 if m.is_synthetic else 0,
                m.scenario,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def insert_measurements(rows: Iterable[Measurement]) -> int:
    """Bulk-insert readings; returns the number inserted."""
    payload = [
        (
            m.user_id,
            m.timestamp,
            m.metric_type,
            m.value,
            m.quality,
            1 if m.is_synthetic else 0,
            m.scenario,
        )
        for m in rows
    ]
    if not payload:
        return 0
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO measurements
                (user_id, timestamp, metric_type, value, quality, is_synthetic, scenario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        conn.commit()
        return len(payload)


def query_measurements(
    *,
    metric_type: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    user_id: int = DEMO_USER_ID,
    limit: Optional[int] = None,
) -> list[Measurement]:
    """Query readings, optionally filtered by metric and time range (inclusive).

    Results are ordered by timestamp ascending.
    """
    clauses = ["user_id = ?"]
    params: list[object] = [user_id]
    if metric_type is not None:
        clauses.append("metric_type = ?")
        params.append(metric_type)
    if start is not None:
        clauses.append("timestamp >= ?")
        params.append(start)
    if end is not None:
        clauses.append("timestamp <= ?")
        params.append(end)

    sql = f"SELECT * FROM measurements WHERE {' AND '.join(clauses)} ORDER BY timestamp ASC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_measurement(r) for r in rows]


def latest_measurement(metric_type: str, *, user_id: int = DEMO_USER_ID) -> Optional[Measurement]:
    """Most recent reading for a metric, or None if there are none."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM measurements
            WHERE user_id = ? AND metric_type = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (user_id, metric_type),
        ).fetchone()
    return _row_to_measurement(row) if row else None


def count_measurements(*, user_id: int = DEMO_USER_ID) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM measurements WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row["n"])


def clear_measurements(*, user_id: int = DEMO_USER_ID) -> None:
    """Remove all readings for a user (used by simulator Reset)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM measurements WHERE user_id = ?", (user_id,))
        conn.commit()


# --------------------------------------------------------------------------- #
# Baselines
# --------------------------------------------------------------------------- #

def upsert_baseline(b: Baseline) -> None:
    """Insert or replace the baseline for (user, metric)."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO baselines (user_id, metric_type, mean, std, sample_count, computed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, metric_type) DO UPDATE SET
                mean = excluded.mean,
                std = excluded.std,
                sample_count = excluded.sample_count,
                computed_at = excluded.computed_at
            """,
            (b.user_id, b.metric_type, b.mean, b.std, b.sample_count, b.computed_at),
        )
        conn.commit()


def get_baseline(metric_type: str, *, user_id: int = DEMO_USER_ID) -> Optional[Baseline]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM baselines WHERE user_id = ? AND metric_type = ?",
            (user_id, metric_type),
        ).fetchone()
    return _row_to_baseline(row) if row else None


def list_baselines(*, user_id: int = DEMO_USER_ID) -> list[Baseline]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM baselines WHERE user_id = ? ORDER BY metric_type", (user_id,)
        ).fetchall()
    return [_row_to_baseline(r) for r in rows]


# --------------------------------------------------------------------------- #
# Anomaly findings
# --------------------------------------------------------------------------- #

def insert_finding(f: AnomalyFinding) -> int:
    created = f.created_at or utc_now_iso()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO anomaly_findings
                (user_id, metric_type, finding_type, severity_band,
                 window_start, window_end, deviation, supporting, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f.user_id,
                f.metric_type,
                f.finding_type,
                f.severity_band,
                f.window_start,
                f.window_end,
                f.deviation,
                f.supporting,
                created,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def clear_current_analysis(*, user_id: int = DEMO_USER_ID) -> None:
    """Clear derived state for a reset, preserving historical alert snapshots."""
    with get_connection() as conn:
        conn.execute("DELETE FROM anomaly_findings WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM baselines WHERE user_id = ?", (user_id,))


def replace_findings(findings: list[AnomalyFinding], *, user_id: int = DEMO_USER_ID) -> None:
    """Atomically publish the current analysis, including an empty result."""
    with get_connection() as conn:
        conn.execute("DELETE FROM anomaly_findings WHERE user_id = ?", (user_id,))
        for f in findings:
            cur = conn.execute(
                """INSERT INTO anomaly_findings
                (user_id, metric_type, finding_type, severity_band, window_start,
                 window_end, deviation, supporting, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, f.metric_type, f.finding_type, f.severity_band,
                 f.window_start, f.window_end, f.deviation, f.supporting,
                 f.created_at or utc_now_iso()),
            )
            f.id = int(cur.lastrowid)


def list_findings(*, user_id: int = DEMO_USER_ID, limit: Optional[int] = None) -> list[AnomalyFinding]:
    sql = "SELECT * FROM anomaly_findings WHERE user_id = ? ORDER BY created_at DESC, id DESC"
    params: list[object] = [user_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_finding(r) for r in rows]


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #

def insert_alert(a: Alert) -> int:
    created = a.created_at or utc_now_iso()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO alerts
                (user_id, state, title, explanation, next_steps, finding_ids, is_experimental, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                a.user_id,
                a.state,
                a.title,
                a.explanation,
                a.next_steps,
                a.finding_ids,
                1 if a.is_experimental else 0,
                created,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def latest_alert(*, user_id: int = DEMO_USER_ID) -> Optional[Alert]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM alerts WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return _row_to_alert(row) if row else None


def list_alerts(*, user_id: int = DEMO_USER_ID, limit: Optional[int] = None) -> list[Alert]:
    sql = "SELECT * FROM alerts WHERE user_id = ? ORDER BY created_at DESC, id DESC"
    params: list[object] = [user_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_alert(r) for r in rows]


# --------------------------------------------------------------------------- #
# Simulator state (single row, id = 1)
# --------------------------------------------------------------------------- #

def get_sim_state() -> SimState:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM sim_state WHERE id = 1").fetchone()
    if row is None:
        # Should not happen after init_db, but fail loudly if it does.
        raise RuntimeError("sim_state row missing; call init_db() first")
    return _row_to_sim_state(row)


def update_sim_state(
    *,
    scenario: Optional[str] = None,
    status: Optional[str] = None,
    seed: Optional[int] = None,
    cursor_ts: object = _UNSET,
) -> SimState:
    """Patch the single sim_state row with any provided fields.

    ``cursor_ts`` uses a sentinel default so that passing ``None`` explicitly
    clears it (sets NULL) while omitting it leaves the stored value unchanged.
    """
    sets: list[str] = []
    params: list[object] = []
    if scenario is not None:
        sets.append("scenario = ?")
        params.append(scenario)
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if seed is not None:
        sets.append("seed = ?")
        params.append(seed)
    if cursor_ts is not _UNSET:
        sets.append("cursor_ts = ?")
        params.append(cursor_ts)
    sets.append("updated_at = ?")
    params.append(utc_now_iso())

    with get_connection() as conn:
        conn.execute(f"UPDATE sim_state SET {', '.join(sets)} WHERE id = 1", params)
        conn.commit()
    return get_sim_state()


# --------------------------------------------------------------------------- #
# Row -> dataclass mappers
# --------------------------------------------------------------------------- #

def _row_to_measurement(r: sqlite3.Row) -> Measurement:
    return Measurement(
        id=r["id"],
        user_id=r["user_id"],
        timestamp=r["timestamp"],
        metric_type=r["metric_type"],
        value=r["value"],
        quality=r["quality"],
        is_synthetic=bool(r["is_synthetic"]),
        scenario=r["scenario"],
    )


def _row_to_baseline(r: sqlite3.Row) -> Baseline:
    return Baseline(
        id=r["id"],
        user_id=r["user_id"],
        metric_type=r["metric_type"],
        mean=r["mean"],
        std=r["std"],
        sample_count=r["sample_count"],
        computed_at=r["computed_at"],
    )


def _row_to_finding(r: sqlite3.Row) -> AnomalyFinding:
    return AnomalyFinding(
        id=r["id"],
        user_id=r["user_id"],
        metric_type=r["metric_type"],
        finding_type=r["finding_type"],
        severity_band=r["severity_band"],
        window_start=r["window_start"],
        window_end=r["window_end"],
        deviation=r["deviation"],
        supporting=r["supporting"],
        created_at=r["created_at"],
    )


def _row_to_alert(r: sqlite3.Row) -> Alert:
    return Alert(
        id=r["id"],
        user_id=r["user_id"],
        state=r["state"],
        title=r["title"],
        explanation=r["explanation"],
        next_steps=r["next_steps"],
        finding_ids=r["finding_ids"],
        is_experimental=bool(r["is_experimental"]),
        created_at=r["created_at"],
    )


def _row_to_sim_state(r: sqlite3.Row) -> SimState:
    return SimState(
        id=r["id"],
        scenario=r["scenario"],
        status=r["status"],
        seed=r["seed"],
        cursor_ts=r["cursor_ts"],
        updated_at=r["updated_at"],
    )
