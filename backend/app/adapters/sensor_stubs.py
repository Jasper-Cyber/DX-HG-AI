"""Future, interface-only sensor adapters (Task 7, Raffy — analytics & simulation engine).

PURPOSE
-------
Requirement 6.3 asks the system to *define* — interface-only, for a future
iteration — three real-device data sources: Apple Health, Android Health Connect,
and a Bluetooth LE sensor. This module holds those placeholders.

WHY THEY EXIST NOW (the pluggable-adapter rationale, Req 6)
-----------------------------------------------------------
The whole point of the ``SensorAdapter`` protocol (see ``sensor.py``) is that a new
data source can be added *without rewriting the app*. Declaring these three stubs
now proves that design: each one matches the same protocol surface as the live
``SimulatedSensorAdapter``, so the day a real integration is built, only the body of
the relevant method changes — every consumer that already reads through
``SensorAdapter`` keeps working untouched.

INTENTIONALLY UNIMPLEMENTED
---------------------------
These are *not* bugs or TODO-shaped half-implementations. They are deliberate,
documented placeholders. Their read methods raise ``NotImplementedError`` with a
clear "future adapter — not implemented in MVP" message so that any accidental use
fails loudly and unmistakably rather than silently returning empty or fake data.
``is_available()`` returns ``False`` for every stub, which is the honest answer in
the MVP: none of these sources can supply readings yet, so well-behaved consumers
that check availability first will correctly skip them. The MVP runs entirely on
``SimulatedSensorAdapter`` (Req 6.4); nothing here is exercised until the future
device-integration work lands.
"""
from __future__ import annotations

from typing import Optional

from ..db.models import Measurement, MetricType

# Shared message so every stub reports the same clear, greppable reason.
_FUTURE_MSG = "future adapter — not implemented in MVP"


class AppleHealthAdapter:
    """Interface-only placeholder for Apple HealthKit (Req 6.3 — future).

    A future iteration would read HR / HRV / SpO2 / activity / sleep from Apple
    HealthKit on iOS. It is defined now only to satisfy the pluggable-adapter
    contract; every read method is intentionally unimplemented in the MVP and
    :meth:`is_available` reports ``False`` because the source cannot supply data yet.
    """

    def is_available(self) -> bool:
        """Not available in the MVP — HealthKit integration is future work."""
        return False

    def read_latest(
        self, metric_type: Optional[MetricType] = None
    ) -> list[Measurement]:
        """Not implemented in the MVP — see module docstring (Req 6.3)."""
        raise NotImplementedError(f"AppleHealthAdapter.read_latest: {_FUTURE_MSG}")

    def read(
        self,
        metric_type: Optional[MetricType] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Measurement]:
        """Not implemented in the MVP — see module docstring (Req 6.3)."""
        raise NotImplementedError(f"AppleHealthAdapter.read: {_FUTURE_MSG}")


class HealthConnectAdapter:
    """Interface-only placeholder for Android Health Connect (Req 6.3 — future).

    A future iteration would read the physiological metrics from Android's Health
    Connect store. Defined now only to satisfy the pluggable-adapter contract; the
    read methods are intentionally unimplemented in the MVP and
    :meth:`is_available` reports ``False``.
    """

    def is_available(self) -> bool:
        """Not available in the MVP — Health Connect integration is future work."""
        return False

    def read_latest(
        self, metric_type: Optional[MetricType] = None
    ) -> list[Measurement]:
        """Not implemented in the MVP — see module docstring (Req 6.3)."""
        raise NotImplementedError(f"HealthConnectAdapter.read_latest: {_FUTURE_MSG}")

    def read(
        self,
        metric_type: Optional[MetricType] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Measurement]:
        """Not implemented in the MVP — see module docstring (Req 6.3)."""
        raise NotImplementedError(f"HealthConnectAdapter.read: {_FUTURE_MSG}")


class BluetoothSensorAdapter:
    """Interface-only placeholder for a Bluetooth LE sensor (Req 6.3 — future).

    A future iteration would stream readings from a paired Bluetooth Low Energy
    heart-rate / SpO2 sensor. Defined now only to satisfy the pluggable-adapter
    contract; the read methods are intentionally unimplemented in the MVP and
    :meth:`is_available` reports ``False`` (no device is paired in the MVP).
    """

    def is_available(self) -> bool:
        """Not available in the MVP — no BLE device is paired; integration is future work."""
        return False

    def read_latest(
        self, metric_type: Optional[MetricType] = None
    ) -> list[Measurement]:
        """Not implemented in the MVP — see module docstring (Req 6.3)."""
        raise NotImplementedError(f"BluetoothSensorAdapter.read_latest: {_FUTURE_MSG}")

    def read(
        self,
        metric_type: Optional[MetricType] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Measurement]:
        """Not implemented in the MVP — see module docstring (Req 6.3)."""
        raise NotImplementedError(f"BluetoothSensorAdapter.read: {_FUTURE_MSG}")
