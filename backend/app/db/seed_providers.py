"""Seed a synthetic provider directory (Task 18).

All providers are fictional/for-demonstration (is_synthetic=1). Coordinates are
placed around a demo city center so distance ranking produces a meaningful order.
Idempotent: only seeds when the providers table is empty.
"""
from __future__ import annotations

from .care_models import Provider
from .care_repository import count_providers, insert_provider

# Demo city center (synthetic). The seeded care profile uses this as its
# default location so suggestions have something to rank against.
DEMO_CENTER_LAT = 40.7128
DEMO_CENTER_LON = -74.0060

# (kind, name, specialty, can_handle_cardiac_emergency, phone, address, d_lat, d_lon)
# d_lat/d_lon are small offsets from the demo center.
_SEED = [
    ("hospital", "Harbor General Hospital", "emergency", True, "+1-555-0100", "1 Harbor Way", 0.010, 0.005),
    ("hospital", "Riverside Medical Center", "emergency", True, "+1-555-0101", "22 Riverside Blvd", -0.025, 0.030),
    ("hospital", "Northgate Community Hospital", "general", False, "+1-555-0102", "90 Northgate Rd", 0.040, -0.020),
    ("hospital", "Summit Cardiac Institute", "cardiology", True, "+1-555-0103", "7 Summit Ave", 0.060, 0.055),
    ("doctor", "Dr. Alice Moreno", "cardiology", False, "+1-555-0200", "Suite 210, Elm Plaza", 0.004, -0.003),
    ("doctor", "Dr. Ben Oyelaran", "cardiology", False, "+1-555-0201", "Suite 5, Maple Court", -0.012, 0.015),
    ("doctor", "Dr. Chen Wei", "internal medicine", False, "+1-555-0202", "Level 3, Oak Tower", 0.030, 0.040),
    ("doctor", "Dr. Dana Kovac", "general practice", False, "+1-555-0203", "12 Birch Lane", -0.050, -0.045),
]


def seed_providers(*, force: bool = False) -> int:
    """Insert the synthetic directory. Returns the number inserted.

    No-op if providers already exist, unless ``force`` is True.
    """
    if not force and count_providers() > 0:
        return 0

    inserted = 0
    for kind, name, specialty, cardiac, phone, address, d_lat, d_lon in _SEED:
        insert_provider(
            Provider(
                kind=kind,
                name=name,
                specialty=specialty,
                can_handle_cardiac_emergency=cardiac,
                phone=phone,
                address=address,
                lat=DEMO_CENTER_LAT + d_lat,
                lon=DEMO_CENTER_LON + d_lon,
                is_synthetic=True,
            )
        )
        inserted += 1
    return inserted
