"""The three independent verification types, and their evidence documents.

Roomie never has one generic "verified" flag. There are three separate
checks, each with its own table, status and history:

* IdentityVerification         - the person is who they say they are.
* StudentVerification          - the person is currently enrolled somewhere.
* ListingAuthorityVerification - the person may list one specific property.

Approving one never affects another. Having no row at all means that the
check has not been done ("not verified").
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UuidPrimaryKeyMixin, enum_type
from app.models.enums import (
    DocumentType,
    OwnerConfirmationStatus,
    StudentVerificationMethod,
    VerificationStatus,
)

if TYPE_CHECKING:
    from app.models.listing import AccommodationListing
    from app.models.user import User


class ReviewableMixin(TimestampMixin):
    """Columns shared by all three verification types.

    Defined once here and reused, so the three tables stay identical in how
    a review is recorded without the code being written three times.
    """

    status: Mapped[VerificationStatus] = mapped_column(
        enum_type(VerificationStatus, "status", 20),
        nullable=False,
        default=VerificationStatus.PENDING,
        server_default=VerificationStatus.PENDING.value,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # The administrator who made the latest decision.
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_note: Mapped[str | None] = mapped_column(Text)


# A decision (anything other than PENDING) must record who made it and when.
_DECISION_IS_ATTRIBUTED = CheckConstraint(
    "status = 'PENDING' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
    name="decision_is_attributed",
)


class IdentityVerification(UuidPrimaryKeyMixin, ReviewableMixin, Base):
    """Confirms a person's identity. At most one per user."""

    __tablename__ = "identity_verifications"
    __table_args__ = (_DECISION_IS_ATTRIBUTED,)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)

    user: Mapped[User] = relationship(
        back_populates="identity_verification", foreign_keys=[user_id]
    )
    documents: Mapped[list[VerificationDocument]] = relationship(
        back_populates="identity_verification"
    )


class StudentVerification(UuidPrimaryKeyMixin, ReviewableMixin, Base):
    """Confirms current enrolment at an institution. At most one per user."""

    __tablename__ = "student_verifications"
    __table_args__ = (_DECISION_IS_ATTRIBUTED,)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    method: Mapped[StudentVerificationMethod] = mapped_column(
        enum_type(StudentVerificationMethod, "method", 20), nullable=False
    )
    institution_name: Mapped[str] = mapped_column(String(180), nullable=False)
    # Enrolment ends. After this date an approval no longer counts.
    valid_until: Mapped[date | None] = mapped_column(Date)

    user: Mapped[User] = relationship(back_populates="student_verification", foreign_keys=[user_id])
    documents: Mapped[list[VerificationDocument]] = relationship(
        back_populates="student_verification"
    )


class ListingAuthorityVerification(UuidPrimaryKeyMixin, ReviewableMixin, Base):
    """Confirms the right to list ONE specific property.

    It belongs to a listing rather than to a user, because the same person
    can own one flat and merely rent another. The person being checked is
    the listing's creator.
    """

    __tablename__ = "listing_authority_verifications"
    __table_args__ = (
        _DECISION_IS_ATTRIBUTED,
        # A confirmation or denial must record which admin spoke to the owner.
        CheckConstraint(
            "owner_confirmation_status IN ('NOT_REQUIRED', 'PENDING') "
            "OR (owner_confirmed_by IS NOT NULL AND owner_confirmed_at IS NOT NULL)",
            name="owner_confirmer_recorded",
        ),
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accommodation_listings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # --- Owner authorisation (private; never in a public response) ---
    owner_name: Mapped[str | None] = mapped_column(String(120))
    owner_contact: Mapped[str | None] = mapped_column(String(255))
    owner_confirmation_status: Mapped[OwnerConfirmationStatus] = mapped_column(
        enum_type(OwnerConfirmationStatus, "owner_confirmation_status", 20),
        nullable=False,
        default=OwnerConfirmationStatus.NOT_REQUIRED,
        server_default=OwnerConfirmationStatus.NOT_REQUIRED.value,
    )
    owner_confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    owner_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_confirmation_note: Mapped[str | None] = mapped_column(Text)

    listing: Mapped[AccommodationListing] = relationship(back_populates="authority_verification")
    documents: Mapped[list[VerificationDocument]] = relationship(
        back_populates="listing_authority_verification"
    )


class VerificationDocument(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """A reference to one evidence file. The file itself is NOT stored here.

    The file lives in private object storage. `storage_key` says where, and
    must never be returned by any public API. Only authorised administrators
    and the uploader may ever obtain the file.
    """

    __tablename__ = "verification_documents"
    __table_args__ = (
        # Every document belongs to exactly one verification.
        CheckConstraint(
            "num_nonnulls(identity_verification_id, student_verification_id, "
            "listing_authority_verification_id) = 1",
            name="exactly_one_verification",
        ),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        Index("ix_verification_documents_identity_verification_id", "identity_verification_id"),
        Index("ix_verification_documents_student_verification_id", "student_verification_id"),
        Index(
            "ix_verification_documents_listing_authority_verification_id",
            "listing_authority_verification_id",
        ),
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

    document_type: Mapped[DocumentType] = mapped_column(
        enum_type(DocumentType, "document_type", 30), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # A fingerprint of the file, to detect tampering or duplicates.
    sha256: Mapped[str | None] = mapped_column(String(64))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Set when the file is erased under the retention policy. The row is
    # kept so the audit trail still shows that evidence once existed.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    identity_verification: Mapped[IdentityVerification | None] = relationship(
        back_populates="documents"
    )
    student_verification: Mapped[StudentVerification | None] = relationship(
        back_populates="documents"
    )
    listing_authority_verification: Mapped[ListingAuthorityVerification | None] = relationship(
        back_populates="documents"
    )
