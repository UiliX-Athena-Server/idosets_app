from email.utils import parseaddr
from secrets import token_urlsafe

from email_validator import EmailNotValidError, validate_email
from flask import current_app, render_template, session
from flask_imp import ImpBlueprint

from app.api.helpers import (
    body,
    email_failed,
    fail,
    log_in,
    ok,
    session_payload,
)
from app.extensions import db
from app.models import Accounts
from app.services import EmailResult, send_email
from app.utilities import dates

LOGIN_LINK_DAYS = 30


def include(bp: ImpBlueprint):
    @bp.post("/login")
    def login():
        _, email_address = parseaddr(str(body().get("email_address", "")))

        try:
            email_address = validate_email(
                email_address, check_deliverability=False
            ).normalized
        except EmailNotValidError:
            return fail("Email address is not valid.")

        account = Accounts.get_by_email(email_address)
        is_new = account is None

        if is_new:
            account = Accounts(
                email_address=email_address,
                settings={"theme": "dark", "units": "kgs"},
                created=dates.now(),
            )
            db.session.add(account)
            db.session.commit()

        auth_code = token_urlsafe(48)
        account.set_auth_code(auth_code, dates.days_from_now(LOGIN_LINK_DAYS))

        url = f"{current_app.config['SET_HOST_URL']}/auth"
        template = "welcome-email.html" if is_new else "login-email.html"
        subject = (
            "Welcome to idosets.app!" if is_new else "Here's your login link!"
        )

        result = send_email(
            to=email_address,
            subject=subject,
            html=render_template(
                template,
                url=url,
                account_id=account.account_id,
                auth=auth_code,
            ),
        )
        if result is not EmailResult.SENT:
            return email_failed(result)

        return ok(message="Login email sent.")

    @bp.post("/auth")
    def auth():
        data = body()
        account = Accounts.from_auth_code(
            data.get("account_id"), data.get("auth_code")
        )
        if not account:
            return fail("Your login link has expired or is not valid.", 401)

        log_in(account)
        return ok(message="Logged in.", **session_payload(account))

    @bp.get("/auth/session")
    def auth_session():
        account = None
        if session.get("logged_in"):
            account = Accounts.get(session.get("account_id"))
            if account is None:
                # The account was deleted, drop the stale session.
                session.clear()
        return ok(**session_payload(account))

    @bp.post("/logout")
    def logout():
        session.clear()
        return ok(message="You have been logged out.")
