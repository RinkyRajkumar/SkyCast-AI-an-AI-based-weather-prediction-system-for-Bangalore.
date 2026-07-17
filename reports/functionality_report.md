# SkyCast AI Functionality Report

Date: 2026-07-16  
Environment: Windows, Python 3.14.5, Node.js 24.16.0, Docker CLI 29.5.3

## Final verdict

**Working.**

The application works end to end both locally and through Docker Compose: React accepted the real 169-hour observation file, Axios called the FastAPI service, the shared feature-engineering function generated model inputs, all 12 selected artifacts produced valid forecasts, and the UI rendered forecast cards plus both charts. Automated backend tests, frontend tests, linting and the production build pass.

Docker Desktop completed its pending WSL bootstrap on 2026-07-17. Both images built successfully, both containers became healthy, and the containerized API returned four forecasts from the real demo input.

## Project and artifact audit

- All Python imports compile successfully with `python -m compileall -q backend src tests`.
- Required source modules, FastAPI files, React components, Dockerfiles, environment examples and deployment files are present.
- Required datasets exist:
  - `data/raw/bangalore_hourly_weather_2015_2025.csv`
  - `data/processed/bangalore_weather_clean.csv`
  - `data/processed/bangalore_weather_features.csv`
- 44 `.joblib` model files exist, including every selected production artifact.
- The selected inference set contains four temperature models, four rain classifiers and four rainfall regressors.
- Metric reports used for model selection exist. The loader also has documented fallback selections if reports are unavailable.
- Backend paths resolve from the project configuration or the optional `SKYCAST_MODELS_ROOT` and `SKYCAST_REPORTS_ROOT` variables.
- Frontend API configuration uses `VITE_API_BASE_URL`, with `http://localhost:8000` as the development fallback.
- No broken imports, missing production files, unresolved feature columns or incorrect selected-model paths remain.

## Dependencies

Commands executed:

```powershell
python -m pip install -r requirements.txt -r backend/requirements.txt
cd frontend
npm.cmd install
```

Results:

- Python requirements installed or were already satisfied.
- Frontend installed 183 packages.
- `npm` reported zero vulnerabilities.

## Automated test results

### Python and FastAPI

```powershell
python -m pytest -q
```

Result: **37 passed**.

One non-failing warning remains: the installed Starlette version warns that its `httpx`-based `TestClient` compatibility path is deprecated.

Coverage includes collection, cleaning, interpolation, feature generation, lags, targets, chronological splits, baseline models, advanced models, rain models, API validation, missing-model behavior and the committed demo request.

### React

```powershell
cd frontend
npm.cmd test -- --reporter=default
```

Result: **7 passed, 1 skipped**. The skipped test is intentionally opt-in because it requires a running FastAPI service.

The normal suite verifies API error handling, component behavior, file validation, forecast rendering, loading state and request error state.

### Live React-to-FastAPI integration

With FastAPI running:

```powershell
cd frontend
$env:SKYCAST_E2E = "1"
npm.cmd test -- App.e2e.test.tsx --reporter=default
```

Result: **1 passed**.

This test uploaded `demo/bangalore_recent_observations.json`, enabled submission, called the real `/predict` endpoint, found the 1h and 24h forecast cards, and found both the temperature and rain-probability chart containers.

### Lint and production build

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

Both passed. Vite transformed 640 modules and produced the production bundle under `frontend/dist/`.

## API checks

FastAPI was started with:

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

All checks below passed:

| Check | Expected result | Actual result |
| --- | --- | --- |
| `GET /health` | 200 | 200 |
| `GET /models` | 200 and 12 models | 200 and 12 models |
| Valid `POST /predict` | 200 and four horizons | 200 and four horizons |
| Humidity above 100 | 422 | 422 |
| Only 20 observations | 422 | 422 |
| Invalid timestamp | 422 | 422 |
| Missing field | 422 | 422 |
| Duplicate timestamp | 422 | 422 |
| Non-hourly gap | 422 | 422 |
| Allowed localhost CORS preflight | Origin header returned | Passed |
| Untrusted-origin preflight | No allow-origin header | Passed |
| Missing model `/health` | 200 liveness | 200 |
| Missing model `/models` | 503 with clear detail | 503 |
| Missing model `/predict` | 503 with clear detail | 503 |

The valid request produced:

| Horizon | Temperature | Rain probability | Rainfall |
| ---: | ---: | ---: | ---: |
| 1h | 20.64 °C | 0.1660 | 0.019 mm |
| 6h | 18.69 °C | 0.3077 | 0.060 mm |
| 12h | 25.38 °C | 0.5887 | 0.196 mm |
| 24h | 20.36 °C | 0.8109 | 1.490 mm |

