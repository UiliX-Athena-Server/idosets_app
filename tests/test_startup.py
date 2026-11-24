import multiprocessing
import sqlite3

import pytest

from app import create_app
from tests.test_migration import old_db  # noqa: F401  (fixture)


def _start(db_file):
    return create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}"}
    )


def _count(db_file, table):
    with sqlite3.connect(db_file) as conn:
        return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_startup_migrates_and_removes_old_database(old_db):  # noqa: F811
    new_db = old_db.parent / "idosets.sqlite"

    _start(new_db)

    assert not old_db.exists()
    assert _count(new_db, "accounts") == 1
    assert _count(new_db, "set_logs") == 2

    # Starting again is a no-op.
    _start(new_db)
    assert _count(new_db, "set_logs") == 2


def test_startup_migrates_into_an_empty_new_database(old_db):  # noqa: F811
    new_db = old_db.parent / "idosets.sqlite"
    sqlite3.connect(new_db).close()  # e.g. created empty by an older build

    _start(new_db)

    assert not old_db.exists()
    assert _count(new_db, "workouts") == 1


def test_startup_keeps_old_database_if_new_one_has_data(old_db):  # noqa: F811
    new_db = old_db.parent / "idosets.sqlite"
    _start(new_db)  # migrates and removes the old file
    old_db.write_bytes((old_db.parent / "idosets.sqlite").read_bytes())

    _start(new_db)

    assert old_db.exists()  # never deleted without having been copied


def test_failed_migration_keeps_old_database(tmp_path):
    old = tmp_path / "database.sqlite"
    old.write_bytes(b"this is not a sqlite database")

    with pytest.raises(sqlite3.DatabaseError):
        _start(tmp_path / "idosets.sqlite")

    assert old.exists()


def _start_in_process(db_file):
    _start(db_file)


def test_concurrent_startups_migrate_once(old_db):  # noqa: F811
    """Like several gunicorn workers booting at the same moment."""
    new_db = old_db.parent / "idosets.sqlite"
    ctx = multiprocessing.get_context("spawn")
    processes = [
        ctx.Process(target=_start_in_process, args=(str(new_db),))
        for _ in range(4)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(60)

    assert [p.exitcode for p in processes] == [0, 0, 0, 0]
    assert not old_db.exists()
    assert _count(new_db, "accounts") == 1
    assert _count(new_db, "set_logs") == 2
