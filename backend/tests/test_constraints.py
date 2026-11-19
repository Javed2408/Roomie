"""Tests that the database itself refuses invalid data.

These rules live in the database (not only in Python) so they hold no
matter which code path writes the data.
"""

from collections.abc import Callable
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Block,
    Conversation,
    Match,
    Message,
    Report,
    ReviewEvent,
    RoommatePreferences,
    StudentProfile,
    Swipe,
    UserSocietyPreference,
    VerificationDocument,
)
from app.models.enums import (
    BrokeragePayableTo,
    DocumentType,
    ListingCreatorType,
    ReportReason,
    SwipeAction,
)
from tests import factories

pytestmark = pytest.mark.integration


def assert_rejected(db: Session, build: Callable[[], object], constraint: str) -> None:
    """Saving what `build` returns must fail on the named constraint."""
    with pytest.raises(IntegrityError) as failure, db.begin_nested():
        record = build()
        if record is not None:
            db.add(record)
        db.flush()
    assert constraint in str(failure.value)


# --- Users and profiles ------------------------------------------------


def test_email_must_be_unique(db: Session) -> None:
    factories.make_user(db, email="same@example.com")

    assert_rejected(db, lambda: factories.make_user(db, email="same@example.com"), "uq_users_email")


def test_email_must_be_lower_case(db: Session) -> None:
    assert_rejected(
        db, lambda: factories.make_user(db, email="Mixed@Example.com"), "ck_users_email_lowercase"
    )


def test_role_must_be_a_known_value(db: Session) -> None:
    from sqlalchemy import text

    with pytest.raises(IntegrityError) as failure, db.begin_nested():
        db.execute(
            text(
                "INSERT INTO users (email, password_hash, role) "
                "VALUES ('x@example.com', 'hash', 'SUPERUSER')"
            )
        )
    assert "ck_users_role" in str(failure.value)


def test_a_user_has_at_most_one_student_profile(db: Session) -> None:
    student = factories.make_student(db)
    db.expunge_all()

    assert_rejected(
        db,
        lambda: StudentProfile(user_id=student.id, full_name="Again", college_name="SRM"),
        "pk_student_profiles",
    )


def test_minimum_budget_cannot_exceed_maximum(db: Session) -> None:
    user = factories.make_user(db)

    assert_rejected(
        db,
        lambda: RoommatePreferences(user_id=user.id, min_budget=12000, max_budget=9000),
        "ck_roommate_preferences_budget_range_ordered",
    )


def test_two_societies_cannot_share_a_rank(db: Session) -> None:
    user = factories.make_user(db)
    first, second = factories.make_society(db), factories.make_society(db)
    db.add(UserSocietyPreference(user_id=user.id, society_id=first.id, priority=1))
    db.flush()

    assert_rejected(
        db,
        lambda: UserSocietyPreference(user_id=user.id, society_id=second.id, priority=1),
        "uq_user_society_preferences_user_id_priority",
    )


# --- Listings: creator types and brokerage ------------------------------


@pytest.mark.parametrize("creator_type", list(ListingCreatorType))
def test_a_property_accepts_each_creator_type(
    db: Session, creator_type: ListingCreatorType
) -> None:
    listing = factories.make_property_listing(db, creator_type=creator_type)

    assert listing.creator_type == creator_type


def test_a_property_must_state_its_creator_type(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(db, creator_type=None),
        "ck_accommodation_listings_creator_type_matches_listing_type",
    )


def test_a_search_request_cannot_have_a_creator_type(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_search_listing(db, creator_type=ListingCreatorType.PROPERTY_OWNER),
        "ck_accommodation_listings_creator_type_matches_listing_type",
    )


def test_an_unknown_creator_type_is_rejected(db: Session) -> None:
    from sqlalchemy import text

    listing = factories.make_property_listing(db)

    with pytest.raises(IntegrityError) as failure, db.begin_nested():
        db.execute(
            text("UPDATE accommodation_listings SET creator_type = 'BROKER' WHERE id = :id"),
            {"id": listing.id},
        )
    assert "ck_accommodation_listings_creator_type" in str(failure.value)


def test_a_property_must_disclose_brokerage(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(db, brokerage_applicable=None),
        "ck_accommodation_listings_brokerage_disclosed_for_property",
    )


def test_brokerage_that_applies_needs_an_amount(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(db, brokerage_applicable=True),
        "ck_accommodation_listings_brokerage_amount_matches_flag",
    )


