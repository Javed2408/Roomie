"""Browsing accommodation, listing photos, and expressing interest.

Every route needs a signed-in member. Browsing only ever returns listings
that pass the visibility rule in app/repositories/listings.py (active,
approved, creator's account open, society still in the directory, and
not blocked either way). Anything else answers "not found".
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, Database
from app.api.photos import PhotoStorage, photo_response
from app.core.errors import NotFoundError
from app.core.rate_limit import rate_limit
from app.models.enums import ListingType, UserRole
from app.models.listing import AccommodationListing, ListingImage
from app.repositories import listings as listings_repo
from app.schemas.account import MessageResponse
from app.schemas.listing import (
    InterestIn,
    InterestOut,
    ListingPageOut,
    ListingViewOut,
    MyInterestOut,
)
from app.services import listing_interest as interest_service
from app.services.listings import to_public_listing

router = APIRouter(tags=["listings"])

_interest_limit = Depends(rate_limit("listing-interest", limit=60, window_seconds=10 * 60))
Money = Annotated[int | None, Query(ge=0, le=1_000_000)]


@router.get("/listings", response_model=ListingPageOut)
def browse_listings(
    user: CurrentUser,
    db: Database,
    type: ListingType | None = None,  # noqa: A002 - the query parameter's name
    society_id: uuid.UUID | None = None,
    locality_id: uuid.UUID | None = None,
    min_rent: Money = None,
    max_rent: Money = None,
    available_by: date | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    sort: listings_repo.SortOrder = "newest",
    limit: Annotated[int, Query(ge=1, le=listings_repo.MAX_PAGE_SIZE)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> ListingPageOut:
    """Approved, active listings only, with filters and paging."""
    filters = listings_repo.ListingFilters(
        listing_type=type,
        society_id=society_id,
        locality_id=locality_id,
        min_rent=min_rent,
        max_rent=max_rent,
        available_by=available_by,
        query=q,
    )
    items, total = listings_repo.find_public_listings(
        db, filters, viewer_id=user.id, sort=sort, limit=limit, offset=offset
    )
    return ListingPageOut(
        items=[to_public_listing(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/listings/{listing_id}", response_model=ListingViewOut)
def read_listing(listing_id: uuid.UUID, user: CurrentUser, db: Database) -> ListingViewOut:
    listing = listings_repo.find_public_listing(db, listing_id, viewer_id=user.id)
    if listing is None:
        raise NotFoundError("This listing is not available.")
    return ListingViewOut(
        listing=to_public_listing(listing),
        is_yours=listing.owner_id == user.id,
        your_interest=interest_service.interest_status(db, user, listing.id),
    )


@router.get("/listings/{listing_id}/photos/{photo_id}")
def read_listing_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    user: CurrentUser,
    db: Database,
    storage: PhotoStorage,
) -> Response:
    """A listing photo, for anyone who may see the listing, its creator, and
    administrators. Anyone else gets "not found"."""
    image = db.scalar(
        select(ListingImage).where(
            ListingImage.id == photo_id, ListingImage.listing_id == listing_id
        )
    )
    owner_id = db.scalar(
        select(AccommodationListing.owner_id).where(AccommodationListing.id == listing_id)
    )
    allowed = image is not None and (
        user.role == UserRole.ADMIN
        or owner_id == user.id
        or listings_repo.find_public_listing(db, listing_id, viewer_id=user.id) is not None
    )
    if image is None or not allowed:
        raise NotFoundError("That photo does not exist.")
    return photo_response(storage.read(image.object_key), image.content_type)


@router.post(
    "/listings/{listing_id}/interest",
    response_model=InterestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_interest_limit],
)
def express_interest(
    listing_id: uuid.UUID, body: InterestIn, user: CurrentUser, db: Database
) -> InterestOut:
    """Share your profile with the listing's creator. If the listing charges
    brokerage, `acknowledge_brokerage` must be true."""
    result = interest_service.express_interest(
        db, user, listing_id, acknowledge_brokerage=body.acknowledge_brokerage
    )
    db.commit()
    return result


@router.delete("/listings/{listing_id}/interest", response_model=MessageResponse)
def withdraw_interest(listing_id: uuid.UUID, user: CurrentUser, db: Database) -> MessageResponse:
    interest_service.withdraw_interest(db, user, listing_id)
    db.commit()
    return MessageResponse(message="Your interest has been withdrawn.")


@router.get("/me/interests", response_model=list[MyInterestOut])
def read_my_interests(user: CurrentUser, db: Database) -> list[MyInterestOut]:
    """Listings you have expressed interest in, and what the creator replied."""
    return interest_service.my_interests(db, user)
