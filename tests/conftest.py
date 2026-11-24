import os

import pytest

os.environ["EMAIL_DEV_MODE"] = "1"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app import create_app
from app.extensions import db


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.sqlite"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SET_HOST_URL": "http://localhost",
        }
    )
    return app


@pytest.fixture(autouse=True)
def fresh_db(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email="lifter@example.com"):
    """Log in through the real magic-link flow and return the account id."""
    from app.models import Accounts

    assert (
        client.post("/api/login", json={"email_address": email}).status_code
        == 200
    )
    with client.application.app_context():
        account = Accounts.get_by_email(email)
        account_id, auth_code = account.account_id, account.auth_code

    response = client.post(
        "/api/auth", json={"account_id": account_id, "auth_code": auth_code}
    )
    assert response.status_code == 200, response.json
    return account_id


@pytest.fixture
def logged_in(client):
    return login(client)


def build_workout(client):
    """A workout with one exercise holding a reps set and a duration set."""
    workout = client.post("/api/workouts", json={"name": "Push"}).json[
        "workout"
    ]
    wid = workout["workout_id"]
    exercise = client.post(
        f"/api/workouts/{wid}/exercises", json={"name": "Bench", "info_url": ""}
    ).json["exercise"]
    eid = exercise["exercise_id"]
    reps = client.post(
        f"/api/workouts/{wid}/exercises/{eid}/sets",
        json={"type": "reps", "reps_min": 8, "reps_max": 12},
    ).json["set"]
    timed = client.post(
        f"/api/workouts/{wid}/exercises/{eid}/sets",
        json={"type": "duration", "duration_min": 30, "duration_max": 60},
    ).json["set"]
    return wid, eid, reps["set_id"], timed["set_id"]
