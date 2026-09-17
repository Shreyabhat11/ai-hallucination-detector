# AI Hallucination Detector — Frontend

A standalone React + TypeScript + Tailwind dashboard for the existing
FastAPI backend. Paste an AI-generated answer, get claim-level verification
against evidence, with an explainable breakdown of how the risk score was
computed.

This frontend is read-only against the backend API — it does not modify
backend logic, and every value it displays comes directly from what the
API actually returns. See `src/types/detector.ts` for the exact response
shape this UI assumes.

## Requirements

- Node.js 20+
- The backend running and reachable (locally or deployed)

## Setup

```bash
npm install
cp .env.example .env
# edit .env: set VITE_API_URL to your backend's URL
npm run dev
```

Opens on `http://localhost:5173` by default.

## Scripts

```bash
npm run dev       # local dev server
npm run build     # type-check + production build to dist/
npm run preview   # serve the production build locally
npm run lint       # oxlint
npm run test       # vitest (API client + display-logic unit tests)
```

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `VITE_API_URL` | Base URL of the FastAPI backend, no trailing slash | `http://localhost:8000` |

Set via `.env` locally, or as a build-time environment variable on your
deployment platform (Vercel/Netlify). Vite inlines `VITE_*` vars at build
time, so this must be set *before* `npm run build` runs on the deploy
platform, not just at runtime.

## Required backend configuration (not made by this frontend)

The backend's CORS policy (`ALLOWED_ORIGINS` in `app/config.py`) is
env-var-configurable but defaults to `http://localhost:8501` (the old
Streamlit dev port). For this frontend to be able to call the API from the
browser, set on the backend's deployment (e.g. Render):

```
ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend-domain.vercel.app
```

This is a deployment configuration change, not a backend code change — no
backend files were modified to build this frontend.

## Deployment (Vercel or Netlify)

1. Push this repo (or just the `frontend/` directory as its own project)
2. Import into Vercel/Netlify
3. Build command: `npm run build`, output directory: `dist`
4. Set `VITE_API_URL` as a build-time environment variable in the
   platform's project settings
5. Set the backend's `ALLOWED_ORIGINS` to include the deployed frontend URL
   (see above) — do this before/at the same time as deploying, or the
   deployed frontend will get CORS errors calling the API

## What this UI does and doesn't do

- Shows only fields the backend actually returns — nothing is invented.
  `logic_ms` / `cross_model_ms` are absent (not zero) in Quick mode since
  those checks are skipped, and the UI reflects that explicitly rather
  than showing a fake `0ms`.
- The loading state is an indeterminate spinner with a generic message,
  not a fake per-stage checklist — the backend is a single synchronous
  request and doesn't stream progress, so a "✓ Extracting claims" style
  live stepper would be fabricated.
- Risk-score bands (Low/Medium/High) and the "heuristic, not calibrated"
  language mirror how the backend's own scoring module (`app/detector/scoring.py`)
  describes itself.
