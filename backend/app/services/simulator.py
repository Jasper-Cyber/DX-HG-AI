"""Wearable physiological data simulator (Task 6, Raffy — analytics & simulation engine).

PURPOSE
-------
This module generates the *synthetic* physiological time-series that the rest of
HeartGuardian AI consumes. There is no real hardware in the MVP; every reading the
app charts, baselines, and alerts on originates here. The service produces readings
for all six metric types (HR, HRV, SpO2, rhythm flag, activity, sleep) under three
selectable scenarios and persists them through the repository layer. (Req 2.1, 2.9)

INTEGRATION CONTRACT (with the Task 8 router, backend/app/routers/simulator.py)
------------------------------------------------------------------------------
The control router owns the simulator *session state* (the single ``sim_state`` row)
and calls this service through an optional seam:

    from ..services.simulator import SimulatorService
    sim = SimulatorService()   # MUST be constructible with no arguments
    sim.start()                # POST /simulator/start
    sim.pause()                # POST /simulator/pause
    sim.reset()                # POST /simulator/reset

So ``SimulatorService()`` takes no args and exposes ``start() / pause() / reset()``.
``select_scenario(scenario)`` is also provided for Scenario-select (Req 2.6). The
router persists its own status transitions too; this service reads and writes the
same ``sim_state`` row via the repository, so both sides stay consistent and
idempotent. This service never touches the router or the repository internals — it
only calls the public repository functions.

DESIGN: ON-DEMAND BATCH GENERATION (no background threads/timers)
-----------------------------------------------------------------
A hackathon demo should be deterministic and thread-free. Instead of a timer that
drips readings in real time, ``start()`` synchronously generates a *batch* of ticks
that advance ``cursor_ts`` from where it left off up to "now", then marks the session
running. This keeps generation reproducible and easy to test.

- ``start()``  : mark running; generate a batch of ticks from the stored cursor up to
                 "now"; persist readings; advance cursor_ts. On a fresh/reset session
                 (cursor_ts is None) the cursor is seeded to the current tick boundary,
                 so a first ``start()`` with no elapsed time generates nothing and the
                 session fills in as time advances (or as a caller seeds cursor_ts into
                 the past to backfill a demo history).
- ``pause()``  : mark paused; generate nothing.
- ``reset()``  : clear generated readings, reset cursor_ts to None, keep the selected
                 scenario, and return to the paused start state (Req 2.7).
- ``select_scenario(s)`` : persist the chosen scenario (A/B/C) (Req 2.6).

SCENARIO B DRIFT IS RUN-RELATIVE
--------------------------------
Scenario B's trend is measured from the *run's first generated tick*, not from an
absolute epoch, so "over simulated weeks" means weeks since the run began. The run
anchor is derived deterministically from the start cursor, keeping B reproducible
while the per-tick RNG still keys on the absolute tick index.

REPRODUCIBILITY (Req 2.8)
-------------------------
Randomness comes from ``numpy.random.default_rng``. Crucially, the RNG is re-seeded
*per tick* from a deterministic combination of (seed, scenario, tick-index), not from
one long-lived generator. That makes the k-th reading in a run depend only on the seed
and scenario — never on how the batch happened to be chunked across multiple
``start()`` calls. Same seed + same scenario => byte-identical sequences.

KNOWN LIMITATIONS / ASSUMPTIONS
-------------------------------
- Tick cadence is a fixed simulated hour (``TICK``). Scenario B's "over simulated
  weeks" drift is expressed across the tick index, so a batch that spans many ticks
  shows the trend; a tiny batch shows only its beginning.
- "now" is real wall-clock UTC; on a fresh session we seed cursor_ts to a window in
  the past (``INITIAL_HISTORY``) so there is immediately some history to analyze.
- The physiological numbers are plausible-looking, not clinically calibrated. They
  exist to exercise the analysis/alert pipeline, not to model real cardiology.
- A hard cap (``MAX_TICKS_PER_START``) bounds how much a single ``start()`` generates
  so an idle session that is resumed much later cannot create an unbounded batch.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

from ..db import repository as repo
from ..db.connection import DEMO_USER_ID
from ..db.models import Measurement, SimState

# --------------------------------------------------------------------------- #
# Generation constants.
#
# These are intentionally module-level so the behavior is transparent and the
# tests can reason about it. TICK is the simulated spacing between readings;
# INITIAL_HISTORY is how far back a fresh/reset session starts so there is data
# to analyze immediately; MAX_TICKS_PER_START bounds a single batch.
# --------------------------------------------------------------------------- #
TICK = timedelta(hours=1)
MAX_TICKS_PER_START = 24 * 28                 # cap one batch at ~4 weeks of hourly ticks

# The six metric types, in a fixed order so a tick's rows are deterministic.
_METRICS = ("hr", "hrv", "spo2", "rhythm", "activity", "sleep")

# Per-metric "personal baseline" (mean, std) used by Scenario A and as the
# starting point for Scenario B's drift. Values are plausible resting ranges.
_BASELINE = {
    "hr": (62.0, 3.0),        # bpm
    "hrv": (55.0, 6.0),       # ms (RMSSD-ish)
    "spo2": (97.5, 0.6),      # %
    "activity": (5500.0, 1200.0),  # steps/day proxy per tick
    "sleep": (7.4, 0.5),      # hours (nightly proxy)
}

# Physiological clamps so synthetic noise never produces impossible values.
_CLAMP = {
    "hr": (35.0, 180.0),
    "hrv": (10.0, 120.0),
    "spo2": (88.0, 100.0),
    "activity": (0.0, 20000.0),
    "sleep": (0.0, 12.0),
}

# Rate at which a tick's sample is degraded to low/missing quality. Small so the
# bulk of data is usable but the data-quality path is still exercised (Req 3.4).
_LOW_QUALITY_RATE = 0.04
_MISSING_RATE = 0.03


class SimulatorService:
    """Generates and persists synthetic readings for scenarios A/B/C.

    Constructible with no arguments (router contract). All session state lives in
    the ``sim_state`` row via the repository, so the service itself is stateless
    between calls and safe to re-instantiate per request.
    """

    def __init__(self, user_id: int = DEMO_USER_ID) -> None:
        self.user_id = user_id

    # ------------------------------------------------------------------ #
    # Public control API (router seam).
    # ------------------------------------------------------------------ #
    def select_scenario(self, scenario: str) -> SimState:
        """Persist the chosen scenario (A/B/C) without generating data (Req 2.6)."""
        if scenario not in ("A", "B", "C"):
            raise ValueError("scenario must be one of A, B, C")
        return repo.update_sim_state(scenario=scenario)

    # Fixed anchor for the count-based generate() API: makes output depend only on
    # (scenario, seed, steps), never on wall-clock time, so it is reproducible.
    _EPOCH_ANCHOR = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def generate(
        self,
        *,
        steps: int,
        scenario=None,
        seed=None,
        persist: bool = True,
    ) -> "list[Measurement]":
        """Generate ``steps`` hourly ticks of synthetic readings (compatibility API).

        Public batch-generation entry point used by the scenario/simulator router
        seam, the seed script, and tests. Thin deterministic wrapper over the
        internal ``_generate_batch``: callers request a fixed number of ticks
        without managing cursor_ts. ``scenario``/``seed`` default to the persisted
        sim_state when omitted (and are persisted when provided). Output depends
        only on (scenario, seed, steps) via a fixed epoch anchor (Req 2.8). With
        ``persist=True`` rows are written and the session marked running; with
        ``persist=False`` nothing is written. Returns the generated Measurement rows.
        """
        state = repo.get_sim_state()
        scenario = scenario or state.scenario
        seed = state.seed if seed is None else seed
        if persist and (scenario != state.scenario or seed != state.seed):
            repo.update_sim_state(scenario=scenario, seed=seed)

        start_ts = self._floor_to_tick(self._EPOCH_ANCHOR)
        until = start_ts + max(0, int(steps)) * TICK
        rows, next_cursor = self._generate_batch(
            scenario=scenario,
            seed=seed,
            start_ts=start_ts,
            until=until,
            run_anchor_index=self._tick_index(start_ts),
        )
        if persist and rows:
            repo.insert_measurements(rows)
            repo.update_sim_state(
                status="running",
                cursor_ts=(next_cursor.isoformat() if next_cursor else None),
            )
        return rows

    def start(self) -> SimState:
        """Mark the session running and generate a batch of readings up to now.

        On a fresh/reset session (cursor_ts is None) generation starts
        ``INITIAL_HISTORY`` in the past so the app immediately has history. On a
        resumed session it continues from the stored cursor. The batch is capped
        at ``MAX_TICKS_PER_START`` ticks. (Req 2.6)
        """
        state = repo.get_sim_state()

        start_ts = self._resolve_start_cursor(state)
        # Cap generation at the current tick boundary. Generating only whole,
        # completed ticks keeps timestamps aligned and means a fresh start() at
        # "now" (start_ts == floor(now)) produces zero rows — nothing to backfill
        # until at least one full tick has elapsed.
        until = self._floor_to_tick(self._now())

        rows, next_cursor = self._generate_batch(
            scenario=state.scenario,
            seed=state.seed,
            start_ts=start_ts,
            until=until,
            run_anchor_index=self._tick_index(start_ts),
        )
        if rows:
            repo.insert_measurements(rows)
            # Advance the cursor only when we actually produced ticks. If nothing
            # was generated (a fresh start() with no elapsed full tick), leave
            # cursor_ts untouched — there is nothing to advance, and keeping it at
            # its prior value (NULL on a fresh session) preserves the reset path's
            # ability to return to the clean, cursor-less start state.
            return repo.update_sim_state(
                status="running", cursor_ts=next_cursor.isoformat()
            )

        return repo.update_sim_state(status="running")

    def pause(self) -> SimState:
        """Mark the session paused; generate nothing (Req 2.6)."""
        return repo.update_sim_state(status="paused")

    def reset(self) -> SimState:
        """Clear generated readings and return to the scenario's start state.

        Keeps the selected scenario and seed, drops all readings for the user, and
        resets cursor_ts to None so the next ``start()`` begins a fresh run from the
        seeded history window. Ends in the paused state. (Req 2.7)
        """
        repo.clear_measurements(user_id=self.user_id)
        # cursor_ts cannot be set back to NULL through update_sim_state's patch
        # semantics (None means "leave unchanged"), so reset it explicitly.
        self._reset_cursor_to_null()
        return repo.update_sim_state(status="paused")

    # ------------------------------------------------------------------ #
    # Batch generation.
    # ------------------------------------------------------------------ #
    def _generate_batch(
        self,
        *,
        scenario: str,
        seed: int,
        start_ts: datetime,
        until: datetime,
        run_anchor_index: int,
    ) -> tuple[list[Measurement], Optional[datetime]]:
        """Produce readings for every tick in [start_ts, until), capped.

        ``run_anchor_index`` is the absolute tick index of the run's first tick; it
        anchors Scenario B's drift so the trend is relative to the run, not the Unix
        epoch. Returns the rows and the next cursor (first tick not yet generated),
        or None if nothing was produced.
        """
        rows: list[Measurement] = []
        ts = start_ts
        tick_index = self._tick_index(start_ts)
        produced = 0
        next_cursor: Optional[datetime] = None

        while ts < until and produced < MAX_TICKS_PER_START:
            rows.extend(
                self._generate_tick(scenario, seed, tick_index, run_anchor_index, ts)
            )
            ts = ts + TICK
            tick_index += 1
            produced += 1
            next_cursor = ts

        return rows, next_cursor

    def _generate_tick(
        self,
        scenario: str,
        seed: int,
        tick_index: int,
        run_anchor_index: int,
        ts: datetime,
    ) -> list[Measurement]:
        """Generate the six-metric rows for a single simulated tick.

        A per-tick RNG keyed by (seed, scenario, tick_index) guarantees the k-th
        reading depends only on seed+scenario, independent of batch chunking
        (Req 2.8). Each metric row is tagged with the active scenario and marked
        synthetic (Req 2.9).
        """
        rng = self._tick_rng(seed, scenario, tick_index)
        iso = ts.isoformat()
        rows: list[Measurement] = []
        run_offset = tick_index - run_anchor_index  # ticks since the run began

        for metric in _METRICS:
            value = self._metric_value(metric, scenario, run_offset, rng)
            quality, value = self._apply_quality(value, rng)
            rows.append(
                Measurement(
                    timestamp=iso,
                    metric_type=metric,
                    value=value,
                    quality=quality,
                    scenario=scenario,
                    is_synthetic=True,
                    user_id=self.user_id,
                )
            )
        return rows

    # ------------------------------------------------------------------ #
    # Scenario generation logic.
    #
    # Each metric's value is a function of (baseline, scenario drift, noise). The
    # noise is drawn from the per-tick RNG so it is reproducible.
    # ------------------------------------------------------------------ #
    def _metric_value(
        self, metric: str, scenario: str, run_offset: int, rng: np.random.Generator
    ) -> Optional[float]:
        """Dispatch to the right signal shape for the metric + scenario.

        ``run_offset`` is the number of ticks since the run began; Scenario B's drift
        and Scenario C's burst pattern are expressed against it so they are relative
        to the run rather than to absolute wall-clock time.
        """
        if metric == "rhythm":
            return self._rhythm_flag(scenario, run_offset, rng)

        mean, std = _BASELINE[metric]
        base = float(rng.normal(mean, std))

        # Scenario B applies a slow drift over the run ("simulated weeks").
        if scenario == "B":
            base += self._scenario_b_drift(metric, run_offset)

        low, high = _CLAMP[metric]
        return float(np.clip(base, low, high))

    def _scenario_b_drift(self, metric: str, run_offset: int) -> float:
        """Scenario B — Gradual Deviation (Req 2.4).

        Resting HR trends UP, HRV trends DOWN, and sleep DECLINES over simulated
        weeks. The drift is linear in the number of simulated *days since the run
        began* so it is only clearly visible across a multi-week batch, matching
        "over simulated weeks". Other metrics stay on their Scenario-A baseline.
        """
        days = (run_offset * TICK) / timedelta(days=1)
        if metric == "hr":
            return +0.45 * days      # HR rises ~0.45 bpm/day
        if metric == "hrv":
            return -0.40 * days      # HRV falls ~0.40 ms/day
        if metric == "sleep":
            return -0.03 * days      # sleep declines ~0.03 h/day
        return 0.0

    def _rhythm_flag(
        self, scenario: str, run_offset: int, rng: np.random.Generator
    ) -> float:
        """Rhythm flag: 0.0 = regular, 1.0 = irregular.

        Scenario C — Rhythm Irregularity (Req 2.5) injects a markedly higher rate of
        irregular flags, with a periodic burst pattern so the irregularity looks
        clustered (as real paroxysmal episodes tend to) rather than uniform noise.
        Scenarios A and B emit only a low background rate of irregular flags.
        """
        if scenario == "C":
            # Clustered bursts: elevated probability in a recurring window of ticks,
            # low otherwise. This yields clearly irregular stretches for the detector.
            in_burst = (run_offset % 12) < 4
            p_irregular = 0.55 if in_burst else 0.10
        else:
            p_irregular = 0.01
        return 1.0 if rng.random() < p_irregular else 0.0

    def _apply_quality(
        self, value: Optional[float], rng: np.random.Generator
    ) -> tuple[str, Optional[float]]:
        """Occasionally degrade a sample to low/missing quality.

        - missing : value dropped to None, quality='missing'.
        - low     : value kept but flagged quality='low' (noisier/less trustworthy).
        Draws come from the same per-tick RNG so degradation is reproducible. This
        feeds the engine's data-quality handling (Req 3.4) and the dashboard's
        explicit no-data state (Req 1.6).
        """
        roll = rng.random()
        if roll < _MISSING_RATE:
            return "missing", None
        if roll < _MISSING_RATE + _LOW_QUALITY_RATE:
            return "low", value
        return "ok", value

    # ------------------------------------------------------------------ #
    # RNG seeding (reproducibility, Req 2.8).
    # ------------------------------------------------------------------ #
    @staticmethod
    def _tick_rng(seed: int, scenario: str, tick_index: int) -> np.random.Generator:
        """Deterministic per-tick generator.

        np.random.SeedSequence mixes the base seed, a per-scenario salt, and the
        tick index into independent, high-quality streams. Because the stream for
        tick k is fixed, the sequence is identical no matter how ``start()`` chunks
        the batch across calls.
        """
        scenario_salt = {"A": 1, "B": 2, "C": 3}[scenario]
        ss = np.random.SeedSequence([int(seed), scenario_salt, int(tick_index)])
        return np.random.default_rng(ss)

    # ------------------------------------------------------------------ #
    # Cursor / time helpers.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _resolve_start_cursor(self, state: SimState) -> datetime:
        """Where this batch should begin.

        Fresh/reset session (cursor_ts is None) => the current tick boundary, so a
        first ``start()`` with no elapsed time generates nothing and the session
        fills in as time advances. A caller can seed cursor_ts into the past to
        backfill a demo history. Otherwise continue from the stored cursor.

        Flooring to the tick boundary also makes generated timestamps reproducible:
        they align to whole ticks instead of carrying the sub-tick microseconds of
        whatever instant ``start()`` happened to run.
        """
        if state.cursor_ts is None:
            return self._floor_to_tick(self._now())
        return self._floor_to_tick(self._parse_iso(state.cursor_ts))

    @staticmethod
    def _floor_to_tick(ts: datetime) -> datetime:
        """Snap a timestamp down to the start of its TICK window (UTC)."""
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        whole_ticks = int((ts - epoch) / TICK)
        return epoch + whole_ticks * TICK

    @staticmethod
    def _tick_index(ts: datetime) -> int:
        """Stable tick index for a timestamp: whole ticks since the Unix epoch.

        Keying the per-tick RNG on this (rather than a per-run counter) keeps a
        given wall-clock tick reproducible across runs and batches.
        """
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return int((ts - epoch) / TICK)

    @staticmethod
    def _parse_iso(value: str) -> datetime:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _reset_cursor_to_null(self) -> None:
        """Set cursor_ts back to SQL NULL.

        update_sim_state treats None as "leave unchanged", so reset needs a direct
        write. We go through the repository's connection helper rather than embedding
        schema knowledge here, keeping SQL out of the service beyond this one-field
        reset that the patch API cannot express.
        """
        from ..db.connection import get_connection, utc_now_iso

        with get_connection() as conn:
            conn.execute(
                "UPDATE sim_state SET cursor_ts = NULL, updated_at = ? WHERE id = 1",
                (utc_now_iso(),),
            )
            conn.commit()
