"""Blocks and reports."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin, enum_type
from app.models.enums import ReportReason, ReportStatus


class Block(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """One user blocking another. Affects discovery, messages and interests."""

    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_user_id"),
        CheckConstraint("blocker_id <> blocked_user_id", name="not_self"),
        Index("ix_blocks_blocked_user_id", "blocked_user_id"),
    )

    blocker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    blocked_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class Report(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """A report about a user, a listing or a message, for moderators."""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(reported_user_id, listing_id, message_id) >= 1",
            name="has_a_target",
        ),
        Index("ix_reports_status_created_at", "status", "created_at"),
    )

    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reported_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    listing_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accommodation_listings.id"))
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id"))
    reason: Mapped[ReportReason] = mapped_column(
        enum_type(ReportReason, "reason", 30), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(
        enum_type(ReportStatus, "status", 20),
        nullable=False,
        default=ReportStatus.OPEN,
        server_default=ReportStatus.OPEN.value,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
