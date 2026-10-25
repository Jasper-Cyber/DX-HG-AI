"""Scenario + simulator control endpoints (Task 8).

This router owns the simulator *session state* (the single `sim_state` row):
selecting a scenario and the start / pause / reset transitions. The actual
data *generation* is provided by SimulatorService (Task 6, Raffy); this router
calls into it through a small, optional seam so the two tasks integrate without
either side blocking the other.

Until SimulatorService is wired in, the control endpoints still work: they
update persisted state and return it, and Reset clears generated readings.
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import repository as repo
from ..db.models import SimState

router = APIRouter(tags=["simulator"])

_VALID_SCENARIOS = {"A", "B", "C"}


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
    if body.scenario not in _VALID_SCENARIOS:
        raise HTTPException(status_code=422, detail="scenario must be one of A, B, C")
    state = repo.update_sim_state(scenario=body.scenario)
    return SimStateOut.from_model(state)


@router.post("/simulator/{action}", response_model=SimStateOut)
def control_simulator(action: str) -> SimStateOut:
    """Start, pause, or reset the simulator session.

    - start: mark the session running (SimulatorService generation hook).
    - pause: mark the session paused.
    - reset: clear generated readings and return to the selected scenario's start.
    """
    if action not in {"start", "pause", "reset"}:
        raise HTTPException(status_code=422, detail="action must be start, pause, or reset")

    if action == "start":
        state = repo.update_sim_state(status="running")
        _maybe_start_generation(state)
    elif action == "pause":
        state = repo.update_sim_state(status="paused")
        _maybe_pause_generation(state)
    else:  # reset
        repo.clear_measurements()
        state = repo.update_sim_state(status="paused", cursor_ts=None)
        _maybe_reset_generation(state)

    return SimStateOut.from_model(state)


# --------------------------------------------------------------------------- #
# Integration seam for SimulatorService (Task 6, Raffy).
#
# When the service lands, import it here and call it from these hooks. Keeping
# the hooks optional means this router works today and gains live generation
# the moment the service is available — no endpoint changes required.
# --------------------------------------------------------------------------- #

def _get_simulator():  # pragma: no cover - thin optional import
    try:
        from ..services.simulator import SimulatorService  # type: ignore

        return SimulatorService()
    except Exception:
        return None


# Number of readings generated per Start, so the dashboard has data immediately.
_START_BATCH_STEPS = 168  # ~1 week at hourly cadence


def _maybe_start_generation(state: SimState) -> None:  # pragma: no cover
    sim = _get_simulator()
    if sim is None:
        return
    # Generate a batch for the currently selected scenario/seed.
    if hasattr(sim, "generate"):
        sim.generate(steps=_START_BATCH_STEPS, scenario=state.scenario, seed=state.seed)


def _maybe_pause_generation(state: SimState) -> None:  # pragma: no cover
    sim = _get_simulator()
    if sim is not None and hasattr(sim, "pause"):
        sim.pause()


def _maybe_reset_generation(state: SimState) -> None:  # pragma: no cover
    sim = _get_simulator()
    if sim is not None and hasattr(sim, "reset"):
        sim.reset()
