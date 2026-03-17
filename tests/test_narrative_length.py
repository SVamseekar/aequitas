"""Narratives must be substantive — minimum 200 characters when not suppressed."""
import duckdb
import pytest


@pytest.fixture
def db():
    conn = duckdb.connect("data/aequitas.duckdb", read_only=True)
    yield conn
    conn.close()


def test_narrative_minimum_length(db):
    """Non-suppressed narratives must be at least 200 chars."""
    rows = db.execute("""
        SELECT section_id, region, LENGTH(narrative) as len
        FROM section_results
        WHERE narrative IS NOT NULL AND narrative != ''
          AND LENGTH(narrative) < 200
    """).fetchall()
    short = [(r[0], r[1], r[2]) for r in rows]
    assert len(short) == 0, f"{len(short)} narratives too short: {short[:5]}..."


def test_narrative_has_policy_implication(db):
    """At least 80% of narratives should mention 'policy' or 'implication' or 'recommendation'."""
    total = db.execute("""
        SELECT COUNT(*) FROM section_results
        WHERE narrative IS NOT NULL AND narrative != ''
    """).fetchone()[0]
    policy = db.execute("""
        SELECT COUNT(*) FROM section_results
        WHERE narrative IS NOT NULL AND narrative != ''
          AND (LOWER(narrative) LIKE '%policy%'
            OR LOWER(narrative) LIKE '%implication%'
            OR LOWER(narrative) LIKE '%intervention%'
            OR LOWER(narrative) LIKE '%recommendation%')
    """).fetchone()[0]
    pct = policy / total * 100 if total > 0 else 0
    assert pct >= 80, f"Only {pct:.1f}% of narratives mention policy implications"