def test_no_brokerage_means_no_amount(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(
            db, brokerage_applicable=False, brokerage_amount=5000
        ),
        "ck_accommodation_listings_brokerage_amount_matches_flag",
    )


def test_brokerage_with_an_amount_and_a_recipient_is_accepted(db: Session) -> None:
    listing = factories.make_property_listing(
        db,
        brokerage_applicable=True,
        brokerage_amount=8000,
        brokerage_note="One-time",
        brokerage_payable_to=BrokeragePayableTo.THIRD_PARTY_AGENT,
    )

    assert listing.brokerage_amount == 8000


def test_brokerage_must_name_who_receives_it(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(
            db, brokerage_applicable=True, brokerage_amount=8000
        ),
        "ck_accommodation_listings_brokerage_payee_matches_flag",
    )


def test_no_brokerage_means_no_recipient(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(
            db,
            brokerage_applicable=False,
            brokerage_payable_to=BrokeragePayableTo.THIRD_PARTY_AGENT,
        ),
        "ck_accommodation_listings_brokerage_payee_matches_flag",
    )


@pytest.mark.parametrize(
    "creator_type", [ListingCreatorType.PROPERTY_OWNER, ListingCreatorType.EXISTING_TENANT]
)
def test_only_an_agent_may_collect_brokerage_themselves(
    db: Session, creator_type: ListingCreatorType
) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(
            db,
            creator_type=creator_type,
            brokerage_applicable=True,
            brokerage_amount=8000,
            brokerage_payable_to=BrokeragePayableTo.LISTING_CREATOR,
        ),
        "ck_accommodation_listings_only_agents_collect_brokerage",
    )


def test_an_agent_may_collect_their_own_disclosed_brokerage(db: Session) -> None:
    listing = factories.make_property_listing(
        db,
        creator_type=ListingCreatorType.AUTHORIZED_AGENT,
        brokerage_applicable=True,
        brokerage_amount=9000,
        brokerage_payable_to=BrokeragePayableTo.LISTING_CREATOR,
    )

    assert listing.brokerage_payable_to == BrokeragePayableTo.LISTING_CREATOR


def test_only_known_facilities_are_accepted(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(db, facilities=["WIFI", "CALL 98765 43210"]),
        "ck_accommodation_listings_facilities_known",
    )
    listing = factories.make_property_listing(db, facilities=["WIFI", "POWER_BACKUP"])
    assert listing.facilities == ["WIFI", "POWER_BACKUP"]


def test_a_property_must_name_its_society(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(db, society_id=None),
        "ck_accommodation_listings_property_has_society",
    )


def test_available_rooms_cannot_exceed_bedrooms(db: Session) -> None:
    assert_rejected(
        db,
        lambda: factories.make_property_listing(db, bedroom_count=2, available_bedrooms=3),
        "ck_accommodation_listings_available_bedrooms_within_total",
    )


def test_a_new_listing_starts_as_a_pending_draft(db: Session) -> None:
    """The database defaults are the safe ones: not live, not approved."""
    from sqlalchemy import text

    owner = factories.make_user(db)
    listing_id = db.scalar(
        text(
            "INSERT INTO accommodation_listings "
            "(owner_id, listing_type, title, description, rent_per_person, "
            " available_from, current_group_size, required_roommates) "
            "VALUES (:owner, 'LOOKING_TO_RENT_TOGETHER', 't', 'd', 9000, "
            " :day, 1, 1) RETURNING id"
        ),
        {"owner": owner.id, "day": date(2027, 1, 1)},
    )
    row = db.execute(
        text(
            "SELECT lifecycle_status, moderation_status FROM accommodation_listings WHERE id = :id"
        ),
        {"id": listing_id},
    ).one()

    assert tuple(row) == ("DRAFT", "PENDING")


# --- Verification documents and review history --------------------------


def test_a_document_must_belong_to_a_verification(db: Session) -> None:
    user = factories.make_user(db)

    assert_rejected(
        db,
        lambda: VerificationDocument(
            document_type=DocumentType.GOVERNMENT_ID,
            storage_key="private/orphan.pdf",
            content_type="application/pdf",
            size_bytes=10,
            uploaded_by=user.id,
        ),
        "ck_verification_documents_exactly_one_verification",
    )


