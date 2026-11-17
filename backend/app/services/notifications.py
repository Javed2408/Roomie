"""In-app notifications: reading them and marking them read.

Notifications are created by the features they are about (for example
app/services/matching.py creates "new match" ones). Nothing is emailed or
pushed; they are shown inside the app only.

Every function acts on the signed-in person's own notifications. Someone
else's answers "not found".
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.notification import Notification
from app.models.user import User
from app.schemas.discovery import NotificationOut, NotificationsOut

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def list_notifications(
    db: Session, user: User, *, unread_only: bool = False, limit: int = DEFAULT_LIMIT
) -> NotificationsOut:
    statement = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))
    items = db.scalars(
        statement.order_by(Notification.created_at.desc(), Notification.id).limit(limit)
    )
    unread = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return NotificationsOut(
        items=[NotificationOut.model_validate(item, from_attributes=True) for item in items],
        unread_count=int(unread or 0),
    )


def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> None:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    if notification is None:
        raise NotFoundError("That notification does not exist.")
    notification.is_read = True
    db.flush()


def mark_all_read(db: Session, user: User) -> None:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.flush()
