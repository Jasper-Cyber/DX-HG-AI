"""Repository functions for the care-network tables (Task 18).

Scope: user_settings, care_profiles, emergency_contacts, providers,
dispatch_events. Services (ProviderService / EmergencyService, Tasks 19-20)
call these; they do not embed SQL.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from .care_models import (
    CareProfile,
    DispatchEvent,
    EmergencyContact,
    Provider,
    UserSettings,
)
from .connection import DEMO_USER_ID, get_connection, utc_now_iso

# --------------------------------------------------------------------------- #
# User settings / feature flags
# --------------------------------------------------------------------------- #

def get_settings(*, user_id: int = DEMO_USER_ID) -> UserSettings:
    """Return the user's settings, creating defaults (opt-in off) on first access."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            now = utc_now_iso()
            conn.execute(
                """
                INSERT INTO user_settings
                    (user_id, warnings_enabled, suggestions_enabled, emergency_enabled, updated_at)
                VALUES (?, 1, 0, 0, ?)
                """,
                (user_id, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
            ).fetchone()
    return _row_to_settings(row)


def update_settings(
    *,
    warnings_enabled: Optional[bool] = None,
    suggestions_enabled: Optional[bool] = None,
    emergency_enabled: Optional[bool] = None,
    disclaimer_ack_at: Optional[str] = None,
    user_id: int = DEMO_USER_ID,
) -> UserSettings:
    """Patch any provided settings fields. Ensures a row exists first."""
    get_settings(user_id=user_id)  # ensure row exists

    sets: list[str] = []
    params: list[object] = []
    if warnings_enabled is not None:
        sets.append("warnings_enabled = ?")
        params.append(1 if warnings_enabled else 0)
    if suggestions_enabled is not None:
        sets.append("suggestions_enabled = ?")
        params.append(1 if suggestions_enabled else 0)
    if emergency_enabled is not None:
        sets.append("emergency_enabled = ?")
        params.append(1 if emergency_enabled else 0)
    if disclaimer_ack_at is not None:
        sets.append("disclaimer_ack_at = ?")
        params.append(disclaimer_ack_at)
    sets.append("updated_at = ?")
    params.append(utc_now_iso())
    params.append(user_id)

    with get_connection() as conn:
        conn.execute(f"UPDATE user_settings SET {', '.join(sets)} WHERE user_id = ?", params)
        conn.commit()
    return get_settings(user_id=user_id)


def acknowledge_disclaimer(*, user_id: int = DEMO_USER_ID) -> UserSettings:
    """Record that the experimental disclaimer was acknowledged now (Req 12.5)."""
    return update_settings(disclaimer_ack_at=utc_now_iso(), user_id=user_id)


# --------------------------------------------------------------------------- #
# Providers (seeded directory)
# --------------------------------------------------------------------------- #

def insert_provider(p: Provider) -> int:
    created = p.created_at or utc_now_iso()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO providers
                (kind, name, specialty, can_handle_cardiac_emergency, phone, address, lat, lon, is_synthetic, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p.kind,
                p.name,
                p.specialty,
                1 if p.can_handle_cardiac_emergency else 0,
                p.phone,
                p.address,
                p.lat,
                p.lon,
                1 if p.is_synthetic else 0,
                created,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_providers(*, kind: Optional[str] = None) -> list[Provider]:
    sql = "SELECT * FROM providers"
    params: list[object] = []
    if kind is not None:
        sql += " WHERE kind = ?"
        params.append(kind)
    sql += " ORDER BY name"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_provider(r) for r in rows]


def get_provider(provider_id: int) -> Optional[Provider]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    return _row_to_provider(row) if row else None


def count_providers() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM providers").fetchone()
    return int(row["n"])


# --------------------------------------------------------------------------- #
# Care profile + emergency contacts
# --------------------------------------------------------------------------- #

def get_care_profile(*, user_id: int = DEMO_USER_ID) -> Optional[CareProfile]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM care_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        profile = _row_to_care_profile(row)
        contacts = conn.execute(
            "SELECT * FROM emergency_contacts WHERE user_id = ? ORDER BY priority, id",
            (user_id,),
        ).fetchall()
    profile.emergency_contacts = [_row_to_contact(c) for c in contacts]
    return profile


def upsert_care_profile(profile: CareProfile) -> CareProfile:
    """Insert or update the single care profile for a user and replace its contacts."""
    now = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO care_profiles
                (user_id, full_name, phone, default_lat, default_lon, preferred_provider_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                phone = excluded.phone,
                default_lat = excluded.default_lat,
                default_lon = excluded.default_lon,
                preferred_provider_id = excluded.preferred_provider_id,
                updated_at = excluded.updated_at
            """,
            (
                profile.user_id,
                profile.full_name,
                profile.phone,
                profile.default_lat,
                profile.default_lon,
                profile.preferred_provider_id,
                now,
            ),
        )
        # Replace contacts wholesale (simplest consistent behavior for the MVP).
        conn.execute("DELETE FROM emergency_contacts WHERE user_id = ?", (profile.user_id,))
        for c in profile.emergency_contacts:
            conn.execute(
                """
                INSERT INTO emergency_contacts (user_id, name, relationship, phone, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (profile.user_id, c.name, c.relationship, c.phone, c.priority, c.created_at or now),
            )
        conn.commit()
    result = get_care_profile(user_id=profile.user_id)
    assert result is not None
    return result


# --------------------------------------------------------------------------- #
# Dispatch events
# --------------------------------------------------------------------------- #

def insert_dispatch_event(e: DispatchEvent) -> int:
    created = e.created_at or utc_now_iso()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO dispatch_events
                (user_id, alert_id, recipient_provider_id, routing_reason, channel, status, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                e.user_id,
                e.alert_id,
                e.recipient_provider_id,
                e.routing_reason,
                e.channel,
                e.status,
                e.payload,
                created,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_dispatch_events(*, user_id: int = DEMO_USER_ID, limit: Optional[int] = None) -> list[DispatchEvent]:
    sql = "SELECT * FROM dispatch_events WHERE user_id = ? ORDER BY created_at DESC"
    params: list[object] = [user_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_dispatch(r) for r in rows]


# --------------------------------------------------------------------------- #
# Row -> dataclass mappers
# --------------------------------------------------------------------------- #

def _row_to_settings(r: sqlite3.Row) -> UserSettings:
    return UserSettings(
        user_id=r["user_id"],
        warnings_enabled=bool(r["warnings_enabled"]),
        suggestions_enabled=bool(r["suggestions_enabled"]),
        emergency_enabled=bool(r["emergency_enabled"]),
        disclaimer_ack_at=r["disclaimer_ack_at"],
        updated_at=r["updated_at"],
    )


def _row_to_provider(r: sqlite3.Row) -> Provider:
    return Provider(
        id=r["id"],
        kind=r["kind"],
        name=r["name"],
        specialty=r["specialty"],
        can_handle_cardiac_emergency=bool(r["can_handle_cardiac_emergency"]),
        phone=r["phone"],
        address=r["address"],
        lat=r["lat"],
        lon=r["lon"],
        is_synthetic=bool(r["is_synthetic"]),
        created_at=r["created_at"],
    )


def _row_to_care_profile(r: sqlite3.Row) -> CareProfile:
    return CareProfile(
        id=r["id"],
        user_id=r["user_id"],
        full_name=r["full_name"],
        phone=r["phone"],
        default_lat=r["default_lat"],
        default_lon=r["default_lon"],
        preferred_provider_id=r["preferred_provider_id"],
        updated_at=r["updated_at"],
    )


def _row_to_contact(r: sqlite3.Row) -> EmergencyContact:
    return EmergencyContact(
        id=r["id"],
        user_id=r["user_id"],
        name=r["name"],
        relationship=r["relationship"],
        phone=r["phone"],
        priority=r["priority"],
        created_at=r["created_at"],
    )


def _row_to_dispatch(r: sqlite3.Row) -> DispatchEvent:
    return DispatchEvent(
        id=r["id"],
        user_id=r["user_id"],
        alert_id=r["alert_id"],
        recipient_provider_id=r["recipient_provider_id"],
        routing_reason=r["routing_reason"],
        channel=r["channel"],
        status=r["status"],
        payload=r["payload"],
        created_at=r["created_at"],
    )
