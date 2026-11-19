"""Creating and managing your own listings.

The life of a listing, as the creator sees it:

    create (DRAFT) -> add photos and evidence -> submit (ACTIVE, PENDING review)
        -> an administrator approves (now public) or rejects (fix, resubmit)
    ACTIVE <-> FILLED, and either -> CLOSED (final)

Rules that protect students (each enforced here, and the important ones
also by database constraints):

* Nobody can set a moderation status here. The only automatic changes go
  BACK to "pending": resubmitting a rejected listing, or editing an
  approved one (including its photos or brokerage). Nothing here can ever
  approve anything.
* Every edit is recorded field by field in `listing_changes`.
* Changing a property's society or the creator's role re-opens the
  listing authority check, because that evidence was for the old details.
* A property cannot be submitted until the evidence its creator type
  needs has been uploaded. Uploading is not approval: a person reviews it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    EmailNotVerifiedError,
    NotFoundError,
    PermissionDeniedError,
    ProfileIncompleteError,
)
from app.models.enums import (
    DocumentType,
    ListingCreatorType,
    ListingLifecycleStatus,
    ListingType,
    ModerationStatus,
    OwnerConfirmationStatus,
    UserRole,
    VerificationStatus,
)
from app.models.listing import (
    AccommodationListing,
    ListingChange,
    ListingImage,
    ListingInterest,
    ListingSocietyPreference,
)
from app.models.review import ReviewEvent
from app.models.user import User
from app.repositories.directory import public_society_ids
from app.schemas.listing import PropertyListingIn, SearchListingIn
from app.services.photos import ProcessedPhoto
from app.services.verification import identity_verification_of

# More than this many listings that are not closed looks like a broker.
MAX_OPEN_LISTINGS = 10

FIELD_LABELS = {
    "title": "title",
    "description": "description",
    "creator_type": "your role",
    "society_id": "society",
    "society_ids": "societies",
    "rent_per_person": "rent per person",
    "total_rent": "total rent",
    "deposit": "deposit",
    "brokerage_applicable": "brokerage",
    "brokerage_amount": "brokerage amount",
    "brokerage_payable_to": "who receives the brokerage",
    "brokerage_note": "brokerage details",
    "bedroom_count": "bedrooms",
    "available_bedrooms": "rooms available",
    "furnishing": "furnishing",
    "facilities": "facilities",
    "available_from": "availability date",
    "current_group_size": "people there now",
    "required_roommates": "people wanted",
    "lifecycle_status": "status",
    "photos": "photos",
}

_PROPERTY_IDENTITY = {"creator_type", "society_id"}


# --- Helpers ---------------------------------------------------------------------


def _json(value: Any) -> Any:
    """Make a value safe to keep in the JSON change history."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_json(item) for item in value]
    return value


def _values_from(data: PropertyListingIn | SearchListingIn) -> dict[str, Any]:
    """The form's answers as column values. Field names differ on purpose:
    the API speaks the creator's language, the table stays shared."""
    if isinstance(data, PropertyListingIn):
        return {
            "title": data.title,
            "description": data.description,
            "creator_type": data.creator_type,
            "society_id": data.society_id,
            "rent_per_person": data.rent_per_person,
            "total_rent": data.total_rent,
            "deposit": data.deposit,
            "brokerage_applicable": data.brokerage_applicable,
            "brokerage_amount": data.brokerage_amount,
            "brokerage_payable_to": data.brokerage_payable_to,
            "brokerage_note": data.brokerage_note,
            "bedroom_count": data.bedroom_count,
            "available_bedrooms": data.available_bedrooms,
            "furnishing": data.furnishing,
            "facilities": [facility.value for facility in data.facilities],
            "available_from": data.available_from,
            "current_group_size": data.current_occupants,
            "required_roommates": data.roommates_wanted,
        }
    return {
        "title": data.title,
        "description": data.description,
        "rent_per_person": data.budget_per_person,
        "bedroom_count": data.desired_bedrooms,
        "available_from": data.move_in_date,
        "current_group_size": data.current_group_size,
        "required_roommates": data.roommates_wanted,
    }


