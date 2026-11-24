from flask_imp import ImpBlueprint
from flask_imp.security import checkpoint

from app.api.helpers import (
    account_id,
    body,
    fail,
    not_found,
    ok,
    whole_number,
)
from app.checkpoints import LOGIN_REQUIRED
from app.models import Exercises, Sets

ONE_DAY = 60 * 60 * 24


def include(bp: ImpBlueprint):
    @bp.post("/workouts/<workout_id>/exercises/<exercise_id>/sets")
    @checkpoint(LOGIN_REQUIRED)
    def add_set(workout_id, exercise_id):
        aid = account_id()
        exercise = Exercises.get_owned(aid, workout_id, exercise_id)
        if not exercise:
            return not_found("Exercise")

        data = body()
        set_type = data.get("type")
        if set_type not in ("reps", "duration"):
            return fail("A set must be either reps or duration.")

        is_reps = set_type == "reps"
        reps_min = whole_number(data.get("reps_min")) if is_reps else 0
        reps_max = whole_number(data.get("reps_max")) if is_reps else 0
        duration_min = (
            0 if is_reps else whole_number(data.get("duration_min"), ONE_DAY)
        )
        duration_max = (
            0 if is_reps else whole_number(data.get("duration_max"), ONE_DAY)
        )

        # Accept the range either way round.
        if reps_min and reps_max and reps_min > reps_max:
            reps_min, reps_max = reps_max, reps_min
        if duration_min and duration_max and duration_min > duration_max:
            duration_min, duration_max = duration_max, duration_min

        new_set = Sets.create(
            account_id=aid,
            workout_id=exercise.workout_id,
            exercise_id=exercise.exercise_id,
            is_duration=not is_reps,
            is_reps=is_reps,
            duration_min=duration_min,
            duration_max=duration_max,
            reps_min=reps_min,
            reps_max=reps_max,
        )
        return ok(set=new_set.to_dict())

    @bp.post(
        "/workouts/<workout_id>/exercises/<exercise_id>/sets/<set_id>/copy"
    )
    @checkpoint(LOGIN_REQUIRED)
    def copy_set(workout_id, exercise_id, set_id):
        source = Sets.get_owned(account_id(), workout_id, exercise_id, set_id)
        if not source:
            return not_found("Set")
        copy = source.duplicate()
        return ok(set=copy.to_dict(), after_set_id=source.set_id)

    @bp.delete("/workouts/<workout_id>/exercises/<exercise_id>/sets/<set_id>")
    @checkpoint(LOGIN_REQUIRED)
    def delete_set(workout_id, exercise_id, set_id):
        target = Sets.get_owned(account_id(), workout_id, exercise_id, set_id)
        if not target:
            return not_found("Set")
        target.delete_with_logs()
        return ok(message="Set deleted.")
