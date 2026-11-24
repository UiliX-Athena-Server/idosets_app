import json
import sqlite3

import pytest
from sqlalchemy import select

from app.extensions import db
from app.migration import MigrationError, migrate
from app.models import Accounts, Exercises, SetLogs, Sets, WorkoutSessions

# The tables as the pre-2.0 code (Column(...) style models) created them.
OLD_SCHEMA = """
CREATE TABLE accounts (
    account_id INTEGER NOT NULL PRIMARY KEY,
    email_address VARCHAR(255) NOT NULL,
    settings JSON,
    auth_code VARCHAR(512),
    auth_code_expiry DATETIME,
    created DATETIME NOT NULL
);
CREATE TABLE workouts (
    workout_id INTEGER NOT NULL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts (account_id),
    name VARCHAR(255) NOT NULL,
    created DATETIME NOT NULL
);
CREATE TABLE exercises (
    exercise_id INTEGER NOT NULL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts (account_id),
    workout_id INTEGER REFERENCES workouts (workout_id),
    "order" INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    info_url VARCHAR,
    info_url_favicon VARCHAR
);
CREATE TABLE sets (
    set_id INTEGER NOT NULL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts (account_id),
    workout_id INTEGER REFERENCES workouts (workout_id),
    exercise_id INTEGER REFERENCES exercises (exercise_id),
    is_duration BOOLEAN NOT NULL,
    is_reps BOOLEAN NOT NULL,
    duration_min INTEGER NOT NULL,
    duration_max INTEGER NOT NULL,
    reps_min INTEGER NOT NULL,
    reps_max INTEGER NOT NULL,
    "order" INTEGER NOT NULL
);
CREATE TABLE workout_sessions (
    workout_session_id INTEGER NOT NULL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts (account_id),
    workout_id INTEGER REFERENCES workouts (workout_id),
    started DATETIME NOT NULL,
    finished DATETIME,
    is_finished BOOLEAN NOT NULL,
    duration INTEGER
);
CREATE TABLE set_logs (
    set_log_id INTEGER NOT NULL PRIMARY KEY,
    workout_session_id INTEGER REFERENCES workout_sessions (workout_session_id),
    account_id INTEGER REFERENCES accounts (account_id),
    workout_id INTEGER REFERENCES workouts (workout_id),
    exercise_id INTEGER REFERENCES exercises (exercise_id),
    set_id INTEGER REFERENCES sets (set_id),
    weight FLOAT,
    duration INTEGER,
    reps INTEGER
);
"""


@pytest.fixture
def old_db(tmp_path):
    path = tmp_path / "database.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    q = conn.execute

    # Account 1 is real. Account 2 was "deleted" by the old code, which only
    # removed the account, workouts, exercises and sets - not sessions/logs.
    q(
        "INSERT INTO accounts VALUES (1, 'lifter@example.com', ?, 'code', "
        "'2099-01-01 00:00:00.000000', '2024-01-02 10:00:00.123456')",
        (json.dumps({"theme": "purple"}),),
    )

    q(
        "INSERT INTO workouts VALUES (10, 1, 'Push', '2024-01-02 10:00:00.000000')"
    )
    q(
        "INSERT INTO workouts VALUES (11, 2, 'Orphan', '2024-01-02 10:00:00.000000')"
    )

    # Exercise order with gaps.
    q(
        "INSERT INTO exercises VALUES (20, 1, 10, 5, 'Bench', 'https://x.test', NULL)"
    )
    q("INSERT INTO exercises VALUES (21, 1, 10, 9, 'Dips', NULL, NULL)")

    # Set order with gaps; set 32 belongs to a deleted exercise.
    q("INSERT INTO sets VALUES (30, 1, 10, 20, 0, 1, 0, 0, 8, 12, 4)")
    q("INSERT INTO sets VALUES (31, 1, 10, 20, 1, 0, 30, 60, 0, 0, 7)")
    q("INSERT INTO sets VALUES (32, 1, 10, 99, 0, 1, 0, 0, 5, 5, 0)")

    # A finished session whose stored duration is wrong (summer time bug),
    # and an unfinished one.
    q(
        "INSERT INTO workout_sessions VALUES (40, 1, 10, '2024-06-01 09:00:00.000000',"
        " '2024-06-01 09:45:00.000000', 1, 83700)"
    )
    q(
        "INSERT INTO workout_sessions VALUES (41, 1, 10, '2024-06-02 09:00:00.000000',"
        " NULL, 0, 0)"
    )
    q(
        "INSERT INTO workout_sessions VALUES (42, 2, 11, '2024-06-02 09:00:00.000000',"
        " NULL, 0, 0)"
    )

    # Duplicate logs for set 30 in session 40 (the "finish twice" bug).
    q("INSERT INTO set_logs VALUES (50, 40, 1, 10, 20, 30, 60000, 0, 8)")
    q("INSERT INTO set_logs VALUES (51, 40, 1, 10, 20, 30, 62500, 0, 10)")
    q("INSERT INTO set_logs VALUES (52, 40, 1, 10, 20, 31, 0, 45, 0)")
    q(
        "INSERT INTO set_logs VALUES (53, 40, 1, 10, 99, 32, 0, 0, 5)"
    )  # dead set
    q(
        "INSERT INTO set_logs VALUES (54, 42, 2, 11, 99, 33, 0, 0, 5)"
    )  # dead account
    conn.commit()
    conn.close()
    return path


