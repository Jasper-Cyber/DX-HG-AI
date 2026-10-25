"""Lightweight dataclasses mirroring the core DB rows.

These are plain data carriers used between the repository layer and services.
API request/response schemas (Pydantic) live with the routers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

MetricType = Literal["hr", "hrv", "spo2", "rhythm", "activity", "sleep", "vo2max"]
Quality = Literal["ok", "low", "missing"]
Scenario = Literal["A", "B", "C"]
SeverityBand = Literal["info", "review", "attention"]
AlertState = Literal["normal", "trend_review", "attention"]
FindingType = Literal[
    "persistent_shift", "combination", "rhythm_irregularity", "data_quality"
]


@dataclass(slots=True)
class Measurement:
    timestamp: str
    metric_type: MetricType
    value: Optional[float]
    quality: Quality = "ok"
    scenario: Scenario = "A"
    is_synthetic: bool = True
    id: Optional[int] = None
    user_id: int = 1


@dataclass(slots=True)
class Baseline:
    metric_type: MetricType
    mean: float
    std: float
    sample_count: int
    computed_at: str
    id: Optional[int] = None
    user_id: int = 1


@dataclass(slots=True)
class AnomalyFinding:
    metric_type: MetricType
    finding_type: FindingType
    severity_band: SeverityBand
    window_start: str
    window_end: str
    supporting: str  # JSON text
    deviation: Optional[float] = None
    created_at: Optional[str] = None
    id: Optional[int] = None
    user_id: int = 1


@dataclass(slots=True)
class Alert:
    state: AlertState
    title: str
    explanation: str
    next_steps: str
    finding_ids: str  # JSON array text
    is_experimental: bool = True
    created_at: Optional[str] = None
    id: Optional[int] = None
    user_id: int = 1


@dataclass(slots=True)
class SimState:
    scenario: Scenario
    status: Literal["running", "paused"]
    seed: int
    cursor_ts: Optional[str]
    updated_at: str
    id: int = 1
