"""Shared test fixtures. Pytest loads this file automatically."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.main import app
from app.services.email import Email, get_email_sender
from app.services.storage import LocalPrivateStorage, get_storage

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A client that calls the API in-process, without starting a server."""
    with TestClient(app) as test_client:
        yield test_client
    # Undo any dependency replacements a test made, so tests stay independent.
    app.dependency_overrides.clear()


def alembic_config(database_url: str) -> Config:
    """Alembic settings pointed at a specific database."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


def ensure_database(name: str) -> None:
    """Create a database if it does not exist yet."""
    # CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT.
    admin_engine = create_engine(get_settings().database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine.dispose()


def reset_schema(engine: Engine) -> None:
    """Empty a TEST database completely. Refuses to touch anything else."""
    name = engine.url.database or ""
    if not name.endswith("_test"):
        raise RuntimeError(f"Refusing to wipe '{name}': it is not a test database.")
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    """A separate, throwaway database with every migration applied.

    The tables are built by running the real Alembic migrations, not by a
    shortcut, so the tests also prove that the migrations work. The
    application's own database is never touched.
    """
    settings = get_settings()
    ensure_database(settings.postgres_test_db)

    engine = create_engine(settings.test_database_url)
    reset_schema(engine)
    command.upgrade(
        alembic_config(settings.test_database_url.render_as_string(hide_password=False)),
        "head",
    )
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine: Engine) -> Iterator[Session]:
    """A database session whose changes are thrown away after each test.

    Everything a test does happens inside one outer transaction that is
    rolled back at the end, so every test starts from empty tables. Inside
    it, the session uses savepoints, which lets a test trigger a database
    error on purpose and carry on.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


class MemoryEmailSender:
    """Keeps "sent" emails in a list so tests can read them."""

    def __init__(self) -> None:
        self.sent: list[Email] = []

    def send(self, email: Email) -> None:
        self.sent.append(email)


@pytest.fixture
def mailbox() -> MemoryEmailSender:
    return MemoryEmailSender()


@pytest.fixture
def storage(tmp_path: Path) -> LocalPrivateStorage:
    """Private storage in a temporary folder that pytest deletes afterwards."""
    return LocalPrivateStorage(tmp_path / "private-storage")


@pytest.fixture
def new_client(
    db: Session, mailbox: MemoryEmailSender, storage: LocalPrivateStorage
) -> Iterator[Callable[[], TestClient]]:
    """Make API clients that use the test database, mailbox and storage.

    Each client has its own cookies, so it behaves like a separate browser.
    Tests that need two people ask for two clients.
    """

    def use_test_database() -> Iterator[Session]:
        yield db

    limiter.reset()
    app.dependency_overrides[get_db] = use_test_database
    app.dependency_overrides[get_email_sender] = lambda: mailbox
    app.dependency_overrides[get_storage] = lambda: storage
    clients: list[TestClient] = []

    def make() -> TestClient:
        test_client = TestClient(app)
        clients.append(test_client)
        return test_client

    yield make
    for test_client in clients:
        test_client.close()
    app.dependency_overrides.clear()
    limiter.reset()


@pytest.fixture
def api(new_client: Callable[[], TestClient]) -> TestClient:
    """One API client: one browser."""
    return new_client()
