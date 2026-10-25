"""Scenario-transition tests for SimulatorService (Task 26, Raffy — analytics & simulation engine).

WHAT THIS FILE VERIFIES AND WHY
-------------------------------
Task 26 calls out "scenario transitions (A/B/C select, start/pause/reset state
changes)" as part of Raffy's analytics-&-simulation test scope. The HTTP side of
scenario selection and the start/pause/reset state changes are already covered by
tests/test_api_measurements_simulator.py, and determinism / per-scenario signal
shapes are covered by tests/test_simulator_service.py.

This file closes the remaining gap at the SERVICE layer — the behaviors reached
through ``SimulatorService`` directly rather than through the router:

  1. ``select_scenario`` persists each of A/B/C into the shared ``sim_state`` row
     (the transition the router's POST /scenario delegates to), and rejects an
     invalid scenario with ``ValueError`` (the guard behind the API's 422).
  2. ``select_scenario`` changes ONLY the scenario — it must not start generation
     or disturb status / cursor_ts (a scenario switch is a selection, not a run).
  3. A scenario TRANSITION actually changes what a subsequent run generates: the
     rows produced after switching to the new scenario are tagged with the new
     scenario, and switching A -> B changes the generated HR sequence (the
     transition has real downstream effect, not just a stored label).
  4. The reset state-change preserves the selected scenario while clearing the
     run (complements test_simulator_service.py's reset test from the transition
     angle).

NOTE ON SCOPE (deferred to their owner)
---------------------------------------
Provider distance-ranking / emergency-routing / dispatch tests that also appear
in Task 26's raw checklist belong to maiabrunne's feature (Tasks 18–20, 25); those
services do not exist yet and are intentionally NOT tested here.

Uses the established isolated-temp-DB + importlib.reload fixture pattern: point
HEARTGUARDIAN_DB at a temp file, reload the DB + service modules so they bind to
the temp DB, then init the schema. Each test gets its own fresh DB.
"""
import importlib
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def sim_env(tmp_path, monkeypatch):
    """Fresh temp DB wired to reloaded repository + simulator modules.

    DB-isolation guarantee: HEARTGUARDIAN_DB points at a per-test temp file and
    the connection/repository/service modules are reloaded so they bind to that
    path before any query runs. No state leaks between tests.
    """
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "scenario.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import simulator as sim_mod

    importlib.reload(sim_mod)

    conn_mod.init_db()
    return sim_mod, repo_mod


def _run_from_past(repo, sim_mod, scenario, seed=42, days_back=14):
    """Set scenario+seed, seed a past cursor, run start(); return generated rows."""
    start_cursor = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    repo.update_sim_state(scenario=scenario, seed=seed, cursor_ts=start_cursor)
    sim_mod.SimulatorService().start()
    return repo.query_measurements()


def _hr_series(rows):
    return [r.value for r in rows if r.metric_type == "hr" and r.value is not None]


# --------------------------------------------------------------------------- #
# select_scenario — the A/B/C transition the router delegates to (Req 2.6)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("scenario", ["A", "B", "C"])
def test_select_scenario_persists_each_valid_choice(sim_env, scenario):
    """Each valid scenario selection is persisted to the shared sim_state row."""
    sim_mod, repo = sim_env
    state = sim_mod.SimulatorService().select_scenario(scenario)

    assert state.scenario == scenario
    # And it is durably readable by anyone else holding the same DB.
    assert repo.get_sim_state().scenario == scenario


def test_select_scenario_rejects_invalid(sim_env):
    """An unknown scenario raises ValueError (the guard behind the API 422)."""
    sim_mod, _ = sim_env
    with pytest.raises(ValueError):
        sim_mod.SimulatorService().select_scenario("Z")


def test_select_scenario_is_selection_only_no_generation_or_status_change(sim_env):
    """Selecting a scenario must not start a run or disturb status/cursor.

    A scenario switch is a selection, not a transition into 'running'. It should
    leave the session status and cursor untouched and generate nothing.
    """
    sim_mod, repo = sim_env
    before = repo.get_sim_state()

    state = sim_mod.SimulatorService().select_scenario("C")

    assert state.scenario == "C"
    assert state.status == before.status          # status unchanged by selection
    assert state.cursor_ts == before.cursor_ts    # cursor unchanged (still fresh)
    assert repo.count_measurements() == 0         # no data generated


# --------------------------------------------------------------------------- #
# Transition has real downstream effect on generation (Req 2.6 + 2.9)
# --------------------------------------------------------------------------- #

def test_transition_tags_subsequent_rows_with_new_scenario(sim_env):
    """After switching scenarios and running, generated rows carry the new tag.

    Reset between runs clears the prior run so the only rows present are those of
    the scenario active at generation time — proving the transition took effect
    for the engine, not just as a stored label.
    """
    sim_mod, repo = sim_env

    rows_a = _run_from_past(repo, sim_mod, "A")
    assert rows_a and all(r.scenario == "A" for r in rows_a)

    # Transition A -> C, with a reset so the new run starts clean.
    sim_mod.SimulatorService().reset()
    rows_c = _run_from_past(repo, sim_mod, "C")

    assert rows_c and all(r.scenario == "C" for r in rows_c)


def test_transition_a_to_b_changes_generated_hr_sequence(sim_env):
    """Switching A -> B at the same seed changes the HR output.

    Same seed, same window — only the scenario differs — so a different HR series
    confirms the transition actually drives generation (Scenario B's upward HR
    drift vs. Scenario A's flat baseline), not just a cosmetic label change.
    """
    sim_mod, repo = sim_env

    hr_a = _hr_series(_run_from_past(repo, sim_mod, "A", seed=5))

    sim_mod.SimulatorService().reset()
    hr_b = _hr_series(_run_from_past(repo, sim_mod, "B", seed=5))

    assert hr_a, "scenario A should have produced HR readings"
    assert hr_b, "scenario B should have produced HR readings"
    assert hr_a != hr_b, "A->B transition must change the generated HR sequence"


# --------------------------------------------------------------------------- #
# Reset state-change preserves the selected scenario (Req 2.7) — transition view
# --------------------------------------------------------------------------- #

def test_reset_preserves_selected_scenario_across_the_state_change(sim_env):
    """Reset clears the run and returns to 'paused' but keeps the scenario.

    This is the transition guarantee that lets a user reset a demo and re-run the
    SAME scenario from a clean slate without re-selecting it.
    """
    sim_mod, repo = sim_env
    _run_from_past(repo, sim_mod, "B", seed=9)
    assert repo.count_measurements() > 0

    state = sim_mod.SimulatorService().reset()

    assert state.status == "paused"
    assert state.cursor_ts is None
    assert state.scenario == "B"            # selection survives the reset transition
    assert repo.count_measurements() == 0   # run cleared
