# ARCHITECTURE

RiskGraph EU is an **offline research pipeline** that produces a small, versioned *bundle*, plus a **read-mostly API** and a **Next.js analyst UI** that consume that bundle. No model is trained at request time.

```text
                 OFFLINE (Python, single core)                                   ONLINE
 ┌───────────────┐   ┌─────────────┐   ┌──────────────┐   ┌───────────┐   ┌──────────────┐   ┌─────────────┐
 │ Tide generator│──▶│ Adapter +   │──▶│ Account-day  │──▶│ Split +   │──▶│ Models (LR / │──▶│ Decision    │
 │ (MIT, local)  │   │ validation  │   │ features T B │   │ leakage   │   │ LightGBM)    │   │ engine      │
 └───────────────┘   │ riskgraph/  │   │ G M (53)     │   │ checks    │   │ + calibration│   │ REVIEW /    │
                     │ data        │   │ riskgraph/   │   │ split.py  │   │ models.py    │   │ BACKLOG /   │
                     └─────────────┘   │ features     │   └───────────┘   └──────────────┘   │ AUTO-CLOSE  │
                                       └──────────────┘                                      └──────┬──────┘
                                                                                                    │
   experiments.py (H1/H2/H3) ──▶ artifacts/runs/<run_id>/  (manifest, h1/h2/h3 JSON, scores, model)  │
                                        │                                                           │
                                        ▼                                                           │
                       scripts/build_bundle.py  ──▶  artifacts/demo/{LI,HI}/  ◀────────────────────┘
                          (queue sample, SHAP, evidence, monitoring replay, model, score stream)
                                        │                                   │
                        ┌───────────────┴───────────┐           ┌───────────┴──────────────┐
                        ▼                           ▼           ▼                          
              frontend/public/demo/*.json   backend/ (FastAPI)  ── loads bundle read-only; SQLite for decisions/audit
              (DEMO MODE: static, works      /api/*                                          
               without any server)           ▲                                               
                        ▲                    │ NEXT_PUBLIC_API_URL                          
                        └──────── Next.js UI ┘  (LIVE MODE)
```

## Components
| Layer | Location | Responsibility |
|---|---|---|
| Data adapters | `riskgraph/data/` | Canonical `TxData`; Tide adapter (excludes node attributes that leak the target); experimental AMLNet adapter; synthetic test fixture; validation report |
| Features | `riskgraph/features/build.py` | 53 time-respecting account-day features in four groups; a registry with definition per feature |
| Split / leakage | `riskgraph/split.py`, `leakage.py` | Temporal blocks, scheme-start rule, future-perturbation / label-independence / split-integrity checks |
| Models | `riskgraph/models.py` | Logistic regression, LightGBM (fixed hyper-parameters), Platt calibration on validation only |
| Decision engine | `riskgraph/decision.py` | Capacity-constrained queue; static / rolling / conformal-corrected policies; measures (never assumes) tolerance violation |
| Explanations | `riskgraph/explain.py` | TreeSHAP (`pred_contrib`), reason codes, time-respecting evidence |
| Experiments | `riskgraph/experiments.py`, `runs.py` | H1/H2/H3 stages with scheme-cluster bootstrap; run manifests |
| Export | `riskgraph/export.py` | The application bundle |
| API | `backend/app/` | Validated, rate-limited, read-mostly JSON API; decisions + audit in SQLite |
| UI | `frontend/` | 8 pages; **demo backend** (static bundle + browser-local simulated decisions) or **live backend** (API) selected at runtime |

## Two runtime modes
* **DEMO MODE** (default on a public deployment, no `NEXT_PUBLIC_API_URL`): all data comes from `/demo/*.json`; analyst decisions are stored in the visitor's `localStorage` and labelled *simulated feedback*. Needs no Python at all.
* **LIVE MODE**: the same UI talks to the FastAPI service; decisions are written to SQLite with an audit trail. `POST /api/simulate` and `POST /api/predict` recompute on the server.

## Design decisions worth knowing
* **Unit of analysis:** case = (account, day). **Decision timestamp = end of day d.** Windows are trailing sums over a dense account×day tensor, so a feature at day *d* cannot see later data; the test-suite proves it with a mutation test.
* **One score, one threshold space:** ranking and auto-close thresholds use the raw model score; the Platt-calibrated probability is for display and calibration analysis.
* **API imports only `riskgraph/{config,decision,reasons}.py`** (numpy-only), keeping the container small (see `backend/Dockerfile`).
* **Precompute, don't train online:** the expensive work (features 27 s on one core for LI; a full experiment run ≈ 8–9 min) is offline. Measured API latency on the shipped bundle: ≈ 1–2 ms for reads once warm, ≈ 0.35 s for a cold `/api/simulate` (cached afterwards), ≈ 65 ms average for `/api/predict` including HTTP.
* **No GNN**, no MLflow, no feature store: not justified by the evidence or the compute (see `METHODOLOGY.md`).
