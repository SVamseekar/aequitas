# Deployment Guidelines

Local-first development with optional production on **Vercel (frontend)** + **Cloud Run (API)**.

---

## 1. Local

```bash
cp .env.example .env
./scripts/dev.sh
# or: uv run uvicorn aequitas.api.app:app --reload --port 8000
#     cd frontend && npm run dev
uv run python scripts/smoke_local.py
```

---

## 2. Backend — Cloud Run

Image bundles DuckDB (`data/aequitas.duckdb`) + FAISS. Use **min instances ≥ 1** to avoid cold-start “sleep”.

```bash
PROJECT=$(gcloud config get-value project)
REGION=europe-west4
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/cloud-run-source-deploy/aequitas-api:latest"

gcloud builds submit --tag "$IMAGE" --timeout=1800s .

gcloud run deploy aequitas-api \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 3 \
  --timeout 300 \
  --set-env-vars "ENVIRONMENT=production,DEV_AUTH_BYPASS=false,AEQUITAS_CORS_ORIGINS=https://aequitas.souravamseekar.com,https://aequitas-gray.vercel.app,FRONTEND_URL=https://aequitas.souravamseekar.com,API_PUBLIC_URL=https://aequitas-api-XXXX.run.app" \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest,SESSION_SECRET=SESSION_SECRET:latest,DATABASE_URL=DATABASE_URL:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest"
```

### Required secrets (Secret Manager)

| Secret | Purpose |
|---|---|
| `GEMINI_API_KEY` | Chat (optional; analytics work without) |
| `SESSION_SECRET` | Cookie signing (required for Google OAuth) |
| `DATABASE_URL` | Postgres for auth/tenancy (Neon/Cloud SQL) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth |

Google OAuth redirect URI must include:  
`{API_PUBLIC_URL}/api/auth/callback/google`

Public analytics (`/api/overview`, `/api/sections`, …) work **without** Postgres. Chat, export, conversations, saved items need auth + DB.

---

## 3. Frontend — Vercel

Project: `aequitas` (`frontend/` root). Domain: `aequitas.souravamseekar.com`.

### Environment variables (Production + Preview)

| Name | Value |
|---|---|
| `VITE_SITE_URL` | `https://aequitas.souravamseekar.com` |
| `NEXT_PUBLIC_GA_MEASUREMENT_ID` | (optional) |
| `DISCORD_CONTACT_WEBHOOK_URL` | contact form (optional) |

### `vercel.json` API proxy

Rewrite `/api/*` to the Cloud Run service URL (see repo `frontend/vercel.json`). After each API URL change, update the rewrite and redeploy frontend.

```bash
cd frontend
npx vercel --prod
```

---

## 4. Smoke production

```bash
curl -sS https://aequitas.souravamseekar.com/api/health
# expect JSON {"status":"ok","warehouse":"connected"} — not HTML

curl -sS 'https://aequitas.souravamseekar.com/api/overview?region=all&urban_rural=all' | head -c 200
```

---

## 5. Explicitly not Vercel

DuckDB + FAISS + sentence-transformers **do not** fit Vercel serverless. API is Cloud Run (or equivalent always-on container). Vercel = static SPA + `/api` reverse-proxy rewrites only.
