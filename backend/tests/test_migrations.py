"""Tests that the Alembic migrations build the schema the models describe."""

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, inspect, text

import app.models  # noqa: F401 - registers every table on Base.metadata
from app.core.config import get_settings
from app.db.base import Base
from tests.conftest import alembic_config, ensure_database, reset_schema

pytestmark = pytest.mark.integration


def test_migrations_create_every_table(test_engine: Engine) -> None:
    created = set(inspect(test_engine).get_table_names())

    assert created == set(Base.metadata.tables) | {"alembic_version"}
    assert len(Base.metadata.tables) == 26


def test_database_matches_the_models_exactly(test_engine: Engine) -> None:
    """If a model is changed without a migration, this test fails."""
    with test_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)

    assert differences == []


def test_migrations_can_be_rolled_back_and_reapplied() -> None:
    """Upgrade, downgrade to nothing, then upgrade again, on a scratch database."""
    settings = get_settings()
    scratch_name = "roomie_migration_test"
    scratch_url = settings.database_url.set(database=scratch_name)
    ensure_database(scratch_name)
    engine = create_engine(scratch_url)
    reset_schema(engine)
    config = alembic_config(scratch_url.render_as_string(hide_password=False))

    try:
        command.upgrade(config, "head")
        assert "accommodation_listings" in inspect(engine).get_table_names()

        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}

        command.upgrade(config, "head")
        assert "review_events" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_upgrade_keeps_existing_rows(test_engine: Engine) -> None:
    """Running `upgrade head` on an up-to-date database changes nothing."""
    settings = get_settings()
    config = alembic_config(settings.test_database_url.render_as_string(hide_password=False))

    with test_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO localities (name, name_key, city, state) "
                "VALUES ('Keep Me', 'keep me', 'Test City', 'Test State')"
            )
        )
    try:
        command.upgrade(config, "head")
        with test_engine.connect() as connection:
            kept = connection.scalar(text("SELECT count(*) FROM localities WHERE name = 'Keep Me'"))
        assert kept == 1
    finally:
        with test_engine.begin() as connection:
            connection.execute(text("DELETE FROM localities WHERE name = 'Keep Me'"))
