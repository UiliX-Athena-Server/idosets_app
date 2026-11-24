from sqlalchemy import Boolean, ForeignKey, Integer, func, select, update
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Sets(db.Model):
    set_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.account_id")
    )
    workout_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("workouts.workout_id")
    )
    exercise_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("exercises.exercise_id")
    )

    is_duration: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_reps: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    duration_min: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # seconds
    duration_max: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # seconds
    reps_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reps_max: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            "set_id": self.set_id,
            "exercise_id": self.exercise_id,
            "workout_id": self.workout_id,
            "is_duration": bool(self.is_duration),
            "is_reps": bool(self.is_reps),
            "duration_min": self.duration_min or 0,
            "duration_max": self.duration_max or 0,
            "reps_min": self.reps_min or 0,
            "reps_max": self.reps_max or 0,
            "order": self.order,
        }

    @classmethod
    def get_owned(
        cls, account_id: int, workout_id, exercise_id, set_id
    ) -> "Sets | None":
        try:
            workout_id = int(workout_id)
            exercise_id = int(exercise_id)
            set_id = int(set_id)
        except (TypeError, ValueError):
            return None
        return db.session.execute(
            select(cls).where(
                cls.set_id == set_id,
                cls.exercise_id == exercise_id,
                cls.workout_id == workout_id,
                cls.account_id == account_id,
            )
        ).scalar_one_or_none()

    @classmethod
    def list_for_exercise(
        cls, account_id: int, exercise_id: int
    ) -> list["Sets"]:
        return list(
            db.session.execute(
                select(cls)
                .where(
                    cls.account_id == account_id,
                    cls.exercise_id == exercise_id,
                )
                .order_by(cls.order, cls.set_id)
            ).scalars()
        )

    @classmethod
    def list_for_workout(cls, account_id: int, workout_id: int) -> list["Sets"]:
        return list(
            db.session.execute(
                select(cls)
                .where(
                    cls.account_id == account_id,
                    cls.workout_id == workout_id,
                )
                .order_by(cls.order, cls.set_id)
            ).scalars()
        )

    @classmethod
    def counts_by_exercise(cls, account_id: int, workout_id: int) -> dict:
        rows = db.session.execute(
            select(cls.exercise_id, func.count(cls.set_id))
            .where(cls.account_id == account_id, cls.workout_id == workout_id)
            .group_by(cls.exercise_id)
        )
        return {exercise_id: count for exercise_id, count in rows}

    @classmethod
    def count_for_account(cls, account_id: int) -> int:
        return db.session.execute(
            select(func.count(cls.set_id)).where(cls.account_id == account_id)
        ).scalar_one()

    @classmethod
    def create(
        cls,
        account_id: int,
        workout_id: int,
        exercise_id: int,
        is_duration: bool,
        is_reps: bool,
        duration_min: int,
        duration_max: int,
        reps_min: int,
        reps_max: int,
    ) -> "Sets":
        cls.renumber(account_id, exercise_id)
        next_order = len(cls.list_for_exercise(account_id, exercise_id))
        new_set = cls(
            account_id=account_id,
            workout_id=workout_id,
            exercise_id=exercise_id,
            is_duration=is_duration,
            is_reps=is_reps,
            duration_min=duration_min,
            duration_max=duration_max,
            reps_min=reps_min,
            reps_max=reps_max,
            order=next_order,
        )
        db.session.add(new_set)
        db.session.commit()
        return new_set

    def duplicate(self) -> "Sets":
        """Insert a copy of this set directly after it."""
        self.renumber(self.account_id, self.exercise_id)
        db.session.execute(
            update(Sets)
            .where(
                Sets.exercise_id == self.exercise_id,
                Sets.account_id == self.account_id,
                Sets.order > self.order,
            )
            .values(order=Sets.order + 1)
        )
        copy = Sets(
            account_id=self.account_id,
            workout_id=self.workout_id,
            exercise_id=self.exercise_id,
            is_duration=self.is_duration,
            is_reps=self.is_reps,
            duration_min=self.duration_min,
            duration_max=self.duration_max,
            reps_min=self.reps_min,
            reps_max=self.reps_max,
            order=self.order + 1,
        )
        db.session.add(copy)
        db.session.commit()
        return copy

    def delete_with_logs(self) -> None:
        from .set_logs import SetLogs

        account_id, exercise_id = self.account_id, self.exercise_id
        db.session.execute(
            SetLogs.__table__.delete().where(SetLogs.set_id == self.set_id)
        )
        db.session.delete(self)
        db.session.flush()
        self.renumber(account_id, exercise_id)
        db.session.commit()

    @classmethod
    def renumber(cls, account_id: int, exercise_id: int) -> None:
        """Make ``order`` a contiguous 0..n-1 sequence (does not commit)."""
        for index, set_ in enumerate(
            cls.list_for_exercise(account_id, exercise_id)
        ):
            if set_.order != index:
                set_.order = index
        db.session.flush()
