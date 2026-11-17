"""The `users` table: sign-in and account-level information only."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin, enum_type
from app.models.enums import AccountStatus, UserRole

if TYPE_CHECKING:
    from app.models.profile import RoommatePreferences, StudentProfile
    from app.models.verification import IdentityVerification, StudentVerification


class User(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """An account. Not necessarily a student: owners and agents have one too."""

    __tablename__ = "users"
    __table_args__ = (
        # Stored in lower case so "A@x.com" and "a@x.com" cannot both exist.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    # Only ever a hash. The password itself is never stored anywhere.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        enum_type(UserRole, "role", 20),
        nullable=False,
        default=UserRole.MEMBER,
        server_default=UserRole.MEMBER.value,
    )
    account_status: Mapped[AccountStatus] = mapped_column(
        enum_type(AccountStatus, "account_status", 20),
        nullable=False,
        default=AccountStatus.ACTIVE,
        server_default=AccountStatus.ACTIVE.value,
    )
    # Proves the address works. It is NOT identity or student verification.
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When the person agreed to the Terms of Use and Privacy Policy.
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    student_profile: Mapped[StudentProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    roommate_preferences: Mapped[RoommatePreferences | None] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    # Two separate checks, each optional. See app/models/verification.py.
    identity_verification: Mapped[IdentityVerification | None] = relationship(
        back_populates="user", foreign_keys="IdentityVerification.user_id"
    )
    student_verification: Mapped[StudentVerification | None] = relationship(
        back_populates="user", foreign_keys="StudentVerification.user_id"
    )
