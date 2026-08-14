#!/usr/bin/env python3
"""Ireland pack smoke — health, overview, score, bands, one county.

Does not assert a frozen Gini. API must already be running.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")


class SmokeError(Exception):
    pass


def _get(path: str, *, timeout: float = 30.0) -> tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise SmokeError(f"Connection failed for {url}: {exc.reason}") from exc


def main() -> int:
    st, health = _get("/api/health")
    if st != 200:
        raise SmokeError(f"health {st}")
    print("health", health)

    st, packs = _get("/api/packs")
    if st != 200 or not packs.get("ireland", {}).get("packReady"):
        raise SmokeError(f"Ireland pack not ready: {packs}")
    print("packs ireland ready")

    st, ov = _get("/api/overview?country=ireland&region=all&urban_rural=all")
    if st != 200:
        raise SmokeError(f"overview {st}")
    gini = next(d["headline_stat"]["value"] for d in ov["dimensions"] if d["id"] == "equity")
    if abs(float(gini) - 0.5741) < 1e-6:
        raise SmokeError("Ireland overview returned England Gini 0.5741")
    if ov.get("score") == 80:
        raise SmokeError("Ireland score is England 80")
    print("ireland overview score", ov.get("score"), "gini", gini)

    st, score = _get("/api/score?country=ireland&region=all&urban_rural=all")
    if st != 200:
        raise SmokeError(f"score {st}")
    print("ireland score", score.get("score"))

    st, bands = _get("/api/reach/bands?country=ireland&region=all&urban_rural=all")
    if st != 200:
        raise SmokeError(f"bands {st}")
    print("ireland bands empty", bands.get("empty"), "n", bands.get("n_areas"))

    st, cork = _get("/api/overview?country=ireland&region=cork&urban_rural=all")
    if st != 200:
        raise SmokeError(f"cork overview {st}")
    print("cork score", cork.get("score"), "note", cork.get("score_note"))

    st, dub = _get("/api/overview?country=ireland&region=dublin&urban_rural=all")
    if st != 200:
        raise SmokeError(f"dublin overview {st}")
    if cork.get("score") is not None and dub.get("score") is not None:
        if cork.get("score") == dub.get("score") == 0:
            raise SmokeError("Cork and Dublin scores are both 0 — seed/fail pack")
    print("dublin score", dub.get("score"))

    for dim in (
        "accessibility",
        "service_quality",
        "route_network",
        "correlations",
        "equity",
        "economic",
        "bus_services_act",
        "scenarios",
    ):
        st, body = _get(f"/api/sections?dimension={dim}&country=ireland&region=cork&urban_rural=all")
        if st != 200:
            raise SmokeError(f"sections {dim} {st}")
        secs = body.get("sections") or []
        if not secs:
            raise SmokeError(f"no Ireland sections for {dim}")
        blob = json.dumps(secs).lower()
        if dim == "bus_services_act" and "bus services act 2025" in blob and "not applicable" in blob:
            raise SmokeError("Policy still England BSA not-applicable")
        if dim == "economic" and "not_applicable" in blob and "tag" in blob and "caf" not in blob:
            raise SmokeError("Economy still TAG not-applicable")
        print("sections", dim, len(secs))

    st, t = _get("/api/time?country=ireland&metric=score")
    if st != 200 or t.get("area_noun") != "Small Areas":
        raise SmokeError(f"ireland time {st} {t}")
    print("ireland time points", len(t.get("points") or []), "one_date", t.get("one_date"))

    st, packs = _get("/api/packs")
    if packs.get("netherlands", {}).get("packReady") or packs.get("france", {}).get("packReady"):
        raise SmokeError("NL/FR marked live")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeError as exc:
        print(f"SMOKE FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
