"""Tests for the health-check endpoints."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


def test_health_reports_api_is_running(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Roomie API",
        "version": __version__,
    }


@pytest.mark.integration
def test_database_health_reports_connected(client: TestClient) -> None:
    """Uses the real PostgreSQL container, so it must be running."""
    response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_health_returns_503_when_database_is_unreachable(
    client: TestClient,
) -> None:
    # Point the endpoint at a port where nothing is listening, so the real
    # connection attempt fails exactly as it would during an outage.
    unreachable_url = get_settings().database_url.set(host="127.0.0.1", port=1)
    unreachable_engine = create_engine(unreachable_url, connect_args={"connect_timeout": 2})

    def get_unreachable_db() -> Iterator[Session]:
        with Session(unreachable_engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_unreachable_db

    response = client.get("/api/v1/health/db")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}


def test_frontend_origin_is_allowed_by_cors(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_unknown_origin_is_not_allowed_by_cors(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers
