"""
Outgoing email, sent through notifyvia.email (https://pypi.org/project/notifyvia-email/).

Every email is sent with notifyvia.email's rate limiter turned on: at most
``EMAIL_DAILY_LIMIT`` emails per sender IPv4 address per day. When the limit is
hit the caller gets ``EmailResult.RATE_LIMITED`` and can tell the user.
"""

import ipaddress
import logging
from enum import Enum
from os import getenv

from flask import request
from notifyvia_email.v3 import NotifyViaEmail, SendResult

log = logging.getLogger(__name__)

EMAIL_DAILY_LIMIT = 5
ONE_DAY_SECONDS = 60 * 60 * 24

_TRUTHY = {"1", "true", "yes"}


class EmailResult(Enum):
    SENT = "sent"
    RATE_LIMITED = "rate_limited"
    FAILED = "failed"


def _client() -> NotifyViaEmail:
    return NotifyViaEmail(api_key=getenv("NOTIFYVIA_EMAIL_API_KEY", ""))


def _dev_mode() -> bool:
    return getenv("EMAIL_DEV_MODE", "0").lower() in _TRUTHY


def client_ipv4() -> str | None:
    """
    The requester's IPv4 address. Behind the reverse proxy the real address is
    the first entry of X-Forwarded-For.
    """
    candidates = []
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        candidates.append(forwarded.split(",")[0].strip())
    if request.remote_addr:
        candidates.append(request.remote_addr)

    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if isinstance(address, ipaddress.IPv4Address):
            return str(address)
    return None


def send_email(to: str, subject: str, html: str) -> EmailResult:
    if _dev_mode():
        print("---- email (EMAIL_DEV_MODE, not sent) ----")
        print("To:", to)
        print("Subject:", subject)
        print(html)
        print("------------------------------------------")
        return EmailResult.SENT

    response = _client().send(
        to=to,
        subject=subject,
        html=html,
        enable_rate_limiter=True,
        limit=EMAIL_DAILY_LIMIT,
        within_seconds=ONE_DAY_SECONDS,
        ipv4_address=client_ipv4(),
    )

    if response.ok:
        return EmailResult.SENT
    if response.result is SendResult.RATE_LIMIT_EXCEEDED:
        return EmailResult.RATE_LIMITED

    log.error(
        "notifyvia.email failed to send (%s): %s",
        response.result.name,
        response.errors,
    )
    return EmailResult.FAILED


RATE_LIMIT_MESSAGE = (
    f"You've reached the limit of {EMAIL_DAILY_LIMIT} emails a day. "
    "Please try again tomorrow."
)

__all__ = [
    "EMAIL_DAILY_LIMIT",
    "RATE_LIMIT_MESSAGE",
    "EmailResult",
    "send_email",
]
