"""EmergencyService — opt-in, user-confirmed emergency routing + dispatch (Task 20).

Flow (all transparent + reproducible):
  1. evaluate(): only runs when the user enabled the feature (Req 11.1). Chooses a
     recipient via the routing rule (preferred doctor if reachable, else nearest
     cardiac-capable hospital) and builds the dispatch payload.
  2. dispatch(): records a dispatch_events row. Default channel 'simulated' sends
     nothing externally. channel='real' is rejected unless the opt-in config flag
     is set AND the request is explicitly confirmed (Req 11.6).

Nothing here diagnoses a condition; the finding summary is non-diagnostic and
labeled experimental (Req 11.4 / 11.9).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .. import emergency_config as cfg
from ..adapters.notifier import NotifierAdapter, SimulatedNotifier
from ..db import care_repository as care
from ..db.care_models import DispatchEvent, Provider
from ..db.connection import DEMO_USER_ID, utc_now_iso
from .provider import ProviderService, haversine_km


@dataclass(slots=True)
class EmergencyDecision:
    recipient: Provider
    routing_reason: str  # 'preferred_doctor_reachable' | 'nearest_capable_hospital'
    payload: dict
    channel: str = "simulated"


class EmergencyNotAvailable(Exception):
    """Raised when the feature is disabled or no suitable recipient exists."""


class RealDispatchNotAllowed(Exception):
    """Raised when a real dispatch is requested without the opt-in config flag."""


class EmergencyService:
    def __init__(self, notifier: Optional[NotifierAdapter] = None) -> None:
        self._providers = ProviderService()
        self._notifier = notifier or SimulatedNotifier()

    # --------------------------------------------------------------------- #
    # Evaluation / routing
    # --------------------------------------------------------------------- #

    def evaluate(
        self,
        *,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        finding_summary: str = "No specific findings provided.",
        user_id: int = DEMO_USER_ID,
    ) -> Optional[EmergencyDecision]:
        """Return a routing decision, or None if the feature is disabled.

        Raises EmergencyNotAvailable if enabled but no location or no capable
        provider is available.
        """
        settings = care.get_settings(user_id=user_id)
        if not settings.emergency_enabled:
            return None  # opt-in off => no dispatch path (Req 11.1)

        profile = care.get_care_profile(user_id=user_id)

        # Resolve location: explicit coords, else profile default (approximate).
        approximate = False
        if lat is None or lon is None:
            if profile and profile.default_lat is not None and profile.default_lon is not None:
                lat, lon, approximate = profile.default_lat, profile.default_lon, True
            else:
                raise EmergencyNotAvailable("No location available for emergency routing.")

        recipient, reason = self._route(lat, lon, profile)
        payload = self._build_payload(profile, lat, lon, approximate, finding_summary)
        return EmergencyDecision(recipient=recipient, routing_reason=reason, payload=payload)

    def _route(self, lat: float, lon: float, profile) -> tuple[Provider, str]:
        """Preferred doctor if within MAX_REACHABLE_KM, else nearest capable hospital."""
        preferred_id = profile.preferred_provider_id if profile else None

        if preferred_id is not None:
            preferred = care.get_provider(preferred_id)
            if preferred is not None:
                dist = haversine_km(lat, lon, preferred.lat, preferred.lon)
                if dist <= cfg.MAX_REACHABLE_KM:
                    return preferred, "preferred_doctor_reachable"

        # Fall back to the nearest cardiac-capable provider.
        suggestions = self._providers.suggest(lat, lon, emergency=True)
        for s in suggestions:
            if s.provider.can_handle_cardiac_emergency:
                return s.provider, "nearest_capable_hospital"

        raise EmergencyNotAvailable(
            "No cardiac-capable provider in the directory. Contact local emergency services directly."
        )

    def _build_payload(self, profile, lat, lon, approximate, finding_summary) -> dict:
        contacts = (
            [
                {
                    "name": c.name,
                    "relationship": c.relationship,
                    "phone": c.phone,
                    "priority": c.priority,
                }
                for c in profile.emergency_contacts
            ]
            if profile
            else []
        )
        return {
            "patient": {
                "name": profile.full_name if profile else None,
                "phone": profile.phone if profile else None,
            },
            "location": {
                "lat": lat,
                "lon": lon,
                "approximate": approximate,
            },
            "emergencyContacts": contacts,
            "findingSummary": finding_summary,  # non-diagnostic (Req 11.4)
            "isExperimental": True,
        }

    # --------------------------------------------------------------------- #
    # Dispatch
    # --------------------------------------------------------------------- #

    def dispatch(
        self,
        decision: EmergencyDecision,
        *,
        channel: str = "simulated",
        confirmed: bool = False,
        alert_id: Optional[int] = None,
        user_id: int = DEMO_USER_ID,
    ) -> DispatchEvent:
        """Record and perform a dispatch. Requires explicit confirmation (Req 11.5).

        channel='real' additionally requires the opt-in config flag (Req 11.6),
        otherwise RealDispatchNotAllowed is raised.
        """
        if not confirmed:
            raise EmergencyNotAvailable("Dispatch requires explicit user confirmation.")
        if channel == "real" and not cfg.REAL_DISPATCH_ENABLED:
            raise RealDispatchNotAllowed(
                "Real dispatch is disabled. Set the opt-in config flag to enable it."
            )

        result = self._notifier.send(decision.recipient, decision.payload)
        status = "sent" if result.delivered else "failed"

        event = DispatchEvent(
            user_id=user_id,
            alert_id=alert_id,
            recipient_provider_id=decision.recipient.id,
            routing_reason=decision.routing_reason,
            channel=result.channel,
            status=status,
            payload=json.dumps(decision.payload),
            created_at=utc_now_iso(),
        )
        event.id = care.insert_dispatch_event(event)
        return event

    def history(self, *, user_id: int = DEMO_USER_ID, limit: Optional[int] = None) -> list[DispatchEvent]:
        return care.list_dispatch_events(user_id=user_id, limit=limit)
