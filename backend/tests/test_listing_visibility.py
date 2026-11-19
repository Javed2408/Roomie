"""Tests for the rule that decides which listings the public can see.

A listing is public only when lifecycle = ACTIVE and moderation = APPROVED.
"""

import itertools

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccommodationListing
from app.models.enums import ListingLifecycleStatus, ListingType, ModerationStatus
from app.repositories.listings import ListingFilters, find_public_listing, find_public_listings
from tests import factories

pytestmark = pytest.mark.integration

EVERY_COMBINATION = list(itertools.product(ListingLifecycleStatus, ModerationStatus))


@pytest.mark.parametrize(("lifecycle", "moderation"), EVERY_COMBINATION)
def test_only_active_and_approved_is_visible(
    db: Session, lifecycle: ListingLifecycleStatus, moderation: ModerationStatus
) -> None:
    """All 16 combinations: exactly one is visible."""
    listing = factories.make_property_listing(
        db, lifecycle_status=lifecycle, moderation_status=moderation
    )
    expected = (
        lifecycle == ListingLifecycleStatus.ACTIVE and moderation == ModerationStatus.APPROVED
    )

    # The rule as Python, on a loaded listing...
    assert listing.is_publicly_visible is expected
    # ...and the same rule as SQL, inside a query. They must agree.
    found_by_query = db.scalar(
        select(AccommodationListing.id).where(
            AccommodationListing.id == listing.id,
            AccommodationListing.is_publicly_visible,
        )
    )
    assert (found_by_query is not None) is expected


def test_public_browsing_returns_only_visible_listings(db: Session) -> None:
    for lifecycle, moderation in EVERY_COMBINATION:
        factories.make_property_listing(
            db,
            lifecycle_status=lifecycle,
            moderation_status=moderation,
            title=f"{lifecycle.value}/{moderation.value}",
        )

    results = find_public_listings(db, limit=50)[0]

    assert [listing.title for listing in results] == ["ACTIVE/APPROVED"]


@pytest.mark.parametrize(
    "moderation",
    [ModerationStatus.PENDING, ModerationStatus.REJECTED, ModerationStatus.SUSPENDED],
)
def test_pending_rejected_and_suspended_never_appear(
    db: Session, moderation: ModerationStatus
) -> None:
    listing = factories.make_property_listing(
        db, lifecycle_status=ListingLifecycleStatus.ACTIVE, moderation_status=moderation
    )

    assert find_public_listings(db)[0] == []
    assert find_public_listing(db, listing.id) is None


def test_the_two_statuses_change_independently(db: Session) -> None:
    listing = factories.make_property_listing(
        db,
        lifecycle_status=ListingLifecycleStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
    )

    # The creator marks it filled: moderation is untouched.
    listing.lifecycle_status = ListingLifecycleStatus.FILLED
    db.flush()
    db.refresh(listing)
    assert listing.moderation_status == ModerationStatus.APPROVED
    assert listing.is_publicly_visible is False

    # An admin suspends it: lifecycle is untouched.
    listing.moderation_status = ModerationStatus.SUSPENDED
    db.flush()
    db.refresh(listing)
    assert listing.lifecycle_status == ListingLifecycleStatus.FILLED


def test_public_browsing_can_filter_by_type(db: Session) -> None:
    visible = {
        "lifecycle_status": ListingLifecycleStatus.ACTIVE,
        "moderation_status": ModerationStatus.APPROVED,
    }
    factories.make_property_listing(db, **visible)
    factories.make_search_listing(db, **visible)

    properties = find_public_listings(
        db, ListingFilters(listing_type=ListingType.EXISTING_ACCOMMODATION)
    )[0]
    searches = find_public_listings(
        db, ListingFilters(listing_type=ListingType.LOOKING_TO_RENT_TOGETHER)
    )[0]

    assert [item.listing_type for item in properties] == [ListingType.EXISTING_ACCOMMODATION]
    assert [item.listing_type for item in searches] == [ListingType.LOOKING_TO_RENT_TOGETHER]
