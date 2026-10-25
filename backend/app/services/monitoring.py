"""Single-process demo scheduler: one simulated hour per five wall-clock seconds."""
from __future__ import annotations

import asyncio
import logging
from threading import RLock

from ..db import repository as repo
from .alerts import AlertService
from .simulator import SimulatorService

INTERVAL_SECONDS = 5
INITIAL_STEPS = 24 * 21
lock = RLock()


def refresh():
    with lock:
        has_readings = repo.count_measurements() > 0
        if not has_readings:
            repo.clear_current_analysis()
        return AlertService().evaluate_and_store(run_analysis=has_readings)


def control(action: str):
    with lock:
        sim = SimulatorService()
        state = repo.get_sim_state()
        if action == "start":
            if state.status != "running":
                sim.advance(INITIAL_STEPS if state.cursor_ts is None else 1)
                refresh()
                repo.update_sim_state(status="running")
        elif action == "pause":
            sim.pause()
        elif action == "reset":
            sim.reset()
            refresh()
        else:
            raise ValueError("Unknown simulator action")
        return repo.get_sim_state()


def select_scenario(scenario: str):
    with lock:
        state = repo.get_sim_state()
        if state.scenario == scenario:
            return state
        sim = SimulatorService()
        # A new scenario is a fresh run; prior alerts remain in history.
        sim.reset()
        sim.select_scenario(scenario)
        if state.status == "running":
            return control("start")
        refresh()
        return repo.get_sim_state()


def tick():
    with lock:
        if repo.get_sim_state().status == "running":
            SimulatorService().advance()
            refresh()


async def run(stop: asyncio.Event):
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            try:
                await asyncio.to_thread(tick)
            except Exception:
                logging.getLogger(__name__).exception("Simulator update failed; pausing")
                with lock:
                    repo.update_sim_state(status="paused")
