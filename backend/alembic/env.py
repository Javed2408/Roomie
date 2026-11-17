"""Alembic's entry point: tells it which database and which tables to use.

Run Alembic from the backend/ folder, for example:

    alembic upgrade head      apply every migration not yet applied
    alembic downgrade -1      undo the most recent migration
    alembic current           show which migration the database is on
    alembic revision --autogenerate -m "describe the change"
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# Importing the models package registers every table on Base.metadata.
import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    # Keep loggers that already exist (the application's) switched on.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# What the database SHOULD look like. Alembic compares this with what the
# database actually looks like to work out a migration.
target_metadata = Base.metadata


def get_database_url() -> str:
    """Use the URL handed in by a caller (the tests do this to target the
    test database); otherwise the one from the application settings.

    There is deliberately no database address in alembic.ini, so the
    password stays in the .env file and nowhere else.
    """
    override = config.attributes.get("database_url")
    if override is not None:
        return str(override)
    return get_settings().database_url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (`alembic upgrade head --sql`)."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply the migrations."""
    engine = create_engine(get_database_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Also notice when a column's type changes, not just its name.
            compare_type=True,
        )
        # Each migration runs inside a transaction: it either applies
        # completely or not at all.
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
