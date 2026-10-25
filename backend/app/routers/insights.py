"""GET /insights — current explainable, non-diagnostic insight (Task 12).

PURPOSE
-------
Exposes the latest insight for the demo user over HTTP. It returns the current
alert (state, title, explanation, next steps), the ALWAYS-present emergency
guidance, the experimental label/flag, and the supporting findings the alert was
derived from. This backs the mobile Insights/Alerts screen (Task 15).

REQUIREMENT COVERAGE
--------------------
- Req 4.1 — ``state`` is one of ``normal`` | ``trend_review`` | ``attention``.
- Req 4.2 — ``explanation`` references the supporting data; ``nextSteps`` is present.
- Req 4.3 — ``emergencyGuidance`` is ALWAYS present, including when ``state`` is
            ``normal`` and when there are no findings (never 500 / never empty).
- Req 4.4 — no-diagnosis wording comes straight from ``AlertService`` constants.
- Req 4.5 — ``isExperimental`` is True and ``experimentalLabel`` is populated.

DATA SOURCE (documented choice)
-------------------------------
The insight is built from the most-recent STORED findings via
``alerts.build_alert`` (which reads ``repository.list_findings``). A GET therefore
does NOT trigger a recomputation — recomputation is ``POST /analysis/run`` (Task
11, Jasper). With no findings stored, ``AlertService`` still yields a well-formed
``normal`` insight carrying the emergency guidance and experimental label, so the
endpoint always returns a usable 200 payload.

By default the GET is read-only and does NOT persist a new alert row
(``persist=False``) — repeatedly polling the insight should not fill the alerts
table. (Task 11's analysis run is the place that persists an alert.)

SERIALIZATION
-------------
Response fields are camelCase to stay consistent with the existing routers
(``measurements.py`` uses ``metricType`` / ``isExperimental``; ``simulator.py``
uses ``cursorTs``).
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..db.connection import DEMO_USER_ID
from ..db.models import AnomalyFinding
from ..services import alerts as alert_service

router = APIRouter(prefix="/insights", tags=["insights"])


class AlertSummaryOut(BaseModel):
    id: int
    state: str
    title: str
    createdAt: str


@router.get("/history", response_model=list[AlertSummaryOut])
def get_history(limit: int = Query(default=100, ge=1, le=1000)):
    from ..db import repository as repo

    return [AlertSummaryOut(id=a.id, state=a.state, title=a.title, createdAt=a.created_at)
            for a in repo.list_alerts(limit=limit)]


class FindingOut(BaseModel):
    """A supporting anomaly finding, serialized for the client (camelCase)."""

    id: Optional[int]
    metricType: str
    findingType: str
    severityBand: str
    windowStart: str
    windowEnd: str
    deviation: Optional[float]
    supporting: object  # parsed JSON object (falls back to raw string if invalid)
    createdAt: Optional[str]

    @classmethod
    def from_model(cls, f: AnomalyFinding) -> "FindingOut":
        try:
            supporting = json.loads(f.supporting) if f.supporting else {}
        except (ValueError, TypeError):
            supporting = f.supporting
        return cls(
            id=f.id,
            metricType=f.metric_type,
            findingType=f.finding_type,
            severityBand=f.severity_band,
            windowStart=f.window_start,
            windowEnd=f.window_end,
            deviation=f.deviation,
            supporting=supporting,
            createdAt=f.created_at,
        )


class InsightResponse(BaseModel):
    """The current insight for the demo user.

    ``emergencyGuidance`` and ``experimentalLabel`` are ALWAYS populated (Req
    4.3/4.5), independent of ``state``.
    """

    state: str                      # Req 4.1: normal | trend_review | attention
    title: str
    explanation: str                # Req 4.2
    nextSteps: str                  # Req 4.2 (non-diagnostic)
    emergencyGuidance: str          # Req 4.3 (always present)
    experimentalLabel: str          # Req 4.5 (always present)
    isExperimental: bool = True     # Req 4.5
    findingIds: list[int]
    findings: list[FindingOut]


@router.get("", response_model=InsightResponse)
def get_insights(
    persist: bool = Query(
        default=False,
        description="Persist the built alert as a new row (default False: a read "
        "should not fill the alerts table).",
    ),
) -> InsightResponse:
    """Return the latest insight for the demo user.

    Always returns 200 with a well-formed payload: with no findings the insight is
    a calm ``normal`` state that still carries the emergency guidance and
    experimental label (Req 4.3/4.5).
    """
    result = alert_service.build_alert(user_id=DEMO_USER_ID, persist=persist)
    alert = result.alert

    return InsightResponse(
        state=alert.state,
        title=alert.title,
        explanation=alert.explanation,
        # Return the non-diagnostic next-steps text WITHOUT the embedded label /
        # guidance duplication — those are exposed as their own discrete fields so
        # the UI can place them deliberately. The canonical copy is the AlertService
        # constants (single source of truth).
        nextSteps=alert_service.NEXT_STEPS[alert.state],
        emergencyGuidance=alert_service.EMERGENCY_GUIDANCE,
        experimentalLabel=alert_service.EXPERIMENTAL_LABEL,
        isExperimental=alert.is_experimental,
        findingIds=[f.id for f in result.findings if f.id is not None],
        findings=[FindingOut.from_model(f) for f in result.findings],
    )
