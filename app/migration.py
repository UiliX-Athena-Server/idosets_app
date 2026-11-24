"""
Copy the data from the old database file into a new database built from the
current models.

The old database is opened read-only and is never changed, so the migration
can be re-run (into a fresh file) as often as needed. Primary keys are kept,
so login links, bookmarks and session URLs keep working.

While copying, problems left behind by the old code are cleaned up:

- duplicate logs for one set in one session (from the "finish twice" bug):
  only the newest is kept
- rows that point at deleted parents (e.g. logs of deleted sets, data of
  deleted accounts) are dropped
- exercise and set ``order`` values are renumbered without gaps
- account settings are normalised to a valid theme and unit
- stored session durations are recalculated from the start/finish times
"""

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, insert, select

from app.extensions import db
from app.models import (
    Accounts,
    Exercises,
    SetLogs,
    Sets,
    Workouts,
    WorkoutSessions,
)
from app.models.accounts import normalise_theme
from app.utilities.weights import normalise_unit

TABLES = (Accounts, Workouts, Exercises, Sets, WorkoutSessions, SetLogs)


class MigrationError(Exception):
    pass


@dataclass
class MigrationReport:
    copied: Counter = field(default_factory=Counter)
    skipped: Counter = field(default_factory=Counter)
    notes: list[str] = field(default_factory=list)

    def skip(self, table: str, reason: str, count: int = 1) -> None:
        self.skipped[f"{table}: {reason}"] += count

    def lines(self) -> list[str]:
        lines = ["Copied:"]
        for model in TABLES:
            name = model.__tablename__
            lines.append(f"  {name:<18} {self.copied[name]}")
        if self.skipped:
            lines.append("Cleaned up (not copied):")
            for reason, count in sorted(self.skipped.items()):
                lines.append(f"  {reason}: {count}")
        lines.extend(self.notes)
        return lines


# -- reading the old database --------------------------------------------------


def _read_table(conn: sqlite3.Connection, table: str) -> list[dict]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    if not exists:
        return []
    return [dict(row) for row in conn.execute(f'SELECT * FROM "{table}"')]


def _datetime(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    # Old rows were written as Europe/London wall-clock time; keep it naive.
    return parsed.replace(tzinfo=None, microsecond=0)


def _int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "t", "yes")
    return bool(value)


def _settings(value) -> dict:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            value = {}
    if not isinstance(value, dict):
        value = {}
    return {
        **value,
        "theme": normalise_theme(value.get("theme")),
        "units": normalise_unit(value.get("units")),
    }


# -- the migration ---------------------------------------------------------------


def target_is_empty() -> bool:
    return all(
        db.session.execute(select(func.count()).select_from(model)).scalar_one()
        == 0
        for model in TABLES
    )


