"""Tests for the sensor adapters (Task 7).

Covers Requirement 6:
- SimulatedSensorAdapter conforms to the SensorAdapter protocol (isinstance via
  @runtime_checkable) and reads back the readings the simulator produced (Req 6.1, 6.2).
- The simulated data path needs no real hardware — is_available() is always True (Req 6.4).
- The three future adapters (Apple Health / Health Connect / Bluetooth) are importable,
  structurally conform to the protocol, and raise NotImplementedError on their read
  methods while reporting is_available() == False (Req 6.3).

Uses the same isolated-temp-DB + importlib.reload pattern as
test_simulator_service.py / test_api_measurements_simulator.py: point
HEARTGUARDIAN_DB at a temp file, reload the DB + service + adapter modules so they
bind to the temp DB, then init the schema.
"""
import importlib

import pytest


@pytest.fixture()
def adapter_env(tmp_path, monkeypatch):
    """Fresh temp DB wired to reloaded repository + service + adapter modules."""
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "adapters.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import simulator as sim_mod

    importlib.reload(sim_mod)
    from app.adapters import sensor as sensor_mod

    importlib.reload(sensor_mod)
    from app.adapters import sensor_stubs as stubs_mod

    importlib.reload(stubs_mod)

    conn_mod.init_db()
    return sensor_mod, stubs_mod, sim_mod, repo_mod


def _run_simulator(repo, sim_mod, scenario="A", seed=42, days_back=7):
    """Seed a cursor in the past and run start() so there are readings to read.

    Mirrors the backfill path used by the simulator tests: a cursor ``days_back``
    days in the past makes a single synchronous start() generate a multi-day batch.
    """
    from datetime import datetime, timedelta, timezone

    start_cursor = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    repo.update_sim_state(scenario=scenario, seed=seed, cursor_ts=start_cursor)
    sim_mod.SimulatorService().start()


# --------------------------------------------------------------------------- #
# SimulatedSensorAdapter — protocol conformance + reading the simulator (Req 6.1, 6.2)
# --------------------------------------------------------------------------- #

def test_simulated_adapter_conforms_to_protocol(adapter_env):
    sensor_mod, _, _, _ = adapter_env
    adapter = sensor_mod.SimulatedSensorAdapter()
    # @runtime_checkable protocol => isinstance verifies the structural surface.
    assert isinstance(adapter, sensor_mod.SensorAdapter)


def test_simulated_adapter_constructible_with_no_args(adapter_env):
    sensor_mod, _, _, _ = adapter_env
    # No-arg / dependency-light construction is part of the contract.
    assert sensor_mod.SimulatedSensorAdapter() is not None


def test_simulated_adapter_is_always_available_no_hardware(adapter_env):
    """Req 6.4 — the simulated path works with no real wearable hardware."""
    sensor_mod, _, _, repo = adapter_env
    adapter = sensor_mod.SimulatedSensorAdapter()
    # Available even before any data exists: no device/pairing is involved.
    assert adapter.is_available() is True
    assert repo.count_measurements() == 0


def test_simulated_adapter_reads_simulator_history(adapter_env):
    """Adapter reads back exactly what the simulator persisted (Req 6.2)."""
    sensor_mod, _, sim_mod, repo = adapter_env
    _run_simulator(repo, sim_mod, scenario="A", seed=42, days_back=7)

    adapter = sensor_mod.SimulatedSensorAdapter()
    rows = adapter.read()

    assert len(rows) > 0
    # The adapter is a faithful read-through of the repository's data.
    assert len(rows) == repo.count_measurements()
    assert all(r.is_synthetic for r in rows)
    metrics = {r.metric_type for r in rows}
    assert metrics == {"hr", "hrv", "spo2", "rhythm", "activity", "sleep"}


def test_simulated_adapter_read_is_ordered_oldest_first(adapter_env):
    sensor_mod, _, sim_mod, repo = adapter_env
    _run_simulator(repo, sim_mod, scenario="A", seed=42, days_back=5)

    adapter = sensor_mod.SimulatedSensorAdapter()
    hr_rows = adapter.read(metric_type="hr")

    timestamps = [r.timestamp for r in hr_rows]
    assert timestamps == sorted(timestamps)
    assert all(r.metric_type == "hr" for r in hr_rows)


def test_simulated_adapter_read_latest_specific_metric(adapter_env):
    sensor_mod, _, sim_mod, repo = adapter_env
    _run_simulator(repo, sim_mod, scenario="A", seed=42, days_back=5)

    adapter = sensor_mod.SimulatedSensorAdapter()
    latest = adapter.read_latest(metric_type="hr")

    assert len(latest) == 1
    assert latest[0].metric_type == "hr"
    # It really is the most recent hr reading.
    all_hr = adapter.read(metric_type="hr")
    assert latest[0].timestamp == all_hr[-1].timestamp


def test_simulated_adapter_read_latest_all_metrics(adapter_env):
    sensor_mod, _, sim_mod, repo = adapter_env
    _run_simulator(repo, sim_mod, scenario="A", seed=42, days_back=5)

    adapter = sensor_mod.SimulatedSensorAdapter()
    latest = adapter.read_latest()

    # One latest reading per metric type that has data.
    metrics = {r.metric_type for r in latest}
    assert metrics == {"hr", "hrv", "spo2", "rhythm", "activity", "sleep"}
    assert len(latest) == 6


def test_simulated_adapter_read_latest_empty_when_no_data(adapter_env):
    sensor_mod, _, _, _ = adapter_env
    adapter = sensor_mod.SimulatedSensorAdapter()
    assert adapter.read_latest() == []
    assert adapter.read_latest(metric_type="hr") == []


# --------------------------------------------------------------------------- #
# Future stub adapters (Req 6.3)
# --------------------------------------------------------------------------- #

_STUB_NAMES = ("AppleHealthAdapter", "HealthConnectAdapter", "BluetoothSensorAdapter")


def test_stub_adapters_are_importable(adapter_env):
    _, stubs_mod, _, _ = adapter_env
    for name in _STUB_NAMES:
        assert hasattr(stubs_mod, name), f"{name} should be defined"


def test_stub_adapters_conform_to_protocol(adapter_env):
    """Stubs match the SensorAdapter surface so they are drop-in future sources."""
    sensor_mod, stubs_mod, _, _ = adapter_env
    for name in _STUB_NAMES:
        instance = getattr(stubs_mod, name)()
        assert isinstance(instance, sensor_mod.SensorAdapter), name


def test_stub_adapters_report_unavailable(adapter_env):
    _, stubs_mod, _, _ = adapter_env
    for name in _STUB_NAMES:
        instance = getattr(stubs_mod, name)()
        assert instance.is_available() is False, name


def test_stub_adapters_raise_not_implemented_on_reads(adapter_env):
    _, stubs_mod, _, _ = adapter_env
    for name in _STUB_NAMES:
        instance = getattr(stubs_mod, name)()
        with pytest.raises(NotImplementedError):
            instance.read_latest()
        with pytest.raises(NotImplementedError):
            instance.read(metric_type="hr")
