"""
Database preparation that runs once whenever the application starts.

Every process (each gunicorn worker, ``flask run``, CLI commands) calls
:func:`prepare_database` from ``create_app``. An exclusive lock on
``instance/.startup.lock`` makes sure only one process works on the database
at a time; the others wait, then find the work already done.

Steps, in order:

1. If the pre-2.0 database (``database.sqlite``) sits next to the configured
   database and the configured database is missing or empty, copy the data
   across (see :mod:`app.migration`), check it landed, then delete the old
   file.
2. If the configured database still doesn't exist, create it.
"""

import fcntl
import logging
from contextlib import contextmanager
from pathlib import Path

from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from app.extensions import db

log = logging.getLogger(__name__)

OLD_DATABASE_NAME = "database.sqlite"
LOCK_FILE_NAME = ".startup.lock"


def _sqlite_file(app: Flask) -> Path | None:
    url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if url.get_backend_name() != "sqlite" or url.database in (
        None,
        "",
        ":memory:",
    ):
        return None
    return Path(url.database).resolve()


@contextmanager
def _exclusive_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as handle:
        fcntl.flock(
            handle, fcntl.LOCK_EX
        )  # blocks until other processes finish
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _remove_sqlite_file(path: Path) -> None:
    for suffix in ("", "-journal", "-wal", "-shm"):
        Path(f"{path}{suffix}").unlink(missing_ok=True)


def _migrate_old_database(app: Flask, old_database: Path) -> None:
    from app.migration import TABLES, migrate, target_is_empty

    with app.app_context():
        db.create_all()
        if not target_is_empty():
            log.warning(
                "Found an old database at %s, but the new database already has "
                "data, so it was not migrated or removed. Delete or move the "
                "old file once you're sure it's not needed.",
                old_database,
            )
            return

        log.warning("Migrating the old database %s ...", old_database)
        report = migrate(old_database)
        for line in report.lines():
            log.warning(line)

        # Only delete the old data once the new database is confirmed to hold
        # everything the migration reported copying.
        db.session.remove()
        for model in TABLES:
            name = model.__tablename__
            count = db.session.execute(
                select(func.count()).select_from(model)
            ).scalar_one()
            if count != report.copied[name]:
                raise RuntimeError(
                    f"Migration check failed for {name}: expected "
                    f"{report.copied[name]} rows, found {count}. The old "
                    f"database {old_database} has been kept."
                )

    _remove_sqlite_file(old_database)
    log.warning("Migration complete; removed the old database %s", old_database)


def prepare_database(app: Flask) -> None:
    database_file = _sqlite_file(app)
    if database_file is None:
        return

    old_database = database_file.parent / OLD_DATABASE_NAME

    with _exclusive_lock(database_file.parent / LOCK_FILE_NAME):
        if old_database.exists() and old_database != database_file:
            _migrate_old_database(app, old_database)

        if not database_file.exists():
            with app.app_context():
                db.create_all()
            log.info("Created a new database at %s", database_file)
