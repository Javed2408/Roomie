"""Your own listings: create, edit, submit for review, photos, interest.

Every route acts only on the signed-in person's own listings. Someone
else's listing answers "not found", exactly like one that does not exist,
so ids cannot be probed. No route here can set a moderation status.

Evidence of listing authority is uploaded through
/me/listings/{id}/authority-verification (app/api/v1/verifications.py).
"""

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import AppSettings, CurrentUser, Database
from app.api.photos import PhotoStorage, UploadedPhoto, photo_upload_limit, save_photo
from app.core.errors import NotFoundError
from app.core.rate_limit import rate_limit
from app.models.enums import ListingInterestStatus
from app.models.listing import AccommodationListing
from app.models.user import User
from app.repositories import listings as listings_repo
from app.schemas.account import MessageResponse
from app.schemas.interest import InterestedStudentOut
from app.schemas.listing import (
    InterestRespondIn,
    LifecycleIn,
    ListingIn,
    OwnListingOut,
    OwnListingSummaryOut,
)
from app.services import listing_interest as interest_service
from app.services import listing_management as management
from app.services.listing_views import own_listing_out, own_listing_summaries
from app.services.photos import process_photo, read_photo_upload

router = APIRouter(prefix="/me/listings", tags=["my listings"])

_create_limit = Depends(rate_limit("listing-create", limit=20, window_seconds=3600))


def _own(db: Database, user: User, listing_id: uuid.UUID) -> AccommodationListing:
    listing = listings_repo.find_own_listing(db, user.id, listing_id)
    if listing is None:
        raise NotFoundError("That listing does not exist.")
    return listing


@router.get("", response_model=list[OwnListingSummaryOut])
def list_my_listings(user: CurrentUser, db: Database) -> list[OwnListingSummaryOut]:
    return own_listing_summaries(db, list(listings_repo.find_own_listings(db, user.id)))


@router.post(
    "",
    response_model=OwnListingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_create_limit],
)
def create_listing(body: ListingIn, user: CurrentUser, db: Database) -> OwnListingOut:
    """Save a new listing as a draft. Nobody else sees it until it has been
    submitted and approved."""
    listing = management.create_listing(db, user, body)
    db.commit()
    return own_listing_out(db, listing)


@router.get("/{listing_id}", response_model=OwnListingOut)
def read_my_listing(listing_id: uuid.UUID, user: CurrentUser, db: Database) -> OwnListingOut:
    return own_listing_out(db, _own(db, user, listing_id))


@router.put("/{listing_id}", response_model=OwnListingOut)
def update_my_listing(
    listing_id: uuid.UUID, body: ListingIn, user: CurrentUser, db: Database
) -> OwnListingOut:
    """Replace the listing's details. An approved listing goes back to
    review (and is hidden) until an administrator checks the change."""
    listing = management.update_listing(db, user, _own(db, user, listing_id), body)
    db.commit()
    return own_listing_out(db, listing)


@router.delete("/{listing_id}", response_model=MessageResponse)
def delete_my_listing(
    listing_id: uuid.UUID, user: CurrentUser, db: Database, storage: PhotoStorage
) -> MessageResponse:
    """Delete a draft that was never submitted. Anything else is closed."""
    keys = management.delete_listing(db, _own(db, user, listing_id))
    db.commit()
    for key in keys:
        storage.delete(key)
    return MessageResponse(message="The draft has been deleted.")


@router.post("/{listing_id}/submit", response_model=OwnListingOut)
def submit_my_listing(listing_id: uuid.UUID, user: CurrentUser, db: Database) -> OwnListingOut:
    """Send it to the review queue, once the required evidence is uploaded."""
    listing = _own(db, user, listing_id)
    management.submit_listing(db, user, listing)
    db.commit()
    return own_listing_out(db, listing)


@router.post("/{listing_id}/lifecycle", response_model=OwnListingOut)
def change_my_listing_lifecycle(
    listing_id: uuid.UUID, body: LifecycleIn, user: CurrentUser, db: Database
) -> OwnListingOut:
    """Mark as filled, reopen, or close. Never changes the review status."""
    listing = _own(db, user, listing_id)
    management.change_lifecycle(db, user, listing, body.status)
    db.commit()
    return own_listing_out(db, listing)


@router.post(
    "/{listing_id}/photos",
    response_model=OwnListingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[photo_upload_limit],
)
async def add_my_listing_photo(
    listing_id: uuid.UUID,
    file: UploadedPhoto,
    user: CurrentUser,
    db: Database,
    storage: PhotoStorage,
    settings: AppSettings,
) -> OwnListingOut:
    # Checked first: someone else's listing answers "not found" before the
    # file is even read.
    listing = _own(db, user, listing_id)
    photo = process_photo(await read_photo_upload(file))
    key = save_photo(storage, photo)
    try:
        management.add_photo(
            db, user, listing, key=key, photo=photo, max_photos=settings.max_listing_photos
        )
        db.commit()
    except Exception:
        storage.delete(key)
        raise
    return own_listing_out(db, listing)


@router.delete("/{listing_id}/photos/{photo_id}", response_model=OwnListingOut)
def remove_my_listing_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    user: CurrentUser,
    db: Database,
    storage: PhotoStorage,
) -> OwnListingOut:
    listing = _own(db, user, listing_id)
    key = management.remove_photo(db, user, listing, photo_id)
    db.commit()
    storage.delete(key)
    return own_listing_out(db, listing)


@router.get("/{listing_id}/interests", response_model=list[InterestedStudentOut])
def read_interested_students(
    listing_id: uuid.UUID, user: CurrentUser, db: Database
) -> list[InterestedStudentOut]:
    """People interested in your listing, with their public profiles."""
    return interest_service.interested_students(db, user, _own(db, user, listing_id))


@router.post("/{listing_id}/interests/{interest_id}", response_model=list[InterestedStudentOut])
def respond_to_interest(
    listing_id: uuid.UUID,
    interest_id: uuid.UUID,
    body: InterestRespondIn,
    user: CurrentUser,
    db: Database,
) -> list[InterestedStudentOut]:
    """Accept or decline one person's interest."""
    listing = _own(db, user, listing_id)
    interest_service.respond_to_interest(
        db, user, listing, interest_id, ListingInterestStatus(body.status)
    )
    db.commit()
    return interest_service.interested_students(db, user, listing)
