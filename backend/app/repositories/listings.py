"""Database queries for listings.

Repositories contain queries and nothing else. Keeping them here means the
visibility rule is applied in one place that is easy to find and test.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import ListingType
from app.models.listing import AccommodationListing, ListingSocietyPreference
from app.models.society import Society
from app.models.user import User

MAX_PAGE_SIZE = 50


def find_public_listings(
    db: Session,
    *,
    listing_type: ListingType | None = None,
    society_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[AccommodationListing]:
    """Listings that anyone may see: active AND approved, nothing else.

    This is the only query public browsing should use. Pending, rejected
    and suspended listings can never be returned by it.
    """
    query = (
        select(AccommodationListing)
        .where(AccommodationListing.is_publicly_visible)
        # Load everything a public listing card needs in a few queries
        # rather than one extra query per listing.
        .options(
            selectinload(AccommodationListing.society).selectinload(Society.locality),
            selectinload(AccommodationListing.society_preferences)
            .selectinload(ListingSocietyPreference.society)
            .selectinload(Society.locality),
            selectinload(AccommodationListing.authority_verification),
            selectinload(AccommodationListing.owner).selectinload(User.identity_verification),
            selectinload(AccommodationListing.owner).selectinload(User.student_profile),
        )
        .order_by(AccommodationListing.created_at.desc(), AccommodationListing.id)
        .limit(min(max(limit, 1), MAX_PAGE_SIZE))
        .offset(max(offset, 0))
    )
    if listing_type is not None:
        query = query.where(AccommodationListing.listing_type == listing_type)
    if society_id is not None:
        query = query.where(AccommodationListing.society_id == society_id)

    return list(db.scalars(query))


def find_public_listing(db: Session, listing_id: uuid.UUID) -> AccommodationListing | None:
    """One listing, but only if it is publicly visible."""
    return db.scalar(
        select(AccommodationListing).where(
            AccommodationListing.id == listing_id,
            AccommodationListing.is_publicly_visible,
        )
    )
