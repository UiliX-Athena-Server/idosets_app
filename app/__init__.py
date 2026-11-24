from pathlib import Path

from flask import Flask, redirect, render_template, session
from sqlalchemy.engine import make_url

from app.config import SPA_ROUTES, flask_config, imp_config
from app.extensions import db, imp, vt


def _create_database_if_missing(app: Flask) -> None:
    """Create the SQLite database file and its tables on first run."""
    url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if url.get_backend_name() != "sqlite" or url.database in (
        None,
        "",
        ":memory:",
    ):
        return

    database_file = Path(url.database)
    if database_file.exists():
        return

    database_file.parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db.create_all()
    app.logger.info("Created a new database at %s", database_file)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        static_url_path="/",
        static_folder="static",
        template_folder="templates",
    )
    flask_config.init_app(app)
    if test_config:
        app.config.update(test_config)

    imp.init_app(app, imp_config)
    imp.import_resources("resources")
    imp.import_blueprint("api")
    imp.import_models("models")

    # In development the Vite dev server proxies /api to Flask, so no CORS
    # configuration is needed.
    vt.init_app(app)

    db.init_app(app)
    _create_database_if_missing(app)

    def spa(**_):
        return render_template("index.html")

    app.add_url_rule("/", "index", spa)
    for rule in SPA_ROUTES:
        app.add_url_rule(rule, "spa", spa)

    @app.get("/auth/<account_id>/<auth_code>")
    def auth(account_id, auth_code):
        """The link in the login email. Logs in without needing JavaScript."""
        from app.api.helpers import log_in
        from app.models import Accounts

        account = Accounts.from_auth_code(account_id, auth_code)
        if account:
            log_in(account)
            return redirect("/workouts")

        # Let the SPA show a friendly "link expired" message.
        return render_template("index.html")

    @app.before_request
    def keep_session_alive():
        session.permanent = True

    return app
