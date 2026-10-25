"""ProviderService — nearby-provider suggestions (Task 19).

Computes great-circle (haversine) distance from the user's location to each
provider in the seeded directory and ranks them:
  - non-emergency: by distance ascending
  - emergency: cardiac-capable providers first, then by distance

The user's preferred doctor (if any) is flagged in the results. All providers
are synthetic/for-demonstration (Req 10.8).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from ..db import care_repository as care
from ..db.care_models import Provider

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass(slots=True)
class ProviderSuggestion:
    provider: Provider
    distance_km: float
    is_preferred: bool


class ProviderService:
    """Ranks the provider directory by suitability for a given location."""

    def suggest(
        self,
        lat: float,
        lon: float,
        *,
        emergency: bool = False,
        preferred_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[ProviderSuggestion]:
        providers = care.list_providers()
        suggestions = [
            ProviderSuggestion(
                provider=p,
                distance_km=round(haversine_km(lat, lon, p.lat, p.lon), 3),
                is_preferred=(preferred_id is not None and p.id == preferred_id),
            )
            for p in providers
        ]

        if emergency:
            # Cardiac-capable first, then nearest. (False < True, so negate.)
            suggestions.sort(
                key=lambda s: (not s.provider.can_handle_cardiac_emergency, s.distance_km)
            )
        else:
            suggestions.sort(key=lambda s: s.distance_km)

        if limit is not None:
            suggestions = suggestions[:limit]
        return suggestions
