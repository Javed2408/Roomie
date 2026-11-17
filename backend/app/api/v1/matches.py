"""The signed-in person's matches and notifications.

Nothing here accepts another person's id to act on: a match or
notification that is not yours answers "not found".
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, Database
from app.schemas.account import MessageResponse
from app.schemas.discovery import MatchDetailOut, MatchOut, NotificationsOut
from app.services import matching as matching_service
from app.services import notifications as notification_service

router = APIRouter(tags=["matches"])


@router.get("/matches", response_model=list[MatchOut])
def list_matches(user: CurrentUser, db: Database) -> list[MatchOut]:
    """People you liked who liked you back, newest first."""
    return matching_service.list_matches(db, user)


@router.get("/matches/{match_id}", response_model=MatchDetailOut)
def read_match(match_id: uuid.UUID, user: CurrentUser, db: Database) -> MatchDetailOut:
    return matching_service.match_detail(db, user, match_id)


@router.get("/notifications", response_model=NotificationsOut)
def list_notifications(
    user: CurrentUser,
    db: Database,
    unread_only: bool = False,
    limit: Annotated[
        int, Query(ge=1, le=notification_service.MAX_LIMIT)
    ] = notification_service.DEFAULT_LIMIT,
) -> NotificationsOut:
    return notification_service.list_notifications(db, user, unread_only=unread_only, limit=limit)


@router.post("/notifications/{notification_id}/read", response_model=MessageResponse)
def mark_notification_read(
    notification_id: uuid.UUID, user: CurrentUser, db: Database
) -> MessageResponse:
    notification_service.mark_read(db, user, notification_id)
    db.commit()
    return MessageResponse(message="Marked as read.")


@router.post("/notifications/read-all", response_model=MessageResponse)
def mark_all_notifications_read(user: CurrentUser, db: Database) -> MessageResponse:
    notification_service.mark_all_read(db, user)
    db.commit()
    return MessageResponse(message="All notifications marked as read.")
