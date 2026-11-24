from sqlalchemy import text

from app.extensions import db
from tests.conftest import build_workout, login


def test_requires_login(client):
    response = client.get("/api/workouts")
    assert response.status_code == 401
    assert response.json["status"] == "unauthorized"


def test_session_endpoint_logged_out(client):
    data = client.get("/api/auth/session").json
    assert data["logged_in"] is False


def test_login_and_session(client, logged_in):
    data = client.get("/api/auth/session").json
    assert data["logged_in"] is True
    assert data["account_id"] == logged_in
    assert data["email_address"] == "lifter@example.com"


def test_bad_auth_code_is_rejected(client):
    client.post("/api/login", json={"email_address": "a@example.com"})
    response = client.post(
        "/api/auth", json={"account_id": 1, "auth_code": "nope"}
    )
    assert response.status_code == 401


def test_invalid_email(client):
    response = client.post("/api/login", json={"email_address": "not-an-email"})
    assert response.status_code == 400


def test_workout_crud(client, logged_in):
    wid, eid, reps_set, timed_set = build_workout(client)

    workouts = client.get("/api/workouts").json["workouts"]
    assert workouts[0]["exercise_count"] == 1
    assert workouts[0]["active_session_id"] is None

    workout = client.get(f"/api/workouts/{wid}").json
    assert workout["exercises"][0]["set_count"] == 2

    client.patch(f"/api/workouts/{wid}", json={"name": "Push Day"})
    assert (
        client.get(f"/api/workouts/{wid}").json["workout"]["name"] == "Push Day"
    )

    exercise = client.get(f"/api/workouts/{wid}/exercises/{eid}").json
    assert [s["set_id"] for s in exercise["sets"]] == [reps_set, timed_set]
    assert exercise["sets"][0]["reps_min"] == 8

    assert client.delete(f"/api/workouts/{wid}").status_code == 200
    assert client.get(f"/api/workouts/{wid}").status_code == 404


def test_copy_set_inserts_directly_after(client, logged_in):
    wid, eid, reps_set, timed_set = build_workout(client)
    copy = client.post(
        f"/api/workouts/{wid}/exercises/{eid}/sets/{reps_set}/copy"
    ).json
    assert copy["after_set_id"] == reps_set
    sets = client.get(f"/api/workouts/{wid}/exercises/{eid}").json["sets"]
    assert [s["set_id"] for s in sets] == [
        reps_set,
        copy["set"]["set_id"],
        timed_set,
    ]
    assert [s["order"] for s in sets] == [0, 1, 2]
    assert sets[1]["reps_min"] == 8 and sets[1]["reps_max"] == 12

    client.delete(f"/api/workouts/{wid}/exercises/{eid}/sets/{reps_set}")
    sets = client.get(f"/api/workouts/{wid}/exercises/{eid}").json["sets"]
    assert [s["order"] for s in sets] == [0, 1]


def test_other_accounts_cannot_touch_my_data(app, client, logged_in):
    wid, eid, reps_set, _ = build_workout(client)

    intruder = app.test_client()
    login(intruder, "intruder@example.com")

    assert intruder.get(f"/api/workouts/{wid}").status_code == 404
    assert (
        intruder.patch(f"/api/workouts/{wid}", json={"name": "x"}).status_code
        == 404
    )
    assert intruder.delete(f"/api/workouts/{wid}").status_code == 404
    assert (
        intruder.delete(f"/api/workouts/{wid}/exercises/{eid}").status_code
        == 404
    )
    assert (
        intruder.delete(
            f"/api/workouts/{wid}/exercises/{eid}/sets/{reps_set}"
        ).status_code
        == 404
    )
    assert intruder.get(f"/api/workouts/{wid}/logs").status_code == 404
    assert intruder.post(f"/api/workouts/{wid}/sessions").status_code == 404

    # still intact for the owner
    assert client.get(f"/api/workouts/{wid}").status_code == 200


