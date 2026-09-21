# SECURITY REVIEW

**Scope:** FastAPI service (`backend/`), Next.js UI (`frontend/`), build/deploy config, dependencies.
**Method:** code review + automated tests + tool scans + live checks against a running server. **Not** a penetration test.
**Date:** 2026-09-21. **Deployment status:** not deployed by this build, so nothing here was checked against a public host.

## Summary
No critical or high findings in the reviewed code. The main residual risks are *architectural for a public demo*: anonymous decision writes, in-memory rate limiting, and an ephemeral database. They are acceptable for a synthetic-data portfolio demo and **must be replaced before any real use**.

## Checks and evidence
| Area | Result | Evidence |
|---|---|---|
| Secret exposure | **Pass** | Regex scan of the repository (excluding dependencies and generated data) found no keys/tokens/private keys; no `.env` file present; `.gitignore` excludes `.env*`; the only browser-visible variable is `NEXT_PUBLIC_API_URL` (public by design); no other `process.env` use in `frontend/` |
| Input validation | **Pass** | Pydantic v2 models with `extra="forbid"`, enums, bounds, length caps, regex on `case_id` and `analyst`; 422 tests for each rule (`backend/tests/test_api.py`) |
| SQL injection | **Pass** | Only parameterised SQLite statements (`store.py`); test sends `'; DROP TABLE decisions;--` as a query and as an analyst name, and a quote-injection in a path — all inert/422 |
| XSS | **Pass (code)** / **Untested in browser** | No `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`, `document.write` in `frontend/`; React escapes all interpolated text; `next/link` hrefs are relative paths (`/alerts/${id}`) so an ID cannot become a `javascript:` URL |
| Content-Security-Policy | **Partial** | `default-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`, `connect-src` limited to `'self'` + the configured API origin; **`script-src` allows `'unsafe-inline'`** because Next.js injects inline hydration scripts (a nonce-based CSP needs dynamic rendering). Verified on a production `next start` by `curl -I`; **not exercised in a browser** — check the console after the first deploy |
| Other headers | **Pass** | Frontend: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, HSTS, no `X-Powered-By`. API: `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control: no-store` on writes (tests) |
| CORS | **Pass** | Exact-origin allow-list from `RISKGRAPH_CORS_ORIGINS`, no credentials, methods `GET/POST/OPTIONS`; tests plus a live preflight: allowed origin echoed, foreign origin gets no CORS header |
| AuthN / AuthZ | **Residual risk (by design)** | Public demo: no authentication. Optional `RISKGRAPH_API_KEY` protects `POST …/decision` and `GET /api/audit` (tests: 401 without/with wrong key). A browser-embedded key would not be secret, so the demo does not use it. Real use needs proper authentication (e.g. OIDC) and per-analyst attribution |
| CSRF | **Not applicable** | No cookies or ambient credentials; state-changing calls need a JSON body and (optionally) a custom header; CORS restricts browsers |
| Rate limiting / abuse | **Residual risk** | In-memory sliding window per client address (default 120/min; `/health` exempt; test verifies 429 + `Retry-After`). It is per-process and, behind a proxy, all clients may share one address (uvicorn trusts forwarded headers only from loopback by default — set `FORWARDED_ALLOW_IPS` deliberately after confirming the host's proxy topology). Use the platform's edge limits for real protection |
| Resource exhaustion | **Partial** | `/api/simulate` inputs bounded (α ∈ (0, 0.5], m ∈ [0.1, 10]) and results cached (cold ≈ 0.35 s measured); `/api/predict` accepts ≤ 200 features; **no explicit request-body size limit** in the app — rely on the host/proxy limit |
| Error-message leakage | **Pass** | Global handler returns `{"detail":"internal server error","request_id"}`; test asserts no exception text or path leaks |
| Logging | **Pass with caveat** | Request bodies are not logged. Decision notes (≤ 500 chars) are stored as typed — users must not enter personal data (`RESPONSIBLE_USE.md`) |
| File upload | **N/A** | No upload endpoints |
| SSRF / deserialisation | **Pass** | The API makes no outbound requests; `np.load` uses the default `allow_pickle=False`; model/bundle files are trusted build artefacts loaded from a fixed directory |
| Dependencies | **Pass (at scan time)** | `npm audit`: 0 vulnerabilities; `pip-audit -r backend/requirements.txt`: no known vulnerabilities; `package-lock.json` pins the frontend. Python requirements use lower bounds (`>=`) — **pin them for production** |
| Container | **Pass on inspection** | Non-root user, minimal `COPY`, health check. **Image not built here (no Docker daemon)** |
| Persistence | **Residual risk** | SQLite on a free Render service is ephemeral (documented by Render); decisions are lost on restart. Not a security flaw but a data-integrity limitation |
| OpenAPI docs exposure | **Accepted** | `/docs` is public — appropriate for a synthetic demo; disable for private deployments |

## Not done
Penetration test; threat model beyond the above; browser-based CSP verification; load testing; production-host header verification; dependency review beyond automated advisories.
