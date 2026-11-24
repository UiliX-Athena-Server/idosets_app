import json
from pathlib import Path

import click
from flask import Flask

OLD_DATABASE = "database.sqlite"


def include(app: Flask):
    @app.cli.command("migrate-db")
    @click.option(
        "--old",
        "old_path",
        type=click.Path(dir_okay=False, path_type=Path),
        default=None,
        help="The old database file (default: instance/database.sqlite).",
    )
    def migrate_db(old_path):
        """Copy the old database into the new one, cleaning it up on the way."""
        from app.extensions import db
        from app.migration import MigrationError, migrate

        old_path = old_path or Path(app.instance_path) / OLD_DATABASE
        new_path = db.engine.url.database
        click.echo(f"Old database: {old_path}")
        click.echo(f"New database: {new_path}")

        if Path(old_path).resolve() == Path(new_path).resolve():
            raise click.ClickException(
                "The old and new database are the same file."
            )

        try:
            report = migrate(old_path)
        except MigrationError as err:
            raise click.ClickException(str(err)) from err

        for line in report.lines():
            click.echo(line)
        click.echo("Done. The old database was not changed.")

    @app.cli.command("init-db")
    def init_db():
        """Create any missing tables (safe to run on an existing database)."""
        from app.extensions import db

        db.create_all()
        print("Database ready.")

    @app.cli.command("reset-db")
    @click.confirmation_option(prompt="This deletes ALL data. Continue?")
    def reset_db():
        """Drop and recreate every table."""
        from app.extensions import db

        db.drop_all()
        db.create_all()
        print("Database reset.")

    @app.cli.command("backup-db")
    def backup_db():
        """Write accounts, workouts, exercises and sets to instance/backup.json."""
        from app.models import Accounts, Exercises, Sets, Workouts

        backup = {}
        for account in Accounts.all():
            workouts = []
            for workout in Workouts.list_for_account(account.account_id):
                exercises = []
                for exercise in Exercises.list_for_workout(
                    account.account_id, workout.workout_id
                ):
                    exercises.append(
                        {
                            "order": exercise.order,
                            "name": exercise.name,
                            "info_url": exercise.info_url,
                            "info_url_favicon": exercise.info_url_favicon,
                            "__sets__": [
                                {
                                    key: value
                                    for key, value in s.to_dict().items()
                                    if key
                                    not in (
                                        "set_id",
                                        "exercise_id",
                                        "workout_id",
                                    )
                                }
                                for s in Sets.list_for_exercise(
                                    account.account_id, exercise.exercise_id
                                )
                            ],
                        }
                    )
                workouts.append(
                    {"name": workout.name, "__exercises__": exercises}
                )

            backup[account.email_address] = {
                "settings": account.settings,
                "__workouts__": workouts,
            }

        backup_file = Path(app.instance_path) / "backup.json"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        backup_file.write_text(json.dumps(backup, indent=2), encoding="utf-8")
        print(f"Backed up {len(backup)} account(s) to {backup_file}")

    @app.cli.command("restore-db")
    def restore_db():
        """Restore instance/backup.json into the database (skips existing emails)."""
        from app.extensions import db
        from app.models import Accounts, Exercises, Sets, Workouts

        backup_file = Path(app.instance_path) / "backup.json"
        if not backup_file.exists():
            print(f"No backup found at {backup_file}")
            return

        backup = json.loads(backup_file.read_text(encoding="utf-8"))
        restored = 0

        for email_address, data in backup.items():
            if Accounts.get_by_email(email_address):
                print(f"Skipping {email_address}, account already exists.")
                continue

            account = Accounts(
                email_address=email_address, settings=data.get("settings")
            )
            db.session.add(account)
            db.session.flush()

            for workout_data in data.get("__workouts__", []):
                workout = Workouts(
                    account_id=account.account_id, name=workout_data["name"]
                )
                db.session.add(workout)
                db.session.flush()

                for exercise_data in workout_data.get("__exercises__", []):
                    exercise = Exercises(
                        account_id=account.account_id,
                        workout_id=workout.workout_id,
                        order=exercise_data.get("order", 0),
                        name=exercise_data["name"],
                        info_url=exercise_data.get("info_url"),
                        info_url_favicon=exercise_data.get("info_url_favicon"),
                    )
                    db.session.add(exercise)
                    db.session.flush()

                    for set_data in exercise_data.get("__sets__", []):
                        db.session.add(
                            Sets(
                                account_id=account.account_id,
                                workout_id=workout.workout_id,
                                exercise_id=exercise.exercise_id,
                                **set_data,
                            )
                        )

            restored += 1

        db.session.commit()
        print(f"Restored {restored} account(s).")
