"""Brevo transactional email client for invite delivery."""
from __future__ import annotations

import requests
from loguru import logger

from aequitas.api.config import ApiConfig

_BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"
_FROM_EMAIL = "noreply@aequitas.app"
_FROM_NAME = "Aequitas"


async def send_invite_email(
    *, to_email: str, tenant_name: str, invite_link: str
) -> bool:
    """Send an invite email via Brevo. Returns False on any failure — never raises.

    Invite creation must succeed even when email delivery fails (best-effort
    on top of the link-based flow), so callers should not treat a False
    return as a reason to roll back the invite row.
    """
    cfg = ApiConfig()
    if not cfg.brevo_api_key:
        logger.warning("BREVO_API_KEY not set — invite email not sent")
        return False

    payload = {
        "sender": {"name": _FROM_NAME, "email": _FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": f"You've been invited to join {tenant_name} on Aequitas",
        "htmlContent": (
            f"<p>You've been invited to join <strong>{tenant_name}</strong> on Aequitas.</p>"
            f'<p><a href="{invite_link}">Accept the invite</a></p>'
        ),
    }
    headers = {"api-key": cfg.brevo_api_key, "content-type": "application/json"}

    try:
        response = requests.post(
            _BREVO_SEND_URL, json=payload, headers=headers, timeout=10
        )
    except Exception as exc:
        logger.warning(f"Invite email send failed (network error): {exc}")
        return False

    if not (200 <= response.status_code < 300):
        logger.warning(
            f"Invite email send failed (HTTP {response.status_code}): "
            f"{getattr(response, 'text', '')}"
        )
        return False

    return True
