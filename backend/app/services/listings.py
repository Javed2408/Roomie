"""Turning listing records into what the public is allowed to see."""

from __future__ import annotations

from app.models.enums import Facility, ListingType
from app.models.listing import AccommodationListing, ListingImage
from app.models.society import Society
from app.models.user import User
from app.schemas.listing import (
    BrokeragePublic,
    ListingPhotoOut,
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


def _is_public(society: Society) -> bool:
    return society.is_listed and society.locality.is_listed


def _display_name(user: User) -> str:
    """ "Rohan Mehta" -> "Rohan M.". Never the email address."""
    profile = user.student_profile
    if profile is None or not profile.full_name.strip():
        return "Roomie member"
    parts = profile.full_name.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


def display_name(user: User) -> str:
    return _display_name(user)


def photo_out(listing_id: object, image: ListingImage) -> ListingPhotoOut:
    """A photo as an access-checked API address. The storage key is never
    included: the address names the listing and the photo's id only."""
    return ListingPhotoOut(
        id=image.id,
        url=f"/api/v1/listings/{listing_id}/photos/{image.id}",
        width=image.width,
        height=image.height,
    )


def to_public_listing(listing: AccommodationListing) -> ListingPublic:
    """Build the public view of a listing.

    Call this only for a listing the viewer may see: one returned by
    app.repositories.listings, or the creator's own listing.
    """
    is_property = listing.listing_type == ListingType.EXISTING_ACCOMMODATION
    posted_by = ListingPosterPublic(
        id=listing.owner.id,
        display_name=_display_name(listing.owner),
        identity_verification=public_state(listing.owner.identity_verification),
        # A request to rent together comes from a student, so say whether
        # that has been checked. A property's poster need not be a student.
        student_verification=(
            None if is_property else public_state(listing.owner.student_verification)
        ),
    )
    photos = [photo_out(listing.id, image) for image in listing.images]

    if is_property:
        return ListingPublic(
            id=listing.id,
            type=listing.listing_type,
            title=listing.title,
            description=listing.description,
            posted_by=posted_by,
            available_from=listing.available_from,
            rent_per_person=listing.rent_per_person,
            photos=photos,
            creator_type=listing.creator_type,
            listing_authority=public_state(listing.authority_verification),
            society=public_society(listing.society) if listing.society else None,
            total_rent=listing.total_rent,
            deposit=listing.deposit,
            brokerage=BrokeragePublic(
                applicable=bool(listing.brokerage_applicable),
                amount=listing.brokerage_amount,
                note=listing.brokerage_note,
                payable_to=listing.brokerage_payable_to,
            ),
            bedroom_count=listing.bedroom_count,
            available_bedrooms=listing.available_bedrooms,
            furnishing=listing.furnishing,
            facilities=[Facility(item) for item in listing.facilities],
            current_group_size=listing.current_group_size,
            required_roommates=listing.required_roommates,
        )

    return ListingPublic(
        id=listing.id,
        type=listing.listing_type,
        title=listing.title,
        description=listing.description,
        posted_by=posted_by,
        available_from=listing.available_from,
        rent_per_person=listing.rent_per_person,
        photos=photos,
        bedroom_count=listing.bedroom_count,
        # Only societies still in the directory are shown.
        preferred_societies=[
            public_society(preference.society)
            for preference in listing.society_preferences
            if _is_public(preference.society)
        ],
        current_group_size=listing.current_group_size,
        required_roommates=listing.required_roommates,
    )