def _snapshot(listing: AccommodationListing) -> dict[str, Any]:
    fields = [
        name for name in FIELD_LABELS if name not in {"society_ids", "lifecycle_status", "photos"}
    ]
    snapshot = {name: _json(getattr(listing, name)) for name in fields}
    if listing.listing_type == ListingType.LOOKING_TO_RENT_TOGETHER:
        snapshot["society_ids"] = [
            str(preference.society_id)
            for preference in sorted(listing.society_preferences, key=lambda p: p.priority)
        ]
    return snapshot


def _diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: {"from": before.get(name), "to": value}
        for name, value in after.items()
        if before.get(name) != value
    }


def _record_change(
    db: Session,
    listing: AccommodationListing,
    actor: User,
    changes: dict[str, dict[str, Any]],
    note: str | None = None,
) -> None:
    db.add(ListingChange(listing_id=listing.id, actor_id=actor.id, changes=changes, note=note))


def _review_event(
    db: Session,
    listing: AccommodationListing,
    actor: User,
    *,
    to_status: ModerationStatus,
    note: str,
    from_status: ModerationStatus | None,
) -> None:
    db.add(
        ReviewEvent(
            listing_id=listing.id,
            actor_id=actor.id,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value,
            note=note,
        )
    )


def _requeue_if_approved(
    db: Session, listing: AccommodationListing, actor: User, note: str
) -> None:
    """An approved listing that changes goes back to review, and stays
    hidden until an administrator looks at the new version."""
    if listing.moderation_status == ModerationStatus.APPROVED:
        _review_event(
            db,
            listing,
            actor,
            from_status=ModerationStatus.APPROVED,
            to_status=ModerationStatus.PENDING,
            note=note,
        )
        listing.moderation_status = ModerationStatus.PENDING


def _require_member_who_can_list(user: User) -> None:
    if user.role != UserRole.MEMBER:
        raise PermissionDeniedError("Administrator accounts cannot create listings.")
    if user.email_verified_at is None:
        raise EmailNotVerifiedError("Confirm your email address before posting a listing.")


def _require_published_profile(user: User) -> None:
    profile = user.student_profile
    if profile is None or not profile.profile_completed:
        raise ProfileIncompleteError(
            "A request to find a place together is shown with your profile, so publish "
            "your profile first."
        )


def _require_public_societies(db: Session, society_ids: list[uuid.UUID]) -> None:
    if len(public_society_ids(db, society_ids)) != len(set(society_ids)):
        raise BusinessRuleError(
            "Choose societies from Roomie's directory. One of these is not available."
        )


def _require_editable(listing: AccommodationListing) -> None:
    if listing.lifecycle_status == ListingLifecycleStatus.CLOSED:
        raise ConflictError("A closed listing cannot be changed.")
    if listing.moderation_status == ModerationStatus.SUSPENDED:
        raise ConflictError(
            "This listing has been suspended by Roomie. It can be closed, but not changed."
        )


def _replace_search_societies(
    db: Session, listing: AccommodationListing, society_ids: list[uuid.UUID]
) -> None:
    db.execute(
        delete(ListingSocietyPreference).where(ListingSocietyPreference.listing_id == listing.id)
    )
    db.flush()
    for priority, society_id in enumerate(society_ids, start=1):
        db.add(
            ListingSocietyPreference(
                listing_id=listing.id, society_id=society_id, priority=priority
            )
        )
    db.flush()
    db.refresh(listing, ["society_preferences"])


# --- Creating and editing ----------------------------------------------------------


