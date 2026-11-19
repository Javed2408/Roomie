"""Rules for the three verification types.

Nothing here knows about HTTP. Functions take a database session and model
objects, enforce the rules, and raise an `AppError` when a rule is broken.
The caller decides when to commit.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, PermissionDeniedError
from app.models.enums import (
    DocumentType,
    ListingCreatorType,
    ListingType,
    OwnerConfirmationStatus,
    TenantPermissionBasis,
    UserRole,
    VerificationStatus,
)
from app.models.listing import AccommodationListing
from app.models.review import ReviewEvent
from app.models.user import User
from app.models.verification import (
    IdentityVerification,
    ListingAuthorityVerification,
    StudentVerification,
    VerificationDocument,
)
from app.services import notifications

Verification = IdentityVerification | StudentVerification | ListingAuthorityVerification

# What other people are allowed to learn about a check. A rejection is
# private, so publicly it looks the same as "never checked".
PublicVerificationState = Literal["NOT_VERIFIED", "PENDING", "VERIFIED"]

_NOTE_REQUIRED = {VerificationStatus.REJECTED, VerificationStatus.NEEDS_RESUBMISSION}


def public_state(
    verification: Verification | None, *, today: date | None = None
) -> PublicVerificationState:
    """Translate a verification record into what the public may see."""
    if verification is None:
        return "NOT_VERIFIED"
    if verification.status == VerificationStatus.PENDING:
        return "PENDING"
    if verification.status != VerificationStatus.APPROVED:
        return "NOT_VERIFIED"
    today = today or datetime.now(UTC).date()
    # A student approval stops counting once enrolment has lapsed.
    if isinstance(verification, StudentVerification) and verification.valid_until is not None:
        if verification.valid_until < today:
            return "NOT_VERIFIED"
    # A tenant's authority stops counting once their rental agreement ends.
    if (
        isinstance(verification, ListingAuthorityVerification)
        and verification.rental_agreement_valid_until is not None
        and verification.rental_agreement_valid_until < today
    ):
        return "NOT_VERIFIED"
    return "VERIFIED"


def _current_document_types(documents: list[VerificationDocument]) -> set[DocumentType]:
    """Types of the documents that have not been deleted."""
    return {document.document_type for document in documents if document.deleted_at is None}


def _identity_approved(identity_verification: IdentityVerification | None) -> bool:
    return (
        identity_verification is not None
        and identity_verification.status == VerificationStatus.APPROVED
    )


def listing_authority_gaps(
    listing: AccommodationListing,
    verification: ListingAuthorityVerification,
    identity_verification: IdentityVerification | None,
    *,
    tenant_permission_basis: TenantPermissionBasis | None = None,
    rental_agreement_valid_until: date | None = None,
    today: date | None = None,
) -> list[str]:
    """Say what is still missing before listing authority can be approved.

    An empty list means every requirement for the listing's creator type is
    met. The requirements (docs/DATABASE_SCHEMA.md, 3.7):

    * Owner:  approved identity verification and proof of ownership.
    * Tenant: a rental agreement that is still running, AND the reviewer's
              record of why the tenant may take someone in: either the
              agreement itself permits sharing, or the landlord's written
              permission (which must then be among the documents). A
              genuine agreement proves tenancy, not permission to share.
    * Agent:  approved identity verification, the owner's written
              authorisation, and confirmation obtained directly from the
              owner by a Roomie administrator.

    For tenants, the permission basis and end date can be passed in (as
    the reviewer approves) or already be stored on the verification.
    """
    documents = _current_document_types(verification.documents)
    gaps: list[str] = []
    today = today or datetime.now(UTC).date()

    if listing.creator_type == ListingCreatorType.PROPERTY_OWNER:
        if not _identity_approved(identity_verification):
            gaps.append("The owner's identity has not been verified.")
        if DocumentType.OWNERSHIP_PROOF not in documents:
            gaps.append("Proof of ownership has not been provided.")

    elif listing.creator_type == ListingCreatorType.EXISTING_TENANT:
        basis = tenant_permission_basis or verification.tenant_permission_basis
        valid_until = rental_agreement_valid_until or verification.rental_agreement_valid_until
        if DocumentType.RENTAL_AGREEMENT not in documents:
            gaps.append("A rental agreement has not been provided.")
        if valid_until is None:
            gaps.append("Record the date the rental agreement ends.")
        elif valid_until < today:
            gaps.append("The rental agreement has already ended.")
        if basis is None:
            gaps.append(
                "Record what permits the tenant to take someone in: the agreement "
                "itself, or the landlord's permission."
            )
        elif (
            basis == TenantPermissionBasis.LANDLORD_PERMISSION
            and DocumentType.LANDLORD_PERMISSION not in documents
        ):
            gaps.append("The landlord's permission has not been provided.")

    elif listing.creator_type == ListingCreatorType.AUTHORIZED_AGENT:
        if not _identity_approved(identity_verification):
            gaps.append("The agent's identity has not been verified.")
        if DocumentType.OWNER_AUTHORIZATION not in documents:
            gaps.append("The owner's written authorisation has not been provided.")
        if verification.owner_confirmation_status != OwnerConfirmationStatus.CONFIRMED:
            gaps.append("The owner has not independently confirmed the authorisation.")

    else:
        gaps.append("The listing does not state who is offering the property.")

    return gaps


def identity_verification_of(db: Session, user_id: uuid.UUID) -> IdentityVerification | None:
    """Read a user's identity verification straight from the database.

    A fresh query on purpose: this decides whether an agent may be
    approved, so it must never use a copy loaded earlier that might be
    out of date.
    """
    return db.scalar(
        select(IdentityVerification)
        .where(IdentityVerification.user_id == user_id)
        .execution_options(populate_existing=True)
    )


def _require_admin(actor: User) -> None:
    if actor.role != UserRole.ADMIN:
        raise PermissionDeniedError("Only an administrator can review a verification.")


def _review_event_for(verification: Verification) -> ReviewEvent:
    """Start a history row pointing at the right kind of verification."""
    if isinstance(verification, IdentityVerification):
        return ReviewEvent(identity_verification_id=verification.id)
    if isinstance(verification, StudentVerification):
        return ReviewEvent(student_verification_id=verification.id)
    return ReviewEvent(listing_authority_verification_id=verification.id)


def review_verification(
    db: Session,
    verification: Verification,
    *,
    new_status: VerificationStatus,
    reviewer: User,
    note: str | None = None,
    tenant_permission_basis: TenantPermissionBasis | None = None,
    rental_agreement_valid_until: date | None = None,
) -> ReviewEvent:
    """Record an administrator's decision on ONE verification.

    Only the verification passed in changes. Approving someone's identity
    does not touch their student verification or any listing authority.

    For a tenant's listing authority, approving also records what the
    reviewer saw: the permission basis and the agreement's end date.
    """
    _require_admin(reviewer)

    if new_status == VerificationStatus.PENDING:
        raise BusinessRuleError("A review must reach a decision; it cannot set 'pending'.")
    if verification.status == new_status:
        raise ConflictError(f"This verification is already {new_status.value.lower()}.")
    if new_status in _NOTE_REQUIRED and not (note and note.strip()):
        raise BusinessRuleError("A reason is required when not approving a verification.")

    is_tenant_authority = (
        isinstance(verification, ListingAuthorityVerification)
        and verification.listing.creator_type == ListingCreatorType.EXISTING_TENANT
    )
    if (tenant_permission_basis or rental_agreement_valid_until) and not is_tenant_authority:
        raise BusinessRuleError(
            "A permission basis and agreement end date apply only to a tenant's listing."
        )

    if (
        isinstance(verification, ListingAuthorityVerification)
        and new_status == VerificationStatus.APPROVED
    ):
        listing = verification.listing
        gaps = listing_authority_gaps(
            listing,
            verification,
            identity_verification_of(db, listing.owner_id),
            tenant_permission_basis=tenant_permission_basis,
            rental_agreement_valid_until=rental_agreement_valid_until,
        )
        if gaps:
            raise BusinessRuleError("Listing authority cannot be approved yet.", details=gaps)
        if is_tenant_authority:
            if tenant_permission_basis:
                verification.tenant_permission_basis = tenant_permission_basis
            if rental_agreement_valid_until:
                verification.rental_agreement_valid_until = rental_agreement_valid_until

    event = _review_event_for(verification)
    event.actor_id = reviewer.id
    event.from_status = verification.status.value
    event.to_status = new_status.value
    event.note = note

    verification.status = new_status
    verification.reviewed_by = reviewer.id
    verification.reviewed_at = datetime.now(UTC)
    verification.reviewer_note = note

    db.add(event)
    if isinstance(verification, ListingAuthorityVerification) and new_status in _NOTE_REQUIRED:
        # The creator must act (upload new evidence), so tell them.
        notifications.notify(
            db,
            verification.listing.owner_id,
            type=notifications.AUTHORITY_NEEDS_ATTENTION,
            title="Your listing needs more evidence",
            body=(
                f'Roomie could not confirm your right to list "{verification.listing.title}". '
                "Open the listing to see why."
            ),
            reference_type="listing",
            reference_id=verification.listing.id,
        )
    db.flush()
    return event


def record_owner_confirmation(
    db: Session,
    verification: ListingAuthorityVerification,
    *,
    confirmed: bool,
    admin: User,
    note: str,
) -> None:
    """Record the outcome of an administrator contacting the owner directly.

    This is the "independent owner confirmation" required for agents. The
    note must say how the owner was reached, so the check can be audited.
    """
    _require_admin(admin)
    if verification.listing.listing_type != ListingType.EXISTING_ACCOMMODATION:
        raise BusinessRuleError("Only a property listing can have an owner confirmation.")
    if not note.strip():
        raise BusinessRuleError("Describe how the owner was contacted.")

    verification.owner_confirmation_status = (
        OwnerConfirmationStatus.CONFIRMED if confirmed else OwnerConfirmationStatus.DENIED
    )
    verification.owner_confirmed_by = admin.id
    verification.owner_confirmed_at = datetime.now(UTC)
    verification.owner_confirmation_note = note
    db.flush()
