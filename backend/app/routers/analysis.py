"""Analysis endpoints (Task 11, Req 5/7).

- POST /analysis/run : recompute baselines + findings, refresh the current alert
- GET  /trends       : aggregated trend series (daily|weekly|monthly) + baseline
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import repository as repo
from ..services.alerts import AlertService
from ..services.analysis import NUMERIC_METRICS

router = APIRouter(tags=["analysis"])
_alerts = AlertService()

_RANGE_RULE = {"daily": "D", "weekly": "W", "monthly": "ME"}


class RunResponse(BaseModel):
    findingsCount: int
    alertState: str
    isExperimental: bool = True


@router.post("/analysis/run", response_model=RunResponse)
def run_analysis() -> RunResponse:
    """Recompute analysis and refresh the alert. Returns a short summary."""
    alert = _alerts.evaluate_and_store(run_analysis=True)
    findings = repo.list_findings()
    return RunResponse(findingsCount=len(findings), alertState=alert.state)


class TrendPoint(BaseModel):
    period: str
    mean: Optional[float]
    min: Optional[float]
    max: Optional[float]
    count: int


class TrendSeries(BaseModel):
    metric: str
    baselineMean: Optional[float]
    points: list[TrendPoint]


class TrendsResponse(BaseModel):
    range: str
    isExperimental: bool = True
    series: list[TrendSeries]


@router.get("/trends", response_model=TrendsResponse)
def get_trends(
    range: str = Query(default="daily", description="daily|weekly|monthly"),
    metric: Optional[str] = Query(default=None, description="restrict to one metric"),
) -> TrendsResponse:
    if range not in _RANGE_RULE:
        raise HTTPException(status_code=422, detail="range must be daily, weekly, or monthly")

    metrics = [metric] if metric else list(NUMERIC_METRICS)
    for m in metrics:
        if m not in NUMERIC_METRICS:
            raise HTTPException(status_code=422, detail=f"unknown metric '{m}'")

    rule = _RANGE_RULE[range]
    series: list[TrendSeries] = []
    for m in metrics:
        rows = repo.query_measurements(metric_type=m)
        baseline = repo.get_baseline(m)
        points: list[TrendPoint] = []
        if rows:
            df = pd.DataFrame(
                {
                    "ts": pd.to_datetime([r.timestamp for r in rows], utc=True),
                    "value": [r.value for r in rows],
                }
            ).set_index("ts")
            grouped = df["value"].resample(rule)
            agg = grouped.agg(["mean", "min", "max", "count"])
            for period, row in agg.iterrows():
                points.append(
                    TrendPoint(
                        period=period.isoformat(),
                        mean=None if pd.isna(row["mean"]) else round(float(row["mean"]), 2),
                        min=None if pd.isna(row["min"]) else round(float(row["min"]), 2),
                        max=None if pd.isna(row["max"]) else round(float(row["max"]), 2),
                        count=int(row["count"]),
                    )
                )
        series.append(
            TrendSeries(
                metric=m,
                baselineMean=round(baseline.mean, 2) if baseline else None,
                points=points,
            )
        )
    return TrendsResponse(range=range, series=series)
