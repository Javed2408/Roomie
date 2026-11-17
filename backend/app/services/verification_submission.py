"""Submitting evidence for one of the three verification types.

The same simple rule applies to all three:

* No record yet            -> create one, status PENDING.
* PENDING                  -> the new document is added to it.
* REJECTED / NEEDS_RESUBMISSION -> it goes back to PENDING for a new review.
* APPROVED                 -> refused; there is nothing left to submit.

Submitting never approves anything. Every submission waits for a human.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.enums import (
    DocumentType,
    ListingCreatorType,
    ListingType,
    OwnerConfirmationStatus,
    StudentVerificationMethod,
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
from app.services.storage import PrivateStorage, ValidatedFile, new_storage_key
from app.services.verification import Verification

logger = logging.getLogger(__name__)

# Which kinds of document each verification type accepts. A rental
# agreement, for example, is not evidence of identity.
IDENTITY_DOCUMENTS = {DocumentType.GOVERNMENT_ID}
STUDENT_DOCUMENTS = {DocumentType.STUDENT_ID, DocumentType.ENROLMENT_PROOF}
LISTING_AUTHORITY_DOCUMENTS = {
    DocumentType.OWNERSHIP_PROOF,
    DocumentType.RENTAL_AGREEMENT,
    DocumentType.LANDLORD_PERMISSION,
    DocumentType.OWNER_AUTHORIZATION,
}


def _require_allowed(document_type: DocumentType, allowed: set[DocumentType]) -> None:
    if document_type not in allowed:
        names = ", ".join(sorted(item.value for item in allowed))
        raise BusinessRuleError(f"That kind of document is not accepted here. Accepted: {names}.")


def _reopen_if_needed(db: Session, verification: Verification, actor: User) -> None:
    """Apply the status rule from the top of this file to an existing record."""
    if verification.status == VerificationStatus.APPROVED:
        raise ConflictError("This verification has already been approved.")
    if verification.status == VerificationStatus.PENDING:
        return

    event = ReviewEvent(
        actor_id=actor.id,
        from_status=verification.status.value,
        to_status=VerificationStatus.PENDING.value,
        note="Resubmitted by the applicant.",
    )
    if isinstance(verification, IdentityVerification):
        event.identity_verification_id = verification.id
    elif isinstance(verification, StudentVerification):
        event.student_verification_id = verification.id
    else:
        event.listing_authority_verification_id = verification.id
    db.add(event)

    verification.status = VerificationStatus.PENDING
    verification.submitted_at = datetime.now(UTC)


def _attach_document(
    db: Session,
    storage: PrivateStorage,
    *,
    uploader: User,
    document_type: DocumentType,
    file: ValidatedFile,
    identity: IdentityVerification | None = None,
    student: StudentVerification | None = None,
    authority: ListingAuthorityVerification | None = None,
) -> VerificationDocument:
    """Save the file privately, then record a reference to it."""
    key = new_storage_key()
    storage.save(key, file.data)
    try:
        document = VerificationDocument(
            identity_verification_id=identity.id if identity else None,
            student_verification_id=student.id if student else None,
            listing_authority_verification_id=authority.id if authority else None,
            document_type=document_type,
            storage_key=key,
            original_filename=file.original_filename,
            content_type=file.content_type,
            size_bytes=len(file.data),
            sha256=file.sha256,
            uploaded_by=uploader.id,
        )
        db.add(document)
        db.flush()
    except Exception:
        # Do not leave a file behind that no record points to.
        storage.delete(key)
        raise
    return document


def submit_identity_document(
    db: Session,
    storage: PrivateStorage,
    *,
    user: User,
    document_type: DocumentType,
    file: ValidatedFile,
) -> IdentityVerification:
    _require_allowed(document_type, IDENTITY_DOCUMENTS)

    verification = user.identity_verification
    if verification is None:
        verification = IdentityVerification(user_id=user.id)
        db.add(verification)
        db.flush()
    else:
        _reopen_if_needed(db, verification, user)

    _attach_document(
        db, storage, uploader=user, document_type=document_type, file=file, identity=verification
    )
    db.refresh(verification)
    return verification


def submit_student_document(
    db: Session,
    storage: PrivateStorage,
    *,
    user: User,
    institution_name: str,
    document_type: DocumentType,
    file: ValidatedFile,
) -> StudentVerification:
    _require_allowed(document_type, STUDENT_DOCUMENTS)
    institution_name = institution_name.strip()
    if not institution_name or len(institution_name) > 180:
        raise BusinessRuleError("Enter the name of your college or university.")

    verification = user.student_verification
    if verification is None:
        verification = StudentVerification(
            user_id=user.id,
            method=StudentVerificationMethod.DOCUMENT,
            institution_name=institution_name,
        )
        db.add(verification)
        db.flush()
    else:
        _reopen_if_needed(db, verification, user)
        verification.institution_name = institution_name

    _attach_document(
        db, storage, uploader=user, document_type=document_type, file=file, student=verification
    )
    db.refresh(verification)
    return verification


def get_own_property_listing(
    db: Session, user: User, listing_id: uuid.UUID
) -> AccommodationListing:
    """A property listing that belongs to this user, or "not found".

    Someone else's listing gets exactly the same answer as one that does
    not exist, so ids cannot be probed to learn what exists.
    """
    listing = db.scalar(
        select(AccommodationListing).where(
            AccommodationListing.id == listing_id,
            AccommodationListing.owner_id == user.id,
        )
    )
    if listing is None:
        raise NotFoundError("That listing does not exist.")
    if listing.listing_type != ListingType.EXISTING_ACCOMMODATION:
        raise BusinessRuleError(
            "Only a property listing needs listing authority. A request to rent "
            "together is not a property."
        )
    return listing


def submit_listing_authority_document(
    db: Session,
    storage: PrivateStorage,
    *,
    user: User,
    listing: AccommodationListing,
    document_type: DocumentType,
    file: ValidatedFile,
    owner_name: str | None = None,
    owner_contact: str | None = None,
) -> ListingAuthorityVerification:
    """Add evidence that `user` may list `listing`.

    `listing` must come from `get_own_property_listing`, which is what
    guarantees it belongs to this user.
    """
    _require_allowed(document_type, LISTING_AUTHORITY_DOCUMENTS)
    is_agent = listing.creator_type == ListingCreatorType.AUTHORIZED_AGENT
    owner_name = (owner_name or "").strip() or None
    owner_contact = (owner_contact or "").strip() or None

    verification = listing.authority_verification
    if verification is None:
        # An agent must say who the owner is, so that an administrator can
        # check the owner's details independently and contact them.
        if is_agent and not (owner_name and owner_contact):
            raise BusinessRuleError(
                "As an agent, give the owner's name and contact details so that "
                "Roomie can confirm your authorisation with them."
            )
        verification = ListingAuthorityVerification(
            listing_id=listing.id,
            owner_name=owner_name,
            owner_contact=owner_contact,
            owner_confirmation_status=(
                OwnerConfirmationStatus.PENDING
                if is_agent
                else OwnerConfirmationStatus.NOT_REQUIRED
            ),
        )
        db.add(verification)
        db.flush()
    else:
        _reopen_if_needed(db, verification, user)
        if owner_name:
            verification.owner_name = owner_name
        if owner_contact:
            verification.owner_contact = owner_contact

    _attach_document(
        db, storage, uploader=user, document_type=document_type, file=file, authority=verification
    )
    db.refresh(verification)
    return verification
