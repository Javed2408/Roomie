"""Swipes, matches, conversations and messages."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UuidPrimaryKeyMixin, enum_type
from app.models.enums import MatchStatus, SwipeAction

MESSAGE_MAX_LENGTH = 2000


class Swipe(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """One user's like or pass on another. One decision per pair."""

    __tablename__ = "swipes"
    __table_args__ = (
        UniqueConstraint("actor_id", "target_id"),
        CheckConstraint("actor_id <> target_id", name="not_self"),
        Index("ix_swipes_actor_id_created_at", "actor_id", "created_at"),
        Index("ix_swipes_target_id_action", "target_id", "action"),
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[SwipeAction] = mapped_column(
        enum_type(SwipeAction, "action", 10), nullable=False
    )


class Match(UuidPrimaryKeyMixin, Base):
    """Two users who liked each other.

    The pair is always stored with the smaller id first. That makes
    (A, B) and (B, A) the same row, so a duplicate match is impossible.
    """

    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("user_one_id", "user_two_id"),
        CheckConstraint("user_one_id < user_two_id", name="pair_ordered"),
        CheckConstraint("compatibility_score BETWEEN 0 AND 100", name="score_range"),
        Index("ix_matches_user_two_id", "user_two_id"),
    )

    user_one_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    user_two_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    # The score when the match was made, kept as a record. Empty only if it
    # could not be calculated (not enough answers to compare).
    compatibility_score: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[MatchStatus] = mapped_column(
        enum_type(MatchStatus, "status", 20),
        nullable=False,
        default=MatchStatus.ACTIVE,
        server_default=MatchStatus.ACTIVE.value,
    )
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """The private chat that a match enables. One per match."""

    __tablename__ = "conversations"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id"), nullable=False, unique=True
    )


class Message(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            f"char_length(content) BETWEEN 1 AND {MESSAGE_MAX_LENGTH}",
            name="content_length",
        ),
        Index("ix_messages_conversation_id_created_at", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
