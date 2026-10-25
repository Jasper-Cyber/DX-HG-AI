"""Seed a labeled synthetic dataset for demos (Task 5, Req 5.4 / 8.4).

Populates the SQLite database with:
  - the provider directory (via seed_providers)
  - a synthetic measurement history for a chosen scenario (via SimulatorService)
  - recomputed baselines + anomaly findings + a current alert (via AlertService)
  - a demo care profile with a default location and an emergency contact

Everything written is synthetic and labeled experimental. Idempotent-ish: pass
--reset to wipe and regenerate.

Usage (from the backend/ directory, with the venv active):
    python seed_data.py                  # default scenario B, ~3 weeks hourly
    python seed_data.py --scenario A     # normal baseline data
    python seed_data.py --scenario C --steps 400
    python seed_data.py --reset          # wipe DB first, then seed
"""
from __future__ import annotations

import argparse

from app.db import care_repository as care
from app.db.care_models import CareProfile, EmergencyContact
from app.db.connection import DEMO_USER_ID, init_db, reset_db
from app.db import repository as repo
from app.db.seed_providers import DEMO_CENTER_LAT, DEMO_CENTER_LON, seed_providers
from app.services.alerts import AlertService
from app.services.simulator import SimulatorService


def seed(scenario: str = "B", steps: int = 504, seed_value: int = 42, do_reset: bool = False) -> dict:
    """Seed the database and return a short summary dict."""
    if do_reset:
        reset_db()
    else:
        init_db()

    # 1. Provider directory (idempotent).
    providers_added = seed_providers()

    # 2. Synthetic measurement history for the chosen scenario.
    repo.clear_measurements()  # fresh history for a clean demo
    sim = SimulatorService()
    sim.select_scenario(scenario)
    readings = sim.generate(steps=steps, scenario=scenario, seed=seed_value)

    # 3. Analysis + alert from that history.
    alert_service = AlertService()
    alert = alert_service.evaluate_and_store(run_analysis=True)

    # 4. A demo care profile (synthetic contact data), located at the demo center
    #    so provider suggestions and emergency routing have something to work with.
    care.upsert_care_profile(
        CareProfile(
            full_name="Demo User",
            phone="+1-555-0001",
            default_lat=DEMO_CENTER_LAT,
            default_lon=DEMO_CENTER_LON,
            emergency_contacts=[
                EmergencyContact(name="Jordan (demo contact)", relationship="partner", phone="+1-555-0002", priority=1),
            ],
        )
    )

    findings = repo.list_findings(user_id=DEMO_USER_ID)
    return {
        "scenario": scenario,
        "steps": steps,
        "readings": len(readings),
        "providers_added": providers_added,
        "findings": len(findings),
        "alert_state": alert.state,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic demo data for HeartGuardian AI.")
    parser.add_argument("--scenario", choices=["A", "B", "C"], default="B")
    parser.add_argument("--steps", type=int, default=504, help="number of hourly readings (~3 weeks)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    parser.add_argument("--reset", action="store_true", help="wipe the database before seeding")
    args = parser.parse_args()

    summary = seed(scenario=args.scenario, steps=args.steps, seed_value=args.seed, do_reset=args.reset)

    print("Seeded synthetic demo data (experimental, not real):")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("All data is synthetic and labeled experimental.")


if __name__ == "__main__":
    main()