def test_full_workout_session(client, logged_in):
    wid, eid, reps_set, timed_set = build_workout(client)

    started = client.post(f"/api/workouts/{wid}/sessions").json[
        "workout_session"
    ]
    sid = started["workout_session_id"]

    # Starting again resumes the same session instead of creating another.
    again = client.post(f"/api/workouts/{wid}/sessions").json["workout_session"]
    assert again["workout_session_id"] == sid
    assert (
        client.get("/api/workouts").json["workouts"][0]["active_session_id"]
        == sid
    )

    log_url = f"/api/workouts/{wid}/sessions/{sid}/sets/{reps_set}/log"
    logged = client.put(log_url, json={"reps": 10, "weight": "62.5"}).json[
        "set_log"
    ]
    assert logged["reps"] == 10 and logged["weight"] == 62.5

    # Logging the same set again replaces it (no duplicates).
    client.put(log_url, json={"reps": 9, "weight": 60})
    session = client.get(f"/api/workouts/{wid}/sessions/{sid}").json
    sets = session["exercises"][0]["sets"]
    assert sets[0]["set_log"]["reps"] == 9
    assert sets[1]["set_log"] is None

    # Undo
    client.delete(log_url)
    session = client.get(f"/api/workouts/{wid}/sessions/{sid}").json
    assert session["exercises"][0]["sets"][0]["set_log"] is None

    # Finish, sending logs the client made (e.g. while offline).
    finish_url = f"/api/workouts/{wid}/sessions/{sid}/finish"
    finished = client.post(
        finish_url,
        json={
            "logs": [
                {"set_id": reps_set, "reps": 10, "weight": 50},
                {"set_id": timed_set, "duration": 45},
                {"set_id": 999999, "reps": 1},  # unknown set is ignored
            ]
        },
    ).json
    assert finished["workout_session"]["is_finished"] is True
    assert finished["workout_session"]["total_weight"] == 500  # 50kg x 10
    assert finished["workout_session"]["sets_done"] == 2
    assert finished["workout"]["name"] == "Push"

    # Finishing twice (retry after a timeout) is harmless.
    retry = client.post(
        finish_url, json={"logs": [{"set_id": reps_set, "reps": 99}]}
    ).json
    assert (
        retry["workout_session"]["finished"]
        == finished["workout_session"]["finished"]
    )
    assert retry["workout_session"]["sets_done"] == 2
    assert retry["exercises"][0]["sets"][0]["set_log"]["reps"] == 10

    # Can't log against a finished session.
    assert client.put(log_url, json={"reps": 1}).status_code == 409

    last = client.get("/api/workouts").json
    assert last["last_session"]["workout_session_id"] == sid
    assert last["workouts"][0]["active_session_id"] is None

    logs = client.get(f"/api/workouts/{wid}/logs").json
    assert [log["reps"] for log in logs["exercises"][0]["logs"]] == [10, 0]


def test_logs_are_the_most_recent_ones(client, logged_in):
    wid, eid, reps_set, _ = build_workout(client)
    for reps in range(1, 6):
        sid = client.post(f"/api/workouts/{wid}/sessions").json[
            "workout_session"
        ]["workout_session_id"]
        client.post(
            f"/api/workouts/{wid}/sessions/{sid}/finish",
            json={"logs": [{"set_id": reps_set, "reps": reps}]},
        )
    logs = client.get(f"/api/workouts/{wid}/logs?limit=3").json["exercises"][0][
        "logs"
    ]
    assert [log["reps"] for log in logs] == [3, 4, 5]


def test_units_are_respected(client, logged_in):
    wid, eid, reps_set, _ = build_workout(client)
    settings = client.post("/api/settings", json={"units": "lbs"}).json
    assert settings["units"] == "lbs"

    sid = client.post(f"/api/workouts/{wid}/sessions").json["workout_session"][
        "workout_session_id"
    ]
    client.put(
        f"/api/workouts/{wid}/sessions/{sid}/sets/{reps_set}/log",
        json={"reps": 5, "weight": 100},
    )
    client.post("/api/settings", json={"units": "kgs"})
    session = client.get(f"/api/workouts/{wid}/sessions/{sid}").json
    assert session["exercises"][0]["sets"][0]["set_log"]["weight"] == 45.36

    # Settings are saved to the account, not just the browser session.
    client.post("/api/settings", json={"theme": "light"})
    client.post("/api/logout")
    login(client)
    assert client.get("/api/auth/session").json["theme"] == "light"


def test_cancel_session(client, logged_in):
    wid, _, reps_set, _ = build_workout(client)
    sid = client.post(f"/api/workouts/{wid}/sessions").json["workout_session"][
        "workout_session_id"
    ]
    client.put(
        f"/api/workouts/{wid}/sessions/{sid}/sets/{reps_set}/log",
        json={"reps": 1},
    )
    assert (
        client.delete(f"/api/workouts/{wid}/sessions/{sid}").status_code == 200
    )
    assert client.get(f"/api/workouts/{wid}/sessions/{sid}").status_code == 404
    assert (
        client.get("/api/workouts").json["workouts"][0]["active_session_id"]
        is None
    )


