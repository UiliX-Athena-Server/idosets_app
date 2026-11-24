from sqlalchemy import ForeignKey, Integer, String, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Exercises(db.Model):
    exercise_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.account_id")
    )
    workout_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("workouts.workout_id")
    )

    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    info_url: Mapped[str | None] = mapped_column(String, nullable=True)
    info_url_favicon: Mapped[str | None] = mapped_column(String, nullable=True)

    def to_dict(self) -> dict:
        return {
            "exercise_id": self.exercise_id,
            "workout_id": self.workout_id,
            "order": self.order,
            "name": self.name,
            "info_url": self.info_url,
            "info_url_favicon": self.info_url_favicon,
        }

    @classmethod
    def get_owned(
        cls, account_id: int, workout_id, exercise_id
    ) -> "Exercises | None":
        try:
            workout_id = int(workout_id)
            exercise_id = int(exercise_id)
        except (TypeError, ValueError):
            return None
        return db.session.execute(
            select(cls).where(
                cls.exercise_id == exercise_id,
                cls.workout_id == workout_id,
                cls.account_id == account_id,
            )
        ).scalar_one_or_none()

    @classmethod
    def list_for_workout(
        cls, account_id: int, workout_id: int
    ) -> list["Exercises"]:
        return list(
            db.session.execute(
                select(cls)
                .where(
                    cls.account_id == account_id,
                    cls.workout_id == workout_id,
                )
                .order_by(cls.order, cls.exercise_id)
            ).scalars()
        )

    @classmethod
    def counts_by_workout(cls, account_id: int) -> dict[int, int]:
        rows = db.session.execute(
            select(cls.workout_id, func.count(cls.exercise_id))
            .where(cls.account_id == account_id)
            .group_by(cls.workout_id)
        )
        return {workout_id: count for workout_id, count in rows}

    @classmethod
    def count_for_account(cls, account_id: int) -> int:
        return db.session.execute(
            select(func.count(cls.exercise_id)).where(
                cls.account_id == account_id
            )
        ).scalar_one()

    @classmethod
    def create(
        cls,
        account_id: int,
        workout_id: int,
        name: str,
        info_url: str | None,
        info_url_favicon: str | None,
    ) -> "Exercises":
        next_order = (
            db.session.execute(
                select(func.max(cls.order)).where(cls.workout_id == workout_id)
            ).scalar()
            or 0
        ) + 1
        exercise = cls(
            account_id=account_id,
            workout_id=workout_id,
            order=next_order,
            name=name,
            info_url=info_url,
            info_url_favicon=info_url_favicon,
        )
        db.session.add(exercise)
        db.session.commit()
        return exercise

    def delete_with_data(self) -> None:
        from .set_logs import SetLogs
        from .sets import Sets

        for model in (SetLogs, Sets):
            db.session.execute(
                delete(model).where(model.exercise_id == self.exercise_id)
            )
        db.session.delete(self)
        db.session.commit()
