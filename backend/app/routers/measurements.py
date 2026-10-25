"""GET /measurements — read synthetic physiological readings (Task 8).

Fully backed by the repository layer; no simulator dependency. Supports optional
filtering by metric and time range. All returned readings are labeled synthetic.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..db import repository as repo
from ..db.models import Measurement

router = APIRouter(prefix="/measurements", tags=["measurements"])

_VALID_METRICS = {"hr", "hrv", "spo2", "rhythm", "activity", "sleep", "vo2max"}


class MeasurementOut(BaseModel):
    id: Optional[int]
    timestamp: str
    metricType: str
    value: Optional[float]
    quality: str
    isSynthetic: bool
    scenario: str

    @classmethod
    def from_model(cls, m: Measurement) -> "MeasurementOut":
        return cls(
            id=m.id,
            timestamp=m.timestamp,
            metricType=m.metric_type,
            value=m.value,
            quality=m.quality,
            isSynthetic=m.is_synthetic,
            scenario=m.scenario,
        )


class MeasurementsResponse(BaseModel):
    count: int
    isExperimental: bool = True
    items: list[MeasurementOut]


@router.get("", response_model=MeasurementsResponse)
def get_measurements(
    metric: Optional[str] = Query(default=None, description="hr|hrv|spo2|rhythm|activity|sleep|vo2max"),
    from_: Optional[str] = Query(default=None, alias="from", description="ISO-8601 start (inclusive)"),
    to: Optional[str] = Query(default=None, description="ISO-8601 end (inclusive)"),
    limit: Optional[int] = Query(default=None, ge=1, le=10000),
) -> MeasurementsResponse:
    # Validate the metric up front so the client gets a clear 422 instead of an
    # empty result for a typo'd metric name.
    if metric is not None and metric not in _VALID_METRICS:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=f"Unknown metric '{metric}'")

    rows = repo.query_measurements(metric_type=metric, start=from_, end=to, limit=limit)
    return MeasurementsResponse(
        count=len(rows),
        items=[MeasurementOut.from_model(r) for r in rows],
    )
