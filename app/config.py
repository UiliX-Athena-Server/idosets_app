import logging
from os import getenv
from secrets import token_hex

from dotenv import load_dotenv
from flask_imp.config import FlaskConfig, ImpConfig, SQLiteDatabaseConfig

load_dotenv()

log = logging.getLogger(__name__)

RUN_ENV = getenv("RUN_ENV", "development")
SET_HOST_URL = getenv("SET_HOST_URL", "http://127.0.0.1:5001").rstrip("/")
# Only mark the cookie as https-only when the site is actually served over
# https, otherwise local development could never log in.
HTTPS = SET_HOST_URL.startswith("https://")

_secret_key = getenv("SECRET_KEY")
if not _secret_key or _secret_key == "-":
    # A random key per process means sessions break between gunicorn workers
    # and restarts, so make this loud in production.
    log.warning("SECRET_KEY is not set; using a random key for this process.")
    _secret_key = token_hex(32)

# Routes that are rendered by the SolidJS app. The SPA does its own routing,
# Flask only has to return the shell for each of these.
SPA_ROUTES = (
    "/login",
    "/logout",
    "/account",
    "/account/delete/<account_id>/<auth_code>",
    "/workouts",
    "/workout/<workout_id>",
    "/workout/<workout_id>/logs",
    "/workout/<workout_id>/exercise/<exercise_id>",
    "/workout/<workout_id>/session/<workout_session_id>",
)

flask_config = FlaskConfig(
    secret_key=_secret_key,
    permanent_session_lifetime=60 * 60 * 24 * 31,
    session_cookie_samesite="Lax",
    session_cookie_secure=HTTPS,
    session_cookie_httponly=True,
)

flask_config.set_additional(
    set_host_url=SET_HOST_URL,
    run_env=RUN_ENV,
)

imp_config = ImpConfig(
    init_session={
        "logged_in": False,
        "account_id": 0,
        "theme": "dark",
        "units": "kgs",
    },
    database_main=SQLiteDatabaseConfig(),
)
