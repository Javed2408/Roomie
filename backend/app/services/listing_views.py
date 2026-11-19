"""What a listing's creator, and an administrator, see about a listing.

The creator sees their own listing in every state, with the reason for a
rejection or suspension, the state of the listing authority check and
what is still missing. They never see an administrator's internal notes
about anything else, or another person's documents.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import (
    ListingLifecycleStatus,
    ListingType,
    ModerationStatus,
    VerificationStatus,
)
from app.models.listing import AccommodationListing, ListingChange, ListingInterest
from app.models.review import ReviewEvent
from app.models.user import User
from app.repositories import listings as listings_repo
from app.schemas.admin import (
    AdminListingChangeOut,
    AdminListingDetail,
    AdminListingSummary,
    AdminReviewEventOut,
)
from app.schemas.listing import (
    OwnAuthorityOut,
    OwnListingEventOut,
    OwnListingOut,
    OwnListingSummaryOut,
)
from app.services import listing_management as management
from app.services.listings import photo_out, to_public_listing
from app.services.verification import identity_verification_of, listing_authority_gaps

_NOT_APPROVED = {VerificationStatus.REJECTED, VerificationStatus.NEEDS_RESUBMISSION}

_MODERATION_SUMMARIES = {
    ModerationStatus.APPROVED: "Approved: now visible to students",
    ModerationStatus.REJECTED: "Not approved",
    ModerationStatus.SUSPENDED: "Suspended by Roomie",
}
_AUTHORITY_SUMMARIES = {
    VerificationStatus.APPROVED: "Listing authority verified",
    VerificationStatus.REJECTED: "Listing authority not approved",
    VerificationStatus.NEEDS_RESUBMISSION: "More evidence of listing authority needed",
    VerificationStatus.PENDING: "Listing authority waiting for review",
}


def _listing_events(db: Session, listing: AccommodationListing) -> list[ReviewEvent]:
    return list(
        db.scalars(
            select(ReviewEvent)
            .where(ReviewEvent.listing_id == listing.id)
            .options(selectinload(ReviewEvent.actor))
            .order_by(ReviewEvent.created_at, ReviewEvent.id)
        )
    )


def _authority_events(db: Session, listing: AccommodationListing) -> list[ReviewEvent]:
    verification = listing.authority_verification
    if verification is None:
        return []
    return list(
        db.scalars(
            select(ReviewEvent)
            .where(ReviewEvent.listing_authority_verification_id == verification.id)
            .options(selectinload(ReviewEvent.actor))
            .order_by(ReviewEvent.created_at, ReviewEvent.id)
        )
    )


def _changes(db: Session, listing: AccommodationListing) -> list[ListingChange]:
    return list(
        db.scalars(
            select(ListingChange)
            .where(ListingChange.listing_id == listing.id)
            .order_by(ListingChange.sequence)
        )
    )


def moderation_reason(db: Session, listing: AccommodationListing) -> str | None:
    """Why the listing is rejected or suspended right now, if it is."""
    if listing.moderation_status not in {ModerationStatus.REJECTED, ModerationStatus.SUSPENDED}:
        return None
    return db.scalar(
        select(ReviewEvent.note)
        .where(
            ReviewEvent.listing_id == listing.id,
            ReviewEvent.to_status == listing.moderation_status.value,
        )
        .order_by(ReviewEvent.created_at.desc(), ReviewEvent.id.desc())
        .limit(1)
    )


def _own_authority(listing: AccommodationListing) -> OwnAuthorityOut | None:
    if listing.listing_type != ListingType.EXISTING_ACCOMMODATION:
        return None
    verification = listing.authority_verification
    if verification is None:
        return OwnAuthorityOut(
            status="NOT_SUBMITTED", owner_confirmation="NOT_REQUIRED", documents=[]
        )
    return OwnAuthorityOut(
        status=verification.status.value,  # type: ignore[arg-type]
        # The reviewer writes this for the creator when not approving.
        reason=verification.reviewer_note if verification.status in _NOT_APPROVED else None,
        owner_confirmation=verification.owner_confirmation_status.value,  # type: ignore[arg-type]
        documents=sorted(
            {
                document.document_type.value
                for document in verification.documents
                if document.deleted_at is None
            }
        ),
    )


def _history(db: Session, listing: AccommodationListing) -> list[OwnListingEventOut]:
    events: list[OwnListingEventOut] = []
    for event in _listing_events(db, listing):
        status = ModerationStatus(event.to_status)
        summary = _MODERATION_SUMMARIES.get(status) or (event.note or "Waiting for review")
        events.append(
            OwnListingEventOut(
                at=event.created_at,
                kind="moderation",
                summary=summary,
                note=event.note
                if status in {ModerationStatus.REJECTED, ModerationStatus.SUSPENDED}
                else None,
            )
        )
    for event in _authority_events(db, listing):
        status = VerificationStatus(event.to_status)
        events.append(
            OwnListingEventOut(
                at=event.created_at,
                kind="authority",
                summary=_AUTHORITY_SUMMARIES[status],
                note=event.note if status in _NOT_APPROVED else None,
            )
        )
    for change in _changes(db, listing):
        labels = [management.FIELD_LABELS.get(name, name) for name in change.changes]
        events.append(
            OwnListingEventOut(
                at=change.created_at,
                kind="edit",
                summary=change.note or f"Changed: {', '.join(labels)}",
            )
        )
    return sorted(events, key=lambda item: item.at)


def own_listing_out(db: Session, listing: AccommodationListing) -> OwnListingOut:
    db.refresh(listing)
    requirements = management.submission_requirements(db, listing)
    counts = listings_repo.pending_interest_counts(db, [listing.id])
    return OwnListingOut(
        listing=to_public_listing(listing),
        lifecycle_status=listing.lifecycle_status,
        moderation_status=listing.moderation_status,
        moderation_reason=moderation_reason(db, listing),
        is_public=listings_repo.find_public_listing(db, listing.id) is not None,
        authority=_own_authority(listing),
        submission_requirements=requirements,
        can_submit=management.can_submit_now(listing) and not requirements,
        can_edit=listing.lifecycle_status != ListingLifecycleStatus.CLOSED
        and listing.moderation_status != ModerationStatus.SUSPENDED,
        pending_interests=counts.get(listing.id, 0),
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        history=_history(db, listing),
    )


def own_listing_summaries(
    db: Session, listings: list[AccommodationListing]
) -> list[OwnListingSummaryOut]:
    counts = listings_repo.pending_interest_counts(db, [listing.id for listing in listings])
    public_ids = {
        listing.id
        for listing in listings
        if listings_repo.find_public_listing(db, listing.id) is not None
    }
    return [
        OwnListingSummaryOut(
            id=listing.id,
            type=listing.listing_type,
            title=listing.title,
            lifecycle_status=listing.lifecycle_status,
            moderation_status=listing.moderation_status,
            moderation_reason=moderation_reason(db, listing),
            is_public=listing.id in public_ids,
            authority_status=(
                listing.authority_verification.status.value
                if listing.authority_verification
                else (
                    "NOT_SUBMITTED"
                    if listing.listing_type == ListingType.EXISTING_ACCOMMODATION
                    else None
                )
            ),
            pending_interests=counts.get(listing.id, 0),
            cover_photo=photo_out(listing.id, listing.images[0]) if listing.images else None,
            updated_at=listing.updated_at,
        )
        for listing in listings
    ]


# --- Administrators --------------------------------------------------------------------


def admin_summary(listing: AccommodationListing) -> AdminListingSummary:
    verification = listing.authority_verification
    return AdminListingSummary(
        id=listing.id,
        type=listing.listing_type,
        title=listing.title,
        creator_type=listing.creator_type,
        owner_id=listing.owner_id,
        owner_email=listing.owner.email,
        lifecycle_status=listing.lifecycle_status,
        moderation_status=listing.moderation_status,
        authority_status=verification.status if verification else None,
        authority_verification_id=verification.id if verification else None,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )


def admin_detail(db: Session, listing: AccommodationListing) -> AdminListingDetail:
    db.refresh(listing)
    verification = listing.authority_verification
    review_history = [
        AdminReviewEventOut(
            at=event.created_at,
            actor_email=event.actor.email,
            subject="listing",
            from_status=event.from_status,
            to_status=event.to_status,
            note=event.note,
        )
        for event in _listing_events(db, listing)
    ] + [
        AdminReviewEventOut(
            at=event.created_at,
            actor_email=event.actor.email,
            subject="listing-authority",
            from_status=event.from_status,
            to_status=event.to_status,
            note=event.note,
        )
        for event in _authority_events(db, listing)
    ]
    changes = _changes(db, listing)
    actor_ids = {change.actor_id for change in changes}
    emails = {
        user_id: email
        for user_id, email in db.execute(select(User.id, User.email).where(User.id.in_(actor_ids)))
    }
    interest_count = db.scalar(
        select(func.count())
        .select_from(ListingInterest)
        .where(ListingInterest.listing_id == listing.id)
    )
    return AdminListingDetail(
        **admin_summary(listing).model_dump(),
        listing=to_public_listing(listing),
        authority_requirements=(
            listing_authority_gaps(
                listing, verification, identity_verification_of(db, listing.owner_id)
            )
            if verification is not None
            else []
        ),
        owner_confirmation_status=verification.owner_confirmation_status if verification else None,
        review_history=sorted(review_history, key=lambda item: item.at),
        change_history=[
            AdminListingChangeOut(
                at=change.created_at,
                actor_email=emails.get(change.actor_id, "unknown"),
                changes=change.changes,
                note=change.note,
            )
            for change in changes
        ],
        interest_count=int(interest_count or 0),
    )
