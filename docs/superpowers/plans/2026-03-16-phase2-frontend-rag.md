# Phase 2: Frontend + RAG — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React dashboard (OWID-inspired) + FastAPI backend + Gemini RAG chatbot that lets UK policy makers explore 51 pre-computed bus transport analytics sections across 8 dimensions and 9 regions.

**Architecture:** FastAPI reads pre-computed data from DuckDB (612 rows in section_results + 7 analytics tables). React frontend renders charts via Observable Plot/D3 and maps via MapLibre GL. FAISS index (built at pipeline time) enables RAG retrieval for a Gemini Flash chatbot. Zero runtime analytics — all data is pre-computed.

**Tech Stack:** Python 3.12+, FastAPI, DuckDB, faiss-cpu, sentence-transformers, google-generativeai | React 19, Vite, TypeScript, Tailwind CSS, shadcn/ui, Observable Plot, D3, MapLibre GL, React Router v7, TanStack React Query

**Spec:** `docs/superpowers/specs/2026-03-16-phase2-frontend-rag-design.md`

---

## File Structure

### Backend (new files)

```
src/aequitas/rag/
├── __init__.py
└── index_builder.py          — Build FAISS index from DuckDB narratives (pipeline stage)

src/aequitas/api/
├── __init__.py
├── app.py                    — FastAPI app factory, lifespan, CORS
├── deps.py                   — DI: DuckDB conn, FAISS index, Gemini client, MiniLM model
├── config.py                 — API config: paths, CORS origins, Gemini API key
├── routers/
│   ├── __init__.py
│   ├── overview.py           — GET /api/overview
│   ├── sections.py           — GET /api/sections
│   ├── lsoa.py               — GET /api/lsoa/{table}
│   ├── provenance.py         — GET /api/provenance/{metric_id}
│   └── chat.py               — POST /api/chat (SSE)
├── models/
│   ├── __init__.py
│   ├── requests.py           — ChatRequest, SectionsQuery, LsoaQuery
│   └── responses.py          — OverviewResponse, SectionResponse, ProvenanceResponse
└── services/
    ├── __init__.py
    ├── warehouse.py           — DuckDB query helpers
    └── rag.py                 — FAISS retrieval + Gemini streaming
```

### Frontend (new directory)

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tailwind.config.ts
├── postcss.config.js
├── components.json           — shadcn/ui config
├── public/
│   └── boundaries/
│       └── regions.geojson   — ONS region boundaries (~200KB)
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── vite-env.d.ts
    ├── api/
    │   ├── client.ts
    │   ├── types.ts
    │   └── hooks.ts
    ├── components/
    │   ├── ui/               — shadcn/ui primitives (generated)
    │   ├── layout/
    │   │   ├── AppShell.tsx
    │   │   ├── Header.tsx
    │   │   ├── TabBar.tsx
    │   │   └── FilterDropdowns.tsx
    │   ├── home/
    │   │   ├── HomePage.tsx
    │   │   └── DimensionCard.tsx
    │   ├── dimension/
    │   │   ├── DimensionPage.tsx
    │   │   └── SectionCard.tsx
    │   ├── charts/
    │   │   ├── ChartRenderer.tsx
    │   │   ├── HorizontalBarChart.tsx
    │   │   ├── ScatterRegressionChart.tsx
    │   │   ├── LorenzCurveChart.tsx
    │   │   ├── ShapBarChart.tsx
    │   │   ├── ChoroplethMap.tsx
    │   │   └── DataTable.tsx
    │   ├── chat/
    │   │   ├── ChatDrawer.tsx
    │   │   ├── ChatMessage.tsx
    │   │   └── ChatFAB.tsx
    │   └── shared/
    │       ├── Markdown.tsx
    │       ├── ProvenanceTooltip.tsx  — DEFERRED: hook exists, component added when provenance is widely populated
    │       └── Severity.tsx
    ├── hooks/
    │   └── useChat.ts
    ├── lib/
    │   ├── constants.ts
    │   ├── colours.ts
    │   └── utils.ts          — cn() helper for Tailwind class merging
    └── styles/
        └── globals.css

tests/
├── api/
│   ├── conftest.py           — Test DuckDB, test client fixtures
│   ├── test_overview.py
│   ├── test_sections.py
│   ├── test_lsoa.py
│   ├── test_provenance.py
│   └── test_chat.py
├── rag/
│   └── test_index_builder.py
└── (existing tests unchanged)
```

### Modified files

```
src/aequitas/core/models.py:114       — Fix narrative: dict → str
src/aequitas/warehouse/schema.py:59   — Fix narrative JSON → VARCHAR
src/aequitas/pipeline/_stages.py      — Add run_rag_index() stage
src/aequitas/pipeline/cli.py          — Add `aequitas rag` command
src/aequitas/core/config.py           — Add faiss_index_path, gemini_api_key
pyproject.toml                         — Add faiss-cpu, sentence-transformers, google-generativeai, fastapi, uvicorn, sse-starlette deps
```

---

## Chunk 0: Prerequisites — Narrative Type Fix + Dependencies

### Task 0.1: Fix narrative type in Pydantic model

**Files:**
- Modify: `src/aequitas/core/models.py:114`
- Test: `tests/core/test_models.py`

- [ ] **Step 1: Write test for narrative as string**

```python
# In tests/core/test_models.py — add SectionResult to the existing import line:
#   from aequitas.core.models import BusStop, Route, LSOARecord, RegionSummary, SectionResult

def test_section_result_narrative_is_str():
    """Narrative field must accept a markdown string, not require a dict."""
    result = SectionResult(
        region="all",
        urban_rural="all",
        section_id="f1_gini",
        stats={"gini": 0.5741},
        chart_data={"type": "lorenz_curve"},
        narrative="**Bus service Gini is 0.574** — more unequal than income.",
    )
    assert isinstance(result.narrative, str)
    assert "0.574" in result.narrative
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_models.py::test_section_result_narrative_is_str -v`
Expected: FAIL — Pydantic validation error because `narrative: dict` rejects a string.

- [ ] **Step 3: Fix the model**

In `src/aequitas/core/models.py`, change line 114:

```python
# Before:
narrative: dict
# After:
narrative: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_models.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/core/models.py tests/core/test_models.py
git commit -m "fix(core): SectionResult.narrative type dict → str (markdown string)"
```

### Task 0.2: Fix narrative column in DuckDB schema

**Files:**
- Modify: `src/aequitas/warehouse/schema.py:59`

- [ ] **Step 1: Change JSON to VARCHAR**

In `src/aequitas/warehouse/schema.py`, in the `section_results` CREATE TABLE DDL, change:

```sql
-- Before:
narrative JSON,
-- After:
narrative VARCHAR,
```

- [ ] **Step 2: Run existing warehouse tests**

Run: `python -m pytest tests/warehouse/ -v`
Expected: ALL PASS (narrative was already stored as string; JSON→VARCHAR is compatible)

- [ ] **Step 3: Commit**

```bash
git add src/aequitas/warehouse/schema.py
git commit -m "fix(warehouse): section_results.narrative JSON → VARCHAR (is markdown string)"
```

### Task 0.3: Add Phase 2 Python dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add backend dependencies**

Add to the `[project.dependencies]` list in `pyproject.toml`:

```toml
# API
"fastapi>=0.115.0",
"uvicorn[standard]>=0.32.0",
"sse-starlette>=2.0.0",
# RAG
"faiss-cpu>=1.8.0",
"sentence-transformers>=3.3.0",
"google-generativeai>=0.8.0",
```

- [ ] **Step 2: Install updated deps**

Run: `uv sync` (or `pip install -e ".[dev]"`)
Expected: All new packages install without conflict.

- [ ] **Step 3: Verify imports work**

Run: `python -c "import fastapi; import faiss; import sentence_transformers; import google.generativeai; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add Phase 2 dependencies — FastAPI, FAISS, sentence-transformers, Gemini"
```

### Task 0.4: Add FAISS path + Gemini key to pipeline config

**Files:**
- Modify: `src/aequitas/core/config.py`

- [ ] **Step 1: Add config fields**

Add to the `PipelineConfig` dataclass:

```python
# RAG / API
faiss_index_path: Path = field(default_factory=lambda: Path("data/faiss_index.bin"))
faiss_metadata_path: Path = field(default_factory=lambda: Path("data/faiss_metadata.json"))
gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
api_cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])
```

Add `import os` at top if not already present.

- [ ] **Step 2: Run existing config tests**

Run: `python -m pytest tests/core/ -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add src/aequitas/core/config.py
git commit -m "feat(config): add FAISS paths, Gemini API key, CORS origins"
```

---

## Chunk 1: RAG Index Builder (Pipeline Stage)

### Task 1.1: FAISS index builder — embed narratives + save index

**Files:**
- Create: `src/aequitas/rag/__init__.py`
- Create: `src/aequitas/rag/index_builder.py`
- Test: `tests/rag/test_index_builder.py`

- [ ] **Step 1: Write test for chunking narratives**

```python
# tests/rag/test_index_builder.py
import pytest
from aequitas.rag.index_builder import chunk_narrative, build_faiss_index


def test_chunk_narrative_splits_on_paragraphs():
    text = "First paragraph about equity.\n\nSecond paragraph about Gini.\n\nThird paragraph."
    chunks = chunk_narrative(text, max_tokens=50)
    assert len(chunks) >= 2
    assert all(isinstance(c, str) for c in chunks)
    assert all(len(c.strip()) > 0 for c in chunks)


def test_chunk_narrative_short_text_returns_single():
    text = "Short text."
    chunks = chunk_narrative(text, max_tokens=500)
    assert chunks == ["Short text."]


def test_chunk_narrative_empty_returns_empty():
    chunks = chunk_narrative("", max_tokens=500)
    assert chunks == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/rag/test_index_builder.py::test_chunk_narrative_splits_on_paragraphs -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement index_builder.py**

