from secrets import token_urlsafe

from flask import current_app, render_template, session
from flask_imp import ImpBlueprint
from flask_imp.security import checkpoint

from app.api.helpers import (
    account_id,
    body,
    email_failed,
    fail,
    log_in,
    ok,
    session_payload,
)
from app.checkpoints import LOGIN_REQUIRED
from app.models import Accounts, Exercises, Sets, Workouts
from app.models.accounts import normalise_theme
from app.services import EmailResult, send_email
from app.utilities import dates
from app.utilities.weights import normalise_unit


def include(bp: ImpBlueprint):
    @bp.get("/account")
    @checkpoint(LOGIN_REQUIRED)
    def account_info():
        account = Accounts.get(account_id())
        if not account:
            session.clear()
            return fail("Account not found.", 401)

        return ok(
            email_address=account.email_address,
            days_old=account.days_old(),
            total_workouts=Workouts.count_for_account(account.account_id),
            total_exercises=Exercises.count_for_account(account.account_id),
            total_sets=Sets.count_for_account(account.account_id),
        )

    @bp.post("/settings")
    def update_settings():
        """
        Works logged out too (the landing page has a theme toggle). When
        logged in the choice is also saved to the account so it follows the
        user to other devices.
        """
        data = body()
        theme = data.get("theme")
        units = data.get("units")

        if theme is not None:
            session["theme"] = normalise_theme(theme)
        if units is not None:
            session["units"] = normalise_unit(units)

        account = None
        if session.get("logged_in"):
            account = Accounts.get(account_id())
            if account:
                account.update_settings(theme=theme, units=units)
                log_in(account)

        return ok(**session_payload(account))

    @bp.post("/account/delete/request")
    @checkpoint(LOGIN_REQUIRED)
    def request_delete():
        account = Accounts.get(account_id())
        if not account:
            return fail("Account not found.", 404)

        auth_code = token_urlsafe(48)
        account.set_auth_code(auth_code, dates.days_from_now(1))

        result = send_email(
            to=account.email_address,
            subject="Deleting your idosets.app account",
            html=render_template(
                "delete-account-email.html",
                url=f"{current_app.config['SET_HOST_URL']}/account/delete",
                account_id=account.account_id,
                auth=auth_code,
            ),
        )
        if result is not EmailResult.SENT:
            return email_failed(result)

        return ok(message="Account deletion email sent.")

    @bp.post("/account/delete")
    def delete_account():
        # The emailed auth code proves ownership, so this works even if the
        # link is opened on a device that isn't logged in.
        data = body()
        account = Accounts.from_auth_code(
            data.get("account_id"), data.get("auth_code")
        )
        if not account:
            return fail("This link has expired or is not valid.", 401)

        Accounts.delete_with_data(account.account_id)
        session.clear()
        return ok(message="Account deleted.")
