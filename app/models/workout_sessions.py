from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utilities import dates


class WorkoutSessions(db.Model):
    workout_session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.account_id")
    )
    workout_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("workouts.workout_id")
    )

    started: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=dates.now
    )
    finished: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )
    is_finished: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    duration: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )  # seconds

    def to_dict(self) -> dict:
        return {
            "workout_session_id": self.workout_session_id,
            "workout_id": self.workout_id,
            "started": dates.iso(self.started),
            "finished": dates.iso(self.finished),
            "finished_display": dates.display(self.finished),
            "is_finished": bool(self.is_finished),
            "duration": self.elapsed_seconds(),
        }

    def elapsed_seconds(self) -> int:
        if self.is_finished:
            # Older rows can hold a wrong `duration` (timezone bug), so always
            # derive it from the timestamps when we have them.
            if self.finished is not None:
                return dates.seconds_between(self.started, self.finished)
            return self.duration or 0
        return dates.seconds_between(self.started, dates.now())

    # -- queries --------------------------------------------------------------

    @classmethod
    def get_owned(
        cls, account_id: int, workout_id, workout_session_id
    ) -> "WorkoutSessions | None":
        try:
            workout_id = int(workout_id)
            workout_session_id = int(workout_session_id)
        except (TypeError, ValueError):
            return None
        return db.session.execute(
            select(cls).where(
                cls.workout_session_id == workout_session_id,
                cls.workout_id == workout_id,
                cls.account_id == account_id,
            )
        ).scalar_one_or_none()

    @classmethod
    def active_by_workout(cls, account_id: int) -> dict[int, int]:
        """{workout_id: workout_session_id} for every unfinished session."""
        rows = db.session.execute(
            select(cls.workout_id, cls.workout_session_id)
            .where(cls.account_id == account_id, cls.is_finished.is_(False))
            .order_by(cls.started)
        )
        return {workout_id: session_id for workout_id, session_id in rows}

    @classmethod
    def last_finished(cls, account_id: int) -> "WorkoutSessions | None":
        return db.session.execute(
            select(cls)
            .where(cls.account_id == account_id, cls.is_finished.is_(True))
            .order_by(cls.finished.desc())
            .limit(1)
        ).scalar_one_or_none()

    # -- lifecycle ------------------------------------------------------------

    @classmethod
    def start(cls, account_id: int, workout_id: int) -> "WorkoutSessions":
        """Start a session, or resume the one already in progress."""
        existing = db.session.execute(
            select(cls)
            .where(
                cls.account_id == account_id,
                cls.workout_id == workout_id,
                cls.is_finished.is_(False),
            )
            .order_by(cls.started.desc())
            .limit(1)
        ).scalar_one_or_none()
        if existing:
            return existing

        session = cls(
            account_id=account_id,
            workout_id=workout_id,
            started=dates.now(),
            finished=None,
            is_finished=False,
            duration=0,
        )
        db.session.add(session)
        db.session.commit()
        return session

    def finish(self) -> None:
        """Mark the session finished. Safe to call more than once."""
        if self.is_finished:
            return
        self.finished = dates.now()
        self.duration = dates.seconds_between(self.started, self.finished)
        self.is_finished = True
        db.session.commit()

    def delete_with_logs(self) -> None:
        from .set_logs import SetLogs

        db.session.execute(
            delete(SetLogs).where(
                SetLogs.workout_session_id == self.workout_session_id
            )
        )
        db.session.delete(self)
        db.session.commit()
