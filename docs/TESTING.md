# TESTING

Counts below were measured on 2026-09-21 from machine-readable reports (`pytest --junitxml`, `vitest --reporter=json`).

| Suite | Tests | Result |
|---|---:|---|
| Python core (`tests/`) | 54 | pass — features 8, leakage 7, decision 11, metrics 5, explain 5, data/adapters 5, experiments smoke 4, split 2, legacy profiler 7 |
| Backend API (`backend/tests/`) | 21 | pass — every endpoint, validation, auth, CORS, rate limit, error leakage, SQL-injection attempts, `/api/predict`, `/api/simulate`, and a consistency check of the **shipped** bundle |
| **Python total** | **75** | **0 failed, 0 skipped** |
| Frontend (`frontend/test/`) | 38 | pass — pages (dashboard, alerts filters/sort/pagination/no-results, case decision flow, performance), network graph, formatting/API client, security headers, one jsdom analyst workflow, **3 live-contract tests against a real uvicorn server** |

## Quality gates (last run)
`ruff check` clean · `ruff format --check` clean · `mypy riskgraph backend/app scripts` clean · `eslint` clean · `tsc --noEmit` clean · `next build` succeeds (8 routes) · `npm audit` 0 vulnerabilities · `pip-audit` none.

## What the tests prove
* **Leakage:** future-perturbation invariance (features at day ≤ d identical with or without later data) — and a **mutation test** that a deliberately leaky builder is caught; label independence (same, with a label-using builder caught); forbidden feature names; split integrity; scaler fitted on training rows only; calibration monotone.
* **Exact values:** hand-built graphs check counts, windows (trailing, inclusive), new/reciprocal counterparties, 3-cycles, near-threshold counts.
* **Decision engine:** zones exclusive and exhaustive; daily capacity respected; no-auto-close baseline; conformal thresholds; realised miss ≈ α under i.i.d. and **≫ α under shift** (the engine measures failure); backlog expiry; rolling adapts to shift.
* **Explanations:** TreeSHAP contributions sum to the model margin; evidence never contains transactions after the decision timestamp (also asserted on the shipped bundle).
* **API ↔ pipeline:** `/api/predict` on a stored case's features reproduced its offline score exactly (0.9763 = 0.9763).

## Packaging check that caught a real bug
The clean-room run (`scripts/verify_clean_room.sh`) found that an early ZIP omitted `riskgraph/data/` (the packaging script excluded every directory named `data`, not just the top-level one). A self-consistency check against the ZIP's own manifest had passed. The packager now excludes only the top-level `data/`, and `build_zip.py verify` requires a list of critical files and was shown to reject a ZIP that lacks them.

## Not covered
* **Real-browser end-to-end tests and screenshots** — Playwright's browser download was blocked and no Chromium is installed. The "E2E" test is a jsdom workflow (Dashboard → Alerts → case → network → decision → updated status); it is not a browser test.
* Dockerfile build; deployed-environment smoke tests; load tests; CSP behaviour in a browser.

## Performance (measured locally, single core)
Feature build 27 s and 2.3 GB peak for LI; full experiment run 525 s (LI) / 503 s (HI); API reads ≈ 1–2 ms warm, cold `/api/simulate` ≈ 0.35 s, `/api/predict` ≈ 65 ms average including HTTP; client JS ≈ 346 KB gzipped.

## Run
```bash
pytest                                     # Python (75)
cd frontend && npm test                    # frontend (35 without a live API)
LIVE_API_URL=http://localhost:8000 npm test   # + 3 live-contract tests (start the API first)
```