def test_migrates_and_cleans_old_database(app, old_db):
    before = old_db.read_bytes()

    with app.app_context():
        report = migrate(old_db)

        assert report.copied["accounts"] == 1
        assert report.copied["workouts"] == 1
        assert report.copied["exercises"] == 2
        assert report.copied["sets"] == 2
        assert report.copied["workout_sessions"] == 2
        assert report.copied["set_logs"] == 2

        account = db.session.get(Accounts, 1)
        assert account.settings == {"theme": "dark", "units": "kgs"}
        assert account.auth_code == "code"  # existing login links still work

        orders = db.session.execute(
            select(Exercises.exercise_id, Exercises.order).order_by(
                Exercises.order
            )
        ).all()
        assert orders == [(20, 1), (21, 2)]

        sets = (
            db.session.execute(select(Sets).order_by(Sets.order))
            .scalars()
            .all()
        )
        assert [(s.set_id, s.order) for s in sets] == [(30, 0), (31, 1)]
        assert sets[0].is_reps and not sets[0].is_duration
        assert sets[1].is_duration and not sets[1].is_reps

        finished = db.session.get(WorkoutSessions, 40)
        assert finished.is_finished and finished.duration == 45 * 60
        assert not db.session.get(WorkoutSessions, 41).is_finished

        logs = (
            db.session.execute(select(SetLogs).order_by(SetLogs.set_id))
            .scalars()
            .all()
        )
        assert [(log.set_log_id, log.reps) for log in logs] == [
            (51, 10),
            (52, 0),
        ]

    assert (
        report.skipped["set_logs: duplicate log for the same set and session"]
        == 1
    )
    assert report.skipped["workouts: account no longer exists"] == 1
    assert old_db.read_bytes() == before  # the old database is untouched


def test_migrated_data_works_in_the_api(app, client, old_db):
    with app.app_context():
        migrate(old_db)

    client.post("/api/auth", json={"account_id": 1, "auth_code": "code"})
    session = client.get("/api/workouts/10/sessions/40").json
    assert session["workout_session"]["duration"] == 45 * 60
    assert session["exercises"][0]["sets"][0]["set_log"]["weight"] == 62.5


def test_refuses_to_migrate_into_a_database_with_data(app, old_db):
    with app.app_context():
        migrate(old_db)
        with pytest.raises(MigrationError):
            migrate(old_db)


def test_missing_old_database(app, tmp_path):
    with app.app_context(), pytest.raises(MigrationError):
        migrate(tmp_path / "nope.sqlite")


def test_cli_command(app, old_db):
    result = app.test_cli_runner().invoke(
        args=["migrate-db", "--old", str(old_db)]
    )
    assert result.exit_code == 0, result.output
    assert "set_logs" in result.output
    assert "Done." in result.output
