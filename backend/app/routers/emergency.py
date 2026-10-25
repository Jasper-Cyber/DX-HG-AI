"""Emergency-response endpoints (Task 20).

- POST /emergency/evaluate : routing decision + payload preview (opt-in gated)
- POST /emergency/dispatch  : perform dispatch (simulated default; real gated + confirmed)
- GET  /emergency/history   : past dispatch events

All responses carry the static, non-diagnostic emergency guidance.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import emergency_config as cfg
from ..db import care_repository as care
from ..db.care_models import DispatchEvent
from ..services.emergency import (
    EmergencyDecision,
    EmergencyNotAvailable,
    EmergencyService,
    RealDispatchNotAllowed,
)

router = APIRouter(prefix="/emergency", tags=["emergency"])
_service = EmergencyService()


class EvaluateIn(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    findingSummary: str = "No specific findings provided."


class DecisionOut(BaseModel):
    enabled: bool
    recipientProviderId: Optional[int] = None
    recipientName: Optional[str] = None
    routingReason: Optional[str] = None
    payload: Optional[dict] = None
    channel: Optional[str] = None
    emergencyGuidance: str = cfg.EMERGENCY_GUIDANCE
    isExperimental: bool = True


class DispatchIn(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    findingSummary: str = "No specific findings provided."
    channel: str = "simulated"
    confirmed: bool = False
    alertId: Optional[int] = None


class DispatchOut(BaseModel):
    id: Optional[int]
    recipientProviderId: Optional[int]
    routingReason: str
    channel: str
    status: str
    payload: dict
    emergencyGuidance: str = cfg.EMERGENCY_GUIDANCE
    isExperimental: bool = True


def _decision_to_out(decision: EmergencyDecision) -> DecisionOut:
    return DecisionOut(
        enabled=True,
        recipientProviderId=decision.recipient.id,
        recipientName=decision.recipient.name,
        routingReason=decision.routing_reason,
        payload=decision.payload,
        channel=decision.channel,
    )


@router.post("/evaluate", response_model=DecisionOut)
def evaluate(body: EvaluateIn) -> DecisionOut:
    try:
        decision = _service.evaluate(lat=body.lat, lon=body.lon, finding_summary=body.findingSummary)
    except EmergencyNotAvailable as e:
        raise HTTPException(status_code=409, detail=str(e))
    if decision is None:
        # Feature is disabled; not an error, just nothing to dispatch.
        return DecisionOut(enabled=False)
    return _decision_to_out(decision)


@router.post("/dispatch", response_model=DispatchOut)
def dispatch(body: DispatchIn) -> DispatchOut:
    try:
        decision = _service.evaluate(lat=body.lat, lon=body.lon, finding_summary=body.findingSummary)
    except EmergencyNotAvailable as e:
        raise HTTPException(status_code=409, detail=str(e))
    if decision is None:
        raise HTTPException(status_code=409, detail="Emergency response is not enabled.")

    try:
        event = _service.dispatch(
            decision, channel=body.channel, confirmed=body.confirmed, alert_id=body.alertId
        )
    except RealDispatchNotAllowed as e:
        raise HTTPException(status_code=403, detail=str(e))
    except EmergencyNotAvailable as e:
        # e.g. confirmation missing
        raise HTTPException(status_code=422, detail=str(e))

    import json

    return DispatchOut(
        id=event.id,
        recipientProviderId=event.recipient_provider_id,
        routingReason=event.routing_reason,
        channel=event.channel,
        status=event.status,
        payload=json.loads(event.payload),
    )


class HistoryItem(BaseModel):
    id: Optional[int]
    recipientProviderId: Optional[int]
    routingReason: str
    channel: str
    status: str
    createdAt: Optional[str]


@router.get("/history", response_model=list[HistoryItem])
def history() -> list[HistoryItem]:
    events = _service.history()
    return [
        HistoryItem(
            id=e.id,
            recipientProviderId=e.recipient_provider_id,
            routingReason=e.routing_reason,
            channel=e.channel,
            status=e.status,
            createdAt=e.created_at,
        )
        for e in events
    ]
