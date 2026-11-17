"""Make sure the configured database exists and is fully migrated.

    python -m app.scripts.prepare_database [--reset] [--test-fixtures] [--practice-students]

Creates the database named by POSTGRES_DB if it is missing, then applies
every migration.

Options, all refused unless the database name ends in _test or _e2e, so
they can never touch your real or development data:

--reset              delete the whole database first and start empty
                     (the browser tests do this, so every run starts clean)
--test-fixtures      add the fictional directory records
--practice-students  also add fictional students to discover (implies
                     --test-fixtures)
"""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_ONLY_OPTIONS = ("--reset", "--test-fixtures", "--practice-students")


def is_test_database(name: str) -> bool:
    return name.endswith("_test") or name.endswith("_e2e")


def main() -> int:
    settings = get_settings()
    name = settings.postgres_db
    options = set(sys.argv[1:])

    if options & set(TEST_ONLY_OPTIONS) and not is_test_database(name):
        print(
            f"Refusing to use {', '.join(sorted(options))} on '{name}': "
            "only allowed for databases whose name ends in _test or _e2e."
        )
        return 1

    # Connect to the always-present "postgres" database to create ours.
    # CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT.
    admin_engine = create_engine(
        settings.database_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        # Give up quickly, with a clear message, if PostgreSQL is not running.
        connect_args={"connect_timeout": 5},
    )
    try:
        connection = admin_engine.connect()
    except OperationalError:
        print(
            "Could not connect to PostgreSQL. Is Docker Desktop running, and "
            "has the database been started with 'docker compose up -d --wait'?"
        )
        return 1
    with connection:
        if "--reset" in options:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            print(f"Deleted test database {name}.")
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
            print(f"Created database {name}.")
    admin_engine.dispose()

    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")

    if options & {"--test-fixtures", "--practice-students"}:
        from app.scripts.seed_test_fixtures import main as seed_main

        return seed_main(practice_students="--practice-students" in options)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
