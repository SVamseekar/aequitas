#!/usr/bin/env bash
# One-command local boot: Postgres (if needed) + FastAPI + Vite frontend.
# Local only — no cloud deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
API_PID=""
COMPOSE_STARTED=0

log() { printf '==> %s\n' "$*"; }
warn() { printf 'warn: %s\n' "$*" >&2; }

cleanup() {
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    log "Stopping API (pid ${API_PID})"
    kill "${API_PID}" 2>/dev/null || true
    wait "${API_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# Load .env if present (does not override already-exported vars)
if [[ -f "$ROOT/.env" ]]; then
  log "Loading .env"
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

export ENVIRONMENT="${ENVIRONMENT:-development}"
export AEQUITAS_DB_PATH="${AEQUITAS_DB_PATH:-data/aequitas.duckdb}"
export AEQUITAS_CORS_ORIGINS="${AEQUITAS_CORS_ORIGINS:-http://localhost:5173}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
export API_PUBLIC_URL="${API_PUBLIC_URL:-http://localhost:8000}"
export SESSION_SECRET="${SESSION_SECRET:-dev-local-session-secret-change-me}"

# Analytics-only local demos: set DEV_AUTH_BYPASS=true so /api/auth/me and
# tenant-scoped routes work without Google OAuth. Never use in production.
if [[ -z "${DEV_AUTH_BYPASS:-}" ]]; then
  export DEV_AUTH_BYPASS=true
  log "DEV_AUTH_BYPASS=true (default for local boot; override in .env if needed)"
fi

pg_ready() {
  # Prefer pg_isready when available; fall back to a TCP probe.
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h localhost -p 5432 >/dev/null 2>&1
    return $?
  fi
  (echo >/dev/tcp/127.0.0.1/5432) >/dev/null 2>&1
}

ensure_postgres() {
  if pg_ready; then
    log "Postgres already listening on :5432"
    if [[ -z "${DATABASE_URL:-}" ]]; then
      # Homebrew peer/local default used by Part A docs
      export DATABASE_URL="postgresql://localhost/aequitas"
      log "DATABASE_URL defaulted to ${DATABASE_URL}"
    fi
    return 0
  fi

  if [[ ! -f "$ROOT/docker-compose.yml" ]]; then
    warn "No Postgres on :5432 and no docker-compose.yml — auth routes may fail"
    warn "Analytics (DuckDB) still works. Install Postgres or add compose."
    return 0
  fi

  if ! command -v docker >/dev/null 2>&1; then
    warn "Docker not found and Postgres not running — start Postgres manually"
    return 0
  fi

  log "Starting Postgres via docker compose"
  docker compose -f "$ROOT/docker-compose.yml" up -d
  COMPOSE_STARTED=1
  export DATABASE_URL="${DATABASE_URL:-postgresql://aequitas:aequitas@localhost:5432/aequitas}"
  log "DATABASE_URL=${DATABASE_URL}"

  for _ in $(seq 1 40); do
    if pg_ready; then
      log "Postgres is ready"
      return 0
    fi
    sleep 0.5
  done
  warn "Postgres did not become ready in time; continuing anyway"
}

ensure_postgres

if [[ ! -f "${AEQUITAS_DB_PATH}" ]]; then
  warn "DuckDB warehouse missing at ${AEQUITAS_DB_PATH}"
  warn "Run: uv run aequitas run   (or your pipeline build) before expecting data"
fi

log "Starting API on http://${API_HOST}:${API_PORT}"
uv run uvicorn aequitas.api.app:app --host "${API_HOST}" --port "${API_PORT}" --reload &
API_PID=$!

# Wait for health (analytics core; does not require Postgres)
log "Waiting for /api/health …"
for _ in $(seq 1 60); do
  if curl -sf "http://${API_HOST}:${API_PORT}/api/health" >/dev/null 2>&1; then
    HEALTH="$(curl -sf "http://${API_HOST}:${API_PORT}/api/health" || true)"
    log "API health: ${HEALTH}"
    break
  fi
  if ! kill -0 "${API_PID}" 2>/dev/null; then
    warn "API process exited early"
    exit 1
  fi
  sleep 0.5
done

if ! curl -sf "http://${API_HOST}:${API_PORT}/api/health" >/dev/null 2>&1; then
  warn "API health not ready after ~30s — check logs above"
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  log "Installing frontend dependencies"
  (cd "$ROOT/frontend" && npm install)
fi

cat <<EOF

────────────────────────────────────────────────────────────
  Aequitas local stack

  API:      http://${API_HOST}:${API_PORT}
  Health:   http://${API_HOST}:${API_PORT}/api/health
  Frontend: http://localhost:${WEB_PORT}  (Vite proxies /api → :${API_PORT})

  ENVIRONMENT=${ENVIRONMENT}
  DEV_AUTH_BYPASS=${DEV_AUTH_BYPASS}
  DATABASE_URL=${DATABASE_URL:-(unset)}

  Smoke:    uv run python scripts/smoke_local.py
  Stop:     Ctrl+C  (API stops with this script; compose Postgres stays up)
────────────────────────────────────────────────────────────

EOF

log "Starting frontend (foreground)"
cd "$ROOT/frontend"
exec npm run dev -- --host 127.0.0.1 --port "${WEB_PORT}"