def migrate(old_database: Path) -> MigrationReport:
    """
    Copy ``old_database`` into the database the app is configured with.
    Must be called inside an app context. The target must be empty.
    """
    old_database = Path(old_database).resolve()
    if not old_database.exists():
        raise MigrationError(f"Old database not found: {old_database}")

    db.create_all()
    if not target_is_empty():
        raise MigrationError(
            "The new database already has data in it. Delete it (or point "
            "the app at another file) and run the migration again."
        )

    conn = sqlite3.connect(f"file:{old_database}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        old = {
            model.__tablename__: _read_table(conn, model.__tablename__)
            for model in TABLES
        }
    finally:
        conn.close()

    report = MigrationReport()

    # Accounts --------------------------------------------------------------
    accounts = []
    for row in old["accounts"]:
        if not row.get("email_address"):
            report.skip("accounts", "no email address")
            continue
        accounts.append(
            {
                "account_id": row["account_id"],
                "email_address": row["email_address"].strip(),
                "settings": _settings(row.get("settings")),
                "auth_code": row.get("auth_code"),
                "auth_code_expiry": _datetime(row.get("auth_code_expiry")),
                "created": _datetime(row.get("created"))
                or datetime.now().replace(microsecond=0),
            }
        )
    account_ids = {a["account_id"] for a in accounts}

    # Workouts --------------------------------------------------------------
    workouts = []
    for row in old["workouts"]:
        if row.get("account_id") not in account_ids:
            report.skip("workouts", "account no longer exists")
            continue
        workouts.append(
            {
                "workout_id": row["workout_id"],
                "account_id": row["account_id"],
                "name": (row.get("name") or "Workout").strip()[:255]
                or "Workout",
                "created": _datetime(row.get("created"))
                or datetime.now().replace(microsecond=0),
            }
        )
    workout_owner = {w["workout_id"]: w["account_id"] for w in workouts}

    # Exercises (renumber order per workout) --------------------------------
    exercises = []
    for row in sorted(
        old["exercises"],
        key=lambda r: (
            _int(r.get("workout_id")),
            _int(r.get("order")),
            r["exercise_id"],
        ),
    ):
        if workout_owner.get(row.get("workout_id")) != row.get("account_id"):
            report.skip("exercises", "workout no longer exists")
            continue
        exercises.append(
            {
                "exercise_id": row["exercise_id"],
                "account_id": row["account_id"],
                "workout_id": row["workout_id"],
                "name": (row.get("name") or "Exercise").strip()[:255]
                or "Exercise",
                "info_url": row.get("info_url") or None,
                "info_url_favicon": row.get("info_url_favicon") or None,
            }
        )
    positions: Counter = Counter()
    for exercise in exercises:
        positions[exercise["workout_id"]] += 1
        exercise["order"] = positions[exercise["workout_id"]]
    exercise_parent = {
        e["exercise_id"]: (e["workout_id"], e["account_id"]) for e in exercises
    }

    # Sets (renumber order per exercise) -------------------------------------
    sets = []
    for row in sorted(
        old["sets"],
        key=lambda r: (
            _int(r.get("exercise_id")),
            _int(r.get("order")),
            r["set_id"],
        ),
    ):
        parent = exercise_parent.get(row.get("exercise_id"))
        if parent is None or parent[1] != row.get("account_id"):
            report.skip("sets", "exercise no longer exists")
            continue
        is_duration = _bool(row.get("is_duration"))
        sets.append(
            {
                "set_id": row["set_id"],
                "account_id": row["account_id"],
                "workout_id": parent[0],
                "exercise_id": row["exercise_id"],
                "is_duration": is_duration,
                # A set is either timed or counted in reps.
                "is_reps": not is_duration,
                "duration_min": max(0, _int(row.get("duration_min"))),
                "duration_max": max(0, _int(row.get("duration_max"))),
                "reps_min": max(0, _int(row.get("reps_min"))),
                "reps_max": max(0, _int(row.get("reps_max"))),
            }
        )
    positions = Counter()
    for set_ in sets:
        set_["order"] = positions[set_["exercise_id"]]
        positions[set_["exercise_id"]] += 1
    set_parent = {
        s["set_id"]: (s["exercise_id"], s["workout_id"], s["account_id"])
        for s in sets
    }

    # Workout sessions --------------------------------------------------------
    sessions = []
    for row in old["workout_sessions"]:
        if workout_owner.get(row.get("workout_id")) != row.get("account_id"):
            report.skip("workout_sessions", "workout no longer exists")
            continue
        started = _datetime(row.get("started"))
        if started is None:
            report.skip("workout_sessions", "no start time")
            continue
        finished = _datetime(row.get("finished"))
        is_finished = _bool(row.get("is_finished")) and finished is not None
        sessions.append(
            {
                "workout_session_id": row["workout_session_id"],
                "account_id": row["account_id"],
                "workout_id": row["workout_id"],
                "started": started,
                "finished": finished if is_finished else None,
                "is_finished": is_finished,
                "duration": (
                    max(0, int((finished - started).total_seconds()))
                    if is_finished
                    else 0
                ),
            }
        )
    session_workout = {
        s["workout_session_id"]: s["workout_id"] for s in sessions
    }

    # Set logs (one per session + set, newest wins) ---------------------------
    newest: dict[tuple[int, int], dict] = {}
    for row in sorted(old["set_logs"], key=lambda r: r["set_log_id"]):
        parent = set_parent.get(row.get("set_id"))
        session_id = row.get("workout_session_id")
        if parent is None:
            report.skip("set_logs", "set no longer exists")
            continue
        if session_workout.get(session_id) != parent[1]:
            report.skip("set_logs", "session no longer exists")
            continue
        key = (session_id, row["set_id"])
        if key in newest:
            report.skip(
                "set_logs", "duplicate log for the same set and session"
            )
        newest[key] = {
            "set_log_id": row["set_log_id"],
            "workout_session_id": session_id,
            "account_id": parent[2],
            "workout_id": parent[1],
            "exercise_id": parent[0],
            "set_id": row["set_id"],
            "weight": max(0.0, _float(row.get("weight"))),
            "duration": max(0, _int(row.get("duration"))),
            "reps": max(0, _int(row.get("reps"))),
        }
    set_logs = sorted(newest.values(), key=lambda r: r["set_log_id"])

    # Write everything in one transaction -------------------------------------
    rows_by_model = {
        Accounts: accounts,
        Workouts: workouts,
        Exercises: exercises,
        Sets: sets,
        WorkoutSessions: sessions,
        SetLogs: set_logs,
    }
    try:
        for model, rows in rows_by_model.items():
            if rows:
                db.session.execute(insert(model), rows)
            report.copied[model.__tablename__] = len(rows)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    emails = Counter(a["email_address"].lower() for a in accounts)
    duplicates = [email for email, count in emails.items() if count > 1]
    if duplicates:
        report.notes.append(
            f"Note: {len(duplicates)} email address(es) have more than one "
            "account; they were copied as-is. Login uses the oldest one."
        )
    return report
