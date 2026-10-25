"""SensorAdapter interface + SimulatedSensorAdapter (Task 7, Raffy — analytics & simulation engine).

PURPOSE
-------
HeartGuardian AI charts, baselines, and alerts on *readings*. Those readings have
to come from *somewhere* — in the MVP a software simulator, but in a future
iteration a real wearable (Apple Health, Android Health Connect, a Bluetooth LE
sensor). This module defines the single seam the rest of the app reads readings
through — the ``SensorAdapter`` protocol — and ships the only concrete
implementation the MVP needs: ``SimulatedSensorAdapter``.

WHY A PLUGGABLE ADAPTER (Req 6)
-------------------------------
Requirement 6 asks for a *pluggable sensor interface* so future data sources can
be added "without rewriting the app". We express that as a ``typing.Protocol``:
anything that satisfies the small, documented surface below is usable as a data
source, with no base class to inherit and no registry to wire up. Consumers depend
on the protocol, not on any concrete adapter, so swapping the simulator for a real
device later is a matter of constructing a different adapter — the consuming code
is untouched. The future device adapters live (interface-only) in
``sensor_stubs.py``; this file owns the contract and the simulated implementation.

WHY NO REAL HARDWARE IS NEEDED (Req 6.4)
----------------------------------------
``SimulatedSensorAdapter`` sources its readings from the data the Task 6
``SimulatorService`` persists through the repository. The simulator is pure
software, so the full MVP data path — generate → persist → read-through-adapter —
runs with no device, no Bluetooth, and no paid API. The adapter does not itself
generate data; it *reads* what the simulator produced, keeping a single source of
truth (the repository) and a clean separation between "produce readings" (the
service) and "expose readings as a sensor" (this adapter).

PROTOCOL SURFACE
----------------
The interface is deliberately minimal and cohesive — just what a reading consumer
needs from any data source, real or simulated:

    is_available() -> bool
        Whether this source can currently supply readings. The simulated source is
        always available; real adapters would report permission/pairing state.

    read_latest(metric_type=None) -> list[Measurement]
        The most recent reading(s). With no metric it returns the latest reading
        for each metric type; with a metric it returns that metric's latest (a list
        of zero or one) so the return type is uniform.

    read(metric_type=None, start=None, end=None, limit=None) -> list[Measurement]
        A time-ranged history query, ordered oldest-first. Mirrors the repository's
        filter surface so adapters can map straight onto their native store.

Both reads return the shared ``Measurement`` dataclass (``app.db.models``) so every
data source speaks the same vocabulary to the rest of the app.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ..db import repository as repo
from ..db.connection import DEMO_USER_ID
from ..db.models import Measurement, MetricType


@runtime_checkable
class SensorAdapter(Protocol):
    """The pluggable data-source contract every reading source must satisfy (Req 6.1).

    This is a structural (duck-typed) protocol, not a base class: any object that
    provides these three methods *is* a ``SensorAdapter``, with nothing to inherit.
    It is ``@runtime_checkable`` so tests (and defensive runtime code) can assert
    conformance with ``isinstance(obj, SensorAdapter)``.

    NOTE: ``@runtime_checkable`` only checks that the method *names* exist, not their
    signatures — it is a conformance smoke test, not a full type guarantee. Static
    type checking still enforces the signatures below.
    """

    def is_available(self) -> bool:
        """Return True when this source can currently supply readings."""
        ...

    def read_latest(
        self, metric_type: Optional[MetricType] = None
    ) -> list[Measurement]:
        """Return the most recent reading(s).

        With no ``metric_type``, return the latest reading for each metric type.
        With a ``metric_type``, return that metric's latest as a list of zero or one
        element, so the return shape is always a list.
        """
        ...

    def read(
        self,
        metric_type: Optional[MetricType] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Measurement]:
        """Return a time-ranged history of readings, ordered oldest-first."""
        ...


# The supported metric types, mirrored from the simulator so read_latest() with no
# metric can iterate them. Kept local (not imported from the service) so this
# adapter does not depend on the service module just for a constant.
_METRICS: tuple[MetricType, ...] = ("hr", "hrv", "spo2", "rhythm", "activity", "sleep", "vo2max")


class SimulatedSensorAdapter:
    """The MVP's concrete data source: readings produced by the simulator (Req 6.2, 6.4).

    ROLE
    ----
    Exposes the synthetic readings that ``SimulatorService`` (Task 6) persists via
    the repository as if they came off a sensor. It is the read-side counterpart to
    the service's write-side: the service *generates and stores* readings; this
    adapter *reads them back* through the same repository, so there is a single
    source of truth and no duplicated data path.

    This adapter conforms to :class:`SensorAdapter` structurally — it declares no
    base class, matching the protocol by shape.

    NO HARDWARE REQUIRED (Req 6.4)
    ------------------------------
    Every method is a thin, read-only query over the repository. There is no device,
    no pairing, no network — so :meth:`is_available` is unconditionally True and the
    full MVP runs on synthetic data alone.

    DEPENDENCY-LIGHT CONSTRUCTION
    -----------------------------
    Constructible with no arguments (``SimulatedSensorAdapter()``). An optional
    ``user_id`` scopes the reads to a user, defaulting to the single demo user, so
    the adapter stays usable in the single-user MVP without any wiring.
    """

    def __init__(self, user_id: int = DEMO_USER_ID) -> None:
        self.user_id = user_id

    def is_available(self) -> bool:
        """Always available — the simulated source needs no hardware (Req 6.4)."""
        return True

    def read_latest(
        self, metric_type: Optional[MetricType] = None
    ) -> list[Measurement]:
        """Latest reading(s) from the simulator's persisted data.

        With a specific ``metric_type`` return that metric's most recent reading as
        a zero-or-one-element list. With no metric, return the latest reading for
        each of the six metric types (metrics with no data yet are simply absent).
        """
        if metric_type is not None:
            latest = repo.latest_measurement(metric_type, user_id=self.user_id)
            return [latest] if latest is not None else []

        results: list[Measurement] = []
        for metric in _METRICS:
            latest = repo.latest_measurement(metric, user_id=self.user_id)
            if latest is not None:
                results.append(latest)
        return results

    def read(
        self,
        metric_type: Optional[MetricType] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Measurement]:
        """Time-ranged history from the simulator's persisted data (oldest-first).

        Delegates straight to the repository's ``query_measurements``; the start/end
        bounds are inclusive and results are ordered by timestamp ascending, exactly
        as the repository defines.
        """
        return repo.query_measurements(
            metric_type=metric_type,
            start=start,
            end=end,
            user_id=self.user_id,
            limit=limit,
        )