```python
# src/aequitas/rag/__init__.py
"""RAG pipeline — FAISS index building and retrieval."""

# src/aequitas/rag/index_builder.py
"""Build FAISS index from pre-computed InsightEngine narratives."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import faiss
import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer

from aequitas.core.config import PipelineConfig

_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_EMBEDDING_DIM = 384


def chunk_narrative(text: str, max_tokens: int = 500) -> list[str]:
    """Split narrative into paragraph-aligned chunks.

    Splits on double newlines. If a paragraph exceeds max_tokens (estimated
    as chars/4), it is included as-is (better to have one long chunk than
    break mid-sentence).
    """
    if not text or not text.strip():
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_tokens = len(para) // 4  # rough estimate
        if current and current_len + para_tokens > max_tokens:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = para_tokens
        else:
            current.append(para)
            current_len += para_tokens

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _load_narratives(db_path: Path) -> list[dict]:
    """Load all non-suppressed narratives from section_results."""
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT section_id, region, urban_rural, narrative
            FROM section_results
            WHERE narrative IS NOT NULL AND narrative != ''
            """
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "section_id": r[0],
            "region": r[1],
            "urban_rural": r[2],
            "narrative": r[3],
        }
        for r in rows
    ]


def build_faiss_index(cfg: PipelineConfig) -> dict:
    """Build FAISS index from DuckDB narratives.

    Returns:
        dict with keys: n_narratives, n_chunks, index_path, metadata_path
    """
    logger.info("Loading narratives from DuckDB...")
    narratives = _load_narratives(cfg.warehouse_path)
    logger.info(f"Loaded {len(narratives)} narratives")

    # Chunk
    metadata: list[dict] = []
    texts: list[str] = []
    for row in narratives:
        chunks = chunk_narrative(row["narrative"])
        for chunk in chunks:
            texts.append(chunk)
            metadata.append({
                "section_id": row["section_id"],
                "region": row["region"],
                "urban_rural": row["urban_rural"],
                "text": chunk,
            })

    if not texts:
        logger.warning("No narrative chunks to index")
        return {"n_narratives": 0, "n_chunks": 0}

    logger.info(f"Chunked into {len(texts)} pieces, embedding with {_EMBEDDING_MODEL}...")

    # Embed
    model = SentenceTransformer(_EMBEDDING_MODEL)
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    embeddings_np = np.array(embeddings, dtype=np.float32)

    # Build index
    # Spec says IndexFlatL2 but IndexFlatIP on L2-normalized vectors is equivalent
    # to cosine similarity, which is the standard for sentence-transformers text retrieval.
    index = faiss.IndexFlatIP(embeddings_np.shape[1])
    index.add(embeddings_np)

    # Save
    index_path = cfg.project_root / cfg.faiss_index_path
    metadata_path = cfg.project_root / cfg.faiss_metadata_path
    index_path.parent.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(index_path))
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False))

    logger.info(f"FAISS index saved: {index_path} ({len(texts)} vectors)")
    return {
        "n_narratives": len(narratives),
        "n_chunks": len(texts),
        "index_path": str(index_path),
        "metadata_path": str(metadata_path),
    }
```

- [ ] **Step 4: Run chunking tests**

Run: `python -m pytest tests/rag/test_index_builder.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/rag/ tests/rag/
git commit -m "feat(rag): FAISS index builder — chunk narratives + embed with MiniLM"
```

### Task 1.2: Wire FAISS build into pipeline

**Files:**
- Modify: `src/aequitas/pipeline/_stages.py`
- Modify: `src/aequitas/pipeline/cli.py`

- [ ] **Step 1: Add run_rag_index() stage**

In `src/aequitas/pipeline/_stages.py`, add after `run_validation()`:

```python
def run_rag_index(cfg: PipelineConfig | None = None) -> StageReport:
    """Build FAISS index from DuckDB narratives."""
    if cfg is None:
        cfg = PipelineConfig()

    from aequitas.rag.index_builder import build_faiss_index

    t0 = time.perf_counter()
    result = build_faiss_index(cfg)
    return StageReport(
        stage="rag_index",
        duration_s=time.perf_counter() - t0,
        output_files=[Path(p) for p in [result.get("index_path", ""), result.get("metadata_path", "")] if p],
        checks_passed=1 if result.get("n_chunks", 0) > 0 else 0,
        checks_failed=0 if result.get("n_chunks", 0) > 0 else 1,
    )
```

- [ ] **Step 2: Add CLI command**

In `src/aequitas/pipeline/cli.py`, add:

```python
@main.command()
def rag():
    """Build FAISS index for RAG chatbot."""
    from aequitas.pipeline._stages import run_rag_index
    run_rag_index()
```

Also add `run_rag_index` to the `run` command's stage list (after `run_validation`). In the `run_all()` function, add the import and append to the stages list:

```python
from aequitas.pipeline._stages import (
    run_ingestion, run_processing, run_analytics,
    run_intelligence, run_warehouse, run_validation, run_rag_index,
)
# ... in stages list:
stages = [
    ("ingest", run_ingestion),
    ("process", run_processing),
    ("analytics", run_analytics),
    ("intelligence", run_intelligence),
    ("warehouse", run_warehouse),
    ("validate", run_validation),
    ("rag_index", run_rag_index),  # ← add this
]
```

- [ ] **Step 3: Verify CLI help shows new command**

Run: `python -m aequitas.pipeline --help`
Expected: `rag` appears in the command list.

- [ ] **Step 4: Commit**

```bash
git add src/aequitas/pipeline/_stages.py src/aequitas/pipeline/cli.py
git commit -m "feat(pipeline): add FAISS index build as pipeline stage"
```

---

## Chunk 2: FastAPI Backend — App + Core Endpoints

### Task 2.1: FastAPI app factory + DuckDB lifespan

**Files:**
- Create: `src/aequitas/api/__init__.py`
- Create: `src/aequitas/api/config.py`
- Create: `src/aequitas/api/app.py`
- Create: `src/aequitas/api/deps.py`
- Test: `tests/api/conftest.py`

- [ ] **Step 1: Write test for app startup**

```python
# tests/api/conftest.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Create a test client with a temporary DuckDB."""
    import duckdb

    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE section_results (
            region VARCHAR,
            urban_rural VARCHAR,
            section_id VARCHAR,
            stats JSON,
            chart_data JSON,
            narrative VARCHAR,
            PRIMARY KEY (region, urban_rural, section_id)
        )
    """)
    conn.execute("""
        INSERT INTO section_results VALUES
        ('all', 'all', 'f1_gini', '{"gini": 0.5741}', '{"type": "lorenz_curve"}',
         '**Gini is 0.574.**')
    """)
    conn.execute("""
        CREATE TABLE provenance (
            metric_id VARCHAR PRIMARY KEY,
            value DOUBLE,
            formula VARCHAR,
            inputs JSON,
            source_files VARCHAR[]
        )
    """)
    conn.execute("""
        INSERT INTO provenance VALUES
        ('gini_national', 0.5741, '1 - 2*AUC(lorenz)', '{}', ARRAY['equity.parquet'])
    """)
    conn.close()

    monkeypatch.setenv("AEQUITAS_DB_PATH", str(db_path))
    monkeypatch.setenv("AEQUITAS_FAISS_INDEX", str(tmp_path / "faiss.bin"))
    monkeypatch.setenv("AEQUITAS_FAISS_METADATA", str(tmp_path / "faiss_meta.json"))

    from aequitas.api.app import create_app
    app = create_app()
    with TestClient(app) as client:
        yield client
```

- [ ] **Step 2: Write test for health endpoint**

```python
# tests/api/test_overview.py
def test_health(api_client):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

- [ ] **Step 3: Implement app factory**

```python
# src/aequitas/api/__init__.py
"""FastAPI backend for Aequitas dashboard."""

# src/aequitas/api/config.py
"""API configuration — loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ApiConfig:
    db_path: Path = field(
        default_factory=lambda: Path(os.environ.get("AEQUITAS_DB_PATH", "data/aequitas.duckdb"))
    )
    faiss_index_path: Path = field(
        default_factory=lambda: Path(os.environ.get("AEQUITAS_FAISS_INDEX", "data/faiss_index.bin"))
    )
    faiss_metadata_path: Path = field(
        default_factory=lambda: Path(os.environ.get("AEQUITAS_FAISS_METADATA", "data/faiss_metadata.json"))
    )
    gemini_api_key: str = field(
        default_factory=lambda: os.environ.get("GEMINI_API_KEY", "")
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get(
            "AEQUITAS_CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
    )
```

```python
# src/aequitas/api/deps.py
"""Dependency injection — shared resources loaded at startup."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import duckdb
from loguru import logger

from aequitas.api.config import ApiConfig

_state: dict[str, Any] = {}


def get_db() -> duckdb.DuckDBPyConnection:
    return _state["db"]


def get_faiss():
    return _state.get("faiss_index"), _state.get("faiss_metadata")


def get_embedding_model():
    return _state.get("embedding_model")


@asynccontextmanager
async def lifespan(app):
    """Load DuckDB + FAISS on startup, close on shutdown."""
    cfg = ApiConfig()

    # DuckDB
    logger.info(f"Opening DuckDB: {cfg.db_path}")
    _state["db"] = duckdb.connect(str(cfg.db_path), read_only=True)

    # FAISS (optional — chat won't work without it but dashboard still does)
    if cfg.faiss_index_path.exists():
        import faiss
        logger.info(f"Loading FAISS index: {cfg.faiss_index_path}")
        _state["faiss_index"] = faiss.read_index(str(cfg.faiss_index_path))
        _state["faiss_metadata"] = json.loads(cfg.faiss_metadata_path.read_text())

        from sentence_transformers import SentenceTransformer
        _state["embedding_model"] = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("FAISS + embedding model loaded")
    else:
        logger.warning(f"FAISS index not found at {cfg.faiss_index_path} — chat disabled")

    yield

    _state["db"].close()
    _state.clear()
```

```python
# src/aequitas/api/app.py
"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aequitas.api.config import ApiConfig
from aequitas.api.deps import lifespan


