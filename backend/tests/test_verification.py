"""Tests for the three independent verification types."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, PermissionDeniedError
from app.models import ReviewEvent
from app.models.enums import (
    DocumentType,
    ListingCreatorType,
    OwnerConfirmationStatus,
    TenantPermissionBasis,
    VerificationStatus,
)
from app.services.verification import (
    listing_authority_gaps,
    public_state,
    record_owner_confirmation,
    review_verification,
)
from tests import factories

pytestmark = pytest.mark.integration

APPROVED = VerificationStatus.APPROVED


# --- Independence -------------------------------------------------------


def test_approving_identity_does_not_verify_student_status(db: Session) -> None:
    admin, user = factories.make_admin(db), factories.make_user(db)
    identity = factories.make_identity_verification(db, user)
    student = factories.make_student_verification(db, user)

    review_verification(db, identity, new_status=APPROVED, reviewer=admin)

    assert public_state(identity) == "VERIFIED"
    assert student.status == VerificationStatus.PENDING
    assert public_state(student) == "PENDING"


def test_an_owner_can_be_verified_without_being_a_student(db: Session) -> None:
    """Identity + listing authority, with no student verification at all."""
    admin, owner = factories.make_admin(db), factories.make_user(db)
    identity = factories.make_identity_verification(db, owner)
    listing = factories.make_property_listing(db, owner=owner)
    authority = factories.make_authority_verification(db, listing)
    factories.add_document(db, owner, DocumentType.OWNERSHIP_PROOF, authority=authority)

    review_verification(db, identity, new_status=APPROVED, reviewer=admin)
    review_verification(db, authority, new_status=APPROVED, reviewer=admin)
    db.refresh(owner)

    assert public_state(owner.identity_verification) == "VERIFIED"
    assert public_state(listing.authority_verification) == "VERIFIED"
    assert owner.student_verification is None
    assert public_state(owner.student_verification) == "NOT_VERIFIED"


def test_a_student_can_be_verified_without_listing_authority(db: Session) -> None:
    admin, student_user = factories.make_admin(db), factories.make_student(db)
    identity = factories.make_identity_verification(db, student_user)
    student = factories.make_student_verification(db, student_user)
    listing = factories.make_property_listing(db, owner=student_user)

    review_verification(db, identity, new_status=APPROVED, reviewer=admin)
    review_verification(db, student, new_status=APPROVED, reviewer=admin)

    assert public_state(identity) == "VERIFIED"
    assert public_state(student) == "VERIFIED"
    assert listing.authority_verification is None
    assert public_state(listing.authority_verification) == "NOT_VERIFIED"


def test_listing_authority_is_per_listing_not_per_person(db: Session) -> None:
    admin, owner = factories.make_admin(db), factories.make_user(db)
    first = factories.make_property_listing(db, owner=owner)
    second = factories.make_property_listing(db, owner=owner)
    authority = factories.make_authority_verification(db, first)
    factories.add_document(db, owner, DocumentType.OWNERSHIP_PROOF, authority=authority)
    factories.approve_identity(db, owner, admin)

    review_verification(db, authority, new_status=APPROVED, reviewer=admin)

    assert public_state(first.authority_verification) == "VERIFIED"
    assert public_state(second.authority_verification) == "NOT_VERIFIED"


# --- What the public may learn ------------------------------------------


def test_no_record_means_not_verified() -> None:
    assert public_state(None) == "NOT_VERIFIED"


def test_a_rejection_looks_like_not_verified_to_the_public(db: Session) -> None:
    admin, user = factories.make_admin(db), factories.make_user(db)
    identity = factories.make_identity_verification(db, user)

    review_verification(
        db, identity, new_status=VerificationStatus.REJECTED, reviewer=admin, note="Blurry"
    )

    assert public_state(identity) == "NOT_VERIFIED"


def test_student_verification_lapses_after_its_end_date(db: Session) -> None:
    admin, user = factories.make_admin(db), factories.make_user(db)
    student = factories.make_student_verification(db, user, valid_until=date(2027, 5, 31))
    review_verification(db, student, new_status=APPROVED, reviewer=admin)

    assert public_state(student, today=date(2027, 5, 31)) == "VERIFIED"
    assert public_state(student, today=date(2027, 6, 1)) == "NOT_VERIFIED"


# --- Requirements for each creator type ---------------------------------


def test_an_owner_needs_verified_identity_and_proof_of_ownership(db: Session) -> None:
    admin, owner = factories.make_admin(db), factories.make_user(db)
    listing = factories.make_property_listing(
        db, owner=owner, creator_type=ListingCreatorType.PROPERTY_OWNER
    )
    authority = factories.make_authority_verification(db, listing)

    with pytest.raises(BusinessRuleError) as failure:
        review_verification(db, authority, new_status=APPROVED, reviewer=admin)
    assert failure.value.details == [
        "The owner's identity has not been verified.",
        "Proof of ownership has not been provided.",
    ]

    factories.add_document(db, owner, DocumentType.OWNERSHIP_PROOF, authority=authority)
    with pytest.raises(BusinessRuleError) as failure:
        review_verification(db, authority, new_status=APPROVED, reviewer=admin)
    assert failure.value.details == ["The owner's identity has not been verified."]

    factories.approve_identity(db, owner, admin)
    review_verification(db, authority, new_status=APPROVED, reviewer=admin)
    assert authority.status == APPROVED


NEXT_YEAR = date(date.today().year + 1, 6, 30)


def _tenant_listing(db: Session) -> tuple:
    tenant = factories.make_user(db)
    listing = factories.make_property_listing(
        db, owner=tenant, creator_type=ListingCreatorType.EXISTING_TENANT
    )
    return tenant, listing, factories.make_authority_verification(db, listing)


def test_a_rental_agreement_alone_does_not_prove_permission_to_share(db: Session) -> None:
    admin = factories.make_admin(db)
    tenant, listing, authority = _tenant_listing(db)
    # The wrong kind of document does not count.
    factories.add_document(db, tenant, DocumentType.OWNERSHIP_PROOF, authority=authority)
    assert listing_authority_gaps(listing, authority, None) == [
        "A rental agreement has not been provided.",
        "Record the date the rental agreement ends.",
        "Record what permits the tenant to take someone in: the agreement itself, or "
        "the landlord's permission.",
    ]

    factories.add_document(db, tenant, DocumentType.RENTAL_AGREEMENT, authority=authority)
    # A genuine agreement, but nothing says it allows sharing: refused.
    with pytest.raises(BusinessRuleError):
        review_verification(
            db,
            authority,
            new_status=APPROVED,
            reviewer=admin,
            rental_agreement_valid_until=NEXT_YEAR,
        )

    review_verification(
        db,
        authority,
        new_status=APPROVED,
        reviewer=admin,
        tenant_permission_basis=TenantPermissionBasis.AGREEMENT_PERMITS_SHARING,
        rental_agreement_valid_until=NEXT_YEAR,
    )
    assert authority.status == APPROVED
    assert authority.tenant_permission_basis == TenantPermissionBasis.AGREEMENT_PERMITS_SHARING
    assert authority.rental_agreement_valid_until == NEXT_YEAR


def test_landlord_permission_must_be_on_file_when_it_is_the_basis(db: Session) -> None:
    admin = factories.make_admin(db)
    tenant, _, authority = _tenant_listing(db)
    factories.add_document(db, tenant, DocumentType.RENTAL_AGREEMENT, authority=authority)
    landlord = {
        "tenant_permission_basis": TenantPermissionBasis.LANDLORD_PERMISSION,
        "rental_agreement_valid_until": NEXT_YEAR,
    }

    with pytest.raises(BusinessRuleError) as failure:
        review_verification(db, authority, new_status=APPROVED, reviewer=admin, **landlord)
    assert failure.value.details == ["The landlord's permission has not been provided."]

    factories.add_document(db, tenant, DocumentType.LANDLORD_PERMISSION, authority=authority)
    review_verification(db, authority, new_status=APPROVED, reviewer=admin, **landlord)
    assert authority.status == APPROVED


def test_an_expired_rental_agreement_cannot_be_approved_and_lapses_later(db: Session) -> None:
    admin = factories.make_admin(db)
    tenant, _, authority = _tenant_listing(db)
    factories.add_document(db, tenant, DocumentType.RENTAL_AGREEMENT, authority=authority)
    basis = TenantPermissionBasis.AGREEMENT_PERMITS_SHARING

    with pytest.raises(BusinessRuleError) as failure:
        review_verification(
            db,
            authority,
            new_status=APPROVED,
            reviewer=admin,
            tenant_permission_basis=basis,
            rental_agreement_valid_until=date(2020, 1, 31),
        )
    assert failure.value.details == ["The rental agreement has already ended."]

    review_verification(
        db,
        authority,
        new_status=APPROVED,
        reviewer=admin,
        tenant_permission_basis=basis,
        rental_agreement_valid_until=NEXT_YEAR,
    )
    assert public_state(authority) == "VERIFIED"
    # The day after the agreement ends, the authority no longer counts.
    assert public_state(authority, today=date(NEXT_YEAR.year, 7, 1)) == "NOT_VERIFIED"


def test_tenant_details_are_refused_for_anyone_but_a_tenant(db: Session) -> None:
    admin, owner = factories.make_admin(db), factories.make_user(db)
    listing = factories.make_property_listing(db, owner=owner)
    authority = factories.make_authority_verification(db, listing)

    with pytest.raises(BusinessRuleError):
        review_verification(
            db,
            authority,
            new_status=APPROVED,
            reviewer=admin,
            tenant_permission_basis=TenantPermissionBasis.AGREEMENT_PERMITS_SHARING,
        )


def test_an_agent_needs_identity_authorisation_and_owner_confirmation(db: Session) -> None:
    admin, agent = factories.make_admin(db), factories.make_user(db)
    listing = factories.make_property_listing(
        db, owner=agent, creator_type=ListingCreatorType.AUTHORIZED_AGENT
    )
    authority = factories.make_authority_verification(
        db, listing, owner_confirmation_status=OwnerConfirmationStatus.PENDING
    )

    assert listing_authority_gaps(listing, authority, None) == [
        "The agent's identity has not been verified.",
        "The owner's written authorisation has not been provided.",
        "The owner has not independently confirmed the authorisation.",
    ]

    # 1. Identity verified.
    identity = factories.make_identity_verification(db, agent)
    review_verification(db, identity, new_status=APPROVED, reviewer=admin)
    # 2. Written authorisation uploaded.
    factories.add_document(db, agent, DocumentType.OWNER_AUTHORIZATION, authority=authority)
    db.refresh(agent)

    # The agent's own paperwork is still not enough.
    with pytest.raises(BusinessRuleError) as failure:
        review_verification(db, authority, new_status=APPROVED, reviewer=admin)
    assert failure.value.details == ["The owner has not independently confirmed the authorisation."]

    # 3. An administrator reaches the owner directly.
    record_owner_confirmation(
        db,
        authority,
        confirmed=True,
        admin=admin,
        note="Phoned the owner on the number on the deed.",
    )
    review_verification(db, authority, new_status=APPROVED, reviewer=admin)

    assert authority.status == APPROVED
    assert authority.owner_confirmed_by == admin.id


def test_an_owner_who_denies_blocks_the_agent(db: Session) -> None:
    admin, agent = factories.make_admin(db), factories.make_user(db)
    listing = factories.make_property_listing(
        db, owner=agent, creator_type=ListingCreatorType.AUTHORIZED_AGENT
    )
    authority = factories.make_authority_verification(db, listing)
    identity = factories.make_identity_verification(db, agent)
    review_verification(db, identity, new_status=APPROVED, reviewer=admin)
    factories.add_document(db, agent, DocumentType.OWNER_AUTHORIZATION, authority=authority)
    db.refresh(agent)

    record_owner_confirmation(
        db, authority, confirmed=False, admin=admin, note="Owner says no agent was appointed."
    )

    assert authority.owner_confirmation_status == OwnerConfirmationStatus.DENIED
    with pytest.raises(BusinessRuleError):
        review_verification(db, authority, new_status=APPROVED, reviewer=admin)


def test_a_deleted_document_no_longer_counts(db: Session) -> None:
    from datetime import UTC, datetime

    owner = factories.make_user(db)
    identity = factories.approve_identity(db, owner)
    listing = factories.make_property_listing(db, owner=owner)
    authority = factories.make_authority_verification(db, listing)
    document = factories.add_document(db, owner, DocumentType.OWNERSHIP_PROOF, authority=authority)
    assert listing_authority_gaps(listing, authority, identity) == []

    document.deleted_at = datetime.now(UTC)
    db.flush()
    db.refresh(authority)

    assert listing_authority_gaps(listing, authority, identity) == [
        "Proof of ownership has not been provided."
    ]


# --- Review rules and history -------------------------------------------


def test_only_an_administrator_can_review(db: Session) -> None:
    member, user = factories.make_user(db), factories.make_user(db)
    identity = factories.make_identity_verification(db, user)

    with pytest.raises(PermissionDeniedError):
        review_verification(db, identity, new_status=APPROVED, reviewer=member)
    assert identity.status == VerificationStatus.PENDING


def test_a_rejection_needs_a_reason(db: Session) -> None:
    admin, user = factories.make_admin(db), factories.make_user(db)
    identity = factories.make_identity_verification(db, user)

    with pytest.raises(BusinessRuleError):
        review_verification(
            db, identity, new_status=VerificationStatus.REJECTED, reviewer=admin, note="  "
        )


def test_repeating_a_decision_is_refused(db: Session) -> None:
    admin, user = factories.make_admin(db), factories.make_user(db)
    identity = factories.make_identity_verification(db, user)
    review_verification(db, identity, new_status=APPROVED, reviewer=admin)

    with pytest.raises(ConflictError):
        review_verification(db, identity, new_status=APPROVED, reviewer=admin)


def test_every_decision_is_recorded_in_order(db: Session) -> None:
    admin, user = factories.make_admin(db), factories.make_user(db)
    identity = factories.make_identity_verification(db, user)

    review_verification(
        db,
        identity,
        new_status=VerificationStatus.NEEDS_RESUBMISSION,
        reviewer=admin,
        note="Photo is cropped",
    )
    review_verification(db, identity, new_status=APPROVED, reviewer=admin)

    history = db.scalars(
        select(ReviewEvent)
        .where(ReviewEvent.identity_verification_id == identity.id)
        .order_by(ReviewEvent.created_at, ReviewEvent.to_status.desc())
    ).all()

    assert [(event.from_status, event.to_status) for event in history] == [
        ("PENDING", "NEEDS_RESUBMISSION"),
        ("NEEDS_RESUBMISSION", "APPROVED"),
    ]
    assert history[0].note == "Photo is cropped"
    assert all(event.actor_id == admin.id for event in history)
    assert identity.reviewed_by == admin.id
    assert identity.reviewed_at is not None
