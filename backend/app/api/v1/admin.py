"""Administrator endpoints: the verification review queues.

Every route requires an administrator (`CurrentAdmin`). The screens that
use these are built in roadmap Phase 8; the endpoints exist now so that a
submitted verification can actually be reviewed.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdmin, Database
from app.core.errors import NotFoundError
from app.models.enums import VerificationStatus
from app.models.listing import AccommodationListing
from app.models.user import User
from app.models.verification import (
    IdentityVerification,
    ListingAuthorityVerification,
    StudentVerification,
)
from app.schemas.account import DocumentOut
from app.schemas.admin import (
    AdminVerificationDetail,
    AdminVerificationSummary,
    OwnerConfirmationRequest,
    ReviewRequest,
    VerificationKind,
)
from app.services.verification import (
    Verification,
    identity_verification_of,
    listing_authority_gaps,
    record_owner_confirmation,
    review_verification,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_MODELS: dict[str, type[Verification]] = {
    "identity": IdentityVerification,
    "student": StudentVerification,
    "listing-authority": ListingAuthorityVerification,
}


def _load(db: Session, kind: VerificationKind, verification_id: uuid.UUID) -> Verification:
    verification = db.get(_MODELS[kind], verification_id)
    if verification is None:
        raise NotFoundError("That verification does not exist.")
    return verification


def _applicant(verification: Verification) -> User:
    if isinstance(verification, ListingAuthorityVerification):
        return verification.listing.owner
    return verification.user


def _summary(kind: VerificationKind, verification: Verification) -> AdminVerificationSummary:
    applicant = _applicant(verification)
    listing: AccommodationListing | None = (
        verification.listing if isinstance(verification, ListingAuthorityVerification) else None
    )
    return AdminVerificationSummary(
        kind=kind,
        id=verification.id,
        status=verification.status,
        submitted_at=verification.submitted_at,
        applicant_id=applicant.id,
        applicant_email=applicant.email,
        listing_id=listing.id if listing else None,
        listing_title=listing.title if listing else None,
    )


def _detail(
    db: Session, kind: VerificationKind, verification: Verification
) -> AdminVerificationDetail:
    detail = AdminVerificationDetail(
        **_summary(kind, verification).model_dump(),
        documents=[
            DocumentOut.model_validate(document, from_attributes=True)
            for document in sorted(verification.documents, key=lambda item: item.created_at)
            if document.deleted_at is None
        ],
        reviewer_note=verification.reviewer_note,
        reviewed_at=verification.reviewed_at,
    )
    if isinstance(verification, StudentVerification):
        detail.institution_name = verification.institution_name
    if isinstance(verification, ListingAuthorityVerification):
        listing = verification.listing
        detail.creator_type = listing.creator_type
        detail.owner_name = verification.owner_name
        detail.owner_contact = verification.owner_contact
        detail.owner_confirmation_status = verification.owner_confirmation_status
        detail.owner_confirmation_note = verification.owner_confirmation_note
        detail.outstanding_requirements = listing_authority_gaps(
            listing, verification, identity_verification_of(db, listing.owner_id)
        )
    return detail


@router.get("/verifications", response_model=list[AdminVerificationSummary])
def list_verifications(
    _admin: CurrentAdmin,
    db: Database,
    kind: VerificationKind,
    status: VerificationStatus = VerificationStatus.PENDING,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AdminVerificationSummary]:
    """One review queue (there are three, one per kind), oldest first."""
    model = _MODELS[kind]
    rows = db.scalars(
        select(model).where(model.status == status).order_by(model.submitted_at).limit(limit)
    )
    return [_summary(kind, row) for row in rows]


@router.get("/verifications/{kind}/{verification_id}", response_model=AdminVerificationDetail)
def read_verification(
    kind: VerificationKind, verification_id: uuid.UUID, _admin: CurrentAdmin, db: Database
) -> AdminVerificationDetail:
    return _detail(db, kind, _load(db, kind, verification_id))


@router.post(
    "/verifications/{kind}/{verification_id}/review", response_model=AdminVerificationDetail
)
def review(
    kind: VerificationKind,
    verification_id: uuid.UUID,
    body: ReviewRequest,
    admin: CurrentAdmin,
    db: Database,
) -> AdminVerificationDetail:
    """Approve, reject or ask for resubmission. Affects only this one check."""
    verification = _load(db, kind, verification_id)
    review_verification(
        db,
        verification,
        new_status=VerificationStatus(body.status),
        reviewer=admin,
        note=body.note,
    )
    db.commit()
    return _detail(db, kind, verification)


@router.post(
    "/verifications/listing-authority/{verification_id}/owner-confirmation",
    response_model=AdminVerificationDetail,
)
def confirm_with_owner(
    verification_id: uuid.UUID, body: OwnerConfirmationRequest, admin: CurrentAdmin, db: Database
) -> AdminVerificationDetail:
    """Record that an administrator contacted the property's owner directly."""
    verification = _load(db, "listing-authority", verification_id)
    if not isinstance(verification, ListingAuthorityVerification):
        raise NotFoundError("That verification does not exist.")
    record_owner_confirmation(
        db, verification, confirmed=body.confirmed, admin=admin, note=body.note
    )
    db.commit()
    return _detail(db, "listing-authority", verification)
