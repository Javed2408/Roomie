"""Tests that public responses cannot leak private information."""

import pytest
from sqlalchemy.orm import Session

from app.models.enums import (
    DocumentType,
    ListingCreatorType,
    ListingLifecycleStatus,
    ModerationStatus,
    VerificationStatus,
)
from app.repositories.listings import find_public_listings
from app.schemas.listing import ListingPublic
from app.services.listing_moderation import moderate_listing
from app.services.listings import to_public_listing
from app.services.verification import record_owner_confirmation, review_verification
from tests import factories

pytestmark = pytest.mark.integration


def test_a_public_listing_never_contains_private_fields(db: Session) -> None:
    """Build a listing with every private detail set, then inspect the output."""
    admin, agent = factories.make_admin(db), factories.make_student(db, "Suresh Pillai")
    identity = factories.make_identity_verification(db, agent)
    review_verification(db, identity, new_status=VerificationStatus.APPROVED, reviewer=admin)
    listing = factories.make_property_listing(
        db,
        owner=agent,
        creator_type=ListingCreatorType.AUTHORIZED_AGENT,
        brokerage_applicable=True,
        brokerage_amount=8000,
        brokerage_note="One-time, per flat",
    )
    authority = factories.make_authority_verification(
        db, listing, owner_name="Private Owner Name", owner_contact="+91 99999 00000"
    )
    document = factories.add_document(
        db, agent, DocumentType.OWNER_AUTHORIZATION, authority=authority
    )
    db.refresh(agent)
    record_owner_confirmation(db, authority, confirmed=True, admin=admin, note="Secret call notes")
    review_verification(
        db, authority, new_status=VerificationStatus.APPROVED, reviewer=admin, note="Reviewer note"
    )
    db.refresh(listing)
    moderate_listing(db, listing, new_status=ModerationStatus.APPROVED, actor=admin)

    [found] = find_public_listings(db)
    public = to_public_listing(found)
    output = public.model_dump_json()

    for private_value in (
        "Private Owner Name",
        "+91 99999 00000",
        "Secret call notes",
        "Reviewer note",
        document.storage_key,
        "12 Private Lane",  # the society's address
        agent.email,
        agent.password_hash,
        "Pillai",  # the poster's full surname
    ):
        assert private_value not in output

    # What IS public: the facts a student needs, with specific labels.
    assert public.posted_by.display_name == "Suresh P."
    assert public.posted_by.identity_verification == "VERIFIED"
    assert public.listing_authority == "VERIFIED"
    assert public.creator_type == ListingCreatorType.AUTHORIZED_AGENT
    assert public.brokerage is not None
    assert public.brokerage.model_dump() == {
        "applicable": True,
        "amount": 8000,
        "note": "One-time, per flat",
    }


def test_the_public_schema_has_no_moderation_or_document_fields() -> None:
    """An allow-list check on the schema itself."""
    fields = set(ListingPublic.model_fields)

    for forbidden in (
        "moderation_status",
        "lifecycle_status",
        "owner_name",
        "owner_contact",
        "storage_key",
        "documents",
        "reviewer_note",
        "email",
    ):
        assert forbidden not in fields


def test_brokerage_is_stated_even_when_there_is_none(db: Session) -> None:
    listing = factories.make_property_listing(
        db,
        lifecycle_status=ListingLifecycleStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
    )

    public = to_public_listing(listing)

    assert public.brokerage is not None
    assert public.brokerage.applicable is False
    assert public.listing_authority == "NOT_VERIFIED"
    assert public.posted_by.display_name == "Roomie member"


def test_a_search_request_has_no_property_fields(db: Session) -> None:
    listing = factories.make_search_listing(db)

    public = to_public_listing(listing)

    assert public.creator_type is None
    assert public.listing_authority is None
    assert public.brokerage is None
    assert public.society is None