def create_app() -> FastAPI:
    cfg = ApiConfig()
    app = FastAPI(
        title="Aequitas API",
        description="UK bus transport policy intelligence",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Health
    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # Register routers
    from aequitas.api.routers import overview, sections, lsoa, provenance, chat
    app.include_router(overview.router, prefix="/api")
    app.include_router(sections.router, prefix="/api")
    app.include_router(lsoa.router, prefix="/api")
    app.include_router(provenance.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")

    return app
```

- [ ] **Step 4: Create placeholder routers (empty, to avoid import errors)**

```python
# src/aequitas/api/routers/__init__.py
"""API routers."""

# src/aequitas/api/routers/overview.py
from fastapi import APIRouter
router = APIRouter()

# src/aequitas/api/routers/sections.py
from fastapi import APIRouter
router = APIRouter()

# src/aequitas/api/routers/lsoa.py
from fastapi import APIRouter
router = APIRouter()

# src/aequitas/api/routers/provenance.py
from fastapi import APIRouter
router = APIRouter()

# src/aequitas/api/routers/chat.py
from fastapi import APIRouter
router = APIRouter()
```

- [ ] **Step 5: Run test**

Run: `python -m pytest tests/api/test_overview.py::test_health -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/api/ tests/api/
git commit -m "feat(api): FastAPI app factory, DuckDB lifespan, health endpoint"
```

### Task 2.2: Pydantic request/response models

**Files:**
- Create: `src/aequitas/api/models/__init__.py`
- Create: `src/aequitas/api/models/requests.py`
- Create: `src/aequitas/api/models/responses.py`

- [ ] **Step 1: Write response models**

```python
# src/aequitas/api/models/__init__.py
"""Pydantic v2 models for API requests and responses."""

# src/aequitas/api/models/responses.py
from __future__ import annotations
from pydantic import BaseModel


class HeadlineStat(BaseModel):
    value: float
    label: str
    severity: str  # "high", "medium", "low"


class DimensionOverview(BaseModel):
    id: str
    name: str
    headline_stat: HeadlineStat
    summary: str
    route: str


class OverviewResponse(BaseModel):
    dimensions: list[DimensionOverview]


class SectionItem(BaseModel):
    section_id: str
    dimension: str
    stats: dict
    chart_data: dict
    narrative: str
    suppressed: bool


class SectionsResponse(BaseModel):
    dimension: str
    sections: list[SectionItem]


class LsoaResponse(BaseModel):
    rows: list[dict]
    total: int


class ProvenanceResponse(BaseModel):
    metric_id: str
    value: float
    formula: str
    inputs: dict
    source_files: list[str]
```

```python
# src/aequitas/api/models/requests.py
from __future__ import annotations
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    context: dict = Field(default_factory=dict)
    conversation_id: str | None = None
    history: list[dict] = Field(default_factory=list)
```

- [ ] **Step 2: Commit**

```bash
git add src/aequitas/api/models/
git commit -m "feat(api): Pydantic v2 request/response models"
```

### Task 2.3: DuckDB warehouse service

**Files:**
- Create: `src/aequitas/api/services/__init__.py`
- Create: `src/aequitas/api/services/warehouse.py`
- Test: `tests/api/test_sections.py`

- [ ] **Step 1: Write test for sections query**

```python
# tests/api/test_sections.py

# Uses the api_client fixture from conftest.py which seeds f1_gini

def test_get_sections_returns_dimension(api_client):
    resp = api_client.get("/api/sections", params={"dimension": "equity"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dimension"] == "equity"
    assert len(data["sections"]) >= 1
    section = data["sections"][0]
    assert section["section_id"] == "f1_gini"
    assert section["dimension"] == "equity"
    assert "gini" in section["stats"]
    assert section["narrative"].startswith("**")


def test_get_sections_missing_dimension_returns_422(api_client):
    resp = api_client.get("/api/sections")
    assert resp.status_code == 422


def test_get_sections_unknown_dimension_returns_empty(api_client):
    resp = api_client.get("/api/sections", params={"dimension": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json()["sections"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/api/test_sections.py -v`
Expected: FAIL — endpoint not implemented

- [ ] **Step 3: Implement warehouse service**

```python
# src/aequitas/api/services/__init__.py
"""API services."""

# src/aequitas/api/services/warehouse.py
"""DuckDB query helpers — read-only access to pre-computed data."""
from __future__ import annotations

import json
from typing import Any

import duckdb

# Dimension → section_id prefix(es)
DIMENSION_PREFIXES: dict[str, list[str]] = {
    "equity": ["f"],
    "accessibility": ["a"],
    "service_quality": ["b"],
    "route_network": ["c"],
    "correlations": ["d", "g"],
    "economic": ["j"],
    "bus_services_act": ["bsa"],
    "scenarios": ["ps"],
}

# Headline section per dimension (for /api/overview)
HEADLINE_SECTIONS: dict[str, tuple[str, str]] = {
    # dimension: (section_id, stat_key)
    "equity": ("f1_gini", "gini"),
    "accessibility": ("a5_service_deserts", "desert_count"),
    "service_quality": ("b1_frequency", "mean_headway"),
    "route_network": ("c3_operator_hhi", "national_hhi"),
    "correlations": ("d8_feature_importance", "top_feature_importance"),
    "economic": ("j2_bcr", "national_bcr"),
    "bus_services_act": ("bsa1_franchising_readiness", "mean_readiness"),
    "scenarios": ("ps5_scenario_comparison", "best_scenario_bcr"),
}


def query_sections(
    db: duckdb.DuckDBPyConnection,
    dimension: str,
    region: str = "all",
    urban_rural: str = "all",
) -> list[dict[str, Any]]:
    """Query section_results for a dimension's sections."""
    prefixes = DIMENSION_PREFIXES.get(dimension, [])
    if not prefixes:
        return []

    # Build WHERE clause for prefix matching
    prefix_conditions = " OR ".join(
        f"section_id LIKE '{p}%'" for p in prefixes
    )
    rows = db.execute(
        f"""
        SELECT section_id, stats, chart_data, narrative
        FROM section_results
        WHERE ({prefix_conditions})
          AND region = ?
          AND urban_rural = ?
        ORDER BY section_id
        """,
        [region, urban_rural],
    ).fetchall()

    results = []
    for section_id, stats, chart_data, narrative in rows:
        results.append({
            "section_id": section_id,
            "dimension": dimension,
            "stats": json.loads(stats) if isinstance(stats, str) else stats,
            "chart_data": json.loads(chart_data) if isinstance(chart_data, str) else chart_data,
            "narrative": narrative or "",
            "suppressed": not narrative or narrative.strip() == "",
        })
    return results


def query_overview(
    db: duckdb.DuckDBPyConnection,
    region: str = "all",
    urban_rural: str = "all",
) -> list[dict[str, Any]]:
    """Query headline stats for each dimension."""

    results = []
    for dim_id, (section_id, stat_key) in HEADLINE_SECTIONS.items():
        row = db.execute(
            """
            SELECT stats, narrative
            FROM section_results
            WHERE section_id = ? AND region = ? AND urban_rural = ?
            """,
            [section_id, region, urban_rural],
        ).fetchone()

        if row:
            stats = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            value = stats.get(stat_key, 0)
        else:
            value = 0

        results.append({
            "id": dim_id,
            "value": value,
            "stat_key": stat_key,
        })
    return results


ALLOWED_TABLES = {
    "lsoa_service_quality",
    "lsoa_equity_metrics",
    "lsoa_accessibility",
    "lsoa_economic",
    "lsoa_policy",
    "route_details",
    "lta_readiness",
}


def query_lsoa(
    db: duckdb.DuckDBPyConnection,
    table: str,
    region: str | None = None,
    fields: list[str] | None = None,
    limit: int | None = None,
) -> tuple[list[dict], int]:
    """Query LSOA-level analytics table."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' not in allowed list: {ALLOWED_TABLES}")

    # Count
    count_sql = f"SELECT COUNT(*) FROM {table}"
    params: list = []
    if region:
        count_sql += " WHERE region_code = ?"
        params.append(region)
    total = db.execute(count_sql, params).fetchone()[0]

    # Select — validate field names (alphanumeric + underscore only)
    if fields:
        import re
        for f in fields:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", f):
                raise ValueError(f"Invalid field name: '{f}'")
    cols = ", ".join(fields) if fields else "*"
    sql = f"SELECT {cols} FROM {table}"
    params = []
    if region:
        sql += " WHERE region_code = ?"
        params.append(region)
    if limit:
        sql += f" LIMIT {int(limit)}"

    rows = db.execute(sql, params).fetchdf().to_dict(orient="records")
    return rows, total


def query_provenance(
    db: duckdb.DuckDBPyConnection,
    metric_id: str,
) -> dict | None:
    """Query provenance for a metric."""
    row = db.execute(
        "SELECT metric_id, value, formula, inputs, source_files FROM provenance WHERE metric_id = ?",
        [metric_id],
    ).fetchone()
    if not row:
        return None
    return {
        "metric_id": row[0],
        "value": row[1],
        "formula": row[2],
        "inputs": json.loads(row[3]) if isinstance(row[3], str) else row[3],
        "source_files": list(row[4]) if row[4] else [],
    }
```

- [ ] **Step 4: Implement sections router**

```python
# src/aequitas/api/routers/sections.py
from __future__ import annotations

from fastapi import APIRouter, Query

from aequitas.api.deps import get_db
from aequitas.api.models.responses import SectionItem, SectionsResponse
from aequitas.api.services.warehouse import query_sections

router = APIRouter()


@router.get("/sections", response_model=SectionsResponse)
def get_sections(
    dimension: str = Query(..., description="One of 8 dimension IDs"),
    region: str = Query("all", description="'all' or ONS region code"),
    urban_rural: str = Query("all", description="'all', 'urban', or 'rural'"),
):
    db = get_db()
    rows = query_sections(db, dimension, region, urban_rural)
    return SectionsResponse(
        dimension=dimension,
        sections=[SectionItem(**r) for r in rows],
    )
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/api/test_sections.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/api/services/ src/aequitas/api/routers/sections.py tests/api/test_sections.py
git commit -m "feat(api): /api/sections endpoint + warehouse service"
```

### Task 2.4: Overview, LSOA, and Provenance routers

**Files:**
- Modify: `src/aequitas/api/routers/overview.py`
- Modify: `src/aequitas/api/routers/lsoa.py`
- Modify: `src/aequitas/api/routers/provenance.py`
- Test: `tests/api/test_overview.py` (extend), `tests/api/test_lsoa.py`, `tests/api/test_provenance.py`

- [ ] **Step 1: Write tests**

```python
# tests/api/test_overview.py — add to existing file
def test_overview_returns_dimensions(api_client):
    resp = api_client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "dimensions" in data
    assert len(data["dimensions"]) == 8
```

```python
# tests/api/test_provenance.py
def test_provenance_found(api_client):
    resp = api_client.get("/api/provenance/gini_national")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric_id"] == "gini_national"
    assert data["value"] == 0.5741
    assert "AUC" in data["formula"]


def test_provenance_not_found(api_client):
    resp = api_client.get("/api/provenance/nonexistent")
    assert resp.status_code == 404
```

```python
# tests/api/test_lsoa.py
def test_lsoa_invalid_table(api_client):
    resp = api_client.get("/api/lsoa/evil_table")
    assert resp.status_code == 400
```

- [ ] **Step 2: Implement overview router**

```python
# src/aequitas/api/routers/overview.py
from __future__ import annotations

from fastapi import APIRouter, Query

from aequitas.api.deps import get_db
from aequitas.api.models.responses import (
    DimensionOverview, HeadlineStat, OverviewResponse,
)
from aequitas.api.services.warehouse import query_overview

router = APIRouter()

_DIMENSION_META = {
    "equity": ("Equity & Deprivation", "Gini coefficient", "/equity"),
    "accessibility": ("Accessibility", "Service deserts", "/accessibility"),
    "service_quality": ("Service Quality", "Mean headway", "/service-quality"),
    "route_network": ("Route Network", "Operator HHI", "/route-network"),
    "correlations": ("Socio-Economic & ML", "Top SHAP feature", "/correlations"),
    "economic": ("Economic Appraisal", "National BCR", "/economic"),
    "bus_services_act": ("Bus Services Act 2025", "Mean readiness", "/bus-services-act"),
    "scenarios": ("Policy Scenarios", "Best scenario BCR", "/scenarios"),
}


def _severity(dim_id: str, value: float) -> str:
    """Simple severity classification.

    Only 3 dimensions have domain-appropriate thresholds so far.
    Others default to "low" until policy team confirms cutoffs.
    """
    thresholds = {
        "equity": (0.4, 0.3),       # gini > 0.4 = high
        "accessibility": (5000, 3000),
        "service_quality": (30, 15),
    }
    high, med = thresholds.get(dim_id, (float("inf"), float("inf")))
    if value >= high:
        return "high"
    if value >= med:
        return "medium"
    return "low"


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
):
    db = get_db()
    rows = query_overview(db, region, urban_rural)

    dimensions = []
    for row in rows:
        dim_id = row["id"]
        name, label, route = _DIMENSION_META.get(dim_id, (dim_id, "", f"/{dim_id}"))
        dimensions.append(
            DimensionOverview(
                id=dim_id,
                name=name,
                headline_stat=HeadlineStat(
                    value=row["value"],
                    label=label,
                    severity=_severity(dim_id, row["value"]),
                ),
                summary="",  # populated from narrative in production
                route=route,
            )
        )
    return OverviewResponse(dimensions=dimensions)
```

- [ ] **Step 3: Implement provenance router**

```python
# src/aequitas/api/routers/provenance.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aequitas.api.deps import get_db
from aequitas.api.models.responses import ProvenanceResponse
from aequitas.api.services.warehouse import query_provenance

router = APIRouter()


@router.get("/provenance/{metric_id}", response_model=ProvenanceResponse)
def get_provenance(metric_id: str):
    db = get_db()
    result = query_provenance(db, metric_id)
    if not result:
        raise HTTPException(404, f"No provenance for metric '{metric_id}'")
    return ProvenanceResponse(**result)
```

- [ ] **Step 4: Implement LSOA router**

```python
# src/aequitas/api/routers/lsoa.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aequitas.api.deps import get_db
from aequitas.api.models.responses import LsoaResponse
from aequitas.api.services.warehouse import ALLOWED_TABLES, query_lsoa

router = APIRouter()


@router.get("/lsoa/{table}", response_model=LsoaResponse)
def get_lsoa(
    table: str,
    region: str | None = Query(None),
    fields: str | None = Query(None, description="Comma-separated field names"),
    limit: int | None = Query(None, ge=1, le=50000),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(400, f"Table '{table}' not allowed. Choose from: {sorted(ALLOWED_TABLES)}")
    db = get_db()
    field_list = [f.strip() for f in fields.split(",")] if fields else None
    rows, total = query_lsoa(db, table, region, field_list, limit)
    return LsoaResponse(rows=rows, total=total)
```

- [ ] **Step 5: Run all API tests**

Run: `python -m pytest tests/api/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/aequitas/api/routers/ tests/api/
git commit -m "feat(api): overview, LSOA, provenance endpoints"
```

### Task 2.5: Chat endpoint — RAG service + SSE streaming

**Files:**
- Create: `src/aequitas/api/services/rag.py`
- Modify: `src/aequitas/api/routers/chat.py`
- Test: `tests/api/test_chat.py`

- [ ] **Step 1: Write test**

```python
# tests/api/test_chat.py
def test_chat_without_faiss_returns_503(api_client):
    """When FAISS index is not loaded, chat returns 503."""
    resp = api_client.post("/api/chat", json={"query": "What is the Gini?"})
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Implement RAG service**

```python
# src/aequitas/api/services/rag.py
"""RAG service — FAISS retrieval + Gemini streaming."""
from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator

import numpy as np
from loguru import logger


def retrieve_chunks(
    query: str,
    embedding_model: Any,
    faiss_index: Any,
    faiss_metadata: list[dict],
    top_k: int = 5,
    context: dict | None = None,
) -> list[dict]:
    """Embed query and retrieve top-k nearest narrative chunks."""
    query_vec = embedding_model.encode([query], normalize_embeddings=True)
    query_np = np.array(query_vec, dtype=np.float32)

    scores, indices = faiss_index.search(query_np, top_k)

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(faiss_metadata):
            continue
        chunk = faiss_metadata[idx].copy()
        chunk["score"] = float(scores[0][i])
        results.append(chunk)
    return results


def build_prompt(
    query: str,
    chunks: list[dict],
    context: dict | None = None,
    history: list[dict] | None = None,
) -> list[dict]:
    """Build Gemini message list from query + retrieved chunks."""
    evidence = "\n\n---\n\n".join(c["text"] for c in chunks)
    dim = context.get("dimension", "unknown") if context else "unknown"
    region = context.get("region", "all") if context else "all"
    urban_rural = context.get("urban_rural", "all") if context else "all"

    system = (
        "You are a UK bus transport policy analyst for the Aequitas platform. "
        "Answer based ONLY on the provided evidence. If the evidence doesn't "
        "cover the question, say so. Be concise and cite specific statistics."
    )
    context_line = f"User is viewing {dim} for region={region} ({urban_rural})."

    messages = [{"role": "user", "parts": [f"{system}\n\n{context_line}\n\nEvidence:\n{evidence}"]}]
    messages.append({"role": "model", "parts": ["Understood. I'll answer based on the provided evidence."]})

    # Add history
    if history:
        for msg in history[-6:]:  # last 3 turns
            role = "user" if msg.get("role") == "user" else "model"
            messages.append({"role": role, "parts": [msg.get("content", "")]})

    messages.append({"role": "user", "parts": [query]})
    return messages


async def stream_gemini(
    messages: list[dict],
    api_key: str,
    conversation_id: str | None = None,
    source_sections: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream Gemini Flash response as SSE events."""
    conv_id = conversation_id or str(uuid.uuid4())

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            messages,
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield {"event": "chunk", "data": {"text": chunk.text}}

        yield {
            "event": "done",
            "data": {
                "conversation_id": conv_id,
                "sources": source_sections or [],
            },
        }
    except Exception as e:
        logger.error(f"Gemini streaming error: {e}")
        yield {
            "event": "error",
            "data": {"message": str(e), "code": "gemini_error"},
        }
```

- [ ] **Step 3: Implement chat router**

```python
# src/aequitas/api/routers/chat.py
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from aequitas.api.config import ApiConfig
from aequitas.api.deps import get_embedding_model, get_faiss
from aequitas.api.models.requests import ChatRequest
from aequitas.api.services.rag import build_prompt, retrieve_chunks, stream_gemini

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest):
    faiss_index, faiss_metadata = get_faiss()
    embedding_model = get_embedding_model()

    if faiss_index is None or embedding_model is None:
        raise HTTPException(503, "Chat is unavailable — FAISS index not loaded")

    cfg = ApiConfig()

    # Retrieve
    chunks = retrieve_chunks(
        req.query, embedding_model, faiss_index, faiss_metadata, context=req.context
    )
    source_sections = list({c["section_id"] for c in chunks})

    # Build prompt
    messages = build_prompt(req.query, chunks, req.context, req.history)

    # Stream
    async def event_generator():
        async for event in stream_gemini(
            messages, cfg.gemini_api_key, req.conversation_id, source_sections
        ):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(event_generator())
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/api/test_chat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aequitas/api/services/rag.py src/aequitas/api/routers/chat.py tests/api/test_chat.py
git commit -m "feat(api): /api/chat endpoint — FAISS retrieval + Gemini SSE streaming"
```

---

## Chunk 3: Frontend Scaffold + Layout

### Task 3.1: Vite + React + TypeScript + Tailwind project

**Files:**
- Create: `frontend/` directory with full scaffold

- [ ] **Step 1: Scaffold project**

```bash
cd /Users/souravamseekarmarti/Projects/aequitas
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite @tailwindcss/typography @types/d3 vitest @testing-library/react @testing-library/jest-dom jsdom
npm install react-router @tanstack/react-query react-markdown
npm install @observablehq/plot d3
npm install maplibre-gl
```

- [ ] **Step 2: Configure Tailwind**

Replace `frontend/src/index.css` (or `globals.css`) with:

```css
@import "tailwindcss";
@import "tailwindcss/typography";
```

Add to `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: Initialize shadcn/ui**

```bash
cd frontend
npx shadcn@latest init
# When prompted: TypeScript, default style, CSS variables, baseColor slate
npx shadcn@latest add button select sheet collapsible tooltip
```

- [ ] **Step 4: Verify dev server starts**

```bash
cd frontend && npm run dev
```
Expected: Vite dev server at http://localhost:5173

- [ ] **Step 5: Commit**

```bash
cd /Users/souravamseekarmarti/Projects/aequitas
git add frontend/
git commit -m "feat(frontend): Vite + React + TS + Tailwind + shadcn/ui scaffold"
```

### Task 3.2: Constants + API types + colours

**Files:**
- Create: `frontend/src/lib/constants.ts`
- Create: `frontend/src/lib/colours.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Write constants**

```typescript
// frontend/src/lib/constants.ts
export interface DimensionDef {
  id: string
  name: string
  route: string
  prefixes: string[]
  headlineSection: string
  headlineStatKey: string
  description: string
}

export const DIMENSIONS: DimensionDef[] = [
  { id: "equity", name: "Equity & Deprivation", route: "/equity", prefixes: ["f"], headlineSection: "f1_gini", headlineStatKey: "gini", description: "Gini/Lorenz/Palma, vulnerability index, triple deprivation" },
  { id: "accessibility", name: "Accessibility", route: "/accessibility", prefixes: ["a"], headlineSection: "a5_service_deserts", headlineStatKey: "desert_count", description: "2SFCA, 400m coverage, service deserts, job/healthcare gaps" },
  { id: "service_quality", name: "Service Quality", route: "/service-quality", prefixes: ["b"], headlineSection: "b1_frequency", headlineStatKey: "mean_headway", description: "Headway, evening isolation, Sunday deserts, peak ratios" },
  { id: "route_network", name: "Route Network", route: "/route-network", prefixes: ["c"], headlineSection: "c3_operator_hhi", headlineStatKey: "national_hhi", description: "Geometry, operator HHI, route clustering" },
  { id: "correlations", name: "Socio-Economic & ML", route: "/correlations", prefixes: ["d", "g"], headlineSection: "d8_feature_importance", headlineStatKey: "top_feature_importance", description: "Deprivation correlations, SHAP, clustering, anomalies" },
  { id: "economic", name: "Economic Appraisal", route: "/economic", prefixes: ["j"], headlineSection: "j2_bcr", headlineStatKey: "national_bcr", description: "BCR/Green Book, investment gap, GDP multipliers" },
  { id: "bus_services_act", name: "Bus Services Act 2025", route: "/bus-services-act", prefixes: ["bsa"], headlineSection: "bsa1_franchising_readiness", headlineStatKey: "mean_readiness", description: "LTA franchising readiness, operator concentration" },
  { id: "scenarios", name: "Policy Scenarios", route: "/scenarios", prefixes: ["ps"], headlineSection: "ps5_scenario_comparison", headlineStatKey: "best_scenario_bcr", description: "Frequency restoration, last bus extension, DRT" },
]

export const REGIONS = [
  { code: "all", name: "All England" },
  { code: "E12000001", name: "North East" },
  { code: "E12000002", name: "North West" },
  { code: "E12000003", name: "Yorkshire and The Humber" },
  { code: "E12000004", name: "East Midlands" },
  { code: "E12000005", name: "West Midlands" },
  { code: "E12000006", name: "East of England" },
  { code: "E12000007", name: "London" },
  { code: "E12000008", name: "South East" },
  { code: "E12000009", name: "South West" },
] as const

export const AREA_TYPES = [
  { code: "all", name: "All Areas" },
  { code: "urban", name: "Urban" },
  { code: "rural", name: "Rural" },
] as const
```

```typescript
// frontend/src/lib/colours.ts
/** Colourblind-safe categorical palette (6 colours, WCAG tested). */
export const CATEGORICAL = [
  "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
] as const

/** Severity colours. */
export const SEVERITY = {
  high: "#dc2626",
  medium: "#d97706",
  low: "#059669",
} as const
```

```typescript
// frontend/src/api/types.ts
export interface HeadlineStat {
  value: number
  label: string
  severity: "high" | "medium" | "low"
}

export interface DimensionOverview {
  id: string
  name: string
  headline_stat: HeadlineStat
  summary: string
  route: string
}

export interface OverviewResponse {
  dimensions: DimensionOverview[]
}

export interface SectionItem {
  section_id: string
  dimension: string
  stats: Record<string, unknown>
  chart_data: Record<string, unknown>
  narrative: string
  suppressed: boolean
}

export interface SectionsResponse {
  dimension: string
  sections: SectionItem[]
}

export interface ProvenanceResponse {
  metric_id: string
  value: number
  formula: string
  inputs: Record<string, string>
  source_files: string[]
}

export interface LsoaResponse {
  rows: Record<string, unknown>[]
  total: number
}

export interface ChatChunkEvent {
  text: string
}

export interface ChatDoneEvent {
  conversation_id: string
  sources: string[]
}

export interface ChatErrorEvent {
  message: string
  code: string
}
```

```typescript
// frontend/src/api/client.ts
const BASE = "/api"

export async function fetchJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json()
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/ frontend/src/api/
git commit -m "feat(frontend): constants, API types, colour palettes, fetch client"
```

### Task 3.3: React Query hooks

**Files:**
- Create: `frontend/src/api/hooks.ts`

- [ ] **Step 1: Implement hooks**

```typescript
// frontend/src/api/hooks.ts
import { useQuery } from "@tanstack/react-query"
import { useSearchParams } from "react-router"
import { fetchJson } from "./client"
import type { OverviewResponse, SectionsResponse, ProvenanceResponse, LsoaResponse } from "./types"

/** Read global filters from URL search params. */
export function useFilters() {
  const [params, setParams] = useSearchParams()
  const region = params.get("region") ?? "all"
  const urbanRural = params.get("urban_rural") ?? "all"

  const setRegion = (r: string) => {
    const next = new URLSearchParams(params)
    next.set("region", r)
    setParams(next)
  }
  const setUrbanRural = (u: string) => {
    const next = new URLSearchParams(params)
    next.set("urban_rural", u)
    setParams(next)
  }

  return { region, urbanRural, setRegion, setUrbanRural }
}

export function useOverview(region: string, urbanRural: string) {
  return useQuery({
    queryKey: ["overview", region, urbanRural],
    queryFn: () => fetchJson<OverviewResponse>("/overview", { region, urban_rural: urbanRural }),
    staleTime: Infinity,
  })
}

export function useSections(dimension: string, region: string, urbanRural: string) {
  return useQuery({
    queryKey: ["sections", dimension, region, urbanRural],
    queryFn: () =>
      fetchJson<SectionsResponse>("/sections", { dimension, region, urban_rural: urbanRural }),
    staleTime: Infinity,
  })
}

export function useProvenance(metricId: string | null) {
  return useQuery({
    queryKey: ["provenance", metricId],
    queryFn: () => fetchJson<ProvenanceResponse>(`/provenance/${metricId}`),
    enabled: !!metricId,
    staleTime: Infinity,
  })
}

export function useLsoa(table: string, region?: string) {
  return useQuery({
    queryKey: ["lsoa", table, region],
    queryFn: () => {
      const params: Record<string, string> = {}
      if (region && region !== "all") params.region = region
      return fetchJson<LsoaResponse>(`/lsoa/${table}`, params)
    },
    staleTime: Infinity,
  })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/hooks.ts
git commit -m "feat(frontend): React Query hooks — useOverview, useSections, useLsoa, useProvenance"
```

### Task 3.4: App shell — Header + TabBar + FilterDropdowns + Router

**Files:**
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/layout/TabBar.tsx`
- Create: `frontend/src/components/layout/FilterDropdowns.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Implement layout components**

```typescript
// frontend/src/components/layout/FilterDropdowns.tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { REGIONS, AREA_TYPES } from "@/lib/constants"
import { useFilters } from "@/api/hooks"

export function FilterDropdowns() {
  const { region, urbanRural, setRegion, setUrbanRural } = useFilters()

  return (
    <div className="flex gap-2">
      <Select value={region} onValueChange={setRegion}>
        <SelectTrigger className="w-[180px] bg-white/10 border-white/20 text-white text-sm">
          <SelectValue placeholder="Region" />
        </SelectTrigger>
        <SelectContent>
          {REGIONS.map((r) => (
            <SelectItem key={r.code} value={r.code}>{r.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={urbanRural} onValueChange={setUrbanRural}>
        <SelectTrigger className="w-[130px] bg-white/10 border-white/20 text-white text-sm">
          <SelectValue placeholder="Area type" />
        </SelectTrigger>
        <SelectContent>
          {AREA_TYPES.map((a) => (
            <SelectItem key={a.code} value={a.code}>{a.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
```

```typescript
// frontend/src/components/layout/TabBar.tsx
import { NavLink } from "react-router"
import { DIMENSIONS } from "@/lib/constants"

export function TabBar() {
  return (
    <nav className="border-b bg-white">
      <div className="mx-auto max-w-7xl px-4 flex gap-0 overflow-x-auto">
        {DIMENSIONS.map((d) => (
          <NavLink
            key={d.id}
            to={d.route}
            className={({ isActive }) =>
              `px-4 py-3 text-sm whitespace-nowrap border-b-2 transition-colors ${
                isActive
                  ? "border-indigo-500 text-indigo-600 font-medium"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`
            }
          >
            {d.name}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
```

```typescript
// frontend/src/components/layout/Header.tsx
import { Link } from "react-router"
import { FilterDropdowns } from "./FilterDropdowns"

export function Header() {
  return (
    <header className="bg-[#1a1a2e] text-white">
      <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-semibold tracking-tight">
          Aequitas
        </Link>
        <FilterDropdowns />
      </div>
    </header>
  )
}
```

```typescript
// frontend/src/components/layout/AppShell.tsx
import { Outlet } from "react-router"
import { Header } from "./Header"
import { TabBar } from "./TabBar"

export function AppShell() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <TabBar />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Wire up App.tsx and main.tsx**

```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AppShell } from "./components/layout/AppShell"

const queryClient = new QueryClient()

// Lazy-loaded pages (will be created in next chunks)
function Placeholder({ name }: { name: string }) {
  return <div className="text-gray-500">Page: {name}</div>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<Placeholder name="Home" />} />
            <Route path="equity" element={<Placeholder name="Equity" />} />
            <Route path="accessibility" element={<Placeholder name="Accessibility" />} />
            <Route path="service-quality" element={<Placeholder name="Service Quality" />} />
            <Route path="route-network" element={<Placeholder name="Route Network" />} />
            <Route path="correlations" element={<Placeholder name="Correlations" />} />
            <Route path="economic" element={<Placeholder name="Economic" />} />
            <Route path="bus-services-act" element={<Placeholder name="BSA 2025" />} />
            <Route path="scenarios" element={<Placeholder name="Scenarios" />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

```typescript
// frontend/src/main.tsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import "./styles/globals.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 3: Verify dev server renders shell**

```bash
cd frontend && npm run dev
```
Open http://localhost:5173 — should see dark header with "Aequitas", filter dropdowns, 8 tabs, and placeholder content.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): app shell — Header, TabBar, FilterDropdowns, React Router"
```

---

## Chunk 4: Frontend — Homepage + Dimension Pages

### Task 4.1: Homepage with dimension cards

**Files:**
- Create: `frontend/src/components/home/HomePage.tsx`
- Create: `frontend/src/components/home/DimensionCard.tsx`
- Create: `frontend/src/components/shared/Severity.tsx`

- [ ] **Step 1: Implement components**

```typescript
// frontend/src/components/shared/Severity.tsx
import { SEVERITY } from "@/lib/colours"

interface Props {
  severity: "high" | "medium" | "low"
  children: React.ReactNode
}

export function Severity({ severity, children }: Props) {
  return (
    <span style={{ color: SEVERITY[severity] }} className="font-bold text-3xl">
      {children}
    </span>
  )
}
```

```typescript
// frontend/src/components/home/DimensionCard.tsx
import { Link } from "react-router"
import type { DimensionOverview } from "@/api/types"
import { Severity } from "@/components/shared/Severity"

interface Props {
  dim: DimensionOverview
}

export function DimensionCard({ dim }: Props) {
  return (
    <Link
      to={dim.route}
      className="block bg-white rounded-lg border border-gray-200 p-5 hover:shadow-md transition-shadow"
    >
      <h3 className="text-sm font-semibold text-gray-900 mb-2">{dim.name}</h3>
      <Severity severity={dim.headline_stat.severity}>
        {dim.headline_stat.value.toLocaleString(undefined, { maximumFractionDigits: 3 })}
      </Severity>
      <p className="text-xs text-gray-500 mt-1">{dim.headline_stat.label}</p>
      {dim.summary && <p className="text-sm text-gray-600 mt-2">{dim.summary}</p>}
    </Link>
  )
}
```

```typescript
// frontend/src/components/home/HomePage.tsx
import { useFilters, useOverview } from "@/api/hooks"
import { DimensionCard } from "./DimensionCard"

export function HomePage() {
  const { region, urbanRural } = useFilters()
  const { data, isLoading, error } = useOverview(region, urbanRural)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-32 bg-gray-200 animate-pulse rounded-lg" />
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="text-red-600">Unable to load overview — try refreshing.</p>
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-1">
        Bus Transport Intelligence for England
      </h1>
      <p className="text-gray-500 mb-6">
        Evidence-graded analytics across 8 policy dimensions
      </p>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {data?.dimensions.map((d) => (
          <DimensionCard key={d.id} dim={d} />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire into App.tsx routes**

Replace the `<Placeholder name="Home" />` route with `<HomePage />`. Import `HomePage` from `@/components/home/HomePage`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/home/ frontend/src/components/shared/Severity.tsx frontend/src/App.tsx
git commit -m "feat(frontend): homepage with dimension cards + severity badges"
```

### Task 4.2: DimensionPage + SectionCard

**Files:**
- Create: `frontend/src/components/dimension/DimensionPage.tsx`
- Create: `frontend/src/components/dimension/SectionCard.tsx`
- Create: `frontend/src/components/shared/Markdown.tsx`

- [ ] **Step 1: Implement components**

```typescript
// frontend/src/components/shared/Markdown.tsx
import ReactMarkdown from "react-markdown"

interface Props {
  content: string
}

export function Markdown({ content }: Props) {
  return (
    <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}
```

```typescript
// frontend/src/components/dimension/SectionCard.tsx
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import type { SectionItem } from "@/api/types"
import { Markdown } from "@/components/shared/Markdown"

interface Props {
  section: SectionItem
}

export function SectionCard({ section }: Props) {
  const [open, setOpen] = useState(false)
  const title = section.chart_data?.title as string ?? section.section_id

  return (
    <article className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>

      {/* Chart placeholder — will be replaced by ChartRenderer in Chunk 5 */}
      <div className="bg-gray-100 rounded-md p-8 text-center text-gray-400 text-sm mb-3">
        Chart: {(section.chart_data as Record<string, unknown>)?.type as string ?? "unknown"}
      </div>

      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="text-indigo-600 px-0">
            {open ? "Hide details" : "Read more"}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-3">
          <Markdown content={section.narrative} />
        </CollapsibleContent>
      </Collapsible>
    </article>
  )
}
```

```typescript
// frontend/src/components/dimension/DimensionPage.tsx
import { useParams } from "react-router"
import { useFilters, useSections } from "@/api/hooks"
import { DIMENSIONS, REGIONS, AREA_TYPES } from "@/lib/constants"
import { SectionCard } from "./SectionCard"

export function DimensionPage() {
  const { dimensionSlug } = useParams<{ dimensionSlug: string }>()
  const dim = DIMENSIONS.find((d) => d.route === `/${dimensionSlug}`)
  const dimensionId = dim?.id ?? dimensionSlug ?? ""

  const { region, urbanRural } = useFilters()
  const { data, isLoading, error } = useSections(dimensionId, region, urbanRural)
  const regionName = REGIONS.find((r) => r.code === region)?.name ?? region
  const areaName = AREA_TYPES.find((a) => a.code === urbanRural)?.name ?? urbanRural

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-48 bg-gray-200 animate-pulse rounded-lg" />
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="text-red-600">Unable to load data — try refreshing.</p>
  }

  const sections = data?.sections.filter((s) => !s.suppressed) ?? []

  if (sections.length === 0) {
    return (
      <p className="text-gray-500">
        No data available for {regionName} ({areaName}). Try selecting "All England" for national-level analysis.
      </p>
    )
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-1">{dim?.name}</h2>
      <p className="text-gray-500 text-sm mb-6">{dim?.description}</p>
      {sections.map((s) => (
        <SectionCard key={s.section_id} section={s} />
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Wire into App.tsx routes**

Replace all `<Placeholder>` dimension routes with `<DimensionPage />`. Use a single route with a param:

```typescript
<Route path=":dimensionSlug" element={<DimensionPage />} />
```

Remove the individual dimension routes.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dimension/ frontend/src/components/shared/Markdown.tsx frontend/src/App.tsx
git commit -m "feat(frontend): DimensionPage + SectionCard with collapsible narratives"
```

---

## Chunk 5: Frontend — Chart Components

### Task 5.1: ChartRenderer + DataTable fallback

**Files:**
- Create: `frontend/src/components/charts/ChartRenderer.tsx`
- Create: `frontend/src/components/charts/DataTable.tsx`

- [ ] **Step 1: Implement DataTable**

```typescript
// frontend/src/components/charts/DataTable.tsx
interface Props {
  chartData: Record<string, unknown>
}

export function DataTable({ chartData }: Props) {
  const data = (chartData.data ?? chartData.groups ?? chartData.features ?? []) as Record<string, unknown>[]

  if (!Array.isArray(data) || data.length === 0) {
    return <p className="text-gray-400 text-sm">No data available</p>
  }

  const columns = Object.keys(data[0])

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border border-gray-200">
        <thead>
          <tr className="bg-gray-50">
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium text-gray-700 border-b">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 100).map((row, i) => (
            <tr key={i} className="border-b">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 text-gray-600">
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 100 && (
        <p className="text-xs text-gray-400 mt-1">Showing first 100 of {data.length} rows</p>
      )}
    </div>
  )
}
```

```typescript
// frontend/src/components/charts/ChartRenderer.tsx
import { lazy, Suspense } from "react"
import { DataTable } from "./DataTable"

const HorizontalBarChart = lazy(() => import("./HorizontalBarChart"))
const ScatterRegressionChart = lazy(() => import("./ScatterRegressionChart"))
const LorenzCurveChart = lazy(() => import("./LorenzCurveChart"))
const ShapBarChart = lazy(() => import("./ShapBarChart"))
const ChoroplethMap = lazy(() => import("./ChoroplethMap"))

interface Props {
  chartData: Record<string, unknown>
}

export function ChartRenderer({ chartData }: Props) {
  const type = chartData.type as string | undefined

  const fallback = <div className="h-64 bg-gray-100 animate-pulse rounded" />

  switch (type) {
    case "horizontal_bar":
    case "grouped_bar":
    case "stacked_bar":
      return <Suspense fallback={fallback}><HorizontalBarChart chartData={chartData} /></Suspense>
    case "scatter_regression":
      return <Suspense fallback={fallback}><ScatterRegressionChart chartData={chartData} /></Suspense>
    case "lorenz_curve":
      return <Suspense fallback={fallback}><LorenzCurveChart chartData={chartData} /></Suspense>
    case "shap_bar":
      return <Suspense fallback={fallback}><ShapBarChart chartData={chartData} /></Suspense>
    case "choropleth":
      return <Suspense fallback={fallback}><ChoroplethMap chartData={chartData} /></Suspense>
    default:
      return <DataTable chartData={chartData} />
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/charts/ChartRenderer.tsx frontend/src/components/charts/DataTable.tsx
git commit -m "feat(frontend): ChartRenderer dispatcher + DataTable fallback"
```

### Task 5.2: HorizontalBarChart (Observable Plot)

**Files:**
- Create: `frontend/src/components/charts/HorizontalBarChart.tsx`

- [ ] **Step 1: Implement**

```typescript
// frontend/src/components/charts/HorizontalBarChart.tsx
import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"

interface Props {
  chartData: Record<string, unknown>
}

export default function HorizontalBarChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const variant = chartData.type as string ?? "horizontal_bar"

  useEffect(() => {
    if (!ref.current) return
    const xLabel = chartData.x_label as string ?? "Value"
    const nationalAvg = chartData.national_avg as number | undefined

    const marks: Plot.Markish[] = []

    if (variant === "grouped_bar") {
      // Grouped bar: data has { label, group, value }
      const data = (chartData.data ?? []) as { label: string; group: string; value: number }[]
      marks.push(
        Plot.barX(data, Plot.groupY({ x: "sum" }, {
          y: "label", x: "value", fill: "group",
          sort: { y: "x", reverse: true },
        })),
      )
    } else if (variant === "stacked_bar") {
      // Stacked bar: data has { label, group, value }
      const data = (chartData.data ?? []) as { label: string; group: string; value: number }[]
      marks.push(
        Plot.barX(data, Plot.stackX({
          y: "label", x: "value", fill: "group",
          sort: { y: "x", reverse: true },
        })),
      )
    } else {
      // Simple horizontal bar: data has { label, value }
      const data = (chartData.data ?? []) as { label: string; value: number }[]
      marks.push(
        Plot.barX(data, {
          y: "label", x: "value", fill: CATEGORICAL[0],
          sort: { y: "x", reverse: true },
        }),
        Plot.text(data, {
          y: "label", x: "value",
          text: (d: { value: number }) => d.value.toLocaleString(undefined, { maximumFractionDigits: 1 }),
          dx: 4, textAnchor: "start", fontSize: 11,
        }),
      )
    }

    if (nationalAvg !== undefined) {
      marks.push(
        Plot.ruleX([nationalAvg], { stroke: "#e15759", strokeWidth: 1.5, strokeDasharray: "4,3" }),
        Plot.text([nationalAvg], {
          x: nationalAvg,
          text: [`Avg: ${nationalAvg.toFixed(1)}`],
          dy: -8, fill: "#e15759", fontSize: 10,
        })
      )
    }

    const allData = (chartData.data ?? []) as unknown[]
    const chart = Plot.plot({
      marginLeft: 140,
      marginRight: 60,
      width: 700,
      height: Math.max(300, allData.length * 28),
      x: { label: xLabel },
      y: { label: null },
      color: variant !== "horizontal_bar" ? { legend: true, range: CATEGORICAL } : undefined,
      marks,
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData, variant])

  return (
    <div>
      <div ref={ref} aria-label={chartData.title as string ?? "Bar chart"} role="img" />
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/charts/HorizontalBarChart.tsx
git commit -m "feat(frontend): HorizontalBarChart — Observable Plot horizontal bar"
```

### Task 5.3: ScatterRegressionChart + LorenzCurveChart + ShapBarChart

**Files:**
- Create: `frontend/src/components/charts/ScatterRegressionChart.tsx`
- Create: `frontend/src/components/charts/LorenzCurveChart.tsx`
- Create: `frontend/src/components/charts/ShapBarChart.tsx`

- [ ] **Step 1: Implement ScatterRegressionChart**

```typescript
// frontend/src/components/charts/ScatterRegressionChart.tsx
import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"

interface Props { chartData: Record<string, unknown> }

export default function ScatterRegressionChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const data = (chartData.data ?? []) as { x: number; y: number; id: string }[]
    const r = chartData.r as number | undefined
    const pValue = chartData.p_value as number | undefined
    const regression = chartData.regression_line as { slope: number; intercept: number } | undefined

    const marks: Plot.Markish[] = [
      Plot.dot(data, { x: "x", y: "y", fill: CATEGORICAL[0], opacity: 0.6, r: 3 }),
    ]

    if (regression) {
      const xExtent = [Math.min(...data.map((d) => d.x)), Math.max(...data.map((d) => d.x))]
      const lineData = xExtent.map((x) => ({ x, y: regression.slope * x + regression.intercept }))
      marks.push(Plot.line(lineData, { x: "x", y: "y", stroke: "#e15759", strokeWidth: 2 }))
    }

    const subtitle = r !== undefined ? `r = ${r.toFixed(3)}${pValue !== undefined ? `, p = ${pValue.toFixed(4)}` : ""}` : ""

    const chart = Plot.plot({
      width: 700,
      height: 450,
      x: { label: chartData.x_label as string ?? "X" },
      y: { label: chartData.y_label as string ?? "Y" },
      subtitle,
      marks,
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData])

  return <div ref={ref} aria-label={chartData.title as string ?? "Scatter plot"} role="img" />
}
```

- [ ] **Step 2: Implement LorenzCurveChart**

```typescript
// frontend/src/components/charts/LorenzCurveChart.tsx
import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"

interface Props { chartData: Record<string, unknown> }

export default function LorenzCurveChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const points = (chartData.curve_points ?? []) as { cum_pop: number; cum_service: number }[]
    const gini = chartData.gini as number | undefined
    const refGini = chartData.reference_gini as number | undefined
    const refLabel = chartData.reference_label as string | undefined

    const equality = [{ cum_pop: 0, cum_service: 0 }, { cum_pop: 1, cum_service: 1 }]

    const marks: Plot.Markish[] = [
      Plot.line(equality, { x: "cum_pop", y: "cum_service", stroke: "#999", strokeDasharray: "4,3", strokeWidth: 1 }),
      Plot.line(points, { x: "cum_pop", y: "cum_service", stroke: "#4e79a7", strokeWidth: 2 }),
      Plot.areaY(points, { x: "cum_pop", y1: "cum_service", y2: "cum_pop", fill: "#4e79a7", fillOpacity: 0.1 }),
    ]

    const subtitle = gini !== undefined
      ? `Gini = ${gini.toFixed(3)}${refGini !== undefined ? ` (${refLabel ?? "reference"}: ${refGini.toFixed(3)})` : ""}`
      : ""

    const chart = Plot.plot({
      width: 600,
      height: 500,
      x: { label: "Cumulative population share", domain: [0, 1] },
      y: { label: "Cumulative service share", domain: [0, 1] },
      subtitle,
      marks,
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData])

  return <div ref={ref} aria-label={chartData.title as string ?? "Lorenz curve"} role="img" />
}
```

- [ ] **Step 3: Implement ShapBarChart**

```typescript
// frontend/src/components/charts/ShapBarChart.tsx
import { useRef, useEffect } from "react"
import * as Plot from "@observablehq/plot"
import { CATEGORICAL } from "@/lib/colours"

interface Props { chartData: Record<string, unknown> }

export default function ShapBarChart({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const features = (chartData.features ?? []) as { name: string; importance: number }[]
    const r2 = chartData.model_r2 as number | undefined

    const chart = Plot.plot({
      marginLeft: 160,
      width: 700,
      height: Math.max(300, features.length * 28),
      x: { label: "SHAP Importance" },
      y: { label: null },
      subtitle: r2 !== undefined ? `Model R² = ${r2.toFixed(3)}` : undefined,
      marks: [
        Plot.barX(features, {
          y: "name",
          x: "importance",
          fill: CATEGORICAL[1],
          sort: { y: "x", reverse: true },
        }),
        Plot.text(features, {
          y: "name",
          x: "importance",
          text: (d: { importance: number }) => d.importance.toFixed(3),
          dx: 4,
          textAnchor: "start",
          fontSize: 11,
        }),
      ],
    })

    ref.current.replaceChildren(chart)
    return () => chart.remove()
  }, [chartData])

  return <div ref={ref} aria-label={chartData.title as string ?? "SHAP importance"} role="img" />
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/charts/ScatterRegressionChart.tsx frontend/src/components/charts/LorenzCurveChart.tsx frontend/src/components/charts/ShapBarChart.tsx
git commit -m "feat(frontend): scatter, Lorenz curve, SHAP bar chart components"
```

### Task 5.4: ChoroplethMap (MapLibre GL)

**Files:**
- Create: `frontend/src/components/charts/ChoroplethMap.tsx`

- [ ] **Step 1: Implement**

```typescript
// frontend/src/components/charts/ChoroplethMap.tsx
import { useRef, useEffect } from "react"
import maplibregl from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"

interface Props { chartData: Record<string, unknown> }

export default function ChoroplethMap({ chartData }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const data = (chartData.data ?? []) as { area_code: string; area_name: string; value: number }[]
    const container = ref.current

    // Create value lookup
    const values = new Map(data.map((d) => [d.area_code, d.value]))
    const maxVal = Math.max(...data.map((d) => d.value), 1)

    // Fetch GeoJSON once, inject values, then create map
    fetch("/boundaries/regions.geojson")
      .then((r) => r.json())
      .then((geojson) => {
        // Inject values into feature properties before adding to map
        for (const f of geojson.features) {
          const code = f.properties?.RGN22CD ?? f.properties?.rgn22cd
          f.properties.value = values.get(code) ?? 0
        }

        const map = new maplibregl.Map({
          container,
          style: {
            version: 8,
            sources: {
              regions: { type: "geojson", data: geojson },
            },
            layers: [
              { id: "background", type: "background", paint: { "background-color": "#f8f9fa" } },
              {
                id: "regions-fill",
                type: "fill",
                source: "regions",
                paint: {
                  // Viridis colourblind-safe palette (spec requirement)
                  "fill-color": [
                    "interpolate", ["linear"],
                    ["coalesce", ["get", "value"], 0],
                    0, "#440154",
                    maxVal * 0.25, "#31688e",
                    maxVal * 0.5, "#35b779",
                    maxVal * 0.75, "#90d743",
                    maxVal, "#fde725",
                  ],
                  "fill-opacity": 0.8,
                },
              },
              {
                id: "regions-outline",
                type: "line",
                source: "regions",
                paint: { "line-color": "#666", "line-width": 1 },
              },
            ],
          },
          center: [-1.5, 52.8],
          zoom: 5.5,
          attributionControl: false,
        })

        mapRef.current = map
      })

    return () => { mapRef.current?.remove(); mapRef.current = null }
  }, [chartData])

  return (
    <div
      ref={ref}
      className="h-[500px] rounded-md overflow-hidden"
      aria-label={chartData.title as string ?? "Choropleth map"}
      role="img"
    />
  )
}
```

- [ ] **Step 2: Wire ChartRenderer into SectionCard**

In `frontend/src/components/dimension/SectionCard.tsx`, replace the chart placeholder `<div className="bg-gray-100...">` with:

```typescript
import { ChartRenderer } from "@/components/charts/ChartRenderer"

// Inside the JSX, replace the placeholder:
<ChartRenderer chartData={section.chart_data} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/ChoroplethMap.tsx frontend/src/components/dimension/SectionCard.tsx
git commit -m "feat(frontend): ChoroplethMap (MapLibre GL) + wire ChartRenderer into SectionCard"
```

---

## Chunk 6: Frontend — Chat Drawer

### Task 6.1: useChat hook (SSE streaming)

**Files:**
- Create: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: Implement**

```typescript
// frontend/src/hooks/useChat.ts
import { useCallback, useRef, useState } from "react"

interface Message {
  role: "user" | "assistant"
  content: string
}

interface UseChatReturn {
  messages: Message[]
  isStreaming: boolean
  error: string | null
  sendMessage: (query: string, context: Record<string, string>) => void
  clearMessages: () => void
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const conversationId = useRef<string | null>(null)
  const messagesRef = useRef<Message[]>(messages)
  messagesRef.current = messages

  const sendMessage = useCallback(
    async (query: string, context: Record<string, string>) => {
      setError(null)
      setMessages((prev) => [...prev, { role: "user", content: query }])
      setIsStreaming(true)

      // Add placeholder assistant message
      setMessages((prev) => [...prev, { role: "assistant", content: "" }])

      try {
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            context,
            conversation_id: conversationId.current,
            history: messagesRef.current.slice(-6).map((m) => ({ role: m.role, content: m.content })),
          }),
        })

        if (!resp.ok) {
          const text = await resp.text()
          throw new Error(text)
        }

        const reader = resp.body?.getReader()
        const decoder = new TextDecoder()
        if (!reader) throw new Error("No response body")

        let buffer = ""
        let currentEventType = "chunk"  // SSE state machine

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() ?? ""

          for (const line of lines) {
            // Track current event type for proper dispatch
            if (line.startsWith("event: ")) {
              currentEventType = line.slice(7).trim()
              continue
            }

            if (line.startsWith("data: ")) {
              try {
                const payload = JSON.parse(line.slice(6))

                switch (currentEventType) {
                  case "chunk":
                    if (payload.text) {
                      setMessages((prev) => {
                        const last = prev[prev.length - 1]
                        if (last.role === "assistant") {
                          return [...prev.slice(0, -1), { ...last, content: last.content + payload.text }]
                        }
                        return prev
                      })
                    }
                    break
                  case "done":
                    if (payload.conversation_id) {
                      conversationId.current = payload.conversation_id
                    }
                    break
                  case "error":
                    if (payload.message) setError(payload.message)
                    break
                }
              } catch {
                // ignore malformed JSON
              }
              // Reset to default after processing data line
              currentEventType = "chunk"
            }
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Chat failed")
      } finally {
        setIsStreaming(false)
      }
    },
    []  // stable — reads from messagesRef.current
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    conversationId.current = null
    setError(null)
  }, [])

  return { messages, isStreaming, error, sendMessage, clearMessages }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat(frontend): useChat hook — SSE streaming for Gemini chat"
```

### Task 6.2: ChatDrawer + ChatFAB + ChatMessage

**Files:**
- Create: `frontend/src/components/chat/ChatFAB.tsx`
- Create: `frontend/src/components/chat/ChatMessage.tsx`
- Create: `frontend/src/components/chat/ChatDrawer.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`

- [ ] **Step 1: Implement chat components**

```typescript
// frontend/src/components/chat/ChatFAB.tsx
import { Button } from "@/components/ui/button"

interface Props {
  onClick: () => void
}

export function ChatFAB({ onClick }: Props) {
  return (
    <Button
      onClick={onClick}
      className="fixed bottom-6 right-6 rounded-full w-14 h-14 bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg z-40"
      aria-label="Open AI chat"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    </Button>
  )
}
```

```typescript
// frontend/src/components/chat/ChatMessage.tsx
import { Markdown } from "@/components/shared/Markdown"

interface Props {
  role: "user" | "assistant"
  content: string
}

export function ChatMessage({ role, content }: Props) {
  return (
    <div className={`flex ${role === "user" ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2 text-sm ${
          role === "user"
            ? "bg-indigo-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        {role === "assistant" ? <Markdown content={content || "..."} /> : content}
      </div>
    </div>
  )
}
```

```typescript
// frontend/src/components/chat/ChatDrawer.tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { useEffect, useRef, useState } from "react"
import { useLocation } from "react-router"
import { useChat } from "@/hooks/useChat"
import { useFilters } from "@/api/hooks"
import { DIMENSIONS } from "@/lib/constants"
import { ChatMessage } from "./ChatMessage"

interface Props {
  open: boolean
  onClose: () => void
}

export function ChatDrawer({ open, onClose }: Props) {
  const { messages, isStreaming, error, sendMessage, clearMessages } = useChat()
  const { region, urbanRural } = useFilters()
  const location = useLocation()
  const [input, setInput] = useState("")
  const messagesEnd = useRef<HTMLDivElement>(null)

  // Derive current dimension from URL path
  const slug = location.pathname.replace("/", "")
  const currentDimension = DIMENSIONS.find((d) => d.route === `/${slug}`)?.id ?? ""

  // Auto-scroll to bottom when messages update (including during streaming)
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || isStreaming) return
    sendMessage(input.trim(), { dimension: currentDimension, region, urban_rural: urbanRural })
    setInput("")
  }

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[400px] sm:w-[400px] flex flex-col p-0" side="right">
        <SheetHeader className="p-4 border-b">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-base">Ask Aequitas</SheetTitle>
            <Button variant="ghost" size="sm" onClick={clearMessages}>Clear</Button>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 && (
            <p className="text-sm text-gray-400">
              Ask about bus transport policy — I'll answer using the pre-computed analytics.
            </p>
          )}
          {messages.map((m, i) => (
            <ChatMessage key={i} role={m.role} content={m.content} />
          ))}
          {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
          <div ref={messagesEnd} />
        </div>

        <div className="p-4 border-t">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask a question..."
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              disabled={isStreaming}
            />
            <Button onClick={handleSend} disabled={isStreaming || !input.trim()} size="sm">
              Send
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
```

- [ ] **Step 2: Wire into AppShell**

```typescript
// frontend/src/components/layout/AppShell.tsx — updated
import { useState } from "react"
import { Outlet } from "react-router"
import { Header } from "./Header"
import { TabBar } from "./TabBar"
import { ChatFAB } from "../chat/ChatFAB"
import { ChatDrawer } from "../chat/ChatDrawer"

export function AppShell() {
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <TabBar />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
      <ChatFAB onClick={() => setChatOpen(true)} />
      <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/chat/ frontend/src/components/layout/AppShell.tsx
git commit -m "feat(frontend): ChatDrawer + ChatFAB — Gemini RAG chat panel"
```

---

## Chunk 7: Integration + End-to-End Verification

### Task 7.1: Backend integration test — full API against real DuckDB

**Files:**
- Create: `tests/api/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/api/test_integration.py
"""Integration test — runs API against the real DuckDB warehouse if available."""
import os
import pytest
from pathlib import Path


pytestmark = pytest.mark.skipif(
    not Path("data/aequitas.duckdb").exists(),
    reason="No warehouse built — run pipeline first",
)


@pytest.fixture
def real_client(monkeypatch):
    monkeypatch.setenv("AEQUITAS_DB_PATH", "data/aequitas.duckdb")
    from aequitas.api.app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_overview_returns_8_dimensions(real_client):
    resp = real_client.get("/api/overview")
    assert resp.status_code == 200
    dims = resp.json()["dimensions"]
    assert len(dims) == 8
    equity = [d for d in dims if d["id"] == "equity"][0]
    assert equity["headline_stat"]["value"] == pytest.approx(0.5741, abs=0.01)


def test_sections_equity_has_f_prefixed_sections(real_client):
    resp = real_client.get("/api/sections", params={"dimension": "equity"})
    assert resp.status_code == 200
    sections = resp.json()["sections"]
    assert len(sections) >= 1
    for s in sections:
        assert s["section_id"].startswith("f")
        assert s["dimension"] == "equity"


def test_provenance_gini_exists(real_client):
    resp = real_client.get("/api/provenance/gini_national")
    assert resp.status_code == 200
    assert resp.json()["value"] == pytest.approx(0.5741, abs=0.01)
```

- [ ] **Step 2: Run integration test**

Run: `python -m pytest tests/api/test_integration.py -v`
Expected: PASS if warehouse exists, SKIP if not

- [ ] **Step 3: Commit**

```bash
git add tests/api/test_integration.py
git commit -m "test(api): integration test against real DuckDB warehouse"
```

### Task 7.2: Frontend build verification

- [ ] **Step 1: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors

- [ ] **Step 2: Verify production build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds, `dist/` contains HTML + JS + CSS

- [ ] **Step 3: Commit any fixes**

```bash
git add frontend/
git commit -m "fix(frontend): resolve any TypeScript compilation issues"
```

### Task 7.3: Run both backend and frontend together

- [ ] **Step 1: Start backend**

```bash
cd /Users/souravamseekarmarti/Projects/aequitas
uvicorn aequitas.api.app:create_app --factory --reload --port 8000
```

- [ ] **Step 2: Start frontend (separate terminal)**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Verify end-to-end**

Open http://localhost:5173 and verify:
- Homepage loads with 8 dimension cards
- Clicking a card navigates to dimension page with sections
- Charts render (or DataTable fallback for unsupported types)
- Filter dropdowns update the URL and re-fetch data
- "Read more" expands to show full narrative
- Chat FAB opens drawer; sending a message works (if FAISS index exists)

- [ ] **Step 4: Final commit**

```bash
git add src/aequitas/api/ src/aequitas/rag/ frontend/src/ frontend/package.json frontend/vite.config.ts frontend/tsconfig.json frontend/tailwind.config.ts tests/api/
git commit -m "feat: Phase 2 complete — frontend dashboard + FastAPI backend + RAG chatbot"
```

---

## Execution Notes

### Build Order (Dependencies)

```
Task 0.1-0.4 (Prerequisites) — sequential, must complete first
    → Task 1.1-1.2 (FAISS index builder) — depends on 0.3 (deps), 0.4 (config)
    → Task 2.1-2.5 (FastAPI backend) — depends on 0.1-0.2 (narrative fix), 0.3 (deps)
    → Task 3.1-3.4 (Frontend scaffold) — INDEPENDENT of backend, can parallel
        → Task 4.1-4.2 (Homepage + DimensionPage) — depends on 3.x
            → Task 5.1-5.4 (Chart components) — depends on 4.2
                → Task 6.1-6.2 (Chat) — depends on 5.x (for AppShell wiring)
                    → Task 7.1-7.3 (Integration) — depends on ALL above
```

### Parallelisation Opportunities

Tasks that can run as parallel subagents:
- **After Chunk 0:** Chunk 1 (FAISS) + Chunk 2 (FastAPI) + Chunk 3 (Frontend scaffold) are independent
- **Within Chunk 5:** Tasks 5.2, 5.3, 5.4 are independent chart components

### Filter Combination Note

`PipelineConfig.filter_combinations()` returns 30 combos (10 regions × 3 area types). The spec skips single-region × single-area-type combos (30 − 18 = 12). InsightEngine handles this via suppression — the 612 row count (51 × 12) reflects non-suppressed rows. No config change needed.

### Key Risk Mitigations

1. **Observable Plot SSR:** Observable Plot renders to DOM nodes. In React, use `useRef` + `useEffect` to mount/unmount. Never render inside JSX directly.
2. **MapLibre cleanup:** Always call `map.remove()` in the useEffect cleanup function to prevent memory leaks.
3. **DuckDB JSON columns:** `stats` and `chart_data` come back as strings from DuckDB. Always `json.loads()` on the Python side before returning to the API.
4. **FAISS optional:** Chat endpoint returns 503 if FAISS not loaded. Dashboard works without it.
5. **Vite proxy:** `/api` calls are proxied to `localhost:8000` in dev mode (vite.config.ts). In production, use reverse proxy (nginx).
6. **shadcn/ui paths:** After `npx shadcn init`, components live in `frontend/src/components/ui/`. The `@/` path alias must be configured in tsconfig.json.

### Acceptance Criteria

Phase 2 is DONE when:
- [ ] `uvicorn aequitas.api.app:create_app --factory` starts without error
- [ ] `GET /api/overview` returns 8 dimensions with headline stats
- [ ] `GET /api/sections?dimension=equity` returns f1-f6 sections with chart_data and narratives
- [ ] `cd frontend && npm run build` succeeds
- [ ] Homepage renders 8 dimension cards
- [ ] Clicking a card shows sections with Observable Plot charts
- [ ] Filter dropdowns update URL and re-fetch data
- [ ] Chat drawer opens, sends message, streams Gemini response (with FAISS index)
- [ ] `python -m pytest tests/api/ -v` — all pass
- [ ] `cd frontend && npx tsc --noEmit` — no TypeScript errors
