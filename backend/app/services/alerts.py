"""AlertService: turn anomaly findings into an explainable, non-diagnostic alert (Task 12).

PURPOSE
-------
The analysis engine (Task 9/10, ``app.services.analysis``) emits structured
``AnomalyFinding`` rows. This module is the human-facing layer on top of them: it
maps a set of findings to ONE of three interface states, writes a plain-language
explanation of the supporting data, suggests non-diagnostic next steps, and ALWAYS
attaches symptom-based emergency guidance plus an "experimental / not medical
advice" label. The result is persisted as an ``Alert`` and surfaced by
``GET /insights`` (see ``app.routers.insights``).

REQUIREMENT COVERAGE
--------------------
- Req 4.1  — three states: ``normal`` | ``trend_review`` | ``attention`` (see
             ``map_state`` and ``STATE_TITLES``).
- Req 4.2  — explanation references the supporting data / contributing findings,
             and next steps are provided per state (see ``build_explanation`` and
             ``NEXT_STEPS``).
- Req 4.3  — emergency guidance is ALWAYS attached, regardless of state, as a
             separate always-present constant (see ``EMERGENCY_GUIDANCE``).
- Req 4.4  — no-diagnosis stance: the copy never claims to diagnose arrhythmia,
             heart attack, or stroke; it uses hedged "possible / may warrant
             review / not a diagnosis" language (see ``_NO_DIAGNOSIS`` note below
             and ``NEXT_STEPS``).
- Req 4.5  — every alert carries ``is_experimental=True`` and an explicit
             experimental label in its content (see ``EXPERIMENTAL_LABEL``).

DATA SOURCE (documented choice)
-------------------------------
``build_alert`` consumes findings from ``repository.list_findings`` (the most
recent stored findings) rather than calling ``run_analysis``. Rationale: a read of
the current insight (``GET /insights``) must NOT force an expensive recomputation
and must be deterministic for a given stored finding set. Recomputation is the job
of Jasper's ``POST /analysis/run`` (Task 11); this service reflects whatever that
produced. ``build_alert`` accepts an explicit ``findings`` list too, so callers who
already hold findings (e.g. right after an analysis run) can pass them directly.

STATE-MAPPING RULE (auditable — see ``map_state`` docstring for the exact ladder)
---------------------------------------------------------------------------------
``data_quality`` findings are INFORMATIONAL and must never escalate to
``attention``. A finding set that is ONLY ``data_quality`` maps to ``normal`` (the
non-alarming floor). Any non-data_quality finding in the ``attention`` band drives
``attention``; else any non-data_quality finding in the ``review`` band drives
``trend_review``; otherwise ``normal``.

SHARED WORDING (documented intent)
----------------------------------
``EMERGENCY_GUIDANCE`` and ``EXPERIMENTAL_LABEL`` are module-level CONSTANTS so the
mobile client (Tasks 15/23) and the README can reuse the EXACT wording the backend
emits — one source of truth for the safety copy, so the phrasing never drifts
between the API, the UI, and the docs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from ..db import repository as repo
from ..db.connection import DEMO_USER_ID, utc_now_iso
from ..db.models import Alert, AnomalyFinding

# --------------------------------------------------------------------------- #
# Shared safety copy — reused by mobile (Tasks 15/23) and the README.
# These are the single source of truth for the backend's safety wording.
# --------------------------------------------------------------------------- #

#: Req 4.3 — ALWAYS displayed, independent of the alert state (including
#: ``normal``). Symptom-based; tells the user to call emergency services directly.
#: Deliberately does NOT claim to detect or diagnose any event (Req 4.4).
EMERGENCY_GUIDANCE: str = (
    "If you experience possible heart-attack or stroke symptoms — such as chest "
    "pain or pressure, pain spreading to the arm, jaw, or back, sudden shortness "
    "of breath, a drooping face, arm weakness, or slurred speech — call your local "
    "emergency services immediately. Do not wait for this app. This guidance is "
    "shown at all times and does not depend on your wearable readings."
)

#: Req 4.5 — concise "experimental / not medical advice" label carried by every alert.
EXPERIMENTAL_LABEL: str = (
    "Experimental prototype — not medical advice and not a diagnosis. All data is "
    "synthetic. This does not replace evaluation by a qualified medical professional."
)

#: Req 4.1 — titles for the three interface states.
STATE_TITLES: dict[str, str] = {
    "normal": "Normal monitoring",
    "trend_review": "Trend review recommended",
    "attention": "Potentially concerning measurement requiring further assessment",
}

#: Req 4.2 / 4.4 — non-diagnostic next steps per state. None of these assert a
#: diagnosis; the strongest ("attention") only suggests *considering contacting* a
#: professional. Hedged language ("may", "consider") keeps the framing non-clinical.
NEXT_STEPS: dict[str, str] = {
    "normal": (
        "No action needed beyond continuing to monitor. Keep wearing your device so "
        "your personal baseline stays up to date."
    ),
    "trend_review": (
        "A trend may warrant review. Consider reviewing your recent trends and "
        "mentioning them at your next routine check-up. This is not a diagnosis."
    ),
    "attention": (
        "A potentially concerning pattern was observed in the synthetic data and may "
        "warrant assessment. Consider contacting a healthcare professional to discuss "
        "it. This is not a diagnosis, and if you have urgent symptoms follow the "
        "emergency guidance below."
    ),
}

# Finding types that are purely informational and must not escalate state.
_INFORMATIONAL_TYPES: frozenset[str] = frozenset({"data_quality"})


@dataclass(slots=True)
class InsightResult:
    """What AlertService returns to the router: the persisted alert + its findings.

    Attributes:
        alert:    the ``Alert`` that was built (and persisted, unless
                  ``persist=False``). ``alert.id`` is populated when persisted.
        findings: the ``AnomalyFinding`` list the alert was derived from, in the
                  order the service considered them (most-recent first, as returned
                  by ``repository.list_findings``). The router serializes these as
                  the supporting findings.
    """

    alert: Alert
    findings: list[AnomalyFinding]


def map_state(findings: list[AnomalyFinding]) -> str:
    """Map a set of findings to one interface state (Req 4.1). Auditable ladder.

    EXACT RULE
        1. Ignore ``data_quality`` findings for escalation — they are
           informational (a sensor gap, not a physiological trend) and must NEVER
           push the state to ``attention`` (Req 4.4 framing: a data gap is not a
           concerning measurement).
        2. If any REMAINING finding has ``severity_band == 'attention'`` -> state
           ``'attention'``.
        3. Else if any REMAINING finding has ``severity_band == 'review'`` -> state
           ``'trend_review'``.
        4. Else -> ``'normal'``.

    CONSEQUENCE (documented): a finding set that is EMPTY, or that contains ONLY
    ``data_quality`` findings, maps to ``'normal'`` — the non-alarming floor. A
    data-quality issue therefore never alarms on its own; at most the data-quality
    note appears in the explanation while the state stays ``'normal'``.

    Deterministic for a fixed finding set (pure function of the bands).
    """
    escalating = [f for f in findings if f.finding_type not in _INFORMATIONAL_TYPES]
    if any(f.severity_band == "attention" for f in escalating):
        return "attention"
    if any(f.severity_band == "review" for f in escalating):
        return "trend_review"
    return "normal"


def _describe_finding(f: AnomalyFinding) -> str:
    """One plain-language clause describing a single finding's supporting data.

    Reads the finding's ``supporting`` JSON (written by the detectors) and renders
    a non-diagnostic summary: which metric shifted and in which direction, the
    sustained-trend/irregular-rhythm rate, or the data-quality gap. Falls back to a
    generic clause if the JSON is missing/unpareseable so the explanation is always
    well-formed. Never asserts a diagnosis (Req 4.4).
    """
    try:
        data = json.loads(f.supporting) if f.supporting else {}
    except (ValueError, TypeError):
        data = {}

    metric = (f.metric_type or "metric").upper()
    if f.finding_type == "persistent_shift":
        direction = data.get("direction") or (
            "up" if (f.deviation or 0) > 0 else "down"
        )
        dev = data.get("standardized_deviation", f.deviation)
        dev_txt = f" (standardized deviation {dev:+.2f})" if isinstance(dev, (int, float)) else ""
        return (
            f"{metric} shows a sustained {direction}ward shift from your personal "
            f"baseline{dev_txt}"
        )
    if f.finding_type == "combination":
        hr_dev = data.get("hr_deviation")
        hrv_dev = data.get("hrv_deviation")
        extra = ""
        if isinstance(hr_dev, (int, float)) and isinstance(hrv_dev, (int, float)):
            extra = f" (HR {hr_dev:+.2f}, HRV {hrv_dev:+.2f} vs baseline)"
        return (
            "heart rate is elevated while heart-rate variability is reduced at the "
            f"same time{extra}"
        )
    if f.finding_type == "rhythm_irregularity":
        rate = data.get("irregular_rate")
        rate_txt = f" at a rate of {rate:.0%}" if isinstance(rate, (int, float)) else ""
        return (
            f"irregular-rhythm flags occurred more often than usual{rate_txt} "
            "(a possible rhythm irregularity in the synthetic signal; not a diagnosis)"
        )
    if f.finding_type == "data_quality":
        frac = data.get("missing_fraction")
        frac_txt = f" ({frac:.0%} of the recent window)" if isinstance(frac, (int, float)) else ""
        return (
            f"{metric} readings were missing or low quality{frac_txt}; this is a "
            "data-quality gap, not a physiological trend"
        )
    return f"{metric} produced a {f.finding_type} finding ({f.severity_band})"


def build_explanation(state: str, findings: list[AnomalyFinding]) -> str:
    """Compose the plain-language explanation referencing the supporting data (Req 4.2).

    The explanation names the contributing findings (via ``_describe_finding``),
    which metrics shifted and in which direction, any sustained trend / irregular-
    rhythm rate / data-quality gap, and frames everything as observed in SYNTHETIC
    data without claiming a diagnosis (Req 4.4). When there are no findings it
    returns a calm, well-formed "nothing notable" explanation so ``normal`` is never
    an empty string.
    """
    if not findings:
        return (
            "No notable deviations were detected in your recent synthetic readings. "
            "Your metrics are tracking within your personal baseline."
        )

    escalating = [f for f in findings if f.finding_type not in _INFORMATIONAL_TYPES]
    informational = [f for f in findings if f.finding_type in _INFORMATIONAL_TYPES]

    clauses = [_describe_finding(f) for f in escalating]
    if state == "normal" and not clauses:
        # Only data-quality findings present: lead with the calm summary, then note
        # the data gap so the state stays non-alarming but the user sees why.
        lead = (
            "No concerning physiological trend was detected in your recent synthetic "
            "readings."
        )
    else:
        lead = "This status is based on: " + "; ".join(clauses) + "."

    parts = [lead]
    if informational:
        notes = "; ".join(_describe_finding(f) for f in informational)
        parts.append(f"Data-quality note: {notes}.")
    parts.append(
        "These are descriptive observations of synthetic data, not a clinical "
        "assessment or diagnosis."
    )
    return " ".join(parts)


def build_alert(
    *,
    findings: Optional[list[AnomalyFinding]] = None,
    user_id: int = DEMO_USER_ID,
    persist: bool = True,
) -> InsightResult:
    """Build (and by default persist) an Alert from the current/most-recent findings.

    DATA SOURCE
        When ``findings`` is None, the most-recent stored findings are read via
        ``repository.list_findings`` (documented choice: a read never forces a
        recompute). Pass an explicit list to build from findings already in hand.

    WHAT IT PRODUCES (Req 4.1–4.5)
        - ``state``   via ``map_state`` (data_quality never escalates to attention).
        - ``title``   from ``STATE_TITLES[state]``.
        - ``explanation`` via ``build_explanation`` — references the supporting data.
        - ``next_steps`` from ``NEXT_STEPS[state]`` — non-diagnostic, prefixed with
          the experimental label and suffixed with the always-on emergency guidance
          so every persisted alert's stored text itself carries both (the router also
          exposes them as discrete fields).
        - ``finding_ids`` = JSON array of the contributing findings' ids (ids that
          exist; a not-yet-persisted finding contributes nothing to the array).
        - ``is_experimental`` = True (Req 4.5).

    PERSISTENCE
        With ``persist=True`` the alert is written via ``repository.insert_alert``
        and its ``id`` is populated. The returned ``InsightResult`` carries both the
        alert and the findings it was derived from.
    """
    if findings is None:
        findings = repo.list_findings(user_id=user_id)

    state = map_state(findings)
    title = STATE_TITLES[state]
    explanation = build_explanation(state, findings)
    next_steps = NEXT_STEPS[state]

    # The stored alert text embeds the experimental label and emergency guidance so
    # the persisted record is self-contained (Req 4.3/4.5); the router ALSO returns
    # them as discrete fields for the UI.
    stored_next_steps = (
        f"{next_steps}\n\n{EXPERIMENTAL_LABEL}\n\nEmergency guidance: {EMERGENCY_GUIDANCE}"
    )

    finding_ids = [f.id for f in findings if f.id is not None]

    alert = Alert(
        state=state,  # type: ignore[arg-type]
        title=title,
        explanation=explanation,
        next_steps=stored_next_steps,
        finding_ids=json.dumps(finding_ids),
        is_experimental=True,
        created_at=utc_now_iso(),
        user_id=user_id,
    )

    if persist:
        alert.id = repo.insert_alert(alert)

    return InsightResult(alert=alert, findings=findings)


# --------------------------------------------------------------------------- #
# Class wrapper (Task 11 seam).
#
# BUGFIX (maiabrunne): ``routers/analysis.py`` (Task 11) imports and instantiates
# ``AlertService`` and calls ``evaluate_and_store(run_analysis=True)``, but this
# module historically exposed only the function API above (``build_alert`` et al.,
# used by ``routers/insights.py``). Two parallel PRs merged with mismatched shapes,
# which broke every import of ``app.main``. This thin class reconciles them WITHOUT
# changing the working function API: it optionally triggers a recompute, then builds
# and persists the alert via ``build_alert``.
# --------------------------------------------------------------------------- #
class AlertService:
    """Object-oriented facade over the alert functions in this module.

    Exists so ``POST /analysis/run`` can recompute analysis and refresh the stored
    alert in one call. Delegates to the pure functions above; the function API
    remains the canonical implementation.
    """

    def evaluate_and_store(
        self,
        *,
        run_analysis: bool = False,
        user_id: int = DEMO_USER_ID,
    ) -> Alert:
        """Optionally recompute findings, then build + persist the current alert.

        When ``run_analysis`` is True, the analysis engine recomputes and persists
        findings first (Task 11 ``POST /analysis/run`` behavior); the alert is then
        built from whatever findings are now stored. Returns the persisted ``Alert``
        (``alert.state`` is what the router reports).
        """
        if run_analysis:
            # Imported lazily to avoid a circular import at module load
            # (analysis imports nothing from alerts, but keep the seam one-directional).
            from . import analysis

            analysis.run_analysis(user_id=user_id)

        result = build_alert(user_id=user_id, persist=True)
        return result.alert