def test_a_document_cannot_belong_to_two_verifications(db: Session) -> None:
    user = factories.make_user(db)
    identity = factories.make_identity_verification(db, user)
    student = factories.make_student_verification(db, user)

    assert_rejected(
        db,
        lambda: VerificationDocument(
            identity_verification_id=identity.id,
            student_verification_id=student.id,
            document_type=DocumentType.GOVERNMENT_ID,
            storage_key="private/shared.pdf",
            content_type="application/pdf",
            size_bytes=10,
            uploaded_by=user.id,
        ),
        "ck_verification_documents_exactly_one_verification",
    )


def test_a_review_event_must_have_exactly_one_subject(db: Session) -> None:
    admin = factories.make_admin(db)

    assert_rejected(
        db,
        lambda: ReviewEvent(actor_id=admin.id, to_status="APPROVED"),
        "ck_review_events_exactly_one_subject",
    )


def test_a_user_has_at_most_one_identity_verification(db: Session) -> None:
    user = factories.make_user(db)
    factories.make_identity_verification(db, user)

    assert_rejected(
        db,
        lambda: factories.make_identity_verification(db, user),
        "uq_identity_verifications_user_id",
    )


def test_a_listing_has_at_most_one_authority_verification(db: Session) -> None:
    listing = factories.make_property_listing(db)
    factories.make_authority_verification(db, listing)
    db.expunge_all()

    assert_rejected(
        db,
        lambda: factories.make_authority_verification(db, listing),
        "uq_listing_authority_verifications_listing_id",
    )


def test_a_decision_must_record_who_made_it(db: Session) -> None:
    from sqlalchemy import text

    user = factories.make_user(db)
    verification = factories.make_identity_verification(db, user)

    with pytest.raises(IntegrityError) as failure, db.begin_nested():
        db.execute(
            text("UPDATE identity_verifications SET status = 'APPROVED' WHERE id = :id"),
            {"id": verification.id},
        )
    assert "ck_identity_verifications_decision_is_attributed" in str(failure.value)


# --- Matching and safety ------------------------------------------------


def test_a_user_cannot_swipe_on_themselves(db: Session) -> None:
    user = factories.make_user(db)

    assert_rejected(
        db,
        lambda: Swipe(actor_id=user.id, target_id=user.id, action=SwipeAction.LIKE),
        "ck_swipes_not_self",
    )


def test_one_swipe_per_pair(db: Session) -> None:
    actor, target = factories.make_user(db), factories.make_user(db)
    db.add(Swipe(actor_id=actor.id, target_id=target.id, action=SwipeAction.LIKE))
    db.flush()

    assert_rejected(
        db,
        lambda: Swipe(actor_id=actor.id, target_id=target.id, action=SwipeAction.PASS),
        "uq_swipes_actor_id_target_id",
    )


def test_a_match_pair_must_be_stored_in_order(db: Session) -> None:
    first, second = sorted(
        [factories.make_user(db), factories.make_user(db)], key=lambda user: user.id
    )

    assert_rejected(
        db,
        lambda: Match(user_one_id=second.id, user_two_id=first.id, compatibility_score=80),
        "ck_matches_pair_ordered",
    )


def test_a_pair_can_only_match_once(db: Session) -> None:
    first, second = sorted(
        [factories.make_user(db), factories.make_user(db)], key=lambda user: user.id
    )
    db.add(Match(user_one_id=first.id, user_two_id=second.id, compatibility_score=80))
    db.flush()

    assert_rejected(
        db,
        lambda: Match(user_one_id=first.id, user_two_id=second.id, compatibility_score=70),
        "uq_matches_user_one_id_user_two_id",
    )


def test_a_message_cannot_be_empty(db: Session) -> None:
    first, second = sorted(
        [factories.make_user(db), factories.make_user(db)], key=lambda user: user.id
    )
    match = Match(user_one_id=first.id, user_two_id=second.id, compatibility_score=80)
    db.add(match)
    db.flush()
    conversation = Conversation(match_id=match.id)
    db.add(conversation)
    db.flush()

    assert_rejected(
        db,
        lambda: Message(conversation_id=conversation.id, sender_id=first.id, content=""),
        "ck_messages_content_length",
    )


def test_a_user_cannot_block_themselves(db: Session) -> None:
    user = factories.make_user(db)

    assert_rejected(
        db, lambda: Block(blocker_id=user.id, blocked_user_id=user.id), "ck_blocks_not_self"
    )


def test_a_report_needs_a_target(db: Session) -> None:
    reporter = factories.make_user(db)

    assert_rejected(
        db,
        lambda: Report(reporter_id=reporter.id, reason=ReportReason.OTHER),
        "ck_reports_has_a_target",
    )
