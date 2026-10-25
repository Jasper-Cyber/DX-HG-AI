"""Tests for AlertService + GET /insights (Task 12, Req 4.1–4.5).

Each test wires a FRESH temp SQLite DB via the HEARTGUARDIAN_DB env var and
reloads the DB modules (and, for the API tests, the routers + app) so they pick
up the temp path — mirroring tests/test_api_measurements_simulator.py.

A small helper seeds anomaly_findings directly through the repository so we can
drive AlertService with exactly the finding set each test needs.
"""
import importlib
import json

import pytest
from fastapi.testclient import TestClient

# Text that would constitute a prohibited diagnostic CLAIM (Req 4.4). We assert
# the alert content never asserts these. Hedged phrases like "possible ... stroke
# symptoms" in the emergency guidance are fine; a *claim* like "you have a stroke"
# is not. We check for claim-shaped substrings.
_DIAGNOSTIC_CLAIMS = [
    "you have a heart attack",
    "you are having a heart attack",
    "you have a stroke",
    "you are having a stroke",
    "you have arrhythmia",
    "diagnosed with",
    "this is a heart attack",
    "this is a stroke",
]


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """Repository bound to a fresh temp DB (for direct AlertService unit tests)."""
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "alerts.db"))
    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    # alerts service imports repo/connection by module; reload so it binds to the
    # freshly-reloaded modules reading the temp DB.
    from app.services import alerts as alerts_mod

    importlib.reload(alerts_mod)
    conn_mod.init_db()
    return repo_mod


@pytest.fixture()
def alerts(repo):
    from app.services import alerts as alerts_mod

    return alerts_mod


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """App wired to a fresh temp DB, with the insights router reloaded."""
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "api.db"))
    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import alerts as alerts_mod

    importlib.reload(alerts_mod)
    from app.routers import insights as ins_mod

    importlib.reload(ins_mod)
    from app import main as main_mod

    importlib.reload(main_mod)

    conn_mod.init_db()
    return TestClient(main_mod.app), repo_mod


def _seed_finding(repo, *, finding_type, severity_band, metric_type="hr", supporting=None):
    from app.db.models import AnomalyFinding

    supporting = supporting if supporting is not None else {"detector": finding_type}
    f = AnomalyFinding(
        metric_type=metric_type,
        finding_type=finding_type,
        severity_band=severity_band,
        window_start="2026-01-01T00:00:00+00:00",
        window_end="2026-01-02T00:00:00+00:00",
        supporting=json.dumps(supporting, sort_keys=True),
        deviation=supporting.get("standardized_deviation") if isinstance(supporting, dict) else None,
    )
    return repo.insert_finding(f)


# --------------------------------------------------------------------------- #
# State mapping (Req 4.1)
# --------------------------------------------------------------------------- #

def test_attention_finding_maps_to_attention(alerts, repo):
    _seed_finding(repo, finding_type="combination", severity_band="attention")
    result = alerts.build_alert()
    assert result.alert.state == "attention"
    assert result.alert.title == alerts.STATE_TITLES["attention"]


def test_only_review_maps_to_trend_review(alerts, repo):
    _seed_finding(repo, finding_type="persistent_shift", severity_band="review")
    result = alerts.build_alert()
    assert result.alert.state == "trend_review"


def test_no_findings_maps_to_normal(alerts):
    result = alerts.build_alert()
    assert result.alert.state == "normal"


def test_only_data_quality_does_not_escalate(alerts, repo):
    # Even an 'attention' band on a data_quality finding must NOT alarm.
    _seed_finding(
        repo,
        finding_type="data_quality",
        severity_band="attention",
        supporting={"detector": "data_quality", "missing_fraction": 0.8},
    )
    result = alerts.build_alert()
    assert result.alert.state == "normal"  # non-alarming floor


def test_attention_wins_over_review(alerts, repo):
    _seed_finding(repo, finding_type="persistent_shift", severity_band="review")
    _seed_finding(repo, finding_type="combination", severity_band="attention")
    result = alerts.build_alert()
    assert result.alert.state == "attention"


# --------------------------------------------------------------------------- #
# Explanation references supporting data (Req 4.2)
# --------------------------------------------------------------------------- #

def test_explanation_references_supporting_data(alerts, repo):
    _seed_finding(
        repo,
        finding_type="persistent_shift",
        severity_band="review",
        metric_type="hr",
        supporting={
            "detector": "persistent_shift",
            "direction": "up",
            "standardized_deviation": 2.5,
        },
    )
    result = alerts.build_alert()
    expl = result.alert.explanation.lower()
    # References the metric and the direction of the sustained shift.
    assert "hr" in expl
    assert "sustained" in expl
    assert "up" in expl