Every temperature, probability and rainfall value was finite. All rain probabilities were within 0–1, and all returned rainfall amounts were non-negative.

## Feature and leakage checks

- Inference imports `src.features.create_features`; feature calculations are not duplicated.
- Lag columns use positive `shift` offsets.
- Rolling temperature, humidity, pressure and precipitation features shift by one hour before rolling.
- Future temperature and rain targets are generated only for training/evaluation.
- No selected artifact contains a future target column in `feature_columns`.
- All 12 artifacts were exercised with `features[artifact["feature_columns"]]`, preserving the exact training column order.
- Runtime comparison found no missing feature columns for any selected artifact.
- Chronological split tests verify no overlap and remove rows whose target would cross a split boundary.
- Inference rejects duplicate, invalid, non-contiguous and insufficient observation histories.

No time-series leakage or training/inference feature mismatch was found.

## Frontend and browser checks

- Dashboard loaded with meaningful content and no Vite error overlay.
- Backend status changed from checking to `Backend connected`.
- The real demo file contains 169 valid, contiguous hourly observations and enabled forecasting.
- The live integration rendered all four forecast horizons.
- Temperature and rain-probability charts rendered after prediction.
- Loading state appears while a prediction promise is pending.
- API failure displays `Forecast unavailable` and preserves the 169 loaded observations.
- Browser console inspection returned no warnings or errors.
- At a 390 × 844 viewport, the form uses one column, the submit button remains visible, and the document has no horizontal overflow.

The native file picker was not directly controllable through the browser-testing interface. The equivalent upload and display path was completed by the opt-in React integration test using the same `File` input event and real FastAPI endpoint.

## Docker checks

```powershell
docker compose config
docker compose up --build
```

- Compose interpolation and service configuration: **passed**.
- Backend and frontend image builds: **passed**.
- Backend container health check: **healthy**.
- Frontend container health check: **healthy**.
- Containerized `/health`, `/health/ready`, `/models` and `/predict`: **passed**.
- The real demo request returned horizons 1h, 6h, 12h and 24h.
- Recent container logs contained no error, exception, traceback, panic or fatal patterns.

Docker Desktop initially reported `wslUpdateRequired` while creating its internal WSL environment. The installed WSL package was already current (`2.7.10`), Hyper-V networking initialized successfully, and Docker completed startup without a destructive reset or data deletion.

## Bugs found and fixes made

1. **Demo JSON had a UTF-8 BOM.** Strict JSON parsing failed before the end-to-end request could run.
   - Rewrote the file as UTF-8 without BOM.
   - Added `tests/test_demo.py` to verify JSON parsing, required fields, 169 rows and exact hourly continuity.
2. **Production TypeScript compilation included test-only Node imports.** The new integration tests caused `npm run build` to fail.
   - Excluded `src/**/*.test.ts`, `src/**/*.test.tsx` and `src/test` from `tsconfig.app.json`.
   - Vitest continues to compile and execute the excluded test files.
3. **React Testing Library lacked shared cleanup.** Consecutive app-state tests left multiple dashboards mounted.
   - Added `afterEach(cleanup)` to `src/test/setup.ts`.
4. **Integration fixture path used a browser-style `import.meta.url`.** Vitest/jsdom could not pass it to Node `readFileSync`.
   - Resolved the fixture from the frontend test working directory instead.

After these fixes, Python tests, normal frontend tests, the live integration test, lint and the production build all pass.

## Remaining issues

1. The Starlette `TestClient` deprecation warning should be revisited when compatible FastAPI/Starlette testing dependencies are available; it does not affect current results.
2. Model artifacts are large and generated. A clean deployment must deliver the selected artifacts through Git LFS, a mounted volume or another artifact mechanism.
3. Predictions still require an external source of 169 current contiguous observations; live-weather ingestion is outside this project phase.

## Exact product commands

### Local backend

```powershell
python -m pip install -r requirements.txt -r backend/requirements.txt
uvicorn backend.app.main:app --reload --env-file backend/.env
```

If `backend/.env` has not been created, either copy `backend/.env.example` first or omit `--env-file`; development defaults work from the project root.

### Local frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`, choose `demo/bangalore_recent_observations.json`, and generate the forecast.

### Tests and build

```powershell
python -m pytest
cd frontend
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

### Docker

```powershell
docker compose up --build
```

The verified frontend is available at `http://localhost:5173` and the API at `http://localhost:8000` while the Compose stack is running.