def create_listing(
    db: Session, user: User, data: PropertyListingIn | SearchListingIn
) -> AccommodationListing:
    """Save a new listing as a DRAFT. Nobody else can see it yet."""
    _require_member_who_can_list(user)
    is_search = isinstance(data, SearchListingIn)
    if is_search:
        _require_published_profile(user)
        _require_public_societies(db, data.society_ids)
    else:
        _require_public_societies(db, [data.society_id])

    open_listings = db.scalar(
        select(func.count())
        .select_from(AccommodationListing)
        .where(
            AccommodationListing.owner_id == user.id,
            AccommodationListing.lifecycle_status != ListingLifecycleStatus.CLOSED,
        )
    )
    if (open_listings or 0) >= MAX_OPEN_LISTINGS:
        raise BusinessRuleError(
            f"You can have at most {MAX_OPEN_LISTINGS} listings open at once. "
            "Close one you no longer need."
        )

    duplicate = db.scalar(
        select(AccommodationListing.id).where(
            AccommodationListing.owner_id == user.id,
            AccommodationListing.listing_type == data.listing_type,
            func.lower(AccommodationListing.title) == data.title.lower(),
            AccommodationListing.lifecycle_status != ListingLifecycleStatus.CLOSED,
        )
    )
    if duplicate is not None:
        raise ConflictError("You already have an open listing with this title.")

    listing = AccommodationListing(
        owner_id=user.id,
        listing_type=data.listing_type,
        lifecycle_status=ListingLifecycleStatus.DRAFT,
        moderation_status=ModerationStatus.PENDING,
        authority_declared_at=None if is_search else datetime.now(UTC),
        **_values_from(data),
    )
    db.add(listing)
    db.flush()
    if is_search:
        _replace_search_societies(db, listing, data.society_ids)
    _record_change(db, listing, user, _diff({}, _snapshot(listing)), note="Created as a draft.")
    db.flush()
    return listing


def update_listing(
    db: Session,
    user: User,
    listing: AccommodationListing,
    data: PropertyListingIn | SearchListingIn,
) -> AccommodationListing:
    """Replace a listing's details with new ones.

    `listing` must be the user's own (see app.repositories.listings.
    find_own_listing). If it was approved, it goes back to review.
    """
    _require_editable(listing)
    if data.listing_type != listing.listing_type:
        raise BusinessRuleError(
            "A listing's type cannot change. Close it and post a new one instead."
        )
    is_search = isinstance(data, SearchListingIn)
    if is_search:
        _require_public_societies(db, data.society_ids)
    elif data.society_id != listing.society_id:
        _require_public_societies(db, [data.society_id])

    before = _snapshot(listing)
    for name, value in _values_from(data).items():
        setattr(listing, name, value)
    db.flush()
    if is_search:
        _replace_search_societies(db, listing, data.society_ids)
    changes = _diff(before, _snapshot(listing))
    if not changes:
        return listing

    if not is_search:
        # The creator confirmed their right to list it again with this edit.
        listing.authority_declared_at = datetime.now(UTC)
    _record_change(db, listing, user, changes)
    if not is_search and changes.keys() & _PROPERTY_IDENTITY:
        _reopen_authority(db, listing, user)
    _requeue_if_approved(db, listing, user, "Changed by its creator, so it needs review again.")
    db.flush()
    return listing


def _reopen_authority(db: Session, listing: AccommodationListing, actor: User) -> None:
    """The evidence was for the old society or role, so check it again."""
    verification = listing.authority_verification
    if verification is None:
        return
    if listing.creator_type == ListingCreatorType.AUTHORIZED_AGENT:
        verification.owner_confirmation_status = OwnerConfirmationStatus.PENDING
    else:
        verification.owner_confirmation_status = OwnerConfirmationStatus.NOT_REQUIRED
    verification.owner_confirmed_by = None
    verification.owner_confirmed_at = None
    verification.owner_confirmation_note = None
    verification.tenant_permission_basis = None
    verification.rental_agreement_valid_until = None
    if verification.status != VerificationStatus.PENDING:
        db.add(
            ReviewEvent(
                listing_authority_verification_id=verification.id,
                actor_id=actor.id,
                from_status=verification.status.value,
                to_status=VerificationStatus.PENDING.value,
                note="The property details changed, so listing authority must be checked again.",
            )
        )
        verification.status = VerificationStatus.PENDING
        verification.submitted_at = datetime.now(UTC)


# --- Submitting --------------------------------------------------------------------


def _current_documents(listing: AccommodationListing) -> set[DocumentType]:
    verification = listing.authority_verification
    if verification is None:
        return set()
    return {
        document.document_type for document in verification.documents if document.deleted_at is None
    }


