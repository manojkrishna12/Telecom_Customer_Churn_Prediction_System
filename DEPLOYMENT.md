# Deployment Guide

This project deploys as two free-tier services with no database and no auth:

| Piece | Platform | Why |
|---|---|---|
| FastAPI backend | **Render** (free web service) | Native Python runtime; **build step can run `python -m ml.train`** to regenerate the gitignored 34 MB model artifact on the server — no artifact in git, no Docker needed. `render.yaml` blueprint included. |
| React frontend | **Netlify** (free static hosting) | Vite outputs static files; drag-and-drop or Git-based deploys; env var set in UI at build time so no localhost leaks into the production bundle. |

The two services talk over public HTTPS. No database is used (the model is a
single joblib file loaded at startup). No authentication.

## Model artifact strategy

`ml/artifacts/` is gitignored (model.joblib ≈ 34 MB). The Render service's
build command runs `python -m ml.train`, which regenerates all artifacts with
the exact committed training code (same split, same metrics, same selected
model). Nothing about the ML methodology changes for deployment.

## Backend (Render)

1. Push this repository to GitHub (already done).
2. Render dashboard → **New → Blueprint** → select
   `Telecom_Customer_Churn_Prediction_System` → Apply. Render reads
   `render.yaml` and creates the `churn-api` service.
3. First build takes ~5–8 min (dependency install + training). Watch the log
   for `Selected model: voting_ensemble`.
4. Note the service URL, e.g. `https://churn-api-xxxx.onrender.com`.
   Test: `GET /health` should return `{"status":"ok","model_loaded":true,...}`.
5. After the frontend exists (next section), set the env var
   **`CORS_ALLOW_ORIGINS`** to the frontend URL and let it redeploy.

## Frontend (Netlify)

Build settings live in the repo's root `netlify.toml` and override the UI —
no manual configuration is required:

- **Base directory** `frontend` — scopes dependency detection, dependency
  installation and the build to the frontend only. This is what stops Netlify
  from scanning the repo root, finding the root `requirements.txt` (the
  FastAPI/ML backend's dependencies) and failing its Python 3.14 installer on
  `scikit-learn==1.4.2`. The root requirements.txt stays untouched for Render.
- **Build command** `npm run build`, **Publish directory** `dist`
  (relative to the base, i.e. `frontend/dist`).
- `VITE_API_BASE_URL` is set in `netlify.toml` to the Render backend URL, so
  every production build targets the deployed API (no localhost in the bundle).

1. Netlify dashboard → **Add new site → Import an existing project** → pick
   the GitHub repo → Deploy. The `netlify.toml` settings apply automatically.
2. If your site was created *before* `netlify.toml` existed, open
   **Project configuration → Build & deploy → Build settings** once and clear
   any conflicting manually-set values (the toml takes precedence, but the UI
   may show stale fields).
3. Note the URL, e.g. `https://<site>.netlify.app`.
4. Go back to Render and set `CORS_ALLOW_ORIGINS=https://<site>.netlify.app`,
   then redeploy the backend (Environment → save → automatic redeploy).

## Order matters

Backend first (its URL is a frontend build-time env var), frontend second,
then one backend env var + redeploy to open CORS. Local development is
unaffected: defaults still point at `http://localhost:8000`.

## Free-tier limitations (actual)

- **Render free**: sleeps after ~15 min without traffic; a cold request takes
  ~50 s (instance wake + model load). 750 free instance-hours/month.
- **Netlify free**: 100 GB bandwidth/month; rebuilds on every push.
- No uptime guarantees — this is a portfolio demo, not production hosting.
