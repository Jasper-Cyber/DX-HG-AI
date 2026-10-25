"""Feature-flag settings + disclaimer endpoints (Task 18 / Task 21 seam).

Exposes the user-controlled flags that make warnings, provider suggestions, and
the emergency flow optional. Suggestions and emergency default OFF (Req 10.1, 11.1).
`POST /settings/disclaimer-ack` records the one-time disclaimer acknowledgement (Req 12.5).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..db import care_repository as care
from ..db.care_models import UserSettings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    warningsEnabled: bool
    suggestionsEnabled: bool
    emergencyEnabled: bool
    disclaimerAckAt: Optional[str]
    updatedAt: Optional[str]

    @classmethod
    def from_model(cls, s: UserSettings) -> "SettingsOut":
        return cls(
            warningsEnabled=s.warnings_enabled,
            suggestionsEnabled=s.suggestions_enabled,
            emergencyEnabled=s.emergency_enabled,
            disclaimerAckAt=s.disclaimer_ack_at,
            updatedAt=s.updated_at,
        )


class SettingsUpdate(BaseModel):
    warningsEnabled: Optional[bool] = None
    suggestionsEnabled: Optional[bool] = None
    emergencyEnabled: Optional[bool] = None


@router.get("", response_model=SettingsOut)
def get_settings() -> SettingsOut:
    return SettingsOut.from_model(care.get_settings())


@router.put("", response_model=SettingsOut)
def update_settings(body: SettingsUpdate) -> SettingsOut:
    s = care.update_settings(
        warnings_enabled=body.warningsEnabled,
        suggestions_enabled=body.suggestionsEnabled,
        emergency_enabled=body.emergencyEnabled,
    )
    return SettingsOut.from_model(s)


@router.post("/disclaimer-ack", response_model=SettingsOut)
def acknowledge_disclaimer() -> SettingsOut:
    return SettingsOut.from_model(care.acknowledge_disclaimer())