def submission_requirements(db: Session, listing: AccommodationListing) -> list[str]:
    """What the creator must still do before submitting, in their words.

    Uploading evidence is all a creator can do; whether it is good enough is
    decided by a person afterwards.
    """
    gaps: list[str] = []
    if listing.listing_type == ListingType.LOOKING_TO_RENT_TOGETHER:
        if not public_society_ids(
            db, [preference.society_id for preference in listing.society_preferences]
        ):
            gaps.append("Choose at least one society that is in Roomie's directory.")
        owner = listing.owner
        if owner.student_profile is None or not owner.student_profile.profile_completed:
            gaps.append("Publish your profile.")
        return gaps

    if listing.society_id is None or not public_society_ids(db, [listing.society_id]):
        gaps.append("The society you chose is no longer in the directory. Choose another one.")

    verification = listing.authority_verification
    documents = _current_documents(listing)
    if verification is not None and verification.status in {
        VerificationStatus.REJECTED,
        VerificationStatus.NEEDS_RESUBMISSION,
    }:
        gaps.append("Your evidence was not accepted. Upload new evidence, then submit again.")

    if listing.creator_type == ListingCreatorType.PROPERTY_OWNER:
        if DocumentType.OWNERSHIP_PROOF not in documents:
            gaps.append("Upload proof that you own the property.")
    elif listing.creator_type == ListingCreatorType.EXISTING_TENANT:
        if DocumentType.RENTAL_AGREEMENT not in documents:
            gaps.append("Upload your current rental agreement.")
    elif listing.creator_type == ListingCreatorType.AUTHORIZED_AGENT:
        if DocumentType.OWNER_AUTHORIZATION not in documents:
            gaps.append("Upload the owner's written authorisation for this property.")
        if verification is None or not (verification.owner_name and verification.owner_contact):
            gaps.append(
                "Give the owner's name and contact details, so Roomie can confirm with "
                "them directly."
            )

    if listing.creator_type in {
        ListingCreatorType.PROPERTY_OWNER,
        ListingCreatorType.AUTHORIZED_AGENT,
    }:
        identity = identity_verification_of(db, listing.owner_id)
        if identity is None or identity.status in {
            VerificationStatus.REJECTED,
            VerificationStatus.NEEDS_RESUBMISSION,
        }:
            gaps.append("Submit your identity verification (Profile, then Verification).")
    return gaps


def can_submit_now(listing: AccommodationListing) -> bool:
    """Whether the listing is in a state that can be submitted at all."""
    if listing.lifecycle_status == ListingLifecycleStatus.CLOSED:
        return False
    if listing.moderation_status == ModerationStatus.SUSPENDED:
        return False
    return (
        listing.lifecycle_status == ListingLifecycleStatus.DRAFT
        or listing.moderation_status == ModerationStatus.REJECTED
    )


def submit_listing(db: Session, user: User, listing: AccommodationListing) -> None:
    """Send a draft (or a rejected listing) to the review queue."""
    if not can_submit_now(listing):
        if listing.lifecycle_status == ListingLifecycleStatus.CLOSED:
            raise ConflictError("A closed listing cannot be submitted.")
        if listing.moderation_status == ModerationStatus.SUSPENDED:
            raise ConflictError("A suspended listing cannot be submitted.")
        raise ConflictError("This listing has already been submitted for review.")
    gaps = submission_requirements(db, listing)
    if gaps:
        raise BusinessRuleError("This listing is not ready to submit yet.", details=gaps)

    resubmitting = listing.moderation_status == ModerationStatus.REJECTED
    _review_event(
        db,
        listing,
        user,
        from_status=ModerationStatus.REJECTED if resubmitting else None,
        to_status=ModerationStatus.PENDING,
        note="Resubmitted by the creator." if resubmitting else "Submitted for review.",
    )
    listing.moderation_status = ModerationStatus.PENDING
    if listing.lifecycle_status == ListingLifecycleStatus.DRAFT:
        _record_change(
            db,
            listing,
            user,
            {"lifecycle_status": {"from": "DRAFT", "to": "ACTIVE"}},
            note="Submitted for review.",
        )
        listing.lifecycle_status = ListingLifecycleStatus.ACTIVE
    db.flush()


# --- Lifecycle -------------------------------------------------------------------------

