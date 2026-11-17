"""Discovery: browse other students, see full profiles, like or pass.

Every route needs a signed-in member. Who can be seen is decided in one
place, app/repositories/discovery.py. The scoring rules live in
app/services/compatibility.py; nothing here calculates anything.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, Database
from app.core.rate_limit import rate_limit
from app.models.enums import SwipeAction
from app.schemas.discovery import DecisionOut, DiscoveryPageOut, StudentViewOut
from app.services import discovery as discovery_service
from app.services import matching as matching_service

router = APIRouter(tags=["discovery"])

# PRD 8.11: likes are rate-limited. Generous for a person, tight for a script.
_decision_limit = Depends(rate_limit("decision", limit=300, window_seconds=10 * 60))


@router.get("/discovery", response_model=DiscoveryPageOut)
def discover(
    user: CurrentUser,
    db: Database,
    limit: Annotated[
        int, Query(ge=1, le=discovery_service.MAX_PAGE_SIZE)
    ] = discovery_service.DEFAULT_PAGE_SIZE,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> DiscoveryPageOut:
    """The next people to decide on: those who share your societies first,
    then the same area, then everyone else; best score first within each."""
    return discovery_service.discover(db, user, limit=limit, cursor=cursor)


@router.get("/students/{student_id}", response_model=StudentViewOut)
def read_student(student_id: uuid.UUID, user: CurrentUser, db: Database) -> StudentViewOut:
    """Another student's full profile and your compatibility with them."""
    return discovery_service.view_student(db, user, student_id)


@router.post(
    "/discovery/{student_id}/like", response_model=DecisionOut, dependencies=[_decision_limit]
)
def like(student_id: uuid.UUID, user: CurrentUser, db: Database) -> DecisionOut:
    """Like someone. If they already liked you, this makes a match."""
    result = matching_service.decide(db, user, student_id, SwipeAction.LIKE)
    db.commit()
    return result


@router.post(
    "/discovery/{student_id}/pass", response_model=DecisionOut, dependencies=[_decision_limit]
)
def pass_on(student_id: uuid.UUID, user: CurrentUser, db: Database) -> DecisionOut:
    """Pass on someone. They are not told, and will not appear again."""
    result = matching_service.decide(db, user, student_id, SwipeAction.PASS)
    db.commit()
    return result
