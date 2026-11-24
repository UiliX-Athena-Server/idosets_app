from flask import request
from flask_imp import ImpBlueprint
from flask_imp.security import checkpoint

from app.api.helpers import account_id, body, fail, not_found, ok, text, units
from app.checkpoints import LOGIN_REQUIRED
from app.models import Exercises, SetLogs, Sets, Workouts, WorkoutSessions
from app.utilities import dates


def include(bp: ImpBlueprint):
    @bp.get("/workouts")
    @checkpoint(LOGIN_REQUIRED)
    def list_workouts():
        aid = account_id()
        exercise_counts = Exercises.counts_by_workout(aid)
        active = WorkoutSessions.active_by_workout(aid)

        workouts = [
            {
                **workout.to_dict(),
                "exercise_count": exercise_counts.get(workout.workout_id, 0),
                "active_session_id": active.get(workout.workout_id),
            }
            for workout in Workouts.list_for_account(aid)
        ]

        last_session = None
        last = WorkoutSessions.last_finished(aid)
        if last:
            last_workout = Workouts.get_owned(aid, last.workout_id)
            if last_workout:
                last_session = {
                    "workout_id": last_workout.workout_id,
                    "workout_session_id": last.workout_session_id,
                    "name": last_workout.name,
                    "finished": dates.display(last.finished),
                }

        return ok(workouts=workouts, last_session=last_session)

    @bp.post("/workouts")
    @checkpoint(LOGIN_REQUIRED)
    def add_workout():
        name = text(body().get("name"))
        if not name:
            return fail("Please give the workout a name.")
        workout = Workouts.create(account_id(), name)
        return ok(workout=workout.to_dict())

    @bp.get("/workouts/<workout_id>")
    @checkpoint(LOGIN_REQUIRED)
    def get_workout(workout_id):
        aid = account_id()
        workout = Workouts.get_owned(aid, workout_id)
        if not workout:
            return not_found("Workout")

        set_counts = Sets.counts_by_exercise(aid, workout.workout_id)
        exercises = [
            {
                **exercise.to_dict(),
                "set_count": set_counts.get(exercise.exercise_id, 0),
            }
            for exercise in Exercises.list_for_workout(aid, workout.workout_id)
        ]
        active = WorkoutSessions.active_by_workout(aid)
        return ok(
            workout={
                **workout.to_dict(),
                "active_session_id": active.get(workout.workout_id),
            },
            exercises=exercises,
        )

    @bp.patch("/workouts/<workout_id>")
    @checkpoint(LOGIN_REQUIRED)
    def edit_workout(workout_id):
        workout = Workouts.get_owned(account_id(), workout_id)
        if not workout:
            return not_found("Workout")
        name = text(body().get("name"))
        if not name:
            return fail("Please give the workout a name.")
        workout.rename(name)
        return ok(workout=workout.to_dict())

    @bp.delete("/workouts/<workout_id>")
    @checkpoint(LOGIN_REQUIRED)
    def delete_workout(workout_id):
        workout = Workouts.get_owned(account_id(), workout_id)
        if not workout:
            return not_found("Workout")
        workout.delete_with_data()
        return ok(message="Workout deleted.")

    @bp.get("/workouts/<workout_id>/logs")
    @checkpoint(LOGIN_REQUIRED)
    def workout_logs(workout_id):
        aid = account_id()
        workout = Workouts.get_owned(aid, workout_id)
        if not workout:
            return not_found("Workout")

        limit = request.args.get("limit", default=30, type=int)
        limit = max(1, min(limit, 500))
        unit = units()

        exercises = [
            {
                **exercise.to_dict(),
                "logs": [
                    log.to_dict(unit)
                    for log in SetLogs.recent_for_exercise(
                        aid, exercise.exercise_id, limit
                    )
                ],
            }
            for exercise in Exercises.list_for_workout(aid, workout.workout_id)
        ]
        return ok(workout=workout.to_dict(), exercises=exercises, units=unit)
