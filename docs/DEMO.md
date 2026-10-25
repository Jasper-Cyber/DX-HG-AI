# HeartGuardian AI — Demonstration Script

A step-by-step script for a live demo or a recorded walkthrough. Everything shown is **synthetic**
and labeled experimental; the app is a prototype, not a medical device.

## Setup (once)

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv
source .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python seed_data.py --scenario B --reset   # labeled synthetic history for the demo
uvicorn app.main:app --reload --port 8000

# Terminal 2 — mobile
cd mobile
npm install
npm start                            # open in Expo Go (scan QR) or press w for web
```

Verify the backend is up: open <http://localhost:8000/health> (expect `{"status":"ok", ...}`).

## Walkthrough (~3 minutes)

| # | Step | What to point out |
|---|------|-------------------|
| 1 | Open the app → **Dashboard** | "SIMULATED DATA" ribbon; HR/HRV/SpO₂/rhythm cards; activity, sleep, monitoring + wearable status. All synthetic. |
| 2 | **Disclaimer** (first launch) | Experimental, not reliable, not liable, user decides. Acknowledge; note it's reachable from Settings. |
| 3 | **Simulator → A (Normal)** → Start | Metrics stay within baseline; Insights shows **Normal monitoring**. |
| 4 | **Simulator → B (Gradual Deviation)** → Reset, Start | HR drifts up, HRV down; Insights rises to **Trend review / Attention** with an explanation + next steps. |
| 5 | **Simulator → C (Rhythm Irregularity)** → Reset, Start | Rhythm-irregularity finding flagged for review — never a diagnosis. |
| 6 | **History** | Daily/weekly/monthly toggle; baseline overlay; anomaly markers. |
| 7 | **Settings → enable suggestions** (optional) | Set default location + preferred doctor; on a warning, open nearby-providers sheet (ranked by distance). |
| 8 | **Settings → enable emergency** (optional) | Trigger the flow: routing decision, payload preview (contacts + location + non-diagnostic summary), confirm-with-countdown, **simulated** dispatch recorded in history. Always shows "contact real emergency services" guidance. |
| 9 | Reset to **A** | Leave a clean state. |

## Talking points

- **Personalized, transparent analysis:** baselines are learned per user; every alert cites the
  supporting data; all thresholds live in `analysis_config.py` — no black-box "risk %".
- **Reproducible:** a fixed scenario + seed yields identical data and findings
  (`python seed_data.py --scenario B --seed 42`).
- **Safety-first:** warnings/suggestions/emergency are optional and user-controlled; emergency is
  simulated by default and never sends anything without explicit confirmation.
- **No real sensors or paid APIs** are required for any part of the demo.

## Reset between runs

```bash
cd backend
python seed_data.py --scenario A --reset   # clean normal-state dataset
```
