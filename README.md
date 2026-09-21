# RiskGraph EU

**Capacity-aware financial-crime alert prioritisation under temporal, prevalence and typology-family shift — an explainable analyst-workflow prototype on synthetic data.**

> RiskGraph EU is a research prototype for financial-risk and financial-crime alert prioritisation using public/synthetic data.
> It is not a replacement for AML investigators, compliance systems, law enforcement, or regulatory validation. It makes no claim about real-world effectiveness, regulatory compliance or savings.

## What it is
A complete pipeline from transactions to an analyst UI:

```text
Tide generator → validation → account-day features (T·B·G·M) → temporal split + leakage checks
  → LightGBM / logistic models → calibration → capacity-constrained decision engine
  (REVIEW · BACKLOG · AUTO-CLOSE) → TreeSHAP explanations + evidence → FastAPI → Next.js analyst UI
```

* **Research question:** under a fixed daily review capacity, how reliably can transaction, behavioural and graph signals prioritise suspicious cases over time — and how does the reliability of calibrated auto-closure change under temporal, prevalence and unseen-typology-family shift?
* **Rigour built in:** every feature is time-respecting by construction *and* proven so by tests (including a mutation test that a deliberately leaky builder is caught); a scheme-start rule stops long-lived schemes contaminating later blocks; all intervals resample whole schemes; no hyper-parameter tuning; deviations from the pre-declared plan are listed openly (`docs/RESEARCH_SPEC_FINAL.md` §10).
* **Two runtime modes:** *demo mode* runs entirely from a static bundle (no server; simulated feedback stored in the browser), *live mode* uses the FastAPI service.

## What it found (synthetic data, small sample — read `docs/RESULTS.md` and `docs/LIMITATIONS.md`)
The results are mostly negative or inconclusive, and are reported that way:

* **Graph context did not help** here: adding graph features to transaction/behaviour features changed recall@K at fixed capacity by −1.9 pp on LI (95 % CI −6.3 … +1.5 pp; 8 independent schemes). H1 is not supported under the pre-declared rule.
* **A generator artefact carries much of the signal:** ~98 % of positives are `transfer` transactions; removing transaction-type features cut recall@K sharply.
* **Family holdout (H2) is underpowered:** 1–8 schemes per held-out family; no pooled claim.
* **Auto-close reliability (H3):** on HI (15 schemes) a static threshold at nominal 10 % tolerance realised 20.7 % missed positives (CI 15.3 – 26.5 %), while the conformal-corrected rule realised 12.4 % (CI 7.2 – 17.5 %). On LI (8 schemes) the intervals are too wide to separate policies. If only reviewed cases' labels are ever known, the conformal rule fails badly. No coverage guarantee is claimed.
* **Capacity dominates:** at the primary capacity roughly 60 % of positives are never reviewed; "workload removed" is dominated by trivially low-risk cases and is **not** an hours-saved estimate.

Every figure above is rendered from recorded runs (`artifacts/runs/*`, `artifacts/results_manifest.json`) by `scripts/render_results.py`.

## Quick start
```bash
# Python (3.12)
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
pytest                                                     # 75 tests
uvicorn backend.app.main:create_app --factory --port 8000  # API on the shipped demo bundle

# Frontend (Node >= 20.9)
cd frontend && npm ci
npm run dev                                                # demo mode: http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev      # live mode
npm run lint && npm run typecheck && npm test && npm run build
```
Rebuild the data and results from scratch (about 20 minutes on one core): see `docs/EXPERIMENTS.md`.

## Repository map
```text
riskgraph/       data adapters · features · split · leakage · models · decision engine · explain · experiments · export
backend/         FastAPI service (+ Dockerfile) and API tests
frontend/        Next.js 16 / React 19 / TypeScript / Tailwind UI (8 pages) and tests
scripts/         generate data · run experiments · build bundle · render results & API docs · manifest / zip
artifacts/demo/  application bundle (real pipeline output on synthetic data); artifacts/runs/  run JSON + manifests
tests/           Python tests · docs/  research and engineering documents · ml/profiling/  legacy Gate 0.5 profiler
render.yaml · .github/workflows/ci.yml · .env.example
```

## Documentation
`docs/RESEARCH_SPEC_FINAL.md` (source of truth) · `METHODOLOGY` · `DATA_CARD` · `MODEL_CARD` · `EXPERIMENTS` · `RESULTS` · `LIMITATIONS` · `RESPONSIBLE_USE` · `ARCHITECTURE` · `API` · `SECURITY_REVIEW` · `TESTING` · `DEPLOYMENT` · `FINAL_AUDIT`, plus the Gate 0.5 research record (`RESEARCH_GAP`, `RESEARCH_DECISION`, `GATE_0_5_AUDIT`, `PRIOR_ART_MATRIX`, `NOVELTY_AUDIT`, `LIT_SEARCH_LOG`, `DATA_LICENCE_AUDIT`, `UNIT_OF_ANALYSIS`).

## Status and honesty notes
* **Not deployed yet.** Vercel/Render steps and smoke tests are in `docs/DEPLOYMENT.md`; they need your accounts. No public URL exists.
* **No screenshots and no real-browser E2E tests:** a browser could not be installed in the build environment. Frontend coverage is jsdom-level plus API contract tests.
* Data are **regenerated locally** with the MIT-licensed Tide generator at reduced scale — not the Zenodo release (unverified licence/size). AMLNet (CC BY-NC 4.0) was verified but not used; its adapter is untested on the real file.
* **Licence:** none chosen yet for this repository's own code — add one before publishing. Third-party: Tide (MIT). No third-party data are redistributed.
