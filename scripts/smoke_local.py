#!/usr/bin/env python3
"""Local stack smoke checks — health, overview, 8 dimensions × sample filters.

Usage (API must already be running on BASE_URL):
  uv run python scripts/smoke_local.py
  BASE_URL=http://127.0.0.1:8000 uv run python scripts/smoke_local.py

Optional:
  SMOKE_CHAT=1  — probe /api/chat (skipped unless GEMINI_API_KEY is set)

Exit 0 on success; non-zero if any required check fails.
Not wired into CI (needs a live server + warehouse).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

DIMENSIONS = (
    "equity",
    "accessibility",
    "service_quality",
    "route_network",
    "correlations",
    "economic",
    "bus_services_act",
    "scenarios",
)

# National equity Gini from pre-computed warehouse (Part C canon).
EXPECTED_GINI = 0.5741
GINI_TOLERANCE = 0.005

# London (ONS region) + rural thinning — from live walkthrough filters.
FILTER_CASES: list[tuple[str, str, str]] = [
    ("all", "all", "national"),
    ("E12000002", "all", "North West region"),
    ("E12000007", "rural", "London × rural"),
]


class SmokeError(Exception):
    pass


def _get(path: str, *, timeout: float = 30.0) -> tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except urllib.error.URLError as exc:
        raise SmokeError(f"Connection failed for {url}: {exc.reason}") from exc

    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, body


def _post_json(path: str, payload: dict[str, Any], *, timeout: float = 60.0) -> tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except urllib.error.URLError as exc:
        raise SmokeError(f"Connection failed for {url}: {exc.reason}") from exc


def check_health() -> None:
    status, body = _get("/api/health")
    if status != 200:
        raise SmokeError(f"/api/health → HTTP {status}: {body!r}")
    if not isinstance(body, dict):
        raise SmokeError(f"/api/health returned non-JSON: {body!r}")
    if body.get("status") != "ok":
        raise SmokeError(f"/api/health not ok: {body}")
    if body.get("warehouse") != "connected":
        raise SmokeError(f"/api/health warehouse not connected: {body}")
    print(f"  OK  /api/health → {body}")


def check_overview() -> dict[str, Any]:
    status, body = _get("/api/overview?region=all&urban_rural=all")
    if status != 200:
        raise SmokeError(f"/api/overview → HTTP {status}: {body!r}")
    if not isinstance(body, dict) or "dimensions" not in body:
        raise SmokeError(f"/api/overview unexpected body: {body!r}")
    dims = body["dimensions"]
    if len(dims) < 8:
        raise SmokeError(f"/api/overview expected ≥8 dimensions, got {len(dims)}")
    print(f"  OK  /api/overview → {len(dims)} dimensions")
    return body


def _extract_equity_gini_from_sections(sections: list[dict[str, Any]]) -> float | None:
    for sec in sections:
        if sec.get("section_id") == "f1_gini":
            stats = sec.get("stats") or {}
            if isinstance(stats, str):
                stats = json.loads(stats)
            gini = stats.get("gini")
            if gini is not None:
                return float(gini)
    return None


def check_dimensions() -> None:
    failures: list[str] = []
    gini_checked = False

    for dim in DIMENSIONS:
        for region, urban_rural, label in FILTER_CASES:
            qs = urllib.parse.urlencode(
                {"dimension": dim, "region": region, "urban_rural": urban_rural}
            )
            path = f"/api/sections?{qs}"
            status, body = _get(path)
            if status >= 500:
                failures.append(f"{path} → HTTP {status} ({label})")
                print(f"  FAIL {path} → HTTP {status}")
                continue
            if status != 200:
                failures.append(f"{path} → HTTP {status} ({label})")
                print(f"  FAIL {path} → HTTP {status}")
                continue
            if not isinstance(body, dict):
                failures.append(f"{path} non-JSON ({label})")
                print(f"  FAIL {path} non-JSON")
                continue
            sections = body.get("sections") or []
            # National all/all should have content for every dimension.
            if region == "all" and urban_rural == "all" and len(sections) == 0:
                failures.append(f"{path} empty sections at national ({label})")
                print(f"  FAIL {path} empty national sections")
                continue
            print(f"  OK  {dim:18} {label:20} sections={len(sections)}")

            if dim == "equity" and region == "all" and urban_rural == "all":
                gini = _extract_equity_gini_from_sections(sections)
                if gini is None:
                    failures.append("national equity f1_gini missing gini stat")
                    print("  FAIL national equity Gini missing")
                else:
                    delta = abs(gini - EXPECTED_GINI)
                    if delta > GINI_TOLERANCE:
                        failures.append(
                            f"Gini {gini} not within {GINI_TOLERANCE} of {EXPECTED_GINI}"
                        )
                        print(f"  FAIL Gini={gini} expected≈{EXPECTED_GINI}")
                    else:
                        print(f"  OK  national equity Gini={gini} (≈{EXPECTED_GINI})")
                        gini_checked = True

    if not gini_checked and not failures:
        failures.append("never checked national equity Gini")

    if failures:
        raise SmokeError("dimension checks failed:\n  - " + "\n  - ".join(failures))


def check_chat_optional() -> None:
    if os.environ.get("SMOKE_CHAT", "").lower() not in ("1", "true", "yes"):
        print("  skip /api/chat (set SMOKE_CHAT=1 to probe)")
        return
    if not os.environ.get("GEMINI_API_KEY"):
        print("  skip /api/chat (GEMINI_API_KEY not set)")
        return
    status, body = _post_json(
        "/api/chat",
        {"message": "What is the national Gini coefficient?"},
        timeout=90.0,
    )
    # Chat may stream SSE; accept any non-5xx as "reachable"
    if status >= 500:
        raise SmokeError(f"/api/chat → HTTP {status}: {body!r}")
    print(f"  OK  /api/chat reachable (HTTP {status})")


def main() -> int:
    print(f"Aequitas local smoke against {BASE_URL}\n")
    try:
        print("1. Health")
        check_health()
        print("\n2. Overview")
        check_overview()
        print("\n3. Dimensions × filters")
        check_dimensions()
        print("\n4. Chat (optional)")
        check_chat_optional()
    except SmokeError as exc:
        print(f"\nSMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    print("\nAll required smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
