from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    delete,
    func,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utilities import dates


class Workouts(db.Model):
    workout_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.account_id")
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=dates.now
    )

    def to_dict(self) -> dict:
        return {
            "workout_id": self.workout_id,
            "name": self.name,
            "created": dates.iso(self.created),
        }

    @classmethod
    def get_owned(cls, account_id: int, workout_id) -> "Workouts | None":
        try:
            workout_id = int(workout_id)
        except (TypeError, ValueError):
            return None
        return db.session.execute(
            select(cls).where(
                cls.workout_id == workout_id,
                cls.account_id == account_id,
            )
        ).scalar_one_or_none()

    @classmethod
    def list_for_account(cls, account_id: int) -> list["Workouts"]:
        return list(
            db.session.execute(
                select(cls)
                .where(cls.account_id == account_id)
                .order_by(cls.created.desc(), cls.workout_id.desc())
            ).scalars()
        )

    @classmethod
    def count_for_account(cls, account_id: int) -> int:
        return db.session.execute(
            select(func.count(cls.workout_id)).where(
                cls.account_id == account_id
            )
        ).scalar_one()

    @classmethod
    def create(cls, account_id: int, name: str) -> "Workouts":
        workout = cls(account_id=account_id, name=name, created=dates.now())
        db.session.add(workout)
        db.session.commit()
        return workout

    def rename(self, name: str) -> None:
        self.name = name
        db.session.commit()

    def delete_with_data(self) -> None:
        from .exercises import Exercises
        from .set_logs import SetLogs
        from .sets import Sets
        from .workout_sessions import WorkoutSessions

        for model in (SetLogs, WorkoutSessions, Sets, Exercises):
            db.session.execute(
                delete(model).where(model.workout_id == self.workout_id)
            )
        db.session.delete(self)
        db.session.commit()
