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

# Gini must be a valid coefficient after recompute — not locked to June 2026.

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
                elif not (0.0 <= gini <= 1.0):
                    failures.append(f"Gini {gini} outside [0, 1]")
                    print(f"  FAIL Gini={gini} not a valid coefficient")
                else:
                    print(f"  OK  national equity Gini={gini:.4f}")
                    gini_checked = True

    if not gini_checked and not failures:
        failures.append("never checked national equity Gini")

    if failures:
        raise SmokeError("dimension checks failed:\n  - " + "\n  - ".join(failures))


def check_studio() -> None:
    # Shropshire 035A (WM rural) is >8 km from the nearest packed stop — a real desert.
    payload = {
        "country": "england",
        "region": "E12000005",
        "urban_rural": "rural",
        "source": "drawn",
        "ops": [{"op": "add_stop", "lat": 52.48283, "lon": -2.56191, "name": "Smoke desert stop"}],
    }
    status, body = _post_json("/api/studio/jobs", payload, timeout=90.0)
    if status != 200:
        raise SmokeError(f"/api/studio/jobs → HTTP {status}: {body!r}")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as exc:
            raise SmokeError(f"/api/studio/jobs non-JSON: {body!r}") from exc
    if not isinstance(body, dict):
        raise SmokeError(f"/api/studio/jobs unexpected body: {body!r}")
    job_id = body.get("id")
    if not job_id:
        raise SmokeError(f"/api/studio/jobs missing id: {body}")
    if body.get("status") == "done":
        st, result = _get(f"/api/studio/jobs/{job_id}/result")
        if st != 200 or not isinstance(result, dict):
            raise SmokeError(f"studio result → HTTP {st}: {result!r}")
        if "score_before" not in result or "note" not in result:
            raise SmokeError(f"studio result schema: {result!r}")
        if result.get("mode") == "needs_centroids":
            raise SmokeError("studio still needs_centroids — walk-to-stop is not live")
        if result.get("people_gained", 0) <= 0:
            raise SmokeError(
                f"expected people_gained > 0 on a WM rural desert stop, got {result.get('people_gained')}"
            )
        print(
            f"  OK  /api/studio/jobs → {result.get('mode')} "
            f"{result.get('score_before')}→{result.get('score_after')} "
            f"gained={result.get('people_gained')}"
        )
        return
    print(f"  OK  /api/studio/jobs accepted id={job_id} status={body.get('status')}")


def check_reach_pack() -> None:
    status, body = _get("/api/reach/bands?region=E12000005&urban_rural=rural")
    if status != 200 or not isinstance(body, dict):
        raise SmokeError(f"/api/reach/bands → HTTP {status}: {body!r}")
    if body.get("empty") and "London" in str(body.get("empty_reason")):
        raise SmokeError("West Midlands rural returned London empty copy")
    if "official PTAL" in json.dumps(body).lower() and body.get("not_tfl_ptal") is not True:
        raise SmokeError("bands payload must set not_tfl_ptal")
    print(
        f"  OK  /api/reach/bands WM rural empty={body.get('empty')} "
        f"mode={body.get('mode')} people={body.get('people')} n={body.get('n_areas')}"
    )
    status, body = _get("/api/reach/bands?region=E12000007&urban_rural=rural")
    if status != 200 or not isinstance(body, dict) or not body.get("empty"):
        raise SmokeError(f"London × rural bands should be empty: {body!r}")
    print("  OK  /api/reach/bands London × rural empty")
    status, body = _get("/api/reach?dest_type=jobs&cutoff=45&region=E12000005")
    if status != 200 or not isinstance(body, dict):
        raise SmokeError(f"/api/reach → HTTP {status}: {body!r}")
    if body.get("available") is True and body.get("median") is None:
        raise SmokeError("reach available but median missing")
    print(f"  OK  /api/reach available={body.get('available')} note={str(body.get('note'))[:80]}")
    status, text = _get("/api/export/pack.csv?region=E12000005&urban_rural=rural")
    if status != 200:
        raise SmokeError(f"/api/export/pack.csv → HTTP {status}")
    raw = text if isinstance(text, str) else json.dumps(text)
    if "Section,Item,Value" not in raw and "In-country score" not in raw:
        raise SmokeError("pack CSV missing English headers")
    if "statutory BSIP" not in raw and "Research pack" not in raw:
        raise SmokeError("pack CSV missing caveats")
    print("  OK  /api/export/pack.csv")


def check_time() -> None:
    status, body = _get("/api/time?country=england&metric=score")
    if status != 200 or not isinstance(body, dict):
        raise SmokeError(f"/api/time england → HTTP {status}: {body!r}")
    if body.get("area_noun") != "LSOAs":
        raise SmokeError(f"England time should say LSOAs: {body}")
    print(f"  OK  /api/time england points={len(body.get('points') or [])} one_date={body.get('one_date')}")
    status, body = _get("/api/time?country=ireland&metric=score")
    if status != 200 or not isinstance(body, dict):
        raise SmokeError(f"/api/time ireland → HTTP {status}: {body!r}")
    if body.get("area_noun") != "Small Areas":
        raise SmokeError(f"Ireland time should say Small Areas: {body}")
    print(f"  OK  /api/time ireland points={len(body.get('points') or [])}")
    status, body = _get("/api/time?country=netherlands")
    if status != 200 or not isinstance(body, dict) or not body.get("empty"):
        raise SmokeError(f"NL time should be empty: {body!r}")
    print("  OK  /api/time netherlands empty")


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
        print("\n4. Studio job")
        check_studio()
        print("\n5. Reach bands + research pack")
        check_reach_pack()
        print("\n6. Time series")
        check_time()
        print("\n7. Chat (optional)")
        check_chat_optional()
    except SmokeError as exc:
        print(f"\nSMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    print("\nAll required smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
