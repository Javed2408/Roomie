"""Turning listing records into what the public is allowed to see."""

from __future__ import annotations

from app.models.enums import ListingType
from app.models.listing import AccommodationListing
from app.models.society import Society
from app.models.user import User
from app.schemas.listing import (
    BrokeragePublic,
    ListingPosterPublic,
    ListingPublic,
    LocalityPublic,
    SocietyPublic,
)
from app.services.verification import public_state


def public_society(society: Society) -> SocietyPublic:
    # Name and locality only. The society's address stays private.
    return SocietyPublic(
        id=society.id,
        name=society.name,
        locality=LocalityPublic(
            id=society.locality.id, name=society.locality.name, city=society.locality.city
        ),
    )


def _display_name(user: User) -> str:
    """ "Rohan Mehta" -> "Rohan M.". Never the email address."""
    profile = user.student_profile
    if profile is None or not profile.full_name.strip():
        return "Roomie member"
    parts = profile.full_name.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


def to_public_listing(listing: AccommodationListing) -> ListingPublic:
    """Build the public view of a listing.

    Call this only for a listing that passed the visibility rule, i.e. one
    returned by app.repositories.listings.
    """
    posted_by = ListingPosterPublic(
        id=listing.owner.id,
        display_name=_display_name(listing.owner),
        identity_verification=public_state(listing.owner.identity_verification),
    )

    if listing.listing_type == ListingType.EXISTING_ACCOMMODATION:
        return ListingPublic(
            id=listing.id,
            type=listing.listing_type,
            title=listing.title,
            description=listing.description,
            posted_by=posted_by,
            available_from=listing.available_from,
            rent_per_person=listing.rent_per_person,
            creator_type=listing.creator_type,
            listing_authority=public_state(listing.authority_verification),
            society=public_society(listing.society) if listing.society else None,
            deposit=listing.deposit,
            brokerage=BrokeragePublic(
                applicable=bool(listing.brokerage_applicable),
                amount=listing.brokerage_amount,
                note=listing.brokerage_note,
            ),
            bedroom_count=listing.bedroom_count,
            available_bedrooms=listing.available_bedrooms,
            furnishing=listing.furnishing,
        )

    return ListingPublic(
        id=listing.id,
        type=listing.listing_type,
        title=listing.title,
        description=listing.description,
        posted_by=posted_by,
        available_from=listing.available_from,
        rent_per_person=listing.rent_per_person,
        preferred_societies=[
            public_society(preference.society) for preference in listing.society_preferences
        ],
        current_group_size=listing.current_group_size,
        required_roommates=listing.required_roommates,
    )
