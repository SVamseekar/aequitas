"""Netherlands FAISS is OVapi × SES-WOA only. England Gini must not come back as Dutch."""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import pytest
from sentence_transformers import SentenceTransformer

from aequitas.api.services.rag import retrieve_chunks

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "data" / "netherlands" / "faiss_index.bin"
META = ROOT / "data" / "netherlands" / "faiss_metadata.json"
BANNED = ("bsa", "imd", "pobal", "lsoa", "bods")


@pytest.mark.skipif(not INDEX.exists() or not META.exists(), reason="Netherlands FAISS not built")
def test_every_chunk_is_netherlands_and_has_no_foreign_statute() -> None:
    rows = json.loads(META.read_text())
    assert rows
    assert all(row.get("country") == "netherlands" for row in rows)
    blob = "\n".join(row.get("text") or "" for row in rows).lower()
    for tok in BANNED:
        assert tok not in blob


@pytest.mark.skipif(not INDEX.exists() or not META.exists(), reason="Netherlands FAISS not built")
def test_dutch_gini_query_does_not_return_england_gini() -> None:
    rows = json.loads(META.read_text())
    index = faiss.read_index(str(INDEX))
    model = SentenceTransformer("all-MiniLM-L6-v2")
    hits = retrieve_chunks(
        "Gini of OVapi weekday trips",
        model,
        index,
        rows,
        top_k=5,
        context={"country": "netherlands"},
    )
    assert hits
    joined = "\n".join(h.get("text") or "" for h in hits)
    assert "0.5741" not in joined
    assert all(h.get("country") == "netherlands" for h in hits)
    assert any(h.get("section_id") == "f1_gini" for h in hits)
