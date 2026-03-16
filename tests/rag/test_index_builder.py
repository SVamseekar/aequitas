"""Test FAISS index builder."""
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
