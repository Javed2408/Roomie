"""In-app notifications."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin

# Notification types. Stored as text, so adding one needs no migration.
NEW_MATCH = "NEW_MATCH"


class Notification(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id_is_read_created_at", "user_id", "is_read", "created_at"),
        # One "new match" notification per person per match, enforced by the
        # database, so a retried or simultaneous request cannot send two.
        Index(
            "uq_notifications_new_match",
            "user_id",
            "reference_id",
            unique=True,
            postgresql_where=text(f"type = '{NEW_MATCH}'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # What the notification is about, e.g. ("match", <match id>).
    reference_type: Mapped[str | None] = mapped_column(String(60))
    reference_id: Mapped[uuid.UUID | None] = mapped_column()
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
