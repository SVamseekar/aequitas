#!/usr/bin/env python3
"""81 Ireland filters × overview/score/sections/bands census. API must be running."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from typing import Any

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

REGIONS = [
    "all",
    "carlow",
    "cavan",
    "clare",
    "cork",
    "donegal",
    "dublin",
    "galway",
    "kerry",
    "kildare",
    "kilkenny",
    "laois",
    "leitrim",
    "limerick",
    "longford",
    "louth",
    "mayo",
    "meath",
    "monaghan",
    "offaly",
    "roscommon",
    "sligo",
    "tipperary",
    "waterford",
    "westmeath",
    "wexford",
    "wicklow",
]
URS = ["all", "urban", "rural"]
DIMS = [
    "equity",
    "accessibility",
    "service_quality",
    "route_network",
    "correlations",
    "economic",
    "bus_services_act",
    "scenarios",
]

UK_NOUNS = (
    "LSOA",
    "lsoa",
    "IMD",
    "BODS",
    "BSA",
    "TAG",
    "DfT",
    "franchis",
    "£",
    "Bus Services Act",
)
BANNED_KEYS = ("n_lsoas", "higher_is_better", "catalogue")
OMIT_IDS = {
    "d2_coverage_unemployment",
    "d3_coverage_car",
    "d4_coverage_elderly",
    "d5_coverage_income",
    "d9a_health_access",
    "d9b_employment_access",
    "d9c_crime_access",
    "d9d_environment_access",
    "d9e_barriers_access",
    "f3_ethnic_access",
}


def get(path: str, timeout: float = 60.0) -> tuple[int, Any]:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, body
    except Exception as exc:
        return 0, str(exc)


def walk_find(obj: Any, pred) -> list[str]:
    hits: list[str] = []

    def rec(x: Any, path: str) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                p = f"{path}.{k}" if path else k
                if pred(k, v):
                    hits.append(p)
                rec(v, p)
        elif isinstance(x, list):
            for i, v in enumerate(x[:20]):
                rec(v, f"{path}[{i}]")
        elif isinstance(x, str) and pred(None, x):
            hits.append(path)

    rec(obj, "")
    return hits


def chart_ok(cd: Any) -> bool:
    if not isinstance(cd, dict) or not cd:
        return False
    t = cd.get("type")
    if not t:
        return False
    if t == "kpi_tiles":
        return bool(cd.get("tiles"))
    if t == "lorenz_curve":
        return bool(cd.get("curve_points") or cd.get("data"))
    if t == "gauge":
        return cd.get("value") is not None
    if t in ("box_violin",):
        return bool(cd.get("groups"))
    if t == "shap_bar":
        return bool(cd.get("features"))
    if t == "heatmap":
        return bool(cd.get("values"))
    if t == "table":
        return bool(cd.get("data"))
    if t == "scatter_clusters":
        return bool(cd.get("cluster_sizes") or cd.get("data"))
    return bool(cd.get("data")) or bool(cd.get("tiles"))


def main() -> int:
    flags: list[dict[str, Any]] = []
    scores: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    empty_nonomit: dict[str, int] = defaultdict(int)
    n_filters = 0

    for region in REGIONS:
        for ur in URS:
            n_filters += 1
            q = f"country=ireland&region={region}&urban_rural={ur}"
            key = f"{region}|{ur}"

            st, ov = get(f"/api/overview?{q}")
            if st != 200:
                flags.append({"k": key, "kind": "overview_http", "detail": st})
            else:
                sc = ov.get("score")
                scores[key] = sc
                if sc is None and not (region == "all" and ur != "all"):
                    # possible empty
                    pass
                ticker = json.dumps(ov)
                if "0.5741" in ticker:
                    flags.append({"k": key, "kind": "england_gini", "detail": "0.5741 in overview"})
                if ov.get("score") == 80:
                    flags.append({"k": key, "kind": "england_score", "detail": 80})
                for noun in UK_NOUNS:
                    if noun.lower() in ticker.lower() and noun not in ("franchis",):
                        flags.append({"k": key, "kind": "uk_noun_overview", "detail": noun})
                        break

            st, scb = get(f"/api/score?{q}")
            if st != 200:
                flags.append({"k": key, "kind": "score_http", "detail": st})
            else:
                sv = scb.get("score")
                if isinstance(sv, float) and sv != sv:
                    flags.append({"k": key, "kind": "score_nan"})
                if ov and st == 200 and isinstance(ov, dict) and ov.get("score") != sv:
                    flags.append(
                        {
                            "k": key,
                            "kind": "score_mismatch",
                            "detail": f"overview={ov.get('score')} api={sv}",
                        }
                    )

            st, bands = get(f"/api/reach/bands?{q}")
            if st != 200:
                flags.append({"k": key, "kind": "bands_http", "detail": st})

            payload_bits = []
            for dim in DIMS:
                st, sec = get(f"/api/sections?dimension={dim}&{q}")
                if st != 200:
                    flags.append({"k": key, "kind": "sections_http", "detail": f"{dim} {st}"})
                    continue
                sections = sec.get("sections") or []
                payload_bits.append(json.dumps(sections, sort_keys=True, default=str)[:2000])
                for s in sections:
                    sid = s.get("section_id") or s.get("id")
                    stats = s.get("stats") or {}
                    cd = s.get("chart_data") or {}
                    nar = s.get("narrative") or ""
                    omit = bool(stats.get("omit") or sid in OMIT_IDS)
                    if "n_lsoas" in json.dumps(stats):
                        flags.append({"k": key, "kind": "n_lsoas", "sid": sid})
                    for bk in BANNED_KEYS:
                        if bk in stats and bk != "catalogue":
                            flags.append({"k": key, "kind": "banned_stat", "sid": sid, "detail": bk})
                    if omit:
                        if chart_ok(cd):
                            flags.append({"k": key, "kind": "omit_has_chart", "sid": sid})
                        if not (nar or stats.get("reason")):
                            flags.append({"k": key, "kind": "omit_no_sentence", "sid": sid})
                    else:
                        if stats.get("insufficient_data") or stats.get("empty"):
                            continue
                        if not chart_ok(cd):
                            empty_nonomit[sid or "?"] += 1
                            flags.append({"k": key, "kind": "empty_chart", "sid": sid, "type": (cd or {}).get("type")})
                    blob = (nar + json.dumps(stats)).lower()
                    for noun in ("lsoa", "imd 2019", "bods", "bus services act", "green book"):
                        if noun in blob:
                            flags.append({"k": key, "kind": "uk_noun_section", "sid": sid, "detail": noun})

            hashes[key] = str(hash("|".join(payload_bits)))

    if hashes.get("dublin|all") and hashes.get("cork|all"):
        if hashes["dublin|all"] == hashes["cork|all"]:
            flags.append({"k": "dublin|cork", "kind": "identical_payloads"})

    # print summary
    by_kind: dict[str, int] = defaultdict(int)
    for f in flags:
        by_kind[f["kind"]] += 1

    print("FILTERS", n_filters)
    print("SCORES_SAMPLE")
    for k in ("all|all", "dublin|all", "cork|all", "cork|rural", "leitrim|all", "dublin|rural"):
        print(" ", k, scores.get(k))
    print("FLAG_COUNTS")
    for k, v in sorted(by_kind.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print("EMPTY_CHART_BY_SID")
    for sid, n in sorted(empty_nonomit.items(), key=lambda x: -x[1]):
        print(f"  {sid}: {n}")
    print("FLAGS_HEAD")
    for f in flags[:80]:
        print(" ", f)

    outp = os.environ.get("CENSUS_OUT", "data/ireland_qa_census.json")
    os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)
    with open(outp, "w") as fh:
        json.dump({"n_filters": n_filters, "scores": scores, "flag_counts": dict(by_kind), "empty_nonomit": dict(empty_nonomit), "flags": flags}, fh)
    print("WROTE", outp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
