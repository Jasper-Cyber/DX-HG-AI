"""Simulator controls: serialized generation, analysis, and scenario transitions."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import repository as repo
from ..db.models import SimState

router = APIRouter(tags=["simulator"])


class SimStateOut(BaseModel):
    scenario: str
    status: str
    seed: int
    cursorTs: Optional[str]
    updatedAt: str

    @classmethod
    def from_model(cls, s: SimState) -> "SimStateOut":
        return cls(
            scenario=s.scenario,
            status=s.status,
            seed=s.seed,
            cursorTs=s.cursor_ts,
            updatedAt=s.updated_at,
        )


class ScenarioIn(BaseModel):
    scenario: Literal["A", "B", "C"]


@router.get("/scenario", response_model=SimStateOut)
def get_scenario() -> SimStateOut:
    return SimStateOut.from_model(repo.get_sim_state())


@router.post("/scenario", response_model=SimStateOut)
def set_scenario(body: ScenarioIn) -> SimStateOut:
    from ..services.monitoring import select_scenario

    return SimStateOut.from_model(select_scenario(body.scenario))


@router.post("/simulator/{action}", response_model=SimStateOut)
def control_simulator(action: str) -> SimStateOut:
    from ..services.monitoring import control

    if action not in {"start", "pause", "reset"}:
        raise HTTPException(status_code=422, detail="action must be start, pause, or reset")
    return SimStateOut.from_model(control(action))
