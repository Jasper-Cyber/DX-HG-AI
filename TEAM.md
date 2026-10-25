# Team & Workflow — HeartGuardian AI (DX Competition)

> 📌 **This is the active repository: `DX-HG-AI`.**
> The team has moved here for the DX competition. Clone **this** repo and do all new work here.
> The previous `HeartGuardianAI` repo is now archived/read-only — **do not push to it.**
> Repo: https://github.com/Jasper-Cyber/DX-HG-AI

This file is the team's coordination guide. The single source of truth for *what to build* is
[`.kiro/specs/heartguardian-ai/tasks.md`](.kiro/specs/heartguardian-ai/tasks.md); this file says
*who* does it and *how* we work together without stepping on each other.

## Getting started

### Prerequisites
Install these once. Versions below are what the project is scaffolded against (newer minor versions are usually fine):

| Tool | Version used | Notes |
|------|--------------|-------|
| Git | 2.5+ | — |
| Python | 3.11–3.13 | `python` on Windows (there is no `python3` alias here) |
| Node.js | 20 LTS or newer | project scaffolded with Node 26 / npm 11 |
| Expo | via `npx expo` | no global install needed |
| Expo Go app | latest | on your phone, to run the mobile app without a native build |

### 1. Clone and enter the repo
```bash
git clone https://github.com/Jasper-Cyber/DX-HG-AI.git
cd DX-HG-AI
```

### 2. Run the backend (FastAPI)
```bash
cd backend
python -m venv .venv
# Windows (bash/Git Bash):
source .venv/Scripts/activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Verify: open http://localhost:8000/health (should return `{"status":"ok",...}`) and
http://localhost:8000/docs for the interactive API.
Run backend tests with `pytest` from the `backend/` directory.

### 3. Run the mobile app (Expo)
In a second terminal:
```bash
cd mobile
npm install
npm start          # opens Expo; scan the QR code with Expo Go, or press w for web
```
The app launches to a dark-blue Dashboard with placeholder screens and a "SIMULATED DATA" ribbon.

> The mobile app talks to the backend at `http://localhost:8000`. On a physical phone, replace
> `localhost` with your computer's LAN IP (the API base URL is configured in `mobile/api/` — Task 13).

### First task per person
Start here (full details in `tasks.md`). Open a branch per task (see Git workflow below).

| Member | Start with | Then |
|--------|-----------|------|
| Jasper-Cyber | Task 4 (SQLite schema + repository) | 5, 8, 11 |
| Raffy | Task 6 (SimulatorService) | 7, 9, 10, 12 |
| maiabrunne | Task 18 (care/settings data layer) — after Task 4 lands | 19, 20, 21, 24, 25 |
| Helenawai | Task 13 (API client + hooks) | 14, 15, 16, 17, 22, 23 |

Tasks 1–3 (scaffolding) are **already done**, so everyone is unblocked. Jasper-Cyber's Task 4 is the
next backend dependency; maiabrunne's Task 18 builds on it, so maiabrunne can begin with the provider
directory seed / mock while Task 4 is in review.

## Team

| Member | GitHub | Role (reference only — work is not limited to role) |
|--------|--------|------------------------------------------------------|
| Jasper-Cyber | `Jasper-Cyber` | Founder / project lead |
| Raffy | `Raffy` | Bio specialist |
| maiabrunne | `maiabrunne` | Data specialist 1 |
| Helenawai | `Helenawai` | Data specialist 2 |

Work is allocated to **balance coding load and avoid overlap**, not by role. Everyone writes code
across the stack as the task requires.

## Work allocation

Tasks reference the numbered list in `tasks.md`. Each person owns a set of files/folders so two
people rarely touch the same file.

### Jasper-Cyber — Backend backbone & integration (Tasks 1, 2, 4, 5, 8, 11, 28)
- Repo structure, FastAPI skeleton, SQLite schema + repository layer, seed data.
- Simulator/scenario endpoint wiring and analysis endpoints (the API surface others call).
- Coordinates the README/demo (task 28); everyone contributes their section.
- **Owns:** `backend/app/main.py`, `backend/app/db/`, `backend/app/routers/` (scenario, analysis wiring), `seed_data.py`, root `README.md`.

