"""Response shapes for the health-check endpoints."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Returned when the API process itself is running."""

    status: Literal["ok"]
    service: str
    version: str


class DatabaseHealthResponse(BaseModel):
    """Reports whether the API can currently reach PostgreSQL."""

    status: Literal["ok", "unavailable"]
    database: Literal["connected", "unreachable"]
