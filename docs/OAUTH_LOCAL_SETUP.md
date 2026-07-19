# Google OAuth — local complete setup

## 1. Postgres

```bash
# Option A — Docker Compose (from repo root)
docker compose up -d

# Option B — local Postgres with database `aequitas`
createdb aequitas   # if needed
```

`.env`:

```env
DATABASE_URL=postgresql://aequitas:aequitas@localhost:5432/aequitas
# or: postgresql://localhost/aequitas
SESSION_SECRET=$(openssl rand -hex 32)
```

Schema is applied on API startup (migrations in auth package). Confirm tables: `users`, `tenants`, `sessions`, `memberships`, …

## 2. Google Cloud OAuth client

1. https://console.cloud.google.com/apis/credentials  
2. Create **OAuth 2.0 Client ID** (Web application)  
3. Authorized JavaScript origins: `http://localhost:5173`  
4. Authorized redirect URIs: **`http://localhost:8000/api/auth/callback/google`**  
5. Copy Client ID + Secret into `.env`:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
FRONTEND_URL=http://localhost:5173
API_PUBLIC_URL=http://localhost:8000
AEQUITAS_CORS_ORIGINS=http://localhost:5173
ENVIRONMENT=development
DEV_AUTH_BYPASS=false
```

## 3. Run

```bash
./scripts/dev.sh
# open http://localhost:5173/auth → Continue with Google
```

## 4. Verify

| Check | Expected |
|---|---|
| GET `/api/auth/login/google` without keys | 503 clear message |
| With keys | Redirect to Google |
| After consent | Cookie set; `/api/auth/me` returns user + tenant |
| Dashboard | Loads with session |
| Logout | POST `/api/auth/logout` clears cookie |

## 5. Demo without Google

```env
DEV_AUTH_BYPASS=true
ENVIRONMENT=development
```

`/api/auth/me` returns synthetic dev user. **Never** enable in production.

## 6. Production OAuth (when API is hosted)

- Redirect URI: `https://<api-host>/api/auth/callback/google`  
- `FRONTEND_URL=https://aequitas.souravamseekar.com`  
- `ENVIRONMENT=production` · `DEV_AUTH_BYPASS=false`  
- Managed Postgres `DATABASE_URL`  
- Cookie `Secure` in production  

Currently **deferred** (no Cloud Run API for billing reasons).