def test_data_quality_noted_in_explanation_but_normal(alerts, repo):
    _seed_finding(
        repo,
        finding_type="data_quality",
        severity_band="info",
        metric_type="spo2",
        supporting={"detector": "data_quality", "missing_fraction": 0.6},
    )
    result = alerts.build_alert()
    assert result.alert.state == "normal"
    assert "data-quality" in result.alert.explanation.lower()


# --------------------------------------------------------------------------- #
# Emergency guidance ALWAYS present (Req 4.3) + experimental label (Req 4.5)
# --------------------------------------------------------------------------- #

def test_emergency_guidance_present_even_when_normal(alerts):
    # No findings -> normal; guidance constant is still non-empty and mentions
    # emergency services.
    result = alerts.build_alert()
    assert result.alert.state == "normal"
    assert alerts.EMERGENCY_GUIDANCE
    assert "emergency services" in alerts.EMERGENCY_GUIDANCE.lower()
    # And the persisted alert text embeds it.
    assert "emergency services" in result.alert.next_steps.lower()


def test_every_alert_is_experimental(alerts, repo):
    _seed_finding(repo, finding_type="combination", severity_band="attention")
    result = alerts.build_alert()
    assert result.alert.is_experimental is True
    assert alerts.EXPERIMENTAL_LABEL
    assert "experimental" in result.alert.next_steps.lower()


# --------------------------------------------------------------------------- #
# No diagnostic claim (Req 4.4)
# --------------------------------------------------------------------------- #

def test_no_diagnostic_claim_in_content(alerts, repo):
    _seed_finding(repo, finding_type="combination", severity_band="attention")
    _seed_finding(repo, finding_type="rhythm_irregularity", severity_band="attention",
                  metric_type="rhythm", supporting={"detector": "rhythm_irregularity",
                                                     "irregular_rate": 0.4})
    result = alerts.build_alert()
    blob = " ".join([
        result.alert.title,
        result.alert.explanation,
        result.alert.next_steps,
        alerts.EMERGENCY_GUIDANCE,
        alerts.EXPERIMENTAL_LABEL,
    ]).lower()
    for claim in _DIAGNOSTIC_CLAIMS:
        assert claim not in blob, f"diagnostic claim leaked: {claim!r}"
    # Positive: non-diagnostic framing present.
    assert "not a diagnosis" in blob


def test_finding_ids_persisted_as_json_array(alerts, repo):
    fid = _seed_finding(repo, finding_type="persistent_shift", severity_band="review")
    result = alerts.build_alert()
    assert json.loads(result.alert.finding_ids) == [fid]
    # Alert persisted with an id.
    assert result.alert.id is not None


# --------------------------------------------------------------------------- #
# GET /insights (Req 4.1–4.5) — both no-findings and with-findings
# --------------------------------------------------------------------------- #

def _assert_insight_shape(body):
    for key in (
        "state",
        "title",
        "explanation",
        "nextSteps",
        "emergencyGuidance",
        "experimentalLabel",
        "isExperimental",
        "findings",
    ):
        assert key in body, f"missing field {key}"
    assert body["state"] in {"normal", "trend_review", "attention"}
    assert body["emergencyGuidance"]
    assert "emergency services" in body["emergencyGuidance"].lower()
    assert body["isExperimental"] is True
    assert body["experimentalLabel"]


def test_insights_no_findings_returns_normal_200(client):
    c, _ = client
    resp = c.get("/insights")
    assert resp.status_code == 200
    body = resp.json()
    _assert_insight_shape(body)
    assert body["state"] == "normal"
    assert body["findings"] == []


def test_insights_with_findings_returns_expected_shape(client):
    c, repo = client
    _seed_finding(
        repo,
        finding_type="combination",
        severity_band="attention",
        supporting={"detector": "combination", "hr_deviation": 2.1, "hrv_deviation": -1.8},
    )
    resp = c.get("/insights")
    assert resp.status_code == 200
    body = resp.json()
    _assert_insight_shape(body)
    assert body["state"] == "attention"
    assert len(body["findings"]) == 1
    f = body["findings"][0]
    assert f["findingType"] == "combination"
    assert f["severityBand"] == "attention"
    # supporting is a parsed object.
    assert isinstance(f["supporting"], dict)


def test_insights_read_does_not_persist_alert(client):
    c, repo = client
    _seed_finding(repo, finding_type="persistent_shift", severity_band="review")
    c.get("/insights")
    c.get("/insights")
    # Default GET must not fill the alerts table.
    assert repo.latest_alert() is None


def test_insights_no_diagnostic_claim(client):
    c, repo = client
    _seed_finding(repo, finding_type="combination", severity_band="attention")
    body = c.get("/insights").json()
    blob = " ".join([
        body["title"], body["explanation"], body["nextSteps"],
        body["emergencyGuidance"], body["experimentalLabel"],
    ]).lower()
    for claim in _DIAGNOSTIC_CLAIMS:
        assert claim not in blob
