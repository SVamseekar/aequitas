# Aequitas API — FastAPI + DuckDB + FAISS for Cloud Run (CPU)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl g++ \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY src ./src

# UV_TORCH_BACKEND=cpu prevents multi-GB CUDA wheels
RUN pip install --no-cache-dir uv \
    && UV_TORCH_BACKEND=cpu uv sync --frozen --no-dev

COPY data/aequitas.duckdb data/faiss_index.bin data/faiss_metadata.json ./data/

ENV AEQUITAS_DB_PATH=data/aequitas.duckdb \
    AEQUITAS_FAISS_INDEX=data/faiss_index.bin \
    AEQUITAS_FAISS_METADATA=data/faiss_metadata.json \
    ENVIRONMENT=production \
    DEV_AUTH_BYPASS=false \
    PORT=8000 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    UV_TORCH_BACKEND=cpu

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health" || exit 1

CMD ["sh", "-c", "uv run uvicorn aequitas.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
