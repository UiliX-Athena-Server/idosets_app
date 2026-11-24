from typing import Any

from flask import request, session

from app.models import Accounts
from app.utilities.weights import normalise_unit, to_number


def account_id() -> int:
    return int(session.get("account_id") or 0)


def units() -> str:
    return normalise_unit(session.get("units"))


def body() -> dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def text(value: Any, max_length: int = 255) -> str:
    if value is None:
        return ""
    return str(value).strip()[:max_length]


def whole_number(value: Any, maximum: int = 100_000) -> int:
    return min(int(to_number(value)), maximum)


def ok(**data: Any) -> dict[str, Any]:
    return {"status": "success", **data}


def fail(message: str, status: int = 400) -> tuple[dict[str, Any], int]:
    return {"status": "error", "message": message}, status


def email_failed(result) -> tuple[dict[str, Any], int]:
    """The response for an email that could not be sent."""
    from app.services import RATE_LIMIT_MESSAGE, EmailResult

    if result is EmailResult.RATE_LIMITED:
        return {"status": "rate_limited", "message": RATE_LIMIT_MESSAGE}, 429
    return fail("Unable to send the email, please try again later.", 502)


def not_found(what: str = "Item") -> tuple[dict[str, Any], int]:
    return fail(f"{what} not found.", 404)


def log_in(account: Accounts) -> None:
    session.permanent = True
    session["logged_in"] = True
    session["account_id"] = account.account_id
    session["theme"] = account.theme
    session["units"] = account.units


def session_payload(account: Accounts | None) -> dict[str, Any]:
    if account is None:
        return {
            "logged_in": False,
            "account_id": 0,
            "email_address": None,
            "theme": session.get("theme", "dark"),
            "units": units(),
        }
    return {
        "logged_in": True,
        "account_id": account.account_id,
        "email_address": account.email_address,
        "theme": account.theme,
        "units": account.units,
    }
