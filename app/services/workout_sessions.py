"""Builds the JSON payload for a workout session (in progress or finished)."""

from app.models import Exercises, SetLogs, Sets, Workouts, WorkoutSessions
from app.utilities import dates


def session_payload(
    account_id: int,
    workout: Workouts,
    workout_session: WorkoutSessions,
    units: str,
) -> dict:
    exercises = Exercises.list_for_workout(account_id, workout.workout_id)
    sets = Sets.list_for_workout(account_id, workout.workout_id)
    logs = SetLogs.for_session(workout_session.workout_session_id)
    previous = SetLogs.previous_for_sets(
        account_id,
        [s.set_id for s in sets],
        exclude_session_id=workout_session.workout_session_id,
    )

    sets_by_exercise: dict[int, list[dict]] = {}
    for set_ in sets:
        data = set_.to_dict()
        log = logs.get(set_.set_id)
        data["set_log"] = log.to_dict(units) if log else None
        # What was done for this set last time, to help pick today's numbers.
        data["previous_log"] = None
        if set_.set_id in previous:
            previous_log, finished = previous[set_.set_id]
            data["previous_log"] = {
                **previous_log.to_dict(units),
                "finished": dates.iso(finished),
                "finished_display": dates.display(finished),
            }
        sets_by_exercise.setdefault(set_.exercise_id, []).append(data)

    exercise_payload = []
    for exercise in exercises:
        data = exercise.to_dict()
        data["sets"] = sets_by_exercise.get(exercise.exercise_id, [])
        exercise_payload.append(data)

    # "Total weight lifted": each logged set's weight times its reps (a timed
    # set with a weight counts once).
    total_weight = 0.0
    sets_done = 0
    for log in logs.values():
        sets_done += 1
        weight = log.to_dict(units)["weight"]
        total_weight += weight * max(log.reps or 0, 1)

    return {
        "workout": workout.to_dict(),
        "workout_session": {
            **workout_session.to_dict(),
            "total_weight": round(total_weight, 2),
            "sets_done": sets_done,
            "sets_total": len(sets),
        },
        "exercises": exercise_payload,
        "units": units,
    }
