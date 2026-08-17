"""HTTP fetches for ops collectors. Log every URL; never invent a fallback."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from typing import Any

import requests

USER_AGENT = "aequitas-ops/0.1 (+https://github.com; research briefing; not a commercial AVL client)"


@dataclass
class FetchHit:
    url: str
    status: int | None
    bytes: int
    elapsed_ms: int
    entity: str
    auth: str
    error: str | None = None
    content_type: str | None = None
    redirected_to: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def fetch_bytes(
    url: str,
    *,
    entity: str,
    auth: str = "none",
    headers: dict[str, str] | None = None,
    timeout: int = 60,
    api_key: str | None = None,
    api_key_header: str | None = None,
    api_key_query: str | None = None,
) -> tuple[FetchHit, bytes | None]:
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    params: dict[str, str] = {}
    if api_key and api_key_header:
        hdrs[api_key_header] = api_key
    if api_key and api_key_query:
        params[api_key_query] = api_key
    t0 = time.perf_counter()
    try:
        r = requests.get(url, headers=hdrs, params=params, timeout=timeout, allow_redirects=True)
        elapsed = int((time.perf_counter() - t0) * 1000)
        body = r.content or b""
        hit = FetchHit(
            url=url,
            status=r.status_code,
            bytes=len(body),
            elapsed_ms=elapsed,
            entity=entity,
            auth=auth,
            content_type=r.headers.get("Content-Type"),
            redirected_to=r.url if r.url != url else None,
        )
        if r.status_code >= 400:
            hit.error = f"HTTP {r.status_code}"
            return hit, None
        return hit, body
    except requests.RequestException as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        hit = FetchHit(
            url=url,
            status=None,
            bytes=0,
            elapsed_ms=elapsed,
            entity=entity,
            auth=auth,
            error=f"{type(exc).__name__}: {exc}",
        )
        return hit, None


def env_key(*names: str) -> str | None:
    for name in names:
        val = os.environ.get(name, "").strip()
        if val:
            return val
    return None
