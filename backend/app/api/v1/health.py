"""Health-check endpoints.

Two separate questions, two endpoints:

* GET /health     - "Is the API process running?" Never touches the database.
* GET /health/db  - "Can the API reach PostgreSQL right now?"

Keeping them apart means a database outage is reported as a database outage,
not as "the whole API is down".
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse
from app.services.health import is_database_reachable

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def read_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version=__version__)


@router.get(
    "/db",
    response_model=DatabaseHealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": DatabaseHealthResponse,
            "description": "The database cannot be reached.",
        }
    },
)
def read_database_health(
    response: Response, db: Session = Depends(get_db)
) -> DatabaseHealthResponse:
    if is_database_reachable(db):
        return DatabaseHealthResponse(status="ok", database="connected")

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return DatabaseHealthResponse(status="unavailable", database="unreachable")
