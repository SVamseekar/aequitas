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

    Splits on double newlines. If a paragraph exceeds max_tokens (measured
    in characters), it is included as-is (better to have one long chunk than
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
        para_tokens = len(para)  # character count as proxy for token length
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

    # Build index — IndexFlatIP on L2-normalized vectors = cosine similarity
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
