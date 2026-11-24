from sqlalchemy import Float, ForeignKey, Integer, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utilities.weights import from_grams


class SetLogs(db.Model):
    set_log_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    workout_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("workout_sessions.workout_session_id")
    )
    account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.account_id")
    )
    workout_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("workouts.workout_id")
    )
    exercise_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("exercises.exercise_id")
    )
    set_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sets.set_id")
    )

    weight: Mapped[float | None] = mapped_column(Float, nullable=True)  # grams
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self, units: str) -> dict:
        return {
            "set_log_id": self.set_log_id,
            "workout_session_id": self.workout_session_id,
            "exercise_id": self.exercise_id,
            "set_id": self.set_id,
            "weight": from_grams(self.weight or 0, units),
            "duration": self.duration or 0,
            "reps": self.reps or 0,
        }

    @classmethod
    def upsert(
        cls,
        account_id: int,
        workout_id: int,
        workout_session_id: int,
        exercise_id: int,
        set_id: int,
        weight_grams: float,
        reps: int,
        duration: int,
        commit: bool = True,
    ) -> "SetLogs":
        """
        Store the log for one set in one session. There is only ever one log
        per (session, set), so retrying a request can never duplicate data.
        """
        existing = list(
            db.session.execute(
                select(cls)
                .where(
                    cls.workout_session_id == workout_session_id,
                    cls.set_id == set_id,
                )
                .order_by(cls.set_log_id)
            ).scalars()
        )

        if existing:
            log = existing[-1]
            for duplicate in existing[:-1]:
                db.session.delete(duplicate)
        else:
            log = cls(
                account_id=account_id,
                workout_id=workout_id,
                workout_session_id=workout_session_id,
                exercise_id=exercise_id,
                set_id=set_id,
            )
            db.session.add(log)

        log.weight = weight_grams
        log.reps = reps
        log.duration = duration

        if commit:
            db.session.commit()
        return log

    @classmethod
    def remove(cls, workout_session_id: int, set_id: int) -> None:
        db.session.execute(
            delete(cls).where(
                cls.workout_session_id == workout_session_id,
                cls.set_id == set_id,
            )
        )
        db.session.commit()

    @classmethod
    def remove_except(cls, workout_session_id: int, set_ids: set[int]) -> None:
        """Delete this session's logs for any set not in ``set_ids``."""
        db.session.execute(
            delete(cls).where(
                cls.workout_session_id == workout_session_id,
                cls.set_id.not_in(set_ids),
            )
        )

    @classmethod
    def for_session(cls, workout_session_id: int) -> dict[int, "SetLogs"]:
        """{set_id: log}. If old data has duplicates, the newest one wins."""
        logs = db.session.execute(
            select(cls)
            .where(cls.workout_session_id == workout_session_id)
            .order_by(cls.set_log_id)
        ).scalars()
        return {log.set_id: log for log in logs}

    @classmethod
    def previous_for_sets(
        cls, account_id: int, set_ids: list[int], exclude_session_id: int
    ) -> dict[int, tuple["SetLogs", object]]:
        """
        For each set, the log from the most recent *finished* session other
        than ``exclude_session_id``: {set_id: (log, session_finished_at)}.
        """
        from .workout_sessions import WorkoutSessions

        if not set_ids:
            return {}
        rows = db.session.execute(
            select(cls, WorkoutSessions.finished)
            .join(
                WorkoutSessions,
                WorkoutSessions.workout_session_id == cls.workout_session_id,
            )
            .where(
                cls.account_id == account_id,
                cls.set_id.in_(set_ids),
                WorkoutSessions.is_finished.is_(True),
                WorkoutSessions.workout_session_id != exclude_session_id,
            )
            .order_by(WorkoutSessions.finished.desc(), cls.set_log_id.desc())
        )
        previous: dict[int, tuple[SetLogs, object]] = {}
        for log, finished in rows:
            previous.setdefault(log.set_id, (log, finished))
        return previous

    @classmethod
    def recent_for_exercise(
        cls, account_id: int, exercise_id: int, limit: int
    ) -> list["SetLogs"]:
        """The newest ``limit`` logs, returned oldest first (for charts)."""
        logs = list(
            db.session.execute(
                select(cls)
                .where(
                    cls.account_id == account_id,
                    cls.exercise_id == exercise_id,
                )
                .order_by(cls.set_log_id.desc())
                .limit(limit)
            ).scalars()
        )
        logs.reverse()
        return logs

    @classmethod
    def count_for_session(cls, workout_session_id: int) -> int:
        return db.session.execute(
            select(func.count(cls.set_log_id)).where(
                cls.workout_session_id == workout_session_id
            )
        ).scalar_one()
