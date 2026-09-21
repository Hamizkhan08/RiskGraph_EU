# DEPLOYMENT

## Status (honest)
| Item | Status |
|---|---|
| Frontend on Vercel | **NOT DEPLOYED** — needs your Vercel account |
| Backend on a Python host | **NOT DEPLOYED** — needs your Render (or other) account |
| Public demo URL | _none yet_ |
| Production API URL | _none yet_ |
| Production smoke test | **NOT RUN** |

Everything below was prepared and checked locally; the live steps must be performed with your accounts. When done, record the URLs in this file.

## Local run (verified)
```bash
# API  (serves artifacts/demo; SQLite decisions in ./riskgraph_decisions.db)
python -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements.txt
uvicorn backend.app.main:create_app --factory --port 8000
# UI, DEMO MODE (no server needed)
cd frontend && npm ci && npm run dev             # http://localhost:3000
# UI, LIVE MODE against the local API
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```
Quality gates: `npm run lint && npm run typecheck && npm test && npm run build` (frontend) · `ruff check . && mypy riskgraph backend/app scripts && pytest` (Python).

## Backend → Render (recommended)
`render.yaml` is a blueprint using `backend/Dockerfile`. Facts checked against Render's documentation (2026-09-21, `render.com/docs/free`, updated Aug 2026): free web services **spin down after 15 minutes without traffic and take ≈ 1 minute to start**; the **filesystem is ephemeral** (local SQLite is lost on restart/redeploy/spin-down); 750 free instance hours/month. Consequences: the first request after idle is slow, and analyst decisions do not persist on the free plan (use a paid disk or an external database if you need persistence — a Postgres store is **not implemented**).

1. Push the repository to GitHub.  2. Render → *New → Blueprint* → select the repo (uses `render.yaml`).
3. Set `RISKGRAPH_CORS_ORIGINS` to the exact Vercel origin (e.g. `https://<project>.vercel.app`). 4. Deploy; check `https://<service>.onrender.com/health`.

| Variable | Where | Value |
|---|---|---|
| `RISKGRAPH_DEMO_MODE` | API | `true` (decisions labelled *simulated*) |
| `RISKGRAPH_CORS_ORIGINS` | API | exact origin(s), comma-separated |
| `RISKGRAPH_RATE_LIMIT_PER_MIN` | API | `120` |
| `RISKGRAPH_API_KEY` | API (secret) | optional; protects decision writes and `/api/audit` |
| `FORWARDED_ALLOW_IPS` | API | set only after confirming the proxy topology (see `SECURITY_REVIEW.md`) |
| `NEXT_PUBLIC_API_URL` | Frontend (public) | `https://<service>.onrender.com`; **leave empty for pure demo mode** |

Start command (Dockerfile): `uvicorn backend.app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers`. Health endpoint: `/health`.

## Frontend → Vercel
1. Import the repo; **Root Directory: `frontend`**; framework preset *Next.js*; default build/output settings.
2. Node.js: Next 16 requires ≥ 20.9 (`engines` is set); Vercel defaults new projects to the latest LTS and lets you pick a version under *Settings → Build and Deployment*; choose 22.x.
3. Add `NEXT_PUBLIC_API_URL` only if you want live mode. Without it the app runs entirely from the static bundle in `/demo`.
4. Vercel's Hobby plan is for personal, non-commercial use (per reports of Vercel's terms — confirm on vercel.com before relying on it).

## Production smoke test (run after deploying)
```bash
API=https://<service>.onrender.com; UI=https://<project>.vercel.app
curl -fsS $API/health                                                   # status ok, datasets LI+HI, model_loaded true
curl -fsS "$API/api/alerts?page_size=2&sort=score"                      # data returns
curl -si -X OPTIONS $API/api/alerts -H "Origin: $UI" -H "Access-Control-Request-Method: GET" | grep -i allow-origin   # echoes $UI
curl -sI $UI | grep -i content-security-policy                          # header present
# then open $UI in a browser: Dashboard → Alerts → a case → Network → record a decision; check the console for CSP violations
```
Static assets `frontend/public/demo` are ≈ 6 MB; the client JavaScript is ≈ 346 KB gzipped (measured).

## Rollback
Vercel: promote a previous deployment. Render: roll back from the service's *Deploys* tab.
