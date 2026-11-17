"""SQLAlchemy engine and session setup.

The engine manages a pool of connections to PostgreSQL. A session is a short
conversation with the database that lasts for one API request.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

# Creating the engine does not connect yet; the first query does.
engine = create_engine(
    get_settings().database_url,
    # Test each pooled connection before use, so a database restart does not
    # leave the API holding dead connections.
    pool_pre_ping=True,
    # Fail quickly instead of hanging when the database is unreachable.
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: provide a session and always close it afterwards."""
    with SessionLocal() as session:
        yield session