### Raffy — Analytics & simulation engine (Tasks 6, 7, 9, 10, 12, 26)
- SimulatorService (scenarios A/B/C), SensorAdapter + SimulatedSensorAdapter.
- AnalysisEngine: baseline, rolling stats, anomaly detectors; AlertService.
- Python test suite (task 26).
- **Owns:** `backend/app/services/{simulator,analysis,alerts}.py`, `backend/app/adapters/sensor*.py`, `backend/app/analysis_config.py`, `backend/tests/`.

### maiabrunne — Care network & emergency (full stack) (Tasks 18, 19, 20, 21, 24, 25)
- Care profile / contacts / settings data layer + provider directory seed.
- ProviderService (distance ranking) and EmergencyService + NotifierAdapter (routing, payload, simulated dispatch).
- The matching mobile screens: nearby-provider suggestions and the emergency-response flow.
- **Owns:** `backend/app/services/{provider,emergency}.py`, `backend/app/adapters/notifier*.py`, `backend/app/emergency_config.py`, `mobile/app/emergency.tsx`, `mobile/components/{ProviderSuggestionCard,NearbyProvidersSheet,EmergencyConfirmDialog,DispatchHistoryList}.tsx`.

### Helenawai — Mobile app & UI (Tasks 3, 13, 14, 15, 16, 17, 22, 23, 27)
- Expo scaffold + theme, API client + React Query hooks (the shared data layer other screens use).
- Core screens: Dashboard, Insights/Alerts, History, Simulator, Care-profile/Settings, Disclaimer.
- TypeScript test suite (task 27).
- **Owns:** `mobile/app/(tabs)/`, `mobile/app/disclaimer.tsx`, `mobile/api/`, `mobile/theme.ts`, `mobile/components/` (shared, except maiabrunne's care/emergency ones), `mobile/__tests__/`.

### Load balance (approx. coding weight)
| Member | Tasks | Notes |
|--------|-------|-------|
| Jasper-Cyber | 7 | Smaller-but-foundational tasks; also owns demo coordination |
| Raffy | 6 | Logic-heavy engine + Python tests |
| maiabrunne | 6 | Full-stack feature (backend services + 2 mobile screens) |
| Helenawai | 9 | Many screens but each is UI-focused; includes TS tests |

## Build order (dependencies)

```
Phase 0 (1–3)  scaffold          → do FIRST, ideally together (touches shared files)
Phase 1 (4–5)  DB + seed         → unblocks everything backend
Phase 2 (6–8)  simulator         ─┐
Phase 3 (9–11) analysis           ├→ backend feature-complete
Phase 4 (12)   alerts            ─┘
Phase 5 (13–17) core mobile      → build against mock data early, real API once above lands
Phase 6 (18–25) care + emergency → depends on alerts (12) + mobile data layer (13)
Phase 7 (26–28) tests + docs     → ongoing; finalize last
```

Front-end owners (Helenawai, maiabrunne) should work against **mock API responses** early so they
are never blocked waiting on the backend.

> **Unblock note:** Tasks 1–3 (scaffolding) are already done and committed — `backend/` and
> `mobile/` exist and run. All four members can start their first task now (see "First task per
> person" in Getting Started below).

## Known issues / in-progress fixes

- **Backend import chain broken on `main` (being fixed by maiabrunne).** After several
  parallel PRs merged, `main` could not even import `app.main` (every test errored at
  collection), because `routers/analysis.py` referenced names its dependencies didn't export:
  - `services/alerts.py` exposed only a function API but `routers/analysis.py` imported an
    `AlertService` class — fixed by adding a thin `AlertService` wrapper over the existing
    functions (function API unchanged).
  - `services/analysis.py` defined `_BASELINE_METRICS` but `routers/analysis.py` imported
    `NUMERIC_METRICS` — fixed by exposing a public `NUMERIC_METRICS` alias (no logic change).

  This restores the backend to importable/runnable (0 → 116 passing tests).

- **Remaining ~41 test failures are pre-existing on `main`** and span several owners' modules
  (analysis engine, alerts, sensor adapter, provider, settings, emergency, measurements). They
  are API/shape mismatches from parallel merges and need each module's **owner** to reconcile
  intended behavior — they are out of scope for the import fix above. Owners: please check your
  module's failing tests.

- **[RESOLVED] Mobile API client ↔ backend response-shape mismatches (owner: Helenawai).**
  The mobile `api/` layer (Task 13) was written before several endpoints existed and assumed
  shapes that differ from what the backend actually returns. Backend verified to import/run; these
  are client-side contract bugs that would break mobile screens at runtime even with the backend up:
  - **`GET /insights`** returns a *flat* object (`state`, `title`, `explanation`, `nextSteps`,
    `emergencyGuidance`, `findings`, …). The client expected `{ current, history }`. Breaks the
    Insights screen and the Dashboard monitoring card + History past-alerts (all read `.current`/`.history`).
  - **`GET /trends`** series use `metric` and `TrendPoint{period,mean,min,max,count}` with no
    `baselineStd`. The client expected `metricType` and `TrendPoint{timestamp,value}` + `baselineStd`.
    Breaks the History trend charts.
  - **`GET /providers`** returns an envelope `{count,isExperimental,items:[…]}`; the client typed it
    as a bare array. Breaks `useProviders` (used by the provider-suggestion components).
  - There is **no past-alerts history endpoint** (`/insights` returns only the current insight), so
    the History screen's "past alerts" has no data source — needs a backend decision (add endpoint or
    drop the section).

  Resolution (done, branch `fix/mobile-api-contracts`): the **mobile client** was adapted to the
  backend's actual shapes — `/insights` read as a flat object, `/trends` series/point field names
  (`metric`, `period`/`mean`), and `/providers` envelope unwrapped to `ProviderSuggestion[]`. All
  shapes verified against the running backend. The missing past-alerts history endpoint remains a
  separate backend-owner decision; for now the History screen derives a single recent entry from
  the current non-normal insight.

- **[RESOLVED] Care-network duplication + wrong emergency contract in shared `api/` layer (maiabrunne).**
  My Tasks 24/25 mobile code originally used a stand-in `mobile/api/care.ts` (written before the
  shared Task 13 client existed). When `fix/mobile-api-contracts` (Task 13) merged, the shared
  `api/{client,types,hooks}.ts` duplicated almost all of `care.ts` (Provider, ProviderSuggestion,
  EmergencyContact, CareProfile, EmergencyDecision, Settings, ApiError, and the care/emergency
  hooks). Additionally, the shared layer's **emergency** pieces were typed against the design doc,
  not the running backend: `EmergencyDecision` was nested (`recipient`, `payload`) and
  `useEmergencyEvaluation`/`useDispatch` took `{lat,lon}` / `{channel,confirm}` — but the backend
  `/emergency/evaluate` returns a FLAT `DecisionOut` and `/dispatch` takes
  `{lat,lon,findingSummary,confirmed}` and re-evaluates routing server-side.
  Resolution (done): deleted `care.ts`; pointed the care/emergency components + `emergency.tsx` at
  the shared `api/` layer; corrected the shared `EmergencyDecision`/`DispatchResult`/`DispatchEvent`
  types and the `evaluate`/`dispatch` client+hook signatures to match the real backend. Verified:
  `tsc --noEmit` clean and all 33 mobile Jest tests pass (incl. Helenawai's client/trends suites).

- **[RESOLVED] Mobile client read the wrong error-body field — all backend error messages were lost (maiabrunne).**
  `mobile/api/client.ts` built its `ApiError` message from `errBody.error`, and `ApiErrorBody`
  declared a required `error: string`. But the backend raises plain `HTTPException(detail=...)` with
  no custom handler, so FastAPI serializes errors as `{"detail": "..."}`. `error` was therefore
  always `undefined`, and every surfaced error fell back to a generic "Request failed with <status>"
  — the specific reasons (e.g. "Emergency response is not enabled.", "Dispatch requires explicit
  user confirmation.", "Real dispatch is disabled…") never reached the UI (notably `emergency.tsx`'s
  dispatch error handler). Fix: `ApiErrorBody` now has `detail?` (primary) + optional `error?`, and
  the client reads `detail` (string) first, then `error`, then the generic fallback. Verified against
  the running backend (a disabled-dispatch 409 now surfaces "Emergency response is not enabled.").

- **[RESOLVED] Emergency dispatch confirm-vs-dispatch split-brain / null coordinates (maiabrunne).**
  `emergency.tsx` evaluated a decision (server resolves location + routing, previewed in the confirm
  dialog), but on dispatch re-sent the live `useUserLocation` `lat`/`lon`. Those could be `null` (GPS
  denied, falling back to an approximate/empty location) or could re-resolve to a DIFFERENT recipient
  than the one previewed/confirmed, since `/dispatch` independently re-evaluates routing server-side.
  Result: dispatch could 409/422 after a successful preview, or notify a recipient other than the one
  the user confirmed. Fix: dispatch now reuses the coordinates the decision was evaluated against
  (`decision.payload.location.{lat,lon}`), falling back to live location only if absent — so the
  server re-resolves to the same recipient and never receives null when evaluation used a default
  location. Verified: `tsc --noEmit` clean, 33/33 mobile tests pass.

- **[RESOLVED] Four routers imported but never registered in `main.py` (maiabrunne).** A later merge
  mangled the router-registration block in `backend/app/main.py`: it `import`s
  `analysis, emergency, insights, measurements, providers, settings, simulator`, but only calls
  `app.include_router(...)` for `measurements`, `simulator`, and `insights`. As a result
  **`settings`, `providers`, `emergency`, and `analysis` are never mounted**, so the running app
  serves only `/health`, `/insights`, `/measurements`, `/scenario`, `/simulator/{action}`. Every
  other endpoint 404s — verified missing: `/settings`, `/settings/disclaimer-ack`, `/care/profile`,
  `/providers`, `/emergency/evaluate|dispatch|history`, `/analysis/run`, `/trends`. This is the
  root cause of the `assert 404 == 200/422/403` failures in `test_api_settings.py`,
  `test_provider_service.py`, and `test_emergency_service.py` (NOT a per-module logic bug, so it is
  distinct from the ~41 failures above). It is also distinct from the mobile API-contract bugs
  (owner: Helenawai) — those are client-side response-shape issues; this is server-side routes
  simply not being mounted.
  Fix: add `app.include_router(...)` for `analysis`, `settings`, `providers`, and `emergency` in
  `main.py`, and drop the duplicate `from .routers import insights` line.

## Git workflow (one branch per task)

Never commit directly to `main`.

```bash
git checkout main
git pull                                   # always start from latest
git checkout -b feat/<area>-<short-desc>   # e.g. feat/backend-measurements-endpoint
# ... code + commit ...
git push -u origin feat/<area>-<short-desc>
# open a Pull Request on GitHub → 1 review → merge
```

Branch naming: `feat/...` (new work), `fix/...` (bug fixes). Keep branches small and short-lived.
Reference the task number in the PR title, e.g. `Task 14: Dashboard screen`.

### Stay in sync (do this daily)
```bash
git checkout main && git pull
git checkout your-branch
git merge main        # pick merge OR rebase as a team and stick with it
```

## Shared files — edit carefully (conflict magnets)

These get touched by many tasks; keep edits **small and additive** so git auto-merges:
- `backend/app/main.py` (router registration) — append one line per router.
- `mobile/app/(tabs)/_layout.tsx` (tab nav) — append one tab at a time.
- `.kiro/specs/heartguardian-ai/tasks.md` (the checklist) — only check off your own task.
- Dependency files: `backend/pyproject.toml`, `mobile/package.json`.

Claim a task (check it off / assign on GitHub) **before** starting so two people don't pick the same one.

## Recommended GitHub settings (repo admin)

Configure on GitHub.com → Settings → Branches → add a ruleset for `main`:
- Require a pull request before merging (≥ 1 approval).
- Require branches to be up to date before merging.
- Block force pushes.

## Definition of done (per task)
- Code compiles / app runs; no new linter errors.
- Tests added or updated where the task calls for it; existing tests pass.
- PR reviewed and merged to `main`; the app is still runnable.
