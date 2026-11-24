from flask_imp import ImpBlueprint
from flask_imp.security import checkpoint

from app.api.helpers import account_id, body, fail, not_found, ok, text
from app.checkpoints import LOGIN_REQUIRED
from app.extensions import db
from app.models import Exercises, Sets, Workouts
from app.utilities.favicon import clean_url, find_favicon


def include(bp: ImpBlueprint):
    @bp.post("/workouts/<workout_id>/exercises")
    @checkpoint(LOGIN_REQUIRED)
    def add_exercise(workout_id):
        aid = account_id()
        workout = Workouts.get_owned(aid, workout_id)
        if not workout:
            return not_found("Workout")

        data = body()
        name = text(data.get("name"))
        if not name:
            return fail("Please give the exercise a name.")

        info_url = clean_url(text(data.get("info_url"), 2048))
        exercise = Exercises.create(
            account_id=aid,
            workout_id=workout.workout_id,
            name=name,
            info_url=info_url,
            info_url_favicon=find_favicon(info_url),
        )
        return ok(exercise=exercise.to_dict())

    @bp.get("/workouts/<workout_id>/exercises/<exercise_id>")
    @checkpoint(LOGIN_REQUIRED)
    def get_exercise(workout_id, exercise_id):
        aid = account_id()
        workout = Workouts.get_owned(aid, workout_id)
        exercise = Exercises.get_owned(aid, workout_id, exercise_id)
        if not workout or not exercise:
            return not_found("Exercise")

        return ok(
            workout=workout.to_dict(),
            exercise=exercise.to_dict(),
            sets=[
                s.to_dict()
                for s in Sets.list_for_exercise(aid, exercise.exercise_id)
            ],
        )

    @bp.patch("/workouts/<workout_id>/exercises/<exercise_id>")
    @checkpoint(LOGIN_REQUIRED)
    def edit_exercise(workout_id, exercise_id):
        exercise = Exercises.get_owned(account_id(), workout_id, exercise_id)
        if not exercise:
            return not_found("Exercise")

        data = body()
        name = text(data.get("name"))
        if not name:
            return fail("Please give the exercise a name.")

        info_url = clean_url(text(data.get("info_url"), 2048))
        if info_url != exercise.info_url or not exercise.info_url_favicon:
            exercise.info_url_favicon = find_favicon(info_url)

        exercise.name = name
        exercise.info_url = info_url

        db.session.commit()
        return ok(exercise=exercise.to_dict())

    @bp.delete("/workouts/<workout_id>/exercises/<exercise_id>")
    @checkpoint(LOGIN_REQUIRED)
    def delete_exercise(workout_id, exercise_id):
        exercise = Exercises.get_owned(account_id(), workout_id, exercise_id)
        if not exercise:
            return not_found("Exercise")
        exercise.delete_with_data()
        return ok(message="Exercise deleted.")
