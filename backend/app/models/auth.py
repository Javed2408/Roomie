"""Sign-in sessions and single-use account tokens."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin, enum_type
from app.models.enums import AccountTokenPurpose


class UserSession(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """One signed-in browser.

    The browser holds a random token in a cookie. Only the token's hash is
    stored here, so reading this table does not let anyone sign in.
    """

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_id", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # The session stops working at this time, whatever happens.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Used to end sessions that have been idle for too long.
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Set on logout, password reset or suspension. A revoked session is dead.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(255))


class AccountToken(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single-use token sent by email: verify an address or reset a password."""

    __tablename__ = "account_tokens"
    __table_args__ = (Index("ix_account_tokens_user_id_purpose", "user_id", "purpose"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[AccountTokenPurpose] = mapped_column(
        enum_type(AccountTokenPurpose, "purpose", 30), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Set the moment the token is used, so it can never be used twice.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
