"""Allow OAuth to resume a known local application page without open redirects."""

import re
from urllib.parse import urlsplit

_PAGE = (
    r"(?:equity|access|service|network|correlations|economy|policy|scenarios"
    r"|studio|compare|reach|time|ops)"
)
_PATH = re.compile(
    rf"(?:/app/(?:england|ireland|netherlands|france)(?:/{_PAGE})?/?"
    r"|/(?:saved|notes|regions|conversations|profile)|/invite/[A-Za-z0-9_-]{1,256})"
)


def safe_return_path(value: str | None) -> str:
    """Only known same-origin routes can survive the signed OAuth session."""
    fallback = "/app/england"
    if (
        not value
        or not value.startswith("/")
        or value.startswith("//")
        or len(value) > 4096
        or "\\" in value
        or any(ord(c) < 32 for c in value)
    ):
        return fallback
    parts = urlsplit(value)
    if parts.scheme or parts.netloc or not _PATH.fullmatch(parts.path):
        return fallback
    return value
