"""Tests for administrator moderation of listings."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, PermissionDeniedError
from app.models import ReviewEvent
from app.models.enums import (
    DocumentType,
    ListingCreatorType,
    ListingLifecycleStatus,
    ModerationStatus,
    VerificationStatus,
)
from app.repositories.listings import find_public_listings
from app.services.listing_moderation import moderate_listing
from app.services.verification import review_verification
from tests import factories

pytestmark = pytest.mark.integration

APPROVED = ModerationStatus.APPROVED


def test_a_property_cannot_be_approved_without_verified_authority(db: Session) -> None:
    """The safeguard against unauthorised brokers."""
    admin = factories.make_admin(db)
    listing = factories.make_property_listing(db, creator_type=ListingCreatorType.AUTHORIZED_AGENT)

    # No authority verification at all.
    with pytest.raises(BusinessRuleError):
        moderate_listing(db, listing, new_status=APPROVED, actor=admin)

    # Submitted but not yet approved.
    factories.make_authority_verification(db, listing)
    db.refresh(listing)
    with pytest.raises(BusinessRuleError):
        moderate_listing(db, listing, new_status=APPROVED, actor=admin)

    assert listing.moderation_status == ModerationStatus.PENDING
    assert find_public_listings(db)[0] == []


def test_a_property_with_verified_authority_can_be_approved(db: Session) -> None:
    admin, owner = factories.make_admin(db), factories.make_user(db)
    listing = factories.make_property_listing(db, owner=owner)
    authority = factories.make_authority_verification(db, listing)
    factories.add_document(db, owner, DocumentType.OWNERSHIP_PROOF, authority=authority)
    factories.approve_identity(db, owner, admin)
    review_verification(db, authority, new_status=VerificationStatus.APPROVED, reviewer=admin)
    db.refresh(listing)

    moderate_listing(db, listing, new_status=APPROVED, actor=admin)

    assert [item.id for item in find_public_listings(db)[0]] == [listing.id]


def test_a_search_request_needs_no_listing_authority(db: Session) -> None:
    """It is a request from students, not a property."""
    admin = factories.make_admin(db)
    listing = factories.make_search_listing(db)

    moderate_listing(db, listing, new_status=APPROVED, actor=admin)

    assert listing.is_publicly_visible is True


def test_suspending_removes_a_listing_from_public_view(db: Session) -> None:
    admin = factories.make_admin(db)
    listing = factories.make_search_listing(db)
    moderate_listing(db, listing, new_status=APPROVED, actor=admin)
    assert len(find_public_listings(db)[0]) == 1

    moderate_listing(
        db, listing, new_status=ModerationStatus.SUSPENDED, actor=admin, note="Reported as a scam"
    )

    assert find_public_listings(db)[0] == []
    # The creator's own status was not changed by the admin's decision.
    assert listing.lifecycle_status == ListingLifecycleStatus.ACTIVE


@pytest.mark.parametrize("status", [ModerationStatus.REJECTED, ModerationStatus.SUSPENDED])
def test_rejecting_or_suspending_needs_a_reason(db: Session, status: ModerationStatus) -> None:
    admin = factories.make_admin(db)
    listing = factories.make_search_listing(db)

    with pytest.raises(BusinessRuleError):
        moderate_listing(db, listing, new_status=status, actor=admin)


def test_only_an_administrator_can_moderate(db: Session) -> None:
    member = factories.make_user(db)
    listing = factories.make_search_listing(db, owner=member)

    # Not even the listing's own creator can approve it.
    with pytest.raises(PermissionDeniedError):
        moderate_listing(db, listing, new_status=APPROVED, actor=member)
    assert listing.moderation_status == ModerationStatus.PENDING


def test_repeating_a_decision_is_refused(db: Session) -> None:
    admin = factories.make_admin(db)
    listing = factories.make_search_listing(db)
    moderate_listing(db, listing, new_status=APPROVED, actor=admin)

    with pytest.raises(ConflictError):
        moderate_listing(db, listing, new_status=APPROVED, actor=admin)


def test_every_moderation_decision_is_recorded(db: Session) -> None:
    admin = factories.make_admin(db)
    listing = factories.make_search_listing(db)

    moderate_listing(db, listing, new_status=APPROVED, actor=admin)
    moderate_listing(
        db, listing, new_status=ModerationStatus.SUSPENDED, actor=admin, note="Under review"
    )

    history = db.scalars(
        select(ReviewEvent)
        .where(ReviewEvent.listing_id == listing.id)
        .order_by(ReviewEvent.created_at, ReviewEvent.to_status)
    ).all()

    assert [(event.from_status, event.to_status, event.note) for event in history] == [
        ("PENDING", "APPROVED", None),
        ("APPROVED", "SUSPENDED", "Under review"),
    ]
