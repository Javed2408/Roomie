"""Database queries for listings.

Repositories contain queries and nothing else. Keeping them here means the
visibility rule is applied in one place that is easy to find and test.

THE public visibility rule (PRD 8.9), plus two safety additions:

1. lifecycle_status = ACTIVE AND moderation_status = APPROVED, and
2. the creator's account is still open (a suspended creator's listings
   disappear), and
3. a property's society is still in the public directory (verified and
   active, in a verified and active locality), and
4. a tenant's listing disappears once their rental agreement has ended.

For a signed-in viewer, listings by anyone they have blocked, or who has
blocked them, are also left out.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import ColumnElement, Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import (
    AccountStatus,
    ListingCreatorType,
    ListingInterestStatus,
    ListingType,
)
from app.models.listing import (
    AccommodationListing,
    ListingInterest,
    ListingSocietyPreference,
)
from app.models.society import Locality, Society
from app.models.user import User
from app.models.verification import ListingAuthorityVerification
from app.repositories.discovery import blocked_between

MAX_PAGE_SIZE = 50
SortOrder = Literal["newest", "rent_low", "available_soon"]


def _public_society(society_id_column: ColumnElement[uuid.UUID]) -> ColumnElement[bool]:
    """The society (and its locality) is verified and active."""
    return exists().where(
        Society.id == society_id_column,
        Society.is_listed,
        Locality.id == Society.locality_id,
        Locality.is_listed,
    )


def public_conditions(viewer_id: uuid.UUID | None = None) -> list[ColumnElement[bool]]:
    """Every condition a listing must meet to be shown to `viewer_id`."""
    owner_open = exists().where(
        User.id == AccommodationListing.owner_id,
        User.account_status == AccountStatus.ACTIVE,
    )
    # A tenant's right to list ends with their rental agreement.
    agreement_running = exists().where(
        ListingAuthorityVerification.listing_id == AccommodationListing.id,
        ListingAuthorityVerification.rental_agreement_valid_until >= func.current_date(),
    )
    conditions: list[ColumnElement[bool]] = [
        AccommodationListing.is_publicly_visible,
        owner_open,
        or_(
            AccommodationListing.listing_type == ListingType.LOOKING_TO_RENT_TOGETHER,
            _public_society(AccommodationListing.society_id),
        ),
        or_(
            AccommodationListing.creator_type.is_distinct_from(ListingCreatorType.EXISTING_TENANT),
            agreement_running,
        ),
    ]
    if viewer_id is not None:
        conditions.append(~blocked_between(viewer_id, AccommodationListing.owner_id))
    return conditions


def with_listing_details(statement: Select[tuple[AccommodationListing]]) -> Select:
    """Load everything a listing card needs in a few queries, not one per row."""
    return statement.options(
        selectinload(AccommodationListing.society).selectinload(Society.locality),
        selectinload(AccommodationListing.society_preferences)
        .selectinload(ListingSocietyPreference.society)
        .selectinload(Society.locality),
        selectinload(AccommodationListing.authority_verification),
        selectinload(AccommodationListing.owner).selectinload(User.identity_verification),
        selectinload(AccommodationListing.owner).selectinload(User.student_verification),
        selectinload(AccommodationListing.owner).selectinload(User.student_profile),
        selectinload(AccommodationListing.images),
    )


@dataclass(frozen=True)
class ListingFilters:
    listing_type: ListingType | None = None
    society_id: uuid.UUID | None = None
    locality_id: uuid.UUID | None = None
    min_rent: int | None = None
    max_rent: int | None = None
    # Available (or moving in) on or before this date.
    available_by: date | None = None
    # Words from the title, or a society or locality name.
    query: str | None = None


def _in_society(society_id: uuid.UUID) -> ColumnElement[bool]:
    """A property in this society, or a search hoping for it."""
    return or_(
        AccommodationListing.society_id == society_id,
        exists().where(
            ListingSocietyPreference.listing_id == AccommodationListing.id,
            ListingSocietyPreference.society_id == society_id,
        ),
    )


def _in_locality(locality_id: uuid.UUID) -> ColumnElement[bool]:
    return or_(
        exists().where(
            Society.id == AccommodationListing.society_id, Society.locality_id == locality_id
        ),
        exists().where(
            ListingSocietyPreference.listing_id == AccommodationListing.id,
            Society.id == ListingSocietyPreference.society_id,
            Society.locality_id == locality_id,
        ),
    )


def _matches_text(text: str) -> ColumnElement[bool]:
    society_named = and_(
        Society.name.icontains(text, autoescape=True),
        Society.is_listed,
    )
    return or_(
        AccommodationListing.title.icontains(text, autoescape=True),
        exists().where(Society.id == AccommodationListing.society_id, society_named),
        exists().where(
            ListingSocietyPreference.listing_id == AccommodationListing.id,
            Society.id == ListingSocietyPreference.society_id,
            society_named,
        ),
        exists().where(
            Society.id == AccommodationListing.society_id,
            Locality.id == Society.locality_id,
            Locality.name.icontains(text, autoescape=True),
        ),
    )


def _filter_conditions(filters: ListingFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.listing_type is not None:
        conditions.append(AccommodationListing.listing_type == filters.listing_type)
    if filters.society_id is not None:
        conditions.append(_in_society(filters.society_id))
    if filters.locality_id is not None:
        conditions.append(_in_locality(filters.locality_id))
    if filters.min_rent is not None:
        conditions.append(AccommodationListing.rent_per_person >= filters.min_rent)
    if filters.max_rent is not None:
        conditions.append(AccommodationListing.rent_per_person <= filters.max_rent)
    if filters.available_by is not None:
        conditions.append(AccommodationListing.available_from <= filters.available_by)
    if filters.query and filters.query.strip():
        conditions.append(_matches_text(filters.query.strip()))
    return conditions


_ORDERING = {
    "newest": (AccommodationListing.created_at.desc(), AccommodationListing.id),
    "rent_low": (AccommodationListing.rent_per_person, AccommodationListing.id),
    "available_soon": (AccommodationListing.available_from, AccommodationListing.id),
}


def find_public_listings(
    db: Session,
    filters: ListingFilters | None = None,
    *,
    viewer_id: uuid.UUID | None = None,
    sort: SortOrder = "newest",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[AccommodationListing], int]:
    """A page of listings anyone may see, and how many there are in total.

    This is the only query public browsing uses. Drafts, and pending,
    rejected and suspended listings, can never be returned by it.
    """
    conditions = public_conditions(viewer_id) + _filter_conditions(filters or ListingFilters())
    total = db.scalar(select(func.count()).select_from(AccommodationListing).where(*conditions))
    statement = (
        select(AccommodationListing)
        .where(*conditions)
        .order_by(*_ORDERING[sort])
        .limit(min(max(limit, 1), MAX_PAGE_SIZE))
        .offset(max(offset, 0))
    )
    return list(db.scalars(with_listing_details(statement))), int(total or 0)


def find_public_listing(
    db: Session, listing_id: uuid.UUID, *, viewer_id: uuid.UUID | None = None
) -> AccommodationListing | None:
    """One listing, but only if `viewer_id` may see it."""
    statement = select(AccommodationListing).where(
        AccommodationListing.id == listing_id, *public_conditions(viewer_id)
    )
    return db.scalar(with_listing_details(statement))


def find_own_listing(
    db: Session, owner_id: uuid.UUID, listing_id: uuid.UUID
) -> AccommodationListing | None:
    """One of the owner's listings, whatever its status. Someone else's
    listing is not found, exactly like one that does not exist."""
    statement = select(AccommodationListing).where(
        AccommodationListing.id == listing_id, AccommodationListing.owner_id == owner_id
    )
    return db.scalar(with_listing_details(statement))


def find_own_listings(db: Session, owner_id: uuid.UUID) -> Sequence[AccommodationListing]:
    statement = (
        select(AccommodationListing)
        .where(AccommodationListing.owner_id == owner_id)
        .order_by(AccommodationListing.updated_at.desc(), AccommodationListing.id)
    )
    return db.scalars(with_listing_details(statement)).all()


def pending_interest_counts(db: Session, listing_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not listing_ids:
        return {}
    rows = db.execute(
        select(ListingInterest.listing_id, func.count())
        .where(
            ListingInterest.listing_id.in_(listing_ids),
            ListingInterest.status == ListingInterestStatus.PENDING,
        )
        .group_by(ListingInterest.listing_id)
    )
    return {listing_id: int(count) for listing_id, count in rows}
