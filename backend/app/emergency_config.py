"""Transparent, configurable settings for the emergency-response flow (Task 20).

All routing/dispatch behavior is driven by these values so the logic is auditable
and reproducible (Req 11.10). Nothing here is a clinical threshold.
"""
from __future__ import annotations

import os

# A preferred doctor is only chosen if within this distance; otherwise the flow
# falls back to the nearest cardiac-capable hospital (Req 11.3 routing rule).
MAX_REACHABLE_KM: float = float(os.environ.get("HG_MAX_REACHABLE_KM", "15"))

# Real outbound dispatch is OFF unless this opt-in flag is explicitly enabled.
# When False, any request for channel='real' is rejected (Req 11.6 / 403).
REAL_DISPATCH_ENABLED: bool = os.environ.get("HG_REAL_DISPATCH_ENABLED", "0") == "1"

# Static, non-diagnostic guidance always shown alongside any dispatch (Req 11.8).
EMERGENCY_GUIDANCE: str = (
    "This is an experimental prototype and may be wrong. If you or someone nearby "
    "has symptoms of a possible heart attack or stroke (e.g. chest pain, trouble "
    "breathing, face drooping, weakness, or difficulty speaking), contact your local "
    "emergency services immediately. This app does not replace professional medical care."
)