_ALLOWED_MOVES: dict[ListingLifecycleStatus, set[ListingLifecycleStatus]] = {
    ListingLifecycleStatus.DRAFT: {ListingLifecycleStatus.CLOSED},
    ListingLifecycleStatus.ACTIVE: {ListingLifecycleStatus.FILLED, ListingLifecycleStatus.CLOSED},
    ListingLifecycleStatus.FILLED: {ListingLifecycleStatus.ACTIVE, ListingLifecycleStatus.CLOSED},
    ListingLifecycleStatus.CLOSED: set(),
}


def change_lifecycle(
    db: Session, user: User, listing: AccommodationListing, new_status: ListingLifecycleStatus
) -> None:
    """Mark as filled, reopen, or close. Never touches the moderation status."""
    current = listing.lifecycle_status
    if new_status == current:
        raise ConflictError(f"This listing is already {current.value.lower()}.")
    if current == ListingLifecycleStatus.DRAFT and new_status == ListingLifecycleStatus.ACTIVE:
        raise BusinessRuleError("Submit the draft for review to make it active.")
    if new_status not in _ALLOWED_MOVES[current]:
        raise BusinessRuleError(
            f"A {current.value.lower()} listing cannot be marked {new_status.value.lower()}."
        )
    if (
        listing.moderation_status == ModerationStatus.SUSPENDED
        and new_status != ListingLifecycleStatus.CLOSED
    ):
        raise ConflictError("A suspended listing can only be closed.")
    _record_change(
        db, listing, user, {"lifecycle_status": {"from": current.value, "to": new_status.value}}
    )
    listing.lifecycle_status = new_status
    db.flush()


def delete_listing(db: Session, listing: AccommodationListing) -> list[str]:
    """Delete a draft that was never submitted and has no evidence or interest.

    Anything else is closed instead, so its history is kept. Returns the
    photo storage keys to remove once the deletion is committed.
    """
    submitted = db.scalar(select(ReviewEvent.id).where(ReviewEvent.listing_id == listing.id))
    interested = db.scalar(
        select(ListingInterest.id).where(ListingInterest.listing_id == listing.id)
    )
    if (
        listing.lifecycle_status != ListingLifecycleStatus.DRAFT
        or submitted is not None
        or listing.authority_verification is not None
        or interested is not None
    ):
        raise ConflictError(
            "Only a draft that was never submitted, and has no evidence, can be deleted. "
            "Close this listing instead."
        )
    keys = [image.object_key for image in listing.images]
    db.delete(listing)
    db.flush()
    return keys


# --- Photos ----------------------------------------------------------------------------


def add_photo(
    db: Session,
    user: User,
    listing: AccommodationListing,
    *,
    key: str,
    photo: ProcessedPhoto,
    max_photos: int,
) -> ListingImage:
    """Attach an already-saved, cleaned photo to the listing."""
    _require_editable(listing)
    if len(listing.images) >= max_photos:
        raise BusinessRuleError(f"A listing can have at most {max_photos} photos.")
    next_order = max((image.sort_order for image in listing.images), default=-1) + 1
    image = ListingImage(
        listing_id=listing.id,
        object_key=key,
        sort_order=next_order,
        content_type=photo.content_type,
        width=photo.width,
        height=photo.height,
        size_bytes=len(photo.data),
    )
    db.add(image)
    count = len(listing.images)
    _record_change(db, listing, user, {"photos": {"from": count, "to": count + 1}})
    _requeue_if_approved(db, listing, user, "Photos changed, so it needs review again.")
    db.flush()
    db.refresh(listing, ["images"])
    return image


def remove_photo(
    db: Session, user: User, listing: AccommodationListing, photo_id: uuid.UUID
) -> str:
    """Remove one photo. Returns its storage key, to delete after commit."""
    _require_editable(listing)
    image = next((item for item in listing.images if item.id == photo_id), None)
    if image is None:
        raise NotFoundError("That photo does not exist.")
    key = image.object_key
    count = len(listing.images)
    db.delete(image)
    _record_change(db, listing, user, {"photos": {"from": count, "to": count - 1}})
    _requeue_if_approved(db, listing, user, "Photos changed, so it needs review again.")
    db.flush()
    db.refresh(listing, ["images"])
    return key
