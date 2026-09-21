# PROJECT MANIFEST — RiskGraph EU (final build)

Generated 2026-09-21T14:15:07+00:00 by `scripts/build_zip.py`.

## Version / provenance
* Pipeline 1.0.0 · feature version fv1 · API 1.0.0 · no VCS commit (the build environment had no repository); **source-tree hash** (SHA-256 over sorted file hashes): `4a8a9e1a39c612b19901ad63147e9adb966cb36b9001a4aa0ec0d37259e67572`
* Run `Tide-HI-local-fv1-r1` — generator `mntijn/Tide (MIT)` @ `522ccebf266d6a77ddf29e59725d5b27a5a8a0a3`, seed 42, config {'individuals': 1500, 'num_illicit_patterns': 107, 'target_fraud_ratio': 0.0009}
* Run `Tide-LI-local-fv1-r1` — generator `mntijn/Tide (MIT)` @ `522ccebf266d6a77ddf29e59725d5b27a5a8a0a3`, seed 42, config {'individuals': 1500, 'num_illicit_patterns': 60, 'target_fraud_ratio': 0.0005}

## Status
* **Quality gates** (2026-09-21T14:11:37+00:00): PASS ruff check · PASS ruff format --check · PASS mypy · PASS pytest · PASS pip-audit (backend) · PASS eslint · PASS tsc --noEmit · PASS vitest · PASS next build · PASS npm audit
* **Tests:** Python {'tests': 75, 'failures': 0, 'errors': 0, 'skipped': 0} · Frontend {'tests': 38, 'passed': 38, 'failed': 0, 'skipped': 0, 'live_contract_included': True}
* **Build:** `next build` succeeded (8 routes); production server started and all routes returned HTTP 200 locally.
* **Deployment:** **NOT DEPLOYED** (no Vercel/Render account available to the build). No public URLs.
* **This ZIP:** verified by `scripts/build_zip.py verify` and the clean-room run `scripts/verify_clean_room.sh` against this exact file (its SHA-256 is reported with the release, not inside the archive)

## Included directories (file counts)
* repository root — 6
* `.github/` — 1
* `artifacts/` — 35
* `backend/` — 13
* `docs/` — 24
* `frontend/` — 68
* `ml/` — 2
* `riskgraph/` — 19
* `scripts/` — 9
* `tests/` — 11

## Important files
* `README.md` — recruiter-facing overview, honest findings, quick start
* `requirements.txt` — Python dependencies (tested lower bounds)
* `pyproject.toml` — ruff / mypy / pytest configuration
* `render.yaml` — Render blueprint for the API (not applied)
* `.env.example` — environment variable template (no secrets)
* `.github/workflows/ci.yml` — CI mirroring local gates (not executed)
* `riskgraph/features/build.py` — time-respecting account-day feature engine + registry
* `riskgraph/decision.py` — capacity-constrained decision engine, 3 auto-close policies
* `riskgraph/experiments.py` — H1/H2/H3 experiment stages
* `riskgraph/leakage.py` — automated leakage checks
* `riskgraph/export.py` — application-bundle exporter
* `backend/app/api.py` — FastAPI routes
* `backend/Dockerfile` — API container (not built in the build environment)
* `frontend/lib/api.ts` — demo/live backend abstraction
* `frontend/next.config.ts` — security headers / CSP
* `scripts/run_qa.py` — runs and records every quality gate
* `scripts/build_zip.py` — this packaging tool
* `artifacts/qa_status.json` — recorded outcome of the quality gates
* `artifacts/results_manifest.json` — every reported figure traced to run/dataset/split/model/seed/source file
* `docs/RESEARCH_SPEC_FINAL.md` — source of truth for the research design
* `docs/RESULTS.md` — generated results
* `docs/FINAL_AUDIT.md` — PASS/FAIL checklist with evidence

## Intentionally excluded
* `.git`, `node_modules`, `.next`, virtual environments, `__pycache__`, tool caches — rebuildable; not source
* `data/` (raw/interim Tide files, feature caches — ≈ 590 MB) — regenerable with `scripts/generate_tide.py`; raw datasets are never committed
* `artifacts/runs/*/scores_*.npz`, `artifacts/runs/*/model_main.txt` — large/regenerable; the run JSON + manifests ARE included; the served model is in `artifacts/demo/*/model/`
* `.env`, `*.pem`, `*.key`, `*.db` — secrets / local state (none present)
* `*.zip` (including the superseded Gate 0.5 archive), logs, `tsconfig.tsbuildinfo`, `next-env.d.ts` — build/derived files

## SHA-256 of important artefacts (all files: `MANIFEST_SHA256.txt`)
| File | SHA-256 |
|---|---|
| `artifacts/demo/HI/manifest.json` | `cf42306bf2ac07867520a0b32ebb6aa7ad991d75e2f959a5305044c7820f73d6` |
| `artifacts/demo/HI/metrics.json` | `fcd51d9272ad887b6a87531e75d150105890774ebeb02390e78008f329905c80` |
| `artifacts/demo/HI/model/model_main.txt` | `bc209e02f86f0c61286416f82519f062babe0c5a72288991d180858bb435a9d6` |
| `artifacts/demo/HI/model/stream.npz` | `204addf90c6957d440987bb6c6bab9690d6f33f5805737f06629453a66e85181` |
| `artifacts/demo/HI/summary.json` | `89d89aab57d5689bcbfa462914e5077b2ea62ab1fad902219b53f775456b5cff` |
| `artifacts/demo/LI/manifest.json` | `8e804a1916da5f50a5725872e7b75eea175048d90e43e482e54fb8fff6ea3e03` |
| `artifacts/demo/LI/metrics.json` | `22e8b2eb72d23fb4af0c1c6f4e0d99bcc59c97e457f7e139e954dbb0114e75f5` |
| `artifacts/demo/LI/model/model_main.txt` | `74f7865903d2547ae30cbeede6a458d4871ede4a5bf10d6f5b478d9aad7106da` |
| `artifacts/demo/LI/model/stream.npz` | `6c8c79d9625447f224fc7888122a139b3d19edaa8eb085f38aaa9139644cb011` |
| `artifacts/demo/LI/summary.json` | `4350dc41e1a871ab8e0b5684080435480286af236d99c7c7d2cdbccf8cbccea9` |
| `artifacts/qa_status.json` | `85ed1558e8f62a959525df16da716048f247ded3bf0ce1ad9ba0d37cffb5f1dc` |
| `artifacts/results_manifest.json` | `75dfc50052f338ad6a9ae0ad103b4283ba9bff1ce45df49c6e905d5eb9a030ea` |
| `artifacts/runs/Tide-HI-local-fv1-r1/manifest.json` | `cf42306bf2ac07867520a0b32ebb6aa7ad991d75e2f959a5305044c7820f73d6` |
| `artifacts/runs/Tide-LI-local-fv1-r1/manifest.json` | `8e804a1916da5f50a5725872e7b75eea175048d90e43e482e54fb8fff6ea3e03` |
| `docs/RESEARCH_SPEC_FINAL.md` | `28454865caac40b3d5aae2ab4ed19137e203fe3ac83b05b3acf8cfded8c8ac67` |
| `docs/RESULTS.md` | `40ab9fe54371f463f2911f725b569628b416c7f535f319863f716ce277001060` |
| `frontend/package-lock.json` | `a71b8cc899ccfb3ce11517de1fcba0fc25e350efd0e3b0d30abd270e937b3436` |
| `requirements.txt` | `fc75636c158871bd9063ace633778edb4c968e1a38793041fb9ea9b7240b07e0` |