def test_delete_account_removes_everything(app, client, logged_in):
    wid, _, reps_set, _ = build_workout(client)
    sid = client.post(f"/api/workouts/{wid}/sessions").json["workout_session"][
        "workout_session_id"
    ]
    client.post(
        f"/api/workouts/{wid}/sessions/{sid}/finish",
        json={"logs": [{"set_id": reps_set, "reps": 3}]},
    )
    assert client.post("/api/account/delete/request").status_code == 200

    from app.models import Accounts

    with app.app_context():
        code = Accounts.get(logged_in).auth_code

    # Works from a device that isn't logged in.
    other_device = app.test_client()
    response = other_device.post(
        "/api/account/delete", json={"account_id": logged_in, "auth_code": code}
    )
    assert response.status_code == 200

    with app.app_context():
        for table in (
            "accounts",
            "workouts",
            "exercises",
            "sets",
            "workout_sessions",
            "set_logs",
        ):
            assert (
                db.session.execute(
                    text(f"SELECT count(*) FROM {table}")
                ).scalar()
                == 0
            )


def test_old_duplicate_logs_do_not_break_finished_session(
    app, client, logged_in
):
    """
    The old finish flow could insert every log twice (client timeout + retry).
    Reading such a session used to crash with MultipleResultsFound, so the
    finished workout never showed. It must load now.
    """
    wid, eid, reps_set, _ = build_workout(client)
    sid = client.post(f"/api/workouts/{wid}/sessions").json["workout_session"][
        "workout_session_id"
    ]
    with app.app_context():
        for reps in (7, 8):
            db.session.execute(
                text(
                    "INSERT INTO set_logs (workout_session_id, account_id, workout_id,"
                    " exercise_id, set_id, weight, duration, reps)"
                    " VALUES (:sid, :aid, :wid, :eid, :set_id, 20000, 0, :reps)"
                ),
                dict(
                    sid=sid,
                    aid=logged_in,
                    wid=wid,
                    eid=eid,
                    set_id=reps_set,
                    reps=reps,
                ),
            )
        db.session.execute(
            text(
                "UPDATE workout_sessions SET is_finished = 1,"
                " finished = datetime(started, '+30 minutes') WHERE workout_session_id = :sid"
            ),
            dict(sid=sid),
        )
        db.session.commit()

    session = client.get(f"/api/workouts/{wid}/sessions/{sid}")
    assert session.status_code == 200
    data = session.json
    assert data["workout_session"]["is_finished"] is True
    assert data["workout_session"]["duration"] == 30 * 60
    assert data["exercises"][0]["sets"][0]["set_log"]["reps"] == 8


def test_spa_routes_render(client):
    for path in (
        "/",
        "/login",
        "/workouts",
        "/workout/1/session/2",
        "/account",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        assert b'id="root"' in response.data


def test_unknown_api_route_is_json(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.json["status"] == "error"


def test_finish_with_replace_drops_logs_undone_offline(client, logged_in):
    wid, _, reps_set, timed_set = build_workout(client)
    sid = client.post(f"/api/workouts/{wid}/sessions").json["workout_session"][
        "workout_session_id"
    ]
    for set_id in (reps_set, timed_set):
        client.put(
            f"/api/workouts/{wid}/sessions/{sid}/sets/{set_id}/log",
            json={"reps": 5},
        )
    finished = client.post(
        f"/api/workouts/{wid}/sessions/{sid}/finish",
        json={"logs": [{"set_id": reps_set, "reps": 6}], "replace": True},
    ).json
    sets = finished["exercises"][0]["sets"]
    assert sets[0]["set_log"]["reps"] == 6
    assert sets[1]["set_log"] is None


def test_session_shows_previous_log_for_each_set(client, logged_in):
    wid, _, reps_set, timed_set = build_workout(client)
    base = f"/api/workouts/{wid}/sessions"

    first = client.post(base).json["workout_session"]["workout_session_id"]
    client.post(
        f"{base}/{first}/finish",
        json={"logs": [{"set_id": reps_set, "reps": 8, "weight": 40}]},
    )
    second = client.post(base).json["workout_session"]["workout_session_id"]
    client.post(
        f"{base}/{second}/finish",
        json={"logs": [{"set_id": reps_set, "reps": 10, "weight": 42.5}]},
    )

    current = client.post(base).json["workout_session"]["workout_session_id"]
    # A log in the current session must not count as "previous".
    client.put(f"{base}/{current}/sets/{reps_set}/log", json={"reps": 1})

    sets = client.get(f"{base}/{current}").json["exercises"][0]["sets"]
    previous = sets[0]["previous_log"]
    assert previous["reps"] == 10
    assert previous["weight"] == 42.5
    assert previous["workout_session_id"] == second
    assert previous["finished_display"]
    assert sets[1]["previous_log"] is None


def test_database_is_created_when_missing(tmp_path):
    from sqlalchemy import inspect

    from app import create_app

    db_file = tmp_path / "nested" / "fresh.sqlite"
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}"}
    )
    assert db_file.exists()
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())
    assert {
        "accounts",
        "workouts",
        "exercises",
        "sets",
        "workout_sessions",
        "set_logs",
    } <= tables
