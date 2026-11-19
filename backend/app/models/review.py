"""The append-only history of administrative decisions."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ReviewEvent(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """One decision: who changed which status, from what, to what, and why.

    A row is written for every change to a verification's status and every
    change to a listing's moderation status. Rows are never edited or
    deleted, which is what makes this a trustworthy audit trail.
    """

    __tablename__ = "review_events"
    __table_args__ = (
        # Every event is about exactly one thing.
        CheckConstraint(
            "num_nonnulls(identity_verification_id, student_verification_id, "
            "listing_authority_verification_id, listing_id) = 1",
            name="exactly_one_subject",
        ),
        Index("ix_review_events_identity_verification_id", "identity_verification_id"),
        Index("ix_review_events_student_verification_id", "student_verification_id"),
        Index(
            "ix_review_events_listing_authority_verification_id",
            "listing_authority_verification_id",
        ),
        Index("ix_review_events_listing_id", "listing_id"),
    )

    identity_verification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("identity_verifications.id", ondelete="CASCADE")
    )
    student_verification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("student_verifications.id", ondelete="CASCADE")
    )
    listing_authority_verification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listing_authority_verifications.id", ondelete="CASCADE")
    )
    # Set for listing moderation decisions.
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accommodation_listings.id", ondelete="CASCADE")
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    actor: Mapped[User] = relationship()
