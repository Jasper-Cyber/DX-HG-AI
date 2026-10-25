"""Care-profile + provider-suggestion endpoints (Task 19).

- GET/PUT /care/profile : the user's optional contact info + emergency contacts + preferred doctor
- GET /providers        : nearby provider suggestions ranked by distance (and capability if emergency)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..db import care_repository as care
from ..db.care_models import CareProfile, EmergencyContact
from ..services.provider import ProviderService

router = APIRouter(tags=["care-network"])
_service = ProviderService()


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

class ContactSchema(BaseModel):
    name: str
    phone: str
    relationship: Optional[str] = None
    priority: int = 1


class CareProfileIn(BaseModel):
    fullName: Optional[str] = None
    phone: Optional[str] = None
    defaultLat: Optional[float] = None
    defaultLon: Optional[float] = None
    preferredProviderId: Optional[int] = None
    emergencyContacts: list[ContactSchema] = []


class CareProfileOut(BaseModel):
    fullName: Optional[str]
    phone: Optional[str]
    defaultLat: Optional[float]
    defaultLon: Optional[float]
    preferredProviderId: Optional[int]
    emergencyContacts: list[ContactSchema]

    @classmethod
    def from_model(cls, p: CareProfile) -> "CareProfileOut":
        return cls(
            fullName=p.full_name,
            phone=p.phone,
            defaultLat=p.default_lat,
            defaultLon=p.default_lon,
            preferredProviderId=p.preferred_provider_id,
            emergencyContacts=[
                ContactSchema(
                    name=c.name, phone=c.phone, relationship=c.relationship, priority=c.priority
                )
                for c in p.emergency_contacts
            ],
        )


class ProviderSchema(BaseModel):
    id: Optional[int]
    kind: str
    name: str
    specialty: Optional[str]
    canHandleCardiacEmergency: bool
    phone: Optional[str]
    address: Optional[str]
    lat: float
    lon: float
    isSynthetic: bool


class SuggestionSchema(BaseModel):
    provider: ProviderSchema
    distanceKm: float
    isPreferred: bool


class SuggestionsResponse(BaseModel):
    count: int
    isExperimental: bool = True
    items: list[SuggestionSchema]


# --------------------------------------------------------------------------- #
# Care profile
# --------------------------------------------------------------------------- #

@router.get("/care/profile", response_model=Optional[CareProfileOut])
def get_care_profile() -> Optional[CareProfileOut]:
    profile = care.get_care_profile()
    return CareProfileOut.from_model(profile) if profile else None


@router.put("/care/profile", response_model=CareProfileOut)
def put_care_profile(body: CareProfileIn) -> CareProfileOut:
    profile = CareProfile(
        full_name=body.fullName,
        phone=body.phone,
        default_lat=body.defaultLat,
        default_lon=body.defaultLon,
        preferred_provider_id=body.preferredProviderId,
        emergency_contacts=[
            EmergencyContact(
                name=c.name, phone=c.phone, relationship=c.relationship, priority=c.priority
            )
            for c in body.emergencyContacts
        ],
    )
    saved = care.upsert_care_profile(profile)
    return CareProfileOut.from_model(saved)


# --------------------------------------------------------------------------- #
# Provider suggestions
# --------------------------------------------------------------------------- #

@router.get("/providers", response_model=SuggestionsResponse)
def get_providers(
    lat: Optional[float] = Query(default=None, description="user latitude"),
    lon: Optional[float] = Query(default=None, description="user longitude"),
    emergency: bool = Query(default=False),
    limit: Optional[int] = Query(default=None, ge=1, le=100),
) -> SuggestionsResponse:
    # Fall back to the care profile's default location when live coords are
    # not supplied (Req 10.8 approximate-location handling).
    if lat is None or lon is None:
        profile = care.get_care_profile()
        if profile and profile.default_lat is not None and profile.default_lon is not None:
            lat = lat if lat is not None else profile.default_lat
            lon = lon if lon is not None else profile.default_lon

    if lat is None or lon is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail="No location available: provide lat/lon or set a default location in the care profile.",
        )

    preferred_id = None
    profile = care.get_care_profile()
    if profile:
        preferred_id = profile.preferred_provider_id

    suggestions = _service.suggest(lat, lon, emergency=emergency, preferred_id=preferred_id, limit=limit)
    items = [
        SuggestionSchema(
            provider=ProviderSchema(
                id=s.provider.id,
                kind=s.provider.kind,
                name=s.provider.name,
                specialty=s.provider.specialty,
                canHandleCardiacEmergency=s.provider.can_handle_cardiac_emergency,
                phone=s.provider.phone,
                address=s.provider.address,
                lat=s.provider.lat,
                lon=s.provider.lon,
                isSynthetic=s.provider.is_synthetic,
            ),
            distanceKm=s.distance_km,
            isPreferred=s.is_preferred,
        )
        for s in suggestions
    ]
    return SuggestionsResponse(count=len(items), items=items)
