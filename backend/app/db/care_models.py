"""Dataclasses for the care-network tables (Task 18).

Kept separate from the core `models.py` so the two task areas stay decoupled.
Covers user_settings, care_profiles, emergency_contacts, providers, dispatch_events.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

ProviderKind = Literal["doctor", "hospital"]
DispatchChannel = Literal["simulated", "real"]
DispatchStatus = Literal["pending_confirm", "cancelled", "sent", "failed"]


@dataclass(slots=True)
class UserSettings:
    warnings_enabled: bool = True
    suggestions_enabled: bool = False  # opt-in (Req 10.1)
    emergency_enabled: bool = False    # opt-in, off by default (Req 11.1)
    disclaimer_ack_at: Optional[str] = None
    updated_at: Optional[str] = None
    user_id: int = 1


@dataclass(slots=True)
class EmergencyContact:
    name: str
    phone: str
    relationship: Optional[str] = None
    priority: int = 1
    created_at: Optional[str] = None
    id: Optional[int] = None
    user_id: int = 1


@dataclass(slots=True)
class CareProfile:
    full_name: Optional[str] = None
    phone: Optional[str] = None
    default_lat: Optional[float] = None
    default_lon: Optional[float] = None
    preferred_provider_id: Optional[int] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None
    user_id: int = 1
    emergency_contacts: list[EmergencyContact] = field(default_factory=list)


@dataclass(slots=True)
class Provider:
    kind: ProviderKind
    name: str
    lat: float
    lon: float
    specialty: Optional[str] = None
    can_handle_cardiac_emergency: bool = False
    phone: Optional[str] = None
    address: Optional[str] = None
    is_synthetic: bool = True
    created_at: Optional[str] = None
    id: Optional[int] = None


@dataclass(slots=True)
class DispatchEvent:
    routing_reason: str
    channel: DispatchChannel
    status: DispatchStatus
    payload: str  # JSON text
    recipient_provider_id: Optional[int] = None
    alert_id: Optional[int] = None
    created_at: Optional[str] = None
    id: Optional[int] = None
    user_id: int = 1
