# FINAL AUDIT

Status vocabulary: **PASS** = verified by a recorded run or inspection · **PARTIAL** = verified in part, gap stated · **FAIL** = not done / not verified. Nothing is PASS unless it was actually checked. Gate outcomes are recorded in `artifacts/qa_status.json`.

| # | Item | Status | Evidence / caveat |
|---|---|---|---|
| 1 | Research question finalized | **PASS** | `RESEARCH_SPEC_FINAL.md` §2–3 (pre-declared decision rules; deviations listed in §10) |
| 2 | Research gap documented | **PASS** | `RESEARCH_GAP.md`, `GATE_0_5_AUDIT.md`, `PRIOR_ART_MATRIX.md`, `NOVELTY_AUDIT.md` (partial overlap with prior work — stated, not hidden) |
| 3 | Dataset verified | **PASS (scoped)** | Locally generated Tide LI/HI validated: 100 % typology coverage, tail rows, type artefact (`data_quality.json`, `DATA_CARD.md`, `tests/test_data.py`). The Zenodo release and AMLNet were **not** used/unverifiable |
| 4 | Licence documented | **PASS (scoped)** | Tide generator MIT (read from repo); AMLNet CC BY-NC 4.0 (from record); Zenodo-Tide licence **unverified** (`DATA_LICENCE_AUDIT.md`). This repository's own licence is **not chosen** |
| 5 | Data pipeline complete | **PASS** | adapters → validation → features → split → models → engine → export; reproducible via `docs/EXPERIMENTS.md` |
| 6 | Leakage tests complete | **PASS** | future-perturbation, label-independence, name detector, split integrity, scaler/calibrator scope, evidence cut-off; **mutation tests** show leaky builders are caught (`tests/test_leakage.py`) |
| 7 | Temporal evaluation complete | **PASS** | burn-in / train / validation / purge / test with scheme-start rule; strict and all views |
| 8 | Baseline model complete | **PASS** | M1 logistic regression, M2 gradient boosting (T+B) |
| 9 | Main model complete | **PASS** | M3 graph-enhanced gradient boosting; served by the API and reproduced exactly by `/api/predict` |
| 10 | Graph experiment complete | **PASS** | H1 executed with paired scheme-cluster bootstrap; **result: not supported** (`RESULTS.md`) |
| 11 | Ablation complete | **PASS** | T only; without transaction-type features; feature-group ladder |
| 12 | Capacity evaluation complete | **PASS** | m ∈ {0.5, 1, 2, 5} across models and policies |
| 13 | Auto-close evaluation complete | **PASS** | static / rolling / conformal-corrected × α grid, oracle and review-only labels; intervals by scheme resampling; no guarantee claimed |
| 14 | Shift evaluation complete | **PASS (executed; inconclusive)** | leave-one-family-out ran for all 5 families; 1–8 schemes each → **underpowered**, flagged as such |
| 15 | Explainability complete | **PASS** | TreeSHAP sums to margin (test); evidence limited to decision timestamp (tests, incl. shipped bundle); no LLM used |
| 16 | Backend complete | **PASS (local)** | 17 operations, validation, auth option, CORS, rate limit, SQLite decisions/audit; 21 API tests; live server exercised |
| 17 | Frontend complete | **PASS (code/tests/build)** | 8 pages with loading/error/empty/no-results states; **not visually reviewed in a browser** (see rows 30–31) |
| 18 | Demo mode complete | **PASS** | static bundle + browser-local simulated decisions; production server served all routes and bundle files (HTTP 200) |
| 19 | Monitoring complete | **PASS** | backtest replay (labelled "not live monitoring"): volume, score distribution, PSI drift, calibration windows, data quality |
| 20 | Unit tests | **PASS** | Python 75 (0 failed) · Frontend 38 (0 failed) — `TESTING.md` |
| 21 | Integration tests | **PASS** | API tests; experiment smoke tests; 3 frontend live-contract tests against a real uvicorn server |
| 22 | E2E tests | **PARTIAL** | a jsdom workflow test (dashboard → alerts → case → network → decision → updated status) passes; **no real-browser E2E** (Playwright download blocked, no Chromium) |
| 23 | Security review | **PASS** | `SECURITY_REVIEW.md`: code review, tests, scans (npm audit 0, pip-audit none, secret scan clean), live CORS/header checks. Not a penetration test; residual risks listed |
| 24 | Frontend production build | **PASS** | `next build` succeeds (8 routes); `next start` served headers incl. CSP; lint and typecheck clean |
| 25 | Backend production health | **FAIL** | not deployed. Local `/health` verified (status ok, model loaded). Dockerfile **not built** (no Docker daemon); its import closure is exercised in the ZIP verification |
| 26 | Vercel deployment | **FAIL** | not performed — requires your Vercel account (`DEPLOYMENT.md`) |
| 27 | Production smoke test | **FAIL** | not run; commands prepared in `DEPLOYMENT.md` |
| 28 | Documentation complete | **PASS** | all documents in the required list exist; `RESULTS.md` and `API.md` are generated; numbers quoted elsewhere were cross-checked against run files |
| 29 | Final ZIP verified | **PASS** | `python scripts/build_zip.py verify` (integrity, every SHA-256 vs `MANIFEST_SHA256.txt`, required files present, no excluded content) **and** the clean-room run `sh scripts/verify_clean_room.sh` (extract → fresh venv → `pip install -r requirements.txt` → ruff, mypy, pytest → API-only venv + the Dockerfile's `COPY` set → health / `/api/simulate` / `/api/predict` / CORS → `npm ci` → lint, typecheck, tests, build). Run against the exact delivered ZIP; its SHA-256 is reported alongside the release, not inside it. An earlier build **failed** this check (it omitted `riskgraph/data/`); the packaging bug and its guard are documented in `TESTING.md` |
| 30 | Real-browser visual review / screenshots | **FAIL** | no browser available; README says so |
| 31 | CSP behaviour in a browser | **FAIL** | header inspected only; check the console after the first deploy |
| 32 | GitHub CI executed | **FAIL** | workflow written, never run |

## Research truthfulness
Reported as measured: H1 not supported; H2 underpowered; H3 differences visible on HI (15 schemes) and not separable on LI (8 schemes); a large share of signal is a generator artefact; calibration skill is modest; capacity, not auto-close, limits recall. No metric was typed into the UI or docs by hand.

## What is needed from you
1. Vercel + backend-host accounts to complete rows 25–27 (steps in `DEPLOYMENT.md`).
2. A licence choice for this repository's own code.
3. Optionally, a machine with a browser to add screenshots and a real E2E run.
