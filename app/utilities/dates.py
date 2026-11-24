from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# All datetimes are stored in the database as *naive* Europe/London wall-clock
# times. That is how the existing data was written, so we keep doing it to
# avoid a data migration. Always use these helpers instead of datetime.now().
LOCAL_TZ = ZoneInfo("Europe/London")


def now() -> datetime:
    """The current Europe/London time, as a naive datetime (DB format)."""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None, microsecond=0)


def days_from_now(days: int) -> datetime:
    return now() + timedelta(days=days)


def seconds_between(start: datetime | None, end: datetime | None) -> int:
    """Whole seconds between two naive datetimes, never negative."""
    if start is None or end is None:
        return 0
    return max(0, int((end - start).total_seconds()))


def display(value: datetime | None) -> str | None:
    """Human readable timestamp, e.g. 'Tue, 24 Nov, 18:30'."""
    if value is None:
        return None
    return value.strftime("%a, %d %b, %H:%M")


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
