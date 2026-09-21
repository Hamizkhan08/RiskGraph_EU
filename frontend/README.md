# RiskGraph EU — frontend

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS 4 · Radix UI · Recharts · d3-force.

```bash
npm install
npm run dev          # http://localhost:3000  (demo mode by default)
npm run lint && npm run typecheck && npm test && npm run build
```

* **Demo mode** (default, no backend needed): reads the static bundle in `public/demo/` — real pipeline output on
  locally generated synthetic Tide-format data. Analyst decisions are *simulated feedback* stored in `localStorage`.
* **Live mode**: set `NEXT_PUBLIC_API_URL` to the FastAPI service (see `../docs/DEPLOYMENT.md`) and use the switch on the Settings page.

Regenerate the demo bundle with `python scripts/build_bundle.py` (repository root). Tests use small fixtures in `test/fixtures/`
and run in jsdom (no real browser is required or used).
