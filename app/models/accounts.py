from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utilities import dates
from app.utilities.weights import normalise_unit

THEMES = ("dark", "light")
DEFAULT_SETTINGS = {"theme": "dark", "units": "kgs"}


def normalise_theme(theme: str | None) -> str:
    return theme if theme in THEMES else "dark"


class Accounts(db.Model):
    account_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    settings: Mapped[dict | None] = mapped_column(
        JSON, default=lambda: dict(DEFAULT_SETTINGS)
    )
    auth_code: Mapped[str | None] = mapped_column(String(512), nullable=True)
    auth_code_expiry: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=dates.now
    )

    # -- settings -------------------------------------------------------------

    @property
    def theme(self) -> str:
        return normalise_theme((self.settings or {}).get("theme"))

    @property
    def units(self) -> str:
        return normalise_unit((self.settings or {}).get("units"))

    def update_settings(
        self, theme: str | None = None, units: str | None = None
    ) -> None:
        settings = dict(self.settings or DEFAULT_SETTINGS)
        if theme is not None:
            settings["theme"] = normalise_theme(theme)
        if units is not None:
            settings["units"] = normalise_unit(units)
        # Reassign so SQLAlchemy notices the JSON column changed.
        self.settings = settings
        db.session.commit()

    # -- auth -----------------------------------------------------------------

    def set_auth_code(self, auth_code: str, expiry: datetime) -> None:
        self.auth_code = auth_code
        self.auth_code_expiry = expiry
        db.session.commit()

    def auth_code_is_valid(self, auth_code: str | None) -> bool:
        if not auth_code or not self.auth_code:
            return False
        if self.auth_code != auth_code:
            return False
        if self.auth_code_expiry is None:
            return False
        return dates.now() < self.auth_code_expiry

    # -- queries --------------------------------------------------------------

    @classmethod
    def get(cls, account_id) -> "Accounts | None":
        try:
            account_id = int(account_id)
        except (TypeError, ValueError):
            return None
        return db.session.get(cls, account_id)

    @classmethod
    def get_by_email(cls, email_address: str) -> "Accounts | None":
        return (
            db.session.execute(
                select(cls)
                .where(cls.email_address == email_address)
                .order_by(cls.account_id)
            )
            .scalars()
            .first()
        )

    @classmethod
    def all(cls) -> list["Accounts"]:
        return list(db.session.execute(select(cls)).scalars())

    @classmethod
    def from_auth_code(cls, account_id, auth_code) -> "Accounts | None":
        account = cls.get(account_id)
        if account and account.auth_code_is_valid(auth_code):
            return account
        return None

    @classmethod
    def delete_with_data(cls, account_id: int) -> None:
        """Delete the account and every row that belongs to it."""
        from .exercises import Exercises
        from .set_logs import SetLogs
        from .sets import Sets
        from .workout_sessions import WorkoutSessions
        from .workouts import Workouts

        for model in (SetLogs, WorkoutSessions, Sets, Exercises, Workouts):
            db.session.execute(
                delete(model).where(model.account_id == account_id)
            )
        db.session.execute(delete(cls).where(cls.account_id == account_id))
        db.session.commit()

    def days_old(self) -> int:
        if self.created is None:
            return 0
        return max(0, (dates.now() - self.created).days)
