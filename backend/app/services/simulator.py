"""Deterministic synthetic readings for six hourly metrics plus daily VO2 max and scenarios A/B/C.

The HTTP simulator uses ``advance`` through services.monitoring: a fresh run
creates demo history, then a lifespan worker appends hourly ticks on an accelerated
clock. The persisted cursor prevents replay on resume; the first reading anchors
run-relative drift so chunking does not change the generated signal.

``generate`` is the fixed-count, fixed-epoch API used by the seed script and for
reproducible standalone datasets. ``start`` is the legacy wall-clock backfill API.
Neither creates its own timer. ``pause`` and ``reset`` update persisted state;
reset clears current readings and analysis while retaining historical alerts.

Randomness is seeded per tick from (seed, scenario, absolute tick index).
These values exercise the prototype and are not clinically calibrated.
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

    def advance(self, steps: int = 1) -> SimState:
        """Append simulated hours, preserving the cursor and run-relative drift."""
        state = repo.get_sim_state()
        existing = repo.query_measurements(user_id=self.user_id, limit=1)
        anchor = self._parse_iso(existing[0].timestamp) if existing else self._EPOCH_ANCHOR
        start = self._parse_iso(state.cursor_ts) if state.cursor_ts else anchor
        rows, cursor = self._generate_batch(
            scenario=state.scenario, seed=state.seed, start_ts=start,
            until=start + steps * TICK, run_anchor_index=self._tick_index(anchor),
        )
        if rows:
            repo.insert_measurements(rows)
            return repo.update_sim_state(cursor_ts=cursor.isoformat())
        return state

    def start(self) -> SimState:
        """Mark the session running and generate a batch of readings up to now.

        A fresh session has no completed ticks and generates nothing. A resumed
        session continues from its stored cursor, capped at MAX_TICKS_PER_START.
        The HTTP demo uses advance() instead of this wall-clock backfill API.
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
        resets cursor_ts to None so the next demo start begins a fresh dataset.
        Ends in the paused state. (Req 2.7)
        """
        repo.clear_measurements(user_id=self.user_id)
        repo.clear_current_analysis(user_id=self.user_id)
        # Return to the beginning of the selected scenario.
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
        if ts.hour == 0:
            rows.append(self._vo2_reading(ts, scenario, seed, run_offset))
        return rows

    def _vo2_reading(self, ts: datetime, scenario: str, seed: int, run_offset: int) -> Measurement:
        """Standalone daily synthetic VO2 max; not inferred from HR or SpO2.

        An independent RNG leaves all pre-existing hourly metric sequences intact.
        The values and gradual drift exist only to demonstrate trend charts.
        """
        rng = self._tick_rng(seed + 7919, scenario, self._tick_index(ts))
        days = max(0, run_offset) / 24
        drift = (-0.035 if scenario == "B" else 0.025) * days
        value = round(float(np.clip(48.0 + drift + rng.normal(0, 0.65), 15, 80)), 2)
        quality, value = self._apply_quality(value, rng)
        return Measurement(timestamp=ts.isoformat(), metric_type="vo2max", value=value,
                           quality=quality, scenario=scenario, is_synthetic=True, user_id=self.user_id)

    def backfill_vo2(self) -> int:
        """Upgrade existing synthetic demo history without replacing any readings."""
        history = repo.query_measurements(metric_type="hr", user_id=self.user_id)
        if not history:
            return 0
        existing = {self._parse_iso(r.timestamp).astimezone(timezone.utc).isoformat()
                    for r in repo.query_measurements(metric_type="vo2max", user_id=self.user_id)}
        anchor = self._tick_index(self._parse_iso(history[0].timestamp))
        seed = repo.get_sim_state().seed
        rows = []
        for reading in history:
            ts = self._parse_iso(reading.timestamp).astimezone(timezone.utc)
            if reading.is_synthetic and ts.hour == 0 and ts.isoformat() not in existing:
                rows.append(self._vo2_reading(ts, reading.scenario, seed, self._tick_index(ts) - anchor))
                existing.add(ts.isoformat())
        return repo.insert_measurements(rows)

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
