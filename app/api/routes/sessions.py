from flask_imp import ImpBlueprint
from flask_imp.security import checkpoint

from app.api.helpers import (
    account_id,
    body,
    fail,
    not_found,
    ok,
    units,
    whole_number,
)
from app.checkpoints import LOGIN_REQUIRED
from app.extensions import db
from app.models import SetLogs, Sets, Workouts, WorkoutSessions
from app.services.workout_sessions import session_payload
from app.utilities.weights import to_grams, to_number

ONE_DAY = 60 * 60 * 24
MAX_WEIGHT = 10_000  # in the user's unit; anything above is a typo


def _log_values(data: dict, unit: str) -> dict:
    weight = min(to_number(data.get("weight")), MAX_WEIGHT)
    return {
        "weight_grams": to_grams(weight, unit),
        "reps": whole_number(data.get("reps"), 10_000),
        "duration": whole_number(data.get("duration"), ONE_DAY),
    }


def _load(workout_id, workout_session_id):
    aid = account_id()
    workout = Workouts.get_owned(aid, workout_id)
    workout_session = WorkoutSessions.get_owned(
        aid, workout_id, workout_session_id
    )
    if not workout or not workout_session:
        return None, None
    return workout, workout_session


def include(bp: ImpBlueprint):
    @bp.post("/workouts/<workout_id>/sessions")
    @checkpoint(LOGIN_REQUIRED)
    def start_session(workout_id):
        aid = account_id()
        workout = Workouts.get_owned(aid, workout_id)
        if not workout:
            return not_found("Workout")
        workout_session = WorkoutSessions.start(aid, workout.workout_id)
        return ok(workout_session=workout_session.to_dict())

    @bp.get("/workouts/<workout_id>/sessions/<workout_session_id>")
    @checkpoint(LOGIN_REQUIRED)
    def get_session(workout_id, workout_session_id):
        workout, workout_session = _load(workout_id, workout_session_id)
        if not workout:
            return not_found("Workout session")
        return ok(
            **session_payload(account_id(), workout, workout_session, units())
        )

    @bp.put(
        "/workouts/<workout_id>/sessions/<workout_session_id>/sets/<set_id>/log"
    )
    @checkpoint(LOGIN_REQUIRED)
    def log_set(workout_id, workout_session_id, set_id):
        workout, workout_session = _load(workout_id, workout_session_id)
        if not workout:
            return not_found("Workout session")
        if workout_session.is_finished:
            return fail("This workout has already been finished.", 409)

        set_ = db.session.get(Sets, int(set_id)) if set_id.isdigit() else None
        if not set_ or set_.workout_id != workout.workout_id:
            return not_found("Set")

        unit = units()
        log = SetLogs.upsert(
            account_id=account_id(),
            workout_id=workout.workout_id,
            workout_session_id=workout_session.workout_session_id,
            exercise_id=set_.exercise_id,
            set_id=set_.set_id,
            **_log_values(body(), unit),
        )
        return ok(set_log=log.to_dict(unit))

    @bp.delete(
        "/workouts/<workout_id>/sessions/<workout_session_id>/sets/<set_id>/log"
    )
    @checkpoint(LOGIN_REQUIRED)
    def undo_set(workout_id, workout_session_id, set_id):
        workout, workout_session = _load(workout_id, workout_session_id)
        if not workout:
            return not_found("Workout session")
        if workout_session.is_finished:
            return fail("This workout has already been finished.", 409)
        if not set_id.isdigit():
            return not_found("Set")
        SetLogs.remove(workout_session.workout_session_id, int(set_id))
        return ok(message="Set log removed.")

    @bp.post("/workouts/<workout_id>/sessions/<workout_session_id>/finish")
    @checkpoint(LOGIN_REQUIRED)
    def finish_session(workout_id, workout_session_id):
        """
        Saves any logs the client still holds (e.g. made while offline) and
        finishes the session. Idempotent: calling it again after a timeout
        or a double tap just returns the finished summary.
        """
        aid = account_id()
        workout, workout_session = _load(workout_id, workout_session_id)
        if not workout:
            return not_found("Workout session")

        unit = units()

        if not workout_session.is_finished:
            workout_sets = {
                s.set_id: s
                for s in Sets.list_for_workout(aid, workout.workout_id)
            }
            data = body()
            logs = data.get("logs") or []
            if not isinstance(logs, list):
                logs = []
            # With "replace", the client's list is the complete record of
            # the session: logs for sets missing from it (undone while
            # offline) are removed.
            kept_set_ids = set()

            for item in logs:
                if not isinstance(item, dict):
                    continue
                try:
                    set_ = workout_sets.get(int(item.get("set_id")))
                except (TypeError, ValueError):
                    continue
                if not set_:
                    continue
                SetLogs.upsert(
                    account_id=aid,
                    workout_id=workout.workout_id,
                    workout_session_id=workout_session.workout_session_id,
                    exercise_id=set_.exercise_id,
                    set_id=set_.set_id,
                    commit=False,
                    **_log_values(item, unit),
                )
                kept_set_ids.add(set_.set_id)

            if data.get("replace") is True:
                SetLogs.remove_except(
                    workout_session.workout_session_id, kept_set_ids
                )

            workout_session.finish()  # commits the logs too

        return ok(**session_payload(aid, workout, workout_session, unit))

    @bp.delete("/workouts/<workout_id>/sessions/<workout_session_id>")
    @checkpoint(LOGIN_REQUIRED)
    def cancel_session(workout_id, workout_session_id):
        workout, workout_session = _load(workout_id, workout_session_id)
        if not workout:
            # Already gone, which is what the caller wanted.
            return ok(message="Workout session cancelled.")
        workout_session.delete_with_logs()
        return ok(message="Workout session cancelled.")
